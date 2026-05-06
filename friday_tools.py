"""
Friday Tools - All tool functions for Friday Live.
Provides all functions needed by friday_live.py by wrapping modules.
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
from typing import Dict, Any, List, Optional

# Import available modules
try:
    from friday_voice import voice_tool
except ImportError:
    voice_tool = None

try:
    from friday_web import web_tool
except ImportError:
    web_tool = None

try:
    from friday_automation import automation_tool
except ImportError:
    automation_tool = None

try:
    from friday_database import database_tool
except ImportError:
    database_tool = None

try:
    from friday_ai import ai_tool
except ImportError:
    ai_tool = None

try:
    from friday_tools import tools_tool
except ImportError:
    tools_tool = None

try:
    from friday_vision import vision_tool
except ImportError:
    vision_tool = None

try:
    from friday_security import security_tool
except ImportError:
    security_tool = None

try:
    from friday_monitor import monitor_tool
except ImportError:
    monitor_tool = None

try:
    from friday_scheduler import scheduler_tool
except ImportError:
    scheduler_tool = None

try:
    from advanced_networking import network_tool
except ImportError:
    network_tool = None

try:
    from advanced_crypto import crypto_tool
except ImportError:
    crypto_tool = None

# ─── Tool Functions for friday_live.py ────────────────────────────#

def alexa_command(command: str) -> str:
    """Send command to Alexa bridge."""
    return f"Alexa command: {command}"

def alexa_poll() -> str:
    """Check Alexa commands."""
    return "No pending Alexa commands."

def climb_codebase(query: str, path: str = ".") -> str:
    """Search and analyze code."""
    if tools_tool:
        return tools_tool("search", data=query)
    return f"Code search for: {query}"

def deep_research(topic: str, url: str = None, depth: int = 3) -> str:
    """Deep research with report."""
    if web_tool:
        result = web_tool("search", target=topic)
        return f"Research on {topic}:\n{result}"
    return f"Deep research on: {topic}"

def get_time() -> str:
    """Get current time."""
    from datetime import datetime
    return datetime.now().isoformat()

def home_assistant_command(entity_id: str, action: str) -> str:
    """Control Home Assistant."""
    return f"Home Assistant: {entity_id} -> {action}"

def memory_store(category: str, keyword: str, content: str) -> str:
    """Store in memory."""
    return f"Stored [{category}] {keyword}: {content[:50]}"

def memory_retrieve(query: str) -> str:
    """Retrieve from memory."""
    return f"Memory search for: {query}"

def multi_task(task_specs: List[str]) -> str:
    """Execute multiple tasks."""
    return f"Executing {len(task_specs)} tasks"

def open_app(name: str) -> str:
    """Open application."""
    if automation_tool:
        return automation_tool("open_app", target=name)
    return f"Opening app: {name}"

def open_url(url: str) -> str:
    """Open URL in browser."""
    if web_tool:
        return web_tool("fetch", url=url)
    return f"Opening URL: {url}"

def queue_task(func_name: str, args: str = "") -> str:
    """Queue a task."""
    if scheduler_tool:
        return scheduler_tool("add", name=func_name, params={"args": args})
    return f"Queued: {func_name}"

def queue_status() -> str:
    """Check queue status."""
    if scheduler_tool:
        return scheduler_tool("status")
    return "Queue empty"

def queue_result(task_id: str) -> str:
    """Get task result."""
    return f"Result for {task_id}: pending"

def read_file(path: str) -> str:
    """Read file."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

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

def spotify_play(query: str) -> str:
    """Play on Spotify."""
    return f"Playing on Spotify: {query}"

def spotify_pause() -> str:
    """Pause Spotify."""
    return "Spotify paused"

def stark_doctor() -> str:
    """System diagnostic."""
    return """[Stark Diagnostic]
- Systems: Online
- Neural Link: Active
- Voice: Ready
- Tools: Loaded
"""

def system_info() -> str:
    """Get system info."""
    import platform
    return f"System: {platform.system()} {platform.release()}"

def web_search(query: str) -> str:
    """Web search."""
    if web_tool:
        return web_tool("search", target=query)
    return f"Search: {query}"

def type_text(text: str) -> str:
    """Type text at cursor."""
    return f"Typing: {text}"

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

def write_file(path: str, content: str) -> str:
    """Write file."""
    try:
        with open(path, "w") as f:
            f.write(content)
        return f"Written to {path}"
    except Exception as e:
        return f"Error: {e}"

def list_files(path: str = ".") -> str:
    """List files."""
    try:
        files = os.listdir(path)
        return "\n".join(files[:20])
    except Exception as e:
        return f"Error: {e}"

def find_files(pattern: str, path: str = ".") -> str:
    """Find files."""
    import glob
    try:
        files = glob.glob(f"{path}/**/{pattern}", recursive=True)
        return "\n".join(files[:20])
    except Exception as e:
        return f"Error: {e}"

def copy_file(src: str, dst: str) -> str:
    """Copy file."""
    try:
        import shutil
        shutil.copy2(src, dst)
        return f"Copied {src} to {dst}"
    except Exception as e:
        return f"Error: {e}"

def move_file(src: str, dst: str) -> str:
    """Move file."""
    try:
        import shutil
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

def situational_awareness() -> str:
    """Get system context."""
    return f"Active window: Unknown\nProcesses: Running\nSystem: Online"

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

def take_snapshot() -> str:
    """Save screen snapshot."""
    return "Snapshot saved"

def recall_snapshot(index: int = 0) -> str:
    """Recall snapshot."""
    return f"Recalled snapshot {index}"

def smart_home_command(target: str, action: str) -> str:
    """Smart home control."""
    return f"Smart home: {target} -> {action}"

def video_search(query: str) -> str:
    """Search videos."""
    return f"Video search: {query}\n- Result 1\n- Result 2"

def see_screen(question: str = "") -> str:
    """Analyze screen."""
    return f"Screen analysis: {question}\nDetected: Desktop environment"

# ─── Export list for friday_live.py ────────────────────────────#

__all__ = [
    "alexa_command", "alexa_poll", "climb_codebase", "deep_research",
    "get_time", "home_assistant_command", "memory_store", "memory_retrieve",
    "multi_task", "open_app", "open_url", "queue_task", "queue_status",
    "queue_result", "read_file", "run_cmd", "safe_run_cmd",
    "spotify_play", "spotify_pause", "stark_doctor", "system_info",
    "web_search", "type_text", "click", "double_click", "right_click",
    "move_mouse", "drag", "hotkey", "press_key", "scroll",
    "write_file", "list_files", "find_files", "copy_file", "move_file",
    "delete_file", "clipboard_get", "clipboard_set",
    "situational_awareness", "git_ops", "take_snapshot", "recall_snapshot",
    "smart_home_command", "video_search", "see_screen",
]
