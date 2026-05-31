# -*- coding: utf-8 -*-
"""
FRIDAY - Sovereign AI Agent.
CLI entry point: launches the live engine. The terminal is the primary interface.
"""

from __future__ import annotations
import os
import signal
import sys
import threading
import time

from dotenv import load_dotenv
load_dotenv()

from friday._singletons import set_service_state, get_service_state, clear_service_state, clear_all_state

_API_PORT = 7070


def _log(msg: str):
    print(f"[FRIDAY] {msg}", flush=True)


def _signal_handler(sig, frame):
    _log("Shutdown signal received. Cleaning up...")
    clear_all_state()
    sys.exit(0)


def _prepare_background_services() -> None:
    """Start lightweight support services before the live engine starts."""
    try:
        from friday.startup import bootstrap_configs
        bootstrap_configs(log_fn=_log)
    except Exception as e:
        _log(f"[WARN] Failed to bootstrap configs: {e}")

    try:
        from friday.startup import _run_memory_check
        result = _run_memory_check()
        if result.get("profile_exists"):
            _log("[OK] Memory profile loaded")
        else:
            _log("[WARN] Memory profile not found yet")
    except Exception as e:
        _log(f"[WARN] Memory check failed: {e}")

    try:
        from friday.startup import _start_sidecar_heartbeat
        result = _start_sidecar_heartbeat()
        if result.get("success"):
            _log("[OK] Sidecar heartbeat running")
    except Exception as e:
        _log(f"[WARN] Sidecar heartbeat failed: {e}")

    try:
        from friday.scheduler import scheduler_tool
        scheduler_tool("start")
        set_service_state("scheduler", status="running", pid=os.getpid())
        _log("[OK] Scheduler running")
    except Exception as e:
        _log(f"[WARN] Scheduler not started: {e}")


def _start_live_engine():
    """Start the Gemini Live engine in a daemon background thread."""
    def _run_live():
        import asyncio
        try:
            set_service_state("live_engine", status="starting", pid=os.getpid())
            from friday.live import friday_live_engine
            asyncio.run(friday_live_engine())
        except ImportError as e:
            _log(f"[WARN] Live engine dependencies missing: {e}")
            clear_service_state("live_engine")
        except Exception as e:
            _log(f"[ERROR] Live engine crashed on startup: {e}")
            import traceback
            traceback.print_exc()
            clear_service_state("live_engine")

    t = threading.Thread(target=_run_live, name="FridayLiveEngine", daemon=True)
    t.start()
    _log("[OK] Live engine thread launched (connecting to Gemini Live API…)")

    # Wait briefly then show status
    time.sleep(3)
    state = get_service_state("live_engine")
    if state and state.get("status") == "running":
        _log("[OK] Neural link established.")
    else:
        _log("[WARN] Live engine still connecting (see logs above).")


def main():
    os.environ["OPENCV_LOG_LEVEL"] = "OFF"
    os.environ.setdefault("PYTHONUTF8", "1")

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    _log("")
    _log("=" * 50)
    _log("  F.R.I.D.A.Y   Sovereign AI Agent")
    _log("  CLI boot sequence initiated...")
    _log("=" * 50)
    _log("")

    _prepare_background_services()

    # ── Launch Textual TUI (the ONLY UI) ──
    use_textual = os.environ.get("FRIDAY_NO_TEXTUAL", "").lower() not in ("1", "true", "yes")

    if use_textual:
        try:
            from friday.textual_runner import run_with_textual
            run_with_textual()
            return
        except ImportError as e:
            _log(f"[WARN] Textual not installed: {e}")
        except Exception as e:
            _log(f"[ERROR] Textual TUI crashed: {e}")
            import traceback
            traceback.print_exc()

    _log("")
    _log("ERROR: Textual TUI failed to start.")
    _log("Run: python -m pip install textual")
    _log("Set FRIDAY_NO_TEXTUAL=1 only as last resort.")
    _log("")


if __name__ == "__main__":
    main()
