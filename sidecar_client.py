"""Standalone sidecar client for Friday.

Usage: python sidecar_client.py --config ~/.friday-sidecar/config.yaml
Dependencies: websockets, pyjwt, psutil, Pillow
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import socket
from pathlib import Path
from typing import Any, Dict

import psutil
import websockets

from sidecar_transport import SidecarTransport
from capabilities import terminal as terminal_cap
from capabilities import filesystem as filesystem_cap
from capabilities import screenshot as screenshot_cap
from capabilities import system_info as system_info_cap


def _parse_simple_yaml(text: str) -> dict:
    """Parse minimal YAML for sidecar config without external YAML dependency."""
    data: dict = {}
    current_list_key = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list_key:
            data.setdefault(current_list_key, []).append(line[4:].strip())
            continue
        current_list_key = None
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value == "":
                data[key] = []
                current_list_key = key
            elif value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                data[key] = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
            else:
                data[key] = value.strip('"').strip("'")
    return data


def load_config_from_file(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return _parse_simple_yaml(text)


class WebSocketTransport(SidecarTransport):
    def __init__(self, uri: str):
        self.uri = uri
        self._ws = None

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.uri, ping_interval=None)

    async def send_json(self, payload: dict) -> None:
        await self._ws.send(json.dumps(payload))

    async def recv_text(self) -> str:
        return await self._ws.recv()

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()


def _has_camera() -> bool:
    try:
        import cv2  # optional runtime probe only
        cap = cv2.VideoCapture(0)
        ok = bool(cap and cap.isOpened())
        if cap:
            cap.release()
        return ok
    except Exception:
        return False


def _has_mic() -> bool:
    try:
        import pyaudio  # optional runtime probe only
        p = pyaudio.PyAudio()
        count = p.get_device_count()
        p.terminate()
        return count > 0
    except Exception:
        return False


def _safe_disk_usage() -> float:
    try:
        target = "C:\\" if os.name == "nt" else "/"
        return psutil.disk_usage(target).percent
    except Exception:
        return 0.0


 


async def send_telemetry(transport: SidecarTransport, config: dict):
    while True:
        payload = {
            "type": "telemetry",
            "device_name": config.get("device_name") or socket.gethostname(),
            "payload": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": psutil.virtual_memory().percent,
                "disk_percent": _safe_disk_usage(),
                "camera_available": _has_camera(),
                "mic_available": _has_mic(),
                "platform": platform.platform(),
                "hostname": socket.gethostname(),
            },
        }
        await transport.send_json(payload)
        await asyncio.sleep(60)


async def _handle_command(msg: dict, transport: SidecarTransport, config: dict):
    command_id = msg.get("command_id")
    capability = msg.get("capability")
    action = msg.get("action")
    params = msg.get("params", {})

    if capability not in config.get("capabilities", []):
        await transport.send_json({"type": "result", "command_id": command_id, "payload": {"error": "capability not permitted"}})
        return

    if capability == "terminal":
        result = await terminal_cap.handle(action, params, command_id, transport)
    elif capability == "filesystem":
        result = await filesystem_cap.handle(action, params)
    elif capability == "screenshot":
        result = await screenshot_cap.handle(action, params)
    elif capability == "system_info":
        result = await system_info_cap.handle(action, params)
    else:
        result = {"error": f"capability not implemented: {capability}"}

    await transport.send_json({"type": "result", "command_id": command_id, "device_name": config.get("device_name"), "payload": result})


async def _message_loop(transport: SidecarTransport, config: dict):
    while True:
        raw = await transport.recv_text()
        msg = json.loads(raw)
        msg_type = msg.get("type")

        if msg_type == "ping":
            await transport.send_json({"type": "pong", "ping_id": msg.get("ping_id"), "device_name": config.get("device_name")})
            continue

        if msg_type == "command":
            await _handle_command(msg, transport, config)


async def run_client(config_path: str):
    config = load_config_from_file(config_path)
    brain_url = str(config.get("brain_url", "")).strip()
    token = str(config.get("token", "")).strip()
    if not brain_url or not token:
        raise RuntimeError("brain_url and token required in sidecar config")

    backoff = 1
    while True:
        try:
            uri = f"{brain_url}?token={token}"
            transport = WebSocketTransport(uri)
            await transport.connect()
            telemetry_task = asyncio.create_task(send_telemetry(transport, config))
            try:
                await _message_loop(transport, config)
            finally:
                telemetry_task.cancel()
                await transport.close()
            backoff = 1
        except Exception:
            await asyncio.sleep(min(backoff, 60))
            backoff = min(backoff * 2, 60)


def main():
    parser = argparse.ArgumentParser(description="Run Friday sidecar client")
    parser.add_argument("--config", default=str(Path.home() / ".friday-sidecar" / "config.yaml"))
    args = parser.parse_args()
    asyncio.run(run_client(args.config))


if __name__ == "__main__":
    main()
