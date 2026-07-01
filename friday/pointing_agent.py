"""FRIDAY Pointing Agent — Screen coordinate mapping + POINT tag pipeline.

Core mechanic:
  1. Capture screenshot of all monitors
  2. Send to LLM vision model with question
  3. LLM responds with [POINT:x,y:label] tags for every relevant element
  4. Parse tags → map to screen coordinates → annotate on overlay
  5. All annotations stay until cleared
"""

from __future__ import annotations

import re
import math
import time
import base64
import io
from typing import Optional
from dataclasses import dataclass

from PIL import Image, ImageGrab


@dataclass
class PointTarget:
    x: float
    y: float
    label: str = ""
    screen_number: int = 0


POINT_PATTERN = re.compile(
    r'\[POINT:(?:(none)|(\d+)\s*,\s*(\d+)(?::([^\]:\s][^\]:]*?))?(?::screen(\d+))?)\]',
    re.IGNORECASE
)


def parse_point_tags(text: str) -> tuple[list[PointTarget], str]:
    """Parse [POINT:x,y:label] tags from LLM response text.

    Returns:
      (targets, cleaned_text) — targets is list of PointTarget, cleaned_text
      has tags removed.
    """
    targets: list[PointTarget] = []
    cleaned = text

    for match in POINT_PATTERN.finditer(text):
        is_none = match.group(1) is not None
        if is_none:
            continue

        x_str, y_str = match.group(2), match.group(3)
        label = match.group(4) or ""
        screen_str = match.group(5)

        if x_str is None or y_str is None:
            continue

        x = float(x_str)
        y = float(y_str)
        screen = int(screen_str) if screen_str else 0

        targets.append(PointTarget(x=x, y=y, label=label, screen_number=screen))

    cleaned = POINT_PATTERN.sub('', cleaned)

    return targets, cleaned


def map_to_screen_coords(x: float, y: float,
                         capture_w: int = 0, capture_h: int = 0,
                         monitor_index: int = 0) -> tuple[float, float]:
    """Map screenshot-relative coords to absolute screen coords.

    If capture_w/h are 0, uses current screen size (1:1 mapping).
    monitor_index: which monitor the coords are relative to (for multi-monitor).
    """
    screen_w, screen_h = _get_screen_size()
    monitors = _get_monitor_offsets()
    monitor_count = len(monitors)

    if capture_w <= 0 or capture_h <= 0:
        capture_w, capture_h = screen_w, screen_h

    if monitor_index > 0 and monitor_index <= monitor_count:
        mx, my, mw, mh = monitors[monitor_index - 1]
        scale_x = mw / max(capture_w, 1)
        scale_y = mh / max(capture_h, 1)
        abs_x = x * scale_x + mx
        abs_y = y * scale_y + my
    else:
        scale_x = screen_w / max(capture_w, 1)
        scale_y = screen_h / max(capture_h, 1)
        abs_x = x * scale_x
        abs_y = y * scale_y

    abs_x = max(0, min(abs_x, float(screen_w)))
    abs_y = max(0, min(abs_y, float(screen_h)))

    return (abs_x, abs_y)


def capture_for_llm(max_dim: int = 1280) -> tuple[str, int, int]:
    """Capture primary monitor screenshot, resize for LLM vision.
    Returns (b64_jpeg, width, height).
    """
    import base64, io
    img = ImageGrab.grab()
    orig_w, orig_h = img.size
    scale = min(max_dim / orig_w, max_dim / orig_h, 1.0)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode()

    return (b64, new_w, new_h)


def capture_all_monitors(max_dim: int = 1280) -> list[dict]:
    """Capture all monitors separately for multi-monitor support.
    Returns list of dicts: {b64, w, h, label, screen_number, offset_x, offset_y, display_w, display_h}
    """
    monitors = _get_monitor_offsets()
    results = []

    for i, (mx, my, mw, mh) in enumerate(monitors):
        img = ImageGrab.grab(bbox=(mx, my, mx + mw, my + mh))
        scale = min(max_dim / mw, max_dim / mh, 1.0)
        nw, nh = int(mw * scale), int(mh * scale)
        img_resized = img.resize((nw, nh), Image.LANCZOS)

        buf = io.BytesIO()
        img_resized.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()

        cursor_here = _is_cursor_in_rect(mx, my, mw, mh)

        results.append({
            "b64": b64,
            "w": nw,
            "h": nh,
            "label": f"screen {i+1} of {len(monitors)}{' -- cursor is here (primary focus)' if cursor_here else ''}",
            "screen_number": i + 1,
            "offset_x": mx,
            "offset_y": my,
            "display_w": mw,
            "display_h": mh,
        })

    return results


def _is_cursor_in_rect(x: int, y: int, w: int, h: int) -> bool:
    try:
        cx, cy = _get_cursor_pos()
        return x <= cx <= x + w and y <= cy <= y + h
    except Exception:
        return False


def _get_cursor_pos() -> tuple[int, int]:
    try:
        import pyautogui
        return pyautogui.position()
    except Exception:
        return (0, 0)


def _get_screen_size() -> tuple[int, int]:
    try:
        from screeninfo import get_monitors
        monitors = get_monitors()
        max_w = max(m.width for m in monitors)
        max_h = max(m.height for m in monitors)
        return (max_w, max_h)
    except ImportError:
        import pyautogui
        w, h = pyautogui.size()
        return (int(w), int(h))


def _get_monitor_offsets() -> list[tuple[int, int, int, int]]:
    try:
        from screeninfo import get_monitors
        return [(m.x, m.y, m.width, m.height) for m in get_monitors()]
    except ImportError:
        import pyautogui
        w, h = pyautogui.size()
        return [(0, 0, int(w), int(h))]


def process_llm_response(text: str, overlay_engine=None,
                         auto_click: bool = False,
                         capture_w: int = 0, capture_h: int = 0,
                         draw_labels: bool = True) -> str:
    """Parse [POINT] tags from LLM response and execute pointing actions.

    Args:
      text: Raw LLM response text with [POINT:x,y:label] tags
      overlay_engine: OverlayEngine instance for visual annotation
      auto_click: Whether to click at each target after pointing
      capture_w: Screenshot width used for LLM vision (for coordinate mapping)
      capture_h: Screenshot height used for LLM vision
      draw_labels: Whether to draw text labels at each coordinate

    Returns:
      Cleaned text with tags removed
    """
    targets, cleaned = parse_point_tags(text)

    if not targets:
        return cleaned

    if overlay_engine is None:
        return cleaned

    from friday.overlay_engine import ensure_running
    ensure_running()

    for t in targets:
        abs_x, abs_y = map_to_screen_coords(
            t.x, t.y, capture_w, capture_h,
            monitor_index=t.screen_number
        )

        overlay_engine.fly_to(abs_x, abs_y, t.label)

        if draw_labels and t.label:
            overlay_engine.show_text(abs_x + 40, abs_y - 15, t.label)

        if auto_click:
            _do_click(abs_x, abs_y)

    return cleaned


def _do_click(x: float, y: float):
    try:
        import pyautogui
        pyautogui.click(int(x), int(y))
        pyautogui.sleep(0.1)
    except Exception:
        pass


def analyze_screen(question: str = "",
                   overlay_engine=None,
                   auto_annotate: bool = True) -> str:
    """Full pipeline: capture screen → NIM vision → parse coordinates → annotate.

    Captures all monitors, sends to NVIDIA NIM VL model with question, parses
    [POINT] tags from the response, and annotates everything on the overlay.

    Falls through model chain:
      microsoft/Florence-2-large →
      nvidia/nemotron-nano-12b-v2-vl →
      meta/llama-3.2-11b-vision-instruct →
      Gemini (if NIM keys fail)

    Args:
      question: What to ask about the screen (e.g. "Find all buttons and input fields")
      overlay_engine: OverlayEngine for visual annotation
      auto_annotate: Whether to automatically draw labels/pointers at each coordinate

    Returns:
      Cleaned LLM response text
    """
    try:
        import base64 as _b64
        import io as _io
        import os as _os
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()

        monitors = capture_all_monitors()

        if overlay_engine and auto_annotate:
            from friday.overlay_engine import ensure_running
            ensure_running()

        prompt = (
            "List ALL visible UI elements on this screen. Include buttons, text fields, "
            "menu items, icons, tabs, scroll bars, title bar, and any interactive controls. "
            "For each element return a [POINT:x,y:label] tag with its "
            "center coordinates and a precise label describing its function. "
            "Be thorough. Include at least 10 [POINT] tags."
        )
        if question:
            prompt = (
                f"The user asks: {question}\n\n"
                "List ALL visible UI elements on this screen. Include buttons, text fields, "
                "menu items, icons, tabs, scroll bars, title bar, and any interactive controls. "
                "For each element return a [POINT:x,y:label] tag with its "
                "center coordinates and a precise label describing its function. "
                "Be thorough. Include at least 10 [POINT] tags."
            )

        api_key = (
            _os.environ.get("NVIDIA_VISION_API_KEY")
            or _os.environ.get("NVIDIA_NIM_API_KEY")
            or _os.environ.get("NVIDIA_API_KEY")
            or _os.environ.get("NIM_API_KEY")
        )
        if not api_key:
            # fallback: try Gemini directly
            return _analyze_screen_gemini(question, monitors, overlay_engine, auto_annotate)

        client = OpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            max_retries=0,
        )

        content: list[dict] = [{"type": "text", "text": prompt}]
        for m in monitors:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{m['b64']}"},
            })
            content.append({"type": "text", "text": f"--- {m['label']} ---"})

        vision_models = [
            "nvidia/nemotron-nano-12b-v2-vl",
            "meta/llama-3.2-11b-vision-instruct",
        ]

        text = ""
        for model in vision_models:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=1024,
                    temperature=0.3,
                    timeout=45,
                )
                text = response.choices[0].message.content.strip()
                if text:
                    break
            except Exception:
                continue

        if not text:
            return "[FAIL] All NIM vision models failed."

        if overlay_engine and auto_annotate:
            targets, cleaned = parse_point_tags(text)
            _annotate_targets(targets, monitors, overlay_engine)
            return cleaned

        return text

    except ImportError as e:
        return f"[FAIL] Missing dependency: {e}"
    except Exception as e:
        return f"[FAIL] analyze_screen error: {e}"

def _analyze_screen_gemini(question: str, monitors: list[dict],
                            overlay_engine=None,
                            auto_annotate: bool = True) -> str:
    """Fallback: use Gemini when no NIM key is available."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        import requests as _requests
        import os as _os
        api_key = _os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "[FAIL] No NIM or Gemini API key configured."

        prompt = (
            "List ALL visible UI elements on this screen. Include buttons, text fields, "
            "menu items, icons, tabs, scroll bars, title bar, and any interactive controls. "
            "For each element return a [POINT:x,y:label] tag with its "
            "center coordinates and a precise label describing its function. "
            "Be thorough. Include at least 10 [POINT] tags."
        )
        if question:
            prompt = (
                f"The user asks: {question}\n\n"
                "List ALL visible UI elements on this screen. Include buttons, text fields, "
                "menu items, icons, tabs, scroll bars, title bar, and any interactive controls. "
                "For each element return a [POINT:x,y:label] tag with its "
                "center coordinates and a precise label describing its function. "
                "Be thorough. Include at least 10 [POINT] tags."
            )

        parts = [{"text": prompt}]
        for m in monitors:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": m["b64"]}})
            parts.append({"text": f"--- {m['label']} ---"})

        resp = _requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={"contents": [{"parts": parts}]},
            timeout=30
        )
        data = resp.json()
        if "candidates" not in data or not data["candidates"]:
            return f"[FAIL] Gemini error: {data}"
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        if overlay_engine and auto_annotate:
            targets, cleaned = parse_point_tags(text)
            _annotate_targets(targets, monitors, overlay_engine)
            return cleaned
        return text
    except Exception as e:
        return f"[FAIL] Gemini fallback error: {e}"


def _annotate_targets(targets: list[PointTarget],
                      monitors: list[dict],
                      overlay_engine):
    """Draw labels and pointers at each target coordinate."""
    for t in targets:
        monitor_info = None
        if t.screen_number > 0 and t.screen_number <= len(monitors):
            monitor_info = monitors[t.screen_number - 1]

        if monitor_info:
            abs_x, abs_y = map_to_screen_coords(
                t.x, t.y,
                monitor_info["w"], monitor_info["h"],
                t.screen_number
            )
        else:
            abs_x, abs_y = map_to_screen_coords(t.x, t.y)

        overlay_engine.fly_to(abs_x, abs_y, t.label)

        if t.label:
            overlay_engine.show_text(abs_x + 40, abs_y - 15, t.label)


def find_and_click_element(element_desc: str, overlay_engine=None) -> str:
    """Find a UI element by description and click it.
    Uses NIM vision to locate elements, then clicks at the matched one.
    """
    b64, cap_w, cap_h = capture_for_llm()

    from dotenv import load_dotenv
    load_dotenv()
    import os as _os
    from openai import OpenAI
    api_key = (
        _os.environ.get("NVIDIA_VISION_API_KEY")
        or _os.environ.get("NVIDIA_NIM_API_KEY")
        or _os.environ.get("NVIDIA_API_KEY")
        or _os.environ.get("NIM_API_KEY")
    )
    if not api_key:
        return "[FAIL] No NVIDIA NIM API key configured."

    client = OpenAI(
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        max_retries=0,
    )

    vision_prompt = (
        f"Find the exact pixel location of '{element_desc}' on this "
        f"screenshot. The screenshot is {cap_w}x{cap_h}px. "
        "Return ONLY a [POINT:x,y:label] tag."
    )

    text = ""
    for model in ("nvidia/nemotron-nano-12b-v2-vl", "meta/llama-3.2-11b-vision-instruct"):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": vision_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]}],
                max_tokens=256,
                temperature=0.3,
                timeout=45,
            )
            text = response.choices[0].message.content.strip()
            if text:
                break
        except Exception:
            continue

    if not text:
        return f"[FAIL] Could not locate: {element_desc} (NIM vision returned empty)"

    targets, _ = parse_point_tags(text)
    if not targets:
        return f"[FAIL] Could not locate: {element_desc}"

    t = targets[0]
    abs_x, abs_y = map_to_screen_coords(t.x, t.y, cap_w, cap_h)

    if overlay_engine:
        from friday.overlay_engine import ensure_running
        ensure_running()
        overlay_engine.fly_to(abs_x, abs_y, f"Click: {element_desc}")
        time.sleep(0.5)

    _do_click(abs_x, abs_y)

    return f"[OK] Clicked '{element_desc}' at ({int(abs_x)}, {int(abs_y)})"
