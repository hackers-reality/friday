"""Diagnostic v2: test the live engine module-level code."""
import sys, traceback

def test(label, do_import):
    try:
        do_import()
        print(f"[OK] {label}")
        return True
    except Exception as e:
        print(f"[FAIL] {label}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print()

# Test the env vars first
import os
print(f"GOOGLE_API_KEY set: {bool(os.getenv('GOOGLE_API_KEY'))}")
print(f"GROQ_API_KEY set: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"PICOVOICE_ACCESS_KEY set: {bool(os.getenv('PICOVOICE_ACCESS_KEY'))}")
print(f"FRIDAY_WEBHOOK_SECRET set: {bool(os.getenv('FRIDAY_WEBHOOK_SECRET'))}")
print()

# Test all live.py module-level imports one by one
from friday.tools import (
    stark_doctor, get_time, web_search
)
print("[OK] friday.tools partial import")

test("friday.tool_registry", lambda: __import__("friday.tool_registry"))
test("friday.authority", lambda: __import__("friday.authority"))
test("friday.snapshots", lambda: __import__("friday.snapshots"))
test("friday.autonomy", lambda: __import__("friday.autonomy"))
test("friday.dashboard_api", lambda: __import__("friday.dashboard_api"))
test("friday.capabilities", lambda: __import__("friday.capabilities"))
test("friday.ironman", lambda: __import__("friday.ironman"))
test("friday.memory_tree", lambda: __import__("friday.memory_tree"))
test("friday.model_router", lambda: __import__("friday.model_router"))
test("friday.extension_registry", lambda: __import__("friday.extension_registry"))
test("friday.diagnostics", lambda: __import__("friday.diagnostics"))
test("friday.cv_engine", lambda: __import__("friday.cv_engine"))

# Try the full live engine import
test("friday.live (full module import)", lambda: __import__("friday.live"))
test("friday.live.friday_live_engine", lambda: __import__("friday.live"))

print(f"\nAll live.py direct imports done. Module cached: {'friday.live' in sys.modules}")
if 'friday.live' in sys.modules:
    live_mod = sys.modules['friday.live']
    print(f"  Has friday_live_engine: {hasattr(live_mod, 'friday_live_engine')}")
