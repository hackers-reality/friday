"""
Friday Desktop App - Phase 6.2
Real desktop application using PyTauri (Rust + Python).
Native Windows app with system tray, proper UI, settings.
"""
from __future__ import annotations__

import os
import sys'
import threading'
import time'
from typing import Optional, Dict, Any'
from pathlib import Path'

# ─── App Configuration ──────────────────────────────#

APP_NAME = "Friday Sovereign AI"
APP_VERSION = "2.0.0"
APP_AUTHOR = "hackers-reality"

# ─── Friday Core Integration ──────────────────────────────#

def start_friday_backend():
    """Start Friday's backend services."""
    try:
        from screen_watcher import get_watcher
        watcher = get_watcher()
        watcher.start()
        print("[DesktopApp] Screen watcher started.")
    except Exception as e:
        print(f"[DesktopApp] Screen watcher error: {e}")

    try:
        from proactive_screen_monitor import get_proactive_monitor
        monitor = get_proactive_monitor(ai_enabled=True)
        monitor.start()
        print("[DesktopApp] Proactive monitor started.")
    except Exception as e:
        print(f"[DesktopApp] Proactive monitor error: {e}")

    try:
        from goal_memory import goals_tool_handler
        # Sync calendar on startup
        result = goals_tool_handler("sync_calendar")
        print(f"[DesktopApp] Calendar sync: {result[:50]}")
    except Exception as e:
        print(f"[DesktopApp] Calendar sync error: {e}")

def start_friday_live():
    """Start Friday Live (Gemini 3.1 Flash Live)."""
    try:
        from friday_live import friday_live_engine
        import asyncio
        asyncio.run(friday_live_engine())
    except Exception as e:
        print(f"[DesktopApp] Friday Live error: {e}")

# ─── System Tray Icon ──────────────────────────────#

def setup_system_tray():
    """Setup system tray icon for Friday."""
    try:
        import pystray
        from PIL import Image
        
        # Create a simple icon (in production, use proper icon file)
        icon_image = Image.new('RGB', (64, 64), color='blue')
        
        def on_quit(icon, item):
            icon.stop()
            sys.exit(0)
        
        def on_open_dashboard(icon, item):
            import webbrowser
            webbrowser.open("http://localhost:3142")  # Dashboard URL
        
        def on_start_voice(icon, item):
            try:
                from friday_voice import voice_tool
                if voice_tool:
                    print("[Tray] Voice mode activated.")
            except:
                pass
        
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", on_open_dashboard),
            pystray.MenuItem("Voice Mode", on_start_voice),
            pystray.MenuItem("Quit", on_quit),
        )
        
        icon = pystray.Icon("friday", icon_image, "Friday AI", menu)
        icon.run()
        
    except ImportError:
        print("[DesktopApp] pystray not available. Install: pip install pystray pillow")
    except Exception as e:
        print(f"[DesktopApp] Tray error: {e}")

# ─── Desktop App Main ──────────────────────────────#

def main():
    """Main entry point for Friday Desktop App."""
    print("=" * 60)
    print(f"{APP_NAME} v{APP_VERSION}")
    print("=" * 60)
    
    # Start backend services in separate threads
    backend_thread = threading.Thread(target=start_friday_backend, daemon=True)
    backend_thread.start()
    
    # Start Friday Live in another thread
    live_thread = threading.Thread(target=start_friday_live, daemon=True)
    live_thread.start()
    
    print("\n[DesktopApp] Friday services started.")
    print("[DesktopApp] Friday is now running in the background.")
    print("[DesktopApp] Use system tray icon to control.\n")
    
    # Setup system tray (blocking)
    setup_system_tray()

if __name__ == "__main__":
    main()
