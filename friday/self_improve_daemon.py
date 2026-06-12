"""
Continuous Self-Improvement Daemon — Fable 5-equivalent autonomous improvement loop.
Runs in background, periodically:
  1. Scans code for improvement opportunities (lint, type check, complexity)
  2. Generates LLM proposals for each issue
  3. Tests changes before applying
  4. Applies, commits, pushes
  5. Rolls back on failure
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY

_DAEMON_DIR = os.path.join(FRIDAY_MEMORY, "self_improve")
_PROPOSALS_FILE = os.path.join(_DAEMON_DIR, "proposals.json")
_HISTORY_FILE = os.path.join(_DAEMON_DIR, "history.jsonl")
_SCAN_RESULTS_FILE = os.path.join(_DAEMON_DIR, "last_scan.json")

_daemon_thread: Optional[threading.Thread] = None
_daemon_stop = threading.Event()

DEFAULT_INTERVAL = 3600
MAX_PROPOSALS_PER_CYCLE = 3


def _ensure_dirs():
    os.makedirs(_DAEMON_DIR, exist_ok=True)


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _log_history(entry: dict):
    _ensure_dirs()
    with open(_HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Scanning ──

def _find_python_files(root: str, max_files: int = 50) -> list[str]:
    py_files = []
    for dirpath, _, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel.startswith((".", "__pycache__", "node_modules", ".git", "venv", "env")):
            continue
        for f in filenames:
            if f.endswith(".py") and not f.startswith("__"):
                py_files.append(os.path.join(dirpath, f))
                if len(py_files) >= max_files:
                    return py_files
    return py_files


def _run_lint(filepath: str) -> list[dict]:
    issues = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--output-format", "json", filepath],
            capture_output=True, text=True, timeout=30,
        )
        if result.stdout:
            for issue in json.loads(result.stdout):
                issues.append({
                    "file": filepath,
                    "line": issue.get("location", {}).get("row", 0),
                    "code": issue.get("code", ""),
                    "message": issue.get("message", ""),
                    "severity": "warning",
                    "source": "ruff",
                })
    except Exception:
        pass
    return issues


def _run_mypy(filepath: str) -> list[dict]:
    issues = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--show-column-numbers", "--no-error-summary", filepath],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.split("\n"):
            m = re.match(r"(.+?):(\d+):(\d+):\s*(error|warning|note):\s*(.+)", line)
            if m:
                issues.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "code": "mypy",
                    "message": m.group(5).strip(),
                    "severity": m.group(4),
                    "source": "mypy",
                })
    except Exception:
        pass
    return issues


def _compute_complexity(filepath: str) -> dict:
    complexity = {"cyclomatic": 0, "lines": 0, "functions": 0, "classes": 0}
    try:
        with open(filepath) as f:
            content = f.read()
        lines = content.split("\n")
        complexity["lines"] = len(lines)
        complexity["functions"] = len(re.findall(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE))
        complexity["classes"] = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))

        # Rough cyclomatic complexity: count if/elif/for/while/except/and/or
        branches = len(re.findall(r"\b(if|elif|for|while|except|and|or)\b", content))
        complexity["cyclomatic"] = branches + 1
    except Exception:
        pass
    return complexity


def scan_for_improvements(root: str = "") -> list[dict]:
    if not root:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    py_files = _find_python_files(root)
    all_issues = []

    for fpath in py_files:
        lint_issues = _run_lint(fpath)
        type_issues = _run_mypy(fpath)
        complexity = _compute_complexity(fpath)

        all_issues.extend(lint_issues)
        all_issues.extend(type_issues)

        if complexity["cyclomatic"] > 20:
            all_issues.append({
                "file": fpath,
                "line": 0,
                "code": "C901",
                "message": f"Cyclomatic complexity {complexity['cyclomatic']} > 20, consider refactoring",
                "severity": "warning",
                "source": "complexity",
                "complexity": complexity["cyclomatic"],
            })

    _save_json(_SCAN_RESULTS_FILE, {
        "scanned_at": datetime.now().isoformat(),
        "files_scanned": len(py_files),
        "issues_found": len(all_issues),
        "issues": all_issues[:100],
    })

    return all_issues


# ── Proposal Generation ──

def _generate_proposal(issue: dict) -> Optional[dict]:
    filepath = issue.get("file", "")
    if not filepath or not os.path.exists(filepath):
        return None

    with open(filepath) as f:
        content = f.read()

    lines = content.split("\n")
    error_line = issue.get("line", 0)
    context_start = max(0, error_line - 10)
    context_end = min(len(lines), error_line + 10)
    context = "\n".join(
        f"{context_start + i + 1}:{lines[context_start + i]}"
        for i in range(context_end - context_start)
    )

    prompt = (
        f"Analyze this code issue and propose a fix.\n\n"
        f"File: {filepath}\n"
        f"Issue: [{issue.get('code', '?')}] {issue.get('message', '')}\n\n"
        f"Context (line {error_line}):\n```\n{context}\n```\n\n"
        "Return a JSON object with:\n"
        '  "description": "brief description of the fix (max 100 chars)"\n'
        '  "file": "path to the file to change"\n'
        '  "old_string": "exact string to replace (from the context above)"\n'
        '  "new_string": "replacement string"\n\n'
        "If the issue is not fixable or not worth fixing, return {\"skip\": true}.\n"
        "Return ONLY valid JSON. No markdown."
    )

    try:
        from friday.tools.ai_tools import model_query
        result = model_query(
            prompt=prompt,
            system="You are a senior Python engineer finding and fixing code issues. Output only JSON.",
            model="opencode/big-pickle",
        )
        text = ""
        if isinstance(result, dict):
            text = result.get("text", "") or result.get("response", "") or result.get("content", "")
        else:
            text = str(result)

        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()

        parsed = json.loads(text)
        if parsed.get("skip"):
            return None
        return parsed
    except Exception:
        return None


# ── Testing ──

def _run_tests() -> dict:
    result = {"success": False, "output": "", "returncode": -1}
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=short", "-q"],
            cwd=project_root, capture_output=True, text=True, timeout=120,
        )
        result = {
            "success": proc.returncode == 0,
            "output": (proc.stdout + proc.stderr)[:2000],
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        result["output"] = "Tests timed out after 120s"
    except Exception as e:
        result["output"] = str(e)
    return result


def _git_snapshot() -> str:
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run(["git", "stash"], cwd=project_root, capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "stash", "create"],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
        stash_id = result.stdout.strip()
        return stash_id
    except Exception:
        return ""


def _git_restore(stash_id: str = "") -> bool:
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if stash_id:
            subprocess.run(["git", "stash", "apply", stash_id], cwd=project_root, capture_output=True, timeout=10)
            return True
        subprocess.run(["git", "checkout", "--", "."], cwd=project_root, capture_output=True, timeout=10)
        return True
    except Exception:
        return False


# ── Apply + Commit ──

def _apply_proposal(proposal: dict) -> str:
    filepath = proposal.get("file", "")
    old_string = proposal.get("old_string", "")
    new_string = proposal.get("new_string", "")

    if not filepath or not os.path.exists(filepath):
        return "[FAIL] File not found"
    if not old_string:
        return "[FAIL] No old_string to replace"

    with open(filepath) as f:
        content = f.read()

    if old_string not in content:
        return "[FAIL] old_string not found in file"

    new_content = content.replace(old_string, new_string, 1)
    with open(filepath, "w") as f:
        f.write(new_content)

    return f"[OK] Applied fix to {os.path.basename(filepath)}"


def _commit_and_push(description: str, filepath: str) -> str:
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run(["git", "add", filepath], cwd=project_root, capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", f"[Self-Improve] {description[:200]}"],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            subprocess.run(["git", "push"], cwd=project_root, capture_output=True, timeout=30)
            return f"[OK] Committed and pushed"
        return f"[INFO] {result.stdout.strip()}"
    except Exception as e:
        return f"[FAIL] Git error: {e}"


# ── Main Cycle ──

def run_improvement_cycle(root: str = "") -> str:
    _ensure_dirs()
    cycle_id = uuid.uuid4().hex[:8]
    start = time.time()
    log = {
        "cycle_id": cycle_id,
        "started_at": datetime.now().isoformat(),
        "status": "running",
    }

    # Step 1: Run tests before anything
    pre_test = _run_tests()
    if not pre_test["success"]:
        log["status"] = "skipped_tests_failing"
        log["pre_test_output"] = pre_test["output"][:500]
        _log_history(log)
        return (
            f"### Self-Improvement Cycle {cycle_id}\n"
            f"Status: SKIPPED — tests are already failing\n"
            f"Tests output: {pre_test['output'][:300]}"
        )

    # Step 2: Scan for issues
    issues = scan_for_improvements(root)
    log["issues_found"] = len(issues)

    if not issues:
        log["status"] = "no_issues_found"
        _log_history(log)
        return f"### Self-Improvement Cycle {cycle_id}\nStatus: No issues found in {len(os.listdir(os.path.dirname(root)) if root else os.listdir('.'))} files."

    # Step 3: Generate proposals
    proposals = []
    for issue in issues[:MAX_PROPOSALS_PER_CYCLE]:
        proposal = _generate_proposal(issue)
        if proposal:
            proposals.append(proposal)

    log["proposals_generated"] = len(proposals)

    if not proposals:
        log["status"] = "no_proposals"
        _log_history(log)
        return f"### Self-Improvement Cycle {cycle_id}\nStatus: {len(issues)} issues found, but none generated actionable proposals."

    # Step 4: Snapshot git state
    stash_id = _git_snapshot()

    # Step 5: Apply proposals
    results = []
    for proposal in proposals:
        result = _apply_proposal(proposal)
        results.append({"proposal": proposal, "result": result})
        log.setdefault("applied", []).append({
            "file": proposal.get("file", ""),
            "description": proposal.get("description", ""),
            "result": result,
        })

    # Step 6: Run tests after changes
    post_test = _run_tests()
    log["post_test_success"] = post_test["success"]

    if post_test["success"]:
        # All good — commit and push
        commit_results = []
        for proposal in proposals:
            filepath = proposal.get("file", "")
            desc = proposal.get("description", "")
            cr = _commit_and_push(desc, filepath)
            commit_results.append(cr)

        log["status"] = "success"
        log["completed_at"] = datetime.now().isoformat()
        log["elapsed_seconds"] = round(time.time() - start)
        _log_history(log)

        summary = "\n".join(
            f"  ✓ {r['proposal'].get('description', 'Fix')[:80]}" for r in results
        )
        return (
            f"### Self-Improvement Cycle {cycle_id}\n"
            f"Status: SUCCESS\n"
            f"Issues found: {len(issues)}, Proposals: {len(proposals)}, Tests: PASS\n"
            f"Changes:\n{summary}"
        )

    # Step 7: Tests failed — rollback
    _git_restore(stash_id)
    log["status"] = "rolled_back"
    log["post_test_output"] = post_test["output"][:500]
    log["completed_at"] = datetime.now().isoformat()
    log["elapsed_seconds"] = round(time.time() - start)
    _log_history(log)

    return (
        f"### Self-Improvement Cycle {cycle_id}\n"
        f"Status: ROLLED BACK — tests failed after changes\n"
        f"Issues found: {len(issues)}, Proposals: {len(proposals)}\n"
        f"Tests output: {post_test['output'][:300]}"
    )


# ── Daemon Loop ──

def _daemon_loop(interval: int = DEFAULT_INTERVAL):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while not _daemon_stop.is_set():
        try:
            result = run_improvement_cycle(root=root)
            _log_history({
                "type": "daemon_cycle",
                "timestamp": datetime.now().isoformat(),
                "result_preview": result[:200],
            })
        except Exception as e:
            _log_history({
                "type": "daemon_error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            })
        _daemon_stop.wait(interval)


def daemon_start(interval: int = DEFAULT_INTERVAL) -> str:
    global _daemon_thread, _daemon_stop
    if _daemon_thread and _daemon_thread.is_alive():
        return "[OK] Self-improvement daemon already running."
    _daemon_stop.clear()
    _daemon_thread = threading.Thread(
        target=_daemon_loop, args=(interval,), daemon=True
    )
    _daemon_thread.start()
    return f"[OK] Self-improvement daemon started (interval: {interval}s)"


def daemon_stop() -> str:
    _daemon_stop.set()
    if _daemon_thread:
        _daemon_thread.join(timeout=5)
    return "[OK] Self-improvement daemon stopped."


def daemon_status() -> str:
    return json.dumps({
        "running": _daemon_thread is not None and _daemon_thread.is_alive(),
        "interval": DEFAULT_INTERVAL,
        "proposals_file": _PROPOSALS_FILE,
        "history_file": _HISTORY_FILE,
    }, indent=2)


def get_history(limit: int = 20) -> str:
    if not os.path.exists(_HISTORY_FILE):
        return "No self-improvement history yet."
    entries = []
    with open(_HISTORY_FILE) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if not entries:
        return "No history."

    lines = [f"### Self-Improvement History ({len(entries)} entries)"]
    for e in entries[-limit:]:
        ts = e.get("timestamp", e.get("started_at", e.get("cycle_id", "?")))[:19]
        status = e.get("status", "?")
        issues = e.get("issues_found", 0)
        proposals = e.get("proposals_generated", 0)
        lines.append(f"  [{ts}] {status} ({issues} issues, {proposals} proposals)")
    return "\n".join(lines)


# ── Tool ──

def self_improve_daemon_tool(action: str = "status", **kwargs) -> str:
    """Continuous self-improvement daemon.
    
    Actions:
      status - Show daemon status
      start [interval] - Start the daemon (interval in seconds, default 3600)
      stop - Stop the daemon
      cycle [root] - Run a single improvement cycle now
      scan [root] - Scan for issues without applying
      history [limit] - Show recent improvement history
    """
    if action == "status":
        return daemon_status()

    elif action == "start":
        interval = int(kwargs.get("interval", DEFAULT_INTERVAL))
        return daemon_start(interval)

    elif action == "stop":
        return daemon_stop()

    elif action == "cycle":
        root = kwargs.get("root", "")
        return run_improvement_cycle(root=root)

    elif action == "scan":
        root = kwargs.get("root", "")
        issues = scan_for_improvements(root=root)
        if not issues:
            return "No issues found. Code looks clean!"
        lines = [f"### Scan Results ({len(issues)} issues)"]
        for issue in issues[:20]:
            fname = os.path.basename(issue.get("file", "?"))
            line = issue.get("line", 0)
            code = issue.get("code", "?")
            msg = issue.get("message", "")[:80]
            lines.append(f"  - {fname}:{line} [{code}] {msg}")
        return "\n".join(lines)

    elif action == "history":
        limit = int(kwargs.get("limit", 20))
        return get_history(limit)

    return f"[FAIL] Unknown action: {action}"
