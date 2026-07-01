"""
FRIDAY CV Engine — background camera capture with object detection, scene labeling.
All analysis runs in background; results are consumed by the LLM only, not shown to the user.
Supports multiple detection backends:
  - OpenCV DNN (MobileNet-SSD, COCO 80 classes) [primary]
  - HOG people detector [built-in]
  - Frame differencing motion detection [fallback]
  - Gemini Vision API [optional, rich scene description]
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import os
import threading
import time
import base64
import io
import re
from pathlib import Path
import urllib.request
import urllib.error
import shutil

import contextlib

@contextlib.contextmanager
def _suppress_opencv_stderr():
    """Temporarily redirect stderr to nul to suppress OpenCV DShow noise."""
    import sys
    old_stderr = sys.stderr
    try:
        with open(os.devnull, 'w') as null:
            sys.stderr = null
            yield
    finally:
        sys.stderr = old_stderr

try:
    import cv2
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        pass
except Exception:
    pass

from friday._paths import FRIDAY_MEMORY
from friday.vision_pipeline import VisionPipeline, reset_motion_detection

# Try to load .env so NIM keys are available without manual export
try:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            m_v = re.match(r'^NVIDIA_VISION_API_KEY=(.+)', line.strip())
            if m_v:
                val = m_v.group(1).strip().strip("\"").strip("'")
                if "NVIDIA_VISION_API_KEY" not in os.environ:
                    os.environ["NVIDIA_VISION_API_KEY"] = val
        for line in env_path.read_text().splitlines():
            m = re.match(r'^NVIDIA_NIM_API_KEY=(.+)', line.strip())
            if m:
                val = m.group(1).strip().strip("\"").strip("'")
                if "NVIDIA_NIM_API_KEY" not in os.environ:
                    os.environ["NVIDIA_NIM_API_KEY"] = val
                break
except Exception:
    pass

_CV_DIR = os.path.join(FRIDAY_MEMORY, "cv")
_MODELS_DIR = os.path.join(_CV_DIR, "models")
_CV_STATE_FILE = os.path.join(_CV_DIR, "cv_state.json")

# MobileNet-SSD COCO class names (80 classes)
COCO_CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat", "bottle",
    "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse",
    "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor",
    "apple", "backpack", "banana", "baseball bat", "baseball glove", "bear",
    "bed", "bench", "book", "bowl", "broccoli", "cake", "carrot", "cell phone",
    "clock", "cup", "donut", "elephant", "fire hydrant", "fork", "frisbee",
    "giraffe", "hair drier", "handbag", "hot dog", "keyboard", "kite", "knife",
    "laptop", "microwave", "mouse", "orange", "oven", "parking meter", "pizza",
    "refrigerator", "remote", "sandwich", "scissors", "sink", "skateboard",
    "skis", "snowboard", "spoon", "sports ball", "stop sign", "suitcase",
    "surfboard", "tennis racket", "tie", "toaster", "toilet", "toothbrush",
    "traffic light", "truck", "umbrella", "vase", "wine glass", "zebra",
]

# Model file URLs (OpenCV DNN format)
MOBILENET_PROTOTXT_URL = (
    "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/"
    "master/deploy.prototxt"
)
MOBILENET_CAFFEMODEL_URL = (
    "https://github.com/chuanqi305/MobileNet-SSD/raw/"
    "master/mobilenet_iter_73000.caffemodel"
)


# ─── Shared State ──────────────────────────────────────────

_cv_lock = threading.Lock()
_cv_state: Dict[str, Any] = {
    "camera_active": False,
    "camera_index": 0,
    "capture_interval": 2.0,
    "last_capture": None,
    "last_frame_data": None,
    "last_analysis": {},
    "detections": [],
    "motion_detected": False,
    "scene_description": "",
    "human_readable_scene": "",
    "people_count": 0,
    "objects_found": [],
    "hands_detected": [],
    "faces_detected": 0,
    "face_expressions": [],
    "animals_detected": [],
    "scene_stats": {},
    "pipeline_latency_ms": {},
    "error": None,
    "stats": {},
    "last_seen": {},          # label → {"camera_index": int, "timestamp": str}
}
_cv_thread: Optional[threading.Thread] = None
_cv_stop_event = threading.Event()
_camera_cap = None
_vision_pipeline: Optional[VisionPipeline] = None
_vision_results: Dict[str, Any] = {}
_vision_lock = threading.Lock()

# ─── Cycling State ──────────────────────────────────────────
_cycling_active = False
_cycling_thread: Optional[threading.Thread] = None
_cycling_stop_event = threading.Event()
_cycling_interval = 5.0


# ─── Model Management ──────────────────────────────────────

def _ensure_model_dirs():
    os.makedirs(_MODELS_DIR, exist_ok=True)


def _model_path(name: str) -> str:
    return os.path.join(_MODELS_DIR, name)


def _download_model(url: str, dest_name: str) -> bool:
    """Download a model file if it doesn't exist. Returns True if available."""
    dest = _model_path(dest_name)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    try:
        print(f"[CV] Downloading model {dest_name}...")
        urllib.request.urlretrieve(url, dest)
        if os.path.getsize(dest) > 1000:
            print(f"[CV] Model {dest_name} downloaded ({os.path.getsize(dest)} bytes)")
            return True
        return False
    except Exception as e:
        print(f"[CV] Failed to download {dest_name}: {e}")
        return False


def _ensure_models() -> bool:
    """Ensure MobileNet-SSD model files are available. Returns True if loaded OK.
    
    Downloads are non-blocking — runs in a background thread so camera capture
    starts immediately even if models are missing. DNN detection will skip
    until models finish downloading.
    """
    _ensure_model_dirs()
    prototxt = _model_path("MobileNetSSD_deploy.prototxt")
    caffemodel = _model_path("MobileNetSSD_deploy.caffemodel")

    if os.path.exists(prototxt) and os.path.exists(caffemodel):
        return True

    # Download in background — don't block camera startup
    def _download_job():
        _download_model(MOBILENET_PROTOTXT_URL, "MobileNetSSD_deploy.prototxt")
        _download_model(MOBILENET_CAFFEMODEL_URL, "MobileNetSSD_deploy.caffemodel")
        global _dnn_net
        try:
            import cv2
            p = _model_path("MobileNetSSD_deploy.prototxt")
            c = _model_path("MobileNetSSD_deploy.caffemodel")
            if os.path.exists(p) and os.path.exists(c):
                _dnn_net = cv2.dnn.readNetFromCaffe(p, c)
        except Exception:
            pass

    threading.Thread(target=_download_job, daemon=True, name="cv-model-download").start()
    return False


# ─── DNN Object Detection ──────────────────────────────────

_dnn_net = None


def _init_dnn() -> bool:
    """Initialize the DNN object detector. Returns True if ready."""
    global _dnn_net
    if _dnn_net is not None:
        return True
    try:
        import cv2
        prototxt = _model_path("MobileNetSSD_deploy.prototxt")
        caffemodel = _model_path("MobileNetSSD_deploy.caffemodel")
        if os.path.exists(prototxt) and os.path.exists(caffemodel):
            _dnn_net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
            return True
    except Exception:
        pass
    return False


def _detect_objects_dnn(frame) -> List[Dict[str, Any]]:
    """Run DNN object detection on a frame. Returns list of detections."""
    global _dnn_net
    if _dnn_net is None:
        if not _init_dnn():
            return []
    try:
        import cv2
        import numpy as np
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        _dnn_net.setInput(blob)
        detections = _dnn_net.forward()
        results = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence > 0.4:
                cls_id = int(detections[0, 0, i, 1])
                label = COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else f"class_{cls_id}"
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                results.append({
                    "label": label,
                    "confidence": round(confidence, 3),
                    "bbox": [float(x) for x in box],
                    "class_id": cls_id,
                })
        return results
    except Exception:
        return []


# ─── HOG People Detection ──────────────────────────────────

_hog_detector = None


def _detect_people_hog(frame) -> List[Dict]:
    """Detect people using OpenCV HOG descriptor (built-in)."""
    global _hog_detector
    try:
        import cv2
        if _hog_detector is None:
            _hog_detector = cv2.HOGDescriptor()
            _hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        boxes, weights = _hog_detector.detectMultiScale(
            frame, winStride=(4, 4), padding=(8, 8), scale=1.05
        )
        results = []
        for (x, y, w, h), weight in zip(boxes, weights):
            results.append({
                "label": "person",
                "confidence": round(float(weight), 3),
                "bbox": [float(x), float(y), float(x + w), float(y + h)],
            })
        return results
    except Exception:
        return []


# ─── Motion Detection ──────────────────────────────────────

_previous_frame_gray = None


def _detect_motion(frame) -> Tuple[bool, float]:
    """Simple frame differencing motion detection. Returns (motion_detected, magnitude)."""
    global _previous_frame_gray
    try:
        import cv2
        import numpy as np
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if _previous_frame_gray is None:
            _previous_frame_gray = gray
            return False, 0.0

        diff = cv2.absdiff(_previous_frame_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        motion_pct = float(np.sum(thresh > 0)) / float(thresh.size)
        _previous_frame_gray = gray
        return motion_pct > 0.01, motion_pct
    except Exception:
        return False, 0.0


# ─── Scene Analysis ────────────────────────────────────────

def _analyze_scene(frame) -> Dict[str, Any]:
    """Basic scene analysis: brightness, contrast, dominant colors."""
    try:
        import cv2
        import numpy as np
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # Dominant colors (simple quantization)
        pixels = frame.reshape(-1, 3)
        pixel_float = pixels.astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixel_float, 4, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        colors = []
        for i, center in enumerate(centers):
            count = int(np.sum(labels == i))
            b, g, r = int(center[0]), int(center[1]), int(center[2])
            colors.append({"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}", "pixels": count})

        # Light level assessment
        if brightness < 50:
            lighting = "dark"
        elif brightness < 100:
            lighting = "dim"
        elif brightness < 180:
            lighting = "well-lit"
        else:
            lighting = "bright"

        return {
            "width": w,
            "height": h,
            "brightness": round(brightness, 1),
            "contrast": round(contrast, 1),
            "lighting": lighting,
            "dominant_colors": sorted(colors, key=lambda c: -c["pixels"])[:3],
        }
    except Exception:
        return {}


def _ask_nim_vl(question: str, frame_b64: str) -> str:
    """Ask a custom question about a camera frame using NVIDIA NIM vision-language model.

    Uses phi-4-multimodal-instruct (primary) → llama-3.2-11b-vision-instruct → nemotron-nano-12b-v2-vl.
    """
    from openai import OpenAI
    api_key = os.environ.get("NVIDIA_VISION_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_API_KEY")
    if not api_key:
        return ""
    client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1", timeout=8, max_retries=0)
    image_data = frame_b64.split(",")[-1] if "," in frame_b64 else frame_b64
    image_url = f"data:image/jpeg;base64,{image_data}"

    for model in (
        "nvidia/nemotron-nano-12b-v2-vl",
        "meta/llama-3.2-11b-vision-instruct",
    ):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }],
                max_tokens=512,
                temperature=0.3,
                timeout=10,
            )


            return response.choices[0].message.content.strip()
        except Exception:
            continue
    return ""


def _describe_scene_nim(frame_b64: str) -> str:
    """Wrapper: generic scene description via NIM VL model."""
    return _ask_nim_vl(
        "Describe this camera scene in 2-3 sentences. List every object, person, lighting condition, and activity visible.",
        frame_b64,
    )


# ─── Expression Detection (OpenCV Haar cascades) ──────────

_face_cascade = None
_eye_cascade = None
_smile_cascade = None
_expression_init_done = False


def _init_expression_models():
    """Load Haar cascades for face, eye, and smile detection.

    Uses OpenCV's built-in cascades — no external downloads needed.
    Thread-safe: only initializes once.
    """
    global _face_cascade, _eye_cascade, _smile_cascade, _expression_init_done
    if _expression_init_done:
        return
    try:
        import cv2
        _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        _eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        _smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
    except Exception:
        pass
    _expression_init_done = True


def _detect_expressions(frame) -> list[dict]:
    """Detect faces and classify expressions using OpenCV Haar cascades.

    Returns a list of dicts, one per detected face:
        {
            "bbox": [x, y, w, h],         # pixel coordinates
            "expression": str,             # "neutral"|"smiling"|"surprised"|"eyes_closed"
            "smile": bool,
            "eyes_open": bool,
            "confidence": float,           # approximate confidence (0-1)
        }
    Returns empty list if OpenCV is unavailable or no faces found.
    """
    _init_expression_models()
    if _face_cascade is None:
        return []
    try:
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        results = []
        for (x, y, w, h) in faces:
            face_roi_gray = gray[y:y+h, x:x+w]
            face_roi_color = frame[y:y+h, x:x+w]
            expression = "neutral"
            smile = False
            eyes_open = False

            # Detect smile
            if _smile_cascade is not None:
                smiles = _smile_cascade.detectMultiScale(
                    face_roi_gray, scaleFactor=1.7, minNeighbors=20, minSize=(25, 25)
                )
                smile = len(smiles) > 0

            # Detect eyes
            if _eye_cascade is not None:
                eyes = _eye_cascade.detectMultiScale(
                    face_roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
                )
                eyes_open = len(eyes) >= 1

            # Classify expression
            if smile and eyes_open:
                expression = "smiling"
            elif smile and not eyes_open:
                expression = "smiling"
            elif not eyes_open and not smile:
                expression = "eyes_closed"
            else:
                expression = "neutral"

            results.append({
                "bbox": [int(x), int(y), int(w), int(h)],
                "expression": expression,
                "smile": bool(smile),
                "eyes_open": bool(eyes_open),
                "confidence": round(min(1.0, max(0.5, 0.5 + (h - 60) / 200)), 3),
            })
        return results
    except Exception:
        return []


# ─── Camera Thread ─────────────────────────────────────────

def _camera_loop(camera_index: int, interval: float):
    """Background thread: captures frames, runs detection, updates state."""
    global _camera_cap, _cv_state, _previous_frame_gray, _dnn_net, _vision_pipeline, _vision_results
    _previous_frame_gray = None  # Reset motion detection

    try:
        import cv2
        import numpy as np
    except ImportError:
        with _cv_lock:
            _cv_state["error"] = "OpenCV not installed"
        return

    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        with _cv_lock:
            _cv_state["error"] = f"Cannot open camera {camera_index}"
        return

    _camera_cap = cap
    with _cv_lock:
        _cv_state["camera_active"] = True
        _cv_state["error"] = None

    # Non-blocking model init
    _ensure_models()
    _init_dnn()

    # Initialize VisionPipeline
    try:
        _vision_pipeline = VisionPipeline()
    except Exception:
        _vision_pipeline = None

    while not _cv_stop_event.is_set():
        # Brief wait before read — DShow on Windows can block the first
        # read indefinitely if the camera stream isn't fully initialized
        _cv_stop_event.wait(timeout=0.05)
        ret, frame = cap.read()
        if not ret:
            with _cv_lock:
                _cv_state["error"] = "Camera read failed"
            break
        # Dynamically auto-brighten dark/dim frames
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_b = float(np.mean(gray))
            if 1.5 < mean_b < 95.0:
                gamma = 0.4 if mean_b < 45.0 else 0.65
                invGamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                frame = cv2.LUT(frame, table)
        except Exception:
            pass

        # Encode frame for storage
        try:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_b64 = base64.b64encode(buffer).decode("utf-8")
        except Exception as exc:
            print(f"[CV ERR] encode: {exc}", flush=True)
            continue

        # Run analyses
        analysis: Dict[str, Any] = {}

        # Motion detection (fast)
        motion, motion_mag = _detect_motion(frame)

        # Scene stats
        stats = _analyze_scene(frame)

        # DNN object detection
        dnn_detections = _detect_objects_dnn(frame)

        # HOG people detection
        people = _detect_people_hog(frame)

        # Expression detection (OpenCV Haar cascades)
        face_expressions = _detect_expressions(frame)

        # Run VisionPipeline (parallel MediaPipe + YOLO) in background
        vision_result = {}
        if _vision_pipeline is not None:
            try:
                vision_result = _vision_pipeline.analyze_frame(frame)
                with _vision_lock:
                    _vision_results = vision_result
            except Exception:
                pass

        # Merge detections (dedupe by label+bbox proximity)
        all_detections = []
        seen_labels = set()
        for d in dnn_detections:
            label = d["label"]
            all_detections.append(d)
            if label != "background":
                seen_labels.add(label)
        for p in people:
            all_detections.append(p)
            seen_labels.add("person")

        # Add vision pipeline detections
        for obj in vision_result.get("objects", []):
            all_detections.append(obj)
        for animal in vision_result.get("animals", []):
            all_detections.append(animal)
        for person_obj in vision_result.get("people", []):
            if person_obj.get("bbox"):
                all_detections.append({
                    "label": "person",
                    "confidence": person_obj.get("face_confidence") or 0.5,
                    "bbox": person_obj["bbox"],
                })
                seen_labels.add("person")

        people_count = max(
            len(people) if people else 0,
            sum(1 for d in dnn_detections if d["label"] == "person"),
            len(vision_result.get("people", [])),
            len(vision_result.get("faces", [])),
        )

        # Build scene description
        desc_parts = []
        if people_count > 0:
            desc_parts.append(f"{people_count} person(s) detected")
        objects_found = [d["label"] for d in all_detections if d["label"] not in ("background", "person")]

        # Hands info from vision pipeline
        hands = vision_result.get("hands", [])
        for h in hands:
            hand_desc = f"{h.get('handedness', 'Unknown')} hand"
            fingers = h.get("fingers_up", 0)
            if fingers > 0:
                hand_desc += f" ({fingers} fingers up)"
            if h.get("holding_object"):
                hand_desc += " holding something"
            desc_parts.append(hand_desc)
            objects_found.append(hand_desc)

        if objects_found:
            from collections import Counter
            obj_counts = Counter(objects_found)
            obj_str = ", ".join(f"{n} {c}" if c > 1 else n for n, c in obj_counts.most_common(5))
            desc_parts.append(f"objects: {obj_str}")
        if motion:
            desc_parts.append("motion detected")
        if stats.get("lighting"):
            desc_parts.append(f"lighting: {stats['lighting']}")

        scene_desc = ". ".join(desc_parts) if desc_parts else "No significant objects detected"

        # Human-readable scene description from vision pipeline
        human_readable = ""
        if vision_result:
            try:
                human_readable = _vision_pipeline.get_human_readable(vision_result)
            except Exception:
                pass

        # Store frame + metadata FIRST so get_cv_frame_b64() returns immediately.
        # NIM description runs after (may take 8-16s with timeout) and updates scene_description.
        with _cv_lock:
            _cv_state["last_capture"] = datetime.now().isoformat()
            _cv_state["last_frame_data"] = frame_b64
            _cv_state["last_analysis"] = analysis
            _cv_state["detections"] = all_detections
            _cv_state["motion_detected"] = motion
            _cv_state["motion_magnitude"] = round(float(motion_mag), 4)
            _cv_state["people_count"] = people_count
            _cv_state["objects_found"] = list(set(objects_found))
            _cv_state["scene_description"] = human_readable or scene_desc
            _cv_state["human_readable_scene"] = human_readable
            _cv_state["hands_detected"] = [
                {"handedness": h.get("handedness"), "fingers_up": h.get("fingers_up"),
                 "holding_object": h.get("holding_object")}
                for h in hands
            ]
            _cv_state["faces_detected"] = max(len(vision_result.get("faces", [])), len(face_expressions))
            _cv_state["face_expressions"] = face_expressions
            _cv_state["animals_detected"] = vision_result.get("animals", [])
            _cv_state["scene_stats"] = vision_result.get("scene", {})
            _cv_state["pipeline_latency_ms"] = vision_result.get("latency_ms", {})
            _cv_state["stats"] = stats
            _cv_state["error"] = None

        # NIM vision description (skipped if no API key, runs after frame is stored)
        nim_key = os.environ.get("NVIDIA_VISION_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("NVIDIA_API_KEY") or os.environ.get("NIM_API_KEY")
        if nim_key:
            nim_desc = _describe_scene_nim(frame_b64)
            if nim_desc:
                with _cv_lock:
                    _cv_state["scene_description"] = nim_desc

        try:
            with open(_CV_STATE_FILE, "w") as f:
                state_save = {k: v for k, v in _cv_state.items() if k != "last_frame_data"}
                json.dump(state_save, f, indent=2, default=str)
        except Exception:
            pass

        # Show live feed window if requested
        _was_feed_active = getattr(_camera_loop, "_feed_was_active", False)
        if _cv_feed_active:
            try:
                import cv2
                cv2.imshow(_CV_FEED_NAME, frame)
                cv2.waitKey(1)
            except Exception:
                pass
            _camera_loop._feed_was_active = True
        elif _was_feed_active:
            try:
                import cv2
                cv2.destroyWindow(_CV_FEED_NAME)
            except Exception:
                pass
            _camera_loop._feed_was_active = False

        _cv_stop_event.wait(timeout=interval)

    cap.release()
    _camera_cap = None
    with _cv_lock:
        _cv_state["camera_active"] = False


# ─── Public API ────────────────────────────────────────────

def start_camera(camera_index: int = 0, interval: float = 2.0) -> str:
    """Start background camera capture and analysis.

    Args:
        camera_index: Camera device index (0 = default webcam).
        interval: Seconds between captures.

    Returns:
        Status string.
    """
    global _cv_thread, _cv_stop_event, _cv_state, _previous_frame_gray, _dnn_net

    stop_camera()

    # Check camera availability before starting thread, validating brightness
    try:
        import cv2
        import numpy as np

        # Preflight check on the selected camera index
        test_cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not test_cap.isOpened():
            test_cap = cv2.VideoCapture(camera_index)
        has_light = False
        if test_cap.isOpened():
            for _ in range(25):
                ok, frame = test_cap.read()
                if ok and frame is not None and np.mean(frame) > 2.0:
                    has_light = True
                    break
                time.sleep(0.02)

        if not has_light:
            if test_cap.isOpened():
                test_cap.release()
            found_alt = False
            if camera_index in (0, 1, 2):
                for alternative_index in (0, 1, 2):
                    if alternative_index == camera_index:
                        continue
                    alt_cap = cv2.VideoCapture(alternative_index, cv2.CAP_DSHOW)
                    if not alt_cap.isOpened():
                        alt_cap = cv2.VideoCapture(alternative_index)
                    if alt_cap.isOpened():
                        alt_ok = False
                        for _ in range(25):
                            ok, frame = alt_cap.read()
                            if ok and frame is not None and np.mean(frame) > 2.0:
                                alt_ok = True
                                break
                            time.sleep(0.02)
                        if alt_ok:
                            camera_index = alternative_index
                            test_cap = alt_cap
                            found_alt = True
                            break
                        alt_cap.release()

            if not found_alt:
                test_cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                if not test_cap.isOpened():
                    test_cap = cv2.VideoCapture(camera_index)
                if not test_cap.isOpened():
                    return f"[FAIL] Cannot open camera {camera_index} and no functional alternative found."
        
        if test_cap.isOpened():
            test_cap.release()
    except Exception as e:
        return f"[FAIL] Camera check failed: {e}"

    _cv_stop_event.clear()
    _previous_frame_gray = None
    _dnn_net = None
    reset_motion_detection()

    with _cv_lock:
        _cv_state["camera_index"] = camera_index
        _cv_state["capture_interval"] = interval
        _cv_state["error"] = None

    _cv_thread = threading.Thread(
        target=_camera_loop,
        args=(camera_index, interval),
        daemon=True,
    )
    _cv_thread.start()
    time.sleep(0.5)  # brief wait for init

    with _cv_lock:
        if _cv_state.get("error"):
            return f"[FAIL] {_cv_state['error']}"
    return f"[OK] Camera {camera_index} started (interval: {interval}s)"


def stop_camera() -> str:
    """Stop background camera capture."""
    global _cv_thread, _cv_stop_event, _camera_cap, _previous_frame_gray
    _cv_stop_event.set()
    if _camera_cap:
        try:
            _camera_cap.release()
        except Exception:
            pass
        _camera_cap = None
    if _cv_thread:
        _cv_thread.join(timeout=3)
        _cv_thread = None
    with _cv_lock:
        _cv_state["camera_active"] = False
        _cv_state["last_frame_data"] = None
    _previous_frame_gray = None
    return "[OK] Camera stopped"


def get_cv_status() -> Dict[str, Any]:
    """Get current CV engine status (LLM-consumable context).

    Returns a dict with all analysis results.
    No images are returned — only text labels and descriptions.
    """
    with _cv_lock:
        return {
            "camera_active": _cv_state.get("camera_active", False),
            "last_capture": _cv_state.get("last_capture"),
            "people_count": _cv_state.get("people_count", 0),
            "objects_found": _cv_state.get("objects_found", []),
            "detections": [
                {"label": d["label"], "confidence": d["confidence"]}
                for d in _cv_state.get("detections", [])
            ],
            "motion_detected": _cv_state.get("motion_detected", False),
            "scene_description": _cv_state.get("scene_description", ""),
            "human_readable_scene": _cv_state.get("human_readable_scene", ""),
            "hands_detected": _cv_state.get("hands_detected", []),
            "faces_detected": _cv_state.get("faces_detected", 0),
            "face_expressions": _cv_state.get("face_expressions", []),
            "animals_detected": _cv_state.get("animals_detected", []),
            "pipeline_latency_ms": _cv_state.get("pipeline_latency_ms", {}),
            "stats": _cv_state.get("stats", {}),
            "cycling_active": _cycling_active,
            "camera_descriptions": _cv_state.get("camera_descriptions", {}),
            "unified_scene": _cv_state.get("unified_scene", ""),
            "error": _cv_state.get("error"),
        }


def get_cv_frame_b64() -> Optional[str]:
    """Get the latest frame as base64 JPEG (for forwarding to Gemini Vision).

    Only returns the frame if camera is active. The frame is NOT displayed
    to the user — it's for LLM consumption via API calls.
    """
    with _cv_lock:
        return _cv_state.get("last_frame_data")


# ─── Feed Window ────────────────────────────────────────────

_cv_feed_active = False
_CV_FEED_NAME = "FRIDAY Camera"


def show_feed(timeout: float = 5.0) -> str:
    """Open an OpenCV window showing the live camera feed.

    Waits up to *timeout* seconds for the camera to become active (e.g. during
    auto-start). Call after cv_tool('start') or after module import.
    """
    global _cv_feed_active
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with _cv_lock:
            if _cv_state.get("camera_active"):
                _cv_feed_active = True
                return f"[OK] Feed window '{_CV_FEED_NAME}' opened"
        time.sleep(0.2)
    return "[FAIL] Camera not active after waiting. Start camera first."


def hide_feed() -> str:
    """Close the live camera feed window."""
    global _cv_feed_active
    _cv_feed_active = False
    try:
        import cv2
        cv2.destroyWindow(_CV_FEED_NAME)
    except Exception:
        pass
    return "[OK] Feed window closed"


# ─── Camera Management ──────────────────────────────────────

def list_available_cameras() -> str:
    """Scan indices 0-3 and return which cameras are accessible."""
    import cv2
    available = []
    with _suppress_opencv_stderr():
        for i in range(4):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(str(i))
                cap.release()
    if available:
        return f"[OK] Camera indices found: {', '.join(available)}"
    return "[FAIL] No cameras detected on indices 0-3"


def switch_camera(index: int) -> str:
    """Switch to a different camera index. Restarts the capture thread."""
    with _cv_lock:
        if not _cv_state.get("camera_active"):
            return start_camera(camera_index=index, interval=2.0)
        interval = _cv_state.get("capture_interval", 2.0)
    stop_camera()
    time.sleep(0.3)
    return start_camera(index, interval)


# ─── Dedicated FRIDAY tools ────────────────────────────────

def ask_camera(question: str) -> str:
    """Ask a visual question about the current camera frame.

    FRIDAY should call this when the user asks to see or identify something
    via the camera (e.g. 'what am I holding?', 'what's on my desk?', 'who is this?').
    """
    return cv_tool("ask", question=question)


def show_camera_feed() -> str:
    """Open a window showing the live camera feed."""
    return cv_tool("show_feed")


def hide_camera_feed() -> str:
    """Close the live camera feed window."""
    return cv_tool("hide_feed")


def nim_describe_screen(question: str = "Describe this screen in detail. What applications, windows, text, images, and UI elements are visible?") -> str:
    """Capture the current screen and ask NVIDIA NIM VL model for a detailed description.

    Use this when you need FRIDAY to analyze the screen contents in detail
    (e.g. 'what code is on my screen?', 'what website am I looking at?',
    'read the text in the document I have open').
    """
    try:
        from PIL import ImageGrab, Image
        import io
        import base64
        img = ImageGrab.grab()
        img.thumbnail((1920, 1080), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        frame_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        answer = _ask_nim_vl(question, frame_b64)
        return f"[NIM SCREEN] {answer}" if answer else "[FAIL] NIM vision returned empty"
    except Exception as e:
        return f"[FAIL] Screen capture: {e}"


def locate_on_camera(label: str) -> str:
    """Find which camera last saw an object and return its index + scene context."""
    return cv_tool("locate", label=label)


def ask_camera_smart(question: str, label_hint: str = "") -> str:
    """Ask about something, auto-switching to the camera that last saw it."""
    return cv_tool("smart_ask", question=question, label_hint=label_hint)


# ─── Auto-Camera Cycling Mode ──────────────────────────────

def _camera_cycle_worker(interval: float):
    """Background thread that rotates through all available cameras."""
    global _cycling_active
    available = []
    import cv2
    with _suppress_opencv_stderr():
        for i in range(4):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
    if not available:
        _cycling_active = False
        return

    while not _cycling_stop_event.is_set():
        for idx in available:
            if _cycling_stop_event.is_set():
                break
            with _suppress_opencv_stderr():
                cap_temp = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not cap_temp.isOpened():
                    cap_temp = cv2.VideoCapture(idx)
                if not cap_temp.isOpened():
                    continue

            ok, frame = cap_temp.read()
            if not ok or frame is None:
                cap_temp.release()
                continue

            # Encode frame
            import base64
            try:
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf).decode("utf-8")
            except Exception:
                cap_temp.release()
                continue

            cap_temp.release()

            # Describe scene with NIM
            desc = _describe_scene_nim(frame_b64)

            with _cv_lock:
                _cv_state["camera_index"] = idx
                _cv_state["last_capture"] = datetime.now().isoformat()
                _cv_state["last_frame_data"] = frame_b64
                _cv_state["scene_description"] = desc or "No scene description"
                _cv_state["camera_active"] = True
                if "camera_descriptions" not in _cv_state:
                    _cv_state["camera_descriptions"] = {}
                _cv_state["camera_descriptions"][str(idx)] = desc or "No scene description"
                # Build unified scene
                descs = _cv_state["camera_descriptions"]
                unified = "; ".join(f"Camera {k}: {v}" for k, v in descs.items())
                _cv_state["unified_scene"] = unified

                # Update last_seen: extract object labels from description
                if desc:
                    desc_lower = desc.lower()
                    known_labels = ["hand", "person", "phone", "laptop", "book", "bottle",
                                    "cup", "keyboard", "mouse", "watch", "pen", "paper",
                                    "glasses", "food", "drink", "remote", "plant", "bag",
                                    "headphone", "cable", "lamp", "toy", "dog", "cat"]
                    for label in known_labels:
                        if label in desc_lower:
                            _cv_state.setdefault("last_seen", {})[label] = {
                                "camera_index": idx,
                                "timestamp": datetime.now().isoformat(),
                            }



            # Wait for interval (poll stop_event)
            _cycling_stop_event.wait(timeout=interval)

    _cycling_active = False


def start_camera_cycle(interval: float = 5.0) -> str:
    """Rotate through all available cameras, building a unified scene description."""
    global _cycling_thread, _cycling_active, _cycling_interval, _cycling_stop_event
    if _cycling_active:
        return "[OK] Already cycling"
    _cycling_stop_event.clear()
    _cycling_interval = interval
    _cycling_active = True
    # Stop any single-camera capture
    stop_camera()
    with _cv_lock:
        _cv_state["camera_descriptions"] = {}
        _cv_state["unified_scene"] = ""
    _cycling_thread = threading.Thread(
        target=_camera_cycle_worker, args=(interval,), daemon=True, name="cv-cycle"
    )
    _cycling_thread.start()
    time.sleep(0.5)
    return f"[OK] Camera cycling started (interval: {interval}s, cycling all cameras)"


def stop_camera_cycle() -> str:
    """Stop camera cycling and return to single-camera mode."""
    global _cycling_thread, _cycling_active
    if not _cycling_active:
        return "[OK] Not cycling"
    _cycling_stop_event.set()
    if _cycling_thread:
        _cycling_thread.join(timeout=3)
        _cycling_thread = None
    _cycling_active = False
    # Restart single camera
    idx = 0
    with _cv_lock:
        idx = _cv_state.get("camera_index", 0)
    return start_camera(camera_index=idx, interval=2.0)


# ─── Smart Camera Tracking ──────────────────────────────

def locate_object(label: str) -> str:
    """Find which camera last detected an object. Returns camera index + context."""
    label_lower = label.strip().lower()
    with _cv_lock:
        last_seen = _cv_state.get("last_seen", {})
        if label_lower in last_seen:
            info = last_seen[label_lower]
            cam = info["camera_index"]
            ts = info.get("timestamp", "unknown")
            desc = _cv_state.get("camera_descriptions", {}).get(str(cam), "")
            return f"[OK] '{label}' last seen on camera {cam} at {ts}. Scene: {desc[:200]}"
        # Check unified scene for clues
        unified = _cv_state.get("unified_scene", "")
        if unified and label_lower in unified.lower():
            return f"[CLUE] '{label}' mentioned in unified scene. Use 'ask_camera' to check all cameras."
        return f"[FAIL] '{label}' not seen by any camera recently."


def smart_ask(question: str, label_hint: str = "") -> str:
    """Ask about an object, auto-selecting the camera that last saw it.

    If label_hint is provided, checks that camera first.
    If not found, falls back to current camera.
    If cycling is active, scans all cameras in order.
    """
    import base64, cv2

    label = label_hint.strip().lower() if label_hint else ""

    # Determine target cameras to try
    target_cameras = []
    with _cv_lock:
        current_idx = _cv_state.get("camera_index", 0)
        if label and _cv_state.get("last_seen", {}).get(label):
            target_cameras.append(_cv_state["last_seen"][label]["camera_index"])
        target_cameras.append(current_idx)
        # Add all cycling cameras if active
        if _cycling_active:
            for ci in range(10):
                c = str(ci)
                if c in _cv_state.get("camera_descriptions", {}):
                    if ci not in target_cameras:
                        target_cameras.append(ci)

    # Try each camera
    for cam_idx in target_cameras:
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            continue

        for _ in range(15):
            ok, frame = cap.read()
            if ok and frame is not None:
                cap.release()
                break
        else:
            cap.release()
            continue

        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_b64 = base64.b64encode(buf).decode("utf-8")
        except Exception:
            continue

        answer = _ask_nim_vl(question, frame_b64)
        if answer and "no" not in answer.lower()[:20] and "not" not in answer.lower()[:20]:
            # We got a real answer — update last_seen and return
            with _cv_lock:
                _cv_state["last_frame_data"] = frame_b64
                _cv_state["camera_index"] = cam_idx
                _cv_state["scene_description"] = answer
                if label:
                    _cv_state.setdefault("last_seen", {})[label] = {
                        "camera_index": cam_idx,
                        "timestamp": datetime.now().isoformat(),
                    }
            return f"[Camera {cam_idx}] {answer}"
        if answer:
            return f"[Camera {cam_idx}] {answer}"

    return "[FAIL] No camera available to answer."


# ─── CV Tool (FRIDAY-accessible) ────────────────────────────

def cv_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: camera CV operations (background, LLM-only).

    Actions:
        status       - Show CV engine status
        start        - Start camera capture (args: camera_index=0, interval=2.0)
        stop         - Stop camera capture
        context      - Get rich context for LLM (detections, scene, stats)
        list_cameras - List available camera devices
    """
    if action == "status":
        status = get_cv_status()
        if status.get("error"):
            return f"[FAIL] CV error: {status['error']}"
        lines = ["### CV ENGINE STATUS", ""]
        lines.append(f"Camera: {'ACTIVE' if status.get('camera_active') else 'INACTIVE'}")
        lines.append(f"Cycling: {'ACTIVE' if _cycling_active else 'INACTIVE'}")
        if status.get("camera_active"):
            lines.append(f"Last capture: {status.get('last_capture', 'N/A')}")
            lines.append(f"People: {status.get('people_count', 0)}")
            objects = status.get("objects_found", [])
            lines.append(f"Objects: {', '.join(objects[:8]) if objects else 'none'}")
            lines.append(f"Motion: {'YES' if status.get('motion_detected') else 'no'}")
            lines.append(f"Scene: {status.get('scene_description', '')[:200]}")
            stats = status.get("stats", {})
            if stats:
                lines.append(f"Lighting: {stats.get('lighting', 'N/A')}")
            exprs = status.get("face_expressions", [])
            if exprs:
                lines.append(f"Faces: {len(exprs)} detected")
                for e in exprs[:3]:
                    lines.append(f"  - {e.get('expression', '?')} (conf: {e.get('confidence', 0):.2f})")
            if _cycling_active:
                unified = status.get("unified_scene", "")
                if unified:
                    lines.append(f"Unified scene: {unified[:300]}")
        return "\n".join(lines)

    if action == "start":
        if _cycling_active:
            return "[FAIL] Stop camera cycling first (use 'stop_cycle')"
        idx = int(kwargs.get("camera_index", 0))
        interval = float(kwargs.get("interval", 2.0))
        return start_camera(idx, interval)

    if action == "stop":
        return stop_camera()

    if action == "context":
        """Rich context block for LLM system prompt injection."""
        status = get_cv_status()
        if not status.get("camera_active"):
            return ""
        lines = ["[CAMERA CONTEXT]"]
        if status.get("scene_description"):
            lines.append(f"Scene: {status['scene_description']}")
        if status.get("people_count", 0) > 0:
            lines.append(f"People visible: {status['people_count']}")
        objects = status.get("objects_found", [])
        if objects:
            lines.append(f"Objects: {', '.join(objects[:10])}")
        if status.get("motion_detected"):
            lines.append("Motion detected")
        stats = status.get("stats", {})
        if stats:
            lines.append(f"Lighting: {stats.get('lighting', '')}, "
                         f"Brightness: {stats.get('brightness', 0):.0f}/255")
        if _cycling_active:
            unified = _cv_state.get("unified_scene", "")
            if unified:
                lines.append(f"Multi-camera: {unified[:400]}")
        return "\n".join(lines)

    if action == "list_cameras":
        return list_available_cameras()

    if action == "describe_scene":
        with _cv_lock:
            human = _cv_state.get("human_readable_scene", "")
            if human:
                return f"[SCENE] {human}"
            desc = _cv_state.get("scene_description", "")
            if desc:
                return f"[SCENE] {desc}"
            return "[SCENE] Camera feed not available."

    if action == "nim_describe":
        """Use NIM vision to describe current camera frame."""
        frame_b64 = get_cv_frame_b64()
        if not frame_b64:
            return "[FAIL] No camera frame available"
        desc = _describe_scene_nim(frame_b64)
        return f"[NIM VISION] {desc}" if desc else "[FAIL] NIM vision returned empty"

    if action == "nim_label":
        """Use NIM vision to label all objects in current camera frame."""
        frame_b64 = get_cv_frame_b64()
        if not frame_b64:
            return "[FAIL] No camera frame available"
        return f"[NIM LABELS]\n{_ask_nim_vl('List ONLY the object names you see in this image, one per line. No descriptions, no sentences. Just object names.', frame_b64)}"

    if action == "ask":
        """Ask a custom question about the current camera frame using NIM VL model."""
        question = kwargs.get("question", "")
        if not question:
            return "[FAIL] No question provided. Use: question='what do you see?'"
        # Wait briefly for a frame if camera just started
        frame_b64 = get_cv_frame_b64()
        deadline = time.monotonic() + 5.0
        while not frame_b64 and time.monotonic() < deadline:
            time.sleep(0.3)
            frame_b64 = get_cv_frame_b64()
        if not frame_b64:
            return "[FAIL] No camera frame available"
        answer = _ask_nim_vl(question, frame_b64)
        return f"[NIM ANSWER] {answer}" if answer else "[FAIL] NIM vision returned empty"

    if action == "switch":
        """Switch to a different camera index."""
        index = int(kwargs.get("camera_index", 1))
        return switch_camera(index)

    if action == "show_feed":
        return show_feed()

    if action == "hide_feed":
        return hide_feed()

    if action == "describe_screen":
        question = kwargs.get("question", "")
        return nim_describe_screen(question) if question else nim_describe_screen()

    if action == "cycle":
        interval = float(kwargs.get("interval", 5.0))
        return start_camera_cycle(interval)

    if action == "stop_cycle":
        return stop_camera_cycle()

    if action == "locate":
        label = kwargs.get("label", "")
        if not label:
            return "[FAIL] Provide a label to locate (e.g. label='hand')"
        return locate_object(label)

    if action == "smart_ask":
        question = kwargs.get("question", "")
        label_hint = kwargs.get("label_hint", "")
        if not question:
            return "[FAIL] Provide a question to ask"
        return smart_ask(question, label_hint)

    return f"[FAIL] Unknown action: {action}"


# ═══════════════════════════════════════════════════════════════════
# Auto-start camera on module import
# ═══════════════════════════════════════════════════════════════════

def _ensure_camera_running():
    """Auto-start camera in background if not already running."""
    with _cv_lock:
        if _cv_state.get("camera_active"):
            return
    try:
        import cv2
        result = start_camera(camera_index=0, interval=1.5)
        if "[OK]" in result:
            print(f"[CV] Camera auto-started: {result}")
        else:
            print(f"[CV] Camera auto-start skipped: {result}")
    except Exception as e:
        print(f"[CV] Camera auto-start error: {e}")


# Auto-start in a background thread (non-blocking)
threading.Thread(target=_ensure_camera_running, daemon=True, name="cv-autostart").start()
