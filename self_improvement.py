"""
Friday Self-Improvement Loop - Phase 7.5
Friday analyzes its own performance, identifies improvement areas,
and suggests/implements enhancements automatically.
"""
from __future__ import annotations

import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


# ─── Performance Metrics ────────────────────────────────────#

class PerformanceMetrics:
    """Track Friday's performance metrics."""

    def __init__(self, storage_path: str = "friday_memory/metrics.json"):
        self.storage_path = storage_path
        self.metrics = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load metrics from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "avg_response_time": 0,
                "tool_calls": {},
                "errors": [],
                "improvements_applied": [],
                "last_updated": None,
            }

    def save(self):
        """Save metrics to storage."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def record_task(self, success: bool, duration: float, tool_name: str = None):
        """Record a completed task."""
        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1

        # Update average response time
        n = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        old_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (old_avg * (n - 1) + duration) / n

        if tool_name:
            self.metrics["tool_calls"][tool_name] = self.metrics["tool_calls"].get(tool_name, 0) + 1

        self.metrics["last_updated"] = datetime.now().isoformat()
        self.save()

    def record_error(self, error: str, context: str = None):
        """Record an error."""
        self.metrics["errors"].append({
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only last 50 errors
        self.metrics["errors"] = self.metrics["errors"][-50:]
        self.save()

    def get_stats(self) -> str:
        """Get human-readable stats."""
        total = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        success_rate = (self.metrics["tasks_completed"] / total * 100) if total > 0 else 0

        lines = [
            "### FRIDAY PERFORMANCE METRICS",
            "",
            f"**Total Tasks**: {total}",
            f"**Success Rate**: {success_rate:.1f}%",
            f"**Avg Response Time**: {self.metrics['avg_response_time']:.2f}s",
            "",
            "**Tool Usage**:",
        ]

        for tool, count in sorted(self.metrics["tool_calls"].items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  - {tool}: {count} calls")

        if self.metrics["errors"]:
            lines.append("")
            lines.append(f"**Recent Errors** ({len(self.metrics['errors'])}):")
            for err in self.metrics["errors"][-3:]:
                lines.append(f"  - {err['error'][:80]}")

        return "\n".join(lines)


# ─── Improvement Suggestions ────────────────────────────────────#

class ImprovementEngine:
    """Analyzes performance and suggests improvements."""

    def __init__(self, metrics: PerformanceMetrics):
        self.metrics = metrics

    def analyze(self) -> List[Dict[str, Any]]:
        """Analyze metrics and return improvement suggestions."""
        suggestions = []

        # Check success rate
        total = self.metrics.metrics["tasks_completed"] + self.metrics.metrics["tasks_failed"]
        if total >= 10:
            success_rate = self.metrics.metrics["tasks_completed"] / total
            if success_rate < 0.8:
                suggestions.append({
                    "type": "reliability",
                    "priority": "high",
                    "issue": f"Low success rate: {success_rate:.1%}",
                    "suggestion": "Review error logs and add more error handling",
                    "action": "review_errors",
                })

        # Check response time
        avg_time = self.metrics.metrics["avg_response_time"]
        if avg_time > 5.0:
            suggestions.append({
                "type": "performance",
                "priority": "medium",
                "issue": f"Slow response time: {avg_time:.1f}s",
                "suggestion": "Optimize slow tools, add caching, or use faster models",
                "action": "optimize_performance",
            })

        # Check for recurring errors
        error_types = {}
        for err in self.metrics.metrics["errors"]:
            err_msg = err["error"]
            # Categorize errors
            if "timeout" in err_msg.lower():
                error_types["timeout"] = error_types.get("timeout", 0) + 1
            elif "import" in err_msg.lower() or "module" in err_msg.lower():
                error_types["import"] = error_types.get("import", 0) + 1
            elif "api" in err_msg.lower():
                error_types["api"] = error_types.get("api", 0) + 1

        for err_type, count in error_types.items():
            if count >= 3:
                suggestions.append({
                    "type": "error_pattern",
                    "priority": "high" if count >= 5 else "medium",
                    "issue": f"Recurring {err_type} errors ({count} times)",
                    "suggestion": f"Investigate and fix {err_type} error root cause",
                    "action": f"fix_{err_type}_errors",
                })

        # Check tool usage balance
        tool_calls = self.metrics.metrics["tool_calls"]
        if tool_calls:
            most_used = max(tool_calls.items(), key=lambda x: x[1])
            if most_used[1] > sum(tool_calls.values()) * 0.5:
                suggestions.append({
                    "type": "usage_balance",
                    "priority": "low",
                    "issue": f"Over-reliance on {most_used[0]} ({most_used[1]} calls)",
                    "suggestion": "Consider using alternative tools or distributing workload",
                    "action": "balance_tool_usage",
                })

        return suggestions

    def get_improvement_plan(self) -> str:
        """Generate a human-readable improvement plan."""
        suggestions = self.analyze()

        if not suggestions:
            return "[OK] No improvements needed at this time."

        lines = ["### IMPROVEMENT PLAN", ""]

        # Group by priority
        high = [s for s in suggestions if s["priority"] == "high"]
        medium = [s for s in suggestions if s["priority"] == "medium"]
        low = [s for s in suggestions if s["priority"] == "low"]

        if high:
            lines.append("**HIGH PRIORITY**:")
            for s in high:
                lines.append(f"  🔴 {s['issue']}")
                lines.append(f"     → {s['suggestion']}")
            lines.append("")

        if medium:
            lines.append("**MEDIUM PRIORITY**:")
            for s in medium:
                lines.append(f"  🟡 {s['issue']}")
                lines.append(f"     → {s['suggestion']}")
            lines.append("")

        if low:
            lines.append("**LOW PRIORITY**:")
            for s in low:
                lines.append(f"  [OK] {s['issue']}")
                lines.append(f"     → {s['suggestion']}")

        return "\n".join(lines)


# ─── Self-Improvement Loop ────────────────────────────────────#

class SelfImprovementLoop:
    """
    Main loop that periodically analyzes performance
    and applies improvements.
    """

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.engine = ImprovementEngine(self.metrics)
        self.running = False

    def record_success(self, duration: float, tool_name: str = None):
        """Record a successful task."""
        self.metrics.record_task(success=True, duration=duration, tool_name=tool_name)

    def record_failure(self, duration: float, error: str, context: str = None):
        """Record a failed task."""
        self.metrics.record_task(success=False, duration=duration)
        self.metrics.record_error(error, context)

    def get_status(self) -> str:
        """Get full status report."""
        lines = []

        # Performance stats
        lines.append(self.metrics.get_stats())
        lines.append("")
        lines.append("---")
        lines.append("")

        # Improvement plan
        lines.append(self.engine.get_improvement_plan())

        return "\n".join(lines)

    def apply_improvement(self, action: str) -> str:
        """
        Apply a specific improvement.
        In production, this would actually modify code/configuration.
        """
        if action == "review_errors":
            errors = self.metrics.metrics["errors"][-10:]
            return f"📋 Reviewing {len(errors)} recent errors:\n" + "\n".join(
                f"  - {e['error'][:80]}" for e in errors
            )

        elif action == "optimize_performance":
            return "⚡ Performance optimization:\n  - Enable response caching\n  - Use faster model for simple queries\n  - Reduce screenshot frequency"

        elif action == "fix_timeout_errors":
            return "🔧 Fixing timeout errors:\n  - Increase default timeouts\n  - Add retry logic\n  - Use async where possible"

        elif action == "fix_import_errors":
            return "📦 Fixing import errors:\n  - Check requirements.txt\n  - Install missing packages\n  - Add try/except for optional imports"

        elif action == "fix_api_errors":
            return "🔑 Fixing API errors:\n  - Verify API keys\n  - Add rate limiting\n  - Implement exponential backoff"

        return f"Unknown action: {action}"


# ─── Global Instance ────────────────────────────────────#

_improver_instance = None

def get_improver() -> SelfImprovementLoop:
    """Get or create the global improver instance."""
    global _improver_instance
    if _improver_instance is None:
        _improver_instance = SelfImprovementLoop()
    return _improver_instance


# ─── Tool Function for Friday ────────────────────────────────────#

def self_improvement_tool(
    action: str = "status",
    duration: float = None,
    success: bool = None,
    error: str = None,
    improvement_action: str = None,
) -> str:
    """
    Friday tool for self-improvement.
    Actions: status, record, apply, plan
    """
    improver = get_improver()

    if action == "status":
        return improver.get_status()

    if action == "record":
        if duration is not None:
            if success:
                improver.record_success(duration)
                return "[OK] Recorded successful task."
            else:
                improver.record_failure(duration, error or "Unknown error")
                return "[FAIL] Recorded failed task."
        return "[FAIL] Duration required for recording."

    if action == "plan":
        return improver.engine.get_improvement_plan()

    if action == "apply":
        if improvement_action:
            return improver.apply_improvement(improvement_action)
        return "[FAIL] Improvement action required."

    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Self-Improvement Loop...\n")

    improver = get_improver()

    # Simulate some task recordings
    improver.record_success(1.5, "friday_query")
    improver.record_success(2.0, "friday_query")
    improver.record_failure(10.0, "TimeoutError: API timeout", "friday_query")
    improver.record_failure(8.0, "TimeoutError: API timeout", "friday_query")
    improver.record_failure(12.0, "ImportError: No module named 'xyz'", "file_generator")

    # Show status
    print(improver.get_status())
