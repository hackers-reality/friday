"""
Coding Auto-Fix Loop — FRIDAY self-testing code agent.
Iteratively runs tests, parses failures, auto-fixes code via LLM,
and re-runs until all pass or max iterations reached.

Architecture:
  1. Run user's test command (pytest, unittest, node test, etc.)
  2. Parse failure output to identify error locations + messages
  3. Read source files at error locations
  4. Call LLM to generate fixes
  5. Apply fixes via edit
  6. Re-run tests
  7. Loop until green or max_iterations
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY


MAX_FIX_ITERATIONS = 5


def _run_command(cmd: str, cwd: str, timeout: int = 120) -> dict:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": f"Command timed out after {timeout}s", "success": False}
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e), "success": False}


def _parse_test_failures(output: str) -> list[dict]:
    """Parse test failure output to extract file, line, and error message."""
    failures = []

    # Python pytest format
    pytest_pattern = re.compile(
        r'(?:FAILED|ERROR)\s+(\S+?\.py)\:\:(\w+).*?\-\s+(.*?)$',
        re.MULTILINE,
    )
    for m in pytest_pattern.finditer(output):
        failures.append({
            "file": m.group(1),
            "test": m.group(2),
            "message": m.group(3).strip()[:200],
            "type": "pytest",
        })

    # Python traceback format (File "...", line N, in ...)
    tb_pattern = re.compile(
        r'File\s+"([^"]+\.py)",\s+line\s+(\d+).*?\n\s+(.*?)$',
        re.MULTILINE,
    )
    for m in tb_pattern.finditer(output):
        failures.append({
            "file": m.group(1),
            "line": int(m.group(2)),
            "message": m.group(3).strip()[:200],
            "type": "traceback",
        })

    # AssertionError format
    assert_pattern = re.compile(
        r'(?:assert|AssertionError|Exception|Error):\s*(.*?)$',
        re.MULTILINE,
    )
    for m in assert_pattern.finditer(output):
        if not any(f["message"] == m.group(1).strip() for f in failures):
            failures.append({
                "file": "",
                "line": 0,
                "message": m.group(1).strip()[:200],
                "type": "assertion",
            })

    return failures


def _read_file_lines(filepath: str) -> list[str]:
    """Read file lines, resolving relative paths."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath) as f:
            return f.readlines()
    except Exception:
        return []


def _generate_fix(filepath: str, error_lines: list[dict], failure_message: str) -> Optional[str]:
    """Call LLM to generate a fix for the given error."""
    lines = _read_file_lines(filepath)
    if not lines:
        return None

    max_context = min(len(lines), 100)
    error_line_nums = {e.get("line", 0) for e in error_lines if e.get("line")}
    context_start = max(0, min(error_line_nums) - 15) if error_line_nums else 0
    context_end = min(len(lines), max(error_line_nums) + 10) if error_line_nums else max_context

    context_lines = lines[context_start:context_end]
    context_text = "".join(
        f"{context_start + i + 1}:{l}" for i, l in enumerate(context_lines)
    )

    prompt = (
        f"The following test failed with error:\n{failure_message[:500]}\n\n"
        f"Source file ({filepath}), lines {context_start + 1}-{context_end}:\n"
        f"```\n{context_text}\n```\n\n"
        "Fix the bug. Return ONLY the exact replacement code for the problematic function or block. "
        "Do NOT include any explanation. Output must be valid Python."
    )

    try:
        from friday.tools.ai_tools import model_query
        result = model_query(
            prompt=prompt,
            system="You are a senior Python engineer. Output ONLY fixed code, no explanation.",
            model="opencode/big-pickle",
        )
        if isinstance(result, dict):
            return result.get("text", "") or result.get("response", "") or result.get("content", "")
        return str(result)
    except Exception:
        return None


def _apply_fix(filepath: str, fix_code: str, error_line: int = 0) -> str:
    """Apply a fix to the source file."""
    if not fix_code or not os.path.exists(filepath):
        return "[FAIL] No fix code or file not found"

    # Clean the fix code
    fix_code = fix_code.strip()
    if fix_code.startswith("```"):
        fix_code = fix_code.split("\n", 1)[1] if "\n" in fix_code else fix_code
        fix_code = fix_code.rsplit("```", 1)[0].strip()

    lines = _read_file_lines(filepath)
    if not lines:
        return "[FAIL] Could not read file"

    # Try to find the function/block to replace
    # Use indentation-based heuristic: find the block containing the error line
    if error_line and 0 < error_line <= len(lines):
        # Find function start (backtrack to def or class)
        func_start = error_line - 1
        while func_start > 0:
            line = lines[func_start - 1]
            if line.strip().startswith(("def ", "class ", "@")):
                break
            func_start -= 1

        # Find function end
        func_end = error_line
        base_indent = len(lines[func_start]) - len(lines[func_start].lstrip()) if func_start < len(lines) else 0
        while func_end < len(lines):
            stripped = lines[func_end].rstrip()
            if stripped and not stripped.startswith((" ", "\t")):
                if stripped.startswith(("def ", "class ", "@")):
                    break
                curr_indent = len(lines[func_end]) - len(lines[func_end].lstrip())
                if curr_indent <= base_indent and stripped:
                    break
            func_end += 1

        # Replace the block
        new_lines = lines[:func_start] + [fix_code + "\n"] + lines[func_end:]
    else:
        # No specific line, append to end (worst case)
        new_lines = lines + ["\n" + fix_code + "\n"]

    try:
        with open(filepath, "w") as f:
            f.writelines(new_lines)
        return f"[OK] Applied fix to {os.path.basename(filepath)}"
    except Exception as e:
        return f"[FAIL] Could not write fix: {e}"


def run_auto_fix(
    test_command: str = "python -m pytest",
    workdir: str = "",
    max_iterations: int = MAX_FIX_ITERATIONS,
    files_to_watch: Optional[list[str]] = None,
) -> str:
    """Run the auto-fix loop: test -> parse failures -> fix -> retest.
    
    Args:
        test_command: Shell command to run tests (e.g. 'python -m pytest tests/')
        workdir: Working directory for test command. Defaults to cwd.
        max_iterations: Max fix-attempt iterations (default 5).
        files_to_watch: List of file paths to focus fixes on. If empty, auto-detects.
    
    Returns:
        JSON string with iteration log and final status.
    """
    if not workdir:
        workdir = os.getcwd()

    log = []
    current_status = "unknown"

    for iteration in range(1, max_iterations + 1):
        iteration_log = {
            "iteration": iteration,
            "test_command": test_command,
            "timestamp": datetime.now().isoformat(),
        }

        # Step 1: Run tests
        result = _run_command(test_command, workdir)
        iteration_log["returncode"] = result["returncode"]
        iteration_log["output_preview"] = (result["stdout"] + result["stderr"])[:1000]

        if result["success"]:
            current_status = "passed"
            iteration_log["status"] = "passed"
            log.append(iteration_log)
            break

        # Step 2: Parse failures
        full_output = result["stdout"] + "\n" + result["stderr"]
        failures = _parse_test_failures(full_output)
        iteration_log["failures"] = failures

        if not failures:
            current_status = "failed_no_fix"
            iteration_log["status"] = "failed_no_parseable_failures"
            log.append(iteration_log)
            break

        # Step 3: Generate and apply fixes
        fixes_applied = 0
        seen_files = set()
        for failure in failures[:5]:
            filepath = failure.get("file", "")
            if not filepath:
                continue

            # Resolve relative to workdir
            if not os.path.isabs(filepath):
                resolved = os.path.join(workdir, filepath)
                if os.path.exists(resolved):
                    filepath = resolved

            if filepath in seen_files:
                continue
            seen_files.add(filepath)

            if files_to_watch and filepath not in files_to_watch:
                continue

            fix_code = _generate_fix(filepath, [failure], failure.get("message", ""))
            if fix_code:
                error_line = failure.get("line", 0)
                apply_result = _apply_fix(filepath, fix_code, error_line)
                if "[OK]" in apply_result:
                    fixes_applied += 1
                    iteration_log.setdefault("fixes", []).append({
                        "file": filepath,
                        "message": apply_result,
                    })

        iteration_log["fixes_applied"] = fixes_applied

        if fixes_applied == 0:
            current_status = "failed_no_fix"
            iteration_log["status"] = "no_fixes_applied"
            log.append(iteration_log)
            break

        iteration_log["status"] = f"applied_{fixes_applied}_fixes"
        log.append(iteration_log)

        # Small delay before re-running
        time.sleep(1)

    else:
        current_status = "max_iterations_reached"

    summary = {
        "status": current_status,
        "iterations": len(log),
        "test_command": test_command,
        "workdir": workdir,
        "log": log,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(summary, indent=2, default=str)


def _save_to_memory(result_json: str) -> str:
    os.makedirs(FRIDAY_MEMORY, exist_ok=True)
    path = os.path.join(FRIDAY_MEMORY, "auto_fix_history.jsonl")
    with open(path, "a") as f:
        f.write(result_json + "\n")
    return path


def coding_auto_fix_tool(
    action: str = "fix",
    test_command: str = "python -m pytest",
    workdir: str = "",
    max_iterations: int = MAX_FIX_ITERATIONS,
    files: str = "",
) -> str:
    """Coding Auto-Fix Loop — iteratively test, parse failures, fix code, retest.
    
    Actions:
      fix - Run the auto-fix loop on the given test command
      history - Show recent auto-fix history
    
    Args:
      test_command: Shell command to run tests
      workdir: Working directory (default: cwd)
      max_iterations: Max fix iterations (default: 5)
      files: Comma-separated list of file paths to restrict fixes to
    """
    if action == "fix":
        files_list = [f.strip() for f in files.split(",") if f.strip()] if files else None
        result = run_auto_fix(
            test_command=test_command,
            workdir=workdir,
            max_iterations=max_iterations,
            files_to_watch=files_list,
        )
        path = _save_to_memory(result)
        parsed = json.loads(result)
        status = parsed.get("status", "unknown")
        iterations = parsed.get("iterations", 0)
        return (
            f"### Auto-Fix Result\n"
            f"Status: {status}\n"
            f"Iterations: {iterations}\n"
            f"Test: {test_command}\n"
            f"[Saved to {path}]\n\n"
            f"{result}"
        )

    elif action == "history":
        path = os.path.join(FRIDAY_MEMORY, "auto_fix_history.jsonl")
        if not os.path.exists(path):
            return "No auto-fix history found."
        lines = []
        with open(path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    status = entry.get("status", "?")
                    its = entry.get("iterations", 0)
                    cmd = entry.get("test_command", "")
                    lines.append(f"  [{status}] {its} iters: {cmd[:80]}")
                except Exception:
                    continue
        return "### Auto-Fix History\n" + "\n".join(lines[-10:]) if lines else "No history."

    return f"[FAIL] Unknown action: {action}"
