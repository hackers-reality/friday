"""
FRIDAY Startup — supervisor for background services.

Launches Dashboard API, Dashboard UI, sidecar heartbeat, memory checks,
and the live engine. All services are tracked via runtime_state.json
so they survive process boundaries.
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


# ─── Dashboard API ──────────────────────────────────────

def _start_dashboard_api(host: str = "127.0.0.1", port: int = 8090) -> dict:
    """Start the Dashboard API server. Returns structured result."""
    from friday.dashboard_api import DashboardAPI

    # Check if port is in use — could be our own from a previous launch
    port_check = check_port_open(host, port)
    if port_check["open"]:
        # Check if it's a healthy FRIDAY API
        health = check_http_endpoint(f"http://{host}:{port}/api/health")
        if health.get("reachable"):
            set_service_state("dashboard_api", url=f"http://{host}:{port}", port=port, pid=0, status="already_running")
            return {"success": True, "url": f"http://{host}:{port}", "port": port, "status": "already_running"}
        # Port is occupied but not FRIDAY — find a free one
        port = find_free_port(8091, 20)
        _log(f"Port 8090 busy, using {port}")

    api = DashboardAPI(host=host, port=port)
    result = api.start()

    if "error" in result:
        return {"success": False, "error": result["error"]}

    # Store in runtime state
    set_service_state("dashboard_api",
        url=result.get("url", f"http://{host}:{port}"),
        port=port,
        pid=_get_pid(),
        started_at=time.time(),
        status="running",
    )
    return {"success": True, "url": f"http://{host}:{port}", "port": port, "status": "started"}


def _stop_dashboard_api() -> dict:
    """Stop the Dashboard API server."""
    from friday.dashboard_api import DashboardAPI
    # We can't import the module's _dashboard_instance from here.
    # Instead, we check runtime state for services that need stopping.
    # Since DashboardAPI runs in this process's thread, we manage via module var.
    return {"success": True, "message": "Dashboard API will stop when supervisor exits"}


# ─── Dashboard UI ───────────────────────────────────────

def _start_dashboard_ui(api_url: str = "http://127.0.0.1:8090", host: str = "127.0.0.1", port: int = 8080) -> dict:
    """Start the HTML Dashboard server. Returns structured result."""
    from friday.dashboard import DashboardServer

    port_check = check_port_open(host, port)
    if port_check["open"]:
        # Check if a FRIDAY dashboard is already serving
        health = check_http_endpoint(f"http://{host}:{port}/")
        if health.get("reachable"):
            set_service_state("dashboard_ui", url=f"http://{host}:{port}", port=port, pid=0, status="already_running")
            return {"success": True, "url": f"http://{host}:{port}", "port": port, "status": "already_running"}
        port = find_free_port(8081, 20)
        _log(f"Port 8080 busy, using {port}")

    ds = DashboardServer(port=port)
    result = ds.start()
    if "error" in result:
        return {"success": False, "error": result.get("error", "Unknown error")}

    set_service_state("dashboard_ui",
        url=result.get("url", f"http://{host}:{port}"),
        port=port,
        pid=_get_pid(),
        started_at=time.time(),
        api_url=api_url,
        status="running",
    )
    return {"success": True, "url": result.get("url", f"http://{host}:{port}"), "port": port, "status": "started"}


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


# ─── Full Launch ────────────────────────────────────────

def launch_all(api_port: int = 8090, ui_port: int = 8080,
               start_live: bool = False, start_sidecar_ws: bool = False,
               log_fn=None) -> Dict[str, Any]:
    """
    Launch all background services in the current process.

    Args:
        api_port: Preferred port for dashboard API
        ui_port: Preferred port for dashboard UI
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

    # 1. Memory check
    _log("[CHECK] Memory...")
    mem_result = _run_memory_check()
    results["memory"] = mem_result
    if mem_result.get("profile_exists"):
        _log(f"[OK] Memory loaded: {FRIDAY_MEMORY}")
    else:
        _log(f"[WARN] No user profile at {FRIDAY_MEMORY}/user_profile.json")

    # 2. Dashboard API
    _log("[START] Dashboard API...")
    api_result = _start_dashboard_api(port=api_port)
    results["dashboard_api"] = api_result
    if api_result.get("success"):
        _log(f"[OK] Dashboard API: {api_result['url']}")
    else:
        _log(f"[FAIL] Dashboard API: {api_result.get('error', 'unknown')}")

    # 3. Dashboard UI
    api_url = api_result.get("url", f"http://127.0.0.1:{api_port}")
    _log("[START] Dashboard UI...")
    ui_result = _start_dashboard_ui(api_url=api_url, port=ui_port)
    results["dashboard_ui"] = ui_result
    if ui_result.get("success"):
        _log(f"[OK] Dashboard UI: {ui_result['url']}")
    else:
        _log(f"[FAIL] Dashboard UI: {ui_result.get('error', 'unknown')}")

    # 4. Sidecar heartbeat
    _log("[START] Sidecar heartbeat...")
    sc_result = _start_sidecar_heartbeat()
    results["sidecar_heartbeat"] = sc_result
    if sc_result.get("success"):
        _log("[OK] Sidecar heartbeat running")
    else:
        _log(f"[FAIL] Sidecar heartbeat: {sc_result.get('error', 'unknown')}")

    # 4.5 Scheduler
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
    if ui_result.get("success"):
        _log(f"  Dashboard UI:  {ui_result['url']}")
    if api_result.get("success"):
        _log(f"  Dashboard API: {api_result['url']}")
    if results.get("sidecar_ws", {}).get("success"):
        _log("  Sidecar WS:    ws://127.0.0.1:42070")
    _log("  Say 'FRIDAY' to activate voice (if live engine started)")
    _log("=" * 50)
    _log("")

    # 5. Live engine (optional, blocks)
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
    """Legacy: start API + UI in this process thread. Returns True on success."""
    results = launch_all(api_port=8090, ui_port=8080, start_live=False)
    api_ok = results.get("dashboard_api", {}).get("success", False)
    ui_ok = results.get("dashboard_ui", {}).get("success", False)
    return api_ok or ui_ok


def launch_all_background_services() -> dict:
    """Legacy: return dict of service name → bool."""
    results = launch_all(api_port=8090, ui_port=8080, start_live=False)
    return {
        "dashboard": results.get("dashboard_api", {}).get("success", False) or results.get("dashboard_ui", {}).get("success", False),
        "sidecar": results.get("sidecar_heartbeat", {}).get("success", False),
    }
