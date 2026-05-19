"""Terminal capability for sidecar client."""
from __future__ import annotations

import subprocess
from typing import Dict


class TerminalHandler:
    async def handle(self, action: str, params: Dict) -> Dict:
        cmd = params.get("cmd")
        if not cmd:
            return {"error": "cmd required"}
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"stdout": proc.stdout, "stderr": proc.stderr, "rc": proc.returncode}
