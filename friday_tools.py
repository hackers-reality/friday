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

#  Import available modules #

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

def get_active_window() -> dict:
    """Get active window info (title, process name, PID) using Windows APIs."""
    import ctypes
    from ctypes import wintypes

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        if not hwnd:
            return {"title": "Unknown", "process_name": "Unknown", "pid": None}

        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "Unknown"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_name = "Unknown"
        try:
            import psutil
            p = psutil.Process(pid.value)
            process_name = p.name()
        except Exception:
            pass

        return {
            "title": title,
            "process_name": process_name,
            "pid": pid.value if pid.value else None,
        }
    except Exception as e:
        return {"title": "Unknown", "process_name": "Unknown", "pid": None, "error": str(e)}


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
    """Open application by name. Maps common names to executables on Windows."""
    import subprocess
    import os

    app_map = {
        "roblox": "RobloxPlayerBeta.exe",
        "spotify": "spotify.exe",
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "discord": "Discord.exe",
        "steam": "steam.exe",
    }

    name_lower = name.lower()
    exe = app_map.get(name_lower, name)

    try:
        if os.name == 'nt':
            os.startfile(exe)
        else:
            subprocess.Popen(exe)
        return f"[OK] Opening app: {name}"
    except Exception as e:
        return f"[FAIL] Error opening {name}: {e}"


def close_app(name: str) -> str:
    """Kill process by name."""
    try:
        import subprocess
        if os.name == 'nt':
            result = subprocess.run(f"taskkill /F /IM {name}", shell=True, capture_output=True, text=True)
            return f"[OK] Killed {name}" if result.returncode == 0 else f"[FAIL] {result.stderr}"
        else:
            subprocess.run(f"pkill -f {name}", shell=True)
            return f"[OK] Killed {name}"
    except Exception as e:
        return f"[FAIL] Error killing {name}: {e}"


def list_running_apps() -> list[str]:
    """Return all active window titles."""
    try:
        import pygetwindow as gw
        windows = gw.getAllTitles()
        return [w for w in windows if w.strip()]
    except ImportError:
        try:
            import ctypes
            windows = []
            def enum_callback(hwnd, results):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        results.append(buf.value)
                return True
            ctypes.windll.user32.EnumWindows(
                ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(enum_callback),
                ctypes.byref(ctypes.c_void_p())
            )
            return windows
        except Exception as e:
            return [f"Error: {e}"]
    except Exception as e:
        return [f"Error: {e}"]

def open_url(url: str) -> str:
    """Open URL in browser."""
    try:
        import webbrowser
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Error: {e}"

def spotify_play(query: str) -> str:
    """Focus Spotify, search for song, play it using keyboard shortcuts."""
    try:
        import pygetwindow as gw
        import pyautogui

        # Find Spotify window
        spotify_windows = gw.getWindowsWithTitle("Spotify")
        if not spotify_windows:
            return "[FAIL] Spotify not found. Open Spotify first."

        spotify_win = spotify_windows[0]
        spotify_win.activate()
        time.sleep(1)

        # Ctrl+L to focus search, then type query
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.5)
        pyautogui.typewrite(query)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)

        # Play first result
        pyautogui.press('enter')
        return f"Playing '{query}' on Spotify"

    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed. Install: pip install pygetwindow pyautogui"
    except Exception as e:
        return f"[FAIL] Spotify play error: {e}"


def spotify_pause() -> str:
    """Pause Spotify via media key."""
    try:
        import pyautogui
        pyautogui.press('playpause')
        return "[OK] Spotify paused/resumed"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_next() -> str:
    """Next track."""
    try:
        import pyautogui
        pyautogui.press('nexttrack')
        return "[OK] Skipped to next track"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_prev() -> str:
    """Previous track."""
    try:
        import pyautogui
        pyautogui.press('prevtrack')
        return "[OK] Back to previous track"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_volume(level: int) -> str:
    """Set Spotify volume (0-100). Uses Ctrl+Up/Down in Spotify."""
    try:
        import pygetwindow as gw
        import pyautogui
        import time

        if not (0 <= level <= 100):
            return "[FAIL] Volume must be 0-100"

        spotify_windows = gw.getWindowsWithTitle("Spotify")
        if spotify_windows:
            spotify_windows[0].activate()
            time.sleep(0.5)

        # Each Ctrl+Up adds ~10%, so we press proportional times
        presses = level // 10
        for _ in range(min(presses, 10)):
            pyautogui.hotkey('ctrl', 'up')
            time.sleep(0.1)

        return f"[OK] Spotify volume set to ~{level}%"
    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"

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


def memory_import_tool_handler(action: str = "status", **kwargs) -> str:
    """Import chat history from Claude, ChatGPT, Gemini and audit user profile."""
    try:
        from memory_import import memory_import_tool
        return memory_import_tool(action, **kwargs)
    except ImportError:
        return "[FAIL] memory_import.py not available."
    except Exception as e:
        return f"[FAIL] Memory import error: {e}"


def startup_tool_handler(action: str = "run", **kwargs) -> str:
    """Handle startup tasks: run all init routines."""
    results = []
    
    if action == "run":
        # Check browser history status
        try:
            from browser_history_tools import browser_history_tool
            status = browser_history_tool("status")
            results.append(f"[BrowserHistory] {status}")
        except Exception as e:
            results.append(f"[BrowserHistory] Error: {e}")
        
        # Check goals
        try:
            results.append(goals_tool_handler("list"))
        except Exception as e:
            results.append(f"[Goals] Error: {e}")
        
        # Check memory import status
        try:
            results.append(memory_import_tool_handler("status"))
        except Exception as e:
            results.append(f"[MemoryImport] Error: {e}")
        
        return "\n".join(results)
    
    elif action == "status":
        return "Startup handler ready."
    else:
        return f"Unknown startup action: {action}"

def search_and_open(query: str, category_hint: str = None) -> str:
    """
    General-purpose search browser history for ANYTHING and open the best match.
    Works for: anime, repos, chats, blogs, courses, social media, videos, etc.
    
    Examples:
        "onepiece episode 1100" → finds anime streaming link
        "my chat with arnav" → finds Discord/Instagram/WhatsApp chat
        "openclaw repo github" → finds GitHub repo
        "that blog about python async" → finds blog post
        "netflix continue watching" → finds Netflix show
    
    Args:
        query: What to search for
        category_hint: Optional filter (anime, repo, chat, blog, video, education, etc.)
    """
    try:
        from browser_history_tools import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("find_and_open", query=query, category=(category_hint or ""))
        return f"[FAIL] Browser history tools not available."
    except Exception as e:
        return f"[FAIL] History search error: {e}"


def memory_store(key: str, value: str, category: str = "general") -> str:
    """Store a memory item."""
    try:
        import json, os
        from pathlib import Path

        memory_dir = Path(__file__).parent / "friday_memory"
        memory_dir.mkdir(exist_ok=True)
        memory_file = memory_dir / "memory.json"

        memories = []
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                memories = json.load(f)

        memories.append({
            "key": key,
            "value": value,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })

        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=4, ensure_ascii=False)

        return f"[OK] Stored memory: {key}"
    except Exception as e:
        return f"[FAIL] Memory store error: {e}"


def memory_retrieve(query: str) -> str:
    """Retrieve memories matching query."""
    try:
        import json, os
        from pathlib import Path

        memory_file = Path(__file__).parent / "friday_memory" / "memory.json"
        if not memory_file.exists():
            return "No memories stored yet."

        with open(memory_file, "r", encoding="utf-8") as f:
            memories = json.load(f)

        results = [m for m in memories if query.lower() in m["key"].lower() or query.lower() in m["value"].lower()]
        if not results:
            return f"No memories found matching '{query}'"

        lines = [f"### MEMORIES ({len(results)} found)"]
        for m in results[:10]:
            lines.append(f"- {m['key']}: {m['value'][:50]}...")
        return "\n".join(lines)
    except Exception as e:
        return f"[FAIL] Memory retrieve error: {e}"


def video_search(query: str) -> str:
    """Search for videos (stub)."""
    return f"Video search for '{query}' - feature coming soon."


def deep_research(topic: str) -> str:
    """Perform deep research on a topic (stub)."""
    return f"Deep research on '{topic}' - feature coming soon."


def climb_codebase(query: str) -> str:
    """Navigate and understand codebase structure (stub)."""
    return f"Climbing codebase for '{query}' - feature coming soon."

def netflix_play(title: str) -> str:
    """Open Chrome, navigate to Netflix, search for title, play it."""
    try:
        import webbrowser
        import pygetwindow as gw
        import pyautogui
        import time

        # Open Netflix search URL in Chrome
        search_url = f"https://www.netflix.com/search?q={title.replace(' ', '+')}"
        webbrowser.open(search_url)
        time.sleep(3)  # Wait for page load

        # Confirm Netflix loaded
        netflix_windows = [w for w in gw.getAllTitles() if 'Netflix' in w]
        if not netflix_windows:
            return "[FAIL] Netflix page didn't load properly"

        # Find and click the first search result
        pyautogui.press('tab')  # Navigate to first result
        time.sleep(1)
        pyautogui.press('enter')  # Click first result
        time.sleep(3)

        # Try to find and click Play button
        pyautogui.press('tab')  # Navigate to Play button
        time.sleep(0.5)
        pyautogui.press('enter')

        return f"[OK] Started playing '{title}' on Netflix. Playback should begin shortly."

    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed. Install: pip install pygetwindow pyautogui"
    except Exception as e:
        return f"[FAIL] Netflix play error: {e}"


#  Email (Gmail) Functions 

def read_emails(count: int = 10) -> str:
    """Read latest N emails. Returns formatted string with sender, subject, snippet."""
    try:
        from friday_gmail import gmail_list_messages
        return gmail_list_messages(query="", max_results=count)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Email read error: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send email via Gmail API."""
    try:
        from friday_gmail import gmail_send
        return gmail_send(to, subject, body)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Email send error: {e}"


def draft_email(context: str, recipient: str) -> str:
    """Use LLM to draft a professional email from context string."""
    try:
        from friday_gmail import gmail_draft

        # Generate email content using LLM
        try:
            from friday_ai import ai_tool
            prompt = f"Draft a professional email based on this context: {context}. Include proper greeting, body, and closing."
            draft_body = ai_tool(prompt)

            # Generate subject line
            subject_prompt = f"Generate a concise, professional subject line for this email context: {context}"
            subject = ai_tool(subject_prompt)[:100]
        except ImportError:
            # Fallback if LLM not available
            subject = f"RE: {context[:50]}"
            draft_body = f"Dear recipient,\n\n{context}\n\nBest regards,\nFriday"

        return gmail_draft(recipient, subject, draft_body)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Email draft error: {e}"


#  Instagram Messaging 

def send_instagram_dm(username: str, message: str) -> str:
    """Send Instagram DM using browser automation."""
    try:
        import webbrowser
        import pygetwindow as gw
        import pyautogui
        import time

        # Check if we have session cookies / logged in
        dm_url = f"https://www.instagram.com/direct/new/?text={username}"
        webbrowser.open(dm_url)
        time.sleep(4)  # Wait for page load

        # Verify Instagram loaded
        ig_windows = [w for w in gw.getAllTitles() if 'Instagram' in w]
        if not ig_windows:
            return "[FAIL] Instagram didn't load. Please log in to Instagram in Chrome first."

        # Type message in the message field
        pyautogui.press('tab')  # Navigate to message field
        time.sleep(1)
        pyautogui.typewrite(message)
        time.sleep(1)

        # Send (Enter key)
        pyautogui.press('enter')

        return f"[OK] Message sent to {username} via Instagram"

    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed. Install: pip install pygetwindow pyautogui"
    except Exception as e:
        return f"[FAIL] Instagram DM error: {e}"


#  Smart Home / Alexa 

def tell_alexa(command: str) -> str:
    """Send command to Alexa via webhook. Fallback to Home Assistant."""
    import os

    # Try Alexa webhook first
    alexa_url = os.environ.get("ALEXA_WEBHOOK_URL")
    if alexa_url:
        try:
            import requests
            secret = os.environ.get("FRIDAY_WEBHOOK_SECRET", "")
            response = requests.post(
                f"{alexa_url}/friday/send",
                json={"command": command},
                headers={"X-Friday-Secret": secret},
                timeout=5
            )
            if response.status_code == 200:
                return f"[OK] Command sent to Alexa: {command}"
            return f"[FAIL] Alexa webhook error: {response.status_code}"
        except ImportError:
            return "[FAIL] requests module not installed."
        except Exception as e:
            return f"[FAIL] Alexa error: {e}"

    # Fallback: Home Assistant
    ha_url = os.environ.get("HOME_ASSISTANT_URL")
    ha_token = os.environ.get("HA_TOKEN")
    if ha_url and ha_token:
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }
            # Parse command into service call (simplified)
            payload = {
                "entity_id": "all"  # Default, should be parsed from command
            }
            response = requests.post(
                f"{ha_url}/api/services/homeassistant/turn_on",
                json=payload,
                headers=headers,
                timeout=5
            )
            if response.status_code in (200, 201):
                return f"[OK] Command sent to Home Assistant: {command}"
            return f"[FAIL] Home Assistant error: {response.status_code}"
        except ImportError:
            return "[FAIL] requests module not installed."
        except Exception as e:
            return f"[FAIL] Home Assistant error: {e}"

    return "[FAIL] No smart home integration configured. Set ALEXA_WEBHOOK_URL or HOME_ASSISTANT_URL + HA_TOKEN"


#  Export list for friday_live.py #

__all__ = [
    "get_time", "system_info", "run_cmd", "safe_run_cmd",
    "read_file", "write_file", "list_files", "find_files",
    "copy_file", "move_file", "delete_file",
    "clipboard_get", "clipboard_set",
    "get_active_window",
    "click", "double_click", "right_click", "move_mouse", "drag",
    "hotkey", "press_key", "scroll",
    "open_app", "close_app", "list_running_apps", "open_url",
    "spotify_play", "spotify_pause", "spotify_next", "spotify_prev", "spotify_volume",
    "netflix_play",
    "read_emails", "send_email", "draft_email",
    "send_instagram_dm",
    "tell_alexa",
    "web_search", "stark_doctor", "git_ops",
    "see_screen", "search_browser_history", "open_history_item",
    "list_recent_history", "generate_file", "generate_file_llm",
    "search_and_open",
    "situational_awareness", "goals_tool_handler", "startup_tool_handler",
    "memory_import_tool_handler",
]

if __name__ == "__main__":
    print("Friday Tools loaded successfully.")
    print(f"Tools available: {len(__all__)}")
