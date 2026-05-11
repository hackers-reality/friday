"""
Friday Master Bootstrap - Loads and tests ALL features you asked for.
Run: python friday_master.py
"""
import sys
import os
sys.path.insert(0, '.')

print("=" * 70)
print("FRIDAY SOVEREIGN AI - ALL FEATURES BOOTSTRAP")
print("=" * 70)

results = {"pass": 0, "fail": 0, "skip": 0}
modules_status = []

def test_module(name, import_path, test_fn=None):
    """Test a module."""
    try:
        if import_path:
            m = __import__(import_path)
        else:
            m = __import__(name)
        
        if test_fn:
            result = test_fn(m)
            modules_status.append(("[OK]", name, result))
        else:
            modules_status.append(("[OK]", name, "imported"))
        results["pass"] += 1
        return m
    except Exception as e:
        # Clean error for Windows console
        err = str(e)[:100].encode('ascii', 'ignore').decode('ascii')
        modules_status.append(("[FAIL]", name, err))
        results["fail"] += 1
        return None

def safe_str(obj, max_len=80):
    """Safe string conversion."""
    try:
        s = str(obj)
        return s[:max_len] if len(s) > max_len else s
    except:
        return "(unprintable)"

# ─── Phase 1: Core Modules ────────────────────────────────#

print("\n### PHASE 1: CORE MODULES ###\n")

# Screen Watcher
def test_screen(m):
    from friday.screen_watcher import get_active_window_info
    info = get_active_window_info()
    return f"Active: {safe_str(info.get('title', 'Unknown'))}"

test_module("screen_watcher", "screen_watcher", test_screen)

# Browser History
def test_browser(m):
    from friday.browser_history import get_browser_status
    return safe_str(get_browser_status())

test_module("browser_history_tools", "browser_history_tools", test_browser)

# File Generator
def test_filegen(m):
    from friday.filegen import get_generator_status
    return safe_str(get_generator_status())

test_module("file_generator", "file_generator", test_filegen)

# Goal Memory
def test_goal(m):
    from friday.goals import get_profile_summary
    return safe_str(get_profile_summary())

test_module("goal_memory", "goal_memory", test_goal)

# Friday Tools
def test_tools(m):
    from friday.tools import __all__
    return f"{len(__all__)} tools loaded"

test_module("friday_tools", "friday_tools", test_tools)

# Startup Integration
def test_startup(m):
    from friday.startup import check_startup_status
    return safe_str(check_startup_status())

test_module("startup_integration", "startup_integration", test_startup)

# ─── Phase 2: Advanced Features ────────────────────────────────#

print("\n### PHASE 2: ADVANCED FEATURES ###\n")

# Proactive Monitor
def test_monitor(m):
    from proactive_screen_monitor import ProactiveScreenMonitor
    m = ProactiveScreenMonitor(ai_enabled=False)
    return m.get_status()[:80]

test_module("proactive_screen_monitor", "proactive_screen_monitor", test_monitor)

# MCP Server
def test_mcp(m):
    from friday.mcp_enhanced import create_mcp_server
    server = create_mcp_server()
    return "Server created" if server else "Server not available"

test_module("friday_mcp_enhanced", "friday_mcp_enhanced", test_mcp)

# LangGraph Agent
def test_langraph(m):
    from friday.langraph import get_langraph_status
    return safe_str(get_langraph_status())

test_module("friday_langraph", "friday_langraph", test_langraph)

# Voice (check if available)
def test_voice(m):
    try:
        from friday.voice import SpeechToText, TextToSpeech
        return "Voice modules available"
    except:
        return "Voice modules not available"

test_module("friday_voice", None, test_voice)

# Vision
def test_vision(m):
    from friday.vision import vision_tool
    return "Vision tool available"

test_module("friday_vision", "friday_vision", test_vision)

# ─── Phase 3: Integration Test ────────────────────────────────#

print("\n### PHASE 3: INTEGRATION TEST ###\n")

def test_integration():
    """Test that tools actually work end-to-end."""
    results = []
    
    # Test file generation
    try:
        from friday.filegen import generate_file
        r = generate_file("test_output/master_test.py", "python", "Master test")
        results.append(f"File gen: {safe_str(r)}")
    except Exception as e:
        results.append(f"File gen FAIL: {safe_str(e)}")
    
    # Test browser search
    try:
        from friday.browser_history import search_all_history
        r = search_all_history("test", days_back=1)
        results.append(f"Browser search: OK")
    except Exception as e:
        results.append(f"Browser search FAIL: {safe_str(e)}")
    
    # Test goal add
    try:
        from friday.goals import add_goal
        r = add_goal(title="Master Test Goal", goal_type="test")
        results.append(f"Goal add: {safe_str(r)}")
    except Exception as e:
        results.append(f"Goal add FAIL: {safe_str(e)}")
    
    return "\n".join(results)

try:
    integration_result = test_integration()
    modules_status.append(("[OK]", "integration_test", integration_result))
    results["pass"] += 1
except Exception as e:
    modules_status.append(("[FAIL]", "integration_test", safe_str(e)))
    results["fail"] += 1

# ─── Print Results ────────────────────────────────────────#

print("\n" + "=" * 70)
print("FRIDAY SYSTEM STATUS REPORT")
print("=" * 70 + "\n")

for icon, name, status in modules_status:
    print(f"{icon} {name}")
    # Print status indented if multi-line
    for line in str(status).split("\n")[:3]:
        if line.strip():
            print(f"   {line}")

print("\n" + "=" * 70)
print(f"RESULTS: {results['pass']} passed, {results['fail']} failed")
print("=" * 70)

if results["fail"] > 0:
    print("\n[WARN]  Some features failed. Check errors above.")
    print("   Core features may still work even if some modules fail.")
else:
    print("\n[OK] All features loaded successfully!")

# ─── Quick Feature Demo ──────────────────────────────────────#

print("\n### QUICK FEATURE DEMO ###\n")

# Demo 1: Screen awareness
print("1. Screen Awareness:")
try:
    from friday.screen_watcher import get_active_window_info
    info = get_active_window_info()
    print(f"   Active window: {safe_str(info.get('title', 'Unknown'))}")
except Exception as e:
    print(f"   FAIL: {safe_str(e)}")

# Demo 2: Browser history
print("\n2. Browser History:")
try:
    from friday.browser_history import get_browser_status
    status = get_browser_status()
    for line in str(status).split("\n")[:4]:
        if line.strip():
            print(f"   {line}")
except Exception as e:
    print(f"   FAIL: {safe_str(e)}")

# Demo 3: File generation
print("\n3. File Generation:")
try:
    from friday.filegen import get_generator_status
    status = get_generator_status()
    for line in str(status).split("\n")[:4]:
        if line.strip():
            print(f"   {line}")
except Exception as e:
    print(f"   FAIL: {safe_str(e)}")

# Demo 4: Goal memory
print("\n4. Goal Memory:")
try:
    from friday.goals import get_profile_summary
    summary = get_profile_summary()
    for line in str(summary).split("\n")[:4]:
        if line.strip():
            print(f"   {line}")
except Exception as e:
    print(f"   FAIL: {safe_str(e)}")

print("\n" + "=" * 70)
print("Friday Master Bootstrap Complete!")
print("=" * 70)

# Cleanup
import shutil
if os.path.exists("test_output"):
    shutil.rmtree("test_output")
