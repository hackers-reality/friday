"""
FRIDAY Browser Manager — singleton that manages one persistent Chrome instance
via Playwright CDP or Pyppeteer CDP (child process).

Launches Chrome with the user's existing profile to inherit all cookies, sessions,
and logged-in accounts. Inspired by CatGPT-Gateway's child process + existing
profile approach.

Backends:
  - "pyppeteer" (default): launch Chrome as child process, connect via CDP
  - "playwright": use Playwright's launch_persistent_context
"""

from __future__ import annotations

import asyncio
import os
import random
import socket
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from friday.anti_detection import apply_stealth, random_viewport
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)

_SCREENSHOT_DIR = Path(tempfile.gettempdir()) / "friday_browser"
_PLAYWRIGHT_IMPORTED = False
_PYPPETEER_IMPORTED = False


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


def _ensure_pyppeteer():
    global _PYPPETEER_IMPORTED
    if _PYPPETEER_IMPORTED:
        return True
    try:
        import pyppeteer
        _PYPPETEER_IMPORTED = True
        return True
    except ImportError:
        return False


def _detect_chrome_profile() -> str:
    if os.name == "nt":
        base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        if os.path.isdir(base):
            return base
    elif os.uname().sysname == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        if os.path.isdir(base):
            return base
    else:
        base = os.path.expanduser("~/.config/google-chrome")
        if os.path.isdir(base):
            return base
        alt = os.path.expanduser("~/.config/chromium")
        if os.path.isdir(alt):
            return alt
    return ""


def _chrome_executable() -> Optional[str]:
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
    for path in os.environ.get("PATH", "").split(os.pathsep):
        for name in ("chrome", "google-chrome", "chromium", "chromium-browser"):
            full = os.path.join(path, name + (".exe" if os.name == "nt" else ""))
            if os.path.isfile(full):
                return full
    return None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


class BrowserManager:
    """
    Singleton managing a persistent Chrome instance.

    Usage:
        bm = BrowserManager()
        await bm.start()
        page = await bm.new_page("https://youtube.com")
        html = await page.inner_text("body")
        await bm.screenshot()

    Sessions: personal, work (configurable in config.yaml).
    Backends: pyppeteer (default), playwright (fallback).
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
        self._backend: Optional[str] = None
        self._chrome_process: Any = None
        self._cdp_port: Optional[int] = None
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> BrowserManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    # ── Lifecycle ────────────────────────────────────────────

    async def start(self, backend: Optional[str] = None):
        if self._started:
            return

        cfg = ensure_config().get("browser", {})

        if backend:
            self._backend = backend
        if not self._backend:
            self._backend = cfg.get("backend", "auto")

        if self._backend == "auto":
            if _ensure_pyppeteer():
                self._backend = "pyppeteer"
            elif _ensure_playwright():
                self._backend = "playwright"
            else:
                raise RuntimeError(
                    "No browser backend available. Install pyppeteer: pip install pyppeteer\n"
                    "Or Playwright: pip install playwright && playwright install chromium"
                )

        if self._backend == "pyppeteer":
            await self._start_pyppeteer(cfg)
        elif self._backend == "playwright":
            await self._start_playwright(cfg)
        else:
            raise RuntimeError(f"Unknown browser backend: {self._backend}")

        self._started = True
        logger.info("Browser started — backend: %s, profile: %s, headless: %s",
                     self._backend, cfg.get("chrome_profile", "auto"), cfg.get("headless", True))

    async def _start_pyppeteer(self, cfg: dict):
        """Launch Chrome as child process with CDP, connect via pyppeteer."""
        import pyppeteer

        headless = cfg.get("headless", True)
        chrome_path = cfg.get("chrome_executable") or _chrome_executable()
        if not chrome_path:
            raise RuntimeError("Chrome executable not found. Install Chrome or set chrome_executable in config.")

        profile_path = cfg.get("chrome_profile", "auto")
        if not profile_path or profile_path.lower() == "auto":
            profile_path = _detect_chrome_profile()

        if not profile_path:
            logger.warning("No Chrome profile found — using temporary context (no cookies)")
            profile_path = tempfile.mkdtemp(prefix="friday_profile_")

        self._cdp_port = _find_free_port()

        launch_args = [
            chrome_path,
            f"--user-data-dir={profile_path}",
            f"--remote-debugging-port={self._cdp_port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--no-sandbox",
            f"--window-size=1920,1080",
        ]

        if headless:
            launch_args.append("--headless=new")

        logger.info("Launching Chrome (pyppeteer) on port %s — profile: %s", self._cdp_port, profile_path)

        self._chrome_process = await asyncio.create_subprocess_exec(
            *launch_args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        await _wait_for_cdp(self._cdp_port, timeout=15)

        self._browser = await pyppeteer.connect(
            browserURL=f"http://127.0.0.1:{self._cdp_port}",
            options={"headless": False},
        )

        self._contexts["personal"] = self._browser

        pages = await self._browser.pages()
        self._active_page = pages[0] if pages else await self._browser.newPage()

        anti_detection = cfg.get("anti_detection", True)
        if anti_detection:
            await apply_stealth(self._active_page)

        logger.info("Pyppeteer browser ready — %d page(s)", len(pages) if pages else 0)

    async def _start_playwright(self, cfg: dict):
        """Start Playwright-based browser with persistent context."""
        if not _ensure_playwright():
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        import playwright.async_api as pwa

        self._playwright = await pwa.async_playwright().start()

        profile_path = cfg.get("chrome_profile", "auto")
        if not profile_path or profile_path.lower() == "auto":
            profile_path = _detect_chrome_profile()

        if not profile_path:
            logger.warning("No Chrome profile found — using temporary context (no cookies)")

        headless_default = cfg.get("headless", True)
        anti_detection = cfg.get("anti_detection", True)
        chrome_path = cfg.get("chrome_executable") or _chrome_executable()

        launch_args = [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            f"--window-size=1920,1080",
        ]
        if not profile_path:
            launch_args.append("--incognito")

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
            logger.error("Failed to launch Chrome (Playwright): %s", exc)
            raise

        self._contexts["personal"] = self._browser
        self._active_context = "personal"

        pages = self._browser.pages
        self._active_page = pages[0] if pages else await self._browser.new_page()

        if anti_detection:
            await apply_stealth(self._active_page)

    async def stop(self):
        for ctx_name, ctx in self._contexts.items():
            try:
                if self._backend == "pyppeteer":
                    await ctx.disconnect()
                else:
                    await ctx.close()
            except Exception:
                pass
        self._contexts.clear()

        if self._browser and self._backend == "pyppeteer":
            try:
                await self._browser.disconnect()
            except Exception:
                pass

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass

        if self._chrome_process:
            try:
                if os.name == "nt":
                    self._chrome_process.kill()
                else:
                    self._chrome_process.terminate()
                await self._chrome_process.wait()
            except Exception:
                pass
            self._chrome_process = None

        self._started = False
        self._active_page = None
        self._browser = None
        self._playwright = None
        self._cdp_port = None
        logger.info("Browser stopped")

    # ── Page Operations ──────────────────────────────────────

    async def get_page(self) -> Any:
        if not self._started:
            await self.start()
        if not self._active_page:
            ctx = self._contexts.get(self._active_context)
            if not ctx:
                raise RuntimeError("No active browser context")
            if self._backend == "pyppeteer":
                self._active_page = await ctx.newPage()
            else:
                self._active_page = await ctx.new_page()
        return self._active_page

    async def new_page(self, url: str = "") -> Any:
        ctx = self._contexts.get(self._active_context)
        if not ctx:
            raise RuntimeError(f"No context for session: {self._active_context}")

        if self._backend == "pyppeteer":
            page = await ctx.newPage()
        else:
            page = await ctx.new_page()

        if url:
            try:
                goto_kwargs = {"waitUntil": "domcontentloaded", "timeout": 30000} if self._backend == "pyppeteer" else {"wait_until": "domcontentloaded", "timeout": 30000}
                await page.goto(url, **goto_kwargs)
            except Exception as exc:
                logger.warning("Navigation to %s failed: %s", url, exc)

        await apply_stealth(page)
        self._active_page = page
        return page

    async def close_page(self, page=None):
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
        page = await self.get_page()
        try:
            if self._backend == "pyppeteer":
                resp = await page.goto(url, waitUntil="networkidle0", timeout=timeout_ms)
                status = resp.status if resp else 0
            else:
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
        target = page or self._active_page
        if not target:
            return ""
        try:
            self._screenshot_counter += 1
            path = _SCREENSHOT_DIR / f"screenshot_{self._screenshot_counter}.png"
            await target.screenshot(path=str(path), fullPage=False if self._backend == "pyppeteer" else False)
            import base64
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            return ""

    # ── Session Management ───────────────────────────────────

    async def switch_session(self, session_name: str) -> bool:
        if session_name in self._contexts:
            self._active_context = session_name
            ctx = self._contexts[session_name]
            if self._backend == "pyppeteer":
                pages = await ctx.pages()
                self._active_page = pages[0] if pages else await ctx.newPage()
            else:
                pages = ctx.pages
                self._active_page = pages[0] if pages else await ctx.new_page()
            return True

        cfg = ensure_config().get("browser", {}).get("sessions", {})
        session_cfg = cfg.get(session_name, {})
        profile_dir = session_cfg.get("profile_dir", "")
        headless = session_cfg.get("headless", True)

        if not profile_dir or not os.path.isdir(profile_dir):
            logger.warning("Session %s has no valid profile_dir", session_name)
            return False

        try:
            if self._backend == "pyppeteer":
                import pyppeteer
                port = _find_free_port()
                chrome_path = _chrome_executable()
                proc = await asyncio.create_subprocess_exec(
                    chrome_path,
                    f"--user-data-dir={profile_dir}",
                    f"--remote-debugging-port={port}",
                    "--no-first-run",
                    "--headless=new" if headless else "",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                await _wait_for_cdp(port, timeout=10)
                ctx = await pyppeteer.connect(browserURL=f"http://127.0.0.1:{port}")
                self._contexts[session_name] = ctx
                self._active_context = session_name
                self._active_page = await ctx.newPage()
            else:
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
        cfg = ensure_config()
        cfg["browser"]["headless"] = headless
        await self.stop()
        await self.start()

    # ── Status ───────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "running": self._started,
            "backend": self._backend,
            "active_session": self._active_context,
            "sessions": list(self._contexts.keys()),
            "profile": "user_profile" if self._started else "none",
        }

    def health_check(self) -> dict:
        """Return browser health status for the health monitor."""
        if not self._started:
            return {"status": "stopped", "detail": "Browser not started"}
        try:
            page = self._active_page
            if page is None:
                return {"status": "degraded", "detail": "No active page"}
            return {"status": "ok", "detail": f"Backend: {self._backend}, Session: {self._active_context}"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# ── Helper: wait for CDP endpoint ───────────────────────────

async def _wait_for_cdp(port: int, timeout: int = 15):
    """Wait until the Chrome DevTools Protocol endpoint is ready."""
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"http://127.0.0.1:{port}/json/version")
                if resp.status_code == 200:
                    return
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError(f"Chrome CDP not ready on port {port} after {timeout}s")
