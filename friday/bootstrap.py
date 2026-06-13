"""
FRIDAY Bootstrap — auto-start all background services.
Single entry point to bring FRIDAY to life:
  - Self-improve daemon
  - Dashboard web API
  - Periodic checkpointing
  - Validation middleware
  - Persistence loop
  - Configuration system
  - Service lifecycle manager
  - Health monitoring
  - Graceful shutdown
  - Service dependency graph
  - Resource monitoring
  - Scheduled tasks
  - Logging system
  - State persistence
  - Remote control server
  - Webhook notifications
  - Startup validation
  - Boot sequence profiles
  - Recovery mode
"""

from __future__ import annotations

import json
import os
import sys
import signal
import socket
import threading
import time
import shutil
import errno
import re
import traceback
import logging
import logging.handlers
import queue
import atexit
import textwrap
import inspect
import math
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from dataclasses import dataclass, field, asdict

from friday._paths import FRIDAY_MEMORY


# ── Constants ──

BOOTSTRAP_VERSION = "2.2.0"
DEFAULT_CONFIG_FILE = "bootstrap_config.json"
DEFAULT_STATE_FILE = "bootstrap_state.json"
DEFAULT_LOG_DIR = "logs"
DEFAULT_CONFIG = {
    "services": ["daemon", "dashboard", "checkpointer", "validation", "persistence"],
    "intervals": {
        "checkpointer": 300,
        "validation": 60,
        "persistence": 300,
        "health_check": 30,
        "resource_monitor": 60,
    },
    "auto_restart": True,
    "log_level": "INFO",
    "port_numbers": {
        "dashboard": 8765,
        "control_server": 9876,
    },
    "boot_profile": "standard",
    "max_restart_attempts": 5,
    "shutdown_timeout": 30,
    "webhook_url": "",
}


# ── Helpers ──

_internal_log_queue: queue.Queue = queue.Queue()


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)
    _internal_log_queue.put_nowait({"timestamp": ts, "level": "INFO", "message": msg})


def _log_warn(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] WARN {msg}", flush=True)
    _internal_log_queue.put_nowait({"timestamp": ts, "level": "WARN", "message": msg})


def _log_error(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] ERROR {msg}", flush=True)
    _internal_log_queue.put_nowait({"timestamp": ts, "level": "ERROR", "message": msg})


def _touch(path: str, content: str = ""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _read_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_timestamp() -> str:
    return datetime.now().isoformat()


def _get_timestamp_short() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _get_free_port(start: int = 9000, end: int = 9999) -> int:
    """Find a free port in range."""
    for port in range(start, end + 1):
        if _is_port_open(port):
            return port
    return 0


# ══════════════════════════════════════════════════════════════
#  1.  Configuration System
# ══════════════════════════════════════════════════════════════


class BootstrapConfig:
    """Configuration manager for FRIDAY bootstrap services.

    Loads configuration from FRIDAY_MEMORY/bootstrap_config.json.
    Provides typed access to all configuration values with defaults.
    """

    def __init__(self):
        self._config_path = os.path.join(FRIDAY_MEMORY, DEFAULT_CONFIG_FILE)
        self._data: dict = {}
        self.load_config()

    def load_config(self) -> dict:
        """Load configuration from disk, merging with defaults."""
        self._data = dict(DEFAULT_CONFIG)
        disk = _read_json(self._config_path, {})
        if disk:
            self._deep_merge(self._data, disk)
        return self._data

    def save_config(self) -> str:
        """Save current configuration to disk."""
        _write_json(self._config_path, self._data)
        return f"Configuration saved to {self._config_path}"

    @staticmethod
    def _deep_merge(base: dict, overrides: dict):
        """Recursively merge overrides into base dict."""
        for key, value in overrides.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                BootstrapConfig._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level config value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set a top-level config value and save."""
        self._data[key] = value
        self.save_config()

    def get_interval(self, service: str, default: int = 300) -> int:
        """Get the interval in seconds for a given service."""
        intervals = self._data.get("intervals", {})
        return intervals.get(service, default)

    def set_interval(self, service: str, interval: int):
        """Set the interval for a service and save."""
        if "intervals" not in self._data:
            self._data["intervals"] = {}
        self._data["intervals"][service] = interval
        self.save_config()

    def get_port(self, service: str, default: int = 8765) -> int:
        """Get the port number for a given service."""
        ports = self._data.get("port_numbers", {})
        return ports.get(service, default)

    def set_port(self, service: str, port: int):
        """Set a port number for a service and save."""
        if "port_numbers" not in self._data:
            self._data["port_numbers"] = {}
        self._data["port_numbers"][service] = port
        self.save_config()

    def get_log_level(self) -> str:
        """Get the current log level."""
        return self._data.get("log_level", "INFO")

    def set_log_level(self, level: str):
        """Set the log level and save."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level.upper() not in valid:
            raise ValueError(f"Invalid log level: {level}. Choose from {valid}")
        self._data["log_level"] = level.upper()
        self.save_config()

    def get_services(self) -> list[str]:
        """Get the list of enabled services."""
        return self._data.get("services", [])

    def set_services(self, services: list[str]):
        """Set the list of enabled services and save."""
        self._data["services"] = services
        self.save_config()

    def get_boot_profile(self) -> str:
        """Get the boot profile name."""
        return self._data.get("boot_profile", "standard")

    def set_boot_profile(self, profile: str):
        """Set the boot profile and save."""
        valid = {"minimal", "standard", "full"}
        if profile not in valid:
            raise ValueError(f"Invalid profile: {profile}. Choose from {valid}")
        self._data["boot_profile"] = profile
        self.save_config()

    def get_auto_restart(self) -> bool:
        """Check if auto-restart is enabled."""
        return self._data.get("auto_restart", True)

    def set_auto_restart(self, enabled: bool):
        """Enable or disable auto-restart."""
        self._data["auto_restart"] = bool(enabled)
        self.save_config()

    def get_max_restart_attempts(self) -> int:
        """Get the max restart attempts per service."""
        return self._data.get("max_restart_attempts", 5)

    def get_shutdown_timeout(self) -> int:
        """Get the shutdown timeout in seconds."""
        return self._data.get("shutdown_timeout", 30)

    def get_webhook_url(self) -> str:
        """Get the configured webhook URL."""
        return self._data.get("webhook_url", "")

    def set_webhook_url(self, url: str):
        """Set the webhook URL and save."""
        self._data["webhook_url"] = url
        self.save_config()

    def to_dict(self) -> dict:
        """Return the full config as a dict."""
        return dict(self._data)

    def reset_to_defaults(self) -> str:
        """Reset configuration to factory defaults."""
        self._data = dict(DEFAULT_CONFIG)
        return self.save_config()


_config_instance: Optional[BootstrapConfig] = None


def get_config() -> BootstrapConfig:
    """Get the global BootstrapConfig singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = BootstrapConfig()
    return _config_instance


# ══════════════════════════════════════════════════════════════
#  8.  Logging System  (defined early because other modules use it)
# ══════════════════════════════════════════════════════════════


class BootstrapLogger:
    """Rotating file logger for bootstrap services.

    Writes structured JSON logs to FRIDAY_MEMORY/logs/ directory.
    Supports configurable log levels and retrieval of recent logs.
    """

    def __init__(self, log_dir: Optional[str] = None, level: str = "INFO"):
        self._log_dir = log_dir or os.path.join(FRIDAY_MEMORY, DEFAULT_LOG_DIR)
        os.makedirs(self._log_dir, exist_ok=True)
        self._level = getattr(logging, level.upper(), logging.INFO)

        self._logger = logging.getLogger("friday.bootstrap")
        self._logger.setLevel(self._level)
        self._logger.handlers.clear()

        log_file = os.path.join(self._log_dir, f"bootstrap_{_get_timestamp_short()}.log")
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

        self._recent: list[dict] = []
        self._max_recent = 500

    def _log(self, level: str, msg: str):
        entry = {
            "timestamp": _get_timestamp(),
            "level": level,
            "message": msg,
        }
        self._recent.append(entry)
        if len(self._recent) > self._max_recent:
            self._recent.pop(0)

        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method(msg)

    def set_level(self, level: str):
        """Change the log level at runtime."""
        self._level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(self._level)

    def get_recent_logs(self, count: int = 50) -> list[dict]:
        """Return the most recent log entries."""
        return self._recent[-count:]

    def get_log_file_path(self) -> str:
        """Get the current log file path."""
        handler = self._logger.handlers[0] if self._logger.handlers else None
        if handler and hasattr(handler, "baseFilename"):
            return handler.baseFilename
        return ""

    def get_log_directory(self) -> str:
        """Get the log directory path."""
        return self._log_dir

    def info(self, msg: str):
        """Log an info message."""
        self._log("INFO", msg)

    def warning(self, msg: str):
        """Log a warning message."""
        self._log("WARNING", msg)

    def error(self, msg: str):
        """Log an error message."""
        self._log("ERROR", msg)

    def debug(self, msg: str):
        """Log a debug message."""
        self._log("DEBUG", msg)

    def critical(self, msg: str):
        """Log a critical message."""
        self._log("CRITICAL", msg)

    def get_log_files(self) -> list[str]:
        """List all log files in the log directory."""
        if not os.path.isdir(self._log_dir):
            return []
        return sorted(
            os.path.join(self._log_dir, f)
            for f in os.listdir(self._log_dir)
            if f.endswith(".log")
        )

    def cleanup_old_logs(self, keep_days: int = 30):
        """Remove log files older than keep_days."""
        now = time.time()
        cutoff = now - (keep_days * 86400)
        for fpath in self.get_log_files():
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
            except OSError:
                pass

    def get_stats(self) -> dict:
        """Get logging statistics."""
        files = self.get_log_files()
        total_size = sum(os.path.getsize(f) for f in files) if files else 0
        return {
            "log_files": len(files),
            "total_size_bytes": total_size,
            "recent_entries": len(self._recent),
            "log_directory": self._log_dir,
        }


_logger_instance: Optional[BootstrapLogger] = None


def get_logger() -> BootstrapLogger:
    """Get the global BootstrapLogger singleton."""
    global _logger_instance
    if _logger_instance is None:
        cfg = get_config()
        _logger_instance = BootstrapLogger(level=cfg.get_log_level())
    return _logger_instance


# ══════════════════════════════════════════════════════════════
#  2.  Service Lifecycle Manager
# ══════════════════════════════════════════════════════════════


@dataclass
class ServiceStatus:
    """Data class representing the status of a single service."""
    name: str
    status: str = "stopped"
    thread: Optional[threading.Thread] = None
    start_time: Optional[str] = None
    restart_count: int = 0
    last_error: Optional[str] = None
    pid: int = 0


class Service:
    """Represents a single bootstrappable service with lifecycle management.

    Each service has a name, a start function, a stop function, and
    tracks its own status, thread, start time, restart count, and errors.
    """

    def __init__(
        self,
        name: str,
        start_func: Callable,
        stop_func: Optional[Callable] = None,
        dependencies: Optional[list[str]] = None,
        daemon: bool = True,
    ):
        self.name = name
        self._start_func = start_func
        self._stop_func = stop_func
        self._dependencies = dependencies or []
        self._daemon = daemon
        self.status = ServiceStatus(name=name)
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the service in a new thread. Returns True on success."""
        with self._lock:
            if self.status.status == "running":
                _log_warn(f"service '{self.name}' is already running")
                return True
            try:
                self.status.restart_count += 1
                self.status.start_time = _get_timestamp()
                self.status.pid = os.getpid()
                result = self._start_func()
                if result is True or result is None:
                    self.status.status = "running"
                    self.status.last_error = None
                    return True
                else:
                    self.status.status = "failed"
                    self.status.last_error = f"start_func returned {result}"
                    return False
            except Exception as e:
                self.status.status = "failed"
                self.status.last_error = f"{type(e).__name__}: {e}"
                _log_error(f"service '{self.name}' failed to start: {e}")
                return False

    def stop(self) -> bool:
        """Signal the service to stop. Returns True on success."""
        with self._lock:
            if self.status.status == "stopped":
                return True
            try:
                if self._stop_func:
                    self._stop_func()
                self.status.status = "stopped"
                self.status.thread = None
                _log(f"service '{self.name}' stopped")
                return True
            except Exception as e:
                _log_error(f"error stopping '{self.name}': {e}")
                self.status.last_error = f"{type(e).__name__}: {e}"
                return False

    def restart(self) -> bool:
        """Restart the service (stop then start)."""
        self.stop()
        time.sleep(0.5)
        return self.start()

    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self.status.status == "running"

    def get_status(self) -> dict:
        """Get a dictionary representation of service status."""
        with self._lock:
            return {
                "name": self.name,
                "status": self.status.status,
                "start_time": self.status.start_time,
                "restart_count": self.status.restart_count,
                "last_error": self.status.last_error,
                "pid": self.status.pid,
                "dependencies": self._dependencies,
            }

    def get_dependencies(self) -> list[str]:
        """Get the list of dependency names for this service."""
        return list(self._dependencies)

    def set_thread(self, thread: Optional[threading.Thread]):
        """Associate a thread with this service."""
        self.status.thread = thread


class ServiceManager:
    """Singleton that manages lifecycle of all FRIDAY bootstrap services.

    Provides centralized start, stop, restart for any named service
    and bulk operations like start_all, stop_all.
    """

    _instance: Optional[ServiceManager] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._services: dict[str, Service] = OrderedDict()
        self._lock = threading.Lock()

    def register(self, service: Service):
        """Register a service with the manager."""
        with self._lock:
            self._services[service.name] = service
            _log(f"service '{service.name}' registered")

    def unregister(self, name: str):
        """Unregister a service by name."""
        with self._lock:
            if name in self._services:
                svc = self._services.pop(name)
                svc.stop()

    def get_service(self, name: str) -> Optional[Service]:
        """Get a registered service by name."""
        with self._lock:
            return self._services.get(name)

    def start_service(self, name: str) -> bool:
        """Start a single service by name."""
        svc = self.get_service(name)
        if svc is None:
            _log_error(f"unknown service: '{name}'")
            return False
        return svc.start()

    def stop_service(self, name: str) -> bool:
        """Stop a single service by name."""
        svc = self.get_service(name)
        if svc is None:
            _log_error(f"unknown service: '{name}'")
            return False
        return svc.stop()

    def restart_service(self, name: str) -> bool:
        """Restart a single service by name."""
        svc = self.get_service(name)
        if svc is None:
            _log_error(f"unknown service: '{name}'")
            return False
        return svc.restart()

    def start_all(self, names: Optional[list[str]] = None) -> dict:
        """Start all registered services, or only those in names."""
        with self._lock:
            targets = names or list(self._services.keys())
            started_order = get_ordered_services(targets)
            results = {}
            for svc_name in started_order:
                svc = self._services.get(svc_name)
                if svc:
                    results[svc_name] = svc.start()
                else:
                    results[svc_name] = False
            return results

    def stop_all(self, timeout: Optional[int] = None) -> dict:
        """Stop all registered services."""
        with self._lock:
            results = {}
            for name, svc in reversed(list(self._services.items())):
                results[name] = svc.stop()
            return results

    def get_all_status(self) -> dict:
        """Get status for all registered services."""
        with self._lock:
            return {name: svc.get_status() for name, svc in self._services.items()}

    def get_running_services(self) -> list[str]:
        """Get list of names of running services."""
        with self._lock:
            return [name for name, svc in self._services.items() if svc.is_running()]

    def get_service_names(self) -> list[str]:
        """Get list of all registered service names."""
        with self._lock:
            return list(self._services.keys())

    def count_services(self) -> int:
        """Get the total number of registered services."""
        return len(self._services)

    def count_running(self) -> int:
        """Get the number of running services."""
        return len(self.get_running_services())


def get_service_manager() -> ServiceManager:
    """Get the global ServiceManager singleton."""
    return ServiceManager()


# ══════════════════════════════════════════════════════════════
#  5.  Service Dependency Graph
# ══════════════════════════════════════════════════════════════


class ServiceDependency:
    """Represents dependencies between FRIDAY services.

    Used to resolve start order so that services start in the correct
    sequence based on their declared dependencies.
    """

    _dependency_map: dict[str, list[str]] = {
        "daemon": ["persistence"],
        "dashboard": ["checkpointer"],
        "checkpointer": ["persistence"],
        "validation": ["checkpointer"],
        "persistence": [],
    }

    @classmethod
    def get_dependencies(cls, service_name: str) -> list[str]:
        """Get direct dependencies for a service."""
        return cls._dependency_map.get(service_name, [])

    @classmethod
    def get_dependents(cls, service_name: str) -> list[str]:
        """Get services that depend on the given service."""
        dependents = []
        for svc, deps in cls._dependency_map.items():
            if service_name in deps:
                dependents.append(svc)
        return dependents

    @classmethod
    def get_all_dependencies(cls, service_name: str) -> list[str]:
        """Get all transitive dependencies for a service."""
        result = []
        visited = set()

        def _walk(name: str):
            for dep in cls._dependency_map.get(name, []):
                if dep not in visited:
                    visited.add(dep)
                    result.append(dep)
                    _walk(dep)

        _walk(service_name)
        return result

    @classmethod
    def resolve_start_order(cls, services: list[str]) -> list[str]:
        """Topological sort of services by their dependencies.

        Returns services in start order (dependencies first).
        """
        graph = {}
        for svc in services:
            deps = cls.get_dependencies(svc)
            graph[svc] = [d for d in deps if d in services]

        visited = set()
        sorted_list = []

        def _dfs(node: str, path: set):
            if node in path:
                _log_warn(f"circular dependency detected involving '{node}'")
                return
            if node in visited:
                return
            path.add(node)
            for dep in graph.get(node, []):
                _dfs(dep, path)
            path.remove(node)
            visited.add(node)
            sorted_list.append(node)

        for svc in services:
            if svc not in visited:
                _dfs(svc, set())

        return sorted_list

    @classmethod
    def check_dependency_health(cls, service_name: str) -> dict:
        """Check if all dependencies of a service are healthy.

        Returns a dict with 'healthy' bool and details per dependency.
        """
        mgr = get_service_manager()
        deps = cls.get_dependencies(service_name)
        result = {"service": service_name, "healthy": True, "dependencies": {}}
        for dep_name in deps:
            svc = mgr.get_service(dep_name)
            if svc is None:
                result["dependencies"][dep_name] = {"status": "not_registered", "healthy": False}
                result["healthy"] = False
            elif svc.is_running():
                result["dependencies"][dep_name] = {"status": "running", "healthy": True}
            else:
                result["dependencies"][dep_name] = {
                    "status": svc.status.status,
                    "healthy": False,
                    "error": svc.status.last_error,
                }
                result["healthy"] = False
        return result

    @classmethod
    def validate_service_graph(cls) -> list[str]:
        """Validate the entire dependency graph for cycles.

        Returns a list of warning messages.
        """
        warnings = []
        visited = set()
        rec_stack = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in cls._dependency_map.get(node, []):
                if dep not in visited:
                    if _dfs(dep):
                        return True
                elif dep in rec_stack:
                    warnings.append(f"circular dependency: {node} -> {dep}")
                    return True
            rec_stack.remove(node)
            return False

        for svc in cls._dependency_map:
            if svc not in visited:
                _dfs(svc)

        return warnings


def get_ordered_services(services: list[str]) -> list[str]:
    """Get services sorted by their dependency order."""
    return ServiceDependency.resolve_start_order(services)


# ══════════════════════════════════════════════════════════════
#  3.  Health Monitoring
# ══════════════════════════════════════════════════════════════


class HealthMonitor(threading.Thread):
    """Background thread that pings all services periodically and
    auto-restarts dead services with exponential backoff.
    """

    def __init__(self, interval: int = 30, auto_restart: bool = True):
        super().__init__(daemon=True, name="health-monitor")
        self._interval = interval
        self._auto_restart = auto_restart
        self._stop_event = threading.Event()
        self._failures: dict[str, int] = defaultdict(int)
        self._backoff: dict[str, float] = defaultdict(lambda: 1.0)
        self._max_backoff = 300.0
        self._health_history: list[dict] = []
        self._max_history = 1000
        self._lock = threading.Lock()

    def run(self):
        _log("health monitor started")
        while not self._stop_event.is_set():
            self._check_all()
            self._stop_event.wait(self._interval)

    def stop(self):
        """Signal the health monitor to stop."""
        self._stop_event.set()
        _log("health monitor stopped")

    def _check_all(self):
        """Check all registered services."""
        mgr = get_service_manager()
        current_time = _get_timestamp()
        for name in mgr.get_service_names():
            svc = mgr.get_service(name)
            if svc is None:
                continue
            if svc.is_running():
                with self._lock:
                    self._failures[name] = 0
                    self._backoff[name] = 1.0
            else:
                with self._lock:
                    self._failures[name] += 1
                failure_count = self._failures[name]
                _log_warn(f"health: service '{name}' is {svc.status.status} (failure #{failure_count})")

                if self._auto_restart and failure_count <= get_config().get_max_restart_attempts():
                    self._try_auto_restart(name, svc)

        report = {
            "timestamp": current_time,
            "running": mgr.count_running(),
            "total": mgr.count_services(),
            "failures": dict(self._failures),
        }
        with self._lock:
            self._health_history.append(report)
            if len(self._health_history) > self._max_history:
                self._health_history.pop(0)

    def _try_auto_restart(self, name: str, svc: Service):
        """Attempt to auto-restart a failed service with backoff."""
        with self._lock:
            delay = min(self._backoff[name], self._max_backoff)
            self._backoff[name] = min(self._backoff[name] * 2, self._max_backoff)

        _log(f"health: auto-restarting '{name}' in {delay:.1f}s (backoff)")
        time.sleep(delay)

        success = svc.restart()
        if success:
            _log(f"health: '{name}' auto-restart succeeded")
            with self._lock:
                self._failures[name] = 0
                self._backoff[name] = 1.0
        else:
            _log_error(f"health: '{name}' auto-restart failed")

    def get_health_report(self) -> dict:
        """Generate a detailed health report for all services."""
        mgr = get_service_manager()
        services_status = mgr.get_all_status()
        unhealthy = []
        for name, status in services_status.items():
            if status["status"] != "running":
                dep_health = ServiceDependency.check_dependency_health(name)
                unhealthy.append({
                    "service": name,
                    "status": status["status"],
                    "last_error": status["last_error"],
                    "restart_count": status["restart_count"],
                    "dependency_health": dep_health,
                })

        return {
            "timestamp": _get_timestamp(),
            "healthy": len(unhealthy) == 0,
            "total_services": mgr.count_services(),
            "running_services": mgr.count_running(),
            "unhealthy_services": unhealthy,
            "failure_counts": dict(self._failures),
            "backoff_delays": {k: round(v, 1) for k, v in self._backoff.items()},
        }

    def get_failure_count(self, service_name: str) -> int:
        """Get the failure count for a specific service."""
        return self._failures.get(service_name, 0)

    def reset_failure_count(self, service_name: str):
        """Reset the failure count for a specific service."""
        with self._lock:
            self._failures[service_name] = 0
            self._backoff[service_name] = 1.0

    def get_history(self, count: int = 10) -> list[dict]:
        """Get recent health check history."""
        with self._lock:
            return self._health_history[-count:]


_health_monitor_instance: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global HealthMonitor singleton."""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        cfg = get_config()
        interval = cfg.get_interval("health_check", 30)
        _health_monitor_instance = HealthMonitor(interval=interval, auto_restart=cfg.get_auto_restart())
    return _health_monitor_instance


# ══════════════════════════════════════════════════════════════
#  6.  Resource Monitoring
# ══════════════════════════════════════════════════════════════


class ResourceMonitor(threading.Thread):
    """Background thread that tracks memory/CPU usage per service thread,
    logs resource usage, and alerts on potential leaks.
    """

    def __init__(self, interval: int = 60):
        super().__init__(daemon=True, name="resource-monitor")
        self._interval = interval
        self._stop_event = threading.Event()
        self._history: list[dict] = []
        self._max_history = 500
        self._lock = threading.Lock()
        self._alerts: list[dict] = []

    def run(self):
        _log("resource monitor started")
        while not self._stop_event.is_set():
            self._sample()
            self._stop_event.wait(self._interval)

    def stop(self):
        """Signal the resource monitor to stop."""
        self._stop_event.set()
        _log("resource monitor stopped")

    def _sample(self):
        """Sample resource usage of active threads."""
        import tracemalloc

        try:
            import psutil
            has_psutil = True
        except ImportError:
            has_psutil = False

        sample = {
            "timestamp": _get_timestamp(),
            "active_threads": threading.active_count(),
            "thread_details": [],
            "memory_mb": 0,
            "cpu_percent": 0,
            "alerts": [],
        }

        if has_psutil:
            proc = psutil.Process()
            try:
                mem = proc.memory_info()
                sample["memory_mb"] = round(mem.rss / (1024 * 1024), 2)
                sample["cpu_percent"] = proc.cpu_percent(interval=0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            for thread_obj in threading.enumerate():
                if thread_obj.daemon or thread_obj.name.startswith("resource-monitor"):
                    continue
                try:
                    thread_id = thread_obj.ident or 0
                    thread_sample = {
                        "name": thread_obj.name or "unknown",
                        "id": thread_id,
                        "alive": thread_obj.is_alive(),
                    }
                    sample["thread_details"].append(thread_sample)
                except Exception:
                    pass
        else:
            for thread_obj in threading.enumerate():
                if thread_obj.daemon:
                    continue
                sample["thread_details"].append({
                    "name": thread_obj.name or "unknown",
                    "id": thread_obj.ident or 0,
                    "alive": thread_obj.is_alive(),
                })

        if sample["memory_mb"] > 500:
            alert = {
                "timestamp": sample["timestamp"],
                "type": "high_memory",
                "value_mb": sample["memory_mb"],
                "threshold": 500,
            }
            sample["alerts"].append(alert)
            self._alerts.append(alert)
            _log_warn(f"high memory usage: {sample['memory_mb']} MB")

        previous = self._history[-1] if self._history else None
        if previous and sample["memory_mb"] > 0:
            delta = sample["memory_mb"] - previous.get("memory_mb", 0)
            if delta > 50:
                alert = {
                    "timestamp": sample["timestamp"],
                    "type": "memory_leak_suspected",
                    "delta_mb": round(delta, 2),
                    "current_mb": sample["memory_mb"],
                }
                sample["alerts"].append(alert)
                self._alerts.append(alert)
                _log_warn(f"suspected memory leak: +{delta:.1f} MB since last sample")

        with self._lock:
            self._history.append(sample)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            if len(self._alerts) > 200:
                self._alerts = self._alerts[-200:]

    def get_resource_report(self) -> dict:
        """Get a summary resource report."""
        with self._lock:
            recent = self._history[-10:] if self._history else []
            avg_mem = 0
            max_mem = 0
            avg_threads = 0
            if recent:
                mems = [s["memory_mb"] for s in recent if s["memory_mb"]]
                avg_mem = round(sum(mems) / len(mems), 2) if mems else 0
                max_mem = max(mems) if mems else 0
                avg_threads = round(sum(s["active_threads"] for s in recent) / len(recent), 1)

            return {
                "timestamp": _get_timestamp(),
                "current_memory_mb": recent[-1]["memory_mb"] if recent else 0,
                "avg_memory_mb": avg_mem,
                "peak_memory_mb": max_mem,
                "avg_active_threads": avg_threads,
                "current_active_threads": recent[-1]["active_threads"] if recent else 0,
                "alerts_count": len(self._alerts),
                "recent_alerts": self._alerts[-10:],
                "samples_collected": len(self._history),
            }

    def get_memory_history(self, count: int = 50) -> list[dict]:
        """Get memory usage history."""
        with self._lock:
            return [
                {"timestamp": s["timestamp"], "memory_mb": s["memory_mb"], "cpu_percent": s["cpu_percent"]}
                for s in self._history[-count:]
            ]

    def get_alerts(self) -> list[dict]:
        """Get all resource alerts."""
        return list(self._alerts)

    def clear_alerts(self):
        """Clear all resource alerts."""
        with self._lock:
            self._alerts.clear()


_resource_monitor_instance: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get the global ResourceMonitor singleton."""
    global _resource_monitor_instance
    if _resource_monitor_instance is None:
        cfg = get_config()
        interval = cfg.get_interval("resource_monitor", 60)
        _resource_monitor_instance = ResourceMonitor(interval=interval)
    return _resource_monitor_instance


# ══════════════════════════════════════════════════════════════
#  7.  Scheduled Tasks (cron-like scheduler)
# ══════════════════════════════════════════════════════════════


class ScheduledTask:
    """Represents a single scheduled task with interval and function."""

    def __init__(self, name: str, interval_seconds: float, func: Callable, daemon: bool = True):
        self.name = name
        self.interval = interval_seconds
        self.func = func
        self.daemon = daemon
        self.last_run: Optional[float] = None
        self.next_run: float = time.time() + interval_seconds
        self.run_count: int = 0
        self.error_count: int = 0
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._active = False

    def execute(self) -> Any:
        """Execute the task function, tracking timing and errors."""
        with self._lock:
            self._active = True
            self.last_run = time.time()
            self.next_run = self.last_run + self.interval
            self.run_count += 1
        try:
            result = self.func()
            with self._lock:
                self._active = False
            return result
        except Exception as e:
            with self._lock:
                self.error_count += 1
                self.last_error = f"{type(e).__name__}: {e}"
                self._active = False
            _log_error(f"scheduled task '{self.name}' failed: {e}")
            return None

    def is_due(self, now: Optional[float] = None) -> bool:
        """Check if the task is due to run."""
        if now is None:
            now = time.time()
        return now >= self.next_run

    def get_status(self) -> dict:
        """Get status dict for this task."""
        with self._lock:
            return {
                "name": self.name,
                "interval": self.interval,
                "last_run": datetime.fromtimestamp(self.last_run).isoformat() if self.last_run else None,
                "next_run": datetime.fromtimestamp(self.next_run).isoformat(),
                "run_count": self.run_count,
                "error_count": self.error_count,
                "last_error": self.last_error,
                "active": self._active,
            }


class TaskScheduler(threading.Thread):
    """Background thread that manages and executes scheduled tasks."""

    def __init__(self):
        super().__init__(daemon=True, name="task-scheduler")
        self._tasks: dict[str, ScheduledTask] = {}
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def run(self):
        _log("task scheduler started")
        while not self._stop_event.is_set():
            now = time.time()
            due_tasks = []
            with self._lock:
                for name, task in self._tasks.items():
                    if task.is_due(now):
                        due_tasks.append(task)
            for task in due_tasks:
                if not self._stop_event.is_set():
                    thread = threading.Thread(target=task.execute, daemon=True, name=f"sched-{task.name}")
                    thread.start()
            self._stop_event.wait(1.0)

    def stop(self):
        """Stop the task scheduler."""
        self._stop_event.set()
        _log("task scheduler stopped")

    def schedule_task(self, name: str, interval_seconds: float, func: Callable) -> str:
        """Schedule a new recurring task."""
        if interval_seconds <= 0:
            raise ValueError("interval must be positive")
        with self._lock:
            if name in self._tasks:
                return f"task '{name}' already exists, unschedule first"
            self._tasks[name] = ScheduledTask(name, interval_seconds, func)
            _log(f"scheduled task '{name}' every {interval_seconds}s")
            return f"task '{name}' scheduled every {interval_seconds}s"

    def unschedule_task(self, name: str) -> str:
        """Remove a scheduled task."""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                _log(f"unscheduled task '{name}'")
                return f"task '{name}' removed"
            return f"task '{name}' not found"

    def list_scheduled_tasks(self) -> list[dict]:
        """List all scheduled tasks with their status."""
        with self._lock:
            return [task.get_status() for task in self._tasks.values()]

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a specific task by name."""
        with self._lock:
            return self._tasks.get(name)

    def has_task(self, name: str) -> bool:
        """Check if a task with the given name exists."""
        with self._lock:
            return name in self._tasks

    def count_tasks(self) -> int:
        """Get the number of scheduled tasks."""
        return len(self._tasks)


_task_scheduler_instance: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    """Get the global TaskScheduler singleton."""
    global _task_scheduler_instance
    if _task_scheduler_instance is None:
        _task_scheduler_instance = TaskScheduler()
    return _task_scheduler_instance


# ══════════════════════════════════════════════════════════════
#  9.  State Persistence
# ══════════════════════════════════════════════════════════════


class StateManager:
    """Persists bootstrap state (running services, PIDs) to disk.

    On restart, compares current state with saved state to detect
    stale processes and recover gracefully.
    """

    def __init__(self):
        self._state_path = os.path.join(FRIDAY_MEMORY, DEFAULT_STATE_FILE)
        self._backup_path = self._state_path + ".bak"
        self._lock = threading.Lock()

    def save_state(self) -> str:
        """Save current bootstrap state to disk."""
        mgr = get_service_manager()
        now = _get_timestamp()
        state = {
            "version": BOOTSTRAP_VERSION,
            "timestamp": now,
            "pid": os.getpid(),
            "services": mgr.get_all_status(),
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
            },
        }
        if os.path.exists(self._state_path):
            try:
                shutil.copy2(self._state_path, self._backup_path)
            except (OSError, shutil.Error):
                pass
        _write_json(self._state_path, state)
        return f"state saved at {now}"

    def load_state(self) -> Optional[dict]:
        """Load the saved bootstrap state from disk."""
        state = _read_json(self._state_path, None)
        if state is None:
            backup = _read_json(self._backup_path, None)
            if backup:
                _log_warn("using backup state file")
                return backup
            return None
        return state

    def recover_stale_state(self) -> dict:
        """Detect and clean up stale state from previous runs.

        Compares saved PID with current process. If different, cleans
        up stale flags and state. Returns recovery report.
        """
        report = {
            "timestamp": _get_timestamp(),
            "recovered": False,
            "actions_taken": [],
            "stale_pids_found": [],
        }

        state = self.load_state()
        if state is None:
            report["actions_taken"].append("no saved state found, nothing to recover")
            return report

        saved_pid = state.get("pid")
        current_pid = os.getpid()

        if saved_pid and saved_pid != current_pid:
            report["stale_pids_found"].append(saved_pid)
            _log(f"stale state detected: previous PID={saved_pid}, current PID={current_pid}")

            try:
                stale_proc = _read_json(self._state_path, {})
                if stale_proc:
                    _log("cleaning up stale service flags")
                    flags_dir = FRIDAY_MEMORY
                    for fname in os.listdir(flags_dir):
                        if fname.startswith("_") and fname.endswith(".flag"):
                            fpath = os.path.join(flags_dir, fname)
                            try:
                                os.remove(fpath)
                                report["actions_taken"].append(f"removed stale flag: {fname}")
                            except OSError:
                                pass

                    report["recovered"] = True
                    _log("stale state recovered successfully")
            except Exception as e:
                _log_error(f"recovery error: {e}")
                report["actions_taken"].append(f"recovery error: {e}")
        else:
            report["actions_taken"].append("no stale state detected")

        return report

    def clear_state(self) -> str:
        """Remove the state file from disk."""
        try:
            if os.path.exists(self._state_path):
                os.remove(self._state_path)
            if os.path.exists(self._backup_path):
                os.remove(self._backup_path)
            return "state cleared"
        except OSError as e:
            return f"failed to clear state: {e}"

    def get_state_path(self) -> str:
        """Get the path to the state file."""
        return self._state_path

    def state_exists(self) -> bool:
        """Check if a state file exists on disk."""
        return os.path.exists(self._state_path) or os.path.exists(self._backup_path)

    def compare_with_current(self) -> dict:
        """Compare saved state with current runtime state.

        Returns a dict showing services that were running but are now
        missing (stale), and services running now that weren't saved.
        """
        saved = self.load_state()
        if not saved:
            return {"message": "no saved state to compare", "differences": []}

        mgr = get_service_manager()
        saved_services = set(saved.get("services", {}).keys())
        current_services = set(mgr.get_service_names())

        stale = saved_services - current_services
        new = current_services - saved_services

        return {
            "timestamp": _get_timestamp(),
            "saved_pid": saved.get("pid"),
            "current_pid": os.getpid(),
            "stale_services": list(stale),
            "new_services": list(new),
            "differences": len(stale) + len(new),
        }


_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global StateManager singleton."""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance


# ══════════════════════════════════════════════════════════════
# 10.  Remote Control Server
# ══════════════════════════════════════════════════════════════


class ControlServer(threading.Thread):
    """Lightweight TCP server that accepts IPC commands.

    Listens on localhost for JSON commands: start, stop, restart, status,
    config, health, resources, shutdown.
    """

    def __init__(self, port: int = 9876, host: str = "127.0.0.1"):
        super().__init__(daemon=True, name="control-server")
        self._host = host
        self._port = port
        self._stop_event = threading.Event()
        self._server_socket: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def run(self):
        _log(f"control server listening on {self._host}:{self._port}")
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        try:
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(5)
        except OSError as e:
            _log_error(f"control server bind failed: {e}")
            return

        while not self._stop_event.is_set():
            try:
                conn, addr = self._server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr),
                    daemon=True,
                    name=f"ctrl-{addr[1]}",
                )
                thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

        _log("control server stopped")

    def stop(self):
        """Stop the control server."""
        self._stop_event.set()
        with self._lock:
            if self._server_socket:
                try:
                    self._server_socket.close()
                except OSError:
                    pass
                self._server_socket = None

    def _handle_connection(self, conn: socket.socket, addr: tuple):
        """Handle a single control connection."""
        try:
            conn.settimeout(10.0)
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(data) > 65536:
                    break

            if not data:
                conn.close()
                return

            try:
                payload = json.loads(data.decode("utf-8").strip())
            except json.JSONDecodeError:
                self._send_response(conn, {"error": "invalid JSON"})
                return

            action = payload.get("action", "")
            kwargs = payload.get("kwargs", {})
            response = self._dispatch(action, kwargs)
            self._send_response(conn, response)
        except Exception as e:
            try:
                self._send_response(conn, {"error": str(e)})
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _send_response(self, conn: socket.socket, data: dict):
        """Send a JSON response over the connection."""
        resp = json.dumps(data).encode("utf-8")
        conn.sendall(resp)

    def _dispatch(self, action: str, kwargs: dict) -> dict:
        """Dispatch a control command to the appropriate handler."""
        if action == "start":
            result = bootstrap_tool("start", **kwargs)
            return {"action": "start", "result": result}
        elif action == "stop":
            result = bootstrap_tool("stop")
            return {"action": "stop", "result": result}
        elif action == "restart":
            svc_name = kwargs.get("service", "")
            mgr = get_service_manager()
            success = mgr.restart_service(svc_name) if svc_name else False
            return {"action": "restart", "service": svc_name, "success": success}
        elif action == "status":
            mgr = get_service_manager()
            return {"action": "status", "services": mgr.get_all_status()}
        elif action == "config":
            cfg = get_config()
            return {"action": "config", "config": cfg.to_dict()}
        elif action == "health":
            hm = get_health_monitor()
            return {"action": "health", "report": hm.get_health_report()}
        elif action == "resources":
            rm = get_resource_monitor()
            return {"action": "resources", "report": rm.get_resource_report()}
        elif action == "shutdown":
            graceful_shutdown()
            return {"action": "shutdown", "result": "shutdown initiated"}
        elif action == "ping":
            return {"action": "pong", "timestamp": _get_timestamp()}
        else:
            return {"error": f"unknown action: {action}"}

    def get_address(self) -> str:
        """Get the server address string."""
        return f"{self._host}:{self._port}"


_control_server_instance: Optional[ControlServer] = None


def start_control_server(port: Optional[int] = None) -> ControlServer:
    """Start the remote control server on the given port.

    If no port is given, uses the configured port from BootstrapConfig.
    """
    global _control_server_instance
    if _control_server_instance and _control_server_instance.is_alive():
        _log("control server already running")
        return _control_server_instance

    if port is None:
        port = get_config().get_port("control_server", 9876)
    _control_server_instance = ControlServer(port=port)
    _control_server_instance.start()
    return _control_server_instance


def stop_control_server():
    """Stop the remote control server."""
    global _control_server_instance
    if _control_server_instance:
        _control_server_instance.stop()
        _control_server_instance = None


# ══════════════════════════════════════════════════════════════
# 11.  Webhook Notifications
# ══════════════════════════════════════════════════════════════


class WebhookNotifier:
    """Sends HTTP POST notifications on service start/stop/failure events.

    Configure with a URL and sends JSON payloads for each event.
    """

    def __init__(self, url: str = ""):
        self._url = url
        self._enabled = bool(url)
        self._queue: queue.Queue = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_status: Optional[int] = None
        self._notification_count = 0

    def start(self):
        """Start the background notification worker."""
        if not self._enabled:
            return
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="webhook-worker"
        )
        self._worker.start()
        _log("webhook notifier started")

    def stop(self):
        """Stop the background notification worker."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5)

    def configure_webhook(self, url: str) -> str:
        """Set the webhook URL and enable notifications."""
        self._url = url
        self._enabled = bool(url)
        if self._enabled:
            self.start()
            return f"webhook configured: {url}"
        else:
            self.stop()
            return "webhook disabled"

    def send_webhook(self, event_type: str, payload: dict) -> bool:
        """Enqueue a webhook notification."""
        if not self._enabled or not self._url:
            return False
        self._queue.put_nowait({"event": event_type, "payload": payload, "timestamp": _get_timestamp()})
        return True

    def test_webhook(self) -> dict:
        """Send a test notification to verify webhook configuration."""
        test_payload = {
            "event": "test",
            "message": "This is a test notification from FRIDAY Bootstrap",
            "timestamp": _get_timestamp(),
            "version": BOOTSTRAP_VERSION,
        }
        if not self._url:
            return {"success": False, "error": "no webhook URL configured"}
        try:
            import urllib.request
            import urllib.error
            data = json.dumps(test_payload).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=10)
            self._last_status = resp.status
            self._notification_count += 1
            return {
                "success": 200 <= resp.status < 300,
                "status_code": resp.status,
                "response": resp.read().decode("utf-8", errors="replace")[:500],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def notify_service_start(self, service_name: str):
        """Send a service start notification."""
        self.send_webhook("service_start", {
            "service": service_name,
            "pid": os.getpid(),
        })

    def notify_service_stop(self, service_name: str):
        """Send a service stop notification."""
        self.send_webhook("service_stop", {
            "service": service_name,
        })

    def notify_service_failure(self, service_name: str, error: str):
        """Send a service failure notification."""
        self.send_webhook("service_failure", {
            "service": service_name,
            "error": error,
        })

    def _worker_loop(self):
        """Background worker that sends queued webhook notifications."""
        import urllib.request
        import urllib.error

        while not self._stop_event.is_set():
            try:
                notification = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                data = json.dumps(notification).encode("utf-8")
                req = urllib.request.Request(
                    self._url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=10)
                self._last_status = resp.status
                self._notification_count += 1
            except Exception as e:
                _log_warn(f"webhook send failed: {e}")

    def get_status(self) -> dict:
        """Get current webhook notifier status."""
        return {
            "enabled": self._enabled,
            "url": self._url,
            "last_http_status": self._last_status,
            "notification_count": self._notification_count,
            "queue_size": self._queue.qsize(),
        }


_webhook_notifier_instance: Optional[WebhookNotifier] = None


def get_webhook_notifier() -> WebhookNotifier:
    """Get the global WebhookNotifier singleton."""
    global _webhook_notifier_instance
    if _webhook_notifier_instance is None:
        url = get_config().get_webhook_url()
        _webhook_notifier_instance = WebhookNotifier(url=url)
    return _webhook_notifier_instance


# ══════════════════════════════════════════════════════════════
#  4.  Graceful Shutdown
# ══════════════════════════════════════════════════════════════


_shutdown_in_progress = False


def graceful_shutdown(timeout: Optional[int] = None) -> dict:
    """Gracefully shut down all services with timeout.

    Signals services to stop, waits for completion, and force-kills
    if the timeout is exceeded. Saves state before exit.
    """
    global _shutdown_in_progress
    if _shutdown_in_progress:
        return {"message": "shutdown already in progress"}
    _shutdown_in_progress = True

    if timeout is None:
        timeout = get_config().get_shutdown_timeout()

    _log(f"graceful shutdown initiated (timeout={timeout}s)")

    report = {
        "timestamp": _get_timestamp(),
        "stopped_services": [],
        "failed_services": [],
        "force_killed": [],
    }

    try:
        hm = get_health_monitor()
        if hm.is_alive():
            hm.stop()
            hm.join(timeout=5)
            _log("health monitor stopped")
    except Exception:
        pass

    try:
        rm = get_resource_monitor()
        if rm.is_alive():
            rm.stop()
            rm.join(timeout=5)
            _log("resource monitor stopped")
    except Exception:
        pass

    try:
        scheduler = get_task_scheduler()
        if scheduler.is_alive():
            scheduler.stop()
            scheduler.join(timeout=5)
            _log("task scheduler stopped")
    except Exception:
        pass

    try:
        stop_control_server()
        _log("control server stopped")
    except Exception:
        pass

    try:
        wh = get_webhook_notifier()
        wh.stop()
    except Exception:
        pass

    mgr = get_service_manager()
    running = mgr.get_running_services()
    for name in running:
        try:
            svc = mgr.get_service(name)
            if svc and svc.stop():
                report["stopped_services"].append(name)
            else:
                report["failed_services"].append(name)
        except Exception as e:
            report["failed_services"].append(name)
            _log_error(f"error stopping '{name}': {e}")

    remaining = mgr.get_running_services()
    if remaining:
        _log_warn(f"waiting for {len(remaining)} services to stop (timeout={timeout}s)")
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = mgr.get_running_services()
            if not remaining:
                break
            time.sleep(0.5)

        still_running = mgr.get_running_services()
        if still_running:
            _log_error(f"force killing {len(still_running)} services")
            report["force_killed"] = still_running
            for name in still_running:
                svc = mgr.get_service(name)
                if svc:
                    svc.status.status = "stopped"

    try:
        state_mgr = get_state_manager()
        state_mgr.save_state()
        _log("state saved before shutdown")
    except Exception as e:
        _log_error(f"failed to save state: {e}")

    daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
    if os.path.exists(daemon_flag):
        try:
            os.remove(daemon_flag)
        except Exception:
            pass

    _log("FRIDAY services stopped")
    _shutdown_in_progress = False
    return report


def _signal_handler(sig, frame):
    """Handle OS signals (SIGINT, SIGTERM) for graceful shutdown."""
    signame = signal.Signals(sig).name
    _log(f"received {signame}, initiating graceful shutdown")
    result = graceful_shutdown()
    _log(f"shutdown complete: {len(result.get('stopped_services', []))} services stopped")
    sys.exit(0)


def install_signal_handlers():
    """Install signal handlers for graceful shutdown on SIGINT/SIGTERM.
    Only works in the main thread; skipped silently in worker threads."""
    if threading.current_thread() is not threading.main_thread():
        return
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)
    _log("signal handlers installed (Ctrl+C, SIGTERM)")


# ══════════════════════════════════════════════════════════════
# 12.  Startup Validation
# ══════════════════════════════════════════════════════════════


class StartupValidator:
    """Validates the environment and configuration before bootstrap starts."""

    @staticmethod
    def validate_environment() -> dict:
        """Check Python version, import availability, disk space, port availability.

        Returns a dict with 'valid' bool and list of warnings/errors.
        """
        result = {
            "valid": True,
            "python": {"version": sys.version, "ok": False},
            "imports": {},
            "disk": {"ok": False, "free_bytes": 0, "free_mb": 0},
            "ports": {},
            "warnings": [],
            "errors": [],
        }

        if sys.version_info >= (3, 8):
            result["python"]["ok"] = True
        else:
            result["valid"] = False
            result["errors"].append(f"Python 3.8+ required, got {sys.version_info}")

        required_imports = [
            "json", "os", "sys", "threading", "time", "datetime",
            "socket", "signal", "logging", "queue",
        ]
        optional_imports = ["psutil"]

        for mod_name in required_imports:
            try:
                __import__(mod_name)
                result["imports"][mod_name] = True
            except ImportError:
                result["imports"][mod_name] = False
                result["valid"] = False
                result["errors"].append(f"required import '{mod_name}' not found")

        for mod_name in optional_imports:
            try:
                __import__(mod_name)
                result["imports"][mod_name] = True
            except ImportError:
                result["imports"][mod_name] = False
                result["warnings"].append(f"optional import '{mod_name}' not found (resource monitoring limited)")

        try:
            stat = shutil.disk_usage(FRIDAY_MEMORY)
            result["disk"]["free_bytes"] = stat.free
            result["disk"]["free_mb"] = round(stat.free / (1024 * 1024), 2)
            if stat.free < 100 * 1024 * 1024:
                result["valid"] = False
                result["errors"].append(f"low disk space: {result['disk']['free_mb']} MB free (need >= 100 MB)")
            else:
                result["disk"]["ok"] = True
        except OSError as e:
            result["warnings"].append(f"disk check failed: {e}")
            result["disk"]["ok"] = True

        ports_to_check = get_config().get("port_numbers", {})
        for port_name, port_num in ports_to_check.items():
            available = _is_port_open(port_num)
            result["ports"][port_name] = {
                "port": port_num,
                "available": available,
            }
            if not available:
                result["warnings"].append(f"port {port_num} ({port_name}) is already in use")

        if not result["errors"]:
            _log("environment validation passed")
        else:
            _log_error(f"environment validation failed: {len(result['errors'])} error(s)")

        return result

    @staticmethod
    def validate_services_config() -> dict:
        """Validate the services configuration before starting.

        Checks that all configured services have registered handlers
        and that intervals/ports are within acceptable ranges.
        """
        result = {
            "valid": True,
            "services": {},
            "warnings": [],
            "errors": [],
        }

        cfg = get_config()
        services = cfg.get_services()
        known_handlers = {
            "daemon": _start_daemon,
            "dashboard": _start_dashboard_api,
            "checkpointer": _start_checkpointer,
            "validation": _start_validation_flusher,
            "persistence": _start_persistence,
        }

        for svc_name in services:
            svc_result = {"configured": True, "has_handler": svc_name in known_handlers}
            if svc_name in known_handlers:
                svc_result["handler"] = known_handlers[svc_name].__name__
            else:
                svc_result["handler"] = None
                result["warnings"].append(f"service '{svc_name}' has no registered handler")
            result["services"][svc_name] = svc_result

            interval = cfg.get_interval(svc_name, None)
            if interval is not None and (interval < 1 or interval > 86400):
                result["warnings"].append(
                    f"service '{svc_name}' interval {interval}s is outside recommended range (1-86400)"
                )

            port = cfg.get_port(svc_name, None)
            if port is not None and (port < 1024 or port > 65535):
                result["errors"].append(
                    f"service '{svc_name}' port {port} is outside valid range (1024-65535)"
                )
                result["valid"] = False

        dep_warnings = ServiceDependency.validate_service_graph()
        result["warnings"].extend(dep_warnings)

        if not result["errors"]:
            _log("services configuration validation passed")
        else:
            _log_error("services configuration validation failed")

        return result


# ══════════════════════════════════════════════════════════════
# 13.  Boot Sequence
# ══════════════════════════════════════════════════════════════


BOOT_PROFILES = {
    "minimal": {
        "services": ["persistence", "checkpointer"],
        "delay_between": 1.0,
        "description": "Just persistence and checkpointing",
    },
    "standard": {
        "services": ["persistence", "checkpointer", "daemon", "validation"],
        "delay_between": 2.0,
        "description": "Core services for daily operation",
    },
    "full": {
        "services": ["persistence", "checkpointer", "daemon", "dashboard", "validation"],
        "delay_between": 2.0,
        "description": "All available services",
    },
}


def boot_sequence(profile: str = "standard") -> dict:
    """Execute a boot sequence, starting services in dependency order.

    Profiles:
      - "minimal": just checkpointer + persistence
      - "standard": checkpointer + daemon + validation + persistence
      - "full": all services including dashboard

    Returns a dict with results per service.
    """
    if profile not in BOOT_PROFILES:
        _log_warn(f"unknown profile '{profile}', falling back to 'standard'")
        profile = "standard"

    profile_def = BOOT_PROFILES[profile]
    services_to_start = profile_def["services"]
    delay = profile_def["delay_between"]

    _log(f"boot sequence '{profile}': starting {len(services_to_start)} services")

    ordered = get_ordered_services(services_to_start)
    _log(f"start order: {', '.join(ordered)}")

    mgr = get_service_manager()
    results = {}

    for svc_name in ordered:
        svc = mgr.get_service(svc_name)
        if svc is None:
            _log_warn(f"service '{svc_name}' not registered, skipping")
            results[svc_name] = False
            continue

        _log(f"starting '{svc_name}'...")
        success = svc.start()
        results[svc_name] = success
        if success:
            _log(f"'{svc_name}' started successfully")
        else:
            _log_error(f"'{svc_name}' failed to start")

        time.sleep(delay)

    summary = {
        "profile": profile,
        "total": len(ordered),
        "succeeded": sum(1 for v in results.values() if v),
        "failed": sum(1 for v in results.values() if not v),
        "results": results,
        "timestamp": _get_timestamp(),
    }

    _log(f"boot sequence complete: {summary['succeeded']}/{summary['total']} services up")
    return summary


# ══════════════════════════════════════════════════════════════
# 14.  Recovery Mode
# ══════════════════════════════════════════════════════════════


class RecoveryMode:
    """Recovery mode for FRIDAY bootstrap.

    Stops all services, backs up current state, runs diagnostics,
    and attempts auto-fix of common issues.
    """

    def __init__(self):
        self._diagnostics_history: list[dict] = []
        self._backup_dir = os.path.join(FRIDAY_MEMORY, "recovery_backups")

    def enter_recovery_mode(self) -> dict:
        """Stop all services, back up state, run diagnostics, attempt auto-fix.

        Returns a detailed recovery report.
        """
        _log("entering recovery mode")
        report = {
            "timestamp": _get_timestamp(),
            "recovery_id": str(uuid.uuid4())[:8],
            "steps_taken": [],
            "fixes_applied": [],
            "suggestions": [],
            "diagnostics": {},
            "success": False,
        }

        _log("step 1: stopping all services")
        mgr = get_service_manager()
        stop_results = mgr.stop_all()
        report["steps_taken"].append("stopped all services")
        report["service_stop_results"] = stop_results

        _log("step 2: backing up current state")
        backup_path = self._backup_state()
        if backup_path:
            report["steps_taken"].append(f"state backed up to {backup_path}")
        else:
            report["steps_taken"].append("no state to back up")

        _log("step 3: running diagnostics")
        diagnostics = self.run_diagnostics()
        report["diagnostics"] = diagnostics
        report["steps_taken"].append("ran full diagnostics")

        _log("step 4: attempting auto-fixes")
        fixes = self._auto_fix(diagnostics)
        report["fixes_applied"] = fixes

        _log("step 5: generating suggestions")
        suggestions = self._generate_suggestions(diagnostics)
        report["suggestions"] = suggestions

        report["success"] = len(fixes) > 0 or len(diagnostics.get("errors", [])) == 0
        _log("recovery mode complete")
        return report

    def run_diagnostics(self) -> dict:
        """Run comprehensive diagnostics and return health report + suggestions."""
        diagnostics = {
            "timestamp": _get_timestamp(),
            "environment": StartupValidator.validate_environment(),
            "config_validation": StartupValidator.validate_services_config(),
            "errors": [],
            "warnings": [],
            "info": [],
        }

        env = diagnostics["environment"]
        if not env.get("valid", True):
            diagnostics["errors"].extend(env.get("errors", []))

        cfg = diagnostics["config_validation"]
        if not cfg.get("valid", True):
            diagnostics["errors"].extend(cfg.get("errors", []))

        diagnostics["warnings"].extend(env.get("warnings", []))
        diagnostics["warnings"].extend(cfg.get("warnings", []))

        mem_dir = FRIDAY_MEMORY
        try:
            files = os.listdir(mem_dir)
            diagnostics["info"].append(f"FRIDAY_MEMORY contains {len(files)} entries")
        except OSError as e:
            diagnostics["errors"].append(f"cannot read FRIDAY_MEMORY: {e}")

        config_path = os.path.join(FRIDAY_MEMORY, DEFAULT_CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                cfg_size = os.path.getsize(config_path)
                diagnostics["info"].append(f"config file size: {cfg_size} bytes")
            except OSError:
                pass
        else:
            diagnostics["warnings"].append("config file not found, using defaults")

        state_path = os.path.join(FRIDAY_MEMORY, DEFAULT_STATE_FILE)
        if os.path.exists(state_path):
            state = _read_json(state_path, {})
            saved_pid = state.get("pid")
            if saved_pid and saved_pid != os.getpid():
                diagnostics["warnings"].append(
                    f"stale state file: saved PID {saved_pid} != current PID {os.getpid()}"
                )

        self._diagnostics_history.append(diagnostics)
        return diagnostics

    def _backup_state(self) -> Optional[str]:
        """Back up the current bootstrap state."""
        state_mgr = get_state_manager()
        state = state_mgr.load_state()
        if state is None:
            return None

        os.makedirs(self._backup_dir, exist_ok=True)
        backup_file = os.path.join(
            self._backup_dir, f"state_backup_{_get_timestamp_short()}.json"
        )
        _write_json(backup_file, state)
        return backup_file

    def _auto_fix(self, diagnostics: dict) -> list[str]:
        """Attempt to automatically fix common issues.

        Returns a list of fixes applied.
        """
        fixes = []

        errors = diagnostics.get("errors", [])
        for error in errors:
            if "disk space" in error.lower():
                _log("attempting disk space cleanup")
                count = self._cleanup_temp_files()
                if count > 0:
                    fixes.append(f"cleaned up {count} temporary files to free disk space")

        state_mgr = get_state_manager()
        recovery = state_mgr.recover_stale_state()
        if recovery.get("recovered"):
            fixes.append(f"recovered stale state: {', '.join(recovery['actions_taken'])}")

        log_dir = os.path.join(FRIDAY_MEMORY, DEFAULT_LOG_DIR)
        if os.path.isdir(log_dir):
            try:
                logger = get_logger()
                logger.cleanup_old_logs(keep_days=7)
                fixes.append("cleaned up log files older than 7 days")
            except Exception:
                pass

        return fixes

    def _generate_suggestions(self, diagnostics: dict) -> list[str]:
        """Generate human-readable suggestions based on diagnostics."""
        suggestions = []
        warnings = diagnostics.get("warnings", [])

        for warn in warnings:
            if "optional import" in warn and "psutil" in warn:
                suggestions.append("Install psutil for resource monitoring: pip install psutil")
            if "port" in warn and "in use" in warn:
                suggestions.append("Check for conflicting services using the specified ports")
            if "stale state" in warn:
                suggestions.append("Run recover_stale_state() to clean up orphaned state")

        if not diagnostics.get("environment", {}).get("disk", {}).get("ok", True):
            suggestions.append("Free up disk space in the FRIDAY_MEMORY directory")

        config_path = os.path.join(FRIDAY_MEMORY, DEFAULT_CONFIG_FILE)
        if not os.path.exists(config_path):
            suggestions.append("Save a bootstrap_config.json to customize settings")

        if not suggestions:
            suggestions.append("No issues detected. System appears healthy.")

        return suggestions

    @staticmethod
    def _cleanup_temp_files() -> int:
        """Clean up temporary files in FRIDAY_MEMORY.

        Returns count of removed files.
        """
        count = 0
        patterns_to_clean = [
            r"\.tmp$",
            r"\.temp$",
            r"^_daemon_active\.flag$",
            r"^_dashboard_active\.flag$",
        ]
        try:
            for fname in os.listdir(FRIDAY_MEMORY):
                fpath = os.path.join(FRIDAY_MEMORY, fname)
                if not os.path.isfile(fpath):
                    continue
                for pattern in patterns_to_clean:
                    if re.search(pattern, fname):
                        try:
                            os.remove(fpath)
                            count += 1
                        except OSError:
                            pass
                        break
        except OSError:
            pass
        return count

    def get_diagnostics_history(self) -> list[dict]:
        """Get the history of all diagnostics runs."""
        return list(self._diagnostics_history)


def enter_recovery_mode() -> dict:
    """Enter recovery mode: stop services, back up, diagnose, attempt fixes."""
    rm = RecoveryMode()
    return rm.enter_recovery_mode()


def run_diagnostics() -> dict:
    """Run system diagnostics and return a health report."""
    rm = RecoveryMode()
    return rm.run_diagnostics()


# ══════════════════════════════════════════════════════════════
#  Service Implementations (original + new)
# ══════════════════════════════════════════════════════════════


# ── Service: Self-Improve Daemon ──

def _start_daemon() -> bool:
    """Start self-improve daemon in background thread."""
    try:
        from friday.self_improve_daemon import daemon_start
        daemon_thread = threading.Thread(target=daemon_start, daemon=True, name="self-improve")
        daemon_thread.start()
        pid = os.getpid()
        _touch(os.path.join(FRIDAY_MEMORY, "_daemon_active.flag"), str(pid))
        _log("self-improve daemon started")
        wh = get_webhook_notifier()
        wh.notify_service_start("daemon")
        return True
    except Exception as e:
        _log_error(f"self-improve daemon failed: {e}")
        wh = get_webhook_notifier()
        wh.notify_service_failure("daemon", str(e))
        return False


def _stop_daemon() -> bool:
    """Stop self-improve daemon by removing flag file."""
    daemon_flag = os.path.join(FRIDAY_MEMORY, "_daemon_active.flag")
    if os.path.exists(daemon_flag):
        try:
            os.remove(daemon_flag)
            wh = get_webhook_notifier()
            wh.notify_service_stop("daemon")
            return True
        except Exception:
            return False
    return True


# ── Service: Dashboard Web API ──

def _start_dashboard_api() -> bool:
    """Start dashboard web API in background thread."""
    try:
        from friday.dashboard import start_dashboard
        api_thread = threading.Thread(
            target=start_dashboard,
            daemon=True,
            name="dashboard-api",
        )
        api_thread.start()
        _log("dashboard API started (port 8765)")
        wh = get_webhook_notifier()
        wh.notify_service_start("dashboard")
        return True
    except Exception as e:
        _log_error(f"dashboard API failed: {e}")
        wh = get_webhook_notifier()
        wh.notify_service_failure("dashboard", str(e))
        return False


def _stop_dashboard_api() -> bool:
    """Stop the dashboard API service."""
    try:
        from friday.dashboard import stop_dashboard
        stop_dashboard()
        wh = get_webhook_notifier()
        wh.notify_service_stop("dashboard")
        return True
    except ImportError:
        return True
    except Exception as e:
        _log_error(f"error stopping dashboard: {e}")
        return False


# ── Service: Periodic Checkpointer ──

_checkpointer_stop = threading.Event()


def _checkpoint_loop(interval: int = 300):
    """Periodically checkpoint agent state."""
    checkpoint_dir = os.path.join(FRIDAY_MEMORY, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    while not _checkpointer_stop.is_set():
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "pid": os.getpid(),
                "type": "auto_checkpoint",
            }
            filename = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            path = os.path.join(checkpoint_dir, filename)
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
            _log(f"checkpoint saved: {filename}")
        except Exception as e:
            _log_error(f"checkpoint failed: {e}")

        try:
            files = sorted([f for f in os.listdir(checkpoint_dir) if f.endswith(".json")])
            while len(files) > 24:
                os.remove(os.path.join(checkpoint_dir, files.pop(0)))
        except Exception:
            pass

        _checkpointer_stop.wait(interval)


def _start_checkpointer(interval: Optional[int] = None) -> bool:
    """Start the periodic checkpointing service."""
    if interval is None:
        interval = get_config().get_interval("checkpointer", 300)
    _checkpointer_stop.clear()
    thread = threading.Thread(
        target=_checkpoint_loop,
        args=(interval,),
        daemon=True,
        name="checkpointer",
    )
    thread.start()
    _log(f"checkpointer started (every {interval}s)")
    wh = get_webhook_notifier()
    wh.notify_service_start("checkpointer")
    return True


def _stop_checkpointer() -> bool:
    """Stop the checkpointing service."""
    _checkpointer_stop.set()
    wh = get_webhook_notifier()
    wh.notify_service_stop("checkpointer")
    _log("checkpointer stopped")
    return True


# ── Service: Validation Logger Flush ──

_validation_stop = threading.Event()


def _validation_flush_loop(interval: int = 60):
    """Periodically flush validation log."""
    while not _validation_stop.is_set():
        try:
            from friday.validation_middleware import validation_tool
            validation_tool("stats")
        except Exception:
            pass
        _validation_stop.wait(interval)


def _start_validation_flusher(interval: Optional[int] = None) -> bool:
    """Start the validation log flusher service."""
    if interval is None:
        interval = get_config().get_interval("validation", 60)
    _validation_stop.clear()
    thread = threading.Thread(
        target=_validation_flush_loop,
        args=(interval,),
        daemon=True,
        name="val-flusher",
    )
    thread.start()
    _log("validation flusher started")
    wh = get_webhook_notifier()
    wh.notify_service_start("validation")
    return True


def _stop_validation_flusher() -> bool:
    """Stop the validation flusher."""
    _validation_stop.set()
    wh = get_webhook_notifier()
    wh.notify_service_stop("validation")
    _log("validation flusher stopped")
    return True


# ── Service: Persistence Loop ──

_persistence_stop = threading.Event()


def _persistence_loop(interval: int = 300):
    """Periodically flush agent state to disk."""
    while not _persistence_stop.is_set():
        try:
            from friday.persistence import record_continuity
            record_continuity("periodic_checkpoint", {"interval": interval})
            _log("persistence checkpoint flushed")
        except Exception as e:
            _log_error(f"persistence flush failed: {e}")
        _persistence_stop.wait(interval)


def _start_persistence(interval: Optional[int] = None) -> bool:
    """Start the persistence flush loop."""
    if interval is None:
        interval = get_config().get_interval("persistence", 300)
    _persistence_stop.clear()
    thread = threading.Thread(
        target=_persistence_loop,
        args=(interval,),
        daemon=True,
        name="persistence",
    )
    thread.start()
    _log(f"persistence started (every {interval}s)")
    wh = get_webhook_notifier()
    wh.notify_service_start("persistence")
    return True


def _stop_persistence() -> bool:
    """Stop the persistence loop."""
    _persistence_stop.set()
    wh = get_webhook_notifier()
    wh.notify_service_stop("persistence")
    _log("persistence stopped")
    return True


# ══════════════════════════════════════════════════════════════
#  Register All Services
# ══════════════════════════════════════════════════════════════


def register_default_services():
    """Register all built-in services with the ServiceManager."""
    mgr = get_service_manager()

    mgr.register(Service("persistence", _start_persistence, _stop_persistence, dependencies=[]))
    mgr.register(Service("checkpointer", _start_checkpointer, _stop_checkpointer, dependencies=["persistence"]))
    mgr.register(Service("daemon", _start_daemon, _stop_daemon, dependencies=["persistence"]))
    mgr.register(Service("dashboard", _start_dashboard_api, _stop_dashboard_api, dependencies=["checkpointer"]))
    mgr.register(Service("validation", _start_validation_flusher, _stop_validation_flusher, dependencies=["checkpointer"]))

    _log(f"{mgr.count_services()} services registered")


# ══════════════════════════════════════════════════════════════
#  Config Tool
# ══════════════════════════════════════════════════════════════


def config_tool(action: str = "get", **kwargs) -> str:
    """FRIDAY Bootstrap Configuration Tool.

    Actions:
      get            - Get the full configuration
      get <key>      - Get a specific config value
      set <key> <val> - Set a config value
      save           - Save current configuration to disk
      load           - Reload configuration from disk
      reset          - Reset configuration to defaults
      interval <service> <seconds> - Set service interval
      port <service> <number>      - Set service port
      log-level <level>            - Set log level
      profile <name>               - Set boot profile
      webhook <url>                - Set webhook URL
      auto-restart <true/false>    - Enable/disable auto-restart

    Returns JSON string with result.
    """
    cfg = get_config()

    if action == "get":
        key = kwargs.get("key")
        if key:
            return json.dumps({"key": key, "value": cfg.get(key)}, indent=2)
        return json.dumps(cfg.to_dict(), indent=2)

    elif action == "set":
        key = kwargs.get("key")
        value = kwargs.get("value")
        if key and value is not None:
            cfg.set(key, value)
            return json.dumps({"action": "set", "key": key, "value": value, "status": "saved"})
        return json.dumps({"error": "key and value required"}, indent=2)

    elif action == "save":
        result = cfg.save_config()
        return json.dumps({"action": "save", "status": result}, indent=2)

    elif action == "load":
        cfg.load_config()
        return json.dumps({"action": "load", "status": "configuration reloaded"}, indent=2)

    elif action == "reset":
        result = cfg.reset_to_defaults()
        return json.dumps({"action": "reset", "status": result}, indent=2)

    elif action == "interval":
        service = kwargs.get("service", "")
        seconds = kwargs.get("seconds")
        if service and seconds is not None:
            try:
                cfg.set_interval(service, int(seconds))
                return json.dumps({"action": "interval", "service": service, "interval": int(seconds)}, indent=2)
            except ValueError:
                return json.dumps({"error": "seconds must be an integer"}, indent=2)
        return json.dumps({"error": "service and seconds required"}, indent=2)

    elif action == "port":
        service = kwargs.get("service", "")
        port = kwargs.get("port")
        if service and port is not None:
            try:
                cfg.set_port(service, int(port))
                return json.dumps({"action": "port", "service": service, "port": int(port)}, indent=2)
            except ValueError:
                return json.dumps({"error": "port must be an integer"}, indent=2)
        return json.dumps({"error": "service and port required"}, indent=2)

    elif action == "log-level":
        level = kwargs.get("level", "INFO")
        try:
            cfg.set_log_level(level)
            logger = get_logger()
            logger.set_level(level)
            return json.dumps({"action": "log-level", "level": level.upper()}, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)

    elif action == "profile":
        profile = kwargs.get("profile", "standard")
        try:
            cfg.set_boot_profile(profile)
            return json.dumps({"action": "profile", "profile": profile}, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)

    elif action == "webhook":
        url = kwargs.get("url", "")
        cfg.set_webhook_url(url)
        notifier = get_webhook_notifier()
        result = notifier.configure_webhook(url)
        return json.dumps({"action": "webhook", "url": url, "result": result}, indent=2)

    elif action == "auto-restart":
        enabled = kwargs.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() in ("true", "1", "yes")
        cfg.set_auto_restart(enabled)
        return json.dumps({"action": "auto-restart", "enabled": bool(enabled)}, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)


# ══════════════════════════════════════════════════════════════
#  Bootstrap (original entry points, expanded)
# ══════════════════════════════════════════════════════════════


def start_friday(services: Optional[list[str]] = None, profile: Optional[str] = None) -> dict:
    """Start FRIDAY background services.

    Parameters:
      services: list of service names to start (default: from config profile)
      profile: boot profile name ("minimal", "standard", "full")

    Returns dict with status of each service.
    """
    if services is None:
        if profile:
            cfg_profile = profile
        else:
            cfg_profile = get_config().get_boot_profile()
        profile_def = BOOT_PROFILES.get(cfg_profile, BOOT_PROFILES["standard"])
        services = profile_def["services"]

    _log(f"FRIDAY Bootstrap: starting {len(services)} service(s)")

    env_check = StartupValidator.validate_environment()
    if not env_check.get("valid", True):
        _log_warn("environment checks have warnings, proceeding anyway")

    state_mgr = get_state_manager()
    state_mgr.recover_stale_state()

    register_default_services()

    ordered = get_ordered_services(services)
    mgr = get_service_manager()
    results = mgr.start_all(ordered)

    hm = get_health_monitor()
    if not hm.is_alive():
        hm.start()

    rm = get_resource_monitor()
    if not rm.is_alive():
        rm.start()

    scheduler = get_task_scheduler()
    if not scheduler.is_alive():
        scheduler.start()

    wh = get_webhook_notifier()
    wh.start()

    start_control_server()

    try:
        state_mgr.save_state()
    except Exception as e:
        _log_error(f"state save failed: {e}")

    _log(f"services started: {sum(1 for v in results.values() if v)}/{len(results)}")
    return results


def stop_friday() -> dict:
    """Signal FRIDAY background services to stop."""
    result = graceful_shutdown()
    return result


def status_friday() -> dict:
    """Get the full status of all FRIDAY services."""
    mgr = get_service_manager()
    hm = get_health_monitor()
    rm = get_resource_monitor()
    wh = get_webhook_notifier()

    return {
        "timestamp": _get_timestamp(),
        "pid": os.getpid(),
        "version": BOOTSTRAP_VERSION,
        "services": mgr.get_all_status(),
        "health": hm.get_health_report() if hm.is_alive() else {"status": "not_running"},
        "resources": rm.get_resource_report() if rm.is_alive() else {"status": "not_running"},
        "scheduled_tasks": get_task_scheduler().list_scheduled_tasks(),
        "webhook": wh.get_status(),
        "config": get_config().to_dict(),
        "log_stats": get_logger().get_stats(),
    }


# ══════════════════════════════════════════════════════════════
#  Bootstrap Tool (dispatcher)
# ══════════════════════════════════════════════════════════════


def bootstrap_tool(action: str = "start", **kwargs) -> str:
    """FRIDAY Bootstrap — manage background services.

    Actions:
      start [services=...] [profile=...]   - Start background services
      stop                                  - Stop background services
      restart <service>                     - Restart a specific service
      status                                - Show full service status
      health                                - Show health report
      resources                             - Show resource report

    Config actions:
      config <sub_action> [params...]       - Configuration management

    Scheduled task actions:
      schedule <name> <interval_sec>        - Schedule a recurring task
      unschedule <name>                     - Remove a scheduled task
      tasks                                 - List scheduled tasks

    Logging actions:
      logs [count=50]                       - Get recent log entries
      log-level <level>                     - Set log level

    State actions:
      save-state                            - Save current state
      recover-state                         - Recover from stale state

    Webhook actions:
      webhook <url>                         - Configure webhook
      test-webhook                          - Test webhook configuration

    Diagnostic actions:
      validate                              - Validate environment/config
      diagnostics                           - Run full diagnostics
      recovery                              - Enter recovery mode
    """
    if action == "start":
        svcs_str = kwargs.get("services", "")
        services = [s.strip() for s in svcs_str.split(",") if s.strip()] if svcs_str else None
        profile = kwargs.get("profile")
        result = start_friday(services, profile=profile)
        return json.dumps(result, indent=2)

    elif action == "stop":
        result = stop_friday()
        return json.dumps(result, indent=2)

    elif action == "restart":
        service_name = kwargs.get("service", kwargs.get("name", ""))
        if not service_name:
            return json.dumps({"error": "service name required"}, indent=2)
        mgr = get_service_manager()
        success = mgr.restart_service(service_name)
        return json.dumps({"action": "restart", "service": service_name, "success": success}, indent=2)

    elif action == "status":
        result = status_friday()
        return json.dumps(result, indent=2, default=str)

    elif action == "health":
        hm = get_health_monitor()
        if hm.is_alive():
            report = hm.get_health_report()
        else:
            report = {"status": "not_running"}
        return json.dumps(report, indent=2, default=str)

    elif action == "resources":
        rm = get_resource_monitor()
        if rm.is_alive():
            report = rm.get_resource_report()
        else:
            report = {"status": "not_running"}
        return json.dumps(report, indent=2, default=str)

    elif action == "config":
        sub = kwargs.get("sub_action", kwargs.get("sub", "get"))
        return config_tool(sub, **{k: v for k, v in kwargs.items() if k not in ("sub_action", "sub")})

    elif action == "schedule":
        name = kwargs.get("name", "")
        interval = kwargs.get("interval", kwargs.get("interval_sec", kwargs.get("seconds", 0)))
        func_name = kwargs.get("func", kwargs.get("function", ""))
        if not name or not interval:
            return json.dumps({"error": "name and interval required"}, indent=2)
        try:
            interval = float(interval)
        except ValueError:
            return json.dumps({"error": "interval must be a number"}, indent=2)

        def _noop():
            pass

        target_func = _noop
        if func_name:
            try:
                parts = func_name.split(".")
                mod = __import__(".".join(parts[:-1]), fromlist=[parts[-1]])
                target_func = getattr(mod, parts[-1])
            except (ImportError, AttributeError, IndexError):
                pass

        scheduler = get_task_scheduler()
        result = scheduler.schedule_task(name, interval, target_func)
        return json.dumps({"action": "schedule", "result": result}, indent=2)

    elif action == "unschedule":
        name = kwargs.get("name", "")
        scheduler = get_task_scheduler()
        result = scheduler.unschedule_task(name)
        return json.dumps({"action": "unschedule", "result": result}, indent=2)

    elif action == "tasks":
        scheduler = get_task_scheduler()
        tasks = scheduler.list_scheduled_tasks()
        return json.dumps({"scheduled_tasks": tasks}, indent=2, default=str)

    elif action == "logs":
        count = int(kwargs.get("count", 50))
        logger = get_logger()
        logs = logger.get_recent_logs(count)
        return json.dumps({"logs": logs}, indent=2, default=str)

    elif action == "log-level":
        level = kwargs.get("level", "INFO")
        cfg = get_config()
        try:
            cfg.set_log_level(level)
            logger = get_logger()
            logger.set_level(level)
            return json.dumps({"action": "log-level", "level": level.upper()}, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e)}, indent=2)

    elif action == "save-state":
        state_mgr = get_state_manager()
        result = state_mgr.save_state()
        return json.dumps({"action": "save-state", "result": result}, indent=2)

    elif action == "recover-state":
        state_mgr = get_state_manager()
        report = state_mgr.recover_stale_state()
        return json.dumps(report, indent=2, default=str)

    elif action == "webhook":
        url = kwargs.get("url", "")
        cfg = get_config()
        cfg.set_webhook_url(url)
        notifier = get_webhook_notifier()
        result = notifier.configure_webhook(url)
        return json.dumps({"action": "webhook", "url": url, "result": result}, indent=2)

    elif action == "test-webhook":
        notifier = get_webhook_notifier()
        result = notifier.test_webhook()
        return json.dumps(result, indent=2, default=str)

    elif action == "validate":
        env = StartupValidator.validate_environment()
        svc = StartupValidator.validate_services_config()
        return json.dumps({"environment": env, "services_config": svc}, indent=2, default=str)

    elif action == "diagnostics":
        diag = run_diagnostics()
        return json.dumps(diag, indent=2, default=str)

    elif action == "recovery":
        report = enter_recovery_mode()
        return json.dumps(report, indent=2, default=str)

    elif action == "shutdown":
        result = graceful_shutdown()
        return json.dumps(result, indent=2, default=str)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)


# ══════════════════════════════════════════════════════════════
#  Initialization / Auto-setup
# ══════════════════════════════════════════════════════════════


def init_bootstrap():
    """Initialize the bootstrap system on module load.

    Registers services, installs signal handlers, recovers stale state.
    """
    get_config()
    register_default_services()
    install_signal_handlers()
    state_mgr = get_state_manager()
    state_mgr.recover_stale_state()
    _log("bootstrap initialized")


# Auto-initialize on import
init_bootstrap()


# ══════════════════════════════════════════════════════════════
#  CLI Entry Point
# ══════════════════════════════════════════════════════════════


def main():
    """CLI entry point for bootstrap management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="FRIDAY Bootstrap - Manage background services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python -m friday.bootstrap start
              python -m friday.bootstrap start --services daemon,dashboard
              python -m friday.bootstrap stop
              python -m friday.bootstrap status
              python -m friday.bootstrap config get
              python -m friday.bootstrap config set log_level DEBUG
              python -m friday.bootstrap health
              python -m friday.bootstrap recovery
        """),
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="start",
        help="Action to perform (start, stop, status, restart, health, resources, "
             "config, validate, diagnostics, recovery, logs, tasks, save-state, "
             "test-webhook)",
    )

    parser.add_argument("--services", "-s", default="", help="Comma-separated list of services")
    parser.add_argument("--profile", "-p", default="", help="Boot profile (minimal, standard, full)")
    parser.add_argument("--service", default="", help="Service name for restart")
    parser.add_argument("--name", default="", help="Task name for schedule/unschedule")
    parser.add_argument("--interval", "-i", type=float, default=0, help="Interval in seconds")
    parser.add_argument("--count", "-c", type=int, default=50, help="Number of log entries")
    parser.add_argument("--level", default="", help="Log level")
    parser.add_argument("--url", default="", help="Webhook URL")
    parser.add_argument("--key", default="", help="Config key")
    parser.add_argument("--value", default="", help="Config value")
    parser.add_argument("--port", type=int, default=0, help="Port number")
    parser.add_argument("--sub", default="", help="Config sub-action")
    parser.add_argument("--seconds", type=int, default=0, help="Interval for config tool")
    parser.add_argument("--enabled", default="", help="Enable/disable flag")
    parser.add_argument("--func", default="", help="Function path for scheduled task")
    parser.add_argument("--daemon", action="store_true", help="Run as persistent daemon")

    args = parser.parse_args()

    kwargs = {}
    if args.services:
        kwargs["services"] = args.services
    if args.profile:
        kwargs["profile"] = args.profile
    if args.service:
        kwargs["service"] = args.service
    if args.name:
        kwargs["name"] = args.name
    if args.interval:
        kwargs["interval"] = args.interval
    if args.count:
        kwargs["count"] = args.count
    if args.level:
        kwargs["level"] = args.level
    if args.url:
        kwargs["url"] = args.url
    if args.key:
        kwargs["key"] = args.key
    if args.value:
        kwargs["value"] = args.value
    if args.port:
        kwargs["port"] = args.port
    if args.sub:
        kwargs["sub"] = args.sub
    if args.seconds:
        kwargs["seconds"] = args.seconds
    if args.enabled:
        kwargs["enabled"] = args.enabled
    if args.func:
        kwargs["func"] = args.func

    if args.action == "restart":
        kwargs["action"] = "restart"
        result = bootstrap_tool("restart", **kwargs)
    elif args.action in ("start", "stop", "status", "health", "resources", "tasks",
                         "save-state", "recover-state", "test-webhook", "validate",
                         "diagnostics", "recovery", "shutdown"):
        result = bootstrap_tool(args.action, **kwargs)
    elif args.action == "config":
        sub = args.sub or kwargs.get("sub", "get")
        result = config_tool(sub, **kwargs)
    elif args.action == "logs":
        result = bootstrap_tool("logs", count=args.count)
    elif args.action == "webhook":
        result = bootstrap_tool("webhook", url=args.url)
    elif args.action == "log-level":
        result = bootstrap_tool("log-level", level=args.level or "INFO")
    elif args.action == "schedule":
        result = bootstrap_tool("schedule",
                                name=args.name,
                                interval=args.interval,
                                func=args.func)
    elif args.action == "unschedule":
        result = bootstrap_tool("unschedule", name=args.name)
    else:
        result = bootstrap_tool(args.action, **kwargs)

    print(result)


if __name__ == "__main__":
    main()
