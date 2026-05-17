"""
FRIDAY Iron Man Features — Damage Report, Suit Check, Morning Plan, Evening Review.

Brings Stark-level awareness to the desktop:
- Damage Report: system health audit with risk scoring
- Suit Check: pre-flight verification of critical subsystems
- Morning Plan: proactive daily briefing with objectives
- Evening Review: end-of-day summary with reflection
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import json
import os
import platform

from friday._paths import FRIDAY_MEMORY

_REPORTS_DIR = os.path.join(FRIDAY_MEMORY, "ironman_reports")
_HISTORY_FILE = os.path.join(_REPORTS_DIR, "history.jsonl")


def _ensure_dirs():
    os.makedirs(_REPORTS_DIR, exist_ok=True)


def _log_report(report_type: str, summary: str, data: dict):
    """Log a report to the history file."""
    _ensure_dirs()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": report_type,
        "summary": summary[:200],
        "data": data,
    }
    try:
        with open(_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _get_system_health() -> dict:
    """Get current system health metrics."""
    health = {"cpu": {}, "memory": {}, "disk": {}, "issues": []}
    try:
        import psutil
        health["cpu"] = {
            "percent": psutil.cpu_percent(interval=0.5),
            "count": psutil.cpu_count(),
        }
        mem = psutil.virtual_memory()
        health["memory"] = {
            "percent": mem.percent,
            "available_gb": round(mem.available / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
        }
        disk = psutil.disk_usage("/")
        health["disk"] = {
            "percent": disk.percent,
            "free_gb": round(disk.free / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2),
        }
        if health["cpu"]["percent"] > 80:
            health["issues"].append(f"High CPU: {health['cpu']['percent']}%")
        if health["memory"]["percent"] > 80:
            health["issues"].append(f"High memory: {health['memory']['percent']}%")
        if health["disk"]["percent"] > 85:
            health["issues"].append(f"Low disk space: {health['disk']['percent']}%")
    except ImportError:
        health["cpu"]["percent"] = 0
        health["memory"]["percent"] = 0
        health["disk"]["percent"] = 0
        health["issues"].append("psutil not available")
    except Exception as e:
        health["issues"].append(str(e))
    return health


def _get_memory_report() -> dict:
    """Get memory system report."""
    report = {"profile_exists": False, "profile_size": 0, "review_count": 0, "conflicts": 0}
    try:
        from friday.memory_import import memory_import_tool
        result = memory_import_tool("doctor")
        if isinstance(result, str):
            report["doctor_summary"] = result[:300]
    except Exception:
        pass
    try:
        profile_file = os.path.join(FRIDAY_MEMORY, "user_profile.json")
        if os.path.exists(profile_file):
            with open(profile_file, "r") as f:
                profile = json.load(f)
            report["profile_exists"] = True
            report["profile_size"] = len(json.dumps(profile))
            report["review_count"] = len(profile.get("_review_queue", []))
    except Exception:
        pass
    return report


def _get_task_report() -> dict:
    """Get autonomy task report."""
    report = {"total": 0, "pending": 0, "failed": 0}
    try:
        from friday.autonomy import autonomy_tool
        status = autonomy_tool("status")
        if isinstance(status, str):
            for line in status.split("\n"):
                if "Total" in line:
                    try:
                        report["total"] = int(line.split(":")[-1].strip())
                    except Exception:
                        pass
                elif "Pending" in line:
                    try:
                        report["pending"] = int(line.split(":")[-1].strip())
                    except Exception:
                        pass
                elif "Failed" in line:
                    try:
                        report["failed"] = int(line.split(":")[-1].strip())
                    except Exception:
                        pass
    except Exception:
        pass
    return report


def _get_tool_usage_summary() -> str:
    """Get tool usage summary from logs."""
    try:
        log_file = os.path.join(FRIDAY_MEMORY, "tool_log.jsonl")
        if not os.path.exists(log_file):
            return "No tool logs available"
        tool_counts = {}
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "tool_call":
                        name = entry.get("name", "unknown")
                        tool_counts[name] = tool_counts.get(name, 0) + 1
                except Exception:
                    pass
        top = sorted(tool_counts.items(), key=lambda x: -x[1])[:10]
        if not top:
            return "No tool calls recorded"
        lines = [f"Top tools used ({sum(tool_counts.values())} total calls):"]
        for name, count in top:
            lines.append(f"  {name}: {count}")
        return "\n".join(lines)
    except Exception:
        return "Tool log unavailable"


# ─── Iron Man Features ──────────────────────────────────────


def damage_report() -> str:
    """Comprehensive system damage/health report.

    Scans: system health, memory integrity, task failures, tool errors.
    Returns a structured markdown report with risk scoring.
    """
    _ensure_dirs()
    health = _get_system_health()
    memory = _get_memory_report()
    tasks = _get_task_report()

    risk_score = 0
    findings = []

    # System checks
    cpu_pct = health.get("cpu", {}).get("percent", 0)
    mem_pct = health.get("memory", {}).get("percent", 0)
    disk_pct = health.get("disk", {}).get("percent", 0)

    if cpu_pct > 90:
        risk_score += 3
        findings.append("[CRITICAL] CPU usage > 90%")
    elif cpu_pct > 75:
        risk_score += 1
        findings.append("[WARN] CPU usage elevated")

    if mem_pct > 90:
        risk_score += 3
        findings.append("[CRITICAL] Memory usage > 90%")
    elif mem_pct > 75:
        risk_score += 1
        findings.append("[WARN] Memory usage elevated")

    if disk_pct > 95:
        risk_score += 3
        findings.append("[CRITICAL] Disk space < 5%")
    elif disk_pct > 85:
        risk_score += 1
        findings.append("[WARN] Disk space low")

    # Memory checks
    if not memory.get("profile_exists"):
        risk_score += 2
        findings.append("[WARN] No user profile found")
    if memory.get("review_count", 0) > 5:
        risk_score += 1
        findings.append(f"[INFO] {memory['review_count']} items awaiting memory review")
    if memory.get("conflicts", 0) > 0:
        risk_score += 2
        findings.append(f"[WARN] {memory['conflicts']} memory conflicts detected")

    # Task checks
    if tasks.get("failed", 0) > 3:
        risk_score += 2
        findings.append(f"[WARN] {tasks['failed']} failed tasks")
    if tasks.get("pending", 0) > 10:
        risk_score += 1
        findings.append(f"[INFO] {tasks['pending']} pending tasks")

    # Risk level
    if risk_score >= 5:
        risk_label = "HIGH"
    elif risk_score >= 2:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"

    lines = [
        "╔══════════════════════════════════════╗",
        "║        DAMAGE REPORT                 ║",
        "╚══════════════════════════════════════╝",
        "",
        f"Risk Score: {risk_score} — {risk_label}",
        f"Timestamp: {datetime.now().isoformat()[:19]}",
        "",
        "── System ──",
        f"  CPU:    {cpu_pct}%",
        f"  Memory: {mem_pct}%",
        f"  Disk:   {disk_pct}%",
        "",
        "── Memory Profile ──",
        f"  Exists:  {memory.get('profile_exists', False)}",
        f"  Size:    {memory.get('profile_size', 0)} bytes",
        f"  Reviews: {memory.get('review_count', 0)} pending",
        "",
        "── Task Queue ──",
        f"  Total:  {tasks.get('total', 0)}",
        f"  Failed: {tasks.get('failed', 0)}",
        f"  Pending: {tasks.get('pending', 0)}",
        "",
    ]

    if findings:
        lines.append("── Findings ──")
        lines.extend(f"  {f}" for f in findings)
        lines.append("")

    lines.append(f"Risk classification: {risk_label}")

    report = "\n".join(lines)
    _log_report("damage_report", f"Risk: {risk_score} — {risk_label}", {
        "risk_score": risk_score,
        "risk_label": risk_label,
        "cpu": cpu_pct,
        "memory": mem_pct,
        "disk": disk_pct,
        "findings_count": len(findings),
    })
    return report


def suit_check() -> str:
    """Pre-flight check of all critical FRIDAY subsystems.

    Verifies: module imports, memory profile, authority policy,
    tool registry, sidecars, dashboard, snapshots, capabilities.
    """
    checks = []
    passes = 0
    fails = 0

    def _check(name: str, ok: bool, detail: str = ""):
        nonlocal passes, fails
        if ok:
            passes += 1
            checks.append(f"  [OK] {name}")
        else:
            fails += 1
            checks.append(f"  [FAIL] {name} — {detail}")

    # Module imports
    modules = [
        "friday.memory_import", "friday.tool_registry", "friday.authority",
        "friday.snapshots", "friday.sidecar", "friday.autonomy",
        "friday.dashboard_api", "friday.capabilities", "friday.hooks",
        "friday.startup", "friday.profile_schema",
    ]
    for mod in modules:
        try:
            __import__(mod)
            _check(mod, True)
        except Exception as e:
            _check(mod, False, str(e)[:60])

    # Memory profile
    try:
        profile_file = os.path.join(FRIDAY_MEMORY, "user_profile.json")
        if os.path.exists(profile_file):
            from friday.profile_schema import validate_profile_file
            valid, errors = validate_profile_file(profile_file)
            _check("Memory profile", valid, "; ".join(errors[:2]))
        else:
            _check("Memory profile", False, "file not found")
    except Exception as e:
        _check("Memory profile", False, str(e)[:60])

    # Authority policy
    try:
        from friday.authority import load_authority_policy
        policy = load_authority_policy()
        _check("Authority policy", bool(policy.get("mode")))
    except Exception as e:
        _check("Authority policy", False, str(e)[:60])

    # Tool registry
    try:
        from friday.tool_registry import build_tool_registry
        registry = build_tool_registry()
        _check("Tool registry", len(registry) > 50, f"{len(registry)} tools")
    except Exception as e:
        _check("Tool registry", False, str(e)[:60])

    lines = [
        "╔══════════════════════════════════════╗",
        "║        SUIT CHECK                    ║",
        "╚══════════════════════════════════════╝",
        "",
        f"Timestamp: {datetime.now().isoformat()[:19]}",
        f"Platform: {platform.system()} {platform.release()}",
        "",
        f"Results: {passes} passed, {fails} failed",
        "",
    ]
    lines.extend(checks)
    lines.append("")
    lines.append(f"Status: {'ALL SYSTEMS NOMINAL' if fails == 0 else f'{fails} SYSTEM(S) NEED ATTENTION'}")

    report = "\n".join(lines)
    _log_report("suit_check", f"{passes}/{passes + fails} passed", {
        "passed": passes,
        "failed": fails,
        "total": passes + fails,
    })
    return report


def morning_plan() -> str:
    """Proactive morning briefing with today's objectives.

    Includes: system status, memory review summary, pending tasks,
    suggested priorities, and a greeting.
    """
    health = _get_system_health()
    memory = _get_memory_report()
    tasks = _get_task_report()
    tool_usage = _get_tool_usage_summary()

    # Determine greeting based on time of day
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    lines = [
        "╔══════════════════════════════════════╗",
        "║        MORNING BRIEFING              ║",
        "╚══════════════════════════════════════╝",
        "",
        f"{greeting}, Boss.",
        f"Today is {date.today().strftime('%A, %B %d, %Y')}.",
        f"System time: {datetime.now().isoformat()[:19]}",
        "",
        "── System Status ──",
        f"  CPU:    {health['cpu'].get('percent', '?')}%",
        f"  Memory: {health['memory'].get('percent', '?')}%",
        f"  Disk:   {health['disk'].get('percent', '?')}%",
        "",
        "── Memory Profile ──",
        f"  Profile: {'Loaded' if memory.get('profile_exists') else 'Not found'}",
        f"  Size: {memory.get('profile_size', 0)} bytes",
        f"  Pending review: {memory.get('review_count', 0)} items",
        "",
        "── Task Queue ──",
        f"  Total: {tasks.get('total', 0)} tasks",
        f"  Pending: {tasks.get('pending', 0)}",
        f"  Failed: {tasks.get('failed', 0)}",
        "",
        "── Recent Activity ──",
        tool_usage,
        "",
    ]

    # Suggestions
    suggestions = []
    if tasks.get("pending", 0) > 0:
        suggestions.append(f"  • Review and process {tasks['pending']} pending tasks")
    if memory.get("review_count", 0) > 0:
        suggestions.append(f"  • Approve or reject {memory['review_count']} pending memory items")
    if health.get("issues"):
        suggestions.append(f"  • Address system issues: {', '.join(health['issues'])}")

    if suggestions:
        lines.append("── Suggested Priorities ──")
        lines.extend(suggestions)
        lines.append("")

    report = "\n".join(lines)
    _log_report("morning_plan", f"Briefing for {date.today()}", {
        "cpu": health['cpu'].get('percent'),
        "memory": health['memory'].get('percent'),
        "disk": health['disk'].get('percent'),
        "pending_tasks": tasks.get('pending', 0),
        "review_items": memory.get('review_count', 0),
    })
    return report


def evening_review() -> str:
    """End-of-day review with accomplishments and reflection.

    Summarizes: tool usage, task completions, memory changes,
    system events, and suggestions for tomorrow.
    """
    health = _get_system_health()
    memory = _get_memory_report()
    tasks = _get_task_report()
    tool_usage = _get_tool_usage_summary()

    today_str = date.today().strftime('%A, %B %d, %Y')

    lines = [
        "╔══════════════════════════════════════╗",
        "║        EVENING REVIEW                ║",
        "╚══════════════════════════════════════╝",
        "",
        f"End of day review for {today_str}.",
        f"Timestamp: {datetime.now().isoformat()[:19]}",
        "",
        "── Daily Summary ──",
        f"  Total tasks processed: {tasks.get('total', 0)}",
        f"  Tasks completed: {tasks.get('total', 0) - tasks.get('pending', 0) - tasks.get('failed', 0)}",
        f"  Tasks failed: {tasks.get('failed', 0)}",
        f"  Tasks pending: {tasks.get('pending', 0)}",
        "",
        "── System End State ──",
        f"  CPU:    {health['cpu'].get('percent', '?')}%",
        f"  Memory: {health['memory'].get('percent', '?')}%",
        f"  Disk:   {health['disk'].get('percent', '?')}%",
        "",
        "── Memory Status ──",
        f"  Profile: {memory.get('profile_size', 0)} bytes",
        f"  Review queue: {memory.get('review_count', 0)} items",
        "",
        "── Activity Log ──",
        tool_usage,
        "",
    ]

    # Reflection
    reflections = []
    if tasks.get("failed", 0) > 0:
        reflections.append(f"  • {tasks['failed']} task(s) failed today — consider reviewing error logs")
    if memory.get("review_count", 0) > 0:
        reflections.append(f"  • {memory['review_count']} memory items need review")
    if health.get("issues"):
        reflections.append("  • System had health warnings — check damage report")

    if reflections:
        lines.append("── Reflection ──")
        lines.extend(reflections)
        lines.append("")

    lines.append("Recommendation: Run suit_check() in the morning to verify system readiness.")

    report = "\n".join(lines)
    _log_report("evening_review", f"Review for {today_str}", {
        "total_tasks": tasks.get('total', 0),
        "failed_tasks": tasks.get('failed', 0),
        "pending_tasks": tasks.get('pending', 0),
        "review_items": memory.get('review_count', 0),
    })
    return report


def ironman_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: Iron Man feature access.

    Actions:
        status        - Brief overview of all Iron Man systems
        damage_report - Full damage/health report with risk scoring
        suit_check    - Pre-flight verification of all subsystems
        morning_plan  - Daily proactive briefing
        evening_review- End-of-day review with reflection
    """
    if action == "damage_report":
        return damage_report()
    elif action == "suit_check":
        return suit_check()
    elif action == "morning_plan":
        return morning_plan()
    elif action == "evening_review":
        return evening_review()
    elif action == "status":
        lines = [
            "### IRON MAN SYSTEMS",
            "",
            "Available features:",
            "  damage_report  - Comprehensive system health audit with risk scoring",
            "  suit_check     - Pre-flight verification of critical subsystems",
            "  morning_plan   - Proactive daily briefing with objectives",
            "  evening_review - End-of-day summary with reflection",
            "",
            f"Reports directory: {_REPORTS_DIR}",
            f"History: {_HISTORY_FILE}",
        ]
        return "\n".join(lines)
    return f"[FAIL] Unknown action: {action}. Available: status, damage_report, suit_check, morning_plan, evening_review"
