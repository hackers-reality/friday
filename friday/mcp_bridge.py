"""Friday MCP Bridge — connects FRIDAY to MCP (Model Context Protocol) servers.
Enables extensibility through external MCP servers for tools, resources, and prompts."""

from __future__ import annotations
import os
import json
import asyncio
import threading
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_MCP_STATE_FILE = os.path.join(FRIDAY_MEMORY, "mcp_bridge.json")


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


# In-memory cache of connected sessions and tools
_connected_sessions: dict = {}
_connected_tools: dict = {}
_bridge_lock = threading.Lock()


async def _connect_server(name: str, command: str, args: list = None) -> str:
    """Connect to an MCP server via stdio."""
    try:
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

                state = _load_state()
                if name not in [s["name"] for s in state.get("connected", [])]:
                    state.setdefault("connected", []).append({
                        "name": name,
                        "command": command,
                        "args": args or [],
                        "connected_at": datetime.now().isoformat(),
                        "tools": len(tools_list),
                    })
                _save_state(state)

                return f"[OK] Connected to MCP server '{name}': {len(tools_list)} tools available."

    except ImportError:
        return "[FAIL] MCP SDK not installed. Run: pip install mcp"
    except Exception as e:
        return f"[FAIL] Could not connect to '{name}': {e}"


async def _call_tool_async(server_name: str, tool_name: str, arguments: dict = None) -> str:
    """Call a tool on an MCP server."""
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
        return f"[FAIL] MCP tool error: {e}"


def _call_tool_sync(server_name: str, tool_name: str, arguments: dict = None) -> str:
    """Synchronous wrapper for calling an MCP tool."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_call_tool_async(server_name, tool_name, arguments))
        loop.close()
        return result
    except Exception as e:
        return f"[FAIL] MCP call error: {e}"


def mcp_tool(action: str = "list", **kwargs) -> str:
    """MCP bridge: connect to external MCP servers for extensibility.
    Actions: list (show servers + tools), connect (add server), disconnect (remove), call (invoke tool)."""
    if action == "list":
        state = _load_state()
        connected = state.get("connected", [])
        if not connected and not _connected_tools:
            return "No MCP servers configured. Use 'connect' to add a server (e.g., command='npx', args='-y @modelcontextprotocol/server-filesystem')."

        lines = ["### MCP SERVERS"]
        for s in connected:
            status = "CONNECTED" if s["name"] in _connected_tools else "DISCONNECTED"
            lines.append(f"  {s['name']} ({s.get('command','')}) — {status} — {s.get('tools', 0)} tools")
            tools = _connected_tools.get(s["name"], [])
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
            result = loop.run_until_complete(_connect_server(name, command, args_list))
            loop.close()
            return result
        except Exception as e:
            return f"[FAIL] Connection error: {e}"

    elif action == "disconnect":
        name = kwargs.get("name", "")
        with _bridge_lock:
            if name in _connected_sessions:
                del _connected_sessions[name]
            if name in _connected_tools:
                del _connected_tools[name]
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
        """Disconnect all servers."""
        with _bridge_lock:
            _connected_sessions.clear()
            _connected_tools.clear()
        state = _load_state()
        state["connected"] = []
        _save_state(state)
        return "[OK] All MCP servers disconnected."

    else:
        return f"[FAIL] Unknown action: {action}"
