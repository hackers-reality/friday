"""
FRIDAY Model Router — provider abstraction with smart routing, fallback, cost metadata.
Routes requests to Gemini, OpenAI, Anthropic, or local models.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os
import time
import threading

from friday._paths import FRIDAY_CONFIG

_ROUTER_CONFIG_PATH = os.path.join(FRIDAY_CONFIG, "model_router.json")
_lock = threading.Lock()

# ─── Model Definitions ───────────────────────────────────

@dataclass
class ModelInfo:
    id: str
    provider: str
    family: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: int = 8192
    capabilities: List[str] = field(default_factory=list)
    max_output_tokens: int = 4096

    @property
    def display_name(self) -> str:
        return f"{self.provider}/{self.id}"


# ─── Preset Models ───────────────────────────────────────

PRESET_MODELS: Dict[str, ModelInfo] = {
    "gemini-2.0-flash": ModelInfo(
        id="gemini-2.0-flash",
        provider="google",
        family="gemini",
        cost_per_1k_input=0.000075,
        cost_per_1k_output=0.00015,
        context_window=1_048_576,
        capabilities=["chat", "vision", "code", "realtime", "function_calling", "streaming", "grounding"],
        max_output_tokens=8192,
    ),
    "gemini-2.5-pro": ModelInfo(
        id="gemini-2.5-pro-exp-03-25",
        provider="google",
        family="gemini",
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
        context_window=1_048_576,
        capabilities=["chat", "vision", "code", "function_calling", "reasoning", "streaming"],
        max_output_tokens=8192,
    ),
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        provider="openai",
        family="gpt",
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
        context_window=128_000,
        capabilities=["chat", "vision", "code", "function_calling", "streaming"],
        max_output_tokens=16384,
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        provider="openai",
        family="gpt",
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        context_window=128_000,
        capabilities=["chat", "vision", "code", "function_calling", "streaming"],
        max_output_tokens=16384,
    ),
    "claude-sonnet-4": ModelInfo(
        id="claude-sonnet-4-20250514",
        provider="anthropic",
        family="claude",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200_000,
        capabilities=["chat", "vision", "code", "function_calling", "streaming"],
        max_output_tokens=8192,
    ),
    "local-llama": ModelInfo(
        id="llama-3.1-8b",
        provider="local",
        family="llama",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        context_window=128_000,
        capabilities=["chat", "code"],
        max_output_tokens=4096,
    ),
}


# ─── Router Config ───────────────────────────────────────

DEFAULT_CONFIG = {
    "primary_model": "gemini-2.0-flash",
    "fallback_model": "gemini-2.5-pro",
    "code_model": "gpt-4o-mini",
    "vision_model": "gemini-2.5-pro",
    "fast_model": "gemini-2.0-flash",
    "local_model": "local-llama",
    "enable_fallback": True,
    "enable_cost_tracking": True,
    "max_retries": 2,
    "retry_delay_seconds": 1.0,
    "health_check_interval_minutes": 15,
}


def _ensure_config():
    os.makedirs(FRIDAY_CONFIG, exist_ok=True)
    if not os.path.exists(_ROUTER_CONFIG_PATH):
        with open(_ROUTER_CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()
    with open(_ROUTER_CONFIG_PATH, "r") as f:
        return json.load(f)


def _save_config(cfg: dict):
    os.makedirs(FRIDAY_CONFIG, exist_ok=True)
    with open(_ROUTER_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ─── Cost Tracking ───────────────────────────────────────

@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    timestamp: str
    success: bool
    error: Optional[str] = None


class CostTracker:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._session_costs: Dict[str, float] = {}
        self._session_tokens: Dict[str, int] = {}
        self._records: List[UsageRecord] = []

    def record(self, rec: UsageRecord):
        with self._lock:
            self._records.append(rec)
            self._session_costs[rec.model] = self._session_costs.get(rec.model, 0.0) + rec.cost
            self._session_tokens[rec.model] = self._session_tokens.get(rec.model, 0) + rec.input_tokens + rec.output_tokens
            if len(self._records) > 1000:
                self._records.pop(0)

    def get_session_stats(self) -> dict:
        with self._lock:
            return {
                "total_cost": round(sum(self._session_costs.values()), 6),
                "total_tokens": sum(self._session_tokens.values()),
                "by_model": {
                    k: {
                        "cost": round(v, 6),
                        "tokens": self._session_tokens.get(k, 0),
                    } for k, v in self._session_costs.items()
                },
                "record_count": len(self._records),
            }

    def get_recent(self, n: int = 10) -> List[dict]:
        with self._lock:
            return [
                {
                    "model": r.model,
                    "cost": r.cost,
                    "tokens": r.input_tokens + r.output_tokens,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "timestamp": r.timestamp,
                } for r in self._records[-n:]
            ][::-1]


_cost_tracker: Optional[CostTracker] = None


def _get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        os.makedirs(FRIDAY_CONFIG, exist_ok=True)
        _cost_tracker = CostTracker(os.path.join(FRIDAY_CONFIG, "model_usage.jsonl"))
    return _cost_tracker


# ─── Health Checks ───────────────────────────────────────

_provider_health: Dict[str, Dict[str, Any]] = {}
_health_lock = threading.Lock()


def check_provider_health(provider: str) -> dict:
    """Quick health check for a provider."""
    with _health_lock:
        now = time.time()
        cached = _provider_health.get(provider)
        if cached and (now - cached["checked_at"]) < 60:
            return cached

    result = {"provider": provider, "status": "unknown", "checked_at": time.time(), "latency_ms": 0}

    try:
        start = time.time()
        if provider == "google":
            import google.generativeai as genai
            genai.list_models()
            result["status"] = "ok"
        elif provider == "openai":
            import openai
            client = openai.OpenAI()
            client.models.list()
            result["status"] = "ok"
        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic()
            client.models.list()
            result["status"] = "ok"
        elif provider == "local":
            result["status"] = "ok"
        else:
            result["status"] = "unknown"
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    with _health_lock:
        _provider_health[provider] = result
    return result


# ─── Router API ──────────────────────────────────────────

def get_config() -> dict:
    return _ensure_config()


def update_config(updates: dict) -> str:
    cfg = _ensure_config()
    cfg.update(updates)
    _save_config(cfg)
    return f"[OK] Router config updated"


def list_models(filter_provider: Optional[str] = None) -> List[dict]:
    models = []
    for mid, info in PRESET_MODELS.items():
        if filter_provider and info.provider != filter_provider:
            continue
        models.append({
            "id": info.id,
            "provider": info.provider,
            "family": info.family,
            "display_name": info.display_name,
            "context_window": info.context_window,
            "cost_per_1k_input": info.cost_per_1k_input,
            "cost_per_1k_output": info.cost_per_1k_output,
            "capabilities": info.capabilities,
        })
    return models


def resolve_model(task_type: str = "chat", preferences: Optional[dict] = None) -> str:
    """Pick the best model ID for a task type."""
    cfg = _ensure_config()
    prefs = preferences or {}
    task_type = task_type.lower()

    # User override
    if "model" in prefs:
        for mid, info in PRESET_MODELS.items():
            if info.id == prefs["model"] or mid == prefs["model"]:
                return info.id

    provider_override = prefs.get("provider", "")
    if provider_override:
        for mid, info in PRESET_MODELS.items():
            if info.provider == provider_override and "chat" in info.capabilities:
                return info.id

    if task_type == "vision":
        return cfg.get("vision_model", "gemini-2.5-pro")
    if task_type == "code":
        return cfg.get("code_model", "gpt-4o-mini")
    if task_type == "fast":
        return cfg.get("fast_model", "gemini-2.0-flash")
    if task_type == "local":
        return cfg.get("local_model", "local-llama")

    return cfg.get("primary_model", "gemini-2.0-flash")


def get_model_info(model_id: str) -> Optional[dict]:
    """Get full info for a model."""
    for mid, info in PRESET_MODELS.items():
        if info.id == model_id or mid == model_id:
            return {
                "id": info.id,
                "provider": info.provider,
                "family": info.family,
                "display_name": info.display_name,
                "context_window": info.context_window,
                "cost_per_1k_input": info.cost_per_1k_input,
                "cost_per_1k_output": info.cost_per_1k_output,
                "capabilities": info.capabilities,
            }
    return None


def track_usage(model_id: str, input_tokens: int, output_tokens: int,
                latency_ms: float, success: bool, error: Optional[str] = None):
    """Record a usage entry for cost tracking."""
    cfg = _ensure_config()
    if not cfg.get("enable_cost_tracking", True):
        return

    info = get_model_info(model_id)
    cost_per_input = info["cost_per_1k_input"] if info else 0.0
    cost_per_output = info["cost_per_1k_output"] if info else 0.0
    cost = (input_tokens / 1000 * cost_per_input) + (output_tokens / 1000 * cost_per_output)

    rec = UsageRecord(
        model=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        latency_ms=latency_ms,
        timestamp=datetime.now().isoformat()[:19],
        success=success,
        error=error,
    )
    _get_cost_tracker().record(rec)


def get_cost_stats() -> dict:
    return _get_cost_tracker().get_session_stats()


def get_recent_usage(n: int = 10) -> List[dict]:
    return _get_cost_tracker().get_recent(n)


def health_all_providers() -> list:
    providers = set(m.provider for m in PRESET_MODELS.values())
    results = []
    for p in sorted(providers):
        results.append(check_provider_health(p))
    return results


# ─── Tool Function ───────────────────────────────────────

def model_router_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: Model Router — provider abstraction with fallback and cost tracking.

    Actions:
        status          - Show router configuration and costs
        list            - List available models
        resolve         - Resolve best model for a task type
        info            - Get model info by ID
        update_config   - Update router configuration
        health          - Health check all providers
        usage           - Show session cost/token usage
        recent          - Show recent usage records
    """
    action = action.lower()

    if action == "status":
        cfg = _ensure_config()
        stats = get_cost_stats()
        return (
            f"### MODEL ROUTER\n\n"
            f"Primary: {cfg.get('primary_model')}\n"
            f"Fallback: {cfg.get('fallback_model')}\n"
            f"Code: {cfg.get('code_model')}\n"
            f"Vision: {cfg.get('vision_model')}\n"
            f"Fast: {cfg.get('fast_model')}\n"
            f"Local: {cfg.get('local_model')}\n"
            f"Fallback enabled: {cfg.get('enable_fallback')}\n"
            f"Session cost: ${stats.get('total_cost', 0):.6f}\n"
            f"Session tokens: {stats.get('total_tokens', 0)}\n"
            f"Usage records: {stats.get('record_count', 0)}"
        )

    if action == "list":
        provider = kwargs.get("provider")
        models = list_models(provider)
        if not models:
            return "[OK] No models found."
        lines = ["### Available Models\n"]
        for m in models:
            lines.append(
                f"- **{m['display_name']}** — {m['context_window']} ctx, "
                f"${m['cost_per_1k_input']:.4f}/${m['cost_per_1k_output']:.4f} per 1K i/o, "
                f"capabilities: {', '.join(m['capabilities'][:4])}"
            )
        return "\n".join(lines)

    if action == "resolve":
        task_type = kwargs.get("task_type", "chat")
        prefs_str = kwargs.get("preferences", "{}")
        prefs = json.loads(prefs_str) if isinstance(prefs_str, str) else prefs_str
        model = resolve_model(task_type, prefs)
        info = get_model_info(model)
        if info:
            return (
                f"### Resolved Model\n\n"
                f"Task type: {task_type}\n"
                f"Model: {info['display_name']}\n"
                f"Context window: {info['context_window']}\n"
                f"Cost: ${info['cost_per_1k_input']:.4f} / ${info['cost_per_1k_output']:.4f} per 1K"
            )
        return f"[OK] Resolved: {model}"

    if action == "info":
        model_id = kwargs.get("model_id", "")
        info = get_model_info(model_id)
        if not info:
            return f"[FAIL] Model '{model_id}' not found."
        return json.dumps(info, indent=2)

    if action == "update_config":
        updates_raw = kwargs.get("updates", "{}")
        updates = json.loads(updates_raw) if isinstance(updates_raw, str) else updates_raw
        return update_config(updates)

    if action == "health":
        results = health_all_providers()
        lines = ["### Provider Health\n"]
        for r in results:
            emoji = "OK" if r["status"] == "ok" else ("ERR" if r["status"] == "error" else "???")
            lines.append(f"- {r['provider']}: {emoji} ({r.get('latency_ms', '?')}ms)")
            if r.get("error"):
                lines[-1] += f" — {r['error']}"
        return "\n".join(lines)

    if action == "usage":
        stats = get_cost_stats()
        return json.dumps(stats, indent=2)

    if action == "recent":
        records = get_recent_usage(int(kwargs.get("n", 10)))
        if not records:
            return "[OK] No usage records yet."
        lines = ["### Recent Usage\n"]
        for r in records:
            lines.append(
                f"- {r['model']} — {r['tokens']} tokens, ${r['cost']:.6f}, "
                f"{r['latency_ms']}ms, {'OK' if r['success'] else 'FAIL'}"
            )
        return "\n".join(lines)

    return f"[FAIL] Unknown action: {action}. Available: status, list, resolve, info, update_config, health, usage, recent"
