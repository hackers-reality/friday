"""
Friday Computer Vision - Advanced visual understanding.
Object detection, OCR, scene analysis, face recognition.
"""
from __future__ import annotations

import os
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path


# ─── Vision Analysis ───────────────────────────────────#

def analyze_image(image_path: str = None, image_b64: str = None) -> Dict[str, Any]:
    """
    Analyze an image using available vision models.
    Returns description, objects, text, colors, etc.
    """
    if not image_path and not image_b64:
        return {"error": "Image path or base64 data required"}
    
    # Try Google Gemini Vision first
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {"error": "GOOGLE_API_KEY not set"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Load image
        if image_b64:
            image_data = base64.b64decode(image_b64)
            import io
            image = io.BytesIO(image_data)
        else:
            image = Path(image_path)
            if not image.exists():
                return {"error": f"Image not found: {image_path}"}
        
        # Generate content
        prompt = """Analyze this image thoroughly. Provide:
        1. Description (2-3 sentences)
        2. Objects detected (list with confidence)
        3. Text found (OCR)
        4. Dominant colors
        5. Scene type
        6. Any notable details
        """
        
        response = model.generate_content([prompt, image])
        
        return {
            "success": True,
            "description": response.text,
            "model": "gemini-1.5-flash",
        }
        
    except ImportError:
        return {"error": "Gemini not available"}
    except Exception as e:
        return {"error": str(e)}


def detect_objects(image_path: str) -> List[Dict[str, Any]]:
    """
    Detect objects in image using YOLO or similar.
    Returns list of {label, confidence, bbox}
    """
    try:
        import cv2
        import numpy as np
        
        # Try YOLO via ultralytics
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")  # Nano model
            results = model(image_path)
            
            objects = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    bbox = [float(x) for x in box.xyxy[0]]
                    objects.append({
                        "label": model.names[cls_id],
                        "confidence": conf,
                        "bbox": bbox,
                    })
            return objects
            
        except ImportError:
            # Fallback: use OpenCV contours (basic)
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            return [
                {"label": "contour", "confidence": 1.0, "bbox": cv2.boundingRect(c)}
                for c in contours[:20]
            ]
            
    except ImportError:
        return [{"error": "OpenCV not installed. Run: pip install opencv-python"}]
    except Exception as e:
        return [{"error": str(e)}]


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using OCR.
    Uses pytesseract or easyocr.
    """
    # Try easyocr first (better accuracy)
    try:
        import easyocr
        reader = easyocr.Reader(['en'])
        result = reader.readtext(image_path)
        text = " ".join([r[1] for r in result])
        return text
        
    except ImportError:
        # Fallback to pytesseract
        try:
            import pytesseract
            from PIL import Image
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text
            
        except ImportError:
            return "[FAIL] OCR not available. Install: pip install easyocr OR pytesseract"
        except Exception as e:
            return f"OCR error: {e}"
            
    except Exception as e:
        return f"EasyOCR error: {e}"


def analyze_video(video_path: str, sample_rate: int = 30) -> Dict[str, Any]:
    """
    Analyze video by sampling frames.
    Returns summary, key frames analysis, object tracking.
    """
    try:
        import cv2
        import numpy as np
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": f"Cannot open video: {video_path}"}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frames_analyzed = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % (sample_rate * int(fps)) == 0:
                # Save frame temporarily
                temp_path = f"temp_frame_{frame_count}.jpg"
                cv2.imwrite(temp_path, frame)
                
                # Analyze frame
                analysis = analyze_image(temp_path)
                if "description" in analysis:
                    frames_analyzed.append({
                        "frame": frame_count,
                        "time": frame_count / fps,
                        "analysis": analysis["description"][:200],
                    })
                
                # Cleanup
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            frame_count += 1
        
        cap.release()
        
        return {
            "duration_seconds": duration,
            "total_frames": total_frames,
            "fps": fps,
            "frames_sampled": len(frames_analyzed),
            "key_frames": frames_analyzed[:10],
        }
        
    except ImportError:
        return {"error": "OpenCV not installed. Run: pip install opencv-python"}
    except Exception as e:
        return {"error": str(e)}


def compare_images(image1_path: str, image2_path: str) -> Dict[str, Any]:
    """
    Compare two images and find differences.
    Returns similarity score, differences.
    """
    try:
        from PIL import Image
        import numpy as np
        
        img1 = Image.open(image1_path).convert("RGB")
        img2 = Image.open(image2_path).convert("RGB")
        
        # Resize to same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size)
        
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # Calculate difference
        diff = np.abs(arr1.astype(float) - arr2.astype(float))
        similarity = 1.0 - (diff.sum() / (diff.size * 255))
        
        # Create diff image
        diff_img = Image.fromarray(diff.astype("uint8"))
        diff_path = "diff_result.jpg"
        diff_img.save(diff_path)
        
        return {
            "similarity": float(similarity),
            "difference_percentage": (1 - similarity) * 100,
            "diff_image": diff_path,
            "pixels_diff": int(diff.sum() / 255),
        }
        
    except ImportError:
        return {"error": "PIL not installed. Run: pip install Pillow"}
    except Exception as e:
        return {"error": str(e)}


def scan_screen_for_objects() -> str:
    """
    Scan current screen and detect objects.
    Uses screenshot + vision analysis.
    """
    try:
        from mss import mss
        import tempfile
        
        with mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            temp_path = tempfile.mktemp(suffix=".jpg")
            mss.tools.to_file(temp_path, screenshot)
        
        objects = detect_objects(temp_path)
        
        if not objects:
            return "No objects detected."
        if "error" in objects[0]:
            return objects[0]["error"]
        
        lines = ["### SCREEN OBJECTS DETECTED", ""]
        for obj in objects[:20]:
            lines.append(f"- {obj['label']} ({obj['confidence']:.1%})")
        
        # Cleanup
        try:
            os.remove(temp_path)
        except:
            pass
        
        return "\n".join(lines)
        
    except ImportError:
        return "[FAIL] mss not installed. Run: pip install mss"
    except Exception as e:
        return f"Screen scan error: {e}"


# ─── Tool Function for Friday ───────────────────────────────────#

def vision_tool(
    action: str = "analyze",
    image_path: str = None,
    image_b64: str = None,
) -> str:
    """
    Friday tool for computer vision operations.
    Actions: analyze, objects, ocr, video, compare, screen_scan
    """
    if action == "analyze":
        result = analyze_image(image_path, image_b64)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"### IMAGE ANALYSIS\n\n{result.get('description', 'No description')}"
    
    if action == "objects":
        if not image_path:
            return "[FAIL] Image path required."
        objects = detect_objects(image_path)
        if not objects:
            return "No objects detected."
        if "error" in objects[0]:
            return f"[FAIL] {objects[0]['error']}"
        
        lines = [f"### OBJECTS DETECTED ({len(objects)})", ""]
        for obj in objects[:30]:
            lines.append(f"- {obj['label']} ({obj['confidence']:.1%})")
        return "\n".join(lines)
    
    if action == "ocr":
        if not image_path:
            return "[FAIL] Image path required."
        text = extract_text_from_image(image_path)
        return f"### TEXT EXTRACTED\n\n{text[:1000]}"
    
    if action == "video":
        if not image_path:
            return "[FAIL] Video path required."
        result = analyze_video(image_path)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        lines = ["### VIDEO ANALYSIS", ""]
        lines.append(f"**Duration**: {result['duration_seconds']:.1f}s")
        lines.append(f"**Frames**: {result['total_frames']} ({result['fps']:.1f} FPS)")
        lines.append(f"**Sampled**: {result['frames_sampled']} frames")
        lines.append("")
        lines.append("**Key Frames**:")
        for kf in result.get("key_frames", [])[:5]:
            lines.append(f"  {kf['time']:.1f}s: {kf['analysis']}")
        return "\n".join(lines)
    
    if action == "compare":
        if not image_path or "," not in image_path:
            return "[FAIL] Provide two image paths separated by comma."
        img1, img2 = [p.strip() for p in image_path.split(",", 1)]
        result = compare_images(img1, img2)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        return f"""### IMAGE COMPARISON
**Similarity**: {result['similarity']:.1%}
**Difference**: {result['difference_percentage']:.1f}%
**Diff Image**: {result.get('diff_image', 'N/A')}
"""
    
    if action == "screen_scan":
        return scan_screen_for_objects()
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Computer Vision...\n")
    
    # Test with a sample image if available
    test_img = "test_image.jpg"
    if os.path.exists(test_img):
        print("--- Analyze Image ---")
        print(vision_tool("analyze", image_path=test_img))
    else:
        print("No test image available.")
