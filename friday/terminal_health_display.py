"""
FRIDAY Terminal Health Display — builds an ASCII health dashboard that can be
printed to the terminal, shown in the agent's context, or broadcast to the UI.

This is the visual front-end of the health_monitor system. It reads health
snapshots and renders them as a clean, color-coded ASCII table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def _colorize(text: str, status: str) -> str:
    """Apply ANSI color based on status."""
    colors = {
        "ok": "\033[92m",       # green
        "healthy": "\033[92m",
        "degraded": "\033[93m",  # yellow
        "warning": "\033[93m",
        "error": "\033[91m",     # red
        "fail": "\033[91m",
        "critical": "\033[91m\033[5m",  # red blinking
        "stopped": "\033[90m",   # grey
        "starting": "\033[94m",  # blue
        "unknown": "\033[90m",   # grey
        "info": "\033[94m",      # blue
    }
    color = colors.get(status.lower(), "\033[0m")
    return f"{color}{text}\033[0m"


def _status_icon(status: str) -> str:
    icons = {
        "ok": "\u2714",         # ✔
        "healthy": "\u2714",
        "degraded": "\u26A0",   # ⚠
        "warning": "\u26A0",
        "error": "\u2718",      # ✘
        "fail": "\u2718",
        "critical": "\u26A1",   # ⚡
        "stopped": "\u25CB",    # ○
        "starting": "\u25D4",   # ◔
        "unknown": "?",
    }
    return icons.get(status.lower(), "?")


def build_health_dashboard(snapshot: Optional[dict] = None) -> str:
    """Build a full ASCII health dashboard string.
    
    Args:
        snapshot: A health_monitor.snapshot() dict. If None, attempts to load
                  from the singleton HealthMonitor.
    
    Returns:
        str: The formatted dashboard.
    """
    if snapshot is None:
        try:
            from friday.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snapshot = hm.snapshot()
        except Exception:
            snapshot = {"overall": "unknown", "components": {}, "alerts": [], "uptime_human": "0s"}

    ts = snapshot.get("timestamp", datetime.now().isoformat())[:19]
    overall = snapshot.get("overall", "unknown")
    uptime = snapshot.get("uptime_human", "?")
    components = snapshot.get("components", {})
    alerts = snapshot.get("alerts", [])

    lines = []
    lines.append("")
    lines.append(_colorize("=" * 60, "info"))
    lines.append(_colorize("  FRIDAY SYSTEM HEALTH", "info"))
    lines.append(_colorize(f"  {ts}  |  Uptime: {uptime}", "info"))
    lines.append(_colorize(f"  Overall Status: ", "info") + _colorize(overall.upper(), overall))
    lines.append(_colorize("-" * 60, "info"))

    if components:
        lines.append(_colorize(f"  {'COMPONENT':<25} {'STATUS':<12} DETAIL", "info"))
        lines.append(_colorize("  " + "-" * 55, "info"))
        for name, status in sorted(components.items()):
            st = status.get("status", "unknown")
            detail = status.get("detail", "")[:45]
            icon = _status_icon(st)
            line = f"  {icon} {name:<22} {_colorize(st.upper(), st):<12} {detail}"
            lines.append(line)

    if alerts:
        lines.append(_colorize("-" * 60, "info"))
        lines.append(_colorize(f"  ALERTS ({len(alerts)} recent)", "warning"))
        for a in alerts[-5:]:
            ts_a = a.get("time", "")[11:19] if len(a.get("time", "")) > 19 else a.get("time", "?")
            sev = a.get("severity", "info")
            src = a.get("source", "?")
            msg = a.get("message", "")
            lines.append(f"  [{ts_a}] {_colorize(f'[{sev.upper()}]', sev)} {src}: {msg}")
            if a.get("detail"):
                lines.append(f"          {a['detail']}")

    lines.append(_colorize("=" * 60, "info"))
    lines.append("")
    return "\n".join(lines)


def compact_status_line(snapshot: Optional[dict] = None) -> str:
    """One-liner status for embedding in terminal prompt or log."""
    if snapshot is None:
        try:
            from friday.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snapshot = hm.snapshot()
        except Exception:
            return "[FRIDAY] health: unknown"

    overall = snapshot.get("overall", "?")
    comp_count = snapshot.get("monitored_count", 0)
    uptime = snapshot.get("uptime_human", "?")
    alert_count = len(snapshot.get("alerts", []))
    icon = _status_icon(overall)
    return f"[FRIDAY] {icon} health:{overall} components:{comp_count} uptime:{uptime} alerts:{alert_count}"


def print_dashboard(snapshot: Optional[dict] = None):
    """Print the health dashboard to stdout."""
    print(build_health_dashboard(snapshot))
