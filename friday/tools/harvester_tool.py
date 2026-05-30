import asyncio
import subprocess
import json
import re
import os
from typing import Any


HARVESTER_PATH = os.environ.get("HARVESTER_PATH", "theHarvester")


async def run_harvester(domain: str, sources: str = "all") -> dict[str, Any]:
    if not domain or "." not in domain:
        return {"error": "Valid domain required", "domain": domain, "emails": [], "hosts": []}
    result: dict[str, Any] = {"domain": domain, "emails": [], "hosts": [], "ips": []}
    try:
        proc = await asyncio.create_subprocess_exec(
            HARVESTER_PATH, "-d", domain, "-b", sources,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace")
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", output)
        result["emails"] = list(set(emails))
        hosts = re.findall(r"Host:\s*(\S+)", output)
        ips = re.findall(r"IP:\s*(\S+)", output)
        result["hosts"] = list(set(hosts))
        result["ips"] = list(set(ips))
        # Try JSON output
        try:
            proc2 = await asyncio.create_subprocess_exec(
                HARVESTER_PATH, "-d", domain, "-b", sources, "-f", "harvester_output.json",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
            )
            await asyncio.wait_for(proc2.communicate(), timeout=120)
            if os.path.exists("harvester_output.json"):
                with open("harvester_output.json") as f:
                    jdata = json.load(f)
                result["emails"] = list(set(result["emails"] + jdata.get("emails", [])))
                result["hosts"] = list(set(result["hosts"] + jdata.get("hosts", [])))
                os.remove("harvester_output.json")
        except Exception:
            pass
    except FileNotFoundError:
        result["error"] = "theHarvester not installed. Install with: pip install theHarvester"
    except Exception as e:
        result["error"] = str(e)
    return result


async def run_harvester_emails(domain: str) -> dict[str, Any]:
    return await run_harvester(domain, "google,bing,yahoo,linkedin")
