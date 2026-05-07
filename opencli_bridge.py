"""
OpenCLI Bridge - wraps the opencli npm CLI tool for Friday.
Provides browser automation via `opencli browser` commands.
"""

import subprocess
import json
import os
import tempfile
import time
from typing import Optional


def _run_opencli(args: list, timeout: int = 30) -> dict:
    """Run an opencli command and return parsed result."""
    cmd = ["opencli"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Try to parse stdout as JSON
        if stdout:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass
        if result.returncode != 0:
            return {"error": stderr or stdout or f"exit code {result.returncode}"}
        return {"output": stdout}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except FileNotFoundError:
        return {"error": "OpenCLI not installed. Run: npm install -g @jackwener/opencli"}
    except Exception as e:
        return {"error": str(e)}


def _run_opencli_raw(args: list, timeout: int = 30) -> str:
    """Run an opencli command and return raw stdout."""
    cmd = ["opencli"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return f"[FAIL] {result.stderr or result.stdout}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[FAIL] Command timed out"
    except FileNotFoundError:
        return "[FAIL] OpenCLI not installed. Run: npm install -g @jackwener/opencli"
    except Exception as e:
        return f"[FAIL] {e}"


def opencli_init(profile: Optional[str] = None) -> str:
    """Initialize the OpenCLI browser bridge."""
    args = ["browser", "init"]
    if profile:
        args.extend(["--profile", profile])
    result = _run_opencli_raw(args, timeout=60)
    return result


def opencli_open(url: str) -> str:
    """Open URL in the OpenCLI browser automation window."""
    result = _run_opencli_raw(["browser", "open", url])
    return result


def opencli_click(target: str) -> str:
    """Click element identified by selector or text."""
    result = _run_opencli_raw(["browser", "click", target])
    return result


def opencli_type(target: str, text: str) -> str:
    """Click element then type text."""
    result = _run_opencli_raw(["browser", "type", target, text])
    return result


def opencli_fill(target: str, text: str) -> str:
    """Set input value exactly and verify."""
    result = _run_opencli_raw(["browser", "fill", target, text])
    return result


def opencli_extract() -> str:
    """Extract page content as markdown."""
    result = _run_opencli_raw(["browser", "extract"])
    return result


def opencli_screenshot(path: Optional[str] = None) -> str:
    """Take a screenshot. Saves to given path or temp file."""
    args = ["browser", "screenshot"]
    if path:
        args.append(path)
    result = _run_opencli_raw(args)
    return result


def opencli_scroll(direction: str = "down") -> str:
    """Scroll the page. Direction: down, up, top, bottom."""
    result = _run_opencli_raw(["browser", "scroll", direction])
    return result


def opencli_keys(key: str) -> str:
    """Press a keyboard key (Enter, Escape, Tab, etc.)."""
    result = _run_opencli_raw(["browser", "keys", key])
    return result


def opencli_state() -> str:
    """Get current page state: URL, title, interactive elements."""
    result = _run_opencli_raw(["browser", "state"])
    return result


def opencli_back() -> str:
    """Go back in browser history."""
    result = _run_opencli_raw(["browser", "back"])
    return result


def opencli_eval(js: str) -> str:
    """Execute JavaScript in the browser page."""
    result = _run_opencli_raw(["browser", "eval", js])
    return result


def opencli_close() -> str:
    """Release the current automation tab lease."""
    result = _run_opencli_raw(["browser", "close"])
    return result


def opencli_dialog(action: str = "dismiss") -> str:
    """Handle a blocking JavaScript dialog. action: dismiss, accept, or accept <text>."""
    args = ["browser", "dialog"]
    if action:
        args.append(action)
    result = _run_opencli_raw(args)
    return result


def opencli_wait(type_: str, value: Optional[str] = None) -> str:
    """Wait for selector, text, time, or XHR."""
    args = ["browser", "wait", type_]
    if value:
        args.append(value)
    result = _run_opencli_raw(args, timeout=60)
    return result


def opencli_doctor() -> str:
    """Diagnose OpenCLI browser bridge connectivity."""
    result = _run_opencli_raw(["doctor"], timeout=30)
    return result


def opencli_verify() -> str:
    """Verify browser bridge connection."""
    result = _run_opencli_raw(["browser", "verify"])
    return result


def opencli_analyze(url: str) -> str:
    """Classify a website for adapter compatibility."""
    result = _run_opencli_raw(["browser", "analyze", url])
    return result


# Convenience: high-level action sequences

def opencli_navigate_and_wait(url: str, wait_for: str = "load") -> str:
    """Navigate to URL and wait for page to load."""
    nav = opencli_open(url)
    if "[FAIL]" in nav:
        return nav
    time.sleep(2)
    if wait_for == "load":
        return nav
    return opencli_wait(wait_for)


def opencli_type_and_enter(target: str, text: str) -> str:
    """Type text into an element and press Enter."""
    result = opencli_type(target, text)
    if "[FAIL]" in result:
        return result
    time.sleep(0.5)
    return opencli_keys("Enter")


def opencli_get_page_text() -> str:
    """Extract readable text from current page."""
    return opencli_eval("document.body.innerText")
