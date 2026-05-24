# -*- coding: utf-8 -*-
"""
FRIDAY — Sovereign AI Agent.
Entry point: launches the dashboard server and live engine.
"""

from __future__ import annotations
import os
import sys
import signal
import time
import threading

from dotenv import load_dotenv
load_dotenv()

from friday._singletons import set_service_state, clear_all_state


def _log(msg: str):
    print(f"[FRIDAY] {msg}")


def _signal_handler(sig, frame):
    _log("Shutdown signal received. Cleaning up...")
    clear_all_state()
    sys.exit(0)


def main():
    os.environ.setdefault("PYTHONUTF8", "1")
    signal.signal(signal.SIGINT, _signal_handler)

    _log("")
    _log("=" * 50)
    _log("  F·R·I·D·A·Y   Sovereign Agent")
    _log("  Boot sequence initiated...")
    _log("=" * 50)
    _log("")

    # Start dashboard server in its own thread
    _log("[START] Dashboard server...")
    dash_thread = threading.Thread(
        target=_start_dashboard_blocking,
        daemon=True,
    )
    dash_thread.start()
    time.sleep(1.5)

    # Automatically open dashboard in user's default browser
    try:
        import webbrowser
        _log("[OPEN] Opening dashboard in browser: http://localhost:7070")
        webbrowser.open("http://localhost:7070")
    except Exception as e:
        _log(f"[WARN] Failed to open browser automatically: {e}")


    # Live engine (optional — if Gemini API is unavailable the dashboard keeps running)
    _log("[START] Live engine...")
    set_service_state("live_engine", status="running", pid=os.getpid())

    try:
        import asyncio
        from friday.live import friday_live_engine
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        _log("Shutting down.")
    except Exception as e:
        import traceback
        _log(f"[FAIL] Live engine error: {e}")
        traceback.print_exc()
        _log("[INFO] Dashboard remains available at http://localhost:7070")
        _log("[INFO] Press Ctrl+C to stop everything.")

    # Keep main thread alive so the daemon dashboard thread keeps serving
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Shutting down.")

    clear_all_state()
    _log("FRIDAY shutdown complete.")


def _start_dashboard_blocking():
    """Run the FastAPI server (blocks)."""
    from friday.api import FridayAPI
    api = FridayAPI(host="0.0.0.0", port=7070)
    api.start()


if __name__ == "__main__":
    main()
