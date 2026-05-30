"""
Holehe OSINT Tool — check if an email is registered on 120+ online services.
Wraps the holehe Python library for FRIDAY OSINT profiling.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class HoleheServiceResult:
    name: str
    registered: bool
    rate_limit: bool = False
    error: Optional[str] = None


@dataclass
class HoleheResult:
    email: str
    services: list[HoleheServiceResult] = field(default_factory=list)
    total_checked: int = 0
    registered_count: int = 0
    scan_time_s: float = 0.0
    error: Optional[str] = None


async def _ensure_holehe_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import holehe; print(holehe.__version__)",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("holehe not found — attempting pip install holehe ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "holehe",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("holehe install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("holehe install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


def _import_holehe_modules():
    """Dynamically import all holehe check modules."""
    import importlib
    import pkgutil
    import holehe.modules as modules_pkg
    mods = []
    for importer, modname, ispkg in pkgutil.walk_packages(modules_pkg.__path__, prefix="holehe.modules."):
        if not ispkg:
            try:
                mod = importlib.import_module(modname)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if callable(attr) and attr_name != "import_module":
                        mods.append((modname.split(".")[-1], attr))
                        break
            except Exception:
                pass
    return mods


async def run_holehe(
    email: str,
    services: Optional[list[str]] = None,
    timeout: int = 60,
) -> HoleheResult:
    """
    Check if an email is registered on 120+ online services using holehe.

    Args:
        email: Target email address to check
        services: Only check specific services (e.g. ["instagram", "snapchat"])
        timeout: Timeout in seconds for the entire check

    Returns:
        HoleheResult with list of service results
    """
    available = await _ensure_holehe_installed()
    if not available:
        return HoleheResult(
            email=email,
            error="holehe not installed and automatic install failed",
        )

    t0 = time.time()
    try:
        import httpx

        check_modules = _import_holehe_modules()
        if services:
            check_modules = [(n, f) for n, f in check_modules if n in services]

        if not check_modules:
            return HoleheResult(
                email=email,
                error="No matching service modules found",
            )

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for name, check_func in check_modules:
                out = []
                try:
                    await asyncio.wait_for(
                        check_func(email, client, out),
                        timeout=timeout / max(len(check_modules), 1),
                    )
                except asyncio.TimeoutError:
                    out.append({"name": name, "rateLimit": True, "exists": False})
                except Exception as e:
                    out.append({"name": name, "error": str(e), "exists": False})

                for entry in out:
                    sr = HoleheServiceResult(
                        name=entry.get("name", name),
                        registered=entry.get("exists", False),
                        rate_limit=entry.get("rateLimit", False),
                        error=entry.get("error"),
                    )
                    results.append(sr)

        elapsed = time.time() - t0
        return HoleheResult(
            email=email,
            services=results,
            total_checked=len(results),
            registered_count=sum(1 for r in results if r.registered),
            scan_time_s=round(elapsed, 2),
        )

    except asyncio.TimeoutError:
        return HoleheResult(
            email=email,
            error=f"Holehe check timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Holehe check failed for %s: %s", email, exc)
        return HoleheResult(
            email=email,
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
