"""
FRIDAY Desktop-Use Bridge — native Windows app control via UI Automation.
Parallel to browser_use_bridge.py but for desktop apps (Notepad, Discord, Chrome, etc).

Uses pywinauto (MS UI Automation backend) for element discovery and interaction.
All operations are synchronous (no async needed).
"""
from __future__ import annotations

import json
import os
import base64
import time
from datetime import datetime
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_DESKTOP_AVAILABLE = False

try:
    import pywinauto
    _DESKTOP_AVAILABLE = True
except ImportError:
    pass

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "desktop_use_state.json")
_HISTORY_PATH = os.path.join(FRIDAY_MEMORY, "desktop_use_history.jsonl")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": 0, "total_actions": 0, "last_window": ""}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _log_history(entry: dict) -> None:
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    with open(_HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _ensure_com():
    """Initialize COM on this thread for UI Automation."""
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass


def _get_windows():
    """Return list of all desktop windows, retrying with win32 backend if UIA crashes."""
    from pywinauto import Desktop
    last_err = None
    for backend in ("uia", "win32"):
        for attempt in range(2):
            try:
                import gc; gc.collect()
                if backend == "uia":
                    _ensure_com()
                d = Desktop(backend=backend)
                return d.windows()
            except Exception as e:
                last_err = e
                logger.warning("_get_windows(%s) attempt %d failed: %s", backend, attempt + 1, e)
                time.sleep(1)
    raise last_err or RuntimeError("Failed to list desktop windows")


def _get_desktop():
    from pywinauto import Desktop
    last_err = None
    for backend in ("uia", "win32"):
        for attempt in range(2):
            try:
                if backend == "uia":
                    _ensure_com()
                return Desktop(backend=backend)
            except Exception as e:
                last_err = e
                logger.warning("Desktop init %s attempt %d failed: %s", backend, attempt + 1, e)
                time.sleep(1)
    raise last_err or RuntimeError("Failed to initialize Desktop")


def desktop_use_status() -> str:
    if not _DESKTOP_AVAILABLE:
        return "Desktop control not available. Install: pip install pywinauto"
    state = _load_state()
    return json.dumps({
        "available": True,
        "backend": "uia",
        "sessions": state["sessions"],
        "total_actions": state["total_actions"],
        "last_window": state["last_window"],
    }, indent=2)


def desktop_list_windows() -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    last_error = "unknown error"
    try:
        wins = _get_windows()
        results = []
        for w in wins:
            try:
                title = w.window_text()
                if title.strip():
                    results.append({
                        "title": title,
                        "class_name": w.class_name(),
                        "handle": str(w.handle),
                    })
            except Exception:
                continue
        results.sort(key=lambda x: x["title"].lower())
        return json.dumps({"windows": results[:50], "count": len(results)}, indent=2)
    except Exception as e:
        last_error = str(e)
        logger.exception("list_windows failed")
    return json.dumps({"error": last_error})


_SKIP_WINDOWS = {"Taskbar", "ToolBarHiddenWindow", "Program Manager", "Shell_TrayWnd",
                 "Windows.UI.Core.CoreWindow", "Windows.UI.Composition.DesktopWindowContentBridge"}


def desktop_get_active_window() -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    for attempt in range(2):
        try:
            import gc; gc.collect()
            wins = _get_windows()
            for w in wins:
                try:
                    txt = w.window_text().strip()
                    if txt and txt not in _SKIP_WINDOWS:
                        return json.dumps({"active_window": txt, "class": w.class_name()}, indent=2)
                except Exception:
                    continue
            return json.dumps({"active_window": "(no window found)"}, indent=2)
        except Exception as e:
            if attempt == 0:
                logger.warning("get_active_window attempt %d failed, retrying: %s", attempt + 1, e)
                time.sleep(1)
                continue
            return json.dumps({"error": str(e)})


def desktop_focus_window(title: str) -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    for attempt in range(3):
        try:
            import gc; gc.collect()
            win = _find_window(title)
            if not win:
                return json.dumps({"error": f"Window '{title}' not found"})
            win.set_focus()
            time.sleep(0.3)
            state = _load_state()
            state["last_window"] = win.window_text()
            state["total_actions"] += 1
            _save_state(state)
            _log_history({
                "timestamp": datetime.now().isoformat(),
                "type": "focus", "window": win.window_text(),
            })
            return json.dumps({"success": True, "window": win.window_text()}, indent=2)
        except Exception as e:
            if attempt < 2:
                logger.warning("focus_window attempt %d failed, retrying: %s", attempt + 1, e)
                time.sleep(1 + attempt)
                continue
            return json.dumps({"error": str(e)})


def desktop_launch_app(path: str) -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        from pywinauto import Application
        app = Application(backend="uia").start(path, timeout=15)
        title = app.top_window().window_text()
        state = _load_state()
        state["total_actions"] += 1
        state["last_window"] = title
        _save_state(state)
        return json.dumps({"success": True, "launched": path, "window": title}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_click(text: str = "", auto_id: str = "", class_name: str = "", title: str = "") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        if not any([text, auto_id, class_name, title]):
            return json.dumps({"error": "Provide text, auto_id, class_name, or title to click"})

        if title:
            win = _find_window(title)
            if not win:
                return json.dumps({"error": f"Window '{title}' not found"})
            return json.dumps({"success": True, "action": "focused", "window": win.window_text()}, indent=2)

        # Click element anywhere on desktop
        desktop = _get_desktop()
        criteria = {}
        if text:
            criteria["title"] = text
        if auto_id:
            criteria["auto_id"] = auto_id
        if class_name:
            criteria["class_name"] = class_name

        elem = desktop.window(**criteria)
        elem.click_input()
        time.sleep(0.3)
        state = _load_state()
        state["total_actions"] += 1
        _save_state(state)
        return json.dumps({"success": True, "criteria": criteria}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _find_window(title_containing: str):
    """Find first window whose title contains the given string."""
    for attempt in range(3):
        try:
            import gc; gc.collect()
            wins = _get_windows()
            for w in wins:
                try:
                    if title_containing.lower() in w.window_text().lower():
                        return w
                except Exception:
                    continue
            return None
        except Exception as e:
            if attempt < 2:
                logger.warning("_find_window attempt %d failed, retrying: %s", attempt + 1, e)
                time.sleep(1 + attempt)
                continue
            raise


def desktop_type_text(text: str, window_title: str = "", auto_id: str = "") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        if window_title:
            win = _find_window(window_title)
            if not win:
                return json.dumps({"error": f"Window containing '{window_title}' not found"})
        else:
            wins = _get_windows()
            win = next((w for w in wins if "Notepad" in w.class_name()), wins[0] if wins else None)
            if not win:
                return json.dumps({"error": "No windows found"})

        win.click_input()
        time.sleep(0.2)
        from pywinauto.keyboard import send_keys
        send_keys(text, with_spaces=True)
        time.sleep(0.3)
        state = _load_state()
        state["total_actions"] += 1
        _save_state(state)
        return json.dumps({"success": True, "typed": text[:200], "into": win.window_text()}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_extract_text(window_title: str = "") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        wins = _get_windows()
        if window_title:
            wins = [w for w in wins if window_title.lower() in w.window_text().lower()]

        results = []
        for w in wins[:10]:
            try:
                txt = w.window_text()
                if txt.strip():
                    results.append({"window": txt, "class": w.class_name()})
            except Exception:
                continue
        return json.dumps({"results": results, "count": len(results)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_screenshot() -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return json.dumps({"screenshot_b64": b64, "length": len(b64)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_scroll(direction: str = "down", clicks: int = 3) -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        import pywinauto.mouse as mouse
        delta = -120 * clicks if direction == "down" else 120 * clicks
        mouse.scroll(coords=(0, 0), wheel_dist=delta)
        state = _load_state()
        state["total_actions"] += 1
        _save_state(state)
        return json.dumps({"success": True, "direction": direction, "clicks": clicks}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_press_key(key: str = "{ENTER}") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        from pywinauto.keyboard import send_keys
        send_keys(key)
        time.sleep(0.2)
        state = _load_state()
        state["total_actions"] += 1
        _save_state(state)
        return json.dumps({"success": True, "key": key}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_get_element_tree(window_title: str = "") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    for attempt in range(2):
        for backend in ("uia", "win32"):
            try:
                import gc; gc.collect()
                from io import StringIO
                import sys
                from pywinauto import Desktop

                if backend == "uia":
                    _ensure_com()
                d = Desktop(backend=backend)
                if window_title:
                    found = _find_window(window_title)
                    if not found:
                        return json.dumps({"error": f"Window '{window_title}' not found"})
                    spec = d.window(title=found.window_text())
                else:
                    wins = _get_windows()
                    wins = [w for w in wins if w.window_text().strip()]
                    if not wins:
                        return json.dumps({"error": "No windows with title found"})
                    spec = d.window(title=wins[0].window_text())

                old_stdout = sys.stdout
                sys.stdout = StringIO()
                try:
                    spec.dump_tree()
                    tree = sys.stdout.getvalue()
                finally:
                    sys.stdout = old_stdout

                return json.dumps({"window": spec.window_text(), "tree": tree[:10000]}, indent=2)
            except Exception as e:
                logger.warning("get_element_tree %s attempt %d failed: %s", backend, attempt + 1, e)
                time.sleep(1)
                continue
    return json.dumps({"error": "get_element_tree failed after all retries"})
