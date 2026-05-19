"""Dedicated camera capture manager running in an isolated daemon thread."""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Optional

import psutil

from friday.context_bus import get_bus
from friday.cv_pipeline import CVPipeline
from friday.frame_buffer import FrameBuffer, FrameEntry
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)


class CameraManager:
    """Always-on camera manager isolated from audio and agent event loops."""

    def __init__(self, frame_buffer: Optional[FrameBuffer] = None, stop_event: Optional[threading.Event] = None) -> None:
        cfg = ensure_config().get("camera", {})
        self.enabled = bool(cfg.get("enabled", True))
        self.proactive_events = bool(cfg.get("proactive_events", True))
        self.available = False

        self._buffer = frame_buffer or FrameBuffer(max_frames=30, max_memory_mb=50)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = stop_event or threading.Event()
        self._pipeline = CVPipeline()
        self._capture = None
        self._frame_id = 0
        self._target_fps = 15.0

    def start(self) -> None:
        if not self.enabled:
            logger.info("Camera manager disabled by config")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_capture_loop, name="FridayCameraThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_available(self) -> bool:
        return self.available

    def get_latest_frame(self):
        snapshot = self._buffer.get_snapshot()
        return snapshot.raw_frame if snapshot else None

    def get_buffer(self) -> FrameBuffer:
        return self._buffer

    def show_camera_feed(self) -> bool:
        """Display live camera feed until any keypress (explicit user-trigger only)."""
        if not self.available or self._capture is None:
            return False
        try:
            import cv2
        except Exception:
            return False

        while True:
            ok, frame = self._capture.read()
            if not ok:
                break
            cv2.imshow("Friday Camera", frame)
            if cv2.waitKey(1) != -1:
                break
        cv2.destroyWindow("Friday Camera")
        return True

    def _open_camera(self):
        try:
            import cv2
        except Exception as exc:
            logger.warning("OpenCV unavailable for camera manager: %s", exc)
            return None

        for idx in (0, 1, 2):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                logger.info("Camera manager connected on index %s", idx)
                return cap
            cap.release()
        return None

    def _publish_camera_event(self, payload: dict) -> None:
        if not self.proactive_events:
            return
        try:
            # camera thread is isolated; safe one-shot event loop for non-blocking best-effort publish
            asyncio.run(get_bus().publish("camera.events", payload))
        except Exception:
            pass

    def _run_capture_loop(self) -> None:
        self._capture = self._open_camera()
        if self._capture is None:
            self.available = False
            logger.warning("No camera found at indices 0/1/2. Camera pipeline disabled.")
            return

        self.available = True
        last_frame_ts = time.monotonic()

        while not self._stop_event.is_set():
            ok, frame = self._capture.read()
            if not ok:
                time.sleep(0.05)
                continue

            self._frame_id += 1
            now = time.time()
            entry = FrameEntry(frame_id=self._frame_id, timestamp=now, raw_frame=frame)
            self._buffer.push(entry)

            labels, events = self._pipeline.process_frame(frame, now)
            self._buffer.update_labels(self._frame_id, labels)
            for event in events:
                self._publish_camera_event(event)

            cpu = psutil.cpu_percent(interval=None)
            if cpu > 80:
                self._target_fps = max(5.0, self._target_fps - 2.0)
            elif self._target_fps < 15.0:
                self._target_fps = min(15.0, self._target_fps + 1.0)

            frame_interval = 1.0 / max(self._target_fps, 1.0)
            elapsed = time.monotonic() - last_frame_ts
            sleep_for = max(0.0, frame_interval - elapsed)
            if sleep_for > 0:
                time.sleep(sleep_for)
            last_frame_ts = time.monotonic()

        try:
            self._capture.release()
        except Exception:
            pass
