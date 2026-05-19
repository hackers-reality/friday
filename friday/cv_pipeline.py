"""Lightweight computer vision pass for every captured frame.

Detectors:
- MediaPipe FaceDetection (fast)
- MediaPipe Hands (fast)
- YOLOv8n object detection on CPU

The pipeline degrades gracefully if detector initialization fails.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from friday._paths import PROJECT_ROOT
from friday.frame_buffer import CVLabels, FaceDetection, HandDetection, ObjectDetection
from friday.logging_utils import configure_logging


logger = configure_logging(__name__)


def _bbox_overlap_ratio(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = float((ix2 - ix1) * (iy2 - iy1))
    area_a = float(max(1, (ax2 - ax1) * (ay2 - ay1)))
    area_b = float(max(1, (bx2 - bx1) * (by2 - by1)))
    return inter / min(area_a, area_b)


class CVPipeline:
    """Runs fast CV detectors and emits proactive event payloads."""

    def __init__(self) -> None:
        self._face_detector = None
        self._hands_detector = None
        self._yolo_model = None
        self._face_absence_streak = 0
        self._last_face_ts = 0.0

        self._init_face_detector()
        self._init_hands_detector()
        self._init_yolo()

    def _init_face_detector(self) -> None:
        try:
            import mediapipe as mp

            self._face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5,
            )
        except Exception as exc:
            logger.warning("MediaPipe FaceDetection unavailable: %s", exc)

    def _init_hands_detector(self) -> None:
        try:
            import mediapipe as mp

            self._hands_detector = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as exc:
            logger.warning("MediaPipe Hands unavailable: %s", exc)

    def _init_yolo(self) -> None:
        try:
            from ultralytics import YOLO

            models_dir = Path(PROJECT_ROOT) / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            target = models_dir / "yolov8n.pt"

            if target.exists():
                self._yolo_model = YOLO(str(target))
                return

            # Triggers first-run download via ultralytics. Then persist in project cache.
            transient = YOLO("yolov8n.pt")
            self._yolo_model = transient
            try:
                source_path = Path(str(getattr(transient, "ckpt_path", "")))
                if source_path.exists():
                    target.write_bytes(source_path.read_bytes())
                    self._yolo_model = YOLO(str(target))
            except Exception:
                # Keep transient model if local copy fails.
                pass
        except Exception as exc:
            logger.warning("YOLOv8n unavailable: %s", exc)

    def process_frame(self, frame: np.ndarray, timestamp: float) -> Tuple[CVLabels, List[Dict[str, object]]]:
        faces = self._detect_faces(frame)
        hands = self._detect_hands(frame)
        objects = self._detect_objects(frame)
        labels = CVLabels(faces=faces, hands=hands, objects=objects)
        events = self._detect_events(labels, timestamp)
        return labels, events

    def _detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        if self._face_detector is None:
            return []
        try:
            import cv2

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out = self._face_detector.process(rgb)
            if not out.detections:
                return []

            faces: List[FaceDetection] = []
            for detection in out.detections:
                rel = detection.location_data.relative_bounding_box
                x1 = max(0, int(rel.xmin * w))
                y1 = max(0, int(rel.ymin * h))
                x2 = min(w, int((rel.xmin + rel.width) * w))
                y2 = min(h, int((rel.ymin + rel.height) * h))
                keypoints = []
                for kp in detection.location_data.relative_keypoints:
                    keypoints.append((float(kp.x), float(kp.y)))
                faces.append(
                    FaceDetection(
                        bbox=(x1, y1, x2, y2),
                        confidence=float(detection.score[0]) if detection.score else 0.0,
                        landmarks=keypoints,
                    )
                )
            return faces
        except Exception:
            return []

    def _detect_hands(self, frame: np.ndarray) -> List[HandDetection]:
        if self._hands_detector is None:
            return []
        try:
            import cv2

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out = self._hands_detector.process(rgb)
            if not out.multi_hand_landmarks:
                return []

            hands: List[HandDetection] = []
            handedness = out.multi_handedness or []
            for idx, lm_group in enumerate(out.multi_hand_landmarks):
                xs = [lm.x for lm in lm_group.landmark]
                ys = [lm.y for lm in lm_group.landmark]
                x1 = max(0, int(min(xs) * w))
                y1 = max(0, int(min(ys) * h))
                x2 = min(w, int(max(xs) * w))
                y2 = min(h, int(max(ys) * h))
                label = "unknown"
                conf = 0.0
                if idx < len(handedness) and handedness[idx].classification:
                    cls = handedness[idx].classification[0]
                    label = cls.label.lower()
                    conf = float(cls.score)
                hands.append(
                    HandDetection(
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        handedness=label,
                        landmarks=[(float(lm.x), float(lm.y)) for lm in lm_group.landmark],
                    )
                )
            return hands
        except Exception:
            return []

    def _detect_objects(self, frame: np.ndarray) -> List[ObjectDetection]:
        if self._yolo_model is None:
            return []
        try:
            results = self._yolo_model.predict(source=frame, verbose=False, conf=0.35, device="cpu")
            objects: List[ObjectDetection] = []
            if not results:
                return objects

            names = getattr(results[0], "names", {}) or {}
            boxes = getattr(results[0], "boxes", None)
            if boxes is None:
                return objects

            xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy
            confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else boxes.conf
            clss = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else boxes.cls

            for bbox, conf, cls_idx in zip(xyxy, confs, clss):
                x1, y1, x2, y2 = [int(v) for v in bbox]
                class_name = str(names.get(int(cls_idx), f"class_{int(cls_idx)}"))
                objects.append(ObjectDetection(bbox=(x1, y1, x2, y2), class_name=class_name, confidence=float(conf)))
            return objects
        except Exception:
            return []

    def _detect_events(self, labels: CVLabels, timestamp: float) -> List[Dict[str, object]]:
        events: List[Dict[str, object]] = []

        if labels.faces:
            if self._face_absence_streak >= 5:
                events.append(
                    {
                        "event_type": "person_entered",
                        "timestamp": timestamp,
                        "faces_count": len(labels.faces),
                        "after_absence_frames": self._face_absence_streak,
                    }
                )
            self._face_absence_streak = 0
            self._last_face_ts = timestamp
        else:
            self._face_absence_streak += 1
            if self._last_face_ts > 0 and (timestamp - self._last_face_ts) > 30:
                events.append(
                    {
                        "event_type": "no_one_detected",
                        "timestamp": timestamp,
                        "absence_seconds": round(timestamp - self._last_face_ts, 2),
                    }
                )
                # Prevent duplicate spam each frame.
                self._last_face_ts = timestamp

        if labels.hands and labels.objects:
            for hand in labels.hands:
                for obj in labels.objects:
                    if _bbox_overlap_ratio(hand.bbox, obj.bbox) >= 0.30:
                        events.append(
                            {
                                "event_type": "object_in_hand",
                                "timestamp": timestamp,
                                "object": obj.class_name,
                                "confidence": obj.confidence,
                            }
                        )
                        break

        return events
