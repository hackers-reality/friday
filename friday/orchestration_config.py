"""Shared config helpers for Friday's multi-agent orchestration layer.

Reads and writes the project-level config.yaml used by the NIM router,
agent registry, and orchestration scheduler.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:  # pragma: no cover - fallback for minimal environments
    yaml = None

from friday._paths import PROJECT_ROOT
from friday.logging_utils import configure_logging


logger = configure_logging(__name__)

CONFIG_PATH = Path(PROJECT_ROOT) / "config.yaml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "nim": {
        "api_base": "https://integrate.api.nvidia.com/v1",
        "rate_limit_rpm": 40,
        "model_map": {
            "code_gen": [
                "nvidia/llama-3.1-nemotron-70b-instruct",
                "deepseek/deepseek-v3",
                "meta/llama-3.3-70b-instruct",
            ],
            "image_analysis": [
                "nvidia/neva-22b",
                "microsoft/phi-3-vision-128k-instruct",
            ],
            "research": [
                "meta/llama-3.1-405b-instruct",
                "meta/llama-3.3-70b-instruct",
            ],
            "summarization": [
                "mistralai/mixtral-8x22b-instruct-v0.1",
                "meta/llama-3.3-70b-instruct",
            ],
            "reasoning": [
                "minimax/minimax-01",
                "nvidia/nemotron-4-340b-instruct",
                "meta/llama-3.1-405b-instruct",
            ],
            "general": [
                "meta/llama-3.3-70b-instruct",
                "nvidia/llama-3.1-nemotron-70b-instruct",
            ],
        },
    },
    "agents": [
        {
            "id": "research_agent",
            "name": "Veronica",
            "task_types": ["research", "summarization"],
            "nim_model": "meta/llama-3.1-405b-instruct",
            "tools": ["web_search", "deep_research"],
            "enabled": False,
        },
        {
            "id": "code_agent",
            "name": "Forge",
            "task_types": ["code_gen", "reasoning"],
            "nim_model": "nvidia/llama-3.1-nemotron-70b-instruct",
            "tools": ["read_file", "write_file", "git_ops"],
            "enabled": False,
        },
    ],
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries recursively without mutating the inputs."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def ensure_config(path: Path | None = None) -> Dict[str, Any]:
    """Load config.yaml, creating it from defaults when missing."""
    config_path = Path(path or CONFIG_PATH)
    if not config_path.exists():
        save_config(DEFAULT_CONFIG, config_path)
        return deepcopy(DEFAULT_CONFIG)

    try:
        raw_text = config_path.read_text(encoding="utf-8")
        if yaml is not None:
            raw = yaml.safe_load(raw_text) or {}
        else:
            try:
                raw = json.loads(raw_text) if raw_text.strip() else {}
            except Exception:
                logger.warning("Config %s is not JSON and PyYAML is unavailable; using defaults", config_path)
                raw = {}
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.exception("Failed to read config file %s", config_path)
        raise RuntimeError(f"Failed to load config: {exc}") from exc

    if not isinstance(raw, dict):
        raise TypeError(f"config.yaml must contain a mapping, got {type(raw)!r}")

    return deep_merge(DEFAULT_CONFIG, raw)


def save_config(config: Dict[str, Any], path: Path | None = None) -> Path:
    """Persist an orchestration config to disk."""
    config_path = Path(path or CONFIG_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        serialized = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    else:
        serialized = json.dumps(config, indent=2)
    config_path.write_text(serialized, encoding="utf-8")
    return config_path
