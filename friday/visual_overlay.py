"""FRIDAY Visual Overlay — Cursor buddy + screen pointer inspired by Clicky.
Shows temporary visual indicators (circles, labels, hints) on screen.
Uses transparent Tkinter overlay windows for cross-platform compatibility.
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Optional

_overlay_lock = threading.Lock()
_overlay_windows: list[tk.Tk] = []


def _make_overlay_window(x: int, y: int, width: int, height: int,
                         color: str = "#3B82F6") -> tk.Tk:
    """Create a transparent always-on-top overlay window."""
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "white")
    root.configure(bg="white")
    root.geometry(f"{width}x{height}+{x}+{y}")
    with _overlay_lock:
        _overlay_windows.append(root)
    return root


def show_pointer(x: int, y: int, label: str = "",
                 duration: float = 3.0, color: str = "#3B82F6") -> str:
    """Show a circular pointer with optional label at screen coordinates.
    Inspired by Clicky's [POINT:x,y:label] mechanic.
    """
    try:
        size = 120
        root = _make_overlay_window(x - size // 2, y - size // 2, size, size + 30)
        canvas = tk.Canvas(root, width=size, height=size + 30,
                           bg="white", highlightthickness=0)
        canvas.pack()
        cx, cy = size // 2, size // 2 - 5
        r = 25
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           outline=color, width=4, fill="")

        inner_r = 8
        canvas.create_oval(cx - inner_r, cy - inner_r,
                           cx + inner_r, cy + inner_r,
                           fill=color, outline="")

        if label:
            canvas.create_text(cx, cy + r + 15, text=label,
                               font=("Segoe UI", 10), fill=color)

        root.after(int(duration * 1000), _destroy_window, root)
        root.mainloop()
        return f"[OK] Pointer at ({x}, {y})" + (f": {label}" if label else "")
    except Exception as e:
        return f"[FAIL] Pointer: {e}"


def show_cursor_hint(text: str, duration: float = 3.0,
                     color: str = "#3B82F6") -> str:
    """Show a text hint near the current cursor position (like Clicky's buddy)."""
    try:
        import pyautogui
        mx, my = pyautogui.position()
        padding = 16
        line_height = 20
        lines = text.split("\n")
        width = max(200, min(500, max(len(l) for l in lines) * 9))
        height = len(lines) * line_height + padding * 2

        x = min(mx + 20, pyautogui.size().width - width - 20)
        y = min(my - height // 2, pyautogui.size().height - height - 20)
        if y < 0:
            y = max(0, my + 20)

        root = _make_overlay_window(int(x), int(y), int(width), int(height))
        canvas = tk.Canvas(root, width=int(width), height=int(height),
                           bg="white", highlightthickness=0)
        canvas.pack()

        canvas.create_rectangle(0, 0, int(width), int(height),
                                fill=color, outline="", stipple="gray25")
        canvas.create_rectangle(2, 2, int(width) - 2, int(height) - 2,
                                fill="white", outline=color, width=2)

        for i, line in enumerate(lines):
            canvas.create_text(int(width) // 2, padding + i * line_height + 4,
                               text=line, font=("Segoe UI", 10),
                               fill=color, anchor="n")

        root.after(int(duration * 1000), _destroy_window, root)
        root.mainloop()
        return f"[OK] Cursor hint: {text[:60]}"
    except Exception as e:
        return f"[FAIL] Cursor hint: {e}"


def show_annotation_box(x: int, y: int, width: int, height: int,
                        label: str = "", color: str = "#EF4444",
                        duration: float = 4.0) -> str:
    """Highlight a region of the screen with a colored border box.
    Useful for pointing out UI elements, buttons, or sections.
    """
    try:
        root = _make_overlay_window(x, y, width, height)
        canvas = tk.Canvas(root, width=width, height=height,
                           bg="white", highlightthickness=0)
        canvas.pack()

        canvas.create_rectangle(2, 2, width - 2, height - 2,
                                outline=color, width=4, dash=(8, 4))

        if label:
            text_bg = canvas.create_rectangle(4, 4, 8 + len(label) * 9, 24,
                                              fill=color, outline="")
            canvas.create_text(8 + len(label) * 4, 14, text=label,
                               font=("Segoe UI", 10, "bold"),
                               fill="white", anchor="center")

        root.after(int(duration * 1000), _destroy_window, root)
        root.mainloop()
        return f"[OK] Annotation at ({x},{y}) {width}x{height}"
    except Exception as e:
        return f"[FAIL] Annotation: {e}"


def clear_overlays() -> str:
    """Destroy all active overlay windows immediately."""
    with _overlay_lock:
        for w in _overlay_windows[:]:
            try:
                w.destroy()
            except Exception:
                pass
        _overlay_windows.clear()
    return "[OK] All overlays cleared."


def _destroy_window(root: tk.Tk):
    """Safely destroy an overlay window."""
    try:
        root.destroy()
        with _overlay_lock:
            if root in _overlay_windows:
                _overlay_windows.remove(root)
    except Exception:
        pass
