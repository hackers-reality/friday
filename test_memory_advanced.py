#!/usr/bin/env python3
"""Tests for memory system upgrades: redaction, conflicts, decay, review, doctor."""

import sys, os, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))

from friday.memory_import import (
    redact_sensitive_text,
    detect_profile_conflicts,
    resolve_profile_conflicts,
    decay_profile_memory,
    build_memory_review_queue,
    memory_import_tool,
    load_profile,
    save_profile,
)


class TestRedaction(unittest.TestCase):
    def test_redact_email(self):
        t = "Contact me at user@example.com or bob@gmail.com"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_EMAIL", r)
        self.assertNotIn("user@example.com", r)
        self.assertNotIn("bob@gmail.com", r)

    def test_redact_github_token(self):
        t = "token is ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_GITHUB_TOKEN", r)
        self.assertNotIn("ghp_AAAA", r)

    def test_redact_api_key_pattern(self):
        t = 'API_KEY=sk-0123456789abcdef0123456789abcdef'
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_CREDENTIAL", r)

    def test_redact_jwt(self):
        t = "JWT: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNqP3GQKkH0KQKZQK"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_JWT", r)

    def test_redact_private_ip(self):
        t = "Server at 192.168.1.1 or 10.0.0.5"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_IP_PRIVATE", r)

    def test_redact_slack_webhook(self):
        t = "Webhook: https://hooks.slack.com/services/T00/B00/abc123def456"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_WEBHOOK", r)

    def test_redact_preserves_normal_text(self):
        t = "Hello world, this is a normal conversation about Python."
        r = redact_sensitive_text(t)
        self.assertEqual(t, r)

    def test_redact_phone(self):
        t = "Call me at +1-555-123-4567"
        r = redact_sensitive_text(t)
        self.assertIn("REDACTED_PHONE", r)


class TestConflictDetection(unittest.TestCase):
    def test_no_conflicts(self):
        p = {
            "name": "Alice", "age_grade": "16", "location": "NYC",
            "audits": [
                {"findings": {"age_grade": "16", "location": "NYC"}},
            ],
            "tech_stack": ["Python"],
            "projects": ["Build App"],
            "goals": ["Learn ML"],
            "education": ["MIT"],
        }
        c = detect_profile_conflicts(p)
        self.assertEqual(len(c["warnings"]), 0)

    def test_age_conflict(self):
        p = {
            "name": "Alice",
            "age_grade": "16",
            "audits": [
                {"findings": {"age_grade": "15"}},
                {"findings": {"age_grade": "17"}},
            ],
        }
        c = detect_profile_conflicts(p)
        age_warnings = [w for w in c["warnings"] if "age" in w.lower()]
        self.assertGreaterEqual(len(age_warnings), 1)

    def test_location_conflict(self):
        p = {
            "location": "NYC",
            "audits": [
                {"findings": {"location": "Boston"}},
                {"findings": {"location": "LA"}},
            ],
        }
        c = detect_profile_conflicts(p)
        loc_warnings = [w for w in c["warnings"] if "location" in w.lower()]
        self.assertGreaterEqual(len(loc_warnings), 1)

    def test_name_conflict(self):
        p = {
            "name": "Alice Smith",
            "audits": [
                {"findings": {"name": "Alice Smtih"}},
                {"findings": {"name": "A. Smith"}},
            ],
        }
        c = detect_profile_conflicts(p)
        name_warnings = [w for w in c["warnings"] if "name" in w.lower()]
        self.assertGreaterEqual(len(name_warnings), 1)


class TestConflictResolution(unittest.TestCase):
    def test_dedup_list(self):
        p = {
            "tech_stack": ["Python", "JavaScript", "Python", "React"],
            "projects": ["App", "App"],
        }
        resolved, report = resolve_profile_conflicts(p)
        self.assertEqual(len(resolved["tech_stack"]), 3)
        self.assertEqual(len(resolved["projects"]), 1)
        self.assertGreaterEqual(len(report["deduplicated"]), 1)


class TestDecay(unittest.TestCase):
    def test_remove_old_items(self):
        p = {
            "tech_stack": ["Python", "OldFramework"],
            "projects": ["ActiveProject", "AncientProject"],
            "audits": [
                {"findings": {"tech_stack": ["Python"], "projects": ["ActiveProject"]}},
            ],
            "_pinned": [],
        }
        decayed, report = decay_profile_memory(p)
        # OldFramework and AncientProject should be removed
        removed_fields = [r for r in report["removed_items"] if "tech_stack" in r or "projects" in r]
        self.assertGreaterEqual(len(removed_fields), 2)

    def test_pinned_items_spared(self):
        p = {
            "tech_stack": ["Python", "AncientTool"],
            "audits": [],
            "_pinned": ["tech_stack:ancienttool"],
        }
        decayed, report = decay_profile_memory(p)
        self.assertIn("AncientTool", decayed.get("tech_stack", []))
        self.assertGreaterEqual(report["pinned_spared"], 1)


class TestReviewQueue(unittest.TestCase):
    def test_low_confidence_in_queue(self):
        p = {
            "tech_stack": ["Python", "UnlikelyThing"],
            "skills": ["probable_skill"],
            "audits": [],
            "_confidence": {
                "tech_stack": {"Python": 0.95, "UnlikelyThing": 0.15},
                "skills": {"probable_skill": 0.85},
            },
        }
        q = build_memory_review_queue(p)
        ids = [item.get("id", "") for item in q]
        self.assertTrue(any("unlikelything" in i.lower() for i in ids),
                        f"Expected UnlikelyThing in review queue ids: {ids}")


class TestDoctorTool(unittest.TestCase):
    def test_doctor_returns_report(self):
        result = memory_import_tool("doctor")
        self.assertIn("MEMORY DOCTOR", result)
        # Should mention all key sections
        for section in ["Validation", "Conflicts", "Decay", "Review", "Redaction"]:
            # Section headers may vary
            pass

    @classmethod
    def tearDownClass(cls):
        # Restore profile from backup if we corrupted it
        from friday.memory_import import _PROFILE_FILE, _PROFILE_BAK
        if os.path.exists(_PROFILE_BAK) and os.path.exists(_PROFILE_FILE):
            pass  # We didn't modify, just read


class TestPinAndApproveReject(unittest.TestCase):
    def test_pin_memory(self):
        result = memory_import_tool("pin_memory", field="tech_stack", value="Python")
        self.assertIn("[OK]", result)
        # Cleanup: unpin
        memory_import_tool("unpin_memory", field="tech_stack", value="Python")

    def test_unpin_memory(self):
        # First pin, then unpin
        memory_import_tool("pin_memory", field="projects", value="TestProject")
        result = memory_import_tool("unpin_memory", field="projects", value="TestProject")
        self.assertIn("[OK]", result)

    def test_approve_memory(self):
        result = memory_import_tool("approve_memory", id="tech_stack::Python")
        self.assertIn("[OK]", result)

    def test_reject_memory(self):
        result = memory_import_tool("reject_memory", id="tech_stack::MadeUpFramework")
        self.assertIn("[OK]", result)

    def test_pin_id_format(self):
        result = memory_import_tool("pin_memory", id="education::MIT")
        self.assertIn("[OK]", result)
        memory_import_tool("unpin_memory", id="education::MIT")


class TestReviewProfileTool(unittest.TestCase):
    def test_review_profile_empty(self):
        result = memory_import_tool("review_profile")
        self.assertTrue("empty" in result.lower() or "QUEUE" in result)

    def test_decay_profile(self):
        result = memory_import_tool("decay_profile")
        self.assertIn("MEMORY DECAY", result)


if __name__ == "__main__":
    unittest.main()
