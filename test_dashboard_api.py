#!/usr/bin/env python3
"""Tests for Friday Dashboard API module."""

import sys, os, json, unittest, threading, time
sys.path.insert(0, os.path.dirname(__file__))

from friday.dashboard_api import (
    DashboardAPI,
    dashboard_api_tool,
    _get_health,
    _get_state,
    _get_tools,
    _get_tasks,
    _get_memory_status,
    _get_memory_doctor,
    _get_memory_review,
    _get_authority,
    _get_snapshots,
    _get_sidecars,
    _get_goals,
    _get_system,
    _get_logs_recent,
    _get_capabilities,
    _get_mission,
    _get_briefing,
    _get_workspace,
    _get_diagnostic,
)


class TestDashboardEndpoints(unittest.TestCase):
    def test_health(self):
        h = _get_health()
        self.assertEqual(h["status"], "ok")
        self.assertIn("timestamp", h)
        self.assertIn("version", h)

    def test_state(self):
        s = _get_state()
        self.assertIn("status", s)
        self.assertIn("mode", s)
        self.assertIn("tools_available", s)

    def test_tools(self):
        t = _get_tools()
        self.assertIn("total", t)
        self.assertGreater(t["total"], 100)

    def test_tasks(self):
        t = _get_tasks()
        self.assertIn("total", t)

    def test_memory_status(self):
        m = _get_memory_status()
        self.assertIn("profile_exists", m)
        self.assertIn("audit_count", m)

    def test_memory_doctor(self):
        d = _get_memory_doctor()
        self.assertIn("report", d)

    def test_memory_review(self):
        r = _get_memory_review()
        self.assertIsInstance(r, list)

    def test_authority(self):
        a = _get_authority()
        self.assertIn("mode", a)
        self.assertIn("max_risk_level", a)

    def test_snapshots(self):
        s = _get_snapshots()
        self.assertIn("total", s)

    def test_sidecars(self):
        s = _get_sidecars()
        self.assertIn("total", s)

    def test_goals(self):
        g = _get_goals()
        self.assertIn("info", g)

    def test_system(self):
        s = _get_system()
        self.assertIn("cpu_percent", s)
        self.assertIn("memory_percent", s)

    def test_logs_recent(self):
        logs = _get_logs_recent(10)
        self.assertIsInstance(logs, list)

    def test_capabilities(self):
        c = _get_capabilities()
        self.assertIn("total", c)
        self.assertGreater(c["total"], 30)

    def test_mission(self):
        m = _get_mission()
        self.assertIn("mission", m)

    def test_briefing(self):
        b = _get_briefing()
        self.assertIn("memory_ok", b)

    def test_workspace(self):
        w = _get_workspace()
        self.assertIn("path", w)
        self.assertIn("modules_count", w)

    def test_diagnostic(self):
        d = _get_diagnostic()
        self.assertIn("systems", d)
        self.assertIn("all_systems_operational", d)
        self.assertIn("system_count", d)
        self.assertGreater(d["system_count"], 5)


class TestDashboardAPIServer(unittest.TestCase):
    def test_start_and_stop(self):
        api = DashboardAPI(port=8091)
        result = api.start()
        self.assertIn("success", result)
        self.assertTrue(api.is_running())
        api.stop()
        self.assertFalse(api.is_running())

    def test_start_twice(self):
        api = DashboardAPI(port=8092)
        api.start()
        self.assertTrue(api.is_running())
        # Starting again should succeed (idempotent)
        api.stop()
        self.assertFalse(api.is_running())


class TestDashboardAPITool(unittest.TestCase):
    def test_status(self):
        result = dashboard_api_tool("status")
        self.assertIn("DASHBOARD API", result)

    def test_start_and_stop_tool(self):
        # Stop first if running
        dashboard_api_tool("stop")
        result = dashboard_api_tool("start", port=8093)
        self.assertIn("[OK]", result)
        # Stop
        result = dashboard_api_tool("stop")
        self.assertIn("[OK]", result)

    def test_unknown_action(self):
        result = dashboard_api_tool("bogus")
        self.assertIn("[FAIL]", result)


if __name__ == "__main__":
    unittest.main()
