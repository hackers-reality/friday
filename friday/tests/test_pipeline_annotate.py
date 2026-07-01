"""End-to-end pipeline test: NIM vision → overlay annotations on screen.
Run this, then LOOK at your screen to see the annotations appear."""
import sys, os, time
sys.path.insert(0, r"E:\open-interpreter")
os.chdir(r"E:\open-interpreter")
os.environ["FRIDAY_MODE"] = "cli"
from dotenv import load_dotenv
load_dotenv()

from friday.overlay_engine import ensure_running, get_engine
from friday.pointing_agent import analyze_screen, parse_point_tags

# 1. Start overlay
ensure_running()
engine = get_engine()
time.sleep(1)

# 2. NIM vision tags what's on screen
print("[NIM] Analyzing screen...")
result = analyze_screen()
targets, _ = parse_point_tags(result)
print(f"[NIM] Found {len(targets)} elements")

# 3. FRIDAY annotates each one on screen
for t in targets[:8]:  # first 8
    label = t.label or "element"
    engine.fly_to(t.x, t.y, label)
    engine.show_text(t.x + 50, t.y - 10, label)
    time.sleep(0.4)

print(f"\n[OK] Annotated {min(len(targets), 8)} elements on screen.")
print("LOOK at your screen — you should see the white dot buddy pointing and labels!")
print("\n(The demo runs for 60s then cleans up. Close the overlay window to stop early.)")
time.sleep(60)

engine.clear_all()
print("[OK] Overlay cleared.")
