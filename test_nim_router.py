"""Tests for Friday NIM routing logic."""

from pathlib import Path

from friday.nim_router import NIMRouter
from friday.orchestration_config import save_config


def write_config(tmp_path: Path, overrides: dict | None = None) -> Path:
    config = {
        "nim": {
            "api_base": "https://integrate.api.nvidia.com/v1",
            "rate_limit_rpm": 40,
            "model_map": {
                "code_gen": ["custom/code-primary", "custom/code-fallback"],
                "general": ["custom/general-primary", "custom/general-fallback"],
            },
        },
        "agents": [],
    }
    if overrides:
        config["nim"]["model_map"].update(overrides)
    path = tmp_path / "config.yaml"
    save_config(config, path)
    return path


def test_config_override_wins(tmp_path):
    path = write_config(tmp_path)
    router = NIMRouter(config_path=path)
    assert router.get_candidates("code_gen") == ["custom/code-primary", "custom/code-fallback"]
    assert router.resolve_model("code_gen") == "custom/code-primary"


def test_catalog_filter_prefers_available_model(tmp_path):
    path = write_config(tmp_path)
    router = NIMRouter(config_path=path)
    router.update_catalog({"custom/code-fallback", "custom/general-fallback"})
    assert router.resolve_model("code_gen") == "custom/code-fallback"
    assert router.resolve_model("general") == "custom/general-fallback"


def test_mark_unavailable_skips_blocked_model(tmp_path):
    path = write_config(tmp_path)
    router = NIMRouter(config_path=path)
    router.mark_unavailable("custom/code-primary")
    assert router.resolve_model("code_gen") == "custom/code-fallback"


def test_default_category_falls_back_to_general(tmp_path):
    path = write_config(tmp_path, overrides={"research": []})
    router = NIMRouter(config_path=path)
    router.update_catalog({"meta/llama-3.3-70b-instruct"})
    assert router.resolve_model("research") == "meta/llama-3.3-70b-instruct"


def test_string_override_normalizes_to_list(tmp_path):
    config = {
        "nim": {
            "api_base": "https://integrate.api.nvidia.com/v1",
            "rate_limit_rpm": 40,
            "model_map": {
                "summary": "single/model-id",
            },
        },
        "agents": [],
    }
    path = tmp_path / "config.yaml"
    save_config(config, path)
    router = NIMRouter(config_path=path)
    assert router.get_candidates("summary") == ["single/model-id"]
