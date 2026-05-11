"""
Friday Hooks System — pre/post execution hooks for tool calls.
Enables logging, notifications, validation, and event-driven reactions.
"""

import os
import json
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional

# Hook registry
_pre_hooks: List[Callable] = []
_post_hooks: List[Callable] = []
_error_hooks: List[Callable] = []


def register_pre_hook(fn: Callable) -> None:
    """Register a function to run BEFORE every tool call.
    Signature: fn(name: str, args: dict, session) -> dict | None
    Return modified args or None to block execution.
    """
    _pre_hooks.append(fn)


def register_post_hook(fn: Callable) -> None:
    """Register a function to run AFTER every successful tool call.
    Signature: fn(name: str, args: dict, result: str, session)
    """
    _post_hooks.append(fn)


def register_error_hook(fn: Callable) -> None:
    """Register a function to run on tool call errors.
    Signature: fn(name: str, args: dict, error: Exception, session)
    """
    _error_hooks.append(fn)


def run_pre_hooks(name: str, args: dict, session=None) -> Optional[Dict]:
    """Run all pre-hooks. Returns modified args or None to block."""
    modified = dict(args)
    for hook in _pre_hooks:
        try:
            result = hook(name, modified, session)
            if result is None:
                return None  # Block execution
            if isinstance(result, dict):
                modified.update(result)
        except Exception:
            pass
    return modified


def run_post_hooks(name: str, args: dict, result: str, session=None) -> None:
    """Run all post-hooks."""
    for hook in _post_hooks:
        try:
            hook(name, args, result, session)
        except Exception:
            pass


def run_error_hooks(name: str, args: dict, error: Exception, session=None) -> None:
    """Run all error hooks."""
    for hook in _error_hooks:
        try:
            hook(name, args, error, session)
        except Exception:
            pass


# ─── Built-in hooks ────────────────────────────────────────#

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory", "tool_log.jsonl")
_MAX_LOG_ENTRIES = 1000


def _ensure_log_dir():
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)


def _logging_pre_hook(name: str, args: dict, session=None) -> dict:
    """Log every tool call before execution."""
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "tool_call",
        "name": name,
        "args": {k: str(v)[:100] for k, v in args.items()},
        "status": "started",
    }
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
    return args


def _logging_post_hook(name: str, args: dict, result: str, session=None) -> None:
    """Log tool call result."""
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "tool_result",
        "name": name,
        "result": str(result)[:200],
        "status": "completed",
    }
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _logging_error_hook(name: str, args: dict, error: Exception, session=None) -> None:
    """Log tool call error."""
    _ensure_log_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "tool_error",
        "name": name,
        "error": str(error)[:200],
        "status": "failed",
    }
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# Auto-register logging hooks on import
register_pre_hook(_logging_pre_hook)
register_post_hook(_logging_post_hook)
register_error_hook(_logging_error_hook)
