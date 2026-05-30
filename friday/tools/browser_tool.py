"""
Browser-Use integration — autonomous AI-powered browser control.
Wraps the browser-use library (97k+ stars) for FRIDAY.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class BrowserActionResult:
    task: str
    success: bool
    summary: str
    steps: int = 0
    model_used: str = ""
    error: Optional[str] = None


async def _ensure_browser_use_installed() -> bool:
    """Install browser-use if missing. Returns True if available after attempt."""
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import browser_use; print(browser_use.__version__)",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    logger.info("browser-use not found — attempting pip install browser-use ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "browser-use",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("browser-use install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("browser-use install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


async def run_browser_task(
    task: str,
    llm_provider: str = "google",
    llm_model: str = "gemini-3.1-flash-live-preview",
    headless: bool = False,
    max_steps: int = 30,
    keep_browser_open: bool = False,
) -> BrowserActionResult:
    """
    Execute an autonomous browser task using browser-use AI agent.

    Args:
        task: Natural language description of what to do in the browser
        llm_provider: LLM provider: google, openai, anthropic, or builtin (browser-use's own model)
        llm_model: Model name (e.g. gemini-3.1-flash-live-preview, gpt-4o, claude-sonnet-4-20250514)
        headless: Run browser in headless mode (no visible window)
        max_steps: Maximum number of browser action steps before stopping
        keep_browser_open: Keep the browser instance alive after task (for debugging)

    Returns:
        BrowserActionResult with success status, summary, and step count
    """
    available = await _ensure_browser_use_installed()
    if not available:
        return BrowserActionResult(
            task=task, success=False, summary="",
            error="browser-use not installed and automatic install failed",
        )

    try:
        from browser_use import Agent, Browser, BrowserConfig

        llm = _build_llm(llm_provider, llm_model)
        if llm is None:
            return BrowserActionResult(
                task=task, success=False, summary="",
                error=f"Unsupported llm_provider: {llm_provider}. Use: google, openai, anthropic, builtin",
            )

        browser = None
        if not headless:
            browser = Browser(
                config=BrowserConfig(
                    headless=False,
                    keep_alive=keep_browser_open,
                )
            )

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            max_actions_per_step=1,
            max_steps=max_steps,
        )

        history = await agent.run(max_steps=max_steps)

        steps = len(history.action_names()) if hasattr(history, "action_names") else 0
        summary = _summarize_result(history)

        return BrowserActionResult(
            task=task,
            success=True,
            summary=summary,
            steps=steps,
            model_used=f"{llm_provider}/{llm_model}",
        )

    except Exception as exc:
        logger.exception("browser-use task failed: %s", exc)
        return BrowserActionResult(
            task=task, success=False, summary="",
            error=str(exc),
        )


def _build_llm(provider: str, model: str):
    """Build the LLM instance for browser-use based on provider."""
    if provider == "builtin":
        from browser_use import ChatBrowserUse
        return ChatBrowserUse(model=model if model != "gemini-3.1-flash-live-preview" else None)
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model=model, api_key=api_key)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(model=model, api_key=api_key)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return ChatAnthropic(model=model, api_key=api_key)
    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        return ChatOpenAI(model=model or "deepseek-chat", api_key=api_key, base_url="https://api.deepseek.com")
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


async def browser_navigate(url: str, headless: bool = False) -> BrowserActionResult:
    """Quick navigation: go to a URL and return page info."""
    return await run_browser_task(
        task=f"Navigate to {url} and tell me the page title, main heading, and a brief summary of what the page is about.",
        headless=headless,
        max_steps=5,
    )


async def browser_extract_content(url: str, instructions: str = "") -> BrowserActionResult:
    """Navigate to a URL and extract specific content from it."""
    task = f"Go to {url}. {instructions}".strip()
    return await run_browser_task(task=task, headless=True, max_steps=10)


async def browser_search(query: str, engine: str = "google") -> BrowserActionResult:
    """Search the web and return top results with snippets."""
    urls = {
        "google": "https://www.google.com",
        "bing": "https://www.bing.com",
        "duckduckgo": "https://duckduckgo.com",
    }
    url = urls.get(engine, urls["google"])
    return await run_browser_task(
        task=f"Go to {url}, search for '{query}', and return the top 5 results with their titles and snippets.",
        headless=True,
        max_steps=10,
    )
