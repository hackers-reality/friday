"""
Friday Screen Watcher - Phase 2.1 & 2.2
Active window detection + continuous screen capture in background thread.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import json
import io
from typing import Optional, Callable, Dict, Any

from PIL import ImageGrab

# Try to import window detection libraries
try:
    import pywinctl as pwc
    PYWINCTL_AVAILABLE = True
except Exception as e:
    print(f"[ScreenWatcher] pywinctl not available: {e}")
    PYWINCTL_AVAILABLE = False

try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = sys.platform == "win32"
except Exception:
    CTYPES_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False


# ─── Active Window Detection ────────────────────────────────────────────

def get_active_window_info() -> Dict[str, Any]:
    """
    Get active window title, process name, and PID.
    Uses pywinctl (cross-platform) with ctypes fallback on Windows.
    """
    result = {
        "title": "Unknown",
        "process_name": "Unknown",
        "pid": None,
        "is_active": False,
    }
    
    if PYWINCTL_AVAILABLE:
        try:
            active = pwc.getActiveWindow()
            if active:
                result["title"] = active.title or "Unknown"
                result["is_active"] = getattr(active, 'is_active', False)
                # Try to get PID
                if hasattr(active, 'pid') and active.pid:
                    result["pid"] = active.pid
                    if PSUTIL_AVAILABLE:
                        try:
                            p = psutil.Process(active.pid)
                            result["process_name"] = p.name()
                        except Exception:
                            pass
                return result
        except Exception as e:
            print(f"[ScreenWatcher] pywinctl error: {e}")
    
    # Windows fallback using ctypes
    if CTYPES_AVAILABLE:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                result["title"] = buf.value or "Unknown"
                result["is_active"] = True
                
                # Get PID
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    result["pid"] = pid.value
                    if PSUTIL_AVAILABLE:
                        try:
                            p = psutil.Process(pid.value)
                            result["process_name"] = p.name()
                        except Exception:
                            pass
                return result
        except Exception as e:
            print(f"[ScreenWatcher] ctypes error: {e}")
    
    return result


def get_all_windows() -> list[Dict[str, Any]]:
    """Get all visible windows."""
    windows = []
    if PYWINCTL_AVAILABLE:
        try:
            for win in pwc.getAllWindows():
                windows.append({
                    "title": win.title or "Unknown",
                    "pid": getattr(win, 'pid', None),
                    "is_active": getattr(win, 'is_active', False),
                })
        except Exception as e:
            print(f"[ScreenWatcher] getAllWindows error: {e}")
    return windows


# ─── Screen Capture ──────────────────────────────────────────────────────

def capture_screen(resize_to=(960, 540), quality=50) -> Optional[bytes]:
    """Capture the screen and return JPEG bytes."""
    try:
        screen = ImageGrab.grab()
        if resize_to:
            screen = screen.resize(resize_to)
        buffer = io.BytesIO()
        screen.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()
    except Exception as e:
        print(f"[ScreenWatcher] Screen capture error: {e}")
        return None


def capture_active_window() -> Optional[bytes]:
    """Capture only the active window if possible."""
    if not PYWINCTL_AVAILABLE:
        return capture_screen()
    
    try:
        active = pwc.getActiveWindow()
        if active and hasattr(active, 'left'):
            # Use pywinctl to get window bounds
            region = (active.left, active.top, active.right, active.bottom)
            screen = ImageGrab.grab(bbox=region)
            buffer = io.BytesIO()
            screen.save(buffer, format="JPEG", quality=70)
            return buffer.getvalue()
    except Exception as e:
        print(f"[ScreenWatcher] Window capture error: {e}")
    
    return capture_screen()


# ─── Continuous Screen Watcher ──────────────────────────────────────────

class ScreenWatcher:
    """
    Background thread that continuously watches the screen and active window.
    Can trigger callbacks when the active window changes or periodically.
    """
    
    def __init__(
        self,
        on_window_change: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_screenshot: Optional[Callable[[bytes], None]] = None,
        screenshot_interval: float = 3.0,
        window_check_interval: float = 1.0,
    ):
        self.on_window_change = on_window_change
        self.on_screenshot = on_screenshot
        self.screenshot_interval = screenshot_interval
        self.window_check_interval = window_check_interval
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_window_title = ""
        self._last_screenshot_time = 0.0
        
        # State file for persisting current window
        self.state_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sovereign_state.json"
        )
    
    def _update_state(self, window_info: Dict[str, Any]):
        """Update the state file with current window info."""
        try:
            state = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            
            state["active_window"] = window_info.get("title", "Unknown")
            state["active_process"] = window_info.get("process_name", "Unknown")
            state["active_pid"] = window_info.get("pid")
            state["last_update"] = time.time()
            
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"[ScreenWatcher] State update error: {e}")
    
    def _run(self):
        """Main watcher loop."""
        while not self._stop_event.is_set():
            try:
                # Check active window
                window_info = get_active_window_info()
                current_title = window_info.get("title", "")
                
                if current_title != self._last_window_title:
                    self._last_window_title = current_title
                    self._update_state(window_info)
                    if self.on_window_change:
                        try:
                            self.on_window_change(window_info)
                        except Exception as e:
                            print(f"[ScreenWatcher] Callback error: {e}")
                
                # Periodic screenshot
                now = time.time()
                if now - self._last_screenshot_time >= self.screenshot_interval:
                    self._last_screenshot_time = now
                    screenshot = capture_screen()
                    if screenshot and self.on_screenshot:
                        try:
                            self.on_screenshot(screenshot)
                        except Exception as e:
                            print(f"[ScreenWatcher] Screenshot callback error: {e}")
                
            except Exception as e:
                print(f"[ScreenWatcher] Loop error: {e}")
            
            # Sleep in small increments to allow stop
            for _ in range(int(self.window_check_interval * 10)):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
    
    def start(self):
        """Start the watcher thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[ScreenWatcher] Started.")
    
    def stop(self):
        """Stop the watcher thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[ScreenWatcher] Stopped.")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current window state."""
        return get_active_window_info()


# ─── Singleton Watcher ──────────────────────────────────────────────────

_watcher_instance: Optional[ScreenWatcher] = None
_watcher_lock = threading.Lock()

def get_watcher(
    on_window_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_screenshot: Optional[Callable[[bytes], None]] = None,
) -> ScreenWatcher:
    """Get or create the singleton watcher."""
    global _watcher_instance
    with _watcher_lock:
        if _watcher_instance is None:
            _watcher_instance = ScreenWatcher(
                on_window_change=on_window_change,
                on_screenshot=on_screenshot,
            )
        else:
            if on_window_change:
                _watcher_instance.on_window_change = on_window_change
            if on_screenshot:
                _watcher_instance.on_screenshot = on_screenshot
        return _watcher_instance


# ─── Integration with Friday Tools ─────────────────────────────────────

def enhanced_situational_awareness() -> str:
    """Enhanced version of situatial_awareness with process info."""
    try:
        info = get_active_window_info()
        cwd = os.getcwd()
        lines = [
            "### SITUATIONAL REPORT",
            f"- Active Window: {info['title']}",
            f"- Process: {info['process_name']}",
            f"- PID: {info['pid'] or 'N/A'}",
            f"- CWD: {cwd}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Sensors failing: {e}"


if __name__ == "__main__":
    # Test
    print("Testing ScreenWatcher...")
    
    def on_window_change(info):
        print(f"[Callback] Window changed: {info['title']}")
    
    def on_screenshot(data):
        print(f"[Callback] Screenshot captured: {len(data)} bytes")
    
    watcher = get_watcher(
        on_window_change=on_window_change,
        on_screenshot=on_screenshot,
    )
    watcher.screenshot_interval = 5.0
    watcher.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
