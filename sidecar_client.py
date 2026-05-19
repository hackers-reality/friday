"""Standalone sidecar client for Friday.

Usage: python sidecar_client.py --config ~/.friday-sidecar/config.yaml
"""
from __future__ import annotations

import asyncio
import json
import os
import base64
import argparse
from pathlib import Path
from typing import Any

import jwt
import websockets
import psutil

from PIL import ImageGrab

from friday.sidecar.capabilities.terminal import TerminalHandler
from friday.sidecar.capabilities.filesystem import FilesystemHandler
from friday.sidecar.capabilities.screenshot import ScreenshotHandler
from friday.sidecar.capabilities.system_info import SystemInfoHandler


HANDLERS = {
    "terminal": TerminalHandler(),
    "filesystem": FilesystemHandler(),
    "screenshot": ScreenshotHandler(),
    "system_info": SystemInfoHandler(),
}


async def send_telemetry(ws):
    while True:
        payload = {
            "type": "telemetry",
            "device_name": CONFIG.get("device_name"),
            "payload": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "platform": os.name,
                "hostname": CONFIG.get("device_name") or os.uname().nodename,
            },
        }
        try:
            await ws.send(json.dumps(payload))
        except Exception:
            break
        await asyncio.sleep(60)


async def handle_messages(ws):
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        if msg.get("type") == "ping":
            await ws.send(json.dumps({"type": "pong", "ts": msg.get("ts")}))
            continue
        if msg.get("type") == "command":
            command_id = msg.get("command_id")
            capability = msg.get("capability")
            action = msg.get("action")
            params = msg.get("params", {})
            if capability not in CONFIG.get("capabilities", []):
                await ws.send(json.dumps({"type": "result", "command_id": command_id, "payload": {"error": "capability not permitted"}}))
                continue
            handler = HANDLERS.get(capability)
            if not handler:
                await ws.send(json.dumps({"type": "result", "command_id": command_id, "payload": {"error": "capability not implemented"}}))
                continue
            try:
                res = await handler.handle(action, params)
            except Exception as e:
                res = {"error": str(e)}
            await ws.send(json.dumps({"type": "result", "command_id": command_id, "payload": res}))


async def run_client(config_path: str):
    global CONFIG
    CONFIG = json.loads(Path(config_path).read_text(encoding="utf-8"))
    brain_url = CONFIG.get("brain_url")
    token = CONFIG.get("token")
    if not brain_url or not token:
        raise RuntimeError("brain_url and token required in config")

    backoff = 1
    while True:
        try:
            uri = f"{brain_url}?token={token}"
            async with websockets.connect(uri, ping_interval=None) as ws:
                # start telemetry task
                t = asyncio.create_task(send_telemetry(ws))
                await handle_messages(ws)
                t.cancel()
        except Exception:
            await asyncio.sleep(min(backoff, 60))
            backoff = min(backoff * 2, 60)


def load_config_from_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=str(Path.home() / ".friday-sidecar" / "config.yaml"))
    args = p.parse_args()
    asyncio.run(run_client(args.config))


if __name__ == "__main__":
    main()
