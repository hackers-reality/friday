"""Friday GEPA Self-Reflection Loop — deep analysis of tool outcomes.
Inspired by Hermes Agent's GEPA (Gather, Evaluate, Plan, Act) cycle.
Analyzes tool execution logs to identify failure patterns, success strategies,
and self-improvement opportunities."""

from __future__ import annotations
import os
import json
from datetime import datetime
from collections import defaultdict
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_LOG_PATH = os.path.join(FRIDAY_MEMORY, "tool_log.jsonl")
_REFLECTION_FILE = os.path.join(FRIDAY_MEMORY, "reflection_state.json")


def _load_state() -> dict:
    if os.path.exists(_REFLECTION_FILE):
        try:
            with open(_REFLECTION_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_reflections": 0,
        "last_reflection": None,
        "failure_patterns": [],
        "improvements_applied": [],
        "success_patterns": [],
    }


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_REFLECTION_FILE), exist_ok=True)
    try:
        with open(_REFLECTION_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _load_logs(max_entries: int = 500) -> list:
    if not os.path.exists(_LOG_PATH):
        return []
    entries = []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return entries[-max_entries:]


def _reconstruct_sequences(entries: list) -> list:
    sequences = []
    current_seq = []
    for entry in entries:
        etype = entry.get("type", "")
        if etype == "tool_call":
            current_seq = [entry]
        elif etype in ("tool_result", "tool_error") and current_seq:
            current_seq.append(entry)
            sequences.append(current_seq)
            current_seq = []
    return sequences


def _analyze_success_rate(sequences: list) -> dict:
    tool_stats = defaultdict(lambda: {"success": 0, "fail": 0, "total": 0, "errors": [], "avg_result_len": 0})
    for seq in sequences:
        if len(seq) < 2:
            continue
        call = seq[0]
        result = seq[1]
        tool_name = call.get("name", "unknown")
        tool_stats[tool_name]["total"] += 1
        status = result.get("status", "")
        result_text = result.get("result", result.get("error", ""))
        if status == "completed" and not result_text.startswith("[FAIL]"):
            tool_stats[tool_name]["success"] += 1
        elif status == "failed" or result_text.startswith("[FAIL]"):
            tool_stats[tool_name]["fail"] += 1
            tool_stats[tool_name]["errors"].append(result_text[:150])
    return dict(tool_stats)

def _identify_failure_patterns(tool_stats: dict) -> list:
    patterns = []
    for tool, stats in tool_stats.items():
        total = stats["total"]
        if total == 0:
            continue
        fail_rate = stats["fail"] / total
        if total >= 3 and fail_rate >= 0.3:
            common_errors = {}
            for err in stats["errors"][:15]:
                key = err.split(":")[0].split("(")[0].strip()[:50]
                if key:
                    common_errors[key] = common_errors.get(key, 0) + 1
            top_errors = sorted(common_errors.items(), key=lambda x: -x[1])[:3]
            patterns.append({
                "tool": tool,
                "fail_rate": round(fail_rate, 2),
                "total_calls": total,
                "fail_count": stats["fail"],
                "common_errors": [e for e, c in top_errors],
                "identified": datetime.now().isoformat(),
            })
    return patterns


def _generate_improvement_strategies(patterns: list) -> list:
    strategies = []
    for p in patterns:
        tool = p["tool"]
        suggestion = None
        if tool == "web_search":
            suggestion = "Use more specific queries or get_page_content for known URLs. Try different search engines."
        elif tool == "open_app":
            suggestion = "Use 'start' command fallback. Check if app is installed via 'where' command first."
        elif tool == "search_browser_history":
            suggestion = "Use shorter queries or fewer days_back. The SQLite database may be large."
        elif tool.startswith("github"):
            suggestion = "Check token validity via github_authorize(). Verify repo exists and permissions are correct."
        elif "opencli" in tool:
            suggestion = "Ensure OpenCLI session is active. Run opencli_list_sessions to verify active sessions."
        elif tool == "get_page_content":
            suggestion = "Try with requests library directly. The URL may require specific headers or cookies."
        elif tool == "send_email":
            suggestion = "Verify Gmail token is valid. Run google_authorize() if needed."
        elif tool == "spotify_play":
            suggestion = "Try exact track name. Spotify search can be picky with special characters."
        else:
            suggestion = f"Review {tool} arguments and error context. Consider retrying with different parameters."
        strategies.append({
            "tool": tool,
            "fail_rate": p["fail_rate"],
            "errors": p["common_errors"],
            "suggestion": suggestion,
            "applied": False,
        })
    return strategies


def _run_reflection_cycle() -> str:
    state = _load_state()
    entries = _load_logs(500)
    if not entries:
        return "[INFO] No tool logs to analyze yet."

    sequences = _reconstruct_sequences(entries)
    if not sequences:
        return "[INFO] No complete tool sequences found."

    tool_stats = _analyze_success_rate(sequences)

    failure_patterns = _identify_failure_patterns(tool_stats)
    strategies = _generate_improvement_strategies(failure_patterns)

    improvements_applied = []
    for strategy in strategies:
        try:
            from friday.skills import skills_tool
            result = skills_tool(
                "auto_create",
                name=f"Fix: {strategy['tool']} - {strategy['suggestion'][:40]}",
                steps=strategy['suggestion'],
                trigger=strategy['tool'],
                tags=f"auto, reflection, fix, {strategy['tool']}",
            )
            if result.startswith("[OK]"):
                strategy["applied"] = True
                improvements_applied.append(strategy["tool"])
        except Exception:
            pass

    state["total_reflections"] += 1
    state["last_reflection"] = datetime.now().isoformat()
    if failure_patterns:
        state["failure_patterns"] = failure_patterns
    state["improvements_applied"].extend(improvements_applied)
    state["improvements_applied"] = state["improvements_applied"][-50:]

    success_patterns = []
    for tool, stats in tool_stats.items():
        if stats["total"] >= 5 and stats["success"] / stats["total"] >= 0.8:
            success_patterns.append({
                "tool": tool,
                "success_rate": round(stats["success"] / stats["total"], 2),
                "total_calls": stats["total"],
            })
    if success_patterns:
        state["success_patterns"] = success_patterns[-20:]
    _save_state(state)

    lines = [f"### Reflection Cycle #{state['total_reflections']}"]
    if failure_patterns:
        lines.append(f"Found {len(failure_patterns)} failure patterns:")
        for fp in failure_patterns:
            lines.append(f"  - {fp['tool']}: {fp['fail_count']}/{fp['total_calls']} fails ({fp['fail_rate']:.0%})")
    if improvements_applied:
        lines.append(f"Applied {len(improvements_applied)} improvement strategies as skills.")
    if success_patterns:
        lines.append(f"Identified {len(success_patterns)} reliable tools with >80% success.")
    if not failure_patterns and not improvements_applied:
        lines.append("No significant issues found. Everything looks healthy.")
    return "\n".join(lines)


def reflection_tool(action: str = "status", **kwargs) -> str:
    """GEPA self-reflection: analyze tool outcomes, find failure patterns,
    and auto-improve. Actions: cycle, analyze, improvements, status."""
    if action == "cycle":
        return _run_reflection_cycle()
    elif action == "analyze":
        state = _load_state()
        patterns = state.get("failure_patterns", [])
        if not patterns:
            return "No failure patterns found. System is running cleanly."
        lines = ["### FAILURE PATTERNS"]
        for p in patterns:
            lines.append(
                f"  - {p['tool']}: {p['fail_rate']:.0%} fail rate ({p['fail_count']}/{p['total_calls']})\n"
                f"    Common errors: {', '.join(p['common_errors'][:3])}"
            )
        return "\n".join(lines)
    elif action == "improvements":
        state = _load_state()
        applied = state.get("improvements_applied", [])
        if not applied:
            return "No improvements applied yet."
        lines = ["### IMPROVEMENTS APPLIED"]
        for imp in applied[-20:]:
            lines.append(f"  - {imp}")
        return "\n".join(lines)
    elif action == "status":
        state = _load_state()
        reflections = state.get("total_reflections", 0)
        last = state.get("last_reflection", "never")
        patterns = len(state.get("failure_patterns", []))
        improvements = len(state.get("improvements_applied", []))
        success = len(state.get("success_patterns", []))
        return (
            f"GEPA Self-Reflection System:\n"
            f"  Cycles completed: {reflections}\n"
            f"  Last reflection: {last}\n"
            f"  Active failure patterns: {patterns}\n"
            f"  Improvements applied: {improvements}\n"
            f"  Reliable tools identified: {success}"
        )
    else:
        return f"[FAIL] Unknown action: {action}"


def start_reflection_on_boot():
    """Run an initial reflection cycle on boot."""
    try:
        _run_reflection_cycle()
    except Exception:
        pass
