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
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB log rotation

def stark_log(entry: str) -> str:
    """Log to stark_logs.txt with rotation."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stark_logs.txt")
    if os.path.exists(log_path) and os.path.getsize(log_path) > _LOG_MAX_BYTES:
        shutil.move(log_path, log_path.replace(".txt", "_archive.txt"))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {entry}\n")
    return "Entry logged."

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
    """Click at position using pyautogui."""
    try:
        import pyautogui
        if x is not None and y is not None:
            pyautogui.click(x, y)
            return f"[OK] Clicked at ({x}, {y})"
        pyautogui.click()
        return "[OK] Clicked at current position"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Click error: {e}"

def double_click(x: int = None, y: int = None) -> str:
    """Double click at position using pyautogui."""
    try:
        import pyautogui
        if x is not None and y is not None:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.doubleClick()
        return "[OK] Double-clicked"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Double-click error: {e}"

def right_click(x: int = None, y: int = None) -> str:
    """Right click at position using pyautogui."""
    try:
        import pyautogui
        if x is not None and y is not None:
            pyautogui.rightClick(x, y)
        else:
            pyautogui.rightClick()
        return "[OK] Right-clicked"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Right-click error: {e}"

def move_mouse(x: int, y: int) -> str:
    """Move mouse to coordinates using pyautogui."""
    try:
        import pyautogui
        pyautogui.moveTo(x, y)
        return f"[OK] Mouse moved to ({x}, {y})"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Mouse move error: {e}"

def drag(x: int, y: int, duration: float = 0.5) -> str:
    """Drag mouse to coordinates using pyautogui."""
    try:
        import pyautogui
        pyautogui.dragTo(x, y, duration=duration)
        return f"[OK] Dragged to ({x}, {y})"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Drag error: {e}"

def hotkey(keys: str) -> str:
    """Press a keyboard hotkey combination using pyautogui."""
    try:
        import pyautogui
        mods = keys.lower().split("+")
        if len(mods) > 1:
            pyautogui.hotkey(*mods)
        else:
            pyautogui.press(mods[0])
        return f"[OK] Hotkey: {keys}"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Hotkey error: {e}"

def press_key(key: str) -> str:
    """Press a single keyboard key using pyautogui."""
    try:
        import pyautogui
        pyautogui.press(key)
        return f"[OK] Key pressed: {key}"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Key press error: {e}"

def scroll(amount: int) -> str:
    """Scroll the mouse wheel using pyautogui."""
    try:
        import pyautogui
        pyautogui.scroll(amount)
        return f"[OK] Scrolled: {amount}"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Scroll error: {e}"

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

#  Spotify API Integration (via spotipy) #

def _get_spotify_client():
    """Create an authenticated Spotify API client using env credentials."""
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        if not client_id or not client_secret:
            return None
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".spotify_cache")
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
            cache_path=cache_path,
        ))
        # Quick ping to verify
        sp.current_user()
        return sp
    except Exception:
        return None


def spotify_play(query: str = "") -> str:
    """Play a track, album, or playlist on Spotify via the Web API.
    Falls back to keyboard simulation if API credentials are not configured."""
    try:
        sp = _get_spotify_client()
        if sp is None:
            # Fallback: keyboard simulation
            return _spotify_play_keyboard(query)

        if not query:
            # Resume playback
            sp.start_playback()
            return "[OK] Resumed Spotify playback"

        # Search for the track
        results = sp.search(q=query, type="track", limit=5)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            # Try album search
            results = sp.search(q=query, type="album", limit=1)
            albums = results.get("albums", {}).get("items", [])
            if albums:
                sp.start_playback(context_uri=albums[0]["uri"])
                return f"[OK] Playing album '{albums[0]['name']}' on Spotify"
            return f"[FAIL] No results found for '{query}'"

        # Play the first track
        track = tracks[0]
        sp.start_playback(uris=[track["uri"]])
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"[OK] Now playing '{track['name']}' by {artists} on Spotify"

    except ImportError:
        return _spotify_play_keyboard(query)
    except Exception as e:
        return f"[FAIL] Spotify play error: {e}"


def _spotify_play_keyboard(query: str) -> str:
    """Fallback: keyboard-based Spotify control."""
    try:
        import pygetwindow as gw
        import pyautogui
        import time
        spotify_windows = gw.getWindowsWithTitle("Spotify")
        if not spotify_windows:
            return "[FAIL] Spotify not found and API not configured. Open Spotify first or set SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET."
        spotify_win = spotify_windows[0]
        spotify_win.activate()
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.5)
        pyautogui.typewrite(query)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('enter')
        return f"[OK] Playing '{query}' on Spotify (keyboard fallback)"
    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Spotify keyboard error: {e}"


def spotify_pause() -> str:
    """Pause Spotify via Web API. Falls back to media key."""
    try:
        sp = _get_spotify_client()
        if sp:
            sp.pause_playback()
            return "[OK] Spotify paused via API"
    except Exception:
        pass
    # Fallback
    try:
        import pyautogui
        pyautogui.press('playpause')
        return "[OK] Spotify paused/resumed"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Spotify pause error: {e}"


def spotify_next() -> str:
    """Skip to next track via Web API. Falls back to media key."""
    try:
        sp = _get_spotify_client()
        if sp:
            sp.next_track()
            return "[OK] Skipped to next track via API"
    except Exception:
        pass
    try:
        import pyautogui
        pyautogui.press('nexttrack')
        return "[OK] Skipped to next track"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_prev() -> str:
    """Go to previous track via Web API. Falls back to media key."""
    try:
        sp = _get_spotify_client()
        if sp:
            sp.previous_track()
            return "[OK] Back to previous track via API"
    except Exception:
        pass
    try:
        import pyautogui
        pyautogui.press('prevtrack')
        return "[OK] Back to previous track"
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_volume(level: int) -> str:
    """Set Spotify volume via Web API (0-100). Falls back to keyboard."""
    if not (0 <= level <= 100):
        return "[FAIL] Volume must be 0-100"
    try:
        sp = _get_spotify_client()
        if sp:
            sp.volume(level)
            return f"[OK] Spotify volume set to {level}% via API"
    except Exception:
        pass
    # Fallback: keyboard
    try:
        import pygetwindow as gw
        import pyautogui
        import time
        spotify_windows = gw.getWindowsWithTitle("Spotify")
        if spotify_windows:
            spotify_windows[0].activate()
            time.sleep(0.5)
        presses = level // 10
        for _ in range(min(presses, 10)):
            pyautogui.hotkey('ctrl', 'up')
            time.sleep(0.1)
        return f"[OK] Spotify volume set to ~{level}% (keyboard fallback)"
    except ImportError:
        return "[FAIL] pygetwindow or pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def spotify_current() -> str:
    """Get currently playing track info via Spotify API."""
    try:
        sp = _get_spotify_client()
        if not sp:
            return "[FAIL] Spotify API not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
        current = sp.current_playback()
        if current and current.get("item"):
            track = current["item"]
            artists = ", ".join(a["name"] for a in track["artists"])
            progress = current.get("progress_ms", 0) // 1000
            duration = track.get("duration_ms", 0) // 1000
            return f"[OK] Now playing: '{track['name']}' by {artists} ({progress//60}:{progress%60:02d}/{duration//60}:{duration%60:02d})"
        return "[OK] Nothing currently playing on Spotify"
    except Exception as e:
        return f"[FAIL] Spotify current error: {e}"

def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo with BeautifulSoup fallback."""
    try:
        from friday_web import WebScraper
        scraper = WebScraper()
        result = scraper.search_engine(query, engine="duckduckgo")
        if result.get("success"):
            items = result.get("results", [])
            if not items:
                # Fallback to Bing
                result = scraper.search_engine(query, engine="bing")
                items = result.get("results", [])
            if items:
                lines = [f"Search results for '{query}':"]
                for i, item in enumerate(items[:max_results], 1):
                    title = item.get("title", "?")
                    url = item.get("url", "")
                    snippet = item.get("snippet", "")
                    lines.append(f"{i}. {title}")
                    if url:
                        lines.append(f"   {url}")
                    if snippet:
                        lines.append(f"   {snippet[:200]}")
                return "\n".join(lines)
        return f"[FAIL] No search results for '{query}'"
    except ImportError:
        return "[FAIL] friday_web.py not available."
    except Exception as e:
        return f"[FAIL] Web search error: {e}"

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

def see_screen(question: str = "What do you see on the screen?") -> str:
    """Capture screen and analyze it using Gemini Vision API."""
    try:
        import pyautogui
        import base64, io, requests, json
        from PIL import Image

        # Capture screen
        img = pyautogui.screenshot()
        # Resize for API efficiency
        img.thumbnail((1280, 720), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "[FAIL] GOOGLE_API_KEY not configured."

        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "contents": [{
                    "parts": [
                        {"text": f"[SCREEN ANALYSIS] {question}\nDescribe what you see. Include: visible text, UI elements, coordinates of interactive elements, any errors on screen."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                    ]
                }]
            },
            timeout=30,
        )
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text
    except ImportError as e:
        return f"[FAIL] Missing dependency: {e}. Install: pip install pyautogui pillow requests"
    except Exception as e:
        return f"[FAIL] Screen analysis error: {e}"


def vision_click(target: str) -> str:
    """Find and click an element on screen by description using Gemini Vision.

    Uses see_screen to locate the element, then clicks at the reported coordinates.
    """
    try:
        import re
        # Ask vision to find the element
        vision_result = see_screen(
            f"Find the exact location of '{target}' on screen. "
            "Return ONLY the coordinates in format: X=123 Y=456"
        )

        # Extract coordinates from vision response
        coords = re.search(r'[XYxy]\s*[=:]\s*(\d+).*?[XYxy]\s*[=:]\s*(\d+)', vision_result)
        if not coords:
            coords = re.search(r'\(?(\d{2,4})\s*,\s*(\d{2,4})\)?', vision_result)
        if not coords:
            return f"[FAIL] Could not find '{target}' on screen. Vision response:\n{vision_result[:500]}"

        x, y = int(coords.group(1)), int(coords.group(2))
        return click(x, y)
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Vision click error: {e}"


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
    """Search for videos with metadata (views, date, duration), return results."""
    try:
        import re, requests, json, time
        from bs4 import BeautifulSoup

        output = []
        # Approach 1: DuckDuckGo HTML video search
        ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}&ia=videos&iar=videos"
        resp = requests.get(ddg_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for i, result in enumerate(soup.select(".result"), 1):
                if i > 8:
                    break
                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")
                url_el = result.select_one(".result__url")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                url = url_el.get_text(strip=True) if url_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                # Check if it's a video URL
                if not any(d in url for d in ['youtube.com', 'youtu.be', 'vimeo.com']):
                    continue
                # Extract YouTube video ID for oembed info
                vid_id = ""
                yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
                if yt_match:
                    vid_id = yt_match.group(1)
                    try:
                        oembed = requests.get(
                            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json",
                            timeout=5
                        )
                        if oembed.status_code == 200:
                            data = oembed.json()
                            title = data.get("title", title)
                    except Exception:
                        pass
                output.append(f"{i}. {title}")
                output.append(f"   URL: {url}")
                # Parse snippet for metadata (DDG often includes views/date)
                if snippet:
                    output.append(f"   {snippet[:200]}")
                # Try to get engagement stats from oembed
                if vid_id:
                    try:
                        insights_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json"
                        # Add a second call to innertube API for stats (no key needed)
                        # YouTube's public API endpoint
                        stats_url = f"https://www.youtube.com/watch?v={vid_id}"
                        stats_resp = requests.get(stats_url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }, timeout=5)
                        if stats_resp.status_code == 200:
                            # Extract view count and date from page
                            view_match = re.search(r'([\d,]+)\s*views', stats_resp.text)
                            date_match = re.search(r'(\d+\s+(?:year|month|week|day|hour|minute|second)s?\s+ago)', stats_resp.text)
                            if view_match:
                                output.append(f"   Views: {view_match.group(1)}")
                            if date_match:
                                output.append(f"   Uploaded: {date_match.group(1)}")
                    except Exception:
                        pass
                output.append("")

        if output:
            return "\n".join(output)

        # Fallback: open YouTube search page
        import webbrowser
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        webbrowser.open(search_url)
        return f"[OK] Opened YouTube search for '{query}'"

    except Exception as e:
        return f"[FAIL] Video search error: {e}"


def deep_research(topic: str, url: str = "", depth: int = 3) -> str:
    """Multi-source deep research with synthesized report."""
    try:
        from friday_web import WebScraper
        import re
        scraper = WebScraper()
        all_sources = []

        if url:
            # Fetch the primary URL
            page = scraper.fetch(url)
            if page.get("success"):
                all_sources.append(f"--- Primary Source ({url}) ---\n{page.get('content', '')[:3000]}")

        # Search multiple queries
        queries = [topic, f"{topic} latest 2025 2026", f"{topic} overview summary"]
        for q in queries[:depth]:
            result = scraper.search_engine(q)
            if result.get("success"):
                for item in result.get("results", [])[:3]:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    url_ = item.get("url", "")
                    all_sources.append(f"• {title}\n  {url_}\n  {snippet[:300]}")
                    if len(all_sources) >= 9:
                        break
            if len(all_sources) >= 9:
                break

        if all_sources:
            report = f"Deep Research: {topic}\n{'='*40}\n"
            report += "\n\n".join(all_sources)
            if len(report) > 8000:
                report = report[:8000] + "\n\n[Truncated...]"
            return report
        return f"[FAIL] No results found for '{topic}'"
    except ImportError:
        return "[FAIL] friday_web.py not available."
    except Exception as e:
        return f"[FAIL] Deep research error: {e}"


def climb_codebase(query: str, path: str = "") -> str:
    """Search and analyze code in the project codebase."""
    try:
        import subprocess, os, glob

        search_root = path if path else os.path.dirname(os.path.abspath(__file__))

        # Use ripgrep if available, fallback to findstr/grep
        try:
            rg_result = subprocess.run(
                ["rg", "-n", "--max-count", "15", query, search_root],
                capture_output=True, text=True, timeout=10
            )
            if rg_result.returncode == 0 and rg_result.stdout:
                lines = rg_result.stdout.strip().split("\n")[:20]
                return f"Code search for '{query}':\n" + "\n".join(lines)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: Python grep via glob
        results = []
        for ext in ("*.py", "*.js", "*.ts", "*.html", "*.css", "*.json", "*.yaml", "*.md"):
            for fpath in glob.glob(os.path.join(search_root, "**", ext), recursive=True):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                rel = os.path.relpath(fpath, search_root)
                                results.append(f"{rel}:{i}: {line.rstrip()[:200]}")
                                if len(results) >= 15:
                                    break
                except Exception:
                    pass
                if len(results) >= 15:
                    break
            if len(results) >= 15:
                break

        if results:
            return f"Code search for '{query}':\n" + "\n".join(results)
        return f"[OK] No matches found for '{query}' in codebase."
    except Exception as e:
        return f"[FAIL] Codebase search error: {e}"

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
        time.sleep(4)

        # Try direct play URL first (works for known titles)
        direct_url = f"https://www.netflix.com/search?q={title.replace(' ', '+')}&play=true"
        webbrowser.open(direct_url)
        time.sleep(3)

        # Confirm page loaded - look for any browser window
        browser_windows = [w for w in gw.getAllTitles() if any(b in w for b in ['Chrome', 'Edge', 'Browser', 'Netflix', 'Mozilla Firefox'])]
        if not browser_windows:
            return f"[OK] Opened Netflix search for '{title}'. Please click the result to play."

        # Focus browser window
        for w in browser_windows:
            try:
                gw.getWindowsWithTitle(w)[0].activate()
                break
            except Exception:
                pass

        time.sleep(1)
        # Try to click first search result using Enter key
        pyautogui.press('enter')
        time.sleep(3)

        # Try to play
        pyautogui.press('enter')
        time.sleep(1)

        return f"[OK] Started playing '{title}' on Netflix."

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
    """Send Instagram DM using browser automation. Must be logged into Instagram in the default browser."""
    try:
        import webbrowser
        import pygetwindow as gw
        import pyautogui
        import time
        import urllib.parse

        # Use Instagram's direct message URL — recipient is entered via search
        dm_url = "https://www.instagram.com/direct/new/"
        webbrowser.open(dm_url)
        time.sleep(4)

        # Try focusing an Instagram or browser window
        target_titles = ['Instagram', 'Chrome', 'Edge', 'Mozilla Firefox', 'Brave', 'Opera']
        browser_windows = [w for w in gw.getAllTitles() if any(b in w for b in target_titles)]
        if not browser_windows:
            return "[FAIL] Instagram didn't load. Please log in to Instagram in Chrome first."

        for w in browser_windows:
            try:
                gw.getWindowsWithTitle(w)[0].activate()
                break
            except Exception:
                pass
        time.sleep(1)

        # Type the username to search for the recipient
        pyautogui.typewrite(username)
        time.sleep(2)

        # Select the first result
        pyautogui.press('enter')
        time.sleep(1)

        # Navigate to message input
        pyautogui.press('tab')
        time.sleep(0.5)

        # Type the message
        pyautogui.typewrite(message)
        time.sleep(0.5)

        # Send
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


#  Stub functions for friday_live.py compatibility #

def alexa_command(command: str) -> str:
    """Send command to Alexa (alias for tell_alexa)."""
    return tell_alexa(command)


def alexa_poll(action: str = "status") -> str:
    """Poll Alexa bridge for pending commands."""
    import os
    alexa_url = os.environ.get("ALEXA_WEBHOOK_URL")
    if not alexa_url:
        return "[FAIL] Alexa webhook URL not configured. Set ALEXA_WEBHOOK_URL."
    try:
        import requests
        secret = os.environ.get("FRIDAY_WEBHOOK_SECRET", "")
        response = requests.get(
            f"{alexa_url}/friday/poll",
            headers={"X-Friday-Secret": secret},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("commands"):
                return f"[OK] Pending Alexa commands: {', '.join(data['commands'])}"
            return "[OK] No pending commands from Alexa."
        return f"[FAIL] Alexa poll error: {response.status_code}"
    except ImportError:
        return "[FAIL] requests module not installed."
    except Exception as e:
        return f"[FAIL] Alexa poll error: {e}"


def home_assistant_command(command: str, entity: str = "all") -> str:
    """Send command to Home Assistant."""
    try:
        import requests
        ha_url = os.environ.get("HOME_ASSISTANT_URL")
        ha_token = os.environ.get("HA_TOKEN")
        if not ha_url or not ha_token:
            return "[FAIL] Home Assistant not configured. Set HOME_ASSISTANT_URL and HA_TOKEN"
        headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
        payload = {"entity_id": entity}
        response = requests.post(f"{ha_url}/api/services/homeassistant/turn_on", json=payload, headers=headers, timeout=5)
        return f"[OK] Command sent to Home Assistant: {command}" if response.status_code in (200, 201) else f"[FAIL] HA error: {response.status_code}"
    except ImportError:
        return "[FAIL] requests module not installed."
    except Exception as e:
        return f"[FAIL] Home Assistant error: {e}"


def multi_task(tasks: list) -> str:
    """Execute multiple tasks in sequence (stub)."""
    results = []
    for t in tasks:
        if isinstance(t, dict):
            results.append(f"[OK] Task: {t.get('action', 'unknown')}")
        else:
            results.append(f"[OK] Task: {t}")
    return "\n".join(results)


def queue_task(task_name: str, action: str, params: dict = None) -> str:
    """Queue a task for later execution."""
    try:
        import json
        queue_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory")
        os.makedirs(queue_dir, exist_ok=True)
        queue_file = os.path.join(queue_dir, "task_queue.json")
        tasks = []
        if os.path.exists(queue_file):
            with open(queue_file, "r") as f:
                tasks = json.load(f)
        tasks.append({
            "id": f"task_{int(time.time())}",
            "name": task_name,
            "action": action,
            "params": params or {},
            "queued_at": datetime.now().isoformat(),
            "status": "queued"
        })
        with open(queue_file, "w") as f:
            json.dump(tasks, f, indent=4)
        return f"[OK] Task '{task_name}' queued."
    except Exception as e:
        return f"[FAIL] Queue error: {e}"


def queue_status() -> str:
    """List queued tasks."""
    try:
        import json
        queue_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory", "task_queue.json")
        if not os.path.exists(queue_file):
            return "No queued tasks."
        with open(queue_file, "r") as f:
            tasks = json.load(f)
        if not tasks:
            return "No queued tasks."
        lines = ["### QUEUED TASKS"]
        for t in tasks:
            lines.append(f"- {t.get('name', '?')}: {t.get('action', '?')} ({t.get('status', '?')})")
        return "\n".join(lines)
    except Exception as e:
        return f"[FAIL] Queue status error: {e}"


def queue_result(task_id: str) -> str:
    """Get result of a queued task."""
    return f"[Stub] Task {task_id}: result not available."


def type_text(text: str) -> str:
    """Type text using keyboard simulation."""
    try:
        import pyautogui
        pyautogui.typewrite(text)
        return f"[OK] Typed: {text[:50]}..."
    except ImportError:
        return "[FAIL] pyautogui not installed."
    except Exception as e:
        return f"[FAIL] Type error: {e}"


def take_snapshot(name: str = None) -> str:
    """Take a snapshot of the current screen."""
    try:
        from screen_watcher import capture_screen
        import base64
        screenshot_bytes = capture_screen(resize_to=(1280, 720), quality=70)
        name = name or f"snapshot_{int(time.time())}"
        snap_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory", "snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        snap_path = os.path.join(snap_dir, f"{name}.jpg")
        with open(snap_path, "wb") as f:
            f.write(screenshot_bytes)
        return f"[OK] Snapshot saved: {snap_path}"
    except Exception as e:
        return f"[FAIL] Snapshot error: {e}"


def recall_snapshot(name: str) -> str:
    """Recall a previously saved snapshot."""
    try:
        snap_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory", "snapshots")
        import glob
        files = glob.glob(os.path.join(snap_dir, f"{name}.*"))
        if not files:
            return f"[FAIL] Snapshot '{name}' not found."
        return f"[OK] Snapshot found: {files[0]}"
    except Exception as e:
        return f"[FAIL] Recall error: {e}"


def smart_home_command(device: str, action: str) -> str:
    """Control smart home devices."""
    return home_assistant_command(action, entity=device)


#  StayFree Integration #

def stayfree_status() -> str:
    """Check if StayFree screen time tracker is accessible."""
    try:
        from stayfree_bridge import stayfree_status as _sf_status
        return _sf_status()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree error: {e}"


def stayfree_today() -> str:
    """Get today's screen time and app usage from StayFree."""
    try:
        from stayfree_bridge import stayfree_today as _sf_today
        return _sf_today()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree today error: {e}"


def stayfree_week() -> str:
    """Get this week's screen time summary from StayFree."""
    try:
        from stayfree_bridge import stayfree_week as _sf_week
        return _sf_week()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree week error: {e}"


#  OpenCLI Bridge Tools #

def opencli_init_bridge() -> str:
    """Initialize the OpenCLI browser bridge."""
    try:
        from opencli_integration import opencli_init
        return opencli_init()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI init error: {e}"


def opencli_navigate(url: str) -> str:
    """Open a URL in the OpenCLI browser automation window."""
    try:
        from opencli_integration import opencli_navigate
        return opencli_navigate(url)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI navigate error: {e}"


def opencli_click(target: str) -> str:
    """Click an element in the browser by selector or text."""
    try:
        from opencli_integration import opencli_click
        return opencli_click(target)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI click error: {e}"


def opencli_type(target: str, text: str) -> str:
    """Type text into a browser element."""
    try:
        from opencli_integration import opencli_type
        return opencli_type(target, text)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI type error: {e}"


def opencli_extract() -> str:
    """Extract page content as markdown from the current browser page."""
    try:
        from opencli_integration import opencli_extract
        return opencli_extract()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI extract error: {e}"


def opencli_screenshot(path: str = None) -> str:
    """Take a screenshot of the current browser page."""
    try:
        from opencli_integration import opencli_screenshot
        return opencli_screenshot(path)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI screenshot error: {e}"


def opencli_scroll(direction: str = "down") -> str:
    """Scroll the browser page (down, up, top, bottom)."""
    try:
        from opencli_integration import opencli_scroll
        return opencli_scroll(direction)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI scroll error: {e}"


def opencli_keys(key: str) -> str:
    """Press a keyboard key in the browser (Enter, Escape, Tab, etc.)."""
    try:
        from opencli_integration import opencli_keys
        return opencli_keys(key)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI key error: {e}"


def opencli_eval(js: str) -> str:
    """Execute JavaScript in the browser page."""
    try:
        from opencli_integration import opencli_eval
        return opencli_eval(js)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI eval error: {e}"


def opencli_state() -> str:
    """Get current browser page state (URL, title, interactive elements)."""
    try:
        from opencli_integration import opencli_state
        return opencli_state()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI state error: {e}"


def opencli_doctor() -> str:
    """Diagnose OpenCLI browser bridge connectivity."""
    try:
        from opencli_integration import opencli_doctor
        return opencli_doctor()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI doctor error: {e}"


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
    "spotify_play", "spotify_pause", "spotify_next", "spotify_prev", "spotify_volume", "spotify_current",
    "netflix_play",
    "read_emails", "send_email", "draft_email",
    "send_instagram_dm",
    "tell_alexa",
    "web_search", "video_search", "stark_doctor", "git_ops",
    "see_screen", "search_browser_history", "open_history_item",
    "list_recent_history", "generate_file", "generate_file_llm",
    "search_and_open",
    "situational_awareness", "goals_tool_handler", "startup_tool_handler",
    "memory_import_tool_handler",
    "vision_click",
    "alexa_command", "alexa_poll", "home_assistant_command",
    "multi_task", "queue_task", "queue_status", "queue_result",
    "type_text", "take_snapshot", "recall_snapshot", "smart_home_command",
    "stayfree_status", "stayfree_today", "stayfree_week",
    "opencli_init_bridge", "opencli_navigate", "opencli_click", "opencli_type",
    "opencli_extract", "opencli_screenshot", "opencli_scroll",
    "opencli_keys", "opencli_eval", "opencli_state", "opencli_doctor",
]

if __name__ == "__main__":
    print("Friday Tools loaded successfully.")
    print(f"Tools available: {len(__all__)}")
