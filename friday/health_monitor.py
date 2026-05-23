"""
FRIDAY Unified Health Monitor — central hub that aggregates health data from all
subsystems (system monitor, diagnostics, browser, context bus, agents, etc.)

Publishes periodic snapshots to the context bus so that the AI agent, proactive
speaker, morning briefing builder, and terminal health display can all read from
one source of truth.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from friday._paths import FRIDAY_MEMORY

_HEALTH_STATE_FILE = os.path.join(FRIDAY_MEMORY, "health_state.json")


class HealthMonitor:
    """
    Singleton health monitor that aggregates component health.
    
    Components register a check function (returning dict with "status" key).
    The monitor runs all checks periodically and publishes to context_bus.
    """

    _instance: Optional[HealthMonitor] = None
    _lock = threading.Lock()

    def __init__(self):
        self._components: dict[str, dict] = {}
        self._statuses: dict[str, dict] = {}
        self._alerts: list[dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._start_time = time.time()
        self._check_interval = 30

    @classmethod
    def get_instance(cls) -> HealthMonitor:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Component Registration ─────────────────────────────────

    def register(self, name: str, check_fn: Callable[[], dict], interval: float = 60.0):
        """Register a component to be monitored.
        
        check_fn must return a dict with at minimum {"status": "ok"|"degraded"|"error"|"stopped"}
        """
        self._components[name] = {"fn": check_fn, "interval": interval}

    def unregister(self, name: str):
        self._components.pop(name, None)
        self._statuses.pop(name, None)

    # ── Lifecycle ───────────────────────────────────────────────

    def start(self, interval: float = 30.0):
        if self._running:
            return
        self._check_interval = interval
        self._running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._running = False
        self._save_state()

    def _run_loop(self):
        while not self._stop.is_set():
            try:
                self._check_all()
                self._publish()
                self._save_state()
            except Exception:
                pass
            self._stop.wait(self._check_interval)

    # ── Checks ──────────────────────────────────────────────────

    def _check_all(self):
        for name, comp in list(self._components.items()):
            try:
                result = comp["fn"]()
                if not isinstance(result, dict):
                    result = {"status": "unknown", "detail": str(result)}
                if "status" not in result:
                    result["status"] = "unknown"
                result["last_check"] = datetime.now().isoformat()
                self._statuses[name] = result
            except Exception as e:
                self._statuses[name] = {"status": "error", "detail": str(e), "last_check": datetime.now().isoformat()}

    # ── Alerts ──────────────────────────────────────────────────

    def add_alert(self, severity: str, source: str, message: str):
        alert = {
            "severity": severity,
            "source": source,
            "message": message,
            "time": datetime.now().isoformat(),
        }
        self._alerts.append(alert)
        self._alerts = self._alerts[-50:]

    def recent_alerts(self, limit: int = 10) -> list[dict]:
        return self._alerts[-limit:]

    # ── Snapshot ────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Return a complete health snapshot."""
        uptime = time.time() - self._start_time
        statuses = dict(self._statuses)
        overall = self._overall_status(statuses)
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "uptime_human": self._format_uptime(uptime),
            "overall": overall,
            "components": statuses,
            "alerts": self.recent_alerts(10),
            "monitored_count": len(self._components),
        }

    def _overall_status(self, statuses: dict) -> str:
        if not statuses:
            return "starting"
        errors = sum(1 for s in statuses.values() if s.get("status") in ("error", "fail", "critical"))
        degraded = sum(1 for s in statuses.values() if s.get("status") == "degraded")
        if errors:
            return "critical" if errors > 1 else "degraded"
        if degraded:
            return "degraded"
        return "healthy"

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m {secs}s"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    # ── Publish to Context Bus ──────────────────────────────────

    def _publish(self):
        try:
            snap = self.snapshot()
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._async_publish(snap))
                else:
                    loop.run_until_complete(self._async_publish(snap))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._async_publish(snap))
                loop.close()
        except Exception:
            pass

    async def _async_publish(self, snap: dict):
        try:
            from friday.context_bus import get_bus
            await get_bus().publish("system.health_snapshot", snap)
        except Exception:
            pass

    # ── Persistence ─────────────────────────────────────────────

    def _save_state(self):
        try:
            data = {
                "statuses": self._statuses,
                "alerts": self._alerts[-50:],
                "last_update": datetime.now().isoformat(),
                "uptime": time.time() - self._start_time,
            }
            os.makedirs(os.path.dirname(_HEALTH_STATE_FILE), exist_ok=True)
            with open(_HEALTH_STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def load_saved_state(cls) -> dict:
        if os.path.exists(_HEALTH_STATE_FILE):
            try:
                with open(_HEALTH_STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    # ── Status for display ──────────────────────────────────────

    def component_status(self, name: str) -> str:
        comp = self._statuses.get(name, {})
        return comp.get("status", "unknown")

    def is_healthy(self) -> bool:
        return self._overall_status(self._statuses) == "healthy"


# ── Singleton Accessor ─────────────────────────────────────────

def get_health_monitor() -> HealthMonitor:
    return HealthMonitor.get_instance()


# ── Bundled Check Functions ────────────────────────────────────

def check_system_resources() -> dict:
    """Check CPU, memory, disk."""
    result = {"status": "ok", "checks": {}}
    try:
        from friday.system_monitor import get_cpu_usage, get_memory_usage
        cpu = get_cpu_usage()
        mem = get_memory_usage()
        result["checks"]["cpu"] = f"{cpu:.0f}%"
        result["checks"]["memory"] = f"{mem.get('percent', 0)}%"
        if cpu > 90:
            result["status"] = "degraded"
            result["detail"] = f"High CPU: {cpu:.0f}%"
        elif mem.get("percent", 0) > 90:
            result["status"] = "degraded"
            result["detail"] = f"High memory: {mem.get('percent', 0)}%"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_browser() -> dict:
    """Check browser_manager health."""
    try:
        from friday.browser_manager import BrowserManager
        bm = BrowserManager.get_instance()
        return bm.health_check()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_context_bus() -> dict:
    """Check context bus health."""
    try:
        from friday.context_bus import get_bus
        bus = get_bus()
        snap = bus.status_snapshot()
        return {"status": "ok", "detail": f"{snap['subscriptions']} subscribers, {snap['history_size']} events"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_disk_space() -> dict:
    """Check available disk space."""
    try:
        import shutil
        total, used, free = shutil.disk_usage(os.path.dirname(FRIDAY_MEMORY) if os.path.exists(FRIDAY_MEMORY) else ".")
        free_gb = free // (1024 ** 3)
        if free_gb < 1:
            return {"status": "critical", "detail": f"Only {free_gb}GB free!"}
        if free_gb < 5:
            return {"status": "degraded", "detail": f"{free_gb}GB free"}
        return {"status": "ok", "detail": f"{free_gb}GB free"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_active_monitors() -> dict:
    """Check if proactive monitors are running."""
    details = []
    try:
        from friday.monitor import _monitor_thread, _load_state
        sys_mon_running = _monitor_thread is not None and _monitor_thread.is_alive()
        details.append(f"system: {'running' if sys_mon_running else 'idle'}")
    except Exception:
        details.append("system: unavailable")
    try:
        from friday.proactivity_monitor import get_proactive_monitor
        pm = get_proactive_monitor()
        details.append(f"screen: {'running' if pm._thread and pm._thread.is_alive() else 'idle'}")
    except Exception:
        details.append("screen: unavailable")
    status = "ok" if any("running" in d for d in details) else "degraded"
    return {"status": status, "detail": ", ".join(details)}


# ─── Register Default Components ──────────────────────────────

def register_default_checks(health: HealthMonitor):
    """Register all built-in health checks."""
    health.register("system_resources", check_system_resources, interval=30)
    health.register("browser", check_browser, interval=60)
    health.register("context_bus", check_context_bus, interval=60)
    health.register("disk_space", check_disk_space, interval=120)
    health.register("active_monitors", check_active_monitors, interval=60)


# ─── Tool Function ────────────────────────────────────────────

def health_monitor_tool(action: str = "status") -> str:
    """Unified health monitor: check status of all FRIDAY subsystems.
    
    Actions:
        status         - Show overall health snapshot
        alerts         - Show recent alerts
        components     - List registered components
        refresh        - Force immediate check of all components
    """
    hm = get_health_monitor()

    if action == "status":
        snap = hm.snapshot()
        lines = [
            "=" * 60,
            "  FRIDAY HEALTH DASHBOARD",
            f"  {snap['timestamp']}",
            f"  Uptime: {snap['uptime_human']}",
            f"  Overall: {snap['overall'].upper()}",
            f"  Components monitored: {snap['monitored_count']}",
            "-" * 60,
        ]
        for name, status in snap["components"].items():
            st = status.get("status", "?").upper()
            detail = status.get("detail", "")
            icon = {"OK": "[OK]", "DEGRADED": "[WARN]", "ERROR": "[FAIL]", "CRITICAL": "[CRIT]", "STOPPED": "[STOP]"}.get(st, "[?]")
            lines.append(f"  {icon} {name}: {st}  {detail}")
        if snap["alerts"]:
            lines.append("-" * 60)
            lines.append("  RECENT ALERTS:")
            for a in snap["alerts"][-5:]:
                ts = a.get("time", "?")[11:19] if len(a.get("time", "")) > 19 else a.get("time", "?")
                lines.append(f"    [{ts}] [{a.get('severity','info').upper()}] {a.get('source','?')}: {a.get('message','')}")
        lines.append("=" * 60)
        return "\n".join(lines)

    elif action == "alerts":
        alerts = hm.recent_alerts()
        if not alerts:
            return "No alerts recorded."
        lines = ["### RECENT HEALTH ALERTS"]
        for a in alerts:
            ts = a.get("time", "?")[11:19] if len(a.get("time", "")) > 19 else a.get("time", "?")
            lines.append(f"  [{ts}] [{a.get('severity','').upper()}] {a.get('source','')}: {a.get('message','')}")
        return "\n".join(lines)

    elif action == "components":
        if not hm._components:
            return "No components registered."
        lines = ["### REGISTERED COMPONENTS"]
        for name in hm._components:
            status = hm._statuses.get(name, {}).get("status", "unknown")
            lines.append(f"  {name}: {status}")
        return "\n".join(lines)

    elif action == "refresh":
        hm._check_all()
        snap = hm.snapshot()
        return f"[OK] Health check refreshed. Overall status: {snap['overall']}"

    return f"[FAIL] Unknown action: {action}"
