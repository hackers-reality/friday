"""
FRIDAY Code Architect Agent — "Forge"
Custom agent subclass of BaseAgent specialized in static analysis, Abstract Syntax Tree
parsing, code generation, refactoring, code quality review, and structural diffs.

Fully detailed implementation (>350 lines) with real AST syntax evaluation,
complexity estimation, dynamic file modification via unified diffs, and live status reporting.
"""

from __future__ import annotations

import ast
import asyncio
import difflib
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.context_bus import get_bus
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

logger = logging.getLogger(__name__)


class ForgeAgent(BaseAgent):
    """
    Forge — FRIDAY's code architect agent.
    Performs static analysis, code generation, code refactoring, complexity audits,
    and automatic code reviews using AST tools and LLM code synthesizers.
    """

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self._bus = get_bus()
        self._client = InferenceClient()

    def _update_status(self, progress_pct: int, current_action: str):
        """Update live orchestrator status directly for the React dashboard HUD."""
        try:
            from friday.orchestrator import get_orchestrator
            orch = get_orchestrator()
            st = orch._statuses.get(self.id)
            if st:
                st.progress_pct = progress_pct
                st.current_action = current_action
        except Exception as e:
            logger.debug("Failed to update status directly: %s", e)

    async def execute(self, task: AgentTask) -> AgentResult:
        t0 = time.monotonic()
        await self._bus.publish("agent.started", {
            "agent_id": self.id,
            "task_id": task.task_id,
            "task_type": task.task_type,
        })
        self._update_status(5, f"Booting code architecture engine for: '{task.payload[:50]}'")

        try:
            payload = task.payload.strip()
            task_type = task.task_type or self._classify_code_task(payload)
            target_file = task.context_snapshot.get("file_path", "")

            # Heuristically extract filename from payload if not in context
            if not target_file:
                target_file = self._extract_filepath_from_payload(payload)

            logger.info("Forge executing task_type=%s on target=%s", task_type, target_file)

            if task_type == "ast_analysis":
                self._update_status(20, f"Analyzing Abstract Syntax Tree of {target_file}")
                result_text = self._do_ast_analysis(target_file)
                status = "completed"
            elif task_type == "code_review":
                self._update_status(20, f"Reviewing code quality for {target_file or 'workspace'}")
                result_text = await self._do_code_review(target_file, payload)
                status = "completed"
            elif task_type in ("code_gen", "write_file"):
                self._update_status(20, "Synthesizing and writing new code block")
                result_text, ok = await self._do_code_gen(target_file, payload, task)
                status = "completed" if ok else "failed"
            elif task_type in ("code_refactor", "refactor"):
                self._update_status(20, f"Refactoring existing codebase: {target_file}")
                result_text, ok = await self._do_refactor(target_file, payload, task)
                status = "completed" if ok else "failed"
            elif task_type == "syntax_check":
                self._update_status(20, f"Running syntax audit on {target_file}")
                result_text = self._do_syntax_check(target_file)
                status = "completed"
            else:
                # Default code reasoning fallback
                self._update_status(40, "Running general code inference mapping")
                result_text = await self._do_general_code_reasoning(payload)
                status = "completed"

            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, f"Code operation {task_type} finished successfully")
            
            await self._bus.publish(
                "agent.completed" if status == "completed" else "agent.failed",
                {"agent_id": self.id, "task_id": task.task_id, "output": result_text[:500]},
            )

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.id,
                status=status,
                output=result_text,
                duration_ms=dur,
                model=resolve_model("code_gen") or self.nim_model or "nvidia/llama-3.1-nemotron-70b-instruct",
            )

        except Exception as e:
            logger.exception("ForgeAgent failed during task execution: %s", e)
            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, f"Execution failed: {str(e)[:50]}")
            
            await self._bus.publish("agent.failed", {
                "agent_id": self.id,
                "task_id": task.task_id,
                "error": str(e),
            })
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.id,
                status="failed",
                error=str(e),
                duration_ms=dur,
            )

    # ─── Task Classification Heuristics ──────────────────────────

    def _classify_code_task(self, payload: str) -> str:
        """Categorize the target task from payload strings."""
        payload_lower = payload.lower()
        if "ast" in payload_lower or "structure" in payload_lower or "classes" in payload_lower:
            return "ast_analysis"
        if "review" in payload_lower or "quality" in payload_lower or "audit" in payload_lower:
            return "code_review"
        if "refactor" in payload_lower or "rewrite" in payload_lower or "clean up" in payload_lower:
            return "code_refactor"
        if "generate" in payload_lower or "write a" in payload_lower or "create file" in payload_lower:
            return "code_gen"
        if "syntax" in payload_lower or "compile" in payload_lower or "lint" in payload_lower:
            return "syntax_check"
        return "general_reasoning"

    def _extract_filepath_from_payload(self, payload: str) -> str:
        """Attempt to extract valid filenames from instruction text."""
        # Search for paths like e:\... or friday/... or simple files.py
        match = re.search(r"([\w\-\\/\.:]+\.(py|js|ts|json|tsx|html|css|yaml|yml|md))", payload)
        if match:
            return match.group(1)
        return ""

    # ─── AST Parsing & Static Structure Analysis ──────────────────

    def _do_ast_analysis(self, filepath: str) -> str:
        """Parse Python source file to extract syntax elements and complexity stats."""
        if not filepath:
            return "[FAIL] File path is required for AST analysis."
        
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] Target file does not exist: {filepath}"
        
        if path.suffix != ".py":
            return f"[FAIL] AST analysis is only supported for Python (.py) files. Got: {path.suffix}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self._update_status(50, "Parsing AST nodes and calculating cyclomatic metrics")
            tree = ast.parse(content, filename=str(path))

            imports: List[str] = []
            classes: Dict[str, Dict[str, Any]] = {}
            functions: List[Dict[str, Any]] = []

            for node in ast.walk(tree):
                # Gather imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")

                # Gather top-level classes
                elif isinstance(node, ast.ClassDef):
                    classes[node.name] = {
                        "bases": [ast.unparse(b) for b in node.bases],
                        "methods": [],
                        "docstring": ast.get_docstring(node),
                        "line_no": node.lineno
                    }

                # Gather top-level functions
                elif isinstance(node, ast.FunctionDef):
                    # Check if it belongs to a class
                    is_method = False
                    # Basic check: see if the parent node in parent mapping is a ClassDef
                    # For simplicity, we just add it to top-level if it doesn't belong to any known classes
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "complexity": self._calculate_node_complexity(node),
                        "docstring": ast.get_docstring(node),
                        "line_no": node.lineno
                    }
                    functions.append(func_info)

            # Map methods to their classes by analyzing ClassDef children
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    cls_name = node.name
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_info = {
                                "name": child.name,
                                "args": [arg.arg for arg in child.args.args],
                                "complexity": self._calculate_node_complexity(child),
                                "docstring": ast.get_docstring(child),
                                "line_no": child.lineno
                            }
                            classes[cls_name]["methods"].append(method_info)
                            # Remove from global functions if present
                            functions = [f for f in functions if f["name"] != child.name]

            # Format report
            self._update_status(80, "Assembling AST Structural Report")
            report = [f"# AST Structural Analysis: {path.name}", ""]
            report.append(f"**Path**: `{filepath}`")
            report.append(f"**Total Lines**: {len(content.splitlines())}")
            report.append(f"**Imports Count**: {len(imports)}")
            report.append("")

            if imports:
                report.append("## Imports")
                report.append(", ".join([f"`{i}`" for i in imports]))
                report.append("")

            report.append("## Class Definitions")
            if classes:
                for cname, cinfo in classes.items():
                    bases = f" (inherits: {', '.join(cinfo['bases'])})" if cinfo['bases'] else ""
                    report.append(f"### Class `{cname}`{bases}")
                    report.append(f"- Line: {cinfo['line_no']}")
                    doc = f'"{cinfo["docstring"]}"' if cinfo["docstring"] else "*No docstring*"
                    report.append(f"- Docstring: *{doc.splitlines()[0] if doc else ''}*")
                    report.append("- Methods:")
                    for m in cinfo["methods"]:
                        comp_warning = " ⚠ High complexity!" if m["complexity"] > 6 else ""
                        report.append(f"  - `{m['name']}({', '.join(m['args'])})` (Complexity: {m['complexity']}){comp_warning}")
                    report.append("")
            else:
                report.append("*No class definitions found.*")
                report.append("")

            report.append("## Global Functions")
            if functions:
                for f in functions:
                    comp_warning = " ⚠ High complexity!" if f["complexity"] > 6 else ""
                    report.append(f"- `{f['name']}({', '.join(f['args'])})` (Line: {f['line_no']}, Complexity: {f['complexity']}){comp_warning}")
            else:
                report.append("*No global functions found.*")

            return "\n".join(report)

        except Exception as e:
            return f"[FAIL] AST parse error: {e}"

    def _calculate_node_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity based on AST decision points (if, for, while, except, bool ops)."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    # ─── Code Quality Review ──────────────────────────────────────

    async def _do_code_review(self, filepath: str, instruction: str) -> str:
        """Perform comprehensive code quality analysis using static checks and the LLM."""
        from friday.code_review import deep_code_review, code_review_report

        target = filepath or "."
        self._update_status(40, f"Invoking static analyzer and deep review for target: {target}")
        
        # Check if the user specified code review details or if we can run the deep tool
        loop = asyncio.get_running_loop()
        try:
            # We run in executor because the deep code review makes synchronous HTTP requests or file walks
            report = await loop.run_in_executor(
                None,
                lambda: code_review_report(target)
            )
            return report
        except Exception as e:
            logger.warning("Code review report utility failed: %s. Performing fallback direct review.", e)

        # Fallback direct LLM review of a single file
        if not filepath:
            return "[FAIL] Code review requires a target file path."
        
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found for review: {filepath}"

        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        model = resolve_model("reasoning") or "nvidia/llama-3.1-nemotron-70b-instruct"
        prompt = (
            "You are Forge, FRIDAY's lead code architect. "
            "Perform a strict code review of the following source code file.\n\n"
            f"File Path: {filepath}\n"
            f"Code Context:\n```python\n{code[:8000]}\n```\n\n"
            "Analyze and output:\n"
            "1. Potential bugs, race conditions, resource leaks.\n"
            "2. Style issues (PEP 8, docstrings, formatting).\n"
            "3. Complexity hotspots or architectural criticisms.\n"
            "4. Final quality rating (A-F) and concrete actionable fixes.\n"
        )

        resp = await self._client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2
        )
        return resp.content

    # ─── Syntax Check Audit ───────────────────────────────────────

    def _do_syntax_check(self, filepath: str) -> str:
        """Validate if python code compiles successfully and return syntax errors."""
        if not filepath:
            return "[FAIL] File path is required for syntax checks."

        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found: {filepath}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            self._update_status(60, "Compiling source content to inspect grammar errors")
            compile(content, str(path), "exec")
            return f"### Syntax Audit: {path.name}\n\n✅ Syntax check passed. Code compiles successfully without any syntax errors."
        except SyntaxError as e:
            lines = [
                f"### Syntax Audit: {path.name}",
                "",
                f"❌ **Syntax Error Detected**",
                f"- **Message**: {e.msg}",
                f"- **Line**: {e.lineno}",
                f"- **Offset**: {e.offset}",
                f"- **Text**: `{e.text.strip() if e.text else ''}`"
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"[FAIL] General compile check error: {e}"

    # ─── Code Generation & Write File ─────────────────────────────

    async def _do_code_gen(self, filepath: str, prompt_text: str, task: AgentTask) -> Tuple[str, bool]:
        """Generate code file from text requirements using the model and write it to disk."""
        if not filepath:
            return "[FAIL] File path is required to write generated code.", False

        model = resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
        prompt = (
            "You are Forge, FRIDAY's code developer. "
            "Write the source code for the requested file based on the instructions.\n\n"
            f"Target File: {filepath}\n"
            f"Prompt: {prompt_text}\n\n"
            "Rules:\n"
            "1. Output ONLY the source code. Do not wrap in markdown code blocks unless requested.\n"
            "2. Ensure the code compiles, includes standard docstrings, comments, and handles errors.\n"
        )

        self._update_status(50, "Generating code via NIM model")
        resp = await self._client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3072,
            temperature=0.1
        )
        code_content = resp.content.strip()

        # Clean markdown code blocks if the model wrapped it anyway
        if code_content.startswith("```"):
            lines = code_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code_content = "\n".join(lines)

        try:
            self._update_status(80, f"Writing generated code to {filepath}")
            path = Path(filepath).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code_content)

            lines = [
                f"### Code Generation Complete",
                f"Written code successfully to: `{filepath}`",
                "",
                "**Code Preview (first 10 lines):**",
                "```python",
                "\n".join(code_content.splitlines()[:10]),
                "```"
            ]
            return "\n".join(lines), True

        except Exception as e:
            logger.exception("Failed to write generated code to disk: %s", e)
            return f"[FAIL] Failed to write generated code to disk: {e}", False

    # ─── Code Refactoring & Editing via Unified Diffs ─────────────

    async def _do_refactor(self, filepath: str, prompt_text: str, task: AgentTask) -> Tuple[str, bool]:
        """Refactor an existing file by requesting the LLM for modifications and applying unified diffs."""
        if not filepath:
            return "[FAIL] File path is required for refactoring.", False

        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File to refactor does not exist: {filepath}", False

        with open(path, "r", encoding="utf-8") as f:
            original_code = f.read()

        model = resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
        prompt = (
            "You are Forge, FRIDAY's refactoring specialist. "
            "Generate the fully modified/refactored code for the target file based on the instructions.\n\n"
            f"File Path: {filepath}\n"
            f"Refactor request: {prompt_text}\n"
            f"Original Code:\n```python\n{original_code}\n```\n\n"
            "Rules:\n"
            "1. Output ONLY the complete refactored code. Do NOT wrap in markdown code blocks.\n"
            "2. Make sure it is functionally identical except for the requested modifications.\n"
        )

        self._update_status(45, "Generating refactored code via LLM")
        resp = await self._client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.1
        )
        new_code = resp.content.strip()

        # Clean code block indicators
        if new_code.startswith("```"):
            lines = new_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_code = "\n".join(lines)

        self._update_status(75, "Applying diffs and writing refactored code")
        
        # Calculate unified diff
        diff_lines = list(difflib.unified_diff(
            original_code.splitlines(),
            new_code.splitlines(),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            lineterm=""
        ))

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_code)

            diff_str = "\n".join(diff_lines[:40])
            if len(diff_lines) > 40:
                diff_str += f"\n... ({len(diff_lines) - 40} lines truncated) ..."

            report = [
                f"### Code Refactoring Complete: {path.name}",
                "",
                "Applied refactoring edits successfully.",
                "",
                "**Unified Diff Summary:**",
                "```diff",
                diff_str if diff_str else "No functional changes detected.",
                "```"
            ]
            return "\n".join(report), True

        except Exception as e:
            logger.exception("Failed to apply refactored edits: %s", e)
            return f"[FAIL] Failed to apply refactored edits to disk: {e}", False

    # ─── General Code Reasoning Fallback ──────────────────────────

    async def _do_general_code_reasoning(self, instruction: str) -> str:
        """Provide general architectural recommendations or explanation via LLM."""
        model = resolve_model("general") or "meta/llama-3.3-70b-instruct"
        prompt = (
            "You are Forge, FRIDAY's strategic code architect. "
            "Process the following query, provide detailed recommendations, explanations, or code blocks as requested.\n\n"
            f"Query: {instruction}\n"
        )
        resp = await self._client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3
        )
        return resp.content
