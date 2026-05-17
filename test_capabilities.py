#!/usr/bin/env python3
"""Tests for Friday Capability Report module."""

import sys, os, unittest
sys.path.insert(0, os.path.dirname(__file__))

from friday.capabilities import (
    CAPABILITIES,
    generate_capability_report,
    get_capability_status,
    list_capabilities,
    capabilities_tool,
    CAPABILITY_REPORT_FILE,
)


class TestCapabilities(unittest.TestCase):
    def test_all_capabilities_have_required_fields(self):
        for name, info in CAPABILITIES.items():
            self.assertIn("status", info, f"{name} missing status")
            self.assertIn("description", info, f"{name} missing description")

    def test_valid_statuses(self):
        valid = ("stable", "partial", "experimental", "planned")
        for name, info in CAPABILITIES.items():
            self.assertIn(info["status"], valid, f"{name} has invalid status '{info['status']}'")

    def test_generate_report(self):
        report = generate_capability_report()
        self.assertIn("FRIDAY Capability Report", report)
        self.assertIn("stable", report)
        self.assertIn("partial", report)
        self.assertIn("Summary", report)
        # Should have counts
        self.assertIn("Total capabilities", report)
        self.assertIn("Coverage", report)

    def test_report_written_to_file(self):
        self.assertTrue(os.path.exists(CAPABILITY_REPORT_FILE))
        with open(CAPABILITY_REPORT_FILE, "r") as f:
            content = f.read()
        self.assertIn("FRIDAY Capability Report", content)

    def test_get_capability_status(self):
        self.assertEqual(get_capability_status("voice"), "stable")
        self.assertEqual(get_capability_status("dashboard"), "stable")
        self.assertIsNone(get_capability_status("nonexistent_xyz"))

    def test_list_capabilities(self):
        all_caps = list_capabilities()
        self.assertGreater(len(all_caps), 30)
        names = [n for n, _ in all_caps]
        self.assertIn("voice", names)
        self.assertIn("memory_profile", names)
        self.assertIn("authority", names)

    def test_list_capabilities_by_status(self):
        stable = list_capabilities("stable")
        for _, info in stable:
            self.assertEqual(info["status"], "stable")
        self.assertGreater(len(stable), 20)

    def test_minimum_capability_count(self):
        self.assertGreaterEqual(len(CAPABILITIES), 40)

    def test_capabilities_tool_list(self):
        result = capabilities_tool("list")
        self.assertTrue(result.startswith("[OK]"))
        self.assertIn("capabilities", result)
        self.assertIn("voice", result)
        self.assertIn("authority", result)

    def test_capabilities_tool_get(self):
        result = capabilities_tool("get", capability="voice")
        self.assertIn("voice", result)
        self.assertIn("stable", result)

    def test_capabilities_tool_get_unknown(self):
        result = capabilities_tool("get", capability="nonexistent")
        self.assertTrue(result.startswith("[FAIL]"))

    def test_capabilities_tool_report(self):
        result = capabilities_tool("report")
        self.assertIn("FRIDAY Capability Report", result)

    def test_capabilities_tool_unknown_action(self):
        result = capabilities_tool("bogus")
        self.assertTrue(result.startswith("[FAIL]"))


if __name__ == "__main__":
    unittest.main()
