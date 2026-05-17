"""Tests for FRIDAY runtime state and singleton management."""

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from friday import _singletons as rt


class TestRuntimeState(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_memory = rt.FRIDAY_MEMORY
        self._orig_path = rt.RUNTIME_STATE_PATH
        rt.FRIDAY_MEMORY = self.tmpdir
        rt.RUNTIME_STATE_PATH = os.path.join(self.tmpdir, "runtime_state.json")

    def tearDown(self):
        rt.FRIDAY_MEMORY = self._orig_memory
        rt.RUNTIME_STATE_PATH = self._orig_path
        shutil.rmtree(self.tmpdir)

    def test_load_empty(self):
        state = rt.load_runtime_state()
        self.assertEqual(state, {})

    def test_save_and_load(self):
        rt.save_runtime_state({"test": "value"})
        state = rt.load_runtime_state()
        self.assertEqual(state.get("test"), "value")
        self.assertIn("_updated_at", state)

    def test_set_service_state(self):
        rt.set_service_state("dashboard_api", url="http://127.0.0.1:8090", status="running")
        state = rt.load_runtime_state()
        self.assertIn("dashboard_api", state)
        self.assertEqual(state["dashboard_api"]["url"], "http://127.0.0.1:8090")
        self.assertEqual(state["dashboard_api"]["status"], "running")

    def test_get_service_state(self):
        rt.set_service_state("test_svc", foo="bar")
        svc = rt.get_service_state("test_svc")
        self.assertEqual(svc.get("foo"), "bar")

    def test_get_service_state_missing(self):
        svc = rt.get_service_state("nonexistent")
        self.assertEqual(svc, {})

    def test_clear_service_state(self):
        rt.set_service_state("temp_svc", value=1)
        rt.clear_service_state("temp_svc")
        self.assertEqual(rt.get_service_state("temp_svc"), {})

    def test_clear_all_state(self):
        rt.set_service_state("svc1", a=1)
        rt.set_service_state("svc2", b=2)
        rt.clear_all_state()
        self.assertEqual(rt.load_runtime_state(), {})

    def test_check_http_endpoint_unreachable(self):
        result = rt.check_http_endpoint("http://127.0.0.1:19999/health", timeout=1)
        self.assertFalse(result["reachable"])
        self.assertIsNotNone(result["error"])

    def test_check_port_open_closed(self):
        result = rt.check_port_open("127.0.0.1", 19998, timeout=1)
        self.assertFalse(result["open"])

    def test_find_free_port(self):
        port = rt.find_free_port(18990, 5)
        self.assertGreater(port, 0)
        # Port should not be in use
        chk = rt.check_port_open("127.0.0.1", port)
        self.assertFalse(chk["open"])

    def test_get_dashboard_state_empty(self):
        dash = rt.get_dashboard_state()
        self.assertIn("api", dash)
        self.assertIn("ui", dash)
        self.assertIn("api_healthy", dash)
        self.assertFalse(dash["api_healthy"])

    def test_get_dashboard_state_with_data(self):
        rt.set_service_state("dashboard_api", url="http://127.0.0.1:8090", port=8090, status="running")
        dash = rt.get_dashboard_state()
        self.assertEqual(dash["api"]["url"], "http://127.0.0.1:8090")

    def test_save_preserves_existing(self):
        rt.set_service_state("svc1", x=1)
        rt.set_service_state("svc2", y=2)
        svc1 = rt.get_service_state("svc1")
        self.assertEqual(svc1.get("x"), 1)
        svc2 = rt.get_service_state("svc2")
        self.assertEqual(svc2.get("y"), 2)

    def test_runtime_state_path_exists(self):
        self.assertFalse(os.path.exists(rt.RUNTIME_STATE_PATH))
        rt.save_runtime_state({"a": 1})
        self.assertTrue(os.path.exists(rt.RUNTIME_STATE_PATH))

    def test_corrupted_state_file(self):
        os.makedirs(self.tmpdir, exist_ok=True)
        with open(rt.RUNTIME_STATE_PATH, "w") as f:
            f.write("{corrupted")
        state = rt.load_runtime_state()
        self.assertEqual(state, {})


if __name__ == "__main__":
    unittest.main()
