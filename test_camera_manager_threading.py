"""Threading isolation checks for camera manager."""
from __future__ import annotations

import threading
import time
import cv2
import numpy as np

class DummyVideoCapture:
    def __init__(self, camera_index=0, *args, **kwargs):
        self.is_open = (camera_index != 999)
    def isOpened(self):
        return self.is_open
    def read(self):
        if not self.is_open:
            return False, None
        return True, np.zeros((480, 640, 3), dtype=np.uint8)
    def release(self):
        self.is_open = False
    def set(self, *args, **kwargs):
        return True
    def get(self, *args, **kwargs):
        return 0.0

cv2.VideoCapture = DummyVideoCapture

from friday.camera_manager import CameraManager
from friday.frame_buffer import FrameBuffer


def test_camera_manager_start_non_blocking():
    stop_event = threading.Event()
    manager = CameraManager(frame_buffer=FrameBuffer(max_frames=5, max_memory_mb=5), stop_event=stop_event)

    before = time.time()
    manager.start()
    elapsed = time.time() - before

    # start should return immediately, camera loop runs in daemon thread
    assert elapsed < 0.2
    assert manager._thread is not None
    assert manager._thread.daemon is True

    stop_event.set()
