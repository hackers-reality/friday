from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

# ──────────────────────────────────────────────
# Dataclass results
# ──────────────────────────────────────────────

@dataclass
class PrecommitResult:
    """Result from running pre-commit hooks."""
    path: str
    passed_hooks: list[str]
    failed_hooks: list[dict]
    error: Optional[str] = None


@dataclass
class GitAnalysisResult:
    """Result from PyDriller git repository analysis."""
    repo: str
    total_commits: int
    contributors: list[dict]
    avg_commits_per_day: float
    files_changed_most: list[dict]
    error: Optional[str] = None


@dataclass
class CodemodResult:
    """Result from a LibCST Python codemod transformation."""
    file: str
    success: bool
    changes: str
    error: Optional[str] = None


@dataclass
class AuditResult:
    """Result from ``pip-audit`` vulnerability scan."""
    path: str
    vulnerabilities: list[dict]
    safe: bool = True
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Lazy dependency flags
# ──────────────────────────────────────────────

HAS_PRECOMMIT = False
try:
    from pre_commit.main import main as precommit_main
    HAS_PRECOMMIT = True
except ImportError:
    pass

HAS_PYDRILLER = False
try:
    from pydriller import RepositoryMining
    HAS_PYDRILLER = True
except ImportError:
    pass

HAS_LIBCST = False
try:
    import libcst as cst
    import libcst.matchers as m
    HAS_LIBCST = True
except ImportError:
    pass

HAS_PIPAUDIT = False
try:
    from pip_audit._service import PyPIAuditService
    from pip_audit._virtual_env import VirtualEnv
    HAS_PIPAUDIT = True
except ImportError:
    pass


# ──────────────────────────────────────────────
# Pre-commit — run hooks against a repository
# ──────────────────────────────────────────────

async def run_precommit(path: str = ".", hook: str | None = None) -> PrecommitResult:
    """Run pre-commit hooks on a local repository.

    Args:
        path: Path to the git repository (default ``"."``).
        hook: Optional hook ID to run only a specific hook (e.g.
            ``"black"``, ``"ruff"``).  When ``None`` all hooks run.

    Returns:
        A ``PrecommitResult`` listing which hooks passed and which
        failed (with their error messages).
    """
    if not HAS_PRECOMMIT:
        return PrecommitResult(
            path=path, passed_hooks=[], failed_hooks=[],
            error="pre-commit package not installed (pip install pre-commit)",
        )

    import subprocess
    import sys

    async def _run() -> PrecommitResult:
        try:
            cmd = [sys.executable, "-m", "pre_commit", "run", "--all-files"]
            if hook:
                cmd.append(hook)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode() + stderr.decode()

            passed: list[str] = []
            failed: list[dict] = []
            for line in output.splitlines():
                line = line.strip()
                if "Passed" in line:
                    parts = line.split()
                    if parts:
                        passed.append(parts[0])
                elif "Failed" in line:
                    parts = line.split("-", 1)
                    name = parts[0].strip().split()[-1] if parts else "unknown"
                    msg = parts[1].strip() if len(parts) > 1 else ""
                    failed.append({"name": name, "message": msg})

            return PrecommitResult(path=path, passed_hooks=passed, failed_hooks=failed)
        except Exception as exc:
            return PrecommitResult(path=path, passed_hooks=[], failed_hooks=[], error=str(exc))

    return await _run()


# ──────────────────────────────────────────────
# PyDriller — mine git history / repository analysis
# ──────────────────────────────────────────────

async def analyze_git_repo(
    repo_path: str = ".",
    metrics: list[str] | None = None,
) -> GitAnalysisResult:
    """Analyse a local git repository with PyDriller.

    Mines the entire commit history to extract contributor statistics,
    commit frequency, and file-change hotspots.

    Args:
        repo_path: Path to the git repository (default ``"."``).
        metrics: Not currently used (reserved for future metric selection).

    Returns:
        A ``GitAnalysisResult`` with aggregated statistics.
    """
    if not HAS_PYDRILLER:
        return GitAnalysisResult(
            repo=repo_path, total_commits=0, contributors=[],
            avg_commits_per_day=0.0, files_changed_most=[],
            error="pydriller package not installed (pip install pydriller)",
        )

    def _blocking() -> GitAnalysisResult:
        try:
            contrib_map: dict[str, dict] = {}
            file_changes: dict[str, int] = {}
            dates: list[datetime] = []

            for commit in RepositoryMining(repo_path).traverse_commits():
                dates.append(commit.committer_date)
                author = commit.author.name or commit.author.email or "unknown"
                if author not in contrib_map:
                    contrib_map[author] = {"name": author, "commits": 0, "additions": 0, "deletions": 0}
                contrib_map[author]["commits"] += 1
                contrib_map[author]["additions"] += commit.insertions
                contrib_map[author]["deletions"] += commit.deletions

                for mod in commit.modifications:
                    fp = mod.new_path or mod.old_path or "unknown"
                    file_changes[fp] = file_changes.get(fp, 0) + 1

            total = len(dates)
            days = ((max(dates) - min(dates)).total_seconds() / 86400) if dates else 1
            avg_commits = round(total / max(days, 1), 2)

            sorted_contribs = sorted(contrib_map.values(), key=lambda c: c["commits"], reverse=True)
            sorted_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:20]

            return GitAnalysisResult(
                repo=os.path.abspath(repo_path),
                total_commits=total,
                contributors=sorted_contribs,
                avg_commits_per_day=avg_commits,
                files_changed_most=[
                    {"file": f, "change_count": c} for f, c in sorted_files
                ],
            )
        except Exception as exc:
            return GitAnalysisResult(
                repo=repo_path, total_commits=0, contributors=[],
                avg_commits_per_day=0.0, files_changed_most=[],
                error=str(exc),
            )

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# LibCST — codemod Python source files
# ──────────────────────────────────────────────

async def codemod_python(file_path: str, transformation: str) -> CodemodResult:
    """Apply a Python source transformation using LibCST.

    Supported ``transformation`` values:

    - ``"rename_function:old_name->new_name"``
    - ``"add_decorator:decorator_name"``
    - ``"add_return_annotation:->Type"``

    Args:
        file_path: Path to the Python file to modify.
        transformation: Transformation specifier (see description).

    Returns:
        A ``CodemodResult`` with the resulting diff.
    """
    if not HAS_LIBCST:
        return CodemodResult(
            file=file_path, success=False, changes="",
            error="libcst package not installed (pip install libcst)",
        )

    def _blocking() -> CodemodResult:
        try:
            with open(file_path, encoding="utf-8") as fh:
                source = fh.read()

            original_tree = cst.parse_module(source)

            if transformation.startswith("rename_function:"):
                rest = transformation[len("rename_function:"):]
                old_name, new_name = rest.split("->", 1)

                class RenameTransformer(cst.CSTTransformer):
                    def leave_FunctionDef(self, node, updated_node):
                        if node.name.value == old_name:
                            return updated_node.with_changes(
                                name=updated_node.name.with_changes(value=new_name)
                            )
                        return updated_node

                new_tree = original_tree.visit(RenameTransformer())

            elif transformation.startswith("add_decorator:"):
                decorator_name = transformation[len("add_decorator:"):]

                class DecoratorTransformer(cst.CSTTransformer):
                    def leave_FunctionDef(self, node, updated_node):
                        new_decorator = cst.Decorator(
                            decorator=cst.parse_expression(decorator_name)
                        )
                        return updated_node.with_changes(
                            decorators=(new_decorator,) + updated_node.decorators
                        )

                new_tree = original_tree.visit(DecoratorTransformer())

            elif transformation.startswith("add_return_annotation:"):
                annotation_raw = transformation[len("add_return_annotation:"):]

                class AnnotationTransformer(cst.CSTTransformer):
                    def leave_FunctionDef(self, node, updated_node):
                        if updated_node.returns is None:
                            ann = cst.Annotation(
                                annotation=cst.parse_expression(annotation_raw)
                            )
                            return updated_node.with_changes(returns=ann)
                        return updated_node

                new_tree = original_tree.visit(AnnotationTransformer())

            else:
                return CodemodResult(
                    file=file_path, success=False, changes="",
                    error=f"Unknown transformation: '{transformation}'",
                )

            new_source = new_tree.code
            if new_source == source:
                return CodemodResult(
                    file=file_path, success=True, changes="(no changes applied)",
                )

            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(new_source)

            import difflib
            diff = "".join(difflib.unified_diff(
                source.splitlines(keepends=True),
                new_source.splitlines(keepends=True),
                fromfile=file_path, tofile=file_path,
            ))
            return CodemodResult(file=file_path, success=True, changes=diff)

        except Exception as exc:
            return CodemodResult(file=file_path, success=False, changes="", error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# Pip-audit — scan dependencies for CVEs
# ──────────────────────────────────────────────

async def audit_dependencies(path: str = ".") -> AuditResult:
    """Scan Python dependencies for known vulnerabilities using pip-audit.

    Analyses the active virtual environment (or a ``requirements.txt`` /
    ``pyproject.toml`` at ``path``) against the PyPI JSON advisory feed.

    Args:
        path: Path to the project directory (default ``"."``).

    Returns:
        An ``AuditResult`` listing vulnerable packages with CVE
        identifiers and severity scores.
    """
    if not HAS_PIPAUDIT:
        return AuditResult(
            path=path, vulnerabilities=[],
            error="pip-audit package not installed (pip install pip-audit)",
        )

    import subprocess
    import sys
    import json

    async def _run() -> AuditResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip_audit",
                "--format", "json",
                cwd=path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0 and not stdout:
                return AuditResult(
                    path=path, vulnerabilities=[],
                    error=stderr.decode().strip(),
                )

            data = json.loads(stdout.decode())
            vulns: list[dict] = []
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    vulns.append({
                        "package": dep.get("name", ""),
                        "version": dep.get("version", ""),
                        "cve": vuln.get("id", ""),
                        "severity": vuln.get("severity", ""),
                    })

            return AuditResult(
                path=os.path.abspath(path),
                vulnerabilities=vulns,
                safe=len(vulns) == 0,
            )
        except Exception as exc:
            return AuditResult(path=path, vulnerabilities=[], error=str(exc))

    return await _run()
