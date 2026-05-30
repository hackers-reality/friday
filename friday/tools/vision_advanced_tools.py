"""
Advanced Vision & Image Processing tools
Libraries: opencv-python, pillow, scikit-image, matplotlib, pytesseract, easyocr,
paddleocr, ultralytics, mediapipe, face-recognition, dlib, retinaface, insightface, clip
"""
import asyncio
import base64
import io
import os
import tempfile
from typing import Any

HAS_CV2 = False
HAS_PIL = False
HAS_SKIMAGE = False
HAS_TESSERACT = False
HAS_EASYOCR = False
HAS_ULTRALYTICS = False
HAS_MEDIAPIPE = False
HAS_FACE_REC = False
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    pass
try:
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_PIL = True
except ImportError:
    pass
try:
    from skimage import io as skio, filters, color, measure
    HAS_SKIMAGE = True
except ImportError:
    pass
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pass
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    pass
try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    pass
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    pass
try:
    import face_recognition
    HAS_FACE_REC = True
except ImportError:
    pass


async def ocr_image(image_path: str, engine: str = "tesseract", lang: str = "eng") -> dict[str, Any]:
    if engine == "tesseract" and HAS_TESSERACT:
        try:
            text = await asyncio.get_event_loop().run_in_executor(None, lambda: pytesseract.image_to_string(image_path, lang=lang))
            data = await asyncio.get_event_loop().run_in_executor(None, lambda: pytesseract.image_to_data(image_path, lang=lang, output_type=pytesseract.Output.DICT))
            return {"text": text.strip(), "engine": "tesseract", "language": lang,
                    "words": len([w for w in data.get("text", []) if w.strip()]),
                    "confidences": [int(c) for c in data.get("conf", []) if c > 0]}
        except Exception as e:
            return {"error": str(e)}
    if engine == "easyocr" and HAS_EASYOCR:
        try:
            reader = easyocr.Reader([lang], gpu=False)
            results = await asyncio.get_event_loop().run_in_executor(None, lambda: reader.readtext(image_path))
            text = " ".join([r[1] for r in results])
            return {"text": text, "engine": "easyocr", "language": lang,
                    "detections": [{"bbox": r[0], "text": r[1], "confidence": float(r[2])} for r in results]}
        except Exception as e:
            return {"error": str(e)}
    return {"error": f"No OCR engine available for '{engine}'"}


async def detect_objects(image_path: str, model: str = "yolov8n") -> dict[str, Any]:
    if HAS_ULTRALYTICS:
        try:
            yolo = await asyncio.get_event_loop().run_in_executor(None, lambda: YOLO(model))
            results = await asyncio.get_event_loop().run_in_executor(None, lambda: yolo(image_path))
            dets = []
            for r in results:
                for box in r.boxes:
                    dets.append({"class": r.names[int(box.cls[0])], "confidence": float(box.conf[0]),
                                "bbox": [float(x) for x in box.xyxy[0]]})
            return {"detections": dets, "count": len(dets), "model": model}
        except Exception as e:
            return {"error": str(e)}
    if HAS_CV2:
        try:
            img = cv2.imread(image_path)
            if img is None:
                return {"error": "Could not read image"}
            h, w = img.shape[:2]
            return {"width": w, "height": h, "detections": [], "note": "YOLO not installed. Used basic image info."}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "cv2 / ultralytics not installed"}


async def detect_faces(image_path: str) -> dict[str, Any]:
    if HAS_FACE_REC:
        try:
            img = await asyncio.get_event_loop().run_in_executor(None, lambda: face_recognition.load_image_file(image_path))
            locs = await asyncio.get_event_loop().run_in_executor(None, lambda: face_recognition.face_locations(img))
            encs = await asyncio.get_event_loop().run_in_executor(None, lambda: face_recognition.face_encodings(img, locs))
            return {"faces": len(locs), "locations": [{"top": t, "right": r, "bottom": b, "left": l} for t, r, b, l in locs],
                    "encodings": len(encs)}
        except Exception as e:
            return {"error": str(e)}
    if HAS_CV2:
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = await asyncio.get_event_loop().run_in_executor(None, lambda: face_cascade.detectMultiScale(gray, 1.1, 4))
            return {"faces": len(faces), "locations": [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "face recognition libraries not installed"}


async def pose_detection(image_path: str) -> dict[str, Any]:
    if not HAS_MEDIAPIPE:
        return {"error": "mediapipe not installed"}
    try:
        mp_pose = mp.solutions.pose
        mp_draw = mp.solutions.drawing_utils
        img = cv2.imread(image_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            results = await asyncio.get_event_loop().run_in_executor(None, lambda: pose.process(rgb))
            if results.pose_landmarks:
                landmarks = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                            for lm in results.pose_landmarks.landmark]
                return {"pose_detected": True, "landmarks": landmarks[:33]}
            return {"pose_detected": False}
    except Exception as e:
        return {"error": str(e)}


async def hand_detection(image_path: str) -> dict[str, Any]:
    if not HAS_MEDIAPIPE:
        return {"error": "mediapipe not installed"}
    try:
        mp_hands = mp.solutions.hands
        img = cv2.imread(image_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5) as hands:
            results = await asyncio.get_event_loop().run_in_executor(None, lambda: hands.process(rgb))
            hands_data = []
            if results.multi_hand_landmarks:
                for hlm in results.multi_hand_landmarks:
                    hands_data.append([{"x": lm.x, "y": lm.y, "z": lm.z} for lm in hlm.landmark])
            return {"hands": len(hands_data), "landmarks": hands_data}
    except Exception as e:
        return {"error": str(e)}


async def image_enhance(image_path: str, operation: str = "enhance_contrast", factor: float = 1.5) -> dict[str, Any]:
    if not HAS_PIL:
        return {"error": "Pillow not installed"}
    try:
        img = Image.open(image_path)
        ops = {
            "enhance_contrast": ImageEnhance.Contrast(img).enhance(factor),
            "enhance_brightness": ImageEnhance.Brightness(img).enhance(factor),
            "enhance_sharpness": ImageEnhance.Sharpness(img).enhance(factor),
            "enhance_color": ImageEnhance.Color(img).enhance(factor),
            "grayscale": img.convert("L"),
            "blur": img.filter(ImageFilter.BLUR),
            "edge_enhance": img.filter(ImageFilter.EDGE_ENHANCE),
            "sharpen": img.filter(ImageFilter.SHARPEN),
            "smooth": img.filter(ImageFilter.SMOOTH),
            "emboss": img.filter(ImageFilter.EMBOSS),
        }
        result = ops.get(operation, img)
        out = os.path.join(tempfile.gettempdir(), f"friday_{operation}.png")
        await asyncio.get_event_loop().run_in_executor(None, lambda: result.save(out))
        return {"path": out, "operation": operation, "factor": factor if operation.startswith("enhance") else None}
    except Exception as e:
        return {"error": str(e)}


async def image_analysis(image_path: str) -> dict[str, Any]:
    info = {"path": image_path, "format": None, "size": None, "mode": None, "width": None, "height": None, "histogram": None}
    if HAS_PIL:
        try:
            img = Image.open(image_path)
            info["format"] = img.format
            info["mode"] = img.mode
            info["width"], info["height"] = img.size
            info["size"] = os.path.getsize(image_path)
            h = img.histogram()
            info["histogram"] = {"mean": sum(h) / len(h) if h else 0, "peaks": len([v for v in h if v > 100])}
        except Exception:
            pass
    if HAS_CV2:
        try:
            img = cv2.imread(image_path)
            if img is not None:
                info["channels"] = img.shape[2] if len(img.shape) > 2 else 1
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                info["hsv_mean"] = [float(hsv[..., i].mean()) for i in range(3)]
        except Exception:
            pass
    if HAS_SKIMAGE:
        try:
            img = skio.imread(image_path)
            info["dtype"] = str(img.dtype)
            info["shape"] = list(img.shape)
            edges = filters.sobel(color.rgb2gray(img) if len(img.shape) == 3 else img)
            info["edge_intensity"] = float(edges.mean())
        except Exception:
            pass
    return info


async def resize_image(image_path: str, width: int, height: int) -> dict[str, Any]:
    if not HAS_PIL:
        return {"error": "Pillow not installed"}
    try:
        img = Image.open(image_path)
        resized = img.resize((width, height), Image.LANCZOS)
        out = os.path.join(tempfile.gettempdir(), "friday_resized.png")
        await asyncio.get_event_loop().run_in_executor(None, lambda: resized.save(out))
        return {"path": out, "original": {"width": img.width, "height": img.height}, "resized": {"width": width, "height": height}}
    except Exception as e:
        return {"error": str(e)}


async def convert_image_format(image_path: str, output_format: str = "png") -> dict[str, Any]:
    if not HAS_PIL:
        return {"error": "Pillow not installed"}
    try:
        img = Image.open(image_path)
        base = os.path.splitext(image_path)[0]
        out = f"{base}.{output_format}"
        await asyncio.get_event_loop().run_in_executor(None, lambda: img.save(out, format=output_format.upper()))
        return {"input": image_path, "output": out, "format": output_format}
    except Exception as e:
        return {"error": str(e)}
