"""
Friday MCP Server - Phase 6.2 Enhanced
Expose Friday's tools via Model Context Protocol.
Extended with browser history, file generation, goal management.
"""
from __future__ import annotations__

import os
import sys'
import json'
from typing import Dict, Any, List, Optional'

try:
    from mcp import Server, Tool, types
    from mcp.server.stdio import stdio_server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP not available. Install: pip install mcp")

# ─── Import Friday Tools ────────────────────────────────#

if MCP_AVAILABLE:
    try:
        from friday_tools import (
            get_time, system_info, run_cmd, safe_run_cmd,
            read_file, write_file, list_files, find_files,
            copy_file, move_file, delete_file,
            clipboard_get, clipboard_set,
            click, double_click, right_click, move_mouse, drag,
            hotkey, press_key, scroll,
            open_app, open_url, spotify_play, spotify_pause,
            web_search, stark_doctor, git_ops,
            see_screen, search_browser_history, open_history_item,
            list_recent_history, generate_file, generate_file_llm,
            situational_awareness, goals_tool_handler, startup_tool_handler,
        )
        print("✅ Friday tools imported for MCP")
    except Exception as e:
        print(f"❌ Friday tools import error: {e}")

# ─── MCP Server Setup ────────────────────────────────#

def create_mcp_server() -> Optional[Server]:
    """Create and configure the MCP server."""
    if not MCP_AVAILABLE:
        return None

    server = Server("friday-mcp-server")

    # ─── Tool Definitions ──────────────#

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List all available tools."""
        return [
            Tool(
                name="get_time",
                description="Get current date and time.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="system_info",
                description="Get system information.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="run_cmd",
                description="Run a shell command.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"},
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="read_file",
                description="Read a file from disk.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="write_file",
                description="Write content to a file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                        "content": {"type": "string", "description": "Content to write"},
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="see_screen",
                description="Analyze the current screen and active window.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Optional question about screen"},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="search_browser_history",
                description="Search browser history across Chrome, Edge, Brave, Opera.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "days_back": {"type": "integer", "description": "Days to look back"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="open_history_item",
                description="Find and open the most recent browser history item matching query.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search for"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="generate_file",
                description="Generate any type of file (code, docs, config, etc.).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Output file path"},
                        "file_type": {"type": "string", "description": "File type or 'auto'"},
                        "description": {"type": "string", "description": "File description"},
                        "content": {"type": "string", "description": "Direct content (optional)"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="goals_tool_handler",
                description="Manage goals: add, list, complete, enforce, sync_calendar.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action: add, list, complete, enforce, sync_calendar"},
                        "title": {"type": "string", "description": "Goal title (for add)"},
                        "goal_type": {"type": "string", "description": "Type: course, exam, etc."},
                        "url": {"type": "string", "description": "Related URL"},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="open_url",
                description="Open a URL in the default browser.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to open"},
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="spotify_play",
                description="Play a track on Spotify.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for Spotify"},
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute a tool call."""
        try:
            if name == "get_time":
                result = get_time()
            elif name == "system_info":
                result = system_info()
            elif name == "run_cmd":
                result = run_cmd(arguments.get("command", ""))
            elif name == "read_file":
                result = read_file(arguments.get("path", ""))
            elif name == "write_file":
                result = write_file(arguments.get("path", ""), arguments.get("content", ""))
            elif name == "see_screen":
                result = see_screen(arguments.get("question", ""))
            elif name == "search_browser_history":
                result = search_browser_history(
                    arguments.get("query", ""),
                    arguments.get("days_back", 30)
                )
            elif name == "open_history_item":
                result = open_history_item(arguments.get("query", ""))
            elif name == "generate_file":
                result = generate_file(
                    arguments.get("path", ""),
                    arguments.get("file_type", "auto"),
                    arguments.get("description", ""),
                    arguments.get("content", ""),
                )
            elif name == "goals_tool_handler":
                result = goals_tool_handler(
                    arguments.get("action", ""),
                    title=arguments.get("title"),
                    goal_type=arguments.get("goal_type"),
                    url=arguments.get("url"),
                )
            elif name == "open_url":
                result = open_url(arguments.get("url", ""))
            elif name == "spotify_play":
                result = spotify_play(arguments.get("query", ""))
            else:
                result = f"Unknown tool: {name}"

            return [types.TextContent(type="text", text=str(result))]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {e}")]

    return server

# ─── Main Entry Point ────────────────────────────────#

async def main():
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        print("❌ MCP (Model Context Protocol) is not available.")
        print("Install with: pip install mcp")
        sys.exit(1)

    server = create_mcp_server()
    if not server:
        print("❌ Failed to create MCP server.")
        sys.exit(1)

    print("Starting Friday MCP Server...")
    print("Server name: friday-mcp-server")
    print("Transport: stdio")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nFriday MCP Server stopped.")
    except Exception as e:
        print(f"Fatal error: {e}")
