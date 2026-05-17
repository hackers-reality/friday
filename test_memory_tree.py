"""Tests for FRIDAY Memory Tree module."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import friday.memory_tree as mt


class TestMemoryTree(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_dir = mt._MEMORY_TREE_DIR
        self._orig_daily = mt._DAILY_NOTES_DIR
        self._orig_friday = mt.FRIDAY_MEMORY
        mt._MEMORY_TREE_DIR = os.path.join(self.tmpdir, "memory_tree")
        mt._DAILY_NOTES_DIR = os.path.join(mt._MEMORY_TREE_DIR, "daily_notes")
        mt.FRIDAY_MEMORY = self.tmpdir
        mt._ensure_dirs()

    def tearDown(self):
        mt._MEMORY_TREE_DIR = self._orig_dir
        mt._DAILY_NOTES_DIR = self._orig_daily
        mt.FRIDAY_MEMORY = self._orig_friday
        shutil.rmtree(self.tmpdir)

    def test_ensure_dirs(self):
        self.assertTrue(os.path.exists(mt._MEMORY_TREE_DIR))
        self.assertTrue(os.path.exists(mt._DAILY_NOTES_DIR))

    def test_build_index(self):
        # Create a test page
        mt.write_page("test_page", "# Test Content\nHello world")
        index = mt.build_index()
        self.assertIn("[[test_page]]", index)
        self.assertIn("Memory Tree Index", index)

    def test_read_write_page(self):
        mt.write_page("mypage", "# My Page\nContent here")
        content = mt.read_page("mypage")
        self.assertIsNotNone(content)
        self.assertIn("Content here", content)

    def test_read_nonexistent(self):
        self.assertIsNone(mt.read_page("nonexistent"))

    def test_daily_note_create(self):
        note = mt.get_daily_note("2026-01-15")
        self.assertIn("2026-01-15", note)
        self.assertIn("Today's Focus", note)

    def test_daily_note_reuse(self):
        mt.get_daily_note("2026-01-15")
        note2 = mt.get_daily_note("2026-01-15")
        self.assertIn("2026-01-15", note2)

    def test_list_daily_notes(self):
        mt.get_daily_note("2026-01-15")
        mt.get_daily_note("2026-01-16")
        notes = mt.list_daily_notes()
        self.assertIn("2026-01-16", notes)
        self.assertIn("2026-01-15", notes)

    def test_search(self):
        mt.write_page("colors", "# Colors\nRed and blue are nice")
        mt.write_page("animals", "# Animals\nDogs and cats")
        results = mt.search_memory_tree("blue")
        self.assertEqual(len(results), 1)
        self.assertIn("colors", results[0]["file"])

    def test_search_multiple(self):
        mt.write_page("a", "# A\napple banana")
        mt.write_page("b", "# B\nbanana cherry")
        results = mt.search_memory_tree("banana")
        self.assertEqual(len(results), 2)

    def test_backlink_extraction(self):
        content = "See [[people]] and [[goals]] for more."
        links = mt.extract_backlinks(content)
        self.assertEqual(links, ["people", "goals"])

    def test_tool_status(self):
        result = mt.memory_tree_tool("status")
        self.assertIn("MEMORY TREE", result)

    def test_tool_read(self):
        mt.write_page("test123", "# T\nC")
        result = mt.memory_tree_tool("read", name="test123")
        self.assertIn("C", result)

    def test_tool_write(self):
        result = mt.memory_tree_tool("write", name="newpage", content="# New\nContent")
        self.assertIn("OK", result)
        self.assertIsNotNone(mt.read_page("newpage"))

    def test_tool_search(self):
        mt.write_page("data", "# D\nsecret_key=xyz")
        result = mt.memory_tree_tool("search", query="secret_key")
        self.assertIn("data", result)

    def test_tool_daily_note(self):
        result = mt.memory_tree_tool("daily_note", date="2026-06-01")
        self.assertIn("2026-06-01", result)

    def test_tool_daily_notes_list(self):
        mt.get_daily_note("2026-06-01")
        result = mt.memory_tree_tool("daily_notes")
        self.assertIn("2026-06-01", result)

    def test_tool_build_index(self):
        result = mt.memory_tree_tool("build_index")
        self.assertIn("OK", result)

    def test_tool_context(self):
        mt.write_page("current_context", "# Current Context\nWorking on project X")
        result = mt.memory_tree_tool("context")
        # May be empty if no daily note focus, but shouldn't fail
        self.assertIsInstance(result, str)

    def test_tool_unknown_action(self):
        result = mt.memory_tree_tool("nonexistent")
        self.assertIn("FAIL", result)

    def test_update_from_profile_no_profile(self):
        result = mt.update_from_profile()
        self.assertIn("FAIL", result)

    def test_context_has_today_focus(self):
        ctx = mt.build_memory_tree_context()
        self.assertIn("Today's Focus", ctx)


if __name__ == "__main__":
    unittest.main()
