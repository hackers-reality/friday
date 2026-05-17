"""
FRIDAY Extension & MCP Registry — manage extension servers, MCP tool providers,
health checks, and capability discovery.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

from friday._paths import FRIDAY_CONFIG

_REGISTRY_PATH = os.path.join(FRIDAY_CONFIG, "extension_registry.json")
_lock = threading.Lock()


# ─── Extension Types ─────────────────────────────────────

EXTENSION_TYPES = {
    "mcp": "Model Context Protocol server — provides tools/resources to LLM",
    "tool": "Standalone tool plugin — exposes executable or script",
    "bridge": "External service bridge — connects to REST/gRPC/WebSocket API",
    "hook": "Event hook — reacts to FRIDAY lifecycle events",
    "adapter": "Provider adapter — adapts a new LLM provider",
}


@dataclass
class ExtensionEntry:
    name: str
    type: str
    endpoint: str
    enabled: bool = True
    description: str = ""
    version: str = "0.1.0"
    capabilities: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    health_status: str = "unknown"
    health_last_checked: str = ""
    added_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def _now() -> str:
    return datetime.now().isoformat()[:19]


def _load_registry() -> dict:
    if os.path.exists(_REGISTRY_PATH):
        with open(_REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {"extensions": {}, "mcp_servers": {}, "version": 1, "updated_at": _now()}


def _save_registry(reg: dict):
    reg["updated_at"] = _now()
    os.makedirs(FRIDAY_CONFIG, exist_ok=True)
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(reg, f, indent=2)


# ─── MCP Server Management ───────────────────────────────

def register_mcp_server(name: str, command: str, args: Optional[List[str]] = None,
                        env: Optional[Dict[str, str]] = None,
                        description: str = "") -> str:
    """Register an MCP server (stdio-based, launched as subprocess)."""
    reg = _load_registry()
    if name in reg.get("mcp_servers", {}):
        return f"[FAIL] MCP server '{name}' already registered. Use update_mcp_server to modify."

    entry = {
        "name": name,
        "command": command,
        "args": args or [],
        "env": env or {},
        "description": description,
        "enabled": True,
        "health_status": "unknown",
        "health_last_checked": "",
        "added_at": _now(),
        "updated_at": _now(),
    }
    reg.setdefault("mcp_servers", {})[name] = entry
    _save_registry(reg)
    return f"[OK] MCP server '{name}' registered"


def update_mcp_server(name: str, **updates) -> str:
    """Update an MCP server registration."""
    reg = _load_registry()
    servers = reg.get("mcp_servers", {})
    if name not in servers:
        return f"[FAIL] MCP server '{name}' not found"

    for key in ("command", "args", "env", "description", "enabled"):
        if key in updates:
            servers[name][key] = updates[key]
    servers[name]["updated_at"] = _now()
    _save_registry(reg)
    return f"[OK] MCP server '{name}' updated"


def remove_mcp_server(name: str) -> str:
    """Remove an MCP server registration."""
    reg = _load_registry()
    servers = reg.get("mcp_servers", {})
    if name not in servers:
        return f"[FAIL] MCP server '{name}' not found"
    del servers[name]
    _save_registry(reg)
    return f"[OK] MCP server '{name}' removed"


def list_mcp_servers() -> List[dict]:
    reg = _load_registry()
    return list(reg.get("mcp_servers", {}).values())


def check_mcp_server_health(name: str, timeout: float = 5.0) -> dict:
    """Ping an MCP server process."""
    reg = _load_registry()
    servers = reg.get("mcp_servers", {})
    entry = servers.get(name)
    if not entry:
        return {"name": name, "status": "not_found", "error": "Not registered"}

    result = {"name": name, "status": "unknown", "pid": None, "error": None}

    if not entry.get("enabled", True):
        result["status"] = "disabled"
        return result

    command = entry.get("command", "")
    try:
        proc = subprocess.Popen(
            [command] + entry.get("args", []),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, **(entry.get("env") or {})},
        )
        proc.poll()
        if proc.returncode is None:
            result["status"] = "running"
            result["pid"] = proc.pid
        elif proc.returncode == 0:
            result["status"] = "exited_ok"
        else:
            result["status"] = "exited_error"
            result["error"] = f"Exit code {proc.returncode}"
    except FileNotFoundError:
        result["status"] = "not_found"
        result["error"] = f"Command not found: {command}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    # Update registry
    reg["mcp_servers"][name]["health_status"] = result["status"]
    reg["mcp_servers"][name]["health_last_checked"] = _now()
    _save_registry(reg)

    return result


# ─── Extension Management ────────────────────────────────

def register_extension(name: str, ext_type: str, endpoint: str,
                       description: str = "", capabilities: Optional[List[str]] = None,
                       env_vars: Optional[Dict[str, str]] = None) -> str:
    """Register a new extension."""
    if ext_type not in EXTENSION_TYPES:
        types_list = ", ".join(EXTENSION_TYPES.keys())
        return f"[FAIL] Unknown type '{ext_type}'. Valid: {types_list}"

    reg = _load_registry()
    extensions = reg.get("extensions", {})
    if name in extensions:
        return f"[FAIL] Extension '{name}' already registered"

    entry = ExtensionEntry(
        name=name,
        type=ext_type,
        endpoint=endpoint,
        description=description or EXTENSION_TYPES.get(ext_type, ""),
        capabilities=capabilities or [],
        env_vars=env_vars or {},
        added_at=_now(),
    )
    extensions[name] = {
        "name": entry.name,
        "type": entry.type,
        "endpoint": entry.endpoint,
        "enabled": entry.enabled,
        "description": entry.description,
        "version": entry.version,
        "capabilities": entry.capabilities,
        "env_vars": entry.env_vars,
        "health_status": entry.health_status,
        "health_last_checked": entry.health_last_checked,
        "added_at": entry.added_at,
        "metadata": entry.metadata,
    }
    _save_registry(reg)
    return f"[OK] Extension '{name}' ({ext_type}) registered at {endpoint}"


def update_extension(name: str, **updates) -> str:
    """Update an extension registration."""
    reg = _load_registry()
    exts = reg.get("extensions", {})
    if name not in exts:
        return f"[FAIL] Extension '{name}' not found"

    allowed = ("type", "endpoint", "enabled", "description", "version", "capabilities", "env_vars", "metadata")
    for key, val in updates.items():
        if key in allowed:
            exts[name][key] = val
    _save_registry(reg)
    return f"[OK] Extension '{name}' updated"


def remove_extension(name: str) -> str:
    """Remove an extension."""
    reg = _load_registry()
    exts = reg.get("extensions", {})
    if name not in exts:
        return f"[FAIL] Extension '{name}' not found"
    del exts[name]
    _save_registry(reg)
    return f"[OK] Extension '{name}' removed"


def list_extensions(ext_type: Optional[str] = None) -> List[dict]:
    reg = _load_registry()
    exts = reg.get("extensions", {})
    result = []
    for name, entry in exts.items():
        if ext_type and entry.get("type") != ext_type:
            continue
        result.append(entry)
    return result


def check_extension_health(name: str, timeout: float = 5.0) -> dict:
    """Check if an extension endpoint is reachable."""
    reg = _load_registry()
    exts = reg.get("extensions", {})
    entry = exts.get(name)
    if not entry:
        return {"name": name, "status": "not_found", "error": "Not registered"}

    result = {"name": name, "status": "unknown", "error": None, "latency_ms": 0}

    if not entry.get("enabled", True):
        result["status"] = "disabled"
        return result

    endpoint = entry.get("endpoint", "")
    start = time.time()
    try:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            req = urllib.request.Request(endpoint, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result["status"] = "ok" if resp.status < 500 else "error"
                result["status_code"] = resp.status
        else:
            host, port_str = endpoint.split(":")
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            result["status"] = "ok"
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError, OSError) as e:
        result["status"] = "error"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    finally:
        result["latency_ms"] = round((time.time() - start) * 1000, 1)

    # Update registry
    reg["extensions"][name]["health_status"] = result["status"]
    reg["extensions"][name]["health_last_checked"] = _now()
    _save_registry(reg)

    return result


def health_all_extensions() -> List[dict]:
    reg = _load_registry()
    results = []
    for name in reg.get("extensions", {}):
        results.append(check_extension_health(name))
    for name in reg.get("mcp_servers", {}):
        results.append(check_mcp_server_health(name))
    return results


# ─── Capability Discovery ────────────────────────────────

def discover_capabilities(query: str = "") -> List[dict]:
    """Search across all extensions for a capability."""
    reg = _load_registry()
    results = []
    query_lower = query.lower()

    for name, entry in reg.get("extensions", {}).items():
        caps = [c.lower() for c in entry.get("capabilities", [])]
        if not query_lower or any(query_lower in c for c in caps):
            results.append({
                "name": name,
                "type": "extension",
                "endpoint": entry.get("endpoint"),
                "capabilities": entry.get("capabilities", []),
                "enabled": entry.get("enabled", True),
                "health_status": entry.get("health_status", "unknown"),
            })

    for name, entry in reg.get("mcp_servers", {}).items():
        if not query_lower:
            results.append({
                "name": name,
                "type": "mcp_server",
                "command": entry.get("command"),
                "enabled": entry.get("enabled", True),
                "health_status": entry.get("health_status", "unknown"),
            })

    return results


# ─── Tool Function ───────────────────────────────────────

def extension_registry_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: Extension & MCP Registry — manage extension servers, tools, and bridges.

    Actions:
        status                - Show registry overview
        register_extension    - Register a new extension
        update_extension      - Update an existing extension
        remove_extension      - Remove an extension
        list_extensions       - List all extensions (optionally filter by type)
        register_mcp          - Register an MCP server
        update_mcp            - Update an MCP server
        remove_mcp            - Remove an MCP server
        list_mcp              - List all MCP servers
        health                - Run health checks on all extensions + MCP servers
        discover              - Search for capabilities across extensions
    """
    action = action.lower()

    if action == "status":
        reg = _load_registry()
        exts = reg.get("extensions", {})
        servers = reg.get("mcp_servers", {})
        enabled_exts = sum(1 for e in exts.values() if e.get("enabled"))
        enabled_svrs = sum(1 for s in servers.values() if s.get("enabled"))
        return (
            f"### EXTENSION & MCP REGISTRY\n\n"
            f"Extensions: {len(exts)} registered ({enabled_exts} enabled)\n"
            f"MCP Servers: {len(servers)} registered ({enabled_svrs} enabled)\n"
            f"Types available: {', '.join(EXTENSION_TYPES.keys())}\n"
            f"Last updated: {reg.get('updated_at', 'never')}\n"
            f"Registry path: {_REGISTRY_PATH}"
        )

    if action == "register_extension":
        return register_extension(
            name=kwargs.get("name", ""),
            ext_type=kwargs.get("type", kwargs.get("ext_type", "")),
            endpoint=kwargs.get("endpoint", ""),
            description=kwargs.get("description", ""),
            capabilities=kwargs.get("capabilities"),
            env_vars=kwargs.get("env_vars"),
        )

    if action == "update_extension":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name'"
        updates = {k: v for k, v in kwargs.items() if k != "action" and k != "name"}
        return update_extension(name, **updates)

    if action == "remove_extension":
        return remove_extension(kwargs.get("name", ""))

    if action == "list_extensions":
        ext_type = kwargs.get("type")
        exts = list_extensions(ext_type)
        if not exts:
            return "[OK] No extensions registered."
        lines = ["### Extensions\n"]
        for e in exts:
            status = "ENABLED" if e.get("enabled") else "DISABLED"
            lines.append(f"- **{e['name']}** ({e.get('type')}) — {e.get('endpoint')} [{status}]")
            if e.get("capabilities"):
                lines[-1] += f"\n  capabilities: {', '.join(e['capabilities'][:5])}"
        return "\n".join(lines)

    if action == "register_mcp":
        return register_mcp_server(
            name=kwargs.get("name", ""),
            command=kwargs.get("command", ""),
            args=kwargs.get("args"),
            env=kwargs.get("env"),
            description=kwargs.get("description", ""),
        )

    if action == "update_mcp":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name'"
        updates = {k: v for k, v in kwargs.items() if k != "action" and k != "name"}
        return update_mcp_server(name, **updates)

    if action == "remove_mcp":
        return remove_mcp_server(kwargs.get("name", ""))

    if action == "list_mcp":
        servers = list_mcp_servers()
        if not servers:
            return "[OK] No MCP servers registered."
        lines = ["### MCP Servers\n"]
        for s in servers:
            status = "ENABLED" if s.get("enabled") else "DISABLED"
            lines.append(f"- **{s['name']}** — `{s.get('command')} {' '.join(s.get('args', []))}` [{status}]")
        return "\n".join(lines)

    if action == "health":
        results = health_all_extensions()
        if not results:
            return "[OK] Nothing to check."
        lines = ["### Health Check Results\n"]
        ok_count = sum(1 for r in results if r.get("status") == "ok")
        for r in results:
            sym = "OK" if r["status"] == "ok" else ("DIS" if r["status"] == "disabled" else "ERR")
            lines.append(f"- {r['name']}: {sym} ({r.get('latency_ms', '?')}ms)")
            if r.get("error"):
                lines[-1] += f" — {r['error']}"
        return "\n".join(lines)

    if action == "discover":
        query = kwargs.get("query", "")
        results = discover_capabilities(query)
        if not results:
            return f"[OK] No capabilities found matching '{query}'."
        lines = [f"### Capability Discovery: '{query}' ({len(results)} results)\n"]
        for r in results:
            lines.append(f"- **{r['name']}** ({r['type']})")
            if r.get("capabilities"):
                lines[-1] += f": {', '.join(r['capabilities'][:4])}"
            lines[-1] += f" — {r.get('health_status', 'unknown')}"
        return "\n".join(lines)

    return f"[FAIL] Unknown action: {action}"
