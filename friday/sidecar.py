"""
Friday Sidecar System — registrable, heartbeated, capability-reporting subprocesses.

Sidecars are helper processes that extend FRIDAY's reach:
- Desktop automation helpers
- Browser automation daemons
- Filesystem watchers
- System monitors
- Code workspace agents
- Smart home bridges
- Mobile/cloud placeholder connections
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import copy

from friday._paths import FRIDAY_MEMORY

_SIDECARS_FILE = os.path.join(FRIDAY_MEMORY, "sidecars.json")

SIDECAR_TYPES = {
    "desktop": "Desktop automation helper",
    "browser": "Browser automation daemon",
    "filesystem": "Filesystem watcher",
    "system_monitor": "System performance monitor",
    "code_workspace": "Code workspace agent",
    "smart_home": "Smart home bridge",
    "mobile_placeholder": "Mobile device placeholder",
    "cloud_placeholder": "Cloud service placeholder",
}


def _load_sidecars() -> dict:
    """Load the sidecars registry from disk."""
    if os.path.exists(_SIDECARS_FILE):
        try:
            with open(_SIDECARS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sidecars": [], "next_id": 1}


def _save_sidecars(data: dict) -> None:
    """Save the sidecars registry to disk."""
    os.makedirs(os.path.dirname(_SIDECARS_FILE), exist_ok=True)
    with open(_SIDECARS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def register_sidecar(
    name: str,
    sidecar_type: str,
    endpoint: str = "",
    host: str = "localhost",
    port: int = 0,
    capabilities: list = None,
    metadata: dict = None,
) -> dict:
    """
    Register a new sidecar in the registry.

    Args:
        name: Human-readable name (e.g., "desktop-agent-1").
        sidecar_type: One of SIDECAR_TYPES keys.
        endpoint: URL or pipe name for communication.
        host: Host address.
        port: Port number.
        capabilities: List of capability strings (e.g., ["click", "type", "screenshot"]).
        metadata: Additional freeform metadata.

    Returns:
        dict with "id", "name", "status" etc.
    """
    if sidecar_type not in SIDECAR_TYPES:
        return {"error": f"Unknown sidecar type '{sidecar_type}'. Valid: {', '.join(SIDECAR_TYPES.keys())}"}

    data = _load_sidecars()
    sidecar_id = data["next_id"]
    data["next_id"] += 1

    entry = {
        "id": sidecar_id,
        "name": name,
        "type": sidecar_type,
        "endpoint": endpoint,
        "host": host,
        "port": port,
        "capabilities": capabilities or [],
        "metadata": metadata or {},
        "status": "registered",
        "first_seen": datetime.now().isoformat(),
        "last_heartbeat": "",
        "logs": [],
    }

    data["sidecars"].append(entry)
    _save_sidecars(data)
    return {"success": True, "id": sidecar_id, "name": name}


def heartbeat_sidecar(sidecar_id: int, status: str = "alive", log: str = "") -> dict:
    """
    Record a heartbeat from a sidecar.

    Args:
        sidecar_id: Sidecar ID.
        status: "alive", "busy", "error", or "shutdown".
        log: Optional log message.

    Returns:
        dict with success/error.
    """
    data = _load_sidecars()
    for entry in data["sidecars"]:
        if entry["id"] == sidecar_id:
            entry["last_heartbeat"] = datetime.now().isoformat()
            entry["status"] = status
            if log:
                entry.setdefault("logs", []).append({
                    "timestamp": entry["last_heartbeat"],
                    "message": log,
                })
                # Keep only last 100 logs
                if len(entry["logs"]) > 100:
                    entry["logs"] = entry["logs"][-100:]
            _save_sidecars(data)
            return {"success": True, "id": sidecar_id, "status": status}
    return {"error": f"Sidecar {sidecar_id} not found"}


def list_sidecars(include_logs: bool = False) -> list:
    """List all registered sidecars, sorted by first_seen desc."""
    data = _load_sidecars()
    result = sorted(data["sidecars"], key=lambda x: x.get("first_seen", ""), reverse=True)
    if not include_logs:
        for r in result:
            r.pop("logs", None)
    return result


def sidecar_status(sidecar_id: int) -> Optional[dict]:
    """Get the status of a specific sidecar."""
    data = _load_sidecars()
    for entry in data["sidecars"]:
        if entry["id"] == sidecar_id:
            return dict(entry)
    return None


def dispatch_sidecar_command(sidecar_id: int, command: str, params: dict = None) -> dict:
    """
    Dispatch a command to a sidecar.

    For local sidecars (endpoint empty), tries to execute locally.
    For remote sidecars (endpoint set), would send over network.

    Args:
        sidecar_id: Sidecar ID.
        command: Command string (e.g., "exec", "ping", "shutdown").
        params: Optional parameters.

    Returns:
        dict with result or error.
    """
    data = _load_sidecars()
    entry = None
    for e in data["sidecars"]:
        if e["id"] == sidecar_id:
            entry = e
            break

    if not entry:
        return {"error": f"Sidecar {sidecar_id} not found"}

    if entry["status"] == "shutdown":
        return {"error": f"Sidecar {sidecar_id} is shut down"}

    # Remote dispatch placeholder
    if entry.get("endpoint"):
        return {"info": f"Remote dispatch to {entry['endpoint']} - not yet implemented", "command": command, "params": params}

    # Local dispatch placeholder
    return {"info": f"Local dispatch to {entry['name']} - not yet implemented", "command": command, "params": params}


def sidecar_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool for sidecar management.
    Actions: status, list, register, heartbeat, info, dispatch.
    """
    if action == "status":
        sidecars = list_sidecars()
        alive = sum(1 for s in sidecars if s.get("status") in ("alive", "busy"))
        return (
            f"### SIDECAR STATUS\n\n"
            f"Total sidecars: {len(sidecars)}\n"
            f"Alive: {alive}\n"
            f"Types: {', '.join(SIDECAR_TYPES.keys())}"
        )

    if action == "list":
        sidecars = list_sidecars()
        if not sidecars:
            return "[OK] No sidecars registered."
        lines = ["### SIDECARS\n"]
        for s in sidecars:
            hb = s.get("last_heartbeat", "")[:19] if s.get("last_heartbeat") else "never"
            lines.append(
                f"  [{s['id']}] {s.get('name','?')} ({s.get('type','?')}) "
                f"- {s.get('status','?')} - last HB: {hb}"
            )
        return "\n".join(lines)

    if action == "register":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name' for the sidecar."
        stype = kwargs.get("type", "")
        if stype and stype not in SIDECAR_TYPES:
            return f"[FAIL] Unknown type '{stype}'. Valid: {', '.join(SIDECAR_TYPES.keys())}"
        endpoint = kwargs.get("endpoint", "")
        capabilities = kwargs.get("capabilities", [])
        if isinstance(capabilities, str):
            capabilities = [c.strip() for c in capabilities.split(",")]

        result = register_sidecar(name, stype or "desktop", endpoint=endpoint, capabilities=capabilities)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Sidecar #{result['id']} '{result['name']}' registered."

    if action == "heartbeat":
        sid = kwargs.get("id", None)
        if sid is None:
            return "[FAIL] Provide 'id'."
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        status = kwargs.get("status", "alive")
        log_msg = kwargs.get("log", "")
        result = heartbeat_sidecar(sid, status=status, log=log_msg)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Sidecar #{sid} heartbeat: {status}"

    if action == "info":
        sid = kwargs.get("id", None)
        if sid is None:
            return "[FAIL] Provide 'id'."
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        s = sidecar_status(sid)
        if not s:
            return f"[FAIL] Sidecar #{sid} not found."
        lines = [f"### SIDECAR #{sid}\n"]
        for k, v in s.items():
            if k == "logs":
                lines.append(f"  logs: {len(v)} entries")
            elif isinstance(v, (dict, list)):
                lines.append(f"  {k}: {json.dumps(v, default=str)[:100]}")
            else:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    if action == "dispatch":
        sid = kwargs.get("id", None)
        if sid is None:
            return "[FAIL] Provide 'id'."
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        command = kwargs.get("command", "")
        if not command:
            return "[FAIL] Provide 'command'."
        result = dispatch_sidecar_command(sid, command, kwargs.get("params"))
        return json.dumps(result, default=str)

    return f"[FAIL] Unknown action: {action}. Available: status, list, register, heartbeat, info, dispatch"
