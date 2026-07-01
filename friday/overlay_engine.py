"""FRIDAY Overlay Engine — Non-blocking transparent screen overlay.
Replaces visual_overlay.py with a real-time animated overlay system.

Architecture:
  Runs Tkinter in a daemon thread. Commands arrive via queue.Queue.
  The overlay window is always-on, transparent, and click-through on Windows.
  A cursor "buddy" (small ring+dot) follows the mouse when idle.
  When fly_to is triggered, the buddy animates in a bezier arc to the target,
  displays a speech bubble, then returns to cursor-following mode.

Capabilities:
  - Cursor buddy that follows the mouse (always-on)
  - Bezier-arc flight animation to any screen coordinate
  - Speech bubble with streaming text
  - Annotation boxes, arrows, text labels
  - SVG path drawing (arbitrary shapes via path data strings)
  - Teaching mode: independent second cursor for demonstrations
  - Multi-monitor support (one overlay per display)

State machine:
  HIDDEN -> FOLLOWING -> ANIMATING -> POINTING -> RETURNING -> FOLLOWING
  HIDDEN/FOLLOWING -> TEACHING (independent cursor mode)
"""

from __future__ import annotations

import math
import threading
import queue
import time
import tkinter as tk
import re
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

import pyautogui


class BuddyState(Enum):
    HIDDEN = auto()
    FOLLOWING = auto()
    ANIMATING = auto()
    POINTING = auto()
    RETURNING = auto()
    TEACHING = auto()


@dataclass
class AnimationState:
    start_x: float = 0.0
    start_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    control_x: float = 0.0
    control_y: float = 0.0
    start_time: float = 0.0
    duration: float = 0.8
    progress: float = 0.0
    label: str = ""
    return_start: tuple = (0.0, 0.0)
    label_visible: bool = False
    label_chars_printed: int = 0


class OverlayEngine:
    """Non-blocking transparent overlay window.

    Usage:
        eng = OverlayEngine()
        eng.start()
        eng.fly_to(500, 300, "Click the Submit button")
        eng.draw_path("M 100 100 C 200 50, 300 150, 400 100")
        eng.start_teaching()
        eng.teaching_move_to(500, 400, "Click here")
        ...
        eng.stop()
    """

    def __init__(self, primary_color: str = "#FFFFFF",
                 secondary_color: str = "#3B82F6",
                 text_color: str = "#000000",
                 bg_color: str = "#FF00FF"):
        self.primary = primary_color
        self.secondary = secondary_color
        self.text_color = text_color
        self.bg_color = bg_color

        self._cmd_queue: queue.Queue = queue.Queue()
        self._result_queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False

        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None

        self._state = BuddyState.HIDDEN
        self._anim = AnimationState()
        self._buddy_visible = False
        self._follow_enabled = True

        self._cursor_x = 0.0
        self._cursor_y = 0.0
        self._buddy_x = 0.0
        self._buddy_y = 0.0

        self._annotations: list[dict] = []
        self._text_bubbles: list[dict] = []
        self._duration_timers: dict = {}

        self._screen_w = 0
        self._screen_h = 0

        self._teaching_mode = False
        self._teaching_x = 0.0
        self._teaching_y = 0.0
        self._teaching_visible = False
        self._teaching_click_anim = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="overlay-engine")
        self._thread.start()
        time.sleep(0.1)

    def stop(self):
        self._running = False
        self._cmd_queue.put({"cmd": "shutdown"})

    def fly_to(self, x: float, y: float, label: str = "",
               duration: Optional[float] = None):
        self._cmd_queue.put({
            "cmd": "fly_to",
            "x": x, "y": y,
            "label": label,
            "duration": duration
        })

    def show_buddy(self, visible: bool = True):
        self._cmd_queue.put({"cmd": "show_buddy", "visible": visible})

    def draw_box(self, x: float, y: float, w: float, h: float,
                 color: Optional[str] = None, label: str = "",
                 duration: float = 3.0, persist: Optional[float] = None):
        self._cmd_queue.put({
            "cmd": "draw_box",
            "x": x, "y": y, "w": w, "h": h,
            "color": color or self.secondary,
            "label": label, "duration": duration,
            "persist": persist,
        })

    def draw_arrow(self, x1: float, y1: float, x2: float, y2: float,
                   color: Optional[str] = None, duration: float = 3.0,
                   persist: Optional[float] = None):
        self._cmd_queue.put({
            "cmd": "draw_arrow",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "color": color or "#3B82F6", "duration": duration,
            "persist": persist,
        })

    def draw_line(self, x1: float, y1: float, x2: float, y2: float,
                  color: Optional[str] = None, width: float = 4,
                  duration: float = 3.0, persist: Optional[float] = None):
        """Draw a simple straight line between two points (no arrowhead).
        duration controls animation speed. persist controls how long it stays.
        """
        self._cmd_queue.put({
            "cmd": "draw_line",
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "color": color or "#3B82F6", "width": width,
            "duration": duration, "persist": persist,
        })

    def draw_polygon(self, points: list[tuple[float, float]],
                     color: Optional[str] = None,
                     fill_color: Optional[str] = None,
                     duration: float = 5.0,
                     persist: Optional[float] = None):
        """Draw a closed polygon from a list of (x,y) points."""
        flat = []
        for p in points:
            flat.extend(p)
        self._cmd_queue.put({
            "cmd": "draw_polygon",
            "points": flat,
            "color": color or "#3B82F6",
            "fill_color": fill_color,
            "duration": duration, "persist": persist,
        })

    def draw_path(self, path_data: str, x: float = 0, y: float = 0,
                  color: Optional[str] = None, width: float = 3,
                  duration: float = 5.0, persist: Optional[float] = None):
        """Draw an arbitrary SVG path on the overlay.
        path_data: SVG path commands like 'M 100 100 C 200 50, 300 150, 400 100'
        x, y: offset to translate the path
        """
        self._cmd_queue.put({
            "cmd": "draw_path",
            "path_data": path_data,
            "x": x, "y": y,
            "color": color or self.primary,
            "width": width,
            "duration": duration, "persist": persist,
        })

    def show_text(self, x: float, y: float, text: str,
                  color: Optional[str] = None, duration: float = 5.0,
                  persist: Optional[float] = None):
        self._cmd_queue.put({
            "cmd": "show_text",
            "x": x, "y": y, "text": text,
            "color": color or self.text_color,
            "duration": duration, "persist": persist,
        })

    def clear_all(self):
        self._cmd_queue.put({"cmd": "clear_all"})

    def clear_annotations(self):
        self._cmd_queue.put({"cmd": "clear_annotations"})

    def set_state(self, state: str):
        if state == "hidden":
            self._cmd_queue.put({"cmd": "set_state", "state": "HIDDEN"})
        elif state == "active":
            self._cmd_queue.put({"cmd": "set_state", "state": "FOLLOWING"})

    def set_colors(self, primary: Optional[str] = None,
                   secondary: Optional[str] = None,
                   text: Optional[str] = None):
        cmd = {"cmd": "set_colors"}
        if primary:
            cmd["primary"] = primary
        if secondary:
            cmd["secondary"] = secondary
        if text:
            cmd["text"] = text
        self._cmd_queue.put(cmd)

    def start_teaching(self):
        """Enter teaching mode — independent cursor for demonstrations."""
        self._cmd_queue.put({"cmd": "start_teaching"})

    def stop_teaching(self):
        """Exit teaching mode, return to following mode."""
        self._cmd_queue.put({"cmd": "stop_teaching"})

    def teaching_move_to(self, x: float, y: float, label: str = "",
                         duration: float = 0.8):
        """Move the teaching cursor to a position with bezier flight."""
        self._cmd_queue.put({
            "cmd": "teaching_move_to",
            "x": x, "y": y, "label": label, "duration": duration
        })

    def teaching_click(self, x: float, y: float, label: str = ""):
        """Move teaching cursor to (x,y), animate a click effect, then optionally click."""
        self._cmd_queue.put({
            "cmd": "teaching_click",
            "x": x, "y": y, "label": label
        })

    def teaching_highlight(self, x: float, y: float, w: float, h: float,
                           label: str = ""):
        """Draw attention to a region with the teaching cursor."""
        self._cmd_queue.put({
            "cmd": "teaching_highlight",
            "x": x, "y": y, "w": w, "h": h, "label": label
        })

    def teaching_type(self, text: str):
        """Show typing visualization at the teaching cursor position."""
        self._cmd_queue.put({
            "cmd": "teaching_type",
            "text": text
        })

    def _run(self):
        self._root = tk.Tk()
        self._setup_window()
        self._canvas = tk.Canvas(
            self._root,
            width=self._screen_w,
            height=self._screen_h,
            bg=self.bg_color,
            highlightthickness=0
        )
        self._canvas.pack()

        self._make_clickthrough()

        self._state = BuddyState.FOLLOWING
        self._buddy_visible = True

        self._tick()
        self._root.mainloop()

    def _setup_window(self):
        self._screen_w = self._root.winfo_screenwidth()
        self._screen_h = self._root.winfo_screenheight()
        self._buddy_x = self._screen_w / 2
        self._buddy_y = self._screen_h / 2

        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-transparentcolor", self.bg_color)
        self._root.configure(bg=self.bg_color)
        self._root.geometry(f"{self._screen_w}x{self._screen_h}+0+0")
        self._root.attributes("-alpha", 0.85)

    def _make_clickthrough(self):
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetParent(
                self._root.winfo_id())
            GWLP_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            WS_EX_TOOLWINDOW = 0x80
            style = ctypes.windll.user32.GetWindowLongW(
                hwnd, GWLP_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWLP_EXSTYLE, style)
        except Exception:
            pass

    def _tick(self):
        if not self._running:
            self._root.destroy()
            return

        self._process_commands()
        self._update_cursor_position()
        self._update_animations()
        self._render()

        try:
            self._root.after(16, self._tick)
        except tk.TclError:
            self._running = False

    def _process_commands(self):
        while not self._cmd_queue.empty():
            try:
                cmd = self._cmd_queue.get_nowait()
                self._handle_command(cmd)
            except queue.Empty:
                break

    def _handle_command(self, cmd: dict):
        ctype = cmd.get("cmd")

        if ctype == "shutdown":
            self._running = False

        elif ctype == "fly_to":
            self._start_fly_to(
                cmd["x"], cmd["y"],
                cmd.get("label", ""),
                cmd.get("duration")
            )

        elif ctype == "show_buddy":
            self._buddy_visible = cmd.get("visible", True)
            if self._buddy_visible and self._state == BuddyState.HIDDEN:
                self._state = BuddyState.FOLLOWING
            elif not self._buddy_visible:
                self._state = BuddyState.HIDDEN

        elif ctype == "draw_box":
            dur = cmd.get("duration", 3.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "box",
                "x": cmd["x"], "y": cmd["y"],
                "w": cmd["w"], "h": cmd["h"],
                "color": cmd.get("color", self.secondary),
                "label": cmd.get("label", ""),
            }, dur, persist)

        elif ctype == "draw_arrow":
            dur = cmd.get("duration", 3.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "arrow",
                "x1": cmd["x1"], "y1": cmd["y1"],
                "x2": cmd["x2"], "y2": cmd["y2"],
                "color": cmd.get("color", "#3B82F6"),
            }, dur, persist)

        elif ctype == "draw_line":
            dur = cmd.get("duration", 3.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "line",
                "x1": cmd["x1"], "y1": cmd["y1"],
                "x2": cmd["x2"], "y2": cmd["y2"],
                "color": cmd.get("color", "#3B82F6"),
                "width": cmd.get("width", 4),
                "progress": 0.0,
            }, dur, persist)

        elif ctype == "draw_polygon":
            dur = cmd.get("duration", 5.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "polygon",
                "points": cmd.get("points", []),
                "color": cmd.get("color", "#3B82F6"),
                "fill_color": cmd.get("fill_color"),
            }, dur, persist)

        elif ctype == "draw_path":
            dur = cmd.get("duration", 5.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "path",
                "path_data": cmd.get("path_data", ""),
                "x": cmd.get("x", 0),
                "y": cmd.get("y", 0),
                "color": cmd.get("color", self.primary),
                "width": cmd.get("width", 3),
            }, dur, persist)

        elif ctype == "show_text":
            dur = cmd.get("duration", 5.0)
            persist = cmd.get("persist")
            self._add_annotation({
                "type": "text",
                "x": cmd["x"], "y": cmd["y"],
                "text": cmd["text"],
                "color": cmd.get("color", self.text_color),
            }, dur, persist)

        elif ctype == "clear_all":
            self._annotations.clear()
            self._text_bubbles.clear()
            if self._state in (BuddyState.ANIMATING,
                               BuddyState.POINTING,
                               BuddyState.RETURNING):
                self._state = BuddyState.FOLLOWING

        elif ctype == "clear_annotations":
            self._annotations.clear()

        elif ctype == "set_state":
            target = cmd.get("state", "FOLLOWING")
            try:
                self._state = BuddyState[target]
            except KeyError:
                pass

        elif ctype == "set_colors":
            if "primary" in cmd:
                self.primary = cmd["primary"]
            if "secondary" in cmd:
                self.secondary = cmd["secondary"]
            if "text" in cmd:
                self.text_color = cmd["text"]

        elif ctype == "start_teaching":
            self._teaching_mode = True
            self._teaching_visible = True
            self._teaching_x = self._buddy_x
            self._teaching_y = self._buddy_y
            self._state = BuddyState.TEACHING

        elif ctype == "stop_teaching":
            self._teaching_mode = False
            self._teaching_visible = False
            self._state = BuddyState.FOLLOWING

        elif ctype == "teaching_move_to":
            if not self._teaching_mode:
                self._teaching_mode = True
                self._teaching_visible = True
            self._start_fly_to(
                cmd["x"], cmd["y"],
                cmd.get("label", ""),
                cmd.get("duration")
            )
            self._teaching_x = cmd["x"]
            self._teaching_y = cmd["y"]

        elif ctype == "teaching_click":
            if not self._teaching_mode:
                self._teaching_mode = True
                self._teaching_visible = True
            self._start_fly_to(
                cmd["x"], cmd["y"],
                cmd.get("label", ""),
                0.6
            )
            self._teaching_x = cmd["x"]
            self._teaching_y = cmd["y"]
            self._teaching_click_anim = 1.0

        elif ctype == "teaching_highlight":
            self._add_annotation({
                "type": "box",
                "x": cmd["x"], "y": cmd["y"],
                "w": cmd["w"], "h": cmd["h"],
                "color": "#FFD700",
                "label": cmd.get("label", ""),
            }, 4.0)
            if self._teaching_mode:
                cx = cmd["x"] + cmd["w"] / 2
                cy = cmd["y"] + cmd["h"] / 2
                self._start_fly_to(cx, cy, cmd.get("label", ""), 0.8)
                self._teaching_x = cx
                self._teaching_y = cy

        elif ctype == "teaching_type":
            if self._teaching_mode and self._teaching_visible:
                self._add_annotation({
                    "type": "text",
                    "x": self._teaching_x + 20,
                    "y": self._teaching_y - 30,
                    "text": cmd.get("text", ""),
                    "color": "#FFFFFF",
                }, 3.0)

    def _add_annotation(self, ann: dict, duration: float,
                        persist: Optional[float] = None):
        ann["created"] = time.time()
        try:
            ann["duration"] = float(duration)
        except (ValueError, TypeError):
            ann["duration"] = 3.0
        if persist is not None:
            try:
                ann["persist"] = float(persist)
            except (ValueError, TypeError):
                ann["persist"] = 5.0
        self._annotations.append(ann)

    def _start_fly_to(self, x: float, y: float, label: str = "",
                      duration: Optional[float] = None):
        sx, sy = self._buddy_x, self._buddy_y
        dx, dy = x - sx, y - sy
        dist = math.hypot(dx, dy)

        if duration is None:
            duration = min(max(dist / 800.0, 0.6), 1.4)

        mid_x = (sx + x) / 2.0
        mid_y = (sy + y) / 2.0
        arc_height = min(dist * 0.2, 80.0)
        cx = mid_x
        cy = mid_y - arc_height

        self._anim = AnimationState(
            start_x=sx, start_y=sy,
            target_x=x, target_y=y,
            control_x=cx, control_y=cy,
            start_time=time.time(),
            duration=duration,
            progress=0.0,
            label=label,
            label_visible=False,
            label_chars_printed=0
        )
        self._state = BuddyState.ANIMATING

    def _update_cursor_position(self):
        try:
            mx, my = pyautogui.position()
            self._cursor_x = float(mx)
            self._cursor_y = float(my)
        except Exception:
            pass

    def _update_animations(self):
        now = time.time()

        self._annotations = [
            a for a in self._annotations
            if (now - a["created"]) < a.get("persist", a.get("duration", 3.0))
        ]

        for ann in self._annotations:
            if ann.get("type") == "line" and ann.get("progress", 1.0) < 1.0:
                elapsed = now - ann["created"]
                dur = ann.get("duration", 3.0)
                ann["progress"] = min(elapsed / dur, 1.0)
                prog = ann["progress"]
                sx, sy = ann["x1"], ann["y1"]
                ex, ey = ann["x2"], ann["y2"]
                self._buddy_x = sx + (ex - sx) * prog
                self._buddy_y = sy + (ey - sy) * prog
                if prog >= 1.0:
                    self._buddy_x = ex
                    self._buddy_y = ey

        if self._teaching_click_anim > 0:
            self._teaching_click_anim = max(0, self._teaching_click_anim - 0.05)

        if self._state == BuddyState.ANIMATING:
            elapsed = now - self._anim.start_time
            t = max(0.0, min(elapsed / self._anim.duration, 1.0))
            smooth = t * t * (3.0 - 2.0 * t)
            self._anim.progress = smooth

            bx = self._bezier_point(self._anim, t)
            by = self._bezier_point_y(self._anim, t)
            self._buddy_x = bx
            self._buddy_y = by

            if t >= 1.0:
                self._buddy_x = self._anim.target_x
                self._buddy_y = self._anim.target_y
                if self._teaching_mode:
                    self._state = BuddyState.TEACHING
                    if self._anim.label:
                        self._add_annotation({
                            "type": "text",
                            "x": self._buddy_x + 20,
                            "y": self._buddy_y - 20,
                            "text": self._anim.label,
                            "color": "#FFD700",
                        }, 2.5)
                elif self._anim.label:
                    self._anim.label_visible = True
                    self._anim.label_chars_printed = 0
                    self._state = BuddyState.POINTING
                    self._anim.start_time = now
                else:
                    self._anim.return_start = (self._buddy_x, self._buddy_y)
                    self._anim.start_time = now
                    self._state = BuddyState.RETURNING

        elif self._state == BuddyState.POINTING:
            elapsed = now - self._anim.start_time
            chars_to_print = min(
                int(elapsed / 0.04),
                len(self._anim.label)
            )
            self._anim.label_chars_printed = chars_to_print

            if elapsed > 3.0 or chars_to_print >= len(self._anim.label):
                self._anim.return_start = (self._buddy_x, self._buddy_y)
                self._anim.start_time = now
                self._state = BuddyState.RETURNING

        elif self._state == BuddyState.RETURNING:
            elapsed = now - self._anim.start_time
            ret_dur = 0.5
            t = max(0.0, min(elapsed / ret_dur, 1.0))
            smooth = t * t * (3.0 - 2.0 * t)

            sx, sy = self._anim.return_start
            ex, ey = self._cursor_x, self._cursor_y
            self._buddy_x = sx + (ex - sx) * smooth
            self._buddy_y = sy + (ey - sy) * smooth

            if t >= 1.0:
                self._state = BuddyState.FOLLOWING
                self._anim.label_visible = False

        elif self._state == BuddyState.FOLLOWING:
            dx = self._cursor_x - self._buddy_x
            dy = self._cursor_y - self._buddy_y
            dist = math.hypot(dx, dy)
            if dist > 2.0:
                follow_speed = min(dist * 0.15, 20.0)
                angle = math.atan2(dy, dx)
                self._buddy_x += math.cos(angle) * follow_speed
                self._buddy_y += math.sin(angle) * follow_speed
            else:
                self._buddy_x = self._cursor_x
                self._buddy_y = self._cursor_y

        elif self._state == BuddyState.TEACHING:
            pass

        elif self._state == BuddyState.HIDDEN:
            pass

    def _bezier_point(self, anim: AnimationState, t: float) -> float:
        return ((1 - t) ** 2 * anim.start_x +
                2 * (1 - t) * t * anim.control_x +
                t ** 2 * anim.target_x)

    def _bezier_point_y(self, anim: AnimationState, t: float) -> float:
        return ((1 - t) ** 2 * anim.start_y +
                2 * (1 - t) * t * anim.control_y +
                t ** 2 * anim.target_y)

    def _render(self):
        self._canvas.delete("all")

        if self._state == BuddyState.HIDDEN:
            return

        for ann in self._annotations:
            self._render_annotation(ann)

        if self._teaching_mode and self._teaching_visible:
            self._draw_teaching_cursor()
        elif self._buddy_visible and self._state != BuddyState.HIDDEN:
            self._draw_buddy()

        if self._state == BuddyState.POINTING and self._anim.label_visible:
            self._draw_speech_bubble(
                self._anim.target_x,
                self._anim.target_y,
                self._anim.label,
                self._anim.label_chars_printed
            )

    def _render_annotation(self, ann: dict):
        try:
            atype = ann["type"]
            if atype == "box":
                x, y, w, h = ann["x"], ann["y"], ann["w"], ann["h"]
                color = ann["color"]
                self._canvas.create_rectangle(
                    x, y, x + w, y + h,
                    outline=color, width=4, dash=(8, 4)
                )
                if ann.get("label"):
                    lbl = ann["label"]
                    self._canvas.create_rectangle(
                        x + 4, y + 4, x + 8 + len(lbl) * 9, y + 24,
                        fill=color, outline=""
                    )
                    self._canvas.create_text(
                        x + 8 + len(lbl) * 4, y + 14,
                        text=lbl, font=("Segoe UI", 10, "bold"),
                        fill="#FFFFFF", anchor="center"
                    )

            elif atype == "arrow":
                x1, y1 = ann["x1"], ann["y1"]
                x2, y2 = ann["x2"], ann["y2"]
                color = ann["color"]
                self._canvas.create_line(
                    x1, y1, x2, y2,
                    fill=color, width=5, capstyle=tk.ROUND,
                    arrow=tk.LAST,
                    arrowshape=(16, 20, 8)
                )

            elif atype == "line":
                x1, y1 = ann["x1"], ann["y1"]
                x2, y2 = ann["x2"], ann["y2"]
                color = ann["color"]
                width = ann.get("width", 4)
                progress = ann.get("progress", 1.0)
                if progress < 1.0:
                    mx = x1 + (x2 - x1) * progress
                    my = y1 + (y2 - y1) * progress
                    self._canvas.create_line(
                        x1, y1, mx, my,
                        fill=color, width=width,
                        capstyle=tk.ROUND
                    )
                else:
                    self._canvas.create_line(
                        x1, y1, x2, y2,
                        fill=color, width=width,
                        capstyle=tk.ROUND
                    )

            elif atype == "polygon":
                pts = ann.get("points", [])
                color = ann["color"]
                fill = ann.get("fill_color")
                coords = [(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
                flat = []
                for p in coords:
                    flat.extend(p)
                kwargs = {"outline": color, "width": 3}
                if fill:
                    kwargs["fill"] = fill
                self._canvas.create_polygon(*flat, **kwargs)

            elif atype == "path":
                self._render_svg_path(
                    ann.get("path_data", ""),
                    ann.get("x", 0), ann.get("y", 0),
                    ann.get("color", self.primary),
                    ann.get("width", 3)
                )

            elif atype == "text":
                txt = ann["text"]
                font_size = 11
                char_w = 7
                line_h = 16
                lines = txt.split("\n")
                max_len = max(len(l) for l in lines) if lines else 0
                tw = max_len * char_w + 12
                th = len(lines) * line_h + 8
                self._canvas.create_rectangle(
                    ann["x"] - 4, ann["y"] - 4,
                    ann["x"] + tw, ann["y"] + th,
                    fill="#FFFFFF", outline="#CCCCCC", width=1
                )
                for i, ln in enumerate(lines):
                    self._canvas.create_text(
                        ann["x"] + 2, ann["y"] + 2 + i * line_h,
                        text=ln, font=("Segoe UI", font_size),
                        fill=ann["color"], anchor="nw"
                    )
        except Exception:
            pass

    def _render_svg_path(self, path_data: str, ox: float, oy: float,
                         color: str, width: float):
        """Parse a subset of SVG path commands and render them on the canvas.
        Supports: M, L, C, Q, Z (case sensitive: uppercase = absolute).
        """
        if not path_data:
            return

        cmd_re = re.compile(r'([MLCQZ])\s*([-\d.,\s]*)', re.IGNORECASE)
        pairs_re = re.compile(r'(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)')

        points: list[tuple[float, float]] = []
        curves: list[tuple] = []
        path_start: Optional[tuple[float, float]] = None
        current: tuple[float, float] = (0, 0)

        for match in cmd_re.finditer(path_data):
            cmd = match.group(1).upper()
            args_str = match.group(2).strip()
            args = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', args_str)]

            if cmd == 'M':
                for i in range(0, len(args), 2):
                    pt = (args[i] + ox, args[i + 1] + oy)
                    if path_start is None:
                        path_start = pt
                    current = pt
                    points = [pt]

            elif cmd == 'L':
                for i in range(0, len(args), 2):
                    pt = (args[i] + ox, args[i + 1] + oy)
                    if points:
                        self._canvas.create_line(
                            current[0], current[1],
                            pt[0], pt[1],
                            fill=color, width=width, smooth=False
                        )
                    current = pt
                    points.append(pt)

            elif cmd == 'C':
                for i in range(0, len(args), 6):
                    if i + 5 >= len(args):
                        break
                    c1 = (args[i] + ox, args[i + 1] + oy)
                    c2 = (args[i + 2] + ox, args[i + 3] + oy)
                    end = (args[i + 4] + ox, args[i + 5] + oy)
                    self._canvas.create_line(
                        current[0], current[1],
                        c1[0], c1[1],
                        c2[0], c2[1],
                        end[0], end[1],
                        fill=color, width=width, smooth=True,
                        splinesteps=32
                    )
                    current = end

            elif cmd == 'Q':
                for i in range(0, len(args), 4):
                    if i + 3 >= len(args):
                        break
                    c = (args[i] + ox, args[i + 1] + oy)
                    end = (args[i + 2] + ox, args[i + 3] + oy)
                    mid = ((current[0] + c[0]) / 2, (current[1] + c[1]) / 2)
                    self._canvas.create_line(
                        current[0], current[1], c[0], c[1],
                        end[0], end[1],
                        fill=color, width=width, smooth=True,
                        splinesteps=32
                    )
                    current = end

            elif cmd == 'Z':
                if path_start and current != path_start:
                    self._canvas.create_line(
                        current[0], current[1],
                        path_start[0], path_start[1],
                        fill=color, width=width
                    )
                    current = path_start

    def _draw_buddy(self, scale: float = 1.0):
        cx, cy = self._buddy_x, self._buddy_y
        r = 6 * scale
        self._canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="#FFFFFF", outline="#DDDDDD", width=1,
            tags="buddy"
        )

    def _draw_teaching_cursor(self):
        cx, cy = self._teaching_x, self._teaching_y
        r = 10
        self._canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="#FFD700", outline="#CC9900", width=1,
            tags="teach_dot"
        )

        if self._teaching_click_anim > 0:
            burst_r = 25 + 20 * self._teaching_click_anim
            self._canvas.create_oval(
                cx - burst_r, cy - burst_r,
                cx + burst_r, cy + burst_r,
                fill="", outline="#FFD700",
                width=int(4 * self._teaching_click_anim),
                tags="teach_click"
            )

    def _draw_speech_bubble(self, x: float, y: float,
                            text: str, chars_printed: int):
        displayed = text[:chars_printed]
        if not displayed:
            return

        padding = 12
        font_size = 11
        line_height = 18
        char_width = 7
        max_line_chars = 50

        lines = []
        for paragraph in displayed.split("\n"):
            words = paragraph.split(" ")
            current = ""
            for word in words:
                test = current + (" " if current else "") + word
                if len(test) > max_line_chars:
                    if current:
                        lines.append(current)
                    current = word
                else:
                    current = test
            if current:
                lines.append(current)

        n_lines = len(lines)
        bubble_w = max(200, min(400, max(len(l) for l in lines) * char_width + padding * 2))
        bubble_h = n_lines * line_height + padding * 2 + 10
        tail_h = 12

        bx = x - bubble_w // 2
        by = y - bubble_h - tail_h - 40

        bx = max(10, min(bx, self._screen_w - bubble_w - 10))
        by = max(10, min(by, self._screen_h - bubble_h - tail_h - 10))

        self._canvas.create_rectangle(
            bx, by, bx + bubble_w, by + bubble_h,
            fill="#FFFFFF", outline="#CCCCCC", width=1,
            tags="bubble_bg"
        )

        tail_x = x
        tail_y = by + bubble_h
        self._canvas.create_polygon(
            tail_x - 8, tail_y,
            tail_x + 8, tail_y,
            x, tail_y + tail_h,
            fill="#FFFFFF", outline="#CCCCCC", width=1,
            tags="bubble_tail"
        )

        for i, line in enumerate(lines):
            self._canvas.create_text(
                bx + padding, by + padding + i * line_height,
                text=line, font=("Segoe UI", font_size),
                fill="#000000", anchor="nw",
                tags="bubble_text"
            )

    def get_state(self) -> str:
        return self._state.name

    def get_buddy_position(self) -> tuple[float, float]:
        return (self._buddy_x, self._buddy_y)

    def get_teaching_position(self) -> tuple[float, float]:
        return (self._teaching_x, self._teaching_y)

    def is_animating(self) -> bool:
        return self._state in (BuddyState.ANIMATING,
                               BuddyState.POINTING,
                               BuddyState.RETURNING)

    def is_teaching(self) -> bool:
        return self._teaching_mode


_engine: Optional[OverlayEngine] = None

def get_engine() -> OverlayEngine:
    global _engine
    if _engine is None:
        _engine = OverlayEngine()
    return _engine


def ensure_running():
    eng = get_engine()
    eng.start()
    eng.show_buddy(True)
    return eng


def auto_start():
    """Auto-start the overlay engine (called at FRIDAY boot)."""
    eng = get_engine()
    eng.start()
    eng.show_buddy(True)
    return eng
