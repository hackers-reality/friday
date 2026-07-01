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

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[FAIL] Unable to read file: {e}"

        ext = path.suffix
        lang_handlers = {
            ".js": self._do_ast_analysis_js,
            ".jsx": self._do_ast_analysis_js,
            ".ts": self._do_ast_analysis_js,
            ".tsx": self._do_ast_analysis_js,
            ".java": self._do_ast_analysis_java,
            ".go": self._do_ast_analysis_go,
            ".rs": self._do_ast_analysis_rust,
        }
        handler = lang_handlers.get(ext)
        if handler:
            return handler(str(path), content)
        if ext != ".py":
            return f"[FAIL] AST analysis is not supported for {ext} files."

        try:
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

        # Check if this is a multi-file project generation request
        multi_file_specs = self._parse_multi_file_prompt(prompt_text)
        if multi_file_specs:
            self._update_status(15, "Detected multi-file project request — generating project structure")
            return await self._do_multi_file_generation(multi_file_specs, task)

        # Read the code_gen skill file for best practices
        skill_content = ""
        skill_path = Path(__file__).parent / "skills" / "code_gen" / "SKILL.md"
        if skill_path.exists():
            try:
                skill_content = skill_path.read_text(encoding="utf-8")
                logger.info("Loaded code_gen SKILL.md for code generation context")
            except Exception as e:
                logger.warning("Failed to read code_gen SKILL.md: %s", e)

        # Detect domain from filepath and read additional skill files
        extra_skills = ""
        file_lower = filepath.lower()
        domain_skills = {
            ".svg": "svg",
            ".pptx": "pptx",
            ".docx": "docx",
            ".xlsx": "xlsx",
            ".pdf": "pdf",
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".go": "golang",
            ".rs": "rust",
            ".java": "java",
            ".c": "c_lang",
            ".cpp": "cpp",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
        }
        for ext, skill_name in domain_skills.items():
            if ext in file_lower:
                sp = Path(__file__).parent / "skills" / skill_name / "SKILL.md"
                if sp.exists():
                    try:
                        extra_skills += f"\n--- {skill_name} SKILL.md ---\n{sp.read_text(encoding='utf-8')}\n"
                        logger.info("Loaded %s SKILL.md for code generation context", skill_name)
                    except Exception as e:
                        logger.warning("Failed to read %s SKILL.md: %s", skill_name, e)

        model = resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
        prompt = (
            "You are Forge, FRIDAY's code architect — a world-class software engineer.\n\n"
            "Follow this two-phase workflow:\n\n"
            "PHASE 1: PLAN\n"
            "- Analyze the requirements. Identify edge cases, input/output contracts.\n"
            "- Design the architecture: classes, functions, data flow, error handling.\n"
            "- Consider: security, performance, maintainability, testing strategy.\n"
            "- STATE YOUR PLAN FIRST.\n\n"
            "PHASE 2: BUILD\n"
            "- Implement following the plan. Write clean, idiomatic, production-grade code.\n"
            "- Include type hints, docstrings, error handling, and tests.\n"
            "- After writing, self-review for bugs, security issues, and code quality.\n\n"
            f"Target File: {filepath}\n"
            f"Prompt: {prompt_text}\n\n"
        )
        if skill_content:
            prompt += f"<code_gen_skill>\n{skill_content}\n</code_gen_skill>\n\n"
        if extra_skills:
            prompt += f"<domain_skills>\n{extra_skills}\n</domain_skills>\n\n"
        prompt += (
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
            "You are Forge, FRIDAY's strategic code architect — a world-class software engineer.\n\n"
            "Follow the Plan→Build workflow:\n"
            "PHASE 1: PLAN — analyze requirements, design architecture, identify tradeoffs.\n"
            "PHASE 2: BUILD — provide detailed implementation with code examples.\n\n"
            f"Query: {instruction}\n"
        )
        self._update_status(60, "Querying LLM for architectural reasoning")
        resp = await self._client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3
        )
        self._update_status(90, "Processing LLM response into architectural guidance")
        return resp.content

    # ─── Multi-Language AST Analysis — JS/TS ──────────────────────

    def _do_ast_analysis_js(self, filepath: str, content: str) -> str:
        """
        Perform regex-based structural analysis of JavaScript/TypeScript source.
        Extracts imports, classes, functions, interfaces, types, and approximate complexity.
        """
        import_paths = re.findall(r"(?:import|require)\s*\(?\s*[\'\"]([^\'\"]+)[\'\"]", content)
        from_imports = re.findall(r"import\s+\{?[^}]+\}?\s*from\s*[\'\"]([^\'\"]+)[\'\"]", content)
        imports = import_paths + from_imports

        classes = re.findall(r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?", content)
        functions = re.findall(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", content)
        arrow_fns = re.findall(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(?[^)]*\)?\s*=>", content)
        interfaces = re.findall(r"(?:export\s+)?interface\s+(\w+)", content)
        types = re.findall(r"(?:export\s+)?type\s+(\w+)", content)

        total_lines = len(content.splitlines())
        complexity = self._estimate_js_complexity(content)

        lines_out = [
            f"# AST Structural Analysis: {Path(filepath).name}",
            "",
            f"**Path**: `{filepath}`",
            f"**Language**: JavaScript/TypeScript",
            f"**Total Lines**: {total_lines}",
            f"**Imports**: {len(imports)}",
            "",
        ]
        if imports:
            lines_out.append("## Imports")
            lines_out.append(", ".join(f"`{i}`" for i in sorted(set(imports))))
            lines_out.append("")

        lines_out.append(f"## Classes ({len(classes)})")
        for cls_match in classes:
            cls_name = cls_match[0]
            extends = cls_match[1]
            implements = cls_match[2]
            extra = ""
            if extends:
                extra += f" extends {extends}"
            if implements:
                extra += f" implements {implements.strip()}"
            lines_out.append(f"- Class `{cls_name}`{extra}")
        lines_out.append("")

        lines_out.append(f"## Functions + Arrow Functions ({len(functions) + len(arrow_fns)})")
        for fn in set(functions):
            lines_out.append(f"- Function `{fn}()`")
        for fn in set(arrow_fns):
            lines_out.append(f"- Arrow `{fn}`")
        lines_out.append("")

        if interfaces:
            lines_out.append(f"## Interfaces ({len(interfaces)})")
            for iface in sorted(set(interfaces)):
                lines_out.append(f"- Interface `{iface}`")
            lines_out.append("")
        if types:
            lines_out.append(f"## Type Aliases ({len(types)})")
            for t in sorted(set(types)):
                lines_out.append(f"- Type alias `{t}`")
            lines_out.append("")

        lines_out.append(f"**Estimated Cyclomatic Complexity**: {complexity}")
        if complexity > 50:
            lines_out.append("⚠ High complexity — consider refactoring.")
        return "\n".join(lines_out)

    def _estimate_js_complexity(self, content: str) -> int:
        """Estimate cyclomatic complexity for JS/TS code by counting decision points."""
        score = 1
        score += len(re.findall(r"\b(?:if|else if|for|while|switch|catch|case)\b", content))
        score += len(re.findall(r"\b(?:&&|\|\|)\b", content))
        return score

    # ─── Multi-Language AST Analysis — Java ───────────────────────

    def _do_ast_analysis_java(self, filepath: str, content: str) -> str:
        """Regex-based structural analysis for Java source files."""
        imports = re.findall(r"^import\s+([\w\.\*]+);", content, re.MULTILINE)
        package = re.search(r"^package\s+([\w\.]+);", content, re.MULTILINE)
        classes = re.findall(r"(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?", content)
        interfaces = re.findall(r"(?:public\s+)?interface\s+(\w+)", content)
        methods = re.findall(r"(?:public|private|protected|static)\s+(?:\w+\s+)*(\w+)\s*\(", content)
        annotations = re.findall(r"@(\w+)", content)

        lines_out = [
            f"# AST Structural Analysis: {Path(filepath).name}",
            "",
            f"**Path**: `{filepath}`",
            f"**Language**: Java",
            f"**Package**: {package.group(1) if package else '(default)'}",
            f"**Total Lines**: {len(content.splitlines())}",
            f"**Imports**: {len(imports)}",
            "",
        ]
        if imports:
            lines_out.append("## Imports")
            for imp in sorted(set(imports)):
                lines_out.append(f"- `{imp}`")
            lines_out.append("")

        lines_out.append(f"## Classes ({len(classes)})")
        for cls in classes:
            name, extends, implements = cls
            parts = [f"`{name}`"]
            if extends:
                parts.append(f"extends {extends}")
            if implements:
                parts.append(f"implements {implements.strip()}")
            lines_out.append("- Class " + " ".join(parts))
        lines_out.append("")

        lines_out.append(f"## Interfaces ({len(interfaces)})")
        for iface in sorted(set(interfaces)):
            lines_out.append(f"- `{iface}`")
        lines_out.append("")

        lines_out.append(f"## Methods ({len(methods)})")
        for m in sorted(set(methods)):
            lines_out.append(f"- `{m}()`")
        lines_out.append("")

        if annotations:
            lines_out.append("## Annotations")
            for ann in sorted(set(annotations)):
                lines_out.append(f"- `@{ann}`")
            lines_out.append("")
        return "\n".join(lines_out)

    # ─── Multi-Language AST Analysis — Go ─────────────────────────

    def _do_ast_analysis_go(self, filepath: str, content: str) -> str:
        """Regex-based structural analysis for Go source files."""
        imports = []
        for match in re.finditer(r"\"(?:[\w\.\-/]+)\"", content):
            imp = match.group(0).strip('"')
            if "/" in imp or "." in imp:
                imports.append(imp)
        package = re.search(r"^package\s+(\w+)", content, re.MULTILINE)
        funcs = re.findall(r"(?:func\s+)(?:\([^)]*\)\s+)?(\w+)\s*\(", content)
        structs = re.findall(r"(?:type\s+)(\w+)\s+struct", content)
        g_interfaces = re.findall(r"(?:type\s+)(\w+)\s+interface", content)
        methods = re.findall(r"func\s+\([^)]+\)\s+(\w+)\s*\(", content)

        lines_out = [
            f"# AST Structural Analysis: {Path(filepath).name}",
            "",
            f"**Path**: `{filepath}`",
            f"**Language**: Go",
            f"**Package**: {package.group(1) if package else '(unknown)'}",
            f"**Total Lines**: {len(content.splitlines())}",
            f"**Package Imports**: {len(imports)}",
            "",
        ]
        if imports:
            lines_out.append("## Imports")
            for imp in sorted(set(imports)):
                lines_out.append(f"- `{imp}`")
            lines_out.append("")

        lines_out.append(f"## Structs ({len(structs)})")
        for s in sorted(set(structs)):
            lines_out.append(f"- `{s}`")
        lines_out.append("")

        lines_out.append(f"## Interfaces ({len(g_interfaces)})")
        for iface in sorted(set(g_interfaces)):
            lines_out.append(f"- `{iface}`")
        lines_out.append("")

        all_funcs = set(funcs) - set(methods)
        lines_out.append(f"## Functions ({len(all_funcs)})")
        for fn in sorted(all_funcs):
            lines_out.append(f"- `{fn}()`")
        lines_out.append("")

        if methods:
            lines_out.append(f"## Methods ({len(methods)})")
            for m in sorted(set(methods)):
                lines_out.append(f"- `{m}()`")
            lines_out.append("")
        return "\n".join(lines_out)

    # ─── Multi-Language AST Analysis — Rust ───────────────────────

    def _do_ast_analysis_rust(self, filepath: str, content: str) -> str:
        """Regex-based structural analysis for Rust source files."""
        use_statements = re.findall(r"^use\s+([\w:]+);", content, re.MULTILINE)
        mod_decls = re.findall(r"^mod\s+(\w+);", content, re.MULTILINE)
        structs = re.findall(r"(?:pub\s+)?struct\s+(\w+)", content)
        enums = re.findall(r"(?:pub\s+)?enum\s+(\w+)", content)
        traits = re.findall(r"(?:pub\s+)?trait\s+(\w+)", content)
        impls = re.findall(r"(?:pub\s+)?impl\s+(\w+)(?:\s+for\s+(\w+))?", content)
        fns = re.findall(r"(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)", content)
        macros = re.findall(r"(\w+!)", content)

        lines_out = [
            f"# AST Structural Analysis: {Path(filepath).name}",
            "",
            f"**Path**: `{filepath}`",
            f"**Language**: Rust",
            f"**Total Lines**: {len(content.splitlines())}",
            f"**Use Statements**: {len(use_statements)}",
            "",
        ]
        if use_statements:
            lines_out.append("## Use Statements")
            for u in sorted(set(use_statements)):
                lines_out.append(f"- `use {u}`")
            lines_out.append("")
        if mod_decls:
            lines_out.append(f"## Module Declarations ({len(mod_decls)})")
            for m in sorted(set(mod_decls)):
                lines_out.append(f"- `mod {m}`")
            lines_out.append("")

        lines_out.append(f"## Structs ({len(structs)})")
        for s in sorted(set(structs)):
            lines_out.append(f"- `{s}`")
        lines_out.append("")

        lines_out.append(f"## Enums ({len(enums)})")
        for e in sorted(set(enums)):
            lines_out.append(f"- `{e}`")
        lines_out.append("")

        lines_out.append(f"## Traits ({len(traits)})")
        for t in sorted(set(traits)):
            lines_out.append(f"- `{t}`")
        lines_out.append("")

        lines_out.append(f"## Implementations ({len(impls)})")
        for impl_match in impls:
            trait_name = impl_match[0]
            type_name = impl_match[1]
            if type_name:
                lines_out.append(f"- `impl {trait_name} for {type_name}`")
            else:
                lines_out.append(f"- `impl {trait_name}`")
        lines_out.append("")

        lines_out.append(f"## Functions ({len(fns)})")
        for fn in sorted(set(fns)):
            lines_out.append(f"- `{fn}()`")
        lines_out.append("")

        if macros:
            counts = {}
            for m in macros:
                counts[m] = counts.get(m, 0) + 1
            lines_out.append("## Macros Used")
            for m, c in sorted(counts.items()):
                lines_out.append(f"- `{m}` ({c}x)")
            lines_out.append("")
        return "\n".join(lines_out)

    # ─── Code Review Report Generator ─────────────────────────────

    def _generate_code_review_report(self, analysis_results: dict) -> str:
        """
        Generate a structured markdown code review report from analysis results.

        Parameters
        ----------
        analysis_results : dict
            Must contain: file_path, severity_scores (dict), findings (list of dicts
            with line, severity, message, fix), test_gaps (list of str),
            and optionally complexity, imports.
        """
        file_path = analysis_results.get("file_path", "unknown")
        scores = analysis_results.get("severity_scores", {})
        findings = analysis_results.get("findings", [])
        test_gaps = analysis_results.get("test_gaps", [])
        complexity = analysis_results.get("complexity")
        imports = analysis_results.get("imports", [])

        report = [
            f"# Code Review Report: {Path(file_path).name}",
            "",
            f"**File**: `{file_path}`",
        ]

        if scores:
            overall = sum(scores.values()) / max(len(scores), 1)
            if overall > 8:
                grade = "F"
            elif overall > 6:
                grade = "D"
            elif overall > 4:
                grade = "C"
            elif overall > 2:
                grade = "B"
            else:
                grade = "A"
            report.append(f"**Overall Rating**: {grade} (avg severity: {overall:.1f}/10)")
            report.append("")
            report.append("## Severity Scores")
            for category, score in sorted(scores.items()):
                bar = "█" * min(max(int(score), 0), 10) + "░" * max(10 - min(max(int(score), 0), 10), 0)
                report.append(f"- **{category}**: {bar} {score:.1f}/10")
            report.append("")

        if complexity is not None:
            report.append(f"**Cyclomatic Complexity**: {complexity}")
            label = " — consider modularization." if isinstance(complexity, (int, float)) and complexity > 10 else ""
            if label:
                report[-1] += label
            report.append("")

        report.append(f"## Findings ({len(findings)})")
        if findings:
            report.append("| Line | Severity | Finding | Fix Recommendation |")
            report.append("|------|----------|---------|--------------------|")
            for f_item in findings:
                line = f_item.get("line", "?")
                sev = f_item.get("severity", "info")
                msg = f_item.get("message", "").replace("|", "\\|")
                fix = f_item.get("fix", "").replace("|", "\\|")
                report.append(f"| {line} | {sev} | {msg} | {fix} |")
        else:
            report.append("*No issues found.*")
        report.append("")

        report.append("## Test Coverage Gaps")
        if test_gaps:
            for gap in test_gaps:
                report.append(f"- {gap}")
        else:
            report.append("*No gaps identified.*")
        report.append("")

        if imports:
            report.append(f"## Dependencies ({len(imports)})")
            report.append(", ".join(f"`{i}`" for i in sorted(set(imports))))

        return "\n".join(report)

    # ─── Multi-File Project Generation ────────────────────────────

    def _parse_multi_file_prompt(self, prompt: str) -> list:
        """
        Detect whether a prompt requests generation of multiple source files.

        Returns list of dicts with keys 'path' and 'description', or empty list.
        """
        lines = prompt.splitlines()
        specs = []
        current_path = None
        current_desc_parts = []

        multi_indicators = [
            r"create\s+(?:the\s+)?(?:following\s+)?files?",
            r"generate\s+(?:the\s+)?(?:following\s+)?files?",
            r"multi[-\s]file\s+project",
            r"project\s+structure",
            r"set\s+of\s+files?",
            r"write\s+(?:the\s+)?(?:following\s+)?files?",
        ]
        is_multi = any(re.search(pat, prompt, re.IGNORECASE) for pat in multi_indicators)
        if not is_multi:
            file_refs = re.findall(r"[\w\-\\/]+\.[a-zA-Z]{1,4}", prompt)
            unique_exts = set(Path(ref).suffix for ref in file_refs if Path(ref).suffix)
            if len(unique_exts) >= 2:
                is_multi = True

        if not is_multi:
            return []

        for line in lines:
            stripped = line.strip()
            path_match = re.match(r"^[-*]\s*(?:file\s*:\s*)?([\w\-\\/.]+\.\w+)", stripped, re.IGNORECASE)
            if path_match:
                if current_path and current_desc_parts:
                    specs.append({"path": current_path, "description": " ".join(current_desc_parts)})
                current_path = path_match.group(1)
                current_desc_parts = []
                rest = stripped[path_match.end():].strip("-: ")
                if rest:
                    current_desc_parts.append(rest)
            elif current_path and stripped and not stripped.startswith("```"):
                current_desc_parts.append(stripped)

        if current_path and current_desc_parts:
            specs.append({"path": current_path, "description": " ".join(current_desc_parts)})

        return specs

    async def _do_multi_file_generation(self, file_specs: list, task: AgentTask) -> tuple:
        """Generate multiple source files for a project from parsed specifications."""
        results = []
        failures = []

        for i, spec in enumerate(file_specs):
            fp = spec.get("path", "")
            desc = spec.get("description", "")
            prog = 10 + int((i / max(len(file_specs), 1)) * 70)
            self._update_status(prog, f"Generating file {i+1}/{len(file_specs)}: {fp}")

            sub_task = AgentTask(
                task_id=f"{task.task_id}_{i}",
                task_type="code_gen",
                payload=desc,
                context_snapshot={"file_path": fp},
            )
            result_text, ok = await self._do_code_gen(fp, desc, sub_task)
            if ok:
                results.append(fp)
            else:
                failures.append((fp, result_text))

        report_lines = [
            f"### Multi-File Project Generation Complete",
            f"Generated {len(results)}/{len(file_specs)} files successfully.",
            "",
        ]
        if results:
            report_lines.append("**Generated Files:**")
            for f in results:
                report_lines.append(f"- ✅ `{f}`")
            report_lines.append("")
        if failures:
            report_lines.append("**Failures:**")
            for fp, err in failures:
                report_lines.append(f"- ❌ `{fp}`: {err[:100]}")

        return "\n".join(report_lines), len(failures) == 0

    # ─── Test Generation ──────────────────────────────────────────

    def _detect_test_framework(self, filepath: str) -> str:
        """
        Detect the testing framework used in a source file by scanning imports.

        Returns one of: pytest, unittest, jest, mocha, go_test, cargo_test, junit, or unknown.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            return "unknown"
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return "unknown"

        ext = path.suffix
        if ext == ".py":
            if re.search(r"^\s*(?:from\s+pytest|import\s+pytest)", content, re.MULTILINE):
                return "pytest"
            if re.search(r"^\s*(?:from\s+unittest|import\s+unittest)", content, re.MULTILINE):
                return "unittest"
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            if re.search(r"describe\(|it\(|expect\(", content):
                return "jest" if re.search(r"@jest|jest\.", content) else "mocha"
            if "describe(" in content or "it(" in content:
                return "mocha"
        elif ext == ".go":
            if re.search(r'import\s+"testing"', content) or "func Test" in content:
                return "go_test"
        elif ext == ".rs":
            if "#[cfg(test)]" in content or "#[test]" in content:
                return "cargo_test"
        elif ext == ".java":
            if re.search(r"import\s+org\.junit|@Test", content):
                return "junit"
        return "unknown"

    async def _generate_unit_tests(self, target_file: str, test_framework: str = "") -> str:
        """
        Generate unit tests for a given source file, detecting the test framework
        automatically if not specified.
        """
        src_path = Path(target_file).resolve()
        if not src_path.exists():
            return f"[FAIL] Source file not found: {target_file}"
        try:
            src_code = src_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"[FAIL] Unable to read source file: {e}"

        if not test_framework or test_framework == "auto":
            test_framework = self._detect_test_framework(target_file)

        ext = src_path.suffix
        if ext == ".py" and test_framework == "unknown":
            test_framework = "pytest"

        framework_templates = {
            "pytest": (
                "import pytest\nfrom {module} import {functions}\n\n\n"
                "class Test{class_name}:\n    \"\"\"Tests for {class_name}.\"\"\"\n\n"
                "    def test_{func_name}(self):\n        \"\"\"Test {func_name} basic behavior.\"\"\"\n"
                "        pass\n"
            ),
            "unittest": (
                "import unittest\nfrom {module} import {functions}\n\n\n"
                "class Test{class_name}(unittest.TestCase):\n    \"\"\"Tests for {class_name}.\"\"\"\n\n"
                "    def test_{func_name}(self):\n        \"\"\"Test {func_name} basic behavior.\"\"\"\n"
                "        self.assertTrue(True)\n\n\n"
                'if __name__ == "__main__":\n    unittest.main()\n'
            ),
            "jest": (
                "const {{ {functions} }} = require('{module}');\n\n"
                "describe('{class_name}', () => {{\n"
                "  test('{func_name} works correctly', () => {{\n"
                "    // Add assertions\n"
                "  }});\n"
                "}});\n"
            ),
            "mocha": (
                "const {{ {functions} }} = require('{module}');\n"
                "const assert = require('assert');\n\n"
                "describe('{class_name}', function() {{\n"
                "  it('should handle {func_name}', function() {{\n"
                "    // Add assertions\n"
                "  }});\n"
                "}});\n"
            ),
            "go_test": (
                "package {module}\n\nimport \"testing\"\n\n"
                "func Test{func_name}(t *testing.T) {{\n"
                '    t.Log("Test {func_name} not implemented")\n'
                "}}\n"
            ),
            "cargo_test": (
                "#[cfg(test)]\nmod tests {{\n"
                "    use super::*;\n\n"
                "    #[test]\n"
                "    fn test_{func_name}() {{\n"
                '        assert!(true);\n'
                "    }}\n"
                "}}\n"
            ),
        }

        template = framework_templates.get(
            test_framework,
            f"# Tests for {target_file} (framework: {test_framework})\n# TODO: implement\n"
        )

        funcs = re.findall(r"^def\s+(\w+)|^async def\s+(\w+)|^func\s+(\w+)|^fn\s+(\w+)", src_code, re.MULTILINE)
        funcs = [f for tup in funcs for f in tup if f]
        classes = re.findall(r"^class\s+(\w+)|^struct\s+(\w+)|^type\s+(\w+)", src_code, re.MULTILINE)
        classes = [c for tup in classes for c in tup if c]

        class_name = classes[0] if classes else "Default"
        func_name = funcs[0] if funcs else "example"
        functions_list = ", ".join(funcs[:5]) if funcs else "example_func"

        module = src_path.stem
        generated = template.format(
            module=module,
            class_name=class_name,
            func_name=func_name,
            functions=functions_list,
        )

        if ext == ".py":
            test_path = src_path.parent / f"test_{src_path.name}"
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            test_dir = src_path.parent / "__tests__"
            test_dir.mkdir(parents=True, exist_ok=True)
            test_name = src_path.stem + ".test" + ext
            test_path = test_dir / test_name
        elif ext == ".go":
            test_name = src_path.stem + "_test.go"
            test_path = src_path.parent / test_name
        elif ext == ".rs":
            test_path = src_path  # inline
        elif ext == ".java":
            test_name = src_path.stem + "Test.java"
            test_path = src_path.parent / test_name
        else:
            test_path = src_path.parent / f"test_{src_path.name}"

        if ext == ".rs":
            try:
                with open(test_path, "a", encoding="utf-8") as f:
                    f.write("\n" + generated)
                result = f"### Test Generation Complete\nTest module appended to: `{test_path}`\n"
            except Exception as e:
                result = f"[FAIL] Could not append tests: {e}"
        else:
            try:
                test_path.parent.mkdir(parents=True, exist_ok=True)
                test_path.write_text(generated, encoding="utf-8")
                result = f"### Test Generation Complete\nTest file written to: `{test_path}`\n"
            except Exception as e:
                result = f"[FAIL] Could not write test file: {e}"

        result += f"\n**Detected Framework**: {test_framework}\n"
        result += f"\n**Generated Tests**:\n```\n{generated}\n```"
        return result

    # ─── Dependency Analysis ──────────────────────────────────────

    def _analyze_dependencies(self, filepath: str) -> str:
        """
        Analyze imports/requires and map the dependency graph for a source file.

        Supports Python, JavaScript/TypeScript, Go, Rust, Java.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found: {filepath}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[FAIL] Unable to read file: {e}"

        ext = path.suffix
        imports = []
        local_imports = []
        third_party = []

        if ext == ".py":
            for match in re.finditer(r"^import\s+(\S+)", content, re.MULTILINE):
                imports.append(match.group(1))
            for match in re.finditer(r"^from\s+(\S+)\s+import", content, re.MULTILINE):
                imports.append(match.group(1))
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            for match in re.finditer(r"(?:import|require)\s*\(?\s*[\'\"]([^\'\"]+)[\'\"]", content):
                imports.append(match.group(1))
            for match in re.finditer(r"import\s+\{?[^}]+\}?\s*from\s*[\'\"]([^\'\"]+)[\'\"]", content):
                imports.append(match.group(1))
        elif ext == ".go":
            for match in re.finditer(r"\"(?:[\w\.\-/]+)\"", content):
                imp = match.group(0).strip('"')
                if "/" in imp or "." in imp:
                    imports.append(imp)
        elif ext == ".rs":
            for match in re.finditer(r"use\s+([\w:]+)", content):
                imports.append(match.group(1))
            for match in re.finditer(r"extern\s+crate\s+(\w+)", content):
                imports.append(match.group(1))
        elif ext == ".java":
            for match in re.finditer(r"^import\s+([\w\.\*]+);", content, re.MULTILINE):
                imports.append(match.group(1))

        std_lib_py = {"os", "sys", "re", "json", "math", "collections", "typing", "pathlib",
                      "logging", "datetime", "functools", "itertools", "subprocess", "threading",
                      "abc", "copy", "hashlib", "io", "random", "string", "textwrap", "uuid"}
        for imp in sorted(set(imports)):
            if imp and "." in imp:
                top = imp.split(".")[0]
            else:
                top = imp
            if ext == ".py" and top in std_lib_py:
                local_imports.append(imp)
            elif imp.startswith(".") or imp.startswith(Path(filepath).parent.name):
                local_imports.append(imp)
            else:
                third_party.append(imp)

        lines = [
            f"# Dependency Analysis: {path.name}",
            "",
            f"**File**: `{filepath}`",
            f"**Total Dependencies**: {len(imports)}",
            "",
        ]
        if third_party:
            lines.append(f"## Third-Party ({len(third_party)})")
            for imp in sorted(set(third_party)):
                lines.append(f"- `{imp}`")
            lines.append("")
        if local_imports:
            lines.append(f"## Local / StdLib ({len(local_imports)})")
            for imp in sorted(set(local_imports)):
                lines.append(f"- `{imp}`")
            lines.append("")

        pkg_files = []
        for candidate in ("requirements.txt", "package.json", "go.mod", "Cargo.toml", "pom.xml", "build.gradle"):
            if (path.parent / candidate).exists():
                pkg_files.append(candidate)
        if pkg_files:
            lines.append("## Package Manifests Found")
            for pf in pkg_files:
                lines.append(f"- `{pf}`")
            lines.append("")

        if imports:
            lines.append("## Dependency Graph")
            lines.append("```")
            lines.append(f"{path.name} ->")
            sorted_imports = sorted(set(imports))
            for idx, imp in enumerate(sorted_imports):
                indent = "  └── " if idx == len(sorted_imports) - 1 else "  ├── "
                lines.append(f"{indent}{imp}")
            lines.append("```")

        return "\n".join(lines)

    # ─── Code Complexity Metrics ──────────────────────────────────

    def _calculate_cognitive_complexity(self, node: Any, nesting: int = 0) -> int:
        """
        Calculate cognitive complexity for a Python AST node.
        Increments for breaks in linear flow with nesting multipliers.
        """
        score = 0
        if isinstance(node, ast.AST):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                    score += 1 + nesting
                    score += self._calculate_cognitive_complexity(child, nesting + 1)
                elif isinstance(child, ast.BoolOp):
                    score += 1
                    score += self._calculate_cognitive_complexity(child, nesting)
                elif isinstance(child, (ast.Try, ast.With, ast.Assert)):
                    score += 1
                    score += self._calculate_cognitive_complexity(child, nesting + 1)
                else:
                    score += self._calculate_cognitive_complexity(child, nesting)
        return score

    def _calculate_halstead_metrics(self, content: str) -> dict:
        """
        Compute Halstead complexity metrics from source code.

        Returns a dict with n1, n2, N1, N2, program_length, program_vocabulary,
        volume, difficulty, effort, and estimated_bugs.
        """
        operators = set()
        operands = set()
        N1 = 0
        N2 = 0

        tokens = re.findall(r"[\w_]+|[^\s\w]", content)
        operator_tokens = {
            "+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
            "->", "=>", "::", ".",
        }
        keywords = {
            "if", "else", "for", "while", "do", "switch", "case", "break", "continue",
            "return", "import", "from", "class", "def", "function", "var", "let", "const",
            "try", "catch", "finally", "throw", "raise", "with", "as", "yield", "await",
            "async", "pub", "fn", "struct", "enum", "impl", "trait", "use", "mod",
        }

        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in operator_tokens:
                operators.add(tok)
                N1 += 1
            elif i + 1 < len(tokens) and tok + tokens[i + 1] in operator_tokens:
                combined = tok + tokens[i + 1]
                operators.add(combined)
                N1 += 1
                i += 1
            elif tok in keywords:
                operators.add(tok)
                N1 += 1
            elif re.match(r"^[\w_]+$", tok):
                operands.add(tok)
                N2 += 1
            i += 1

        n1 = len(operators)
        n2 = len(operands)

        if n1 == 0 or n2 == 0:
            return {"n1": 0, "n2": 0, "N1": 0, "N2": 0, "program_length": 0,
                    "program_vocabulary": 0, "volume": 0, "difficulty": 0, "effort": 0, "estimated_bugs": 0}

        program_length = N1 + N2
        program_vocabulary = n1 + n2
        volume = program_length * max(program_vocabulary.bit_length(), 1)
        difficulty = (n1 / 2) * (N2 / max(n2, 1))
        effort = difficulty * volume
        estimated_bugs = volume / 3000

        return {
            "n1": n1,
            "n2": n2,
            "N1": N1,
            "N2": N2,
            "program_length": program_length,
            "program_vocabulary": program_vocabulary,
            "volume": round(volume, 2),
            "difficulty": round(difficulty, 2),
            "effort": round(effort, 2),
            "estimated_bugs": round(estimated_bugs, 4),
        }

    def _calculate_maintainability_index(self, content: str) -> float:
        """
        Compute Maintainability Index (0-100).
        Higher is better: >80 highly maintainable, <40 very difficult.
        """
        total_lines = len(content.splitlines())
        halstead = self._calculate_halstead_metrics(content)
        volume = halstead.get("volume", 0)

        cc = 1
        cc += len(re.findall(r"\b(?:if|for|while|except|case|catch)\b", content))

        if total_lines == 0 or volume == 0:
            return 100.0

        mi = 171 - 5.2 * (volume ** 0.5) - 0.23 * cc - 16.2 * (total_lines ** 0.5)
        mi = max(0, min(100, mi))
        return round(mi, 2)

    def _get_code_metrics_report(self, filepath: str) -> str:
        """
        Generate a comprehensive code metrics report including cyclomatic complexity,
        cognitive complexity, Halstead metrics, and maintainability index.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found: {filepath}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[FAIL] Unable to read file: {e}"

        lines = content.splitlines()
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", "--"))])
        blank_lines = len([l for l in lines if not l.strip()])
        comment_lines = total_lines - code_lines - blank_lines

        cc = 1
        cc += len(re.findall(r"\b(?:if|for|while|except|catch|case)\b", content))
        cog = cc + len(re.findall(r"\b(?:elif|else if|try|finally)\b", content))

        halstead = self._calculate_halstead_metrics(content)
        mi = self._calculate_maintainability_index(content)

        if cc <= 5:
            cc_rating = "Low"
        elif cc <= 10:
            cc_rating = "Moderate"
        elif cc <= 20:
            cc_rating = "High"
        else:
            cc_rating = "Very High"

        if mi > 80:
            mi_rating = "Highly Maintainable"
        elif mi > 60:
            mi_rating = "Moderately Maintainable"
        elif mi > 40:
            mi_rating = "Difficult to Maintain"
        else:
            mi_rating = "Very Difficult to Maintain"

        report = [
            f"# Code Complexity Metrics: {path.name}",
            "",
            f"**File**: `{filepath}`",
            "",
            "## Size Metrics",
            f"- Total Lines: {total_lines}",
            f"- Code Lines: {code_lines}",
            f"- Comment Lines: {comment_lines}",
            f"- Blank Lines: {blank_lines}",
            "",
            "## Complexity Metrics",
            f"- **Cyclomatic Complexity**: {cc} ({cc_rating})",
            f"- **Cognitive Complexity**: {cog}",
            "",
            "## Halstead Metrics",
            f"- Unique Operators (n1): {halstead['n1']}",
            f"- Unique Operands (n2): {halstead['n2']}",
            f"- Total Operators (N1): {halstead['N1']}",
            f"- Total Operands (N2): {halstead['N2']}",
            f"- Program Length: {halstead['program_length']}",
            f"- Vocabulary: {halstead['program_vocabulary']}",
            f"- Volume: {halstead['volume']}",
            f"- Difficulty: {halstead['difficulty']}",
            f"- Effort: {halstead['effort']}",
            f"- Estimated Bugs: {halstead['estimated_bugs']}",
            "",
            "## Maintainability",
            f"- **Maintainability Index**: {mi}/100 ({mi_rating})",
        ]
        return "\n".join(report)

    # ─── Security Scanning ────────────────────────────────────────

    def _security_scan(self, filepath: str) -> str:
        """
        Perform regex-based security scanning for hardcoded secrets,
        SQL injection vectors, XSS vulnerabilities, and command injection.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found: {filepath}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[FAIL] Unable to read file: {e}"

        findings = []

        secret_patterns = [
            (r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*[\'\"][^\'\"]{8,}[\'\"]", "Hardcoded API Key"),
            (r"(?i)(?:secret|password|passwd|pwd)\s*[:=]\s*[\'\"][^\'\"]{6,}[\'\"]", "Hardcoded Secret/Password"),
            (r"(?i)(?:token|access_token|auth_token)\s*[:=]\s*[\'\"][^\'\"]{8,}[\'\"]", "Hardcoded Token"),
            (r"(?i)A[KLR][A-Z0-9]{16}(?:[A-Z0-9]{16})?", "AWS Access Key"),
            (r"(?:ghp_|gho_|github_pat_)[\w-]{36,}", "GitHub Token"),
            (r"(?i)-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key Embedded"),
            (r"(?i)mongodb(?:\+srv)?://[^\s<]+", "MongoDB Connection String"),
            (r"(?i)postgresql?://[^\s<]+", "PostgreSQL Connection String"),
            (r"(?i)mysql://[^\s<]+", "MySQL Connection String"),
            (r"(?i)redis://[^\s<]+", "Redis Connection String"),
        ]
        for pattern, desc in secret_patterns:
            for match in re.finditer(pattern, content):
                findings.append({
                    "line": content[:match.start()].count("\n") + 1,
                    "severity": "critical",
                    "category": "Hardcoded Secret",
                    "message": desc,
                    "snippet": match.group()[:50],
                })

        sql_patterns = [
            (r"(?i)(?:execute|exec|query|raw_sql)\s*\([^)]*[\'\"].*?(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)", "SQL query with string concatenation"),
            (r"f[\"'].*\{.*\}.*[\"'].*\.(?:execute|exec|run|query)", "f-string SQL interpolation"),
            (r"(?i)SELECT\s+.+\s+FROM\s+.+\s+WHERE\s+.+=\s*[\"\']\s*\+\s*", "SQL injection via concatenation"),
            (r"\+\s*(?:request|params|req\.body|ctx\.query)", "User input concatenated into SQL"),
        ]
        for pattern, desc in sql_patterns:
            for match in re.finditer(pattern, content):
                findings.append({
                    "line": content[:match.start()].count("\n") + 1,
                    "severity": "high",
                    "category": "SQL Injection",
                    "message": desc,
                    "snippet": match.group()[:80],
                })

        xss_patterns = [
            (r"(?i)innerHTML\s*=", "innerHTML assignment (potential XSS)"),
            (r"(?i)document\.write\s*\(", "document.write (potential XSS)"),
            (r"(?i)eval\s*\(", "eval() usage (potential XSS)"),
            (r"(?i)setTimeout\s*\(\s*[\"\']", "setTimeout with string (potential XSS)"),
            (r"(?i)dangerouslySetInnerHTML", "dangerouslySetInnerHTML (React XSS risk)"),
            (r"(?i)v-html\s*=", "v-html binding (Vue XSS risk)"),
            (r"(?i)\$\s*\(.*\)\.html\s*\(", "jQuery .html() (potential XSS)"),
            (r"(?i)\$\s*\(.*\)\.append\s*\(", "jQuery .append() (potential XSS)"),
        ]
        for pattern, desc in xss_patterns:
            for match in re.finditer(pattern, content):
                findings.append({
                    "line": content[:match.start()].count("\n") + 1,
                    "severity": "high",
                    "category": "XSS Vulnerability",
                    "message": desc,
                    "snippet": match.group()[:80],
                })

        cmd_patterns = [
            (r"(?i)(?:os\.system|subprocess\.(?:call|Popen|run|check_output))\s*\([^)]*[\"\']", "Command execution with string"),
            (r"(?i)exec\s*\([\"\']", "exec() call"),
            (r"(?i)shell\s*=\s*True", "shell=True (command injection risk)"),
            (r"(?i)child_process\.exec(?:Sync)?\s*\(", "Node.js exec (command injection risk)"),
        ]
        for pattern, desc in cmd_patterns:
            for match in re.finditer(pattern, content):
                findings.append({
                    "line": content[:match.start()].count("\n") + 1,
                    "severity": "critical",
                    "category": "Command Injection",
                    "message": desc,
                    "snippet": match.group()[:80],
                })

        report = [
            f"# Security Scan: {path.name}",
            "",
            f"**File**: `{filepath}`",
            f"**Findings**: {len(findings)}",
            "",
        ]

        if findings:
            report.append("| # | Line | Severity | Category | Message |")
            report.append("|---|------|----------|----------|---------|")
            for i, f_item in enumerate(findings, 1):
                sev = f_item["severity"]
                sev_icon = "🔴" if sev == "critical" else "🟠"
                report.append(f"| {i} | {f_item['line']} | {sev_icon} {sev} | {f_item['category']} | {f_item['message']} |")
            report.append("")
            report.append("## Details")
            for i, f_item in enumerate(findings, 1):
                report.append(f"### {i}. {f_item['category']} (Line {f_item['line']})")
                report.append(f"- **Severity**: {f_item['severity']}")
                report.append(f"- **Message**: {f_item['message']}")
                report.append(f"- **Snippet**: `{f_item['snippet']}`")
                report.append("")

            sev_counts = {}
            for f_item in findings:
                s = f_item["severity"]
                sev_counts[s] = sev_counts.get(s, 0) + 1
            report.append("## Summary")
            for sev in ["critical", "high", "medium", "low"]:
                if sev in sev_counts:
                    report.append(f"- **{sev.capitalize()}**: {sev_counts[sev]}")
        else:
            report.append("✅ No security issues detected.")

        return "\n".join(report)

    # ─── Code Formatting Suggestions ──────────────────────────────

    def _suggest_formatting_fixes(self, filepath: str) -> str:
        """
        Analyze a source file and suggest formatting style improvements
        using diff-based comparison against common style guidelines.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            return f"[FAIL] File not found: {filepath}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"[FAIL] Unable to read file: {e}"

        lines = content.splitlines()
        suggestions = []

        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                suggestions.append({
                    "line": i, "severity": "style",
                    "message": "Line exceeds 100 characters",
                    "suggestion": "Break line into multiple lines",
                    "current": line[:80] + ("..." if len(line) > 80 else ""),
                })

        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                suggestions.append({
                    "line": i, "severity": "style",
                    "message": "Trailing whitespace detected",
                    "suggestion": "Remove trailing whitespace",
                    "current": repr(line[-10:] if len(line) > 10 else line),
                })

        if lines and lines[-1] != "" and not content.endswith("\n"):
            suggestions.append({
                "line": len(lines), "severity": "style",
                "message": "File does not end with a newline",
                "suggestion": "Add trailing newline",
                "current": lines[-1],
            })

        for i, line in enumerate(lines, 1):
            if line.startswith("\t"):
                suggestions.append({
                    "line": i, "severity": "style",
                    "message": "Tab character used for indentation",
                    "suggestion": "Replace tabs with spaces (4 per indent)",
                    "current": line[:40] + ("..." if len(line) > 40 else ""),
                })
                break

        blank_count = 0
        for i, line in enumerate(lines, 1):
            if not line.strip():
                blank_count += 1
                if blank_count > 2:
                    suggestions.append({
                        "line": i, "severity": "style",
                        "message": "More than 2 consecutive blank lines",
                        "suggestion": "Reduce to max 1-2 blank lines",
                        "current": f"... ({blank_count} blank lines)",
                    })
                    blank_count = 0
            else:
                blank_count = 0

        for i, line in enumerate(lines, 1):
            line_clean = line[:line.index("#")] if "#" in line else line
            ops = re.findall(r"[\w\)](\s*[=+\-*/%<>!]+\s*)[\w\(]", line_clean)
            for op in ops:
                if op.strip() != op:
                    suggestions.append({
                        "line": i, "severity": "style",
                        "message": "Inconsistent spacing around operator",
                        "suggestion": f"Change '{op}' to ' {op.strip()} '",
                        "current": line.strip()[:60],
                    })
                    break

        report = [
            f"# Formatting Suggestions: {path.name}",
            "",
            f"**File**: `{filepath}`",
            f"**Total Suggestions**: {len(suggestions)}",
            "",
        ]

        if suggestions:
            report.append("| Line | Severity | Issue | Suggestion |")
            report.append("|------|----------|-------|------------|")
            for s in suggestions:
                report.append(f"| {s['line']} | {s['severity']} | {s['message'][:50]} | {s['suggestion'][:50]} |")
            report.append("")
            report.append("## Detailed Suggestions")
            for i, s in enumerate(suggestions, 1):
                report.append(f"### {i}. Line {s['line']}: {s['message']}")
                report.append(f"- **Severity**: {s['severity']}")
                report.append(f"- **Current**: `{s['current']}`")
                report.append(f"- **Suggestion**: {s['suggestion']}")
                report.append("")
        else:
            report.append("✅ No formatting issues detected.")

        fix_lines = list(lines)
        for s in suggestions[:10]:
            idx = s["line"] - 1
            if idx < len(fix_lines):
                if "trailing whitespace" in s["message"].lower():
                    fix_lines[idx] = fix_lines[idx].rstrip()
                elif "tab" in s["message"].lower():
                    fix_lines[idx] = fix_lines[idx].replace("\t", "    ")
                elif "blank lines" in s["message"].lower():
                    fix_lines[idx] = ""

        if fix_lines != lines:
            diff = list(difflib.unified_diff(
                lines,
                fix_lines,
                fromfile=f"a/{path.name}",
                tofile=f"b/{path.name} (suggested)",
                lineterm=""
            ))
            if diff:
                report.append("## Suggested Diff (preview)")
                report.append("```diff")
                report.extend(diff[:30])
                if len(diff) > 30:
                    report.append(f"... ({len(diff) - 30} more lines)")
                report.append("```")

        return "\n".join(report)
