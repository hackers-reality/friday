"""
Agent Town Hall — autonomous agent deliberation & coordination system.
Agents discuss tasks, delegate work, review results, and plan together.

Architecture:
  - TownHall: manages agent sessions, agendas, minutes
  - AgentSession: one deliberation session with agenda + outcomes
  - Auto-delegation: agents propose tasks, others accept/review

Expanded with:
  - AgentProfile / AgentRegistry class system
  - Voting, consensus, proposals, debates
  - Deliberation templates, session history, persistence
  - Communication patterns, role permissions, escalation
  - Outcome tracking, action items, scheduling
  - Summarization, conflict resolution, personality engine
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("townhall")

_TOWNHALL_DIR = os.path.join(FRIDAY_MEMORY, "townhall")
_SESSIONS_FILE = os.path.join(_TOWNHALL_DIR, "sessions.json")
_MINUTES_DIR = os.path.join(_TOWNHALL_DIR, "minutes")
_AGENDA_FILE = os.path.join(_TOWNHALL_DIR, "agenda.json")
_PROPOSALS_FILE = os.path.join(_TOWNHALL_DIR, "proposals.json")
_VOTES_FILE = os.path.join(_TOWNHALL_DIR, "votes.json")
_DEBATES_FILE = os.path.join(_TOWNHALL_DIR, "debates.json")
_DMS_FILE = os.path.join(_TOWNHALL_DIR, "direct_messages.json")
_OUTCOMES_FILE = os.path.join(_TOWNHALL_DIR, "outcomes.json")
_ACTIONS_FILE = os.path.join(_TOWNHALL_DIR, "action_items.json")
_SCHEDULE_FILE = os.path.join(_TOWNHALL_DIR, "schedule.json")
_ESCALATIONS_FILE = os.path.join(_TOWNHALL_DIR, "escalations.json")
_ARCHIVE_DIR = os.path.join(_TOWNHALL_DIR, "archive")

AGENT_ROLES = {
    "veronica": "Deep research & intelligence — finds information, analyzes data",
    "forge": "Code architect — writes, reviews, refactors code",
    "ghost": "Cybersecurity — OSINT, recon, vulnerability assessment",
    "atlas": "Knowledge curator — memory, graphs, relationships",
    "jarvis": "Personal assistant — desktop, browser, system control",
    "nova": "Strategist & scheduler — planning, timelines, coordination",
    "athena": "Strategic planner — risk analysis, roadmaps",
    "sentinel": "PR reviewer — code review, test validation",
}

# ── Enums ──

class VoteType(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    BLOCK = "block"

class ProposalStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DISCUSSING = "discussing"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    AMENDED = "amended"

class MessageType(Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    PROPOSAL = "proposal"
    VOTE = "vote"
    SYSTEM = "system"
    DEBATE = "debate"

class SessionStatus(Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

# ── Personality Engine ──

class PersonalityProfile:
    """Defines behavioral traits for an agent that influence voting, debate, and deliberation."""

    def __init__(
        self,
        assertiveness: float = 0.5,
        cooperativeness: float = 0.5,
        risk_tolerance: float = 0.5,
        expertise_depth: float = 0.5,
        openness: float = 0.5,
        conscientiousness: float = 0.5,
    ):
        self.assertiveness = max(0.0, min(1.0, assertiveness))
        self.cooperativeness = max(0.0, min(1.0, cooperativeness))
        self.risk_tolerance = max(0.0, min(1.0, risk_tolerance))
        self.expertise_depth = max(0.0, min(1.0, expertise_depth))
        self.openness = max(0.0, min(1.0, openness))
        self.conscientiousness = max(0.0, min(1.0, conscientiousness))

    def to_dict(self) -> dict[str, float]:
        return {
            "assertiveness": self.assertiveness,
            "cooperativeness": self.cooperativeness,
            "risk_tolerance": self.risk_tolerance,
            "expertise_depth": self.expertise_depth,
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "PersonalityProfile":
        return cls(**data)

    def likelihood_to_speak(self, round_num: int, total_rounds: int) -> float:
        """Higher assertiveness = more likely to speak early."""
        base = self.assertiveness * 0.7 + (1 - self.cooperativeness) * 0.3
        if round_num == 1:
            return base * 1.2
        return base * (0.8 + 0.4 * (round_num / total_rounds))

    def likelihood_to_approve(self) -> float:
        return self.cooperativeness * 0.6 + self.risk_tolerance * 0.2 + self.conscientiousness * 0.2

    def likelihood_to_block(self) -> float:
        return self.assertiveness * 0.5 + (1 - self.risk_tolerance) * 0.3 + self.expertise_depth * 0.2

    def debate_aggressiveness(self) -> float:
        return self.assertiveness * 0.6 + (1 - self.cooperativeness) * 0.4

# ── AgentProfile ──

class AgentProfile:
    """Represents a single agent with role, personality, expertise, and communication style."""

    def __init__(
        self,
        name: str,
        role: str,
        personality: Optional[PersonalityProfile] = None,
        expertise_areas: Optional[list[str]] = None,
        communication_style: str = "formal",
        color: str = "#888888",
        icon: str = "robot",
    ):
        self.name = name
        self.role = role
        self.personality = personality or PersonalityProfile()
        self.expertise_areas = expertise_areas or []
        self.communication_style = communication_style
        self.color = color
        self.icon = icon
        self.agent_id = name.lower().replace(" ", "_")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "personality": self.personality.to_dict(),
            "expertise_areas": self.expertise_areas,
            "communication_style": self.communication_style,
            "color": self.color,
            "icon": self.icon,
            "agent_id": self.agent_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        personality = PersonalityProfile.from_dict(data.get("personality", {}))
        return cls(
            name=data["name"],
            role=data["role"],
            personality=personality,
            expertise_areas=data.get("expertise_areas", []),
            communication_style=data.get("communication_style", "formal"),
            color=data.get("color", "#888888"),
            icon=data.get("icon", "robot"),
        )

    def has_expertise_in(self, area: str) -> bool:
        return any(area.lower() in e.lower() for e in self.expertise_areas)

# ── AgentRegistry (Singleton) ──

class AgentRegistry:
    """Singleton registry managing all AgentProfile instances."""

    _instance: Optional[AgentRegistry] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> AgentRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._agents: dict[str, AgentProfile] = {}
        self._initialized = True
        self._init_default_agents()

    def _init_default_agents(self):
        """Populate registry with default agents from AGENT_ROLES."""
        defaults = {
            "veronica": AgentProfile(
                name="Veronica",
                role=AGENT_ROLES["veronica"],
                personality=PersonalityProfile(assertiveness=0.7, cooperativeness=0.5, risk_tolerance=0.4, expertise_depth=0.9, openness=0.8, conscientiousness=0.7),
                expertise_areas=["research","osint","data analysis","intelligence","web scraping"],
                communication_style="analytical", color="#ff6600", icon="search",
            ),
            "forge": AgentProfile(
                name="Forge", role=AGENT_ROLES["forge"],
                personality=PersonalityProfile(assertiveness=0.6, cooperativeness=0.6, risk_tolerance=0.3, expertise_depth=0.95, openness=0.4, conscientiousness=0.9),
                expertise_areas=["python","javascript","code review","architecture","testing","refactoring"],
                communication_style="technical", color="#0066ff", icon="code",
            ),
            "ghost": AgentProfile(
                name="Ghost", role=AGENT_ROLES["ghost"],
                personality=PersonalityProfile(assertiveness=0.8, cooperativeness=0.3, risk_tolerance=0.7, expertise_depth=0.85, openness=0.6, conscientiousness=0.8),
                expertise_areas=["cybersecurity","osint","pentesting","vulnerability assessment","threat intel"],
                communication_style="direct", color="#ff003c", icon="shield",
            ),
            "atlas": AgentProfile(
                name="Atlas", role=AGENT_ROLES["atlas"],
                personality=PersonalityProfile(assertiveness=0.4, cooperativeness=0.8, risk_tolerance=0.3, expertise_depth=0.85, openness=0.7, conscientiousness=0.8),
                expertise_areas=["knowledge graphs","memory","databases","neo4j","chromadb","vector search"],
                communication_style="methodical", color="#00ffcc", icon="database",
            ),
            "jarvis": AgentProfile(
                name="Jarvis", role=AGENT_ROLES["jarvis"],
                personality=PersonalityProfile(assertiveness=0.5, cooperativeness=0.7, risk_tolerance=0.4, expertise_depth=0.7, openness=0.6, conscientiousness=0.6),
                expertise_areas=["desktop automation","system control","browser","media","filesystem"],
                communication_style="helpful", color="#9933ff", icon="monitor",
            ),
            "nova": AgentProfile(
                name="Nova", role=AGENT_ROLES["nova"],
                personality=PersonalityProfile(assertiveness=0.6, cooperativeness=0.7, risk_tolerance=0.5, expertise_depth=0.8, openness=0.7, conscientiousness=0.85),
                expertise_areas=["scheduling","planning","coordination","timelines","project management"],
                communication_style="organized", color="#33ccff", icon="calendar",
            ),
            "athena": AgentProfile(
                name="Athena", role=AGENT_ROLES["athena"],
                personality=PersonalityProfile(assertiveness=0.7, cooperativeness=0.5, risk_tolerance=0.3, expertise_depth=0.9, openness=0.6, conscientiousness=0.9),
                expertise_areas=["strategic planning","risk analysis","roadmapping","decision analysis"],
                communication_style="strategic", color="#ffcc00", icon="target",
            ),
            "sentinel": AgentProfile(
                name="Sentinel", role=AGENT_ROLES["sentinel"],
                personality=PersonalityProfile(assertiveness=0.5, cooperativeness=0.5, risk_tolerance=0.2, expertise_depth=0.85, openness=0.3, conscientiousness=0.95),
                expertise_areas=["code review","testing","qa","validation","standards compliance"],
                communication_style="precise", color="#ff3366", icon="git-pull-request",
            ),
        }
        for name, profile in defaults.items():
            self.register(profile)

    def register(self, profile: AgentProfile) -> str:
        self._agents[profile.agent_id] = profile
        return profile.agent_id

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get(self, agent_id: str) -> Optional[AgentProfile]:
        return self._agents.get(agent_id)

    def get_by_name(self, name: str) -> Optional[AgentProfile]:
        for agent in self._agents.values():
            if agent.name.lower() == name.lower():
                return agent
        return None

    def list_all(self) -> list[AgentProfile]:
        return list(self._agents.values())

    def list_names(self) -> list[str]:
        return [a.name for a in self._agents.values()]

    def find_by_expertise(self, area: str) -> list[AgentProfile]:
        return [a for a in self._agents.values() if a.has_expertise_in(area)]


def get_agent_registry() -> AgentRegistry:
    return AgentRegistry()

# ── Role-Based Permissions ──

class Permission(Enum):
    PROPOSE = "propose"
    VOTE = "vote"
    APPROVE_TECHNICAL = "approve_technical"
    ESCALATE = "escalate"
    SCHEDULE = "schedule"
    ARCHIVE = "archive"
    MEDIATE = "mediate"
    BROADCAST = "broadcast"
    MANAGE_AGENDA = "manage_agenda"
    MANAGE_ACTIONS = "manage_actions"
    CONCLUDE_SESSION = "conclude_session"
    WITHDRAW_PROPOSAL = "withdraw_proposal"

class RolePermission:
    """Maps agent roles to their permitted actions."""
    _permissions: dict[str, set[Permission]] = {
        "veronica": {Permission.PROPOSE, Permission.VOTE, Permission.BROADCAST, Permission.MANAGE_AGENDA},
        "forge": {Permission.PROPOSE, Permission.VOTE, Permission.APPROVE_TECHNICAL, Permission.BROADCAST, Permission.MANAGE_ACTIONS},
        "ghost": {Permission.PROPOSE, Permission.VOTE, Permission.ESCALATE, Permission.BROADCAST},
        "atlas": {Permission.PROPOSE, Permission.VOTE, Permission.BROADCAST, Permission.ARCHIVE, Permission.MANAGE_AGENDA},
        "jarvis": {Permission.PROPOSE, Permission.VOTE, Permission.BROADCAST, Permission.SCHEDULE},
        "nova": {Permission.PROPOSE, Permission.VOTE, Permission.BROADCAST, Permission.SCHEDULE, Permission.MANAGE_AGENDA, Permission.CONCLUDE_SESSION},
        "athena": {Permission.PROPOSE, Permission.VOTE, Permission.BROADCAST, Permission.MEDIATE, Permission.CONCLUDE_SESSION, Permission.WITHDRAW_PROPOSAL},
        "sentinel": {Permission.PROPOSE, Permission.VOTE, Permission.APPROVE_TECHNICAL, Permission.BROADCAST, Permission.ARCHIVE},
    }

    @classmethod
    def check_permission(cls, agent_id: str, permission: Permission) -> bool:
        if agent_id not in cls._permissions:
            return False
        return permission in cls._permissions[agent_id]

    @classmethod
    def get_permissions(cls, agent_id: str) -> set[Permission]:
        return cls._permissions.get(agent_id, set())

    @classmethod
    def list_permissions(cls, agent_id: str) -> list[str]:
        return [p.value for p in cls.get_permissions(agent_id)]

    @classmethod
    def grant_permission(cls, agent_id: str, permission: Permission):
        if agent_id not in cls._permissions:
            cls._permissions[agent_id] = set()
        cls._permissions[agent_id].add(permission)

    @classmethod
    def revoke_permission(cls, agent_id: str, permission: Permission):
        if agent_id in cls._permissions:
            cls._permissions[agent_id].discard(permission)

# ── Helpers ──

def _ensure_dirs():
    for d in (_TOWNHALL_DIR, _MINUTES_DIR, _ARCHIVE_DIR):
        os.makedirs(d, exist_ok=True)

def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def _save_json(path: str, data):
    _ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

def _now_iso() -> str:
    return datetime.now().isoformat()

def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

# ── Agenda Management ──

def add_agenda_item(title: str, description: str = "", assigned_to: str = "", priority: str = "medium") -> dict:
    """Add an item to the town hall agenda."""
    agendas = _load_json(_AGENDA_FILE, {"items": []})
    item = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "priority": priority,
        "status": "open",
        "created": _now_iso(),
        "resolved_at": "",
    }
    agendas["items"].append(item)
    _save_json(_AGENDA_FILE, agendas)
    return item

def list_agenda(status: str = "") -> str:
    agendas = _load_json(_AGENDA_FILE, {"items": []})
    items = agendas.get("items", [])
    if status:
        items = [i for i in items if i.get("status") == status]
    if not items:
        return "No agenda items."
    lines = [f"### Town Hall Agenda ({len(items)} items)"]
    for item in items:
        icon = {"open":"\u25cb","in_progress":"\u25d0","resolved":"\u25cf","cancelled":"\u2297"}.get(item.get("status","open"),"\u25cb")
        assign = f" \u2192 {item["assigned_to"]}" if item.get("assigned_to") else ""
        lines.append(f"  {icon} [{item["id"]}] {item["title"]}{assign} ({item.get("priority","medium")})")
        if item.get("description"):
            lines.append(f"      {item["description"][:100]}")
    return "\n".join(lines)

def resolve_agenda_item(item_id: str, resolution: str = "completed") -> str:
    agendas = _load_json(_AGENDA_FILE, {"items": []})
    for item in agendas["items"]:
        if item["id"] == item_id:
            item["status"] = "resolved" if resolution == "completed" else "cancelled"
            item["resolved_at"] = _now_iso()
            item["resolution"] = resolution
            _save_json(_AGENDA_FILE, agendas)
            return f"[OK] Agenda item {item_id} resolved: {resolution}"
    return f"[FAIL] Agenda item {item_id} not found"

# ── Voting System ──

def cast_vote(session_id: str, agent_name: str, vote: str, proposal_id: str = "") -> str:
    try:
        vote_enum = VoteType(vote.lower())
    except ValueError:
        return f"[FAIL] Invalid vote type: {vote}. Use: approve, reject, abstain, block"
    votes_data = _load_json(_VOTES_FILE, {"votes": []})
    vote_record = {
        "id": uuid.uuid4().hex[:8],
        "session_id": session_id,
        "agent_name": agent_name,
        "vote": vote_enum.value,
        "proposal_id": proposal_id,
        "cast_at": _now_iso(),
    }
    votes_data["votes"].append(vote_record)
    _save_json(_VOTES_FILE, votes_data)
    return f"[OK] {agent_name} cast vote {vote} in session {session_id[:8]}"

def tally_votes(session_id: str, proposal_id: str = "") -> str:
    votes_data = _load_json(_VOTES_FILE, {"votes": []})
    relevant = [v for v in votes_data["votes"] if v["session_id"] == session_id and (not proposal_id or v.get("proposal_id") == proposal_id)]
    if not relevant:
        return "No votes recorded."
    registry = get_agent_registry()
    tally = {"approve": 0, "reject": 0, "abstain": 0, "block": 0}
    weighted = {"approve": 0.0, "reject": 0.0, "abstain": 0.0, "block": 0.0}
    for v in relevant:
        vote_val = v["vote"]
        tally[vote_val] = tally.get(vote_val, 0) + 1
        agent = registry.get(v["agent_name"])
        weight = 1.0
        if agent:
            weight = 0.5 + 0.5 * agent.personality.expertise_depth
        weighted[vote_val] = weighted.get(vote_val, 0.0) + weight
    lines = [f"### Vote Tally for Session {session_id[:8]}"]
    if proposal_id:
        lines[0] += f" (Proposal: {proposal_id})"
    lines.append("")
    lines.append("Simple Tally:")
    for vt in ("approve","reject","abstain","block"):
        if tally.get(vt,0) > 0:
            lines.append(f"  {vt}: {tally[vt]}")
    lines.append("")
    lines.append("Weighted Tally (by expertise depth):")
    for vt in ("approve","reject","abstain","block"):
        if weighted.get(vt,0.0) > 0:
            lines.append(f"  {vt}: {weighted[vt]:.1f}")
    lines.append(f"\nTotal votes: {sum(tally.values())}")
    return "\n".join(lines)

# ── Consensus Algorithms ──

def reach_consensus(session_id: str, proposal: str, algorithm: str = "majority") -> str:
    votes_data = _load_json(_VOTES_FILE, {"votes": []})
    session_votes = [v for v in votes_data["votes"] if v["session_id"] == session_id]
    if not session_votes:
        return "No votes cast. Cannot reach consensus."
    approve = sum(1 for v in session_votes if v["vote"] == "approve")
    reject = sum(1 for v in session_votes if v["vote"] == "reject")
    abstain = sum(1 for v in session_votes if v["vote"] == "abstain")
    block = sum(1 for v in session_votes if v["vote"] == "block")
    non_abstain = len(session_votes) - abstain
    if non_abstain == 0:
        return "All votes abstained. No consensus possible."
    algorithm = algorithm.lower()
    result = {"consensus": False, "algorithm": algorithm, "for": approve, "against": reject+block, "abstain": abstain}
    if algorithm == "majority":
        result["consensus"] = approve > (reject + block)
        pct = approve / non_abstain * 100 if non_abstain > 0 else 0
        result["threshold"] = ">50%"
        result["approval_pct"] = round(pct, 1)
    elif algorithm == "supermajority":
        required = non_abstain * 2 / 3
        result["consensus"] = approve >= required
        result["threshold"] = ">=66.7%"
        result["required"] = required
        pct = approve / non_abstain * 100 if non_abstain > 0 else 0
        result["approval_pct"] = round(pct, 1)
    elif algorithm == "unanimous":
        result["consensus"] = reject == 0 and block == 0 and approve > 0
        result["threshold"] = "100%"
        result["approval_pct"] = 100 if result["consensus"] else 0
    elif algorithm == "weighted":
        registry = get_agent_registry()
        wfor = 0.0; wagainst = 0.0
        for v in session_votes:
            agent = registry.get(v["agent_name"])
            weight = 1.0
            if agent:
                weight = 0.5 + 0.5 * agent.personality.expertise_depth
            if v["vote"] == "approve": wfor += weight
            elif v["vote"] in ("reject","block"): wagainst += weight
        result["consensus"] = wfor > wagainst
        total = wfor + wagainst
        result["approval_pct"] = round(wfor/total*100, 1) if total > 0 else 0
        result["weighted_for"] = round(wfor, 1)
        result["weighted_against"] = round(wagainst, 1)
    else:
        return f"[FAIL] Unknown algorithm: {algorithm}"
    if block > 0:
        result["blocked"] = True
        result["consensus"] = False
    outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
    outcomes["outcomes"].append({"type":"consensus_attempt","session_id":session_id,"proposal":proposal,"result":result,"timestamp":_now_iso()})
    _save_json(_OUTCOMES_FILE, outcomes)
    if result["consensus"]:
        return f"[OK] Consensus REACHED via {algorithm}. Approval: {result.get("approval_pct","?")}%"
    blockers = []
    if block > 0: blockers.append(f"{block} block(s)")
    return f"[NO] Consensus NOT reached via {algorithm}. Blockers: {" ".join(blockers) or "unknown"}. Approval: {result.get("approval_pct","?")}%"

def detect_consensus_blockers(session_id: str) -> str:
    votes_data = _load_json(_VOTES_FILE, {"votes": []})
    session_votes = [v for v in votes_data["votes"] if v["session_id"] == session_id]
    if not session_votes: return "No votes recorded."
    blockers = [v for v in session_votes if v["vote"] == "block"]
    rejectors = [v for v in session_votes if v["vote"] == "reject"]
    lines = [f"### Consensus Blockers for Session {session_id[:8]}"]
    if blockers:
        lines.append(f"\nBlocking agents ({len(blockers)}):")
        for b in blockers:
            ts = b.get("cast_at","")[11:19] if b.get("cast_at") else "?"
            lines.append(f"  \u26d4 {b["agent_name"]} at {ts}")
    if rejectors:
        lines.append(f"\nRejecting agents ({len(rejectors)}):")
        for r in rejectors:
            ts = r.get("cast_at","")[11:19] if r.get("cast_at") else "?"
            lines.append(f"  \u274c {r["agent_name"]} at {ts}")
    if not blockers and not rejectors:
        lines.append("\nNo blockers detected.")
    return "\n".join(lines)

# ── Proposal System ──

def create_proposal(session_id: str, title: str, description: str, proposed_by: str) -> str:
    if not RolePermission.check_permission(proposed_by, Permission.PROPOSE):
        return f"[FAIL] {proposed_by} does not have permission to propose."
    proposals = _load_json(_PROPOSALS_FILE, {"proposals": []})
    proposal = {
        "id": uuid.uuid4().hex[:8], "session_id": session_id,
        "title": title, "description": description,
        "proposed_by": proposed_by, "status": ProposalStatus.SUBMITTED.value,
        "amendments": [], "created_at": _now_iso(), "updated_at": _now_iso(), "vote_tally": {},
    }
    proposals["proposals"].append(proposal)
    _save_json(_PROPOSALS_FILE, proposals)
    return f"[OK] Proposal \"{title}\" created with id {proposal["id"]}"

def amend_proposal(proposal_id: str, amendment: str) -> str:
    proposals = _load_json(_PROPOSALS_FILE, {"proposals": []})
    for prop in proposals["proposals"]:
        if prop["id"] == proposal_id:
            if prop["status"] in (ProposalStatus.APPROVED.value, ProposalStatus.REJECTED.value, ProposalStatus.WITHDRAWN.value):
                return f"[FAIL] Cannot amend {prop["status"]} proposal."
            amendment_record = {"id": uuid.uuid4().hex[:8], "text": amendment, "added_at": _now_iso()}
            prop["amendments"].append(amendment_record)
            prop["status"] = ProposalStatus.AMENDED.value
            prop["updated_at"] = _now_iso()
            _save_json(_PROPOSALS_FILE, proposals)
            return f"[OK] Amendment added to proposal {proposal_id}"
    return f"[FAIL] Proposal {proposal_id} not found"

def withdraw_proposal(proposal_id: str) -> str:
    proposals = _load_json(_PROPOSALS_FILE, {"proposals": []})
    for prop in proposals["proposals"]:
        if prop["id"] == proposal_id:
            prop["status"] = ProposalStatus.WITHDRAWN.value
            prop["updated_at"] = _now_iso()
            _save_json(_PROPOSALS_FILE, proposals)
            return f"[OK] Proposal {proposal_id} withdrawn"
    return f"[FAIL] Proposal {proposal_id} not found"

def list_proposals(session_id: str = "") -> str:
    proposals = _load_json(_PROPOSALS_FILE, {"proposals": []})
    items = proposals["proposals"]
    if session_id: items = [p for p in items if p["session_id"] == session_id]
    if not items: return "No proposals found."
    lines = [f"### Proposals ({len(items)})"]
    for p in items:
        ac = len(p.get("amendments",[]))
        at = f" +{ac} amendments" if ac else ""
        lines.append(f"  [{p["status"]}] [{p["id"]}] {p["title"]} (by {p["proposed_by"]}){at}")
        if p.get("description"):
            lines.append(f"      {p["description"][:120]}")
    return "\n".join(lines)

# ── Deliberation Templates ──

class DeliberationTemplate:
    def __init__(self, name: str, description: str, phases: list[dict[str, Any]], default_duration: int = 10):
        self.name = name
        self.description = description
        self.phases = phases
        self.default_duration = default_duration
    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "phases": self.phases, "default_duration": self.default_duration}

DELIBERATION_TEMPLATES: dict[str, DeliberationTemplate] = {
    "quick_decision": DeliberationTemplate(
        name="Quick Decision",
        description="Single-round rapid decision making for low-risk, time-sensitive topics.",
        phases=[{"name":"Opening Statements","round":1,"prompt":"State your position briefly."},{"name":"Vote","round":1,"prompt":"Cast your vote."}],
        default_duration=5,
    ),
    "deep_analysis": DeliberationTemplate(
        name="Deep Analysis",
        description="Three-round deep dive for complex strategic topics.",
        phases=[{"name":"Initial Findings","round":1,"prompt":"Share initial analysis and relevant data."},{"name":"Cross-Examination","round":2,"prompt":"Challenge or support other agents findings."},{"name":"Synthesis","round":3,"prompt":"Synthesize all perspectives and state final recommendation."}],
        default_duration=20,
    ),
    "technical_review": DeliberationTemplate(
        name="Technical Review",
        description="Two-round review for technical correctness, security, and architecture.",
        phases=[{"name":"Technical Assessment","round":1,"prompt":"Assess feasibility, security, and architecture."},{"name":"Recommendation","round":2,"prompt":"Provide your final recommendation."}],
        default_duration=15,
    ),
    "strategic_planning": DeliberationTemplate(
        name="Strategic Planning",
        description="Three-round strategic planning with risk assessment and roadmap.",
        phases=[{"name":"Situational Analysis","round":1,"prompt":"Analyze situation, risks, and opportunities."},{"name":"Resource Planning","round":2,"prompt":"Propose resource allocation and timeline."},{"name":"Final Strategy","round":3,"prompt":"Present final strategy with mitigation plans."}],
        default_duration=25,
    ),
    "crisis_response": DeliberationTemplate(
        name="Crisis Response",
        description="Rapid single-round response for urgent situations.",
        phases=[{"name":"Situation Assessment","round":1,"prompt":"Assess crisis severity and immediate actions."},{"name":"Action Plan","round":1,"prompt":"Propose immediate action steps."}],
        default_duration=5,
    ),
}

def list_templates() -> str:
    lines = ["### Deliberation Templates"]
    for name, t in DELIBERATION_TEMPLATES.items():
        ps = ", ".join(p["name"] for p in t.phases)
        lines.append(f"  \u2022 {t.name} ({t.default_duration}min)")
        lines.append(f"      {t.description}")
        lines.append(f"      Phases: {ps}")
    return "\n".join(lines)

def run_template(template_name: str, topic: str) -> str:
    template = DELIBERATION_TEMPLATES.get(template_name)
    if not template: return f"[FAIL] Unknown template: {template_name}"
    sid = start_session(topic)
    sessions = _load_json(_SESSIONS_FILE, [])
    for s in sessions:
        if s["session_id"] == sid:
            s["template"] = template_name
            _save_json(_SESSIONS_FILE, sessions)
            break
    for phase in template.phases:
        for agent in AGENT_ROLES:
            try:
                from friday.tools.ai_tools import model_query
                resp = model_query(
                    prompt=f"Topic: {topic}\nPhase: {phase["name"]}\n{phase["prompt"]}\n\nContribute as {agent}.",
                    system=f"You are {agent.upper()}, FRIDAY's {AGENT_ROLES[agent]}.",
                    model="opencode/big-pickle",
                )
                text = ""
                if isinstance(resp, dict):
                    text = resp.get("text","") or resp.get("response","") or resp.get("content","")
                else:
                    text = str(resp)
                post_message(sid, agent, f"[{phase["name"]}] {text.strip()[:300]}")
            except Exception as e:
                post_message(sid, agent, f"[{phase["name"]}] (unavailable: {e})")
    return sid

# ── Session Management ──

def start_session(topic: str, participants: Optional[list[str]] = None) -> str:
    _ensure_dirs()
    sessions = _load_json(_SESSIONS_FILE, [])
    session = {
        "session_id": uuid.uuid4().hex[:8],
        "topic": topic,
        "participants": participants or list(AGENT_ROLES.keys()),
        "started_at": _now_iso(),
        "status": SessionStatus.IN_PROGRESS.value,
        "messages": [], "outcomes": [], "agenda_items": [],
        "template": "", "tags": [],
    }
    session["messages"].append({"from": "townhall", "text": f"Town Hall session started. Topic: {topic}", "timestamp": _now_iso(), "type": MessageType.SYSTEM.value})
    sessions.append(session)
    _save_json(_SESSIONS_FILE, sessions)
    return session["session_id"]

def post_message(session_id: str, agent_name: str, message: str, msg_type: str = "") -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            entry = {"from": agent_name, "text": message, "timestamp": _now_iso(), "type": msg_type or MessageType.BROADCAST.value}
            session["messages"].append(entry)
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] {agent_name} posted to session {session_id[:8]}"
    return f"[FAIL] Session {session_id} not found"

def conclude_session(session_id: str, summary: str = "") -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            session["status"] = SessionStatus.COMPLETED.value
            session["completed_at"] = _now_iso()
            session["summary"] = summary or session.get("summary", "")
            _save_json(_SESSIONS_FILE, sessions)
            minutes_path = os.path.join(_MINUTES_DIR, f"minutes_{session_id}.json")
            with open(minutes_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, default=str)
            return f"[OK] Session {session_id[:8]} concluded."
    return f"[FAIL] Session {session_id} not found"

def get_session(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            lines = [f"### Town Hall Session: {session["topic"]} ({session["status"]})"]
            lines.append(f"ID: {session_id}")
            lines.append(f"Participants: {", ".join(session.get("participants",[]))}")
            lines.append(f"Started: {session.get("started_at","?")[:19]}")
            if session.get("template"): lines.append(f"Template: {session["template"]}")
            lines.append("")
            for msg in session.get("messages",[]):
                frm = msg.get("from","?")
                txt = msg.get("text","")[:200]
                ts = msg.get("timestamp","?")[11:19]
                lines.append(f"  [{ts}] <{frm}> {txt}")
            outcomes = session.get("outcomes",[])
            if outcomes:
                lines.append(f"\nOutcomes ({len(outcomes)}):")
                for o in outcomes: lines.append(f"  - {o[:200]}")
            return "\n".join(lines)
    return f"Session {session_id} not found."

def list_sessions(status: str = "") -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    if status: sessions = [s for s in sessions if s.get("status") == status]
    if not sessions: return "No sessions found."
    lines = [f"### Town Hall Sessions ({len(sessions)})"]
    for s in sessions:
        sid = s.get("session_id","?")[:8]
        topic = s.get("topic","?")[:50]
        icon = {"in_progress":"\u25d0","completed":"\u25cf","planned":"\u25cb","archived":"\ud83d\uddc2"}.get(s.get("status",""),"\u25cb")
        lines.append(f"  {icon} [{sid}] {topic} ({len(s.get("messages",[]))} msgs, {len(s.get("participants",[]))} agents)")
    return "\n".join(lines)

def cancel_session(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            if session["status"] == SessionStatus.COMPLETED.value: return f"[FAIL] Cannot cancel completed session."
            session["status"] = SessionStatus.CANCELLED.value
            session["cancelled_at"] = _now_iso()
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] Session {session_id[:8]} cancelled."
    return f"[FAIL] Session {session_id} not found"

# ── Session Persistence & History ──

def archive_session(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            if session["status"] != SessionStatus.COMPLETED.value: return f"[FAIL] Only completed sessions can be archived."
            session["status"] = SessionStatus.ARCHIVED.value
            archive_path = os.path.join(_ARCHIVE_DIR, f"session_{session_id}.json")
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, default=str)
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] Session {session_id[:8]} archived to {archive_path}"
    return f"[FAIL] Session {session_id} not found"

def search_sessions(query: str) -> str:
    q = query.lower()
    sessions = _load_json(_SESSIONS_FILE, [])
    if os.path.isdir(_ARCHIVE_DIR):
        for fname in os.listdir(_ARCHIVE_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(_ARCHIVE_DIR, fname), encoding="utf-8") as f:
                        sessions.append(json.load(f))
                except Exception: pass
    matches = []
    for s in sessions:
        score = 0
        if q in s.get("topic","").lower(): score += 3
        for p in s.get("participants",[]):
            if q in p.lower(): score += 2
        for msg in s.get("messages",[]):
            if q in msg.get("text","").lower(): score += 1
            if q in msg.get("from","").lower(): score += 2
        if score > 0: matches.append((score, s))
    matches.sort(key=lambda x: -x[0])
    if not matches: return f"No sessions match \"{query}\"."
    lines = [f"### Search Results for \"{query}\" ({len(matches)} matches)"]
    for score, s in matches[:20]:
        sid = s.get("session_id","?")[:8]
        topic = s.get("topic","?")[:60]
        lines.append(f"  [{s.get("status","?")}] [{sid}] {topic} ({len(s.get("messages",[]))} msgs, relevance: {score})")
    return "\n".join(lines)

def get_session_timeline(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session and os.path.isdir(_ARCHIVE_DIR):
        for fname in os.listdir(_ARCHIVE_DIR):
            if session_id in fname:
                try:
                    with open(os.path.join(_ARCHIVE_DIR, fname), encoding="utf-8") as f:
                        session = json.load(f)
                except Exception: pass
    if not session: return f"Session {session_id} not found."
    events = [("session_started", session.get("started_at",""), f"Session started: {session["topic"]}")]
    for msg in session.get("messages",[]):
        events.append((msg.get("type","message"), msg.get("timestamp",""), f"<{msg["from"]}> {msg["text"][:100]}"))
    if session.get("completed_at"): events.append(("session_completed", session["completed_at"], "Session completed"))
    events.sort(key=lambda x: x[1])
    lines = [f"### Timeline for Session {session_id[:8]}"]
    icons = {"session_started":"\ud83d\ude80","session_completed":"\u2705","system":"\ud83d\udd14","vote":"\ud83d\uddf3","proposal":"\ud83d\udccb","direct":"\ud83d\udce9"}
    for etype, ts, desc in events:
        t = ts[11:19] if ts else "??:??:??"
        lines.append(f"  {icons.get(etype,"\ud83d\udcac")} [{t}] {desc}")
    return "\n".join(lines)

def export_session_json(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            return json.dumps(session, indent=2, default=str)
    return "Session not found."

def export_session_markdown(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return "Session not found."
    lines = [f"# Town Hall Session: {session["topic"]}","",f"- **ID:** {session_id}",f"- **Status:** {session.get("status","?")}",f"- **Started:** {session.get("started_at","?")[:19]}",f"- **Participants:** {", ".join(session.get("participants",[]))}","",f"## Messages",""]
    for msg in session.get("messages",[]):
        ts = msg.get("timestamp","?")[11:19]
        lines.append(f"### [{ts}] {msg["from"]}")
        lines.extend(["", msg["text"], ""])
    if session.get("outcomes"):
        lines.append("## Outcomes")
        for o in session["outcomes"]: lines.append(f"- {o}")
    return "\n".join(lines)

def generate_daily_summary() -> str:
    today = _date_str()
    sessions = _load_json(_SESSIONS_FILE, [])
    today_sessions = [s for s in sessions if s.get("started_at","").startswith(today)]
    if not today_sessions: return f"No sessions recorded for {today}."
    total_msgs = sum(len(s.get("messages",[])) for s in today_sessions)
    total_outcomes = sum(len(s.get("outcomes",[])) for s in today_sessions)
    completed = sum(1 for s in today_sessions if s["status"] == SessionStatus.COMPLETED.value)
    in_progress = sum(1 for s in today_sessions if s["status"] == SessionStatus.IN_PROGRESS.value)
    lines = [f"## Daily Town Hall Summary - {today}","",f"- Sessions: {len(today_sessions)} ({completed} completed, {in_progress} in progress)",f"- Messages: {total_msgs}",f"- Outcomes: {total_outcomes}","","### Sessions"]
    for s in today_sessions:
        lines.append(f"- [{s["status"]}] {s.get("topic","?")[:60]} ({s.get("session_id","?")[:8]}, {len(s.get("messages",[]))} msgs)")
    content = "\n".join(lines)
    summary_path = os.path.join(_MINUTES_DIR, f"daily_{today}.md")
    with open(summary_path, "w", encoding="utf-8") as f: f.write(content)
    return content

# ── Agent Communication Patterns ──

def direct_message(from_agent: str, to_agent: str, message: str) -> str:
    if from_agent not in AGENT_ROLES and from_agent != "townhall": return f"[FAIL] Unknown sender: {from_agent}"
    if to_agent not in AGENT_ROLES and to_agent != "townhall": return f"[FAIL] Unknown recipient: {to_agent}"
    dms = _load_json(_DMS_FILE, {"direct_messages": []})
    dm = {"id": uuid.uuid4().hex[:8], "from": from_agent, "to": to_agent, "message": message, "timestamp": _now_iso(), "read": False}
    dms["direct_messages"].append(dm)
    _save_json(_DMS_FILE, dms)
    return f"[OK] DM sent from {from_agent} to {to_agent}"

def read_dms(agent_name: str, mark_read: bool = True) -> str:
    dms = _load_json(_DMS_FILE, {"direct_messages": []})
    agent_dms = [d for d in dms["direct_messages"] if d["to"] == agent_name]
    if not agent_dms: return f"No DMs for {agent_name}."
    unread = [d for d in agent_dms if not d.get("read")]
    lines = [f"### DMs for {agent_name} ({len(unread)} unread of {len(agent_dms)})"]
    for d in agent_dms:
        ts = d.get("timestamp","?")[11:19]
        tag = " (NEW)" if not d.get("read") else ""
        lines.append(f"  [{ts}] <{d["from"]}> {d["message"][:200]}{tag}")
        if mark_read: d["read"] = True
    if mark_read: _save_json(_DMS_FILE, dms)
    return "\n".join(lines)

def broadcast(agent_name: str, message: str, channel: str = "general") -> str:
    if agent_name not in AGENT_ROLES and agent_name != "townhall": return f"[FAIL] Unknown agent: {agent_name}"
    sessions = _load_json(_SESSIONS_FILE, [])
    active = [s for s in sessions if s["status"] == SessionStatus.IN_PROGRESS.value]
    if not active: return f"[OK] Broadcast sent but no active sessions."
    count = 0
    for s in active:
        s["messages"].append({"from": agent_name, "text": f"[Broadcast-{channel}] {message}", "timestamp": _now_iso(), "type": MessageType.BROADCAST.value})
        count += 1
    _save_json(_SESSIONS_FILE, sessions)
    return f"[OK] {agent_name} broadcast to {count} active session(s)"

# ── Debate System ──

class DebateRound:
    def __init__(self, debate_id: str, round_number: int):
        self.debate_id = debate_id
        self.round_number = round_number
        self.arguments: list[dict[str, Any]] = []
        self.started_at = _now_iso()
    def add_argument(self, agent, position, argument):
        entry = {"agent": agent, "position": position, "argument": argument, "timestamp": _now_iso()}
        self.arguments.append(entry)
        return entry
    def to_dict(self):
        return {"round_number": self.round_number, "arguments": self.arguments, "started_at": self.started_at}

def start_debate(session_id: str, motion: str, proposer: str, opposer: str) -> str:
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    debate = {
        "id": uuid.uuid4().hex[:8], "session_id": session_id,
        "motion": motion, "proposer": proposer, "opposer": opposer,
        "status": "active", "rounds": [], "current_round": 0,
        "created_at": _now_iso(), "resolution": "",
    }
    debates["debates"].append(debate)
    _save_json(_DEBATES_FILE, debates)
    return f"[OK] Debate started on \"{motion[:60]}\" ({debate["id"]})"

def add_argument(debate_id: str, agent: str, position: str, argument: str) -> str:
    position = position.upper()
    if position not in ("FOR","AGAINST","NEUTRAL"): return f"[FAIL] Position must be FOR, AGAINST, or NEUTRAL"
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    for debate in debates["debates"]:
        if debate["id"] == debate_id:
            if debate["status"] != "active": return f"[FAIL] Debate not active ({debate["status"]})"
            if debate.get("current_round", 0) == 0:
                debate["rounds"].append({"round_number": 1, "arguments": [], "started_at": _now_iso()})
                debate["current_round"] = 1
            round_data = debate["rounds"][-1]
            round_data["arguments"].append({"agent": agent, "position": position, "argument": argument, "timestamp": _now_iso()})
            debate["updated_at"] = _now_iso()
            _save_json(_DEBATES_FILE, debates)
            return f"[OK] {agent} added {position} argument"
    return f"[FAIL] Debate {debate_id} not found"

def close_debate(debate_id: str, resolution: str = "") -> str:
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    for debate in debates["debates"]:
        if debate["id"] == debate_id:
            if debate["status"] != "active": return f"[FAIL] Debate already {debate["status"]}"
            debate["status"] = "closed"
            debate["resolution"] = resolution
            debate["closed_at"] = _now_iso()
            fcnt = acnt = ncnt = 0
            for rd in debate.get("rounds",[]):
                for arg in rd.get("arguments",[]):
                    if arg["position"] == "FOR": fcnt += 1
                    elif arg["position"] == "AGAINST": acnt += 1
                    else: ncnt += 1
            debate["statistics"] = {"for": fcnt, "against": acnt, "neutral": ncnt, "total_rounds": len(debate.get("rounds",[])), "total_arguments": fcnt+acnt+ncnt}
            _save_json(_DEBATES_FILE, debates)
            return f"[OK] Debate {debate_id[:8]} closed. FOR: {fcnt}, AGAINST: {acnt}"
    return f"[FAIL] Debate {debate_id} not found"

def list_debates(session_id: str = "") -> str:
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    items = debates["debates"]
    if session_id: items = [d for d in items if d["session_id"] == session_id]
    if not items: return "No debates found."
    lines = [f"### Debates ({len(items)})"]
    for d in items:
        icon = "\u2696\ufe0f" if d["status"]=="active" else "\u2705"
        lines.append(f"  {icon} [{d["id"][:8]}] {d.get("motion","?")[:50]} ({d["status"]}, {len(d.get("rounds",[]))} rounds)")
    return "\n".join(lines)

# ── Escalation ──

def escalate_to_human(session_id: str, issue: str, agent_name: str = "") -> str:
    escalations = _load_json(_ESCALATIONS_FILE, {"escalations": []})
    esc = {"id": uuid.uuid4().hex[:8], "session_id": session_id, "issue": issue, "agent_name": agent_name or "unknown", "status": "pending", "created_at": _now_iso(), "resolved_at": "", "resolution": ""}
    escalations["escalations"].append(esc)
    _save_json(_ESCALATIONS_FILE, escalations)
    return f"[OK] Escalated: {issue[:100]} ({esc["id"]})"

def escalation_queue(status: str = "pending") -> str:
    escalations = _load_json(_ESCALATIONS_FILE, {"escalations": []})
    items = escalations["escalations"]
    if status: items = [e for e in items if e["status"] == status]
    if not items: return "No escalations."
    lines = [f"### Escalations ({len(items)})"]
    for e in items:
        ts = e.get("created_at","?")[11:19]
        icon = {"pending":"\u23f3","resolved":"\u2705","rejected":"\u274c"}.get(e["status"],"\u2753")
        lines.append(f"  {icon} [{e["id"][:8]}] from {e.get("session_id","?")[:8]} at {ts}")
        lines.append(f"      {e["issue"][:120]}")
    return "\n".join(lines)

def resolve_escalation(escalation_id: str, resolution: str) -> str:
    escalations = _load_json(_ESCALATIONS_FILE, {"escalations": []})
    for e in escalations["escalations"]:
        if e["id"] == escalation_id:
            e["status"] = "resolved"; e["resolution"] = resolution; e["resolved_at"] = _now_iso()
            _save_json(_ESCALATIONS_FILE, escalations)
            return f"[OK] Escalation {escalation_id[:8]} resolved."
    return f"[FAIL] Escalation {escalation_id} not found"

def check_auto_escalation(session_id: str, max_rounds: int = 3) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    msg_count = len(session.get("messages",[]))
    if msg_count >= max_rounds * len(AGENT_ROLES):
        votes = _load_json(_VOTES_FILE, {"votes": []})
        sv = [v for v in votes["votes"] if v["session_id"] == session_id]
        if sv:
            approve = sum(1 for v in sv if v["vote"]=="approve")
            reject = sum(1 for v in sv if v["vote"]=="reject")
            if approve <= reject:
                escalate_to_human(session_id, f"Auto-escalation: No consensus after {msg_count} messages.", agent_name="townhall")
                return f"[OK] Auto-escalation triggered for session {session_id[:8]}"
    return f"[OK] Session {session_id[:8]} within limits ({msg_count} msgs)"

# ── Outcome Tracking ──

class OutcomeTracker:
    def __init__(self):
        self._lock = threading.Lock()

    def record_outcome(self, session_id, description, agenda_item_id="", decision="") -> str:
        outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
        o = {"id": uuid.uuid4().hex[:8], "session_id": session_id, "description": description, "agenda_item_id": agenda_item_id, "decision": decision or description, "status": "decided", "implementation_status": "pending", "recorded_at": _now_iso(), "implemented_at": ""}
        outcomes["outcomes"].append(o)
        _save_json(_OUTCOMES_FILE, outcomes)
        return o["id"]

    def update_implementation_status(self, outcome_id: str, status: str) -> str:
        outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
        for o in outcomes["outcomes"]:
            if o["id"] == outcome_id:
                o["implementation_status"] = status
                if status == "implemented": o["implemented_at"] = _now_iso()
                _save_json(_OUTCOMES_FILE, outcomes)
                return f"[OK] Outcome {outcome_id[:8]} status: {status}"
        return f"[FAIL] Outcome {outcome_id} not found"

    def link_to_agenda(self, outcome_id: str, agenda_item_id: str) -> str:
        outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
        for o in outcomes["outcomes"]:
            if o["id"] == outcome_id:
                o["agenda_item_id"] = agenda_item_id
                _save_json(_OUTCOMES_FILE, outcomes)
                return f"[OK] Linked outcome {outcome_id[:8]} to agenda {agenda_item_id[:8]}"
        return f"[FAIL] Outcome {outcome_id} not found"

    def get_outcome_stats(self) -> str:
        outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
        items = outcomes["outcomes"]
        if not items: return "No outcomes recorded."
        total = len(items)
        by_status = {}; by_impl = {}
        for o in items:
            s = o.get("status","unknown"); by_status[s] = by_status.get(s,0)+1
            i = o.get("implementation_status","unknown"); by_impl[i] = by_impl.get(i,0)+1
        linked = sum(1 for o in items if o.get("agenda_item_id"))
        lines = ["### Outcome Statistics", "", f"Total: {total}", f"Linked to agenda: {linked}", "", "By status:"]
        for s, c in sorted(by_status.items()): lines.append(f"  {s}: {c}")
        lines.extend(["", "By implementation:"])
        for s, c in sorted(by_impl.items()): lines.append(f"  {s}: {c} ({round(c/total*100,1) if total>0 else 0}%)")
        return "\n".join(lines)

    def list_outcomes(self, session_id: str = "") -> str:
        outcomes = _load_json(_OUTCOMES_FILE, {"outcomes": []})
        items = outcomes["outcomes"]
        if session_id: items = [o for o in items if o["session_id"] == session_id]
        if not items: return "No outcomes found."
        icons = {"pending":"\u23f3","in_progress":"\ud83d\udd28","implemented":"\u2705","blocked":"\u26d4"}
        lines = [f"### Outcomes ({len(items)})"]
        for o in items:
            icon = icons.get(o.get("implementation_status",""),"\u2753")
            lines.append(f"  {icon} [{o["id"][:8]}] {o["description"][:80]}")
            lines.append(f"      Session: {o.get("session_id","?")[:8]} | {o.get("status","?")} | Impl: {o.get("implementation_status","?")}")
        return "\n".join(lines)


_outcome_tracker: Optional[OutcomeTracker] = None

def get_outcome_tracker() -> OutcomeTracker:
    global _outcome_tracker
    if _outcome_tracker is None:
        _outcome_tracker = OutcomeTracker()
    return _outcome_tracker

# ── Action Items ──

def create_action_item(session_id: str, description: str, assignee: str, deadline: str = "") -> str:
    actions = _load_json(_ACTIONS_FILE, {"actions": []})
    a = {"id": uuid.uuid4().hex[:8], "session_id": session_id, "description": description, "assignee": assignee, "status": "open", "deadline": deadline, "created_at": _now_iso(), "completed_at": "", "notes": ""}
    actions["actions"].append(a)
    _save_json(_ACTIONS_FILE, actions)
    return f"[OK] Action for {assignee}: {description[:80]} ({a["id"]})"

def update_action_item_status(item_id: str, status: str) -> str:
    actions = _load_json(_ACTIONS_FILE, {"actions": []})
    for a in actions["actions"]:
        if a["id"] == item_id:
            a["status"] = status
            if status == "completed": a["completed_at"] = _now_iso()
            a["updated_at"] = _now_iso()
            _save_json(_ACTIONS_FILE, actions)
            return f"[OK] Action {item_id[:8]} status: {status}"
    return f"[FAIL] Action {item_id} not found"

def list_action_items(agent_name: str = "") -> str:
    actions = _load_json(_ACTIONS_FILE, {"actions": []})
    items = actions["actions"]
    if agent_name: items = [a for a in items if a["assignee"] == agent_name]
    if not items: return "No action items."
    open_i = [a for a in items if a["status"]=="open"]
    ip_i = [a for a in items if a["status"]=="in_progress"]
    done_i = [a for a in items if a["status"]=="completed"]
    lines = [f"### Actions ({len(items)})"]
    if open_i:
        lines.append(f"\nOpen ({len(open_i)}):")
        for a in open_i:
            d = f" due {a["deadline"]}" if a.get("deadline") else ""
            lines.append(f"  \u25cb [{a["id"][:8]}] {a["description"][:80]} \u2192 {a["assignee"]}{d}")
    if ip_i:
        lines.append(f"\nIn Progress ({len(ip_i)}):")
        for a in ip_i: lines.append(f"  \ud83d\udd28 [{a["id"][:8]}] {a["description"][:80]} \u2192 {a["assignee"]}")
    if done_i:
        lines.append(f"\nCompleted ({len(done_i)}):")
        for a in done_i[:5]: lines.append(f"  \u2705 [{a["id"][:8]}] {a["description"][:80]}")
        if len(done_i) > 5: lines.append(f"  ... and {len(done_i)-5} more")
    return "\n".join(lines)

def auto_create_actions(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    summary = session.get("summary","")
    if not summary: return "No summary available."
    import re
    keywords = ["will","should","must","needs to","responsible for","tasked with"]
    created = 0
    for kw in keywords:
        for part in summary.split("."):
            if kw in part.lower():
                m = re.search("\\b("+"|".join(AGENT_ROLES.keys())+")\\b", part.lower())
                assignee = m.group(0) if m else "unassigned"
                desc = part.strip()[:150]
                if desc: create_action_item(session_id, desc, assignee); created += 1
    return f"[OK] Created {created} action items."

# ── Meeting Scheduling ──

def schedule_session(topic: str, participants: Optional[list[str]] = None, time_str: str = "") -> str:
    schedule = _load_json(_SCHEDULE_FILE, {"sessions": []})
    parsed_time = _now_iso()
    if time_str:
        try: parsed_time = datetime.fromisoformat(time_str).isoformat()
        except ValueError:
            try: parsed_time = (datetime.now() + timedelta(hours=float(time_str))).isoformat()
            except: parsed_time = time_str
    s = {"id": uuid.uuid4().hex[:8], "topic": topic, "participants": participants or list(AGENT_ROLES.keys()), "scheduled_time": parsed_time, "status": "scheduled", "created_at": _now_iso(), "session_id": ""}
    schedule["sessions"].append(s)
    _save_json(_SCHEDULE_FILE, schedule)
    return f"[OK] Scheduled: \"{topic}\" at {parsed_time[:19]} ({s["id"]})"

def reschedule_session(schedule_id: str, time_str: str) -> str:
    schedule = _load_json(_SCHEDULE_FILE, {"sessions": []})
    for s in schedule["sessions"]:
        if s["id"] == schedule_id:
            try: s["scheduled_time"] = datetime.fromisoformat(time_str).isoformat()
            except: return f"[FAIL] Invalid time: {time_str}"
            s["updated_at"] = _now_iso()
            _save_json(_SCHEDULE_FILE, schedule)
            return f"[OK] Rescheduled to {s["scheduled_time"][:19]}"
    return f"[FAIL] Schedule {schedule_id} not found"

def get_schedule() -> str:
    schedule = _load_json(_SCHEDULE_FILE, {"sessions": []})
    items = schedule["sessions"]
    if not items: return "No scheduled sessions."
    now = _now_iso()
    upcoming = [s for s in items if s.get("scheduled_time","") >= now and s["status"]=="scheduled"]
    past = [s for s in items if s.get("scheduled_time","") < now or s["status"]!="scheduled"]
    lines = ["### Scheduled Sessions"]
    if upcoming:
        lines.append(f"\nUpcoming ({len(upcoming)}):")
        for s in sorted(upcoming, key=lambda x: x.get("scheduled_time","")):
            lines.append(f"  \ud83d\udcc5 [{s["id"][:8]}] {s.get("topic","?")[:50]} at {s.get("scheduled_time","?")[:19]}")
    if past:
        lines.append(f"\nPast ({len(past)}):")
        for s in past[:5]: lines.append(f"  [{s.get("status","?")}] {s.get("topic","?")[:40]} at {s.get("scheduled_time","?")[:19]}")
        if len(past) > 5: lines.append(f"  ... and {len(past)-5} more")
    return "\n".join(lines)

# ── Summarization Engine ──

def summarize_session(session_id: str, max_length: int = 500) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    if session.get("summary") and len(session["summary"]) <= max_length: return session["summary"]
    lines = [f"Summary: {session["topic"]} ({session_id[:8]})", f"Status: {session["status"]}"]
    agent_msgs = {}
    for msg in session.get("messages",[]):
        a = msg.get("from","?")
        if a != "townhall": agent_msgs[a] = agent_msgs.get(a, 0) + 1
    if agent_msgs:
        lines.append("")
        for a, c in sorted(agent_msgs.items(), key=lambda x: -x[1]): lines.append(f"  {a}: {c} msgs")
    result = "\n".join(lines)
    return result[:max_length] + "..." if len(result) > max_length else result

def extract_key_decisions(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    decisions = session.get("outcomes",[])
    votes = _load_json(_VOTES_FILE, {"votes": []})
    sv = [v for v in votes["votes"] if v["session_id"] == session_id]
    lines = [f"Key Decisions: {session["topic"]}"]
    if decisions:
        lines.append(f"\nOutcomes ({len(decisions)}):")
        for d in decisions: lines.append(f"  - {d[:200]}")
    else: lines.append("\nNo formal outcomes.")
    if sv:
        app = sum(1 for v in sv if v["vote"]=="approve")
        rej = sum(1 for v in sv if v["vote"]=="reject")
        abst = sum(1 for v in sv if v["vote"]=="abstain")
        blk = sum(1 for v in sv if v["vote"]=="block")
        lines.append(f"\nVotes: {app} approve, {rej} reject, {abst} abstain, {blk} block")
    return "\n".join(lines)

def generate_minutes(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    lines = ["# Meeting Minutes", "", f"## Session: {session["topic"]}", "", f"- **Date:** {session.get("started_at","?")[:10]}", f"- **Time:** {session.get("started_at","?")[11:19]}", f"- **Status:** {session.get("status","?")}", "- **ID:** "+session_id[:8], "", "## Participants", ""]
    for p in session.get("participants",[]):
        role = AGENT_ROLES.get(p,"")
        lines.append(f"- {p.capitalize()}{" - "+role if role else ""}")
    lines.extend(["", "## Agenda", "", f"1. {session["topic"]}", "", "## Discussion", ""])
    for msg in session.get("messages",[]):
        ts = msg.get("timestamp","?")[11:19]
        for line in msg.get("text","").split("\n"):
            if line.strip(): lines.append(f"**{msg["from"]}** ({ts}): {line.strip()[:200]}")
    lines.extend(["", "## Decisions", ""])
    outcomes = session.get("outcomes",[])
    if outcomes:
        for o in outcomes: lines.append(f"- {o[:200]}")
    else: lines.append("No formal decisions.")
    content = "\n".join(lines)
    mp = os.path.join(_MINUTES_DIR, f"minutes_{session_id}.md")
    with open(mp, "w", encoding="utf-8") as f: f.write(content)
    return content

# ── Conflict Resolution ──

def detect_conflict(session_id: str, agent_a: str, agent_b: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    msgs_a = [m for m in session.get("messages",[]) if m.get("from","").lower() == agent_a.lower()]
    msgs_b = [m for m in session.get("messages",[]) if m.get("from","").lower() == agent_b.lower()]
    if not msgs_a: return f"No messages from {agent_a}."
    if not msgs_b: return f"No messages from {agent_b}."
    kw = ["disagree","incorrect","wrong","dispute","reject","oppose","against","no","cannot","should not","must not","unacceptable","flawed"]
    lines = [f"### Conflict: {agent_a} vs {agent_b}"]
    found = 0
    for mb in msgs_b:
        if any(k in mb.get("text","").lower() for k in kw):
            found += 1
            lines.append(f"  \u26a1 [{mb.get("timestamp","?")[11:19]}] {agent_b}: \"{mb["text"][:120]}\"")
    for ma in msgs_a:
        if any(k in ma.get("text","").lower() for k in kw):
            found += 1
            lines.append(f"  \u26a1 [{ma.get("timestamp","?")[11:19]}] {agent_a}: \"{ma["text"][:120]}\"")
    if found == 0: lines.append(f"  No direct conflicts detected.")
    else: lines.append(f"\nConflict indicators: {found}")
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    rd = [d for d in debates["debates"] if d["session_id"]==session_id and agent_a in (d.get("proposer",""),d.get("opposer","")) and agent_b in (d.get("proposer",""),d.get("opposer",""))]
    if rd:
        lines.append("\nActive debates:")
        for d in rd: lines.append(f"  \u2696\ufe0f {d["motion"][:80]} ({d["id"][:8]})")
    return "\n".join(lines)

def mediate_conflict(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    session = None
    for s in sessions:
        if s["session_id"] == session_id: session = s; break
    if not session: return f"Session {session_id} not found."
    agents = session.get("participants",[])
    msgs = session.get("messages",[])
    if not msgs: return "No messages to mediate."
    positions = {}
    for msg in msgs:
        a = msg.get("from","")
        if a in AGENT_ROLES:
            positions.setdefault(a, []).append(msg.get("text",""))
    kw = ["disagree","incorrect","wrong","dispute","reject","oppose","no","cannot","should not","must not"]
    graph = []
    for a1 in agents:
        for a2 in agents:
            if a1 >= a2: continue
            t = (" ".join(positions.get(a1,[])) + " " + " ".join(positions.get(a2,[]))).lower()
            c = sum(1 for k in kw if k in t)
            if c > 0: graph.append((a1, a2, c))
    if not graph: return f"No conflicts detected in {session_id[:8]}."
    graph.sort(key=lambda x: -x[2])
    lines = [f"### Mediation: {session["topic"]}"]
    for a1, a2, score in graph[:3]:
        lines.extend(["", f"\u2696\ufe0f {a1} vs {a2} (intensity: {score})", f"  {a1}: \"{" ".join(positions.get(a1,[]))[:200]}\"", f"  {a2}: \"{" ".join(positions.get(a2,[]))[:200]}\"", "  \ud83e\udd1d Compromise: find common ground, consider phased approach, escalate if needed"])
    post_message(session_id, "townhall", f"[Mediation] Identified {len(graph)} conflict pair(s).", msg_type="system")
    return "\n".join(lines)

# ── Autonomous Deliberation ──

def auto_deliberate(topic: str, rounds: int = 2) -> str:
    sid = start_session(topic, participants=list(AGENT_ROLES.keys()))
    for round_num in range(1, rounds + 1):
        for agent, role_desc in AGENT_ROLES.items():
            try:
                from friday.tools.ai_tools import model_query
                prompt = (
                    f"You are {agent.upper()}, FRIDAY's {role_desc}.\n"
                    f"Topic: {topic}\n"
                    f"Round {round_num}/{rounds}\n"
                    f"Contribute your perspective as {agent}. Be concise. "
                    f"Focus on what YOUR expertise brings to this topic."
                )
                response = model_query(
                    prompt=prompt,
                    system=f"You are {agent.upper()}, FRIDAY's {role_desc}. Respond in character.",
                    model="opencode/big-pickle",
                )
                text = ""
                if isinstance(response, dict):
                    text = response.get("text","") or response.get("response","") or response.get("content","")
                else:
                    text = str(response)
                post_message(sid, agent, text.strip())
            except Exception as e:
                post_message(sid, agent, f"(unavailable: {e})")
    summary_prompt = f"Summarize the town hall deliberation on \"{topic}\". Extract key decisions, action items, and consensus points."
    try:
        from friday.tools.ai_tools import model_query
        summary_resp = model_query(prompt=summary_prompt, system="You are a meeting scribe.", model="opencode/big-pickle")
        summary = ""
        if isinstance(summary_resp, dict):
            summary = summary_resp.get("text","") or summary_resp.get("response","") or summary_resp.get("content","")
        else: summary = str(summary_resp)
    except Exception:
        summary = "Deliberation completed."
    conclude_session(sid, summary=summary)
    auto_create_actions(sid)
    return get_session(sid)

# ── Tool Dispatcher ──


# ── Session Audit & Notifications ──

class SessionAudit:
    """Records and tracks all changes made during town hall sessions.
    Provides an immutable log of who did what and when,
    enabling full accountability and replay capability.
    """

    def __init__(self):
        self._lock = threading.Lock()

    def log_event(self, session_id: str, agent: str, event_type: str, details: str) -> str:
        """Record an audit event with timestamp and details."""
        audit = _load_json(os.path.join(_TOWNHALL_DIR, "audit.json"), {"events": []})
        event = {
            "id": uuid.uuid4().hex[:8],
            "session_id": session_id,
            "agent": agent,
            "event_type": event_type,
            "details": details,
            "timestamp": _now_iso(),
        }
        audit["events"].append(event)
        _save_json(os.path.join(_TOWNHALL_DIR, "audit.json"), audit)
        return event["id"]

    def get_session_audit(self, session_id: str) -> str:
        """Retrieve audit trail for a specific session."""
        audit = _load_json(os.path.join(_TOWNHALL_DIR, "audit.json"), {"events": []})
        events = [e for e in audit["events"] if e["session_id"] == session_id]
        if not events: return f"No audit events for session {session_id[:8]}."
        lines = [f"### Audit Log for Session {session_id[:8]} ({len(events)} events)"]
        for e in events:
            ts = e.get("timestamp","?")[11:19]
            lines.append(f"  [{ts}] {e["agent"]} - {e["event_type"]}: {e["details"][:100]}")
        return "\n".join(lines)

    def get_agent_audit(self, agent_name: str) -> str:
        """Retrieve all audit events for a specific agent."""
        audit = _load_json(os.path.join(_TOWNHALL_DIR, "audit.json"), {"events": []})
        events = [e for e in audit["events"] if e["agent"].lower() == agent_name.lower()]
        if not events: return f"No audit events for {agent_name}."
        lines = [f"### Audit Log for {agent_name} ({len(events)} events)"]
        for e in events:
            ts = e.get("timestamp","?")[11:19]
            sid = e.get("session_id","?")[:8]
            lines.append(f"  [{ts}] session {sid} - {e["event_type"]}: {e["details"][:100]}")
        return "\n".join(lines)


def get_audit() -> SessionAudit:
    return SessionAudit()


# ── Notification Manager ──

class NotificationManager:
    """Manages agent-facing notifications for events requiring attention.
    Supports priority levels and read/unread tracking.
    """

    def __init__(self):
        self._notifications_file = os.path.join(_TOWNHALL_DIR, "notifications.json")

    def send_notification(self, to_agent: str, subject: str, message: str, priority: str = "normal") -> str:
        """Send a notification to an agent."""
        notifs = _load_json(self._notifications_file, {"notifications": []})
        n = {
            "id": uuid.uuid4().hex[:8],
            "to_agent": to_agent,
            "subject": subject,
            "message": message,
            "priority": priority,
            "read": False,
            "created_at": _now_iso(),
            "read_at": "",
        }
        notifs["notifications"].append(n)
        _save_json(self._notifications_file, notifs)
        return n["id"]

    def get_notifications(self, agent_name: str, unread_only: bool = True) -> str:
        """Get notifications for a specific agent."""
        notifs = _load_json(self._notifications_file, {"notifications": []})
        items = [n for n in notifs["notifications"] if n["to_agent"].lower() == agent_name.lower()]
        if unread_only:
            items = [n for n in items if not n.get("read")]
        if not items: return f"No notifications for {agent_name}."
        lines = [f"### Notifications for {agent_name} ({len(items)})"]
        for n in items:
            icon = {"high": "🔴", "normal": "🔵", "low": "⚪"}.get(n.get("priority","normal"), "🔵")
            ts = n.get("created_at","?")[11:19]
            lines.append(f"  {icon} [{ts}] {n["subject"][:60]}")
            lines.append(f"      {n["message"][:120]}")
        return "\n".join(lines)

    def mark_read(self, notification_id: str) -> str:
        """Mark a notification as read."""
        notifs = _load_json(self._notifications_file, {"notifications": []})
        for n in notifs["notifications"]:
            if n["id"] == notification_id:
                n["read"] = True
                n["read_at"] = _now_iso()
                _save_json(self._notifications_file, notifs)
                return f"[OK] Notification {notification_id[:8]} marked read."
        return f"[FAIL] Notification {notification_id} not found"

    def clear_all(self, agent_name: str) -> str:
        """Clear all notifications for an agent."""
        notifs = _load_json(self._notifications_file, {"notifications": []})
        before = len(notifs["notifications"])
        notifs["notifications"] = [n for n in notifs["notifications"] if n["to_agent"].lower() != agent_name.lower()]
        after = len(notifs["notifications"])
        _save_json(self._notifications_file, notifs)
        return f"[OK] Cleared {before - after} notifications for {agent_name}."


def get_notification_manager() -> NotificationManager:
    return NotificationManager()


# ── Report Generator ──

class ReportGenerator:
    """Generates comprehensive reports from session data.
    Supports multiple output formats including text, JSON, and structured summaries.
    """

    def generate_session_report(self, session_id: str, include_messages: bool = True) -> str:
        """Generate a comprehensive report for a session."""
        sessions = _load_json(_SESSIONS_FILE, [])
        session = None
        for s in sessions:
            if s["session_id"] == session_id:
                session = s
                break
        if not session: return f"Session {session_id} not found."
        lines = [
            "=" * 60,
            f"TOWN HALL SESSION REPORT",
            "=" * 60,
            f"",
            f"Session ID: {session_id}",
            f"Topic: {session.get("topic","?")}",
            f"Status: {session.get("status","?")}",
            f"Started: {session.get("started_at","?")[:19]}",
            f"Duration: {session.get("completed_at",_now_iso())[:19]}",
            f"Participants: {len(session.get("participants",[]))}",
            f"Total Messages: {len(session.get("messages",[]))}",
            f"",
            f"PARTICIPANTS",
            "-" * 40,
        ]
        for p in session.get("participants",[]):
            role = AGENT_ROLES.get(p, "")
            msg_count = sum(1 for m in session.get("messages",[]) if m.get("from","") == p)
            lines.append(f"  {p.capitalize()} - {role[:50]} ({msg_count} messages)")
        if include_messages and session.get("messages"):
            lines.extend(["", "MESSAGE LOG", "-" * 40])
            for msg in session.get("messages",[]):
                ts = msg.get("timestamp","?")[11:19]
                lines.append(f"  [{ts}] <{msg["from"]}> {msg["text"][:150]}")
        outcomes = session.get("outcomes",[])
        if outcomes:
            lines.extend(["", "OUTCOMES", "-" * 40])
            for o in outcomes:
                lines.append(f"  - {o[:200]}")
        lines.extend(["", "=" * 60, "END OF REPORT", "=" * 60])
        return "\n".join(lines)

    def generate_summary_report(self) -> str:
        """Generate a summary report across all sessions."""
        sessions = _load_json(_SESSIONS_FILE, [])
        if not sessions: return "No sessions to report."
        total = len(sessions)
        completed = sum(1 for s in sessions if s["status"] == SessionStatus.COMPLETED.value)
        active = sum(1 for s in sessions if s["status"] == SessionStatus.IN_PROGRESS.value)
        total_msgs = sum(len(s.get("messages",[])) for s in sessions)
        total_outcomes = sum(len(s.get("outcomes",[])) for s in sessions)
        agent_msg_count = {}
        for s in sessions:
            for msg in s.get("messages",[]):
                a = msg.get("from","")
                if a in AGENT_ROLES:
                    agent_msg_count[a] = agent_msg_count.get(a, 0) + 1
        most_active = sorted(agent_msg_count.items(), key=lambda x: -x[1])[:3]
        lines = [
            "=" * 60,
            "TOWN HALL SUMMARY REPORT",
            "=" * 60,
            f"",
            f"Total Sessions: {total}",
            f"Completed: {completed}",
            f"Active: {active}",
            f"Total Messages: {total_msgs}",
            f"Total Outcomes: {total_outcomes}",
            f"",
            f"MOST ACTIVE AGENTS",
            "-" * 40,
        ]
        for agent, count in most_active:
            lines.append(f"  {agent.capitalize()}: {count} messages")
        lines.extend(["", "=" * 60, "END OF REPORT", "=" * 60])
        return "\n".join(lines)


def get_report_generator() -> ReportGenerator:
    return ReportGenerator()



# ── Tag Management ──

def add_tag_to_session(session_id: str, tag: str) -> str:
    """Add a tag to a session for categorization and filtering."""
    sessions = _load_json(_SESSIONS_FILE, [])
    for s in sessions:
        if s["session_id"] == session_id:
            if "tags" not in s:
                s["tags"] = []
            if tag not in s["tags"]:
                s["tags"].append(tag)
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] Tag '{tag}' added to session {session_id[:8]}"
    return f"[FAIL] Session {session_id} not found"


def remove_tag_from_session(session_id: str, tag: str) -> str:
    """Remove a tag from a session."""
    sessions = _load_json(_SESSIONS_FILE, [])
    for s in sessions:
        if s["session_id"] == session_id:
            if "tags" in s and tag in s["tags"]:
                s["tags"].remove(tag)
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] Tag '{tag}' removed from session {session_id[:8]}"
    return f"[FAIL] Session {session_id} not found"


def list_tags() -> str:
    """List all tags used across sessions with counts."""
    sessions = _load_json(_SESSIONS_FILE, [])
    tag_counts = {}
    for s in sessions:
        for t in s.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    if not tag_counts:
        return "No tags in use."
    lines = [f"### Tags ({len(tag_counts)})"]
    for t, c in sorted(tag_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  • {t}: {c} session(s)")
    return "\n".join(lines)


def find_sessions_by_tag(tag: str) -> str:
    """Find all sessions with a specific tag."""
    sessions = _load_json(_SESSIONS_FILE, [])
    matches = [s for s in sessions if tag in s.get("tags", [])]
    if not matches:
        return f"No sessions tagged with '{tag}'."
    lines = [f"### Sessions tagged '{tag}' ({len(matches)})"]
    for s in matches:
        sid = s.get("session_id", "?")[:8]
        topic = s.get("topic", "?")[:50]
        lines.append(f"  [{s.get('status','?')}] [{sid}] {topic}")
    return "\n".join(lines)


# ── Session Stats ──

def get_session_statistics() -> str:
    """Get comprehensive statistics about all town hall activity."""
    sessions = _load_json(_SESSIONS_FILE, [])
    agenda = _load_json(_AGENDA_FILE, {"items": []})
    proposals = _load_json(_PROPOSALS_FILE, {"proposals": []})
    votes = _load_json(_VOTES_FILE, {"votes": []})
    actions = _load_json(_ACTIONS_FILE, {"actions": []})
    debates = _load_json(_DEBATES_FILE, {"debates": []})
    escalations = _load_json(_ESCALATIONS_FILE, {"escalations": []})

    total_sessions = len(sessions)
    total_msgs = sum(len(s.get("messages", [])) for s in sessions)
    total_participants = sum(len(s.get("participants", [])) for s in sessions)

    lines = [
        "=" * 60,
        "TOWN HALL STATISTICS",
        "=" * 60,
        "",
        f"Sessions: {total_sessions}",
        f"  Active: {sum(1 for s in sessions if s['status']==SessionStatus.IN_PROGRESS.value)}",
        f"  Completed: {sum(1 for s in sessions if s['status']==SessionStatus.COMPLETED.value)}",
        f"  Archived: {sum(1 for s in sessions if s['status']==SessionStatus.ARCHIVED.value)}",
        f"  Cancelled: {sum(1 for s in sessions if s['status']==SessionStatus.CANCELLED.value)}",
        "",
        f"Messages: {total_msgs}",
        f"Average messages per session: {total_msgs/max(total_sessions,1):.1f}",
        f"Average participants per session: {total_participants/max(total_sessions,1):.1f}",
        "",
        f"Agenda Items: {len(agenda.get('items',[]))}",
        f"  Open: {sum(1 for i in agenda.get('items',[]) if i.get('status')=='open')}",
        f"  Resolved: {sum(1 for i in agenda.get('items',[]) if i.get('status')=='resolved')}",
        "",
        f"Proposals: {len(proposals.get('proposals',[]))}",
        f"Votes Cast: {len(votes.get('votes',[]))}",
        f"Action Items: {len(actions.get('actions',[]))}",
        f"  Open: {sum(1 for a in actions.get('actions',[]) if a.get('status')=='open')}",
        f"  Completed: {sum(1 for a in actions.get('actions',[]) if a.get('status')=='completed')}",
        "",
        f"Debates: {len(debates.get('debates',[]))}",
        f"  Active: {sum(1 for d in debates.get('debates',[]) if d['status']=='active')}",
        f"  Closed: {sum(1 for d in debates.get('debates',[]) if d['status']=='closed')}",
        "",
        f"Escalations: {len(escalations.get('escalations',[]))}",
        f"  Pending: {sum(1 for e in escalations.get('escalations',[]) if e['status']=='pending')}",
        f"  Resolved: {sum(1 for e in escalations.get('escalations',[]) if e['status']=='resolved')}",
        "",
        "=" * 60,
    ]
    return "\n".join(lines)


# ── Bulk Operations ──

def bulk_close_sessions(status: str = "in_progress") -> str:
    """Close all sessions with a given status."""
    sessions = _load_json(_SESSIONS_FILE, [])
    count = 0
    for s in sessions:
        if s.get("status") == status:
            s["status"] = SessionStatus.COMPLETED.value
            s["completed_at"] = _now_iso()
            count += 1
    if count > 0:
        _save_json(_SESSIONS_FILE, sessions)
        return f"[OK] Closed {count} sessions with status '{status}'."
    return f"No sessions with status '{status}' found."


def purge_archived_sessions() -> str:
    """Remove archived sessions from the active sessions file."""
    sessions = _load_json(_SESSIONS_FILE, [])
    before = len(sessions)
    sessions = [s for s in sessions if s.get("status") != SessionStatus.ARCHIVED.value]
    after = len(sessions)
    _save_json(_SESSIONS_FILE, sessions)
    return f"[OK] Purged {before - after} archived sessions. {after} remain."


# ── Session Comparison ──

def compare_sessions(session_id_a: str, session_id_b: str) -> str:
    """Compare two sessions side by side."""
    sessions = _load_json(_SESSIONS_FILE, [])
    sa = sb = None
    for s in sessions:
        if s["session_id"] == session_id_a: sa = s
        if s["session_id"] == session_id_b: sb = s
    if not sa: return f"Session {session_id_a[:8]} not found."
    if not sb: return f"Session {session_id_b[:8]} not found."

    lines = [
        f"### Session Comparison",
        f"",
        f"{'Metric':<30} {'Session A':<40} {'Session B':<40}",
        f"{'-'*30:<30} {'-'*40:<40} {'-'*40:<40}",
        f"{'Topic':<30} {sa.get('topic','?')[:38]:<40} {sb.get('topic','?')[:38]:<40}",
        f"{'Status':<30} {sa.get('status','?'):<40} {sb.get('status','?'):<40}",
        f"{'Messages':<30} {str(len(sa.get('messages',[]))):<40} {str(len(sb.get('messages',[]))):<40}",
        f"{'Participants':<30} {str(len(sa.get('participants',[]))):<40} {str(len(sb.get('participants',[]))):<40}",
        f"{'Outcomes':<30} {str(len(sa.get('outcomes',[]))):<40} {str(len(sb.get('outcomes',[]))):<40}",
        f"{'Template':<30} {sa.get('template','none')[:38]:<40} {sb.get('template','none')[:38]:<40}",
    ]
    return "\n".join(lines)



def townhall_tool(action: str = "status", **kwargs) -> str:
    """Agent Town Hall — autonomous agent deliberation & coordination.

    Actions:
      status - Show town hall status
      agenda - List agenda items [status]
      add_agenda - Add agenda item (title, description, assigned_to, priority)
      resolve_agenda - Resolve agenda item (item_id, resolution)
      start - Start session (topic, participants)
      post - Post message (session_id, agent, message)
      conclude - Conclude session (session_id, summary)
      session - Show session (session_id)
      sessions - List sessions [status]
      cancel_session - Cancel a session (session_id)
      deliberate - Run autonomous deliberation (topic, rounds)
      vote - Cast vote (session_id, agent, vote, proposal_id)
      tally - Tally votes (session_id, proposal_id)
      consensus - Reach consensus (session_id, proposal, algorithm)
      blockers - Detect consensus blockers (session_id)
      propose - Create proposal (session_id, title, description, proposed_by)
      amend - Amend proposal (proposal_id, amendment)
      withdraw - Withdraw proposal (proposal_id)
      proposals - List proposals [session_id]
      templates - List templates
      run_template - Run template (template_name, topic)
      dm - Send DM (from, to, message)
      read_dms - Read DM inbox (agent)
      broadcast - Broadcast to all sessions (agent, message, channel)
      debate - Start debate (session_id, motion, proposer, opposer)
      argue - Add argument (debate_id, agent, position, argument)
      close_debate - Close debate (debate_id, resolution)
      debates - List debates [session_id]
      escalate - Escalate to human (session_id, issue, agent)
      escalations - Show escalation queue [status]
      resolve_esc - Resolve escalation (escalation_id, resolution)
      auto_escalate - Check auto-escalation (session_id, max_rounds)
      record_outcome - Record outcome (session_id, description)
      outcomes - List outcomes [session_id]
      outcome_stats - Outcome statistics
      update_outcome - Update outcome status (outcome_id, status)
      create_action - Create action (session_id, description, assignee, deadline)
      update_action - Update action status (item_id, status)
      actions - List actions [agent]
      schedule - Schedule session (topic, participants, time_str)
      reschedule - Reschedule (schedule_id, time_str)
      schedule_list - Show schedule
      summarize - Summarize session (session_id, max_length)
      decisions - Extract key decisions (session_id)
      minutes - Generate minutes (session_id)
      daily_summary - Generate daily summary
      detect_conflict - Detect conflict (session_id, agent_a, agent_b)
      mediate - Mediate conflicts (session_id)
      archive - Archive session (session_id)
      search - Search sessions (query)
      timeline - Session timeline (session_id)
      export_json - Export session JSON (session_id)
      export_md - Export session markdown (session_id)
      permissions - List agent permissions [agent]
      check_perm - Check permission (agent, permission)
      personality - Show agent personality [agent]
      registry - List agent registry
      find_by_expertise - Find agents by expertise (area)
    """
    _ensure_dirs()

    if action == "status":
        sessions = _load_json(_SESSIONS_FILE, [])
        agenda = _load_json(_AGENDA_FILE, {"items": []})
        active = sum(1 for s in sessions if s.get("status") == SessionStatus.IN_PROGRESS.value)
        total_msgs = sum(len(s.get("messages",[])) for s in sessions)
        open_items = sum(1 for i in agenda.get("items",[]) if i.get("status")=="open")
        votes = _load_json(_VOTES_FILE, {"votes": []})
        actions = _load_json(_ACTIONS_FILE, {"actions": []})
        open_actions = sum(1 for a in actions.get("actions",[]) if a.get("status")=="open")
        registry = get_agent_registry()
        return json.dumps({
            "total_sessions": len(sessions),
            "active_sessions": active,
            "total_messages": total_msgs,
            "open_agenda_items": open_items,
            "agents_available": len(AGENT_ROLES),
            "agents_registered": len(registry.list_all()),
            "total_votes_cast": len(votes.get("votes",[])),
            "open_action_items": open_actions,
        }, indent=2)

    elif action == "agenda":
        return list_agenda(status=kwargs.get("status",""))
    elif action == "add_agenda":
        item = add_agenda_item(title=kwargs.get("title",""), description=kwargs.get("description",""), assigned_to=kwargs.get("assigned_to",""), priority=kwargs.get("priority","medium"))
        return f"[OK] Agenda: {item["title"]} ({item["id"]})"
    elif action == "resolve_agenda":
        return resolve_agenda_item(item_id=kwargs.get("item_id",""), resolution=kwargs.get("resolution","completed"))

    elif action == "start":
        topic = kwargs.get("topic","General planning")
        participants = kwargs.get("participants")
        if participants and isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",")]
        return f"[OK] Session started: {start_session(topic, participants)}"
    elif action == "post":
        return post_message(session_id=kwargs.get("session_id",""), agent_name=kwargs.get("agent",kwargs.get("from","unknown")), message=kwargs.get("message",""))
    elif action == "conclude":
        return conclude_session(session_id=kwargs.get("session_id",""), summary=kwargs.get("summary",""))
    elif action == "session":
        return get_session(kwargs.get("session_id",""))
    elif action == "sessions":
        return list_sessions(status=kwargs.get("status",""))
    elif action == "cancel_session":
        return cancel_session(kwargs.get("session_id",""))
    elif action == "deliberate":
        return auto_deliberate(topic=kwargs.get("topic","General"), rounds=int(kwargs.get("rounds",2)))

    elif action == "vote":
        return cast_vote(session_id=kwargs.get("session_id",""), agent_name=kwargs.get("agent",kwargs.get("from","unknown")), vote=kwargs.get("vote","abstain"), proposal_id=kwargs.get("proposal_id",""))
    elif action == "tally":
        return tally_votes(session_id=kwargs.get("session_id",""), proposal_id=kwargs.get("proposal_id",""))
    elif action == "consensus":
        return reach_consensus(session_id=kwargs.get("session_id",""), proposal=kwargs.get("proposal",kwargs.get("topic","General")), algorithm=kwargs.get("algorithm","majority"))
    elif action == "blockers":
        return detect_consensus_blockers(kwargs.get("session_id",""))

    elif action == "propose":
        return create_proposal(session_id=kwargs.get("session_id",""), title=kwargs.get("title","Untitled"), description=kwargs.get("description",""), proposed_by=kwargs.get("proposed_by",kwargs.get("agent","unknown")))
    elif action == "amend":
        return amend_proposal(proposal_id=kwargs.get("proposal_id",""), amendment=kwargs.get("amendment",""))
    elif action == "withdraw":
        return withdraw_proposal(kwargs.get("proposal_id",""))
    elif action == "proposals":
        return list_proposals(session_id=kwargs.get("session_id",""))

    elif action == "templates":
        return list_templates()
    elif action == "run_template":
        sid = run_template(template_name=kwargs.get("template_name","quick_decision"), topic=kwargs.get("topic","General"))
        return f"[OK] Template started: {sid}"

    elif action == "dm":
        return direct_message(from_agent=kwargs.get("from",kwargs.get("agent","unknown")), to_agent=kwargs.get("to",""), message=kwargs.get("message",""))
    elif action == "read_dms":
        return read_dms(agent_name=kwargs.get("agent",""), mark_read=kwargs.get("mark_read","true").lower()=="true")
    elif action == "broadcast":
        return broadcast(agent_name=kwargs.get("agent",kwargs.get("from","unknown")), message=kwargs.get("message",""), channel=kwargs.get("channel","general"))

    elif action == "debate":
        return start_debate(session_id=kwargs.get("session_id",""), motion=kwargs.get("motion",kwargs.get("topic","General")), proposer=kwargs.get("proposer",kwargs.get("agent","unknown")), opposer=kwargs.get("opposer",""))
    elif action == "argue":
        return add_argument(debate_id=kwargs.get("debate_id",""), agent=kwargs.get("agent",kwargs.get("from","unknown")), position=kwargs.get("position","NEUTRAL"), argument=kwargs.get("argument",kwargs.get("message","")))
    elif action == "close_debate":
        return close_debate(debate_id=kwargs.get("debate_id",""), resolution=kwargs.get("resolution",""))
    elif action == "debates":
        return list_debates(session_id=kwargs.get("session_id",""))

    elif action == "escalate":
        return escalate_to_human(session_id=kwargs.get("session_id",""), issue=kwargs.get("issue",kwargs.get("message","No details")), agent_name=kwargs.get("agent",""))
    elif action == "escalations":
        return escalation_queue(status=kwargs.get("status","pending"))
    elif action == "resolve_esc":
        return resolve_escalation(escalation_id=kwargs.get("escalation_id",""), resolution=kwargs.get("resolution",""))
    elif action == "auto_escalate":
        return check_auto_escalation(session_id=kwargs.get("session_id",""), max_rounds=int(kwargs.get("max_rounds",3)))

    elif action == "record_outcome":
        t = get_outcome_tracker()
        oid = t.record_outcome(session_id=kwargs.get("session_id",""), description=kwargs.get("description",kwargs.get("message","")), agenda_item_id=kwargs.get("agenda_item_id",""), decision=kwargs.get("decision",""))
        return f"[OK] Outcome: {oid}"
    elif action == "outcomes":
        return get_outcome_tracker().list_outcomes(session_id=kwargs.get("session_id",""))
    elif action == "outcome_stats":
        return get_outcome_tracker().get_outcome_stats()
    elif action == "update_outcome":
        return get_outcome_tracker().update_implementation_status(outcome_id=kwargs.get("outcome_id",""), status=kwargs.get("status","pending"))

    elif action == "create_action":
        return create_action_item(session_id=kwargs.get("session_id",""), description=kwargs.get("description",kwargs.get("message","")), assignee=kwargs.get("assignee",kwargs.get("agent","unassigned")), deadline=kwargs.get("deadline",""))
    elif action == "update_action":
        return update_action_item_status(item_id=kwargs.get("item_id",""), status=kwargs.get("status","open"))
    elif action == "actions":
        return list_action_items(agent_name=kwargs.get("agent",""))

    elif action == "schedule":
        participants = kwargs.get("participants")
        if participants and isinstance(participants, str): participants = [p.strip() for p in participants.split(",")]
        return schedule_session(topic=kwargs.get("topic","General"), participants=participants, time_str=kwargs.get("time_str",kwargs.get("time","")))
    elif action == "reschedule":
        return reschedule_session(schedule_id=kwargs.get("schedule_id",""), time_str=kwargs.get("time_str",kwargs.get("time","")))
    elif action == "schedule_list":
        return get_schedule()

    elif action == "summarize":
        return summarize_session(session_id=kwargs.get("session_id",""), max_length=int(kwargs.get("max_length",500)))
    elif action == "decisions":
        return extract_key_decisions(kwargs.get("session_id",""))
    elif action == "minutes":
        return generate_minutes(kwargs.get("session_id",""))
    elif action == "daily_summary":
        return generate_daily_summary()

    elif action == "detect_conflict":
        return detect_conflict(kwargs.get("session_id",""), agent_a=kwargs.get("agent_a",""), agent_b=kwargs.get("agent_b",""))
    elif action == "mediate":
        return mediate_conflict(kwargs.get("session_id",""))

    elif action == "archive":
        return archive_session(kwargs.get("session_id",""))
    elif action == "search":
        return search_sessions(kwargs.get("query",""))
    elif action == "timeline":
        return get_session_timeline(kwargs.get("session_id",""))
    elif action == "export_json":
        return export_session_json(kwargs.get("session_id",""))
    elif action == "export_md":
        return export_session_markdown(kwargs.get("session_id",""))

    elif action == "permissions":
        agent_id = kwargs.get("agent","")
        if not agent_id:
            lines = ["### Permissions"]
            for a in get_agent_registry().list_all():
                p = RolePermission.list_permissions(a.agent_id)
                lines.append(f"  {a.name}: {", ".join(p) if p else "none"}")
            return "\n".join(lines)
        return f"Permissions: {", ".join(RolePermission.list_permissions(agent_id))}"
    elif action == "check_perm":
        allowed = RolePermission.check_permission(kwargs.get("agent",""), Permission(kwargs.get("permission","vote")))
        return f"Permission {kwargs.get("permission")} for {kwargs.get("agent")}: {"GRANTED" if allowed else "DENIED"}"

    elif action == "personality":
        agent_id = kwargs.get("agent","")
        reg = get_agent_registry()
        if not agent_id:
            lines = ["### Personalities"]
            for a in reg.list_all():
                p = a.personality
                lines.append(f"  {a.name}: assert={p.assertiveness:.2f} coop={p.cooperativeness:.2f} risk={p.risk_tolerance:.2f} expert={p.expertise_depth:.2f}")
            return "\n".join(lines)
        agent = reg.get(agent_id) or reg.get_by_name(agent_id)
        if not agent: return f"Agent {agent_id} not found."
        return json.dumps({"name": agent.name, "role": agent.role, "personality": agent.personality.to_dict(), "expertise_areas": agent.expertise_areas, "style": agent.communication_style}, indent=2)

    elif action == "registry":
        lines = [f"### Agent Registry ({len(get_agent_registry().list_all())} agents)"]
        for a in get_agent_registry().list_all():
            lines.append(f"  \u2022 {a.name} ({a.agent_id}) - {a.role[:60]} / {", ".join(a.expertise_areas[:3])}")
        return "\n".join(lines)

    elif action == "find_by_expertise":
        agents = get_agent_registry().find_by_expertise(kwargs.get("area",""))
        if not agents: return f"No agents with expertise in {kwargs.get("area")}."
        lines = [f"Agents with expertise in {kwargs.get("area")}:"]
        for a in agents: lines.append(f"  \u2022 {a.name}")
        return "\n".join(lines)

    elif action == "add_tag":
        return add_tag_to_session(session_id=kwargs.get("session_id",""), tag=kwargs.get("tag",""))
    elif action == "remove_tag":
        return remove_tag_from_session(session_id=kwargs.get("session_id",""), tag=kwargs.get("tag",""))
    elif action == "list_tags":
        return list_tags()
    elif action == "find_by_tag":
        return find_sessions_by_tag(tag=kwargs.get("tag",""))
    elif action == "stats":
        return get_session_statistics()
    elif action == "compare_sessions":
        return compare_sessions(session_id_a=kwargs.get("session_id_a",""), session_id_b=kwargs.get("session_id_b",""))
    elif action == "close_all":
        return bulk_close_sessions(status=kwargs.get("status","in_progress"))
    elif action == "purge_archived":
        return purge_archived_sessions()

    elif action == "audit_log":
        sess_id = kwargs.get("session_id","")
        agent_n = kwargs.get("agent","")
        audit = get_audit()
        if sess_id: return audit.get_session_audit(sess_id)
        if agent_n: return audit.get_agent_audit(agent_n)
        return "Specify session_id or agent."
    elif action == "send_notification":
        nm = get_notification_manager()
        nid = nm.send_notification(to_agent=kwargs.get("to",""), subject=kwargs.get("subject",""), message=kwargs.get("message",""), priority=kwargs.get("priority","normal"))
        return f"[OK] Notification sent: {nid}"
    elif action == "notifications":
        return get_notification_manager().get_notifications(agent_name=kwargs.get("agent",""), unread_only=kwargs.get("unread_only","true").lower()=="true")
    elif action == "mark_notification_read":
        return get_notification_manager().mark_read(notification_id=kwargs.get("notification_id",""))
    elif action == "clear_notifications":
        return get_notification_manager().clear_all(agent_name=kwargs.get("agent",""))
    elif action == "report":
        return get_report_generator().generate_session_report(session_id=kwargs.get("session_id",""), include_messages=kwargs.get("include_messages","true").lower()=="true")
    elif action == "summary_report":
        return get_report_generator().generate_summary_report()

    return f"[FAIL] Unknown action: {action}"
