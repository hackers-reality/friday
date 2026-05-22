"""
FRIDAY Browser Tools — async browser action functions called by orchestrator
and browser_agent. All return structured results with optional screenshots.

Each function takes an optional 'page' parameter (from browser_manager).
If not provided, uses the active page from the singleton BrowserManager.

Functions: navigate, click, type_text, extract_text, extract_links,
scroll, wait_for, get_cookies, fill_form, run_js, screenshot.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from typing import Any, Optional
from urllib.parse import urlparse

from friday.anti_detection import human_like_click, human_like_type, random_delay, apply_stealth
from friday.browser_manager import BrowserManager
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


def _get_bm() -> BrowserManager:
    return BrowserManager.get_instance()


async def _ensure_page():
    bm = _get_bm()
    if not bm._started:
        await bm.start()
    return await bm.get_page()


# ── Actions ─────────────────────────────────────────────────

async def navigate(url: str, timeout_ms: int = 30000) -> dict:
    """
    Navigate to a URL. Waits for networkidle.
    Returns {title, url, status_code, screenshot_b64}.
    """
    page = await _ensure_page()
    bm = _get_bm()
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        status = resp.status if resp else 0
        await random_delay()
        ss = await bm.screenshot(page)
        return {
            "title": await page.title(),
            "url": page.url,
            "status_code": status,
            "ok": 200 <= status < 400 if status else False,
            "screenshot_b64": ss,
        }
    except Exception as exc:
        return {"title": "", "url": url, "status_code": 0, "ok": False, "error": str(exc)}


async def click(selector: str = "", text: str = "") -> dict:
    """
    Click element by CSS selector OR visible text match.
    Returns {success, screenshot_b64}.
    """
    page = await _ensure_page()
    bm = _get_bm()
    try:
        if selector:
            ok = await human_like_click(page, selector)
        elif text:
            try:
                el = page.get_by_text(text, exact=True).first
                await el.wait_for(timeout=5000)
                await el.click()
                await random_delay()
                ok = True
            except Exception:
                # Try partial text
                try:
                    el = page.get_by_text(text).first
                    await el.wait_for(timeout=3000)
                    await el.click()
                    await random_delay()
                    ok = True
                except Exception:
                    ok = False
        else:
            return {"success": False, "error": "No selector or text provided"}
        ss = await bm.screenshot(page)
        return {"success": ok, "screenshot_b64": ss}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def type_text(selector: str, text: str, clear_first: bool = True) -> dict:
    """
    Type into input field with human-like keystrokes.
    Returns {success}.
    """
    page = await _ensure_page()
    try:
        ok = await human_like_type(page, selector, text, clear_first)
        return {"success": ok}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def extract_text(selector: str = "") -> dict:
    """
    Extract visible text from page or specific element.
    Returns {text, full_page_text, truncated}.
    """
    page = await _ensure_page()
    try:
        if selector:
            el = await page.query_selector(selector)
            text = await el.inner_text() if el else ""
        else:
            text = await page.inner_text("body")

        truncated = len(text) > 50000
        return {"text": text[:50000], "full_page_text": text[:50000], "truncated": truncated}
    except Exception as exc:
        return {"text": "", "full_page_text": "", "error": str(exc)}


async def extract_links() -> dict:
    """
    Extract all links from current page.
    Returns {links: [{text, href, is_external}], count}.
    """
    page = await _ensure_page()
    try:
        current_domain = urlparse(page.url).netloc
        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.innerText.trim().slice(0, 100),
                href: a.href,
            }))
        """)
        enriched = []
        for link in links:
            if not link.get("href"):
                continue
            try:
                link_domain = urlparse(link["href"]).netloc
                is_ext = link_domain and link_domain != current_domain
            except Exception:
                is_ext = False
            enriched.append({
                "text": link.get("text", ""),
                "href": link["href"],
                "is_external": is_ext,
            })

        return {"links": enriched[:200], "count": len(enriched)}
    except Exception as exc:
        return {"links": [], "count": 0, "error": str(exc)}


async def scroll(direction: str = "down", amount: int = 500) -> dict:
    """
    Scroll page. direction: down, up, to_bottom.
    Returns {success}.
    """
    page = await _ensure_page()
    try:
        if direction == "to_bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "down":
            await page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await page.evaluate(f"window.scrollBy(0, -{abs(amount)})")
        await random_delay()
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def wait_for(selector: str, timeout_ms: int = 5000) -> dict:
    """
    Wait for element to appear.
    Returns {found, screenshot_b64}.
    """
    page = await _ensure_page()
    bm = _get_bm()
    try:
        await page.wait_for_selector(selector, timeout=timeout_ms)
        ss = await bm.screenshot(page)
        return {"found": True, "screenshot_b64": ss}
    except Exception:
        ss = await bm.screenshot(page)
        return {"found": False, "screenshot_b64": ss}


async def get_cookies() -> dict:
    """
    Get cookies for current domain.
    Returns {cookies: [{name, value, domain, path, expires}], count}.
    """
    page = await _ensure_page()
    try:
        ctx = page.context
        cookies = await ctx.cookies()
        enriched = []
        for c in cookies:
            enriched.append({
                "name": c.get("name", ""),
                "value": c.get("value", "")[:40],
                "domain": c.get("domain", ""),
                "path": c.get("path", ""),
                "expires": c.get("expires", 0),
            })
        return {"cookies": enriched, "count": len(enriched)}
    except Exception as exc:
        return {"cookies": [], "count": 0, "error": str(exc)}


async def fill_form(fields: dict[str, str], submit_selector: str = "") -> dict:
    """
    Fill multiple form fields + optionally click submit button.
    Returns {success, screenshot_b64}.
    """
    page = await _ensure_page()
    bm = _get_bm()
    try:
        for selector, value in fields.items():
            if selector == "submit":
                continue
            await human_like_type(page, selector, value)
            await random_delay(0.2, 0.5)

        if submit_selector:
            await human_like_click(page, submit_selector)
        elif "submit" in fields:
            await page.keyboard.press("Enter")
            await random_delay()

        ss = await bm.screenshot(page)
        return {"success": True, "screenshot_b64": ss}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def run_js(script: str) -> dict:
    """
    Execute arbitrary JavaScript in page context.
    Returns {result, error}.
    """
    page = await _ensure_page()
    try:
        result = await page.evaluate(script)
        return {"result": str(result)[:5000]}
    except Exception as exc:
        return {"error": str(exc)}


async def take_screenshot() -> dict:
    """
    Take a screenshot of the current page.
    Returns {screenshot_b64}.
    """
    bm = _get_bm()
    page = await _ensure_page()
    ss = await bm.screenshot(page)
    return {"screenshot_b64": ss}


# ── Tool Entry Point (for legacy Friday tool pattern) ──────

_BROWSER_TOOL_ACTIONS = {
    "navigate": navigate,
    "click": click,
    "type_text": type_text,
    "extract_text": extract_text,
    "extract_links": extract_links,
    "scroll": scroll,
    "wait_for": wait_for,
    "get_cookies": get_cookies,
    "fill_form": fill_form,
    "run_js": run_js,
    "screenshot": take_screenshot,
}


async def browser_tool(action: str = "status", **kwargs) -> dict | str:
    """
    Friday tool for browser automation.
    Actions: navigate, click, type_text, extract_text, extract_links,
             scroll, wait_for, get_cookies, fill_form, run_js, screenshot, status
    """
    if action == "status":
        bm = _get_bm()
        st = bm.status()
        lines = ["### BROWSER STATUS", ""]
        lines.append(f"Running: {st['running']}")
        lines.append(f"Active session: {st['active_session']}")
        lines.append(f"Sessions: {', '.join(st['sessions']) or 'none'}")
        return "\n".join(lines)

    fn = _BROWSER_TOOL_ACTIONS.get(action)
    if not fn:
        return {"error": f"Unknown action: {action}. Available: {list(_BROWSER_TOOL_ACTIONS.keys())}"}

    result = await fn(**kwargs)
    return result
