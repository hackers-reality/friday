"""
Quick test script for Friday core features.
Run: python test_friday.py
"""
import sys
import os
sys.path.insert(0, '.')

print("=" * 60)
print("FRIDAY CORE FEATURES TEST")
print("=" * 60)

results = {"pass": 0, "fail": 0}

def test(name, func):
    """Run a test."""
    try:
        result = func()
        # Clean for Windows console
        import re
        clean = re.sub(r'[^\x00-\x7F]+', '', str(result))[:100]
        print(f"  [OK] {name}: {clean}")
        results["pass"] += 1
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        results["fail"] += 1
        return False

# ─── Test 1: Screen Watcher ─────────────────────────────
print("\n### 1. SCREEN WATCHER ###")

def test_screen_watcher():
    from screen_watcher import get_active_window_info
    info = get_active_window_info()
    return f"Active: {info.get('title', 'Unknown')[:30]}"

test("Active Window Detection", test_screen_watcher)

# ─── Test 2: Browser History ───────────────────────────────
print("\n### 2. BROWSER HISTORY ###")

def test_browser_status():
    from browser_history_tools import get_browser_status
    return get_browser_status()

test("Browser Status Check", test_browser_status)

# ─── Test 3: File Generator ────────────────────────────────
print("\n### 3. FILE GENERATOR ###")

def test_file_gen():
    from file_generator import get_generator_status
    return get_generator_status()

test("Generator Status", test_file_gen)

def test_file_create():
    from file_generator import generate_file
    result = generate_file("test_output/hello.py", "python", "Test script")
    return result

test("File Creation", test_file_create)

# ─── Test 4: Goal Memory ──────────────────────────────────
print("\n### 4. GOAL MEMORY ###")

def test_goal_profile():
    from goal_memory import get_profile_summary
    return get_profile_summary()

test("Profile Summary", test_goal_profile)

def test_goal_add():
    from goal_memory import add_goal
    return add_goal(
        title="Test Course",
        goal_type="course",
        description="Test goal for Friday",
        start_date="2026-05-06",
        end_date="2026-05-31",
        url="https://test.com",
        priority="high",
        verification_method="browser_history",
        verification_data="test",
    )

test("Add Goal", test_goal_add)

# ─── Test 5: Startup Integration ─────────────────────────
print("\n### 5. STARTUP INTEGRATION ###")

def test_startup():
    from startup_integration import check_startup_status
    return check_startup_status()

test("Startup Status", test_startup)

# ─── Test 6: Friday Tools Integration ──────────────────
print("\n### 6. FRIDAY TOOLS (friday_tools.py) ###")

def test_tools_import():
    from friday_tools import see_screen, search_browser_history
    return "Tools imported successfully"

test("Tools Import", test_tools_import)

# ─── Summary ───────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {results['pass']} passed, {results['fail']} failed")
print("=" * 60)

if results["fail"] > 0:
    print("\n[WARN]  Some tests failed. Check the errors above.")
else:
    print("\n[OK] All core features working!")

# Cleanup
import shutil
if os.path.exists("test_output"):
    shutil.rmtree("test_output")
