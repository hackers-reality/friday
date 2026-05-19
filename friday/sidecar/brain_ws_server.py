"""Brain WebSocket server for sidecar connections.

Mount `router` into an existing FastAPI app:

    from friday.sidecar.brain_ws_server import router as sidecar_router
    app.include_router(sidecar_router)

"""
from __future__ import annotations

import asyncio
import json
import jwt
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

from friday.orchestration_config import ensure_config
from friday.sidecar.device_registry import get_registry


router = APIRouter()


@router.get("/sidecar/health")
async def _health():
    return JSONResponse({"ok": True, "timestamp": datetime.utcnow().isoformat()})


@router.websocket("/sidecar")
async def sidecar_ws(websocket: WebSocket, token: str = Query(None)):
    if not token:
        await websocket.close(code=4001)
        return

    config = ensure_config()
    secret = config.get("sidecar", {}).get("secret_key")
    if not secret:
        await websocket.close(code=4002)
        return

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        await websocket.close(code=4003)
        return

    device_name = payload.get("device_name")
    device_id = payload.get("device_id")
    capabilities = payload.get("capabilities", [])
    if not device_name or not device_id:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    registry = get_registry()
    rec = await registry.register(device_name, device_id, capabilities, websocket)

    ping_task = asyncio.create_task(_ping_loop(device_name, websocket))
    try:
        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            try:
                msg = json.loads(data)
            except Exception:
                continue

            mtype = msg.get("type")
            if mtype == "telemetry":
                await registry.update_telemetry(device_name, msg.get("payload", {}))
            elif mtype == "result":
                # command result
                command_id = msg.get("command_id")
                await registry.handle_command_result(command_id, msg.get("payload", {}))
            elif mtype == "event":
                # ignored for now - could publish to event bus
                pass

    finally:
        ping_task.cancel()
        await registry.deregister(device_name)


async def _ping_loop(device_name: str, websocket: WebSocket):
    registry = get_registry()
    try:
        while True:
            try:
                await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
            except Exception:
                break
            await asyncio.sleep(30)
    finally:
        # mark offline
        await registry.deregister(device_name)
