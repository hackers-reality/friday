"""
Friday Auto-Update System - Self-updating capabilities.
Checks for updates, pulls from git, and safely applies updates.
"""
from __future__ import annotations

import os
import sys
import subprocess
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


# ─── Update Configuration ───────────────────────────────────#

UPDATE_CONFIG = {
    "repo_url": "https://github.com/hackers-reality/friday.git",
    "branch": "main",
    "check_interval_hours": 6,
    "auto_apply": False,  # Manual approval required by default
    "backup_before_update": True,
    "rollback_on_failure": True,
}


# ─── Update Checker ───────────────────────────────────#

class UpdateChecker:
    """Checks for available updates from git repository."""
    
    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path or os.path.dirname(__file__))
        self.config = UPDATE_CONFIG.copy()
    
    def check_for_updates(self) -> Dict[str, Any]:
        """
        Check if updates are available.
        Returns {available: bool, current: str, latest: str, commits: List}
        """
        try:
            # Fetch latest from remote
            result = self._run_git(["fetch", "origin"])
            if not result["success"]:
                return {"error": result["error"]}
            
            # Get current commit
            current = self._run_git(["rev-parse", "HEAD"])
            current_hash = current["output"].strip() if current["success"] else "unknown"
            
            # Get latest remote commit
            latest = self._run_git(["rev-parse", "origin/main"])
            latest_hash = latest["output"].strip() if latest["success"] else "unknown"
            
            # Check if different
            available = current_hash != latest_hash and latest_hash != "unknown"
            
            # Get commit difference
            commits = []
            if available:
                log_result = self._run_git([
                    "log", "--oneline", "--max-count=10",
                    f"{current_hash}..{latest_hash}"
                ])
                if log_result["success"]:
                    commits = [
                        line.strip() 
                        for line in log_result["output"].split("\n") 
                        if line.strip()
                    ]
            
            return {
                "available": available,
                "current": current_hash[:7],
                "latest": latest_hash[:7],
                "commits": commits,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_changelog(self, from_commit: str = None, to_commit: str = "origin/main") -> List[str]:
        """Get changelog between commits."""
        try:
            cmd = ["log", "--pretty=format:%h - %s (%an, %ar)"]
            if from_commit:
                cmd.append(f"{from_commit}..{to_commit}")
            else:
                cmd.append(to_commit)
            cmd.append("--max-count=20")
            
            result = self._run_git(cmd)
            if result["success"]:
                return [line for line in result["output"].split("\n") if line.strip()]
            return []
        except Exception:
            return []
    
    def _run_git(self, args: List[str]) -> Dict[str, Any]:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Update Applier ───────────────────────────────────#

class UpdateApplier:
    """Applies updates from git."""
    
    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path or os.path.dirname(__file__))
        self.backup_dir = self.repo_path / "friday_memory" / "update_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def apply_update(self, create_backup: bool = True) -> Dict[str, Any]:
        """
        Pull and apply updates from remote.
        Returns {success: bool, message: str, backup: str}
        """
        backup_path = None
        
        try:
            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup()
            
            # Pull updates
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Pull failed: {result.stderr}",
                    "backup": backup_path,
                }
            
            # Verify Python files compile
            verify = self._verify_update()
            if not verify["success"]:
                # Rollback
                if backup_path:
                    self._restore_backup(backup_path)
                return {
                    "success": False,
                    "message": f"Verification failed: {verify['error']}",
                    "backup": backup_path,
                    "rolled_back": True,
                }
            
            return {
                "success": True,
                "message": result.stdout,
                "backup": backup_path,
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "backup": backup_path,
            }
    
    def _create_backup(self) -> str:
        """Create backup of current state."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Backup key files
        key_files = ["*.py", "*.md", "requirements.txt", ".env*"]
        for pattern in key_files:
            for f in self.repo_path.glob(pattern):
                if f.is_file():
                    rel_path = f.relative_to(self.repo_path)
                    dest = backup_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(f.read_bytes())
        
        # Save git commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            (backup_path / "commit.txt").write_text(result.stdout)
        
        return str(backup_path)
    
    def _restore_backup(self, backup_path: str):
        """Restore from backup."""
        backup = Path(backup_path)
        if not backup.exists():
            return
        
        for f in backup.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(backup)
                dest = self.repo_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        
        # Reset git to backup commit
        commit_file = backup / "commit.txt"
        if commit_file.exists():
            commit = commit_file.read_text().strip()
            subprocess.run(
                ["git", "reset", "--hard", commit],
                cwd=str(self.repo_path)
            )
    
    def _verify_update(self) -> Dict[str, Any]:
        """Verify updated files compile."""
        try:
            python_files = list(self.repo_path.glob("*.py"))
            for py_file in python_files:
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), py_file.name, 'exec')
            return {"success": True}
        except SyntaxError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Update Scheduler ───────────────────────────────────#

class UpdateScheduler:
    """Schedules periodic update checks."""
    
    def __init__(self):
        self.checker = UpdateChecker()
        self.applier = UpdateApplier()
        self.last_check_file = Path("friday_memory/last_update_check.json")
        self._running = False
        self._thread = None
    
    def start(self):
        """Start the update scheduler."""
        if self._running:
            return
        self._running = True
        # This would run in a thread in production
        print("[UpdateScheduler] Started.")
    
    def stop(self):
        """Stop the update scheduler."""
        self._running = False
        print("[UpdateScheduler] Stopped.")
    
    def should_check(self) -> bool:
        """Check if it's time to check for updates."""
        if not self.last_check_file.exists():
            return True
        
        try:
            data = json.loads(self.last_check_file.read_text())
            last_check = datetime.fromisoformat(data["timestamp"])
            hours_since = (datetime.now() - last_check).total_seconds() / 3600
            return hours_since >= UPDATE_CONFIG["check_interval_hours"]
        except:
            return True
    
    def run_check(self) -> Dict[str, Any]:
        """Run update check and save timestamp."""
        result = self.checker.check_for_updates()
        
        # Save timestamp
        self.last_check_file.parent.mkdir(parents=True, exist_ok=True)
        self.last_check_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }))
        
        return result


# ─── Singleton Instances ───────────────────────────────────#

_checker: Optional[UpdateChecker] = None
_applier: Optional[UpdateApplier] = None
_scheduler: Optional[UpdateScheduler] = None

def get_update_checker() -> UpdateChecker:
    global _checker
    if _checker is None:
        _checker = UpdateChecker()
    return _checker

def get_update_applier() -> UpdateApplier:
    global _applier
    if _applier is None:
        _applier = UpdateApplier()
    return _applier

def get_update_scheduler() -> UpdateScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = UpdateScheduler()
    return _scheduler


# ─── Tool Function for Friday ───────────────────────────────────#

def update_tool(
    action: str = "check",
    auto_apply: bool = False,
) -> str:
    """
    Friday tool for auto-update operations.
    Actions: check, changelog, apply, status, scheduler_start, scheduler_stop
    """
    if action == "check":
        checker = get_update_checker()
        result = checker.check_for_updates()
        
        if "error" in result:
            return f"[FAIL] Update check failed: {result['error']}"
        
        if not result["available"]:
            return f"[OK] Friday is up to date (commit {result['current']})"
        
        lines = [
            f"### UPDATE AV以上就是AILABLE",
            "",
            f"**Current**: {result['current']}",
            f"**Latest**: {result['latest']}",
            f"**New Commits**: {len(result['commits'])}",
            "",
            "**Recent Commits**:",
        ]
        for commit in result["commits"][:10]:
            lines.append(f"  - {commit}")
        
        return "\n".join(lines)
    
    if action == "changelog":
        checker = get_update_checker()
        commits = checker.get_changelog()
        if not commits:
            return "No changelog available."
        lines = ["### CHANGELOG", ""]
        for commit in commits:
            lines.append(f"- {commit}")
        return "\n".join(lines)
    
    if action == "apply":
        applier = get_update_applier()
        result = applier.apply_update(create_backup=True)
        
        if result["success"]:
            return f"[OK] Update applied successfully!\n{result['message'][:500]}"
        else:
            msg = f"[FAIL] Update failed: {result['message'][:300]}"
            if result.get("rolled_back"):
                msg += "\n🔄 System rolled back to previous version."
            return msg
    
    if action == "status":
        scheduler = get_update_scheduler()
        checker = get_update_checker()
        
        lines = ["### UPDATE STATUS", ""]
        
        # Last check
        if scheduler.last_check_file.exists():
            try:
                data = json.loads(scheduler.last_check_file.read_text())
                lines.append(f"**Last Check**: {data['timestamp'][:19]}")
                if "result" in data and "current" in data["result"]:
                    lines.append(f"**Current Version**: {data['result']['current']}")
            except:
                lines.append("**Last Check**: Unknown")
        else:
            lines.append("**Last Check**: Never")
        
        lines.append(f"**Auto-Check Interval**: {UPDATE_CONFIG['check_interval_hours']} hours")
        lines.append(f"**Auto-Apply**: {'Enabled' if UPDATE_CONFIG['auto_apply'] else 'Disabled'}")
        
        return "\n".join(lines)
    
    if action == "scheduler_start":
        scheduler = get_update_scheduler()
        scheduler.start()
        return "[OK] Update scheduler started."
    
    if action == "scheduler_stop":
        scheduler = get_update_scheduler()
        scheduler.stop()
        return "⏸ Update scheduler stopped."
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Auto-Update System...\n")
    
    # Check for updates
    print("--- Update Check ---")
    print(update_tool("check"))
    
    print("\n--- Status ---")
    print(update_tool("status"))
    
    print("\n--- Changelog ---")
    print(update_tool("changelog"))
