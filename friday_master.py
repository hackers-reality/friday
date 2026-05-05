"""
Friday Master Integration - Main Entry Point
Integrates all Friday subsystems into a unified AI agent.
"""
from __future__ import annotations

import os
import sys
import argparse
import threading
from typing import Optional

# ─── Version ────────────────────────────────────#

FRIDAY_VERSION = "1.0.0"
FRIDAY_CODENAME = "Sovereign"


# ─── Banner ────────────────────────────────────#

def print_banner():
    """Print Friday banner."""
    print(f"""
===============================================================
|                                                             |
|     FFFFF  RRRR   III  DDDD   AAA   Y   Y                  |
|     F      R   R   I   D   D  A   A   Y Y                    |
|     FFF    RRRR    I   D   D  AAAAA    Y                     |
|     F      R   R   I   D   D  A   A    Y                     |
|     F      R    R III  DDDD   A   A    Y                     |
|                                                             |
|         Ultimate AI Agent v{FRIDAY_VERSION} "{FRIDAY_CODENAME}"       |
|                                                             |
===============================================================
""")


# ─── Component Status ────────────────────────────────────#

def check_components() -> dict:
    """Check which components are available."""
    status = {}

    # LangGraph
    try:
        import langgraph
        status["langgraph"] = True
    except ImportError:
        status["langgraph"] = False

    # MCP
    try:
        import mcp
        status["mcp"] = True
    except ImportError:
        status["mcp"] = False

    # Screen watcher
    try:
        import pywinctl
        status["screen_watcher"] = True
    except ImportError:
        status["screen_watcher"] = False

    # Browser history
    try:
        import browser_history
        status["browser_history"] = True
    except ImportError:
        status["browser_history"] = False

    # Voice wake
    try:
        import pvporcupine
        status["voice_wake"] = True
    except ImportError:
        status["voice_wake"] = False

    # Google Calendar
    try:
        from google.oauth2.credentials import Credentials
        status["google_calendar"] = True
    except ImportError:
        status["google_calendar"] = False

    return status


def print_status(status: dict):
    """Print component status."""
    print("\n### COMPONENT STATUS\n")
    for name, available in status.items():
        icon = "[OK]" if available else "[MISSING]"
        print(f"  {icon} {name.replace('_', ' ').title()}")
    print()


# ─── Main Entry Points ────────────────────────────────────#

def run_mcp_server():
    """Run the MCP server."""
    print("🚀 Starting Friday MCP Server...")
    try:
        from friday_mcp import main as mcp_main
        mcp_main()
    except ImportError as e:
        print(f"❌ Failed to import MCP server: {e}")
        sys.exit(1)


def run_multi_agent():
    """Run the multi-agent system."""
    print("🤖 Starting Friday Multi-Agent System...")
    try:
        from multi_agent import FridaySupervisor
        supervisor = FridaySupervisor()
        result = supervisor.run("Hello Friday! What can you do?")
        print(result)
    except ImportError as e:
        print(f"❌ Failed to import multi-agent system: {e}")
        sys.exit(1)


def run_screen_watcher():
    """Run the screen watcher."""
    print("👀 Starting Screen Watcher...")
    try:
        from screen_watcher import get_watcher
        watcher = get_watcher()
        watcher.start()
        print("Screen watcher running. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("\nScreen watcher stopped.")
    except ImportError as e:
        print(f"❌ Failed to import screen watcher: {e}")
        sys.exit(1)


def run_goal_check():
    """Run goal check."""
    print("🎯 Running Goal Check...")
    try:
        from goal_memory import get_goal_manager
        manager = get_goal_manager()
        result = manager.enforce_goals()
        print(result)
    except ImportError as e:
        print(f"❌ Failed to import goal memory: {e}")
        sys.exit(1)


def run_coding_agent(task: str):
    """Run the coding agent."""
    print(f"💻 Starting Coding Agent for task: {task}")
    try:
        from coding_agent import coding_agent_tool
        result = coding_agent_tool("run", task=task)
        print(result)
    except ImportError as e:
        print(f"❌ Failed to import coding agent: {e}")
        sys.exit(1)


def run_self_improvement():
    """Run self-improvement analysis."""
    print("📈 Running Self-Improvement Analysis...")
    try:
        from self_improvement import self_improvement_tool
        result = self_improvement_tool("status")
        print(result)
    except ImportError as e:
        print(f"❌ Failed to import self-improvement: {e}")
        sys.exit(1)


def run_voice_wake():
    """Run voice wake word detection."""
    print("🎤 Starting Voice Wake Word Detection...")
    try:
        from voice_wake import get_wake_detector
        detector = get_wake_detector()
        detector.start()
        print("Voice wake detector running. Say 'Friday' to activate. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        detector.stop()
        print("\nVoice wake detector stopped.")
    except ImportError as e:
        print(f"❌ Failed to import voice wake: {e}")
        sys.exit(1)


def run_message_channels():
    """Run message channel integration."""
    print("💬 Starting Message Channel Integration...")
    try:
        from message_channels import message_channel_tool
        result = message_channel_tool("status")
        print(result)
    except ImportError as e:
        print(f"❌ Failed to import message channels: {e}")
        sys.exit(1)


# ─── Main ────────────────────────────────────#

def main():
    """Main entry point."""
    print_banner()

    parser = argparse.ArgumentParser(
        description=f"Friday v{FRIDAY_VERSION} - Ultimate AI Agent"
    )
    parser.add_argument(
        "command",
        choices=[
            "mcp", "multi-agent", "screen", "goals", "coding",
            "improve", "voice", "messages", "status", "all"
        ],
        help="Command to run"
    )
    parser.add_argument("--task", type=str, help="Task for coding agent")

    args = parser.parse_args()

    # Check components
    status = check_components()
    print_status(status)

    # Run command
    if args.command == "mcp":
        run_mcp_server()
    elif args.command == "multi-agent":
        run_multi_agent()
    elif args.command == "screen":
        run_screen_watcher()
    elif args.command == "goals":
        run_goal_check()
    elif args.command == "coding":
        if not args.task:
            print("❌ --task required for coding agent")
            sys.exit(1)
        run_coding_agent(args.task)
    elif args.command == "improve":
        run_self_improvement()
    elif args.command == "voice":
        run_voice_wake()
    elif args.command == "messages":
        run_message_channels()
    elif args.command == "status":
        print("[OK] Friday status check complete.")
    elif args.command == "all":
        print("[LAUNCH] Starting all Friday subsystems...")
        # This would start everything in threads
        print("This feature is coming soon!")


if __name__ == "__main__":
    main()
