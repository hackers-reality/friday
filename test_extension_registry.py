"""Tests for FRIDAY Extension / MCP Registry module."""

import os
import shutil
import tempfile
import unittest

import friday.extension_registry as er


class TestExtensionRegistry(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_fc = er.FRIDAY_CONFIG
        self._orig_rp = er._REGISTRY_PATH
        er.FRIDAY_CONFIG = self.tmpdir
        er._REGISTRY_PATH = os.path.join(self.tmpdir, "extension_registry.json")

    def tearDown(self):
        er.FRIDAY_CONFIG = self._orig_fc
        er._REGISTRY_PATH = self._orig_rp
        shutil.rmtree(self.tmpdir)

    def _registry_file(self):
        return os.path.join(self.tmpdir, "extension_registry.json")

    def test_register_extension(self):
        result = er.register_extension("test-ext", "tool", "http://localhost:8081")
        self.assertIn("OK", result)
        self.assertTrue(os.path.exists(self._registry_file()))

    def test_register_extension_duplicate(self):
        er.register_extension("dup", "tool", "http://localhost:8081")
        result = er.register_extension("dup", "tool", "http://localhost:8082")
        self.assertIn("FAIL", result)

    def test_register_extension_invalid_type(self):
        result = er.register_extension("bad", "invalid_type", "http://localhost")
        self.assertIn("FAIL", result)

    def test_list_extensions(self):
        er.register_extension("ext1", "tool", "http://localhost:8081")
        er.register_extension("ext2", "bridge", "http://localhost:8082")
        exts = er.list_extensions()
        self.assertEqual(len(exts), 2)

    def test_list_extensions_filter(self):
        er.register_extension("ext1", "tool", "http://localhost:8081")
        er.register_extension("ext2", "bridge", "http://localhost:8082")
        exts = er.list_extensions(ext_type="tool")
        self.assertEqual(len(exts), 1)
        self.assertEqual(exts[0]["name"], "ext1")

    def test_update_extension(self):
        er.register_extension("ext1", "tool", "http://localhost:8081")
        result = er.update_extension("ext1", description="Updated desc")
        self.assertIn("OK", result)
        exts = er.list_extensions()
        self.assertEqual(exts[0]["description"], "Updated desc")

    def test_update_extension_not_found(self):
        result = er.update_extension("nonexistent", description="test")
        self.assertIn("FAIL", result)

    def test_remove_extension(self):
        er.register_extension("ext1", "tool", "http://localhost:8081")
        result = er.remove_extension("ext1")
        self.assertIn("OK", result)
        self.assertEqual(len(er.list_extensions()), 0)

    def test_remove_extension_not_found(self):
        result = er.remove_extension("nonexistent")
        self.assertIn("FAIL", result)

    def test_register_mcp_server(self):
        result = er.register_mcp_server("test-mcp", "echo")
        self.assertIn("OK", result)

    def test_register_mcp_server_duplicate(self):
        er.register_mcp_server("dup", "echo")
        result = er.register_mcp_server("dup", "cat")
        self.assertIn("FAIL", result)

    def test_list_mcp_servers(self):
        er.register_mcp_server("mcp1", "echo")
        er.register_mcp_server("mcp2", "cat")
        servers = er.list_mcp_servers()
        self.assertEqual(len(servers), 2)

    def test_update_mcp_server(self):
        er.register_mcp_server("mcp1", "echo")
        result = er.update_mcp_server("mcp1", description="Updated")
        self.assertIn("OK", result)

    def test_remove_mcp_server(self):
        er.register_mcp_server("mcp1", "echo")
        result = er.remove_mcp_server("mcp1")
        self.assertIn("OK", result)
        self.assertEqual(len(er.list_mcp_servers()), 0)

    def test_health_all_extensions_empty(self):
        results = er.health_all_extensions()
        self.assertIsInstance(results, list)

    def test_discover_capabilities(self):
        er.register_extension("img-proc", "tool", "http://localhost:8081",
                              capabilities=["image_resize", "image_convert"])
        results = er.discover_capabilities("image")
        self.assertGreater(len(results), 0)

    def test_discover_capabilities_no_match(self):
        er.register_extension("img-proc", "tool", "http://localhost:8081",
                              capabilities=["image_resize"])
        results = er.discover_capabilities("database")
        self.assertEqual(len(results), 0)

    # Tool function tests
    def test_tool_status(self):
        result = er.extension_registry_tool("status")
        self.assertIn("EXTENSION & MCP REGISTRY", result)

    def test_tool_register_extension(self):
        result = er.extension_registry_tool(
            "register_extension",
            name="tool-ext",
            type="tool",
            endpoint="http://localhost:9090",
        )
        self.assertIn("OK", result)

    def test_tool_update_extension(self):
        er.register_extension("upd-ext", "tool", "http://localhost:9090")
        result = er.extension_registry_tool(
            "update_extension",
            name="upd-ext",
            description="Updated via tool",
        )
        self.assertIn("OK", result)

    def test_tool_remove_extension(self):
        er.register_extension("del-ext", "tool", "http://localhost:9090")
        result = er.extension_registry_tool("remove_extension", name="del-ext")
        self.assertIn("OK", result)

    def test_tool_list_extensions(self):
        er.register_extension("list-ext", "tool", "http://localhost:9090")
        result = er.extension_registry_tool("list_extensions")
        self.assertIn("list-ext", result)

    def test_tool_register_mcp(self):
        result = er.extension_registry_tool(
            "register_mcp",
            name="tool-mcp",
            command="echo",
        )
        self.assertIn("OK", result)

    def test_tool_list_mcp(self):
        er.register_mcp_server("tool-mcp-list", "echo")
        result = er.extension_registry_tool("list_mcp")
        self.assertIn("tool-mcp-list", result)

    def test_tool_health(self):
        result = er.extension_registry_tool("health")
        # Empty registry: either "Health Check Results" or "[OK] Nothing to check"
        self.assertTrue("Health Check Results" in result or "Nothing to check" in result)

    def test_tool_discover(self):
        er.register_extension("disc-ext", "tool", "http://localhost:8081",
                              capabilities=["search", "index"])
        result = er.extension_registry_tool("discover", query="search")
        self.assertIn("disc-ext", result)

    def test_tool_unknown_action(self):
        result = er.extension_registry_tool("nonexistent")
        self.assertIn("FAIL", result)


if __name__ == "__main__":
    unittest.main()
