"""
FRIDAY Autonomous Git Branch/PR Tester and Self-Healing Repairer Agent.
Custom agent subclass of BaseAgent specialized in:
1. Fetching local git status, diffs, and modified files.
2. Generating detailed line-by-line commentary on changes using InferenceClient.
3. Spawning test runs in a subprocess, parsing failures (pytest/unittest).
4. Running a code self-healing loop to modify code/tests and verify success.
5. Committing and pushing successful fixes back to origin.
"""

from __future__ import annotations

import ast
import asyncio
import difflib
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.context_bus import get_bus, ContextBus
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

# Setup module-level logger
logger = logging.getLogger(__name__)

SYSTEM_REVIEW_PROMPT = """You are an expert software developer and security engineer. Your task is to perform a detailed, line-by-line code review of the provided Git diff.
Focus on correctness, logic bugs, edge cases, potential security issues, and style violations.
You must output your findings as a JSON array of objects. Each object MUST represent a specific comment on a specific line of a modified file.

JSON Schema:
[
  {
    "file": "filename",
    "line": 123,  // the 1-indexed line number in the new/modified file (must map to one of the '+' or ' ' lines from diff hunks)
    "type": "correctness" | "security" | "performance" | "style",
    "message": "Explanation of the issue",
    "suggestion": "Optional replacement code snippet or correction"
  }
]
Output ONLY valid JSON. If you wrap the output in markdown code blocks, use standard ```json. Do not include conversational text outside the JSON array."""

SYSTEM_REPAIR_PROMPT = """You are an expert developer with self-healing capabilities.
Your task is to fix a test failure by correcting either the implementation file or the test file.
You will be provided with:
1. The test failure details and traceback.
2. The implementation file content.
3. The test file content.

You must output a JSON object containing:
- "file_to_edit": The relative path of the file you chose to fix (either the implementation file or the test file).
- "new_content": The complete, updated content of that file.

JSON Schema:
{
  "file_to_edit": "path/to/file.py",
  "new_content": "... entire file contents with the fix applied ..."
}

Output ONLY valid JSON. If you wrap the output in markdown code blocks, use standard ```json. Do not include extra conversational text."""


class AutonomousPRReviewer(BaseAgent):
    """
    AutonomousPRReviewer - FRIDAY's autonomous PR/branch tester and repair agent.
    Performs branch diff analysis, runs test suites, self-heals code on test failures,
    and commits/pushes successful fixes.
    """

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self.bus = get_bus()
        self.client = InferenceClient()
        self.logger = logger
        
        # Configure repository path context
        from friday.paths import get_project_root
        self.repo_path = os.getenv("FRIDAY_REPO_PATH") or str(get_project_root())
        if not os.path.exists(self.repo_path):
            self.repo_path = os.getcwd()
            
        self.base_branch = "main"

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
            self.logger.debug("Failed to update status directly: %s", e)

    def _run_cmd(self, cmd: List[str] | str, shell: bool = False) -> Tuple[int, str, str]:
        """Runs a system command with logging and returns exit code, stdout, and stderr."""
        self.logger.info(f"Running command: {cmd} (shell={shell}, cwd={self.repo_path})")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=shell,
                encoding="utf-8",
                errors="replace"
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            self.logger.error(f"Command execution failed: {cmd}. Error: {e}")
            return -1, "", str(e)

    # ─── Git Operations ──────────────────────────────────────────

    def get_git_status(self) -> str:
        """Fetch local git status."""
        code, stdout, stderr = self._run_cmd(["git", "status"])
        if code != 0:
            raise RuntimeError(f"git status failed: {stderr}")
        return stdout

    def get_git_diff(self, base_branch: Optional[str] = None) -> str:
        """Fetch git diff against a base branch."""
        base = base_branch or self.base_branch
        # Verify base branch exists locally or origin
        code, _, _ = self._run_cmd(["git", "show-ref", f"refs/heads/{base}"])
        ref = base if code == 0 else f"origin/{base}"
        
        # Try full merge-base diff first (changes made on HEAD branch since branching off ref)
        code, stdout, stderr = self._run_cmd(["git", "diff", f"{ref}...HEAD"])
        if code != 0:
            code, stdout, stderr = self._run_cmd(["git", "diff", ref])
        if code != 0:
            code, stdout, stderr = self._run_cmd(["git", "diff", "HEAD"])
            
        return stdout

    def get_modified_files(self, base_branch: Optional[str] = None) -> List[str]:
        """List modified, added, or deleted files between base branch and HEAD."""
        base = base_branch or self.base_branch
        code, _, _ = self._run_cmd(["git", "show-ref", f"refs/heads/{base}"])
        ref = base if code == 0 else f"origin/{base}"
        
        code, stdout, stderr = self._run_cmd(["git", "diff", "--name-only", f"{ref}...HEAD"])
        if code != 0:
            code, stdout, stderr = self._run_cmd(["git", "diff", "--name-only", ref])
        if code != 0:
            code, stdout, stderr = self._run_cmd(["git", "diff", "--name-only", "HEAD"])
            
        if code != 0:
            # Fallback to status parsing
            code, stdout, stderr = self._run_cmd(["git", "status", "--porcelain"])
            files = []
            for line in stdout.splitlines():
                if len(line) > 3:
                    files.append(line[3:].strip())
            return list(set(files))
            
        files = [line.strip() for line in stdout.splitlines() if line.strip()]
        # Filter files that exist on disk
        valid_files = [f for f in files if os.path.exists(os.path.join(self.repo_path, f))]
        return list(set(valid_files))

    def _parse_unified_diff(self, diff_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parses a unified diff string into structured hunk records grouped by file path.
        Enables line-number mapping back to the modified file contents.
        """
        parsed_diff = {}
        current_file = None
        current_hunk = None
        
        file_header_re = re.compile(r'^diff --git a/(.*) b/(.*)$')
        hunk_header_re = re.compile(r'^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@')
        
        new_line_counter = 0
        
        for line in diff_text.splitlines():
            match = file_header_re.match(line)
            if match:
                current_file = match.group(2)
                parsed_diff[current_file] = []
                current_hunk = None
                continue
                
            if current_file is None:
                continue
                
            hunk_match = hunk_header_re.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_lines = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                new_start = int(hunk_match.group(3))
                new_lines = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                
                new_line_counter = new_start
                
                current_hunk = {
                    "header": line,
                    "old_start": old_start,
                    "old_lines": old_lines,
                    "new_start": new_start,
                    "new_lines": new_lines,
                    "lines": []
                }
                parsed_diff[current_file].append(current_hunk)
                continue
                
            if current_hunk is None:
                continue
                
            if line.startswith('+'):
                current_hunk["lines"].append(('+', line[1:], new_line_counter))
                new_line_counter += 1
            elif line.startswith('-'):
                current_hunk["lines"].append(('-', line[1:], None))
            elif line.startswith(' '):
                current_hunk["lines"].append((' ', line[1:], new_line_counter))
                new_line_counter += 1
                
        return parsed_diff

    # ─── LLM JSON Parser Helpers ──────────────────────────────────

    def _extract_json(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extracts a JSON list from text, handling markdown blocks."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass
            
        match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass
                
        match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0).strip())
            except Exception:
                pass
                
        return None

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts a single JSON object/dictionary from text."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass
            
        match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass
                
        match = re.search(r'{.*}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0).strip())
            except Exception:
                pass
                
        return None

    # ─── PR Review Generation ────────────────────────────────────

    async def review_branch_diffs(self, base_branch: Optional[str] = None) -> Dict[str, Any]:
        """Generates detailed line-by-line commentary on changes using InferenceClient."""
        base = base_branch or self.base_branch
        self.logger.info(f"Starting branch code review comparing with {base}")
        
        # Publish start event
        await self.bus.publish("pr_agent.started", {
            "branch": base,
            "action": "review",
            "timestamp": time.time()
        })
        
        diff_text = self.get_git_diff(base)
        modified_files = self.get_modified_files(base)
        
        if not diff_text or not modified_files:
            self.logger.info("No modifications detected.")
            result = {
                "summary": "No changes found on this branch compared to base.",
                "comments": [],
                "verdict": "Approve",
                "approved": True
            }
            await self.bus.publish("pr_agent.completed", {
                "action": "review",
                "result": result,
                "timestamp": time.time()
            })
            return result

        parsed_diff = self._parse_unified_diff(diff_text)
        all_comments = []
        
        for idx, filename in enumerate(modified_files):
            full_path = os.path.join(self.repo_path, filename)
            file_content = ""
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        file_content = f.read()
                except Exception as e:
                    self.logger.error(f"Cannot read {filename} for code review: {e}")
            
            file_diff_hunks = parsed_diff.get(filename, [])
            if not file_diff_hunks:
                continue
                
            hunks_str = json.dumps(file_diff_hunks, indent=2)
            user_prompt = f"""Review the changes for file: `{filename}`.
Here is the complete contents of the file as it stands on this branch:
---
{file_content}
---

Here are the diff hunks showing the modifications:
{hunks_str}

Perform a rigorous check. For any correctness, security, performance, or styling defects in the modified lines, generate a review comment mapping to the NEW line number (provided in the hunks diff details).
If no issues are found, return an empty array [].
"""
            # Publish file review progress
            pct = int((idx / len(modified_files)) * 100)
            await self.bus.publish("pr_agent.progress", {
                "action": "review",
                "progress_pct": pct,
                "message": f"Reviewing changes in {filename} ({idx+1}/{len(modified_files)})"
            })
            self._update_status(pct, f"Reviewing {filename}")
            
            try:
                model = resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
                resp = await self.client.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_REVIEW_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                
                comments = self._extract_json(resp.content)
                if comments:
                    for c in comments:
                        c["file"] = filename
                        all_comments.append(c)
                else:
                    self.logger.debug(f"No comments parsed for {filename}")
            except Exception as e:
                self.logger.error(f"Error during LLM chat for review of {filename}: {e}")
                
        # Generate summary assessment
        summary_prompt = f"""Summarize the code review results.
Here are the gathered comments:
{json.dumps(all_comments, indent=2)}

Provide a developer-friendly report summary that outlines:
1. Overall assessment of the changes.
2. Major defects (bugs, crashes, security risks).
3. Minor style or optimization recommendations.
4. Final verdict: "Approve" (if no critical defects) or "Changes Requested" (if correctness/security concerns exist).
"""
        try:
            model = resolve_model("general") or "meta/llama-3.3-70b-instruct"
            summary_resp = await self.client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a tech lead performing a branch review summary."},
                    {"role": "user", "content": summary_prompt}
                ]
            )
            summary_text = summary_resp.content
        except Exception as e:
            summary_text = f"Review completed. Detected {len(all_comments)} feedback comments."
            
        verdict = "Changes Requested" if any(c.get("type") in ("correctness", "security") for c in all_comments) else "Approve"
        
        result = {
            "summary": summary_text,
            "comments": all_comments,
            "verdict": verdict,
            "approved": verdict == "Approve"
        }
        
        await self.bus.publish("pr_agent.completed", {
            "action": "review",
            "result": result,
            "timestamp": time.time()
        })
        
        return result

    # ─── Heuristic Test Mapping and Running ───────────────────────

    def _find_test_files_for_modified(self, modified_files: List[str]) -> List[str]:
        """Heuristically finds test files related to modified source files."""
        test_files = []
        for file in modified_files:
            filename = os.path.basename(file)
            if filename.startswith("test_") or filename.endswith("_test.py"):
                test_files.append(file)
                continue
                
            base_name = os.path.splitext(filename)[0]
            # Search structures in repo
            search_patterns = [
                f"test_{base_name}.py",
                f"{base_name}_test.py",
                os.path.join("tests", f"test_{base_name}.py"),
                os.path.join("test", f"test_{base_name}.py"),
            ]
            for pattern in search_patterns:
                if os.path.exists(os.path.join(self.repo_path, pattern)):
                    test_files.append(pattern)
                elif os.path.exists(os.path.join(self.repo_path, pattern.replace("/", os.sep))):
                    test_files.append(pattern.replace("/", os.sep))
                    
        return list(set(test_files))

    def _find_imported_files(self, test_file_path: str) -> List[str]:
        """Parses the test file AST to identify imported files in the repo."""
        imported_files = []
        full_path = os.path.join(self.repo_path, test_file_path)
        if not os.path.exists(full_path):
            return []
            
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                
            tree = ast.parse(content, filename=test_file_path)
            for node in ast.walk(tree):
                module_name = ""
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ""
                
                if module_name:
                    parts = module_name.split('.')
                    possible_rel_paths = [
                        "/".join(parts) + ".py",
                        "/".join(parts) + "/__init__.py",
                    ]
                    if len(parts) > 1:
                        possible_rel_paths.append(parts[0] + ".py")
                        possible_rel_paths.append(parts[0] + "/__init__.py")
                        
                    for rel_p in possible_rel_paths:
                        for p in (rel_p, rel_p.replace("/", os.sep)):
                            candidate = os.path.join(self.repo_path, p)
                            if os.path.exists(candidate) and os.path.isfile(candidate):
                                imported_files.append(os.path.relpath(candidate, self.repo_path))
                                break
        except Exception as e:
            self.logger.error(f"Error parsing AST imports from {test_file_path}: {e}")
            # Fallback regex parsing
            try:
                imports = re.findall(r'^(?:import|from)\s+([\w\.]+)', content, re.MULTILINE)
                for imp in imports:
                    parts = imp.split('.')
                    base_name = parts[0]
                    possible_paths = [
                        f"{base_name}.py",
                        os.path.join(base_name, "__init__.py"),
                    ]
                    for p in possible_paths:
                        candidate = os.path.join(self.repo_path, p)
                        if os.path.exists(candidate):
                            imported_files.append(p)
            except Exception:
                pass
                
        return list(set(imported_files))

    def test_branch_changes(self, test_command: Optional[str] = None) -> Dict[str, Any]:
        """Spawns the test command in a subprocess and parses failures."""
        self.logger.info("Executing tests for branch modifications")
        modified_files = self.get_modified_files()
        
        if not test_command:
            test_files = self._find_test_files_for_modified(modified_files)
            if test_files:
                test_command = "pytest " + " ".join(test_files)
            else:
                test_command = "pytest"
                
        self.logger.info(f"Running command: {test_command}")
        code, stdout, stderr = self._run_cmd(test_command, shell=True)
        
        failures = self._parse_test_failures(stdout, stderr)
        
        return {
            "success": code == 0 and len(failures) == 0,
            "exit_code": code,
            "stdout": stdout,
            "stderr": stderr,
            "failures": failures,
            "test_command": test_command
        }

    def _parse_test_failures(self, stdout: str, stderr: str) -> List[Dict[str, Any]]:
        """Parses pytest / unittest outputs to isolate test case failures and tracebacks."""
        failures = []
        
        # Pytest failure blocks parsing
        pytest_hunk_re = re.compile(r'_{3,}\s*(.*?)\s*_{3,}\n(.*?)(?=\n_{3,}|\n={3,})', re.DOTALL)
        matches = pytest_hunk_re.findall(stdout)
        
        for test_name, block in matches:
            test_name = test_name.strip()
            file_line_match = re.search(r'([\w/\-\\]+\.py):(\d+): (.*)', block)
            file_path = file_line_match.group(1) if file_line_match else "unknown"
            line_num = int(file_line_match.group(2)) if file_line_match else 0
            error_msg = file_line_match.group(3) if file_line_match else "Test failed"
            
            error_details = []
            for line in block.splitlines():
                if line.startswith('E   ') or line.startswith('E '):
                    error_details.append(line)
            
            failures.append({
                "test_name": test_name,
                "file": file_path,
                "line": line_num,
                "error": error_msg,
                "details": "\n".join(error_details) or block.strip(),
                "full_traceback": block
            })
            
        # Unittest failure blocks parsing fallback
        if not failures and ("FAILED" in stdout or "errors" in stderr or "FAIL" in stdout):
            unittest_failure_re = re.compile(r'(FAIL|ERROR): (\w+) \(([\w.]+)\)\n(.*?)(?=\n(FAIL|ERROR): |\n-{5,}|\n={5,})', re.DOTALL)
            matches = unittest_failure_re.findall(stdout)
            for status, t_name, class_name, block in matches:
                tb_lines = block.strip().splitlines()
                offending_file = "unknown"
                offending_line = 0
                for line in reversed(tb_lines):
                    tb_match = re.search(r'File "([^"]+)", line (\d+)', line)
                    if tb_match:
                        offending_file = tb_match.group(1)
                        offending_line = int(tb_match.group(2))
                        break
                        
                error_msg = tb_lines[-1] if tb_lines else "Test failed"
                failures.append({
                    "test_name": f"{class_name}.{t_name}",
                    "file": offending_file,
                    "line": offending_line,
                    "error": error_msg,
                    "details": block.strip(),
                    "full_traceback": block
                })
                
        return failures

    # ─── Self-Healing Logic ──────────────────────────────────────

    async def auto_repair_failed_tests(self, test_failures: List[Dict[str, Any]], max_attempts: int = 3) -> Dict[str, Any]:
        """Uses a feedback-driven code repair loop to fix failing code files."""
        self.logger.info(f"Initiating self-healing repair. Total failures to resolve: {len(test_failures)}")
        
        await self.bus.publish("pr_agent.progress", {
            "action": "repair",
            "progress_pct": 0,
            "message": f"Starting auto-repair loop for {len(test_failures)} failing tests."
        })
        
        current_failures = test_failures
        attempt = 0
        repaired_files = []
        
        while current_failures and attempt < max_attempts:
            attempt += 1
            self.logger.info(f"Self-healing repair attempt {attempt}/{max_attempts}")
            
            await self.bus.publish("pr_agent.progress", {
                "action": "repair",
                "progress_pct": int(((attempt - 1) / max_attempts) * 100),
                "message": f"Repair attempt {attempt}/{max_attempts} in progress."
            })
            self._update_status(int(((attempt - 1) / max_attempts) * 100), f"Repairing attempt {attempt}")
            
            for failure in current_failures:
                test_file = failure["file"]
                test_name = failure["test_name"]
                
                test_full_path = os.path.join(self.repo_path, test_file)
                if not os.path.exists(test_full_path):
                    # Search for test file in workspace if path is partial
                    found_paths = []
                    for root, _, files in os.walk(self.repo_path):
                        for f in files:
                            if f == os.path.basename(test_file):
                                found_paths.append(os.path.relpath(os.path.join(root, f), self.repo_path))
                    if found_paths:
                        test_file = found_paths[0]
                        test_full_path = os.path.join(self.repo_path, test_file)
                
                # Fetch relevant implementation files imported by this test
                impl_files = self._find_imported_files(test_file)
                
                test_content = ""
                if os.path.exists(test_full_path):
                    with open(test_full_path, "r", encoding="utf-8", errors="replace") as f:
                        test_content = f.read()
                        
                impl_contents = {}
                for impl_file in impl_files:
                    impl_full_path = os.path.join(self.repo_path, impl_file)
                    if os.path.exists(impl_full_path):
                        with open(impl_full_path, "r", encoding="utf-8", errors="replace") as f:
                            impl_contents[impl_file] = f.read()
                            
                impl_context = "\n\n".join([f"--- FILE: {path} ---\n{content}" for path, content in impl_contents.items()])
                
                prompt = f"""Failed Test Name: {test_name}
Test File: {test_file}
Failure Line: {failure.get('line', 'unknown')}
Failure Details/Traceback:
{failure['details']}

--- TEST FILE: {test_file} ---
{test_content}

--- IMPLEMENTATION FILES ---
{impl_context or "No implementation files discovered."}

Locate the bug. Provide the updated file with changes applied to resolve the failure.
"""
                try:
                    model = resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
                    resp = await self.client.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_REPAIR_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1
                    )
                    
                    fix_data = self._extract_json_object(resp.content)
                    if fix_data and "file_to_edit" in fix_data and "new_content" in fix_data:
                        file_to_edit = fix_data["file_to_edit"]
                        new_content = fix_data["new_content"]
                        
                        target_path = os.path.join(self.repo_path, file_to_edit)
                        original_content = ""
                        if os.path.exists(target_path):
                            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                                original_content = f.read()
                                
                        # Print diff using standard library difflib
                        diff_lines = list(difflib.unified_diff(
                            original_content.splitlines(keepends=True),
                            new_content.splitlines(keepends=True),
                            fromfile=f"a/{file_to_edit}",
                            tofile=f"b/{file_to_edit}"
                        ))
                        if diff_lines:
                            self.logger.info(f"Applying self-healing patch to {file_to_edit}:\n" + "".join(diff_lines))
                            
                        # Apply edit
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                            
                        # Perform syntax validation
                        syntax_valid = True
                        if file_to_edit.endswith(".py"):
                            code, _, compile_err = self._run_cmd([sys.executable, "-m", "py_compile", file_to_edit])
                            if code != 0:
                                self.logger.warning(f"Syntax validation failed for repaired file: {compile_err}. Reverting.")
                                with open(target_path, "w", encoding="utf-8") as f:
                                    f.write(original_content)
                                syntax_valid = False
                                
                        if syntax_valid:
                            repaired_files.append(file_to_edit)
                            # Publish repaired event
                            await self.bus.publish("pr_agent.repaired", {
                                "file": file_to_edit,
                                "test_name": test_name,
                                "attempt": attempt,
                                "timestamp": time.time()
                            })
                    else:
                        self.logger.warning(f"Failed to extract structured repair JSON from model output: {resp.content}")
                except Exception as e:
                    self.logger.error(f"Error during auto-repair generation: {e}")
                    
            # Re-run tests to check state
            test_results = self.test_branch_changes()
            if test_results["success"]:
                self.logger.info("All tests passed after auto-repair updates.")
                current_failures = []
                break
            else:
                self.logger.info(f"Failures persist. Remaining failures: {len(test_results['failures'])}")
                current_failures = test_results["failures"]
                
        success = len(current_failures) == 0
        return {
            "success": success,
            "attempts": attempt,
            "repaired_files": list(set(repaired_files)),
            "remaining_failures": current_failures
        }

    # ─── Push Modifications ───────────────────────────────────────

    async def commit_and_push_fixes(self, branch_name: str, commit_message: Optional[str] = None) -> Dict[str, Any]:
        """Stages modifications, commits them, and pushes upstream to the branch remote."""
        self.logger.info(f"Committing and pushing self-healed fixes to branch: {branch_name}")
        
        code, stdout, _ = self._run_cmd(["git", "status", "--porcelain"])
        if not stdout.strip():
            self.logger.info("No modifications to commit.")
            return {"success": True, "committed": False, "pushed": False}
            
        code, _, stderr = self._run_cmd(["git", "add", "-A"])
        if code != 0:
            raise RuntimeError(f"git add failed: {stderr}")
            
        if not commit_message:
            diff_text = self.get_git_diff()
            if diff_text:
                try:
                    model = resolve_model("general") or "meta/llama-3.3-70b-instruct"
                    resp = await self.client.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a git commit bot. Output ONLY a clean, single-line commit message summarizing the changes. Do not wrap in quotes or code blocks."},
                            {"role": "user", "content": f"Write a commit message for this diff:\n\n{diff_text[:5000]}"}
                        ]
                    )
                    commit_message = resp.content.strip().strip('"').strip("'")
                except Exception:
                    pass
            if not commit_message:
                commit_message = "fix: autonomous self-healing of test failures"
                
        self.logger.info(f"Committing changes: {commit_message}")
        code, stdout, stderr = self._run_cmd(["git", "commit", "-m", commit_message])
        if code != 0:
            if "nothing to commit" in stdout or "nothing to commit" in stderr:
                self.logger.info("Nothing to commit.")
                return {"success": True, "committed": False, "pushed": False}
            raise RuntimeError(f"git commit failed: {stderr}")
            
        self.logger.info(f"Pushing branch '{branch_name}' to remote origin")
        code, stdout, stderr = self._run_cmd(["git", "push", "origin", branch_name])
        if code != 0:
            self.logger.info("Standard push failed. Attempting upstream registration...")
            code, stdout, stderr = self._run_cmd(["git", "push", "--set-upstream", "origin", branch_name])
            
        if code != 0:
            raise RuntimeError(f"git push failed: {stderr}")
            
        self.logger.info("Successfully pushed changes upstream.")
        return {"success": True, "committed": True, "pushed": True, "commit_msg": commit_message}

    # ─── End-to-End Workflow Coordinator ──────────────────────────

    async def run_workflow(self, branch_name: str, test_command: Optional[str] = None, max_repair_attempts: int = 3) -> Dict[str, Any]:
        """Coordinates the complete autonomous PR/branch lifecycle workflow."""
        self.logger.info(f"Beginning end-to-end PR pipeline on branch '{branch_name}'")
        
        await self.bus.publish("pr_agent.started", {
            "branch": branch_name,
            "test_command": test_command,
            "timestamp": time.time()
        })
        
        # 1. Review
        await self.bus.publish("pr_agent.progress", {
            "action": "workflow",
            "progress_pct": 10,
            "message": "Generating code review comments."
        })
        self._update_status(10, "Reviewing changes")
        review_results = await self.review_branch_diffs()
        
        # 2. Test Execution
        await self.bus.publish("pr_agent.progress", {
            "action": "workflow",
            "progress_pct": 40,
            "message": "Running test suite on current branch."
        })
        self._update_status(40, "Running tests")
        test_results = self.test_branch_changes(test_command)
        
        repair_results = None
        commit_results = None
        
        # 3. Auto-Repair on failure
        if not test_results["success"]:
            self.logger.info("Test failures encountered. Starting self-healing...")
            await self.bus.publish("pr_agent.progress", {
                "action": "workflow",
                "progress_pct": 60,
                "message": f"Tests failed with {len(test_results['failures'])} errors. Starting repairs."
            })
            self._update_status(60, "Running repairs")
            repair_results = await self.auto_repair_failed_tests(
                test_results["failures"], 
                max_attempts=max_repair_attempts
            )
            
            # 4. Push fixes
            if repair_results["success"] and repair_results["repaired_files"]:
                await self.bus.publish("pr_agent.progress", {
                    "action": "workflow",
                    "progress_pct": 90,
                    "message": "Repairs succeeded. Committing and pushing patches."
                })
                self._update_status(90, "Pushing changes")
                commit_results = await self.commit_and_push_fixes(branch_name)
            elif not repair_results["success"]:
                await self.bus.publish("pr_agent.progress", {
                    "action": "workflow",
                    "progress_pct": 95,
                    "message": "Self-healing attempts exhausted; some test failures remain."
                })
                self._update_status(95, "Failed to self-heal all tests")
        else:
            self.logger.info("All tests passed initially.")
            await self.bus.publish("pr_agent.progress", {
                "action": "workflow",
                "progress_pct": 95,
                "message": "All branch tests passed successfully."
            })
            self._update_status(95, "Tests passed")
            
        summary = {
            "branch": branch_name,
            "review": review_results,
            "tests_passed_initially": test_results["success"],
            "repairs_attempted": repair_results is not None,
            "repair_success": repair_results["success"] if repair_results else None,
            "repaired_files": repair_results["repaired_files"] if repair_results else [],
            "committed_and_pushed": commit_results["pushed"] if commit_results else False,
            "timestamp": time.time()
        }
        
        await self.bus.publish("pr_agent.completed", {
            "branch": branch_name,
            "summary": summary,
            "timestamp": time.time()
        })
        
        return summary

    # ─── BaseAgent Execute Entrypoint ─────────────────────────────

    async def execute(self, task: AgentTask) -> AgentResult:
        """Executes the assigned PR agent task."""
        t0 = time.monotonic()
        await self.bus.publish("agent.started", {
            "agent_id": self.id,
            "task_id": task.task_id,
            "task_type": task.task_type,
        })
        self._update_status(5, f"Booting Autonomous PR Agent: '{task.payload[:50]}'")

        try:
            payload = task.payload.strip().lower()
            base_branch = task.context_snapshot.get("base_branch") or self.base_branch
            test_command = task.context_snapshot.get("test_command")
            branch_name = task.context_snapshot.get("branch_name")
            
            # Discover active branch name
            if not branch_name:
                code, stdout, _ = self._run_cmd(["git", "branch", "--show-current"])
                if code == 0 and stdout.strip():
                    branch_name = stdout.strip()
                else:
                    branch_name = "main"

            if "review" in payload:
                self._update_status(20, "Running diff-based code review")
                review_res = await self.review_branch_diffs(base_branch=base_branch)
                status = "completed"
                output = f"Review Verdict: {review_res['verdict']}\n\nSummary:\n{review_res['summary']}\n\nComments:\n{json.dumps(review_res['comments'], indent=2)}"
                
            elif "test" in payload and "repair" not in payload and "fix" not in payload:
                self._update_status(20, f"Running tests on branch: {branch_name}")
                test_res = self.test_branch_changes(test_command=test_command)
                status = "completed" if test_res["success"] else "failed"
                output = f"Test Success: {test_res['success']}\nExit Code: {test_res['exit_code']}\nFailures Count: {len(test_res['failures'])}\n\nStdout:\n{test_res['stdout']}\n\nStderr:\n{test_res['stderr']}"
                
            elif "repair" in payload or "fix" in payload:
                self._update_status(20, "Running tests and resolving failures")
                test_res = self.test_branch_changes(test_command=test_command)
                if test_res["success"]:
                    status = "completed"
                    output = "All tests passed initially. No repairs required."
                else:
                    repair_res = await self.auto_repair_failed_tests(test_res["failures"])
                    status = "completed" if repair_res["success"] else "failed"
                    output = f"Repair Success: {repair_res['success']}\nAttempts: {repair_res['attempts']}\nRepaired Files: {repair_res['repaired_files']}\nRemaining Failures: {len(repair_res['remaining_failures'])}"
            
            else:
                self._update_status(10, f"Running full autonomous PR workflow on branch {branch_name}")
                workflow_res = await self.run_workflow(
                    branch_name=branch_name,
                    test_command=test_command
                )
                status = "completed" if (workflow_res["tests_passed_initially"] or workflow_res["repair_success"]) else "failed"
                output = f"Autonomous PR Workflow Complete.\n\nSummary:\n{json.dumps(workflow_res, indent=2)}"

            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, "PR Agent task completed successfully")
            
            await self.bus.publish(
                "agent.completed" if status == "completed" else "agent.failed",
                {"agent_id": self.id, "task_id": task.task_id, "output": output[:1000]},
            )

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.id,
                status=status,
                output=output,
                duration_ms=dur,
                model=resolve_model("code_gen") or self.nim_model or "nvidia/llama-3.1-nemotron-70b-instruct",
            )

        except Exception as e:
            self.logger.exception("PR Agent failed during execution: %s", e)
            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, f"Execution failed: {str(e)[:50]}")
            
            await self.bus.publish("agent.failed", {
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
