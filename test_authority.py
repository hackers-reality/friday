#!/usr/bin/env python3
"""Tests for Friday Authority & Action Policy module."""

import sys, os, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(__file__))

# Backup and restore authority policy file
from friday._paths import FRIDAY_MEMORY
_AUTHORITY_POLICY_FILE = os.path.join(FRIDAY_MEMORY, "authority_policy.json")
_AUTHORITY_LOG_FILE = os.path.join(FRIDAY_MEMORY, "authority_log.jsonl")

from friday.authority import (
    classify_tool_risk,
    load_authority_policy,
    save_authority_policy,
    should_allow_tool,
    log_authority_decision,
    authority_tool,
    _get_default_policy,
    RISK_ORDER,
)


class TestClassifyToolRisk(unittest.TestCase):
    def test_classify_read_only(self):
        self.assertEqual(classify_tool_risk("read_file"), "read_only")
        self.assertEqual(classify_tool_risk("list_files"), "read_only")
        self.assertEqual(classify_tool_risk("system_info"), "read_only")
        self.assertEqual(classify_tool_risk("search_browser_history"), "read_only")

    def test_classify_local_write(self):
        self.assertIn(classify_tool_risk("write_file"), ("local_write", "network_write"))
        self.assertEqual(classify_tool_risk("open_app"), "local_write")
        self.assertEqual(classify_tool_risk("click"), "local_write")
        self.assertEqual(classify_tool_risk("type_text"), "local_write")

    def test_classify_destructive(self):
        self.assertEqual(classify_tool_risk("delete_file"), "destructive")

    def test_classify_external_send(self):
        self.assertEqual(classify_tool_risk("send_email"), "external_send")
        self.assertEqual(classify_tool_risk("send_instagram_dm"), "external_send")

    def test_classify_credential(self):
        self.assertEqual(classify_tool_risk("gmail_authorize"), "credential")
        self.assertEqual(classify_tool_risk("exchange_oauth_code"), "credential")

    def test_classify_fallback_to_read_only(self):
        self.assertEqual(classify_tool_risk("unknown_custom_tool"), "read_only")


class TestAuthorityPolicy(unittest.TestCase):
    def setUp(self):
        # Start fresh: save and remove any stale policy
        self._orig_content = None
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            with open(_AUTHORITY_POLICY_FILE, "r") as f:
                self._orig_content = f.read()
            os.remove(_AUTHORITY_POLICY_FILE)

    def tearDown(self):
        if self._orig_content:
            with open(_AUTHORITY_POLICY_FILE, "w") as f:
                f.write(self._orig_content)
        elif os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)

    def test_default_policy(self):
        p = _get_default_policy()
        self.assertEqual(p["mode"], "auto")
        self.assertTrue(p["allow_read_only"])
        self.assertFalse(p["allow_destructive"])

    def test_load_policy_default(self):
        # Remove policy file if exists
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)
        p = load_authority_policy()
        self.assertEqual(p["mode"], "auto")

    def test_save_and_load(self):
        p = _get_default_policy()
        p["mode"] = "dry_run"
        save_authority_policy(p)
        loaded = load_authority_policy()
        self.assertEqual(loaded["mode"], "dry_run")

    def test_save_and_load_custom(self):
        p = {"mode": "block_all", "max_risk_level": 0}
        save_authority_policy(p)
        loaded = load_authority_policy()
        self.assertEqual(loaded["mode"], "block_all")


class TestShouldAllowTool(unittest.TestCase):
    def setUp(self):
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)

    def tearDown(self):
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)

    def test_allow_read_only(self):
        d = should_allow_tool("read_file")
        self.assertTrue(d["allowed"])

    def test_allow_local_write_default(self):
        d = should_allow_tool("write_file")
        self.assertTrue(d["allowed"])

    def test_block_destructive_default(self):
        d = should_allow_tool("delete_file")
        self.assertFalse(d["allowed"])
        self.assertTrue(d["needs_approval"])

    def test_block_all_mode(self):
        p = _get_default_policy()
        p["mode"] = "block_all"
        save_authority_policy(p)
        d = should_allow_tool("read_file")
        self.assertFalse(d["allowed"])

    def test_blocked_tools_list(self):
        p = _get_default_policy()
        p["blocked_tools"] = ["delete_file"]
        save_authority_policy(p)
        d = should_allow_tool("delete_file")
        self.assertFalse(d["allowed"])

    def test_dry_run_mode(self):
        p = _get_default_policy()
        p["mode"] = "dry_run"
        save_authority_policy(p)
        d = should_allow_tool("delete_file")
        self.assertFalse(d["allowed"])


class TestAuthorityTool(unittest.TestCase):
    def setUp(self):
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)

    def tearDown(self):
        if os.path.exists(_AUTHORITY_POLICY_FILE):
            os.remove(_AUTHORITY_POLICY_FILE)

    def test_status(self):
        result = authority_tool("status")
        self.assertIn("AUTHORITY STATUS", result)
        self.assertIn("Mode", result)

    def test_mode_change(self):
        result = authority_tool("mode", mode="dry_run")
        self.assertIn("[OK]", result)
        p = load_authority_policy()
        self.assertEqual(p["mode"], "dry_run")
        # Reset
        authority_tool("mode", mode="auto")

    def test_classify_tool(self):
        result = authority_tool("classify", tool="delete_file")
        self.assertIn("destructive", result)

    def test_allow_risk(self):
        result = authority_tool("allow", risk="destructive")
        self.assertIn("[OK]", result)

    def test_block_risk(self):
        result = authority_tool("block", risk="destructive")
        self.assertIn("[OK]", result)

    def test_block_tool(self):
        result = authority_tool("block", tool="read_file")
        self.assertIn("[OK]", result)

    def test_policy(self):
        result = authority_tool("policy")
        self.assertIn("AUTHORITY POLICY", result)

    def test_unknown_action(self):
        result = authority_tool("bogus_action_xyz")
        self.assertIn("[FAIL]", result)


if __name__ == "__main__":
    unittest.main()
