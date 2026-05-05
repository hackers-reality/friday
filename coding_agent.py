"""
Friday Coding Sub-Agent - Phase 7.4
Claude Code-style coding agent that can spawn, read files, edit code, run tests.
Uses LangGraph for orchestration with file operations and shell execution.
"""
from __future__ import annotations

import os
import sys
import json
import asyncio
import subprocess
import tempfile
from typing import Optional, Dict, Any, List, TypedDict
from pathlib import Path

# Try to import LangGraph
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[CodingAgent] LangGraph not available")


# ─── Coding Agent State ────────────────────────────────────#

class CodingState(TypedDict):
    """State for the coding agent."""
    messages: List[Dict[str, str]]
    task: str
    files_read: List[str]
    files_modified: List[str]
    current_file: Optional[str]
    shell_outputs: List[str]
    test_results: Optional[str]
    status: str  # "working", "done", "error"
    plan: List[str]
    current_step: int


# ─── File Operations ────────────────────────────────────#

class FileOps:
    """File operations for the coding agent."""

    @staticmethod
    def read_file(filepath: str) -> str:
        """Read a file and return its contents."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"📄 {filepath} ({len(content)} chars):\n\n{content[:3000]}" + (f"\n... [truncated, {len(content)} total chars]" if len(content) > 3000 else "")
        except Exception as e:
            return f"❌ Error reading {filepath}: {str(e)}"

    @staticmethod
    def write_file(filepath: str, content: str) -> str:
        """Write content to a file."""
        try:
            # Create directory if needed
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Written to {filepath} ({len(content)} chars)"
        except Exception as e:
            return f"❌ Error writing {filepath}: {str(e)}"

    @staticmethod
    def edit_file(filepath: str, old_str: str, new_str: str, replace_all: bool = False) -> str:
        """Edit a file by replacing old_str with new_str."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_str not in content:
                return f"❌ String not found in {filepath}"

            if replace_all:
                new_content = content.replace(old_str, new_str)
            else:
                new_content = content.replace(old_str, new_str, 1)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return f"✅ Edited {filepath} ({content.count(old_str)} replacement(s))"
        except Exception as e:
            return f"❌ Error editing {filepath}: {str(e)}"

    @staticmethod
    def list_files(directory: str = ".", pattern: str = "**/*.py") -> str:
        """List files matching a pattern."""
        try:
            files = list(Path(directory).glob(pattern))
            if not files:
                return f"No files matching {pattern} in {directory}"
            return f"📁 Found {len(files)} files:\n" + "\n".join(str(f) for f in files[:20])
        except Exception as e:
            return f"❌ Error listing files: {str(e)}"


# ─── Shell Operations ────────────────────────────────────#

class ShellOps:
    """Shell operations for the coding agent."""

    @staticmethod
    def run_command(command: str, workdir: str = None, timeout: int = 60) -> str:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir
            )
            output = result.stdout[:2000]
            if result.stderr:
                output += f"\n--- STDERR ---\n{result.stderr[:1000]}"
            return f"💻 {command}\nExit code: {result.returncode}\n\n{output}"
        except subprocess.TimeoutExpired:
            return f"❌ Command timed out after {timeout}s: {command}"
        except Exception as e:
            return f"❌ Error running command: {str(e)}"

    @staticmethod
    def run_python_script(script_path: str, args: str = "") -> str:
        """Run a Python script."""
        return ShellOps.run_command(f"python {script_path} {args}")

    @staticmethod
    def run_tests(test_path: str = "tests/", test_framework: str = "pytest") -> str:
        """Run tests."""
        if test_framework == "pytest":
            return ShellOps.run_command(f"python -m pytest {test_path} -v")
        elif test_framework == "unittest":
            return ShellOps.run_command(f"python -m unittest discover {test_path}")
        return f"Unknown test framework: {test_framework}"


# ─── Coding Agent ────────────────────────────────────#

class CodingAgent:
    """
    Claude Code-style coding agent.
    Can read files, edit code, run tests, and execute shell commands.
    """

    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.getcwd()
        self.file_ops = FileOps()
        self.shell_ops = ShellOps()
        self.graph = None
        self._init_graph()

    def _init_graph(self):
        """Initialize the LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            return

        workflow = StateGraph(CodingState)

        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("file_reader", self._file_reader_node)
        workflow.add_node("coder", self._coder_node)
        workflow.add_node("tester", self._tester_node)
        workflow.add_node("done", self._done_node)

        # Add edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "file_reader")
        workflow.add_edge("file_reader", "coder")
        workflow.add_edge("coder", "tester")
        workflow.add_conditional_edges(
            "tester",
            self._should_continue,
            {
                "continue": "file_reader",
                "done": "done",
            }
        )
        workflow.add_edge("done", END)

        # Compile with checkpointer
        db_path = os.path.join(self.workspace, "friday_memory", "coding_checkpoints.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with SqliteSaver.from_conn_string(db_path) as checkpointer:
            self.graph = workflow.compile(checkpointer=checkpointer)

    def _planner_node(self, state: CodingState) -> CodingState:
        """Plan the coding task."""
        task = state["task"]
        # In production, this would use an LLM to create a plan
        state["plan"] = [
            "1. Understand the task",
            "2. Read relevant files",
            "3. Implement the changes",
            "4. Run tests",
            "5. Verify the result"
        ]
        state["current_step"] = 0
        state["messages"].append({
            "role": "assistant",
            "content": f"📋 Plan created for task: {task}"
        })
        return state

    def _file_reader_node(self, state: CodingState) -> CodingState:
        """Read files relevant to the task."""
        # This would use LLM to determine which files to read
        state["messages"].append({
            "role": "assistant",
            "content": "📖 Reading relevant files..."
        })
        return state

    def _coder_node(self, state: CodingState) -> CodingState:
        """Make code changes."""
        state["messages"].append({
            "role": "assistant",
            "content": "💻 Implementing code changes..."
        })
        return state

    def _tester_node(self, state: CodingState) -> CodingState:
        """Run tests."""
        state["messages"].append({
            "role": "assistant",
            "content": "🧪 Running tests..."
        })
        state["test_results"] = "Tests passed (placeholder)"
        state["status"] = "done"
        return state

    def _done_node(self, state: CodingState) -> CodingState:
        """Finalize."""
        state["messages"].append({
            "role": "assistant",
            "content": "✅ Coding task completed!"
        })
        return state

    def _should_continue(self, state: CodingState) -> str:
        """Decide whether to continue or finish."""
        if state["status"] == "done":
            return "done"
        return "continue"

    def run_task(self, task: str, thread_id: str = "coding_1") -> str:
        """Run a coding task."""
        if not self.graph:
            return "❌ LangGraph not available. Install: pip install langgraph"

        initial_state: CodingState = {
            "messages": [{"role": "user", "content": task}],
            "task": task,
            "files_read": [],
            "files_modified": [],
            "current_file": None,
            "shell_outputs": [],
            "test_results": None,
            "status": "working",
            "plan": [],
            "current_step": 0
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.graph.invoke(initial_state, config)
            return "\n".join([m["content"] for m in result["messages"]])
        except Exception as e:
            return f"❌ Error running coding task: {str(e)}"


# ─── Tool Functions for Friday ────────────────────────────────────#

def coding_agent_tool(
    action: str = "run",
    task: str = None,
    file_path: str = None,
    content: str = None,
    command: str = None,
) -> str:
    """
    Friday tool for coding operations.
    Actions: run, read, write, edit, shell, test
    """
    agent = CodingAgent()
    ops = FileOps()
    shell = ShellOps()

    if action == "run" and task:
        return agent.run_task(task)

    if action == "read" and file_path:
        return ops.read_file(file_path)

    if action == "write" and file_path and content is not None:
        return ops.write_file(file_path, content)

    if action == "edit" and file_path and task:  # task = old_str here
        # Parse: old_str|new_str
        parts = task.split("|", 1)
        if len(parts) == 2:
            return ops.edit_file(file_path, parts[0], parts[1])
        return "❌ edit requires 'old_str|new_str' format"

    if action == "shell" and command:
        return shell.run_command(command)

    if action == "test":
        return shell.run_tests()

    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Coding Agent...")

    # Test file operations
    print("\n--- File Operations ---")
    result = coding_agent_tool("read", file_path="voice_wake.py")
    print(result[:200])

    # Test shell
    print("\n--- Shell Operations ---")
    result = coding_agent_tool("shell", command="echo Hello from coding agent")
    print(result)

    # Test run task (if LangGraph available)
    if LANGGRAPH_AVAILABLE:
        print("\n--- Coding Task ---")
        result = coding_agent_tool("run", task="Fix syntax errors in Python files")
        print(result[:500])
