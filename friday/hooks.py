"""
Friday Hooks System — pre/post execution hooks for tool calls.
Enables logging, notifications, validation, and event-driven reactions.
"""

import os
import json
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from friday._paths import FRIDAY_MEMORY

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

_LOG_PATH = os.path.join(FRIDAY_MEMORY, "tool_log.jsonl")
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


# ─── Knowledge Graph Auto-Extraction Hook (jarvis parity) ───

def _kg_extraction_post_hook(name: str, args: dict, result: str, session=None) -> None:
    """Auto-extract entities and facts from tool results into the knowledge graph."""
    if not result or not isinstance(result, str):
        return
    if len(result) < 20 or len(result) > 2000:
        return
    try:
        from friday.knowledge_graph import add_triple, kg_exists
        if not kg_exists():
            return
        # Extract simple patterns: "X is Y", "X has Y", "X: Y"
        import re
        lines = result.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # "[OK] Verb: Detail" → entity, relation, value
            m = re.match(r'^\[?(OK|FAIL|WARN|INFO)\]?\s+(.+?):\s+(.+)$', line)
            if m:
                add_triple("Friday", m.group(2).strip().lower(), m.group(3).strip()[:100])
            # "Title: Value" patterns
            m2 = re.match(r'^(.+?):\s+(.+)$', line)
            if m2:
                key = m2.group(1).strip().lower()
                val = m2.group(2).strip()[:100]
                if len(key) > 3 and len(key) < 50:
                    add_triple("Context", key, val)
    except Exception:
        pass


def _kg_tool_name_filter(name: str) -> bool:
    """Only extract from informative tools, not desktop noise."""
    noisy = {"click", "move_mouse", "scroll", "press_key", "hotkey", "type_text",
             "opencli_scroll", "opencli_keys", "opencli_screenshot"}
    return name not in noisy


_kg_active_post_hook = lambda n, a, r, s: _kg_extraction_post_hook(n, a, r, s) if _kg_tool_name_filter(n) else None

# Register KG hook
register_post_hook(_kg_active_post_hook)


# Auto-register logging hooks on import
register_pre_hook(_logging_pre_hook)
register_post_hook(_logging_post_hook)
register_error_hook(_logging_error_hook)


# ─── Know Your User Post-Hook ────────────────────────────────────────────────

def _kyu_post_hook(name: str, args: dict, result: str, session=None) -> None:
    """Feed tool usage into KYU learning system."""
    if not name or name == "kyu_tool_handler":
        return
    try:
        from friday.kyu import kyu_learn
        kyu_learn(tool_name=name, active_window=None, hour=None)
    except Exception:
        pass

register_post_hook(_kyu_post_hook)
