"""Tests for FRIDAY Diagnostics & Benchmarks module."""

import json
import os
import shutil
import tempfile
import unittest

import friday.diagnostics as diag


class TestDiagnostics(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_memory = diag.FRIDAY_MEMORY
        self._orig_config = diag.FRIDAY_CONFIG
        diag.FRIDAY_MEMORY = os.path.join(self.tmpdir, "memory")
        diag.FRIDAY_CONFIG = os.path.join(self.tmpdir, "config")
        os.makedirs(diag.FRIDAY_MEMORY, exist_ok=True)
        os.makedirs(diag.FRIDAY_CONFIG, exist_ok=True)

        from unittest.mock import patch
        self.io_patcher = patch("friday.diagnostics._measure_io_benchmark", return_value={
            "1KB": {"write_speed_mbps": 100.0, "read_speed_mbps": 150.0, "write_ms": 0.01, "read_ms": 0.01},
            "1MB": {"write_speed_mbps": 100.0, "read_speed_mbps": 150.0, "write_ms": 10.0, "read_ms": 5.0},
            "10MB": {"write_speed_mbps": 100.0, "read_speed_mbps": 150.0, "write_ms": 100.0, "read_ms": 50.0},
        })
        self.io_patcher.start()

        self.module_patcher = patch("friday.diagnostics._check_module", side_effect=lambda name, path: {
            "check": f"module:{name}", "status": "ok", "detail": f"mocked import {path}"
        })
        self.module_patcher.start()

    def tearDown(self):
        self.io_patcher.stop()
        self.module_patcher.stop()
        diag.FRIDAY_MEMORY = self._orig_memory
        diag.FRIDAY_CONFIG = self._orig_config
        shutil.rmtree(self.tmpdir)

    def test_run_diagnostics(self):
        results = diag.run_diagnostics()
        self.assertGreater(len(results), 10)
        # Should have python_version check
        self.assertTrue(any(r["check"] == "python_version" for r in results))

    def test_diagnostics_checks_paths(self):
        results = diag.run_diagnostics()
        path_checks = [r for r in results if r["check"].startswith("path:")]
        self.assertGreater(len(path_checks), 0)

    def test_diagnostics_module_checks(self):
        results = diag.run_diagnostics()
        module_checks = [r for r in results if r["check"].startswith("module:")]
        self.assertGreater(len(module_checks), 5)

    def test_diagnostics_hardware(self):
        results = diag.run_diagnostics()
        self.assertTrue(any(r["check"] == "cpu_cores" for r in results))
        self.assertTrue(any(r["check"] == "disk_space" for r in results))

    def test_format_report(self):
        results = diag.run_diagnostics()
        report = diag.format_diagnostic_report(results)
        self.assertIn("FRIDAY DIAGNOSTIC REPORT", report)
        self.assertIn("Passed", report)

    def test_format_report_verbose(self):
        results = diag.run_diagnostics()
        report = diag.format_diagnostic_report(results, verbose=True)
        self.assertIn("ALL CHECKS", report)

    def test_run_benchmarks(self):
        results = diag.run_benchmarks()
        self.assertIn("timestamp", results)
        self.assertIn("platform", results)
        self.assertIn("io", results)
        self.assertIn("json_serialize_ms", results)

    def test_benchmarks_io(self):
        results = diag.run_benchmarks()
        io = results["io"]
        self.assertIn("1KB", io)
        self.assertIn("1MB", io)
        self.assertIn("write_speed_mbps", io["1KB"])
        self.assertIn("read_speed_mbps", io["1KB"])

    # Tool function tests
    def test_tool_diagnostics(self):
        result = diag.diagnostics_tool("diagnostics")
        self.assertIn("FRIDAY DIAGNOSTIC REPORT", result)
        self.assertIn("Failed", result)

    def test_tool_diagnostics_verbose(self):
        result = diag.diagnostics_tool("diagnostics", verbose=True)
        self.assertIn("ALL CHECKS", result)

    def test_tool_benchmarks(self):
        result = diag.diagnostics_tool("benchmarks")
        data = json.loads(result)
        self.assertIn("timestamp", data)
        self.assertIn("io", data)

    def test_tool_report(self):
        result = diag.diagnostics_tool("report")
        data = json.loads(result)
        self.assertIn("diagnostics", data)
        self.assertIn("benchmarks", data)

    def test_tool_unknown_action(self):
        result = diag.diagnostics_tool("nonexistent")
        self.assertIn("FAIL", result)


if __name__ == "__main__":
    unittest.main()
