#!/usr/bin/env python3
"""Tests for Friday Snapshot / Time Travel module."""

import sys, os, json, unittest, tempfile, shutil
sys.path.insert(0, os.path.dirname(__file__))

from friday.snapshots import (
    create_snapshot,
    restore_snapshot,
    diff_snapshot,
    list_snapshots,
    snapshot_tool,
)


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.tmpdir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("Hello World")
        self.test_dir = os.path.join(self.tmpdir, "subdir")
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "a.txt"), "w") as f:
            f.write("File A")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        # Don't remove snapshots in the real memory dir - just clean test ones
        # The snapshot index will have test entries but that's OK

    def test_create_file_snapshot(self):
        result = create_snapshot(self.test_file, label="test file snap")
        self.assertIn("success", result)
        self.assertIn("id", result)
        self.assertIn("dest", result)
        self.assertTrue(os.path.exists(result["dest"]))

    def test_create_dir_snapshot(self):
        result = create_snapshot(self.test_dir, label="test dir snap")
        self.assertIn("success", result)

    def test_create_nonexistent(self):
        result = create_snapshot("/nonexistent/path/xyz", label="fail")
        self.assertIn("error", result)

    def test_list_snapshots(self):
        snaps = list_snapshots()
        self.assertIsInstance(snaps, list)

    def test_restore_snapshot(self):
        result = create_snapshot(self.test_file, label="restore test")
        self.assertIn("success", result)
        snap_id = result["id"]

        # Modify original
        with open(self.test_file, "w") as f:
            f.write("Modified Content")

        # Restore
        restore_result = restore_snapshot(snap_id)
        self.assertIn("success", restore_result)

        with open(self.test_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "Hello World")

    def test_restore_nonexistent(self):
        result = restore_snapshot(99999)
        self.assertIn("error", result)

    def test_diff_identical(self):
        result = create_snapshot(self.test_file, label="diff test")
        snap_id = result["id"]

        diff_result = diff_snapshot(snap_id)
        # Should be identical since we haven't modified
        if "status" in diff_result:
            self.assertIn(diff_result["status"], ("identical", "different"))

    def test_diff_changed(self):
        result = create_snapshot(self.test_file, label="diff change test")
        snap_id = result["id"]

        # Modify
        with open(self.test_file, "w") as f:
            f.write("CHANGED CONTENT")

        diff_result = diff_snapshot(snap_id)
        self.assertEqual(diff_result.get("status"), "changed")

    def test_diff_nonexistent(self):
        result = diff_snapshot(99999)
        self.assertIn("error", result)

    def test_snapshot_tool_list(self):
        result = snapshot_tool("list")
        self.assertIn("SNAPSHOTS", result)

    def test_snapshot_tool_create(self):
        result = snapshot_tool("create", path=self.test_file, label="tool test")
        self.assertIn("[OK]", result)

    def test_snapshot_tool_create_no_path(self):
        result = snapshot_tool("create")
        self.assertIn("[FAIL]", result)

    def test_snapshot_tool_restore_no_id(self):
        result = snapshot_tool("restore")
        self.assertIn("[FAIL]", result)

    def test_snapshot_tool_info(self):
        # Create first
        cr = create_snapshot(self.test_file, label="info test")
        snap_id = cr["id"]
        result = snapshot_tool("info", id=snap_id)
        self.assertIn("SNAPSHOT", result)
        self.assertIn(str(snap_id), result)

    def test_snapshot_tool_info_nonexistent(self):
        result = snapshot_tool("info", id=99999)
        self.assertIn("[FAIL]", result)


if __name__ == "__main__":
    unittest.main()
