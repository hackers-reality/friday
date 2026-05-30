"""
Workflow Orchestrator — decomposes complex tasks into DAG pipelines,
spawns agents, manages inter-agent dependencies and data flow.

Example workflw:
  User: "Research quantum computing, find bugs in our web app, and document fixes"
  → Research Agent (Veronica) → waits for results →
  → Bug Finder Agent (Ghost) → waits for results →
  → Documentation Agent (Forge) → creates docs
  → Planner Agent synthesizes final report
"""
from __future__ import annotations

import asyncio
import datetime
import json
import uuid
from typing import Any

from friday.agent_bus import publish, wait_for_result, get_task_status, get_agent_messages
from friday.orchestrator import get_orchestrator

_workflows: dict[str, dict[str, Any]] = {}


async def create_workflow(task_description: str, user_id: str = "default") -> dict[str, Any]:
    """Create a workflow from a task description by decomposing it into steps."""
    wid = f"wf_{uuid.uuid4().hex[:10]}"
    workflow = {
        "id": wid,
        "description": task_description,
        "status": "planning",
        "steps": [],
        "created_at": datetime.datetime.now().isoformat(),
        "user_id": user_id,
        "current_step": -1,
        "total_steps": 0,
        "completed_steps": 0,
    }
    _workflows[wid] = workflow
    return workflow


async def decompose_task(task: str) -> list[dict[str, Any]]:
    """Decompose a complex task into steps with agent assignments."""
    # Use the main FRIDAY or an LLM to decompose
    # For now, use a rule-based decomposition
    steps = []

    # Research step
    if any(kw in task.lower() for kw in ["research", "find", "search", "investigate", "look up", "analyze"]):
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "veronica",
            "task": f"Research: {task}",
            "description": "Gather information and research",
            "depends_on": [],
            "status": "pending",
            "output_key": "research_data",
        })

    # OSINT / security step
    if any(kw in task.lower() for kw in ["scan", "vulnerability", "osint", "security", "recon", "hack", "breach", "threat"]):
        depends = [s["id"] for s in steps if s["agent_id"] == "veronica"]
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "ghost",
            "task": f"Security: {task}",
            "description": "Security analysis and OSINT",
            "depends_on": depends,
            "status": "pending",
            "output_key": "security_data",
        })

    # Code / development step
    if any(kw in task.lower() for kw in ["code", "develop", "write", "program", "build", "create", "fix", "debug", "implement"]):
        depends = [s["id"] for s in steps if s["agent_id"] in ("veronica", "ghost")]
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "forge",
            "task": f"Development: {task}",
            "description": "Code writing and development",
            "depends_on": depends,
            "status": "pending",
            "output_key": "code_data",
        })

    # Documentation / report step
    if any(kw in task.lower() for kw in ["document", "report", "write up", "summarize", "create file", "create document", "presentation"]):
        depends = [s["id"] for s in steps]
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "planner",
            "task": f"Documentation: {task}",
            "description": "Create final documentation and reports",
            "depends_on": depends,
            "status": "pending",
            "output_key": "documentation",
        })

    # If no specific steps detected, do a general research + report
    if not steps:
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "veronica",
            "task": f"Research: {task}",
            "description": "Gather information",
            "depends_on": [],
            "status": "pending",
            "output_key": "research_data",
        })
        steps.append({
            "id": f"step_{uuid.uuid4().hex[:8]}",
            "agent_id": "planner",
            "task": f"Report: {task}",
            "description": "Create summary report",
            "depends_on": [steps[0]["id"]],
            "status": "pending",
            "output_key": "report",
        })

    return steps


async def run_workflow(wid: str) -> dict[str, Any]:
    """Execute a workflow plan step by step, respecting dependencies."""
    wf = _workflows.get(wid)
    if not wf:
        return {"error": f"Workflow {wid} not found"}

    wf["status"] = "running"
    wf["total_steps"] = len(wf["steps"])
    orch = get_orchestrator()

    completed = {}
    all_step_ids = {s["id"] for s in wf["steps"]}

    while True:
        ready = [
            s for s in wf["steps"]
            if s["status"] == "pending"
            and all(dep in completed for dep in s["depends_on"])
        ]

        if not ready:
            remaining = [s for s in wf["steps"] if s["status"] == "pending"]
            if not remaining:
                break
            # Wait for dependencies
            await asyncio.sleep(1)
            continue

        # Run ready steps (can run in parallel if no cross-dependencies)
        tasks = []
        for step in ready:
            step["status"] = "running"
            tasks.append(_execute_step(wf, step, completed, orch))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for step, result in zip(ready, results):
            if isinstance(result, Exception):
                step["status"] = "failed"
                step["error"] = str(result)
                await publish("workflow", f"workflow.{wid}.step.failed", {
                    "step": step["id"], "error": str(result)
                })
            else:
                step["status"] = "completed"
                completed[step["id"]] = result
                wf["completed_steps"] += 1
                await publish("workflow", f"workflow.{wid}.step.completed", {
                    "step": step["id"], "result": result
                })

    wf["status"] = "completed" if wf["completed_steps"] == wf["total_steps"] else "partial"
    wf["completed_at"] = datetime.datetime.now().isoformat()

    # Collect all outputs
    all_outputs = {}
    for s in wf["steps"]:
        if s["id"] in completed:
            step_result = completed[s["id"]]
            k = s.get("output_key", s["id"])
            all_outputs[k] = step_result

    wf["outputs"] = all_outputs

    await publish("workflow", f"workflow.{wid}.completed", {
        "workflow_id": wid,
        "status": wf["status"],
        "outputs": all_outputs,
    })

    return wf


async def _execute_step(wf: dict, step: dict, completed: dict, orch) -> Any:
    """Execute a single step by spawning the appropriate agent with context."""
    step_input = {
        "task": step["task"],
        "description": step["description"],
    }

    # Pass context from completed dependencies
    context = {}
    for dep_id in step["depends_on"]:
        dep_result = completed.get(dep_id)
        if dep_result:
            dep_step = next(s for s in wf["steps"] if s["id"] == dep_id)
            k = dep_step.get("output_key", dep_id)
            context[k] = dep_result

    if context:
        step_input["context"] = json.dumps(context, default=str)[:10000]

    # Spawn the agent
    result = await orch.delegate(step["agent_id"], json.dumps(step_input), "workflow_task")

    output = getattr(result, "output", "") or getattr(result, "error", "") or str(result)

    # Publish result to bus
    await publish(
        step["agent_id"],
        f"agent.{step['agent_id']}.result",
        {"step": step["id"], "output": output[:5000]},
        task_id=step["id"],
    )

    return {"output": output[:5000], "agent": step["agent_id"], "task": step["task"]}


async def create_and_run_workflow(task: str) -> dict[str, Any]:
    """High-level function: decompose + run workflow."""
    wf = await create_workflow(task)
    steps = await decompose_task(task)
    wf["steps"] = steps
    result = await run_workflow(wf["id"])
    return result


def get_workflow(wid: str) -> dict[str, Any] | None:
    return _workflows.get(wid)


def list_workflows(limit: int = 10) -> list[dict[str, Any]]:
    all_wf = sorted(_workflows.values(), key=lambda w: w.get("created_at", ""), reverse=True)
    return all_wf[:limit]


def get_workflow_status_text(wid: str) -> str:
    wf = _workflows.get(wid)
    if not wf:
        return "Workflow not found."
    lines = [f"📋 Workflow: {wf['description'][:80]}"]
    lines.append(f"   Status: {wf['status']}  ({wf['completed_steps']}/{wf['total_steps']} steps)")
    for s in wf["steps"]:
        icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(s["status"], "⏳")
        lines.append(f"   {icon} {s['agent_id'].title()}: {s['description'][:60]}")
    if wf.get("outputs"):
        lines.append(f"   📄 Output keys: {', '.join(wf['outputs'].keys())}")
    return "\n".join(lines)
