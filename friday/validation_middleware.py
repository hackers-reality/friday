"""
Validation Middleware — auto-verifies every tool call & result.
FRIDAY self-verification "checks its own work" loop.
Intercepts tool execution, runs verification, logs confidence.

Architecture:
  validate_call(tool_name, args, result) -> dict
    Auto-detects tool type and runs appropriate verification:
    - code tools: verify_code()
    - file tools: verify file exists, size, content
    - vision tools: verify image exists, valid format
    - search tools: verify results have expected structure
    - generic: verify no error, non-empty result
    
  get_validation_history() -> str
    Returns recent validation history for LLM context
"""
from __future__ import annotations

import json
import os
import re
import time
import traceback
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("validation_middleware")

_VALIDATION_LOG = os.path.join(FRIDAY_MEMORY, "validation_history.jsonl")
_STATS_FILE = os.path.join(FRIDAY_MEMORY, "validation_stats.json")
_RECENT_CACHE: list[dict] = []
_MAX_CACHE = 200


def _log_validation(entry: dict):
    global _RECENT_CACHE
    entry["timestamp"] = datetime.now().isoformat()
    _RECENT_CACHE.append(entry)
    if len(_RECENT_CACHE) > _MAX_CACHE:
        _RECENT_CACHE = _RECENT_CACHE[-_MAX_CACHE:]
    os.makedirs(os.path.dirname(_VALIDATION_LOG), exist_ok=True)
    with open(_VALIDATION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _update_stats(entry)


def _update_stats(entry: dict):
    stats = {}
    if os.path.exists(_STATS_FILE):
        try:
            with open(_STATS_FILE) as f:
                stats = json.load(f)
        except Exception:
            pass
    tool = entry.get("tool", "unknown")
    valid = entry.get("valid", False)
    if tool not in stats:
        stats[tool] = {"total": 0, "passed": 0, "failed": 0}
    stats[tool]["total"] += 1
    if valid:
        stats[tool]["passed"] += 1
    else:
        stats[tool]["failed"] += 1
    with open(_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    stats["_last_updated"] = datetime.now().isoformat()


def _classify_tool(name: str) -> str:
    name_lower = name.lower()
    if any(x in name_lower for x in ("code", "lint", "format", "parse", "type_check", "review", "fix")):
        return "code"
    if any(x in name_lower for x in ("file", "read", "write", "create", "save", "copy", "move", "delete")):
        return "file"
    if any(x in name_lower for x in ("image", "vision", "screenshot", "ocr", "face", "pose", "detect")):
        return "vision"
    if any(x in name_lower for x in ("search", "find", "lookup", "query", "whois", "shodan", "dns")):
        return "search"
    if any(x in name_lower for x in ("upload", "download", "http", "fetch", "request", "api")):
        return "network"
    if any(x in name_lower for x in ("run", "exec", "cmd", "shell", "command")):
        return "execution"
    return "generic"


def _verify_code_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    # Check for Python syntax errors in result
    if "SyntaxError" in result_str or "IndentationError" in result_str:
        issues.append("Result contains syntax errors")

    # Check for common failure patterns
    if "Traceback" in result_str or "traceback" in result_str:
        issues.append("Result contains traceback/exception")

    # Check if result is empty
    if not result_str.strip() or result_str.strip() in ("{}", "[]", "None", "''", '""'):
        issues.append("Empty result")

    # Extract code blocks and try to validate
    code_blocks = re.findall(r"```(\w*)\n(.*?)```", result_str, re.DOTALL)
    for lang, code in code_blocks:
        if lang in ("python", "py", ""):
            try:
                compile(code.strip(), "<verify>", "exec")
            except SyntaxError as e:
                issues.append(f"Generated code has syntax error: {e}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.3),
    }


def _verify_file_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    paths = re.findall(r'["\']([^"\']+\.\w+)["\']', result_str)
    if not paths:
        paths = re.findall(r'[A-Z]:(?:\\[^\\\s]+)+\.\w+', result_str, re.IGNORECASE)

    verified_paths = 0
    for p in paths[:5]:
        if os.path.exists(p):
            verified_paths += 1
            if os.path.getsize(p) == 0:
                issues.append(f"File is empty: {p}")
        else:
            issues.append(f"Referenced path does not exist: {p}")

    if "error" in result_str.lower() or "fail" in result_str.lower():
        issues.append("Result mentions error/failure")
    if not result_str.strip():
        issues.append("Empty result")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.25) if not issues else 0.5,
    }


def _verify_vision_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    paths = re.findall(r'["\']([^"\']+\.(png|jpg|jpeg|gif|bmp))["\']', result_str, re.IGNORECASE)
    for p, _ in paths:
        if os.path.exists(p):
            if os.path.getsize(p) == 0:
                issues.append(f"Image file is empty: {p}")
        else:
            issues.append(f"Image path not found: {p}")

    if "detections" in result_str and '"detections": []' in result_str:
        issues.append("Object detection returned zero results")
    if "faces" in result_str and '"faces": 0' in result_str:
        issues.append("Face detection returned zero results")
    if "error" in result_str.lower():
        issues.append("Result contains error")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.2) if not issues else 0.5,
    }


def _verify_search_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    try:
        parsed = json.loads(result_str) if isinstance(result_str, str) and result_str.startswith(("{", "[")) else {}
        if isinstance(parsed, dict):
            if parsed.get("error"):
                issues.append(f"API error: {parsed['error']}")
            if parsed.get("results") == [] or parsed.get("items") == []:
                issues.append("Empty results array")
            if parsed.get("count") == 0:
                issues.append("Zero results returned")
    except Exception:
        pass

    if "error" in result_str.lower():
        issues.append("Result contains error")
    if "timed out" in result_str.lower():
        issues.append("Request timed out")
    if "not found" in result_str.lower():
        issues.append("Not found")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.33),
    }


def _verify_network_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    if any(x in result_str.lower() for x in ("connection refused", "connection reset", "timeout", "dns lookup failed")):
        issues.append("Network error in result")
    if "error" in result_str.lower():
        issues.append("Result contains error")
    if "403" in result_str or "401" in result_str or "404" in result_str:
        issues.append(f"HTTP error in result")
    if not result_str.strip():
        issues.append("Empty result")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.25),
    }


def _verify_execution_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    if "returncode" in result_str:
        try:
            parsed = json.loads(result_str) if isinstance(result_str, str) else result
            if isinstance(parsed, dict) and parsed.get("returncode", 0) != 0:
                issues.append(f"Non-zero return code: {parsed.get('returncode')}")
        except Exception:
            pass

    if "Traceback" in result_str or "Error:" in result_str:
        issues.append("Execution produced error/traceback")
    if not result_str.strip():
        issues.append("Empty result")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": max(0, 1.0 - len(issues) * 0.3),
    }


def _verify_generic_result(tool: str, result: Any, args: dict) -> dict:
    result_str = str(result)
    issues = []

    if not result_str or (isinstance(result_str, str) and not result_str.strip()):
        issues.append("Empty result")
    elif isinstance(result_str, str) and result_str.strip() in ("{}", "[]", "None", "null"):
        issues.append("Null/empty result")

    if isinstance(result_str, str) and "error" in result_str.lower() and "success" not in result_str.lower():
        issues.append("Result indicates error without success")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "confidence": 0.8 if not issues else 0.3,
    }


_VERIFIERS = {
    "code": _verify_code_result,
    "file": _verify_file_result,
    "vision": _verify_vision_result,
    "search": _verify_search_result,
    "network": _verify_network_result,
    "execution": _verify_execution_result,
    "generic": _verify_generic_result,
}


def validate_call(tool_name: str, args: dict, result: Any, duration_ms: float = 0) -> dict:
    """Validate a tool call result. Returns validation verdict."""
    category = _classify_tool(tool_name)
    verifier = _VERIFIERS.get(category, _verify_generic_result)
    verdict = verifier(tool_name, result, args)

    entry = {
        "tool": tool_name,
        "category": category,
        "args_snapshot": {k: str(v)[:100] for k, v in args.items()},
        "result_preview": str(result)[:200],
        "duration_ms": round(duration_ms, 1),
        "valid": verdict["valid"],
        "issues": verdict["issues"],
        "confidence": round(verdict["confidence"], 2),
    }

    _log_validation(entry)

    if not verdict["valid"]:
        logger.warning("Validation FAILED for %s: %s", tool_name, "; ".join(verdict["issues"]))

    return verdict


def get_validation_stats() -> str:
    if not os.path.exists(_STATS_FILE):
        return "No validation data yet."
    with open(_STATS_FILE) as f:
        stats = json.load(f)
    total = sum(v["total"] for k, v in stats.items() if not k.startswith("_"))
    passed = sum(v["passed"] for k, v in stats.items() if not k.startswith("_"))
    failed = sum(v["failed"] for k, v in stats.items() if not k.startswith("_"))
    rate = (passed / total * 100) if total > 0 else 0

    lines = [
        f"### Validation Stats",
        f"Total calls: {total}",
        f"Passed: {passed} ({rate:.0f}%)",
        f"Failed: {failed}",
    ]
    failing_tools = sorted(
        [(k, v) for k, v in stats.items() if not k.startswith("_") and v["failed"] > 0],
        key=lambda x: -x[1]["failed"],
    )
    if failing_tools:
        lines.append("\nFailing tools:")
        for tool, stat in failing_tools[:10]:
            lines.append(f"  {tool}: {stat['passed']}/{stat['total']} passed ({stat['failed']} failures)")
    return "\n".join(lines)


def auto_verify(tool_name: str, args: dict, result: Any) -> str:
    """Run validation and return a formatted string for LLM context."""
    verdict = validate_call(tool_name, args, result)
    if verdict["valid"]:
        return ""
    issues = "; ".join(verdict["issues"])
    return f"\n[Auto-Validation] {tool_name} result may need review: {issues}"


def validation_tool(action: str = "stats", **kwargs) -> str:
    """Validation Middleware — auto-verifies every tool call result.
    
    Actions:
      stats - Show validation statistics
      history [limit] - Show recent validation history
      check - Run a single validation (tool, args JSON, result)
    """
    if action == "stats":
        return get_validation_stats()

    elif action == "history":
        limit = int(kwargs.get("limit", 20))
        if not os.path.exists(_VALIDATION_LOG):
            return "No validation history yet."
        entries = []
        with open(_VALIDATION_LOG) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
        if not entries:
            return "No entries."

        lines = [f"### Validation History (last {min(limit, len(entries))})"]
        for e in entries[-limit:]:
            ts = e.get("timestamp", "?")[11:19]
            tool = e.get("tool", "?")
            valid = "✓" if e.get("valid") else "✗"
            conf = e.get("confidence", 0)
            issues = "; ".join(e.get("issues", []))[:60]
            lines.append(f"  {valid} [{ts}] {tool} (conf={conf:.2f}) {issues}")
        return "\n".join(lines)

    elif action == "check":
        tool = kwargs.get("tool", "")
        args_str = kwargs.get("args", "{}")
        result_str = kwargs.get("result", "")
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except Exception:
            args = {}
        verdict = validate_call(tool, args, result_str)
        return json.dumps(verdict, indent=2)

    return f"[FAIL] Unknown action: {action}"
