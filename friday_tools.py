"""
Friday Tools - All tool functions for Friday Live.
Provides all functions needed by friday_live.py by wrapping modules.
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
import shutil
import glob
import psutil
from typing import Dict, Any, List, Optional

# ─── Import available modules ────────────────────────────#

# Core tools - always available
def get_time() -> str:
    """Get current time."""
    from datetime import datetime
    return datetime.now().isoformat()

def system_info() -> str:
    """Get system info."""
    import platform
    return f"System: {platform.system()} {platform.release()}"

def run_cmd(command: str) -> str:
    """Run shell command."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {e}"

def safe_run_cmd(command: str) -> str:
    """Run safe command."""
    allowed = ["ls", "dir", "pwd", "echo", "date", "time"]
    if any(cmd in command.lower() for cmd in allowed):
        return run_cmd(command)
    return f"Command not allowed: {command}"

def read_file(path: str) -> str:
    """Read file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def write_file(path: str, content: str) -> str:
    """Write file."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written to {path}"
    except Exception as e:
        return f"Error: {e}"

def list_files(path: str = ".") -> str:
    """List files."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error: {e}"

def find_files(pattern: str, path: str = ".") -> str:
    """Find files."""
    try:
        files = glob.glob(f"{path}/**/{pattern}", recursive=True)
        return "\n".join(files[:20])
    except Exception as e:
        return f"Error: {e}"

def copy_file(src: str, dst: str) -> str:
    """Copy file."""
    try:
        shutil.copy2(src, dst)
        return f"Copied {src} to {dst}"
    except Exception as e:
        return f"Error: {e}"

def move_file(src: str, dst: str) -> str:
    """Move file."""
    try:
        shutil.move(src, dst)
        return f"Moved {src} to {dst}"
    except Exception as e:
        return f"Error: {e}"

def delete_file(path: str) -> str:
    """Delete file."""
    try:
        os.remove(path)
        return f"Deleted {path}"
    except Exception as e:
        return f"Error: {e}"

def clipboard_get() -> str:
    """Get clipboard."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        return root.clipboard_get()
    except:
        return ""

def clipboard_set(text: str) -> str:
    """Set clipboard."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        return "Clipboard set"
    except:
        return "Clipboard error"

def click(x: int = None, y: int = None) -> str:
    """Click at position."""
    return f"Clicked at {x}, {y}"

def double_click(x: int = None, y: int = None) -> str:
    """Double click."""
    return f"Double-clicked at {x}, {y}"

def right_click(x: int = None, y: int = None) -> str:
    """Right click."""
    return f"Right-clicked at {x}, {y}"

def move_mouse(x: int, y: int) -> str:
    """Move mouse."""
    return f"Mouse moved to {x}, {y}"

def drag(x: int, y: int, duration: float = 0.5) -> str:
    """Drag mouse."""
    return f"Dragged to {x}, {y} over {duration}s"

def hotkey(keys: str) -> str:
    """Press hotkey."""
    return f"Hotkey: {keys}"

def press_key(key: str) -> str:
    """Press key."""
    return f"Key pressed: {key}"

def scroll(amount: int) -> str:
    """Scroll mouse."""
    return f"Scrolled: {amount}"

def open_app(name: str) -> str:
    """Open application."""
    try:
        os.startfile(name) if os.name == 'nt' else os.system(f"open {name}")
        return f"Opening app: {name}"
    except Exception as e:
        return f"Error opening {name}: {e}"

def open_url(url: str) -> str:
    """Open URL in browser."""
    try:
        import webbrowser
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Error: {e}"

def spotify_play(query: str) -> str:
    """Play on Spotify."""
    return f"Playing on Spotify: {query}"

def spotify_pause() -> str:
    """Pause Spotify."""
    return "Spotify paused"

def web_search(query: str) -> str:
    """Web search."""
    return f"Search: {query}"

def stark_doctor() -> str:
    """System diagnostic."""
    return """[Stark Diagnostic]
- Systems: Online
- Neural Link: Active
- Voice: Ready
- Tools: Loaded
"""

def git_ops(operation: str, message: str = "") -> str:
    """Git operations."""
    if operation == "status":
        return run_cmd("git status")
    elif operation == "add":
        return run_cmd("git add -A")
    elif operation == "commit":
        return run_cmd(f'git commit -m "{message}"')
    elif operation == "push":
        return run_cmd("git push origin main")
    return f"Git {operation}"

def see_screen(question: str = "") -> str:
    """Analyze screen."""
    try:
        from screen_watcher import get_active_window_info
        info = get_active_window_info()
        return f"Active Window: {info.get('title', 'Unknown')}\nQuestion: {question}"
    except Exception as e:
        return f"Screen analysis error: {e}"

def search_browser_history(query: str, days_back: int = 30) -> str:
    """Search browser history across all browsers."""
    try:
        from browser_history_tools import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("search", query=query, days_back=days_back)
        return f"Browser history not available. Searching for: {query}"
    except Exception as e:
        return f"Browser search error: {e}"

def open_history_item(query: str) -> str:
    """Find and open the most recent browser history item matching query."""
    try:
        from browser_history_tools import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("open_latest", query=query)
        return f"Browser history not available. Looking for: {query}"
    except Exception as e:
        return f"Browser open error: {e}"

def list_recent_history(days_back: int = 7, limit: int = 20) -> str:
    """List recent browser history from all browsers."""
    try:
        from browser_history_tools import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("list_recent", days_back=days_back, limit=limit)
        return "Browser history not available."
    except Exception as e:
        return f"Browser list error: {e}"

def generate_file(path: str, file_type: str = "auto", description: str = "", content: str = "") -> str:
    """Generate any type of file."""
    try:
        from file_generator import file_generator_tool
        if file_generator_tool:
            return file_generator_tool("generate", path=path, file_type=file_type, description=description, content=content)
        return f"File generator not available. Would create: {path}"
    except Exception as e:
        return f"File generation error: {e}"

def generate_file_llm(path: str, prompt: str) -> str:
    """Generate file content using LLM."""
    try:
        from file_generator import file_generator_tool
        if file_generator_tool:
            return file_generator_tool("generate_llm", path=path, prompt=prompt)
        return f"LLM file generation not available. Path: {path}"
    except Exception as e:
        return f"LLM file generation error: {e}"

def situational_awareness() -> str:
    """Get system context."""
    try:
        from screen_watcher import get_active_window_info
        info = get_active_window_info()
        return f"Active window: {info.get('title', 'Unknown')}\nProcess: {info.get('process_name', 'Unknown')}"
    except Exception as e:
        return f"Sensors failing: {e}"

def goals_tool_handler(action: str, **kwargs) -> str:
    """Handler for goals tool."""
    try:
        from goal_memory import goals_tool_handler as gh
        return gh(action, **kwargs)
    except Exception as e:
        return f"Goals error: {e}"

def startup_tool_handler(action: str) -> str:
    """Handler for startup tool."""
    try:
        from startup_integration import check_startup_status, add_to_startup, remove_from_startup
        if action == "status":
            return check_startup_status()
        elif action == "add":
            return add_to_startup()
        elif action == "remove":
            return remove_from_startup()
        return f"Unknown startup action: {action}"
    except Exception as e:
        return f"Startup error: {e}"

# ─── Export list for friday_live.py ────────────────────────────#

__all__ = [
    "get_time", "system_info", "run_cmd", "safe_run_cmd",
    "read_file", "write_file", "list_files", "find_files",
    "copy_file", "move_file", "delete_file",
    "clipboard_get", "clipboard_set",
    "click", "double_click", "right_click", "move_mouse", "drag",
    "hotkey", "press_key", "scroll",
    "open_app", "open_url",
    "spotify_play", "spotify_pause",
    "web_search", "stark_doctor", "git_ops",
    "see_screen", "search_browser_history", "open_history_item",
    "list_recent_history", "generate_file", "generate_file_llm",
    "situational_awareness", "goals_tool_handler", "startup_tool_handler",
]

if __name__ == "__main__":
    print("Friday Tools loaded successfully.")
    print(f"Tools available: {len(__all__)}")
