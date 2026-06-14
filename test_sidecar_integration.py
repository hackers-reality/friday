"""Integration tests for Friday sidecar brain registry loop."""
from __future__ import annotations

import asyncio
import unittest

from friday.sidecar.device_registry import DeviceRegistry, SidecarCommand


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


class TestDeviceRegistry(unittest.IsolatedAsyncioTestCase):
    async def test_registry_register_and_send_command_result(self):
        registry = DeviceRegistry()
        ws = FakeWebSocket()

        await registry.register("test-device", ["system_info"], ws, device_id="dev-1")
        self.assertIsNotNone(registry.get("test-device"))

        async def resolve_result():
            await asyncio.sleep(0.05)
            await registry.handle_command_result("cmd-123", {"ok": True, "value": 42})

        task = asyncio.create_task(resolve_result())
        result = await registry.send_command(
            "test-device",
            {
                "type": "command",
                "command_id": "cmd-123",
                "capability": "system_info",
                "action": "get",
                "params": {},
            },
            timeout=2,
        )
        await task

        self.assertEqual(result, {"ok": True, "value": 42})
        self.assertEqual(len(ws.sent), 1)
        self.assertEqual(ws.sent[0]["command_id"], "cmd-123")

    async def test_registry_broadcast(self):
        registry = DeviceRegistry()
        ws_a = FakeWebSocket()
        ws_b = FakeWebSocket()

        await registry.register("a", ["system_info"], ws_a, device_id="dev-a")
        await registry.register("b", ["system_info"], ws_b, device_id="dev-b")

        async def resolve_later(command_id: str):
            await asyncio.sleep(0.05)
            await registry.handle_command_result(command_id, {"ok": True})

        command = SidecarCommand(capability="system_info", action="get", params={})
        waiter = asyncio.create_task(resolve_later(command.command_id))
        results = await registry.broadcast(command, timeout=2)
        await waiter

        self.assertIn("a", results)
        self.assertIn("b", results)

