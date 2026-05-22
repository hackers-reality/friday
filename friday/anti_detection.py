"""
FRIDAY Anti-Detection — stealth patches to avoid bot detection on web pages.
Applied to every page created by browser_manager.

Patches:
  - Remove navigator.webdriver flag via CDP
  - Randomize viewport dimensions
  - Human-like mouse movement (intermediate points)
  - Random delays between actions
  - Realistic user agent matching installed Chrome version
"""

from __future__ import annotations

import asyncio
import random
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 720},
]

_ACTION_DELAY_MIN = 0.3
_ACTION_DELAY_MAX = 1.2


def random_viewport() -> dict:
    return random.choice(_VIEWPORTS)


async def random_delay(min_s: float = _ACTION_DELAY_MIN, max_s: float = _ACTION_DELAY_MAX):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def apply_stealth(page) -> None:
    """Apply all stealth patches to a page."""
    try:
        # Remove webdriver flag via CDP
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
    except Exception as exc:
        logger.debug("Stealth init script failed: %s", exc)

    # Randomize viewport
    vp = random_viewport()
    try:
        await page.set_viewport_size(vp)
    except Exception:
        pass


async def human_like_click(page, selector: str, **kwargs):
    """Click an element with human-like mouse movement."""
    await random_delay()
    try:
        el = await page.query_selector(selector)
        if not el:
            # Try text-based fallback
            el = await page.get_by_text(kwargs.get("text", ""), exact=True).first.element_handle()
            if not el:
                return False

        box = await el.bounding_box()
        if box:
            # Move mouse in small steps to element
            start_x, start_y = random.randint(0, 500), random.randint(0, 500)
            end_x = box["x"] + box["width"] / 2
            end_y = box["y"] + box["height"] / 2
            steps = random.randint(4, 8)
            for i in range(1, steps + 1):
                curr_x = start_x + (end_x - start_x) * (i / steps) + random.randint(-3, 3)
                curr_y = start_y + (end_y - start_y) * (i / steps) + random.randint(-3, 3)
                await page.mouse.move(curr_x, curr_y)
                await asyncio.sleep(random.uniform(0.02, 0.08))

        await el.click(**kwargs)
        await random_delay()
        return True
    except Exception as exc:
        logger.debug("Human-like click failed: %s", exc)
        return False


async def human_like_type(page, selector: str, text: str, clear_first: bool = True):
    """Type text with realistic keystroke timing."""
    await random_delay()
    try:
        el = await page.query_selector(selector)
        if not el:
            return False

        await el.click()
        if clear_first:
            await el.fill("")
            await asyncio.sleep(random.uniform(0.1, 0.3))

        # Type character by character with random delays
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.03, 0.15))
        await random_delay()
        return True
    except Exception as exc:
        logger.debug("Human-like type failed: %s", exc)
        return False
