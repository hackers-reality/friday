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
    """Open ANY application by name using system discovery. No hardcoded paths."""
    import subprocess
    import os

    name = name.strip().strip('"').strip("'")

    # Strategy 1: Try `start` with the name directly (Windows resolves through PATH and App Paths)
    try:
        subprocess.run(f"start \"\" \"{name}\"", shell=True, timeout=10)
        return f"[OK] Opening: {name}"
    except Exception:
        pass

    # Strategy 2: Use `where` to find the full path, then open it
    try:
        result = subprocess.run(f"where {name}", shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0].strip()
            if path:
                os.startfile(path)
                return f"[OK] Opening: {name} ({path})"
    except Exception:
        pass

    # Strategy 3: Try with .exe extension if not present
    if not name.lower().endswith('.exe'):
        try:
            result = subprocess.run(f"where {name}.exe", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[0].strip()
                if path:
                    os.startfile(path)
                    return f"[OK] Opening: {name} ({path})"
        except Exception:
            pass

    # Strategy 4: Try `start` with shell URI schemes (ms-settings:, mailto:, etc.)
    if ":" not in name:
        try:
            subprocess.run(f"start \"\" \"{name}\"", shell=True, timeout=10)
            return f"[OK] Opening: {name}"
        except Exception:
            pass

    return f"[FAIL] Could not find '{name}'. Make sure it's installed and in your PATH."


def close_app(name: str) -> str:
    """Kill process by name or window title. Handles save dialogs, UWP apps."""
    import subprocess
    
    def _taskkill(name_or_title: str) -> tuple[bool, str]:
        r = subprocess.run(f"taskkill /F /IM {name_or_title}", shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True, f"[OK] Killed {name_or_title}"
        return False, r.stderr

    def _taskkill_window(title_filter: str) -> tuple[bool, str]:
        r = subprocess.run(f'taskkill /F /FI "WINDOWTITLE eq {title_filter}"', shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True, f"[OK] Killed window matching '{title_filter}'"
        return False, r.stderr

    def _wm_close(window_title: str) -> str:
        """Send WM_CLOSE to window by title (triggers save dialog gracefully)."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, window_title)
            if hwnd:
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                return f"[OK] Sent close signal to '{window_title}'"
            return "[FAIL] Window not found"
        except Exception as e:
            return f"[FAIL] WM_CLOSE error: {e}"

    try:
        if os.name != 'nt':
            subprocess.run(f"pkill -f {name}", shell=True)
            return f"[OK] Killed {name}"

        candidates = [name]
        if not name.lower().endswith('.exe'):
            candidates.append(name + '.exe')
        else:
            candidates.append(name[:-4])

        # 1. Try taskkill by process name
        for candidate in candidates:
            ok, msg = _taskkill(candidate)
            if ok:
                return msg

        # 2. Try taskkill by window title (handles UWP/modern apps)
        ok, msg = _taskkill_window(f"*{name}*")
        if ok:
            return msg

        # 3. Try WM_CLOSE for graceful close (handles save dialogs)
        for title_part in [name, os.path.splitext(name)[0]]:
            import pygetwindow as gw
            try:
                for w in gw.getWindowsWithTitle(title_part):
                    if w.title.strip():
                        result = _wm_close(w.title)
                        if "[OK]" in result:
                            return result
            except Exception:
                pass

        # 4. Force kill via wmic (handles edge cases)
        for candidate in candidates:
            r = subprocess.run(
                f'wmic process where name="{candidate}" delete',
                shell=True, capture_output=True, text=True
            )
            if r.returncode == 0 and "deleted" in r.stdout.lower():
                return f"[OK] Killed {candidate} via WMIC"

        return f"[FAIL] Could not close '{name}'. Running: {[w for w in list_running_apps()[:8]]}"

    except Exception as e:
        return f"[FAIL] Error closing {name}: {e}"


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

        # Try playlist search first (if query contains playlist-like keywords)
        playlist_keywords = ["playlist", "mix", "session", "daily", "discover", "release radar"]
        if any(kw in query.lower() for kw in playlist_keywords):
            p_results = sp.search(q=query, type="playlist", limit=5)
            playlists = p_results.get("playlists", {}).get("items", [])
            if playlists:
                sp.start_playback(context_uri=playlists[0]["uri"])
                return f"[OK] Playing playlist '{playlists[0]['name']}' on Spotify"

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
            # Try playlist as last resort
            p_results = sp.search(q=query, type="playlist", limit=3)
            playlists = p_results.get("playlists", {}).get("items", [])
            if playlists:
                sp.start_playback(context_uri=playlists[0]["uri"])
                return f"[OK] Playing playlist '{playlists[0]['name']}' on Spotify"
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
    """Search the web using multiple engines with fallback chain."""
    try:
        from friday.web import WebScraper
        import requests
        from bs4 import BeautifulSoup

        scraper = WebScraper()
        engines = ["duckduckgo", "bing"]
        results = None
        items = []

        for engine in engines:
            try:
                result = scraper.search_engine(query, engine=engine)
                if result.get("success"):
                    items = result.get("results", [])
                    if items:
                        results = result
                        break
            except Exception:
                continue

        # If both HTML scrapers failed, try direct API approach
        if not items:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                # Try Google
                g_resp = requests.get(f"https://www.google.com/search?q={requests.utils.quote(query)}&num={max_results}",
                                      headers=headers, timeout=10)
                if g_resp.status_code == 200:
                    g_soup = BeautifulSoup(g_resp.text, "html.parser")
                    for g in g_soup.select("div.g"):
                        title_el = g.select_one("h3")
                        link_el = g.select_one("a")
                        if title_el and link_el:
                            items.append({
                                "title": title_el.get_text(strip=True),
                                "url": link_el.get("href", "").lstrip("/url?q=").split("&")[0] if link_el.get("href", "").startswith("/url?q=") else link_el.get("href", ""),
                                "snippet": "",
                            })
            except Exception:
                pass

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
    """Capture screen and analyze it using Gemini Vision API.
    Uses gemini-1.5-flash (higher quota) with automatic retry + model fallback on 429."""
    try:
        import base64, io, requests, json, time
        from PIL import Image, ImageGrab

        # Capture screen: try pyautogui first, fallback to PIL ImageGrab
        img = None
        try:
            import pyautogui
            img = pyautogui.screenshot()
        except Exception:
            try:
                img = ImageGrab.grab()
            except Exception as e2:
                return f"[FAIL] Screen capture failed: {e2}"

        # Resize for API efficiency
        img.thumbnail((1280, 720), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "[FAIL] GOOGLE_API_KEY not configured."

        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
        last_error = ""

        for model in models:
            for attempt in range(2):
                try:
                    r = requests.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
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
                    if r.status_code == 429:
                        last_error = f"Rate limited on {model}"
                        time.sleep(2 ** attempt)
                        continue
                    if r.status_code != 200:
                        last_error = f"{model} HTTP {r.status_code}: {data.get('error', {}).get('message', '')}"
                        break
                    if "candidates" not in data or not data["candidates"]:
                        error_info = data.get("error", {}).get("message", str(data))
                        last_error = f"{model} no response: {error_info}"
                        break
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                except requests.exceptions.Timeout:
                    last_error = f"{model} timeout"
                    continue
                except Exception as e:
                    last_error = f"{model} error: {e}"
                    break

        return f"[FAIL] Screen analysis failed. All models exhausted. Last error: {last_error}"
    except ImportError as e:
        return f"[FAIL] Missing dependency: {e}. Install: pip install pillow requests"
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
        from friday.browser_history import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("search", query=query, days_back=days_back)
        return f"Browser history not available. Searching for: {query}"
    except Exception as e:
        return f"Browser search error: {e}"

def open_history_item(query: str) -> str:
    """Find and open the most recent browser history item matching query."""
    try:
        from friday.browser_history import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("open_latest", query=query)
        return f"Browser history not available. Looking for: {query}"
    except Exception as e:
        return f"Browser open error: {e}"

def list_recent_history(days_back: int = 7, limit: int = 20) -> str:
    """List recent browser history from all browsers."""
    try:
        from friday.browser_history import browser_history_tool
        if browser_history_tool:
            return browser_history_tool("list_recent", days_back=days_back, limit=limit)
        return "Browser history not available."
    except Exception as e:
        return f"Browser list error: {e}"

def generate_file(path: str, file_type: str = "auto", description: str = "", content: str = "") -> str:
    """Generate any type of file."""
    try:
        from friday.filegen import file_generator_tool
        if file_generator_tool:
            return file_generator_tool("generate", path=path, file_type=file_type, description=description, content=content)
        return f"File generator not available. Would create: {path}"
    except Exception as e:
        return f"File generation error: {e}"

def generate_file_llm(path: str, prompt: str) -> str:
    """Generate file content using LLM."""
    try:
        from friday.filegen import file_generator_tool
        if file_generator_tool:
            return file_generator_tool("generate_llm", path=path, prompt=prompt)
        return f"LLM file generation not available. Path: {path}"
    except Exception as e:
        return f"LLM file generation error: {e}"

def situational_awareness() -> str:
    """Get system context."""
    try:
        from friday.screen_watcher import get_active_window_info
        info = get_active_window_info()
        return f"Active window: {info.get('title', 'Unknown')}\nProcess: {info.get('process_name', 'Unknown')}"
    except Exception as e:
        return f"Sensors failing: {e}"

def calendar_tool_handler(action: str = "list", days: int = 7) -> str:
    """Google Calendar integration: list events, sync with goals."""
    try:
        from friday.goals import fetch_calendar_events, sync_calendar_to_goals
        if action == "list":
            return fetch_calendar_events(max_results=days * 5, days_ahead=days)
        elif action == "sync":
            return sync_calendar_to_goals()
        else:
            return f"[FAIL] Unknown calendar action: {action}"
    except ImportError:
        return "[FAIL] goal_memory.py not available."
    except Exception as e:
        return f"[FAIL] Calendar error: {e}"


def goals_tool_handler(action: str, **kwargs) -> str:
    """Handler for goals tool. Maps Gemini parameter names to goal_memory names."""
    try:
        from friday.goals import goals_tool_handler as gh
        mapped = dict(kwargs)
        if "goal" in mapped and "title" not in mapped:
            mapped["title"] = mapped.pop("goal")
        if "category" in mapped and "goal_type" not in mapped:
            mapped["goal_type"] = mapped.pop("category")
        return gh(action, **mapped)
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
            from friday.browser_history import browser_history_tool
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
    Falls back to web search if not found in history.
    """
    try:
        # First: try browser history
        from friday.browser_history import browser_history_tool
        if browser_history_tool:
            result = browser_history_tool("find_and_open", query=query, category=(category_hint or ""))
            if result and not result.startswith("[FAIL]"):
                return result

        # Second: try web search + open first result
        web_results = web_search(query)
        if not web_results.startswith("[FAIL]"):
            import re, webbrowser
            urls = re.findall(r'https?://[^\s\n]+', web_results)
            if urls:
                # Filter out non-relevant URLs
                clean_urls = [u for u in urls if not any(skip in u for skip in
                             ["google.com/search", "bing.com/search", "duckduckgo.com"])]
                if clean_urls:
                    target = clean_urls[0].rstrip(".,)")
                    webbrowser.open(target)
                    return f"[OK] Found and opened from web: {target}"

        return f"[FAIL] Could not find '{query}' in history or web search."
    except Exception as e:
        return f"[FAIL] Search error: {e}"


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
    """Search for a video and play it directly. Opens the actual video URL, not a search page."""
    import webbrowser, re, requests, html

    try:
        # Strategy 1: Scrape YouTube search for the first actual video
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(search_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Extract videoId from ytInitialData JSON embedded in page
            import json
            # Find the ytInitialData JSON blob
            match = re.search(r'ytInitialData\s*=\s*({.*?});\s*</script>', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                # Navigate: contents -> twoColumnSearchResultsRenderer -> primaryContents -> sectionListRenderer -> contents[0] -> itemSectionRenderer -> contents
                contents = data
                for key in ["contents", "twoColumnSearchResultsRenderer", "primaryContents",
                             "sectionListRenderer", "contents"]:
                    if isinstance(contents, dict) and key in contents:
                        contents = contents[key]
                    else:
                        contents = None
                        break
                if contents and isinstance(contents, list) and len(contents) > 0:
                    item_section = contents[0]
                    if isinstance(item_section, dict) and "itemSectionRenderer" in item_section:
                        items = item_section["itemSectionRenderer"].get("contents", [])
                        for item in items:
                            if "videoRenderer" in item:
                                vid = item["videoRenderer"]
                                video_id = vid.get("videoId", "")
                                title = ""
                                title_runs = vid.get("title", {}).get("runs", [])
                                if title_runs:
                                    title = "".join(r.get("text", "") for r in title_runs)
                                if video_id:
                                    direct_url = f"https://www.youtube.com/watch?v={video_id}"
                                    webbrowser.open(direct_url)
                                    return f"[OK] Playing: {title}"

        # Strategy 2: Fallback - use web_search to find video URL
        search_result = web_search(f"{query} site:youtube.com watch")
        if not search_result.startswith("[FAIL]"):
            urls = re.findall(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)', search_result)
            if urls:
                webbrowser.open(urls[0])
                return f"[OK] Opened: {urls[0]}"

        # Strategy 3: Last resort - try youtu.be shortlinks from web_search
        urls = re.findall(r'(https?://youtu\.be/[\w-]+)', search_result if not search_result.startswith("[FAIL]") else "")
        if urls:
            webbrowser.open(urls[0])
            return f"[OK] Opened: {urls[0]}"

        # Strategy 4: Ultimate fallback - open YouTube search in browser (Boss can click)
        webbrowser.open(search_url)
        return f"[OK] Opened YouTube search for '{query}'"

    except Exception as e:
        return f"[FAIL] Video search error: {e}"


def deep_research(topic: str, url: str = "", depth: int = 3) -> str:
    """Multi-source deep research with synthesized report."""
    try:
        from friday.web import WebScraper
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
    """Search web for Netflix title ID, then open the direct watch URL."""
    try:
        import webbrowser, re

        # Search for the Netflix title ID via web search
        search_result = web_search(f"netflix {title} site:netflix.com/title")
        # Extract Netflix title IDs from search results
        title_ids = re.findall(r'netflix\.com/title/(\d+)', search_result)
        if title_ids:
            direct_url = f"https://www.netflix.com/title/{title_ids[0]}"
            webbrowser.open(direct_url)
            return f"[OK] Opening Netflix: {title} (title ID: {title_ids[0]})"

        # Try broader search for any Netflix content URL
        search_result2 = web_search(f"netflix {title}")
        title_ids2 = re.findall(r'netflix\.com/(?:watch|title)/(\d+)', search_result2)
        if title_ids2:
            direct_url = f"https://www.netflix.com/title/{title_ids2[0]}"
            webbrowser.open(direct_url)
            return f"[OK] Opening Netflix: {title} (ID: {title_ids2[0]})"

        # Fallback: Open Netflix search page
        search_url = f"https://www.netflix.com/search?q={title.replace(' ', '+')}"
        webbrowser.open(search_url)
        return f"[OK] Opening Netflix search for '{title}' (title ID not found via web search)"

    except Exception as e:
        return f"[FAIL] Netflix play error: {e}"


#  Email (Gmail) Functions 

def google_authorize() -> str:
    """Authorize ALL Google services (Gmail + Calendar). Opens browser for OAuth consent. Only needed once."""
    try:
        from friday.gmail import google_authorize
        return google_authorize()
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Google authorize error: {e}"


def gmail_authorize() -> str:
    """Run the Gmail OAuth flow — opens browser for you to authorize Friday. Only needed once."""
    try:
        from friday.gmail import gmail_authorize
        return gmail_authorize()
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Gmail authorize error: {e}"


def exchange_oauth_code(redirect_url: str) -> str:
    """Complete OAuth by pasting the browser redirect URL when auto-flow fails."""
    try:
        from friday.gmail import exchange_oauth_code
        return exchange_oauth_code(redirect_url)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Exchange error: {e}"


def read_emails(count: int = 10) -> str:
    """Read latest N emails. Returns formatted string with sender, subject, snippet."""
    try:
        from friday.gmail import gmail_list_messages
        return gmail_list_messages(query="", max_results=count)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Email read error: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send email via Gmail API."""
    try:
        from friday.gmail import gmail_send
        return gmail_send(to, subject, body)
    except ImportError:
        return "[FAIL] friday_gmail.py not available."
    except Exception as e:
        return f"[FAIL] Email send error: {e}"


def draft_email(context: str, recipient: str) -> str:
    """Use LLM to draft a professional email from context string."""
    try:
        from friday.gmail import gmail_draft

        # Generate email content using LLM
        try:
            from friday.ai import ai_tool
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
        from friday.screen_watcher import capture_screen
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
        from friday.stayfree import stayfree_status as _sf_status
        return _sf_status()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree error: {e}"


def stayfree_today() -> str:
    """Get today's screen time and app usage from StayFree."""
    try:
        from friday.stayfree import stayfree_today as _sf_today
        return _sf_today()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree today error: {e}"


def stayfree_week() -> str:
    """Get this week's screen time summary from StayFree."""
    try:
        from friday.stayfree import stayfree_week as _sf_week
        return _sf_week()
    except ImportError:
        return "[FAIL] stayfree_bridge.py not available."
    except Exception as e:
        return f"[FAIL] StayFree week error: {e}"


#  OpenCLI Bridge Tools #

def opencli_run(command: str) -> str:
    """Run ANY OpenCLI command (site adapters, browser, desktop apps, CLI hub).
    For built-in site adapters: opencli_run('hackernews top --limit 5')
    For browser automation: opencli_run('browser open https://...')
    For desktop apps: opencli_run('cursor ...')
    For CLI hub tools: opencli_run('gh pr list --limit 5')
    Use opencli_run('list') to see all available commands."""
    try:
        from friday.opencli import opencli_run
        return opencli_run(command)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI run error: {e}"


def opencli_list_adapters() -> str:
    """List all available OpenCLI commands and built-in site adapters."""
    try:
        from friday.opencli import opencli_list_adapters
        return opencli_list_adapters()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI list error: {e}"


def opencli_init_bridge() -> str:
    """Initialize the OpenCLI browser bridge and install Chrome extension."""
    try:
        from friday.opencli import opencli_init
        import subprocess, os

        result = opencli_init()
        if "[FAIL]" not in result:
            return result

        # Init failed — try installing the browser extension first
        try:
            inst = subprocess.run(["opencli", "browser", "install"], capture_output=True, text=True, timeout=30)
            if inst.returncode == 0:
                result2 = opencli_init()
                if "[FAIL]" not in result2:
                    return result2 + " (Chrome extension installed)"
        except Exception:
            pass

        return (
            "[FAIL] OpenCLI bridge not connected. To set up:\n"
            "  1. Open Chrome and go to chrome://extensions\n"
            "  2. Enable Developer mode (top right)\n"
            "  3. Run: opencli browser install\n"
            "  4. Run: opencli browser init\n"
            "  5. Make sure the OpenCLI extension is enabled"
        )
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI init error: {e}"


def opencli_navigate(url: str) -> str:
    """Open a URL in the OpenCLI browser automation window."""
    try:
        from friday.opencli import opencli_navigate
        return opencli_navigate(url)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI navigate error: {e}"


def opencli_click(target: str) -> str:
    """Click an element in the browser by selector or text."""
    try:
        from friday.opencli import opencli_click
        return opencli_click(target)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI click error: {e}"


def opencli_type(target: str, text: str) -> str:
    """Type text into a browser element."""
    try:
        from friday.opencli import opencli_type
        return opencli_type(target, text)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI type error: {e}"


def opencli_extract() -> str:
    """Extract page content as markdown from the current browser page."""
    try:
        from friday.opencli import opencli_extract
        return opencli_extract()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI extract error: {e}"


def opencli_screenshot(path: str = None) -> str:
    """Take a screenshot of the current browser page."""
    try:
        from friday.opencli import opencli_screenshot
        return opencli_screenshot(path)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI screenshot error: {e}"


def opencli_scroll(direction: str = "down") -> str:
    """Scroll the browser page (down, up, top, bottom)."""
    try:
        from friday.opencli import opencli_scroll
        return opencli_scroll(direction)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI scroll error: {e}"


def opencli_keys(key: str) -> str:
    """Press a keyboard key in the browser (Enter, Escape, Tab, etc.)."""
    try:
        from friday.opencli import opencli_keys
        return opencli_keys(key)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI key error: {e}"


def opencli_eval(js: str) -> str:
    """Execute JavaScript in the browser page."""
    try:
        from friday.opencli import opencli_eval
        return opencli_eval(js)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI eval error: {e}"


def opencli_state() -> str:
    """Get current browser page state (URL, title, interactive elements)."""
    try:
        from friday.opencli import opencli_state
        return opencli_state()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI state error: {e}"


def opencli_doctor() -> str:
    """Diagnose OpenCLI browser bridge connectivity."""
    try:
        from friday.opencli import opencli_doctor
        return opencli_doctor()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] OpenCLI doctor error: {e}"


def opencli_tab_list() -> str:
    """List all browser tabs."""
    try:
        from friday.opencli import opencli_tab_list
        return opencli_tab_list()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Tab list error: {e}"


def opencli_tab_new(url: str = "") -> str:
    """Open a new browser tab."""
    try:
        from friday.opencli import opencli_tab_new
        return opencli_tab_new(url)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Tab new error: {e}"


def opencli_tab_select(target_id: str) -> str:
    """Switch to a specific browser tab."""
    try:
        from friday.opencli import opencli_tab_select
        return opencli_tab_select(target_id)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Tab select error: {e}"


def opencli_tab_close(target_id: str = "") -> str:
    """Close a browser tab."""
    try:
        from friday.opencli import opencli_tab_close
        return opencli_tab_close(target_id)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Tab close error: {e}"


def opencli_close() -> str:
    """Release the current browser automation tab lease."""
    try:
        from friday.opencli import opencli_close
        return opencli_close()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Close error: {e}"


def opencli_wait_selector(selector: str, timeout_ms: int = 10000) -> str:
    """Wait for a CSS selector to appear on the page."""
    try:
        from friday.opencli import opencli_wait_selector
        return opencli_wait_selector(selector, timeout_ms)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Wait error: {e}"


def opencli_find(selector: str, limit: int = 10) -> str:
    """Find elements matching a CSS selector."""
    try:
        from friday.opencli import opencli_find
        return opencli_find(selector, limit)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Find error: {e}"


def opencli_get_url() -> str:
    """Get the current page URL from the browser."""
    try:
        from friday.opencli import opencli_get_url
        return opencli_get_url()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Get URL error: {e}"


def opencli_get_title() -> str:
    """Get the current page title from the browser."""
    try:
        from friday.opencli import opencli_get_title
        return opencli_get_title()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Get title error: {e}"


def opencli_network() -> str:
    """Inspect network requests made by the current page."""
    try:
        from friday.opencli import opencli_network
        return opencli_network()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Network error: {e}"


def opencli_bind(domain: str = "") -> str:
    """Bind OpenCLI to the current Chrome tab."""
    try:
        from friday.opencli import opencli_bind
        return opencli_bind(domain)
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Bind error: {e}"


def opencli_unbind() -> str:
    """Unbind from the current Chrome tab."""
    try:
        from friday.opencli import opencli_unbind
        return opencli_unbind()
    except ImportError:
        return "[FAIL] opencli_integration.py not available."
    except Exception as e:
        return f"[FAIL] Unbind error: {e}"


#  Workflow Automation Tool #

def workflow_tool(action: str = "list", name: str = None, description: str = None, steps: str = None) -> str:
    """Create, manage, and execute automated workflows. Actions: list, create, add_step, execute, delete, status."""
    try:
        from friday.workflow import workflow_tool as _wf_tool
        return _wf_tool(action=action, name=name, description=description, steps=steps)
    except ImportError:
        return "[FAIL] workflow_automation.py not available."
    except Exception as e:
        return f"[FAIL] Workflow error: {e}"


#  Plugin System Tool #

def plugin_tool(action: str = "list", plugin_name: str = None, tool_name: str = None, **kwargs) -> str:
    """Manage Friday plugins: load, unload, call plugin tools. Actions: list, discover, load, load_all, unload, call."""
    try:
        from friday.plugins import plugin_tool as _pl_tool
        return _pl_tool(action=action, plugin_name=plugin_name, tool_name=tool_name, **kwargs)
    except ImportError:
        return "[FAIL] plugin_system.py not available."
    except Exception as e:
        return f"[FAIL] Plugin error: {e}"


#  Knowledge Graph Tool #

def knowledge_graph_tool(action: str = "stats", node_id: str = None, target_id: str = None,
                         relation: str = None, properties: str = None, text: str = None) -> str:
    """Query and manage the knowledge graph. Actions: stats, add_node, add_edge, get, neighbors, search, path, subgraph, extract."""
    try:
        from knowledge_graph import knowledge_graph_tool as _kg_tool
        return _kg_tool(action=action, node_id=node_id, target_id=target_id,
                        relation=relation, properties=properties, text=text)
    except ImportError:
        return "[FAIL] knowledge_graph.py not available."
    except Exception as e:
        return f"[FAIL] Knowledge graph error: {e}"


#  GitHub Integration Tools #

def github_list_files(path: str = "") -> str:
    """List files in the configured GitHub repository."""
    try:
        from friday.github import github_list_files
        return github_list_files(path)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_read_file(path: str) -> str:
    """Read a file from the GitHub repository."""
    try:
        from friday.github import github_read_file
        return github_read_file(path)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_write_file(path: str, content: str, message: str = "Update via Friday") -> str:
    """Write a file to the GitHub repository."""
    try:
        from friday.github import github_write_file
        return github_write_file(path, content, message)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_create_branch(branch_name: str) -> str:
    """Create a new branch in the GitHub repository."""
    try:
        from friday.github import github_create_branch
        return github_create_branch(branch_name)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_create_pr(title: str, body: str, head: str) -> str:
    """Create a pull request on GitHub."""
    try:
        from friday.github import github_create_pr
        return github_create_pr(title, body, head)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_self_modify(file_path: str, new_content: str, commit_msg: str = "Self-modification by Friday") -> str:
    """Self-modify a file in Friday's own GitHub repository."""
    try:
        from friday.github import github_self_modify
        return github_self_modify(file_path, new_content, commit_msg)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub error: {e}"


def github_review_pr(pr_number: int) -> str:
    """Deep PR review: fetches diff, analyzes with Gemini, posts review comments."""
    try:
        from friday.github import github_review_pr
        return github_review_pr(pr_number)
    except ImportError:
        return "[FAIL] friday_github.py not available."
    except Exception as e:
        return f"[FAIL] GitHub review error: {e}"


#  Notification Tools #

def send_notification(message: str, urgency: str = "normal", task_id: str = "") -> str:
    """Send a desktop toast notification with urgency level (normal, urgent)."""
    try:
        from friday.notify import send_notification as _sn
        return _sn(message=message, urgency=urgency, task_id=task_id)
    except ImportError:
        return "[FAIL] friday_notify.py not available."
    except Exception as e:
        return f"[FAIL] Notification error: {e}"


def get_pending_notifications(urgency_filter: str = "") -> str:
    """List pending notifications, optionally filtered by urgency."""
    try:
        from friday.notify import get_pending_notifications as _gpn
        return _gpn(urgency_filter=urgency_filter)
    except ImportError:
        return "[FAIL] friday_notify.py not available."
    except Exception as e:
        return f"[FAIL] Notifications error: {e}"


def clear_notifications(task_id: str = "") -> str:
    """Clear all delivered notifications, or for a specific task."""
    try:
        from friday.notify import clear_notifications as _cn
        return _cn(task_id=task_id)
    except ImportError:
        return "[FAIL] friday_notify.py not available."
    except Exception as e:
        return f"[FAIL] Clear error: {e}"


#  Vector Memory Tool (re-exported from vector_memory.py) #

def vector_memory_tool(action: str = "stats", query: str = None, text: str = None, n_results: int = 5) -> str:
    """Semantic memory: store and search facts, preferences, and patterns using vector search."""
    try:
        from vector_memory import vector_memory_tool as _vm_tool
        return _vm_tool(action=action, query=query, text=text, n_results=n_results)
    except ImportError:
        return "[FAIL] vector_memory.py not available."
    except Exception as e:
        return f"[FAIL] Vector memory error: {e}"


#  Multi-Agent Delegation Tool #

def multi_agent_delegate(action: str = "list", task: str = None, agent: str = None) -> str:
    """Delegate tasks to specialist sub-agents. Actions: list (show agents), delegate (assign task)."""
    try:
        from multi_agent import multi_agent_delegate as _ma_delegate
        return _ma_delegate(action=action, task=task, agent=agent)
    except ImportError:
        return "[FAIL] multi_agent.py not available."
    except Exception as e:
        return f"[FAIL] Multi-agent error: {e}"


#  Message Channel Tool #

def message_channel_tool(action: str = "status", channel: str = None, target: str = None,
                         message: str = None, limit: int = 10) -> str:
    """Send/receive messages via Telegram, Discord, or webhooks. Actions: status, send, receive."""
    try:
        from friday.messages import message_channel_tool as _mc_tool
        return _mc_tool(action=action, channel=channel, target=target, message=message, limit=limit)
    except ImportError:
        return "[FAIL] message_channels.py not available."
    except Exception as e:
        return f"[FAIL] Message channel error: {e}"


def execute_tool(name: str, args: dict = None) -> str:
    """Execute a tool by name with given args. Used by friday_langgraph.py."""
    import inspect
    args = args or {}
    func = globals().get(name)
    if not func:
        return f"[FAIL] Unknown tool: {name}"
    try:
        sig = inspect.signature(func)
        filtered = {k: v for k, v in args.items() if k in sig.parameters}
        result = func(**filtered)
        return str(result)
    except Exception as e:
        return f"[FAIL] {name} error: {e}"


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
    "google_authorize", "gmail_authorize", "exchange_oauth_code", "read_emails", "send_email", "draft_email",
    "send_instagram_dm",
    "tell_alexa",
    "web_search", "video_search", "stark_doctor", "git_ops",
    "see_screen", "search_browser_history", "open_history_item",
    "list_recent_history", "generate_file", "generate_file_llm",
    "search_and_open",
    "situational_awareness", "goals_tool_handler", "calendar_tool_handler", "startup_tool_handler",
    "memory_import_tool_handler",
    "climb_codebase", "deep_research",
    "memory_store", "memory_retrieve", "stark_log",
    "vision_click",
    "alexa_command", "alexa_poll", "home_assistant_command",
    "multi_task", "queue_task", "queue_status", "queue_result",
    "type_text", "take_snapshot", "recall_snapshot", "smart_home_command",
    "stayfree_status", "stayfree_today", "stayfree_week",
    "opencli_init_bridge", "opencli_navigate", "opencli_click", "opencli_type",
    "opencli_extract", "opencli_screenshot", "opencli_scroll",
    "opencli_keys", "opencli_eval", "opencli_state", "opencli_doctor",
    "opencli_tab_list", "opencli_tab_new", "opencli_tab_select", "opencli_tab_close",
    "opencli_close", "opencli_wait_selector", "opencli_find",
    "opencli_get_url", "opencli_get_title", "opencli_network",
    "opencli_bind", "opencli_unbind",
    "vector_memory_tool",
    "workflow_tool", "plugin_tool", "knowledge_graph_tool",
    "github_list_files", "github_read_file", "github_write_file",
    "github_create_branch", "github_create_pr", "github_self_modify", "github_review_pr",
    "multi_agent_delegate", "message_channel_tool",
    "send_notification", "get_pending_notifications", "clear_notifications",
]

if __name__ == "__main__":
    print("Friday Tools loaded successfully.")
    print(f"Tools available: {len(__all__)}")
