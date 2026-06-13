"""
FRIDAY System Dashboard -- CLI output style (like Claude Code / opencode CLI).
Expanded version with detailed reports, history, alerts, export, search,
timeline, agent panels, interactive mode, service probes, error viewer,
memory graph viewer, and configuration viewer.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from friday._paths import FRIDAY_MEMORY, FRIDAY_CONFIG, PROJECT_ROOT, STARK_LOGS
from friday.tool_registry import list_tool_registry, check_tool_registry_consistency, TOOL_META
from friday.validation_middleware import validation_tool
from friday.townhall_agents import townhall_tool, AGENT_ROLES

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


HISTORY_FILE = os.path.join(FRIDAY_MEMORY, "dashboard_history.jsonl")
ALERTS_FILE = os.path.join(FRIDAY_MEMORY, "dashboard_alerts.json")
_dashboard_lock = Lock()


def _system_stats() -> dict:
    """Gather current system stats using psutil where available."""
    stats = {}
    if HAS_PSUTIL:
        stats["cpu"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        stats["memory"] = mem.percent
        stats["memory_used_gb"] = round(mem.used / (1024 ** 3), 2)
        stats["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
        stats["memory_available_gb"] = round(mem.available / (1024 ** 3), 2)
        disk = psutil.disk_usage("/")
        stats["disk"] = disk.percent
        stats["disk_used_gb"] = round(disk.used / (1024 ** 3), 2)
        stats["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)
        stats["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
        stats["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        try:
            net = psutil.net_io_counters()
            stats["net_sent_mb"] = round(net.bytes_sent / (1024 ** 2), 2)
            stats["net_recv_mb"] = round(net.bytes_recv / (1024 ** 2), 2)
        except Exception:
            pass
        try:
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            stats["cpu_count"] = cpu_count
            if cpu_freq:
                stats["cpu_freq_mhz"] = round(cpu_freq.current, 1)
        except Exception:
            pass
        try:
            load_avg = psutil.getloadavg()
            stats["load_1min"] = round(load_avg[0], 2)
            stats["load_5min"] = round(load_avg[1], 2)
            stats["load_15min"] = round(load_avg[2], 2)
        except Exception:
            pass
        try:
            swap = psutil.swap_memory()
            stats["swap_percent"] = swap.percent
            stats["swap_used_gb"] = round(swap.used / (1024 ** 3), 2)
            stats["swap_total_gb"] = round(swap.total / (1024 ** 3), 2)
        except Exception:
            pass
        try:
            sensors = psutil.sensors_temperatures()
            if sensors:
                for name, entries in sensors.items():
                    if entries:
                        stats[f"temp_{name}"] = round(entries[0].current, 1)
                        break
        except Exception:
            pass
        try:
            procs = len(psutil.pids())
            stats["processes"] = procs
        except Exception:
            pass
    return stats


def _pct(val: float, warn: float = 70, bad: float = 90) -> str:
    """Format a percentage value with warning/high thresholds."""
    if val >= bad:
        return f"{val:.0f}% HIGH"
    if val >= warn:
        return f"{val:.0f}%"
    return f"{val:.0f}%"


def _sep(title: str = "") -> str:
    """Return a separator line with optional title."""
    line = "-" * 48
    if title:
        return f"\n-- {title} {line[len(title)+5:]}"
    return line


def _load_json(path: str, default: Any = None) -> Any:
    """Load a JSON file safely, returning default on failure."""
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data: Any) -> None:
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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
        if "cpu_freq_mhz" in stats:
            lines.append(f"  CPU Freq {stats['cpu_freq_mhz']:.0f} MHz ({stats.get('cpu_count', '?')} cores)")
        if "load_1min" in stats:
            lines.append(f"  Load    {stats['load_1min']}/{stats['load_5min']}/{stats['load_15min']} (1/5/15 min)")
        if "swap_percent" in stats:
            lines.append(f"  Swap    {_pct(stats['swap_percent'])}")
        if "processes" in stats:
            lines.append(f"  Procs   {stats['processes']} running")

    # Agents & Town Hall
    lines.append(_sep("Agents & Town Hall"))
    try:
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


# ---------------------------------------------------------------------------
# 1. Category-specific detailed reports
# ---------------------------------------------------------------------------

def detailed_system_report() -> str:
    """Generate a comprehensive system health report with 5-10x more detail."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED SYSTEM HEALTH REPORT")
    lines.append("=" * 56)
    stats = _system_stats()
    lines.append(f"  Timestamp:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not stats:
        lines.append("  [psutil not available -- limited system info]")
        lines.append("=" * 56)
        return "\n".join(lines)

    lines.append("")
    lines.append("--- CPU ---")
    lines.append(f"  Usage:           {_pct(stats.get('cpu', 0))}")
    lines.append(f"  Cores:           {stats.get('cpu_count', 'N/A')}")
    if "cpu_freq_mhz" in stats:
        lines.append(f"  Frequency:       {stats['cpu_freq_mhz']:.1f} MHz")
    if "load_1min" in stats:
        lines.append(f"  Load Average:    {stats['load_1min']} / {stats['load_5min']} / {stats['load_15min']}  (1/5/15 min)")

    lines.append("")
    lines.append("--- Memory ---")
    lines.append(f"  Usage:           {_pct(stats.get('memory', 0))}")
    if "memory_total_gb" in stats:
        lines.append(f"  Total:           {stats['memory_total_gb']:.2f} GB")
        lines.append(f"  Used:            {stats['memory_used_gb']:.2f} GB")
        lines.append(f"  Available:       {stats['memory_available_gb']:.2f} GB")

    lines.append("")
    lines.append("--- Swap ---")
    if "swap_percent" in stats:
        lines.append(f"  Usage:           {_pct(stats['swap_percent'])}")
        lines.append(f"  Total:           {stats['swap_total_gb']:.2f} GB")
        lines.append(f"  Used:            {stats['swap_used_gb']:.2f} GB")
    else:
        lines.append("  (not available)")

    lines.append("")
    lines.append("--- Disk ---")
    lines.append(f"  Usage:           {_pct(stats.get('disk', 0), warn=80, bad=90)}")
    if "disk_total_gb" in stats:
        lines.append(f"  Total:           {stats['disk_total_gb']:.2f} GB")
        lines.append(f"  Used:            {stats['disk_used_gb']:.2f} GB")
        lines.append(f"  Free:            {stats['disk_free_gb']:.2f} GB")

    lines.append("")
    lines.append("--- Network ---")
    if "net_sent_mb" in stats:
        lines.append(f"  Data Sent:       {stats['net_sent_mb']:.2f} MB")
        lines.append(f"  Data Received:   {stats['net_recv_mb']:.2f} MB")
    else:
        lines.append("  (not available)")

    lines.append("")
    lines.append("--- System ---")
    lines.append(f"  Boot Time:       {stats.get('boot_time', '?')[:19]}")
    if "processes" in stats:
        lines.append(f"  Processes:       {stats['processes']}")
    if "temp_coretemp" in stats:
        lines.append(f"  CPU Temp:        {stats['temp_coretemp']:.1f}C")
    lines.append(f"  Python:          {sys.version.split()[0]}")
    lines.append(f"  Platform:        {sys.platform}")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


def detailed_agent_report() -> str:
    """Generate a detailed agent and town hall status report."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED AGENT REPORT")
    lines.append("=" * 56)
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("--- Agent Roles ---")
    try:
        for name, desc in AGENT_ROLES.items():
            lines.append(f"  o {name.capitalize():12s}  {desc}")
    except Exception:
        lines.append("  (unavailable)")

    lines.append("")
    lines.append("--- Sessions ---")
    try:
        sessions_info = json.loads(townhall_tool("status"))
        lines.append(f"  Total Sessions:     {sessions_info.get('total_sessions', 0)}")
        lines.append(f"  Active Sessions:    {sessions_info.get('active_sessions', 0)}")
        lines.append(f"  Total Messages:     {sessions_info.get('total_messages', 0)}")
        lines.append(f"  Open Agenda Items:  {sessions_info.get('open_agenda_items', 0)}")
        lines.append(f"  Agents Available:   {sessions_info.get('agents_available', 0)}")
    except Exception as e:
        lines.append(f"  (town hall error: {e})")

    lines.append("")
    lines.append("--- Session Detail ---")
    try:
        all_sessions = json.loads(townhall_tool("sessions"))
        if "No sessions" in all_sessions:
            lines.append("  No sessions found.")
        else:
            for s_line in all_sessions.split("\n"):
                lines.append(f"  {s_line}")
    except Exception:
        lines.append("  Could not list sessions.")

    lines.append("")
    lines.append("--- Agenda Items ---")
    try:
        agenda_text = townhall_tool("agenda")
        if not agenda_text or agenda_text == "No agenda items.":
            lines.append("  No agenda items.")
        else:
            for a_line in agenda_text.split("\n"):
                lines.append(f"  {a_line}")
    except Exception:
        lines.append("  Could not load agenda.")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


def detailed_tool_report() -> str:
    """Generate a detailed tool registry report."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED TOOL REGISTRY REPORT")
    lines.append("=" * 56)
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    try:
        grouped = list_tool_registry()
        total_tools = sum(len(v) for v in grouped.values())
        lines.append(f"  Total Tools:  {total_tools}")
        lines.append(f"  Categories:   {len(grouped)}")
        lines.append("")

        # Risk distribution
        risk_counts: Dict[str, int] = defaultdict(int)
        for tname, tmeta in TOOL_META.items():
            risk_counts[tmeta.get("risk", "unknown")] += 1

        lines.append("--- Risk Distribution ---")
        for risk, count in sorted(risk_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {risk:25s}  {count}")
        lines.append("")

        lines.append("--- Tools by Category ---")
        for cat in sorted(grouped.keys()):
            tools = grouped[cat]
            lines.append(f"  [{cat}] ({len(tools)} tools)")
            for t in sorted(tools):
                meta = TOOL_META.get(t, {})
                risk = meta.get("risk", "?")
                desc = meta.get("description", "")[:60]
                lines.append(f"    - {t:30s}  [{risk:20s}]  {desc}")
            lines.append("")
    except Exception as e:
        lines.append(f"  (registry error: {e})")

    lines.append("=" * 56)
    return "\n".join(lines)


def detailed_daemon_report() -> str:
    """Generate a detailed daemon and persistence status report."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED DAEMON REPORT")
    lines.append("=" * 56)
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("--- Self-Improve Daemon ---")
    daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
    if os.path.exists(daemon_flag):
        with open(daemon_flag) as f:
            daemon_pid = f.read().strip()
        lines.append(f"  Status:    RUNNING")
        lines.append(f"  PID:       {daemon_pid}")
        daemon_log = os.path.join(FRIDAY_MEMORY, "self_improve", "daemon.log")
        if os.path.exists(daemon_log):
            size_kb = os.path.getsize(daemon_log) / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(daemon_log)).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"  Log Size:  {size_kb:.1f} KB")
            lines.append(f"  Last Mod:  {mtime}")
    else:
        lines.append("  Status:    STOPPED")
    lines.append("")

    lines.append("--- Sidecars ---")
    sidecars_file = os.path.join(FRIDAY_MEMORY, "sidecars.json")
    sidecars = _load_json(sidecars_file, {})
    if isinstance(sidecars, dict) and sidecars:
        lines.append(f"  Active Sidecars: {len(sidecars)}")
        for sc_name, sc_info in list(sidecars.items())[:10]:
            sc_pid = sc_info.get("pid", "?") if isinstance(sc_info, dict) else "?"
            lines.append(f"    - {sc_name}: PID {sc_pid}")
    else:
        lines.append("  None active")
    lines.append("")

    lines.append("--- Checkpoints ---")
    checkpoint_dir = os.path.join(FRIDAY_MEMORY, "checkpoints")
    if os.path.isdir(checkpoint_dir):
        checkpoints = sorted([f for f in os.listdir(checkpoint_dir) if f.endswith(".json")])
        lines.append(f"  Total Checkpoints: {len(checkpoints)}")
        if checkpoints:
            total_size = sum(os.path.getsize(os.path.join(checkpoint_dir, c)) for c in checkpoints)
            lines.append(f"  Total Size:        {total_size / 1024:.1f} KB")
            lines.append(f"  Latest:            {checkpoints[-1].replace('.json', '')[:19]}")
            lines.append(f"  Earliest:          {checkpoints[0].replace('.json', '')[:19]}")
    else:
        lines.append("  No checkpoints directory")
    lines.append("")

    lines.append("--- Persistence Directory ---")
    persist_dir = os.path.join(FRIDAY_MEMORY, "persistence")
    if os.path.isdir(persist_dir):
        entries = os.listdir(persist_dir)
        total_size = 0
        for entry in entries:
            ep = os.path.join(persist_dir, entry)
            if os.path.isfile(ep):
                total_size += os.path.getsize(ep)
        lines.append(f"  Files: {len(entries)}")
        lines.append(f"  Size:  {total_size / 1024:.1f} KB")
    else:
        lines.append("  No persistence directory")
    lines.append("")

    lines.append("--- Memory Graph ---")
    memory_file = os.path.join(FRIDAY_MEMORY, "memory_graph.json")
    if os.path.exists(memory_file):
        size_kb = os.path.getsize(memory_file) / 1024
        mtime = datetime.fromtimestamp(os.path.getmtime(memory_file)).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"  Size:     {size_kb:.1f} KB")
        lines.append(f"  Modified: {mtime}")
        try:
            with open(memory_file, "r") as f:
                mg = json.load(f)
            nodes = len(mg.get("nodes", []))
            edges = len(mg.get("edges", []))
            lines.append(f"  Nodes:    {nodes}")
            lines.append(f"  Edges:    {edges}")
        except Exception:
            lines.append("  (could not parse)")
    else:
        lines.append("  Not found")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


def detailed_validation_report() -> str:
    """Generate a detailed validation middleware report."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED VALIDATION REPORT")
    lines.append("=" * 56)
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    try:
        vs = json.loads(validation_tool("stats"))
        lines.append("--- Validation Stats ---")
        for key, value in vs.items():
            lines.append(f"  {key:30s}  {value}")
    except Exception:
        lines.append("  (validation middleware unavailable)")
    lines.append("")

    lines.append("--- Recent Validation Log ---")
    vlog = os.path.join(FRIDAY_MEMORY, "validation_log.jsonl")
    if os.path.exists(vlog):
        entries = []
        with open(vlog, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        passed = sum(1 for e in entries if e.get("passed", False))
        failed = sum(1 for e in entries if not e.get("passed", True))
        total = len(entries)
        lines.append(f"  Total Entries:  {total}")
        lines.append(f"  Passed:         {passed}")
        lines.append(f"  Failed:         {failed}")
        lines.append(f"  Log File Size:  {os.path.getsize(vlog) / 1024:.1f} KB")
        lines.append("")
        lines.append("  Last 10 entries:")
        for e in entries[-10:]:
            name = e.get("name", "?")
            sev = e.get("severity", "?")
            msg = e.get("message", "")[:60]
            status = "PASS" if e.get("passed", False) else "FAIL"
            lines.append(f"    [{status}] {name:25s} {sev:8s} {msg}")
    else:
        lines.append("  Validation log not found")

    lines.append("")
    lines.append("--- Profiles ---")
    try:
        from friday.validation_middleware import PROFILE_THRESHOLDS
        for pname, pconf in PROFILE_THRESHOLDS.items():
            lines.append(f"  {pname:12s}  fail_on={pconf['fail_on']}, log_level={pconf['log_level']}")
    except Exception:
        lines.append("  (profiles unavailable)")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


def detailed_services_report() -> str:
    """Generate a detailed services and integration report."""
    lines = []
    lines.append("=" * 56)
    lines.append("  DETAILED SERVICES REPORT")
    lines.append("=" * 56)
    lines.append(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("--- Python Environment ---")
    lines.append(f"  Python:    {sys.version.split()[0]}")
    lines.append(f"  Platform:  {sys.platform}")
    lines.append(f"  Executable: {sys.executable}")
    lines.append("")

    lines.append("--- Installed Packages ---")
    pkgs = {}
    try:
        import pkg_resources
        for dist in pkg_resources.working_set:
            pkgs[dist.key] = dist.version
    except Exception:
        pass

    for pkg_name in ["interpreter", "fastapi", "uvicorn", "pydantic", "rich", "psutil", "httpx", "requests", "websockets"]:
        if pkg_name in pkgs:
            lines.append(f"  {pkg_name:25s}  {pkgs[pkg_name]}")
        else:
            lines.append(f"  {pkg_name:25s}  (not installed)")
    lines.append("")

    lines.append("--- Open Interpreter ---")
    try:
        import interpreter
        lines.append(f"  Version:       {interpreter.__version__}")
    except (ImportError, AttributeError):
        lines.append("  Not available")
    lines.append("")

    lines.append("--- Dashboard API ---")
    try:
        import fastapi
        lines.append(f"  fastapi:       {fastapi.__version__}")
    except (ImportError, AttributeError):
        lines.append("  fastapi:       not available")
    try:
        import uvicorn
        lines.append(f"  uvicorn:       {uvicorn.__version__}")
    except (ImportError, AttributeError):
        lines.append("  uvicorn:       not available")
    lines.append("")

    lines.append("--- MCP Servers ---")
    mcp_dir = os.path.join(FRIDAY_MEMORY, "mcp")
    if os.path.isdir(mcp_dir):
        servers = sorted([d for d in os.listdir(mcp_dir) if os.path.isdir(os.path.join(mcp_dir, d))])
        lines.append(f"  Total: {len(servers)}")
        for s in servers:
            srv_dir = os.path.join(mcp_dir, s)
            cfg_file = os.path.join(srv_dir, "config.json")
            if os.path.exists(cfg_file):
                try:
                    cfg = _load_json(cfg_file, {})
                    status = cfg.get("status", "unknown")
                    lines.append(f"  o {s:20s}  {status}")
                except Exception:
                    lines.append(f"  - {s:20s}  (config unreadable)")
            else:
                lines.append(f"  - {s:20s}  (no config)")
    else:
        lines.append("  No MCP directory")
    lines.append("")

    lines.append("--- Cron / Scheduler ---")
    sched_file = os.path.join(FRIDAY_MEMORY, "schedules.json")
    schedules = _load_json(sched_file, {})
    if isinstance(schedules, dict):
        sched_count = len(schedules.get("schedules", [])) if "schedules" in schedules else (len(schedules) if schedules else 0)
        lines.append(f"  Scheduled tasks: {sched_count}")
    else:
        lines.append("  No schedules found")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. History tracking
# ---------------------------------------------------------------------------

class DashboardHistory:
    """Tracks historical readings of system metrics with delta computation."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._entries: List[dict] = []
        self._load()

    def _load(self) -> None:
        """Load history entries from disk."""
        with _dashboard_lock:
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    self._entries.append(json.loads(line))
                                except Exception:
                                    pass
                except Exception:
                    pass
            while len(self._entries) > self.max_entries:
                self._entries.pop(0)

    def save(self) -> None:
        """Persist all entries to disk."""
        with _dashboard_lock:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, "w") as f:
                for entry in self._entries:
                    f.write(json.dumps(entry) + "\n")

    def add_entry(self, entry: dict) -> None:
        """Add a new history entry with timestamp."""
        entry["_timestamp"] = time.time()
        entry["_datetime"] = datetime.now().isoformat()
        self._entries.append(entry)
        while len(self._entries) > self.max_entries:
            self._entries.pop(0)

    def get_all(self) -> List[dict]:
        """Return all history entries."""
        return list(self._entries)

    def get_recent(self, count: int = 10) -> List[dict]:
        """Return the most recent N entries."""
        return self._entries[-count:]

    def deltas(self) -> dict:
        """Compute deltas between the last two entries."""
        if len(self._entries) < 2:
            return {}
        prev = self._entries[-2]
        curr = self._entries[-1]
        deltas = {}
        for key in ["cpu", "memory", "disk", "swap_percent", "processes"]:
            if key in curr and key in prev:
                try:
                    diff = float(curr[key]) - float(prev[key])
                    deltas[f"{key}_delta"] = round(diff, 1)
                except (ValueError, TypeError):
                    pass
        if "_timestamp" in curr and "_timestamp" in prev:
            deltas["time_delta_sec"] = round(curr["_timestamp"] - prev["_timestamp"], 1)
        return deltas

    def show_trends(self, duration: str = "1h") -> str:
        """Show trend data over a specified duration (e.g. 30m, 1h, 4h, 24h)."""
        lines = []
        lines.append("=" * 56)
        lines.append(f"  SYSTEM TRENDS (last {duration})")
        lines.append("=" * 56)

        if not self._entries:
            lines.append("  No history data available.")
            lines.append("=" * 56)
            return "\n".join(lines)

        # Parse duration
        unit = duration[-1]
        try:
            amount = int(duration[:-1])
        except ValueError:
            lines.append(f"  Invalid duration: {duration}. Use e.g. 30m, 1h, 4h, 24h")
            lines.append("=" * 56)
            return "\n".join(lines)

        if unit == "m":
            cutoff = time.time() - amount * 60
        elif unit == "h":
            cutoff = time.time() - amount * 3600
        elif unit == "d":
            cutoff = time.time() - amount * 86400
        else:
            lines.append(f"  Invalid unit: {unit}. Use m, h, or d.")
            lines.append("=" * 56)
            return "\n".join(lines)

        relevant = [e for e in self._entries if e.get("_timestamp", 0) >= cutoff]
        if not relevant:
            lines.append(f"  No data in the last {duration}.")
            lines.append("=" * 56)
            return "\n".join(lines)

        cpu_vals = [e.get("cpu", 0) for e in relevant if "cpu" in e]
        mem_vals = [e.get("memory", 0) for e in relevant if "memory" in e]
        disk_vals = [e.get("disk", 0) for e in relevant if "disk" in e]

        def summarize(vals: List[float], label: str) -> str:
            if not vals:
                return f"  {label:12s}  no data"
            avg = sum(vals) / len(vals)
            mn = min(vals)
            mx = max(vals)
            return f"  {label:12s}  avg={avg:.1f}%  min={mn:.1f}%  max={mx:.1f}%  samples={len(vals)}"

        lines.append(summarize(cpu_vals, "CPU"))
        lines.append(summarize(mem_vals, "Memory"))
        lines.append(summarize(disk_vals, "Disk"))

        lines.append("")
        lines.append("--- Last 6 Readings ---")
        for e in relevant[-6:]:
            ts = datetime.fromtimestamp(e.get("_timestamp", 0)).strftime("%H:%M:%S")
            cpu_s = f"{e.get('cpu', '?'):>5}" if "cpu" in e else "  N/A"
            mem_s = f"{e.get('memory', '?'):>5}" if "memory" in e else "  N/A"
            dsk_s = f"{e.get('disk', '?'):>5}" if "disk" in e else "  N/A"
            lines.append(f"  {ts}   CPU={cpu_s}%  MEM={mem_s}%  DSK={dsk_s}%")

        lines.append("=" * 56)
        return "\n".join(lines)

    def export_csv(self, output_path: str) -> str:
        """Export history entries to a CSV file."""
        if not self._entries:
            return "No history entries to export."
        fieldnames = set()
        for e in self._entries:
            fieldnames.update(e.keys())
        fieldnames = sorted(fieldnames)
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for e in self._entries:
                    writer.writerow(e)
            return f"Exported {len(self._entries)} entries to {output_path}"
        except Exception as exc:
            return f"Export failed: {exc}"

    def __len__(self) -> int:
        return len(self._entries)


_history_instance: Optional[DashboardHistory] = None


def _get_history() -> DashboardHistory:
    """Return the singleton DashboardHistory instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = DashboardHistory()
    return _history_instance


def save_history_entry(stats: Optional[dict] = None) -> str:
    """Save a snapshot of current stats to the history log."""
    if stats is None:
        stats = _system_stats()
    history = _get_history()
    history.add_entry(stats)
    history.save()
    return f"History entry saved ({len(history)} total entries)"


def load_history() -> List[dict]:
    """Load and return all history entries."""
    return _get_history().get_all()


def show_trends(duration: str = "1h") -> str:
    """Show system metric trends over a specified duration."""
    return _get_history().show_trends(duration)


# ---------------------------------------------------------------------------
# 3. Alert system
# ---------------------------------------------------------------------------

class AlertThreshold:
    """Define an alert threshold for a system metric."""

    def __init__(
        self,
        metric: str,
        warning: float = 80.0,
        critical: float = 90.0,
        label: str = "",
        enabled: bool = True,
    ):
        self.metric = metric
        self.warning = warning
        self.critical = critical
        self.label = label or metric
        self.enabled = enabled

    def check(self, value: float) -> Optional[str]:
        """Check a value against thresholds. Returns severity or None."""
        if not self.enabled:
            return None
        if value >= self.critical:
            return "CRITICAL"
        if value >= self.warning:
            return "WARNING"
        return None

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "warning": self.warning,
            "critical": self.critical,
            "label": self.label,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(d: dict) -> AlertThreshold:
        return AlertThreshold(
            metric=d.get("metric", "unknown"),
            warning=d.get("warning", 80),
            critical=d.get("critical", 90),
            label=d.get("label", ""),
            enabled=d.get("enabled", True),
        )


DEFAULT_THRESHOLDS = [
    AlertThreshold("cpu", warning=80, critical=90, label="CPU Usage"),
    AlertThreshold("memory", warning=80, critical=90, label="Memory Usage"),
    AlertThreshold("disk", warning=85, critical=95, label="Disk Usage"),
    AlertThreshold("swap_percent", warning=70, critical=85, label="Swap Usage"),
]


class AlertManager:
    """Manages alert thresholds, checking, and history."""

    def __init__(self):
        self._thresholds: List[AlertThreshold] = list(DEFAULT_THRESHOLDS)
        self._alerts: List[dict] = []
        self._load()

    def _load(self) -> None:
        """Load alert history from disk."""
        data = _load_json(ALERTS_FILE, {"alerts": [], "thresholds": []})
        self._alerts = data.get("alerts", [])
        loaded_thresholds = data.get("thresholds", [])
        if loaded_thresholds:
            self._thresholds = [AlertThreshold.from_dict(t) for t in loaded_thresholds]

    def _save(self) -> None:
        """Save alerts and thresholds to disk."""
        data = {
            "alerts": self._alerts,
            "thresholds": [t.to_dict() for t in self._thresholds],
        }
        _save_json(ALERTS_FILE, data)

    def set_threshold(self, metric: str, warning: float, critical: float) -> str:
        """Set or update a threshold for a metric."""
        for t in self._thresholds:
            if t.metric == metric:
                t.warning = warning
                t.critical = critical
                self._save()
                return f"Threshold updated: {metric} ({warning}/{critical})"
        self._thresholds.append(AlertThreshold(metric, warning, critical, label=metric))
        self._save()
        return f"Threshold created: {metric} ({warning}/{critical})"

    def remove_threshold(self, metric: str) -> str:
        """Remove a threshold by metric name."""
        for t in self._thresholds:
            if t.metric == metric:
                self._thresholds.remove(t)
                self._save()
                return f"Threshold removed: {metric}"
        return f"No threshold found for: {metric}"

    def check(self, current_stats: dict) -> List[dict]:
        """Check current stats against all thresholds and generate alerts."""
        new_alerts = []
        for threshold in self._thresholds:
            value = current_stats.get(threshold.metric)
            if value is None:
                continue
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
            severity = threshold.check(value)
            if severity:
                alert = {
                    "metric": threshold.metric,
                    "label": threshold.label,
                    "value": value,
                    "severity": severity,
                    "warning": threshold.warning,
                    "critical": threshold.critical,
                    "timestamp": time.time(),
                    "datetime": datetime.now().isoformat(),
                }
                self._alerts.append(alert)
                new_alerts.append(alert)
        # Prune old alerts (keep max 1000)
        while len(self._alerts) > 1000:
            self._alerts.pop(0)
        self._save()
        return new_alerts

    def list_alerts(self, severity: str = "") -> List[dict]:
        """List all alerts, optionally filtered by severity."""
        if severity:
            return [a for a in self._alerts if a.get("severity", "").upper() == severity.upper()]
        return list(self._alerts)

    def clear_alerts(self) -> str:
        """Clear all alerts."""
        count = len(self._alerts)
        self._alerts = []
        self._save()
        return f"Cleared {count} alert(s)"

    def list_thresholds(self) -> List[dict]:
        """Return all thresholds as dicts."""
        return [t.to_dict() for t in self._thresholds]

    def last_alert_time(self) -> Optional[str]:
        """Return the timestamp of the most recent alert."""
        if not self._alerts:
            return None
        return self._alerts[-1].get("datetime", "")

    def alert_count(self) -> int:
        """Return total number of alerts."""
        return len(self._alerts)


_alert_manager_instance: Optional[AlertManager] = None


def _get_alert_manager() -> AlertManager:
    """Return the singleton AlertManager instance."""
    global _alert_manager_instance
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager()
    return _alert_manager_instance


def check_alerts(current_stats: Optional[dict] = None) -> str:
    """Check current stats against all thresholds and report new alerts."""
    if current_stats is None:
        current_stats = _system_stats()
    mgr = _get_alert_manager()
    new_alerts = mgr.check(current_stats)
    if not new_alerts:
        return "No alerts triggered."
    lines = [f"ALERTS TRIGGERED ({len(new_alerts)}):"]
    for a in new_alerts:
        lines.append(f"  [{a['severity']}] {a['label']}: {a['value']:.1f}% (threshold: {a['warning']}%/ {a['critical']}%)")
    return "\n".join(lines)


def list_alerts(severity: str = "") -> str:
    """List all tracked alerts, optionally filtered by severity."""
    mgr = _get_alert_manager()
    alerts = mgr.list_alerts(severity)
    if not alerts:
        return f"No alerts recorded{'' if not severity else f' with severity {severity}'}."
    lines = [f"ALERTS ({len(alerts)} total):"]
    for a in alerts[-50:]:
        ts = a.get("datetime", "")[11:19] if a.get("datetime", "") else "??:??:??"
        sev = a["severity"]
        label = a.get("label", a["metric"])
        val = a.get("value", "?")
        lines.append(f"  [{ts}] [{sev:8s}] {label}: {val}")
    return "\n".join(lines)


def clear_alerts() -> str:
    """Clear all recorded alerts."""
    return _get_alert_manager().clear_alerts()


# ---------------------------------------------------------------------------
# 4. Export functionality
# ---------------------------------------------------------------------------

def export_report(format: str = "text", output_path: str = "") -> str:
    """Export the system report in the specified format.

    Supported formats: text, json, html, markdown.
    If output_path is empty, returns the report as a string.
    """
    stats = _system_stats()
    now = datetime.now().isoformat()

    if format == "text":
        report = build_text_report()
    elif format == "json":
        report_data = {
            "timestamp": now,
            "system": stats,
        }
        try:
            sessions_info = json.loads(townhall_tool("status"))
            report_data["town_hall"] = sessions_info
        except Exception:
            report_data["town_hall"] = {"error": "unavailable"}
        try:
            grouped = list_tool_registry()
            report_data["tool_registry"] = {
                "total": sum(len(v) for v in grouped.values()),
                "categories": {k: len(v) for k, v in grouped.items()},
            }
        except Exception:
            report_data["tool_registry"] = {"error": "unavailable"}
        try:
            vs = json.loads(validation_tool("stats"))
            report_data["validation"] = vs
        except Exception:
            report_data["validation"] = {"error": "unavailable"}
        report = json.dumps(report_data, indent=2)
    elif format == "html":
        lines = ["<!DOCTYPE html><html><head><title>FRIDAY System Report</title>",
                 "<style>body{font-family:monospace;background:#1e1e1e;color:#d4d4d4;padding:20px}"
                 "h1{color:#569cd6}.section{margin:10px 0;padding:5px;border-left:3px solid #569cd6}"
                 ".ok{color:#4ec9b0}.warn{color:#dcdcaa}.high{color:#f44747}</style></head><body>",
                 f"<h1>FRIDAY System Report</h1>",
                 f"<p class='ok'>{now}</p>"]
        if stats:
            cpu_cls = "high" if stats.get("cpu", 0) >= 90 else ("warn" if stats.get("cpu", 0) >= 70 else "ok")
            mem_cls = "high" if stats.get("memory", 0) >= 90 else ("warn" if stats.get("memory", 0) >= 80 else "ok")
            dsk_cls = "high" if stats.get("disk", 0) >= 90 else ("warn" if stats.get("disk", 0) >= 85 else "ok")
            lines.append("<div class='section'>")
            lines.append(f"<p>CPU: <span class='{cpu_cls}'>{stats.get('cpu', 0)}%</span></p>")
            lines.append(f"<p>Memory: <span class='{mem_cls}'>{stats.get('memory', 0)}%</span></p>")
            lines.append(f"<p>Disk: <span class='{dsk_cls}'>{stats.get('disk', 0)}%</span></p>")
            lines.append("</div>")
        lines.append("</body></html>")
        report = "\n".join(lines)
    elif format == "markdown":
        lines = [f"# FRIDAY System Report", f"**Generated:** {now[:19]}", ""]
        if stats:
            lines.append("## System Health")
            lines.append(f"- CPU: {_pct(stats.get('cpu', 0))}")
            lines.append(f"- Memory: {_pct(stats.get('memory', 0))}")
            lines.append(f"- Disk: {_pct(stats.get('disk', 0), warn=80, bad=90)}")
            lines.append(f"- Boot: {stats.get('boot_time', '?')[:19]}")
            lines.append("")
        try:
            sessions_info = json.loads(townhall_tool("status"))
            lines.append("## Town Hall")
            lines.append(f"- Active Sessions: {sessions_info.get('active_sessions', 0)}")
            lines.append(f"- Total Messages: {sessions_info.get('total_messages', 0)}")
            lines.append("")
        except Exception:
            pass
        report = "\n".join(lines)
    else:
        return f"Unsupported format: {format}. Supported: text, json, html, markdown"

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            return f"Report exported to {output_path} ({len(report)} bytes)"
        except Exception as exc:
            return f"Export failed: {exc}"
    return report


def export_history_csv(output_path: str) -> str:
    """Export the dashboard history to a CSV file."""
    history = _get_history()
    if len(history) == 0:
        return "No history entries to export."
    return history.export_csv(output_path)


# ---------------------------------------------------------------------------
# 5. Filter and search
# ---------------------------------------------------------------------------

def filter_by_category(category: str) -> str:
    """Filter the tool registry by category and return a report."""
    lines = []
    lines.append("=" * 56)
    lines.append(f"  TOOLS IN CATEGORY: {category}")
    lines.append("=" * 56)

    try:
        grouped = list_tool_registry(category)
        if not grouped or category not in grouped:
            lines.append(f"  No tools found in category '{category}'.")
            lines.append(f"  Available categories:")
            all_groups = list_tool_registry()
            for cat in sorted(all_groups.keys()):
                lines.append(f"    - {cat}")
            lines.append("=" * 56)
            return "\n".join(lines)

        tools = grouped[category]
        lines.append(f"  Total: {len(tools)} tools")
        lines.append("")
        for t in sorted(tools):
            meta = TOOL_META.get(t, {})
            risk = meta.get("risk", "?")
            desc = meta.get("description", "")[:70]
            lines.append(f"  - {t:35s}  [{risk:20s}]  {desc}")
    except Exception as e:
        lines.append(f"  Error: {e}")

    lines.append("=" * 56)
    return "\n".join(lines)


def search_report(query: str) -> str:
    """Search within the report data for a given text query."""
    lines = []
    lines.append("=" * 56)
    lines.append(f"  SEARCH RESULTS FOR: '{query}'")
    lines.append("=" * 56)

    query_lower = query.lower()
    found = False

    # Search system stats
    stats = _system_stats()
    lines.append("--- System Stats ---")
    for key, value in stats.items():
        if query_lower in str(key).lower() or query_lower in str(value).lower():
            lines.append(f"  {key}: {value}")
            found = True
    if not any(query_lower in str(key).lower() or query_lower in str(value).lower() for key, value in stats.items()):
        lines.append("  (no matches)")

    # Search tool registry
    lines.append("")
    lines.append("--- Tool Registry ---")
    try:
        grouped = list_tool_registry()
        total = sum(len(v) for v in grouped.values())
        if query_lower in str(total) or query_lower in "tools" and "registered" in query:
            lines.append(f"  Total tools: {total}")
            found = True
        for cat, tools in sorted(grouped.items()):
            if query_lower in cat.lower():
                lines.append(f"  {cat}: {len(tools)} tools")
                found = True
            for t in tools:
                if query_lower in t.lower():
                    meta = TOOL_META.get(t, {})
                    lines.append(f"  {t:30s}  [{meta.get('risk', '?')}]  ({cat})")
                    found = True
                elif query_lower in meta.get("description", "").lower():
                    lines.append(f"  {t:30s}  - {meta.get('description', '')[:60]}")
                    found = True
    except Exception:
        lines.append("  (unavailable)")
    if not found:
        lines.append("  (no matches in tool registry)")

    # Search town hall
    lines.append("")
    lines.append("--- Town Hall ---")
    try:
        sessions_info = json.loads(townhall_tool("status"))
        for key, value in sessions_info.items():
            if query_lower in str(key).lower() or query_lower in str(value).lower():
                lines.append(f"  {key}: {value}")
                found = True
    except Exception:
        lines.append("  (unavailable)")

    # Search agent roles
    lines.append("")
    lines.append("--- Agents ---")
    try:
        for name, desc in AGENT_ROLES.items():
            if query_lower in name.lower() or query_lower in desc.lower():
                lines.append(f"  {name}: {desc}")
                found = True
    except Exception:
        lines.append("  (unavailable)")

    if not found:
        lines.append("")
        lines.append("  No matches found in any section.")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. Timeline view
# ---------------------------------------------------------------------------

def show_timeline(hours: int = 1) -> str:
    """Show system metrics over time in ASCII format.

    Displays a simple ASCII chart of CPU, memory, and disk over recent history.
    """
    lines = []
    lines.append("=" * 56)
    lines.append(f"  SYSTEM TIMELINE (last {hours} hour(s))")
    lines.append("=" * 56)

    history = _get_history()
    cutoff = time.time() - hours * 3600
    entries = [e for e in history.get_all() if e.get("_timestamp", 0) >= cutoff]

    if len(entries) < 2:
        lines.append("  Not enough history data. Use save_history_entry() periodically.")
        lines.append("=" * 56)
        return "\n".join(lines)

    width = 48
    height = 10

    def render_chart(values: List[float], label: str, high: float = 100) -> str:
        """Render an ASCII line chart for a list of values."""
        chart_lines = []
        chart_lines.append(f"  {label} (0-{high:.0f}%)")
        if not values:
            chart_lines.append("    no data")
            return "\n".join(chart_lines)

        max_val = max(values) if values else 1
        scale = height / max(high, max_val) if max_val > 0 else 1

        for row in range(height, 0, -1):
            threshold = row / scale
            bar = ""
            for v in values:
                if v >= threshold:
                    bar += "#"
                else:
                    bar += " "
            chart_lines.append(f"  {threshold:5.0f} |{bar}")

        # X axis
        ts_marks = len(values)
        x_axis = "       "
        if ts_marks > 0:
            step = max(1, ts_marks // 10)
            for i in range(0, ts_marks, step):
                if i < len(entries):
                    ts = datetime.fromtimestamp(entries[i].get("_timestamp", 0)).strftime("%H:%M")
                    x_axis += ts + " " * (min(step, ts_marks - i) - 1)
        chart_lines.append(x_axis)
        chart_lines.append("")

        return "\n".join(chart_lines)

    cpu_vals = [e.get("cpu", 0) for e in entries if "cpu" in e]
    mem_vals = [e.get("memory", 0) for e in entries if "memory" in e]
    disk_vals = [e.get("disk", 0) for e in entries if "disk" in e]

    if cpu_vals:
        lines.append("")
        lines.append(render_chart(cpu_vals, "CPU", 100))
    if mem_vals:
        lines.append(render_chart(mem_vals, "Memory", 100))
    if disk_vals:
        lines.append(render_chart(disk_vals, "Disk", 100))

    # Summary row
    if cpu_vals:
        avg_cpu = sum(cpu_vals) / len(cpu_vals)
        max_cpu = max(cpu_vals)
        lines.append(f"  CPU Summary:   avg={avg_cpu:.1f}%, max={max_cpu:.1f}%, samples={len(cpu_vals)}")
    if mem_vals:
        avg_mem = sum(mem_vals) / len(mem_vals)
        max_mem = max(mem_vals)
        lines.append(f"  Memory Summary: avg={avg_mem:.1f}%, max={max_mem:.1f}%, samples={len(mem_vals)}")
    if disk_vals:
        avg_disk = sum(disk_vals) / len(disk_vals)
        max_disk = max(disk_vals)
        lines.append(f"  Disk Summary:   avg={avg_disk:.1f}%, max={max_disk:.1f}%, samples={len(disk_vals)}")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. Agent-specific panels
# ---------------------------------------------------------------------------

def show_agent_detail(agent_name: str) -> str:
    """Show detailed information for a specific agent.

    Includes active sessions, message counts, agenda items assigned, and performance stats.
    """
    lines = []
    lines.append("=" * 56)
    lines.append(f"  AGENT DETAIL: {agent_name.upper()}")
    lines.append("=" * 56)

    agent_name_lower = agent_name.lower()

    # Agent role info
    lines.append("")
    lines.append("--- Role ---")
    try:
        if agent_name_lower in AGENT_ROLES:
            lines.append(f"  Name: {agent_name.capitalize()}")
            lines.append(f"  Role: {AGENT_ROLES[agent_name_lower]}")
        else:
            lines.append(f"  Unknown agent: {agent_name}")
            lines.append(f"  Available: {', '.join(AGENT_ROLES.keys())}")
            lines.append("=" * 56)
            return "\n".join(lines)
    except Exception as e:
        lines.append(f"  (roles unavailable: {e})")

    # Session participation
    lines.append("")
    lines.append("--- Session Activity ---")
    try:
        all_sessions_text = townhall_tool("sessions")
        if isinstance(all_sessions_text, str):
            for s_line in all_sessions_text.split("\n"):
                if agent_name_lower in s_line.lower():
                    lines.append(f"  {s_line}")
    except Exception:
        pass

    # Count sessions this agent participated in
    try:
        sessions_data = _load_json(
            os.path.join(FRIDAY_MEMORY, "townhall", "sessions.json"), []
        )
        agent_sessions = 0
        agent_messages = 0
        for s in sessions_data:
            participants = s.get("participants", [])
            if agent_name_lower in [p.lower() for p in participants]:
                agent_sessions += 1
                for msg in s.get("messages", []):
                    if msg.get("from", "").lower() == agent_name_lower:
                        agent_messages += 1
        lines.append(f"  Sessions Participated: {agent_sessions}")
        lines.append(f"  Messages Posted:       {agent_messages}")
    except Exception:
        lines.append("  (session data unavailable)")

    # Agenda items assigned to this agent
    lines.append("")
    lines.append("--- Agenda Assignments ---")
    try:
        agenda_data = _load_json(
            os.path.join(FRIDAY_MEMORY, "townhall", "agenda.json"), {"items": []}
        )
        assigned = [i for i in agenda_data.get("items", [])
                    if i.get("assigned_to", "").lower() == agent_name_lower]
        if assigned:
            lines.append(f"  Total Assigned: {len(assigned)}")
            for item in assigned:
                status = item.get("status", "open")
                title = item.get("title", "?")[:50]
                lines.append(f"    [{status}] {title}")
        else:
            lines.append("  No agenda items assigned.")
    except Exception:
        lines.append("  (agenda data unavailable)")

    # Agent-specific files (logs, state)
    lines.append("")
    lines.append("--- Agent Files ---")
    agent_dirs = [
        os.path.join(FRIDAY_MEMORY, "agent_logs"),
        os.path.join(FRIDAY_MEMORY, "townhall"),
    ]
    found_files = []
    for d in agent_dirs:
        if os.path.isdir(d):
            for fname in os.listdir(d):
                if agent_name_lower in fname.lower():
                    found_files.append(os.path.join(d, fname))
    if found_files:
        for fp in found_files:
            size = os.path.getsize(fp)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"  {os.path.basename(fp):40s}  {size:>8} B  {mtime}")
    else:
        lines.append("  No agent-specific files found.")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. Interactive mode
# ---------------------------------------------------------------------------

def _interactive_loop() -> None:
    """Run an interactive dashboard with keyboard shortcuts.

    Shortcuts:
      (s)ystem      -- detailed system report
      (a)gents      -- detailed agent report
      (t)ools       -- detailed tool report
      (d)aemons     -- detailed daemon report
      (v)alidation  -- detailed validation report
      (e)xport      -- export report
      (h)istory     -- show trends
      (m)emory      -- show memory graph
      (r)rors       -- show recent errors
      (c)onfig      -- show configuration
      (l)ist alerts -- list alerts
      (q)uit        -- exit interactive mode
    """
    print("FRIDAY Interactive Dashboard")
    print("=" * 56)
    print("Shortcuts:")
    print("  (s)ystem      - detailed system report")
    print("  (a)gents      - detailed agent report")
    print("  (t)ools       - detailed tool report")
    print("  (d)aemons     - detailed daemon report")
    print("  (v)alidation  - detailed validation report")
    print("  (e)xport      - export report (text/json/html/markdown)")
    print("  (h)istory     - show trends")
    print("  (m)emory      - show memory graph")
    print("  (r)rors       - show recent errors")
    print("  (c)onfig      - show configuration")
    print("  (l)ist alerts - list alerts")
    print("  (p)robe       - service health probes")
    print("  (w)atch       - watch mode")
    print("  (q)uit        - exit")
    print("=" * 56)

    actions = {
        "s": lambda: print(detailed_system_report()),
        "a": lambda: print(detailed_agent_report()),
        "t": lambda: print(detailed_tool_report()),
        "d": lambda: print(detailed_daemon_report()),
        "v": lambda: print(detailed_validation_report()),
        "e": lambda: _interactive_export(),
        "h": lambda: print(show_trends()),
        "m": lambda: print(show_memory_graph()),
        "r": lambda: print(show_recent_errors(10)),
        "c": lambda: print(show_config()),
        "l": lambda: print(list_alerts()),
        "p": lambda: _interactive_probe(),
        "w": lambda: _interactive_watch(),
        "q": lambda: None,
    }

    while True:
        try:
            cmd = input("\nDashboard> ").strip().lower()
            if cmd == "q" or cmd == "quit":
                print("Exiting interactive dashboard.")
                break
            if cmd == "":
                print(build_text_report())
                continue
            if cmd in actions:
                actions[cmd]()
                # Save a history entry on each command
                save_history_entry()
                check_alerts()
            else:
                # Try longer commands
                if cmd.startswith("export"):
                    parts = cmd.split()
                    fmt = parts[1] if len(parts) > 1 else "text"
                    out = parts[2] if len(parts) > 2 else ""
                    print(export_report(fmt, out))
                elif cmd.startswith("watch"):
                    parts = cmd.split()
                    interval = float(parts[1]) if len(parts) > 1 else 5
                    print(dashboard_cli_tool("watch", interval=interval))
                elif cmd.startswith("trends"):
                    parts = cmd.split()
                    dur = parts[1] if len(parts) > 1 else "1h"
                    print(show_trends(dur))
                elif cmd.startswith("search"):
                    query = cmd[6:].strip()
                    if query:
                        print(search_report(query))
                    else:
                        print("Usage: search <query>")
                elif cmd.startswith("filter"):
                    cat = cmd[6:].strip()
                    if cat:
                        print(filter_by_category(cat))
                    else:
                        print("Usage: filter <category>")
                elif cmd.startswith("agent"):
                    name = cmd[5:].strip()
                    if name:
                        print(show_agent_detail(name))
                    else:
                        print("Usage: agent <name>")
                elif cmd.startswith("alerts"):
                    parts = cmd.split()
                    if len(parts) > 1 and parts[1] == "clear":
                        print(clear_alerts())
                    elif len(parts) > 1:
                        print(list_alerts(parts[1]))
                    else:
                        print(list_alerts())
                elif cmd.startswith("probe"):
                    parts = cmd.split()
                    service = parts[1] if len(parts) > 1 else ""
                    print(probe_service(service))
                elif cmd.startswith("errors"):
                    parts = cmd.split()
                    count = int(parts[1]) if len(parts) > 1 else 10
                    print(show_recent_errors(count))
                elif cmd.startswith("history"):
                    parts = cmd.split()
                    dur = parts[1] if len(parts) > 1 else "1h"
                    print(show_trends(dur))
                elif cmd.startswith("help"):
                    print("Shortcuts: s, a, t, d, v, e, h, m, r, c, l, p, w, q")
                    print("Commands: export <fmt> [path], watch [sec], trends <dur>,")
                    print("          search <query>, filter <cat>, agent <name>,")
                    print("          alerts [clear|severity], probe [svc], errors [n],")
                    print("          history [dur]")
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for commands.")
        except KeyboardInterrupt:
            print("\nExiting interactive dashboard.")
            break
        except EOFError:
            print("\nExiting interactive dashboard.")
            break


def _interactive_export() -> None:
    """Helper for interactive export selection."""
    print("Export format: text, json, html, markdown")
    fmt = input("Format [text]: ").strip().lower() or "text"
    out = input("Output path (empty for stdout): ").strip()
    result = export_report(fmt, out if out else "")
    if not out:
        print(result)
    else:
        print(result)


def _interactive_watch() -> None:
    """Helper for interactive watch mode."""
    print("Watch mode (Ctrl+C to stop)")
    try:
        interval_s = input("Interval seconds [5]: ").strip()
        interval = float(interval_s) if interval_s else 5.0
    except ValueError:
        interval = 5.0
    dashboard_cli_tool("watch", interval=interval)


def _interactive_probe() -> None:
    """Helper for interactive service probing."""
    print("Available probes: dashboard, mcp, registry, persistence, all")
    svc = input("Service [all]: ").strip().lower() or "all"
    if svc == "all":
        # Probe all key services
        for s in ["dashboard", "mcp", "registry", "persistence"]:
            print(probe_service(s))
            print("")
    else:
        print(probe_service(svc))


# ---------------------------------------------------------------------------
# 9. Service health probes
# ---------------------------------------------------------------------------

def probe_service(service_name: str) -> str:
    """Probe a specific service and return health information.

    Supported services: dashboard, mcp, registry, persistence.
    Use 'all' to probe all services.
    """
    lines = []
    lines.append("=" * 56)
    lines.append(f"  SERVICE PROBE: {service_name.upper()}")
    lines.append("=" * 56)

    if service_name == "dashboard" or service_name == "all":
        lines.append("")
        lines.append("--- Dashboard API ---")
        try:
            import fastapi
            import uvicorn
            lines.append(f"  fastapi:  {fastapi.__version__}")
            lines.append(f"  uvicorn:  {uvicorn.__version__}")
        except ImportError as e:
            lines.append(f"  MISSING: {e}")
        # Try to ping the API if there's a known port
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", 8000))
            s.close()
            if result == 0:
                lines.append("  Port 8000: OPEN (dashboard may be running)")
            else:
                lines.append("  Port 8000: CLOSED (dashboard not detected)")
        except Exception as e:
            lines.append(f"  Port check error: {e}")

    if service_name == "mcp" or service_name == "all":
        lines.append("")
        lines.append("--- MCP Servers ---")
        mcp_dir = os.path.join(FRIDAY_MEMORY, "mcp")
        if os.path.isdir(mcp_dir):
            servers = sorted([d for d in os.listdir(mcp_dir) if os.path.isdir(os.path.join(mcp_dir, d))])
            lines.append(f"  Found {len(servers)} MCP server(s)")
            for srv in servers:
                cfg_path = os.path.join(mcp_dir, srv, "config.json")
                if os.path.exists(cfg_path):
                    cfg = _load_json(cfg_path, {})
                    status = cfg.get("status", "configured")
                    lines.append(f"  o {srv:20s}  status={status}")
                else:
                    lines.append(f"  - {srv:20s}  no config.json")
        else:
            lines.append("  MCP directory not found")
        # Check for MCP socket files
        sock_dir = os.path.join(FRIDAY_MEMORY, "sidecar_network")
        if os.path.isdir(sock_dir):
            socks = [f for f in os.listdir(sock_dir) if f.endswith(".sock")]
            lines.append(f"  Socket files: {len(socks)}")

    if service_name == "registry" or service_name == "all":
        lines.append("")
        lines.append("--- Tool Registry Consistency ---")
        try:
            total_meta = len(TOOL_META)
            cats = set(m.get("category", "uncategorized") for m in TOOL_META.values())
            risk_types = set(m.get("risk", "unknown") for m in TOOL_META.values())
            lines.append(f"  Declared tools:    {total_meta}")
            lines.append(f"  Categories:        {len(cats)}")
            lines.append(f"  Risk levels:       {len(risk_types)}")
            lines.append(f"  Categories:        {', '.join(sorted(cats))}")
            lines.append(f"  Risk levels:       {', '.join(sorted(risk_types))}")

            # Check for missing descriptions
            missing_desc = sum(1 for m in TOOL_META.values() if not m.get("description"))
            if missing_desc:
                lines.append(f"  WARNING: {missing_desc} tools missing descriptions")
            else:
                lines.append(f"  All tools have descriptions: OK")
        except Exception as e:
            lines.append(f"  Registry check failed: {e}")

    if service_name == "persistence" or service_name == "all":
        lines.append("")
        lines.append("--- Persistence Directory ---")
        persist_dir = os.path.join(FRIDAY_MEMORY, "persistence")
        if os.path.isdir(persist_dir):
            entries = os.listdir(persist_dir)
            total_size = 0
            file_count = 0
            for entry in entries:
                ep = os.path.join(persist_dir, entry)
                if os.path.isfile(ep):
                    file_count += 1
                    total_size += os.path.getsize(ep)
            lines.append(f"  Files:  {file_count}")
            lines.append(f"  Size:   {total_size / 1024:.1f} KB")
            lines.append(f"  Status: OK")
        else:
            lines.append(f"  Directory not found: {persist_dir}")
            lines.append(f"  Status: MISSING")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 10. Error log viewer
# ---------------------------------------------------------------------------

def show_recent_errors(count: int = 10) -> str:
    """Read FRIDAY error logs and show the most recent failures.

    Checks STARK_LOGS, crash_log.json, and any .log files in friday_memory.
    """
    lines = []
    lines.append("=" * 56)
    lines.append(f"  RECENT ERRORS (last {count})")
    lines.append("=" * 56)

    all_errors = []

    # Check STARK_LOGS
    if os.path.exists(STARK_LOGS):
        try:
            with open(STARK_LOGS, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if line.strip():
                        keywords = ["error", "exception", "traceback", "fail", "crash", "critical"]
                        if any(k in line.lower() for k in keywords):
                            all_errors.append({
                                "source": "STARK_LOGS",
                                "timestamp": line[:19] if len(line) > 19 else "",
                                "message": line[:200],
                                "stacktrace": "",
                            })
        except Exception as e:
            lines.append(f"  Could not read STARK_LOGS: {e}")

    # Check crash_log.json
    crash_log = os.path.join(FRIDAY_MEMORY, "crash_log.json")
    if os.path.exists(crash_log):
        try:
            crash_data = _load_json(crash_log, {})
            if isinstance(crash_data, dict):
                msg = crash_data.get("error", crash_data.get("message", str(crash_data)[:200]))
                ts = crash_data.get("timestamp", crash_data.get("time", ""))
                trace = crash_data.get("traceback", crash_data.get("trace", ""))
                all_errors.append({
                    "source": "crash_log.json",
                    "timestamp": str(ts)[:19] if ts else "",
                    "message": str(msg)[:200],
                    "stacktrace": str(trace)[:500],
                })
            elif isinstance(crash_data, list):
                for item in crash_data[-count:]:
                    msg = item.get("error", item.get("message", str(item)[:200]))
                    ts = item.get("timestamp", item.get("time", ""))
                    trace = item.get("traceback", "")
                    all_errors.append({
                        "source": "crash_log.json",
                        "timestamp": str(ts)[:19] if ts else "",
                        "message": str(msg)[:200],
                        "stacktrace": str(trace)[:500],
                    })
        except Exception as e:
            lines.append(f"  Could not read crash_log.json: {e}")

    # Check validation log for failures
    vlog = os.path.join(FRIDAY_MEMORY, "validation_log.jsonl")
    if os.path.exists(vlog):
        try:
            with open(vlog, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if not entry.get("passed", True):
                                all_errors.append({
                                    "source": "validation_log",
                                    "timestamp": datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S") if entry.get("timestamp") else "",
                                    "message": f"[{entry.get('severity', '?')}] {entry.get('name', '?')}: {entry.get('message', '')[:150]}",
                                    "stacktrace": "",
                                })
                        except Exception:
                            pass
        except Exception:
            pass

    # Check for any .log files in friday_memory
    try:
        for fname in os.listdir(FRIDAY_MEMORY):
            if fname.endswith(".log") or fname.endswith(".log.txt"):
                fpath = os.path.join(FRIDAY_MEMORY, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            line = line.rstrip("\n")
                            keywords = ["error", "exception", "traceback", "fail", "crash"]
                            if any(k in line.lower() for k in keywords):
                                all_errors.append({
                                    "source": fname,
                                    "timestamp": line[:19] if len(line) > 19 else "",
                                    "message": line[:200],
                                    "stacktrace": "",
                                })
                                break  # One per file is enough
                except Exception:
                    pass
    except Exception:
        pass

    # Sort by timestamp descending, then take most recent N
    def sort_key(e):
        ts = e.get("timestamp", "")
        if ts:
            try:
                return datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                return 0
        return 0

    all_errors.sort(key=sort_key, reverse=True)
    recent = all_errors[:count]

    if not recent:
        lines.append("  No recent errors found.")
        lines.append("")
        lines.append("=" * 56)
        return "\n".join(lines)

    lines.append(f"  Found {len(all_errors)} total error(s), showing {len(recent)}")
    lines.append("")

    for i, err in enumerate(recent, 1):
        lines.append(f"  [{i}] Source:    {err['source']}")
        lines.append(f"      Time:     {err['timestamp'] or '(unknown)'}")
        lines.append(f"      Message:  {err['message']}")
        if err.get("stacktrace"):
            # Show first 3 lines of stacktrace
            stack_lines = err["stacktrace"].split("\n")
            for sl in stack_lines[:3]:
                if sl.strip():
                    lines.append(f"      Stack:    {sl.strip()[:120]}")
        lines.append("")

    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 11. Memory graph viewer
# ---------------------------------------------------------------------------

def show_memory_graph(depth: int = 10) -> str:
    """Read friday_memory/memory_graph.json and display graph information.

    Shows node/edge counts, top entities, recent connections, and depth.
    """
    lines = []
    lines.append("=" * 56)
    lines.append("  MEMORY GRAPH VIEWER")
    lines.append("=" * 56)

    memory_file = os.path.join(FRIDAY_MEMORY, "memory_graph.json")
    if not os.path.exists(memory_file):
        lines.append("  Memory graph file not found.")
        lines.append(f"  Expected: {memory_file}")
        lines.append("=" * 56)
        return "\n".join(lines)

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            graph = json.load(f)
    except Exception as e:
        lines.append(f"  Error reading memory graph: {e}")
        lines.append("=" * 56)
        return "\n".join(lines)

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    metadata = graph.get("metadata", {})

    lines.append(f"  File:        {memory_file}")
    size_kb = os.path.getsize(memory_file) / 1024
    lines.append(f"  Size:        {size_kb:.1f} KB")
    lines.append(f"  Modified:    {datetime.fromtimestamp(os.path.getmtime(memory_file)).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("--- Graph Summary ---")
    lines.append(f"  Total Nodes: {len(nodes)}")
    lines.append(f"  Total Edges: {len(edges)}")
    if isinstance(metadata, dict):
        for mk, mv in metadata.items():
            lines.append(f"  Meta: {mk} = {mv}")
    lines.append("")

    # Top entities (by connection count)
    lines.append(f"--- Top Entities (top {min(depth, len(nodes))}) ---")
    if nodes and edges:
        node_connection_count: Dict[str, int] = defaultdict(int)
        for edge in edges:
            if isinstance(edge, dict):
                src = edge.get("source", edge.get("from", ""))
                tgt = edge.get("target", edge.get("to", ""))
                if isinstance(src, str):
                    node_connection_count[src] += 1
                if isinstance(tgt, str):
                    node_connection_count[tgt] += 1
            elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                node_connection_count[str(edge[0])] += 1
                node_connection_count[str(edge[1])] += 1

        # Sort by connection count
        top_nodes = sorted(node_connection_count.items(), key=lambda x: -x[1])[:depth]

        # Build a label map
        label_map: Dict[str, str] = {}
        for node in nodes:
            if isinstance(node, dict):
                nid = node.get("id", node.get("name", ""))
                label = node.get("label", node.get("name", node.get("type", "")))
                if isinstance(nid, str) and isinstance(label, str):
                    label_map[nid] = label
            elif isinstance(node, str):
                label_map[node] = node

        for rank, (nid, conn_count) in enumerate(top_nodes, 1):
            label = label_map.get(nid, nid)
            # Truncate label
            if len(label) > 50:
                label = label[:47] + "..."
            lines.append(f"  {rank:3d}. {label:50s}  {conn_count} connections")
    elif nodes:
        lines.append("  (no edges to compute connections)")
    else:
        lines.append("  (graph is empty)")

    # Recent connections (last N edges)
    lines.append("")
    lines.append(f"--- Recent Connections (last {min(depth, len(edges))}) ---")
    recent_edges = edges[-min(depth, len(edges)):]
    for edge in recent_edges:
        if isinstance(edge, dict):
            src = edge.get("source", edge.get("from", "?"))
            tgt = edge.get("target", edge.get("to", "?"))
            rel = edge.get("relation", edge.get("type", "connected_to"))
            ts = edge.get("timestamp", edge.get("time", ""))
            if isinstance(ts, (int, float)):
                try:
                    ts = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    ts = str(ts)
            lines.append(f"  {src} --[{rel}]--> {tgt}  ({str(ts)[:19]})")
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            lines.append(f"  {edge[0]} -- connected_to --> {edge[1]}")
        else:
            lines.append(f"  {str(edge)[:80]}")

    # Node type distribution
    lines.append("")
    lines.append("--- Node Type Distribution ---")
    type_counts: Dict[str, int] = defaultdict(int)
    for node in nodes:
        if isinstance(node, dict):
            ntype = node.get("type", node.get("category", "unknown"))
            type_counts[str(ntype)] += 1
        else:
            type_counts["unknown"] += 1
    if type_counts:
        for ntype, ncount in sorted(type_counts.items(), key=lambda x: -x[1]):
            bar = "#" * min(ncount, 50)
            lines.append(f"  {ntype:20s}  {ncount:5d}  {bar}")
    else:
        lines.append("  (no type information)")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 12. Configuration viewer
# ---------------------------------------------------------------------------

def show_config() -> str:
    """Read config files and display their contents.

    Checks FRIDAY_CONFIG directory and any JSON config files in friday_memory.
    """
    lines = []
    lines.append("=" * 56)
    lines.append("  CONFIGURATION VIEWER")
    lines.append("=" * 56)

    config_dir = FRIDAY_CONFIG
    if not os.path.isdir(config_dir):
        lines.append(f"  Config directory not found: {config_dir}")
        lines.append("  Checking alternative locations...")
        # Try common config locations
        alt_configs = [
            os.path.join(FRIDAY_MEMORY, "config.json"),
            os.path.join(PROJECT_ROOT, "opencode.json"),
            os.path.join(PROJECT_ROOT, "opencode.jsonc"),
        ]
        found_any = False
        for ac in alt_configs:
            if os.path.exists(ac):
                found_any = True
                lines.append("")
                lines.append(f"--- {os.path.basename(ac)} ---")
                try:
                    with open(ac, "r", encoding="utf-8") as f:
                        content = f.read()
                    if ac.endswith(".jsonc"):
                        # Just show raw for jsonc
                        lines.append(content[:2000])
                    else:
                        try:
                            data = json.loads(content)
                            if isinstance(data, dict):
                                for ck, cv in data.items():
                                    if isinstance(cv, str) and len(cv) > 80:
                                        cv = cv[:77] + "..."
                                    lines.append(f"  {ck}: {json.dumps(cv) if not isinstance(cv, str) else cv}")
                            else:
                                lines.append(json.dumps(data, indent=2)[:2000])
                        except json.JSONDecodeError:
                            lines.append(content[:2000])
                except Exception as e:
                    lines.append(f"  Error reading: {e}")
        if not found_any:
            lines.append("  No configuration files found.")

        lines.append("")
        lines.append("=" * 56)
        return "\n".join(lines)

    # Found config directory
    lines.append(f"  Config directory: {config_dir}")
    lines.append("")

    config_files = []
    for fname in os.listdir(config_dir):
        fpath = os.path.join(config_dir, fname)
        if os.path.isfile(fpath):
            config_files.append(fpath)

    if not config_files:
        lines.append("  No config files found in directory.")
    else:
        for fpath in sorted(config_files):
            fname = os.path.basename(fpath)
            size = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
            lines.append("")
            lines.append(f"--- {fname} ({size} B, modified {mtime}) ---")
            try:
                if fname.endswith(".json"):
                    data = _load_json(fpath, {})
                    if isinstance(data, dict):
                        for ck, cv in data.items():
                            if isinstance(cv, str) and len(cv) > 80:
                                cv = cv[:77] + "..."
                            lines.append(f"  {ck}: {json.dumps(cv) if not isinstance(cv, str) else cv}")
                    elif isinstance(data, list):
                        lines.append(f"  (list with {len(data)} items)")
                    else:
                        lines.append(f"  {json.dumps(data, indent=2)[:500]}")
                elif fname.endswith((".yaml", ".yml")):
                    try:
                        import yaml
                        with open(fpath, "r") as f:
                            data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            for ck, cv in data.items():
                                lines.append(f"  {ck}: {cv}")
                        else:
                            lines.append(str(data)[:500])
                    except ImportError:
                        lines.append("  (yaml library not available, showing raw text)")
                        with open(fpath, "r") as f:
                            lines.append(f.read()[:500])
                    except Exception as e:
                        lines.append(f"  Error parsing yaml: {e}")
                else:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read(1000)
                    lines.append(content)
            except Exception as e:
                lines.append(f"  Error: {e}")

    # Also show sovereign state config
    sov_state = os.path.join(PROJECT_ROOT, "sovereign_state.json")
    if os.path.exists(sov_state):
        lines.append("")
        lines.append(f"--- sovereign_state.json ---")
        try:
            data = _load_json(sov_state, {})
            if isinstance(data, dict):
                for ck, cv in list(data.items())[:20]:
                    if isinstance(cv, str) and len(cv) > 80:
                        cv = cv[:77] + "..."
                    lines.append(f"  {ck}: {json.dumps(cv) if not isinstance(cv, str) else cv}")
                if len(data) > 20:
                    lines.append(f"  ... and {len(data) - 20} more keys")
        except Exception as e:
            lines.append(f"  Error: {e}")

    # Show runtime state
    runtime_file = os.path.join(FRIDAY_MEMORY, "runtime_state.json")
    if os.path.exists(runtime_file):
        lines.append("")
        lines.append(f"--- runtime_state.json ---")
        try:
            data = _load_json(runtime_file, {})
            if isinstance(data, dict):
                for ck, cv in list(data.items())[:15]:
                    if isinstance(cv, str) and len(cv) > 80:
                        cv = cv[:77] + "..."
                    lines.append(f"  {ck}: {json.dumps(cv) if not isinstance(cv, str) else cv}")
                if len(data) > 15:
                    lines.append(f"  ... and {len(data) - 15} more keys")
        except Exception as e:
            lines.append(f"  Error: {e}")

    lines.append("")
    lines.append("=" * 56)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def dashboard_cli_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Dashboard -- CLI output style, no flicker.

    Actions:
      status              - Print full text report to stdout
      watch               - Print status every N seconds (scrolling)
      json                - Return JSON summary
      detailed_system     - Detailed system health report
      detailed_agents     - Detailed agent report
      detailed_tools      - Detailed tool report
      detailed_daemons    - Detailed daemon report
      detailed_validation - Detailed validation report
      detailed_services   - Detailed services report
      save_history        - Save current stats to history
      trends              - Show trends over duration (arg: duration e.g. 1h)
      check_alerts        - Check and report alerts
      list_alerts         - List recent alerts
      clear_alerts        - Clear all alerts
      export              - Export report (arg: format e.g. text/json/html/markdown)
      export_csv          - Export history to CSV (arg: output_path)
      filter              - Filter tools by category (arg: category)
      search              - Search report data (arg: query)
      timeline            - Show ASCII timeline (arg: hours)
      agent               - Show agent detail (arg: agent_name)
      interactive         - Enter interactive mode
      probe               - Probe a service (arg: service_name)
      errors              - Show recent errors (arg: count)
      memory_graph        - Show memory graph info (arg: depth)
      config              - Show configuration
    """
    if action == "status":
        return build_text_report()

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

    elif action == "detailed_system":
        result = detailed_system_report()
        print(result, flush=True)
        return "Done."

    elif action == "detailed_agents":
        result = detailed_agent_report()
        print(result, flush=True)
        return "Done."

    elif action == "detailed_tools":
        result = detailed_tool_report()
        print(result, flush=True)
        return "Done."

    elif action == "detailed_daemons":
        result = detailed_daemon_report()
        print(result, flush=True)
        return "Done."

    elif action == "detailed_validation":
        result = detailed_validation_report()
        print(result, flush=True)
        return "Done."

    elif action == "detailed_services":
        result = detailed_services_report()
        print(result, flush=True)
        return "Done."

    elif action == "save_history":
        interval = float(kwargs.get("interval", 0))
        if interval > 0:
            count = 0
            try:
                while True:
                    save_history_entry()
                    count += 1
                    print(f"Entry {count} saved at {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(interval)
            except KeyboardInterrupt:
                return f"Stopped. {count} entries saved."
        else:
            result = save_history_entry()
            print(result, flush=True)
            return "Done."

    elif action == "trends":
        duration = kwargs.get("duration", "1h")
        result = show_trends(duration)
        print(result, flush=True)
        return "Done."

    elif action == "check_alerts":
        result = check_alerts()
        print(result, flush=True)
        return "Done."

    elif action == "list_alerts":
        severity = kwargs.get("severity", "")
        result = list_alerts(severity)
        print(result, flush=True)
        return "Done."

    elif action == "clear_alerts":
        result = clear_alerts()
        print(result, flush=True)
        return "Done."

    elif action == "export":
        fmt = kwargs.get("format", "text")
        out_path = kwargs.get("output_path", "")
        result = export_report(fmt, out_path)
        print(result, flush=True)
        return "Done."

    elif action == "export_csv":
        out_path = kwargs.get("output_path", "dashboard_history.csv")
        result = export_history_csv(out_path)
        print(result, flush=True)
        return "Done."

    elif action == "filter":
        category = kwargs.get("category", "")
        if not category:
            return "Usage: filter <category>. Available: system, desktop, filesystem, web, browser, vision, memory, code, github, gmail, smart_home, spotify, instagram, goals, internal, security, email, agent, osint"
        result = filter_by_category(category)
        print(result, flush=True)
        return "Done."

    elif action == "search":
        query = kwargs.get("query", "")
        if not query:
            return "Usage: search <query>"
        result = search_report(query)
        print(result, flush=True)
        return "Done."

    elif action == "timeline":
        hours = int(kwargs.get("hours", 1))
        result = show_timeline(hours)
        print(result, flush=True)
        return "Done."

    elif action == "agent":
        agent_name = kwargs.get("agent_name", "")
        if not agent_name:
            return "Usage: agent <name>. Available: " + ", ".join(AGENT_ROLES.keys())
        result = show_agent_detail(agent_name)
        print(result, flush=True)
        return "Done."

    elif action == "interactive":
        _interactive_loop()
        return "Exited interactive mode."

    elif action == "probe":
        service_name = kwargs.get("service_name", "all")
        result = probe_service(service_name)
        print(result, flush=True)
        return "Done."

    elif action == "errors":
        count = int(kwargs.get("count", 10))
        result = show_recent_errors(count)
        print(result, flush=True)
        return "Done."

    elif action == "memory_graph":
        depth = int(kwargs.get("depth", 10))
        result = show_memory_graph(depth)
        print(result, flush=True)
        return "Done."

    elif action == "config":
        result = show_config()
        print(result, flush=True)
        return "Done."

    return f"Unknown action: {action}. Use: status, watch, json, detailed_system, detailed_agents, detailed_tools, detailed_daemons, detailed_validation, detailed_services, save_history, trends, check_alerts, list_alerts, clear_alerts, export, export_csv, filter, search, timeline, agent, interactive, probe, errors, memory_graph, config"


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    kwargs = {}
    if len(sys.argv) > 2:
        # Try to parse remaining args as key=value pairs
        for arg in sys.argv[2:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kwargs[k] = v
            else:
                kwargs["interval"] = arg
    print(dashboard_cli_tool(action, **kwargs))
