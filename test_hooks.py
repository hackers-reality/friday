"""
Tests for Friday Hooks System — authority enforcement, auto-snapshot, logging.
"""
import unittest
import tempfile
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestHooks(unittest.TestCase):
    """Test hooks registration and built-in hooks."""

    def setUp(self):
        # Clear registries between tests
        from friday.hooks import _pre_hooks, _post_hooks, _error_hooks
        self._saved_pre = list(_pre_hooks)
        self._saved_post = list(_post_hooks)
        self._saved_error = list(_error_hooks)
        _pre_hooks.clear()
        _post_hooks.clear()
        _error_hooks.clear()

    def tearDown(self):
        from friday.hooks import _pre_hooks, _post_hooks, _error_hooks
        _pre_hooks.clear()
        _post_hooks.clear()
        _error_hooks.clear()
        _pre_hooks.extend(self._saved_pre)
        _post_hooks.extend(self._saved_post)
        _error_hooks.extend(self._saved_error)

    def test_register_and_run_pre_hook(self):
        from friday.hooks import register_pre_hook, run_pre_hooks
        seen = []

        def my_hook(name, args, session=None):
            seen.append((name, args))
            return args

        register_pre_hook(my_hook)
        result = run_pre_hooks("test_tool", {"key": "val"}, "sess")
        self.assertEqual(result, {"key": "val"})
        self.assertEqual(seen, [("test_tool", {"key": "val"})])

    def test_pre_hook_block(self):
        from friday.hooks import register_pre_hook, run_pre_hooks

        def blocker(name, args, session=None):
            return None

        register_pre_hook(blocker)
        result = run_pre_hooks("test_tool", {"key": "val"})
        self.assertIsNone(result)

    def test_pre_hook_modify_args(self):
        from friday.hooks import register_pre_hook, run_pre_hooks

        def modifier(name, args, session=None):
            args["modified"] = True
            return args

        register_pre_hook(modifier)
        result = run_pre_hooks("test_tool", {"key": "val"})
        self.assertEqual(result, {"key": "val", "modified": True})

    def test_multiple_pre_hooks(self):
        from friday.hooks import register_pre_hook, run_pre_hooks
        order = []

        def h1(name, args, session=None):
            order.append("h1")
            return args

        def h2(name, args, session=None):
            order.append("h2")
            return args

        register_pre_hook(h1)
        register_pre_hook(h2)
        run_pre_hooks("t", {})
        self.assertEqual(order, ["h1", "h2"])

    def test_block_prevents_later_hooks(self):
        from friday.hooks import register_pre_hook, run_pre_hooks
        order = []

        def blocker(name, args, session=None):
            order.append("blocker")
            return None

        def after(name, args, session=None):
            order.append("after")
            return args

        register_pre_hook(blocker)
        register_pre_hook(after)
        result = run_pre_hooks("t", {})
        self.assertIsNone(result)
        self.assertEqual(order, ["blocker"])

    def test_register_and_run_post_hook(self):
        from friday.hooks import register_post_hook, run_post_hooks
        seen = []

        def my_hook(name, args, result, session=None):
            seen.append((name, result))

        register_post_hook(my_hook)
        run_post_hooks("t", {"a": 1}, "ok", "s")
        self.assertEqual(seen, [("t", "ok")])

    def test_register_and_run_error_hook(self):
        from friday.hooks import register_error_hook, run_error_hooks
        seen = []

        def my_hook(name, args, error, session=None):
            seen.append((name, str(error)))

        register_error_hook(my_hook)
        run_error_hooks("t", {}, ValueError("bad"), "s")
        self.assertEqual(seen, [("t", "bad")])

    def test_hook_exception_does_not_propagate(self):
        from friday.hooks import register_pre_hook, run_pre_hooks

        def broken(name, args, session=None):
            raise RuntimeError("boom")

        register_pre_hook(broken)
        result = run_pre_hooks("t", {"a": 1})
        self.assertEqual(result, {"a": 1})  # exception silently caught

    def test_authority_pre_hook_allows_safe(self):
        """Authority pre-hook should allow read_only tools."""
        from friday.hooks import register_pre_hook, run_pre_hooks, _authority_pre_hook
        register_pre_hook(_authority_pre_hook)
        result = run_pre_hooks("get_time", {})
        self.assertIsNotNone(result)

    def test_authority_pre_hook_blocks_destructive(self):
        """Authority pre-hook should block destructive tools by default."""
        from friday.hooks import register_pre_hook, run_pre_hooks, _authority_pre_hook
        register_pre_hook(_authority_pre_hook)
        result = run_pre_hooks("delete_file", {"path": "test.txt"})
        # Default policy blocks destructive tools
        self.assertIsNone(result)

    def test_auto_snapshot_hook_fires_on_destructive(self):
        """Auto-snapshot pre-hook should not block destructive tools."""
        from friday.hooks import register_pre_hook, run_pre_hooks, _auto_snapshot_pre_hook
        register_pre_hook(_auto_snapshot_pre_hook)
        result = run_pre_hooks("delete_file", {"path": "test.txt"})
        self.assertIsNotNone(result)

    def test_auto_snapshot_hook_ignores_safe(self):
        """Auto-snapshot pre-hook should pass through safe tools."""
        from friday.hooks import register_pre_hook, run_pre_hooks, _auto_snapshot_pre_hook
        register_pre_hook(_auto_snapshot_pre_hook)
        result = run_pre_hooks("get_time", {})
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
