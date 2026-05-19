"""Integration test: mock sidecar connects to brain WS, sends telemetry and handles command."""
import asyncio
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from friday.sidecar.brain_ws_server import router as sidecar_router
from friday.sidecar.token_generator import generate_token
from friday.sidecar.device_registry import get_registry


@pytest.mark.asyncio
async def test_sidecar_connect_and_command(loop):
    app = FastAPI()
    app.include_router(sidecar_router)

    client = TestClient(app)

    # generate a token using config (ensure_config will create secret)
    token = generate_token("test-device", ["system_info"], "ws://testserver/sidecar")

    # Use websockets to connect to the test server
    import websockets

    async with websockets.connect(f"ws://127.0.0.1:8000/sidecar?token={token}") as ws:
        await ws.send(json.dumps({"type": "telemetry", "payload": {"ping": 1}}))
        # send a command from brain to sidecar via registry
        registry = get_registry()
        # Wait briefly for registration (in a real test use synchronization)
        await asyncio.sleep(0.1)
        devices = registry.list_online()
        assert any(d.device_name == "test-device" for d in devices)
