"""
FRIDAY Browser Manager — singleton that manages one persistent Chrome instance
via Playwright CDP. Launches Chrome with the user's existing profile to inherit
all cookies, sessions, and logged-in accounts.

Inspired by CatGPT-Gateway's child process + existing profile approach and
Kimi WebBridge's local-first CDP architecture.
"""

from __future__ import annotations

import asyncio
import os
import random
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from friday.anti_detection import apply_stealth, random_viewport
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)

_SCREENSHOT_DIR = Path(tempfile.gettempdir()) / "friday_browser"
_PLAYWRIGHT_IMPORTED = False


def _ensure_playwright():
    global _PLAYWRIGHT_IMPORTED
    if _PLAYWRIGHT_IMPORTED:
        return True
    try:
        import playwright
        _PLAYWRIGHT_IMPORTED = True
        return True
    except ImportError:
        return False


def _detect_chrome_profile() -> str:
    """Auto-detect the Chrome user data directory for the current OS."""
    if os.name == "nt":  # Windows
        base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        if os.path.isdir(base):
            return base
    elif os.uname().sysname == "Darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        if os.path.isdir(base):
            return base
    else:  # Linux
        base = os.path.expanduser("~/.config/google-chrome")
        if os.path.isdir(base):
            return base
        alt = os.path.expanduser("~/.config/chromium")
        if os.path.isdir(alt):
            return alt
    return ""


def _chrome_executable() -> Optional[str]:
    """Find Chrome/Chromium executable."""
    if os.name == "nt":
        candidates = [
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Chromium\Application\chrome.exe"),
        ]
    elif os.uname().sysname == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]

    for c in candidates:
        if os.path.isfile(c):
            return c
    # Try PATH
    for path in os.environ.get("PATH", "").split(os.pathsep):
        for name in ("chrome", "google-chrome", "chromium", "chromium-browser"):
            full = os.path.join(path, name + (".exe" if os.name == "nt" else ""))
            if os.path.isfile(full):
                return full
    return None


class BrowserManager:
    """
    Singleton managing a persistent Chrome instance via Playwright CDP.

    Usage:
        bm = BrowserManager()
        await bm.start()
        page = await bm.new_page("https://youtube.com")
        html = await page.inner_text("body")
        await bm.screenshot()  # returns base64 PNG

    Sessions: personal, work (configurable in config.yaml).
    """

    _instance: Optional[BrowserManager] = None

    def __init__(self):
        self._playwright: Any = None
        self._browser: Any = None
        self._contexts: dict[str, Any] = {}
        self._active_context: str = "personal"
        self._active_page: Any = None
        self._started = False
        self._screenshot_counter = 0
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> BrowserManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Lifecycle ────────────────────────────────────────────

    async def start(self):
        """Start the browser manager. Launches Playwright + Chrome."""
        if self._started:
            return

        if not _ensure_playwright():
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        import playwright.async_api as pwa

        self._playwright = await pwa.async_playwright().start()
        cfg = ensure_config().get("browser", {})

        # Detect profile
        profile_path = cfg.get("chrome_profile", "auto")
        if not profile_path or profile_path.lower() == "auto":
            profile_path = _detect_chrome_profile()

        if not profile_path:
            logger.warning("No Chrome profile found — using temporary context (no cookies)")

        headless_default = cfg.get("headless", True)
        anti_detection = cfg.get("anti_detection", True)
        chrome_path = cfg.get("chrome_executable") or _chrome_executable()

        # Build launch args
        launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            f"--window-size=1920,1080",
        ]
        if not profile_path:
            launch_args.append("--incognito")

        # Launch persistent context (inherits cookies)
        try:
            self._browser = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path or tempfile.mkdtemp(prefix="friday_browser_"),
                headless=headless_default,
                args=launch_args,
                executable_path=chrome_path,
                ignore_default_args=["--enable-automation"],
                no_viewport=False,
            )
        except Exception as exc:
            logger.error("Failed to launch Chrome: %s", exc)
            raise

        # Store default context as "personal"
        self._contexts["personal"] = self._browser
        self._active_context = "personal"

        # Create initial page
        pages = self._browser.pages
        self._active_page = pages[0] if pages else await self._browser.new_page()

        if anti_detection:
            await apply_stealth(self._active_page)

        self._started = True
        logger.info("Browser started — profile: %s, headless: %s", profile_path or "temp", headless_default)

    async def stop(self):
        """Close browser and cleanup."""
        for ctx_name, ctx in self._contexts.items():
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts.clear()
        if self._playwright:
            await self._playwright.stop()
        self._started = False
        self._active_page = None
        self._browser = None
        logger.info("Browser stopped")

    # ── Page Management ──────────────────────────────────────

    async def get_page(self) -> Any:
        """Return the active page (Page object)."""
        if not self._started:
            await self.start()
        if not self._active_page:
            self._active_page = await self._contexts[self._active_context].new_page()
        return self._active_page

    async def new_page(self, url: str = "") -> Any:
        """Create a new page (tab) and optionally navigate to URL."""
        ctx = self._contexts.get(self._active_context)
        if not ctx:
            raise RuntimeError(f"No context for session: {self._active_context}")
        page = await ctx.new_page()
        if url:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                logger.warning("Navigation to %s failed: %s", url, exc)
        await apply_stealth(page)
        self._active_page = page
        return page

    async def close_page(self, page=None):
        """Close a specific page or the active page."""
        target = page or self._active_page
        if target:
            try:
                await target.close()
            except Exception:
                pass
        if target == self._active_page:
            self._active_page = None

    # ── Navigation ───────────────────────────────────────────

    async def navigate(self, url: str, timeout_ms: int = 30000) -> dict:
        """Navigate to a URL. Returns {url, title, status_code, ok}."""
        page = await self.get_page()
        try:
            resp = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            status = resp.status if resp else 0
            return {
                "url": page.url,
                "title": await page.title(),
                "status_code": status,
                "ok": 200 <= status < 400 if status else False,
            }
        except Exception as exc:
            logger.warning("Navigation error: %s", exc)
            return {"url": url, "title": "", "status_code": 0, "ok": False, "error": str(exc)}

    # ── Screenshot ───────────────────────────────────────────

    async def screenshot(self, page=None) -> str:
        """Take screenshot, return base64 PNG. Saves to temp dir."""
        target = page or self._active_page
        if not target:
            return ""
        try:
            self._screenshot_counter += 1
            path = _SCREENSHOT_DIR / f"screenshot_{self._screenshot_counter}.png"
            await target.screenshot(path=str(path), full_page=False)
            import base64
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            return ""

    # ── Session Management ───────────────────────────────────

    async def switch_session(self, session_name: str) -> bool:
        """Switch to a named session. Creates if needed."""
        if session_name in self._contexts:
            self._active_context = session_name
            pages = self._contexts[session_name].pages
            self._active_page = pages[0] if pages else await self._contexts[session_name].new_page()
            return True

        # Create new session from config
        cfg = ensure_config().get("browser", {}).get("sessions", {})
        session_cfg = cfg.get(session_name, {})
        profile_dir = session_cfg.get("profile_dir", "")
        headless = session_cfg.get("headless", True)

        if not profile_dir or not os.path.isdir(profile_dir):
            logger.warning("Session %s has no valid profile_dir", session_name)
            return False

        try:
            import playwright.async_api as pwa
            ctx = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
            self._contexts[session_name] = ctx
            self._active_context = session_name
            self._active_page = await ctx.new_page()
            logger.info("Created new session: %s", session_name)
            return True
        except Exception as exc:
            logger.error("Failed to create session %s: %s", session_name, exc)
            return False

    def list_sessions(self) -> list[str]:
        return list(self._contexts.keys())

    def active_session(self) -> str:
        return self._active_context

    # ── Toggle Headless ──────────────────────────────────────

    async def set_headless(self, headless: bool):
        """Toggle headless mode (requires restart)."""
        cfg = ensure_config()
        cfg["browser"]["headless"] = headless
        await self.stop()
        await self.start()

    # ── Status ───────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "running": self._started,
            "active_session": self._active_context,
            "sessions": list(self._contexts.keys()),
            "profile": getattr(self._browser, "_user_data_dir", "unknown") if self._browser else "none",
        }
