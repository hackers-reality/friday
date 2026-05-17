"""
Tests for FRIDAY Iron Man features.
"""
import sys, os, json, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from friday.ironman import (
    damage_report,
    suit_check,
    morning_plan,
    evening_review,
    ironman_tool,
    _REPORTS_DIR,
    _HISTORY_FILE,
)


class TestIronMan(unittest.TestCase):
    def test_damage_report_returns_string(self):
        report = damage_report()
        self.assertIsInstance(report, str)
        self.assertIn("DAMAGE REPORT", report)
        self.assertIn("Risk Score", report)

    def test_damage_report_has_risk(self):
        report = damage_report()
        self.assertTrue("LOW" in report or "MEDIUM" in report or "HIGH" in report)

    def test_suit_check_returns_string(self):
        report = suit_check()
        self.assertIsInstance(report, str)
        self.assertIn("SUIT CHECK", report)

    def test_suit_check_has_results(self):
        report = suit_check()
        self.assertIn("passed", report)
        self.assertIn("failed", report)

    def test_morning_plan_returns_string(self):
        plan = morning_plan()
        self.assertIsInstance(plan, str)
        self.assertIn("MORNING BRIEFING", plan)

    def test_morning_plan_has_greeting(self):
        plan = morning_plan()
        self.assertTrue("Good morning" in plan or "Good afternoon" in plan or "Good evening" in plan)

    def test_evening_review_returns_string(self):
        review = evening_review()
        self.assertIsInstance(review, str)
        self.assertIn("EVENING REVIEW", review)

    def test_evening_review_has_summary(self):
        review = evening_review()
        self.assertIn("Daily Summary", review)

    def test_ironman_tool_status(self):
        result = ironman_tool("status")
        self.assertIn("IRON MAN SYSTEMS", result)

    def test_ironman_tool_damage_report(self):
        result = ironman_tool("damage_report")
        self.assertIn("DAMAGE REPORT", result)

    def test_ironman_tool_suit_check(self):
        result = ironman_tool("suit_check")
        self.assertIn("SUIT CHECK", result)

    def test_ironman_tool_morning_plan(self):
        result = ironman_tool("morning_plan")
        self.assertIn("MORNING BRIEFING", result)

    def test_ironman_tool_evening_review(self):
        result = ironman_tool("evening_review")
        self.assertIn("EVENING REVIEW", result)

    def test_ironman_tool_unknown_action(self):
        result = ironman_tool("bogus")
        self.assertIn("[FAIL]", result)

    def test_history_file_created(self):
        """Running a report should create the history log."""
        damage_report()
        self.assertTrue(os.path.exists(_HISTORY_FILE))
        with open(_HISTORY_FILE, "r") as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)

    def test_reports_directory_created(self):
        self.assertTrue(os.path.exists(_REPORTS_DIR))

    def test_suit_check_detects_modules(self):
        report = suit_check()
        self.assertIn("friday.memory_import", report)
        self.assertIn("friday.authority", report)
        self.assertIn("friday.profile_schema", report)


if __name__ == "__main__":
    unittest.main()
