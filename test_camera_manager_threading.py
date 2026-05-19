"""Threading isolation checks for camera manager."""
from __future__ import annotations

import threading
import time

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
