"""
OpenCLI Integration — wraps the real @jackwener/opencli binary for browser automation.
Uses `opencli browser` subcommands directly. Falls back to CDP/vision only if binary not found.
"""

import subprocess
import os
import time
import json
from typing import Optional


def _opencli_binary() -> Optional[str]:
    """Locate the opencli binary. Returns None if not installed."""
    try:
        result = subprocess.run(["where", "opencli"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0].strip()
            if os.path.isfile(path):
                return path
    except Exception:
        pass
    try:
        result = subprocess.run(["opencli", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return "opencli"
    except Exception:
        pass
    return None


def _run_opencli(args: list, timeout: int = 30) -> str:
    """Run an opencli command and return stdout."""
    binary = _opencli_binary()
    if not binary:
        raise RuntimeError("OpenCLI not installed. Run: npm install -g @jackwener/opencli")
    cmd = [binary] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return f"[FAIL] {result.stderr or result.stdout}"
    return result.stdout.strip()


def opencli_navigate(url: str) -> str:
    """Navigate to URL using opencli browser open."""
    try:
        return _run_opencli(["browser", "open", url])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Navigate error: {e}"


def opencli_click(target: str) -> str:
    """Click element using opencli browser click."""
    try:
        return _run_opencli(["browser", "click", target])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Click error: {e}"


def opencli_type(target: str, text: str) -> str:
    """Type text into element using opencli browser type."""
    try:
        return _run_opencli(["browser", "type", target, text])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Type error: {e}"


def opencli_fill(target: str, text: str) -> str:
    """Set input value exactly using opencli browser fill."""
    try:
        return _run_opencli(["browser", "fill", target, text])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Fill error: {e}"


def opencli_extract() -> str:
    """Extract page content as markdown using opencli browser extract."""
    try:
        return _run_opencli(["browser", "extract"], timeout=60)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Extract error: {e}"


def opencli_screenshot(path: Optional[str] = None) -> str:
    """Take screenshot using opencli browser screenshot."""
    try:
        args = ["browser", "screenshot"]
        if path:
            args.append(path)
        return _run_opencli(args)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Screenshot error: {e}"


def opencli_scroll(direction: str = "down") -> str:
    """Scroll page using opencli browser scroll."""
    try:
        return _run_opencli(["browser", "scroll", direction])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Scroll error: {e}"


def opencli_keys(key: str) -> str:
    """Press keyboard key using opencli browser keys."""
    try:
        return _run_opencli(["browser", "keys", key])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Key error: {e}"


def opencli_state() -> str:
    """Get page state using opencli browser state."""
    try:
        return _run_opencli(["browser", "state"])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] State error: {e}"


def opencli_eval(js: str) -> str:
    """Execute JS using opencli browser eval."""
    try:
        return _run_opencli(["browser", "eval", js])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Eval error: {e}"


def opencli_back() -> str:
    """Go back using opencli browser back."""
    try:
        return _run_opencli(["browser", "back"])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Back error: {e}"


def opencli_init() -> str:
    """Initialize OpenCLI browser bridge."""
    try:
        return _run_opencli(["browser", "init"], timeout=60)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Init error: {e}"


def opencli_doctor() -> str:
    """Run OpenCLI doctor to diagnose connectivity."""
    try:
        return _run_opencli(["doctor"], timeout=30)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Doctor error: {e}"


def opencli_verify() -> str:
    """Verify browser bridge connection."""
    try:
        return _run_opencli(["browser", "verify"])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Verify error: {e}"


# Instagram DM via real OpenCLI
def instagram_message_opencli(username: str, message: str) -> str:
    """Send Instagram DM using real OpenCLI browser automation."""
    try:
        result = opencli_navigate("https://www.instagram.com/direct/new/")
        if result.startswith("[FAIL]"):
            return result
        time.sleep(3)

        # Search for the user
        result = opencli_type("input[placeholder='Search...']", username)
        time.sleep(2)

        # Click the first search result
        result = opencli_click("the first search result")
        time.sleep(1)

        # Type message
        result = opencli_type("div[role='textbox']", message)
        time.sleep(1)

        # Send
        result = opencli_keys("Enter")
        return f"Message sent to {username} via OpenCLI"
    except Exception as e:
        return f"Instagram OpenCLI message failed: {e}"
