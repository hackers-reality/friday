"""
Friday Dashboard API — RESTful API for monitoring and controlling FRIDAY.

Provides all requested endpoints for the dashboard frontend.
Uses Flask (preferred) or falls back to http.server.
Designed to be run standalone or imported into the main Friday loop.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import json
import os
import sys
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from friday._paths import FRIDAY_MEMORY

_DASHBOARD_PORT = 8090
_DASHBOARD_HOST = "127.0.0.1"

# ─── Health / State ────────────────────────────────────────


def _get_health() -> dict:
    """Basic health check."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime_seconds": int(time.time() - _get_start_time()),
    }


_start_time: float = 0


def _get_start_time() -> float:
    global _start_time
    if _start_time == 0:
        _start_time = time.time()
    return _start_time


def _get_state() -> dict:
    """Get FRIDAY's current operational state."""
    state: dict = {
        "status": "running",
        "mode": "auto",
        "session_active": False,
        "memory_loaded": False,
        "tools_available": 0,
        "last_activity": "",
    }
    try:
        from friday.authority import load_authority_policy
        policy = load_authority_policy()
        state["mode"] = policy.get("mode", "auto")
    except Exception:
        pass
    try:
        state["memory_loaded"] = bool(
            os.path.exists(os.path.join(FRIDAY_MEMORY, "user_profile.json"))
        )
    except Exception:
        pass
    try:
        from friday.tool_registry import TOOL_META
        state["tools_available"] = len(TOOL_META)
    except Exception:
        pass
    return state


def _get_tools() -> dict:
    """Get tool registry summary."""
    try:
        from friday.tool_registry import list_tool_registry
        grouped = list_tool_registry()
        total = sum(len(v) for v in grouped.values())
        return {"total": total, "categories": {k: len(v) for k, v in grouped.items()}}
    except Exception as e:
        return {"error": str(e)}


def _get_tasks() -> dict:
    """Get autonomy task summary."""
    try:
        from friday.autonomy import list_tasks, task_summary
        tasks = list_tasks(limit=20)
        return {
            "total": len(tasks),
            "recent": [
                {"id": t.get("id"), "description": t.get("description", "")[:60],
                 "status": t.get("status"), "created": t.get("created_at", "")[:19]}
                for t in tasks[:10]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _get_memory_status() -> dict:
    """Get memory subsystem status."""
    status: dict = {
        "profile_exists": False,
        "profile_version": 0,
        "profile_size_bytes": 0,
        "audit_count": 0,
        "confidence_scalar_fields": 0,
        "confidence_list_items": 0,
        "pinned_items": 0,
        "review_queue_size": 0,
        "vector_available": False,
        "episodic_available": False,
        "last_updated": "",
    }
    try:
        from friday.memory_import import load_profile
        profile = load_profile()
        if profile and profile.get("version", 0) >= 1:
            status["profile_exists"] = True
            status["profile_version"] = profile.get("version", 0)
            status["profile_size_bytes"] = len(json.dumps(profile, indent=2))
            status["audit_count"] = len(profile.get("audits", []))
            status["last_updated"] = profile.get("last_updated", "")
            conf = profile.get("_confidence", {})
            scalar_count = sum(1 for v in conf.values() if isinstance(v, (int, float)))
            list_count = sum(len(v) for v in conf.values() if isinstance(v, dict))
            status["confidence_scalar_fields"] = scalar_count
            status["confidence_list_items"] = list_count
            status["pinned_items"] = len(profile.get("_pinned", []))
            from friday.memory_import import build_memory_review_queue
            status["review_queue_size"] = len(build_memory_review_queue(profile))
    except Exception:
        pass
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        status["vector_available"] = vm.is_available() if hasattr(vm, "is_available") else False
    except Exception:
        pass
    try:
        from friday.episodic import get_episodic_memory
        em = get_episodic_memory()
        status["episodic_available"] = True
    except Exception:
        pass
    return status


def _get_memory_doctor() -> dict:
    """Get doctor report as structured data."""
    try:
        from friday.memory_import import memory_import_tool
        report_text = memory_import_tool("doctor")
        # Parse into structured sections
        sections = {}
        current_section = "header"
        sections["header"] = report_text[:200]
        for line in report_text.split("\n"):
            line_s = line.strip()
            if line_s.startswith("[OK]") or line_s.startswith("[ISSUE]") or line_s.startswith("[WARN]") or line_s.startswith("[CONFLICT]") or line_s.startswith("[DECAY]") or line_s.startswith("[REVIEW]"):
                sections.setdefault("findings", []).append(line_s)
            elif "Validation" in line_s:
                current_section = "validation"
            elif "Conflict" in line_s:
                current_section = "conflicts"
            elif "Decay" in line_s:
                current_section = "decay"
            elif "Review" in line_s:
                current_section = "review"
        return {"report": report_text, "sections": sections, "findings_count": len(sections.get("findings", []))}
    except Exception as e:
        return {"error": str(e)}


def _get_memory_review() -> list:
    """Get review queue items."""
    try:
        from friday.memory_import import load_profile, build_memory_review_queue
        profile = load_profile()
        queue = build_memory_review_queue(profile)
        return queue[:30]
    except Exception:
        return []


def _get_authority() -> dict:
    """Get authority status."""
    try:
        from friday.authority import load_authority_policy, should_allow_tool
        policy = load_authority_policy()
        return {
            "mode": policy.get("mode", "auto"),
            "max_risk_level": policy.get("max_risk_level", 2),
            "blocked_tools": policy.get("blocked_tools", []),
            "require_approval": policy.get("require_approval_tools", []),
            "snapshot_before_destructive": policy.get("snapshot_before_destructive", True),
        }
    except Exception as e:
        return {"error": str(e)}


def _get_snapshots() -> dict:
    """Get snapshot summary."""
    try:
        from friday.snapshots import list_snapshots
        snaps = list_snapshots(limit=20)
        return {
            "total": len(snaps),
            "recent": [
                {"id": s.get("id"), "label": s.get("label", ""), "type": s.get("type", ""),
                 "timestamp": s.get("timestamp", "")[:19]}
                for s in snaps[:10]
            ],
        }
    except Exception:
        return {"total": 0, "recent": []}


def _get_sidecars() -> dict:
    """Get sidecar summary."""
    try:
        from friday.sidecar import list_sidecars
        sc = list_sidecars()
        return {
            "total": len(sc),
            "sidecars": [
                {"id": s.get("id"), "name": s.get("name"), "type": s.get("type"),
                 "status": s.get("status"), "last_hb": (s.get("last_heartbeat") or "")[:19]}
                for s in sc[:20]
            ],
        }
    except Exception:
        return {"total": 0, "sidecars": []}


def _get_goals() -> dict:
    """Get goals/productivity summary."""
    try:
        from friday.goals import goals_tool
        # Try to use the goals tool to get data
        return {"info": "Goals subsystem available"}
    except Exception:
        return {"info": "Goals module not loaded"}


def _get_system() -> dict:
    """Get system health info."""
    import psutil
    info = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        "process_count": len(psutil.pids()),
    }
    return info


def _get_logs_recent(limit: int = 50) -> list:
    """Get recent tool log entries."""
    log_file = os.path.join(FRIDAY_MEMORY, "tool_log.jsonl")
    entries = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
            for line in lines[-limit:]:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        entries.append({"raw": line.strip()[:200]})
        except Exception:
            pass
    return entries


def _get_capabilities() -> dict:
    """Get capability matrix summary."""
    try:
        from friday.capabilities import CAPABILITIES
        by_status = {}
        for name, info in CAPABILITIES.items():
            s = info.get("status", "planned")
            by_status.setdefault(s, []).append(name)
        return {
            "total": len(CAPABILITIES),
            "by_status": {k: len(v) for k, v in by_status.items()},
        }
    except Exception as e:
        return {"error": str(e)}


def _get_mission() -> dict:
    """Get current mission/objective."""
    manifest = os.path.join(os.path.dirname(os.path.dirname(__file__)), "FRIDAY_MANIFEST.md")
    mission = "Personal AI OS assistant - Iron Man inspired"
    if os.path.exists(manifest):
        try:
            with open(manifest, "r") as f:
                content = f.read()
            for line in content.split("\n")[:5]:
                if line.startswith("#") and "FRIDAY" in line.upper():
                    mission = line.lstrip("# ").strip()
                    break
        except Exception:
            pass
    return {"mission": mission}


def _get_briefing() -> dict:
    """Get proactive briefing data."""
    try:
        memory_status = _get_memory_status()
        system = _get_system()
        tasks = _get_tasks()
        return {
            "memory_ok": memory_status.get("profile_exists", False),
            "system_ok": system.get("cpu_percent", 0) < 80 if system else True,
            "pending_tasks": tasks.get("total", 0) if isinstance(tasks, dict) else 0,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return {"error": "Briefing unavailable"}


def _get_workspace() -> dict:
    """Get workspace info."""
    ws = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    info = {
        "path": ws,
        "modules_count": 0,
        "test_files": [],
    }
    try:
        friday_dir = os.path.join(ws, "friday")
        if os.path.isdir(friday_dir):
            info["modules_count"] = len([f for f in os.listdir(friday_dir) if f.endswith(".py")])
        test_dir = ws
        if os.path.isdir(test_dir):
            info["test_files"] = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    except Exception:
        pass
    return info


def _get_diagnostic() -> dict:
    """Comprehensive FRIDAY diagnostic."""
    diagnostic = {
        "timestamp": datetime.now().isoformat(),
        "systems": {},
    }
    # Health
    diagnostic["systems"]["health"] = _get_health()
    # State
    diagnostic["systems"]["state"] = _get_state()
    # Memory
    diagnostic["systems"]["memory"] = _get_memory_status()
    # Authority
    diagnostic["systems"]["authority"] = _get_authority()
    # Tools
    diagnostic["systems"]["tools"] = _get_tools()
    # Tasks
    diagnostic["systems"]["tasks"] = _get_tasks()
    # System
    diagnostic["systems"]["system"] = _get_system()
    # Capabilities
    diagnostic["systems"]["capabilities"] = _get_capabilities()
    # Workspace
    diagnostic["systems"]["workspace"] = _get_workspace()

    # Overall status
    all_ok = True
    for name, sys_data in diagnostic["systems"].items():
        if isinstance(sys_data, dict) and "error" in sys_data:
            all_ok = False
    diagnostic["all_systems_operational"] = all_ok
    diagnostic["system_count"] = len(diagnostic["systems"])
    return diagnostic


def _get_cv_context() -> dict:
    """Get CV engine context for dashboard."""
    try:
        from friday.cv_engine import get_cv_status
        return get_cv_status()
    except Exception as e:
        return {"error": str(e)}


def _get_agents() -> list:
    """Get all spawned agents and their status."""
    # Prefer orchestrator/registry status when available, fall back to agents_manager
    try:
        from friday.orchestrator import get_orchestrator
        from friday.agent_registry import get_registry
        orch = get_orchestrator()
        registry = get_registry()
        agents = []
        for profile in registry.list_all():
            status = orch.get_status(profile.agent_id)
            agents.append(
                {
                    "name": profile.display_name,
                    "id": profile.agent_id,
                    "tasks": profile.task_types,
                    "model": profile.nim_model,
                    "status": status.get("status", "idle"),
                    "current_task": status.get("current_task"),
                    "last_result": status.get("last_result"),
                    "last_seen": status.get("last_seen"),
                }
            )
        return agents
    except Exception:
        try:
            from friday.agents_manager import list_agents
            return list_agents()
        except Exception:
            return []


class _APIHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler for the dashboard API."""

    def _respond(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        body = json.dumps(data, default=str, indent=2)
        self.wfile.write(body.encode("utf-8"))

    def _respond_html(self, html: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_OPTIONS(self):
        self._respond({})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Read body
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception:
            self._respond({"error": "Invalid request"}, 400)
            return

        if path == "/api/sidecars/register":
            try:
                from friday.sidecar_network import handle_sidecar_registration
                result = handle_sidecar_registration(data)
                if "error" in result:
                    self._respond(result, 400)
                else:
                    self._respond(result)
            except Exception as e:
                self._respond({"error": str(e)}, 500)
        elif path == "/api/sidecars/heartbeat":
            name = data.get("name", "")
            status = data.get("status", "alive")
            if not name:
                self._respond({"error": "name required"}, 400)
                return
            try:
                from friday.sidecar import sidecar_tool
                result = sidecar_tool("heartbeat", id=name, status=status)
                self._respond({"success": True, "name": name, "status": status})
            except Exception as e:
                self._respond({"error": str(e)}, 500)
        elif path == "/api/agents/spawn":
            try:
                name = data.get("name", "")
                task = data.get("task", "")
                role = data.get("role", "general")
                if not name or not task:
                    self._respond({"error": "name and task required"}, 400)
                    return

                # Prefer orchestrator-backed delegation for configured agents
                try:
                    from friday.orchestrator import get_orchestrator, run_delegate_sync
                    from friday.agent_registry import get_registry
                    registry = get_registry()
                    # If the name matches a configured agent, delegate via orchestrator
                    profile = registry.get_by_id(name) or registry.get_by_name(name)
                    if profile:
                        result = run_delegate_sync(task, context={"requester": "dashboard", "role": role}, preferred_agent=profile.agent_id)
                        self._respond({"success": True, "via": "orchestrator", "result": result})
                        return
                except Exception:
                    # Fall through to legacy spawn if orchestrator not available
                    pass

                # Fallback: use legacy agents_manager spawn (opencode bridge)
                from friday.agents_manager import spawn_agent
                result = spawn_agent(name, task, role)
                self._respond(result)
            except Exception as e:
                self._respond({"error": str(e)}, 500)
        elif path == "/api/fix":
            try:
                from friday.diagnostics import run_diagnostics, run_fixes
                diag = run_diagnostics()
                result = run_fixes(diag)
                self._respond({"success": True, "fixes": result})
            except Exception as e:
                self._respond({"error": str(e)}, 500)
        else:
            self._respond({"error": f"Unknown POST endpoint: {path}"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        routes = {
            "/api/health": ("health", _get_health),
            "/api/state": ("state", _get_state),
            "/api/tools": ("tools", _get_tools),
            "/api/tasks": ("tasks", _get_tasks),
            "/api/memory/status": ("memory_status", _get_memory_status),
            "/api/memory/doctor": ("memory_doctor", _get_memory_doctor),
            "/api/memory/review": ("memory_review", _get_memory_review),
            "/api/authority": ("authority", _get_authority),
            "/api/snapshots": ("snapshots", _get_snapshots),
            "/api/sidecars": ("sidecars", _get_sidecars),
            "/api/goals": ("goals", _get_goals),
            "/api/system": ("system", _get_system),
            "/api/logs/recent": ("logs_recent", lambda: _get_logs_recent(50)),
            "/api/capabilities": ("capabilities", _get_capabilities),
            "/api/mission": ("mission", _get_mission),
            "/api/briefing": ("briefing", _get_briefing),
            "/api/workspace": ("workspace", _get_workspace),
            "/api/diagnostic": ("diagnostic", _get_diagnostic),
            "/api/cv": ("cv", _get_cv_context),
            "/api/agents": ("agents", lambda: {"agents": _get_agents()}),
        }

        if path == "/" or path == "":
            return self._respond_html(
                "<html><body><h1>FRIDAY Dashboard API</h1>"
                "<p>Available endpoints:</p><ul>"
                + "".join(f"<li><a href='{p}'>{p}</a></li>" for p in sorted(routes.keys()))
                + "</ul></body></html>"
            )

        if path in routes:
            name, handler = routes[path]
            try:
                result = handler()
                self._respond(result)
            except Exception as e:
                self._respond({"error": str(e)}, 500)
        elif path.startswith("/api/agents/"):
            # Support /api/agents/{id}/status or /api/agents/{id}
            parts = path.split("/")
            if len(parts) >= 4:
                agent_id = parts[3]
                try:
                    from friday.orchestrator import get_orchestrator
                    orch = get_orchestrator()
                    status = orch.get_status(agent_id)
                    self._respond({"agent_id": agent_id, "status": status})
                    return
                except Exception:
                    try:
                        from friday.agents_manager import agent_status
                        self._respond(agent_status(agent_id))
                        return
                    except Exception:
                        self._respond({"error": "Agent not found"}, 404)
                        return
        else:
            self._respond({"error": f"Unknown endpoint: {path}"}, 404)

    def log_message(self, format, *args):
        # Suppress default logging
        pass


# ─── Dashboard API Server ──────────────────────────────────


class DashboardAPI:
    """FRIDAY Dashboard API server."""

    def __init__(self, host: str = _DASHBOARD_HOST, port: int = _DASHBOARD_PORT):
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> dict:
        """Start the API server in a daemon thread."""
        try:
            self._server = HTTPServer((self.host, self.port), _APIHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            return {"success": True, "url": f"http://{self.host}:{self.port}", "port": self.port}
        except Exception as e:
            return {"error": str(e)}

    def stop(self):
        """Stop the API server and clean up socket."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            self._thread = None

    def is_running(self) -> bool:
        return self._server is not None


def dashboard_api_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool to manage the Dashboard API.
    Actions: status, start, stop.
    """
    global _dashboard_instance

    if action == "status":
        running = _dashboard_instance and _dashboard_instance.is_running()
        if running:
            return (
                f"### DASHBOARD API STATUS\n\n"
                f"Running: Yes\n"
                f"URL: http://{_dashboard_instance.host}:{_dashboard_instance.port}\n"
                f"Endpoints: /api/health, /api/state, /api/tools, /api/tasks, "
                f"/api/memory/status, /api/memory/doctor, /api/memory/review, "
                f"/api/authority, /api/snapshots, /api/sidecars, /api/goals, "
                f"/api/system, /api/logs/recent, /api/capabilities, /api/mission, "
                f"/api/briefing, /api/workspace"
            )
        return "### DASHBOARD API STATUS\n\nNot running."

    if action == "start":
        port = int(kwargs.get("port", _DASHBOARD_PORT))
        if _dashboard_instance and _dashboard_instance.is_running():
            return "[OK] Dashboard API already running."
        api = DashboardAPI(port=port)
        result = api.start()
        _dashboard_instance = api
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Dashboard API started at {result['url']}"

    if action == "stop":
        if _dashboard_instance and _dashboard_instance.is_running():
            _dashboard_instance.stop()
            return "[OK] Dashboard API stopped."
        return "[OK] Dashboard API was not running."

    return f"[FAIL] Unknown action: {action}. Available: status, start, stop"


_dashboard_instance: Optional[DashboardAPI] = None

# Auto-start the dashboard API if module is imported
# (commented out to avoid background thread on import)
# _dashboard_instance = DashboardAPI()
# _dashboard_instance.start()
