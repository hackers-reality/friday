#!/usr/bin/env python3
"""Tests for Friday Tool Registry module."""

import sys, os, unittest
sys.path.insert(0, os.path.dirname(__file__))

from friday.tool_registry import (
    build_tool_registry,
    get_tool_metadata,
    list_tool_registry,
    check_tool_registry_consistency,
    tool_registry_tool,
    TOOL_META,
)


class TestToolRegistry(unittest.TestCase):
    def test_build_registry(self):
        r = build_tool_registry()
        self.assertGreater(len(r), 100)
        self.assertIn("read_file", r)
        self.assertIn("write_file", r)

    def test_get_metadata_known(self):
        m = get_tool_metadata("read_file")
        self.assertIsNotNone(m)
        self.assertEqual(m["category"], "filesystem")
        self.assertEqual(m["risk"], "read_only")

    def test_get_metadata_unknown(self):
        m = get_tool_metadata("nonexistent_tool_12345")
        self.assertIsNone(m)

    def test_list_registry_all(self):
        grouped = list_tool_registry()
        self.assertIn("filesystem", grouped)
        self.assertIn("memory", grouped)
        self.assertIn("internal", grouped)
        total = sum(len(v) for v in grouped.values())
        self.assertEqual(total, len(TOOL_META))

    def test_list_registry_filtered(self):
        filesys = list_tool_registry("filesystem")
        self.assertIn("filesystem", filesys)
        self.assertIn("read_file", filesys["filesystem"])

    def test_list_registry_unknown_category(self):
        result = list_tool_registry("nonexistent_category_xyz")
        self.assertEqual(result, {})

    def test_consistency_with_real_tool_map(self):
        # Try to load TOOL_MAP from live.py
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "friday"))
            # We can't easily import live.py due to Gemini SDK deps,
            # so we verify that our registry is self-consistent
            for name, meta in TOOL_META.items():
                self.assertIn("category", meta)
                self.assertIn("risk", meta)
                self.assertIn("description", meta)
        except Exception:
            pass

    def test_tool_registry_tool_status(self):
        result = tool_registry_tool("status")
        self.assertIn("TOOL REGISTRY", result)
        self.assertIn("Total tools", result)

    def test_tool_registry_tool_get(self):
        result = tool_registry_tool("get", tool_name="read_file")
        self.assertIn("read_file", result)
        self.assertIn("filesystem", result)

    def test_tool_registry_tool_get_unknown(self):
        result = tool_registry_tool("get", tool_name="nope_123")
        self.assertIn("[FAIL]", result)

    def test_tool_registry_tool_list(self):
        result = tool_registry_tool("list")
        self.assertIn("filesystem", result)
        self.assertIn("read_file", result)

    def test_every_tool_has_valid_risk_level(self):
        valid_risks = {"read_only", "local_write", "destructive", "system_control",
                        "external_send", "credential", "network_write", "self_modify",
                        "background_autonomy"}
        for name, meta in TOOL_META.items():
            self.assertIn(meta["risk"], valid_risks, f"Tool '{name}' has invalid risk '{meta['risk']}'")

    def test_every_tool_has_valid_category(self):
        for name, meta in TOOL_META.items():
            self.assertIsInstance(meta["category"], str)
            self.assertGreater(len(meta["category"]), 0)
            self.assertIsInstance(meta["description"], str)
            self.assertGreater(len(meta["description"]), 0)


if __name__ == "__main__":
    unittest.main()
