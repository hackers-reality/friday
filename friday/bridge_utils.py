"""
FRIDAY Bridge Utilities — shared infrastructure for all *-use-bridge modules.
Provides standardized error handling, JSON logging, state/history recording,
and async-to-sync bridging across all 5 bridge modules.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

from friday._paths import FRIDAY_MEMORY

logger = logging.getLogger(__name__)


class BridgeState:
    """Per-bridge persistent state + JSON-line history."""

    def __init__(self, name: str):
        self.name = name
        self._state_path = os.path.join(FRIDAY_MEMORY, f"{name}_state.json")
        self._history_path = os.path.join(FRIDAY_MEMORY, f"{name}_history.jsonl")

    def load(self) -> dict:
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"operations": 0, "errors": 0}

    def save(self, state: dict) -> None:
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        with open(self._state_path, "w") as f:
            json.dump(state, f, indent=2)

    def record(self, action: str, status: str = "ok", **extra) -> None:
        state = self.load()
        state["operations"] = state.get("operations", 0) + 1
        if status != "ok":
            state["errors"] = state.get("errors", 0) + 1
        state["last_action"] = action
        self.save(state)
        os.makedirs(os.path.dirname(self._history_path), exist_ok=True)
        with open(self._history_path, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "status": status,
                **extra,
            }) + "\n")


def _run_async(coro) -> Any:
    """Run a coroutine synchronously — safe from sync or async contexts."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result(timeout=120)
    except RuntimeError:
        return asyncio.run(coro)


def bridge_function(
    state: BridgeState,
    action: str | None = None,
    *,
    async_wrap: bool = False,
) -> Callable:
    """Decorator that standardizes error handling, logging, and JSON output for bridge functions.

    Usage:
        state = BridgeState("desktop")

        @bridge_function(state, "list_windows")
        def desktop_list_windows() -> str:
            ...

        @bridge_function(state, "search", async_wrap=True)
        def shodan_search(query: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> str:
            op = action or func.__name__
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = round(time.time() - start, 3)
                state.record(op, status="ok", elapsed=elapsed)
                return result
            except Exception as e:
                elapsed = round(time.time() - start, 3)
                tb = traceback.format_exc()
                logger.error("[%s] %s failed: %s", state.name, op, e)
                logger.debug("Traceback:\n%s", tb)
                state.record(op, status="error", error=str(e)[:200], elapsed=elapsed)
                return json.dumps({"error": str(e), "action": op})

        if async_wrap:
            @functools.wraps(func)
            def async_wrapper(*args, **kwargs) -> str:
                op = action or func.__name__
                start = time.time()
                try:
                    impl = func(*args, **kwargs)
                    result = _run_async(impl)
                    elapsed = round(time.time() - start, 3)
                    state.record(op, status="ok", elapsed=elapsed)
                    if isinstance(result, str):
                        return result
                    return json.dumps(result, indent=2)
                except Exception as e:
                    elapsed = round(time.time() - start, 3)
                    tb = traceback.format_exc()
                    logger.error("[%s] %s failed: %s", state.name, op, e)
                    logger.debug("Traceback:\n%s", tb)
                    state.record(op, status="error", error=str(e)[:200], elapsed=elapsed)
                    return json.dumps({"error": str(e), "action": op})
            return async_wrapper

        return wrapper
    return decorator
