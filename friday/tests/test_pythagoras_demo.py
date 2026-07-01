"""Pythagoras Teaching Demo — overlay annotation verification.
Demonstrates FRIDAY's teaching flow: triangle → squares → formula, all on screen.
Uses known coordinates (simulates what NIM would detect from a real image).
"""
import sys, os, time
sys.path.insert(0, r"E:\open-interpreter")
os.chdir(r"E:\open-interpreter")
from dotenv import load_dotenv; load_dotenv()
from friday.overlay_engine import ensure_running, get_engine

ensure_running()
eng = get_engine()
time.sleep(0.5)

# Triangle vertices (would come from NIM analyzing a user's image)
A = (300.0, 500.0)  # right angle vertex
B = (700.0, 500.0)  # base end (base=400)
C = (300.0, 200.0)  # top vertex (height=300)
base_len = 400; height_len = 300
hypo_len = (base_len**2 + height_len**2)**0.5  # =500

# Step 1: Trace triangle
eng.draw_line(A[0],A[1], B[0],B[1], "#F59E0B", 4, 3600); time.sleep(0.3)
eng.draw_line(A[0],A[1], C[0],C[1], "#F59E0B", 4, 3600); time.sleep(0.3)
eng.draw_line(C[0],C[1], B[0],B[1], "#F59E0B", 4, 3600); time.sleep(0.5)

# Label base/height/hypo
eng.show_text(A[0]+base_len//2, A[1]+15, f"a = {base_len}px", duration=3600)
eng.show_text(A[0]-70, A[1]-height_len//2, f"b = {height_len}px", duration=3600)
eng.show_text(B[0]-hypo_len//2, B[1]-height_len//2-20, f"c = {hypo_len:.0f}px", duration=3600)

# Step 2: Draw squares on each side
sq_a = [(A[0],A[1]),(B[0],B[1]),(B[0],B[1]+base_len),(A[0],A[1]+base_len)]
eng.draw_polygon(sq_a, "#10B981", "#10B98130", 3600)
eng.show_text(A[0]+base_len//2, A[1]+base_len//2, f"a² = {base_len*base_len:,}", 3600)
sq_b = [(C[0],C[1]),(A[0],A[1]),(A[0]-height_len,A[1]),(C[0]-height_len,C[1])]
eng.draw_polygon(sq_b, "#8B5CF6", "#8B5CF630", 3600)
eng.show_text(A[0]-height_len//2, A[1]-height_len//2, f"b² = {height_len*height_len:,}", 3600)
dx = B[0]-C[0]; dy = B[1]-C[1]
sq_c = [(C[0],C[1]),(B[0],B[1]),(B[0]+dy,B[1]-dx),(C[0]+dy,C[1]-dx)]
eng.draw_polygon(sq_c, "#EF4444", "#EF444430", 3600)
eng.show_text(C[0]+dy//2+dx//2, C[1]-dx//2+dy//2, f"c² = {hypo_len*hypo_len:.0f}", 3600)

# Step 3: Formula
fx = A[0]-40; fy = min(C[1], A[1]-height_len, B[1]+base_len)+60
eng.show_text(fx, fy, "Pythagorean Theorem:", 3600)
eng.show_text(fx, fy+25, f"a² + b² = c²", 3600)
eng.show_text(fx, fy+50, f"{base_len}² + {height_len}² = {hypo_len:.0f}²", 3600)
eng.show_text(fx, fy+75, f"{base_len*base_len:,} + {height_len*height_len:,} = {hypo_len*hypo_len:.0f}", 3600)
eng.show_text(fx, fy+100, f"CHECK: {base_len*base_len + height_len*height_len:.0f} = {hypo_len*hypo_len:.0f} ✓", 3600)

print("LOOK AT YOUR SCREEN!")
print("Orange triangle traced, green/purple/red squares on each side, formula below.")
print("(This runs for 120s. Close overlay window to stop early.)")
time.sleep(120)
eng.clear_all()
