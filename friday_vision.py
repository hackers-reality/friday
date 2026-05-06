"""
Friday Vision - Image processing and computer vision.
OCR, face detection, object detection, image filters, QR codes.
"""
from __future__ import annotations

import os
import sys
import json
import base64
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import io


# ─── Image Processing ────────────────────────────#

class ImageProcessor:
    """Basic image processing operations."""
    
    def __init__(self):
        self.pil_available = self._check_pil()
        self.cv2_available = self._check_cv2()
        
    def _check_pil(self) -> bool:
        try:
            from PIL import Image
            self.Image = Image
            return True
        except ImportError:
            return False
    
    def _check_cv2(self) -> bool:
        try:
            import cv2
            self.cv2 = cv2
            return True
        except ImportError:
            return False
    
    def load_image(self, image_path: str) -> Dict[str, Any]:
        """Load an image."""
        try:
            if self.pil_available:
                img = self.Image.open(image_path)
                return {
                    "success": True,
                    "image": img,
                    "mode": img.mode,
                    "size": img.size,
                }
            else:
                return {"success": False, "error": "PIL not available. Install: pip install pillow"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def resize(self, image_path: str, width: int, height: int, output: str = None) -> Dict[str, Any]:
        """Resize an image."""
        result = self.load_image(image_path)
        if not result["success"]:
            return result
        
        try:
            img = result["image"]
            resized = img.resize((width, height))
            
            output = output or f"resized_{Path(image_path).name}"
            resized.save(output)
            
            return {
                "success": True,
                "output": output,
                "original_size": result["size"],
                "new_size": (width, height),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_format(self, image_path: str, output_format: str, output: str = None) -> Dict[str, Any]:
        """Convert image format."""
        result = self.load_image(image_path)
        if not result["success"]:
            return result
        
        try:
            img = result["image"]
            output = output or f"{Path(image_path).stem}.{output_format.lower()}"
            img.save(output, format=output_format.upper())
            
            return {
                "success": True,
                "output": output,
                "format": output_format,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def rotate(self, image_path: str, degrees: float, output: str = None) -> Dict[str, Any]:
        """Rotate an image."""
        result = self.load_image(image_path)
        if not result["success"]:
            return result
        
        try:
            img = result["image"]
            rotated = img.rotate(degrees, expand=True)
            
            output = output or f"rotated_{Path(image_path).name}"
            rotated.save(output)
            
            return {
                "success": True,
                "output": output,
                "degrees": degrees,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def crop(self, image_path: str, box: Tuple[int, int, int, int], output: str = None) -> Dict[str, Any]:
        """Crop an image."""
        result = self.load_image(image_path)
        if not result["success"]:
            return result
        
        try:
            img = result["image"]
            cropped = img.crop(box)
            
            output = output or f"cropped_{Path(image_path).name}"
            cropped.save(output)
            
            return {
                "success": True,
                "output": output,
                "box": box,
                "size": cropped.size,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_dominant_colors(self, image_path: str, num_colors: int = 5) -> Dict[str, Any]:
        """Get dominant colors in image."""
        try:
            import colorsys
            
            result = self.load_image(image_path)
            if not result["success"]:
                return result
            
            img = result["image"]
            img_rgb = img.convert("RGB")
            pixels = list(img_rgb.getdata())
            
            # Simple: sample pixels and find most common
            from collections import Counter
            sampled = pixels[::max(1, len(pixels) // 1000)]  # Sample 1000 pixels
            color_counts = Counter(sampled)
            most_common = color_counts.most_common(num_colors)
            
            colors = []
            for color, count in most_common:
                r, g, b = color
                h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                colors.append({
                    "rgb": color,
                    "hex": f"#{r:02x}{g:02x}{b:02x}",
                    "hsv": (h, s, v),
                    "count": count,
                })
            
            return {
                "success": True,
                "colors": colors,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── OCR (Optical Character Recognition) ────────────────────────────#

class OCRProcessor:
    """OCR text extraction from images."""
    
    def __init__(self):
        self.tesseract_available = self._check_tesseract()
        
    def _check_tesseract(self) -> bool:
        try:
            import pytesseract
            self.pytesseract = pytesseract
            return True
        except ImportError:
            return False
    
    def extract_text(self, image_path: str, lang: str = "eng") -> Dict[str, Any]:
        """Extract text from image."""
        if not self.tesseract_available:
            return {
                "success": False,
                "error": "Tesseract not available. Install: pip install pytesseract + tesseract-ocr",
            }
        
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            text = self.pytesseract.image_to_string(img, lang=lang)
            
            return {
                "success": True,
                "text": text.strip(),
                "language": lang,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def extract_text_with_boxes(self, image_path: str) -> Dict[str, Any]:
        """Extract text with bounding boxes."""
        if not self.tesseract_available:
            return {"success": False, "error": "Tesseract not available."}
        
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            data = self.pytesseract.image_to_data(img, output_type=self.pytesseract.Output.DICT)
            
            texts = []
            for i, word in enumerate(data["text"]):
                if word.strip():
                    texts.append({
                        "text": word,
                        "confidence": data["conf"][i],
                        "bbox": (
                            data["left"][i],
                            data["top"][i],
                            data["width"][i],
                            data["height"][i],
                        ),
                    })
            
            return {
                "success": True,
                "words": texts,
                "full_text": " ".join([t["text"] for t in texts]),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── QR Code ────────────────────────────#

class QRCodeProcessor:
    """QR code generation and reading."""
    
    def __init__(self):
        self.qrcode_available = self._check_qrcode()
        self.cv2_available = self._check_cv2()
        
    def _check_qrcode(self) -> bool:
        try:
            import qrcode
            self.qrcode = qrcode
            return True
        except ImportError:
            return False
    
    def _check_cv2(self) -> bool:
        try:
            import cv2
            self.cv2 = cv2
            return True
        except ImportError:
            return False
    
    def generate(self, data: str, output: str = "qrcode.png") -> Dict[str, Any]:
        """Generate QR code."""
        if not self.qrcode_available:
            return {
                "success": False,
                "error": "qrcode not available. Install: pip install qrcode[pil]",
            }
        
        try:
            qr = self.qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output)
            
            return {
                "success": True,
                "output": output,
                "data": data,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read(self, image_path: str) -> Dict[str, Any]:
        """Read QR code from image."""
        if not self.cv2_available:
            return {
                "success": False,
                "error": "OpenCV not available. Install: pip install opencv-python",
            }
        
        try:
            import cv2
            
            img = cv2.imread(image_path)
            detector = cv2.QRCodeDetector()
            data, points, _ = detector.detectAndDecode(img)
            
            if data:
                return {
                    "success": True,
                    "data": data,
                    "points": points.tolist() if points is not None else None,
                }
            else:
                return {
                    "success": False,
                    "error": "No QR code found in image.",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Face Detection (Simplified) ────────────────────────────#

class FaceDetector:
    """Face detection using OpenCV."""
    
    def __init__(self):
        self.cv2_available = self._check_cv2()
        self.face_cascade = None
        
        if self.cv2_available:
            self._load_cascade()
    
    def _check_cv2(self) -> bool:
        try:
            import cv2
            self.cv2 = cv2
            return True
        except ImportError:
            return False
    
    def _load_cascade(self):
        try:
            cascade_path = self.cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = self.cv2.CascadeClassifier(cascade_path)
        except:
            self.face_cascade = None
    
    def detect(self, image_path: str) -> Dict[str, Any]:
        """Detect faces in image."""
        if not self.cv2_available or self.face_cascade is None:
            return {
                "success": False,
                "error": "OpenCV or cascade not available.",
            }
        
        try:
            img = self.cv2.imread(image_path)
            gray = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2GRAY)
            
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            face_list = []
            for (x, y, w, h) in faces:
                face_list.append({
                    "bbox": (x, y, w, h),
                    "center": (x + w//2, y + h//2),
                })
            
            return {
                "success": True,
                "faces": face_list,
                "count": len(face_list),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Vision Tool for Friday ────────────────────────────#

def vision_tool(
    action: str = "status",
    image_path: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for vision operations.
    Actions: status, resize, convert, rotate, crop, dominant_colors,
            ocr, qr_generate, qr_read, face_detect
    """
    params = params or {}
    
    if action == "status":
        processor = ImageProcessor()
        lines = ["### VISION STATUS", ""]
        lines.append(f"**PIL/Pillow**: {'✅ Available' if processor.pil_available else '❌ Not available'}")
        lines.append(f"**OpenCV**: {'✅ Available' if processor.cv2_available else '❌ Not available'}")
        lines.append("")
        lines.append("**Available Operations**:")
        lines.append("  - Image processing (resize, crop, rotate, convert)")
        lines.append("  - OCR (pytesseract)")
        lines.append("  - QR code generation and reading")
        lines.append("  - Face detection (OpenCV)")
        return "\n".join(lines)
    
    if action == "resize":
        if not image_path:
            return "❌ Image path required."
        processor = ImageProcessor()
        width = params.get("width", 100)
        height = params.get("height", 100)
        result = processor.resize(image_path, width, height, params.get("output"))
        if result["success"]:
            return f"### RESIZE\n\n✅ Saved to {result['output']}\nOriginal: {result['original_size']} -> New: {result['new_size']}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "convert":
        if not image_path:
            return "❌ Image path required."
        processor = ImageProcessor()
        fmt = params.get("format", "PNG")
        result = processor.convert_format(image_path, fmt, params.get("output"))
        if result["success"]:
            return f"### CONVERT\n\n✅ Saved to {result['output']} (format: {result['format']})"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "rotate":
        if not image_path:
            return "❌ Image path required."
        processor = ImageProcessor()
        degrees = params.get("degrees", 90)
        result = processor.rotate(image_path, degrees, params.get("output"))
        if result["success"]:
            return f"### ROTATE\n\n✅ Saved to {result['output']} (rotated {result['degrees']}°)"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "crop":
        if not image_path or "box" not in params:
            return "❌ Image path and box required."
        processor = ImageProcessor()
        result = processor.crop(image_path, tuple(params["box"]), params.get("output"))
        if result["success"]:
            return f"### CROP\n\n✅ Saved to {result['output']}\nBox: {result['box']}, Size: {result['size']}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "dominant_colors":
        if not image_path:
            return "❌ Image path required."
        processor = ImageProcessor()
        result = processor.get_dominant_colors(image_path, params.get("num_colors", 5))
        if result["success"]:
            colors_preview = "\n".join([f"  - {c['hex']} (RGB: {c['rgb']})" for c in result["colors"]])
            return f"### DOMINANT COLORS\n\n{colors_preview}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "ocr":
        if not image_path:
            return "❌ Image path required."
        ocr = OCRProcessor()
        result = ocr.extract_text(image_path, params.get("lang", "eng"))
        if result["success"]:
            return f"### OCR\n\n**Extracted Text**:\n{result['text'][:500]}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "qr_generate":
        if "data" not in params:
            return "❌ Data required for QR code."
        qr = QRCodeProcessor()
        result = qr.generate(params["data"], params.get("output", "qrcode.png"))
        if result["success"]:
            return f"### QR GENERATE\n\n✅ Saved to {result['output']}\nData: {result['data'][:50]}..."
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "qr_read":
        if not image_path:
            return "❌ Image path required."
        qr = QRCodeProcessor()
        result = qr.read(image_path)
        if result["success"]:
            return f"### QR READ\n\n**Data**: {result['data']}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "face_detect":
        if not image_path:
            return "❌ Image path required."
        detector = FaceDetector()
        result = detector.detect(image_path)
        if result["success"]:
            return f"### FACE DETECTION\n\nFound {result['count']} face(s)."
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Vision...\n")
    
    # Test status
    print("--- Vision Status ---")
    print(vision_tool("status"))
    
    # Test QR generation
    print("\n--- QR Code Generation ---")
    print(vision_tool("qr_generate", params={"data": "https://friday.ai"}))
