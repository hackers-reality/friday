"""Friday Dreaming System — analyzes past sessions while idle.
Runs in background, reviews conversations, extracts patterns,
updates memory and knowledge graph. Like sleeping to consolidate memories."""

from __future__ import annotations
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_DREAM_STATE_FILE = os.path.join(FRIDAY_MEMORY, "dream_state.json")
_dream_thread: Optional[threading.Thread] = None
_dream_stop = threading.Event()


def _load_state() -> dict:
    if os.path.exists(_DREAM_STATE_FILE):
        try:
            with open(_DREAM_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_dream": None, "dream_count": 0, "insights": []}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_DREAM_STATE_FILE), exist_ok=True)
    try:
        with open(_DREAM_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _collect_recent_sessions() -> list:
    """Collect recent session data from vector memory and logs."""
    sessions = []
    log_dir = os.path.join(FRIDAY_MEMORY, "logs")
    if os.path.isdir(log_dir):
        log_files = sorted(
            [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".json")],
            key=os.path.getmtime, reverse=True
        )[:5]
        for lf in log_files:
            try:
                with open(lf) as f:
                    data = json.load(f)
                    sessions.append(data)
            except Exception:
                pass
    return sessions


def _dream_cycle():
    """One full dream cycle: analyze sessions, extract insights, update memory."""
    state = _load_state()
    now = datetime.now()

    sessions = _collect_recent_sessions()
    if not sessions:
        state["last_dream"] = now.isoformat()
        _save_state(state)
        return

    # Extract co-occurring entities, preferences, patterns
    extracted_facts = []
    for session in sessions:
        text = json.dumps(session)
        # Simple keyword extraction (basic pattern)
        keywords = set()
        for word in text.split():
            word = word.strip(",.!?;:'\"[]{}()").lower()
            if len(word) > 4 and word.isalpha() and word not in (
                "about", "there", "which", "their", "would", "could", "should",
                "thing", "these", "those", "after", "before", "other", "every",
            ):
                keywords.add(word)
        if keywords:
            extracted_facts.append({
                "timestamp": session.get("timestamp", now.isoformat()),
                "keywords": list(keywords)[:20],
                "session_type": session.get("type", "conversation"),
            })

    # Store insights
    if extracted_facts:
        state["insights"].extend(extracted_facts)
        state["insights"] = state["insights"][-100:]  # keep last 100
        state["last_dream"] = now.isoformat()
        state["dream_count"] += 1
        _save_state(state)

        # Update vector memory with extracted patterns
        try:
            from friday.vector_memory import vector_memory_tool
            for fact in extracted_facts:
                if fact["keywords"]:
                    vector_memory_tool(
                        action="add",
                        text=f"Dream insight: session with keywords {', '.join(fact['keywords'][:5])}",
                    )
        except Exception:
            pass

        # Update knowledge graph
        try:
            from friday.knowledge_graph import knowledge_graph_tool
            for fact in extracted_facts[:3]:
                if fact["keywords"]:
                    knowledge_graph_tool(
                        action="add_relationship",
                        source="Friday",
                        target=fact["keywords"][0],
                        relationship="analyzed",
                        context=f"Dream analysis from {fact['session_type']} session",
                    )
        except Exception:
            pass


def dream_tool(action: str = "status") -> str:
    """Manage the dreaming system. Actions: status, cycle, start, stop, insights."""
    global _dream_thread, _dream_stop

    if action == "status":
        state = _load_state()
        last = state.get("last_dream", "never")
        count = state.get("dream_count", 0)
        running = _dream_thread is not None and _dream_thread.is_alive()
        return (
            f"Dreaming system: {'ACTIVE' if running else 'IDLE'}\n"
            f"Last dream: {last}\n"
            f"Dream cycles completed: {count}\n"
            f"Insights collected: {len(state.get('insights', []))}"
        )
    elif action == "cycle":
        _dream_cycle()
        return "[OK] Dream cycle completed."
    elif action == "start":
        if _dream_thread and _dream_thread.is_alive():
            return "[INFO] Dreaming already active."
        _dream_stop.clear()
        def _looper():
            while not _dream_stop.is_set():
                _dream_cycle()
                _dream_stop.wait(300)  # 5 minutes between cycles
        _dream_thread = threading.Thread(target=_looper, daemon=True)
        _dream_thread.start()
        return "[OK] Dreaming system started (5-min cycle). I'll analyze sessions while idle."
    elif action == "stop":
        _dream_stop.set()
        if _dream_thread:
            _dream_thread.join(timeout=3)
        _dream_thread = None
        return "[OK] Dreaming stopped."
    elif action == "insights":
        state = _load_state()
        insights = state.get("insights", [])
        if not insights:
            return "No insights yet. Let me dream more."
        lines = ["### DREAM INSIGHTS"]
        for i, ins in enumerate(insights[-10:], 1):
            kws = ", ".join(ins.get("keywords", [])[:5])
            ts = ins.get("timestamp", "?")[:16]
            lines.append(f"  {i}. [{ts}] {kws}")
        return "\n".join(lines)
    else:
        return f"[FAIL] Unknown action: {action}"


def start_dreaming_if_idle():
    """Auto-start dreaming on boot."""
    try:
        dream_tool("start")
    except Exception:
        pass
