"""
FRIDAY CLI — command-line interface for system management.

Usage:
    python -m friday.cli [command] [options]

Commands:
    doctor          Run system diagnostic checks
    status          Show overall system health summary
    memory-tree     Interact with the Memory Tree knowledge base
    sidecar         Manage sidecar network devices
    snapshots       List/manage memory snapshots
    autonomy        View/configure autonomy level
    suit-check      Run pre-flight system verification
    damage-report   Generate damage/risk report
    morning         Run morning planning routine
    evening         Run evening review routine
    dashboard       Manage the HTML dashboard
    config          View/update system configuration
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import argparse
import json
import os
import sys

from friday._paths import FRIDAY_MEMORY, FRIDAY_CONFIG


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
    """Run system diagnostic checks."""
    from friday.diagnostics import run_diagnostics, format_diagnostic_report
    results = run_diagnostics()
    if args.json:
        print(json.dumps(results, indent=2))
        return
    print(format_diagnostic_report(results, verbose=args.verbose))


# ─── Status ──────────────────────────────────────────────

def _cmd_status(args: argparse.Namespace):
    """Show overall system health summary."""
    header = "=" * 60
    print(f"\n{header}")
    print("  FRIDAY SYSTEM STATUS")
    print(f"{header}\n")

    # Basic info
    print(f"  Memory root:  {FRIDAY_MEMORY}")
    print(f"  Config root:  {FRIDAY_CONFIG}")
    print()

    # Counts
    mem_dirs = sum(1 for f in os.listdir(FRIDAY_MEMORY) if os.path.isdir(os.path.join(FRIDAY_MEMORY, f))) if os.path.exists(FRIDAY_MEMORY) else 0
    print(f"  Memory directories:  {mem_dirs}")
    print()

    # Profile
    profile_path = os.path.join(FRIDAY_MEMORY, "user_profile.json")
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile = json.load(f)
        print(f"  User:       {profile.get('name', 'Unknown')}")
        print(f"  Role:       {profile.get('role', 'Unknown')}")
        print(f"  Goals:      {len(profile.get('goals', []))} tracked")
    else:
        print("  User profile: not found")

    # Memory Tree
    mt_path = os.path.join(FRIDAY_MEMORY, "memory_tree")
    if os.path.exists(mt_path):
        mt_files = [f for f in os.listdir(mt_path) if f.endswith(".md")]
        dn_path = os.path.join(mt_path, "daily_notes")
        dn_count = len([f for f in os.listdir(dn_path) if f.endswith(".md")]) if os.path.exists(dn_path) else 0
        print(f"\n  Memory Tree: {len(mt_files)} pages, {dn_count} daily notes")

    print(f"\n{header}\n")


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


# ─── Dashboard ──────────────────────────────────────────

def _cmd_dashboard(args: argparse.Namespace):
    action = args.dash_action or "status"

    if action == "start":
        from friday.startup import launch_dashboard_background
        result = launch_dashboard_background()
        print(result)
    elif action == "stop":
        from friday.dashboard_api import DashboardAPI
        from friday._singletons import _dashboard_api
        if _dashboard_api:
            _dashboard_api.stop()
            print("[OK] Dashboard stopped")
        else:
            print("[OK] Dashboard not running")
    elif action == "url":
        from friday._singletons import _dashboard_api
        if _dashboard_api and hasattr(_dashboard_api, 'port'):
            print(f"http://localhost:{_dashboard_api.port}")
        else:
            print("[FAIL] Dashboard not running")
    else:
        print(f"[FAIL] Unknown dashboard action: {action}")


# ─── Config ──────────────────────────────────────────────

def _cmd_config(args: argparse.Namespace):
    action = args.cfg_action or "show"

    if action == "show":
        print(f"FRIDAY Memory:  {FRIDAY_MEMORY}")
        print(f"FRIDAY Config:  {FRIDAY_CONFIG}")
        print()

        # Show all config files
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
  python -m friday.cli doctor                  # Run diagnostics
  python -m friday.cli doctor --verbose         # Verbose diagnostics
  python -m friday.cli status                   # System status
  python -m friday.cli memory-tree read people  # Read memory page
  python -m friday.cli sidecar status           # Sidecar network status
  python -m friday.cli suit-check               # Pre-flight check
  python -m friday.cli damage-report            # System risk report
  python -m friday.cli snapshots list           # List snapshots
  python -m friday.cli autonomy status          # Check autonomy level
        """
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    sub = parser.add_subparsers(dest="command")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Run system diagnostics")
    p_doctor.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p_doctor.set_defaults(func=_cmd_doctor)

    # status
    p_status = sub.add_parser("status", help="System health summary")
    p_status.set_defaults(func=_cmd_status)

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

    # dashboard
    p_dash = sub.add_parser("dashboard", aliases=["dash"], help="Dashboard management")
    p_dash.add_argument("dash_action", nargs="?", default="status",
                         choices=["start", "stop", "status", "url"],
                         help="Dashboard action")
    p_dash.set_defaults(func=_cmd_dashboard)

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
