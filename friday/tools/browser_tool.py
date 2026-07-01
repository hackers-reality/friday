"""
Browser-Use integration — autonomous AI-powered browser control.
Wraps the browser-use library for FRIDAY.
Uses a persistent Chrome profile at friday_memory/friday_chrome_profile.

CRITICAL: All temp data (profile copy, downloads, extensions) is redirected
to FRIDAY_MEMORY/friday_temp so it NEVER fills the C drive.

Simple navigation/extraction uses the Playwright bridge (fast, reliable).
Complex autonomous tasks use browser-use Agent (LLM-powered).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging
from friday._paths import FRIDAY_MEMORY

logger = configure_logging(__name__)

_CHROME_PROFILE_DIR = str(Path(FRIDAY_MEMORY) / "friday_chrome_profile")
_FRIDAY_TEMP_DIR = str(Path(FRIDAY_MEMORY) / "friday_temp")

# ── Redirect ALL temp/storage to FRIDAY project dir (never C:) ──
os.makedirs(_FRIDAY_TEMP_DIR, exist_ok=True)
os.environ.setdefault("TMP", _FRIDAY_TEMP_DIR)
os.environ.setdefault("TEMP", _FRIDAY_TEMP_DIR)
os.environ.setdefault("TMPDIR", _FRIDAY_TEMP_DIR)

_ORIG_GETTEMPDIR = tempfile.gettempdir
tempfile.gettempdir = lambda: _FRIDAY_TEMP_DIR  # type: ignore[assignment]

# Monkey-patch BrowserProfile._copy_profile to skip wasteful copy to C:\Temp.
try:
    import browser_use.browser.profile as _bp

    def _patched_copy_profile(self):
        if self.user_data_dir is None:
            return
        if "browser-use-user-data-dir-" in str(self.user_data_dir).lower():
            return
        pass  # Keep original dir — no wasteful copy

    _bp.BrowserProfile._copy_profile = _patched_copy_profile
except ImportError:
    pass


@dataclass
class BrowserActionResult:
    task: str
    success: bool
    summary: str
    steps: int = 0
    model_used: str = ""
    error: Optional[str] = None

    def __bool__(self):
        return self.success


# ── Bridge-based helpers (fast, no LLM) ──

def _bridge_result(data) -> BrowserActionResult:
    """Parse bridge result into BrowserActionResult."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return BrowserActionResult(task="", success="FAIL" not in data, summary=data[:500])
    if isinstance(data, dict):
        summary = data.get("title", data.get("text", data.get("result", "")))
        url = data.get("url", "")
        if summary and url:
            summary = f"{url} — {summary}"
        return BrowserActionResult(
            task="",
            success=not data.get("error"),
            summary=str(summary)[:500],
            error=data.get("error"),
        )
    return BrowserActionResult(task="", success=False, summary=str(data)[:500])


async def browser_navigate(url: str, headless: bool = False) -> BrowserActionResult:
    """Quick navigation via Playwright bridge."""
    from friday.browser_use_bridge import _run_async, _direct_action
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: _run_async(_direct_action("navigate", url=url)))
    return _bridge_result(json.dumps(result))


async def browser_extract_content(url: str, instructions: str = "", headless: bool = False) -> BrowserActionResult:
    """Navigate and extract content via Playwright bridge."""
    from friday.browser_use_bridge import _run_async, _direct_action
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: _run_async(_direct_action("navigate", url=url)))
    text_result = await loop.run_in_executor(None, lambda: _run_async(_direct_action("extract_text")))
    summary = f"Navigated to {result.get('title', url)}\n{text_result.get('text', '')[:500]}"
    return BrowserActionResult(task=url, success=not result.get("error"), summary=summary, error=result.get("error"))


async def browser_search(query: str, engine: str = "google", headless: bool = False) -> BrowserActionResult:
    """Search the web via Playwright bridge."""
    search_urls = {
        "google": "https://www.google.com/search?q={q}",
        "bing": "https://www.bing.com/search?q={q}",
        "duckduckgo": "https://duckduckgo.com/?q={q}",
    }
    from urllib.parse import quote
    url = search_urls.get(engine, search_urls["google"]).format(q=quote(query))
    from friday.browser_use_bridge import _run_async, _direct_action
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: _run_async(_direct_action("navigate", url=url)))
    links_result = await loop.run_in_executor(None, lambda: _run_async(_direct_action("extract_links")))
    summary = f"Searched {engine} for '{query}'\n"
    links = links_result.get("links", [])[:5]
    for lnk in links:
        summary += f"  - {lnk.get('text', lnk.get('href', '?'))}: {lnk.get('href', '')}\n"
    return BrowserActionResult(task=query, success=not result.get("error"), summary=summary, error=result.get("error"))


# ── browser-use Agent (complex multi-step tasks, LLM-powered) ──

_MODULE_LOCK = threading.Lock()
_BROWSER_USE_AVAILABLE: bool | None = None


def _check_browser_use() -> bool:
    global _BROWSER_USE_AVAILABLE
    if _BROWSER_USE_AVAILABLE is None:
        with _MODULE_LOCK:
            if _BROWSER_USE_AVAILABLE is None:
                try:
                    import browser_use  # noqa: F401
                    _BROWSER_USE_AVAILABLE = True
                except ImportError:
                    _BROWSER_USE_AVAILABLE = False
    return _BROWSER_USE_AVAILABLE


async def run_browser_task(
    task: str,
    llm_provider: str = "google",
    llm_model: str = "gemini-2.5-flash-native-audio-preview-12-2025",
    headless: bool = False,
    max_steps: int = 30,
    keep_browser_open: bool = False,
) -> BrowserActionResult:
    """
    Execute an autonomous browser task using browser-use AI agent.
    Requires browser-use, langchain-* LLM packages, and Playwright.
    Falls back to bridge-based simple navigation if browser-use is unavailable.
    """
    if not _check_browser_use():
        logger.info("browser-use not available, falling back to bridge navigate")
        return await browser_navigate(task if task.startswith("http") else f"https://google.com/search?q={task}")

    # Module-level singleton browser for browser-use Agent
    global _persistent_browser
    _persistent_browser_lock = threading.Lock()

    def _get_browser():
        nonlocal _persistent_browser_lock
        global _persistent_browser
        with _persistent_browser_lock:
            if _persistent_browser is not None:
                return _persistent_browser
            from browser_use import Browser
            downloads_dir = str(Path(_FRIDAY_TEMP_DIR) / "downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            try:
                _persistent_browser = Browser(
                    user_data_dir=_CHROME_PROFILE_DIR,
                    headless=headless,
                    keep_alive=True,
                    disable_security=False,
                    downloads_path=downloads_dir,
                )
            except Exception as e:
                logger.warning("browser-use Browser creation failed: %s", e)
                _persistent_browser = Browser(headless=headless, downloads_path=downloads_dir)
            return _persistent_browser

    try:
        from browser_use import Agent

        llm = _build_llm(llm_provider, llm_model)
        if llm is None:
            return BrowserActionResult(
                task=task, success=False, summary="",
                error=f"Unsupported llm_provider: {llm_provider}",
            )

        browser = _get_browser()
        agent = Agent(task=task, llm=llm, browser=browser, max_actions_per_step=1, max_steps=max_steps)
        history = await agent.run(max_steps=max_steps)
        steps = len(history.action_names()) if hasattr(history, "action_names") else 0
        summary = _summarize_result(history)

        return BrowserActionResult(
            task=task, success=True, summary=summary, steps=steps,
            model_used=f"{llm_provider}/{llm_model}",
        )
    except Exception as exc:
        logger.exception("browser-use task failed: %s", exc)
        return BrowserActionResult(task=task, success=False, summary="", error=str(exc))


async def close_browser():
    """Close the persistent browser-use Agent browser instance."""
    global _persistent_browser
    if _persistent_browser is not None:
        try:
            await _persistent_browser.close()
        except Exception:
            pass
        _persistent_browser = None
        logger.info("Persistent browser closed")


# ── LLM builder for browser-use Agent ──

def _build_llm(provider: str, model: str):
    """Build the LLM instance for browser-use based on provider."""
    def _fix_llm(llm, provider_name, model_name):
        object.__setattr__(llm, "provider", provider_name)
        object.__setattr__(llm, "model_name", model_name)
        object.__setattr__(llm, "model", model_name)
        return llm

    if provider == "builtin":
        from browser_use import ChatBrowserUse
        return ChatBrowserUse(model=model if model != "gemini-2.5-flash-native-audio-preview-12-2025" else None)
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return _fix_llm(ChatGoogleGenerativeAI(model=model, api_key=api_key), "google", model)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        return _fix_llm(ChatOpenAI(model=model, api_key=api_key), "openai", model)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return _fix_llm(ChatAnthropic(model=model, api_key=api_key), "anthropic", model)
    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        return _fix_llm(ChatOpenAI(model=model or "deepseek-chat", api_key=api_key, base_url="https://api.deepseek.com"), "deepseek", model or "deepseek-chat")
    return None


def _summarize_result(history) -> str:
    """Extract a readable summary from browser-use history."""
    try:
        urls = []
        actions = []
        if hasattr(history, "urls"):
            urls = history.urls()
        if hasattr(history, "action_names"):
            actions = history.action_names()

        parts = []
        if urls:
            parts.append(f"Visited {len(urls)} page(s)")
            if len(urls) <= 5:
                for u in urls:
                    parts.append(f"  - {u}")
        if actions:
            parts.append(f"Performed {len(actions)} action(s)")

        final_result = history.final_result() if hasattr(history, "final_result") else None
        if final_result:
            parts.append(f"Result: {str(final_result)[:500]}")

        return "\n".join(parts) if parts else "Task completed (no details available)"
    except Exception:
        return "Task completed (summary unavailable)"


_persistent_browser = None
_persistent_browser_lock = threading.Lock()
