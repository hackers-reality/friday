"""
Naminter OSINT Tool — username enumeration across 500+ sites using WhatsMyName dataset.
Wraps the naminter library for FRIDAY OSINT profiling.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class NaminterProfile:
    site: str
    url: str
    status_code: int = 0
    error: Optional[str] = None


@dataclass
class NaminterResult:
    username: str
    found: list[NaminterProfile] = field(default_factory=list)
    total_checked: int = 0
    found_count: int = 0
    scan_time_s: float = 0.0
    error: Optional[str] = None


async def _ensure_naminter_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import naminter; print(naminter.__version__)",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("naminter not found — attempting pip install naminter ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "naminter",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("naminter install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("naminter install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


async def run_naminter(
    username: str,
    timeout: int = 60,
) -> NaminterResult:
    """
    Search for a username across 500+ sites using the WhatsMyName dataset via naminter.

    Args:
        username: Target username to search for
        timeout: Timeout in seconds for the entire search

    Returns:
        NaminterResult with list of found profiles
    """
    available = await _ensure_naminter_installed()
    if not available:
        return NaminterResult(
            username=username,
            error="naminter not installed and automatic install failed",
        )

    t0 = time.time()
    try:
        from naminter import Naminter

        async with Naminter() as nam:
            raw = await asyncio.wait_for(
                nam.enumerate(username),
                timeout=timeout,
            )

        elapsed = time.time() - t0
        found_profiles = []

        for entry in raw:
            if isinstance(entry, dict) and entry.get("claimed"):
                site_name = entry.get("site", entry.get("name", "unknown"))
                url = entry.get("url", entry.get("uri", ""))
                found_profiles.append(NaminterProfile(
                    site=site_name,
                    url=url,
                    status_code=entry.get("status_code", 200),
                ))

        return NaminterResult(
            username=username,
            found=found_profiles,
            total_checked=len(raw) if isinstance(raw, (list, tuple)) else 0,
            found_count=len(found_profiles),
            scan_time_s=round(elapsed, 2),
        )

    except asyncio.TimeoutError:
        return NaminterResult(
            username=username,
            error=f"Naminter search timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Naminter search failed for %s: %s", username, exc)
        return NaminterResult(
            username=username,
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
