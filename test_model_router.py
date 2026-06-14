"""Tests for FRIDAY Model Router module."""

import json
import os
import shutil
import tempfile
import unittest

import friday.model_router as mr


class TestModelRouter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_fc = mr.FRIDAY_CONFIG
        self._orig_rp = mr._ROUTER_CONFIG_PATH
        mr.FRIDAY_CONFIG = self.tmpdir
        mr._ROUTER_CONFIG_PATH = os.path.join(self.tmpdir, "model_router.json")
        self._orig_health_check = mr.check_provider_health
        mr.check_provider_health = lambda provider: {"provider": provider, "status": "ok", "latency_ms": 1.0}

    def tearDown(self):
        mr.FRIDAY_CONFIG = self._orig_fc
        mr._ROUTER_CONFIG_PATH = self._orig_rp
        mr.check_provider_health = self._orig_health_check
        shutil.rmtree(self.tmpdir)

    def test_get_config_defaults(self):
        cfg = mr.get_config()
        self.assertEqual(cfg["primary_model"], "gemini-3.1-flash-live-preview")
        self.assertTrue(cfg["enable_fallback"])
        self.assertTrue(cfg["enable_cost_tracking"])

    def test_update_config(self):
        result = mr.update_config({"primary_model": "gpt-4o"})
        self.assertIn("OK", result)
        cfg = mr.get_config()
        self.assertEqual(cfg["primary_model"], "gpt-4o")

    def test_list_models_all(self):
        models = mr.list_models()
        self.assertGreater(len(models), 3)

    def test_list_models_filter(self):
        models = mr.list_models(filter_provider="openai")
        for m in models:
            self.assertEqual(m["provider"], "openai")

    def test_resolve_model_default(self):
        model = mr.resolve_model()
        self.assertIsNotNone(model)

    def test_resolve_model_vision(self):
        model = mr.resolve_model("vision")
        self.assertIsNotNone(model)

    def test_resolve_model_code(self):
        model = mr.resolve_model("code")
        self.assertIsNotNone(model)

    def test_resolve_model_fast(self):
        model = mr.resolve_model("fast")
        self.assertIsNotNone(model)

    def test_resolve_model_with_preference(self):
        model = mr.resolve_model("chat", {"model": "gpt-4o"})
        self.assertEqual(model, "gpt-4o")

    def test_get_model_info_found(self):
        info = mr.get_model_info("gemini-2.0-flash")
        self.assertIsNotNone(info)
        self.assertEqual(info["provider"], "google")

    def test_get_model_info_not_found(self):
        self.assertIsNone(mr.get_model_info("nonexistent-model"))

    def test_track_usage(self):
        # Should not raise
        mr.track_usage("gemini-2.0-flash", 100, 50, 200.0, True)
        stats = mr.get_cost_stats()
        self.assertGreater(stats["total_cost"], 0)

    def test_get_cost_stats(self):
        stats = mr.get_cost_stats()
        self.assertIn("total_cost", stats)
        self.assertIn("total_tokens", stats)

    def test_get_recent_usage_empty(self):
        records = mr.get_recent_usage(5)
        self.assertIsInstance(records, list)

    def test_get_recent_usage_with_data(self):
        mr.track_usage("gpt-4o", 200, 100, 500.0, True)
        records = mr.get_recent_usage(5)
        self.assertGreater(len(records), 0)
        self.assertEqual(records[0]["model"], "gpt-4o")

    def test_health_all_providers(self):
        results = mr.health_all_providers()
        self.assertGreater(len(results), 0)

    # Tool function tests
    def test_tool_status(self):
        result = mr.model_router_tool("status")
        self.assertIn("MODEL ROUTER", result)

    def test_tool_list(self):
        result = mr.model_router_tool("list")
        self.assertIn("Available Models", result)

    def test_tool_list_with_provider(self):
        result = mr.model_router_tool("list", provider="google")
        self.assertIn("google", result.lower())

    def test_tool_resolve(self):
        result = mr.model_router_tool("resolve", task_type="chat")
        self.assertIn("Resolved Model", result)

    def test_tool_info(self):
        result = mr.model_router_tool("info", model_id="gemini-2.0-flash")
        self.assertIn("google", result)

    def test_tool_info_not_found(self):
        result = mr.model_router_tool("info", model_id="nonexistent")
        self.assertIn("FAIL", result)

    def test_tool_update_config(self):
        result = mr.model_router_tool("update_config", updates='{"primary_model":"gpt-4o-mini"}')
        self.assertIn("OK", result)
        self.assertEqual(mr.get_config()["primary_model"], "gpt-4o-mini")

    def test_tool_health(self):
        result = mr.model_router_tool("health")
        self.assertIn("Provider Health", result)

    def test_tool_usage(self):
        mr.track_usage("gemini-2.0-flash", 100, 50, 100.0, True)
        result = mr.model_router_tool("usage")
        self.assertIn("total_cost", result)

    def test_tool_recent(self):
        mr.track_usage("gemini-2.0-flash", 10, 5, 50.0, True)
        result = mr.model_router_tool("recent", n=5)
        self.assertIn("tokens", result)

    def test_tool_unknown_action(self):
        result = mr.model_router_tool("nonexistent")
        self.assertIn("FAIL", result)


if __name__ == "__main__":
    unittest.main()
