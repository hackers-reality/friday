"""Thread-safe rolling frame buffer for camera observations.

Stores recent frames with CV labels and enforces a memory budget by evicting
oldest entries.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, List, Optional, Tuple

import numpy as np


@dataclass(slots=True)
class FaceDetection:
    bbox: Tuple[int, int, int, int]
    confidence: float
    landmarks: List[Tuple[float, float]]


@dataclass(slots=True)
class HandDetection:
    bbox: Tuple[int, int, int, int]
    confidence: float
    handedness: str
    landmarks: List[Tuple[float, float]]


@dataclass(slots=True)
class ObjectDetection:
    bbox: Tuple[int, int, int, int]
    class_name: str
    confidence: float


@dataclass(slots=True)
class CVLabels:
    faces: List[FaceDetection]
    hands: List[HandDetection]
    objects: List[ObjectDetection]


@dataclass(slots=True)
class FrameEntry:
    frame_id: int
    timestamp: float
    raw_frame: np.ndarray
    cv_labels: Optional[CVLabels] = None

    @property
    def bytes_size(self) -> int:
        return int(self.raw_frame.nbytes)


class FrameBuffer:
    """Rolling frame buffer with memory cap and lock-based thread safety."""

    def __init__(self, max_frames: int = 30, max_memory_mb: int = 50) -> None:
        self.max_frames = int(max_frames)
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self._entries: Deque[FrameEntry] = deque()
        self._bytes = 0
        self._lock = Lock()

    def push(self, entry: FrameEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            self._bytes += entry.bytes_size
            self._evict_if_needed()

    def update_labels(self, frame_id: int, labels: CVLabels) -> None:
        with self._lock:
            for idx in range(len(self._entries) - 1, -1, -1):
                if self._entries[idx].frame_id == frame_id:
                    self._entries[idx].cv_labels = labels
                    break

    def get_latest(self, n: int = 1) -> List[FrameEntry]:
        with self._lock:
            if n <= 0:
                return []
            return list(self._entries)[-n:]

    def get_snapshot(self) -> Optional[FrameEntry]:
        with self._lock:
            if not self._entries:
                return None
            return self._entries[-1]

    def _evict_if_needed(self) -> None:
        while self._entries and (len(self._entries) > self.max_frames or self._bytes > self.max_memory_bytes):
            oldest = self._entries.popleft()
            self._bytes -= oldest.bytes_size
