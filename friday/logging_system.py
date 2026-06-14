"""FRIDAY Logging System — structured logging with rotation, filtering, and analysis."""
import os
import json
import time
import logging
import hashlib
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime


class LogLevel:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    NAMES = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}
    NAME_MAP = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}


@dataclass
class LogEntry:
    timestamp: float
    level: str
    message: str
    module: str
    function: str
    line: int
    extra: Dict = field(default_factory=dict)
    source: str = "system"
    correlation_id: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class LogStats:
    total_entries: int
    by_level: Dict[str, int]
    by_module: Dict[str, int]
    by_source: Dict[str, int]
    error_rate: float
    avg_entries_per_minute: float
    time_range: Dict[str, float]

    def to_dict(self):
        return asdict(self)


class LogBuffer:
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add(self, entry: LogEntry):
        with self._lock:
            self._buffer.append(entry)

    def get_recent(self, count: int = 100) -> List[Dict]:
        with self._lock:
            items = list(self._buffer)
        return [e.to_dict() for e in items[-count:]]

    def search(self, query: str, level: str = None, limit: int = 100) -> List[Dict]:
        with self._lock:
            items = list(self._buffer)
        results = []
        for entry in reversed(items):
            if level and entry.level != level:
                continue
            if query.lower() in entry.message.lower() or query.lower() in entry.module.lower():
                results.append(entry.to_dict())
                if len(results) >= limit:
                    break
        return results

    def get_by_level(self, level: str, limit: int = 100) -> List[Dict]:
        with self._lock:
            items = list(self._buffer)
        return [e.to_dict() for e in items if e.level == level][-limit:]

    def get_by_module(self, module: str, limit: int = 100) -> List[Dict]:
        with self._lock:
            items = list(self._buffer)
        return [e.to_dict() for e in items if module in e.module][-limit:]

    def get_errors(self, limit: int = 100) -> List[Dict]:
        return self.get_by_level("ERROR", limit) + self.get_by_level("CRITICAL", limit)

    def clear(self):
        with self._lock:
            self._buffer.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)


class LogFileWriter:
    def __init__(self, log_dir: str, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = threading.Lock()
        os.makedirs(log_dir, exist_ok=True)

    def _get_log_path(self, name: str = "friday") -> str:
        return os.path.join(self.log_dir, f"{name}.log")

    def _rotate(self, path: str):
        if not os.path.exists(path):
            return
        if os.path.getsize(path) < self.max_bytes:
            return
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{path}.{i}"
            dst = f"{path}.{i + 1}"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        if os.path.exists(path):
            dst = f"{path}.1"
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(path, dst)

    def write(self, entry: LogEntry, name: str = "friday"):
        with self._lock:
            path = self._get_log_path(name)
            self._rotate(path)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    line = f"[{entry.timestamp:.3f}] [{entry.level}] [{entry.module}] {entry.message}"
                    if entry.extra:
                        line += f" | {json.dumps(entry.extra, default=str)}"
                    f.write(line + "\n")
            except Exception:
                pass

    def write_json(self, entry: LogEntry, name: str = "friday_json"):
        with self._lock:
            path = self._get_log_path(name)
            self._rotate(path)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict(), default=str) + "\n")
            except Exception:
                pass

    def read_lines(self, name: str = "friday", count: int = 100) -> List[str]:
        path = self._get_log_path(name)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return [l.rstrip() for l in lines[-count:]]
        except Exception:
            return []

    def get_files(self) -> List[Dict]:
        files = []
        if os.path.exists(self.log_dir):
            for fname in os.listdir(self.log_dir):
                fpath = os.path.join(self.log_dir, fname)
                if os.path.isfile(fpath):
                    files.append({
                        "name": fname,
                        "size": os.path.getsize(fpath),
                        "modified": os.path.getmtime(fpath),
                    })
        return sorted(files, key=lambda x: x["modified"], reverse=True)

    def clear(self, name: str = "friday"):
        path = self._get_log_path(name)
        if os.path.exists(path):
            os.remove(path)


class FridayLogger:
    def __init__(self, name: str = "friday", log_dir: str = None, level: int = LogLevel.INFO):
        self.name = name
        self.level = level
        self.buffer = LogBuffer(max_size=50000)
        self._source = name

        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), ".friday", "logs")
        self.writer = LogFileWriter(log_dir)
        self._lock = threading.Lock()
        self._correlation_id = ""

    def set_correlation_id(self, cid: str):
        self._correlation_id = cid

    def _log(self, level: int, message: str, module: str = "", function: str = "", line: int = 0, extra: Dict = None):
        if level < self.level:
            return

        level_name = LogLevel.NAMES.get(level, "UNKNOWN")
        entry = LogEntry(
            timestamp=time.time(),
            level=level_name,
            message=message,
            module=module or self.name,
            function=function,
            line=line,
            extra=extra or {},
            source=self._source,
            correlation_id=self._correlation_id,
        )

        self.buffer.add(entry)
        self.writer.write(entry, self.name)
        self.writer.write_json(entry, self.name)

    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def exception(self, message: str, exc: Exception = None, **kwargs):
        extra = kwargs.get("extra", {})
        if exc:
            extra["exception"] = str(exc)
            extra["exception_type"] = type(exc).__name__
        self._log(LogLevel.ERROR, message, extra=extra, **kwargs)

    def get_recent(self, count: int = 100) -> List[Dict]:
        return self.buffer.get_recent(count)

    def search(self, query: str, level: str = None, limit: int = 100) -> List[Dict]:
        return self.buffer.search(query, level, limit)

    def get_errors(self, limit: int = 100) -> List[Dict]:
        return self.buffer.get_errors(limit)

    def get_stats(self) -> Dict:
        with self._lock:
            entries = self.buffer.get_recent(10000)
            if not entries:
                return {"total": 0, "by_level": {}, "by_module": {}, "error_rate": 0}

            by_level = defaultdict(int)
            by_module = defaultdict(int)
            by_source = defaultdict(int)
            for e in entries:
                by_level[e["level"]] += 1
                by_module[e["module"]] += 1
                by_source[e["source"]] += 1

            total = len(entries)
            errors = by_level.get("ERROR", 0) + by_level.get("CRITICAL", 0)
            time_range = {
                "start": entries[0]["timestamp"] if entries else 0,
                "end": entries[-1]["timestamp"] if entries else 0,
            }
            duration = time_range["end"] - time_range["start"]
            avg_per_min = (total / (duration / 60)) if duration > 0 else total

            return {
                "total": total,
                "by_level": dict(by_level),
                "by_module": dict(by_module),
                "by_source": dict(by_source),
                "error_rate": round(errors / total * 100, 2) if total > 0 else 0,
                "avg_per_minute": round(avg_per_min, 2),
                "time_range": time_range,
            }

    def get_log_files(self) -> List[Dict]:
        return self.writer.get_files()

    def clear(self):
        self.buffer.clear()
        self.writer.clear(self.name)


_loggers: Dict[str, FridayLogger] = {}
_lock = threading.Lock()


def get_logger(name: str = "friday", level: int = LogLevel.INFO) -> FridayLogger:
    with _lock:
        if name not in _loggers:
            _loggers[name] = FridayLogger(name=name, level=level)
        return _loggers[name]


def logging_tool(action: str = "log", **kwargs) -> Any:
    """Logging system tool dispatcher."""
    try:
        logger = get_logger(kwargs.get("logger", "friday"))

        if action == "log":
            level = kwargs.get("level", "info").upper()
            message = kwargs.get("message", "")
            module = kwargs.get("module", "")
            extra = kwargs.get("extra", {})

            if not message:
                return {"error": "No message provided"}

            log_fn = getattr(logger, level.lower(), logger.info)
            log_fn(message, module=module, extra=extra)
            return {"success": True, "level": level}

        elif action == "get_recent":
            count = kwargs.get("count", 100)
            return {"entries": logger.get_recent(count), "count": count}

        elif action == "search":
            query = kwargs.get("query", "")
            level = kwargs.get("level")
            limit = kwargs.get("limit", 100)
            if not query:
                return {"error": "No query provided"}
            results = logger.search(query, level, limit)
            return {"results": results, "count": len(results)}

        elif action == "get_errors":
            limit = kwargs.get("limit", 100)
            errors = logger.get_errors(limit)
            return {"errors": errors, "count": len(errors)}

        elif action == "stats":
            return logger.get_stats()

        elif action == "files":
            return {"files": logger.get_log_files()}

        elif action == "clear":
            logger.clear()
            return {"success": True}

        elif action == "set_level":
            level_name = kwargs.get("level", "INFO").upper()
            level = LogLevel.NAME_MAP.get(level_name.lower(), LogLevel.INFO)
            logger.level = level
            return {"success": True, "level": level_name}

        elif action == "correlation":
            cid = kwargs.get("id", hashlib.md5(str(time.time()).encode()).hexdigest()[:8])
            logger.set_correlation_id(cid)
            return {"correlation_id": cid}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
