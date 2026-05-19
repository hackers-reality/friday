"""
FRIDAY CLI — DEPRECATED. The dashboard at http://127.0.0.1:8080 is now the primary interface.

Usage:
    friday                          # Start the full FRIDAY daemon
    friday --sidecar                # Start daemon with sidecar WebSocket server
    friday --jarvis                 # Jarvis-compatibility mode (sidecar only)

All CLI subcommands have been removed. Direct all management through the dashboard.
"""

from __future__ import annotations
from typing import List, Optional
import argparse
import json
import os
import sys
import webbrowser

from friday._singletons import (
    check_http_endpoint,
)


_DEPRECATED_MSG = (
    "[DEPRECATED] CLI subcommands are removed. "
    "Use the FRIDAY dashboard at http://127.0.0.1:8080 instead.\n"
    "Run `friday` with no arguments to start the daemon."
)


# ─── Dashboard ───────────────────────────────────────────

def _cmd_dashboard(args: argparse.Namespace):
    """Manage dashboard services."""
    from friday._singletons import get_dashboard_state, set_service_state, clear_service_state

    action = args.dash_action or "status"

    if action == "start":
        import subprocess
        import time as _time
        dash = get_dashboard_state()
        if dash.get("api_healthy"):
            print("[OK] Dashboard services already running")
            print(f"  API: {dash.get('api_url')}")
            print(f"  UI:  {dash.get('ui_url')}")
            return

        from friday._paths import FRIDAY_MEMORY
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        launcher_path = os.path.join(FRIDAY_MEMORY, ".dashboard_daemon.py")
        with open(launcher_path, "w") as f:
            f.write(
                "import sys\n"
                "sys.path.insert(0, " + repr(project_root) + ")\n"
                "from friday.startup import launch_all\n"
                "launch_all(api_port=8090, ui_port=8080, start_live=False)\n"
                "import time\n"
                "while True:\n"
                "    time.sleep(60)\n"
            )

        CREATE_NO_WINDOW = 0x08000000
        proc = subprocess.Popen(
            [sys.executable, launcher_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        pid = proc.pid

        api_ok = False
        for attempt in range(6):
            _time.sleep(2)
            health = check_http_endpoint("http://127.0.0.1:8090/api/health", timeout=2)
            if health.get("reachable"):
                api_ok = True
                break

        if api_ok:
            set_service_state("dashboard_api",
                url="http://127.0.0.1:8090", port=8090, pid=pid,
                status="running", started_at=_time.time())
            ui_health = check_http_endpoint("http://127.0.0.1:8080/", timeout=2)
            if ui_health.get("reachable"):
                set_service_state("dashboard_ui",
                    url="http://127.0.0.1:8080", port=8080, pid=pid, status="running")
            print(f"[OK] Dashboard services started (PID {pid})")
            print(f"  API: http://127.0.0.1:8090")
            print(f"  UI:  http://127.0.0.1:8080")
        else:
            print("[FAIL] Dashboard services failed to start after 12 seconds")
            try:
                proc.kill()
            except Exception:
                pass

    elif action == "stop":
        import signal as _sig
        dash = get_dashboard_state()
        api = dash.get("api", {})
        pid = api.get("pid", 0)
        if pid and pid > 0:
            try:
                os.kill(pid, _sig.SIGTERM)
                print(f"[OK] Dashboard process (PID {pid}) stopped")
            except ProcessLookupError:
                print("[OK] Dashboard process already exited")
            except Exception as e:
                print(f"[WARN] Could not kill PID {pid}: {e}")
        else:
            print("[OK] No dashboard PID to stop")
        clear_service_state("dashboard_api")
        clear_service_state("dashboard_ui")
        print("[OK] Dashboard runtime state cleared")

    elif action == "status":
        dash = get_dashboard_state()
        api_url = dash.get("api_url", "http://127.0.0.1:8090")
        ui_url = dash.get("ui_url", "http://127.0.0.1:8080")
        api_health = check_http_endpoint(api_url + "/api/health", timeout=2)
        ui_health = check_http_endpoint(ui_url + "/", timeout=2)
        print("  DASHBOARD STATUS")
        print("-" * 50)
        api_status = "[ON] Running" if api_health.get("reachable") else "[OFF] Not running"
        print(f"  API:  {api_url} - {api_status}")
        ui_status = "[ON] Running" if ui_health.get("reachable") else "[OFF] Not running"
        print(f"  UI:   {ui_url} - {ui_status}")

    elif action == "url":
        dash = get_dashboard_state()
        ui_url = dash.get("ui_url", "http://127.0.0.1:8080")
        api_url = dash.get("api_url", "http://127.0.0.1:8090")
        if check_http_endpoint(ui_url + "/", timeout=2).get("reachable"):
            print(ui_url)
        elif check_http_endpoint(api_url + "/api/health", timeout=2).get("reachable"):
            print(api_url)
        else:
            print("http://127.0.0.1:8080")

    elif action == "open":
        dash = get_dashboard_state()
        ui_url = dash.get("ui_url", "http://127.0.0.1:8080")
        api_url = dash.get("api_url", "http://127.0.0.1:8090")
        if check_http_endpoint(ui_url + "/", timeout=2).get("reachable"):
            webbrowser.open(ui_url)
            print(f"[OK] Opened {ui_url}")
        elif check_http_endpoint(api_url + "/api/health", timeout=2).get("reachable"):
            webbrowser.open(api_url)
            print(f"[OK] Opened {api_url} (API — UI not available)")
        else:
            print("[FAIL] No FRIDAY dashboard service is running")
            print("  Run `friday` to start the daemon.")

    else:
        print(f"[FAIL] Unknown dashboard action: {action}")


# ─── Main Parser ─────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday",
        description="FRIDAY CLI — DEPRECATED. Use the dashboard at http://127.0.0.1:8080.",
    )
    sub = parser.add_subparsers(dest="command")

    p_dash = sub.add_parser("dashboard", aliases=["dash"], help="Dashboard management")
    p_dash.add_argument("dash_action", nargs="?", default="status",
                         choices=["start", "stop", "status", "url", "open"],
                         help="Dashboard action")
    p_dash.set_defaults(func=_cmd_dashboard)

    return parser


def cli_main(argv: Optional[List[str]] = None):
    """Entry point for `friday` CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        print(_DEPRECATED_MSG)
        return

    if args.command != "dashboard":
        print(_DEPRECATED_MSG)
        return

    try:
        args.func(args)
    except ImportError as e:
        print(f"[FAIL] Import error: {e}", file=sys.stderr)
        print("[HINT] Run from the project root", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
