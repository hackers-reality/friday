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

_DASHBOARD_PORT = 7070


def _log(msg: str):
    print(f"[FRIDAY] {msg}", flush=True)


def _signal_handler(sig, frame):
    _log("Shutdown signal received. Cleaning up...")
    clear_all_state()
    sys.exit(0)


def _wait_for_server(port: int, timeout: float = 20.0) -> bool:
    """Poll localhost:port until it accepts connections or timeout."""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def main():
    os.environ["OPENCV_LOG_LEVEL"] = "OFF"
    os.environ.setdefault("PYTHONUTF8", "1")

    # Reconfigure stdout/stderr to UTF-8 so emoji/box chars don't crash on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    signal.signal(signal.SIGINT, _signal_handler)

    # Bootstrap configuration files on startup
    try:
        from friday.startup import bootstrap_configs
        bootstrap_configs(log_fn=_log)
    except Exception as e:
        _log(f"[WARN] Failed to bootstrap configs: {e}")

    _log("")
    _log("=" * 50)
    _log("  F.R.I.D.A.Y   Sovereign Agent")
    _log("  Boot sequence initiated...")
    _log("=" * 50)
    _log("")

    # ── Start dashboard server in its own thread ──────────────────
    _log("[START] Dashboard server on http://localhost:7070 ...")
    dash_thread = threading.Thread(
        target=_start_dashboard_blocking,
        daemon=True,
        name="dashboard-server",
    )
    dash_thread.start()

    # ── Wait until server is actually accepting connections ───────
    _log("[WAIT] Waiting for server to be ready...")
    ready = _wait_for_server(_DASHBOARD_PORT, timeout=20.0)
    if ready:
        _log(f"[OK] Dashboard is up at http://localhost:{_DASHBOARD_PORT}")
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{_DASHBOARD_PORT}")
            _log("[OPEN] Browser launched.")
        except Exception as e:
            _log(f"[WARN] Could not open browser: {e}")
    else:
        _log("[WARN] Dashboard server did not start within 20s — check errors above.")
        _log("[INFO] You can still open http://localhost:7070 manually.")

    # ── Live engine (voice AI) ─────────────────────────────────────
    _log("[START] Live voice engine...")
    set_service_state("live_engine", status="running", pid=os.getpid())

    try:
        import asyncio
        from friday.live import friday_live_engine
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        _log("Shutting down (Ctrl+C).")
    except Exception as e:
        import traceback
        _log(f"[FAIL] Live engine error: {e}")
        traceback.print_exc()
        _log("[INFO] Dashboard remains available at http://localhost:7070")
        _log("[INFO] Press Ctrl+C to stop everything.")

    # Keep main thread alive so daemon dashboard thread keeps serving
    try:
        _log("[INFO] Live engine exited. Dashboard still running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Shutting down.")

    clear_all_state()
    _log("FRIDAY shutdown complete.")


def _start_dashboard_blocking():
    """Run the FastAPI/uvicorn server (blocks this thread)."""
    try:
        from friday.api import FridayAPI
        api = FridayAPI(host="0.0.0.0", port=_DASHBOARD_PORT)
        api.start()
    except Exception as e:
        print(f"[FRIDAY] [ERROR] Dashboard failed to start: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
