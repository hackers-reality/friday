"""
FRIDAY Bootstrap — auto-start all background services.
Single entry point to bring FRIDAY to life:
  - Self-improve daemon
  - Dashboard web API
  - Periodic checkpointing
  - Validation middleware
  - Persistence loop
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


# ── Helpers ──

def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)


def _touch(path: str, content: str = ""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


# ── Service: Self-Improve Daemon ──

def _start_daemon():
    """Start self-improve daemon in background thread."""
    try:
        from friday.self_improve_daemon import start_daemon
        daemon_thread = threading.Thread(target=start_daemon, daemon=True, name="self-improve")
        daemon_thread.start()
        pid = os.getpid()
        _touch(os.path.join(FRIDAY_MEMORY, "_daemon_active.flag"), str(pid))
        _log("self-improve daemon started")
        return True
    except Exception as e:
        _log(f"self-improve daemon failed: {e}")
        return False


# ── Service: Dashboard Web API ──

def _start_dashboard_api():
    """Start dashboard web API in background thread."""
    try:
        from friday.dashboard import start_dashboard
        api_thread = threading.Thread(
            target=start_dashboard,
            daemon=True,
            name="dashboard-api",
        )
        api_thread.start()
        _log("dashboard API started (port 8765)")
        return True
    except Exception as e:
        _log(f"dashboard API failed: {e}")
        return False


# ── Service: Periodic Checkpointer ──

def _checkpoint_loop(interval: int = 300):
    """Periodically checkpoint agent state."""
    checkpoint_dir = os.path.join(FRIDAY_MEMORY, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    while True:
        try:
            from friday.persistence import save_checkpoint
            state = {
                "timestamp": datetime.now().isoformat(),
                "pid": os.getpid(),
                "type": "auto_checkpoint",
            }
            filename = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            path = os.path.join(checkpoint_dir, filename)
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
            _log(f"checkpoint saved: {filename}")
        except Exception as e:
            _log(f"checkpoint failed: {e}")

        # Clean old checkpoints (keep last 24)
        try:
            files = sorted([f for f in os.listdir(checkpoint_dir) if f.endswith(".json")])
            while len(files) > 24:
                os.remove(os.path.join(checkpoint_dir, files.pop(0)))
        except Exception:
            pass

        time.sleep(interval)


def _start_checkpointer(interval: int = 300):
    thread = threading.Thread(
        target=_checkpoint_loop,
        args=(interval,),
        daemon=True,
        name="checkpointer",
    )
    thread.start()
    _log(f"checkpointer started (every {interval}s)")
    return thread


# ── Service: Validation Logger Flush ──

def _validation_flush_loop(interval: int = 60):
    """Periodically flush validation log."""
    while True:
        try:
            from friday.validation_middleware import validation_tool
            validation_tool("stats")
        except Exception:
            pass
        time.sleep(interval)


def _start_validation_flusher(interval: int = 60):
    thread = threading.Thread(
        target=_validation_flush_loop,
        args=(interval,),
        daemon=True,
        name="val-flusher",
    )
    thread.start()
    _log("validation flusher started")
    return thread


# ── Bootstrap ──

def start_friday(services: Optional[list[str]] = None) -> dict:
    """Start FRIDAY background services.
    
    services: list of service names to start (default: all)
      - daemon: self-improve daemon
      - dashboard: web API dashboard
      - checkpointer: periodic checkpointing
      - validation: validation log flusher
    
    Returns dict with status of each service.
    """
    if services is None:
        services = ["daemon", "dashboard", "checkpointer", "validation"]

    results = {}
    threads = []

    _log(f"FRIDAY Bootstrap: starting {len(services)} services")

    if "daemon" in services:
        results["daemon"] = _start_daemon()

    if "dashboard" in services:
        results["dashboard"] = _start_dashboard_api()

    if "checkpointer" in services:
        interval = 300
        results["checkpointer"] = bool(_start_checkpointer(interval))

    if "validation" in services:
        interval = 60
        results["validation"] = bool(_start_validation_flusher(interval))

    _log(f"services started: {sum(1 for v in results.values() if v)}/{len(results)}")
    return results


def stop_friday() -> str:
    """Signal FRIDAY background services to stop."""
    daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
    if os.path.exists(daemon_flag):
        try:
            os.remove(daemon_flag)
        except Exception:
            pass
    _log("FRIDAY services stopped")
    return "Services stopped."


def bootstrap_tool(action: str = "start", **kwargs) -> str:
    """FRIDAY Bootstrap — start/stop background services.
    
    Actions:
      start  - Start background services [services: comma-separated list]
      stop   - Stop background services
      status - Show which services are running
    """
    if action == "start":
        svcs = kwargs.get("services", "")
        services = [s.strip() for s in svcs.split(",") if s.strip()] if svcs else None
        result = start_friday(services)
        return json.dumps(result, indent=2)

    elif action == "stop":
        return stop_friday()

    elif action == "status":
        status = {}
        daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
        status["daemon"] = os.path.exists(daemon_flag)

        api_flag = os.path.join(FRIDAY_MEMORY, "_dashboard_active.flag")
        status["dashboard_api"] = os.path.exists(api_flag)

        checkpoint_dir = os.path.join(FRIDAY_MEMORY, "checkpoints")
        if os.path.isdir(checkpoint_dir):
            checkpoints = [f for f in os.listdir(checkpoint_dir) if f.endswith(".json")]
            status["checkpoints"] = len(checkpoints)
        else:
            status["checkpoints"] = 0

        return json.dumps(status, indent=2)

    return f"Unknown action: {action}. Use: start, stop, status"


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    result = bootstrap_tool(action)
    print(result)
