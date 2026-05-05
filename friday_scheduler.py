"""
Friday Scheduler - Task scheduling and reminders.
Cron-like scheduling, reminders, timed tasks, recurring jobs.
"""
from __future__ import annotations

import os
import sys
import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import tempfile


# ─── Task Scheduler ────────────────────────────#

class TaskScheduler:
    """Advanced task scheduler."""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
    def add_task(
        self,
        name: str,
        func: Callable,
        trigger: str = "interval",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Add a task.
        trigger: interval, daily, cron
        kwargs: seconds, minutes, hours, at, cron_string
        """
        with self.lock:
            self.tasks[name] = {
                "name": name,
                "function": func,
                "trigger": trigger,
                "kwargs": kwargs,
                "enabled": True,
                "last_run": None,
                "next_run": None,
                "run_count": 0,
            }
            
            # Schedule using schedule library
            job = None
            if trigger == "interval":
                seconds = kwargs.get("seconds", 60)
                job = schedule.every(seconds).seconds.do(func)
            elif trigger == "daily":
                at_time = kwargs.get("at", "09:00")
                job = schedule.every().day.at(at_time).do(func)
            elif trigger == "cron":
                # Simplified cron: minute, hour, day, month, day_of_week
                cron_string = kwargs.get("cron_string", "* * * * *")
                parts = cron_string.split()
                if len(parts) >= 2:
                    hour, minute = parts[1], parts[0]
                    if hour != "*" and minute != "*":
                        job = schedule.every().day.at(f"{hour}:{minute}").do(func)
            
            if job:
                self.tasks[name]["job"] = job
            
            return {"success": True, "task": name}
    
    def remove_task(self, name: str) -> Dict[str, Any]:
        """Remove a task."""
        with self.lock:
            if name in self.tasks:
                if "job" in self.tasks[name]:
                    schedule.cancel_job(self.tasks[name]["job"])
                del self.tasks[name]
                return {"success": True}
            return {"success": False, "error": "Task not found."}
    
    def enable_task(self, name: str) -> Dict[str, Any]:
        """Enable a task."""
        with self.lock:
            if name in self.tasks:
                self.tasks[name]["enabled"] = True
                return {"success": True}
            return {"success": False, "error": "Task not found."}
    
    def disable_task(self, name: str) -> Dict[str, Any]:
        """Disable a task."""
        with self.lock:
            if name in self.tasks:
                self.tasks[name]["enabled"] = False
                return {"success": True}
            return {"success": False, "error": "Task not found."}
    
    def run_task(self, name: str) -> Dict[str, Any]:
        """Run a task manually."""
        with self.lock:
            if name not in self.tasks:
                return {"success": False, "error": "Task not found."}
            
            task = self.tasks[name]
            try:
                result = task["function"]()
                task["last_run"] = datetime.now().isoformat()
                task["run_count"] += 1
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def list_tasks(self) -> List[Dict]:
        """List all tasks."""
        with self.lock:
            return [
                {
                    "name": name,
                    "trigger": task["trigger"],
                    "enabled": task["enabled"],
                    "last_run": task["last_run"],
                    "run_count": task["run_count"],
                }
                for name, task in self.tasks.items()
            ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        with self.lock:
            return {
                "running": self.running,
                "task_count": len(self.tasks),
                "enabled_count": sum(1 for t in self.tasks.values() if t["enabled"]),
                "pending_jobs": len(schedule.jobs),
            }


# ─── Reminder System ────────────────────────────#

class ReminderSystem:
    """Reminder system with notifications."""
    
    def __init__(self):
        self.reminders: Dict[str, Dict] = {}
        self.next_id = 1
        self.lock = threading.Lock()
        
    def add_reminder(
        self,
        message: str,
        remind_at: datetime = None,
        remind_in: timedelta = None,
    ) -> Dict[str, Any]:
        """Add a reminder."""
        with self.lock:
            reminder_id = f"reminder_{self.next_id}"
            self.next_id += 1
            
            if remind_at:
                trigger_time = remind_at
            elif remind_in:
                trigger_time = datetime.now() + remind_in
            else:
                return {"success": False, "error": "remind_at or remind_in required."}
            
            self.reminders[reminder_id] = {
                "id": reminder_id,
                "message": message,
                "trigger_time": trigger_time.isoformat(),
                "triggered": False,
                "created": datetime.now().isoformat(),
            }
            
            return {"success": True, "id": reminder_id, "trigger_time": trigger_time.isoformat()}
    
    def check_reminders(self) -> List[Dict]:
        """Check and trigger due reminders."""
        due_reminders = []
        now = datetime.now()
        
        with self.lock:
            for reminder_id, reminder in self.reminders.items():
                if not reminder["triggered"]:
                    trigger_time = datetime.fromisoformat(reminder["trigger_time"])
                    if now >= trigger_time:
                        reminder["triggered"] = True
                        due_reminders.append(reminder)
        
        return due_reminders
    
    def list_reminders(self, include_triggered: bool = False) -> List[Dict]:
        """List all reminders."""
        with self.lock:
            reminders = []
            for reminder in self.reminders.values():
                if include_triggered or not reminder["triggered"]:
                    reminders.append(reminder)
            return reminders
    
    def remove_reminder(self, reminder_id: str) -> Dict[str, Any]:
        """Remove a reminder."""
        with self.lock:
            if reminder_id in self.reminders:
                del self.reminders[reminder_id]
                return {"success": True}
            return {"success": False, "error": "Reminder not found."}
    
    def clear_triggered(self):
        """Clear triggered reminders."""
        with self.lock:
            self.reminders = {
                k: v for k, v in self.reminders.items() if not v["triggered"]
            }


# ─── Cron Parser (Simplified) ────────────────────────────#

class CronParser:
    """Simplified cron expression parser."""
    
    @staticmethod
    def parse(cron_string: str) -> Dict[str, Any]:
        """
        Parse cron string: minute hour day month day_of_week
        Returns next run time.
        """
        parts = cron_string.split()
        if len(parts) < 5:
            return {"success": False, "error": "Invalid cron string. Expected: m h dom mon dow"}
        
        minute, hour, dom, month, dow = parts[:5]
        
        return {
            "success": True,
            "minute": minute,
            "hour": hour,
            "day_of_month": dom,
            "month": month,
            "day_of_week": dow,
        }
    
    @staticmethod
    def next_run(cron_string: str) -> Optional[datetime]:
        """Get next run time from cron string (simplified)."""
        # This is a very simplified implementation
        # In production, use a library like croniter
        parts = cron_string.split()
        if len(parts) < 2:
            return None
        
        hour, minute = parts[1], parts[0]
        if hour == "*" or minute == "*":
            return None
        
        now = datetime.now()
        trigger_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        
        if trigger_time <= now:
            trigger_time += timedelta(days=1)
        
        return trigger_time


# ─── Scheduler Tool for Friday ────────────────────────────#

def scheduler_tool(
    action: str = "status",
    name: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for scheduler operations.
    Actions: status, task_add, task_remove, task_run, task_list,
            reminder_add, reminder_list, reminder_remove, cron_parse
    """
    params = params or {}
    
    if action == "status":
        scheduler = TaskScheduler()
        lines = ["### SCHEDULER STATUS", ""]
        status = scheduler.get_status()
        lines.append(f"**Running**: {'✅' if status['running'] else '❌'}")
        lines.append(f"**Tasks**: {status['task_count']}")
        lines.append(f"**Enabled**: {status['enabled_count']}")
        lines.append(f"**Pending Jobs**: {status['pending_jobs']}")
        return "\n".join(lines)
    
    if action == "task_add":
        if not name:
            return "❌ Task name required."
        scheduler = TaskScheduler()
        func_name = params.get("function", "lambda: print('Task executed')")
        trigger = params.get("trigger", "interval")
        result = scheduler.add_task(name, eval(func_name), trigger, **params.get("kwargs", {}))
        if result["success"]:
            return f"### TASK ADD\n\n✅ Added"
        else:
            return f"### TASK ADD\n\n❌ {result.get('error', 'Unknown')}"
    
    if action == "task_remove":
        if not name:
            return "❌ Task name required."
        scheduler = TaskScheduler()
        result = scheduler.remove_task(name)
        if result["success"]:
            return "### TASK REMOVE\n\n✅ Removed"
        else:
            return f"### TASK REMOVE\n\n❌ {result.get('error', 'Unknown')}"
    
    if action == "task_run":
        if not name:
            return "❌ Task name required."
        scheduler = TaskScheduler()
        result = scheduler.run_task(name)
        if result["success"]:
            return "### TASK RUN\n\n✅ Executed"
        else:
            return f"### TASK RUN\n\n❌ {result.get('error', 'Unknown')}"
    
    if action == "task_list":
        scheduler = TaskScheduler()
        tasks = scheduler.list_tasks()
        lines = ["### TASKS", ""]
        for task in tasks:
            status = "✅" if task["enabled"] else "❌"
            lines.append(f"{status} **{task['name']}** ({task['trigger']}) - Runs: {task['run_count']}")
        return "\n".join(lines)
    
    if action == "reminder_add":
        if not name:
            return "❌ Message required."
        reminder_sys = ReminderSystem()
        if "remind_in_seconds" in params:
            remind_in = timedelta(seconds=params["remind_in_seconds"])
            result = reminder_sys.add_reminder(name, remind_in=remind_in)
        elif "remind_at" in params:
            remind_at = datetime.fromisoformat(params["remind_at"])
            result = reminder_sys.add_reminder(name, remind_at=remind_at)
        else:
            return "❌ remind_at or remind_in_seconds required."
        
        if result["success"]:
            return f"### REMINDER ADD\n\n✅ Added\nID: {result.get('id', 'N/A')}"
        else:
            return f"### REMINDER ADD\n\n❌ {result.get('error', 'Unknown')}"
    
    if action == "reminder_list":
        reminder_sys = ReminderSystem()
        reminders = reminder_sys.list_reminders(params.get("include_triggered", False))
        lines = ["### REMINDERS", ""]
        for r in reminders:
            status = "✅ Triggered" if r["triggered"] else "⏰ Pending"
            lines.append(f"{status}: {r['message'][:50]}... (ID: {r['id']})")
        return "\n".join(lines)
    
    if action == "reminder_remove":
        if not name:
            return "❌ Reminder ID required."
        reminder_sys = ReminderSystem()
        result = reminder_sys.remove_reminder(name)
        if result["success"]:
            return "### REMINDER REMOVE\n\n✅ Removed"
        else:
            return f"### REMINDER REMOVE\n\n❌ {result.get('error', 'Unknown')}"
    
    if action == "cron_parse":
        if not name:
            return "❌ Cron string required."
        result = CronParser.parse(name)
        if result["success"]:
            return f"### CRON PARSE\n\n**Minute**: {result['minute']}\n**Hour**: {result['hour']}\n**Day**: {result['day_of_month']}\n**Month**: {result['month']}\n**DOW**: {result['day_of_week']}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Scheduler...\n")
    
    # Test task scheduler
    print("--- Task Scheduler ---")
    print(scheduler_tool("status"))
    
    # Test reminder
    print("\n--- Reminder ---")
    print(scheduler_tool("reminder_add", name="Test reminder", params={"remind_in_seconds": 60}))
