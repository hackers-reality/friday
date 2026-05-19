"""System info capability for sidecar client."""
from __future__ import annotations

import os
import psutil
from typing import Dict


class SystemInfoHandler:
    async def handle(self, action: str, params: Dict) -> Dict:
        return {
            "platform": os.name,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "hostname": os.uname().nodename if hasattr(os, "uname") else os.getenv("COMPUTERNAME"),
        }
