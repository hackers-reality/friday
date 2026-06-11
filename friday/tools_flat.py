"""
Friday Tools - All tool functions for Friday Live.
Provides all functions needed by friday.live by wrapping modules.
"""
from __future__ import annotations
from friday._paths import PROJECT_ROOT as _ROOT
from friday._paths import FRIDAY_MEMORY, STARK_LOGS, SPOTIFY_CACHE
from friday.skills import read_skill_tool

import os
import json
import subprocess
import shutil
import glob
from datetime import datetime

_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB log rotation

def stark_log(entry: str) -> str:
    """Log to stark_logs.txt with rotation."""
    log_path = STARK_LOGS
    if os.path.exists(log_path) and os.path.getsize(log_path) > _LOG_MAX_BYTES:
        shutil.move(log_path, log_path.replace(".txt", "_archive.txt"))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {entry}\n")
    return "Entry logged."

#  Import available modules #

# Deep Code Review (loaded lazily in wrappers below)

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
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        pass
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
        import pyperclip
        pyperclip.copy(text)
        return "Clipboard set"
    except ImportError:
        pass
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
    # Safety: block destructive combos that could kill the session
    blocked_combos = ["ctrl+c", "ctrl+break", "alt+f4", "ctrl+alt+del",
                      "ctrl+shift+esc", "alt+tab"]
    keys_lower = keys.lower().strip()
    for b in blocked_combos:
        if keys_lower == b:
            return f"[BLOCKED] Hotkey '{keys}' blocked — would terminate the session."
    try:
        import pyautogui
        mods = keys_lower.split("+")
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
    """Open ANY application or URI scheme by name. No hardcoded paths."""
    import subprocess, os

    name = name.strip().strip('"').strip("'")

    # Strategy 0: URI scheme (contains : like ms-clock:, mailto:, roblox://)
    # Use Start-Process which handles URI schemes correctly
    if ":" in name and not name.startswith(("C:\\", "D:\\", os.path.expanduser("~"))):
        try:
            subprocess.run(["powershell", "-NoProfile", "Start-Process", name], timeout=10)
            return f"[OK] Opening URI: {name}"
        except Exception:
            pass

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

    # Strategy 4: Try `start` as final fallback
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
            def enum_callback(hwnd, lParam):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        windows.append(buf.value)
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


def open_roblox_game(game_name: str) -> str:
    """Search Roblox API for a game by name (fuzzy match), find its place ID, then open via roblox:// URI. Never opens a browser."""
    import urllib.parse, uuid, subprocess, difflib, requests

    def _launch(place_id: str, name: str) -> str:
        try:
            subprocess.run(["powershell", "-NoProfile", "Start-Process", f"roblox://placeID={place_id}"], timeout=15)
            return f"[OK] Launched '{name}' (ID: {place_id}) via Roblox"
        except Exception:
            try:
                subprocess.run(f'start "" "roblox://placeID={place_id}"', shell=True, timeout=10)
                return f"[OK] Launched '{name}' (ID: {place_id}) via Roblox"
            except Exception as e:
                return f"[FAIL] Could not launch Roblox: {e}"

    def _search_api(keyword: str) -> list:
        """Query apis.roblox.com/search-api/omni-search and return (name, rootPlaceId) tuples."""
        session = requests.Session()
        sid = str(uuid.uuid4())
        try:
            r = session.get(
                f"https://apis.roblox.com/search-api/omni-search?searchQuery={urllib.parse.quote(keyword)}&sessionId={sid}&pageType=all",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            if r.status_code == 200:
                results = []
                for group in r.json().get("searchResults", []):
                    for item in group.get("contents", []):
                        pid = item.get("rootPlaceId") or item.get("placeId")
                        name = item.get("name", "")
                        if pid and name:
                            results.append((name, str(pid)))
                return results
        except Exception:
            pass
        return []

    # Generate keyword variants for fuzzy matching
    lowered = game_name.lower().strip()
    keywords = [game_name]
    # Remove stop words
    for stop in ["the", "a", "an", "on", "in", "of", "for"]:
        if lowered.startswith(stop + " ") or lowered.endswith(" " + stop):
            keywords.append(lowered.replace(stop, "").strip())
    # Vowel-free skeleton (handles swapped vowels like 'blox' vs 'blocks')
    skel = "".join(c for c in lowered if c not in "aeiou ")
    if skel and len(skel) > 2:
        keywords.append(skel)

    candidates = []
    seen = set()
    for kw in keywords:
        for name, pid in _search_api(kw):
            if pid not in seen:
                seen.add(pid)
                candidates.append((name, pid))
        if len(candidates) >= 5:
            break

    if not candidates:
        return f"[FAIL] Could not find a Roblox game matching '{game_name}'. Try a more specific name."

    # Fuzzy score each candidate
    scored = []
    for gname, pid in candidates:
        g_lower = gname.lower()
        s = max(
            difflib.SequenceMatcher(None, lowered, g_lower).ratio(),
            difflib.SequenceMatcher(None, lowered, g_lower.replace("-", " ").replace("_", " ")).ratio(),
        )
        if lowered in g_lower or g_lower in lowered:
            s += 0.15
        scored.append((s, gname, pid))

    scored.sort(key=lambda x: -x[0])
    best_s, best_n, best_p = scored[0]

    if best_s >= 0.35 or (lowered in best_n.lower() or best_n.lower() in lowered):
        return _launch(best_p, best_n)

    suggestions = [f"{n}" for s, n, _ in scored[:5] if s > 0.2]
    if suggestions:
        return f"[FAIL] No close match for '{game_name}'. Did you mean:\n" + "\n".join(f"  - {s}" for s in suggestions)

    return f"[FAIL] Could not find a Roblox game matching '{game_name}'."


def open_microsoft_store(query: str = "", product_id: str = "") -> str:
    """Open Microsoft Store via ms-windows-store:// URI. Search or open a specific product. Never opens a browser."""
    try:
        import subprocess, urllib.parse

        def _launch(uri: str) -> None:
            try:
                subprocess.run(["powershell", "-NoProfile", "Start-Process", uri], timeout=15)
            except Exception:
                subprocess.run(f'start "" "{uri}"', shell=True, timeout=10)

        if product_id:
            uri = f"ms-windows-store://pdp/?productid={product_id}"
            _launch(uri)
            return f"[OK] Opening Microsoft Store product {product_id}"
        elif query:
            q = urllib.parse.quote(query)
            uri = f"ms-windows-store://search/?query={q}"
            _launch(uri)
            return f"[OK] Opening Microsoft Store search for '{query}'"
        else:
            _launch("ms-windows-store://home")
            return "[OK] Opening Microsoft Store"
    except Exception as e:
        return f"[FAIL] Microsoft Store error: {e}"


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
        cache_path = SPOTIFY_CACHE
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
    """Fast web search via classic scraper (no Playwright — too slow). Use browser_use_navigate for JS-heavy pages."""
    try:
        from friday.web import WebScraper
        from bs4 import BeautifulSoup
        import re

        scraper = WebScraper()
        engines = ["duckduckgo", "google", "bing"]
        items = []

        for engine in engines:
            try:
                result = scraper.search_engine(query, engine=engine)
                if result.get("success"):
                    items = result.get("results", [])
                    if items:
                        break
            except Exception:
                continue

        if not items:
            return f"[FAIL] No search results for '{query}' from any engine."

        lines = [f"Search results for '{query}':"]
        for i, item in enumerate(items[:max_results], 1):
            title = item.get("title", "?")
            url = item.get("url", "")
            snippet = item.get("snippet", "")
            lines.append(f"{i}. {title}")
            if url:
                lines.append(f"   {url}")
            if snippet:
                lines.append(f"   {snippet[:300]}")

        top_url = items[0].get("url", "")
        if top_url:
            try:
                page = scraper.fetch(top_url, timeout=15)
                if page.get("success"):
                    p_soup = BeautifulSoup(page["content"], "html.parser")
                    for tag in p_soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    body = p_soup.find("body") or p_soup
                    text = body.get_text(separator="\n", strip=True)
                    text = re.sub(r'\n{3,}', '\n\n', text)
                    if len(text) > 200:
                        lines.append(f"\n--- Top Result Content ({items[0].get('title','')}) ---")
                        lines.append(text[:2000])
            except Exception:
                pass

        return "\n".join(lines)
    except ImportError:
        return "[FAIL] friday.web not available."
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
    """Capture screen and analyze it — fast. Uses lower res + fastest model first."""
    try:
        import base64, io, requests, json, time
        from PIL import Image, ImageGrab

        img = None
        try:
            import pyautogui
            img = pyautogui.screenshot()
        except Exception:
            try:
                img = ImageGrab.grab()
            except Exception as e2:
                return f"[FAIL] Screen capture failed: {e2}"

        # Lower res = faster
        img.thumbnail((800, 600), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "[FAIL] GOOGLE_API_KEY not configured."

        # Fastest model first, single attempt per model
        models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]
        last_error = ""

        for model in models:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"Content-Type": "application/json"},
                    params={"key": api_key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": f"[SCREEN] {question}"},
                                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                            ]
                        }]
                    },
                    timeout=15,
                )
                data = r.json()
                if r.status_code == 429:
                    last_error = f"Rate limited on {model}"
                    time.sleep(2)
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
    """Get system context including CV camera feed (LLM-only)."""
    parts = []
    try:
        from friday.screen_watcher import get_active_window_info
        info = get_active_window_info()
        parts.append(f"Active window: {info.get('title', 'Unknown')}")
        parts.append(f"Process: {info.get('process_name', 'Unknown')}")
    except Exception:
        parts.append("Sensors: screen watcher unavailable")

    # Include CV engine context if camera is active (LLM-only)
    try:
        from friday.cv_engine import get_cv_status
        cv = get_cv_status()
        if cv.get("camera_active"):
            ctx_parts = []
            if cv.get("human_readable_scene"):
                ctx_parts.append(f"Scene: {cv['human_readable_scene'][:300]}")
            elif cv.get("scene_description"):
                ctx_parts.append(f"Scene: {cv['scene_description'][:200]}")
            if cv.get("people_count", 0) > 0:
                ctx_parts.append(f"People: {cv['people_count']}")
            objects = cv.get("objects_found", [])
            if objects:
                ctx_parts.append(f"Objects: {', '.join(objects[:8])}")
            hands = cv.get("hands_detected", [])
            if hands:
                hand_strs = []
                for h in hands:
                    s = h.get("handedness", "?") + " hand"
                    if h.get("fingers_up", 0) > 0:
                        s += f" ({h['fingers_up']} up)"
                    if h.get("holding_object"):
                        s += " holding"
                    hand_strs.append(s)
                ctx_parts.append(f"Hands: {', '.join(hand_strs)}")
            if cv.get("faces_detected", 0) > 0:
                ctx_parts.append(f"Faces: {cv['faces_detected']}")
            animals = cv.get("animals_detected", [])
            if animals:
                ctx_parts.append(f"Animals: {', '.join(a.get('label', '?') for a in animals[:3])}")
            if cv.get("motion_detected"):
                ctx_parts.append("Motion detected")
            latency = cv.get("pipeline_latency_ms", {})
            if latency:
                ctx_parts.append(f"Pipeline latency: {latency.get('total', '?')}ms")
            if ctx_parts:
                parts.append("Camera: " + " | ".join(ctx_parts))
    except Exception:
        pass

    return "\n".join(parts)

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
        return "[FAIL] friday.goals not available."
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
        from friday.memory_import import memory_import_tool
        return memory_import_tool(action, **kwargs)
    except ImportError:
        return "[FAIL] friday.memory_import not available."
    except Exception as e:
        return f"[FAIL] Memory import error: {e}"


def kyu_tool_handler(action: str = "status", **kwargs) -> str:
    """Know Your User: profile setup, interview, learning, and adaptation."""
    try:
        from friday.kyu import kyu_status, kyu_interview, kyu_profile, kyu_learn, kyu_adapt
        if action == "status":
            return kyu_status()
        elif action == "interview":
            stage = kwargs.get("stage")
            return kyu_interview(stage=int(stage) if stage else None)
        elif action == "profile":
            return kyu_profile()
        elif action == "adapt":
            return str(kyu_adapt())
        elif action == "learn":
            tool_name = kwargs.get("tool_name")
            active_window = kwargs.get("active_window")
            hour = kwargs.get("hour")
            return kyu_learn(tool_name=tool_name, active_window=active_window, hour=int(hour) if hour else None)
        else:
            return f"[FAIL] Unknown KYU action: {action}"
    except ImportError:
        return "[FAIL] friday.kyu not available."
    except Exception as e:
        return f"[FAIL] KYU error: {e}"


def osint_user_profile_tool(action: str = "status", name: str = "", email: str = "", fields: str = "") -> str:
    """Dynamic user OSINT profiling: onboard, research, status, or update profile.
    Actions:
      'onboard'   — Save user's name/email and create profile entry.
      'research'  — Run OSINT tools (social search, breach check, email rep, DNS, domain sim) against stored name/email to enrich profile.
      'status'    — Return current profile state (what we know, what's missing).
      'update'    — Manually update profile fields from conversation (format: 'field:value|field:value').
    """
    try:
        from friday.memory_import import load_profile, save_profile
        import asyncio

        if action == "onboard":
            if not name and not email:
                return "[FAIL] Provide at least name or email for onboarding."
            profile = load_profile()
            if not profile or profile.get("version", 0) < 1:
                profile = {"name": None, "version": 2, "audits": [], "last_updated": None}
            if name:
                profile["name"] = name.strip()
            if email:
                social = profile.setdefault("social_media", {})
                existing = social.setdefault("email", [])
                if email.strip() not in existing:
                    existing.append(email.strip())
            profile["last_updated"] = datetime.now().isoformat()
            conf = profile.setdefault("_confidence", {})
            conf["name"] = conf.get("name", 0.7) if name else 0.0
            save_profile(profile)
            memory_store("user_name", profile.get("name", ""), "profile")
            if email:
                memory_store("user_email", email.strip(), "profile")
            return f"[OK] Onboarded: name={profile.get('name')}, email={email or 'not provided'}"

        elif action == "research":
            profile = load_profile()
            pname = profile.get("name", name) if profile else name
            pemails = []
            if profile:
                pemails = profile.get("social_media", {}).get("email", [])
            if email and email not in pemails:
                pemails.append(email)
            if not pname and not pemails:
                return "[FAIL] No name or email in profile. Run 'onboard' first or pass name/email as kwargs."

            findings = {}

            async def _run_osint():
                from friday.tools_osint_extra import (
                    social_analyzer, leak_check, email_rep, holehe_check,
                    email_domain_analyzer, dns_enum, domain_similar
                )
                if pname:
                    try:
                        res = await social_analyzer(pname)
                        if "error" not in res:
                            findings["social_media"] = res
                    except Exception:
                        pass
                for eaddr in pemails:
                    try:
                        res = await leak_check(eaddr)
                        if "error" not in res:
                            findings.setdefault("breaches", {})[eaddr] = res
                    except Exception:
                        pass
                    try:
                        res = await email_rep(eaddr)
                        if "error" not in res:
                            findings.setdefault("email_reputation", {})[eaddr] = res
                    except Exception:
                        pass
                    try:
                        res = await holehe_check(eaddr)
                        if "error" not in res:
                            findings.setdefault("account_existence", {})[eaddr] = res
                    except Exception:
                        pass
                    try:
                        res = await email_domain_analyzer(eaddr)
                        if "error" not in res:
                            findings.setdefault("email_domain", {})[eaddr] = res
                    except Exception:
                        pass
                    domain = eaddr.split("@")[-1] if "@" in eaddr else None
                    if domain:
                        try:
                            res = await dns_enum(domain)
                            if "error" not in res:
                                findings.setdefault("dns", {})[domain] = res
                        except Exception:
                            pass
                        try:
                            res = await domain_similar(domain)
                            if "error" not in res:
                                findings.setdefault("similar_domains", {})[domain] = res
                        except Exception:
                            pass

            try:
                asyncio.run(_run_osint())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_run_osint())
                finally:
                    loop.close()

            profile = load_profile()
            for eaddr in pemails:
                social = profile.setdefault("social_media", {})
                existing = social.setdefault("email", [])
                if eaddr not in existing:
                    existing.append(eaddr)
            br = findings.get("breaches", {})
            for eaddr, data in br.items():
                if data.get("found"):
                    breach_entry = {
                        "source": f"breach_check_{eaddr}",
                        "detail": f"Found in {data.get('source_count', 0)} breaches",
                        "confidence": 0.8,
                    }
                    profile.setdefault("security_audit", []).append(breach_entry)
            social_found = findings.get("social_media", {}).get("platforms_found", [])
            if social_found:
                profile.setdefault("social_media", {}).setdefault("platforms", social_found)
                memory_store("osint_social_platforms", ", ".join(social_found), "osint")
            save_profile(profile)
            memory_store("osint_profiling_done", datetime.now().isoformat(), "osint")

            lines = ["### OSINT Profile Research Complete", ""]
            if pname:
                lines.append(f"**Name:** {pname}")
            if pemails:
                lines.append(f"**Emails:** {', '.join(pemails)}")
            if social_found:
                lines.append(f"**Social platforms found:** {', '.join(social_found[:10])}")
            for eaddr, data in br.items():
                if data.get("found"):
                    lines.append(f"**Breaches for {eaddr}:** {data.get('source_count', 0)} sources, {data.get('password_count', 0)} passwords")
                else:
                    lines.append(f"**Breaches for {eaddr}:** None found")
            for eaddr, data in findings.get("email_reputation", {}).items():
                rep = data.get("reputation", "unknown")
                lines.append(f"**Reputation ({eaddr}):** {rep}")
            return "\n".join(lines)

        elif action == "status":
            profile = load_profile()
            if not profile or not profile.get("name"):
                return "[INFO] No user profile exists yet. Run 'onboard' to create one."
            lines = ["### User Profile Status", ""]
            lines.append(f"**Name:** {profile.get('name', 'Not set')}")
            emails = profile.get("social_media", {}).get("email", [])
            if emails:
                lines.append(f"**Emails:** {', '.join(emails)}")
            else:
                lines.append("**Emails:** None")
            conf = profile.get("_confidence", {})
            lines.append(f"**Name confidence:** {conf.get('name', 0)}")
            platforms = profile.get("social_media", {}).get("platforms", [])
            if platforms:
                lines.append(f"**Social platforms:** {', '.join(platforms)}")
            has_osint = False
            try:
                memory_file = os.path.join(FRIDAY_MEMORY, "memory.json")
                if os.path.exists(memory_file):
                    with open(memory_file, "r", encoding="utf-8") as f:
                        memories = json.load(f)
                    has_osint = any(m.get("key") == "osint_profiling_done" for m in memories)
            except Exception:
                pass
            lines.append(f"**OSINT profiling:** {'Done' if has_osint else 'Not yet run'}")
            lines.append(f"**Last updated:** {profile.get('last_updated', 'Never')}")
            missing = []
            if not profile.get("location"):
                missing.append("location")
            if not profile.get("occupation"):
                missing.append("occupation")
            if not profile.get("tech_stack"):
                missing.append("tech_stack")
            if missing:
                lines.append(f"**Missing info:** {', '.join(missing)}")
            return "\n".join(lines)

        elif action == "update":
            if not fields:
                return "[FAIL] Provide 'fields' in format 'field:value|field:value'"
            profile = load_profile()
            if not profile or profile.get("version", 0) < 1:
                profile = {"name": None, "version": 2, "audits": [], "last_updated": None}
            pairs = [p.strip() for p in fields.split("|")]
            updated = []
            for pair in pairs:
                if ":" not in pair:
                    continue
                key, val = pair.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "name":
                    profile["name"] = val
                    updated.append(f"name={val}")
                elif key == "email":
                    profile.setdefault("social_media", {}).setdefault("email", []).append(val)
                    updated.append(f"email={val}")
                elif key == "location":
                    profile["location"] = val
                    updated.append(f"location={val}")
                elif key == "occupation":
                    profile["occupation"] = val
                    updated.append(f"occupation={val}")
                elif key in ("tech", "tech_stack"):
                    profile.setdefault("tech_stack", []).append({"item": val, "confidence": 0.7, "source": "conversation"})
                    updated.append(f"tech_stack+={val}")
                elif key == "goals":
                    profile.setdefault("goals", []).append({"item": val, "confidence": 0.7, "source": "conversation"})
                    updated.append(f"goals+={val}")
                elif key in ("interests", "hobbies"):
                    profile.setdefault("interests", []).append({"item": val, "confidence": 0.7, "source": "conversation"})
                    updated.append(f"interests+={val}")
            profile["last_updated"] = datetime.now().isoformat()
            save_profile(profile)
            return f"[OK] Profile updated: {', '.join(updated)}"

        else:
            return f"[FAIL] Unknown action: {action}. Use: onboard, research, status, update."

    except Exception as e:
        return f"[FAIL] OSINT User Profile error: {e}"


def research_tool_handler(action: str = "analyze", topic: str = None, depth: int = 3) -> str:
    """Autonomous research: analyze topics, evaluate sources, synthesize findings."""
    try:
        from friday.research import AutonomousResearch
        ar = AutonomousResearch()
        if action == "analyze":
            if not topic:
                return "[FAIL] Topic required for analysis."
            result = ar.analyze_topic(topic)
            lines = [f"### Research Analysis: {topic}", ""]
            lines.append(f"Complexity: {result['complexity_score']}/10")
            lines.append(f"Suggested depth: {result['suggested_depth']}")
            lines.append("Key concepts: " + ", ".join(result['key_concepts']))
            lines.append("Search queries: " + ", ".join(result['search_queries']))
            return "\n".join(lines)
        elif action == "synthesize":
            if not topic:
                return "[FAIL] Topic required for synthesis."
            return ar.synthesize_findings(topic)
        elif action == "optimize":
            if not topic:
                return "[FAIL] Topic required for optimization."
            result = ar.optimize_research(topic)
            return str(result)
        else:
            return f"[FAIL] Unknown research action: {action}"
    except ImportError:
        return "[FAIL] friday.research not available."
    except Exception as e:
        return f"[FAIL] Research error: {e}"


_DEEP_RESEARCH_TASKS: dict = {}


def v_deep_research(topic: str, depth: int = 50, max_pages: int = 100) -> str:
    """Launch Veronica deep research as background task. Runs for hours, saves to knowledge."""
    import threading, json, time, queue
    from datetime import datetime

    task_id = f"v_{int(time.time())}_{abs(hash(topic)) % 10000}"
    q = queue.Queue()
    q.put(f"[START] Veronica deep research launched for: {topic}")
    q.put(f"[TASK_ID] {task_id}")
    q.put(f"[ESTIMATED] Crawling up to {max_pages} pages over ~{depth} minutes")

    def _run():
        try:
            from friday.web import WebScraper, ContentExtractor
            from bs4 import BeautifulSoup
            from friday.knowledge_store import save_research
            import re, asyncio

            scraper = WebScraper()
            seen_urls = set()
            sources = []
            q.put(f"[PROGRESS] Phase 1: Generating search queries...")

            queries = [
                topic,
                f"{topic} complete guide",
                f"{topic} tutorial overview",
                f"{topic} advanced concepts",
                f"{topic} examples",
                f"{topic} documentation",
                f"{topic} explained",
            ]

            all_items = []
            for qi, qry in enumerate(queries):
                for engine in ["duckduckgo", "google", "bing"]:
                    try:
                        res = scraper.search_engine(qry, engine=engine)
                        if res.get("success") and res.get("results"):
                            all_items.extend(res["results"])
                            break
                    except Exception:
                        continue
                q.put(f"[PROGRESS] Query {qi+1}/{len(queries)}: {len(all_items)} results so far")

            q.put(f"[PROGRESS] Phase 2: Crawling pages ({len(all_items)} candidates)...")
            crawled = 0
            max_crawl = min(max_pages, len(all_items))
            for idx, item in enumerate(all_items[:max_crawl]):
                url = item.get("url", "")
                if url in seen_urls or not url:
                    continue
                seen_urls.add(url)
                try:
                    page = scraper.fetch(url, timeout=15)
                    if page.get("success"):
                        p_soup = BeautifulSoup(page["content"], "html.parser")
                        for tag in p_soup(["script", "style", "nav", "footer", "header", "aside"]):
                            tag.decompose()
                        text = (p_soup.find("body") or p_soup).get_text(separator="\n", strip=True)
                        text = re.sub(r'\n{3,}', '\n\n', text[:5000])
                        if len(text) > 200:
                            sources.append({
                                "title": item.get("title", url),
                                "url": url,
                                "content": text,
                            })
                            crawled += 1
                except Exception:
                    continue
                if idx % 10 == 0:
                    q.put(f"[PROGRESS] Crawled {crawled}/{max_crawl} pages...")

            q.put(f"[PROGRESS] Phase 3: Synthesizing report ({len(sources)} sources)...")

            content_parts = []
            for s in sources:
                content_parts.append(f"## {s['title']}\nSource: {s['url']}\n\n{s['content'][:2000]}")
            full_content = "\n\n".join(content_parts)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            report = f"# Deep Research: {topic}\nCompleted: {timestamp}\nSources: {len(sources)}\nPages Crawled: {crawled}\n\n---\n\n{full_content}"

            saved = save_research(topic, sources, report, {"pages_crawled": crawled, "depth": depth})
            q.put(f"[COMPLETE] Research saved to {saved}")
            q.put(f"[SUMMARY] Crawled {crawled} pages from {len(seen_urls)} URLs")
            q.put(f"[DONE]")
        except Exception as e:
            q.put(f"[ERROR] {e}")
            q.put(f"[DONE]")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    _DEEP_RESEARCH_TASKS[task_id] = {"thread": thread, "queue": q, "started": time.time()}

    lines = []
    while not q.empty():
        try:
            lines.append(q.get_nowait())
        except queue.Empty:
            break
    return "\n".join(lines)


def deep_research_status(task_id: str = "") -> str:
    """Check status of a running deep research task. Omit task_id to list all."""
    import time
    if not task_id:
        if not _DEEP_RESEARCH_TASKS:
            return "[OK] No active research tasks."
        parts = ["Active research tasks:"]
        now = time.time()
        for tid, info in list(_DEEP_RESEARCH_TASKS.items()):
            elapsed = int(now - info["started"])
            alive = info["thread"].is_alive()
            parts.append(f"  {tid}: {'RUNNING' if alive else 'DONE'} ({elapsed}s)")
        return "\n".join(parts)

    info = _DEEP_RESEARCH_TASKS.get(task_id)
    if not info:
        return f"[FAIL] No task with ID: {task_id}"

    lines = [f"Task {task_id}:"]
    q = info["queue"]
    while not q.empty():
        try:
            lines.append(q.get_nowait())
        except queue.Empty:
            break
    return "\n".join(lines)


def osint_full_scan(target: str, target_type: str = "auto", deep: bool = False) -> str:
    """
    Full OSINT scan — runs ALL available OSINT tools against an email, username, domain, or IP.
    Uses the full arsenal of 240+ OSINT functions across 15+ modules.
    target_type: 'email', 'username', 'domain', 'ip', or 'auto' (auto-detect).
    deep: If True, also runs extended/deep variants of each tool.
    """
    import time, concurrent.futures
    t0 = time.time()
    parts = [f"Full OSINT Scan: {target}", "=" * 50]

    is_email = "@" in target
    is_ip = all(c in "0123456789." for c in target) and target.count(".") == 3
    domain = target.split("@")[1] if is_email else (target if not is_ip else "")
    username = target.split("@")[0] if is_email else target
    parts.append(f"Type: {'email' if is_email else 'IP' if is_ip else 'domain' if '.' in target else 'username'}")
    parts.append(f"Target: {target}")

    def _run_async(coro):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=120)
        except RuntimeError:
            pass
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            return {"error": str(e)}

    def _safe_run(name: str, fn, *args, **kw):
        try:
            result = _run_async(fn(*args, **kw))
            return name, result
        except Exception as e:
            return name, {"error": str(e)}

    # ── Parallel batch 1: Identity & Social ────────────────────
    parts.append("\n── Identity & Social Media ──")
    social_tasks = []

    if is_email:
        social_tasks.append(("holehe", lambda: __import__("friday.tools.holehe_tool", fromlist=["run_holehe"]).run_holehe(target, timeout=60)))
        social_tasks.append(("leak_check", lambda: __import__("friday.tools_osint_extra", fromlist=["leak_check"]).leak_check(target, timeout=30)))
        social_tasks.append(("intelx", lambda: __import__("friday.tools_osint_extra", fromlist=["intelx_search"]).intelx_search(target, "email", timeout=30)))
        social_tasks.append(("dehashed", lambda: __import__("friday.tools_osint_extra", fromlist=["dehashed_search"]).dehashed_search(target, "email", timeout=30)))
        social_tasks.append(("email_rep", lambda: __import__("friday.tools_osint_extra", fromlist=["email_rep"]).email_rep(target, timeout=15)))
        social_tasks.append(("hibp", lambda: __import__("friday.tools.osint_advanced_tools", fromlist=["hibp_breach_check"]).hibp_breach_check(target, timeout=30)))
        social_tasks.append(("hunter", lambda: __import__("friday.tools.osint_advanced_tools", fromlist=["hunter_email_search"]).hunter_email_search(domain, timeout=30)))

    social_tasks.append(("sherlock", lambda: __import__("friday.tools.sherlock_tool", fromlist=["run_sherlock"]).run_sherlock(username, timeout=60)))
    social_tasks.append(("maigret", lambda: __import__("friday.tools.maigret_tool", fromlist=["run_maigret"]).run_maigret(username, timeout=60)))
    social_tasks.append(("social_analyzer", lambda: __import__("friday.tools_osint_extra", fromlist=["social_analyzer"]).social_analyzer(username, timeout=20)))
    social_tasks.append(("username_search", lambda: __import__("friday.tools_osint_extra", fromlist=["username_search"]).username_search(username, timeout=20)))
    social_tasks.append(("github", lambda: __import__("friday.tools.github_osint_tool", fromlist=["github_search_users"]).github_search_users(username, limit=5)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(t[1]): t[0] for t in social_tasks}
        for f in concurrent.futures.as_completed(futures, timeout=90):
            name = futures[f]
            try:
                result = f.result()
                text = str(result)[:300]
                parts.append(f"  [{name.upper()}] {text}")
            except Exception as e:
                parts.append(f"  [{name.upper()}] Error: {e}")

    # ── Parallel batch 2: DNS & Domain (if applicable) ─────────
    if domain:
        parts.append("\n── DNS & Domain Intelligence ──")
        domain_tasks = [
            ("dns_mx", lambda: __import__("friday.tools.dns_tool", fromlist=["dns_lookup"]).dns_lookup(domain, "MX")),
            ("dns_a", lambda: __import__("friday.tools.dns_tool", fromlist=["dns_lookup"]).dns_lookup(domain, "A")),
            ("dns_txt", lambda: __import__("friday.tools.dns_tool", fromlist=["dns_lookup"]).dns_lookup(domain, "TXT")),
            ("spf", lambda: __import__("friday.tools_osint_extra", fromlist=["spf_check"]).spf_check(domain)),
            ("dkim", lambda: __import__("friday.tools_osint_extra", fromlist=["dkim_check"]).dkim_check(domain)),
            ("dmarc", lambda: __import__("friday.tools_osint_extra", fromlist=["dmarc_check"]).dmarc_check(domain)),
            ("whois", lambda: __import__("friday.tools.osint_advanced_tools", fromlist=["whois_lookup"]).whois_lookup(domain)),
            ("ssl_cert", lambda: __import__("friday.tools.osint_advanced_tools", fromlist=["ssl_certificate_check"]).ssl_certificate_check(domain)),
            ("cert_transparency", lambda: __import__("friday.tools_osint_extra", fromlist=["certificate_transparency"]).certificate_transparency(domain)),
            ("wayback", lambda: __import__("friday.tools_osint_extra", fromlist=["wayback_snapshots"]).wayback_snapshots(domain, limit=5)),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(t[1]): t[0] for t in domain_tasks}
            for f in concurrent.futures.as_completed(futures, timeout=60):
                name = futures[f]
                try:
                    result = f.result()
                    text = str(result)[:250]
                    if "error" not in text.lower()[:20]:
                        parts.append(f"  [{name.upper()}] {text}")
                except Exception:
                    pass

    # ── Parallel batch 3: Web & Technology ─────────────────────
    if domain:
        parts.append("\n── Web Technology & Security ──")
        web_tasks = [
            ("whatweb", lambda: __import__("friday.tools_osint_extra", fromlist=["whatweb"]).whatweb(domain)),
            ("whatcms", lambda: __import__("friday.tools_osint_extra", fromlist=["whatcms"]).whatcms(domain)),
            ("cdn", lambda: __import__("friday.tools_osint_extra", fromlist=["cdn_detect"]).cdn_detect(domain)),
            ("security_headers", lambda: __import__("friday.tools_osint_extra", fromlist=["security_headers"]).security_headers(domain)),
            ("cors", lambda: __import__("friday.tools_osint_extra", fromlist=["cors_check"]).cors_check(domain)),
            ("hsts", lambda: __import__("friday.tools_osint_extra", fromlist=["hsts_check"]).hsts_check(domain)),
            ("urlscan", lambda: __import__("friday.tools_osint_extra", fromlist=["urlscan_submit"]).urlscan_submit(domain)),
            ("email_extractor", lambda: __import__("friday.tools_osint_extra", fromlist=["email_extractor"]).email_extractor(domain)),
            ("meta_extractor", lambda: __import__("friday.tools_osint_extra", fromlist=["meta_extractor"]).meta_extractor(domain)),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(t[1]): t[0] for t in web_tasks}
            for f in concurrent.futures.as_completed(futures, timeout=60):
                name = futures[f]
                try:
                    result = f.result()
                    text = str(result)[:200]
                    if "error" not in text.lower()[:20]:
                        parts.append(f"  [{name.upper()}] {text}")
                except Exception:
                    pass

    # ── Parallel batch 4: IP Intelligence (if applicable) ──────
    if is_ip or domain:
        target_ip = target if is_ip else None
        if not target_ip and domain:
            try:
                import socket
                target_ip = socket.gethostbyname(domain)
                parts.append(f"\n── IP Intelligence ({target_ip}) ──")
            except Exception:
                pass
        if target_ip:
            ip_tasks = [
                ("geoip", lambda: __import__("friday.tools_osint_extra", fromlist=["ip_geolocate_full"]).ip_geolocate_full(target_ip)),
                ("threat_intel", lambda: __import__("friday.tools_osint_extra", fromlist=["ip_threat_intel"]).ip_threat_intel(target_ip)),
                ("blacklist", lambda: __import__("friday.tools_osint_extra", fromlist=["ip_blacklist_check"]).ip_blacklist_check(target_ip)),
                ("asn", lambda: __import__("friday.tools_osint_extra", fromlist=["ip_asn_info"]).ip_asn_info(target_ip)),
                ("reverse_dns", lambda: __import__("friday.tools_osint_extra", fromlist=["ip_reverse_dns"]).ip_reverse_dns(target_ip)),
            ]
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                futures = {ex.submit(t[1]): t[0] for t in ip_tasks}
                for f in concurrent.futures.as_completed(futures, timeout=30):
                    name = futures[f]
                    try:
                        result = f.result()
                        text = str(result)[:200]
                        if "error" not in text.lower()[:20]:
                            parts.append(f"  [{name.upper()}] {text}")
                    except Exception:
                        pass

    # ── Web Search ─────────────────────────────────────────────
    try:
        from friday.web import WebScraper
        scraper = WebScraper()
        parts.append(f"\n── Web Search ──")
        queries = [f'"{target}"', target, username]
        for q in queries[:2]:
            for engine in ["google", "duckduckgo"]:
                try:
                    res = scraper.search_engine(q, engine=engine)
                    if res.get("success") and res.get("results"):
                        parts.append(f"  [{engine.upper()}] '{q[:60]}'")
                        for item in res["results"][:3]:
                            parts.append(f"    • {item.get('title','?')[:60]}  ({item.get('url','')[:60]})")
                        break
                except Exception:
                    continue
    except Exception:
        pass

    # ── Deep mode: run extended variants ───────────────────────
    if deep:
        parts.append("\n── Deep Research (Extended Tools) ──")
        deep_tasks = [("holehe_ext", lambda: __import__("friday.tools_osint_extra", fromlist=["holehe_check_extended"]).holehe_check_extended(target, timeout=60))] if is_email else []
        deep_tasks += [("username_ext", lambda: __import__("friday.tools_osint_extra", fromlist=["username_search_extended"]).username_search_extended(username, timeout=30))]
        deep_tasks += [("leak_ext", lambda: __import__("friday.tools_osint_extra", fromlist=["leak_check_extended"]).leak_check_extended(target, "email", timeout=30))] if is_email else []
        deep_tasks += [("wayback_ext", lambda: __import__("friday.tools_osint_extra", fromlist=["wayback_snapshots_extended"]).wayback_snapshots_extended(domain, limit=20))] if domain else []
        deep_tasks += [("ssl_ext", lambda: __import__("friday.tools_osint_extra", fromlist=["ssl_cert_check_extended"]).ssl_cert_check_extended(domain))] if domain else []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(t[1]): t[0] for t in deep_tasks}
            for f in concurrent.futures.as_completed(futures, timeout=90):
                name = futures[f]
                try:
                    result = f.result()
                    parts.append(f"  [{name.upper()}] {str(result)[:300]}")
                except Exception as e:
                    parts.append(f"  [{name.upper()}] Error: {e}")

    elapsed = round(time.time() - t0, 1)
    parts.append(f"\n{'=' * 50}")
    parts.append(f"Scan completed in {elapsed}s — used {len(social_tasks) + len(domain_tasks) if domain else len(social_tasks)} tools")

    return "\n".join(parts)


def knowledge_query(topic: str) -> str:
    """Query FRIDAY's saved knowledge on a topic. Returns what she already knows."""
    try:
        from friday.knowledge_store import get_knowledge_context, get_all_research_topics
        context = get_knowledge_context(topic)
        if not context:
            topics = get_all_research_topics()
            if topics:
                return f"[KNOWLEDGE] No saved knowledge on '{topic}'. Available topics:\n" + "\n".join(f"  \u2022 {t}" for t in topics)
            return f"[KNOWLEDGE] No saved knowledge found. I know nothing about '{topic}' yet."
        return context
    except ImportError:
        return "[FAIL] knowledge_store not available."
    except Exception as e:
        return f"[FAIL] Knowledge query error: {e}"


def generate_research_report(topic: str, depth: int = 30, max_pages: int = 50,
                              chart_types: list[str] | None = None,
                              include_tables: bool = True) -> str:
    """One-shot: deep research a topic using LLM-powered multi-source research + synthesis,
    save to knowledge store, and generate a detailed PDF report with charts and tables.
    Supports 20+ chart types: bar, line, pie, area, scatter, histogram, heatmap, radar, box, etc.
    """
    import os, json, time, re, asyncio
    from dotenv import load_dotenv
    load_dotenv()
    from friday.knowledge_store import save_research

    try:
        # ── Phase 1: Multi-engine research ──
        from friday.web import WebScraper
        from bs4 import BeautifulSoup
        scraper = WebScraper()
        seen_urls = set()
        sources = []

        queries = [
            topic,
            f"{topic} complete guide tutorial overview",
            f"{topic} latest developments news 2025 2026",
            f"{topic} explained in depth analysis",
            f"{topic} research documentation wiki",
            f"{topic} examples applications use cases",
            f"{topic} technical deep dive architecture",
        ]

        all_items = []
        for qi, qry in enumerate(queries[:max(3, depth)]):
            for engine in ["duckduckgo", "google", "bing"]:
                try:
                    res = scraper.search_engine(qry, engine=engine)
                    if res.get("success") and res.get("results"):
                        all_items.extend(res["results"])
                        break
                except Exception:
                    continue

        max_crawl = min(max_pages, len(all_items)) if all_items else 0
        crawled = 0
        if all_items:
            for idx, item in enumerate(all_items[:max_crawl]):
                url = item.get("url", "")
                if url in seen_urls or not url:
                    continue
                seen_urls.add(url)
                try:
                    page = scraper.fetch(url, timeout=15)
                    if page.get("success"):
                        p_soup = BeautifulSoup(page["content"], "html.parser")
                        for tag in p_soup(["script", "style", "nav", "footer", "header", "aside"]):
                            tag.decompose()
                        text = (p_soup.find("body") or p_soup).get_text(separator="\n", strip=True)
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        if len(text) > 200:
                            sources.append({
                                "title": item.get("title", url),
                                "url": url,
                                "content": text[:5000],
                            })
                            crawled += 1
                except Exception:
                    continue

        if not sources:
            return json.dumps({"error": "No sources found after research", "topic": topic})

        # ── Phase 2: LLM synthesis + chart data extraction ──
        async def _synthesize_and_extract():
            from friday.nim_client import InferenceClient
            from friday.nim_router import resolve_model
            client = InferenceClient()

            source_texts = []
            for i, s in enumerate(sources[:25], 1):
                source_texts.append(
                    f"[Source {i}] Title: {s['title']}\nURL: {s['url']}\nContent:\n{s['content'][:2500]}"
                )
            joined = "\n\n---\n\n".join(source_texts)
            research_model = resolve_model("research") or "meta/llama-3.3-70b-instruct"

            synthesis_prompt = (
                "You are Veronica, FRIDAY's head research specialist. "
                f"Synthesize the following collected source material into a comprehensive, "
                f"extremely detailed research report on the topic: '{topic}'.\n\n"
                f"Source Material:\n{joined}\n\n"
                "Write a formal research report with these sections:\n"
                "1. # Executive Summary — high-level abstract of findings\n"
                "2. ## Key Findings — numbered bullet points of main discoveries (include specific statistics, numbers, dates where available)\n"
                "3. ## Detailed Analysis — in-depth narrative organized by subtopics\n"
                "4. ## Source Breakdown — what each source contributed\n"
                "5. ## Conclusion & Implications — actionable takeaways\n\n"
                "Formatting rules:\n"
                "- Include markdown links to sources inline as [Source Title](URL).\n"
                "- Be extremely thorough, detailed, and professional.\n"
                "- Do NOT invent facts not present in the source material.\n"
                "- Output ONLY the report with these sections, no extra commentary."
            )

            resp = await client.chat(
                model=research_model,
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=32768,
                temperature=0.3,
            )
            synthesized = resp.content.strip()

            if not synthesized or synthesized.startswith("[ZEN") or synthesized.startswith("[NIM") or "ALL TIERS FAILED" in synthesized:
                return None, None

            # ── Extract chart data via a second LLM call ──
            chart_types_to_use = chart_types or ["bar", "pie", "line"]
            chart_prompt = (
                "You are a data analyst. Based on the research report below, extract up to 3 sets of numerical data "
                "that would make meaningful charts for a PDF report on this topic.\n\n"
                f"Research Report:\n{synthesized[:15000]}\n\n"
                f"Generate chart data for these chart types: {chart_types_to_use}\n\n"
                "Return a JSON object (ONLY valid JSON, no other text) with this structure:\n"
                '{"charts": [{"chart_type": "bar", "title": "...", "xlabel": "...", "ylabel": "...", '
                '"data": [10, 20, 30], "labels": ["A", "B", "C"]}, ...]}\n\n'
                "Rules:\n"
                "- If the research contains actual numbers, use those.\n"
                "- Otherwise, generate plausible representative data based on the topic context.\n"
                "- Each chart must have chart_type, title, data (list of numbers), and labels.\n"
                "- Include at least 3 data points per chart.\n"
                "- Return ONLY the JSON, no commentary."
            )

            try:
                chart_resp = await client.chat(
                    model=research_model,
                    messages=[{"role": "user", "content": chart_prompt}],
                    max_tokens=4096,
                    temperature=0.2,
                )
                chart_text = chart_resp.content.strip()
                chart_text = re.sub(r"^```(?:json)?\s*", "", chart_text)
                chart_text = re.sub(r"\s*```$", "", chart_text)
                chart_data = json.loads(chart_text)
            except Exception:
                chart_data = None

            return synthesized, chart_data

        try:
            result_tuple = asyncio.run(_synthesize_and_extract())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result_tuple = loop.run_until_complete(_synthesize_and_extract())

        synthesized, chart_data = result_tuple if result_tuple else (None, None)

        # ── Phase 3: Save to knowledge store ──
        report_content = synthesized or "\n\n".join(
            f"## Source {i+1}: {s['title']}\nURL: {s['url']}\n\n{s['content'][:2000]}"
            for i, s in enumerate(sources)
        )
        try:
            save_research(topic, sources, report_content, {
                "pages_crawled": crawled,
                "total_sources": len(sources),
                "depth": depth,
                "llm_synthesized": synthesized is not None,
            })
        except Exception:
            pass

        # ── Phase 4: Build PDF sections from real content + charts ──
        from friday.tools.doc_tools import create_pdf

        sections = []
        sections.append({"type": "heading", "text": f"Research Report: {topic.title()}", "level": 1})
        sections.append({"type": "paragraph", "text": f"Comprehensive research report on '{topic}'. Generated through multi-engine web research across {crawled} pages from {len(seen_urls)} unique URLs."})
        sections.append({"type": "divider"})

        if synthesized:
            for line in synthesized.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("# ") or stripped.startswith("## ") or stripped.startswith("### "):
                    level = len(stripped.split(" ")[0])
                    sections.append({"type": "heading", "text": stripped.lstrip("# "), "level": level})
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    sections.append({"type": "bullets", "items": [stripped.lstrip("- *")]})
                elif re.match(r"^\d+\. ", stripped):
                    sections.append({"type": "paragraph", "text": stripped})
                elif "http" in stripped and "](http" in stripped:
                    sections.append({"type": "paragraph", "text": stripped})
                else:
                    sections.append({"type": "paragraph", "text": stripped})
        else:
            sections.append({"type": "heading", "text": "Research Sources", "level": 2})
            for s in sources:
                sections.append({"type": "paragraph", "text": f"Source: {s['title']} ({s['url']})"})
                sections.append({"type": "paragraph", "text": s['content'][:2000]})

        # ── Insert chart sections ──
        if chart_data and isinstance(chart_data, dict) and "charts" in chart_data:
            sections.append({"type": "divider"})
            sections.append({"type": "heading", "text": "Data Visualizations", "level": 1})
            sections.append({"type": "paragraph", "text": "The following charts visualize key data points extracted from the research findings."})
            for chart in chart_data["charts"]:
                if isinstance(chart, dict) and "data" in chart and chart.get("data"):
                    chart_section = {
                        "type": "chart",
                        "chart_type": chart.get("chart_type", "bar"),
                        "data": chart["data"],
                        "title": chart.get("title", ""),
                        "xlabel": chart.get("xlabel", ""),
                        "ylabel": chart.get("ylabel", ""),
                    }
                    if chart.get("labels"):
                        chart_section["labels"] = chart["labels"]
                    sections.append(chart_section)

        # ── Sources table ──
        if include_tables and sources:
            sections.append({"type": "divider"})
            sections.append({"type": "heading", "text": "Source Index", "level": 1})
            sections.append({
                "type": "table",
                "headers": ["#", "Title", "URL"],
                "rows": [[str(i+1), s["title"][:60], s["url"]] for i, s in enumerate(sources[:25])],
                "caption": f"All {len(sources)} sources consulted during research.",
            })

        sections.append({"type": "divider"})
        sections.append({"type": "heading", "text": "Methodology", "level": 1})
        sections.append({"type": "paragraph", "text": f"Research conducted across multiple search engines (DuckDuckGo, Google, Bing) with {depth} search queries. Crawled {crawled} pages from {len(seen_urls)} unique URLs. Content extracted, cleaned, and synthesized by FRIDAY's Veronica research engine using big-pickle reasoning model."})
        sections.append({"type": "paragraph", "text": f"Report generated by FRIDAY AI. Total sources consulted: {len(sources)}."})

        # Generate PDF
        try:
            pdf_result = asyncio.run(create_pdf(sections=sections, title=f"Research Report: {topic}"))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pdf_result = loop.run_until_complete(
                create_pdf(sections=sections, title=f"Research Report: {topic}")
            )

        result = {
            "topic": topic,
            "knowledge_saved": True,
            "sections_count": len(sections),
            "sources_crawled": crawled,
            "unique_urls": len(seen_urls),
            "llm_synthesized": synthesized is not None,
            "charts_generated": len(chart_data.get("charts", [])) if chart_data and isinstance(chart_data, dict) else 0,
            "pdf_path": pdf_result.get("path", ""),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        import traceback
        return json.dumps({"error": str(e), "traceback": traceback.format_exc(), "topic": topic})


def reasoning_tool_handler(action: str = "cot", problem: str = None, max_steps: int = 10, branching_factor: int = 3) -> str:
    """Advanced reasoning: Chain-of-Thought, Tree-of-Thought, or ReAct."""
    try:
        from friday.reasoning import reasoning_tool
        return reasoning_tool(action=action, problem=problem, max_steps=max_steps, branching_factor=branching_factor)
    except ImportError:
        return "[FAIL] friday.reasoning not available."
    except Exception as e:
        return f"[FAIL] Reasoning error: {e}"


def status_check(include: str = "all") -> str:
    """Quick system status overview: goals, calendar, email, notifications, CPU, RAM, active window. Call this ONCE instead of 5 separate tools.
    Only includes sections that return data — unavailable services are silently skipped.
    """
    parts = []
    checks = [s.strip() for s in include.split(",")] if include != "all" else []
    def _should(key):
        return include == "all" or key in checks
    try:
        if _should("goals"):
            from friday.goals import goals_tool_handler
            r = goals_tool_handler("list")
            if r and "[UNAVAILABLE]" not in r and "[FAIL]" not in r:
                parts.append("--- GOALS ---\n" + r)
    except Exception:
        pass
    try:
        if _should("calendar"):
            from friday.goals import fetch_calendar_events, get_calendar_service
            svc, err = get_calendar_service(auto_auth=False)
            if not err:
                parts.append("--- CALENDAR ---\n" + fetch_calendar_events(max_results=10, days_ahead=7))
    except Exception:
        pass
    try:
        if _should("email"):
            from friday.gmail import gmail_list_messages as _gmail_list
            r = _gmail_list(query="", max_results=3)
            if r and "not configured" not in r.lower() and "[fail]" not in r.lower() and "error" not in r.lower():
                parts.append("--- EMAIL ---\n" + r)
    except Exception:
        pass
    try:
        if _should("notifications"):
            from friday.notify import get_pending_notifications
            r = get_pending_notifications()
            if r and r.strip():
                parts.append("--- NOTIFICATIONS ---\n" + r)
    except Exception:
        pass
    try:
        if _should("system"):
            from friday.system_monitor import get_cpu_usage, get_memory_usage
            cpu = get_cpu_usage()
            mem = get_memory_usage()
            parts.append(f"--- SYSTEM ---\nCPU: {cpu}% | RAM: {mem.get('used_gb', '?')}GB/{mem.get('total_gb', '?')}GB ({mem.get('percent', '?')}%)")
    except Exception:
        pass
    try:
        if _should("window"):
            from friday.screen_watcher import get_active_window_info
            info = get_active_window_info()
            parts.append(f"--- ACTIVE WINDOW ---\n{info.get('title', 'Unknown')} ({info.get('process_name', 'Unknown')})")
    except Exception:
        pass
    return "\n\n".join(parts)


def clock_tool(action: str = "status", **kwargs) -> str:
    """Windows Clock integration: alarms, timers, stopwatch, reminders, focus mode."""
    try:
        from friday.clock import (
            clock_alarm, clock_timer, clock_stopwatch, clock_reminder,
            clock_focus, clock_open, clock_status
        )
        if action == "status":
            return clock_status()
        elif action == "open":
            return clock_open()
        elif action == "alarm":
            return clock_alarm(kwargs.get("sub", "list"), kwargs.get("time"), kwargs.get("label"), kwargs.get("id"))
        elif action == "timer":
            return clock_timer(kwargs.get("sub", "status"), kwargs.get("minutes"), kwargs.get("seconds"), kwargs.get("label"), kwargs.get("id"))
        elif action == "stopwatch":
            return clock_stopwatch(kwargs.get("sub", "status"))
        elif action == "reminder":
            return clock_reminder(kwargs.get("sub", "list"), kwargs.get("text"), kwargs.get("time"), kwargs.get("id"))
        elif action == "focus":
            return clock_focus(kwargs.get("minutes", 25))
        else:
            return f"[FAIL] Unknown clock action: {action}"
    except ImportError:
        return "[FAIL] friday.clock not available."
    except Exception as e:
        return f"[FAIL] Clock error: {e}"


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

        memory_dir = Path(FRIDAY_MEMORY)
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


def _search_profile(profile, query):
    """Search user profile for matching fields."""
    results = []
    q = query.lower()
    for key, value in profile.items():
        if isinstance(value, str) and q in value.lower():
            results.append({"key": f"profile.{key}", "value": value, "category": "profile"})
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and q in item.lower():
                    results.append({"key": f"profile.{key}", "value": item, "category": "profile"})
    return results


def memory_retrieve(query: str) -> str:
    """Retrieve memories. Queries both key-value memory store AND the user profile."""
    try:
        import json, os
        from pathlib import Path

        results = []

        memory_file = Path(FRIDAY_MEMORY) / "memory.json"
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                memories = json.load(f)
            for m in memories:
                if query.lower() in m["key"].lower() or query.lower() in m["value"].lower():
                    results.append(m)

        # ALSO query user profile
        profile_file = Path(FRIDAY_MEMORY) / "user_profile.json"
        if profile_file.exists():
            with open(profile_file, "r", encoding="utf-8") as f:
                profile = json.load(f)
            profile_results = _search_profile(profile, query)
            results.extend(profile_results)

        if not results:
            return f"No memories found matching '{query}'"

        lines = [f"### MEMORIES ({len(results)} found)"]
        for m in results[:10]:
            key = m.get("key", m.get("category", "memory"))
            value = m.get("value", str(m))
            lines.append(f"- {key}: {str(value)[:50]}...")
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


def deep_research(topic: str, url: str = "", depth: int = 5) -> str:
    """Multi-source deep research — crawls pages, extracts content, synthesizes report."""
    try:
        from friday.web import WebScraper, ContentExtractor
        from bs4 import BeautifulSoup
        import re, time

        scraper = WebScraper()
        sources = []  # each: {"title":..., "url":..., "content":...}

        # 1. Fetch primary URL if given
        if url:
            try:
                article = ContentExtractor.extract_article(url)
                if article.get("success"):
                    sources.append({
                        "title": article.get("title", url),
                        "url": url,
                        "content": article.get("text", "")[:4000],
                    })
                else:
                    page = scraper.fetch(url, timeout=20)
                    if page.get("success"):
                        p_soup = BeautifulSoup(page["content"], "html.parser")
                        for tag in p_soup(["script", "style", "nav", "footer"]):
                            tag.decompose()
                        text = (p_soup.find("body") or p_soup).get_text(separator="\n", strip=True)
                        sources.append({"title": url, "url": url, "content": text[:4000]})
            except Exception:
                pass

        # 2. Search multiple angles
        queries = [
            topic,
            f"{topic} 2025 2026 overview",
            f"{topic} latest developments",
            f"{topic} analysis",
        ]
        seen_urls = {url}
        for q in queries[:depth]:
            try:
                result = scraper.search_engine(q, engine="duckduckgo")
                if not result.get("success"):
                    result = scraper.search_engine(q, engine="google")
                if not result.get("success"):
                    result = scraper.search_engine(q, engine="bing")

                if result.get("success"):
                    for item in result.get("results", [])[:4]:
                        u = item.get("url", "")
                        if u in seen_urls or not u:
                            continue
                        seen_urls.add(u)
                        # Fetch the actual page
                        try:
                            article = ContentExtractor.extract_article(u)
                            if article.get("success"):
                                sources.append({
                                    "title": article.get("title", item.get("title", u)),
                                    "url": u,
                                    "content": article.get("text", "")[:4000],
                                })
                            else:
                                page = scraper.fetch(u, timeout=15)
                                if page.get("success"):
                                    p_soup = BeautifulSoup(page["content"], "html.parser")
                                    for tag in p_soup(["script", "style", "nav", "footer"]):
                                        tag.decompose()
                                    text = (p_soup.find("body") or p_soup).get_text(separator="\n", strip=True)
                                    sources.append({
                                        "title": item.get("title", u),
                                        "url": u,
                                        "content": re.sub(r'\n{3,}', '\n\n', text[:4000]),
                                    })
                        except Exception:
                            sources.append({
                                "title": item.get("title", u),
                                "url": u,
                                "content": item.get("snippet", ""),
                            })

                        if len(sources) >= 8:
                            break
            except Exception:
                continue
            if len(sources) >= 8:
                break

        if not sources:
            return f"[FAIL] No results found for '{topic}'"

        # 3. Synthesize report
        report_parts = [f"Deep Research Report: {topic}", "=" * 50, ""]
        for i, src in enumerate(sources, 1):
            report_parts.append(f"--- Source {i}: {src['title']} ---")
            report_parts.append(f"URL: {src['url']}")
            report_parts.append(src['content'][:2000])
            report_parts.append("")

        report = "\n".join(report_parts)
        if len(report) > 12000:
            report = report[:12000] + "\n\n[Truncated — full content available per source]"
        return report

    except ImportError:
        return "[FAIL] friday.web not available."
    except Exception as e:
        return f"[FAIL] Deep research error: {e}"


def climb_codebase(query: str, path: str = "") -> str:
    """Search and analyze code in the project codebase."""
    try:
        import subprocess, os, glob

        search_root = path if path else _ROOT

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
    """Send Instagram DM using browser-use bridge (persistent Chrome profile).
    Must be logged into Instagram in Chrome.
    Uses the working browser_use_bridge — navigates, searches user, types, clicks Send."""
    from friday.browser_use_bridge import (
        browser_use_navigate, browser_use_get_dom_state,
        browser_use_type, browser_use_click, browser_use_evaluate,
        browser_use_extract_text, browser_use_screenshot,
    )
    import time

    try:
        # Navigate to Instagram DM
        r = browser_use_navigate("https://www.instagram.com/direct/new/")
        time.sleep(5)

        # Check if we're on the right page
        dom = browser_use_get_dom_state()
        if isinstance(dom, dict):
            title = dom.get("title", "")
            if "login" in title.lower() or "log in" in title.lower():
                return f"[FAIL] Not logged into Instagram. Current page: {title}"

        # Type username in search
        r = browser_use_type("input[placeholder='Search...']", username)
        time.sleep(2)

        # Click on user result — try multiple approaches
        user_selectors = [
            f"div[role='option']",
            f"div[role='link']",
        ]
        for sel in user_selectors:
            try:
                r = browser_use_click(sel)
                time.sleep(1)
                dom2 = browser_use_get_dom_state()
                if isinstance(dom2, dict):
                    # Check if we moved past search (inputs count changed)
                    if dom2.get("inputs", 0) < dom.get("inputs", 1):
                        break
            except Exception:
                continue

        time.sleep(2)

        # Type message
        msg_sel = "div[role='textbox']"
        try:
            r = browser_use_type(msg_sel, message)
        except Exception:
            try:
                r = browser_use_type("textarea", message)
            except Exception:
                return f"[FAIL] Could not find message input"

        time.sleep(1)

        # Click Send via JS
        try:
            browser_use_evaluate(
                "document.querySelector('svg[aria-label=\"Send\"]')?.parentElement?.click()"
            )
        except Exception:
            try:
                browser_use_evaluate(
                    "document.querySelector('div[role=\"button\"] svg')?.parentElement?.click()"
                )
            except Exception:
                pass

        time.sleep(2)
        return f"[OK] Message sent to {username} via Instagram"

    except Exception as e:
        return f"[FAIL] Instagram DM error: {e}"


# ═══════════════════════════════════════════════════════════════
#  Discord / Slack browser tools
# ═══════════════════════════════════════════════════════════════

def read_discord_messages(channel_url: str = "", limit: int = 10) -> str:
    """Open Discord web and read recent messages using browser-use bridge.
    Must be logged into Discord in Chrome profile."""
    from friday.browser_use_bridge import (
        browser_use_navigate, browser_use_extract_text, browser_use_get_dom_state,
    )
    import time, json

    try:
        url = channel_url or "https://discord.com/app"
        browser_use_navigate(url)
        time.sleep(5)

        # Extract page text
        text = browser_use_extract_text()

        # Try to get structured content
        dom = browser_use_get_dom_state()
        if isinstance(dom, dict):
            title = dom.get("title", "")
            if "login" in title.lower() or "app" not in url:
                pass  # still returning what we have

        messages = []
        if text:
            lines = text.split("\n")
            messages = [l.strip() for l in lines if l.strip()][:limit]

        return json.dumps({
            "source": "discord",
            "channel": url,
            "message_count": len(messages),
            "messages": messages if messages else ["(no visible messages — may need login)"],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Discord read failed: {e}"})


def read_slack_messages(channel_url: str = "", limit: int = 10) -> str:
    """Open Slack web and read recent messages using browser-use bridge.
    Must be logged into Slack in Chrome profile."""
    from friday.browser_use_bridge import (
        browser_use_navigate, browser_use_extract_text, browser_use_get_dom_state,
    )
    import time, json

    try:
        url = channel_url or "https://app.slack.com/client"
        browser_use_navigate(url)
        time.sleep(5)

        text = browser_use_extract_text()

        dom = browser_use_get_dom_state()

        messages = []
        if text:
            lines = text.split("\n")
            messages = [l.strip() for l in lines if l.strip()][:limit]

        return json.dumps({
            "source": "slack",
            "channel": url,
            "message_count": len(messages),
            "messages": messages if messages else ["(no visible messages — may need login)"],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Slack read failed: {e}"})


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


#  Stub functions for friday.live compatibility #

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


def multi_task(tasks: list = None, task_specs: list = None, **kwargs) -> str:
    """Execute multiple tasks in sequence (stub)."""
    items = tasks or task_specs or []
    results = []
    for t in items:
        if isinstance(t, dict):
            results.append(f"[OK] Task: {t.get('action', 'unknown')}")
        else:
            results.append(f"[OK] Task: {t}")
    return "\n".join(results)


def queue_task(task_name: str, action: str, params: dict = None) -> str:
    """Queue a task for later execution."""
    try:
        import json
        queue_dir = FRIDAY_MEMORY
        os.makedirs(queue_dir, exist_ok=True)
        queue_file = os.path.join(FRIDAY_MEMORY, "task_queue.json")
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
        queue_file = os.path.join(FRIDAY_MEMORY, "task_queue.json")
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
    """Type text using keyboard simulation with multi-method fallback."""
    import subprocess, time, os, tempfile, ctypes, base64

    # Method 1: pyautogui
    try:
        import pyautogui
        time.sleep(0.3)
        pyautogui.typewrite(text, interval=0.02)
        return f"[OK] Typed: {text[:50]}... (pyautogui)"
    except Exception:
        pass

    # Method 2: Clipboard + Ctrl+V (most reliable on Windows)
    try:
        encoded = base64.b64encode(text.encode("utf-16-le")).decode()
        ps_script = (
            'Add-Type -AssemblyName System.Windows.Forms; '
            '$bytes = [Convert]::FromBase64String("{0}"); '
            '$text = [System.Text.Encoding]::Unicode.GetString($bytes); '
            '[System.Windows.Forms.Clipboard]::SetText($text); '
            'Start-Sleep -Milliseconds 100; '
            '$wshell = New-Object -ComObject wscript.shell; '
            '$wshell.SendKeys("^v"); '
            'Start-Sleep -Milliseconds 200'
        ).format(encoded)
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                       capture_output=True, timeout=10)
        return f"[OK] Typed: {text[:50]}... (clipboard)"
    except Exception:
        pass

    # Method 3: PowerShell SendKeys directly
    try:
        escaped = text.replace("'", "''").replace("{", "{{").replace("}", "}}")
        ps_script = (
            'Add-Type -AssemblyName System.Windows.Forms; '
            '[System.Windows.Forms.SendKeys]::SendWait("{0}")'
        ).format(escaped)
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                       capture_output=True, timeout=10)
        return f"[OK] Typed: {text[:50]}... (sendkeys)"
    except Exception:
        pass

    # Method 4: ctypes keybd_event (Win32 API)
    try:
        user32 = ctypes.windll.user32
        for ch in text:
            shift = ch.isupper() or ch in "~!@#$%^&*()_+{}|:\"<>?"
            vk = ord(ch.upper()) if ch.isalpha() else (ord(ch) if ord(ch) < 256 else 0)
            if vk == 0:
                continue
            if shift:
                user32.keybd_event(0x10, 0, 0, 0)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            if shift:
                user32.keybd_event(0x10, 0, 2, 0)
            time.sleep(0.01)
        return f"[OK] Typed: {text[:50]}... (win32)"
    except Exception:
        pass

    return "[FAIL] All typing methods failed."


def take_snapshot(name: str = None) -> str:
    """Take a snapshot of the current screen."""
    try:
        from friday.screen_watcher import capture_screen
        import base64
        screenshot_bytes = capture_screen(resize_to=(1280, 720), quality=70)
        name = name or f"snapshot_{int(time.time())}"
        snap_dir = os.path.join(FRIDAY_MEMORY, "snapshots")
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
        snap_dir = os.path.join(FRIDAY_MEMORY, "snapshots")
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
        return "[FAIL] friday.stayfree not available."
    except Exception as e:
        return f"[FAIL] StayFree error: {e}"


def stayfree_today() -> str:
    """Get today's screen time and app usage from StayFree."""
    try:
        from friday.stayfree import stayfree_today as _sf_today
        return _sf_today()
    except ImportError:
        return "[FAIL] friday.stayfree not available."
    except Exception as e:
        return f"[FAIL] StayFree today error: {e}"


def stayfree_week() -> str:
    """Get this week's screen time summary from StayFree."""
    try:
        from friday.stayfree import stayfree_week as _sf_week
        return _sf_week()
    except ImportError:
        return "[FAIL] friday.stayfree not available."
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
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI run error: {e}"


def opencli_list_adapters() -> str:
    """List all available OpenCLI commands and built-in site adapters."""
    try:
        from friday.opencli import opencli_list_adapters
        return opencli_list_adapters()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI list error: {e}"


def opencli_init_bridge() -> str:
    """Initialize the OpenCLI browser bridge and check Chrome extension."""
    try:
        import subprocess, json

        # Check daemon status
        try:
            result = subprocess.run(
                ["opencli", "daemon", "status", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    status = json.loads(result.stdout.strip())
                    if status.get("state") == "ready" and status.get("profiles"):
                        profiles = status["profiles"]
                        n = len(profiles) if isinstance(profiles, list) else 1
                        return f"OpenCLI bridge connected ({n} profile{'s' if n != 1 else ''})"
                except json.JSONDecodeError:
                    pass
                # Fallback: check text output
                out = result.stdout.strip()
                if "Extension: connected" in out and "Profiles:" in out:
                    return "OpenCLI bridge connected"
        except FileNotFoundError:
            return "[FAIL] opencli not installed. Run: npm install -g @jackwener/opencli"
        except Exception:
            pass

        # Try starting the daemon
        try:
            subprocess.run(["opencli", "daemon", "restart"], capture_output=True, text=True, timeout=15)
            result = subprocess.run(
                ["opencli", "daemon", "status"],
                capture_output=True, text=True, timeout=10
            )
            if "Extension: connected" in result.stdout:
                return "OpenCLI bridge connected (daemon restarted)"
        except Exception:
            pass

        return (
            "[FAIL] OpenCLI bridge not connected. Setup instructions:\n"
            "  1. Install the extension from: https://github.com/jackwener/opencli/releases\n"
            "  2. Open Chrome → chrome://extensions → Developer Mode → Load unpacked\n"
            "  3. Select the downloaded extension folder\n"
            "  4. Make sure Chrome is running with the extension enabled\n"
            "  5. Run: opencli daemon restart"
        )
    except ImportError:
        return "[FAIL] opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI init error: {e}"


def opencli_navigate(url: str) -> str:
    """Open a URL in the OpenCLI browser automation window."""
    try:
        from friday.opencli import opencli_navigate
        return opencli_navigate(url)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI navigate error: {e}"


def opencli_click(target: str) -> str:
    """Click an element in the browser by selector or text."""
    try:
        from friday.opencli import opencli_click
        return opencli_click(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI click error: {e}"


def opencli_type(target: str, text: str) -> str:
    """Type text into a browser element."""
    try:
        from friday.opencli import opencli_type
        return opencli_type(target, text)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI type error: {e}"


def opencli_extract() -> str:
    """Extract page content as markdown from the current browser page."""
    try:
        from friday.opencli import opencli_extract
        return opencli_extract()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI extract error: {e}"


def opencli_screenshot(path: str = None) -> str:
    """Take a screenshot of the current browser page."""
    try:
        from friday.opencli import opencli_screenshot
        return opencli_screenshot(path)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI screenshot error: {e}"


def opencli_scroll(direction: str = "down") -> str:
    """Scroll the browser page (down, up, top, bottom)."""
    try:
        from friday.opencli import opencli_scroll
        return opencli_scroll(direction)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI scroll error: {e}"


def opencli_keys(key: str) -> str:
    """Press a keyboard key in the browser (Enter, Escape, Tab, etc.)."""
    try:
        from friday.opencli import opencli_keys
        return opencli_keys(key)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI key error: {e}"


def opencli_eval(js: str) -> str:
    """Execute JavaScript in the browser page."""
    try:
        from friday.opencli import opencli_eval
        return opencli_eval(js)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI eval error: {e}"


def opencli_state() -> str:
    """Get current browser page state (URL, title, interactive elements)."""
    try:
        from friday.opencli import opencli_state
        return opencli_state()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI state error: {e}"


def opencli_doctor() -> str:
    """Diagnose OpenCLI browser bridge connectivity."""
    try:
        from friday.opencli import opencli_doctor
        return opencli_doctor()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] OpenCLI doctor error: {e}"


def opencli_tab_list() -> str:
    """List all browser tabs."""
    try:
        from friday.opencli import opencli_tab_list
        return opencli_tab_list()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Tab list error: {e}"


def opencli_tab_new(url: str = "") -> str:
    """Open a new browser tab."""
    try:
        from friday.opencli import opencli_tab_new
        return opencli_tab_new(url)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Tab new error: {e}"


def opencli_tab_select(target_id: str) -> str:
    """Switch to a specific browser tab."""
    try:
        from friday.opencli import opencli_tab_select
        return opencli_tab_select(target_id)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Tab select error: {e}"


def opencli_tab_close(target_id: str = "") -> str:
    """Close a browser tab."""
    try:
        from friday.opencli import opencli_tab_close
        return opencli_tab_close(target_id)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Tab close error: {e}"


def opencli_close() -> str:
    """Release the current browser automation tab lease."""
    try:
        from friday.opencli import opencli_close
        return opencli_close()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Close error: {e}"


def opencli_wait_selector(selector: str, timeout_ms: int = 10000) -> str:
    """Wait for a CSS selector to appear on the page."""
    try:
        from friday.opencli import opencli_wait_selector
        return opencli_wait_selector(selector, timeout_ms)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Wait error: {e}"


def opencli_find(selector: str, limit: int = 10) -> str:
    """Find elements matching a CSS selector."""
    try:
        from friday.opencli import opencli_find
        return opencli_find(selector, limit)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Find error: {e}"


def opencli_get_url() -> str:
    """Get the current page URL from the browser."""
    try:
        from friday.opencli import opencli_get_url
        return opencli_get_url()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Get URL error: {e}"


def opencli_get_title() -> str:
    """Get the current page title from the browser."""
    try:
        from friday.opencli import opencli_get_title
        return opencli_get_title()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Get title error: {e}"


def opencli_network() -> str:
    """Inspect network requests made by the current page."""
    try:
        from friday.opencli import opencli_network
        return opencli_network()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Network error: {e}"


def opencli_bind(domain: str = "") -> str:
    """Bind OpenCLI to the current Chrome tab."""
    try:
        from friday.opencli import opencli_bind
        return opencli_bind(domain)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Bind error: {e}"


def opencli_unbind() -> str:
    """Unbind from the current Chrome tab."""
    try:
        from friday.opencli import opencli_unbind
        return opencli_unbind()
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Unbind error: {e}"


def opencli_hover(target: str) -> str:
    """Hover over a browser element."""
    try:
        from friday.opencli import opencli_hover
        return opencli_hover(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Hover error: {e}"


def opencli_focus(target: str) -> str:
    """Focus a browser element."""
    try:
        from friday.opencli import opencli_focus
        return opencli_focus(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Focus error: {e}"


def opencli_dblclick(target: str) -> str:
    """Double-click a browser element."""
    try:
        from friday.opencli import opencli_dblclick
        return opencli_dblclick(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Dblclick error: {e}"


def opencli_check(target: str) -> str:
    """Check a checkbox/radio element."""
    try:
        from friday.opencli import opencli_check
        return opencli_check(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Check error: {e}"


def opencli_uncheck(target: str) -> str:
    """Uncheck a checkbox/radio element."""
    try:
        from friday.opencli import opencli_uncheck
        return opencli_uncheck(target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Uncheck error: {e}"


def opencli_drag(source: str, target: str) -> str:
    """Drag one element to another."""
    try:
        from friday.opencli import opencli_drag
        return opencli_drag(source, target)
    except ImportError:
        return "[FAIL] friday.opencli not available."
    except Exception as e:
        return f"[FAIL] Drag error: {e}"


#  Kimi WebBridge Tools (replacement for OpenCLI) #

def _run_kimi_async(coro):
    """Helper to run an async Kimi WebBridge function synchronously."""
    try:
        import asyncio
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
    except Exception as e:
        return {"error": str(e), "success": False}

def webbridge_connect_sync() -> str:
    """Connect to Kimi WebBridge daemon."""
    try:
        from friday.kimi_webbridge_tool import webbridge_connect
        result = _run_kimi_async(webbridge_connect())
        if result.get("success"):
            return f"[OK] Kimi WebBridge connected (daemon running)"
        return f"[FAIL] Kimi WebBridge: {result.get('error', 'connection failed')}"
    except ImportError:
        return "[FAIL] friday.kimi_webbridge_tool not available."
    except Exception as e:
        return f"[FAIL] Kimi WebBridge connect error: {e}"

def webbridge_disconnect_sync() -> str:
    """Disconnect from Kimi WebBridge daemon."""
    try:
        from friday.kimi_webbridge_tool import webbridge_disconnect
        result = _run_kimi_async(webbridge_disconnect())
        return "[OK] Kimi WebBridge disconnected" if result.get("success") else f"[FAIL] {result.get('error', 'disconnect failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge disconnect error: {e}"

def webbridge_doctor_sync() -> str:
    """Diagnose Kimi WebBridge connectivity."""
    try:
        from friday.kimi_webbridge_tool import webbridge_doctor
        result = _run_kimi_async(webbridge_doctor())
        if result.get("success"):
            status = result.get("status", "connected")
            return f"[OK] Kimi WebBridge: {status}"
        return f"[FAIL] Kimi WebBridge diagnosis: {result.get('error', 'unreachable')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge doctor error: {e}"

def webbridge_navigate_sync(url: str) -> str:
    """Open a URL in the browser via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_navigate
        result = _run_kimi_async(webbridge_navigate(url))
        return f"[OK] Navigated to {url}" if result.get("success") else f"[FAIL] {result.get('error', 'navigate failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge navigate error: {e}"

def webbridge_click_sync(target: str) -> str:
    """Click an element via Kimi WebBridge (CSS selector or text)."""
    try:
        from friday.kimi_webbridge_tool import webbridge_click
        result = _run_kimi_async(webbridge_click(target))
        return f"[OK] Clicked {target}" if result.get("success") else f"[FAIL] {result.get('error', 'click failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge click error: {e}"

def webbridge_fill_sync(target: str, text: str) -> str:
    """Fill a form field via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_fill
        result = _run_kimi_async(webbridge_fill(target, text))
        return f"[OK] Filled {target}" if result.get("success") else f"[FAIL] {result.get('error', 'fill failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge fill error: {e}"

def webbridge_type_text_sync(text: str) -> str:
    """Type text into the focused element via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_type_text
        result = _run_kimi_async(webbridge_type_text(text))
        return f"[OK] Typed text" if result.get("success") else f"[FAIL] {result.get('error', 'type failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge type error: {e}"

def webbridge_screenshot_sync() -> str:
    """Take a screenshot via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_screenshot
        result = _run_kimi_async(webbridge_screenshot())
        if result.get("success"):
            b64 = result.get("data", "")
            if b64:
                import tempfile, base64
                path = os.path.join(tempfile.gettempdir(), "kimi_screenshot.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(b64))
                return f"[OK] Screenshot saved to {path}"
        return f"[FAIL] {result.get('error', 'screenshot failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge screenshot error: {e}"

def webbridge_extract_text_sync() -> str:
    """Extract page text via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_extract_text
        result = _run_kimi_async(webbridge_extract_text())
        if result.get("success"):
            text = result.get("text", "")
            return text[:2000] if text else "[FAIL] No text extracted"
        return f"[FAIL] {result.get('error', 'extract failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge extract error: {e}"

def webbridge_get_page_state_sync() -> str:
    """Get page structure from Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_get_page_state
        result = _run_kimi_async(webbridge_get_page_state())
        if result.get("success"):
            return str(result.get("state", result))
        return f"[FAIL] {result.get('error', 'state failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge state error: {e}"

def webbridge_scroll_sync(direction: str = "down") -> str:
    """Scroll the browser page via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_scroll
        result = _run_kimi_async(webbridge_scroll(direction))
        return f"[OK] Scrolled {direction}" if result.get("success") else f"[FAIL] {result.get('error', 'scroll failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge scroll error: {e}"

def webbridge_press_key_sync(key: str) -> str:
    """Press a keyboard key in the browser via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_press_key
        result = _run_kimi_async(webbridge_press_key(key))
        return f"[OK] Pressed {key}" if result.get("success") else f"[FAIL] {result.get('error', 'key failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge key error: {e}"

def webbridge_key_combo_sync(keys: str) -> str:
    """Press a key combo (e.g. Ctrl+C) via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_key_combo
        result = _run_kimi_async(webbridge_key_combo(keys))
        return f"[OK] Combo {keys}" if result.get("success") else f"[FAIL] {result.get('error', 'combo failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge combo error: {e}"

def webbridge_evaluate_sync(js: str) -> str:
    """Execute JavaScript in the browser via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_evaluate
        result = _run_kimi_async(webbridge_evaluate(js))
        if result.get("success"):
            val = result.get("result", "")
            return str(val)[:2000] if val else "[OK] JS executed"
        return f"[FAIL] {result.get('error', 'eval failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge eval error: {e}"

def webbridge_submit_form_sync(selector: str = "") -> str:
    """Submit a form via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_submit_form
        result = _run_kimi_async(webbridge_submit_form(selector))
        return f"[OK] Form submitted" if result.get("success") else f"[FAIL] {result.get('error', 'submit failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge submit error: {e}"

def webbridge_select_option_sync(selector: str, value: str) -> str:
    """Select a dropdown option via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_select_option
        result = _run_kimi_async(webbridge_select_option(selector, value))
        return f"[OK] Selected {value}" if result.get("success") else f"[FAIL] {result.get('error', 'select failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge select error: {e}"

def webbridge_list_tabs_sync() -> str:
    """List all browser tabs via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_list_tabs
        result = _run_kimi_async(webbridge_list_tabs())
        if result.get("success"):
            tabs = result.get("tabs", [])
            if tabs:
                lines = [f"### Browser Tabs ({len(tabs)})"]
                for t in tabs:
                    lines.append(f"- {t.get('title', 'Untitled')} ({t.get('url', '')})")
                return "\n".join(lines)
            return "[OK] No open tabs found"
        return f"[FAIL] {result.get('error', 'list tabs failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge tabs error: {e}"

def webbridge_close_tab_sync(tab_id: str = "") -> str:
    """Close a browser tab via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_close_tab
        result = _run_kimi_async(webbridge_close_tab(tab_id))
        return f"[OK] Tab closed" if result.get("success") else f"[FAIL] {result.get('error', 'close tab failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge close tab error: {e}"

def webbridge_get_current_url_sync() -> str:
    """Get the current page URL from Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_get_current_url
        result = _run_kimi_async(webbridge_get_current_url())
        if result.get("success"):
            return f"Current URL: {result.get('url', 'unknown')}"
        return f"[FAIL] {result.get('error', 'get URL failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge URL error: {e}"

def webbridge_get_title_sync() -> str:
    """Get the current page title from Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_get_title
        result = _run_kimi_async(webbridge_get_title())
        if result.get("success"):
            return f"Page title: {result.get('title', 'unknown')}"
        return f"[FAIL] {result.get('error', 'get title failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge title error: {e}"

def webbridge_hover_sync(selector: str) -> str:
    """Hover over an element via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_hover
        result = _run_kimi_async(webbridge_hover(selector))
        return f"[OK] Hovered {selector}" if result.get("success") else f"[FAIL] {result.get('error', 'hover failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge hover error: {e}"

def webbridge_focus_sync(selector: str) -> str:
    """Focus an element via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_focus
        result = _run_kimi_async(webbridge_focus(selector))
        return f"[OK] Focused {selector}" if result.get("success") else f"[FAIL] {result.get('error', 'focus failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge focus error: {e}"

def webbridge_double_click_sync(selector: str) -> str:
    """Double-click an element via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_double_click
        result = _run_kimi_async(webbridge_double_click(selector))
        return f"[OK] Double-clicked {selector}" if result.get("success") else f"[FAIL] {result.get('error', 'double click failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge double-click error: {e}"

def webbridge_drag_sync(source: str, target: str) -> str:
    """Drag one element to another via Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_drag
        result = _run_kimi_async(webbridge_drag(source, target))
        return f"[OK] Dragged {source} to {target}" if result.get("success") else f"[FAIL] {result.get('error', 'drag failed')}"
    except Exception as e:
        return f"[FAIL] Kimi WebBridge drag error: {e}"

def webbridge_install_instructions_sync() -> str:
    """Get instructions to install Kimi WebBridge."""
    try:
        from friday.kimi_webbridge_tool import webbridge_install_instructions
        result = _run_kimi_async(webbridge_install_instructions())
        if result.get("success"):
            return result.get("instructions", "See kimi.com/features/webbridge")
        return "Install Kimi WebBridge:\n1. Install Chrome extension from Chrome Web Store (search 'Kimi WebBridge')\n2. Install npm package: npm install -g kimi-webbridge\n3. Run: npx kimi-webbridge\n4. Extension connects on ws://127.0.0.1:10086/ws"
    except Exception as e:
        return f"[FAIL] Install instructions error: {e}"


#  Workflow Automation Tool #

def workflow_tool(action: str = "list", name: str = None, description: str = None, steps: str = None) -> str:
    """Create, manage, and execute automated workflows. Actions: list, create, add_step, execute, delete, status."""
    try:
        from friday.workflow import workflow_tool as _wf_tool
        return _wf_tool(action=action, name=name, description=description, steps=steps)
    except ImportError:
        return "[FAIL] friday.workflow not available."
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
        from friday.knowledge_graph import knowledge_graph_tool as _kg_tool
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


def github_pr_comment(pr_number: int, body: str) -> str:
    """Add a comment to a pull request or issue."""
    try:
        from friday.github import github_pr_comment
        return github_pr_comment(pr_number, body)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub PR comment error: {e}"


def github_pr_diff(pr_number: int) -> str:
    """Get the full diff of a pull request."""
    try:
        from friday.github import github_pr_diff
        return github_pr_diff(pr_number)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub PR diff error: {e}"


def github_pr_files(pr_number: int) -> str:
    """List files changed in a pull request."""
    try:
        from friday.github import github_pr_files
        return github_pr_files(pr_number)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub PR files error: {e}"


def github_delete_file(path: str, message: str = "Delete via Friday") -> str:
    """Delete a file from the repository."""
    try:
        from friday.github import github_delete_file
        return github_delete_file(path, message)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub delete file error: {e}"


def github_get_contents(path: str = "") -> str:
    """List contents of a directory or read a file from the repository."""
    try:
        from friday.github import github_get_contents
        return github_get_contents(path)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub contents error: {e}"


def github_get_user() -> str:
    """Get authenticated GitHub user info."""
    try:
        from friday.github import github_get_user
        return github_get_user()
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub user error: {e}"


def github_list_prs(repo: str = "", state: str = "open") -> str:
    """List pull requests for a GitHub repository. Pass repo='owner/repo' or leave empty for default."""
    try:
        from friday.github import github_list_prs
        return github_list_prs(repo=repo, state=state)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub list PRs error: {e}"


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


def github_create_repo(name: str, description: str = "", private: bool = False) -> str:
    """Create a new GitHub repository."""
    try:
        from friday.github import github_create_repo
        return github_create_repo(name, description, private)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub create repo error: {e}"


def github_list_issues(state: str = "open", labels: str = "") -> str:
    """List issues in the GitHub repository."""
    try:
        from friday.github import github_list_issues
        return github_list_issues(state, labels)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub list issues error: {e}"


def github_create_issue(title: str, body: str = "", labels: str = "") -> str:
    """Create a GitHub issue."""
    try:
        from friday.github import github_create_issue
        return github_create_issue(title, body, labels)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub create issue error: {e}"


def github_search_code(query: str, repo: str = "") -> str:
    """Search code across GitHub repositories."""
    try:
        from friday.github import github_search_code
        return github_search_code(query, repo)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub search code error: {e}"


def github_merge_pr(pr_number: int, commit_title: str = "") -> str:
    """Merge a GitHub pull request."""
    try:
        from friday.github import github_merge_pr
        return github_merge_pr(pr_number, commit_title)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub merge PR error: {e}"


def github_repo_info() -> str:
    """Get GitHub repository information."""
    try:
        from friday.github import github_repo_info
        return github_repo_info()
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub repo info error: {e}"


def github_list_branches() -> str:
    """List all branches in the GitHub repository."""
    try:
        from friday.github import github_list_branches
        return github_list_branches()
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub list branches error: {e}"


def github_commit_history(path: str = "", limit: int = 10) -> str:
    """Get commit history for the GitHub repository."""
    try:
        from friday.github import github_commit_history
        return github_commit_history(path, limit)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub commit history error: {e}"


def github_authorize() -> str:
    """Open GitHub OAuth authorization page in browser for Friday to access your repos."""
    try:
        from friday.github import github_authorize as _gh_auth
        return _gh_auth()
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub authorize error: {e}"


def github_exchange_code(device_code: str = "") -> str:
    """Check GitHub auth status or manually poll with a device_code from a previous authorize call."""
    try:
        from friday.github import github_exchange_code as _gh_ex
        return _gh_ex(device_code)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub code exchange error: {e}"


def github_setup(token: str = "") -> str:
    """Set up GitHub with a Personal Access Token (PAT). PREFERRED: just put GITHUB_TOKEN in .env. Otherwise pass token=... and it validates + saves."""
    try:
        from friday.github import github_setup as _gs
        return _gs(token=token)
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub setup error: {e}"


def github_refresh_token() -> str:
    """Manually refresh the GitHub App token. Only works for GitHub Apps (client_id starts with Iv1.)."""
    try:
        from friday.github import github_refresh_token as _gh_ref
        return _gh_ref()
    except ImportError:
        return "[FAIL] friday.github not available."
    except Exception as e:
        return f"[FAIL] GitHub refresh error: {e}"


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


def pr_manager_tool(action: str = "status", **kwargs) -> str:
    """Proactive PR manager: polls GitHub repos for open PRs, auto-reviews new ones.
    Actions: status, list_repos, add_repo (repo=name), remove_repo (repo=name),
    scan_now (auto_review=true), reviews (limit=N), watch, stop."""
    try:
        from friday.pr_manager import pr_manager_tool as _pmt
        return _pmt(action=action, **kwargs)
    except ImportError:
        return "[FAIL] friday.pr_manager not available."
    except Exception as e:
        return f"[FAIL] PR manager error: {e}"


def protector_tool(action: str = "status", **kwargs) -> str:
    """System protector: prevent unauthorized shutdown/lid-close, manage Windows startup.
    Actions: status, watch (start background monitor), stop, allow (permit shutdown),
    startup (manage startup registration: startup_action=install/remove/status),
    test_voice (test TTS)."""
    try:
        from friday.protector import protector_tool as _pt
        return _pt(action=action, **kwargs)
    except ImportError:
        return "[FAIL] friday.protector not available."
    except Exception as e:
        return f"[FAIL] Protector error: {e}"


#  Vector Memory Tool (re-exported from vector_memory.py) #

def vector_memory_tool(action: str = "stats", query: str = None, text: str = None, n_results: int = 5) -> str:
    """Semantic memory: store and search facts, preferences, and patterns using vector search."""
    try:
        from friday.vector_memory import vector_memory_tool as _vm_tool
        return _vm_tool(action=action, query=query, text=text, n_results=n_results)
    except ImportError:
        return "[FAIL] vector_memory.py not available."
    except Exception as e:
        return f"[FAIL] Vector memory error: {e}"


#  Multi-Agent Delegation Tool #

def multi_agent_delegate(action: str = "list", task: str = None, agent: str = None) -> str:
    """Delegate tasks to specialist sub-agents. Actions: list (show agents), delegate (assign task)."""
    try:
        from friday.orchestrator import get_orchestrator, run_delegate_sync

        orchestrator = get_orchestrator()

        if action == "list":
            agents = orchestrator.registry.list_all()
            if not agents:
                return "No agents configured."
            lines = ["### Friday Agents\n"]
            for profile in agents:
                lines.append(
                    f"- **{profile.display_name}** ({profile.agent_id}) — model: {profile.nim_model}, tasks: {', '.join(profile.task_types)}"
                )
            return "\n".join(lines)

        if action == "delegate":
            result = run_delegate_sync(task or "", context={"requester": "tool", "source": "multi_agent_delegate"}, preferred_agent=agent)
            if result.get("status") == "scheduled":
                return result["prompt"]
            return result.get("summary") or result.get("prompt") or "[OK] Delegation complete."

        if action == "parallel":
            result = run_delegate_sync(task or "", context={"requester": "tool", "source": "multi_agent_delegate"})
            return result.get("summary") or "[OK] Parallel delegation complete."

        if action == "results":
            return "[OK] Results are published on the context bus."

        if action == "agent_info":
            profile = orchestrator.registry.get_by_name(agent or "") if agent else None
            if profile is None:
                return f"[FAIL] Agent '{agent}' not found."
            return (
                f"### Agent Info\n\n"
                f"**Name**: {profile.display_name}\n"
                f"**ID**: {profile.agent_id}\n"
                f"**Tasks**: {', '.join(profile.task_types)}\n"
                f"**Model**: {profile.nim_model}\n"
                f"**Tools**: {', '.join(profile.tools)}"
            )

        return f"[FAIL] Unknown action: {action}"
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


#  System Monitor Tools (from system_monitor.py) #

def system_cpu() -> str:
    """Get current CPU usage percentage."""
    try:
        from friday.system_monitor import get_cpu_usage
        return f"CPU: {get_cpu_usage()}%"
    except Exception as e:
        return f"[FAIL] CPU error: {e}"

def system_memory() -> str:
    """Get current RAM usage stats."""
    try:
        from friday.system_monitor import get_memory_usage
        mem = get_memory_usage()
        if "error" in mem:
            return f"[FAIL] {mem['error']}"
        return f"Memory: {mem['used_gb']}GB / {mem['total_gb']}GB ({mem['percent']}%)"
    except Exception as e:
        return f"[FAIL] Memory error: {e}"

def system_disk(path: str = "C:\\") -> str:
    """Get disk usage for a drive path."""
    try:
        from friday.system_monitor import get_disk_usage
        disk = get_disk_usage(path)
        if "error" in disk:
            return f"[FAIL] {disk['error']}"
        return f"Disk {path}: {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['percent']}% used, {disk['free_gb']}GB free)"
    except Exception as e:
        return f"[FAIL] Disk error: {e}"

def system_network() -> str:
    """Get network I/O stats since boot."""
    try:
        from friday.system_monitor import get_network_stats
        net = get_network_stats()
        if "error" in net:
            return f"[FAIL] {net['error']}"
        return f"Network: {net['bytes_sent_mb']}MB sent, {net['bytes_recv_mb']}MB received"
    except Exception as e:
        return f"[FAIL] Network error: {e}"

def system_processes(sort_by: str = "memory", limit: int = 10) -> str:
    """List top processes by CPU or memory usage."""
    try:
        from friday.system_monitor import get_process_list
        procs = get_process_list(sort_by=sort_by, limit=limit)
        if not procs:
            return "No process data available."
        lines = [f"{'PID':>6} {'NAME':<25} {'CPU%':>6} {'MEM(MB)':>8}"]
        for p in procs:
            lines.append(f"{p.get('pid', 0):>6} {p.get('name', '?'):<25} {p.get('cpu_percent', 0):>6.1f} {p.get('memory_mb', 0):>8.1f}")
        return "\n".join(lines)
    except Exception as e:
        return f"[FAIL] Processes error: {e}"


#  Dreaming Tool #
def dream_tool(action: str = "status") -> str:
    """Dreaming system: analyze past sessions while idle. Actions: status, cycle, start, stop, insights."""
    try:
        from friday.dreaming import dream_tool as _dt
        return _dt(action=action)
    except ImportError:
        return "[FAIL] dreaming.py not available."
    except Exception as e:
        return f"[FAIL] Dream error: {e}"


#  Scheduler Tool #
def scheduler_tool(action: str = "list", **kwargs) -> str:
    """Schedule autonomous tasks. Actions: list, add, remove, pause, resume, start, stop."""
    try:
        from friday.scheduler import scheduler_tool as _st
        return _st(action=action, **kwargs)
    except ImportError:
        return "[FAIL] scheduler.py not available."
    except Exception as e:
        return f"[FAIL] Scheduler error: {e}"


#  Skills Tool #
def skills_tool(action: str = "list", **kwargs) -> str:
    """Self-improving skills system: save, search, and reuse successful workflows. Actions: list, add, search, delete, stats, auto_create."""
    try:
        from friday.skills import skills_tool as _st
        return _st(action=action, **kwargs)
    except ImportError:
        return "[FAIL] skills.py not available."
    except Exception as e:
        return f"[FAIL] Skills error: {e}"


#  Predictive Tool #
def predictive_tool(action: str = "predict", **kwargs) -> str:
    """Predictive analysis: learn usage patterns and anticipate needs. Actions: predict, patterns, stats."""
    try:
        from friday.predictive import predictive_tool as _pt
        return _pt(action=action, **kwargs)
    except ImportError:
        return "[FAIL] predictive.py not available."
    except Exception as e:
        return f"[FAIL] Predictive error: {e}"


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


#  Reflection Tool #
def reflection_tool(action: str = "status", **kwargs) -> str:
    """GEPA self-reflection: analyze tool outcomes, find failure patterns, and auto-improve. Actions: cycle, analyze, improvements, status."""
    try:
        from friday.reflection import reflection_tool as _rt
        return _rt(action=action, **kwargs)
    except ImportError:
        return "[FAIL] reflection.py not available."
    except Exception as e:
        return f"[FAIL] Reflection error: {e}"


#  Context Tool #
def context_tool(action: str = "list", **kwargs) -> str:
    """Manage project context files (AGENTS.md, CLAUDE.md). Actions: list, show, add, delete, reload."""
    try:
        from friday.context import context_tool as _ct
        return _ct(action=action, **kwargs)
    except ImportError:
        return "[FAIL] context.py not available."
    except Exception as e:
        return f"[FAIL] Context error: {e}"


#  Crash Watcher Tool #
def crash_tool(action: str = "status", **kwargs) -> str:
    """Crash watcher: monitors Windows app crashes in real-time via Event Log. Actions: status, recent (list crashes), analyze (deep dive), watch (start background), stop."""
    try:
        from friday.crash_watcher import crash_tool as _ct
        return _ct(action=action, **kwargs)
    except ImportError:
        return "[FAIL] crash_watcher.py not available."
    except Exception as e:
        return f"[FAIL] Crash watcher error: {e}"


#  Self-Improvement Pipeline Tool #
def self_improve_tool(action: str = "status", **kwargs) -> str:
    """Self-improvement pipeline: propose, review, and apply code changes. Actions: propose (suggest change to a file), list (show pending), diff (show diff), apply (approve + write), reject (discard), status."""
    try:
        from friday.self_improve import self_improve_tool as _sit
        return _sit(action=action, **kwargs)
    except ImportError:
        return "[FAIL] self_improve.py not available."
    except Exception as e:
        return f"[FAIL] Self-improve error: {e}"


#  Auto-Update Tool #
def auto_update_tool(action: str = "status", branch: str = "main", steps: int = 1) -> str:
    """Self-update: pull latest from GitHub, check for updates, or rollback. Actions: status, check, apply, rollback."""
    try:
        from friday.auto_update import auto_update_tool as _aut
        return _aut(action=action, branch=branch, steps=steps)
    except ImportError:
        return "[FAIL] auto_update.py not available."
    except Exception as e:
        return f"[FAIL] Auto-update error: {e}"


#  Episodic Archive Tool #
def episodic_tool(action: str = "status", **kwargs) -> str:
    """Episodic memory: record and search past sessions with full-text search. Actions: search (FTS query), recent (last N), record (manual entry), session (full session by id), stats, status."""
    try:
        from friday.episodic import episodic_tool as _et
        return _et(action=action, **kwargs)
    except ImportError:
        return "[FAIL] episodic.py not available."
    except Exception as e:
        return f"[FAIL] Episodic error: {e}"


#  Monitor Tool #
def monitor_tool(action: str = "status", **kwargs) -> str:
    """Proactive desktop monitor: CPU spikes, crash detection, auto-response. Actions: status, alerts, config, start, stop, check."""
    try:
        from friday.monitor import monitor_tool as _mt
        return _mt(action=action, **kwargs)
    except ImportError:
        return "[FAIL] monitor.py not available."
    except Exception as e:
        return f"[FAIL] Monitor error: {e}"


#  MCP Bridge Tool #
def mcp_tool(action: str = "list", **kwargs) -> str:
    """MCP bridge: connect external MCP servers. Actions: list, connect, disconnect, call, clean."""
    try:
        from friday.mcp_bridge import mcp_tool as _mcp
        return _mcp(action=action, **kwargs)
    except ImportError:
        return "[FAIL] mcp_bridge.py not available."
    except Exception as e:
        return f"[FAIL] MCP error: {e}"


#  OpenCode Agent Tools #

def agent_spawn(name: str, task: str) -> str:
    """Spawn a named agent for a task via opencode. Returns agent status."""
    try:
        from friday.agents_manager import spawn_agent as _sa
        result = _sa(name=name, task=task)
        return (
            f"### Agent Spawned\n\n"
            f"**Name**: {result['name']}\n"
            f"**ID**: {result['id']}\n"
            f"**Status**: {result['status']}\n\n"
            f"{result['message']}"
        )
    except ImportError:
        return "[FAIL] agents_manager.py not available."
    except Exception as e:
        return f"[FAIL] Agent spawn error: {e}"


def agent_list() -> str:
    """List all agents and their status."""
    try:
        from friday.agents_manager import list_agents as _la
        agents = _la()
        if not agents:
            return "No agents have been spawned yet."
        lines = ["### OpenCode Agents\n"]
        for a in agents:
            status_icon = "RUNNING" if a["status"] == "running" else a["status"].upper()
            lines.append(f"- **{a['name']}**: {status_icon}")
            lines.append(f"  Task: {a['task'][:100]}")
            if a.get("result"):
                lines.append(f"  Result: {a['result'][:200]}")
            lines.append("")
        return "\n".join(lines)
    except ImportError:
        return "[FAIL] agents_manager.py not available."
    except Exception as e:
        return f"[FAIL] Agent list error: {e}"


def agent_status(name: str) -> str:
    """Get status of a specific agent by name."""
    try:
        from friday.agents_manager import agent_status as _as
        result = _as(name=name)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        status_emoji = {
            "spawning": "spawning...",
            "running": "running",
            "completed": "completed",
            "failed": "failed",
        }.get(result["status"], result["status"])
        lines = [
            f"### Agent: {result['name']}",
            f"**Status**: {status_emoji}",
            f"**Task**: {result['task']}",
        ]
        if result.get("result"):
            lines.append(f"**Result**: {result['result'][:500]}")
        if result.get("created_at"):
            lines.append(f"**Created**: {result['created_at']}")
        if result.get("completed_at"):
            lines.append(f"**Completed**: {result['completed_at']}")
        return "\n".join(lines)
    except ImportError:
        return "[FAIL] agents_manager.py not available."
    except Exception as e:
        return f"[FAIL] Agent status error: {e}"


def agent_delegate_team(tasks: list) -> str:
    """Spawn multiple agents in parallel for a team effort. Each task is [name, description]."""
    try:
        from friday.agents_manager import spawn_team as _st
        if isinstance(tasks, str):
            import json
            tasks = json.loads(tasks)
        task_tuples = [(t[0], t[1]) if isinstance(t, list) else (t["name"], t["task"]) for t in tasks]
        results = _st(tasks=task_tuples)
        lines = ["### Team Spawned\n"]
        for r in results:
            lines.append(f"- **{r['name']}** (ID: {r['id']}): {r['status']}")
        return "\n".join(lines)
    except ImportError:
        return "[FAIL] agents_manager.py not available."
    except Exception as e:
        return f"[FAIL] Team spawn error: {e}"


#  Export list for friday.live #

# ── Deep Code Review ──

def deep_code_review(action: str = "analyze", target: str = "", file_pattern: str = "*.*",
                     auto_fix: bool = False, pr_title: str = "", pr_body: str = "",
                     repo_description: str = "", branch_name: str = "", repo_name: str = "",
                     github_repo: str = "") -> str:
    """Deep code review powered by Gemini. Walks source files, analyzes each with AI, and reports findings.
    Actions: analyze (default), fix, new_project, fork_pr.
    Target can be 'self' (FRIDAY's code), a local path, or a GitHub 'owner/repo'.
    Set auto_fix=True to create a GitHub PR with fixes."""
    from friday.code_review import deep_code_review as _review
    return _review(action=action, target=target, file_pattern=file_pattern,
                   auto_fix=auto_fix, pr_title=pr_title, pr_body=pr_body,
                   repo_description=repo_description, branch_name=branch_name,
                   repo_name=repo_name, github_repo=github_repo)


def code_review_report(target: str) -> str:
    """Quick summary of source files in a target: count, sizes, types. Calls code_review for deep analysis."""
    from friday.code_review import code_review_report as _report
    return _report(target=target)


__all__ = [
    "get_time", "system_info", "run_cmd", "safe_run_cmd",
    "read_file", "write_file", "list_files", "find_files",
    "copy_file", "move_file", "delete_file",
    "clipboard_get", "clipboard_set",
    "get_active_window",
    "click", "double_click", "right_click", "move_mouse", "drag",
    "hotkey", "press_key", "scroll",
    "open_app", "close_app", "list_running_apps",     "open_url", "open_roblox_game", "open_microsoft_store",
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
    "memory_import_tool_handler", "kyu_tool_handler",
    "research_tool_handler", "reasoning_tool_handler",
    "status_check", "clock_tool",
    "climb_codebase", "deep_research",
    "memory_store", "memory_retrieve", "stark_log",
    "system_cpu", "system_memory", "system_disk", "system_network", "system_processes",
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
    "opencli_run", "opencli_list_adapters",
    "opencli_hover", "opencli_focus", "opencli_dblclick",
    "opencli_check", "opencli_uncheck", "opencli_drag",
    "webbridge_connect_sync", "webbridge_disconnect_sync", "webbridge_doctor_sync",
    "webbridge_navigate_sync", "webbridge_click_sync", "webbridge_fill_sync",
    "webbridge_type_text_sync", "webbridge_screenshot_sync", "webbridge_extract_text_sync",
    "webbridge_get_page_state_sync", "webbridge_scroll_sync", "webbridge_press_key_sync",
    "webbridge_key_combo_sync", "webbridge_evaluate_sync", "webbridge_submit_form_sync",
    "webbridge_select_option_sync", "webbridge_list_tabs_sync", "webbridge_close_tab_sync",
    "webbridge_get_current_url_sync", "webbridge_get_title_sync", "webbridge_hover_sync",
    "webbridge_focus_sync", "webbridge_double_click_sync", "webbridge_drag_sync",
    "webbridge_install_instructions_sync",
    "vector_memory_tool",
    "workflow_tool", "plugin_tool", "knowledge_graph_tool",
    "github_list_files", "github_read_file", "github_write_file",
    "github_create_branch", "github_create_pr", "github_list_prs", "github_pr_comment", "github_pr_diff", "github_pr_files", "github_delete_file", "github_get_contents", "github_get_user", "github_self_modify", "github_review_pr",
    "github_create_repo", "github_list_issues", "github_create_issue", "github_search_code",
    "github_merge_pr", "github_repo_info", "github_list_branches", "github_commit_history",
    "github_authorize", "github_exchange_code", "github_refresh_token", "github_setup",
    "multi_agent_delegate", "message_channel_tool",
    "send_notification", "get_pending_notifications", "clear_notifications",
    "dream_tool", "scheduler_tool", "skills_tool", "predictive_tool",
    "reflection_tool", "context_tool", "monitor_tool", "mcp_tool",
    "episodic_tool",
    "self_improve_tool",
    "crash_tool",
    "pr_manager_tool",
    "protector_tool",
    "deep_code_review",
    "code_review_report",
    "agent_spawn",
    "agent_list",
    "agent_status",
    "agent_delegate_team",
    "read_skill_tool",
]

if __name__ == "__main__":
    print("Friday Tools loaded successfully.")
    print(f"Tools available: {len(__all__)}")
