"""
FRIDAY System Dashboard — CLI output style (like Claude Code / opencode CLI).
No flicker, no in-place refresh — clean scrolling terminal output.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.tool_registry import list_tool_registry
from friday.validation_middleware import validation_tool
from friday.townhall_agents import townhall_tool

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _system_stats() -> dict:
    stats = {}
    if HAS_PSUTIL:
        stats["cpu"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        stats["memory"] = mem.percent
        disk = psutil.disk_usage("/")
        stats["disk"] = disk.percent
        stats["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
    return stats


def _pct(val: float, warn: float = 70, bad: float = 90) -> str:
    if val >= bad:
        return f"{val:.0f}% HIGH"
    if val >= warn:
        return f"{val:.0f}%"
    return f"{val:.0f}%"


def _sep(title: str = "") -> str:
    line = "-" * 48
    if title:
        return f"\n-- {title} {line[len(title)+5:]}"
    return line


def build_text_report() -> str:
    """Build a clean text report of all system status."""
    lines = []
    lines.append("FRIDAY System Status")
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # System Health
    lines.append(_sep("System Health"))
    stats = _system_stats()
    if stats:
        lines.append(f"  CPU     {_pct(stats.get('cpu', 0))}")
        lines.append(f"  Memory  {_pct(stats.get('memory', 0))}")
        lines.append(f"  Disk    {_pct(stats.get('disk', 0), warn=80, bad=90)}")
        lines.append(f"  Boot    {stats.get('boot_time', '?')[:19]}")

    # Agents & Town Hall
    lines.append(_sep("Agents & Town Hall"))
    try:
        from friday.townhall_agents import AGENT_ROLES
        lines.append(f"  o {len(AGENT_ROLES)} agents available")
    except Exception:
        lines.append("  - agents unavailable")

    try:
        sessions_info = json.loads(townhall_tool("status"))
        active = sessions_info.get("active_sessions", 0)
        total = sessions_info.get("total_sessions", 0)
        msgs = sessions_info.get("total_messages", 0)
        dot = "o" if active else "-"
        lines.append(f"  {dot} {active} active / {total} total sessions")
        lines.append(f"    {msgs} messages logged")
    except Exception:
        lines.append("  - town hall unavailable")

    # Tool Registry
    lines.append(_sep("Tool Registry"))
    try:
        grouped = list_tool_registry()
        total_tools = sum(len(v) for v in grouped.values())
        lines.append(f"  o {total_tools} tools registered")
        for cat, tools in sorted(grouped.items()):
            lines.append(f"    {cat}: {len(tools)}")
    except Exception:
        lines.append("  - registry unavailable")

    # Daemons & Persistence
    lines.append(_sep("Daemons & Persistence"))
    daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
    if os.path.exists(daemon_flag):
        with open(daemon_flag) as f:
            daemon_pid = f.read().strip()
        lines.append(f"  o self-improve daemon (PID {daemon_pid})")
    else:
        lines.append(f"  - self-improve daemon")

    checkpoint_dir = os.path.join(FRIDAY_MEMORY, "checkpoints")
    if os.path.isdir(checkpoint_dir):
        checkpoints = [f for f in os.listdir(checkpoint_dir) if f.endswith(".json")]
        latest = max(checkpoints).replace(".json", "")[:16] if checkpoints else "none"
        lines.append(f"    {len(checkpoints)} checkpoints (latest: {latest})")
    else:
        lines.append("    0 checkpoints")

    # Memory
    memory_file = os.path.join(FRIDAY_MEMORY, "memory_graph.json")
    if os.path.exists(memory_file):
        size_kb = os.path.getsize(memory_file) / 1024
        lines.append(f"    memory graph: {size_kb:.0f} KB")

    # Validation Middleware
    lines.append(_sep("Validation Middleware"))
    try:
        vs = json.loads(validation_tool("stats"))
        lines.append(f"  o active -- {vs.get('total_calls', 0)} calls tracked")
    except Exception:
        lines.append(f"  - not active")

    # Services
    lines.append(_sep("Services"))
    try:
        import interpreter
        lines.append(f"  Open Interpreter {interpreter.__version__}")
    except (ImportError, AttributeError):
        lines.append(f"  - Open Interpreter not found")

    try:
        import fastapi
        lines.append(f"  Dashboard API    fastapi {fastapi.__version__}")
    except (ImportError, AttributeError):
        lines.append(f"  - Dashboard API not available")

    mcp_dir = os.path.join(FRIDAY_MEMORY, "mcp")
    if os.path.isdir(mcp_dir):
        servers = [d for d in os.listdir(mcp_dir) if os.path.isdir(os.path.join(mcp_dir, d))]
        lines.append(f"  MCP servers      {len(servers)} configured")

    lines.append(_sep())
    return "\n".join(lines)


def dashboard_cli_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Dashboard -- CLI output style, no flicker.
    
    Actions:
      status  - Print full text report to stdout
      watch   - Print status every N seconds (scrolling)
      json    - Return JSON summary
    """
    if action == "status":
        print(build_text_report(), flush=True)
        return "Done."

    elif action == "watch":
        interval = float(kwargs.get("interval", 5))
        try:
            while True:
                print(f"\n-- {datetime.now().strftime('%H:%M:%S')} --")
                print(build_text_report())
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
            return "Stopped."

    elif action == "json":
        stats = _system_stats()
        result = {"system": stats, "timestamp": datetime.now().isoformat()}
        try:
            sessions_info = json.loads(townhall_tool("status"))
            result["town_hall"] = sessions_info
        except Exception:
            result["town_hall"] = {"error": "unavailable"}
        try:
            grouped = list_tool_registry()
            total = sum(len(v) for v in grouped.values())
            result["tool_registry"] = {"total": total, "categories": {k: len(v) for k, v in grouped.items()}}
        except Exception:
            result["tool_registry"] = {"error": "unavailable"}
        try:
            vs = json.loads(validation_tool("stats"))
            result["validation"] = vs
        except Exception:
            result["validation"] = {"error": "unavailable"}
        daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
        result["daemon"] = {"running": os.path.exists(daemon_flag)}
        return json.dumps(result, indent=2)

    return f"Unknown action: {action}. Use: status, watch, json"


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    kwargs = {}
    if len(sys.argv) > 2:
        kwargs["interval"] = sys.argv[2]
    print(dashboard_cli_tool(action, **kwargs))
