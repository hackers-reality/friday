"""FRIDAY Metrics Collector — system and application metrics with time series and aggregation."""
import os
import json
import time
import threading
import psutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from datetime import datetime


@dataclass
class MetricPoint:
    timestamp: float
    name: str
    value: float
    tags: Dict = field(default_factory=dict)
    unit: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class MetricSummary:
    name: str
    count: int
    min: float
    max: float
    mean: float
    median: float
    p95: float
    p99: float
    sum: float
    last: float

    def to_dict(self):
        return asdict(self)


class TimeSeriesBuffer:
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self._data: deque = deque(maxlen=max_points)
        self._lock = threading.Lock()

    def add(self, point: MetricPoint):
        with self._lock:
            self._data.append(point)

    def query(self, start: float = 0, end: float = 0, limit: int = 1000,
              tags: Dict = None) -> List[Dict]:
        with self._lock:
            points = list(self._data)

        if start > 0:
            points = [p for p in points if p.timestamp >= start]
        if end > 0:
            points = [p for p in points if p.timestamp <= end]
        if tags:
            points = [p for p in points if all(p.tags.get(k) == v for k, v in tags.items())]

        return [p.to_dict() for p in points[-limit:]]

    def get_latest(self, name: str = None) -> Optional[Dict]:
        with self._lock:
            if name:
                for p in reversed(self._data):
                    if p.name == name:
                        return p.to_dict()
            elif self._data:
                return self._data[-1].to_dict()
        return None

    def size(self) -> int:
        with self._lock:
            return len(self._data)


class MetricsCollector:
    def __init__(self, data_dir: str = None, buffer_size: int = 50000):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "metrics")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._buffer = TimeSeriesBuffer(max_points=buffer_size)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._collectors: Dict[str, callable] = {}

        self._register_system_collectors()

    def _register_system_collectors(self):
        self._collectors["system_cpu"] = self._collect_cpu
        self._collectors["system_memory"] = self._collect_memory
        self._collectors["system_disk"] = self._collect_disk
        self._collectors["system_network"] = self._collect_network
        self._collectors["system_processes"] = self._collect_processes

    def _collect_cpu(self) -> Dict:
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "cpu_count": psutil.cpu_count(),
                "load_avg": list(os.getloadavg()) if hasattr(os, "getloadavg") else [0, 0, 0],
            }
        except Exception:
            return {}

    def _collect_memory(self) -> Dict:
        try:
            mem = psutil.virtual_memory()
            return {
                "memory_total_gb": round(mem.total / 1024**3, 2),
                "memory_used_gb": round(mem.used / 1024**3, 2),
                "memory_percent": mem.percent,
                "memory_available_gb": round(mem.available / 1024**3, 2),
            }
        except Exception:
            return {}

    def _collect_disk(self) -> Dict:
        try:
            path = "C:\\" if os.name == "nt" else "/"
            usage = psutil.disk_usage(path)
            return {
                "disk_total_gb": round(usage.total / 1024**3, 2),
                "disk_used_gb": round(usage.used / 1024**3, 2),
                "disk_percent": usage.percent,
                "disk_free_gb": round(usage.free / 1024**3, 2),
            }
        except Exception:
            return {}

    def _collect_network(self) -> Dict:
        try:
            net = psutil.net_io_counters()
            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
            }
        except Exception:
            return {}

    def _collect_processes(self) -> Dict:
        try:
            return {
                "process_count": len(psutil.pids()),
                "thread_count": threading.active_count(),
            }
        except Exception:
            return {}

    def record(self, name: str, value: float, tags: Dict = None, unit: str = ""):
        point = MetricPoint(
            timestamp=time.time(),
            name=name,
            value=value,
            tags=tags or {},
            unit=unit,
        )
        self._buffer.add(point)

    def counter(self, name: str, increment: float = 1):
        with self._lock:
            self._counters[name] += increment
        self.record(name, self._counters[name], unit="counter")

    def gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = value
        self.record(name, value, unit="gauge")

    def histogram(self, name: str, value: float):
        with self._lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 10000:
                self._histograms[name] = self._histograms[name][-10000:]
        self.record(name, value, unit="histogram")

    def timing(self, name: str, duration_ms: float):
        self.histogram(name, duration_ms)
        self.record(f"{name}_ms", duration_ms, unit="ms")

    def collect_system_metrics(self) -> Dict:
        all_metrics = {}
        for name, collector in self._collectors.items():
            if name.startswith("system_"):
                metrics = collector()
                all_metrics[name] = metrics
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        self.gauge(f"system.{key}", value)
        return all_metrics

    def query(self, name: str = None, start: float = 0, end: float = 0,
              limit: int = 1000, tags: Dict = None) -> List[Dict]:
        return self._buffer.query(start, end, limit, tags)

    def get_latest(self, name: str = None) -> Optional[Dict]:
        return self._buffer.get_latest(name)

    def get_counter(self, name: str) -> float:
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        with self._lock:
            return self._gauges.get(name)

    def get_histogram(self, name: str) -> Optional[Dict]:
        with self._lock:
            values = self._histograms.get(name)
            if not values:
                return None
            sorted_vals = sorted(values)
            count = len(sorted_vals)
            return {
                "count": count,
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "mean": sum(sorted_vals) / count,
                "median": sorted_vals[count // 2],
                "p95": sorted_vals[int(count * 0.95)] if count > 20 else sorted_vals[-1],
                "p99": sorted_vals[int(count * 0.99)] if count > 100 else sorted_vals[-1],
                "sum": sum(sorted_vals),
            }

    def get_all_counters(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._counters)

    def get_all_gauges(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._gauges)

    def get_all_histograms(self) -> Dict[str, Dict]:
        with self._lock:
            names = list(self._histograms.keys())
        return {name: self.get_histogram(name) for name in names}

    def get_summary(self) -> Dict:
        return {
            "buffer_size": self._buffer.size(),
            "counters": len(self._counters),
            "gauges": len(self._gauges),
            "histograms": len(self._histograms),
            "collectors": len(self._collectors),
        }

    def get_dashboard(self) -> Dict:
        return {
            "system": self.collect_system_metrics(),
            "counters": self.get_all_counters(),
            "gauges": self.get_all_gauges(),
            "summary": self.get_summary(),
        }

    def export_json(self, path: str = None) -> str:
        data = {
            "counters": self.get_all_counters(),
            "gauges": self.get_all_gauges(),
            "histograms": self.get_all_histograms(),
            "exported_at": time.time(),
        }
        if path:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        return json.dumps(data, indent=2, default=str)

    def clear(self):
        self._buffer = TimeSeriesBuffer(max_points=self._buffer.max_points)
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


_collector = None


def _get_collector() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def metrics_collector_tool(action: str = "dashboard", **kwargs) -> Any:
    """Metrics collector tool dispatcher."""
    try:
        collector = _get_collector()

        if action == "dashboard":
            return collector.get_dashboard()

        elif action == "record":
            name = kwargs.get("name", "")
            value = kwargs.get("value", 0)
            tags = kwargs.get("tags", {})
            unit = kwargs.get("unit", "")
            if not name:
                return {"error": "No name provided"}
            collector.record(name, float(value), tags, unit)
            return {"success": True}

        elif action == "counter":
            name = kwargs.get("name", "")
            increment = kwargs.get("increment", 1)
            if not name:
                return {"error": "No name provided"}
            collector.counter(name, float(increment))
            return {"success": True, "value": collector.get_counter(name)}

        elif action == "gauge":
            name = kwargs.get("name", "")
            value = kwargs.get("value", 0)
            if not name:
                return {"error": "No name provided"}
            collector.gauge(name, float(value))
            return {"success": True}

        elif action == "histogram":
            name = kwargs.get("name", "")
            value = kwargs.get("value", 0)
            if not name:
                return {"error": "No name provided"}
            collector.histogram(name, float(value))
            return {"success": True, "stats": collector.get_histogram(name)}

        elif action == "query":
            name = kwargs.get("name")
            start = kwargs.get("start", 0)
            end = kwargs.get("end", 0)
            limit = kwargs.get("limit", 1000)
            tags = kwargs.get("tags")
            results = collector.query(name, start, end, limit, tags)
            return {"metrics": results, "count": len(results)}

        elif action == "latest":
            name = kwargs.get("name")
            result = collector.get_latest(name)
            return result or {"error": "No metrics found"}

        elif action == "counters":
            return {"counters": collector.get_all_counters()}

        elif action == "gauges":
            return {"gauges": collector.get_all_gauges()}

        elif action == "histograms":
            return {"histograms": collector.get_all_histograms()}

        elif action == "summary":
            return collector.get_summary()

        elif action == "collect_system":
            return collector.collect_system_metrics()

        elif action == "export":
            path = kwargs.get("path")
            return {"json": collector.export_json(path)}

        elif action == "clear":
            collector.clear()
            return {"success": True}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
