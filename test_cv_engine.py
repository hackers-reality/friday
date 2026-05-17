"""
Tests for Friday CV Engine — background camera + object detection.
"""
import sys, os, json, unittest, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from friday.cv_engine import (
    cv_tool,
    get_cv_status,
    get_cv_frame_b64,
    start_camera,
    stop_camera,
    _cv_state,
    _cv_lock,
    COCO_CLASSES,
)


class TestCVEngine(unittest.TestCase):
    def test_coco_classes_loaded(self):
        self.assertGreater(len(COCO_CLASSES), 50)
        self.assertIn("person", COCO_CLASSES)
        self.assertIn("car", COCO_CLASSES)
        self.assertIn("dog", COCO_CLASSES)

    def test_cv_tool_status_no_camera(self):
        status = cv_tool("status")
        self.assertIn("CV ENGINE", status)
        self.assertIn("INACTIVE", status)

    def test_cv_tool_context_no_camera(self):
        ctx = cv_tool("context")
        self.assertEqual(ctx, "")

    def test_cv_tool_unknown_action(self):
        result = cv_tool("bogus")
        self.assertIn("[FAIL]", result)

    def test_cv_tool_list_cameras(self):
        """Should not crash — may return fail if no cameras."""
        result = cv_tool("list_cameras")
        self.assertTrue(result.startswith("[OK]") or result.startswith("[FAIL]"))

    def test_cv_state_init(self):
        with _cv_lock:
            self.assertFalse(_cv_state["camera_active"])
            self.assertIsNone(_cv_state["last_capture"])

    def test_get_cv_status_no_camera(self):
        status = get_cv_status()
        self.assertFalse(status["camera_active"])
        self.assertIn("camera_active", status)
        self.assertIn("objects_found", status)
        self.assertIn("detections", status)
        self.assertIn("scene_description", status)

    def test_camera_start_stop_no_crash(self):
        """Starting camera with invalid index should fail gracefully."""
        result = start_camera(camera_index=999, interval=1.0)
        self.assertTrue(result.startswith("[FAIL]"))

    def test_cv_tool_start_stop(self):
        """Calling start then stop should work (even if camera unavailable)."""
        result = cv_tool("start", camera_index=999)
        self.assertTrue(result.startswith("[FAIL]"))
        result = cv_tool("stop")
        self.assertIn("[OK]", result)

    def test_cv_tool_start_valid(self):
        """Start with camera_index=0 may succeed if camera exists."""
        result = cv_tool("start", camera_index=0, interval=3.0)
        # Either way, stop after
        stop_camera()
        self.assertTrue(result.startswith("[OK]") or result.startswith("[FAIL]"))

    def test_stop_when_not_running(self):
        result = stop_camera()
        self.assertIn("[OK]", result)

    def test_double_stop(self):
        stop_camera()
        result = stop_camera()
        self.assertIn("[OK]", result)

    def test_get_cv_frame_no_camera(self):
        frame = get_cv_frame_b64()
        self.assertIsNone(frame)


if __name__ == "__main__":
    unittest.main()
