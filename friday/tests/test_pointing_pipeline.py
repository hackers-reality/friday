"""Test the full pointing pipeline: capture, parse, annotate."""
import sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from friday.overlay_engine import get_engine
eng = get_engine()
eng.start()
eng.show_buddy(True)
time.sleep(0.5)

from friday.pointing_agent import (
    parse_point_tags, map_to_screen_coords, capture_all_monitors
)

# Test 1: Multi-monitor capture
monitors = capture_all_monitors()
print(f"[OK] {len(monitors)} monitor(s) captured")
for m in monitors:
    print(f"  {m['label']}: {m['w']}x{m['h']} (offset: {m['offset_x']},{m['offset_y']})")

# Test 2: Parse POINT tags with screen numbers
mock = (
    "Found these elements: [POINT:100,200:Search bar:screen1] "
    "[POINT:300,150:Submit button:screen1] "
    "[POINT:640,400:Logo]"
)
targets, cleaned = parse_point_tags(mock)
print(f"[OK] Parsed {len(targets)} targets:")
for t in targets:
    ax, ay = map_to_screen_coords(t.x, t.y, 1280, 720, t.screen_number)
    print(f"  ({t.x},{t.y}) -> ({ax:.0f},{ay:.0f}) screen={t.screen_number}: {t.label}")

# Test 3: Annotate everything on screen
for t in targets:
    ax, ay = map_to_screen_coords(t.x, t.y, 1280, 720, t.screen_number)
    eng.fly_to(ax, ay, t.label)
    eng.show_text(ax + 40, ay - 15, t.label)
    time.sleep(1)

time.sleep(3)
eng.clear_all()
eng.stop()
print("[DONE] Pipeline test complete")
