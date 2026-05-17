#!/usr/bin/env python3
"""Tests for Friday Sidecar System."""

import sys, os, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from friday.sidecar import (
    register_sidecar,
    heartbeat_sidecar,
    list_sidecars,
    sidecar_status,
    dispatch_sidecar_command,
    sidecar_tool,
    SIDECAR_TYPES,
)


class TestSidecar(unittest.TestCase):
    def test_register_sidecar(self):
        r = register_sidecar("test-desktop", "desktop", capabilities=["click", "type"])
        self.assertIn("success", r)
        self.assertIn("id", r)
        self.assertEqual(r["name"], "test-desktop")

    def test_register_invalid_type(self):
        r = register_sidecar("bad", "nonexistent_type_xyz")
        self.assertIn("error", r)

    def test_list_sidecars(self):
        # Register a known sidecar for this test
        register_sidecar("list-test-car", "desktop")
        sidecars = list_sidecars()
        self.assertIsInstance(sidecars, list)
        names = [s["name"] for s in sidecars]
        self.assertIn("list-test-car", names)

    def test_heartbeat(self):
        # Register a fresh sidecar
        r = register_sidecar("hb-test", "system_monitor")
        sid = r["id"]
        result = heartbeat_sidecar(sid, status="alive", log="Starting up")
        self.assertIn("success", result)
        self.assertEqual(result["status"], "alive")

        # Verify heartbeat registered
        s = sidecar_status(sid)
        self.assertIsNotNone(s)
        self.assertIn("last_heartbeat", s)
        self.assertNotEqual(s["last_heartbeat"], "")

    def test_heartbeat_nonexistent(self):
        result = heartbeat_sidecar(99999, status="alive")
        self.assertIn("error", result)

    def test_sidecar_status(self):
        r = register_sidecar("status-test", "browser")
        sid = r["id"]
        s = sidecar_status(sid)
        self.assertIsNotNone(s)
        self.assertEqual(s["name"], "status-test")
        self.assertEqual(s["type"], "browser")

    def test_sidecar_status_nonexistent(self):
        s = sidecar_status(99999)
        self.assertIsNone(s)

    def test_dispatch_command(self):
        r = register_sidecar("dispatch-test", "desktop")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "ping")
        self.assertIn("command", result)
        self.assertEqual(result["command"], "ping")

    def test_dispatch_nonexistent(self):
        result = dispatch_sidecar_command(99999, "ping")
        self.assertIn("error", result)

    def test_sidecar_tool_status(self):
        result = sidecar_tool("status")
        self.assertIn("SIDECAR STATUS", result)

    def test_sidecar_tool_list(self):
        result = sidecar_tool("list")
        self.assertIn("SIDECARS", result)

    def test_sidecar_tool_register(self):
        result = sidecar_tool("register", name="tool-test", type="filesystem")
        self.assertIn("[OK]", result)

    def test_sidecar_tool_register_no_name(self):
        result = sidecar_tool("register")
        self.assertIn("[FAIL]", result)

    def test_sidecar_tool_register_bad_type(self):
        result = sidecar_tool("register", name="bad", type="bogus")
        self.assertIn("[FAIL]", result)

    def test_sidecar_tool_heartbeat(self):
        r = register_sidecar("heartbeat-tool-test", "smart_home")
        sid = r["id"]
        result = sidecar_tool("heartbeat", id=sid, status="busy", log="Working")
        self.assertIn("[OK]", result)

    def test_sidecar_tool_heartbeat_no_id(self):
        result = sidecar_tool("heartbeat")
        self.assertIn("[FAIL]", result)

    def test_sidecar_tool_info(self):
        r = register_sidecar("info-test", "code_workspace")
        sid = r["id"]
        result = sidecar_tool("info", id=sid)
        self.assertIn("SIDECAR", result)
        self.assertIn(str(sid), result)

    def test_sidecar_tool_info_nonexistent(self):
        result = sidecar_tool("info", id=99999)
        self.assertIn("[FAIL]", result)

    def test_sidecar_tool_dispatch(self):
        r = register_sidecar("dispatch-tool-test", "desktop")
        sid = r["id"]
        result = sidecar_tool("dispatch", id=sid, command="ping")
        self.assertIn("command", result)
        self.assertIn("ping", result)

    def test_dispatch_ping(self):
        r = register_sidecar("ping-test", "desktop")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "ping")
        self.assertEqual(result.get("command"), "ping")
        self.assertEqual(result.get("result"), "pong")

    def test_dispatch_shutdown(self):
        r = register_sidecar("shutdown-test", "desktop")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "shutdown")
        self.assertEqual(result.get("command"), "shutdown")
        # Verify sidecar status changed
        s = sidecar_status(sid)
        self.assertEqual(s["status"], "shutdown")

    def test_dispatch_capabilities(self):
        r = register_sidecar("cap-test", "desktop", capabilities=["click", "type"])
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "capabilities")
        self.assertEqual(result.get("command"), "capabilities")
        self.assertEqual(result.get("result"), ["click", "type"])

    def test_dispatch_remote_endpoint(self):
        """Dispatch to a remote endpoint should fail gracefully (connection refused)."""
        r = register_sidecar("remote-test", "desktop", endpoint="http://127.0.0.1:1")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "ping")
        # Should have error key (connection refused)
        self.assertIn("error", result)

    def test_dispatch_remote_timeout(self):
        """Dispatch to a non-responsive host should time out gracefully."""
        r = register_sidecar("timeout-test", "desktop", endpoint="http://10.255.255.1:1")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "ping")
        self.assertIn("error", result)

    def test_dispatch_exec_with_params(self):
        """Dispatch exec with proper cmd param."""
        import subprocess, sys
        r = register_sidecar("exec-test", "desktop")
        sid = r["id"]
        result = dispatch_sidecar_command(sid, "exec", params={"cmd": "echo hello"})
        self.assertIn("success", result)
        self.assertIn("stdout", result.get("result", {}))

    def test_sidecar_tool_dispatch_no_id(self):
        result = sidecar_tool("dispatch", command="ping")
        self.assertIn("[FAIL]", result)

    def test_sidecar_tool_dispatch_no_command(self):
        result = sidecar_tool("dispatch", id=1)
        self.assertIn("[FAIL]", result)

    def test_unknown_action(self):
        result = sidecar_tool("bogus")
        self.assertIn("[FAIL]", result)


if __name__ == "__main__":
    unittest.main()
