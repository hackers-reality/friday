"""
Friday MCP Server - Phase 1.2
Expose Friday's tools via Model Context Protocol (stdio transport).
Allows any MCP client (Claude Desktop, Cursor, etc.) to use Friday's tools.
"""
from __future__ import annotations

import json
import os
import sys
import asyncio
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ─── Server Setup ────────────────────────────────────────────────────

server = Server("friday-mcp-server")

# Import Friday's tools
try:
    from friday import tools as ft
    TOOLS_AVAILABLE = True
except Exception as e:
    print(f"[MCP] Friday tools not available: {e}", file=sys.stderr)
    TOOLS_AVAILABLE = False


# ─── Tool Definitions ────────────────────────────────────────────────

def _get_tool_definitions() -> List[Tool]:
    """Get all Friday tool definitions in MCP format."""
    tools = [
        Tool(
            name="stark_doctor",
            description="Full self-diagnostic on all Sovereign AI systems. Returns system status report.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="spotify_play",
            description="Play a track or resume playback on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song or artist to play."}
                },
                "required": [],
            },
        ),
        Tool(
            name="spotify_pause",
            description="Pause Spotify playback.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="open_app",
            description="Open any application or website by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "App or site name."}
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="web_search",
            description="Quick web search for information. Returns text results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "max_results": {"type": "integer", "description": "Max results (default 5)."}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="video_search",
            description="Search for videos online. Opens first result directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Video search query."},
                    "max_results": {"type": "integer", "description": "Max results (default 5)."}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="see_screen",
            description="Analyze current screen. Use for 'what do you see', 'any errors?', 'find X on screen'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Specific question about screen."}
                },
                "required": [],
            },
        ),
        Tool(
            name="open_url",
            description="Open a URL in the browser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open."}
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="run_cmd",
            description="Run a shell command on the host PC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run."}
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="safe_run_cmd",
            description="Run a shell command only if it is on the allowlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run."}
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="memory_store",
            description="Store a fact in Friday's long-term memory vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "episodic, semantic, or preference."},
                    "keyword": {"type": "string", "description": "Unique recall key."},
                    "content": {"type": "string", "description": "Data to remember."},
                },
                "required": ["category", "keyword", "content"],
            },
        ),
        Tool(
            name="memory_retrieve",
            description="Recall information from memory vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword or topic."}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_time",
            description="Get current date and time.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="system_info",
            description="Get host PC hardware and OS status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="deep_research",
            description="Full multi-source deep research with synthesized report.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Research topic."},
                    "url": {"type": "string", "description": "Optional primary URL."},
                    "depth": {"type": "integer", "description": "Pages to fetch (1-5, default 3)."},
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="type_text",
            description="Type text at the current cursor position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type."}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="click",
            description="Click at current mouse position or at x,y coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (optional)."},
                    "y": {"type": "integer", "description": "Y coordinate (optional)."},
                    "target": {"type": "string", "description": "Target element to click (optional)."},
                },
            },
        ),
        Tool(
            name="double_click",
            description="Double-click at current mouse position or at x,y.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (optional)."},
                    "y": {"type": "integer", "description": "Y coordinate (optional)."},
                },
            },
        ),
        Tool(
            name="right_click",
            description="Right-click at current mouse position or at x,y.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (optional)."},
                    "y": {"type": "integer", "description": "Y coordinate (optional)."},
                },
            },
        ),
        Tool(
            name="move_mouse",
            description="Move mouse to x,y coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate."},
                    "y": {"type": "integer", "description": "Y coordinate."},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="drag",
            description="Drag from current position to x,y with duration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Target X."},
                    "y": {"type": "integer", "description": "Target Y."},
                    "duration": {"type": "number", "description": "Drag duration in seconds."},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="hotkey",
            description="Press a keyboard hotkey combination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {"type": "string", "description": "Keys separated by +, e.g. ctrl+c."}
                },
                "required": ["keys"],
            },
        ),
        Tool(
            name="press_key",
            description="Press a single keyboard key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press."}
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="scroll",
            description="Scroll the mouse wheel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "Scroll amount (positive=up, negative=down)."}
                },
                "required": ["amount"],
            },
        ),
        Tool(
            name="read_file",
            description="Read the contents of a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path."}
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
                    "path": {"type": "string", "description": "File path."},
                    "content": {"type": "string", "description": "Content to write."},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="list_files",
            description="List files in a directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path."}
                },
                "required": [],
            },
        ),
        Tool(
            name="find_files",
            description="Find files matching a pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern."},
                    "path": {"type": "string", "description": "Search directory."},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="copy_file",
            description="Copy a file from source to destination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Source path."},
                    "dst": {"type": "string", "description": "Destination path."},
                },
                "required": ["src", "dst"],
            },
        ),
        Tool(
            name="move_file",
            description="Move a file from source to destination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Source path."},
                    "dst": {"type": "string", "description": "Destination path."},
                },
                "required": ["src", "dst"],
            },
        ),
        Tool(
            name="delete_file",
            description="Delete a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path."}
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="clipboard_get",
            description="Get the current clipboard content.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="clipboard_set",
            description="Set the clipboard content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to put on clipboard."}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="climb_codebase",
            description="Search and analyze code in the current project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for."},
                    "path": {"type": "string", "description": "Directory to search in."},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="situational_awareness",
            description="Get current desktop context: active window, running processes, system state.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="git_ops",
            description="Perform git operations: status, add, commit, push, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "Git operation (status, add, commit, push, log, diff)."},
                    "message": {"type": "string", "description": "Commit message (for commit)."},
                },
                "required": ["operation"],
            },
        ),
        Tool(
            name="take_snapshot",
            description="Save the current screen state to memory.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="recall_snapshot",
            description="Recall a previously saved screen snapshot.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Snapshot index to recall."}
                },
            },
        ),

        # ── Browser-Use Bridge (full AI-native browser control) ──
        Tool(
            name="browser_use_navigate",
            description="FULL AUTONOMOUS browser agent via browser-use. Give a natural language task — the AI handles navigation, clicks, forms, extraction. Supports vision, multi-step planning, multi-tab.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Natural language browsing task (e.g. 'Go to google.com, search for X, click first result, extract the article')"},
                    "max_steps": {"type": "integer", "description": "Max action steps (default 20, max 100)"},
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="browser_use_extract",
            description="Extract content from a page using the browser-use AI agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Navigation + what to find"},
                    "instruction": {"type": "string", "description": "Extraction guidance"},
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="browser_use_click",
            description="Click an element on the page by CSS selector or visible text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector (e.g. 'button#submit')"},
                    "text": {"type": "string", "description": "Visible text to click (e.g. 'Sign In')"},
                },
            },
        ),
        Tool(
            name="browser_use_type",
            description="Type text into an input field identified by CSS selector.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector (e.g. 'input[name=\"email\"]')"},
                    "text": {"type": "string", "description": "Text to type"},
                    "clear_first": {"type": "boolean", "description": "Clear field before typing (default true)"},
                },
                "required": ["selector", "text"],
            },
        ),
        Tool(
            name="browser_use_extract_text",
            description="Extract visible text from the page or a specific element.",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector (default 'body')"},
                },
            },
        ),
        Tool(
            name="browser_use_extract_html",
            description="Extract full HTML of the current page.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_extract_links",
            description="Extract all links from the current page.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_screenshot",
            description="Take a screenshot of the current page (returns base64 PNG).",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full page (default false)"},
                },
            },
        ),
        Tool(
            name="browser_use_scroll",
            description="Scroll the page up or down.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "description": "'down' or 'up' (default 'down')"},
                    "amount": {"type": "integer", "description": "Pixels to scroll (default 500)"},
                },
            },
        ),
        Tool(
            name="browser_use_evaluate",
            description="Run JavaScript in the page context and return the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript code to execute (e.g. 'document.title')"},
                },
                "required": ["script"],
            },
        ),
        Tool(
            name="browser_use_get_dom_state",
            description="Get DOM state: URL, title, viewport, link/button/input counts, scroll position.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_get_url",
            description="Get the current page URL.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_get_title",
            description="Get the current page title.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_list_tabs",
            description="List all open browser tabs.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_new_tab",
            description="Open a new browser tab with optional URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to (default 'about:blank')"},
                },
            },
        ),
        Tool(
            name="browser_use_close_tab",
            description="Close the current browser tab.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_go_back",
            description="Navigate back in browser history.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_go_forward",
            description="Navigate forward in browser history.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_status",
            description="Show browser-use bridge status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_clear",
            description="Close the browser and clear session state.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_use_reconnect",
            description="Force-reconnect the browser. Closes existing, re-creates on next action.",
            inputSchema={"type": "object", "properties": {}},
        ),

        # ── Cookbook (Hardware Scanner + Model Recommendations) ──
        Tool(
            name="cookbook_scan",
            description="Scan local hardware (GPU, VRAM, RAM) and show system specs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {"type": "boolean", "description": "Re-scan instead of using cache"},
                },
            },
        ),
        Tool(
            name="cookbook_recommend",
            description="Recommend the best local AI models based on detected GPU/VRAM.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cookbook_ollama_check",
            description="Check if Ollama is installed and list available local models.",
            inputSchema={"type": "object", "properties": {}},
        ),

        # ── Proactive Copilot (Desktop-aware suggestions) ──
        Tool(
            name="proactive_suggest",
            description="Get a proactive suggestion based on current desktop context (active window, clipboard, recent files).",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {"type": "boolean", "description": "Bypass cooldown"},
                },
            },
        ),
        Tool(
            name="proactive_status",
            description="Show proactive copilot status.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="proactive_copilot_enable",
            description="Enable or disable the proactive copilot.",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "True to enable, False to disable"},
                },
            },
        ),
        Tool(
            name="proactive_context",
            description="Get current desktop context: active window, clipboard, recent files.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    return tools


# ─── MCP Handlers ────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return _get_tool_definitions()


@server.call_tool()
async def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
    """Execute a tool call."""
    if not TOOLS_AVAILABLE:
        return [TextContent(type="text", text="Friday tools not available.")]
    
    args = arguments or {}
    func = getattr(ft, name, None)
    
    if not func:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    try:
        no_arg_tools = [
            "stark_doctor", "spotify_pause", "get_time", "system_info",
            "situational_awareness", "take_snapshot", "clipboard_get",
            "browser_use_status", "browser_use_extract_html", "browser_use_extract_links",
            "browser_use_get_dom_state", "browser_use_get_url", "browser_use_get_title",
            "browser_use_list_tabs", "browser_use_close_tab", "browser_use_go_back",
            "browser_use_go_forward", "browser_use_clear", "browser_use_reconnect",
            "cookbook_recommend", "cookbook_ollama_check",
            "proactive_status", "proactive_context",
        ]
        if name in no_arg_tools:
            result = func()
        elif name == "browser_use_navigate":
            result = func(args.get("task", ""), max_steps=args.get("max_steps", 20))
        elif name == "browser_use_extract":
            result = func(args.get("task", ""), instruction=args.get("instruction", "Extract all visible text and links"))
        elif name == "browser_use_click":
            result = func(selector=args.get("selector", ""), text=args.get("text", ""))
        elif name == "browser_use_type":
            result = func(selector=args.get("selector", ""), text=args.get("text", ""),
                         clear_first=args.get("clear_first", True))
        elif name == "browser_use_extract_text":
            result = func(selector=args.get("selector", "body"))
        elif name == "browser_use_screenshot":
            result = func(full_page=args.get("full_page", False))
        elif name == "browser_use_scroll":
            result = func(direction=args.get("direction", "down"), amount=args.get("amount", 500))
        elif name == "browser_use_evaluate":
            result = func(script=args.get("script", ""))
        elif name == "browser_use_new_tab":
            result = func(url=args.get("url", "about:blank"))
        elif name == "cookbook_scan":
            result = func(force=args.get("force", False))
        elif name == "proactive_suggest":
            result = func(force=args.get("force", False))
        elif name == "proactive_copilot_enable":
            result = func(enabled=args.get("enabled", True))
        elif name in ["click", "double_click", "right_click"]:
            x = args.get("x")
            y = args.get("y")
            if x is not None and y is not None:
                result = func(int(x), int(y))
            else:
                result = func()
        elif name == "move_mouse":
            result = func(int(args.get("x", 0)), int(args.get("y", 0)))
        elif name == "drag":
            result = func(int(args.get("x", 0)), int(args.get("y", 0)),
                        float(args.get("duration", 0.5)))
        elif name == "scroll":
            result = func(int(args.get("amount", 1)))
        elif name == "hotkey":
            result = func(args.get("keys", ""))
        elif name == "press_key":
            result = func(args.get("key", ""))
        elif name == "type_text":
            result = func(args.get("text", ""))
        elif name == "git_ops":
            result = func(args.get("operation", "status"), message=args.get("message", ""))
        elif name == "clipboard_set":
            result = func(args.get("text", ""))
        elif name == "memory_store":
            result = func(args.get("category", ""), args.get("keyword", ""),
                         args.get("content", ""))
        elif name == "memory_retrieve":
            result = func(args.get("query", ""))
        elif name == "web_search":
            result = func(args.get("query", ""), max_results=args.get("max_results", 5))
        elif name == "video_search":
            result = func(args.get("query", ""), max_results=args.get("max_results", 5))
        elif name == "deep_research":
            result = func(args.get("topic", ""), url=args.get("url"),
                         depth=args.get("depth", 3))
        elif name == "see_screen":
            result = func(args.get("question", "Analyze the current workspace."))
        elif name == "recall_snapshot":
            result = func(int(args.get("index", -1)))
        else:
            # Generic call with all args
            result = func(**args)
        
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Tool error: {str(e)}")]


# ─── Main Entry Point ─────────────────────────────────────────────────

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    print("[MCP] Friday MCP Server starting...", file=sys.stderr)
    asyncio.run(main())
