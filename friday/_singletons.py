"""
FRIDAY Runtime State — persisted singleton state for cross-process service management.

All dashboard/CLI/startup code reads and writes state here instead of in-memory
references that die when the process exits. State persists at
friday_memory/runtime_state.json.
"""

from __future__ import annotations
from typing import Dict, Optional, Any
import json
import os
import socket
import time
import urllib.request
import urllib.error

from friday._paths import FRIDAY_MEMORY

RUNTIME_STATE_PATH = os.path.join(FRIDAY_MEMORY, "runtime_state.json")


def _ensure_dir():
    os.makedirs(FRIDAY_MEMORY, exist_ok=True)


def load_runtime_state() -> dict:
    """Load the persisted runtime state."""
    if os.path.exists(RUNTIME_STATE_PATH):
        try:
            with open(RUNTIME_STATE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_runtime_state(state: dict):
    """Save runtime state to disk."""
    _ensure_dir()
    state["_updated_at"] = time.time()
    with open(RUNTIME_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def get_service_state(service: str) -> dict:
    """Get state for a specific service."""
    state = load_runtime_state()
    return state.get(service, {})


def set_service_state(service: str, **fields):
    """Set fields on a service state entry."""
    state = load_runtime_state()
    if service not in state:
        state[service] = {}
    state[service].update(fields)
    state[service]["_updated_at"] = time.time()
    save_runtime_state(state)


def clear_service_state(service: str):
    """Remove a service entry from state."""
    state = load_runtime_state()
    state.pop(service, None)
    save_runtime_state(state)


def clear_all_state():
    """Clear all runtime state."""
    if os.path.exists(RUNTIME_STATE_PATH):
        os.remove(RUNTIME_STATE_PATH)


# ─── HTTP Health Checks ─────────────────────────────────

def check_http_endpoint(url: str, timeout: float = 3.0) -> dict:
    """Check if an HTTP endpoint is reachable."""
    result = {"reachable": False, "status_code": None, "error": None, "latency_ms": 0}
    try:
        start = time.time()
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["reachable"] = True
            result["status_code"] = resp.status
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
    except urllib.error.HTTPError as e:
        # HEAD might not be supported; try GET
        try:
            start = time.time()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result["reachable"] = True
                result["status_code"] = resp.status
            result["latency_ms"] = round((time.time() - start) * 1000, 1)
        except Exception as e2:
            result["error"] = str(e2)
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError, OSError) as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


def check_port_open(host: str, port: int, timeout: float = 2.0) -> dict:
    """Check if a TCP port is open."""
    result = {"open": False, "error": None}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result["open"] = sock.connect_ex((host, port)) == 0
        sock.close()
    except Exception as e:
        result["error"] = str(e)
    return result


def find_free_port(start: int = 8080, max_attempts: int = 20) -> int:
    """Find a free TCP port starting from `start`."""
    for port in range(start, start + max_attempts):
        result = check_port_open("127.0.0.1", port, timeout=0.5)
        if not result["open"]:
            return port
    return start + max_attempts  # Give up, return last


# ─── Townhall Bother/Return Signals ─────────────────────
_BOTHER_FLAG = os.path.join(FRIDAY_MEMORY, "_townhall_bother.flag")
_RETURN_FLAG = os.path.join(FRIDAY_MEMORY, "_townhall_return.flag")

def signal_townhall_bother():
    """Signal: user messaging FRIDAY — she leaves agent chat."""
    _ensure_dir()
    with open(_BOTHER_FLAG, "w") as f:
        f.write(str(time.time()))
    for p in [_RETURN_FLAG]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

def signal_townhall_return():
    """Signal: FRIDAY idle — can return to agent chat."""
    _ensure_dir()
    with open(_RETURN_FLAG, "w") as f:
        f.write(str(time.time()))
    for p in [_BOTHER_FLAG]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

def check_townhall_bother() -> bool:
    return os.path.exists(_BOTHER_FLAG)

def check_townhall_return() -> bool:
    return os.path.exists(_RETURN_FLAG)

def clear_townhall_signals():
    for p in [_BOTHER_FLAG, _RETURN_FLAG]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

# ─── Service Convenience ─────────────────────────────────

def get_dashboard_state() -> dict:
    """Get merged dashboard state (API + UI) with health info."""
    state = get_service_state("dashboard_api")
    ui_state = get_service_state("dashboard_ui")
    health = {}
    if state.get("url"):
        health = check_http_endpoint(state["url"] + "/api/health")
        state["health"] = health.get("reachable", False)
    return {
        "api": state,
        "ui": ui_state,
        "api_healthy": health.get("reachable", False),
        "api_pid": state.get("pid"),
        "ui_pid": ui_state.get("pid"),
        "api_url": state.get("url", "http://127.0.0.1:8090"),
        "ui_url": ui_state.get("url", "http://127.0.0.1:8080"),
    }
