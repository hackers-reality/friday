"""
Agent Town Hall — autonomous agent deliberation & coordination system.
Agents discuss tasks, delegate work, review results, and plan together.
Agents discuss tasks, delegate work, review results, and plan together autonomously.

Architecture:
  - TownHall: manages agent sessions, agendas, minutes
  - AgentSession: one deliberation session with agenda + outcomes
  - Auto-delegation: agents propose tasks, others accept/review
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("townhall")

_TOWNHALL_DIR = os.path.join(FRIDAY_MEMORY, "townhall")
_SESSIONS_FILE = os.path.join(_TOWNHALL_DIR, "sessions.json")
_MINUTES_DIR = os.path.join(_TOWNHALL_DIR, "minutes")
_AGENDA_FILE = os.path.join(_TOWNHALL_DIR, "agenda.json")

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


def _ensure_dirs():
    for d in (_TOWNHALL_DIR, _MINUTES_DIR):
        os.makedirs(d, exist_ok=True)


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
        "created": datetime.now().isoformat(),
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
        status_icon = {"open": "○", "in_progress": "◐", "resolved": "●", "cancelled": "⊗"}.get(item.get("status", "open"), "○")
        assign = f" → {item['assigned_to']}" if item.get("assigned_to") else ""
        lines.append(f"  {status_icon} [{item['id']}] {item['title']}{assign} ({item.get('priority', 'medium')})")
        if item.get("description"):
            lines.append(f"      {item['description'][:100]}")
    return "\n".join(lines)


def resolve_agenda_item(item_id: str, resolution: str = "completed") -> str:
    agendas = _load_json(_AGENDA_FILE, {"items": []})
    for item in agendas["items"]:
        if item["id"] == item_id:
            item["status"] = "resolved" if resolution == "completed" else "cancelled"
            item["resolved_at"] = datetime.now().isoformat()
            item["resolution"] = resolution
            _save_json(_AGENDA_FILE, agendas)
            return f"[OK] Agenda item {item_id} resolved: {resolution}"
    return f"[FAIL] Agenda item {item_id} not found"


# ── Deliberation Sessions ──

def start_session(topic: str, participants: Optional[list[str]] = None) -> str:
    """Start a new agent deliberation session."""
    _ensure_dirs()
    sessions = _load_json(_SESSIONS_FILE, [])
    session = {
        "session_id": uuid.uuid4().hex[:8],
        "topic": topic,
        "participants": participants or list(AGENT_ROLES.keys()),
        "started_at": datetime.now().isoformat(),
        "status": "in_progress",
        "messages": [],
        "outcomes": [],
        "agenda_items": [],
    }

    # Opening statement
    session["messages"].append({
        "from": "townhall",
        "text": f"Town Hall session started. Topic: {topic}",
        "timestamp": datetime.now().isoformat(),
    })

    sessions.append(session)
    _save_json(_SESSIONS_FILE, sessions)
    return session["session_id"]


def post_message(session_id: str, agent_name: str, message: str) -> str:
    """Post a message from an agent to a session."""
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            session["messages"].append({
                "from": agent_name,
                "text": message,
                "timestamp": datetime.now().isoformat(),
            })
            _save_json(_SESSIONS_FILE, sessions)
            return f"[OK] {agent_name} posted to session {session_id[:8]}"
    return f"[FAIL] Session {session_id} not found"


def conclude_session(session_id: str, summary: str = "") -> str:
    """Conclude a deliberation session with outcomes."""
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            session["status"] = "completed"
            session["completed_at"] = datetime.now().isoformat()
            session["summary"] = summary or session.get("summary", "")
            _save_json(_SESSIONS_FILE, sessions)

            # Save minutes
            minutes_path = os.path.join(_MINUTES_DIR, f"minutes_{session_id}.json")
            with open(minutes_path, "w") as f:
                json.dump(session, f, indent=2)

            return f"[OK] Session {session_id[:8]} concluded."
    return f"[FAIL] Session {session_id} not found"


def get_session(session_id: str) -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    for session in sessions:
        if session["session_id"] == session_id:
            lines = [f"### Town Hall Session: {session['topic']} ({session['status']})"]
            lines.append(f"Participants: {', '.join(session.get('participants', []))}")
            lines.append(f"Started: {session.get('started_at', '?')[:19]}")
            lines.append("")
            for msg in session.get("messages", []):
                from_name = msg.get("from", "?")
                text = msg.get("text", "")[:200]
                ts = msg.get("timestamp", "?")[11:19]
                lines.append(f"  [{ts}] <{from_name}> {text}")
            outcomes = session.get("outcomes", [])
            if outcomes:
                lines.append(f"\nOutcomes ({len(outcomes)}):")
                for o in outcomes:
                    lines.append(f"  - {o[:200]}")
            return "\n".join(lines)
    return f"Session {session_id} not found."


def list_sessions(status: str = "") -> str:
    sessions = _load_json(_SESSIONS_FILE, [])
    if status:
        sessions = [s for s in sessions if s.get("status") == status]
    if not sessions:
        return "No sessions found."

    lines = [f"### Town Hall Sessions ({len(sessions)})"]
    for s in sessions:
        sid = s.get("session_id", "?")[:8]
        topic = s.get("topic", "?")[:50]
        status_icon = {"in_progress": "◐", "completed": "●", "planned": "○"}.get(s.get("status", ""), "○")
        msgs = len(s.get("messages", []))
        participants = len(s.get("participants", []))
        lines.append(f"  {status_icon} [{sid}] {topic} ({msgs} msgs, {participants} agents)")
    return "\n".join(lines)


# ── Autonomous Deliberation ──

def auto_deliberate(topic: str, rounds: int = 2) -> str:
    """Run an autonomous multi-agent deliberation on a topic.
    Each agent contributes based on their role, then reviews and concludes.
    """
    sid = start_session(topic, participants=list(AGENT_ROLES.keys()))

    for round_num in range(1, rounds + 1):
        for agent, role_desc in AGENT_ROLES.items():
            try:
                prompt = (
                    f"You are {agent.upper()}, FRIDAY's {role_desc}.\n"
                    f"Topic: {topic}\n"
                    f"Round {round_num}/{rounds}\n"
                    f"Contribute your perspective as {agent}. Be concise (2-3 sentences). "
                    f"Focus on what YOUR expertise brings to this topic."
                )

                from friday.tools.ai_tools import model_query
                response = model_query(
                    prompt=prompt,
                    system=f"You are {agent.upper()}, FRIDAY's {role_desc}. Respond in character, be concise.",
                    model="opencode/big-pickle",
                )
                text = ""
                if isinstance(response, dict):
                    text = response.get("text", "") or response.get("response", "") or response.get("content", "")
                else:
                    text = str(response)
                post_message(sid, agent, text.strip())
            except Exception as e:
                post_message(sid, agent, f"(unavailable: {e})")

    # Conclude with summary
    summary_prompt = (
        f"Summarize the town hall deliberation on '{topic}'.\n"
        f"Extract key decisions, action items, and consensus points."
    )
    try:
        from friday.tools.ai_tools import model_query
        summary_resp = model_query(
            prompt=summary_prompt,
            system="You are a meeting scribe. Output a concise summary with bullet points.",
            model="opencode/big-pickle",
        )
        summary = ""
        if isinstance(summary_resp, dict):
            summary = summary_resp.get("text", "") or summary_resp.get("response", "") or summary_resp.get("content", "")
        else:
            summary = str(summary_resp)
    except Exception:
        summary = "Deliberation completed."

    conclude_session(sid, summary=summary)
    return get_session(sid)


# ── Tool ──

def townhall_tool(action: str = "status", **kwargs) -> str:
    """Agent Town Hall — autonomous agent deliberation & coordination.
    
    Actions:
      status - Show town hall status
      agenda - List agenda items [status]
      add_agenda - Add agenda item (title, description, assigned_to, priority)
      resolve_agenda - Resolve agenda item (item_id, resolution)
      start - Start deliberation session (topic, participants)
      post - Post message to session (session_id, agent, message)
      conclude - Conclude session (session_id, summary)
      session - Show session (session_id)
      sessions - List sessions [status]
      deliberate - Run autonomous multi-agent deliberation (topic, rounds)
    """
    _ensure_dirs()

    if action == "status":
        sessions = _load_json(_SESSIONS_FILE, [])
        agenda = _load_json(_AGENDA_FILE, {"items": []})
        active = sum(1 for s in sessions if s.get("status") == "in_progress")
        total_msgs = sum(len(s.get("messages", [])) for s in sessions)
        open_items = sum(1 for i in agenda.get("items", []) if i.get("status") == "open")
        return json.dumps({
            "total_sessions": len(sessions),
            "active_sessions": active,
            "total_messages": total_msgs,
            "open_agenda_items": open_items,
            "agents_available": len(AGENT_ROLES),
        }, indent=2)

    elif action == "agenda":
        return list_agenda(status=kwargs.get("status", ""))

    elif action == "add_agenda":
        item = add_agenda_item(
            title=kwargs.get("title", ""),
            description=kwargs.get("description", ""),
            assigned_to=kwargs.get("assigned_to", ""),
            priority=kwargs.get("priority", "medium"),
        )
        return f"[OK] Agenda item added: {item['title']} ({item['id']})"

    elif action == "resolve_agenda":
        return resolve_agenda_item(
            item_id=kwargs.get("item_id", ""),
            resolution=kwargs.get("resolution", "completed"),
        )

    elif action == "start":
        topic = kwargs.get("topic", "General planning")
        participants = kwargs.get("participants")
        if participants and isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",")]
        sid = start_session(topic, participants=participants)
        return f"[OK] Session started: {sid}"

    elif action == "post":
        return post_message(
            session_id=kwargs.get("session_id", ""),
            agent_name=kwargs.get("agent", kwargs.get("from", "unknown")),
            message=kwargs.get("message", ""),
        )

    elif action == "conclude":
        return conclude_session(
            session_id=kwargs.get("session_id", ""),
            summary=kwargs.get("summary", ""),
        )

    elif action == "session":
        return get_session(kwargs.get("session_id", ""))

    elif action == "sessions":
        return list_sessions(status=kwargs.get("status", ""))

    elif action == "deliberate":
        topic = kwargs.get("topic", "General planning")
        rounds = int(kwargs.get("rounds", 2))
        return auto_deliberate(topic, rounds)

    return f"[FAIL] Unknown action: {action}"
