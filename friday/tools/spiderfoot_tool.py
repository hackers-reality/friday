"""
SpiderFoot OSINT Tool — automated recon via SpiderFoot REST API.

Manages SpiderFoot subprocess lifecycle, starts scans, polls results,
and feeds entities into the knowledge graph.

Optional dependency: if SpiderFoot not installed, logs warning and returns
empty results. Other OSINT tools still work.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Optional

from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)

try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class SpiderFootEntity:
    """A discovered entity from a SpiderFoot scan."""
    name: str
    entity_type: str  # IP_ADDRESS, DOMAIN_NAME, EMAIL_ADDR, etc.
    data: str
    source_module: str = ""
    confidence: int = 0


@dataclass
class SpiderFootThreat:
    """A threat/intel finding."""
    entity: str
    threat_type: str  # MALICIOUS_IPADDR, LEAKSITE_URL, etc.
    description: str = ""
    source: str = ""


@dataclass
class SpiderFootResult:
    target: str
    scan_id: str = ""
    entities: list[SpiderFootEntity] = field(default_factory=list)
    threats: list[SpiderFootThreat] = field(default_factory=list)
    scan_duration_s: float = 0.0
    timed_out: bool = False
    error: str = ""


# Module lists per scan type
_SCAN_MODULES = {
    "ip_scan": [
        "sfp_portscan_tcp", "sfp_shodan", "sfp_virustotal",
        "sfp_torexits", "sfp_torserver", "sfp_riskiq",
    ],
    "domain_scan": [
        "sfp_dns", "sfp_whois", "sfp_ssl", "sfp_webserver",
        "sfp_emailformat", "sfp_hunter",
    ],
    "email_scan": [
        "sfp_hunter", "sfp_haveibeenpwned", "sfp_leakcheck",
        "sfp_email", "sfp_socialmedia",
    ],
}

_THREAT_TYPES = {"MALICIOUS_IPADDR", "LEAKSITE_URL", "TOR_EXIT_NODE",
                 "MALWARE_DOMAIN", "PHISHING_URL"}


async def _check_spiderfoot() -> bool:
    """Check if SpiderFoot is available by pinging API."""
    if httpx is None:
        return False
    cfg = ensure_config()
    api_base = cfg.get("osint", {}).get("spiderfoot_api", "http://127.0.0.1:5002")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{api_base}/api/v1/ping")
            return r.status_code == 200
    except Exception:
        return False


async def _start_spiderfoot() -> bool:
    """Attempt to start SpiderFoot as subprocess."""
    cfg = ensure_config()
    sf_dir = cfg.get("osint", {}).get("spiderfoot_dir", "")
    if not sf_dir or not os.path.isdir(sf_dir):
        logger.warning("SpiderFoot directory not configured. Set osint.spiderfoot_dir in config.yaml")
        return False

    sf_py = os.path.join(sf_dir, "sf.py")
    if not os.path.exists(sf_py):
        logger.warning("sf.py not found at %s", sf_py)
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", sf_py, "-l", "127.0.0.1:5002",
            cwd=sf_dir,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        # Give it time to start
        for _ in range(30):
            await asyncio.sleep(1)
            if await _check_spiderfoot():
                logger.info("SpiderFoot started successfully on 127.0.0.1:5002")
                return True
        logger.warning("SpiderFoot process started but API not responding")
        return False
    except Exception as exc:
        logger.warning("Failed to start SpiderFoot: %s", exc)
        return False


async def run_spiderfoot(
    target: str,
    scan_type: str = "ip_scan",
    timeout: int = 300,
) -> SpiderFootResult:
    """
    Run a SpiderFoot scan against a target.

    Args:
        target: IP address, domain, or email
        scan_type: ip_scan | domain_scan | email_scan
        timeout: max time to wait for scan results (seconds)

    Returns:
        SpiderFootResult with entities and threats
    """
    result = SpiderFootResult(target=target)

    if httpx is None:
        result.error = "httpx not available. Install: pip install httpx"
        return result

    # Check or start SpiderFoot
    available = await _check_spiderfoot()
    if not available:
        logger.info("SpiderFoot not running — attempting to start")
        available = await _start_spiderfoot()

    if not available:
        result.error = "SpiderFoot unavailable. Install from https://github.com/smicallef/spiderfoot"
        logger.warning(result.error)
        return result

    cfg = ensure_config()
    api_base = cfg.get("osint", {}).get("spiderfoot_api", "http://127.0.0.1:5002")
    modules = _SCAN_MODULES.get(scan_type, _SCAN_MODULES["ip_scan"])

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=10, base_url=api_base) as client:
            # 1. Create scan
            scan_name = f"friday_osint_{target}_{int(t0)}"
            r = await client.post("/api/v1/scan/new", json={
                "scanname": scan_name,
                "scantarget": target,
                "typelist": "ALL",
                "modulelist": modules,
            })
            if r.status_code != 200:
                result.error = f"Scan creation failed: HTTP {r.status_code}"
                return result

            scan_data = r.json()
            scan_id = scan_data.get("scan_name") or scan_data.get("scanid")
            if not scan_id:
                result.error = f"Unexpected scan response: {scan_data}"
                return result
            result.scan_id = scan_id

            # 2. Poll results
            poll_interval = 10
            max_polls = timeout // poll_interval
            for _ in range(max_polls):
                await asyncio.sleep(poll_interval)
                r = await client.get(f"/api/v1/scan/{urllib.parse.quote(scan_id, safe='')}/results")
                if r.status_code == 404:
                    continue
                if r.status_code != 200:
                    continue

                data = r.json()
                scan_complete = data.get("status") == "FINISHED" or data.get("scanComplete", False)
                rows = data.get("rows", data.get("results", data.get("data", [])))

                for row in rows:
                    row_type = (row.get("type") or row.get("data_type") or "").upper()
                    row_data = row.get("data", row.get("value", json.dumps(row)))
                    module = row.get("module", row.get("sourceModule", ""))
                    confidence = int(row.get("confidence", row.get("confidenceScore", 50)))

                    # Classify as threat or entity
                    if row_type in _THREAT_TYPES:
                        result.threats.append(SpiderFootThreat(
                            entity=str(row_data)[:200],
                            threat_type=row_type,
                            description=str(row.get("description", row.get("name", "")))[:300],
                            source=module,
                        ))
                    elif row_type and row_data:
                        result.entities.append(SpiderFootEntity(
                            name=str(row_data)[:200],
                            entity_type=row_type,
                            data=str(row_data)[:500],
                            source_module=module,
                            confidence=confidence,
                        ))

                if scan_complete:
                    break
            else:
                result.timed_out = True
                logger.warning("SpiderFoot scan %s timed out after %ds", scan_id, timeout)

            result.scan_duration_s = round(time.time() - t0, 2)
            logger.info("SpiderFoot %s: %d entities, %d threats in %.1fs (timeout=%s)",
                        target, len(result.entities), len(result.threats),
                        result.scan_duration_s, result.timed_out)

    except httpx.RequestError as exc:
        result.error = f"SpiderFoot API error: {exc}"
        logger.warning(result.error)
    except Exception as exc:
        result.error = str(exc)
        logger.exception("SpiderFoot run failed: %s", exc)

    return result
