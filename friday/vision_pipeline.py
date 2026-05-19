"""
FRIDAY Vision Pipeline — unified detection engine combining MediaPipe, YOLO, and CV analysis.
All detectors run in parallel via ThreadPoolExecutor. Graceful degradation if models missing.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import time
import os
import json

import numpy as np

from friday._paths import FRIDAY_MEMORY

_MODELS_DIR = os.path.join(FRIDAY_MEMORY, "models")
_VISION_CONFIG = {
    "enable_mediapipe_hands": True,
    "enable_mediapipe_pose": True,
    "enable_mediapipe_face": True,
    "enable_yolo": True,
    "enable_cv_analysis": True,
    "yolo_confidence_threshold": 0.4,
    "mediapipe_confidence_threshold": 0.5,
    "max_workers": 4,
}


def _ensure_model_dirs():
    os.makedirs(_MODELS_DIR, exist_ok=True)


def _model_path(name: str) -> str:
    return os.path.join(_MODELS_DIR, name)


COCO_YOLO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]

ANIMAL_CLASSES = {"bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"}
VEHICLE_CLASSES = {"bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat"}


# ─── Per-detector state (lazy-init) ──────────────────────────

class _DetectorState:
    hands = None
    pose = None
    face_detection = None
    yolo_net = None
    yolo_available = False
    previous_frame_gray = None


_detector = _DetectorState()


# ─── MediaPipe Hands ─────────────────────────────────────────

def _detect_hands(frame, config: dict) -> List[Dict]:
    if not config.get("enable_mediapipe_hands", True):
        return []
    try:
        import mediapipe as mp
        if _detector.hands is None:
            _detector.hands = mp.solutions.hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                min_detection_confidence=config.get("mediapipe_confidence_threshold", 0.5),
            )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = _detector.hands.process(rgb)

        if not results.multi_hand_landmarks:
            return []

        hands_data = []
        for hand_landmarks, handedness in zip(
            results.multi_hand_landmarks, results.multi_handedness
        ):
            label = handedness.classification[0].label if handedness.classification else "Unknown"
            landmarks = [
                {"x": lm.x, "y": lm.y, "z": lm.z}
                for lm in hand_landmarks.landmark
            ]

            fingers_up = _count_fingers_up(hand_landmarks.landmark)
            holding = _detect_holding(hand_landmarks.landmark)

            hands_data.append({
                "handedness": label,
                "landmarks": landmarks,
                "fingers_up": fingers_up,
                "holding_object": holding,
            })
        return hands_data
    except ImportError:
        return []
    except Exception:
        return []


def _count_fingers_up(landmarks) -> int:
    tips = [4, 8, 12, 16, 20]
    count = 0
    for tip in tips:
        if tip == 4:
            if landmarks[tip].x < landmarks[tip - 1].x:
                count += 1
        else:
            if landmarks[tip].y < landmarks[tip - 2].y:
                count += 1
    return count


def _detect_holding(landmarks) -> bool:
    tips_flexed = 0
    for tip in [8, 12, 16, 20]:
        if landmarks[tip].y > landmarks[tip - 2].y:
            tips_flexed += 1
    return tips_flexed >= 3


# ─── MediaPipe Pose ──────────────────────────────────────────

def _detect_pose(frame, config: dict) -> List[Dict]:
    if not config.get("enable_mediapipe_pose", True):
        return []
    try:
        import mediapipe as mp
        if _detector.pose is None:
            _detector.pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                min_detection_confidence=config.get("mediapipe_confidence_threshold", 0.5),
            )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = _detector.pose.process(rgb)

        if not results.pose_landmarks:
            return []

        landmarks = [
            {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
            for lm in results.pose_landmarks.landmark
        ]
        return [{"landmarks": landmarks}]
    except ImportError:
        return []
    except Exception:
        return []


# ─── MediaPipe Face Detection ────────────────────────────────

def _detect_faces_mediapipe(frame, config: dict) -> List[Dict]:
    if not config.get("enable_mediapipe_face", True):
        return []
    try:
        import mediapipe as mp
        if _detector.face_detection is None:
            _detector.face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=config.get("mediapipe_confidence_threshold", 0.5),
            )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = _detector.face_detection.process(rgb)

        if not results.detections:
            return []

        h, w = frame.shape[:2]
        faces = []
        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box
            x1 = int(bbox.xmin * w)
            y1 = int(bbox.ymin * h)
            x2 = int((bbox.xmin + bbox.width) * w)
            y2 = int((bbox.ymin + bbox.height) * h)
            faces.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": round(detection.score[0], 3),
            })
        return faces
    except ImportError:
        return []
    except Exception:
        return []


# ─── YOLO via OpenCV DNN ─────────────────────────────────────

def _detect_yolo(frame, config: dict) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    if not config.get("enable_yolo", True):
        return [], [], []
    try:
        import cv2
    except ImportError:
        return [], [], []

    if _detector.yolo_net is None:
        _detector.yolo_available = _init_yolo()

    if not _detector.yolo_available:
        return _detect_ssd_mobilenet(frame, config)

    try:
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        _detector.yolo_net.setInput(blob)
        outputs = _detector.yolo_net.forward(_detector.yolo_net.getUnconnectedOutLayersNames())

        objects = []
        animals = []
        people = []

        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence < config.get("yolo_confidence_threshold", 0.4):
                    continue
                label = COCO_YOLO_CLASSES[class_id] if class_id < len(COCO_YOLO_CLASSES) else f"class_{class_id}"
                cx, cy, bw, bh = detection[0:4]
                cx, cy, bw, bh = cx * w, cy * h, bw * w, bh * h
                x1 = int(cx - bw / 2)
                y1 = int(cy - bh / 2)
                x2 = int(cx + bw / 2)
                y2 = int(cy + bh / 2)

                item = {"label": label, "confidence": round(confidence, 3), "bbox": [x1, y1, x2, y2]}

                if label == "person":
                    people.append(item)
                elif label in ANIMAL_CLASSES:
                    animals.append(item)
                else:
                    objects.append(item)

        return objects, animals, people
    except Exception:
        return _detect_ssd_mobilenet(frame, config)


def _init_yolo() -> bool:
    try:
        import cv2
        model_path = _model_path("yolov5s.onnx")
        if os.path.exists(model_path):
            _detector.yolo_net = cv2.dnn.readNetFromONNX(model_path)
            return True
        model_path = _model_path("yolov8n.onnx")
        if os.path.exists(model_path):
            _detector.yolo_net = cv2.dnn.readNetFromONNX(model_path)
            return True
        return False
    except Exception:
        return False


def _init_ssd_mobilenet():
    prototxt = _model_path("MobileNetSSD_deploy.prototxt")
    caffemodel = _model_path("MobileNetSSD_deploy.caffemodel")
    if os.path.exists(prototxt) and os.path.exists(caffemodel):
        try:
            import cv2
            return cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
        except Exception:
            return None
    return None


SSD_CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat", "bottle",
    "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse",
    "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor",
]


def _detect_ssd_mobilenet(frame, config: dict) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    try:
        import cv2
        net = _init_ssd_mobilenet()
        if net is None:
            return [], [], []

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()

        objects = []
        animals = []
        people = []

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < config.get("yolo_confidence_threshold", 0.4):
                continue
            cls_id = int(detections[0, 0, i, 1])
            if cls_id >= len(SSD_CLASSES):
                continue
            label = SSD_CLASSES[cls_id]
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2_w, y2_h = [float(x) for x in box]
            item = {"label": label, "confidence": round(confidence, 3), "bbox": [x1, y1, x2_w, y2_h]}

            if label == "person":
                people.append(item)
            elif label in ANIMAL_CLASSES:
                animals.append(item)
            else:
                objects.append(item)

        return objects, animals, people
    except Exception:
        return [], [], []


# ─── Basic CV Analysis ───────────────────────────────────────

def _analyze_scene_cv(frame) -> Dict:
    try:
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]

        brightness = float(np.mean(gray)) / 255.0

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        is_blurry = laplacian_var < 100

        if _detector.previous_frame_gray is not None:
            diff = cv2.absdiff(_detector.previous_frame_gray, gray)
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            motion_pct = float(np.sum(thresh > 0)) / float(thresh.size)
            motion_detected = motion_pct > 0.01
        else:
            motion_detected = False
            motion_pct = 0.0

        _detector.previous_frame_gray = gray

        return {
            "brightness": round(brightness, 3),
            "is_blurry": is_blurry,
            "blur_score": round(laplacian_var, 1),
            "motion_detected": motion_detected,
            "motion_magnitude": round(motion_pct, 4),
            "width": w,
            "height": h,
        }
    except Exception:
        return {
            "brightness": 0.5,
            "is_blurry": False,
            "motion_detected": False,
            "motion_magnitude": 0.0,
        }


# ─── Helper: Import cv2 once ─────────────────────────────────

def _import_cv2():
    global cv2
    import cv2 as _cv2
    cv2 = _cv2


# ─── VisionPipeline Class ────────────────────────────────────

class VisionPipeline:
    """Unified vision detection engine.

    Runs MediaPipe, YOLO, and CV analysis detectors in parallel.
    Gracefully degrades if optional dependencies (mediapipe) are missing.
    """

    def __init__(self, config: Optional[Dict] = None):
        _ensure_model_dirs()
        self.config = {**_VISION_CONFIG, **(config or {})}
        self._executor = ThreadPoolExecutor(max_workers=self.config.get("max_workers", 4))
        self._latency: Dict[str, float] = {}
        _import_cv2()
        self._previous_frame_gray = None

    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """Run all detectors in parallel on a frame. Returns structured result."""
        start = time.perf_counter()
        latencies: Dict[str, float] = {}
        results: Dict[str, Any] = {
            "people": [],
            "hands": [],
            "faces": [],
            "objects": [],
            "animals": [],
            "scene": {},
        }

        futures = {}

        tasks = [
            ("hands", lambda: _detect_hands(frame, self.config)),
            ("pose", lambda: self._pose_to_people(frame)),
            ("faces", lambda: _detect_faces_mediapipe(frame, self.config)),
            ("yolo", lambda: self._yolo_detection(frame)),
            ("cv", lambda: _analyze_scene_cv(frame)),
        ]

        for name, fn in tasks:
            t0 = time.perf_counter()
            fut = self._executor.submit(fn)
            futures[name] = (fut, t0)

        for name, (fut, t0) in futures.items():
            try:
                result = fut.result(timeout=30)
                latencies[name] = round((time.perf_counter() - t0) * 1000, 1)
                if name == "hands":
                    results["hands"] = result
                elif name == "pose":
                    results["people"] = result
                elif name == "faces":
                    results["faces"] = result
                elif name == "yolo":
                    yolo_objects, yolo_animals, yolo_people = result
                    results["objects"] = yolo_objects
                    results["animals"] = yolo_animals
                    results["people"].extend(yolo_people)
                elif name == "cv":
                    results["scene"] = result
            except Exception:
                latencies[name] = -1

        results["people"] = self._deduplicate_people(results.get("people", []))
        total_ms = round((time.perf_counter() - start) * 1000, 1)
        latencies["total"] = total_ms
        results["latency_ms"] = latencies
        self._latency = latencies

        return results

    def _pose_to_people(self, frame) -> List[Dict]:
        pose_results = _detect_pose(frame, self.config)
        people = []
        for p in pose_results:
            people.append({
                "bbox": [],
                "face_confidence": None,
                "pose_landmarks": p.get("landmarks", []),
            })
        return people

    def _yolo_detection(self, frame) -> Tuple:
        return _detect_yolo(frame, self.config)

    def _deduplicate_people(self, people: List[Dict]) -> List[Dict]:
        if len(people) <= 1:
            return people
        deduped = []
        seen = []
        for p in people:
            bbox = p.get("bbox", [])
            if not bbox:
                deduped.append(p)
                continue
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            is_dup = False
            for s_cx, s_cy in seen:
                if abs(cx - s_cx) < 50 and abs(cy - s_cy) < 50:
                    is_dup = True
                    break
            if not is_dup:
                seen.append((cx, cy))
                deduped.append(p)
        return deduped

    def get_human_readable(self, result: Dict) -> str:
        """Convert detection result to a natural language string."""
        parts = []
        people = result.get("people", [])
        hands = result.get("hands", [])
        faces = result.get("faces", [])
        objects = result.get("objects", [])
        animals = result.get("animals", [])
        scene = result.get("scene", {})

        people_count = len(people) or len(faces) or sum(
            1 for o in result.get("objects", []) if o.get("label") == "person"
        )
        if people_count > 0:
            s = f"I can see {people_count} person" + ("s" if people_count > 1 else "")
            details = []
            for hand in hands:
                hlabel = hand.get("handedness", "").lower()
                fingers = hand.get("fingers_up", 0)
                holding = hand.get("holding_object", False)
                hand_desc = []
                if hlabel:
                    hand_desc.append(f"your {hlabel} hand")
                if fingers > 0:
                    hand_desc.append(f"showing {fingers} finger{'s' if fingers > 1 else ''}")
                if holding:
                    hand_desc.append("holding something")
                if hand_desc:
                    details.append(" ".join(hand_desc))
            if details:
                s += ". " + ". ".join(details)
            parts.append(s)

        if animals:
            animal_counts = {}
            for a in animals:
                label = a.get("label", "animal")
                animal_counts[label] = animal_counts.get(label, 0) + 1
            animal_desc = []
            for label, count in animal_counts.items():
                animal_desc.append(f"{count} {label}" + ("s" if count > 1 else ""))
            parts.append("There's " + ", and ".join(animal_desc) + ".")

        if objects:
            obj_counts = {}
            for o in objects:
                label = o.get("label", "object")
                obj_counts[label] = obj_counts.get(label, 0) + 1
            obj_desc = []
            for label, count in sorted(obj_counts.items(), key=lambda x: -x[1])[:5]:
                prefix = "a" if label[0] in "aeiou" else "a"
                if count > 1:
                    obj_desc.append(f"{count} {label}s")
                else:
                    obj_desc.append(f"{prefix} {label}")
            parts.append("I can see " + ", ".join(obj_desc) + ".")

        brightness = scene.get("brightness", 0.5)
        if brightness < 0.2:
            parts.append("The room is very dark.")
        elif brightness < 0.4:
            parts.append("The room is dimly lit.")
        elif brightness > 0.7:
            parts.append("The room is well-lit.")
        else:
            parts.append("The room lighting is moderate.")

        if scene.get("is_blurry", False):
            parts.append("The camera feed is blurry.")

        if scene.get("motion_detected", False):
            parts.append("There is motion in the frame.")

        if parts:
            return " ".join(parts)
        return "I don't see anything significant in the camera feed."

    @property
    def latency(self) -> Dict[str, float]:
        return dict(self._latency)


# Reset previous frame (call when switching camera/scene)
def reset_motion_detection():
    _detector.previous_frame_gray = None
