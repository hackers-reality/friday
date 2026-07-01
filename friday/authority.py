"""
Friday Authority & Action Policy — classify tool risks and enforce policy.

Allows FRIDAY to self-govern: block dangerous actions, warn on medium risk,
log all decisions, and support configurable policies.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import copy

from friday._paths import FRIDAY_MEMORY

_AUTHORITY_POLICY_FILE = os.path.join(FRIDAY_MEMORY, "authority_policy.json")
_AUTHORITY_LOG_FILE = os.path.join(FRIDAY_MEMORY, "authority_log.jsonl")

# ─── Risk classifications ──────────────────────────────────

RISK_ORDER = [
    "read_only",
    "local_write",
    "destructive",
    "system_control",
    "external_send",
    "credential",
    "network_write",
    "self_modify",
    "background_autonomy",
]

RISK_LEVELS = {k: i for i, k in enumerate(RISK_ORDER)}

# ─── Default policy ────────────────────────────────────────

_DEFAULT_POLICY: Dict[str, Any] = {
    "mode": "auto",  # "auto" | "ask" | "dry_run" | "block_all"
    "allow_read_only": True,
    "allow_local_write": True,
    "allow_destructive": False,
    "allow_system_control": False,
    "allow_external_send": True,
    "allow_credential": True,
    "allow_network_write": False,
    "allow_self_modify": False,
    "allow_background_autonomy": True,
    "max_risk_level": 8,  # 0=read_only, 1=local_write, 2=destructive, ...
    "blocked_tools": [],
    "require_approval_tools": [],
    "snapshot_before_destructive": True,
    "log_all": True,
}


def _get_default_policy() -> dict:
    return copy.deepcopy(_DEFAULT_POLICY)


# ─── Policy I/O ────────────────────────────────────────────

def load_authority_policy() -> dict:
    """Load the authority policy from disk, or return defaults."""
    if os.path.exists(_AUTHORITY_POLICY_FILE):
        try:
            with open(_AUTHORITY_POLICY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _get_default_policy()


def save_authority_policy(policy: dict) -> None:
    """Save the authority policy to disk."""
    os.makedirs(os.path.dirname(_AUTHORITY_POLICY_FILE), exist_ok=True)
    with open(_AUTHORITY_POLICY_FILE, "w") as f:
        json.dump(policy, f, indent=4)


# ─── Classification ────────────────────────────────────────

def classify_tool_risk(tool_name: str) -> str:
    """
    Classify a tool's risk level.

    Uses the tool_registry if available, otherwise falls back to
    heuristics based on tool name patterns.

    Returns one of the RISK_ORDER strings.
    """
    # Try known tool registry first
    try:
        from friday.tool_registry import get_tool_metadata
        meta = get_tool_metadata(tool_name)
        if meta and "risk" in meta:
            return meta["risk"]
    except ImportError:
        pass

    # Heuristic fallback
    name_lower = tool_name.lower()

    # Read-only patterns
    if any(name_lower.startswith(p) for p in ("get_", "list_", "read_", "search_",
                                                 "check_", "status_", "find_",
                                                 "system_", "recall_", "queue_status",
                                                 "queue_result")):
        return "read_only"

    # Destructive patterns
    if any(p in name_lower for p in ("delete", "remove", "destroy", "kill")):
        return "destructive"

    # System control
    if any(p in name_lower for p in ("run_cmd", "safe_run", "hotkey",
                                       "press_key", "shutdown", "restart")):
        return "system_control"

    # External send
    if any(p in name_lower for p in ("send_", "post_", "email_", "dm", "comment")):
        return "external_send"

    # Credential
    if any(p in name_lower for p in ("authorize", "auth", "login", "token", "credential",
                                       "exchange_oauth", "refresh_token")):
        return "credential"

    # Network write
    if any(p in name_lower for p in ("github_write", "github_create", "github_merge",
                                       "github_delete", "write_file")):
        return "network_write"

    # Self-modify
    if any(p in name_lower for p in ("self_modify", "self_improve")):
        return "self_modify"

    # Background autonomy
    if any(p in name_lower for p in ("autonomy_tool", "self_improve")):
        return "background_autonomy"

    # Local write (default for remaining tool-like things)
    if any(p in name_lower for p in ("write", "move", "copy", "create", "set_",
                                       "open_", "close_", "click", "type_", "scroll",
                                       "drag", "focus", "hover", "check", "uncheck",
                                       "generate", "draft", "import", "audit",
                                       "repair", "approve", "reject", "pin", "unpin",
                                       "decay", "store", "queue_task", "multi_task",
                                       "schedule", "workflow", "plugin", "startup",
                                       "notification", "clear_")):
        return "local_write"

    return "read_only"


# ─── Decision ──────────────────────────────────────────────

def should_allow_tool(tool_name: str, args: dict = None) -> dict:
    """
    Decide whether a tool call should be allowed.

    Args:
        tool_name: The tool name.
        args: Optional tool arguments (for context).

    Returns:
        dict with keys:
          - "allowed": bool
          - "risk": str risk level
          - "reason": str explanation
          - "needs_approval": bool
    """
    policy = load_authority_policy()

    # Mode-based blocking
    if policy.get("mode") == "block_all":
        return {"allowed": False, "risk": "blocked", "reason": "Authority mode is block_all", "needs_approval": False}

    # Blocked tools list
    if tool_name in policy.get("blocked_tools", []):
        return {"allowed": False, "risk": "blocked", "reason": f"Tool '{tool_name}' is in blocked list", "needs_approval": False}

    risk = classify_tool_risk(tool_name)
    risk_level = RISK_LEVELS.get(risk, 0)
    max_level = policy.get("max_risk_level", 2)

    # Check individual permission (default True for read_only, False for others)
    perm_key = f"allow_{risk}"
    perm_default = True if risk == "read_only" else False
    if not policy.get(perm_key, perm_default):
        if policy.get("mode") == "dry_run":
            return {"allowed": False, "risk": risk, "reason": f"Dry run: would block {risk} tool '{tool_name}'", "needs_approval": False}
        return {"allowed": False, "risk": risk, "reason": f"Policy blocks {risk} tools", "needs_approval": True}

    # Check max risk level
    if risk_level > max_level:
        if policy.get("mode") == "dry_run":
            return {"allowed": False, "risk": risk, "reason": f"Dry run: risk level {risk_level} > max {max_level}", "needs_approval": False}
        return {"allowed": False, "risk": risk, "reason": f"Risk level {risk_level} exceeds max {max_level}", "needs_approval": True}

    # Require approval for specific tools
    if tool_name in policy.get("require_approval_tools", []):
        return {"allowed": True, "risk": risk, "reason": f"Allowed but requires approval", "needs_approval": True}

    return {"allowed": True, "risk": risk, "reason": "Policy allows", "needs_approval": False}


# ─── Audit log ─────────────────────────────────────────────

def log_authority_decision(tool_name: str, args: dict, decision: dict, session: str = "") -> None:
    """Log an authority decision to the JSONL audit log."""
    if not decision.get("needs_approval") and not decision.get("log", True):
        return
    try:
        os.makedirs(os.path.dirname(_AUTHORITY_LOG_FILE), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "args": str(args)[:200],
            "decision": decision.get("allowed", False),
            "risk": decision.get("risk", "unknown"),
            "reason": decision.get("reason", ""),
            "session": session,
        }
        with open(_AUTHORITY_LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ─── Authority tool ────────────────────────────────────────

def authority_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool to manage authority policy.
    Actions: status, policy, allow, block, mode, log, risk.
    """
    if action == "status":
        policy = load_authority_policy()
        return (
            f"### AUTHORITY STATUS\n\n"
            f"Mode: {policy.get('mode', 'auto')}\n"
            f"Max Risk Level: {policy.get('max_risk_level', 2)} ({RISK_ORDER[policy.get('max_risk_level', 2)]})\n"
            f"Blocked Tools: {', '.join(policy.get('blocked_tools', [])) or 'None'}\n"
            f"Require Approval: {', '.join(policy.get('require_approval_tools', [])) or 'None'}\n"
            f"Snapshot Before Destructive: {policy.get('snapshot_before_destructive', True)}\n"
            f"Log All: {policy.get('log_all', True)}"
        )

    if action == "policy":
        policy = load_authority_policy()
        lines = ["### AUTHORITY POLICY\n"]
        for k, v in policy.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    if action == "mode":
        new_mode = kwargs.get("mode", "")
        if new_mode not in ("auto", "ask", "dry_run", "block_all"):
            return "[FAIL] Mode must be: auto, ask, dry_run, or block_all"
        policy = load_authority_policy()
        policy["mode"] = new_mode
        save_authority_policy(policy)
        return f"[OK] Authority mode set to '{new_mode}'."

    if action == "allow":
        risk = kwargs.get("risk", "")
        if not risk or risk not in RISK_ORDER:
            return f"[FAIL] Risk must be one of: {', '.join(RISK_ORDER)}"
        policy = load_authority_policy()
        perm_key = f"allow_{risk}"
        if perm_key in policy:
            policy[perm_key] = True
        level = RISK_LEVELS.get(risk, 0)
        if level > policy.get("max_risk_level", 2):
            policy["max_risk_level"] = level
        save_authority_policy(policy)
        return f"[OK] Allowed {risk} tools."

    if action == "block":
        risk = kwargs.get("risk", "")
        if risk and risk in RISK_ORDER:
            policy = load_authority_policy()
            perm_key = f"allow_{risk}"
            if perm_key in policy:
                policy[perm_key] = False
            save_authority_policy(policy)
            return f"[OK] Blocked {risk} tools."

        tool_name = kwargs.get("tool", "")
        if tool_name:
            policy = load_authority_policy()
            blocked = policy.setdefault("blocked_tools", [])
            if tool_name not in blocked:
                blocked.append(tool_name)
            save_authority_policy(policy)
            return f"[OK] Blocked tool '{tool_name}'."

        return "[FAIL] Provide 'risk' level or 'tool' name."

    if action == "unblock":
        tool_name = kwargs.get("tool", "")
        if not tool_name:
            return "[FAIL] Provide 'tool' name to unblock."
        policy = load_authority_policy()
        blocked = policy.get("blocked_tools", [])
        if tool_name in blocked:
            blocked.remove(tool_name)
            policy["blocked_tools"] = blocked
            save_authority_policy(policy)
            return f"[OK] Unblocked tool '{tool_name}'."
        return f"[OK] Tool '{tool_name}' was not blocked."

    if action == "max_level":
        level = kwargs.get("level", None)
        if level is None:
            return f"[FAIL] Provide level (0-8). 0=read_only, 2=destructive, 4=external_send, 8=background_autonomy"
        try:
            level = int(level)
        except (TypeError, ValueError):
            return "[FAIL] Level must be an integer."
        if level < 0 or level >= len(RISK_ORDER):
            return f"[FAIL] Level must be 0-{len(RISK_ORDER)-1}"
        policy = load_authority_policy()
        policy["max_risk_level"] = level
        save_authority_policy(policy)
        return f"[OK] Max risk level set to {level} ({RISK_ORDER[level]})."

    if action == "classify":
        tool_name = kwargs.get("tool", "")
        if not tool_name:
            return "[FAIL] Provide 'tool' name."
        risk = classify_tool_risk(tool_name)
        return f"  {tool_name} -> {risk}"

    if action == "log":
        try:
            if not os.path.exists(_AUTHORITY_LOG_FILE):
                return "[OK] No authority decisions logged yet."
            with open(_AUTHORITY_LOG_FILE, "r") as f:
                lines = f.readlines()
            recent = [json.loads(l) for l in lines[-20:] if l.strip()]
            parts = ["### RECENT AUTHORITY DECISIONS\n"]
            for entry in recent[-10:]:
                parts.append(
                    f"  [{entry.get('risk','?')}] {entry.get('tool','?')} -> "
                    f"{'ALLOW' if entry.get('decision') else 'BLOCK'} "
                    f"({entry.get('reason','')[:60]})"
                )
            return "\n".join(parts)
        except Exception as e:
            return f"[FAIL] Error reading log: {e}"

    return f"[FAIL] Unknown action: {action}. Available: status, policy, mode, allow, block, max_level, classify, log"
