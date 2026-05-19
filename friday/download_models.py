"""
FRIDAY Model Downloader — downloads required ML models on first run.
MediaPipe is bundled with pip. YOLOv5s ONNX model is downloaded from GitHub.
Models are cached in friday_memory/models/ and only downloaded once.
"""

from __future__ import annotations
import os
import sys
import urllib.request
import urllib.error
import hashlib

from friday._paths import FRIDAY_MEMORY

_MODELS_DIR = os.path.join(FRIDAY_MEMORY, "models")
_MODEL_REGISTRY = os.path.join(_MODELS_DIR, ".model_registry.json")

YOLOV5S_ONNX_URL = (
    "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx"
)
YOLOV8N_ONNX_URL = (
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx"
)

REQUIRED_MODELS = {
    "yolov5s.onnx": {
        "url": YOLOV5S_ONNX_URL,
        "description": "YOLOv5s ONNX — object detection (80 COCO classes)",
        "size_mb": 14.4,
    },
    "yolov8n.onnx": {
        "url": YOLOV8N_ONNX_URL,
        "description": "YOLOv8n ONNX — object detection (80 COCO classes)",
        "size_mb": 6.2,
    },
}


def _ensure_dirs():
    os.makedirs(_MODELS_DIR, exist_ok=True)


def _load_registry() -> dict:
    import json
    if os.path.exists(_MODEL_REGISTRY):
        try:
            with open(_MODEL_REGISTRY, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_registry(registry: dict):
    import json
    try:
        with open(_MODEL_REGISTRY, "w") as f:
            json.dump(registry, f, indent=2)
    except Exception:
        pass


def _model_path(name: str) -> str:
    return os.path.join(_MODELS_DIR, name)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _download_file(url: str, dest: str, desc: str = "") -> bool:
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    try:
        print(f"[Models] Downloading {desc or os.path.basename(dest)}...")
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        if size > 1000:
            print(f"[Models] Downloaded {desc or os.path.basename(dest)} ({size / 1024 / 1024:.1f} MB)")
            return True
        print(f"[Models] Downloaded file too small ({size} bytes), removing")
        try:
            os.remove(dest)
        except Exception:
            pass
        return False
    except urllib.error.HTTPError as e:
        print(f"[Models] HTTP {e.code} downloading {dest}: {e.reason}")
        return False
    except Exception as e:
        print(f"[Models] Failed to download {dest}: {e}")
        return False


def download_models(force: bool = False) -> list:
    """Download all required models. Returns list of (name, success)."""
    _ensure_dirs()
    registry = _load_registry()
    results = []

    for model_name, info in REQUIRED_MODELS.items():
        dest = _model_path(model_name)
        already = os.path.exists(dest) and os.path.getsize(dest) > 1000

        if already and not force:
            results.append((model_name, True))
            continue

        if already and force:
            try:
                os.remove(dest)
            except Exception:
                pass

        ok = _download_file(info["url"], dest, desc=info["description"])
        results.append((model_name, ok))
        if ok:
            registry[model_name] = {
                "downloaded": True,
                "size": os.path.getsize(dest),
                "sha256_prefix": _sha256(dest),
            }
        _save_registry(registry)

    return results


def check_models() -> dict:
    """Check which models are available. Returns dict of model name -> {available, size}."""
    _ensure_dirs()
    status = {}
    for model_name, info in REQUIRED_MODELS.items():
        dest = _model_path(model_name)
        available = os.path.exists(dest) and os.path.getsize(dest) > 1000
        status[model_name] = {
            "available": available,
            "size": os.path.getsize(dest) if available else 0,
            "description": info["description"],
        }
    return status


def ensure_yolo_model() -> bool:
    """Ensure at least one YOLO ONNX model is available. Returns True if any found."""
    for name in ["yolov5s.onnx", "yolov8n.onnx"]:
        if os.path.exists(_model_path(name)) and os.path.getsize(_model_path(name)) > 1000:
            return True
    results = download_models()
    return any(ok for _, ok in results)


if __name__ == "__main__":
    print("FRIDAY Model Downloader\n")
    results = download_models()
    print()
    for name, ok in results:
        print(f"  {'[OK]' if ok else '[FAIL]'} {name}")
    print()
    status = check_models()
    available = sum(1 for s in status.values() if s["available"])
    total = len(status)
    print(f"Models available: {available}/{total}")
