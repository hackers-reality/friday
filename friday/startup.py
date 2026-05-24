"""
FRIDAY Startup — supervisor for background services.

Launches the FastAPI server (port 7070) with the Vite+React dashboard,
sidecar heartbeat, memory checks, and the live engine.
All services are tracked via runtime_state.json.
"""

from __future__ import annotations
from typing import Dict, Optional, Any
import os
import sys
import time
import threading

from friday._paths import FRIDAY_MEMORY
from friday._singletons import (
    set_service_state, clear_service_state, get_service_state,
    check_http_endpoint, check_port_open, find_free_port,
)


def _log(msg: str):
    print(f"[FRIDAY] {msg}")


def _get_pid() -> int:
    return os.getpid()


# ─── Dashboard (FastAPI + React) ─────────────────────────

def _start_dashboard(port: int = 7070) -> dict:
    """Start the FastAPI server with the Vite+React dashboard."""
    from friday.api import FridayAPI

    port_check = check_port_open("127.0.0.1", port)
    if port_check["open"]:
        health = check_http_endpoint(f"http://127.0.0.1:{port}/api/status")
        if health.get("reachable"):
            set_service_state("dashboard", url=f"http://127.0.0.1:{port}", port=port, pid=0, status="already_running")
            return {"success": True, "url": f"http://127.0.0.1:{port}", "port": port, "status": "already_running"}
        port = find_free_port(port + 1, 20)
        _log(f"Port {port - 1} busy, using {port}")

    api = FridayAPI(host="0.0.0.0", port=port)
    result = api.start()

    if "error" in result:
        return {"success": False, "error": result["error"]}

    set_service_state("dashboard",
        url=f"http://127.0.0.1:{port}",
        port=port,
        pid=_get_pid(),
        started_at=time.time(),
        status="running",
    )
    return {"success": True, "url": f"http://127.0.0.1:{port}", "port": port, "status": "started"}


# ─── Sidecar Heartbeat ──────────────────────────────────

_sidecar_heartbeat_thread: Optional[threading.Thread] = None


def _start_sidecar_heartbeat() -> dict:
    """Start the sidecar heartbeat in a daemon thread."""
    global _sidecar_heartbeat_thread

    def _heartbeat_loop():
        while True:
            try:
                from friday.sidecar import sidecar_tool
                sidecar_tool("heartbeat")
            except Exception:
                pass
            time.sleep(30)

    _sidecar_heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _sidecar_heartbeat_thread.start()
    set_service_state("sidecar_heartbeat", status="running", pid=_get_pid())
    return {"success": True, "status": "started"}


# ─── Memory Check ───────────────────────────────────────

def _run_memory_check() -> dict:
    """Check that memory/profile is loaded. Returns structured result."""
    profile_path = os.path.join(FRIDAY_MEMORY, "user_profile.json")
    memory_tree_path = os.path.join(FRIDAY_MEMORY, "memory_tree")

    profile_exists = os.path.exists(profile_path)
    memory_tree_exists = os.path.exists(memory_tree_path)

    status = "loaded" if profile_exists else "no_profile"
    set_service_state("memory", status=status, profile_exists=profile_exists, memory_tree_exists=memory_tree_exists)

    return {
        "success": True,
        "profile_exists": profile_exists,
        "memory_tree_exists": memory_tree_exists,
        "status": status,
    }


def bootstrap_configs(log_fn=None):
    """Ensure FRIDAY_CONFIG directory and default config files are initialized."""
    log = log_fn or _log
    from friday._paths import FRIDAY_CONFIG
    import json
    import os

    log("[INIT] Checking configuration directory...")
    os.makedirs(FRIDAY_CONFIG, exist_ok=True)
    
    # model_router.json
    router_path = os.path.join(FRIDAY_CONFIG, "model_router.json")
    if not os.path.exists(router_path):
        from friday.model_router import DEFAULT_CONFIG
        with open(router_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        log("[OK] Initialized default model_router.json")

    # extension_registry.json
    ext_path = os.path.join(FRIDAY_CONFIG, "extension_registry.json")
    if not os.path.exists(ext_path):
        default_ext = {"extensions": {}, "mcp_servers": {}, "version": 1}
        with open(ext_path, "w") as f:
            json.dump(default_ext, f, indent=2)
        log("[OK] Initialized default extension_registry.json")

    # autonomy.json
    autonomy_path = os.path.join(FRIDAY_CONFIG, "autonomy.json")
    if not os.path.exists(autonomy_path):
        default_autonomy = {"autonomy_level": "high", "version": 1}
        with open(autonomy_path, "w") as f:
            json.dump(default_autonomy, f, indent=2)
        log("[OK] Initialized default autonomy.json")


# ─── Full Launch ────────────────────────────────────────

def launch_all(dashboard_port: int = 7070,
               start_live: bool = False, start_sidecar_ws: bool = False,
               log_fn=None) -> Dict[str, Any]:
    """
    Launch all background services in the current process.

    Args:
        dashboard_port: Port for the FastAPI server (React dashboard + REST API)
        start_live: If True, also start the live engine (blocks)
        start_sidecar_ws: If True, start the sidecar WebSocket server
        log_fn: Optional logging function

    Returns:
        Dict with status of each service
    """
    if log_fn:
        global _log
        _log = log_fn

    results: Dict[str, Any] = {}

    _log("Starting FRIDAY services...")

    # Initialize configuration files if they are missing
    bootstrap_configs(log_fn=_log)

    # 1. Memory check
    _log("[CHECK] Memory...")
    mem_result = _run_memory_check()
    results["memory"] = mem_result
    if mem_result.get("profile_exists"):
        _log(f"[OK] Memory loaded: {FRIDAY_MEMORY}")
    else:
        _log(f"[WARN] No user profile at {FRIDAY_MEMORY}/user_profile.json")

    # 2. Dashboard (FastAPI + React)
    _log("[START] Dashboard...")
    dash_result = _start_dashboard(port=dashboard_port)
    results["dashboard"] = dash_result
    if dash_result.get("success"):
        _log(f"[OK] Dashboard: {dash_result['url']}")
    else:
        _log(f"[FAIL] Dashboard: {dash_result.get('error', 'unknown')}")

    # 3. Sidecar heartbeat
    _log("[START] Sidecar heartbeat...")
    sc_result = _start_sidecar_heartbeat()
    results["sidecar_heartbeat"] = sc_result
    if sc_result.get("success"):
        _log("[OK] Sidecar heartbeat running")
    else:
        _log(f"[FAIL] Sidecar heartbeat: {sc_result.get('error', 'unknown')}")

    # 4. Scheduler
    _log("[START] Scheduler...")
    try:
        from friday.scheduler import scheduler_tool
        scheduler_status = scheduler_tool("start")
        set_service_state("scheduler", status="running", pid=_get_pid())
        results["scheduler"] = {"success": True, "message": scheduler_status}
        _log("[OK] Scheduler running")
    except Exception as e:
        results["scheduler"] = {"success": False, "error": str(e)}
        _log(f"[WARN] Scheduler failed to start: {e}")

    # 5. Sidecar WebSocket server (optional)
    if start_sidecar_ws:
        try:
            from friday.sidecar_network import start_ws_server
            ws_started = start_ws_server()
            results["sidecar_ws"] = {"success": ws_started}
            if ws_started:
                _log("[OK] Sidecar WebSocket server running on port 42070")
            else:
                _log("[WARN] Sidecar WebSocket server not available (install websockets)")
        except Exception as e:
            _log(f"[WARN] Sidecar WebSocket: {e}")
            results["sidecar_ws"] = {"success": False, "error": str(e)}

    # 6. Camera manager + proactive monitor (optional, guarded by config)
    try:
        from friday.orchestration_config import ensure_config
        cam_cfg = ensure_config().get("camera", {})
        if cam_cfg.get("enabled", False):
            try:
                from friday.camera_manager import CameraManager
                cam_manager = CameraManager()
                cam_manager.start()
                set_service_state("camera_manager", status="running", pid=_get_pid())
                results["camera_manager"] = {"success": True}
            except Exception as e:
                _log(f"[WARN] Camera manager failed to start: {e}")
                results["camera_manager"] = {"success": False, "error": str(e)}

            try:
                from friday.proactive_monitor import ProactiveMonitor

                def _monitor_thread_target():
                    try:
                        import asyncio
                        monitor = ProactiveMonitor()
                        asyncio.run(monitor.run())
                    except Exception:
                        pass

                t = threading.Thread(target=_monitor_thread_target, name="FridayProactiveMonitor", daemon=True)
                t.start()
                set_service_state("proactive_monitor", status="running", pid=_get_pid())
                results["proactive_monitor"] = {"success": True}
            except Exception as e:
                _log(f"[WARN] Proactive monitor failed to start: {e}")
                results["proactive_monitor"] = {"success": False, "error": str(e)}
        else:
            results["camera_manager"] = {"success": False, "reason": "disabled"}
            results["proactive_monitor"] = {"success": False, "reason": "disabled"}
    except Exception as e:
        _log(f"[WARN] Camera startup: {e}")
        results["camera_manager"] = {"success": False, "error": str(e)}

    # Print summary
    _log("")
    _log("=" * 50)
    _log("FRIDAY is running")
    if dash_result.get("success"):
        _log(f"  Dashboard:  {dash_result['url']}")
    if results.get("sidecar_ws", {}).get("success"):
        _log("  Sidecar WS:    ws://127.0.0.1:42070")
    _log("  Say 'FRIDAY' to activate voice (if live engine started)")
    _log("=" * 50)
    _log("")

    # 7. Live engine (optional, blocks)
    if start_live:
        _log("[START] Live engine...")
        try:
            import asyncio
            from friday.live import friday_live_engine
            asyncio.run(friday_live_engine())
        except KeyboardInterrupt:
            _log("Shutting down...")
        except Exception as e:
            _log(f"[FAIL] Live engine: {e}")
        results["live_engine"] = {"success": True, "status": "stopped"}

    return results


def launch_dashboard_background() -> bool:
    """Start the dashboard in the current process thread. Returns True on success."""
    results = launch_all(dashboard_port=7070, start_live=False)
    return bool(results.get("dashboard", {}).get("success", False))


def launch_all_background_services() -> dict:
    """Return dict of service name → bool."""
    results = launch_all(dashboard_port=7070, start_live=False)
    return {
        "dashboard": results.get("dashboard", {}).get("success", False),
        "sidecar": results.get("sidecar_heartbeat", {}).get("success", False),
    }
