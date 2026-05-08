"""
Friday Monitor - System monitoring and alerts.
Real-time monitoring, alerts, logging, performance metrics.
"""
from __future__ import annotations

import os
import time
import threading
import psutil
from datetime import datetime


class SystemMonitor:
    """Monitor system resources and active processes."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._interval = 60
        self._alerts = []
        self._cpu_threshold = 90
        self._mem_threshold = 90

    def get_status(self) -> str:
        """Return current system status."""
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        processes = len(psutil.pids())
        boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
        lines = [
            f"[OK] System Monitor Status",
            f"CPU: {cpu}% | RAM: {mem}% | Disk: {disk}%",
            f"Processes: {processes} | Boot: {boot_time}",
            f"Running: {self._running}",
        ]
        return "\n".join(lines)

    def start(self, interval: int = 60) -> str:
        """Start background monitoring."""
        if self._running:
            return "[OK] Monitor already running"
        self._interval = interval
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return f"[OK] Monitor started (interval={interval}s)"

    def stop(self) -> str:
        """Stop background monitoring."""
        self._running = False
        return "[OK] Monitor stopped"

    def _loop(self):
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                if cpu > self._cpu_threshold:
                    self._alerts.append(f"High CPU: {cpu}%")
                if mem > self._mem_threshold:
                    self._alerts.append(f"High Memory: {mem}%")
            except Exception:
                pass
            time.sleep(self._interval)


monitor = SystemMonitor()


def get_monitor_status() -> str:
    return monitor.get_status()


def start_monitor(interval: int = 60) -> str:
    return monitor.start(interval)


def stop_monitor() -> str:
    return monitor.stop()
