"""
Friday Tool Registry — centrally describes every tool by name, category, risk, and metadata.
Does not replace TOOL_MAP in live.py; augments it with introspection.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any

# ─── Tool metadata schema ──────────────────────────────────

TOOL_META: Dict[str, dict] = {
    # ── Desktop / OS ──
    "open_app": {"category": "desktop", "risk": "local_write", "description": "Open an application by name"},
    "close_app": {"category": "desktop", "risk": "local_write", "description": "Close a running application"},
    "list_running_apps": {"category": "desktop", "risk": "read_only", "description": "List currently running applications"},
    "get_active_window": {"category": "desktop", "risk": "read_only", "description": "Get the active window title"},
    "type_text": {"category": "desktop", "risk": "local_write", "description": "Type text at the current cursor position"},
    "click": {"category": "desktop", "risk": "local_write", "description": "Click at screen coordinates"},
    "double_click": {"category": "desktop", "risk": "local_write", "description": "Double-click at coordinates"},
    "right_click": {"category": "desktop", "risk": "local_write", "description": "Right-click at coordinates"},
    "move_mouse": {"category": "desktop", "risk": "local_write", "description": "Move mouse to coordinates"},
    "drag": {"category": "desktop", "risk": "local_write", "description": "Drag from current position by offset"},
    "scroll": {"category": "desktop", "risk": "local_write", "description": "Scroll by amount"},
    "press_key": {"category": "desktop", "risk": "local_write", "description": "Press a keyboard key"},
    "hotkey": {"category": "desktop", "risk": "local_write", "description": "Execute a hotkey combination"},

    # ── System Info ──
    "system_info": {"category": "system", "risk": "read_only", "description": "General system info"},
    "system_cpu": {"category": "system", "risk": "read_only", "description": "CPU usage information"},
    "system_memory": {"category": "system", "risk": "read_only", "description": "Memory usage information"},
    "system_disk": {"category": "system", "risk": "read_only", "description": "Disk usage information"},
    "system_network": {"category": "system", "risk": "read_only", "description": "Network usage information"},
    "system_processes": {"category": "system", "risk": "read_only", "description": "Running processes list"},
    "get_time": {"category": "system", "risk": "read_only", "description": "Get current date and time"},

    # ── Filesystem ──
    "read_file": {"category": "filesystem", "risk": "read_only", "description": "Read a file's contents"},
    "write_file": {"category": "filesystem", "risk": "local_write", "description": "Write content to a file"},
    "list_files": {"category": "filesystem", "risk": "read_only", "description": "List files in a directory"},
    "find_files": {"category": "filesystem", "risk": "read_only", "description": "Search for files by pattern"},
    "copy_file": {"category": "filesystem", "risk": "local_write", "description": "Copy a file"},
    "move_file": {"category": "filesystem", "risk": "local_write", "description": "Move or rename a file"},
    "delete_file": {"category": "filesystem", "risk": "destructive", "description": "Delete a file permanently"},
    "clipboard_get": {"category": "filesystem", "risk": "read_only", "description": "Get clipboard text"},
    "clipboard_set": {"category": "filesystem", "risk": "local_write", "description": "Set clipboard text"},

    # ── Web / Browser ──
    "web_search": {"category": "web", "risk": "read_only", "description": "Search the web"},
    "video_search": {"category": "web", "risk": "read_only", "description": "Search for videos"},
    "open_url": {"category": "web", "risk": "local_write", "description": "Open a URL in the default browser"},
    "deep_research": {"category": "web", "risk": "read_only", "description": "Perform deep multi-step research"},
    "search_browser_history": {"category": "web", "risk": "read_only", "description": "Search browser history"},
    "open_history_item": {"category": "web", "risk": "local_write", "description": "Open a history item"},

    # ── OpenCLI Browser Automation ──
    "opencli_init_bridge": {"category": "browser", "risk": "local_write", "description": "Initialize OpenCLI browser bridge"},
    "opencli_navigate": {"category": "browser", "risk": "local_write", "description": "Navigate to a URL"},
    "opencli_click": {"category": "browser", "risk": "local_write", "description": "Click on element by selector"},
    "opencli_type": {"category": "browser", "risk": "local_write", "description": "Type text into element"},
    "opencli_extract": {"category": "browser", "risk": "read_only", "description": "Extract text from element"},
    "opencli_screenshot": {"category": "browser", "risk": "read_only", "description": "Take browser screenshot"},
    "opencli_scroll": {"category": "browser", "risk": "local_write", "description": "Scroll the page"},
    "opencli_keys": {"category": "browser", "risk": "local_write", "description": "Send keyboard keys"},
    "opencli_eval": {"category": "browser", "risk": "local_write", "description": "Evaluate JavaScript"},
    "opencli_state": {"category": "browser", "risk": "read_only", "description": "Get browser state"},
    "opencli_doctor": {"category": "browser", "risk": "read_only", "description": "Check OpenCLI bridge health"},
    "opencli_tab_list": {"category": "browser", "risk": "read_only", "description": "List open tabs"},
    "opencli_tab_new": {"category": "browser", "risk": "local_write", "description": "Open new tab"},
    "opencli_tab_select": {"category": "browser", "risk": "local_write", "description": "Switch to tab"},
    "opencli_tab_close": {"category": "browser", "risk": "local_write", "description": "Close a tab"},
    "opencli_close": {"category": "browser", "risk": "local_write", "description": "Close browser"},
    "opencli_get_url": {"category": "browser", "risk": "read_only", "description": "Get current page URL"},
    "opencli_get_title": {"category": "browser", "risk": "read_only", "description": "Get current page title"},
    "opencli_find": {"category": "browser", "risk": "read_only", "description": "Find element on page"},
    "opencli_hover": {"category": "browser", "risk": "local_write", "description": "Hover over element"},
    "opencli_focus": {"category": "browser", "risk": "local_write", "description": "Focus on element"},
    "opencli_dblclick": {"category": "browser", "risk": "local_write", "description": "Double-click element"},
    "opencli_check": {"category": "browser", "risk": "local_write", "description": "Check checkbox"},
    "opencli_uncheck": {"category": "browser", "risk": "local_write", "description": "Uncheck checkbox"},
    "opencli_drag": {"category": "browser", "risk": "local_write", "description": "Drag and drop"},

    # ── Vision / Screen ──
    "see_screen": {"category": "vision", "risk": "read_only", "description": "Capture and analyze screen"},
    "vision_click": {"category": "vision", "risk": "local_write", "description": "Click at vision-detected coordinates"},
    "cv_tool": {"category": "vision", "risk": "read_only", "description": "Camera: start/stop/list cameras, get scene context, describe scene"},

    # ── Memory ──
    "memory_store": {"category": "memory", "risk": "local_write", "description": "Store a fact into memory"},
    "memory_retrieve": {"category": "memory", "risk": "read_only", "description": "Retrieve facts from memory"},
    "vector_memory_tool": {"category": "memory", "risk": "read_only", "description": "Semantic vector memory search"},
    "episodic_tool": {"category": "memory", "risk": "read_only", "description": "Episodic memory search/record"},
    "memory_import_tool_handler": {"category": "memory", "risk": "local_write", "description": "Import chat history and audit profile"},

    # ── Code ──
    "climb_codebase": {"category": "code", "risk": "read_only", "description": "Explore and understand codebase"},
    "situational_awareness": {"category": "code", "risk": "read_only", "description": "Get current project context"},
    "generate_file": {"category": "code", "risk": "local_write", "description": "Generate a file from template"},
    "generate_file_llm": {"category": "code", "risk": "local_write", "description": "Generate file using LLM"},
    "deep_code_review": {"category": "code", "risk": "read_only", "description": "Deep AI code review"},
    "code_review_report": {"category": "code", "risk": "read_only", "description": "Generate code review report"},

    # ── Git / GitHub ──
    "git_ops": {"category": "github", "risk": "local_write", "description": "Git operations (status, add, commit)"},
    "github_list_files": {"category": "github", "risk": "read_only", "description": "List files in GitHub repo"},
    "github_read_file": {"category": "github", "risk": "read_only", "description": "Read file from GitHub"},
    "github_write_file": {"category": "github", "risk": "network_write", "description": "Write file to GitHub"},
    "github_create_branch": {"category": "github", "risk": "network_write", "description": "Create a branch"},
    "github_create_pr": {"category": "github", "risk": "network_write", "description": "Create pull request"},
    "github_list_prs": {"category": "github", "risk": "read_only", "description": "List pull requests"},
    "github_pr_comment": {"category": "github", "risk": "network_write", "description": "Comment on PR"},
    "github_pr_diff": {"category": "github", "risk": "read_only", "description": "Get PR diff"},
    "github_pr_files": {"category": "github", "risk": "read_only", "description": "List PR files"},
    "github_delete_file": {"category": "github", "risk": "network_write", "description": "Delete file from GitHub"},
    "github_get_contents": {"category": "github", "risk": "read_only", "description": "Get repo contents"},
    "github_get_user": {"category": "github", "risk": "read_only", "description": "Get GitHub user info"},
    "github_self_modify": {"category": "github", "risk": "self_modify", "description": "Modify own source code via GitHub"},
    "github_review_pr": {"category": "github", "risk": "read_only", "description": "Review a pull request"},
    "github_create_repo": {"category": "github", "risk": "network_write", "description": "Create repository"},
    "github_list_issues": {"category": "github", "risk": "read_only", "description": "List issues"},
    "github_create_issue": {"category": "github", "risk": "network_write", "description": "Create issue"},
    "github_search_code": {"category": "github", "risk": "read_only", "description": "Search GitHub code"},
    "github_merge_pr": {"category": "github", "risk": "network_write", "description": "Merge a PR"},
    "github_repo_info": {"category": "github", "risk": "read_only", "description": "Get repo information"},
    "github_list_branches": {"category": "github", "risk": "read_only", "description": "List branches"},
    "github_commit_history": {"category": "github", "risk": "read_only", "description": "Get commit history"},
    "github_setup": {"category": "github", "risk": "local_write", "description": "Setup GitHub authentication"},

    # ── Gmail ──
    "read_emails": {"category": "gmail", "risk": "read_only", "description": "Read emails from inbox"},
    "send_email": {"category": "gmail", "risk": "external_send", "description": "Send an email"},
    "draft_email": {"category": "gmail", "risk": "local_write", "description": "Draft an email"},
    "gmail_authorize": {"category": "gmail", "risk": "credential", "description": "Authorize Gmail access"},

    # ── Smart Home / IoT ──
    "alexa_command": {"category": "smart_home", "risk": "network_write", "description": "Send Alexa command"},
    "alexa_poll": {"category": "smart_home", "risk": "read_only", "description": "Poll Alexa status"},
    "home_assistant_command": {"category": "smart_home", "risk": "network_write", "description": "Send Home Assistant command"},
    "smart_home_command": {"category": "smart_home", "risk": "network_write", "description": "General smart home command"},
    "tell_alexa": {"category": "smart_home", "risk": "network_write", "description": "Tell Alexa to speak"},

    # ── Spotify ──
    "spotify_play": {"category": "spotify", "risk": "network_write", "description": "Play Spotify track"},
    "spotify_pause": {"category": "spotify", "risk": "network_write", "description": "Pause Spotify"},
    "spotify_current": {"category": "spotify", "risk": "read_only", "description": "Get current playback"},
    "spotify_next": {"category": "spotify", "risk": "network_write", "description": "Next track"},
    "spotify_prev": {"category": "spotify", "risk": "network_write", "description": "Previous track"},
    "spotify_volume": {"category": "spotify", "risk": "network_write", "description": "Set volume"},

    # ── Instagram ──
    "send_instagram_dm": {"category": "instagram", "risk": "external_send", "description": "Send Instagram DM"},

    # ── Goals / Productivity ──
    "goals_tool_handler": {"category": "goals", "risk": "local_write", "description": "Manage goals and OKRs"},
    "queue_task": {"category": "goals", "risk": "local_write", "description": "Queue a background task"},
    "queue_status": {"category": "goals", "risk": "read_only", "description": "Check queue status"},
    "queue_result": {"category": "goals", "risk": "read_only", "description": "Get task result"},
    "multi_task": {"category": "goals", "risk": "local_write", "description": "Execute multiple tasks in parallel"},
    "scheduler_tool": {"category": "goals", "risk": "local_write", "description": "Schedule a task"},

    # ── Internal / Meta ──
    "workflow_tool": {"category": "internal", "risk": "local_write", "description": "Manage workflows"},
    "plugin_tool": {"category": "internal", "risk": "local_write", "description": "Manage plugins"},
    "knowledge_graph_tool": {"category": "internal", "risk": "read_only", "description": "Query knowledge graph"},
    "kyu_tool_handler": {"category": "internal", "risk": "read_only", "description": "KYU personality adaptation"},
    "research_tool_handler": {"category": "internal", "risk": "read_only", "description": "Research assistant"},
    "reasoning_tool_handler": {"category": "internal", "risk": "read_only", "description": "Multi-step reasoning"},
    "clock_tool": {"category": "internal", "risk": "read_only", "description": "Clock and timer operations"},
    "status_check": {"category": "internal", "risk": "read_only", "description": "General status check"},
    "message_channel_tool": {"category": "internal", "risk": "read_only", "description": "Message channel operations"},
    "send_notification": {"category": "internal", "risk": "local_write", "description": "Send a notification"},
    "get_pending_notifications": {"category": "internal", "risk": "read_only", "description": "List pending notifications"},
    "clear_notifications": {"category": "internal", "risk": "local_write", "description": "Clear notifications"},
    "dream_tool": {"category": "internal", "risk": "read_only", "description": "Dreaming/creativity tool"},
    "skills_tool": {"category": "internal", "risk": "local_write", "description": "Manage skills"},
    "predictive_tool": {"category": "internal", "risk": "read_only", "description": "Predictive analysis"},
    "reflection_tool": {"category": "internal", "risk": "read_only", "description": "Self-reflection tool"},
    "context_tool": {"category": "internal", "risk": "read_only", "description": "Context management"},
    "monitor_tool": {"category": "internal", "risk": "read_only", "description": "System monitoring"},
    "mcp_tool": {"category": "internal", "risk": "read_only", "description": "MCP bridge tool"},
    "self_improve_tool": {"category": "internal", "risk": "background_autonomy", "description": "Self-improvement engine"},
    "crash_tool": {"category": "internal", "risk": "read_only", "description": "Crash analysis tool"},
    "pr_manager_tool": {"category": "internal", "risk": "read_only", "description": "PR management tool"},
    "protector_tool": {"category": "internal", "risk": "read_only", "description": "System protector tool"},
    "multi_agent_delegate": {"category": "internal", "risk": "read_only", "description": "Delegate to sub-agent"},
    "stark_doctor": {"category": "internal", "risk": "read_only", "description": "System health diagnostic"},
    "calendar_tool_handler": {"category": "internal", "risk": "read_only", "description": "Calendar operations"},
    "startup_tool_handler": {"category": "internal", "risk": "read_only", "description": "Startup management"},
    "dashboard_tool": {"category": "internal", "risk": "local_write", "description": "Control the web dashboard"},

    # ── New systems (added by this upgrade) ──
    "authority_tool": {"category": "internal", "risk": "self_modify", "description": "Manage authority policy and decisions"},
    "snapshot_tool": {"category": "internal", "risk": "local_write", "description": "Snapshot management (create/list/restore)"},
    "sidecar_tool": {"category": "internal", "risk": "local_write", "description": "Sidecar process management"},
    "autonomy_tool": {"category": "internal", "risk": "background_autonomy", "description": "Autonomous improvement engine"},
    "tool_registry_tool": {"category": "internal", "risk": "read_only", "description": "Inspect tool registry metadata"},
}

# ─── Risk level classification ─────────────────────────────

RISK_LEVELS = {
    "read_only": 1,
    "local_write": 2,
    "destructive": 3,
    "system_control": 4,
    "external_send": 4,
    "credential": 5,
    "network_write": 5,
    "self_modify": 5,
    "background_autonomy": 5,
}


# ─── Registry API ──────────────────────────────────────────

def build_tool_registry() -> Dict[str, dict]:
    """Return a copy of the full tool metadata registry."""
    return dict(TOOL_META)


def get_tool_metadata(tool_name: str) -> Optional[dict]:
    """Get metadata for a single tool, or None if unknown."""
    return TOOL_META.get(tool_name)


def list_tool_registry(category: Optional[str] = None) -> Dict[str, List[str]]:
    """
    List tools grouped by category.

    If category is specified, only return that category.
    Returns dict of {category: [tool_names]}.
    """
    result: Dict[str, List[str]] = {}
    for name, meta in TOOL_META.items():
        cat = meta.get("category", "uncategorized")
        if category and cat != category:
            continue
        result.setdefault(cat, []).append(name)
    return result


def check_tool_registry_consistency(tool_map: Dict[str, callable]) -> dict:
    """
    Check that all declared tools exist in TOOL_MAP and vice versa.

    Args:
        tool_map: The live TOOL_MAP dict (from live.py).

    Returns:
        dict with keys:
          - "missing_from_registry": tools in map but not in registry
          - "missing_from_map": tools in registry but not in map
          - "orphan_tools": tools in both but with no metadata
    """
    result: dict = {
        "missing_from_registry": [],
        "missing_from_map": [],
        "orphan_tools": [],
    }
    map_names = set(tool_map.keys())
    registry_names = set(TOOL_META.keys())

    for name in map_names:
        if name not in registry_names:
            result["missing_from_registry"].append(name)

    for name in registry_names:
        if name not in map_names:
            result["missing_from_map"].append(name)

    return result


def tool_registry_tool(action: str = "status", tool_name: str = "", category: str = "") -> str:
    """
    Friday tool to inspect the tool registry.
    Actions: status, get, list, check.
    """
    if action == "status":
        total = len(TOOL_META)
        cats = set(m["category"] for m in TOOL_META.values())
        return (
            f"### TOOL REGISTRY\n\n"
            f"Total tools: {total}\n"
            f"Categories ({len(cats)}): {', '.join(sorted(cats))}"
        )

    if action == "get":
        if not tool_name:
            return "[FAIL] Provide tool_name."
        meta = get_tool_metadata(tool_name)
        if not meta:
            return f"[FAIL] Unknown tool: {tool_name}"
        return (
            f"### {tool_name}\n"
            f"Category: {meta['category']}\n"
            f"Risk: {meta['risk']}\n"
            f"Description: {meta['description']}"
        )

    if action == "list":
        cat = category if category else None
        grouped = list_tool_registry(cat)
        lines = ["### TOOL REGISTRY - Tool List\n"]
        for c, tools in sorted(grouped.items()):
            lines.append(f"  {c}: {', '.join(sorted(tools))}")
        return "\n".join(lines)

    if action == "check":
        from typing import Dict, Callable
        return "[INFO] Use check_tool_registry_consistency() programmatically with a TOOL_MAP reference."

    return f"Unknown action: {action}. Available: status, get, list, check"
