# -*- coding: utf-8 -*-
"""
FRIDAY — Sovereign AI Agent.
Foreground supervisor: launches dashboard, sidecar, memory, and live engine.
"""

from __future__ import annotations
import argparse
import os
import sys
import signal
import time

from dotenv import load_dotenv
load_dotenv()

from friday._paths import FRIDAY_MEMORY
from friday._singletons import set_service_state, clear_all_state


def _log(msg: str):
    print(f"[FRIDAY] {msg}")


def _signal_handler(sig, frame):
    _log("Shutdown signal received. Cleaning up...")
    clear_all_state()
    sys.exit(0)


def main():
    os.environ.setdefault("PYTHONUTF8", "1")

    parser = argparse.ArgumentParser(description="FRIDAY Sovereign Agent", add_help=False)
    parser.add_argument("--sidecar", action="store_true", help="Enable sidecar WebSocket server")
    parser.add_argument("--jarvis", action="store_true", help="Jarvis-compatibility mode (sidecar only)")
    parser.add_argument("--help", action="store_true", dest="show_help", help="Show this help")
    args, unknown = parser.parse_known_args()

    if args.show_help or (unknown and unknown[0] in ("-h", "--help")):
        print("FRIDAY Sovereign Agent")
        print()
        print("Usage:  friday [--sidecar] [--jarvis]")
        print()
        print("  (no args)    Start full FRIDAY daemon (dashboard + services)")
        print("  --sidecar    Also start sidecar WebSocket server")
        print("  --jarvis     Start in Jarvis-compatibility mode (sidecar only)")
        print()
        print("FRIDAY is running at http://127.0.0.1:8080")
        return

    if unknown:
        print("FRIDAY is running at http://127.0.0.1:8080")
        print()
        print("Unknown option(s): %s" % " ".join(unknown))
        print("Usage: friday [--sidecar] [--jarvis]")
        return

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, _signal_handler)

    if args.jarvis:
        _log("Jarvis-compatibility mode — sidecar server only")
        _log("Starting sidecar WebSocket server...")
        from friday.sidecar_network import start_ws_server
        start_ws_server()
        _log("Sidecar WebSocket server running on ws://0.0.0.0:42070")
        _log("Waiting for sidecar connections...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            _log("Shutting down.")
        clear_all_state()
        return

    _log("")
    _log("=" * 50)
    _log("  F.R.I.D.A.Y. Sovereign Agent")
    _log("  Boot sequence initiated...")
    _log("=" * 50)
    _log("")

    # Start all background services
    from friday.startup import launch_all
    results = launch_all(api_port=8090, ui_port=8080, start_live=False,
                         start_sidecar_ws=args.sidecar, log_fn=_log)

    api_ok = results.get("dashboard_api", {}).get("success", False)
    ui_ok = results.get("dashboard_ui", {}).get("success", False)

    if not api_ok and not ui_ok:
        _log("[WARN] No dashboard services started. Continuing in headless mode.")

    # Start live engine
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
        max_restarts = 5
        for attempt in range(1, max_restarts + 1):
            _log(f"Restarting (attempt {attempt}/{max_restarts})...")
            time.sleep(3)
            try:
                import asyncio
                from friday.live import friday_live_engine
                asyncio.run(friday_live_engine())
                break
            except KeyboardInterrupt:
                _log("Shutting down.")
                break
            except Exception as e2:
                _log(f"[FAIL] Live engine error (attempt {attempt}): {e2}")
                traceback.print_exc()
        else:
            _log("[FAIL] Max restarts reached. Exiting.")

    # Cleanup
    clear_all_state()
    _log("FRIDAY shutdown complete.")


if __name__ == "__main__":
    main()
