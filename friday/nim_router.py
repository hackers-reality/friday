"""Model routing for Friday's NVIDIA NIM agent pool.

Selects the best NIM model for a task type using config.yaml overrides,
runtime catalog availability, and a simple fallback order per category.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)

DEFAULT_MODEL_MAP: Dict[str, List[str]] = {
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
}

TASK_ALIASES = {
    "code": "code_gen",
    "coding": "code_gen",
    "programming": "code_gen",
    "vision": "image_analysis",
    "image": "image_analysis",
    "camera": "image_analysis",
    "photo": "image_analysis",
    "research": "research",
    "summarize": "summarization",
    "summary": "summarization",
    "reason": "reasoning",
    "reasoning": "reasoning",
    "general": "general",
    "chat": "general",
}


def _normalize_task_type(task_type: str) -> str:
    task = task_type.strip().lower()
    return TASK_ALIASES.get(task, task)


def _normalize_candidates(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        primary = value.get("primary") or value.get("model")
        fallbacks = value.get("fallbacks") or value.get("alternatives") or []
        if isinstance(fallbacks, str):
            fallbacks = [fallbacks]
        items = [primary] if primary else []
        items.extend(fallbacks)
        return [item for item in items if isinstance(item, str) and item]
    if isinstance(value, Sequence):
        return [str(item) for item in value if str(item)]
    return [str(value)]


class NIMRouter:
    """Resolve the best NIM model for a task type."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else None
        self._config = ensure_config(self._config_path) if self._config_path else ensure_config()
        self._catalog: Set[str] = set()
        self._unavailable: Set[str] = set()

    @property
    def config(self) -> Dict[str, Any]:
        """Return the current orchestration config."""
        return self._config

    def reload(self) -> Dict[str, Any]:
        """Reload config.yaml from disk."""
        self._config = ensure_config(self._config_path) if self._config_path else ensure_config()
        return self._config

    def get_candidates(self, task_type: str) -> List[str]:
        """Return the configured candidate models for a task type."""
        config_models = self._config.get("nim", {}).get("model_map", {}) or {}
        normalized_task = _normalize_task_type(task_type)
        candidates = _normalize_candidates(config_models.get(normalized_task))
        if not candidates:
            candidates = _normalize_candidates(DEFAULT_MODEL_MAP.get(normalized_task))
        if not candidates:
            candidates = _normalize_candidates(DEFAULT_MODEL_MAP["general"])
        return candidates

    def update_catalog(self, models: Iterable[str]) -> None:
        """Store a runtime catalog of available models."""
        self._catalog = {str(model) for model in models}
        logger.info("Updated NIM catalog with %d model ids", len(self._catalog))

    def mark_unavailable(self, model_id: str) -> None:
        """Remember a model that returned 404/503 so we skip it next time."""
        self._unavailable.add(model_id)

    def resolve_model(
        self,
        task_type: str,
        *,
        available_models: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> str:
        """Return the first viable model for the task type."""
        candidates = self.get_candidates(task_type)
        catalog = set(available_models or self._catalog)
        blocked = self._unavailable.union({str(item) for item in (exclude or [])})

        for model_id in candidates:
            if model_id in blocked:
                continue
            if catalog and model_id not in catalog:
                continue
            return model_id

        for model_id in candidates:
            if model_id not in blocked:
                logger.warning("Falling back to uncatalogued model %s for %s", model_id, task_type)
                return model_id

        fallback = DEFAULT_MODEL_MAP["general"][0]
        logger.warning("No candidate available for %s, falling back to %s", task_type, fallback)
        return fallback

    async def refresh_catalog(self, client: Any) -> Set[str]:
        """Ask the NIM client for the current model catalog."""
        models = await client.list_models()
        catalog = {entry if isinstance(entry, str) else entry.get("id", "") for entry in models}
        catalog = {model for model in catalog if model}
        self.update_catalog(catalog)
        return catalog


_ROUTER = NIMRouter()


def get_router() -> NIMRouter:
    """Return the shared router instance."""
    return _ROUTER
