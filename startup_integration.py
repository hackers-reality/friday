"""
Friday Startup Integration - Phase 6.1
Add Friday to Windows startup folder for automatic launch.
"""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

STARTUP_FOLDER = os.path.expandvars(
    r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
)

def get_friday_exe_path() -> str:
    """Get the path to the Friday executable or script."""
    # Check if we're running as a frozen exe
    if getattr(sys, 'frozen', False):
        return sys.executable

    # Otherwise, return the path to friday.py
    return os.path.abspath("friday.py")

def get_startup_shortcut_path() -> str:
    """Get the path where the startup shortcut would be."""
    return os.path.join(STARTUP_FOLDER, "Friday.lnk")

def add_to_startup(exe_path: Optional[str] = None) -> str:
    """
    Add Friday to Windows startup folder.
    Creates a shortcut (.lnk) that launches Friday on login.
    """
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return (
            "[FAIL] pywin32 not installed. Install with: pip install pywin32\n"
            "Then run this function again."
        )

    if not exe_path:
        exe_path = get_friday_exe_path()

    try:
        # Ensure startup folder exists
        os.makedirs(STARTUP_FOLDER, exist_ok=True)

        shortcut_path = get_startup_shortcut_path()

        # Create shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)

        # If it's a Python script, set the arguments
        if exe_path.endswith(".py"):
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{exe_path}"'
        else:
            shortcut.Targetpath = exe_path

        shortcut.WorkingDirectory = os.path.dirname(exe_path) or os.getcwd()
        shortcut.Description = "Friday - Sovereign AI Assistant"
        shortcut.save()

        return f"[OK] Friday added to startup! Shortcut: {shortcut_path}"

    except Exception as e:
        return f"[FAIL] Failed to add to startup: {str(e)}"

def remove_from_startup() -> str:
    """Remove Friday from Windows startup."""
    shortcut_path = get_startup_shortcut_path()

    if os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
            return "[OK] Friday removed from startup."
        except Exception as e:
            return f"[FAIL] Failed to remove: {str(e)}"
    return "Friday was not in startup."

def check_startup_status() -> str:
    """Check if Friday is in startup."""
    shortcut_path = get_startup_shortcut_path()

    if os.path.exists(shortcut_path):
        return f"[OK] Friday is in startup. Shortcut: {shortcut_path}"
    return "[FAIL] Friday is NOT in startup."

def add_to_startup_simple() -> str:
    """
    Simpler method: just copy a batch file to startup.
    This is a fallback if COM objects fail.
    """
    try:
        exe_path = get_friday_exe_path()
        bat_content = f'@echo off\n"{sys.executable}" "{exe_path}"\n'

        bat_path = os.path.join(STARTUP_FOLDER, "Friday.bat")

        with open(bat_path, "w") as f:
            f.write(bat_content)

        return f"[OK] Friday added to startup (batch method). File: {bat_path}"

    except Exception as e:
        return f"[FAIL] Failed: {str(e)}"


if __name__ == "__main__":
    # Test
    print("Friday Startup Integration Test")
    print("=" * 40)

    # Check status
    print(check_startup_status())

    # Add to startup
    # print(add_to_startup())

    # Or use simple method
    # print(add_to_startup_simple())
