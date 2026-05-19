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
import urllib.request
import urllib.error
import shutil

from friday._paths import FRIDAY_MEMORY
from friday.vision_pipeline import VisionPipeline, reset_motion_detection

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
    "faces_detected": [],
    "animals_detected": [],
    "scene_stats": {},
    "pipeline_latency_ms": {},
    "error": None,
    "stats": {},
}
_cv_thread: Optional[threading.Thread] = None
_cv_stop_event = threading.Event()
_camera_cap = None
_vision_pipeline: Optional[VisionPipeline] = None
_vision_results: Dict[str, Any] = {}
_vision_lock = threading.Lock()


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
    """Ensure MobileNet-SSD model files are available. Returns True if loaded OK."""
    _ensure_model_dirs()
    prototxt = _model_path("MobileNetSSD_deploy.prototxt")
    caffemodel = _model_path("MobileNetSSD_deploy.caffemodel")

    # Download if missing
    if not (os.path.exists(prototxt) and os.path.exists(caffemodel)):
        _download_model(MOBILENET_PROTOTXT_URL, "MobileNetSSD_deploy.prototxt")
        _download_model(MOBILENET_CAFFEMODEL_URL, "MobileNetSSD_deploy.caffemodel")

    return os.path.exists(prototxt) and os.path.exists(caffemodel)


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


def _describe_scene_gemini(frame_b64: str) -> str:
    """Use Gemini Vision API for rich scene description (if available)."""
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return ""
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        import io
        image_data = base64.b64decode(frame_b64.split(",")[-1] if "," in frame_b64 else frame_b64)
        img = io.BytesIO(image_data)
        prompt = (
            "Describe this camera scene briefly (2-3 sentences) for an AI assistant. "
            "Focus on: what objects/people are visible, lighting conditions, "
            "and any notable activity. Format as a concise paragraph."
        )
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception:
        return ""


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

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        with _cv_lock:
            _cv_state["error"] = f"Cannot open camera {camera_index}"
        return

    _camera_cap = cap
    with _cv_lock:
        _cv_state["camera_active"] = True
        _cv_state["error"] = None

    # Try to load DNN in background
    _ensure_models()
    _init_dnn()

    # Initialize VisionPipeline
    try:
        _vision_pipeline = VisionPipeline()
    except Exception:
        _vision_pipeline = None

    while not _cv_stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            with _cv_lock:
                _cv_state["error"] = "Camera read failed"
            break

        # Encode frame for storage
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")

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

        # Try Gemini description (once if api available)
        gemini_desc = _describe_scene_gemini(frame_b64)

        with _cv_lock:
            _cv_state["last_capture"] = datetime.now().isoformat()
            _cv_state["last_frame_data"] = frame_b64
            _cv_state["last_analysis"] = analysis
            _cv_state["detections"] = all_detections
            _cv_state["motion_detected"] = motion
            _cv_state["motion_magnitude"] = round(float(motion_mag), 4)
            _cv_state["people_count"] = people_count
            _cv_state["objects_found"] = list(set(objects_found))
            _cv_state["scene_description"] = gemini_desc or human_readable or scene_desc
            _cv_state["human_readable_scene"] = human_readable
            _cv_state["hands_detected"] = [
                {"handedness": h.get("handedness"), "fingers_up": h.get("fingers_up"),
                 "holding_object": h.get("holding_object")}
                for h in hands
            ]
            _cv_state["faces_detected"] = len(vision_result.get("faces", []))
            _cv_state["animals_detected"] = vision_result.get("animals", [])
            _cv_state["scene_stats"] = vision_result.get("scene", {})
            _cv_state["pipeline_latency_ms"] = vision_result.get("latency_ms", {})
            _cv_state["stats"] = stats
            _cv_state["error"] = None

        try:
            with open(_CV_STATE_FILE, "w") as f:
                state_save = {k: v for k, v in _cv_state.items() if k != "last_frame_data"}
                json.dump(state_save, f, indent=2, default=str)
        except Exception:
            pass

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

    # Check camera availability before starting thread
    try:
        import cv2
        test_cap = cv2.VideoCapture(camera_index)
        if not test_cap.isOpened():
            return f"[FAIL] Cannot open camera {camera_index}"
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
            "animals_detected": _cv_state.get("animals_detected", []),
            "pipeline_latency_ms": _cv_state.get("pipeline_latency_ms", {}),
            "stats": _cv_state.get("stats", {}),
            "error": _cv_state.get("error"),
        }


def get_cv_frame_b64() -> Optional[str]:
    """Get the latest frame as base64 JPEG (for forwarding to Gemini Vision).

    Only returns the frame if camera is active. The frame is NOT displayed
    to the user — it's for LLM consumption via API calls.
    """
    with _cv_lock:
        return _cv_state.get("last_frame_data")


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
        return "\n".join(lines)

    if action == "start":
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
        return "\n".join(lines)

    if action == "list_cameras":
        try:
            import cv2
            available = []
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available.append(str(i))
                    cap.release()
            if available:
                return f"[OK] Cameras found: {', '.join(available)}"
            return "[FAIL] No cameras detected"
        except Exception as e:
            return f"[FAIL] {e}"

    if action == "describe_scene":
        with _cv_lock:
            human = _cv_state.get("human_readable_scene", "")
            if human:
                return f"[SCENE] {human}"
            desc = _cv_state.get("scene_description", "")
            if desc:
                return f"[SCENE] {desc}"
            return "[SCENE] Camera feed not available."

    return f"[FAIL] Unknown action: {action}"
