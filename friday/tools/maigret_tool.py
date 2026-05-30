"""
Maigret OSINT Tool — username search across 3000+ platforms.
Wraps the maigret Python library for FRIDAY OSINT profiling.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class MaigretProfile:
    platform: str
    url: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None
    follower_count: Optional[int] = None


@dataclass
class MaigretResult:
    username: str
    found: list[MaigretProfile] = field(default_factory=list)
    total_checked: int = 0
    scan_time_s: float = 0.0
    error: Optional[str] = None


async def _ensure_maigret_installed() -> bool:
    """Install maigret if missing. Returns True if available after attempt."""
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import maigret; print(maigret.__version__)",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    logger.info("maigret not found — attempting pip install maigret ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "maigret",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("maigret install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("maigret install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


async def run_maigret(
    username: str,
    top: int = 500,
    tags: Optional[list[str]] = None,
    exclude_tags: Optional[list[str]] = None,
    timeout: int = 60,
    parse_profiles: bool = True,
) -> MaigretResult:
    """
    Search for a username across thousands of platforms using maigret.

    Args:
        username: Target username to search for
        top: Number of top sites to check by traffic rank (default 500, max ~3000)
        tags: Only check sites with these tags (e.g. ["coding", "social"])
        exclude_tags: Exclude sites with these tags (e.g. ["nsfw", "dating"])
        timeout: Timeout in seconds for the entire search
        parse_profiles: Extract profile details (name, bio, location) when found

    Returns:
        MaigretResult with list of found profiles and scan metadata
    """
    available = await _ensure_maigret_installed()
    if not available:
        return MaigretResult(
            username=username,
            error="maigret not installed and automatic install failed",
        )

    t0 = time.time()
    try:
        from maigret import search as maigret_search
        from maigret.sites import MaigretDatabase

        db = MaigretDatabase()
        db.load_from_path(None)

        kwargs = dict(top=top)
        if tags:
            kwargs["tags"] = tags
        if exclude_tags:
            kwargs["excluded_tags"] = exclude_tags
        sites = db.ranked_sites_dict(**kwargs)

        if not sites:
            return MaigretResult(
                username=username,
                error="No sites matched the given tag filters",
            )

        _logger = logging.getLogger("maigret")
        _logger.setLevel(logging.WARNING)

        results = await asyncio.wait_for(
            maigret_search(
                username=username,
                site_dict=sites,
                logger=_logger,
                timeout=30,
                is_parsing_enabled=parse_profiles,
            ),
            timeout=timeout,
        )

        elapsed = time.time() - t0
        found_profiles = []

        for site_name, result in sorted(results.items()):
            status = result.get("status")
            if status and hasattr(status, "is_found") and status.is_found():
                profile = MaigretProfile(
                    platform=site_name,
                    url=result.get("url_user", ""),
                )
                ids_data = result.get("ids_data", {}) or {}
                if ids_data:
                    profile.name = ids_data.get("fullname") or ids_data.get("name")
                    profile.bio = ids_data.get("bio")
                    profile.location = ids_data.get("location")
                    profile.image = ids_data.get("image")
                    try:
                        profile.follower_count = int(ids_data["follower_count"]) if ids_data.get("follower_count") else None
                    except (ValueError, TypeError):
                        pass
                found_profiles.append(profile)

        return MaigretResult(
            username=username,
            found=found_profiles,
            total_checked=len(sites),
            scan_time_s=round(elapsed, 2),
        )

    except asyncio.TimeoutError:
        return MaigretResult(
            username=username,
            error=f"Maigret search timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Maigret search failed for %s: %s", username, exc)
        return MaigretResult(
            username=username,
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
