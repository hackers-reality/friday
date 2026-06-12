"""
Desktop Vision Agent — unifies UIA element tree + screenshot analysis into one agent.
Combines pywinauto UI Automation with vision models (OCR, object detection, pose, face)
to give FRIDAY a complete understanding of what is on screen at any moment.

Architecture:
  1. Capture screenshot + UIA element tree in parallel
  2. Run vision models (OCR, object detection, face, pose) on the screenshot
  3. Merge results into a unified "desktop state" report
  4. Allow LLM to query/interact with specific screen regions
"""
from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from friday._paths import FRIDAY_MEMORY

_DESKTOP_AVAILABLE = False
_HAS_CV2 = False
_HAS_PIL = False
_HAS_TESSERACT = False
_HAS_EASYOCR = False
_HAS_ULTRALYTICS = False
_HAS_MEDIAPIPE = False
_HAS_FACE_REC = False

try:
    import pywinauto
    _DESKTOP_AVAILABLE = True
except ImportError:
    pass

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    pass

try:
    from PIL import Image, ImageGrab
    _HAS_PIL = True
except ImportError:
    pass

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    pass

try:
    import easyocr
    _HAS_EASYOCR = True
except ImportError:
    pass

try:
    from ultralytics import YOLO
    _HAS_ULTRALYTICS = True
except ImportError:
    pass

try:
    import mediapipe as mp
    _HAS_MEDIAPIPE = True
except ImportError:
    pass

try:
    import face_recognition
    _HAS_FACE_REC = True
except ImportError:
    pass


@dataclass
class DesktopState:
    timestamp: str = ""
    active_window: str = ""
    windows: list[dict] = field(default_factory=list)
    element_tree: str = ""
    screenshot_path: str = ""
    screenshot_b64: str = ""
    ocr_text: str = ""
    objects: list[dict] = field(default_factory=list)
    faces: list[dict] = field(default_factory=list)
    poses: list[dict] = field(default_factory=list)
    hands: list[dict] = field(default_factory=list)
    analysis: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


def _ensure_com():
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass


def _get_windows():
    from pywinauto import Desktop
    last_err = None
    for backend in ("uia", "win32"):
        for attempt in range(2):
            try:
                import gc; gc.collect()
                if backend == "uia":
                    _ensure_com()
                d = Desktop(backend=backend)
                return d.windows()
            except Exception as e:
                last_err = e
                time.sleep(1)
    raise last_err or RuntimeError("Failed to list desktop windows")


def _get_desktop():
    from pywinauto import Desktop
    for backend in ("uia", "win32"):
        for attempt in range(2):
            try:
                if backend == "uia":
                    _ensure_com()
                return Desktop(backend=backend)
            except Exception as e:
                time.sleep(1)
    raise RuntimeError("Failed to initialize Desktop")


def _find_window(title_containing: str):
    for attempt in range(3):
        try:
            import gc; gc.collect()
            wins = _get_windows()
            for w in wins:
                try:
                    if title_containing.lower() in w.window_text().lower():
                        return w
                except Exception:
                    continue
            return None
        except Exception as e:
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise


def capture_screenshot() -> tuple[str, str]:
    path = os.path.join(tempfile.gettempdir(), f"friday_desktop_{int(time.time())}.png")
    if _HAS_PIL:
        img = ImageGrab.grab()
        img.save(path, "PNG")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return path, b64
    return "", ""


def get_uia_state() -> tuple[str, list[dict], str]:
    active_window = ""
    windows = []
    tree = ""
    if not _DESKTOP_AVAILABLE:
        return "", [], ""
    try:
        wins = _get_windows()
        for w in wins:
            try:
                title = w.window_text()
                if title.strip():
                    windows.append({
                        "title": title,
                        "class_name": w.class_name(),
                        "handle": str(w.handle),
                    })
            except Exception:
                continue
        windows.sort(key=lambda x: x["title"].lower())

        desktop = _get_desktop()
        active_wins = [w for w in wins if w.window_text().strip()]
        if active_wins:
            target = active_wins[0]
            active_window = target.window_text()
            from io import StringIO
            import sys
            try:
                spec = desktop.window(title=target.window_text())
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                try:
                    spec.dump_tree()
                    tree = sys.stdout.getvalue()[:15000]
                finally:
                    sys.stdout = old_stdout
            except Exception:
                pass
    except Exception:
        pass
    return active_window, windows[:30], tree


def run_ocr(screenshot_path: str) -> str:
    text = ""
    if _HAS_TESSERACT:
        try:
            text = pytesseract.image_to_string(screenshot_path)
        except Exception:
            pass
    if not text.strip() and _HAS_EASYOCR:
        try:
            reader = easyocr.Reader(["en"], gpu=False)
            results = reader.readtext(screenshot_path)
            text = " ".join([r[1] for r in results])
        except Exception:
            pass
    return text.strip()


def detect_objects_in_screenshot(screenshot_path: str) -> list[dict]:
    detections = []
    if _HAS_ULTRALYTICS:
        try:
            yolo = YOLO("yolov8n.pt")
            results = yolo(screenshot_path)
            for r in results:
                for box in r.boxes:
                    detections.append({
                        "class": r.names[int(box.cls[0])],
                        "confidence": float(box.conf[0]),
                        "bbox": [float(x) for x in box.xyxy[0]],
                    })
        except Exception:
            pass
    return detections


def detect_faces_in_screenshot(screenshot_path: str) -> list[dict]:
    faces = []
    if _HAS_FACE_REC:
        try:
            img = face_recognition.load_image_file(screenshot_path)
            locs = face_recognition.face_locations(img)
            for t, r, b, l in locs:
                faces.append({"top": t, "right": r, "bottom": b, "left": l})
        except Exception:
            pass
    if not faces and _HAS_CV2:
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            img = cv2.imread(screenshot_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            detected = face_cascade.detectMultiScale(gray, 1.1, 4)
            for x, y, w, h in detected:
                faces.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        except Exception:
            pass
    return faces


def detect_pose_in_screenshot(screenshot_path: str) -> list[dict]:
    if not _HAS_MEDIAPIPE:
        return []
    try:
        mp_pose = mp.solutions.pose
        img = cv2.imread(screenshot_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            results = pose.process(rgb)
            if results.pose_landmarks:
                return [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                        for lm in results.pose_landmarks.landmark]
    except Exception:
        pass
    return []


def detect_hands_in_screenshot(screenshot_path: str) -> list[list[dict]]:
    if not _HAS_MEDIAPIPE:
        return []
    try:
        mp_hands = mp.solutions.hands
        img = cv2.imread(screenshot_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5) as hands:
            results = hands.process(rgb)
            hands_data = []
            if results.multi_hand_landmarks:
                for hlm in results.multi_hand_landmarks:
                    hands_data.append([{"x": lm.x, "y": lm.y, "z": lm.z} for lm in hlm.landmark])
            return hands_data
    except Exception:
        pass
    return []


def analyze_desktop_state() -> str:
    state = DesktopState(timestamp=datetime.now().isoformat())

    active_window, windows, tree = get_uia_state()
    state.active_window = active_window
    state.windows = windows
    state.element_tree = tree

    ss_path, ss_b64 = capture_screenshot()
    state.screenshot_path = ss_path
    state.screenshot_b64 = ss_b64

    if ss_path and _HAS_PIL:
        state.ocr_text = run_ocr(ss_path)
        state.objects = detect_objects_in_screenshot(ss_path)
        state.faces = detect_faces_in_screenshot(ss_path)
        state.poses = detect_pose_in_screenshot(ss_path)
        state.hands = detect_hands_in_screenshot(ss_path)

    state.analysis = _build_analysis(state)
    return state.to_json()


def _build_analysis(state: DesktopState) -> str:
    parts = []
    parts.append(f"Time: {state.timestamp}")
    parts.append(f"Active window: {state.active_window}")
    parts.append(f"Open windows ({len(state.windows)}):")
    for w in state.windows[:10]:
        parts.append(f"  - {w['title']} ({w['class_name']})")

    if state.ocr_text:
        parts.append(f"\nText on screen ({len(state.ocr_text)} chars):")
        lines = state.ocr_text.split("\n")
        for l in lines[:30]:
            if l.strip():
                parts.append(f"  {l.strip()}")

    if state.objects:
        parts.append(f"\nObjects detected ({len(state.objects)}):")
        for obj in state.objects[:10]:
            parts.append(f"  - {obj['class']} ({obj['confidence']:.2f})")

    if state.faces:
        parts.append(f"\nFaces detected: {len(state.faces)}")

    if state.poses:
        parts.append(f"\nPose detected: {len(state.poses)} landmarks")

    if state.hands:
        parts.append(f"\nHands detected: {len(state.hands)}")

    if state.element_tree:
        parts.append(f"\nUIA Element Tree ({len(state.element_tree)} chars):")
        parts.append(state.element_tree[:3000])

    return "\n".join(parts)


def _save_to_memory(state_json: str) -> str:
    os.makedirs(FRIDAY_MEMORY, exist_ok=True)
    path = os.path.join(FRIDAY_MEMORY, "desktop_states.jsonl")
    with open(path, "a") as f:
        f.write(state_json + "\n")
    return path


def desktop_vision_observe() -> str:
    state_json = analyze_desktop_state()
    path = _save_to_memory(json.loads(state_json))
    return state_json


def desktop_vision_query(question: str = "") -> str:
    state_json = json.loads(analyze_desktop_state())
    analysis = state_json.get("analysis", "")
    return json.dumps({
        "question": question,
        "observation": analysis,
        "screenshot_b64": state_json.get("screenshot_b64", "")[:500] + "..." if state_json.get("screenshot_b64") else "",
    }, indent=2)


def desktop_vision_region(region: str = "center", width_pct: int = 50, height_pct: int = 50) -> str:
    if not _HAS_PIL:
        return json.dumps({"error": "PIL not installed"})
    try:
        ss_path, ss_b64 = capture_screenshot()
        img = Image.open(ss_path)
        w, h = img.size
        regions = {
            "top_left": (0, 0, int(w * width_pct / 100), int(h * height_pct / 100)),
            "top_right": (int(w * (100 - width_pct) / 100), 0, w, int(h * height_pct / 100)),
            "bottom_left": (0, int(h * (100 - height_pct) / 100), int(w * width_pct / 100), h),
            "bottom_right": (int(w * (100 - width_pct) / 100), int(h * (100 - height_pct) / 100), w, h),
            "center": (int(w * (50 - width_pct / 2) / 100), int(h * (50 - height_pct / 2) / 100),
                       int(w * (50 + width_pct / 2) / 100), int(h * (50 + height_pct / 2) / 100)),
        }
        box = regions.get(region, regions["center"])
        cropped = img.crop(box)
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        region_b64 = base64.b64encode(buf.getvalue()).decode()

        ocr_text = ""
        if _HAS_TESSERACT:
            try:
                ocr_text = pytesseract.image_to_string(cropped)
            except Exception:
                pass

        return json.dumps({
            "region": region,
            "box": box,
            "screenshot_b64": region_b64,
            "ocr_text": ocr_text.strip(),
            "width": box[2] - box[0],
            "height": box[3] - box[1],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def desktop_vision_interact(action: str = "click", target_text: str = "", target_region: str = "center") -> str:
    if not _DESKTOP_AVAILABLE:
        return json.dumps({"error": "pywinauto not installed"})
    try:
        if action == "click" and target_text:
            from pywinauto import Desktop
            d = Desktop(backend="uia")
            elem = d.window(title=target_text)
            if elem.exists():
                elem.click_input()
                return json.dumps({"success": True, "action": "click", "target": target_text})
            wins = _get_windows()
            for w in wins:
                try:
                    if target_text.lower() in w.window_text().lower():
                        w.set_focus()
                        w.click_input()
                        return json.dumps({"success": True, "action": "click", "target": target_text, "window": w.window_text()})
                except Exception:
                    continue
            return json.dumps({"error": f"Element '{target_text}' not found"})
        elif action == "focus" and target_text:
            wins = _get_windows()
            for w in wins:
                try:
                    if target_text.lower() in w.window_text().lower():
                        w.set_focus()
                        return json.dumps({"success": True, "action": "focus", "target": target_text})
                except Exception:
                    continue
            return json.dumps({"error": f"Window '{target_text}' not found"})
        elif action == "screenshot":
            return desktop_vision_observe()
        return json.dumps({"error": f"Unknown action '{action}'"})
    except Exception as e:
        return json.dumps({"error": str(e)})
