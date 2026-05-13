"""
OpenCLI Integration — wraps the real @jackwener/opencli binary.
Provides:
  - Browser automation via opencli browser * primitives (navigate, click, type, extract, etc.)
  - Built-in site adapters for 100+ sites (hackernews, reddit, twitter, bilibili, etc.)
  - Desktop app control via CDP (Cursor, Codex, ChatGPT, Notion, Discord)
  - CLI Hub for local binaries (gh, docker, etc.)
"""

import subprocess
import os
import time
import json
from typing import Optional


def _opencli_binary() -> Optional[str]:
    """Locate the opencli binary. Returns None if not installed."""
    # On Windows, npm installs opencli.cmd, opencli.ps1, and opencli (shell script)
    # Prefer .cmd which runs via cmd.exe -> node
    try:
        result = subprocess.run(["where", "opencli"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
            # Prefer .cmd over .ps1 over extensionless
            for pref in [".cmd", ".ps1", ""]:
                for p in paths:
                    if p.endswith(pref):
                        if os.path.isfile(p):
                            return p
    except Exception:
        pass
    return None


SESSION_NAME = "default"

def _browser_args(subcommand: str, *extra: str) -> list:
    """Build args list for browser commands with session."""
    return ["browser", "--session", SESSION_NAME, subcommand, *extra]

def _run_opencli(args: list, timeout: int = 30) -> str:
    """Run an opencli command and return stdout."""
    binary = _opencli_binary()
    if not binary:
        raise RuntimeError("OpenCLI not installed. Run: npm install -g @jackwener/opencli")

    # Build the right command based on file type
    if binary.endswith(".ps1"):
        cmd = ["powershell.exe", "-NoProfile", "-File", binary] + args
    elif binary.endswith(".cmd"):
        cmd = [binary] + args
    else:
        cmd = [binary] + args

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip()
        return f"[FAIL] {msg}" if msg else "[FAIL] Command failed"
    return result.stdout.strip()


def opencli_navigate(url: str) -> str:
    """Open URL in Chrome, then bind OpenCLI to the tab. Avoids 'browser open' hang on Windows."""
    import webbrowser, time
    try:
        webbrowser.open(url)
        time.sleep(2)
        result = _run_opencli(_browser_args("bind"), timeout=15)
        return f"[OK] Opened {url} and bound session.\n{result}" if "[FAIL]" not in result else f"[OK] Opened {url}.\n[WARN] Bind failed: {result}"
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Navigate error: {e}"


def opencli_click(target: str) -> str:
    """Click element using opencli browser click."""
    try:
        return _run_opencli(_browser_args("click", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Click error: {e}"


def opencli_type(target: str, text: str) -> str:
    """Type text into element using opencli browser type."""
    try:
        return _run_opencli(_browser_args("type", target, text))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Type error: {e}"


def opencli_fill(target: str, text: str) -> str:
    """Set input value exactly using opencli browser fill."""
    try:
        return _run_opencli(_browser_args("fill", target, text))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Fill error: {e}"


def opencli_extract() -> str:
    """Extract page content as markdown using opencli browser extract."""
    try:
        return _run_opencli(_browser_args("extract"), timeout=60)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Extract error: {e}"


def opencli_screenshot(path: Optional[str] = None) -> str:
    """Take screenshot using opencli browser screenshot."""
    try:
        args = _browser_args("screenshot")
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
        return _run_opencli(_browser_args("scroll", direction))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Scroll error: {e}"


def opencli_keys(key: str) -> str:
    """Press keyboard key using opencli browser keys."""
    try:
        return _run_opencli(_browser_args("keys", key))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Key error: {e}"


def opencli_state() -> str:
    """Get page state using opencli browser state."""
    try:
        return _run_opencli(_browser_args("state"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] State error: {e}"


def opencli_eval(js: str) -> str:
    """Execute JS using opencli browser eval."""
    try:
        return _run_opencli(_browser_args("eval", js))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Eval error: {e}"


def opencli_run(args: str) -> str:
    """Run ANY opencli command with arbitrary arguments. Flexible catch-all."""
    try:
        import shlex
        return _run_opencli(shlex.split(args), timeout=60)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] opencli run error: {e}"


# ======== BUILT-IN SITE ADAPTERS ========
# These use opencli's 100+ built-in deterministic adapters (no browser needed).

def opencli_site_site(site: str, command: str, args: str = "") -> str:
    """Run a built-in OpenCLI site adapter command.
    Example: opencli_site_site('hackernews', 'top', '--limit 5')
    """
    try:
        import shlex
        cmd_args = [site, command] + shlex.split(args)
        return _run_opencli(cmd_args, timeout=30)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] opencli site error: {e}"


def opencli_hackernews(command: str = "top", limit: int = 5) -> str:
    """Get HackerNews posts. Commands: top, new, best, ask, show, jobs."""
    try:
        return _run_opencli(["hackernews", command, "--limit", str(limit)])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] HackerNews error: {e}"


def opencli_reddit(command: str = "hot", subreddit: str = "", limit: int = 5) -> str:
    """Get Reddit posts. Commands: hot, frontpage, popular, search, subreddit."""
    try:
        args = ["reddit", command, "--limit", str(limit)]
        if subreddit and command == "subreddit":
            args.append(subreddit)
        return _run_opencli(args)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Reddit error: {e}"


def opencli_twitter(command: str = "trending", limit: int = 5) -> str:
    """Get Twitter/X data. Commands: trending, search, timeline, tweets, profile."""
    try:
        return _run_opencli(["twitter", command, "--limit", str(limit)])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Twitter error: {e}"


def opencli_list_adapters() -> str:
    """List all available OpenCLI commands and site adapters."""
    try:
        return _run_opencli(["list"])
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] List error: {e}"


def opencli_back() -> str:
    """Go back using opencli browser back."""
    try:
        return _run_opencli(_browser_args("back"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Back error: {e}"


def opencli_init() -> str:
    """Initialize OpenCLI browser session."""
    try:
        return _run_opencli(_browser_args("state"), timeout=60)
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


# ======== ADDITIONAL OPENCLI BROWSER COMMANDS ========

def opencli_tab_list() -> str:
    """List all browser tabs with their indices, URLs, and titles."""
    try:
        return _run_opencli(_browser_args("tab", "list"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Tab list error: {e}"


def opencli_tab_new(url: str = "") -> str:
    """Open a new browser tab, optionally navigating to a URL."""
    try:
        args = _browser_args("tab", "new")
        if url:
            args.append(url)
        return _run_opencli(args)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Tab new error: {e}"


def opencli_tab_select(target_id: str) -> str:
    """Switch to a specific tab by its target ID."""
    try:
        return _run_opencli(_browser_args("tab", "select", target_id))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Tab select error: {e}"


def opencli_tab_close(target_id: str = "") -> str:
    """Close a browser tab by target ID, or the current tab if empty."""
    try:
        args = _browser_args("tab", "close")
        if target_id:
            args.append(target_id)
        return _run_opencli(args)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Tab close error: {e}"


def opencli_close() -> str:
    """Release the current browser session tab lease."""
    try:
        return _run_opencli(_browser_args("close"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Close error: {e}"


def opencli_wait_selector(selector: str, timeout_ms: int = 10000) -> str:
    """Wait for a CSS selector to appear in the page."""
    try:
        return _run_opencli(_browser_args("wait", "selector", selector, "--timeout", str(timeout_ms)))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Wait error: {e}"


def opencli_wait_text(text: str, timeout_ms: int = 10000) -> str:
    """Wait for text to appear on the page."""
    try:
        return _run_opencli(_browser_args("wait", "text", text, "--timeout", str(timeout_ms)))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Wait text error: {e}"


def opencli_find(selector: str, limit: int = 10) -> str:
    """Find elements matching a CSS selector and return their details."""
    try:
        return _run_opencli(_browser_args("find", "--css", selector, "--limit", str(limit)))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Find error: {e}"


def opencli_get_url() -> str:
    """Get the current page URL."""
    try:
        return _run_opencli(_browser_args("get", "url"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Get URL error: {e}"


def opencli_get_title() -> str:
    """Get the current page title."""
    try:
        return _run_opencli(_browser_args("get", "title"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Get title error: {e}"


def opencli_network() -> str:
    """Inspect network requests made by the current page."""
    try:
        return _run_opencli(_browser_args("network"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Network error: {e}"


def opencli_bind(domain: str = "") -> str:
    """Bind OpenCLI to the current Chrome tab for persistent interaction."""
    try:
        args = _browser_args("bind")
        if domain:
            args.extend(["--domain", domain])
        return _run_opencli(args)
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Bind error: {e}"


def opencli_unbind() -> str:
    """Unbind from the current Chrome tab."""
    try:
        return _run_opencli(_browser_args("unbind"))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Unbind error: {e}"


def opencli_hover(target: str) -> str:
    """Hover over an element."""
    try:
        return _run_opencli(_browser_args("hover", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Hover error: {e}"


def opencli_focus(target: str) -> str:
    """Focus an element."""
    try:
        return _run_opencli(_browser_args("focus", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Focus error: {e}"


def opencli_dblclick(target: str) -> str:
    """Double-click an element."""
    try:
        return _run_opencli(_browser_args("dblclick", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Dblclick error: {e}"


def opencli_check(target: str) -> str:
    """Check a checkbox/radio element."""
    try:
        return _run_opencli(_browser_args("check", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Check error: {e}"


def opencli_uncheck(target: str) -> str:
    """Uncheck a checkbox/radio element."""
    try:
        return _run_opencli(_browser_args("uncheck", target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Uncheck error: {e}"


def opencli_drag(source: str, target: str) -> str:
    """Drag one element to another."""
    try:
        return _run_opencli(_browser_args("drag", source, target))
    except RuntimeError as e:
        return f"[FAIL] {e}"
    except Exception as e:
        return f"[FAIL] Drag error: {e}"
