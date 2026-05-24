"""
FRIDAY NIM Router — maps task_type strings to NIM model IDs.
Supports config.yaml overrides under nim.model_map and auto-fallback
to next-best model in category when a model returns 404.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

_DEFAULT_MODEL_MAP: dict[str, list[str]] = {
    "code_gen": [
        "nvidia/llama-3.1-nemotron-70b-instruct",
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
}

_CONFIG_CACHE: Optional[dict] = None


def _load_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    path = Path.cwd() / "config.yaml"
    if path.exists():
        with open(path) as f:
            _CONFIG_CACHE = yaml.safe_load(f) or {}
    else:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def _build_model_map() -> dict[str, list[str]]:
    """Merge config overrides into defaults."""
    cfg = _load_config()
    overrides = cfg.get("nim", {}).get("model_map", {})
    merged = dict(_DEFAULT_MODEL_MAP)
    for task_type, models in overrides.items():
        if isinstance(models, list) and models:
            merged[task_type] = models
    return merged


def resolve_model(task_type: str, unavailable: Optional[set[str]] = None) -> Optional[str]:
    """
    Given a task type, return the best available NIM model ID.

    Args:
        task_type: e.g. 'code_gen', 'research', 'image_analysis', 'general'
        unavailable: set of model IDs known to be unavailable (from health checks)

    Returns:
        Model ID string, or None if no model available for this task type.
    """
    model_map = _build_model_map()
    candidates = model_map.get(task_type, []) or model_map.get("general", [])
    unavailable = unavailable or set()

    for model in candidates:
        if model not in unavailable:
            return model

    return candidates[0] if candidates else None


def list_task_types() -> list[str]:
    """Return all known task types."""
    return list(_build_model_map().keys())


def list_all_models() -> list[str]:
    """Return deduplicated list of all models across all task types."""
    seen: set[str] = set()
    models: list[str] = []
    for candidates in _build_model_map().values():
        for m in candidates:
            if m not in seen:
                seen.add(m)
                models.append(m)
    return models


def classify_task_type(utterance: str) -> str:
    """
    Lightweight keyword-based task type classification.
    Used before NIM call to route to correct model.
    """
    import re
    text = utterance.lower()

    # Use word boundary checks for keywords to avoid partial matches (e.g. "api" in "capital")
    def matches_any(keywords: list[str]) -> bool:
        for kw in keywords:
            # If keyword has spaces, match literally
            if " " in kw:
                pattern = rf"\b{re.escape(kw)}\b"
            else:
                # Match full word or prefix (for words longer than 4 chars)
                if len(kw) <= 4:
                    pattern = rf"\b{re.escape(kw)}\b"
                else:
                    pattern = rf"\b{re.escape(kw)}"
            if re.search(pattern, text):
                return True
        return False

    code_keywords = ["code", "function", "class", "implement", "debug", "fix", "write",
                     "algorithm", "api", "endpoint", "refactor", "test", "pull request"]
    research_keywords = ["research", "find", "search", "look up", "analyze", "compare",
                         "what is", "investigate"]
    image_keywords = ["see", "look", "image", "picture", "photo", "object", "detect",
                      "animal", "face", "hand", "scene", "what is this", "camera"]
    reasoning_keywords = ["why", "how does", "explain", "reason", "logic", "solving",
                          "strategy", "plan", "optimize", "compare and contrast"]
    summary_keywords = ["summarize", "tl;dr", "brief", "recap", "overview", "key points"]

    if matches_any(image_keywords):
        return "image_analysis"
    if matches_any(code_keywords):
        return "code_gen"
    if matches_any(summary_keywords):
        return "summarization"
    if matches_any(reasoning_keywords):
        return "reasoning"
    if matches_any(research_keywords):
        return "research"

    return "general"
