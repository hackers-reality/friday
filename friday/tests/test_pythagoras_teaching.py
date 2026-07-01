"""Pythagoras Theorem Teaching Demo — Full pipeline test.

Simulates FRIDAY's teaching flow:
  1. Draw a triangle on screen (or user shows one)
  2. analyze_screen detects triangle vertices
  3. FRIDAY traces the triangle with draw_line at EXACT coordinates
  4. FRIDAY draws squares on each side using draw_polygon
  5. FRIDAY labels a², b², c² + formula
  6. FRIDAY narrates throughout
"""

import sys, os, time
sys.path.insert(0, r"E:\open-interpreter")
os.chdir(r"E:\open-interpreter")
os.environ["FRIDAY_MODE"] = "cli"
from dotenv import load_dotenv
load_dotenv()

from friday.overlay_engine import ensure_running, get_engine
from friday.pointing_agent import analyze_screen, parse_point_tags

# ── 1. Start overlay ──
ensure_running()
eng = get_engine()
time.sleep(0.5)

# ── 2. Draw the reference triangle on screen ──
# Right triangle: base=(300,500)→(700,500), height=(300,500)→(300,200), hypo=(300,200)→(700,500)
base_x1, base_y1 = 300, 500
base_x2, base_y2 = 700, 500  # base = 400px
height_x1, height_y1 = 300, 500
height_x2, height_y2 = 300, 200  # height = 300px
hypo_x1, hypo_y1 = 300, 200
hypo_x2, hypo_y2 = 700, 500  # hypotenuse

# Draw the triangle in blue
eng.draw_line(base_x1, base_y1, base_x2, base_y2, "#3B82F6", 3, duration=3600)
time.sleep(0.3)
eng.draw_line(height_x1, height_y1, height_x2, height_y2, "#3B82F6", 3, duration=3600)
time.sleep(0.3)
eng.draw_line(hypo_x1, hypo_y1, hypo_x2, hypo_y2, "#3B82F6", 3, duration=3600)
time.sleep(0.5)

# Label the vertices
eng.show_text(base_x1 - 20, base_y1 + 5, "A", duration=3600)  # A at (300,500) - right angle
eng.show_text(base_x2 + 5, base_y2 + 5, "B", duration=3600)    # B at (700,500)
eng.show_text(hypo_x1 - 20, hypo_y1 - 15, "C", duration=3600)  # C at (300,200)

print("[OVERLAY] Reference triangle drawn on screen at A(300,500), B(700,500), C(300,200)")
print("[OVERLAY] Take a screenshot for NIM to detect...")

# ── 3. Wait a moment then analyze screen ──
# The triangle is drawn on the overlay, so analyze_screen should see it
time.sleep(2)

print("\n[NIM] Analyzing screen to find triangle vertices...")
result = analyze_screen(
    "Find the blue triangle drawn on screen. Return the exact [POINT:x,y:label] "
    "coordinates of its three vertices: the right-angle vertex A, the base end B, "
    "and the top vertex C. Also measure the base length, height, and hypotenuse."
)
targets, cleaned = parse_point_tags(result)
print(f"[NIM] Found {len(targets)} point targets:")
for t in targets:
    print(f"  [POINT:{t.x:.0f},{t.y:.0f}] {t.label}")

# ── 4. If NIM found the vertices, trace over the triangle ──
a_targets = [t for t in targets if "a" in t.label.lower() or "right" in t.label.lower() or "vertex" in t.label.lower()]
b_targets = [t for t in targets if "b" in t.label.lower() or "base" in t.label.lower()]
c_targets = [t for t in targets if "c" in t.label.lower() or "top" in t.label.lower() or "height" in t.label.lower()]

if a_targets and b_targets and c_targets:
    A = (a_targets[0].x, a_targets[0].y)
    B = (b_targets[0].x, b_targets[0].y)
    C = (c_targets[0].x, c_targets[0].y)
    print(f"\n[DETECTED] A{A}, B{B}, C{C}")
else:
    # Fallback to known coordinates
    print(f"\n[DETECT] Using reference coordinates (NIM didn't return 3 vertices)")
    A = (float(base_x1), float(base_y1))
    B = (float(base_x2), float(base_y2))
    C = (float(height_x2), float(height_y2))

# ── 5. FRIDAY traces the triangle with bold lines ──
import math
base_len = abs(B[0] - A[0])
height_len = abs(A[1] - C[1])
hypo_len = math.sqrt(base_len**2 + height_len**2)

print("\n[FRIDAY] 'Let me trace this triangle and show you how Pythagoras works!'")
time.sleep(0.5)

# Trace over triangle in golden color (teaching overlay)
eng.clear_all()  # Remove original blue triangle
time.sleep(0.3)

# Redraw triangle in bold orange/teaching color
eng.draw_line(A[0], A[1], B[0], B[1], "#F59E0B", 4, duration=3600)  # Base
time.sleep(0.3)
eng.draw_line(A[0], A[1], C[0], C[1], "#F59E0B", 4, duration=3600)  # Height
time.sleep(0.3)
eng.draw_line(C[0], C[1], B[0], B[1], "#F59E0B", 4, duration=3600)  # Hypotenuse
time.sleep(0.5)

# Label sides
eng.show_text(A[0] + base_len//2, A[1] + 15, f"a = {base_len:.0f}px", duration=3600)
eng.show_text(A[0] - 60, A[1] - height_len//2, f"b = {height_len:.0f}px", duration=3600)
eng.show_text(B[0] - hypo_len//2, B[1] - height_len//2 - 20, f"c = {hypo_len:.0f}px", duration=3600)

# ── 6. Draw squares on each side ──
print("\n[FRIDAY] 'Now watch — I'll draw squares on each side to prove the theorem!'")
time.sleep(0.5)

# Square on base (side a) - going downward from base line
square_a = [
    (A[0], A[1]),
    (B[0], B[1]),
    (B[0], B[1] + base_len),
    (A[0], A[1] + base_len),
]
eng.draw_polygon(square_a, color="#10B981", fill_color="#10B98130", duration=3600)
eng.show_text(A[0] + base_len//2, A[1] + base_len//2, f"a² = {base_len*base_len:,}", duration=3600)
time.sleep(0.3)

# Square on height (side b) - going left from height line
square_b = [
    (C[0], C[1]),
    (A[0], A[1]),
    (A[0] - height_len, A[1]),
    (C[0] - height_len, C[1]),
]
eng.draw_polygon(square_b, color="#8B5CF6", fill_color="#8B5CF630", duration=3600)
eng.show_text(A[0] - height_len//2, A[1] - height_len//2, f"b² = {height_len*height_len:,}", duration=3600)
time.sleep(0.3)

# Square on hypotenuse (side c) - tricky but approximate
# Direction vector from C to B
dx = B[0] - C[0]
dy = B[1] - C[1]
# Perpendicular (rotate 90 degrees clockwise)
px = dy
py = -dx
# Normalize to length c (already length = hypo_len, so px, py are the perpendicular of correct length)
square_c = [
    (C[0], C[1]),
    (B[0], B[1]),
    (B[0] + px, B[1] + py),
    (C[0] + px, C[1] + py),
]
eng.draw_polygon(square_c, color="#EF4444", fill_color="#EF444430", duration=3600)
label_cx = C[0] + px//2 + dx//2
label_cy = C[1] + py//2 + dy//2
eng.show_text(label_cx, label_cy, f"c² = {hypo_len*hypo_len:.0f}", duration=3600)

# ── 7. Show the formula ──
time.sleep(0.5)
formula_x = A[0] - 40
formula_y = min(C[1], A[1] - height_len, B[1] + base_len) + 60
eng.show_text(formula_x, formula_y, "Pythagorean Theorem:", duration=3600)
eng.show_text(formula_x, formula_y + 25, f"  a² + b² = c²", duration=3600)
eng.show_text(formula_x, formula_y + 50, f"  {base_len}² + {height_len}² = {hypo_len:.0f}²", duration=3600)
eng.show_text(formula_x, formula_y + 75, f"  {base_len*base_len:,} + {height_len*height_len:,} = {hypo_len*hypo_len:.0f}", duration=3600)
eng.show_text(formula_x, formula_y + 100, f"  ✓ {base_len*base_len + height_len*height_len:.0f} = {hypo_len*hypo_len:.0f}", duration=3600)

print("\n[OK] Pythagoras demonstration complete!")
print("LOOK at your screen — triangle traced, squares drawn on each side, formula shown!")
print("(Demo runs for 120s then clears. Close overlay window to stop early.)")
time.sleep(120)

eng.clear_all()
print("[OK] Demo cleared.")
