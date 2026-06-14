"""FRIDAY Health Monitor — service health tracking, alerts, and auto-recovery."""
import os
import json
import time
import uuid
import threading
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from datetime import datetime


@dataclass
class HealthCheck:
    name: str
    check_type: str
    target: str = ""
    interval: int = 30
    timeout: int = 10
    enabled: bool = True
    last_check: float = 0.0
    last_status: str = "unknown"
    last_response_time: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    config: Dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class Alert:
    alert_id: str
    name: str
    severity: str
    message: str
    source: str
    timestamp: float
    resolved: bool = False
    resolved_at: float = 0.0
    acknowledged: bool = False
    acknowledged_by: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class HealthSnapshot:
    timestamp: float
    checks: Dict[str, str]
    metrics: Dict[str, float]
    alerts: List[Dict]
    overall_status: str

    def to_dict(self):
        return asdict(self)


class HealthChecker:
    @staticmethod
    def check_process(name: str = "python", **kwargs) -> Dict:
        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                if name.lower() in proc.info["name"].lower():
                    return {
                        "status": "healthy",
                        "pid": proc.info["pid"],
                        "cpu": proc.info["cpu_percent"],
                        "memory": proc.info["memory_percent"],
                    }
            return {"status": "warning", "message": f"Process '{name}' not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_port(host: str = "localhost", port: int = 8000, **kwargs) -> Dict:
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return {"status": "healthy", "host": host, "port": port}
            return {"status": "error", "message": f"Port {port} not reachable"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_disk(threshold: float = 90, path: str = "/", **kwargs) -> Dict:
        try:
            usage = psutil.disk_usage(path)
            percent = usage.percent
            status = "healthy" if percent < threshold else "error"
            if percent >= threshold * 0.8:
                status = "warning"
            return {
                "status": status,
                "percent": percent,
                "total_gb": round(usage.total / 1024**3, 2),
                "used_gb": round(usage.used / 1024**3, 2),
                "free_gb": round(usage.free / 1024**3, 2),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_memory(threshold: float = 90, **kwargs) -> Dict:
        try:
            mem = psutil.virtual_memory()
            percent = mem.percent
            status = "healthy" if percent < threshold else "error"
            if percent >= threshold * 0.8:
                status = "warning"
            return {
                "status": status,
                "percent": percent,
                "total_gb": round(mem.total / 1024**3, 2),
                "used_gb": round(mem.used / 1024**3, 2),
                "available_gb": round(mem.available / 1024**3, 2),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_cpu(threshold: float = 90, **kwargs) -> Dict:
        try:
            cpu = psutil.cpu_percent(interval=1)
            status = "healthy" if cpu < threshold else "error"
            if cpu >= threshold * 0.8:
                status = "warning"
            return {
                "status": status,
                "percent": cpu,
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_http(url: str = "http://localhost:8000", timeout: int = 10, **kwargs) -> Dict:
        import urllib.request
        try:
            start = time.time()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                duration = time.time() - start
                return {
                    "status": "healthy",
                    "url": url,
                    "status_code": resp.status,
                    "response_time_ms": round(duration * 1000, 2),
                }
        except Exception as e:
            return {"status": "error", "url": url, "message": str(e)}

    @staticmethod
    def check_file(path: str, **kwargs) -> Dict:
        try:
            exists = os.path.exists(path)
            if exists:
                stat = os.stat(path)
                return {
                    "status": "healthy",
                    "path": path,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            return {"status": "warning", "path": path, "message": "File not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def check_database(path: str = None, **kwargs) -> Dict:
        if path is None:
            path = os.path.join(os.path.expanduser("~"), ".friday", "memory", "friday_memory.db")
        try:
            if os.path.exists(path):
                size = os.path.getsize(path)
                return {"status": "healthy", "path": path, "size": size}
            return {"status": "warning", "path": path, "message": "Database not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    CHECKERS = {
        "process": check_process.__func__,
        "port": check_port.__func__,
        "disk": check_disk.__func__,
        "memory": check_memory.__func__,
        "cpu": check_cpu.__func__,
        "http": check_http.__func__,
        "file": check_file.__func__,
        "database": check_database.__func__,
    }


class HealthMonitor:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "health")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._checks: Dict[str, HealthCheck] = {}
        self._alerts: List[Alert] = []
        self._history: deque = deque(maxlen=1000)
        self._handlers: Dict[str, Callable] = {}
        self._alert_handlers: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._load_checks()
        self._load_alerts()
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            HealthCheck("cpu", "cpu", interval=30, config={"threshold": 90}),
            HealthCheck("memory", "memory", interval=30, config={"threshold": 90}),
            HealthCheck("disk", "disk", interval=60, config={"threshold": 90, "path": "/"}),
            HealthCheck("api_server", "port", interval=30, config={"host": "localhost", "port": 8000}),
        ]
        for check in defaults:
            if check.name not in self._checks:
                self._checks[check.name] = check

    def _checks_file(self) -> str:
        return os.path.join(self.data_dir, "checks.json")

    def _alerts_file(self) -> str:
        return os.path.join(self.data_dir, "alerts.json")

    def _load_checks(self):
        if os.path.exists(self._checks_file()):
            try:
                with open(self._checks_file(), "r") as f:
                    data = json.load(f)
                for name, cdata in data.items():
                    self._checks[name] = HealthCheck(**cdata)
            except Exception:
                pass

    def _save_checks(self):
        try:
            data = {name: c.to_dict() for name, c in self._checks.items()}
            with open(self._checks_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _load_alerts(self):
        if os.path.exists(self._alerts_file()):
            try:
                with open(self._alerts_file(), "r") as f:
                    data = json.load(f)
                self._alerts = [Alert(**a) for a in data[-500:]]
            except Exception:
                pass

    def _save_alerts(self):
        try:
            data = [a.to_dict() for a in self._alerts[-500:]]
            with open(self._alerts_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def add_check(self, check: HealthCheck):
        with self._lock:
            self._checks[check.name] = check
            self._save_checks()

    def remove_check(self, name: str) -> bool:
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                self._save_checks()
                return True
            return False

    def get_check(self, name: str) -> Optional[Dict]:
        check = self._checks.get(name)
        return check.to_dict() if check else None

    def list_checks(self) -> List[Dict]:
        with self._lock:
            return [c.to_dict() for c in self._checks.values()]

    def run_check(self, name: str) -> Dict:
        check = self._checks.get(name)
        if not check:
            return {"error": f"Check not found: {name}"}

        checker = HealthChecker.CHECKERS.get(check.check_type)
        if not checker:
            return {"error": f"Unknown check type: {check.check_type}"}

        start = time.time()
        result = checker(**check.config)
        duration = time.time() - start

        with self._lock:
            check.last_check = time.time()
            check.last_status = result.get("status", "unknown")
            check.last_response_time = duration
            if result.get("status") in ("error", "warning"):
                check.failure_count += 1
            else:
                check.success_count += 1
                check.failure_count = max(0, check.failure_count - 1)
            self._save_checks()

        if result.get("status") == "error":
            self._create_alert(
                name=f"health_{name}",
                severity="high" if check.failure_count >= 3 else "medium",
                message=f"Health check '{name}' failed: {result.get('message', 'unknown')}",
                source=name,
            )
        elif result.get("status") == "warning":
            self._create_alert(
                name=f"health_{name}_warning",
                severity="low",
                message=f"Health check '{name}' warning: {result.get('message', 'threshold exceeded')}",
                source=name,
            )

        return result

    def run_all_checks(self) -> Dict[str, Dict]:
        results = {}
        with self._lock:
            check_names = list(self._checks.keys())
        for name in check_names:
            results[name] = self.run_check(name)
        return results

    def _create_alert(self, name: str, severity: str, message: str, source: str, metadata: Dict = None):
        alert = Alert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            name=name,
            severity=severity,
            message=message,
            source=source,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        with self._lock:
            existing = [a for a in self._alerts if a.name == name and not a.resolved]
            if existing:
                return existing[0]
            self._alerts.append(alert)
            self._save_alerts()

        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

        return alert

    def get_alerts(self, unresolved_only: bool = True, severity: str = None, limit: int = 50) -> List[Dict]:
        with self._lock:
            alerts = list(self._alerts)
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [a.to_dict() for a in alerts[-limit:]]

    def resolve_alert(self, alert_id: str) -> bool:
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = time.time()
                    self._save_alerts()
                    return True
            return False

    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_by = user
                    self._save_alerts()
                    return True
            return False

    def on_alert(self, handler: Callable):
        self._alert_handlers.append(handler)

    def get_metrics(self) -> Dict:
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent,
                "boot_time": psutil.boot_time(),
                "uptime": time.time() - psutil.boot_time(),
                "process_count": len(psutil.pids()),
            }
        except Exception:
            return {}

    def get_snapshot(self) -> Dict:
        checks = {}
        with self._lock:
            check_names = list(self._checks.keys())
        for name in check_names:
            check = self._checks.get(name)
            if check:
                checks[name] = check.last_status

        statuses = list(checks.values())
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "error" for s in statuses):
            overall = "error"
        elif any(s == "warning" for s in statuses):
            overall = "warning"
        else:
            overall = "unknown"

        return HealthSnapshot(
            timestamp=time.time(),
            checks=checks,
            metrics=self.get_metrics(),
            alerts=self.get_alerts(unresolved_only=True, limit=10),
            overall_status=overall,
        ).to_dict()

    def get_stats(self) -> Dict:
        with self._lock:
            checks = list(self._checks.values())
            alerts = [a for a in self._alerts if not a.resolved]
            return {
                "total_checks": len(checks),
                "enabled": sum(1 for c in checks if c.enabled),
                "healthy": sum(1 for c in checks if c.last_status == "healthy"),
                "warning": sum(1 for c in checks if c.last_status == "warning"),
                "error": sum(1 for c in checks if c.last_status == "error"),
                "unresolved_alerts": len(alerts),
                "total_alerts": len(self._alerts),
            }

    def start(self, check_interval: int = 30):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, args=(check_interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self, check_interval: int):
        while self._running and not self._stop_event.is_set():
            try:
                self.run_all_checks()
            except Exception:
                pass
            self._stop_event.wait(check_interval)


_monitor = None


def _get_monitor() -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


def health_monitor_tool(action: str = "status", **kwargs) -> Any:
    """Health monitor tool dispatcher."""
    try:
        monitor = _get_monitor()

        if action == "status":
            return monitor.get_snapshot()

        elif action == "checks":
            return {"checks": monitor.list_checks()}

        elif action == "check":
            name = kwargs.get("name", "")
            if not name:
                return {"error": "No check name provided"}
            return monitor.run_check(name)

        elif action == "check_all":
            results = monitor.run_all_checks()
            return {"results": results}

        elif action == "add_check":
            check_data = kwargs.get("check", {})
            check = HealthCheck(**check_data)
            monitor.add_check(check)
            return {"success": True}

        elif action == "remove_check":
            name = kwargs.get("name", "")
            ok = monitor.remove_check(name)
            return {"success": ok}

        elif action == "alerts":
            unresolved = kwargs.get("unresolved_only", True)
            severity = kwargs.get("severity")
            limit = kwargs.get("limit", 50)
            return {"alerts": monitor.get_alerts(unresolved, severity, limit)}

        elif action == "resolve_alert":
            alert_id = kwargs.get("alert_id", "")
            ok = monitor.resolve_alert(alert_id)
            return {"success": ok}

        elif action == "metrics":
            return monitor.get_metrics()

        elif action == "stats":
            return monitor.get_stats()

        elif action == "start":
            interval = kwargs.get("check_interval", 30)
            monitor.start(interval)
            return {"success": True}

        elif action == "stop":
            monitor.stop()
            return {"success": True}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
