"""Friday MCP Bridge — connects FRIDAY to MCP (Model Context Protocol) servers.
Enables extensibility through external MCP servers for tools, resources, and prompts.

Supports stdio and SSE transport, auto-reconnect, and connection pooling.
"""
from __future__ import annotations
import os
import json
import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Callable

from friday._paths import FRIDAY_MEMORY

_MCP_STATE_FILE = os.path.join(FRIDAY_MEMORY, "mcp_bridge.json")

# In-memory caches
_connected_sessions: dict = {}
_connected_tools: dict = {}
_connection_errors: dict = {}
_bridge_lock = threading.Lock()
_reconnect_timers: dict = {}


def _load_state() -> dict:
    if os.path.exists(_MCP_STATE_FILE):
        try:
            with open(_MCP_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"servers": [], "connected": []}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_MCP_STATE_FILE), exist_ok=True)
    try:
        with open(_MCP_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


async def _connect_stdio(name: str, command: str, args: list = None) -> str:
    """Connect to an MCP server via stdio transport."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=command,
        args=args or [],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()

            with _bridge_lock:
                _connected_sessions[name] = session
                tools_list = []
                for tool in tools_result.tools:
                    tools_list.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    })
                _connected_tools[name] = tools_list
                _connection_errors.pop(name, None)

            state = _load_state()
            entry = next((s for s in state.get("connected", []) if s["name"] == name), None)
            if entry:
                entry.update({"command": command, "args": args or [],
                              "connected_at": datetime.now().isoformat(),
                              "tools": len(tools_list), "transport": "stdio"})
            else:
                state.setdefault("connected", []).append({
                    "name": name, "command": command, "args": args or [],
                    "connected_at": datetime.now().isoformat(),
                    "tools": len(tools_list), "transport": "stdio",
                })
            _save_state(state)

            return f"[OK] Connected to MCP server '{name}' (stdio): {len(tools_list)} tools available."


async def _connect_sse(name: str, url: str) -> str:
    """Connect to an MCP server via SSE transport."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()

            with _bridge_lock:
                _connected_sessions[name] = session
                tools_list = []
                for tool in tools_result.tools:
                    tools_list.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    })
                _connected_tools[name] = tools_list
                _connection_errors.pop(name, None)

            state = _load_state()
            entry = next((s for s in state.get("connected", []) if s["name"] == name), None)
            if entry:
                entry.update({"url": url, "connected_at": datetime.now().isoformat(),
                              "tools": len(tools_list), "transport": "sse"})
            else:
                state.setdefault("connected", []).append({
                    "name": name, "url": url,
                    "connected_at": datetime.now().isoformat(),
                    "tools": len(tools_list), "transport": "sse",
                })
            _save_state(state)

            return f"[OK] Connected to MCP server '{name}' (SSE): {len(tools_list)} tools available."


async def _attempt_reconnect(name: str, config: dict):
    """Attempt to reconnect a disconnected MCP server."""
    transport = config.get("transport", "stdio")
    try:
        if transport == "sse":
            result = await _connect_sse(name, config.get("url", ""))
        else:
            result = await _connect_stdio(name, config.get("command", ""), config.get("args", []))
        return result
    except Exception as e:
        return f"[FAIL] Reconnect failed for '{name}': {e}"


async def _call_tool_async(server_name: str, tool_name: str, arguments: dict = None) -> str:
    """Call a tool on a connected MCP server."""
    with _bridge_lock:
        session = _connected_sessions.get(server_name)
    if not session:
        # Try reconnecting
        state = _load_state()
        config = next((s for s in state.get("connected", []) if s["name"] == server_name), None)
        if config:
            result = await _attempt_reconnect(server_name, config)
            if "[OK]" not in result:
                return f"[FAIL] MCP server '{server_name}' not connected. Reconnect failed."
            with _bridge_lock:
                session = _connected_sessions.get(server_name)
        if not session:
            return f"[FAIL] MCP server '{server_name}' not connected. Use mcp_tool connect first."

    try:
        result = await session.call_tool(tool_name, arguments or {})
        if hasattr(result, 'content'):
            texts = []
            for item in result.content:
                if hasattr(item, 'text'):
                    texts.append(item.text)
                else:
                    texts.append(str(item))
            return "\n".join(texts) if texts else "[OK] Tool completed (no text output)."
        return str(result)
    except Exception as e:
        with _bridge_lock:
            _connection_errors[server_name] = str(e)
        return f"[FAIL] MCP tool error on '{server_name}/{tool_name}': {e}"


def _call_tool_sync(server_name: str, tool_name: str, arguments: dict = None) -> str:
    """Synchronous wrapper for calling an MCP tool."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _call_tool_async(server_name, tool_name, arguments)
        )
        loop.close()
        return result
    except Exception as e:
        return f"[FAIL] MCP call error: {e}"


def mcp_tool(action: str = "list", **kwargs) -> str:
    """MCP bridge: connect to external MCP servers for extensibility.
    Actions:
      list — show configured servers and their tools
      connect — add a stdio server (command='npx', args='-y @modelcontextprotocol/server-filesystem')
      connect_sse — add an SSE server (url='http://localhost:8000/sse')
      disconnect (name) — remove a server
      call (server, tool, params='{}') — invoke a tool
      clean — disconnect all servers
      status — detailed health of all connections
    """
    if action == "list":
        state = _load_state()
        connected = state.get("connected", [])
        if not connected and not _connected_tools:
            return ("No MCP servers configured. Examples:\n"
                    "  mcp_tool action=connect name=filesystem command=npx "
                    "args='-y @modelcontextprotocol/server-filesystem'\n"
                    "  mcp_tool action=connect_sse name=my-server url='http://localhost:8000/sse'")

        lines = ["### MCP SERVERS"]
        for s in connected:
            name = s["name"]
            with _bridge_lock:
                status = "CONNECTED" if name in _connected_sessions else "DISCONNECTED"
            errors = _connection_errors.get(name, "")
            transport = s.get("transport", "stdio")
            lines.append(f"  {name} ({transport}) — {status}{' ['+errors+']' if errors else ''}")
            if status == "CONNECTED":
                tools = _connected_tools.get(name, [])
                for t in tools[:5]:
                    lines.append(f"    - {t.get('name', '?')}: {t.get('description', '')[:80]}")
                if len(tools) > 5:
                    lines.append(f"    ... and {len(tools)-5} more")
        return "\n".join(lines)

    elif action == "connect":
        name = kwargs.get("name", "")
        command = kwargs.get("command", "")
        args_str = kwargs.get("args", "")
        if not name or not command:
            return "[FAIL] Server name and command are required."
        args_list = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_connect_stdio(name, command, args_list))
            loop.close()
            return result
        except Exception as e:
            return f"[FAIL] Connection error: {e}"

    elif action == "connect_sse":
        name = kwargs.get("name", "")
        url = kwargs.get("url", "")
        if not name or not url:
            return "[FAIL] Server name and URL are required."
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_connect_sse(name, url))
            loop.close()
            return result
        except Exception as e:
            return f"[FAIL] SSE connection error: {e}"

    elif action == "disconnect":
        name = kwargs.get("name", "")
        with _bridge_lock:
            _connected_sessions.pop(name, None)
            _connected_tools.pop(name, None)
            _connection_errors.pop(name, None)
        state = _load_state()
        state["connected"] = [s for s in state.get("connected", []) if s.get("name") != name]
        _save_state(state)
        return f"[OK] Disconnected from '{name}'."

    elif action == "call":
        server = kwargs.get("server", "")
        tool = kwargs.get("tool", "")
        params_str = kwargs.get("params", "{}")
        if not server or not tool:
            return "[FAIL] Server and tool name required."
        try:
            params = json.loads(params_str) if params_str else {}
        except json.JSONDecodeError:
            return f"[FAIL] Invalid JSON params: {params_str}"
        return _call_tool_sync(server, tool, params)

    elif action == "clean":
        with _bridge_lock:
            _connected_sessions.clear()
            _connected_tools.clear()
            _connection_errors.clear()
        state = _load_state()
        state["connected"] = []
        _save_state(state)
        return "[OK] All MCP servers disconnected."

    elif action == "status":
        lines = ["### MCP BRIDGE STATUS"]
        lines.append(f"**Connected servers**: {len(_connected_sessions)}")
        lines.append(f"**Total tools available**: {sum(len(t) for t in _connected_tools.values())}")
        for name in _connected_sessions:
            tools = _connected_tools.get(name, [])
            err = _connection_errors.get(name, "")
            lines.append(f"  - {name}: {len(tools)} tools{' [error: '+err+']' if err else ''}")
        return "\n".join(lines)

    elif action == "reconnect":
        """Reconnect all disconnected servers from saved state."""
        state = _load_state()
        results = []
        for s in state.get("connected", []):
            name = s["name"]
            with _bridge_lock:
                if name not in _connected_sessions:
                    result, _ = asyncio.run(_attempt_reconnect(name, s))
                    results.append(f"{name}: {result}")
        return "\n".join(results) if results else "[OK] All servers already connected."

    else:
        return f"[FAIL] Unknown action: {action}. Use: list, connect, connect_sse, disconnect, call, clean, status, reconnect"
