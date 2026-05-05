"""
Friday Test Suite - Verify all components work together.
Run: python test_friday.py
"""
from __future__ import annotations

import sys
import os

def test_imports():
    """Test all imports."""
    print("=" * 60)
    print("TESTING FRIDAY COMPONENTS")
    print("=" * 60)

    results = []

    # Test core components
    tests = [
        ("LangGraph", "langgraph"),
        ("MCP", "mcp"),
        ("Screen Watcher (pywinctl)", "pywinctl"),
        ("Browser History", "browser_history"),
        ("Psutil", "psutil"),
    ]

    for name, module in tests:
        try:
            __import__(module)
            results.append((name, "PASS", "OK"))
        except ImportError as e:
            results.append((name, "FAIL", str(e)))

    # Test Friday modules
    friday_modules = [
        ("Friday Graph", "friday_graph"),
        ("Friday MCP", "friday_mcp"),
        ("Friday Live", "friday_live"),
        ("Screen Watcher", "screen_watcher"),
        ("Proactive Commentary", "proactive_commentary"),
        ("Browser History Tools", "browser_history_tools"),
        ("Goal Memory", "goal_memory"),
        ("File Generator", "file_generator"),
        ("Startup Integration", "startup_integration"),
        ("Desktop App", "desktop_app"),
        ("Multi-Agent", "multi_agent"),
        ("Voice Wake", "voice_wake"),
        ("Message Channels", "message_channels"),
        ("Coding Agent", "coding_agent"),
        ("Self Improvement", "self_improvement"),
        ("Master Entry", "friday_master"),
    ]

    for name, module in friday_modules:
        try:
            __import__(module)
            results.append((name, "PASS", "OK"))
        except Exception as e:
            results.append((name, "FAIL", str(e)[:80]))

    # Print results
    print("\n" + "-" * 60)
    print(f"{'Component':<30} {'Status':<8} {'Details'}")
    print("-" * 60)

    passed = 0
    failed = 0

    for name, status, details in results:
        icon = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{name:<30} {icon:<8} {details}")
        if status == "PASS":
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"\nResults: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


def test_tools():
    """Test Friday tools."""
    print("\n\n" + "=" * 60)
    print("TESTING FRIDAY TOOLS")
    print("=" * 60)

    # Test browser history
    print("\n--- Browser History ---")
    try:
        from browser_history_tools import browser_history_tool
        result = browser_history_tool("status")
        print(result[:200])
        print("\n[PASS] Browser history tool works")
    except Exception as e:
        print(f"[FAIL] {e}")

    # Test goal memory
    print("\n--- Goal Memory ---")
    try:
        from goal_memory import goal_tool
        result = goal_tool("status")
        print(result[:200])
        print("\n[PASS] Goal memory tool works")
    except Exception as e:
        print(f"[FAIL] {e}")

    # Test file generator
    print("\n--- File Generator ---")
    try:
        from file_generator import file_generator_tool
        result = file_generator_tool("list")
        print(result[:200])
        print("\n[PASS] File generator tool works")
    except Exception as e:
        print(f"[FAIL] {e}")

    # Test message channels
    print("\n--- Message Channels ---")
    try:
        from message_channels import message_channel_tool
        result = message_channel_tool("status")
        print(result[:200])
        print("\n[PASS] Message channels tool works")
    except Exception as e:
        print(f"[FAIL] {e}")

    # Test self improvement
    print("\n--- Self Improvement ---")
    try:
        from self_improvement import self_improvement_tool
        result = self_improvement_tool("status")
        print(result[:200])
        print("\n[PASS] Self improvement tool works")
    except Exception as e:
        print(f"[FAIL] {e}")

    print("\n" + "=" * 60)


def test_memory():
    """Test memory system."""
    print("\n\n" + "=" * 60)
    print("TESTING MEMORY SYSTEM")
    print("=" * 60)

    memory_dir = "friday_memory"
    if not os.path.exists(memory_dir):
        print(f"\n[INFO] Creating {memory_dir} directory...")
        os.makedirs(memory_dir, exist_ok=True)

    files = [
        "goals.json",
        "user_profile.json",
        "sovereign_state.json",
        "metrics.json",
    ]

    for f in files:
        path = os.path.join(memory_dir, f)
        if os.path.exists(path):
            print(f"[OK] {f} exists")
        else:
            print(f"[INFO] {f} not found (will be created on first use)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("Starting Friday test suite...\n")

    all_passed = test_imports()
    test_tools()
    test_memory()

    print("\n\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)

    if all_passed:
        print("\n[SUCCESS] All core components imported successfully!")
        print("Friday is ready to use.")
    else:
        print("\n[WARNING] Some components failed to import.")
        print("Check the errors above and install missing dependencies.")

    print("\nNext steps:")
    print("  1. Set up API keys (GEMINI_API_KEY in .env)")
    print("  2. Run: python friday_master.py status")
    print("  3. Start Friday: python friday_master.py multi-agent")
