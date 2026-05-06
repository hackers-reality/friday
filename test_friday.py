"""
Friday Tests - Test suite for all modules.
Unit tests, integration tests, test utilities.
"""
from __future__ import annotations

import os
import sys
import json
import unittest
import io
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import unittest.mock as mock


# ─── Test Utilities ────────────────────────────#

class TestUtils:
    """Test utilities for Friday modules."""
    
    @staticmethod
    def mock_response(status_code: int = 200, json_data: Dict = None, text: str = None):
        """Create a mock requests response."""
        mock_resp = mock.MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.text = text or json.dumps(json_data or {})
        return mock_resp
    
    @staticmethod
    def capture_output(func, *args, **kwargs):
        """Capture print output from a function."""
        import io
        import sys
        
        captured = io.StringIO()
        sys.stdout = captured
        try:
            result = func(*args, **kwargs)
        finally:
            sys.stdout = sys.__stdout__
        
        return result, captured.getvalue()
    
    @staticmethod
    def create_temp_file(content: str, suffix: str = ".txt") -> Path:
        """Create a temporary file with content."""
        import tempfile
        
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        
        return Path(path)
    
    @staticmethod
    def cleanup_temp_file(path: Path):
        """Clean up temporary file."""
        if path.exists():
            path.unlink()


# ─── Unit Tests for Friday Core ────────────────────────────#

class TestFridayCore(unittest.TestCase):
    """Test Friday Core module."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from friday_core import FridayCore
            self.friday = FridayCore()
        except ImportError:
            self.skipTest("friday_core module not available")
    
    def test_initialization(self):
        """Test Friday initialization."""
        result = self.friday.initialize()
        self.assertIn("INITIALIZED", result)
        self.assertIn("Friday", result)
    
    def test_help_command(self):
        """Test help command."""
        result = self.friday.process("help")
        self.assertIn("FRIDAY HELP", result)
        self.assertIn("status", result)
    
    def test_status_command(self):
        """Test status command."""
        result = self.friday.process("status")
        self.assertIn("FRIDAY STATUS", result)


# ─── Unit Tests for Advanced Networking ────────────────────────────#

class TestAdvancedNetworking(unittest.TestCase):
    """Test Advanced Networking module."""
    
    def setUp(self):
        try:
            from advanced_networking import network_tool
            self.network_tool = network_tool
        except ImportError:
            self.skipTest("advanced_networking module not available")
    
    @mock.patch('requests.get')
    def test_http2_status(self, mock_get):
        """Test HTTP/2 status check."""
        mock_get.return_value = TestUtils.mock_response(200)
        
        result = self.network_tool("status")
        self.assertIn("ADVANCED NETWORKING STATUS", result)
    
    @mock.patch('subprocess.run')
    def test_ping(self, mock_run):
        """Test ping command."""
        mock_run.return_value = mock.MagicMock(
            returncode=0,
            stdout="Ping statistics: 0% loss",
            stderr=""
        )
        
        result = self.network_tool("ping", target="127.0.0.1")
        self.assertIn("PING", result)


# ─── Unit Tests for Advanced Crypto ────────────────────────────#

class TestAdvancedCrypto(unittest.TestCase):
    """Test Advanced Crypto module."""
    
    def setUp(self):
        try:
            from advanced_crypto import crypto_tool, Hasher
            self.crypto_tool = crypto_tool
            self.hasher = Hasher
        except ImportError:
            self.skipTest("advanced_crypto module not available")
    
    def test_hash(self):
        """Test hashing."""
        result = self.crypto_tool("hash", data="test")
        self.assertIn("SHA-256", result)
        self.assertIn("SHA-512", result)
    
    def test_hasher_sha256(self):
        """Test SHA-256 hashing."""
        result = self.hasher.sha256("test")
        self.assertEqual(len(result), 64)  # SHA-256 produces 64 hex chars


# ─── Unit Tests for Friday Web ────────────────────────────#

class TestFridayWeb(unittest.TestCase):
    """Test Friday Web module."""
    
    def setUp(self):
        try:
            from friday_web import web_tool
            self.web_tool = web_tool
        except ImportError:
            self.skipTest("friday_web module not available")
    
    def test_status(self):
        """Test web status."""
        result = self.web_tool("status")
        self.assertIn("WEB STATUS", result)
    
    @mock.patch('requests.get')
    def test_fetch(self, mock_get):
        """Test web fetch."""
        mock_get.return_value = TestUtils.mock_response(
            200, text="<html><body>Test</body></html>"
        )
        
        result = self.web_tool("fetch", url="https://example.com")
        self.assertIn("FETCH", result)


# ─── Unit Tests for Friday Tools ────────────────────────────#

class TestFridayTools(unittest.TestCase):
    """Test Friday Tools module."""
    
    def setUp(self):
        try:
            from friday_tools import tools_tool, TextProcessor
            self.tools_tool = tools_tool
            self.text_processor = TextProcessor
        except ImportError:
            self.skipTest("friday_tools module not available")
    
    def test_word_count(self):
        """Test word count."""
        result = self.text_processor.word_count("Hello world")
        self.assertEqual(result["words"], 2)
        self.assertEqual(result["characters"], 11)
    
    def test_tools_status(self):
        """Test tools status."""
        result = self.tools_tool("status")
        self.assertIn("TOOLS STATUS", result)


# ─── Integration Tests ────────────────────────────#

class TestIntegration(unittest.TestCase):
    """Integration tests for Friday modules."""
    
    def test_module_imports(self):
        """Test that all modules can be imported."""
        modules = [
            "friday_core",
            "friday_assistant",
            "friday_voice",
            "friday_web",
            "friday_automation",
            "friday_database",
            "friday_ai",
            "friday_tools",
            "friday_vision",
            "friday_security",
            "friday_monitor",
            "friday_scheduler",
            "friday_api",
            "friday_cloud",
            "friday_iot",
            "friday_dashboard",
            "friday_analytics",
            "friday_config",
            "friday_backup",
            "friday_nlp",
            "friday_integrations",
            "advanced_networking",
            "advanced_crypto",
        ]
        
        failed = []
        for module in modules:
            try:
                importlib.import_module(module)
            except ImportError:
                failed.append(module)
        
        if failed:
            self.fail(f"Failed to import: {', '.join(failed)}")
    
    def test_modules_have_tool_function(self):
        """Test that all modules have a tool function."""
        tools = {
            "friday_core": "FridayCore",
            "friday_voice": "voice_tool",
            "friday_web": "web_tool",
            "friday_automation": "automation_tool",
            "friday_database": "database_tool",
            "friday_ai": "ai_tool",
            "friday_tools": "tools_tool",
            "friday_vision": "vision_tool",
            "friday_security": "security_tool",
            "friday_monitor": "monitor_tool",
            "friday_scheduler": "scheduler_tool",
            "friday_api": "api_tool",
            "friday_cloud": "cloud_tool",
            "friday_iot": "iot_tool",
            "friday_dashboard": "dashboard_tool",
            "friday_analytics": "analytics_tool",
            "friday_config": "config_tool",
            "friday_backup": "backup_tool",
            "friday_nlp": "nlp_tool",
            "friday_integrations": "integrations_tool",
            "advanced_networking": "network_tool",
            "advanced_crypto": "crypto_tool",
        }
        
        failed = []
        for module, tool in tools.items():
            try:
                mod = importlib.import_module(module)
                if not hasattr(mod, tool):
                    failed.append(f"{module}.{tool}")
            except ImportError:
                pass  # Skip if module not available
        
        if failed:
            self.fail(f"Missing tool functions: {', '.join(failed)}")


# ─── Test Runner ────────────────────────────#

def run_tests(verbose: bool = True):
    """Run all Friday tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFridayCore,
        TestAdvancedNetworking,
        TestAdvancedCrypto,
        TestFridayWeb,
        TestFridayTools,
        TestIntegration,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
    }


# ─── Main Entry Point ────────────────────────────#

if __name__ == "__main__":
    print("=" * 60)
    print("Friday Test Suite")
    print("=" * 60)
    print()
    
    import importlib
    
    result = run_tests()
    
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result['tests_run']}")
    print(f"Failures: {result['failures']}")
    print(f"Errors: {result['errors']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Success: {'Yes' if result['success'] else 'No'}")
    print("=" * 60)
    
    sys.exit(0 if result["success"] else 1)
