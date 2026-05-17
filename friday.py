# -*- coding: utf-8 -*-
"""
FRIDAY — Sovereign AI Agent.
Foreground supervisor: launches dashboard, sidecar, memory, and live engine.
"""

from __future__ import annotations
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

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, _signal_handler)

    _log("")
    _log("=" * 50)
    _log("  F.R.I.D.A.Y. Sovereign Agent")
    _log("  Boot sequence initiated...")
    _log("=" * 50)
    _log("")

    # Start all background services
    from friday.startup import launch_all
    results = launch_all(api_port=8090, ui_port=8080, start_live=False, log_fn=_log)

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
        _log(f"[FAIL] Live engine error: {e}")
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
        else:
            _log("[FAIL] Max restarts reached. Exiting.")

    # Cleanup
    clear_all_state()
    _log("FRIDAY shutdown complete.")


if __name__ == "__main__":
    main()
