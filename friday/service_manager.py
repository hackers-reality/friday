"""
FRIDAY Service Manager — starts/stops all background daemons.
One command to bring FRIDAY fully alive:
  - Self-improvement daemon
  - Web dashboard
  - Auto-checkpointer (persistence)
  - Proactive scheduler
  - Wake word listener
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY

_SERVICES: dict[str, dict] = {}
_LOCK = threading.Lock()


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[FRIDAY {ts}] {msg}")


def start_all(interval: int = 7200) -> str:
    """Start all FRIDAY background services."""
    results = []

    # 1. Persistence auto-checkpointer
    try:
        from friday.persistence import start_auto_checkpoint
        r = start_auto_checkpoint()
        results.append(f"  Persistence: {r}")
        _log("Persistence auto-checkpointer started")
    except Exception as e:
        results.append(f"  Persistence: FAILED - {e}")

    # 2. Self-improvement daemon
    try:
        from friday.self_improve_daemon import daemon_start
        r = daemon_start(interval=interval)
        results.append(f"  Self-Improve: {r}")
        _log(f"Self-improvement daemon started (interval={interval}s)")
    except Exception as e:
        results.append(f"  Self-Improve: FAILED - {e}")

    # 3. Web dashboard
    try:
        from friday.dashboard import start_dashboard
        r = start_dashboard()
        results.append(f"  Dashboard: {r}")
        _log("Web dashboard started")
    except Exception as e:
        results.append(f"  Dashboard: FAILED - {e}")

    # 4. Proactive scheduler (base)
    try:
        from friday.scheduler import scheduler_tool
        r = scheduler_tool("start")
        results.append(f"  Scheduler: {r}")
        _log("Base scheduler started")
    except Exception as e:
        results.append(f"  Scheduler: FAILED - {e}")

    # 5. Record startup continuity event
    try:
        from friday.persistence import record_continuity
        record_continuity("full_startup", {"services": ["persistence", "self_improve", "dashboard", "scheduler"]})
    except Exception:
        pass

    with _LOCK:
        _SERVICES["last_start"] = datetime.now().isoformat()
        _SERVICES["interval"] = interval

    return "FRIDAY Services Started:\n" + "\n".join(results)


def stop_all() -> str:
    """Stop all FRIDAY background services."""
    results = []

    try:
        from friday.self_improve_daemon import daemon_stop
        r = daemon_stop()
        results.append(f"  Self-Improve: {r}")
    except Exception as e:
        results.append(f"  Self-Improve: FAILED - {e}")

    try:
        from friday.scheduler import scheduler_tool
        r = scheduler_tool("stop")
        results.append(f"  Scheduler: {r}")
    except Exception as e:
        results.append(f"  Scheduler: FAILED - {e}")

    try:
        from friday.persistence import stop_auto_checkpoint
        r = stop_auto_checkpoint()
        results.append(f"  Persistence: {r}")
    except Exception as e:
        results.append(f"  Persistence: FAILED - {e}")

    try:
        from friday.persistence import record_continuity
        record_continuity("full_shutdown")
    except Exception:
        pass

    _log("All services stopped")
    return "FRIDAY Services Stopped:\n" + "\n".join(results)


def status_all() -> str:
    """Get status of all FRIDAY services."""
    status = {}

    try:
        from friday.self_improve_daemon import daemon_status
        d = json.loads(daemon_status())
        status["self_improve"] = d
    except Exception:
        status["self_improve"] = {"running": False, "error": True}

    try:
        from friday.dashboard import dashboard_tool
        d = json.loads(dashboard_tool("status"))
        status["dashboard"] = d
    except Exception:
        status["dashboard"] = {"running": False, "error": True}

    try:
        from friday.persistence import persistence_tool
        p = persistence_tool("status")
        lines = p.split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                parsed[k.strip().lower().replace(" ", "_")] = v.strip()
        status["persistence"] = parsed
    except Exception:
        status["persistence"] = {"error": True}

    try:
        from friday.scheduler import scheduler_tool
        s = scheduler_tool("list")
        status["scheduler"] = {"tasks": len([l for l in s.split("\n") if "[" in l]) if s != "No scheduled tasks." else 0}
    except Exception:
        status["scheduler"] = {"error": True}

    try:
        from friday.proactive_scheduler import proactive_scheduler_tool
        p = proactive_scheduler_tool("status")
        lines = p.split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                parsed[k.strip().lower().replace(" ", "_")] = v.strip()
        status["proactive"] = parsed
    except Exception:
        status["proactive"] = {"error": True}

    status["last_start"] = _SERVICES.get("last_start", "never")
    return json.dumps(status, indent=2)


def service_manager_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Service Manager — start/stop all background daemons.
    
    Actions:
      status - Show all service statuses
      start [interval] - Start all services
      stop - Stop all services
    """
    if action == "status":
        return status_all()
    elif action == "start":
        interval = int(kwargs.get("interval", 7200))
        return start_all(interval=interval)
    elif action == "stop":
        return stop_all()
    return f"[FAIL] Unknown action: {action}"
