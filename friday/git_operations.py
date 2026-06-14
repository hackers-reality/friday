"""FRIDAY Git Operations — git commands wrapper with status, diff, commit, branch management."""
import os
import subprocess
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class GitResult:
    success: bool
    command: str
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0

    def to_dict(self):
        return asdict(self)


class GitOps:
    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)

    def _run(self, *args: str) -> GitResult:
        start = time.time()
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return GitResult(
                success=result.returncode == 0,
                command=f"git {' '.join(args)}",
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                exit_code=result.returncode,
                duration=time.time() - start,
            )
        except subprocess.TimeoutExpired:
            return GitResult(success=False, command=f"git {' '.join(args)}",
                           error="Command timed out", duration=time.time() - start)
        except Exception as e:
            return GitResult(success=False, command=f"git {' '.join(args)}",
                           error=str(e), duration=time.time() - start)

    def is_repo(self) -> bool:
        result = self._run("rev-parse", "--is-inside-work-tree")
        return result.success and result.output == "true"

    def status(self) -> Dict:
        result = self._run("status", "--porcelain")
        if not result.success:
            return {"error": result.error}
        files = []
        for line in result.output.split("\n"):
            if line.strip():
                status_code = line[:2].strip()
                filename = line[3:].strip()
                files.append({"status": status_code, "file": filename})
        branch = self._run("branch", "--show-current")
        return {
            "branch": branch.output if branch.success else "unknown",
            "files": files,
            "clean": len(files) == 0,
        }

    def log(self, count: int = 10) -> List[Dict]:
        result = self._run("log", f"--max-count={count}", "--format=%H|%an|%ae|%ai|%s")
        if not result.success:
            return []
        commits = []
        for line in result.output.split("\n"):
            if "|" in line:
                parts = line.split("|", 4)
                if len(parts) == 5:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    })
        return commits

    def diff(self, staged: bool = False) -> str:
        if staged:
            result = self._run("diff", "--cached")
        else:
            result = self._run("diff")
        return result.output if result.success else result.error

    def diff_stat(self) -> Dict:
        result = self._run("diff", "--stat")
        if not result.success:
            return {"error": result.error}
        return {"stat": result.output}

    def add(self, files: List[str] = None) -> GitResult:
        if files:
            return self._run("add", *files)
        return self._run("add", ".")

    def commit(self, message: str) -> GitResult:
        return self._run("commit", "-m", message)

    def push(self, remote: str = "origin", branch: str = None) -> GitResult:
        if branch:
            return self._run("push", remote, branch)
        return self._run("push", remote)

    def pull(self, remote: str = "origin", branch: str = None) -> GitResult:
        if branch:
            return self._run("pull", remote, branch)
        return self._run("pull", remote)

    def branch_list(self) -> List[str]:
        result = self._run("branch", "--list")
        if not result.success:
            return []
        return [line.strip().replace("* ", "") for line in result.output.split("\n") if line.strip()]

    def branch_create(self, name: str) -> GitResult:
        return self._run("branch", name)

    def branch_delete(self, name: str) -> GitResult:
        return self._run("branch", "-d", name)

    def checkout(self, branch: str) -> GitResult:
        return self._run("checkout", branch)

    def merge(self, branch: str) -> GitResult:
        return self._run("merge", branch)

    def stash(self) -> GitResult:
        return self._run("stash")

    def stash_pop(self) -> GitResult:
        return self._run("stash", "pop")

    def remote_list(self) -> List[Dict]:
        result = self._run("remote", "-v")
        if not result.success:
            return []
        remotes = []
        for line in result.output.split("\n"):
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) == 2:
                    name, url_type = parts
                    url, op = url_type.rsplit(" ", 1)
                    remotes.append({"name": name, "url": url, "operation": op})
        return remotes

    def tags(self) -> List[str]:
        result = self._run("tag", "--list")
        if not result.success:
            return []
        return [t.strip() for t in result.output.split("\n") if t.strip()]

    def blame(self, file_path: str) -> str:
        result = self._run("blame", file_path)
        return result.output if result.success else result.error

    def show(self, commit_hash: str) -> str:
        result = self._run("show", commit_hash)
        return result.output if result.success else result.error

    def search(self, pattern: str) -> List[Dict]:
        result = self._run("log", f"--grep={pattern}", "--format=%H|%s")
        if not result.success:
            return []
        matches = []
        for line in result.output.split("\n"):
            if "|" in line:
                hash_val, message = line.split("|", 1)
                matches.append({"hash": hash_val.strip(), "message": message.strip()})
        return matches

    def get_stats(self) -> Dict:
        status = self.status()
        log_entries = self.log(1)
        branches = self.branch_list()
        return {
            "is_repo": self.is_repo(),
            "branch": status.get("branch", "unknown"),
            "dirty_files": len(status.get("files", [])),
            "branches": len(branches),
            "latest_commit": log_entries[0] if log_entries else None,
        }


_git_ops = None


def _get_git(path: str = ".") -> GitOps:
    global _git_ops
    if _git_ops is None or _git_ops.repo_path != os.path.abspath(path):
        _git_ops = GitOps(path)
    return _git_ops


def git_operations_tool(action: str = "status", **kwargs) -> Any:
    """Git operations tool dispatcher."""
    try:
        path = kwargs.get("path", ".")
        git = _get_git(path)

        if action == "status":
            return git.status()

        elif action == "log":
            count = kwargs.get("count", 10)
            return {"commits": git.log(count)}

        elif action == "diff":
            staged = kwargs.get("staged", False)
            return {"diff": git.diff(staged)}

        elif action == "diff_stat":
            return git.diff_stat()

        elif action == "add":
            files = kwargs.get("files")
            if files and not isinstance(files, list):
                files = [files]
            result = git.add(files)
            return result.to_dict()

        elif action == "commit":
            message = kwargs.get("message", "")
            if not message:
                return {"error": "No commit message provided"}
            result = git.commit(message)
            return result.to_dict()

        elif action == "push":
            remote = kwargs.get("remote", "origin")
            branch = kwargs.get("branch")
            result = git.push(remote, branch)
            return result.to_dict()

        elif action == "pull":
            remote = kwargs.get("remote", "origin")
            branch = kwargs.get("branch")
            result = git.pull(remote, branch)
            return result.to_dict()

        elif action == "branches":
            return {"branches": git.branch_list(), "current": git.status().get("branch")}

        elif action == "branch_create":
            name = kwargs.get("name", "")
            if not name:
                return {"error": "No branch name provided"}
            result = git.branch_create(name)
            return result.to_dict()

        elif action == "branch_delete":
            name = kwargs.get("name", "")
            if not name:
                return {"error": "No branch name provided"}
            result = git.branch_delete(name)
            return result.to_dict()

        elif action == "checkout":
            branch = kwargs.get("branch", "")
            if not branch:
                return {"error": "No branch name provided"}
            result = git.checkout(branch)
            return result.to_dict()

        elif action == "merge":
            branch = kwargs.get("branch", "")
            if not branch:
                return {"error": "No branch name provided"}
            result = git.merge(branch)
            return result.to_dict()

        elif action == "stash":
            result = git.stash()
            return result.to_dict()

        elif action == "stash_pop":
            result = git.stash_pop()
            return result.to_dict()

        elif action == "remotes":
            return {"remotes": git.remote_list()}

        elif action == "tags":
            return {"tags": git.tags()}

        elif action == "blame":
            file_path = kwargs.get("file", "")
            if not file_path:
                return {"error": "No file path provided"}
            return {"blame": git.blame(file_path)}

        elif action == "show":
            commit_hash = kwargs.get("hash", "")
            if not commit_hash:
                return {"error": "No commit hash provided"}
            return {"show": git.show(commit_hash)}

        elif action == "search":
            pattern = kwargs.get("pattern", "")
            if not pattern:
                return {"error": "No search pattern provided"}
            return {"matches": git.search(pattern)}

        elif action == "stats":
            return git.get_stats()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
