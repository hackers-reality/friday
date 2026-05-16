#!/usr/bin/env python3
"""Tests for Friday Autonomy Engine."""

import sys, os, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from friday.autonomy import (
    queue_task,
    get_task,
    list_tasks,
    update_task,
    mark_running,
    mark_completed,
    mark_failed,
    pause_task,
    resume_task,
    task_summary,
    autonomy_tool,
)


class TestAutonomyTaskQueue(unittest.TestCase):
    def test_queue_task(self):
        r = queue_task("Test task", tool_name="read_file", tool_args={"path": "/tmp/test"})
        self.assertIn("success", r)
        self.assertIn("id", r)
        self.assertEqual(r["status"], "queued")

    def test_queue_task_no_description(self):
        r = queue_task("")
        self.assertIn("error", r)

    def test_get_task(self):
        r = queue_task("Get me task", priority=8)
        tid = r["id"]
        t = get_task(tid)
        self.assertIsNotNone(t)
        self.assertEqual(t["description"], "Get me task")
        self.assertEqual(t["priority"], 8)

    def test_get_task_nonexistent(self):
        t = get_task(99999)
        self.assertIsNone(t)

    def test_list_tasks(self):
        queue_task("List test task")
        tasks = list_tasks()
        self.assertGreater(len(tasks), 0)
        descs = [t["description"] for t in tasks]
        self.assertTrue(any("List test task" in d for d in descs))

    def test_list_tasks_by_status(self):
        tasks = list_tasks(status="queued")
        for t in tasks:
            self.assertEqual(t["status"], "queued")

    def test_mark_running(self):
        r = queue_task("Mark running test")
        tid = r["id"]
        result = mark_running(tid)
        self.assertIn("success", result)
        t = get_task(tid)
        self.assertEqual(t["status"], "running")
        self.assertNotEqual(t["started_at"], "")

    def test_mark_completed(self):
        r = queue_task("Mark completed test")
        tid = r["id"]
        mark_running(tid)
        result = mark_completed(tid, result="Done!", reflection="Was easy")
        self.assertIn("success", result)
        t = get_task(tid)
        self.assertEqual(t["status"], "completed")
        self.assertEqual(t["result"], "Done!")

    def test_mark_failed_with_retry(self):
        r = queue_task("Fail with retry test", retry_policy={"max_retries": 2, "backoff": 0.1})
        tid = r["id"]
        result = mark_failed(tid, error="Timeout")
        self.assertTrue(result.get("will_retry", False))
        t = get_task(tid)
        self.assertEqual(t["status"], "queued")
        self.assertEqual(t["retry_count"], 1)

    def test_mark_failed_exhausted(self):
        r = queue_task("Fail exhausted test", retry_policy={"max_retries": 0, "backoff": 0.1})
        tid = r["id"]
        result = mark_failed(tid, error="Failed permanently")
        self.assertFalse(result.get("will_retry", True))
        t = get_task(tid)
        self.assertEqual(t["status"], "failed")

    def test_pause_and_resume(self):
        r = queue_task("Pause resume test")
        tid = r["id"]
        pause_result = pause_task(tid)
        self.assertIn("success", pause_result)
        t = get_task(tid)
        self.assertEqual(t["status"], "paused")

        resume_result = resume_task(tid)
        self.assertIn("success", resume_result)
        t = get_task(tid)
        self.assertEqual(t["status"], "queued")

    def test_pause_completed_task(self):
        r = queue_task("Already done")
        tid = r["id"]
        mark_running(tid)
        mark_completed(tid)
        result = pause_task(tid)
        self.assertIn("error", result)

    def test_task_summary(self):
        summary = task_summary()
        self.assertIn("AUTONOMY TASK SUMMARY", summary)
        self.assertIn("queued", summary.lower())


class TestAutonomyTool(unittest.TestCase):
    def test_autonomy_tool_status(self):
        result = autonomy_tool("status")
        self.assertIn("AUTONOMY TASK SUMMARY", result)

    def test_autonomy_tool_queue(self):
        result = autonomy_tool("queue", description="Tool test task", tool="read_file")
        self.assertIn("[OK]", result)
        self.assertIn("Task #", result)

    def test_autonomy_tool_queue_no_description(self):
        result = autonomy_tool("queue")
        self.assertIn("[FAIL]", result)

    def test_autonomy_tool_list(self):
        result = autonomy_tool("list")
        self.assertIn("AUTONOMY TASKS", result)

    def test_autonomy_tool_get(self):
        r = queue_task("Autonomy tool get test")
        tid = r["id"]
        result = autonomy_tool("get", id=tid)
        self.assertIn("TASK", result)
        self.assertIn(str(tid), result)

    def test_autonomy_tool_get_no_id(self):
        result = autonomy_tool("get")
        self.assertIn("[FAIL]", result)

    def test_autonomy_tool_pause(self):
        r = queue_task("Autonomy pause test")
        tid = r["id"]
        result = autonomy_tool("pause", id=tid)
        self.assertIn("[OK]", result)

    def test_autonomy_tool_resume(self):
        r = queue_task("Autonomy resume test")
        tid = r["id"]
        pause_task(tid)
        result = autonomy_tool("resume", id=tid)
        self.assertIn("[OK]", result)

    def test_autonomy_tool_complete(self):
        r = queue_task("Autonomy complete test")
        tid = r["id"]
        mark_running(tid)
        result = autonomy_tool("complete", id=tid, result="All set!")
        self.assertIn("[OK]", result)

    def test_unknown_action(self):
        result = autonomy_tool("bogus_action_123")
        self.assertIn("[FAIL]", result)


if __name__ == "__main__":
    unittest.main()
