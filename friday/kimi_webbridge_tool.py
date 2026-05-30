"""
FRIDAY Kimi WebBridge Tool — async browser automation via Moonshot AI's
Kimi WebBridge daemon (ws://127.0.0.1:10086/ws).

Replaces Playwright-based browser_agent/browser_tools with a lightweight
WebSocket + JSON-RPC protocol. All public functions return
dict[str, Any] with at least a "success" key.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shlex
import shutil
import socket
import subprocess
import sys
import textwrap
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HAS_WEBSOCKETS = False
try:
    import websockets
    from websockets import WebSocketClientProtocol

    _HAS_WEBSOCKETS = True
except ImportError:
    WebSocketClientProtocol = None  # type: ignore[misc,assignment]

# ── Module-level state ────────────────────────────────────────────

_ws: Optional[WebSocketClientProtocol] = None
_connected: bool = False
_lock: asyncio.Lock = asyncio.Lock()
_request_id: int = 0
_WS_URL: str = "ws://127.0.0.1:10086/ws"
_CONNECT_TIMEOUT: float = 10.0
_RESPONSE_TIMEOUT: float = 30.0
_RECONNECT_ATTEMPTS: int = 3


# ── Internal helpers ──────────────────────────────────────────────


def _ensure_websockets() -> None:
    if not _HAS_WEBSOCKETS:
        raise RuntimeError(
            "The 'websockets' library is required for Kimi WebBridge. "
            "Install it with: pip install websockets"
        )


def _next_id() -> int:
    global _request_id
    _request_id += 1
    return _request_id


def _make_request(method: str, params: dict[str, Any] | None = None) -> str:
    return json.dumps(
        {
            "id": _next_id(),
            "method": method,
            "params": params or {},
        }
    )


def _build_result(success: bool, **kwargs: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"success": success}
    result.update(kwargs)
    return result


async def _send_request(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_websockets()
    global _ws, _connected

    async with _lock:
        if not _connected or _ws is None:
            return _build_result(False, error="Not connected. Call webbridge_connect() first.")

        try:
            req = _make_request(method, params)
            await _ws.send(req)
            resp = await asyncio.wait_for(_ws.recv(), timeout=_RESPONSE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("Request %s timed out after %.1fs", method, _RESPONSE_TIMEOUT)
            return _build_result(False, error=f"Request timed out after {_RESPONSE_TIMEOUT}s")
        except websockets.ConnectionClosed:
            _connected = False
            _ws = None
            return _build_result(False, error="WebSocket connection closed")
        except Exception as exc:
            logger.exception("Error sending request %s", method)
            return _build_result(False, error=str(exc))

        try:
            data = json.loads(resp)
        except (json.JSONDecodeError, TypeError) as exc:
            return _build_result(False, error=f"Invalid JSON response: {exc}")

        if "error" in data:
            err_msg = data["error"].get("message", str(data["error"]))
            return _build_result(False, error=err_msg)

        result = data.get("result", {})
        if result is None:
            result = {}
        return _build_result(True, **result)


# ── Connection management ────────────────────────────────────────


async def webbridge_connect() -> dict[str, Any]:
    """
    Establish a WebSocket connection to the Kimi WebBridge daemon.

    Retries up to _RECONNECT_ATTEMPTS times. Returns
    {"success": True, "message": "Connected to Kimi WebBridge"}
    or {"success": False, "error": "..." }.
    """
    _ensure_websockets()
    global _ws, _connected

    async with _lock:
        if _connected and _ws is not None:
            return _build_result(True, message="Already connected")

        last_error: Optional[str] = None
        for attempt in range(1, _RECONNECT_ATTEMPTS + 1):
            try:
                _ws = await asyncio.wait_for(
                    websockets.connect(_WS_URL, ping_interval=None),
                    timeout=_CONNECT_TIMEOUT,
                )
                _connected = True
                logger.info("Connected to Kimi WebBridge at %s", _WS_URL)
                return _build_result(True, message="Connected to Kimi WebBridge")
            except asyncio.TimeoutError:
                last_error = f"Connection timed out after {_CONNECT_TIMEOUT}s"
                logger.warning("Attempt %d/%d: %s", attempt, _RECONNECT_ATTEMPTS, last_error)
            except (OSError, websockets.WebSocketException) as exc:
                last_error = str(exc)
                logger.warning("Attempt %d/%d: %s", attempt, _RECONNECT_ATTEMPTS, last_error)
            except Exception as exc:
                last_error = str(exc)
                logger.exception("Attempt %d/%d failed", attempt, _RECONNECT_ATTEMPTS)

            if attempt < _RECONNECT_ATTEMPTS:
                await asyncio.sleep(1.0 * attempt)

        _connected = False
        _ws = None
        return _build_result(False, error=f"Failed to connect after {_RECONNECT_ATTEMPTS} attempts: {last_error}")


async def webbridge_disconnect() -> dict[str, Any]:
    """
    Close the WebSocket connection to the Kimi WebBridge daemon.

    Returns {"success": True, "message": "Disconnected"}.
    """
    global _ws, _connected

    async with _lock:
        if _ws is not None:
            try:
                await _ws.close()
            except Exception:
                pass
            _ws = None
        _connected = False
    return _build_result(True, message="Disconnected")


async def webbridge_doctor() -> dict[str, Any]:
    """
    Diagnose connectivity to the Kimi WebBridge daemon.

    Checks:
      1. websockets library availability
      2. Port 10086 reachability (TCP)
      3. WebSocket handshake
      4. list_actions() command round-trip

    Returns {"success": True/False, "checks": [...], "summary": "..."}.
    """
    checks: list[dict[str, Any]] = []

    step1_success = _HAS_WEBSOCKETS
    checks.append({
        "name": "websockets library",
        "passed": step1_success,
        "detail": "installed" if step1_success else "not installed (pip install websockets)",
    })
    if not step1_success:
        return _build_result(False, checks=checks, summary="Missing websockets library")

    step2_success = False
    step2_detail = ""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        result = sock.connect_ex(("127.0.0.1", 10086))
        sock.close()
        step2_success = result == 0
        step2_detail = "port open" if step2_success else "port closed or unreachable"
    except Exception as exc:
        step2_detail = str(exc)
    checks.append({
        "name": "TCP port 10086",
        "passed": step2_success,
        "detail": step2_detail,
    })
    if not step2_success:
        return _build_result(False, checks=checks, summary="Daemon not listening on port 10086")

    step3_success = False
    step3_detail = ""
    try:
        async with asyncio.timeout(5.0):
            async with websockets.connect(_WS_URL, ping_interval=None) as test_ws:
                step3_success = True
                step3_detail = "WebSocket handshake succeeded"
                req = _make_request("list_actions")
                await test_ws.send(req)
                resp = await asyncio.wait_for(test_ws.recv(), timeout=5.0)
                data = json.loads(resp)
                if "error" not in data:
                    step3_detail = "WebSocket OK, list_actions round-trip successful"
                else:
                    step3_detail = f"WebSocket OK but list_actions returned error: {data['error']}"
    except asyncio.TimeoutError:
        step3_detail = "WebSocket handshake timed out"
    except Exception as exc:
        step3_detail = str(exc)
    checks.append({
        "name": "WebSocket command round-trip",
        "passed": step3_success,
        "detail": step3_detail,
    })

    passed = all(c["passed"] for c in checks)
    summary = "All checks passed" if passed else f"{sum(1 for c in checks if not c['passed'])} check(s) failed"
    return _build_result(passed, checks=checks, summary=summary)


async def webbridge_install_instructions() -> dict[str, Any]:
    """
    Return installation and setup instructions for Kimi WebBridge.

    Returns {"success": True, "instructions": [str, ...]}.
    """
    instructions = [
        "Kimi WebBridge Browser Automation — Setup Instructions",
        "",
        "1. Install the Chrome/Edge extension:",
        "   - Open Chrome Web Store and search for 'Kimi WebBridge'",
        "   - OR visit: https://chromewebstore.google.com (search Kimi WebBridge)",
        "   - Click 'Add to Chrome' and pin the extension",
        "",
        "2. Install the daemon via npm:",
        "   npm install -g kimi-webbridge",
        "",
        "3. Start the daemon:",
        "   npx kimi-webbridge",
        "",
        "4. The daemon will listen on: ws://127.0.0.1:10086/ws",
        "",
        "5. Verify it's running:",
        f"   python -c \"import asyncio; from friday.kimi_webbridge_tool import webbridge_connect; print(asyncio.run(webbridge_connect()))\"",
        "",
        "Requirements:",
        "   - Python 3.9+ with: pip install websockets",
        "   - Node.js 18+ (for the daemon)",
        "   - Chrome or Edge browser",
    ]
    return _build_result(True, instructions=instructions)


# ── Browser actions ───────────────────────────────────────────────


async def webbridge_navigate(url: str) -> dict[str, Any]:
    """Navigate to a URL. Returns {"success": True, "url": str} or error."""
    return await _send_request("navigate", {"url": url})


async def webbridge_click(target: str) -> dict[str, Any]:
    """Click an element identified by CSS selector. Returns success status."""
    return await _send_request("click", {"target": target})


async def webbridge_fill(target: str, text: str) -> dict[str, Any]:
    """Fill a form input identified by CSS selector with the given text."""
    return await _send_request("fill", {"selector": target, "value": text})


async def webbridge_type_text(text: str) -> dict[str, Any]:
    """Type text into the currently focused element."""
    return await _send_request("fill", {"selector": "", "value": text})


async def webbridge_screenshot() -> dict[str, Any]:
    """Capture a screenshot. Returns {"success": True, "data": "<base64>"}."""
    return await _send_request("screenshot")


async def webbridge_extract_text() -> dict[str, Any]:
    """Extract visible text from the current page."""
    return await _send_request("extract_text")


async def webbridge_get_page_state() -> dict[str, Any]:
    """Get the page structure / accessible element tree."""
    return await _send_request("snapshot/get_page_state")


async def webbridge_scroll(direction: str = "down") -> dict[str, Any]:
    """Scroll the page in the given direction ("down" or "up")."""
    return await _send_request("scroll", {"direction": direction})


async def webbridge_press_key(key: str) -> dict[str, Any]:
    """Press a single keyboard key (e.g. "Enter", "Escape", "Tab")."""
    return await _send_request("press_key", {"key": key})


async def webbridge_key_combo(keys: str) -> dict[str, Any]:
    """Press a key combination (e.g. "Ctrl+C", "Alt+Tab")."""
    return await _send_request("key_combo", {"keys": keys})


async def webbridge_evaluate(js: str) -> dict[str, Any]:
    """Execute JavaScript in the page context and return the result."""
    return await _send_request("evaluate", {"js": js})


async def webbridge_submit_form(selector: str = "") -> dict[str, Any]:
    """Submit a form identified by CSS selector. If empty, submits the first form."""
    return await _send_request("submit_form", {"selector": selector})


async def webbridge_select_option(selector: str, value: str) -> dict[str, Any]:
    """Select an option in a <select> element by CSS selector and option value."""
    return await _send_request("select_option", {"selector": selector, "value": value})


async def webbridge_list_tabs() -> dict[str, Any]:
    """List all open browser tabs."""
    return await _send_request("list_tabs")


async def webbridge_close_tab(tab_id: str = "") -> dict[str, Any]:
    """Close a tab by ID. If empty, closes the current tab."""
    return await _send_request("close_tab", {"id": tab_id})


async def webbridge_find_element(criteria: dict) -> dict[str, Any]:
    """
    Find an element matching the given criteria dict.

    Criteria can include keys like "text", "selector", "aria_label", etc.
    """
    return await _send_request("find_element", criteria)


async def webbridge_highlight(selector: str) -> dict[str, Any]:
    """Visually highlight an element on the page by CSS selector."""
    return await _send_request("highlight", {"selector": selector})


async def webbridge_save_as_pdf(path: str = "") -> dict[str, Any]:
    """Save the current page as a PDF. If path is empty, returns PDF data."""
    return await _send_request("save_as_pdf", {"path": path})


async def webbridge_network(action: str = "stop") -> dict[str, Any]:
    """Start or stop network request capture. Action: "start" or "stop"."""
    return await _send_request("network", {"action": action})


async def webbridge_get_current_url() -> dict[str, Any]:
    """Get the current page URL."""
    return await _send_request("evaluate", {"js": "window.location.href"})


async def webbridge_get_title() -> dict[str, Any]:
    """Get the current page title."""
    return await _send_request("evaluate", {"js": "document.title"})


async def webbridge_hover(selector: str) -> dict[str, Any]:
    """Hover over an element identified by CSS selector."""
    return await _send_request("hover", {"selector": selector})


async def webbridge_focus(selector: str) -> dict[str, Any]:
    """Focus an element identified by CSS selector."""
    return await _send_request("focus", {"selector": selector})


async def webbridge_double_click(selector: str) -> dict[str, Any]:
    """Double-click an element identified by CSS selector."""
    return await _send_request("double_click", {"selector": selector})


async def webbridge_drag(source: str, target: str) -> dict[str, Any]:
    """Drag an element (CSS selector) onto a target element (CSS selector)."""
    return await _send_request("drag", {"source": source, "target": target})


async def webbridge_file_upload(selector: str, filepath: str) -> dict[str, Any]:
    """Upload a file via an <input type="file"> element identified by CSS selector."""
    return await _send_request("upload", {"selector": selector, "filepath": filepath})
