"""
Friday Workflow Automation - Complex task automation.
Define, execute, and monitor automated workflows.
"""
from __future__ import annotations

import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import threading


# ─── Workflow Definition ───────────────────────────────────#

class WorkflowStep:
    """A single step in a workflow."""
    
    def __init__(
        self,
        step_id: str,
        action: str,
        params: Dict[str, Any] = None,
        depends_on: List[str] = None,
        retry_count: int = 0,
        timeout: int = 60,
    ):
        self.id = step_id
        self.action = action
        self.params = params or {}
        self.depends_on = depends_on or []
        self.retry_count = retry_count
        self.timeout = timeout
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "params": self.params,
            "depends_on": self.depends_on,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        step = cls(
            data["id"],
            data["action"],
            data.get("params"),
            data.get("depends_on"),
            data.get("retry_count", 0),
            data.get("timeout", 60),
        )
        step.status = data.get("status", "pending")
        step.result = data.get("result")
        step.error = data.get("error")
        return step


# ─── Workflow ───────────────────────────────────#

class Workflow:
    """A complete workflow with multiple steps."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.created = datetime.now().isoformat()
        self.status = "created"  # created, running, completed, failed
        
    def add_step(self, step: WorkflowStep) -> bool:
        """Add a step to the workflow."""
        if step.id in self.steps:
            return False
        self.steps[step.id] = step
        return True
    
    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (dependencies met)."""
        ready = []
        for step in self.steps.values():
            if step.status != "pending":
                continue
            # Check dependencies
            deps_met = all(
                self.steps[dep_id].status == "completed"
                for dep_id in step.depends_on
                if dep_id in self.steps
            )
            if deps_met:
                ready.append(step)
        return ready
    
    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(s.status in ("completed", "failed") for s in self.steps.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get workflow status."""
        total = len(self.steps)
        completed = sum(1 for s in self.steps.values() if s.status == "completed")
        failed = sum(1 for s in self.steps.values() if s.status == "failed")
        running = sum(1 for s in self.steps.values() if s.status == "running")
        pending = sum(1 for s in self.steps.values() if s.status == "pending")
        
        return {
            "name": self.name,
            "status": self.status,
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "progress": completed / total if total > 0 else 0,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "created": self.created,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        wf = cls(data["name"], data.get("description", ""))
        wf.created = data.get("created", datetime.now().isoformat())
        wf.status = data.get("status", "created")
        for step_id, step_data in data.get("steps", {}).items():
            wf.steps[step_id] = WorkflowStep.from_dict(step_data)
        return wf


# ─── Workflow Executor ───────────────────────────────────#

class WorkflowExecutor:
    """Executes workflows using available tools."""
    
    def __init__(self, tool_registry: Dict[str, Callable] = None):
        self.tool_registry = tool_registry or {}
        self.active_workflows: Dict[str, Workflow] = {}
        
    def register_tool(self, name: str, func: Callable):
        """Register a tool for use in workflows."""
        self.tool_registry[name] = func
        
    def execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute a workflow to completion."""
        workflow.status = "running"
        max_iterations = len(workflow.steps) * 10  # Prevent infinite loops
        
        for iteration in range(max_iterations):
            ready_steps = workflow.get_ready_steps()
            
            if not ready_steps:
                break
            
            for step in ready_steps:
                step.status = "running"
                
                try:
                    # Get the tool
                    if step.action not in self.tool_registry:
                        raise ValueError(f"Tool not found: {step.action}")
                    
                    tool_func = self.tool_registry[step.action]
                    
                    # Execute with timeout
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(tool_func, **step.params)
                        try:
                            result = future.result(timeout=step.timeout)
                            step.result = result
                            step.status = "completed"
                        except concurrent.futures.TimeoutError:
                            raise TimeoutError(f"Step timed out after {step.timeout}s")
                        
                except Exception as e:
                    step.error = str(e)
                    if step.retry_count > 0:
                        step.retry_count -= 1
                        step.status = "pending"  # Retry
                    else:
                        step.status = "failed"
            
            if workflow.is_complete():
                break
        
        # Update final status
        if workflow.is_complete():
            if any(s.status == "failed" for s in workflow.steps.values()):
                workflow.status = "failed"
            else:
                workflow.status = "completed"
        
        return workflow.get_status()
    
    def execute_async(self, workflow: Workflow, callback: Callable = None):
        """Execute workflow asynchronously."""
        def _run():
            result = self.execute_workflow(workflow)
            if callback:
                callback(workflow)
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread


# ─── Workflow Scheduler ───────────────────────────────────#

class WorkflowScheduler:
    """Schedules workflows for execution."""
    
    def __init__(self):
        self.scheduled: List[Dict[str, Any]] = []
        self.executor = WorkflowExecutor()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
    def schedule_workflow(
        self,
        workflow: Workflow,
        run_at: datetime = None,
        cron: str = None,
        interval: timedelta = None,
    ) -> str:
        """
        Schedule a workflow.
        run_at: Specific time to run
        cron: Cron expression (simplified: "daily", "hourly", "weekly")
        interval: Repeat every interval
        """
        schedule_id = f"sched_{len(self.scheduled)}"
        
        self.scheduled.append({
            "id": schedule_id,
            "workflow": workflow,
            "run_at": run_at,
            "cron": cron,
            "interval": interval,
            "last_run": None,
        })
        
        return schedule_id
    
    def start(self):
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = datetime.now()
            
            for sched in self.scheduled:
                should_run = False
                
                # Check one-time run
                if sched["run_at"] and now >= sched["run_at"]:
                    should_run = True
                    sched["run_at"] = None  # Clear one-time
                
                # Check cron (simplified)
                if sched["cron"]:
                    if sched["cron"] == "daily" and (not sched["last_run"] or (now - sched["last_run"]).days >= 1):
                        should_run = True
                    elif sched["cron"] == "hourly" and (not sched["last_run"] or (now - sched["last_run"]).total_seconds() >= 3600):
                        should_run = True
                
                # Check interval
                if sched["interval"] and sched["last_run"]:
                    if now - sched["last_run"] >= sched["interval"]:
                        should_run = True
                
                if should_run:
                    sched["last_run"] = now
                    self.executor.execute_async(sched["workflow"])
            
            time.sleep(60)  # Check every minute


# ─── Workflow Manager ───────────────────────────────────#

class WorkflowManager:
    """Manages all workflows."""
    
    def __init__(self, storage_path: str = "friday_memory/workflows"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.workflows: Dict[str, Workflow] = {}
        self.scheduler = WorkflowScheduler()
        self.executor = WorkflowExecutor()
        self._load_all()
        
    def _load_all(self):
        """Load all saved workflows."""
        for wf_file in self.storage_path.glob("*.json"):
            try:
                with open(wf_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                workflow = Workflow.from_dict(data)
                self.workflows[workflow.name] = workflow
            except Exception as e:
                print(f"[WorkflowManager] Error loading {wf_file}: {e}")
    
    def save_workflow(self, workflow: Workflow):
        """Save a workflow."""
        wf_path = self.storage_path / f"{workflow.name}.json"
        with open(wf_path, 'w', encoding='utf-8') as f:
            json.dump(workflow.to_dict(), f, indent=2)
        
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """Create a new workflow."""
        if name in self.workflows:
            return self.workflows[name]
        workflow = Workflow(name, description)
        self.workflows[name] = workflow
        return workflow
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        if name not in self.workflows:
            return False
        del self.workflows[name]
        wf_path = self.storage_path / f"{name}.json"
        if wf_path.exists():
            wf_path.unlink()
        return True
    
    def list_workflows(self) -> List[str]:
        """List all workflow names."""
        return list(self.workflows.keys())
    
    def execute_workflow(self, name: str) -> Dict[str, Any]:
        """Execute a workflow by name."""
        workflow = self.workflows.get(name)
        if not workflow:
            return {"error": f"Workflow not found: {name}"}
        
        # Register tools from friday_tools
        try:
            from friday import tools
            self.executor.tool_registry = {
                "web_search": friday_tools.web_search,
                "run_cmd": friday_tools.run_cmd,
                "read_file": friday_tools.read_file,
                "write_file": friday_tools.write_file,
                "open_app": friday_tools.open_app,
            }
        except:
            pass
        
        return self.executor.execute_workflow(workflow)


# ─── Singleton ───────────────────────────────────#

_manager: Optional[WorkflowManager] = None

def get_workflow_manager() -> WorkflowManager:
    global _manager
    if _manager is None:
        _manager = WorkflowManager()
    return _manager


# ─── Tool Function for Friday ───────────────────────────────────#

def workflow_tool(
    action: str = "list",
    name: str = None,
    description: str = None,
    steps: str = None,  # JSON string
) -> str:
    """
    Friday tool for workflow automation.
    Actions: list, create, add_step, execute, delete, status, schedule
    """
    manager = get_workflow_manager()
    
    if action == "list":
        workflows = manager.list_workflows()
        if not workflows:
            return "No workflows defined."
        lines = ["### WORKFLOWS", ""]
        for wf_name in workflows:
            wf = manager.get_workflow(wf_name)
            status = wf.get_status() if hasattr(wf, 'get_status') else {}
            lines.append(f"**{wf_name}** - {wf.description or 'No description'}")
            lines.append(f"  Steps: {len(wf.steps)}, Status: {wf.status}")
            lines.append("")
        return "\n".join(lines)
    
    if action == "create":
        if not name:
            return "[FAIL] Workflow name required."
        workflow = manager.create_workflow(name, description or "")
        manager.save_workflow(workflow)
        return f"[OK] Created workflow: {name}"
    
    if action == "add_step":
        if not name or not steps:
            return "[FAIL] Workflow name and steps (JSON) required."
        
        workflow = manager.get_workflow(name)
        if not workflow:
            return f"[FAIL] Workflow not found: {name}"
        
        try:
            step_data = json.loads(steps)
            step = WorkflowStep.from_dict(step_data)
            if workflow.add_step(step):
                manager.save_workflow(workflow)
                return f"[OK] Added step: {step.id}"
            return f"[FAIL] Step already exists: {step.id}"
        except Exception as e:
            return f"[FAIL] Error adding step: {e}"
    
    if action == "execute":
        if not name:
            return "[FAIL] Workflow name required."
        
        result = manager.execute_workflow(name)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        lines = [f"### WORKFLOW EXECUTION: {name}", ""]
        lines.append(f"**Status**: {result['status']}")
        lines.append(f"**Progress**: {result['progress']:.0%}")
        lines.append(f"**Completed**: {result['completed']}/{result['total_steps']}")
        if result['failed'] > 0:
            lines.append(f"**Failed**: {result['failed']}")
        return "\n".join(lines)
    
    if action == "status":
        if not name:
            return "[FAIL] Workflow name required."
        
        workflow = manager.get_workflow(name)
        if not workflow:
            return f"[FAIL] Workflow not found: {name}"
        
        status = workflow.get_status()
        lines = [f"### WORKFLOW: {name}", ""]
        lines.append(f"**Description**: {workflow.description or 'None'}")
        lines.append(f"**Status**: {status['status']}")
        lines.append(f"**Progress**: {status['progress']:.0%}")
        lines.append(f"**Steps**: {status['completed']} completed, {status['running']} running, {status['pending']} pending, {status['failed']} failed")
        lines.append("")
        lines.append("**Step Details**:")
        for step in workflow.steps.values():
            icon = "[OK]" if step.status == "completed" else "[FAIL]" if step.status == "failed" else "⏸" if step.status == "pending" else "🔄"
            lines.append(f"  {icon} {step.id}: {step.action}")
        return "\n".join(lines)
    
    if action == "delete":
        if not name:
            return "[FAIL] Workflow name required."
        if manager.delete_workflow(name):
            return f"[OK] Deleted workflow: {name}"
        return f"[FAIL] Workflow not found: {name}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Workflow Automation...\n")
    
    manager = get_workflow_manager()
    
    # Create a test workflow
    print("--- Creating Workflow ---")
    workflow = manager.create_workflow(
        "daily_briefing",
        "Morning daily briefing automation"
    )
    
    # Add steps
    print("\n--- Adding Steps ---")
    print(workflow_tool("add_step", name="daily_briefing", 
                        steps=json.dumps({
                            "id": "check_weather",
                            "action": "web_search",
                            "params": {"query": "weather today"},
                        })))
    
    print("\n--- Workflow Status ---")
    print(workflow_tool("status", name="daily_briefing"))
