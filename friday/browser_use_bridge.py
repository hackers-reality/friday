"""
FRIDAY Browser-Use Bridge — full browser control via Playwright.
Provides both:
  - High-level: browser_use_navigate(task) — simple navigation
  - Low-level: direct DOM ops (click, type, extract, screenshot, scroll, etc.)

Playwright manages a persistent Chromium instance in headful (visible) mode.
All Playwright operations run on a dedicated background thread to avoid
event-loop conflicts with Gemini Live API.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import base64
import threading
from datetime import datetime
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_BROWSER_AVAILABLE = False
_AsyncPlaywright = None

try:
    from playwright.async_api import async_playwright as _AsyncPlaywright
    _BROWSER_AVAILABLE = True
except ImportError:
    pass

_playwright_instance = None
_browser_instance = None
_context_instance = None
_page_instance = None

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_ready = threading.Event()

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "browser_use_state.json")
_HISTORY_PATH = os.path.join(FRIDAY_MEMORY, "browser_use_history.jsonl")
_STORAGE_PATH = os.path.join(FRIDAY_MEMORY, "browser_storage_state.json")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": 0, "total_steps": 0, "last_task": ""}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    try:
        with open(_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _log_history(entry: dict):
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    try:
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


import sys as _sys

def _start_bg_loop():
    """Run in background thread: owns the asyncio event loop for Playwright."""
    global _bg_loop
    # Python 3.13 Windows: only ProactorEventLoop supports subprocesses (needed by Playwright)
    if _sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    _bg_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_bg_loop)
    _bg_ready.set()
    _bg_loop.run_forever()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_thread, _bg_loop, _bg_ready
    if _bg_thread is None or not _bg_thread.is_alive():
        _bg_loop = None
        _bg_ready.clear()
        _bg_thread = threading.Thread(target=_start_bg_loop, daemon=True, name="browser-bg")
        _bg_thread.start()
        _bg_ready.wait()
    return _bg_loop


def _run_async(coro) -> Any:
    """Run a coroutine on the background event loop and return result synchronously."""
    loop = _get_bg_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result(timeout=60)


async def _ensure_browser(force_new: bool = False):
    global _playwright_instance, _browser_instance, _context_instance, _page_instance
    # If we already have a live page, return it
    if not force_new and _page_instance is not None:
        try:
            await _page_instance.evaluate("1")
            return _context_instance, _page_instance
        except Exception:
            # Page/context was closed by user — clean up stale globals
            logger.info("Browser page was closed, recreating...")
            for g in ["_context_instance", "_page_instance"]:
                try:
                    obj = globals()[g]
                    if obj is not None:
                        await obj.close()
                except Exception:
                    pass
            _context_instance = None
            _page_instance = None

    if _playwright_instance is None:
        _playwright_instance = await _AsyncPlaywright().__aenter__()

    # If context is dead/stale, recreate it
    profile_dir = os.path.join(FRIDAY_MEMORY, "friday_chrome_profile")
    for attempt in range(3):
        try:
            if _context_instance is None or force_new:
                if _context_instance is not None:
                    try:
                        await _context_instance.close()
                    except Exception:
                        pass
                os.makedirs(profile_dir, exist_ok=True)
                logger.info("Launching persistent Chromium with profile: %s", profile_dir)
                _context_instance = await _playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                    ],
                    no_viewport=True,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                _browser_instance = _context_instance
            break
        except Exception as e:
            err = str(e)
            if "Opening in existing browser session" in err and attempt < 2:
                logger.warning("Profile locked (attempt %d), waiting and retrying...", attempt + 1)
                await asyncio.sleep(2)
            elif attempt == 2:
                logger.warning("Profile locked after 3 attempts, using temp profile")
                import tempfile, shutil
                tmp_dir = os.path.join(tempfile.gettempdir(), "friday_browser_tmp")
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
                _context_instance = await _playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=tmp_dir,
                    headless=False,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                    ],
                    no_viewport=True,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                _browser_instance = _context_instance
            else:
                raise

    if _page_instance is None or force_new:
        pages = _context_instance.pages
        _page_instance = pages[0] if pages else await _context_instance.new_page()
    return _context_instance, _page_instance


async def _save_storage():
    """Save browser cookies/localStorage to disk for persistence across sessions."""
    if _context_instance is not None:
        try:
            state = await _context_instance.storage_state()
            os.makedirs(os.path.dirname(_STORAGE_PATH), exist_ok=True)
            with open(_STORAGE_PATH, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass


async def _direct_action(action: str, **kwargs) -> dict:
    ctx, page = await _ensure_browser()

    if action == "navigate":
        url = kwargs.get("url", "")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        for attempt in range(2):
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await page.title()
                await _save_storage()
                return {"title": title, "url": page.url, "status": resp.status if resp else 0}
            except Exception:
                if attempt == 0:
                    ctx, page = await _ensure_browser(force_new=True)
                    continue
                return {"error": f"navigate failed: {url}"}
        return {"title": "", "url": url, "status": 0}

    elif action == "click":
        selector = kwargs.get("selector", "")
        text = kwargs.get("text", "")
        if text and not selector:
            selector = f"text={text}"
        elif not selector and not text:
            return {"error": "Provide selector or text to click"}
        try:
            await page.click(selector, timeout=5000)
            return {"success": True, "selector": selector}
        except Exception:
            try:
                await page.click(f"text={text}", timeout=5000)
                return {"success": True, "selector": f"text={text}"}
            except Exception as e2:
                return {"error": f"Click failed: {e2}"}

    elif action == "type":
        selector = kwargs.get("selector", "")
        text = kwargs.get("text", "")
        clear_first = kwargs.get("clear_first", True)
        if not selector:
            return {"error": "Provide selector to type into"}
        try:
            if clear_first:
                await page.fill(selector, text)
            else:
                await page.type(selector, text, delay=50)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"error": f"Type failed: {e}"}

    elif action == "extract_text":
        selector = kwargs.get("selector", "body")
        els = await page.query_selector_all(selector)
        results = []
        for el in els[:50]:
            results.append(await el.inner_text())
        text = "\n".join(r.strip() for r in results if r.strip())
        return {"text": text[:10000], "length": len(text)}

    elif action == "extract_html":
        html = await page.content()
        return {"html": html[:50000], "length": len(html)}

    elif action == "extract_links":
        links = await page.query_selector_all("a[href]")
        results = []
        for a in links:
            href = await a.get_attribute("href")
            text = await a.inner_text()
            if href:
                results.append({"href": href.strip(), "text": text.strip()[:100]})
        return {"links": results[:100], "count": len(results)}

    elif action == "screenshot":
        b64_bytes = await page.screenshot(type="png", full_page=kwargs.get("full_page", False))
        b64_str = base64.b64encode(b64_bytes).decode()
        return {"screenshot_b64": b64_str, "length": len(b64_str)}

    elif action == "scroll":
        direction = kwargs.get("direction", "down")
        amount = kwargs.get("amount", 500)
        sign = "+" if direction == "down" else "-"
        await page.evaluate(f"window.scrollBy(0, {sign}{amount})")
        await asyncio.sleep(0.3)
        return {"success": True, "direction": direction, "amount": amount}

    elif action == "evaluate":
        js = kwargs.get("script", "")
        if not js:
            return {"error": "Provide JavaScript to evaluate"}
        result = await page.evaluate(js)
        return {"result": str(result)[:5000]}

    elif action == "get_url":
        return {"url": page.url}

    elif action == "get_title":
        return {"title": await page.title()}

    elif action == "get_dom_state":
        state_info = await page.evaluate("""() => ({
            url: location.href,
            title: document.title,
            viewport: { w: window.innerWidth, h: window.innerHeight },
            links: document.querySelectorAll('a').length,
            buttons: document.querySelectorAll('button, input[type=submit], input[type=button]').length,
            inputs: document.querySelectorAll('input:not([type=hidden]), textarea, select').length,
            images: document.querySelectorAll('img').length,
            scrollY: window.scrollY,
            scrollHeight: document.documentElement.scrollHeight,
        })""")
        return state_info

    elif action == "list_tabs":
        all_pages = _context_instance.pages if _context_instance else []
        tabs = []
        for i, p in enumerate(all_pages):
            try:
                tabs.append({"index": i, "title": await p.title(), "url": p.url, "active": p == page})
            except Exception:
                tabs.append({"index": i, "title": "(unknown)", "url": "(closed?)"})
        return {"tabs": tabs, "count": len(tabs)}

    elif action == "new_tab":
        url = kwargs.get("url", "about:blank")
        new_page = await _context_instance.new_page()
        await new_page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "url": url, "tab_index": len(_context_instance.pages) - 1}

    elif action == "close_tab":
        try:
            await page.close()
            # Switch to the first available page if any
            all_pages = _context_instance.pages if _context_instance else []
            if all_pages:
                global _page_instance
                _page_instance = all_pages[0]
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    elif action == "go_back":
        await page.go_back()
        return {"url": page.url, "title": await page.title()}

    elif action == "go_forward":
        await page.go_forward()
        return {"url": page.url, "title": await page.title()}

    return {"error": f"Unknown action: {action}"}


def _run_sync(action: str, **kwargs) -> str:
    if not _BROWSER_AVAILABLE:
        return browser_use_available()
    try:
        result = _run_async(_direct_action(action, **kwargs))
        return json.dumps(result, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


async def _run_agent(task: str, max_steps: int = 20) -> dict:
    for attempt in range(2):
        ctx, page = await _ensure_browser(force_new=(attempt > 0))
        try:
            resp = await page.goto(task, wait_until="domcontentloaded", timeout=30000)
            title = await page.title()
            content = await page.content()
            return {
                "steps": 1,
                "result": f"Navigated to {page.url}\nPage title: {title}\nContent length: {len(content)} characters",
            }
        except Exception:
            if attempt == 0:
                continue
            return {"steps": 1, "result": f"[FAIL] Browser navigate failed: {task[:80]}"}
    return {"steps": 1, "result": f"[FAIL] Browser navigate failed: {task[:80]}"}


def browser_use_navigate(task: str, max_steps: int = 20) -> str:
    if not _BROWSER_AVAILABLE:
        return browser_use_available()

    state = _load_state()
    state["sessions"] += 1
    state["last_task"] = task[:200]
    _save_state(state)

    try:
        result = _run_async(_run_agent(task, max_steps))

        state = _load_state()
        state["total_steps"] += result["steps"]
        _save_state(state)

        _log_history({
            "timestamp": datetime.now().isoformat(),
            "type": "navigate",
            "task": task[:200],
            "steps": result["steps"],
            "result_preview": result["result"][:500],
        })

        lines = [
            "### BROWSER USE COMPLETE",
            f"**Task**: {task[:200]}",
            f"**Steps taken**: {result['steps']}",
            "",
            result["result"],
        ]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("browser navigate failed: %s", exc)
        return f"[FAIL] Browser navigate failed: {exc}"


def browser_use_extract(task: str, instruction: str = "Extract all visible text, links, and structured data from the page") -> str:
    if not _BROWSER_AVAILABLE:
        return browser_use_available()
    try:
        nav_result = _run_async(_direct_action("navigate", url=task))
        text_result = _run_async(_direct_action("extract_text"))
        return f"### EXTRACT from {task}\n\n{text_result.get('text', '')[:10000]}"
    except Exception as exc:
        return f"[FAIL] Extraction failed: {exc}"


def browser_use_available() -> str:
    if _BROWSER_AVAILABLE:
        return "[OK] Playwright is available."
    return "[FAIL] Playwright not installed. Run: pip install playwright && playwright install chromium"


def browser_use_click(selector: str = "", text: str = "") -> str:
    return _run_sync("click", selector=selector, text=text)


def browser_use_type(selector: str, text: str, clear_first: bool = True) -> str:
    return _run_sync("type", selector=selector, text=text, clear_first=clear_first)


def browser_use_extract_text(selector: str = "body") -> str:
    return _run_sync("extract_text", selector=selector)


def browser_use_extract_html() -> str:
    return _run_sync("extract_html")


def browser_use_extract_links() -> str:
    return _run_sync("extract_links")


def browser_use_screenshot(full_page: bool = False) -> str:
    return _run_sync("screenshot", full_page=full_page)


def browser_use_scroll(direction: str = "down", amount: int = 500) -> str:
    return _run_sync("scroll", direction=direction, amount=amount)


def browser_use_evaluate(script: str) -> str:
    return _run_sync("evaluate", script=script)


def browser_use_get_dom_state() -> str:
    return _run_sync("get_dom_state")


def browser_use_get_url() -> str:
    return _run_sync("get_url")


def browser_use_get_title() -> str:
    return _run_sync("get_title")


def browser_use_list_tabs() -> str:
    return _run_sync("list_tabs")


def browser_use_new_tab(url: str = "about:blank") -> str:
    return _run_sync("new_tab", url=url)


def browser_use_close_tab() -> str:
    return _run_sync("close_tab")


def browser_use_go_back() -> str:
    return _run_sync("go_back")


def browser_use_go_forward() -> str:
    return _run_sync("go_forward")


def browser_use_status() -> str:
    state = _load_state()
    browser_ok = _browser_instance is not None or _context_instance is not None
    lines = [
        "### BROWSER USE STATUS",
        f"**Playwright**: {'Yes' if _BROWSER_AVAILABLE else 'No'}",
        f"**Browser active**: {'Yes' if browser_ok else 'No'}",
        f"**Sessions**: {state.get('sessions', 0)}",
        f"**Total steps**: {state.get('total_steps', 0)}",
        f"**Last task**: {state.get('last_task', 'N/A')[:100]}",
    ]
    if os.path.exists(_HISTORY_PATH):
        try:
            with open(_HISTORY_PATH) as f:
                count = sum(1 for _ in f)
            lines.append(f"**History entries**: {count}")
        except Exception:
            pass
    return "\n".join(lines)


def browser_use_clear() -> str:
    global _playwright_instance, _browser_instance, _context_instance, _page_instance
    try:
        if _context_instance is not None:
            _run_async(_context_instance.close())
    except Exception:
        pass
    try:
        # _browser_instance is same as _context_instance with launch_persistent_context,
        # close is idempotent so this is safe
        if _browser_instance is not None and _browser_instance is not _context_instance:
            _run_async(_browser_instance.close())
    except Exception:
        pass
    try:
        if _playwright_instance is not None:
            _run_async(_playwright_instance.__aexit__(None, None, None))
    except Exception:
        pass
    _playwright_instance = None
    _browser_instance = None
    _context_instance = None
    _page_instance = None
    if os.path.exists(_HISTORY_PATH):
        os.remove(_HISTORY_PATH)
    if os.path.exists(_STATE_PATH):
        os.remove(_STATE_PATH)
    return "[OK] Browser closed and history cleared."


def browser_use_reconnect() -> str:
    global _playwright_instance, _browser_instance, _context_instance, _page_instance
    try:
        if _context_instance is not None:
            _run_async(_context_instance.close())
    except Exception:
        pass
    try:
        if _browser_instance is not None and _browser_instance is not _context_instance:
            _run_async(_browser_instance.close())
    except Exception:
        pass
    try:
        if _playwright_instance is not None:
            _run_async(_playwright_instance.__aexit__(None, None, None))
    except Exception:
        pass
    _playwright_instance = None
    _browser_instance = None
    _context_instance = None
    _page_instance = None
    return "[OK] Browser reconnected. Will re-create on next action."
