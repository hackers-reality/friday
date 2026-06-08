"""
Sherlock OSINT Tool — username lookup across 300+ platforms.
Runs sherlock-project/sherlock as subprocess, parses output.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_FOUND_RE = re.compile(r"\[\+\]\s+(.+?):\s+(https?://\S+)")
_NOT_FOUND_RE = re.compile(r"\[\-\]\s+(.+?):\s+Not Found")


@dataclass
class FoundProfile:
    platform: str
    url: str


@dataclass
class SherlockResult:
    username: str
    found: list[FoundProfile] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    scan_time_s: float = 0.0
    timed_out: bool = False


async def _ensure_sherlock_installed() -> bool:
    """Install sherlock if missing. Returns True if available after attempt."""
    try:
        for mod in ("sherlock", "sherlock_project"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", mod, "--help",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=10)
                if proc.returncode == 0:
                    return True
            except Exception:
                pass
    except Exception:
        pass

    logger.info("Sherlock not found — attempting pip install sherlock-project ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "sherlock-project",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            logger.warning("Sherlock install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("Sherlock install exception: %s", exc)
        return False


async def run_sherlock(
    username: str,
    platforms: Optional[list[str]] = None,
    timeout: int = 120,
) -> SherlockResult:
    """
    Run Sherlock username lookup. Returns structured result.

    Args:
        username: target username
        platforms: optional list of platform names to restrict search
        timeout: hard timeout in seconds (default 120)

    Returns:
        SherlockResult with found profiles, not-found platforms, scan time.
    """
    available = await _ensure_sherlock_installed()
    if not available:
        logger.error("Sherlock not installed and install failed")
        return SherlockResult(username=username, scan_time_s=0.0)

    tmp = Path(tempfile.mkdtemp(prefix="sherlock_"))
    output_path = tmp / f"{username}.txt"

    try:
        sherlock_mod = "sherlock_project"  # pip installs as sherlock_project, not sherlock
        cmd = [sys.executable, "-m", sherlock_mod, username, "--output", str(output_path), "--timeout", "10"]
        if platforms:
            cmd.extend(["--sites", ",".join(platforms)])
        # --unique-output only if sherlock version supports it — skip for compat

        t0 = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            timed_out = False
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            timed_out = True
            logger.warning("Sherlock timed out after %ds for %s", timeout, username)

        elapsed = time.time() - t0
        result = SherlockResult(username=username, scan_time_s=round(elapsed, 2), timed_out=timed_out)

        # Parse output file
        if output_path.exists():
            text = output_path.read_text(encoding="utf-8", errors="replace")
            for m in _FOUND_RE.finditer(text):
                result.found.append(FoundProfile(platform=m.group(1), url=m.group(2)))
            for m in _NOT_FOUND_RE.finditer(text):
                result.not_found.append(m.group(1))

        if not result.found and not timed_out:
            # Fallback: try parsing stdout
            stdout = (proc.stdout or b"").decode(errors="replace")
            for m in _FOUND_RE.finditer(stdout):
                result.found.append(FoundProfile(platform=m.group(1), url=m.group(2)))
            for m in _NOT_FOUND_RE.finditer(stdout):
                result.not_found.append(m.group(1))

        logger.info("Sherlock %s: %d found, %d not found in %.1fs",
                     username, len(result.found), len(result.not_found), elapsed)
        return result

    except Exception as exc:
        logger.exception("Sherlock run failed: %s", exc)
        return SherlockResult(username=username, scan_time_s=0.0, found=[])
    finally:
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
