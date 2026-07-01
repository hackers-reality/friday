"""FRIDAY Visual Overlay — Non-blocking animated screen overlay.
Wraps overlay_engine.py with the same API as before for backward compatibility.

All functions are non-blocking — they queue commands to a background Tkinter
process. The overlay window stays open persistently and shows a cursor-following
"buddy" indicator, bezier-arc flight animations, speech bubbles, and annotations.
"""

from __future__ import annotations

from .overlay_engine import get_engine, ensure_running as _ensure
from typing import Optional


def show_pointer(x: int, y: int, label: str = "",
                 duration: float = 3.0, color: str = "#3B82F6") -> str:
    """Animate the buddy to screen (x,y) with optional label.
    Non-blocking — returns immediately.
    """
    try:
        eng = _ensure()
        eng.set_colors(primary=color)
        eng.fly_to(float(x), float(y), label, duration)
        return f"[OK] Pointer flying to ({x}, {y})" + (f": {label}" if label else "")
    except Exception as e:
        return f"[FAIL] Pointer: {e}"


def show_cursor_hint(text: str, duration: float = 3.0,
                     color: str = "#3B82F6") -> str:
    """Show a speech bubble near the cursor.
    Non-blocking — the bubble appears at the buddy's current position.
    """
    try:
        eng = _ensure()
        eng.set_colors(primary=color)
        bx, by = eng.get_buddy_position()
        eng.fly_to(bx, by - 60, text, duration)
        return f"[OK] Cursor hint: {text[:60]}"
    except Exception as e:
        return f"[FAIL] Cursor hint: {e}"


def show_annotation_box(x: int, y: int, width: int, height: int,
                        label: str = "", color: str = "#EF4444",
                        duration: float = 3.0,
                        persist: float = 3600.0) -> str:
    """Highlight a region with a colored dashed border.
    Non-blocking — draws immediately on the overlay canvas.
    persist: how long to stay (default 3600s = 1hr).
    """
    try:
        eng = _ensure()
        eng.draw_box(float(x), float(y), float(width), float(height),
                     color=color, label=label, duration=duration,
                     persist=persist)
        return f"[OK] Annotation at ({x},{y}) {width}x{height}"
    except Exception as e:
        return f"[FAIL] Annotation: {e}"


def show_draw_arrow(x1: int, y1: int, x2: int, y2: int,
                    color: str = "#3B82F6", duration: float = 3.0,
                    persist: float = 3600.0) -> str:
    """Draw an arrow from (x1,y1) to (x2,y2).
    duration: animation speed. persist: how long to stay on screen.
    """
    try:
        eng = _ensure()
        eng.draw_arrow(float(x1), float(y1), float(x2), float(y2),
                       color=color, duration=duration, persist=persist)
        return f"[OK] Arrow ({x1},{y1}) -> ({x2},{y2})"
    except Exception as e:
        return f"[FAIL] Arrow: {e}"


def draw_line(x1: int, y1: int, x2: int, y2: int,
              color: str = "#3B82F6", width: int = 4,
              duration: float = 3.0, persist: float = 3600.0) -> str:
    """Draw animated line. duration=animation speed, persist=how long it stays."""
    try:
        eng = _ensure()
        eng.draw_line(float(x1), float(y1), float(x2), float(y2),
                      color=color, width=width, duration=duration,
                      persist=persist)
        return f"[OK] Line ({x1},{y1}) -> ({x2},{y2})"
    except Exception as e:
        return f"[FAIL] Line: {e}"


def draw_polygon(points: list, color: str = "#3B82F6",
                 fill_color: Optional[str] = None,
                 duration: float = 3.0,
                 persist: float = 3600.0) -> str:
    """Draw a closed polygon from a list of (x,y) coordinate pairs.
    duration=animation speed, persist=how long it stays.
    """
    try:
        eng = _ensure()
        pts = [(float(p[0]), float(p[1])) for p in points]
        eng.draw_polygon(pts, color=color, fill_color=fill_color,
                         duration=duration, persist=persist)
        return f"[OK] Polygon with {len(pts)} points"
    except Exception as e:
        return f"[FAIL] Polygon: {e}"


def show_text(x: int, y: int, text: str,
              color: str = "#FFFFFF", duration: float = 3.0,
              persist: float = 3600.0) -> str:
    """Show text at screen coordinates.
    duration=animation speed, persist=how long it stays.
    """
    try:
        eng = _ensure()
        eng.show_text(float(x), float(y), text, color=color,
                      duration=duration, persist=persist)
        return f"[OK] Text at ({x},{y}): {text[:60]}"
    except Exception as e:
        return f"[FAIL] Text: {e}"


def draw_path(path_data: str, x: int = 0, y: int = 0,
              color: str = "#3B82F6", width: float = 3,
              duration: float = 3.0, persist: float = 3600.0) -> str:
    """Draw an arbitrary SVG path on the overlay.
    path_data: SVG path string like 'M 100 100 C 200 50, 300 150, 400 100'
    duration: animation speed, persist: how long it stays.
    """
    try:
        eng = _ensure()
        eng.draw_path(path_data, float(x), float(y), color, width,
                      duration, persist)
        return f"[OK] Path drawn at offset ({x},{y})"
    except Exception as e:
        return f"[FAIL] Draw path: {e}"


def start_teaching():
    """Enter teaching mode — independent cursor for demonstrations."""
    try:
        eng = _ensure()
        eng.start_teaching()
        return "[OK] Teaching mode started"
    except Exception as e:
        return f"[FAIL] Start teaching: {e}"


def stop_teaching():
    """Exit teaching mode."""
    try:
        eng = get_engine()
        eng.stop_teaching()
        return "[OK] Teaching mode stopped"
    except Exception as e:
        return f"[FAIL] Stop teaching: {e}"


def teaching_move_to(x: int, y: int, label: str = ""):
    """Move the teaching cursor to a position."""
    try:
        eng = _ensure()
        eng.teaching_move_to(float(x), float(y), label)
        return f"[OK] Teaching cursor moved to ({x},{y})"
    except Exception as e:
        return f"[FAIL] Teaching move: {e}"


def teaching_click(x: int, y: int, label: str = ""):
    """Show teaching cursor clicking at position."""
    try:
        eng = _ensure()
        eng.teaching_click(float(x), float(y), label)
        return f"[OK] Teaching click at ({x},{y})"
    except Exception as e:
        return f"[FAIL] Teaching click: {e}"


def teaching_highlight(x: int, y: int, width: int, height: int, label: str = ""):
    """Highlight a region with the teaching cursor."""
    try:
        eng = _ensure()
        eng.teaching_highlight(float(x), float(y), float(width), float(height), label)
        return f"[OK] Teaching highlight at ({x},{y}) {width}x{height}"
    except Exception as e:
        return f"[FAIL] Teaching highlight: {e}"


def clear_overlays() -> str:
    """Remove all overlays and return buddy to cursor-following mode."""
    try:
        eng = get_engine()
        eng.clear_all()
        return "[OK] All overlays cleared."
    except Exception as e:
        return f"[FAIL] Clear overlays: {e}"


def start_overlay():
    """Start the overlay engine (background thread)."""
    _ensure()


def stop_overlay():
    """Stop the overlay engine."""
    try:
        eng = get_engine()
        eng.stop()
    except Exception:
        pass


def set_overlay_state(state: str):
    """Set overlay visibility state: 'hidden' or 'active'."""
    eng = get_engine()
    eng.set_state(state)
