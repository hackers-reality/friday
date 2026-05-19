from __future__ import annotations

import os
import platform
import socket
import psutil


def _safe_disk_usage() -> float:
    try:
        target = "C:\\" if os.name == "nt" else "/"
        return psutil.disk_usage(target).percent
    except Exception:
        return 0.0


async def handle(action: str, params: dict) -> dict:
    return {
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": _safe_disk_usage(),
        "network_interfaces": list(psutil.net_if_addrs().keys()),
    }
