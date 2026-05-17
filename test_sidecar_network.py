"""
Tests for Friday Sidecar Network — discovery, JWT auth, tokens.
"""
import sys, os, json, unittest, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from friday.sidecar_network import (
    generate_token,
    verify_token,
    list_tokens,
    revoke_token,
    start_discovery,
    stop_discovery,
    get_discovered_sidecars,
    handle_sidecar_registration,
    sidecar_network_tool,
    _TOKENS_FILE,
)


class TestSidecarNetwork(unittest.TestCase):
    def setUp(self):
        # Clean token file before each test
        if os.path.exists(_TOKENS_FILE):
            os.remove(_TOKENS_FILE)

    def test_generate_token(self):
        token = generate_token("test-sidecar")
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

    def test_generate_token_no_expiry(self):
        token = generate_token("test-noexpiry", no_expiry=True)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

    def test_verify_token_valid(self):
        token = generate_token("verify-me")
        payload = verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "verify-me")

    def test_verify_token_no_expiry(self):
        token = generate_token("noexp", no_expiry=True)
        payload = verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "noexp")
        self.assertEqual(payload["exp"], 0)

    def test_verify_token_invalid(self):
        payload = verify_token("invalid.token.here")
        self.assertIsNone(payload)

    def test_verify_token_tampered(self):
        token = generate_token("safe")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignature"
        payload = verify_token(tampered)
        self.assertIsNone(payload)

    def test_list_tokens_empty(self):
        tokens = list_tokens()
        self.assertEqual(tokens, {})

    def test_list_tokens_after_generate(self):
        generate_token("list-me")
        tokens = list_tokens()
        self.assertIn("list-me", tokens)
        self.assertEqual(tokens["list-me"]["no_expiry"], False)

    def test_revoke_token(self):
        generate_token("revoke-me")
        self.assertIn("revoke-me", list_tokens())
        self.assertTrue(revoke_token("revoke-me"))
        self.assertNotIn("revoke-me", list_tokens())

    def test_revoke_nonexistent(self):
        self.assertFalse(revoke_token("does-not-exist"))

    def test_handle_registration_invalid_token(self):
        result = handle_sidecar_registration({"token": "bad.token"})
        self.assertIn("error", result)
        self.assertIn("Invalid", result["error"])

    def test_handle_registration_valid_token(self):
        token = generate_token("reg-test")
        result = handle_sidecar_registration({
            "token": token,
            "name": "reg-test",
            "type": "desktop",
            "host": "192.168.1.100",
            "port": 8095,
            "capabilities": ["exec", "ping"],
        })
        self.assertIn("success", result)
        self.assertEqual(result["name"], "reg-test")

    def test_discovery_start_stop(self):
        result = start_discovery()
        self.assertIn("[OK]", result)
        result = stop_discovery()
        self.assertIn("[OK]", result)

    def test_get_discovered_empty(self):
        sidecars = get_discovered_sidecars()
        self.assertIsInstance(sidecars, list)

    def test_sidecar_network_tool_status(self):
        result = sidecar_network_tool("status")
        self.assertIn("SIDECAR NETWORK", result)

    def test_sidecar_network_tool_generate_token(self):
        result = sidecar_network_tool("generate_token", name="tool-test")
        self.assertIn("[OK]", result)
        self.assertIn("tool-test", result)

    def test_sidecar_network_tool_generate_token_no_name(self):
        result = sidecar_network_tool("generate_token")
        self.assertIn("[FAIL]", result)

    def test_sidecar_network_tool_list_tokens(self):
        generate_token("list-test")
        result = sidecar_network_tool("list_tokens")
        self.assertIn("list-test", result)

    def test_sidecar_network_tool_revoke_token(self):
        generate_token("rev-test")
        result = sidecar_network_tool("revoke_token", name="rev-test")
        self.assertIn("[OK]", result)
        self.assertNotIn("rev-test", list_tokens())

    def test_sidecar_network_tool_revoke_nonexistent(self):
        result = sidecar_network_tool("revoke_token", name="nope")
        self.assertIn("[FAIL]", result)

    def test_sidecar_network_tool_verify_token(self):
        token = generate_token("verify-tool-test")
        result = sidecar_network_tool("verify_token", token=token)
        self.assertIn("[OK]", result)

    def test_sidecar_network_tool_verify_bad_token(self):
        result = sidecar_network_tool("verify_token", token="bad.token.here")
        self.assertIn("[FAIL]", result)

    def test_sidecar_network_tool_unknown_action(self):
        result = sidecar_network_tool("bogus")
        self.assertIn("[FAIL]", result)

    def test_sidecar_network_tool_discovered(self):
        result = sidecar_network_tool("discovered")
        self.assertIsInstance(result, str)

    def test_sidecar_network_tool_start_stop(self):
        result = sidecar_network_tool("start_discovery")
        self.assertIn("[OK]", result)
        result = sidecar_network_tool("stop_discovery")
        self.assertIn("[OK]", result)


if __name__ == "__main__":
    unittest.main()
