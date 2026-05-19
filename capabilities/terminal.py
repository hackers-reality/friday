from __future__ import annotations

import asyncio
from typing import Any, Dict

from sidecar_transport import SidecarTransport


async def handle(action: str, params: Dict[str, Any], command_id: str, transport: SidecarTransport) -> dict:
    if action not in {"run", "run_command"}:
        return {"error": f"unsupported terminal action: {action}"}

    cmd = str(params.get("cmd", "")).strip()
    if not cmd:
        return {"error": "cmd required"}

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def _stream(stream, stream_name: str):
        while True:
            chunk = await stream.readline()
            if not chunk:
                break
            await transport.send_json(
                {
                    "type": "event",
                    "command_id": command_id,
                    "payload": {
                        "stream": stream_name,
                        "chunk": chunk.decode("utf-8", errors="replace"),
                    },
                }
            )

    await asyncio.gather(_stream(proc.stdout, "stdout"), _stream(proc.stderr, "stderr"))
    rc = await proc.wait()
    return {"rc": rc}
