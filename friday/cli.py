"""
FRIDAY CLI — command-line interface for system management.

Usage:
    friday [command] [options]
    python -m friday.cli [command] [options]

Commands:
    doctor          Run system diagnostic checks
    fix             Attempt automatic repairs of common issues
    status          Show overall system health summary with service URLs
    memory-tree     Interact with the Memory Tree knowledge base
    sidecar         Manage sidecar network devices
    snapshots       List/manage memory snapshots
    autonomy        View/configure autonomy level
    suit-check      Run pre-flight system verification
    damage-report   Generate damage/risk report
    morning         Run morning planning routine
    evening         Run evening review routine
    dashboard       Manage the HTML dashboard (start, stop, status, url, open)
    config          View/update system configuration
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser

from friday._paths import FRIDAY_MEMORY, FRIDAY_CONFIG
from friday._singletons import (
    load_runtime_state, get_service_state, set_service_state, clear_service_state,
    check_http_endpoint, check_port_open, find_free_port,
)


def _print_json(data: Any):
    print(json.dumps(data, indent=2, default=str))


def _print_table(items: List[Dict[str, Any]], cols: Optional[List[str]] = None):
    if not items:
        print("(empty)")
        return
    if cols is None:
        cols = list(items[0].keys())
    rows = [[str(item.get(c, "")) for c in cols] for item in items]
    widths = [max(len(c), max(len(r[i]) for r in rows)) for i, c in enumerate(cols)]
    sep = "-+-".join("-" * w for w in widths)
    header = " | ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(r.ljust(w) for r, w in zip(row, widths)))


# ─── Doctor ──────────────────────────────────────────────

def _cmd_doctor(args: argparse.Namespace):
    """Run system diagnostic checks and report findings."""
    from friday.diagnostics import run_diagnostics, format_diagnostic_report
    results = run_diagnostics()
    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(format_diagnostic_report(results, verbose=args.verbose))

    # Additional CLI-specific checks
    print()
    print("  CLI-SPECIFIC CHECKS")
    print("-" * 60)

    # Check runtime state
    state = load_runtime_state()
    if state:
        print(f"  [OK] Runtime state: {len(state)} services tracked")
        for svc, info in state.items():
            if svc.startswith("_"):
                continue
            url = info.get("url", "")
            status = info.get("status", "unknown")
            print(f"       {svc}: {status} {url}")
    else:
        print("  [WARN] No runtime state (services not started)")

    # Check if dashboard health endpoints respond
    for name, port, path in [
        ("Dashboard API", 8090, "/api/health"),
        ("Dashboard UI", 8080, "/"),
    ]:
        health = check_http_endpoint(f"http://127.0.0.1:{port}{path}")
        if health.get("reachable"):
            print(f"  [OK] {name} http://127.0.0.1:{port} — reachable ({health.get('latency_ms', '?')}ms)")
        else:
            chk = check_port_open("127.0.0.1", port)
            if chk["open"]:
                print(f"  [WARN] {name} http://127.0.0.1:{port} — port open but endpoint not responding")
            else:
                print(f"  [WARN] {name} http://127.0.0.1:{port} — port closed (not running)")

    # Check for stale PIDs in state
    for svc, info in state.items():
        if isinstance(info, dict) and info.get("pid"):
            pid = info["pid"]
            if pid == 0:
                continue
            # Check if PID is alive (cross-process)
            try:
                os.kill(pid, 0)
            except (OSError, PermissionError):
                print(f"  [WARN] Stale PID {pid} for {svc} — process no longer exists")


# ─── Fix ─────────────────────────────────────────────────

def _cmd_fix(args: argparse.Namespace):
    """Attempt automatic repairs of common issues."""
    from friday.diagnostics import run_diagnostics
    print("=" * 60)
    print("  FRIDAY AUTO-FIX")
    print(f"  Running repairs for common issues...")
    print("=" * 60)

    fixes_applied = []

    # 1. Check and fix runtime state
    state_path = os.path.join(FRIDAY_MEMORY, "runtime_state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path) as f:
                state = json.load(f)
            # Remove stale entries
            cleaned = False
            for svc in list(state.keys()):
                if svc.startswith("_"):
                    continue
                info = state[svc]
                if isinstance(info, dict) and info.get("pid") and info.get("pid") != 0:
                    try:
                        os.kill(info["pid"], 0)
                    except (OSError, PermissionError):
                        del state[svc]
                        cleaned = True
                        fixes_applied.append(f"Cleaned stale state for {svc}")
            if cleaned:
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
        except Exception:
            # Corrupted state file
            os.remove(state_path)
            fixes_applied.append("Removed corrupted runtime_state.json")

    # 2. Check for port conflicts and offer to clear them
    for port in [8080, 8090]:
        chk = check_port_open("127.0.0.1", port)
        if chk["open"]:
            # Check if it's one of our services
            health = check_http_endpoint(f"http://127.0.0.1:{port}/api/health", timeout=1)
            if not health.get("reachable"):
                # Port is occupied by something else — not much we can do
                fixes_applied.append(f"Port {port} is in use by another process (not FRIDAY)")

    # 3. Ensure memory directories exist
    for d in [FRIDAY_MEMORY, FRIDAY_CONFIG,
              os.path.join(FRIDAY_MEMORY, "memory_tree"),
              os.path.join(FRIDAY_MEMORY, "memory_tree", "daily_notes")]:
        os.makedirs(d, exist_ok=True)
    fixes_applied.append("Ensured memory directory structure exists")

    # 4. Check module imports
    for mod_name in ["friday.dashboard_api", "friday.dashboard", "friday.startup",
                      "friday.cli", "friday._singletons"]:
        try:
            __import__(mod_name)
        except ImportError as e:
            fixes_applied.append(f"Import issue: {mod_name} — {e}")

    if fixes_applied:
        print("\n  Fixes applied:")
        for f in fixes_applied:
            print(f"    ✓ {f}")
    else:
        print("\n  No fixes needed.")

    print("\n  Running post-fix diagnostics...")
    results = run_diagnostics()
    passed = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "fail")
    print(f"  Diagnostics: {passed} passed, {failed} failed")
    print("=" * 60)


# ─── Status ──────────────────────────────────────────────

def _cmd_status(args: argparse.Namespace):
    """Show overall system health summary with service status and URLs."""
    from friday._singletons import get_dashboard_state

    header = "=" * 60
    print(f"\n{header}")
    print("  FRIDAY SYSTEM STATUS")
    print(f"{header}")

    # Basic info
    print(f"  Memory root:   {FRIDAY_MEMORY}")
    print(f"  Config root:   {FRIDAY_CONFIG}")
    print()

    # Dashboard state
    dash = get_dashboard_state()
    api = dash.get("api", {})
    ui = dash.get("ui", {})

    print("  DASHBOARD SERVICES")

    api_healthy = dash.get("api_healthy", False)
    api_url = dash.get("api_url", "http://127.0.0.1:8090")

    # Double-check health directly
    api_health = check_http_endpoint(api_url + "/api/health", timeout=2)
    ui_health = check_http_endpoint(dash.get("ui_url", "http://127.0.0.1:8080") + "/", timeout=2)

    api_ok = api_health.get("reachable", False)
    ui_ok = ui_health.get("reachable", False)

    api_sym = "[ON]" if api_ok else "[OFF]"
    ui_sym = "[ON]" if ui_ok else "[OFF]"
    api_clr = "UP" if api_ok else ("REG" if api.get("status") else "DOWN")
    ui_clr = "UP" if ui_ok else ("REG" if ui.get("status") else "DOWN")

    print(f"  {api_sym} API:     {api_url}  [{api_clr}]")
    if api_ok:
        print(f"             Latency: {api_health.get('latency_ms', '?')}ms")
    print(f"  {ui_sym} UI:      {dash.get('ui_url', 'http://127.0.0.1:8080')}  [{ui_clr}]")
    if ui_ok:
        print(f"             Latency: {ui_health.get('latency_ms', '?')}ms")
    print()

    # Sidecar state
    sc_state = get_service_state("sidecar_heartbeat")
    sc_sym = "[ON]" if sc_state.get("status") == "running" else "[OFF]"
    print(f"  {sc_sym} Sidecar heartbeat: {sc_state.get('status', 'not started')}")
    print()

    # Memory
    profile_path = os.path.join(FRIDAY_MEMORY, "user_profile.json")
    mem_loaded = os.path.exists(profile_path)
    mem_sym = "[ON]" if mem_loaded else "[OFF]"
    print(f"  {mem_sym} Memory:")
    if mem_loaded:
        with open(profile_path) as f:
            profile = json.load(f)
        print(f"       User: {profile.get('name', 'Unknown')}")
        print(f"       Role: {profile.get('role', 'Unknown')}")
        print(f"       Goals: {len(profile.get('goals', []))} tracked")
    else:
        print(f"       No user profile (run friday doctor for details)")

    # Memory Tree
    mt_path = os.path.join(FRIDAY_MEMORY, "memory_tree")
    if os.path.exists(mt_path):
        mt_files = [f for f in os.listdir(mt_path) if f.endswith(".md")]
        dn_path = os.path.join(mt_path, "daily_notes")
        dn_count = len([f for f in os.listdir(dn_path) if f.endswith(".md")]) if os.path.exists(dn_path) else 0
        print(f"  Memory Tree: {len(mt_files)} pages, {dn_count} daily notes")
    print()

    # Live engine
    live_state = get_service_state("live_engine")
    live_sym = "[ON]" if live_state.get("status") == "running" else "[OFF]"
    print(f"  {live_sym} Live engine: {live_state.get('status', 'not started')}")
    print()

    # Runtime state
    state = load_runtime_state()
    if state:
        updated = state.get("_updated_at", 0)
        if updated:
            from datetime import datetime
            print(f"  Runtime state last updated: {datetime.fromtimestamp(updated).strftime('%H:%M:%S')}")
    print()

    # Quick URLs
    print("  QUICK LINKS")
    if ui_ok:
        print(f"    Dashboard UI:  {dash.get('ui_url', 'http://127.0.0.1:8080')}")
    if api_ok:
        print(f"    Dashboard API: {api_url}")
    if not ui_ok and not api_ok:
        print("    (No dashboard services running. Try: friday dashboard start)")
    print(f"\n{header}\n")


# ─── Dashboard ───────────────────────────────────────────

def _cmd_dashboard(args: argparse.Namespace):
    """Manage dashboard services."""
    from friday._singletons import get_dashboard_state

    action = args.dash_action or "status"

    if action == "start":
        # Spawn a persistent background process that keeps the servers alive
        # Check if already running first
        dash = get_dashboard_state()
        if dash.get("api_healthy"):
            print("[OK] Dashboard services already running")
            print(f"  API: {dash.get('api_url')}")
            print(f"  UI:  {dash.get('ui_url')}")
            return

        # Launch with subprocess for persistence across CLI exit.
        # Write a small launcher script in friday_memory so we can track PID.
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

        # Wait with retry for services to come online
        import time as _time
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
        dash = get_dashboard_state()
        api = dash.get("api", {})
        pid = api.get("pid", 0)
        if pid and pid > 0:
            try:
                import signal as _sig
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
        api = dash.get("api", {})
        ui = dash.get("ui", {})

        api_url = dash.get("api_url", "http://127.0.0.1:8090")
        ui_url = dash.get("ui_url", "http://127.0.0.1:8080")

        api_health = check_http_endpoint(api_url + "/api/health", timeout=2)
        ui_health = check_http_endpoint(ui_url + "/", timeout=2)

        print("  DASHBOARD STATUS")
        print("-" * 50)

        api_status = "[ON] Running" if api_health.get("reachable") else \
                     ("[OFF] Registered (check health)" if api.get("status") else "[OFF] Not running")
        print(f"  API:  {api_url} - {api_status}")
        if api_health.get("latency_ms"):
            print(f"        Latency: {api_health['latency_ms']}ms")

        ui_status = "[ON] Running" if ui_health.get("reachable") else \
                     ("[OFF] Registered (check health)" if ui.get("status") else "[OFF] Not running")
        print(f"  UI:   {ui_url} - {ui_status}")
        if ui_health.get("latency_ms"):
            print(f"        Latency: {ui_health['latency_ms']}ms")
        print()

    elif action == "url":
        dash = get_dashboard_state()
        # Check UI first, then API
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
            print("  Start with: friday dashboard start")

    else:
        print(f"[FAIL] Unknown dashboard action: {action}")


# ─── Memory Tree ─────────────────────────────────────────

def _cmd_memory_tree(args: argparse.Namespace):
    from friday.memory_tree import memory_tree_tool

    action = args.mt_action or "status"
    kwargs = {}

    if action == "read":
        kwargs["name"] = args.name or args.mt_page
    elif action == "write":
        kwargs["name"] = args.name
        kwargs["content"] = args.content
    elif action == "search":
        kwargs["query"] = args.query
    elif action == "daily_note":
        if args.date:
            kwargs["date"] = args.date

    result = memory_tree_tool(action, **kwargs)
    print(result)


# ─── Sidecar ─────────────────────────────────────────────

def _cmd_sidecar(args: argparse.Namespace):
    from friday.sidecar_network import sidecar_network_tool

    action = args.sc_action or "status"
    kwargs = {}

    if action == "generate":
        kwargs["label"] = args.label or "cli-token"
    elif action == "verify":
        kwargs["token"] = args.token
        kwargs["host"] = args.host or "unknown"
    elif action == "revoke":
        kwargs["token"] = args.token

    result = sidecar_network_tool(action, **kwargs)
    print(result)


# ─── Snapshots ───────────────────────────────────────────

def _cmd_snapshots(args: argparse.Namespace):
    from friday.snapshots import snapshot_tool

    action = args.snap_action or "list"
    kwargs = {}
    if action == "create":
        kwargs["label"] = args.label or ""
    elif action == "restore":
        kwargs["snapshot_id"] = args.snapshot_id
    elif action == "delete":
        kwargs["snapshot_id"] = args.snapshot_id

    result = snapshot_tool(action, **kwargs)
    print(result)


# ─── Autonomy ────────────────────────────────────────────

def _cmd_autonomy(args: argparse.Namespace):
    from friday.autonomy import autonomy_tool

    action = args.aut_action or "status"
    kwargs = {}
    if action == "set":
        kwargs["level"] = args.level

    result = autonomy_tool(action, **kwargs)
    print(result)


# ─── Suit Check ──────────────────────────────────────────

def _cmd_suit_check(args: argparse.Namespace):
    from friday.ironman import suit_check
    result = suit_check()
    _print_json(result) if args.json else print(result)


# ─── Damage Report ───────────────────────────────────────

def _cmd_damage_report(args: argparse.Namespace):
    from friday.ironman import damage_report
    result = damage_report()
    _print_json(result) if args.json else print(result)


# ─── Morning / Evening ───────────────────────────────────

def _cmd_morning(args: argparse.Namespace):
    from friday.ironman import morning_plan
    result = morning_plan()
    print(result)


def _cmd_evening(args: argparse.Namespace):
    from friday.ironman import evening_review
    result = evening_review()
    print(result)


# ─── Config ──────────────────────────────────────────────

def _cmd_config(args: argparse.Namespace):
    action = args.cfg_action or "show"

    if action == "show":
        print(f"FRIDAY Memory:  {FRIDAY_MEMORY}")
        print(f"FRIDAY Config:  {FRIDAY_CONFIG}")
        print()

        if os.path.exists(FRIDAY_CONFIG):
            for fname in sorted(os.listdir(FRIDAY_CONFIG)):
                fpath = os.path.join(FRIDAY_CONFIG, fname)
                if fname.endswith(".json"):
                    try:
                        with open(fpath) as f:
                            data = json.load(f)
                        print(f"  {fname}:")
                        for k, v in data.items() if isinstance(data, dict) else []:
                            if isinstance(v, dict):
                                print(f"    {k}: ... ({len(v)} keys)")
                            elif isinstance(v, list):
                                print(f"    {k}: [{len(v)} items]")
                            else:
                                print(f"    {k}: {v}")
                    except Exception:
                        print(f"  {fname}: (unreadable)")
        # Runtime state
        state_path = os.path.join(FRIDAY_MEMORY, "runtime_state.json")
        if os.path.exists(state_path):
            print(f"\n  Runtime state: {state_path}")
            with open(state_path) as f:
                state = json.load(f)
            for svc, info in state.items():
                if svc.startswith("_"):
                    continue
                if isinstance(info, dict):
                    pid = info.get("pid", "?")
                    url = info.get("url", "")
                    status = info.get("status", "?")
                    print(f"    {svc}: pid={pid} status={status} {url}")

    elif action == "path":
        print(FRIDAY_CONFIG)
    else:
        print(f"[FAIL] Unknown config action: {action}")


# ─── Main Parser ─────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday",
        description="FRIDAY CLI — personal AI OS management interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  friday doctor                     # Run diagnostics
  friday doctor --verbose           # Verbose diagnostics
  friday fix                        # Auto-fix common issues
  friday status                     # System status with URLs
  friday dashboard start            # Start dashboard services
  friday dashboard open             # Open dashboard in browser
  friday memory-tree read people    # Read memory page
  friday sidecar status             # Sidecar network status
        """
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    sub = parser.add_subparsers(dest="command")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Run system diagnostics")
    p_doctor.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p_doctor.set_defaults(func=_cmd_doctor)

    # fix
    p_fix = sub.add_parser("fix", help="Auto-fix common issues")
    p_fix.set_defaults(func=_cmd_fix)

    # status
    p_status = sub.add_parser("status", help="System health summary with URLs")
    p_status.set_defaults(func=_cmd_status)

    # dashboard
    p_dash = sub.add_parser("dashboard", aliases=["dash"], help="Dashboard management")
    p_dash.add_argument("dash_action", nargs="?", default="status",
                         choices=["start", "stop", "status", "url", "open"],
                         help="Dashboard action")
    p_dash.set_defaults(func=_cmd_dashboard)

    # memory-tree
    p_mt = sub.add_parser("memory-tree", aliases=["mt"], help="Memory Tree operations")
    p_mt.add_argument("mt_action", nargs="?", default="status",
                       choices=["status", "build-index", "read", "write", "search", "daily-note", "daily-notes", "update", "context"],
                       help="Memory tree action")
    p_mt.add_argument("--name", "-n", help="Page name")
    p_mt.add_argument("--content", "-c", help="Page content (for write)")
    p_mt.add_argument("--query", "-q", help="Search query")
    p_mt.add_argument("--date", "-d", help="Date for daily note (YYYY-MM-DD)")
    p_mt.set_defaults(func=_cmd_memory_tree)

    # sidecar
    p_sc = sub.add_parser("sidecar", aliases=["sc"], help="Sidecar network management")
    p_sc.add_argument("sc_action", nargs="?", default="status",
                       choices=["status", "discover", "generate", "verify", "revoke", "list", "health"],
                       help="Sidecar action")
    p_sc.add_argument("--label", "-l", help="Token label (for generate)")
    p_sc.add_argument("--token", "-t", help="Token value (for verify/revoke)")
    p_sc.add_argument("--host", help="Host address (for verify)")
    p_sc.set_defaults(func=_cmd_sidecar)

    # snapshots
    p_snap = sub.add_parser("snapshots", aliases=["snap"], help="Memory snapshot management")
    p_snap.add_argument("snap_action", nargs="?", default="list",
                         choices=["list", "create", "restore", "delete", "info"],
                         help="Snapshot action")
    p_snap.add_argument("--snapshot-id", "-i", help="Snapshot ID (for restore/delete/info)")
    p_snap.add_argument("--label", "-l", help="Label for snapshot")
    p_snap.set_defaults(func=_cmd_snapshots)

    # autonomy
    p_aut = sub.add_parser("autonomy", aliases=["aut"], help="Autonomy level management")
    p_aut.add_argument("aut_action", nargs="?", default="status",
                        choices=["status", "set", "info"],
                        help="Autonomy action")
    p_aut.add_argument("--level", choices=["off", "low", "medium", "high", "full"],
                        help="Autonomy level (for set)")
    p_aut.set_defaults(func=_cmd_autonomy)

    # suit-check
    sub.add_parser("suit-check", aliases=["check"], help="Pre-flight system verification").set_defaults(func=_cmd_suit_check)

    # damage-report
    sub.add_parser("damage-report", aliases=["damage"], help="System risk/damage report").set_defaults(func=_cmd_damage_report)

    # morning
    sub.add_parser("morning", help="Run morning planning routine").set_defaults(func=_cmd_morning)

    # evening
    sub.add_parser("evening", help="Run evening review routine").set_defaults(func=_cmd_evening)

    # config
    p_cfg = sub.add_parser("config", aliases=["cfg"], help="Configuration management")
    p_cfg.add_argument("cfg_action", nargs="?", default="show",
                        choices=["show", "path"],
                        help="Config action")
    p_cfg.set_defaults(func=_cmd_config)

    return parser


def cli_main(argv: Optional[List[str]] = None):
    """Entry point for `friday` CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    try:
        args.func(args)
    except ImportError as e:
        print(f"[FAIL] Import error: {e}", file=sys.stderr)
        print("[HINT] Run from the project root (E:\\open-interpreter)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        if args.json:
            print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
