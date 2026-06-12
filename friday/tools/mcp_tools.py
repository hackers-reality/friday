"""
MCP Server Tools — dynamically create and host MCP servers for any API or service.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from typing import Any, Optional

import requests

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("mcp_tools")
MCP_DIR = os.path.join(FRIDAY_MEMORY, "mcp_servers")

# ── Helpers ──

_RUNNING_SERVERS: dict[str, subprocess.Popen] = {}
_LOCK = threading.Lock()


def _ensure_mcp_dir(name: str) -> str:
    server_dir = os.path.join(MCP_DIR, name)
    os.makedirs(server_dir, exist_ok=True)
    return server_dir


def _find_free_port(start: int = 8765, max_attempts: int = 50) -> int:
    for port in range(start, start + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free port found in range {start}-{start + max_attempts}")


def _type_annotation(val: Any) -> str:
    if isinstance(val, str):
        t = str(val)
    else:
        t = str(val)
    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return mapping.get(t, "str")


def _server_script_path(name: str) -> str:
    return os.path.join(MCP_DIR, name, "server.py")


def _status_file_path(name: str) -> str:
    return os.path.join(MCP_DIR, name, "status.json")


def _write_status(name: str, port: int, status: str = "stopped", pid: int = 0) -> None:
    sp = _status_file_path(name)
    data = {"name": name, "port": port, "status": status, "pid": pid, "updated_at": time.time()}
    with open(sp, "w") as f:
        json.dump(data, f)


def _read_status(name: str) -> dict:
    sp = _status_file_path(name)
    if not os.path.isfile(sp):
        return {"name": name, "port": 0, "status": "unknown", "pid": 0}
    with open(sp) as f:
        return json.load(f)


# ── Server Templates ──

_REST_API_TEMPLATE = r'''"""MCP server for {name} — auto-generated from REST API spec."""
from __future__ import annotations

import json
import os
import sys
import requests as _requests
from fastmcp import FastMCP

mcp = FastMCP("{name}")

BASE_URL = {base_url!r}

{endpoint_functions}

if __name__ == "__main__":
    mcp.run(port={port})
'''

_TOOL_SERVER_TEMPLATE = r'''"""MCP server for {name} — auto-generated tool server."""
from __future__ import annotations

import json
import os
import sys
from fastmcp import FastMCP

mcp = FastMCP("{name}")

{tool_functions}

if __name__ == "__main__":
    mcp.run(port={port})
'''

_OPENAPI_TEMPLATE = r'''"""MCP server for {name} — auto-generated from OpenAPI spec."""
from __future__ import annotations

import json
import os
import sys
import requests as _requests
from fastmcp import FastMCP

mcp = FastMCP("{name}")

BASE_URL = {base_url!r}

{endpoint_functions}

if __name__ == "__main__":
    mcp.run(port={port})
'''


# ── 1. mcp_create_rest_api_server ──


async def mcp_create_rest_api_server(
    name: str,
    base_url: str,
    endpoints_json: str,
    port: int = 8765,
) -> dict[str, Any]:
    """Create a complete MCP server that wraps a REST API."""
    try:
        endpoints = json.loads(endpoints_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid endpoints_json: {e}"}

    if not isinstance(endpoints, list) or not endpoints:
        return {"success": False, "error": "endpoints_json must be a non-empty array"}

    server_dir = _ensure_mcp_dir(name)
    port = _find_free_port(port)

    func_lines: list[str] = []
    for ep in endpoints:
        ep_name = ep.get("name", "unknown")
        method = ep.get("method", "GET").upper()
        path = ep.get("path", "/")
        params = ep.get("params", {})
        description = ep.get("description", f"{method} {path}")

        func_params = ", ".join(
            f"{pname}: {_type_annotation(ptype)}" for pname, ptype in params.items()
        )
        arg_refs = ", ".join(
            f"{pname}={pname}" for pname in params
        )

        full_url = base_url.rstrip("/") + path

        if method == "GET":
            body = (
                f'    params_dict = {{k: v for k, v in locals().items() if v is not None}}\n'
                f'    resp = _requests.get(BASE_URL + "{path}", params=params_dict)'
            )
        else:
            body = (
                f'    body_dict = {{k: v for k, v in locals().items() if v is not None}}\n'
                f'    resp = _requests.{method.lower()}(BASE_URL + "{path}", json=body_dict)'
            )

        func_block = f'''
@mcp.tool()
def {ep_name}({func_params}) -> dict:
    """{description}"""
    try:
{textwrap.indent(body, "        ")}
        resp.raise_for_status()
        return resp.json()
    except Exception as _e:
        return {{"error": str(_e)}}
'''
        func_lines.append(func_block)

    source = _REST_API_TEMPLATE.format(
        name=name,
        base_url=base_url,
        port=port,
        endpoint_functions="\n".join(func_lines),
    )

    script_path = os.path.join(server_dir, "server.py")
    with open(script_path, "w") as f:
        f.write(source)

    _write_status(name, port, "created")
    logger.info("Created REST API MCP server '%s' at %s (port %s)", name, server_dir, port)

    return {
        "success": True,
        "server_dir": server_dir,
        "port": port,
        "name": name,
        "start_command": f"python {script_path}",
    }


# ── 2. mcp_list_servers ──


async def mcp_list_servers() -> dict[str, Any]:
    """List all MCP servers in MCP_DIR/."""
    if not os.path.isdir(MCP_DIR):
        return {"success": True, "servers": []}

    servers: list[dict] = []
    for entry in os.listdir(MCP_DIR):
        server_dir = os.path.join(MCP_DIR, entry)
        if not os.path.isdir(server_dir):
            continue
        status_data = _read_status(entry)
        running = await _check_process(status_data.get("pid", 0))
        servers.append({
            "name": entry,
            "port": status_data.get("port", 0),
            "status": "running" if running else status_data.get("status", "stopped"),
            "created_at": os.path.getctime(server_dir),
        })

    return {"success": True, "servers": servers}


# ── 3. mcp_start_server ──


async def mcp_start_server(name: str) -> dict[str, Any]:
    """Start a created MCP server in background subprocess."""
    server_dir = os.path.join(MCP_DIR, name)
    script_path = _server_script_path(name)
    if not os.path.isfile(script_path):
        return {"success": False, "error": f"Server '{name}' not found. Create it first."}

    status_data = _read_status(name)
    port = status_data.get("port", 0)
    if port <= 0:
        port = _find_free_port()
        _write_status(name, port, "created")

    if await _check_port(port):
        pid = status_data.get("pid", 0)
        if pid and await _check_process(pid):
            return {"success": True, "name": name, "port": port, "pid": pid, "message": "already running"}

    log_path = os.path.join(server_dir, "server.log")
    log_file = open(log_path, "a")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=log_file,
            stderr=log_file,
            env=env,
            cwd=server_dir,
        )
    except Exception as e:
        return {"success": False, "error": f"Failed to start server: {e}"}

    _write_status(name, port, "running", proc.pid)
    with _LOCK:
        _RUNNING_SERVERS[name] = proc

    time.sleep(1.5)

    if proc.poll() is not None:
        return {"success": False, "error": f"Server exited prematurely (check {log_path})"}

    logger.info("Started MCP server '%s' on port %s (pid %s)", name, port, proc.pid)
    return {"success": True, "name": name, "port": port, "pid": proc.pid}


# ── 4. mcp_stop_server ──


async def mcp_stop_server(name: str) -> dict[str, Any]:
    """Stop a running MCP server."""
    proc: subprocess.Popen | None = None
    with _LOCK:
        proc = _RUNNING_SERVERS.pop(name, None)

    if proc is None:
        status_data = _read_status(name)
        pid = status_data.get("pid", 0)
        if pid and await _check_process(pid):
            try:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
            except Exception:
                pass
        _write_status(name, status_data.get("port", 0), "stopped", 0)
        return {"success": True, "name": name, "message": "stopped (was not in process table)"}

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass

    _write_status(name, 0, "stopped", 0)
    logger.info("Stopped MCP server '%s'", name)
    return {"success": True, "name": name}


# ── 5. mcp_server_status ──


async def mcp_server_status(name: str) -> dict[str, Any]:
    """Check if server is running, port in use, etc."""
    status_data = _read_status(name)
    port = status_data.get("port", 0)
    pid = status_data.get("pid", 0)

    running = False
    if pid and await _check_process(pid):
        running = True
        if not await _check_port(port):
            running = False

    port_free = not await _check_port(port) if port else True

    return {
        "success": True,
        "running": running,
        "port": port,
        "pid": pid,
        "port_free": port_free,
        "name": name,
        "status": "running" if running else "stopped",
    }


# ── 6. mcp_create_from_openapi_spec ──


async def mcp_create_from_openapi_spec(
    spec_url_or_json: str,
    name: str = "",
) -> dict[str, Any]:
    """Parse an OpenAPI/Swagger spec and auto-generate an MCP server."""
    spec: dict | None = None

    if spec_url_or_json.strip().startswith(("{", "[")):
        try:
            spec = json.loads(spec_url_or_json)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON spec: {e}"}
    elif spec_url_or_json.startswith(("http://", "https://")):
        try:
            resp = requests.get(spec_url_or_json, timeout=30)
            resp.raise_for_status()
            spec = resp.json()
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch spec: {e}"}
    else:
        return {"success": False, "error": "spec must be a URL or a JSON string"}

    if not spec:
        return {"success": False, "error": "Could not parse spec"}

    if not name:
        name = spec.get("info", {}).get("title", "openapi_server")
        name = name.lower().replace(" ", "_").replace("-", "_")

    info = spec.get("info", {})
    base_url = ""
    servers = spec.get("servers", [])
    if servers:
        base_url = servers[0].get("url", "")
    elif "host" in spec:
        scheme = "https" if spec.get("schemes") and "https" in spec["schemes"] else "http"
        base_path = spec.get("basePath", "")
        base_url = f"{scheme}://{spec['host']}{base_path}"

    paths = spec.get("paths", {})
    endpoints: list[dict] = []

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in ("get", "post", "put", "delete", "patch"):
            op = methods.get(method)
            if not op or not isinstance(op, dict):
                continue
            ep_name = op.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
            ep_name = ep_name.replace("-", "_").replace(".", "_").replace("{", "").replace("}", "")
            params: dict[str, str] = {}
            parameters = op.get("parameters", [])
            for p in parameters:
                if isinstance(p, dict):
                    pname = p.get("name", "")
                    ptype = p.get("schema", {}).get("type", "string") if isinstance(p.get("schema"), dict) else "string"
                    if pname:
                        params[pname] = ptype

            if op.get("requestBody"):
                try:
                    content = op["requestBody"].get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        if schema.get("type") == "object" and schema.get("properties"):
                            for pname, pschema in schema["properties"].items():
                                if isinstance(pschema, dict):
                                    params[pname] = pschema.get("type", "string")
                except Exception:
                    pass

            endpoints.append({
                "name": ep_name,
                "method": method.upper(),
                "path": path,
                "params": params,
                "description": op.get("summary", op.get("description", f"{method.upper()} {path}")),
            })

    if not endpoints:
        return {"success": False, "error": "No parseable endpoints found in spec"}

    port = _find_free_port()
    server_dir = _ensure_mcp_dir(name)

    func_lines: list[str] = []
    for ep in endpoints:
        ep_name = ep["name"]
        method = ep["method"]
        path = ep["path"]
        desc = ep["description"]
        ep_params = ep["params"]

        func_params = ", ".join(
            f"{pname}: {_type_annotation(ptype)}" for pname, ptype in ep_params.items()
        )

        if method == "GET":
            body = (
                f'    params_dict = {{k: v for k, v in locals().items() if v is not None}}\n'
                f'    resp = _requests.get(BASE_URL + "{path}", params=params_dict)'
            )
        else:
            body = (
                f'    body_dict = {{k: v for k, v in locals().items() if v is not None}}\n'
                f'    resp = _requests.{method.lower()}(BASE_URL + "{path}", json=body_dict)'
            )

        func_block = f'''
@mcp.tool()
def {ep_name}({func_params}) -> dict:
    """{desc}"""
    try:
{textwrap.indent(body, "        ")}
        resp.raise_for_status()
        return resp.json()
    except Exception as _e:
        return {{"error": str(_e)}}
'''
        func_lines.append(func_block)

    source = _OPENAPI_TEMPLATE.format(
        name=name,
        base_url=base_url,
        port=port,
        endpoint_functions="\n".join(func_lines),
    )

    script_path = os.path.join(server_dir, "server.py")
    with open(script_path, "w") as f:
        f.write(source)

    _write_status(name, port, "created")
    logger.info(
        "Created OpenAPI MCP server '%s' with %s endpoints (port %s)",
        name,
        len(endpoints),
        port,
    )

    return {
        "success": True,
        "name": name,
        "endpoints_count": len(endpoints),
        "server_dir": server_dir,
        "port": port,
    }


# ── 7. mcp_create_tool_server ──


async def mcp_create_tool_server(
    name: str,
    tools_json: str,
    port: int = 8766,
) -> dict[str, Any]:
    """Create an MCP server exposing custom Python tools/functions."""
    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid tools_json: {e}"}

    if not isinstance(tools, list) or not tools:
        return {"success": False, "error": "tools_json must be a non-empty array"}

    server_dir = _ensure_mcp_dir(name)
    port = _find_free_port(port)

    func_lines: list[str] = []
    for tool in tools:
        tname = tool.get("name", "unknown_tool")
        desc = tool.get("description", "")
        params = tool.get("parameters", {})
        code = tool.get("code", "")

        code = textwrap.dedent(code).strip()

        param_list = ", ".join(
            f"{pname}: {_type_annotation(ptype)}" for pname, ptype in params.items()
        )

        func_block = f'''
@mcp.tool()
def {tname}({param_list}) -> dict:
    """{desc}"""
{textwrap.indent(code, "    ")}
'''
        func_lines.append(func_block)

    source = _TOOL_SERVER_TEMPLATE.format(
        name=name,
        port=port,
        tool_functions="\n".join(func_lines),
    )

    script_path = os.path.join(server_dir, "server.py")
    with open(script_path, "w") as f:
        f.write(source)

    _write_status(name, port, "created")
    logger.info("Created tool MCP server '%s' with %s tools (port %s)", name, len(tools), port)

    return {
        "success": True,
        "name": name,
        "tool_count": len(tools),
        "port": port,
        "server_dir": server_dir,
    }


# ── 8. mcp_test_endpoint ──


async def mcp_test_endpoint(
    name: str,
    tool_name: str,
    params_json: str = "{}",
) -> dict[str, Any]:
    """Test a tool/endpoint on a running MCP server."""
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid params_json: {e}"}

    status_data = _read_status(name)
    port = status_data.get("port", 0)
    if not port:
        return {"success": False, "error": f"Server '{name}' has no port configured"}

    if not await _check_port(port):
        return {"success": False, "error": f"Server '{name}' is not running on port {port}"}

    url = f"http://127.0.0.1:{port}/tools/{tool_name}"
    try:
        resp = requests.post(url, json=params, timeout=15)
        resp.raise_for_status()
        return {"success": True, "result": resp.json()}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# ── Internal helpers ──


async def _check_port(port: int) -> bool:
    """Return True if something is listening on the port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


async def _check_process(pid: int) -> bool:
    """Return True if a process with the given pid is running."""
    if not pid or pid <= 0:
        return False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return str(pid) in proc.stdout
    except Exception:
        return False
