"""
Wappalyzer OSINT Tool — web technology stack detection.
Wraps the python-wappalyzer library for FRIDAY OSINT profiling.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class WappalyzerTech:
    name: str
    version: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    confidence: int = 100


@dataclass
class WappalyzerResult:
    url: str
    technologies: list[WappalyzerTech] = field(default_factory=list)
    tech_count: int = 0
    scan_time_s: float = 0.0
    error: Optional[str] = None


async def _ensure_wappalyzer_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import wappalyzer; print('ok')",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    logger.info("python-wappalyzer not found — attempting pip install ...")
    for pkg in ("wappalyzer", "python-wappalyzer"):
        try:
            proc = await asyncio.create_subprocess_exec(
                _python(), "-m", "pip", "install", pkg,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _python() -> str:
    import sys
    return sys.executable


async def detect_technologies(
    url: str,
    timeout: int = 30,
) -> WappalyzerResult:
    """
    Detect web technologies used by a website using Wappalyzer.

    Args:
        url: Website URL to analyze
        timeout: Timeout in seconds

    Returns:
        WappalyzerResult with detected technologies
    """
    available = await _ensure_wappalyzer_installed()
    if not available:
        return WappalyzerResult(
            url=url,
            error="python-wappalyzer not installed and automatic install failed",
        )

    t0 = time.time()
    try:
        from wappalyzer import Wappalyzer, WebPage

        wapp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: Wappalyzer.latest()
        )

        webpage = await asyncio.get_event_loop().run_in_executor(
            None, lambda: WebPage.new_from_url(url)
        )

        raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: wapp.analyze(webpage)
        )

        if isinstance(raw, set):
            raw_list = [{"name": t, "categories": [], "version": None} for t in raw]
        elif isinstance(raw, dict):
            raw_list = []
            for name, info in raw.items():
                if isinstance(info, dict):
                    raw_list.append({
                        "name": name,
                        "categories": info.get("categories", []),
                        "version": info.get("version"),
                        "confidence": info.get("confidence", 100),
                    })
                else:
                    raw_list.append({"name": name, "categories": [], "version": str(info) if info else None})
        else:
            raw_list = [{"name": str(t), "categories": []} for t in (raw or [])]

        technologies = []
        for item in raw_list:
            wpt = WappalyzerTech(
                name=item["name"],
                version=item.get("version"),
                categories=item.get("categories", []) if isinstance(item.get("categories"), list) else [str(item.get("categories", ""))],
                confidence=item.get("confidence", 100),
            )
            technologies.append(wpt)

        return WappalyzerResult(
            url=url,
            technologies=technologies,
            tech_count=len(technologies),
            scan_time_s=round(time.time() - t0, 2),
        )

    except asyncio.TimeoutError:
        return WappalyzerResult(
            url=url,
            error=f"Wappalyzer detection timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Wappalyzer detection failed for %s: %s", url, exc)
        return WappalyzerResult(
            url=url,
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
