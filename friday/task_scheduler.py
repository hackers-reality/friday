"""FRIDAY Task Scheduler — cron-like scheduling with persistence and execution tracking."""
import os
import json
import time
import uuid
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class Schedule:
    type: str
    interval_seconds: int = 0
    cron_expr: str = ""
    daily_time: str = ""
    weekly_days: List[int] = field(default_factory=list)
    once_at: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class Task:
    task_id: str
    name: str
    description: str
    schedule: Dict
    action: str
    params: Dict = field(default_factory=dict)
    enabled: bool = True
    created_at: float = 0.0
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0
    last_result: str = ""
    last_error: str = ""
    timeout: int = 300
    retries: int = 3
    retry_delay: int = 60
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class TaskRun:
    run_id: str
    task_id: str
    started_at: float
    finished_at: float = 0.0
    duration: float = 0.0
    success: bool = False
    result: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


class ScheduleParser:
    @staticmethod
    def parse_interval(seconds: int, start_at: float = 0) -> float:
        if start_at <= 0:
            start_at = time.time() + seconds
        return start_at

    @staticmethod
    def parse_daily(time_str: str) -> float:
        try:
            now = datetime.now()
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.timestamp()
        except Exception:
            return time.time() + 86400

    @staticmethod
    def parse_weekly(time_str: str, days: List[int]) -> float:
        try:
            now = datetime.now()
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            current_weekday = now.weekday()
            days_ahead = 7
            for day in days:
                if day > current_weekday:
                    days_ahead = min(days_ahead, day - current_weekday)
                elif day == current_weekday and target > now:
                    days_ahead = 0
                    break
                else:
                    days_ahead = min(days_ahead, 7 - current_weekday + day)
            target += timedelta(days=days_ahead)
            return target.timestamp()
        except Exception:
            return time.time() + 604800

    @staticmethod
    def parse_cron(expr: str) -> float:
        return time.time() + 3600

    @staticmethod
    def next_run(schedule: Dict) -> float:
        sched_type = schedule.get("type", "interval")
        if sched_type == "interval":
            return ScheduleParser.parse_interval(
                schedule.get("interval_seconds", 3600),
                schedule.get("start_at", 0),
            )
        elif sched_type == "daily":
            return ScheduleParser.parse_daily(schedule.get("daily_time", "00:00"))
        elif sched_type == "weekly":
            return ScheduleParser.parse_weekly(
                schedule.get("daily_time", "00:00"),
                schedule.get("weekly_days", [0]),
            )
        elif sched_type == "once":
            return schedule.get("once_at", time.time() + 3600)
        elif sched_type == "cron":
            return ScheduleParser.parse_cron(schedule.get("cron_expr", "* * * * *"))
        return time.time() + 3600


class TaskScheduler:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "scheduler")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._tasks: Dict[str, Task] = {}
        self._runs: Dict[str, List[TaskRun]] = defaultdict(list)
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._load_tasks()
        self._load_runs()

    def _tasks_file(self) -> str:
        return os.path.join(self.data_dir, "tasks.json")

    def _runs_file(self) -> str:
        return os.path.join(self.data_dir, "runs.json")

    def _load_tasks(self):
        if os.path.exists(self._tasks_file()):
            try:
                with open(self._tasks_file(), "r") as f:
                    data = json.load(f)
                for tid, tdata in data.items():
                    self._tasks[tid] = Task(**tdata)
            except Exception:
                pass

    def _save_tasks(self):
        try:
            data = {tid: t.to_dict() for tid, t in self._tasks.items()}
            with open(self._tasks_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _load_runs(self):
        if os.path.exists(self._runs_file()):
            try:
                with open(self._runs_file(), "r") as f:
                    data = json.load(f)
                for tid, runs in data.items():
                    self._runs[tid] = [TaskRun(**r) for r in runs[-100:]]
            except Exception:
                pass

    def _save_runs(self):
        try:
            data = {tid: [r.to_dict() for r in runs[-100:]] for tid, runs in self._runs.items()}
            with open(self._runs_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def register_handler(self, action: str, handler: Callable):
        self._handlers[action] = handler

    def add_task(self, name: str, schedule: Dict, action: str, params: Dict = None,
                 description: str = "", timeout: int = 300, retries: int = 3,
                 tags: List[str] = None) -> Task:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        now = time.time()
        task = Task(
            task_id=task_id,
            name=name,
            description=description,
            schedule=schedule,
            action=action,
            params=params or {},
            enabled=True,
            created_at=now,
            next_run=ScheduleParser.next_run(schedule),
            timeout=timeout,
            retries=retries,
            tags=tags or [],
        )
        with self._lock:
            self._tasks[task_id] = task
            self._save_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            if "schedule" in kwargs:
                task.next_run = ScheduleParser.next_run(task.schedule)
            self._save_tasks()
            return True

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._runs.pop(task_id, None)
                self._save_tasks()
                self._save_runs()
                return True
            return False

    def enable_task(self, task_id: str) -> bool:
        return self.update_task(task_id, enabled=True)

    def disable_task(self, task_id: str) -> bool:
        return self.update_task(task_id, enabled=False)

    def list_tasks(self, enabled_only: bool = False, tags: List[str] = None) -> List[Dict]:
        with self._lock:
            tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        return [t.to_dict() for t in sorted(tasks, key=lambda t: t.next_run)]

    def get_runs(self, task_id: str, limit: int = 50) -> List[Dict]:
        runs = self._runs.get(task_id, [])
        return [r.to_dict() for r in runs[-limit:]]

    def get_stats(self) -> Dict:
        with self._lock:
            tasks = list(self._tasks.values())
            total_runs = sum(len(runs) for runs in self._runs.values())
            successful = sum(1 for runs in self._runs.values() for r in runs if r.success)
            failed = total_runs - successful
            return {
                "total_tasks": len(tasks),
                "enabled": sum(1 for t in tasks if t.enabled),
                "disabled": sum(1 for t in tasks if not t.enabled),
                "total_runs": total_runs,
                "successful": successful,
                "failed": failed,
                "success_rate": round(successful / total_runs * 100, 2) if total_runs > 0 else 0,
            }

    def _execute_task(self, task: Task) -> TaskRun:
        run = TaskRun(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            task_id=task.task_id,
            started_at=time.time(),
        )

        handler = self._handlers.get(task.action)
        if not handler:
            run.error = f"No handler for action: {task.action}"
            run.finished_at = time.time()
            run.duration = run.finished_at - run.started_at
            return run

        try:
            result = handler(**task.params)
            run.result = str(result)[:500]
            run.success = True
        except Exception as e:
            run.error = str(e)[:500]
            run.success = False

        run.finished_at = time.time()
        run.duration = run.finished_at - run.started_at
        return run

    def run_task(self, task_id: str) -> Optional[Dict]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        run = self._execute_task(task)

        with self._lock:
            task.last_run = time.time()
            task.run_count += 1
            task.last_result = run.result
            task.last_error = run.error
            task.next_run = ScheduleParser.next_run(task.schedule)
            self._runs[task_id].append(run)
            self._save_tasks()
            self._save_runs()

        return run.to_dict()

    def run_pending(self) -> List[Dict]:
        now = time.time()
        results = []
        with self._lock:
            pending = [t for t in self._tasks.values()
                       if t.enabled and t.next_run <= now]

        for task in pending:
            result = self.run_task(task.task_id)
            if result:
                results.append(result)

        return results

    def start(self, check_interval: int = 10):
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
                self.run_pending()
            except Exception:
                pass
            self._stop_event.wait(check_interval)

    def get_schedule_info(self, schedule: Dict) -> Dict:
        next_run = ScheduleParser.next_run(schedule)
        return {
            "type": schedule.get("type"),
            "next_run": next_run,
            "next_run_human": datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S"),
            "schedule": schedule,
        }


_scheduler = None


def _get_scheduler() -> TaskScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


def task_scheduler_tool(action: str = "list", **kwargs) -> Any:
    """Task scheduler tool dispatcher."""
    try:
        scheduler = _get_scheduler()

        if action == "list":
            enabled_only = kwargs.get("enabled_only", False)
            tags = kwargs.get("tags")
            return {"tasks": scheduler.list_tasks(enabled_only, tags)}

        elif action == "add":
            name = kwargs.get("name", "")
            schedule = kwargs.get("schedule", {"type": "interval", "interval_seconds": 3600})
            action_name = kwargs.get("task_action", "")
            params = kwargs.get("params", {})
            description = kwargs.get("description", "")
            timeout = kwargs.get("timeout", 300)
            retries = kwargs.get("retries", 3)
            tags = kwargs.get("tags", [])
            if not name or not action_name:
                return {"error": "name and task_action required"}
            task = scheduler.add_task(name, schedule, action_name, params, description, timeout, retries, tags)
            return task.to_dict()

        elif action == "get":
            task_id = kwargs.get("task_id", "")
            task = scheduler.get_task(task_id)
            return task.to_dict() if task else {"error": "Task not found"}

        elif action == "update":
            task_id = kwargs.get("task_id", "")
            updates = {k: v for k, v in kwargs.items() if k != "task_id" and k != "action"}
            ok = scheduler.update_task(task_id, **updates)
            return {"success": ok}

        elif action == "delete":
            task_id = kwargs.get("task_id", "")
            ok = scheduler.delete_task(task_id)
            return {"success": ok}

        elif action == "enable":
            task_id = kwargs.get("task_id", "")
            ok = scheduler.enable_task(task_id)
            return {"success": ok}

        elif action == "disable":
            task_id = kwargs.get("task_id", "")
            ok = scheduler.disable_task(task_id)
            return {"success": ok}

        elif action == "run":
            task_id = kwargs.get("task_id", "")
            result = scheduler.run_task(task_id)
            return result or {"error": "Task not found"}

        elif action == "run_pending":
            results = scheduler.run_pending()
            return {"executed": len(results), "results": results}

        elif action == "runs":
            task_id = kwargs.get("task_id", "")
            limit = kwargs.get("limit", 50)
            return {"runs": scheduler.get_runs(task_id, limit)}

        elif action == "stats":
            return scheduler.get_stats()

        elif action == "start":
            interval = kwargs.get("check_interval", 10)
            scheduler.start(interval)
            return {"success": True, "message": "Scheduler started"}

        elif action == "stop":
            scheduler.stop()
            return {"success": True, "message": "Scheduler stopped"}

        elif action == "schedule_info":
            schedule = kwargs.get("schedule", {})
            return scheduler.get_schedule_info(schedule)

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
