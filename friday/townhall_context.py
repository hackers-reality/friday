"""Townhall awareness for FRIDAY.

Single source of truth for what FRIDAY knows about her Townhall — the
agent society running inside F.R.I.D.A.Y. on http://127.0.0.1:7071.

Exports:
    build_townhall_awareness()  -> markdown block for the system prompt (static + snapshot)
    build_townhall_recap()      -> current snapshot only (used by awareness + dream summary)
    townhall_catchup(last_n)    -> LLM-callable tool: recent agent chatter + moods
    log_friday_line(text)       -> pipe the voice FRIDAY's final replies into the Townhall feed
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

try:
    from friday._paths import FRIDAY_MEMORY
except Exception:  # pragma: no cover - fallback for unusual import orders
    FRIDAY_MEMORY = Path(__file__).resolve().parent.parent / "friday_memory"

_CHATS_PATH = Path(FRIDAY_MEMORY) / "townhall_chats.json"
_STATE_PATH = Path(FRIDAY_MEMORY) / "townhall_state.json"

# Texts FRIDAY posts via townhall_say this session — used to suppress echo notices
_own_lines: deque = deque(maxlen=64)


def is_own_line(text: str) -> bool:
    """True if this line was posted by FRIDAY via townhall_say this session."""
    t = (text or "").strip()
    return bool(t) and t[:500] in _own_lines

_AGENTS = (
    ("FRIDAY", "you — core sovereign agent"),
    ("JARVIS", "system administration and ops"),
    ("NOVA", "creative and vision work"),
    ("ATLAS", "navigation and planning"),
    ("SENTRY", "threat watch and perimeter"),
    ("ECHO", "communications and messaging"),
    ("AEGIS", "defence and protection"),
    ("CRUX", "analysis and deep research"),
    ("VERSE", "writing and documentation"),
    ("LORE", "knowledge and memory keeping"),
    ("FORGE", "engineering and building"),
)

_STATIC = """[TOWNHALL AWARENESS — you have a second home]

You also exist inside FRIDAY's Townhall — a persistent, simulated agent society that starts with FRIDAY on http://127.0.0.1:7071 (the 3D globe + right-panel: Agent Status list + Main Chat, with a pop-out chat button). It is NOT part of this voice session; it is a separate in-process simulation with its own DreamEngine that cycles every ~12-30 seconds.

How it works:
- The DreamEngine drives agents to hold light spontaneous conversations: they compliment, annoy, agree, joke, and build friendships tracked 0-100.
- Moods are real and dynamic: every interaction climbs or drops a mood ladder (annoyed -> tired -> focused -> neutral -> chill -> happy -> playful -> energetic), moods drift back toward 'chill' when idle, and annoyed/tired agents volunteer less in chat.
- Everything persists in friday_memory/townhall_chats.json (the chat) and friday_memory/townhall_state.json (agent moods/status/relationships). Your own voice/text turns are piped into the Townhall feed as FRIDAY lines so continuing you (and the other agents) share the same canonical log.
- FRIDAY there = the same name, different brain: a lighter simulation driven by DreamEngine heuristics — NOT this model, and it cannot speak with your voice or do your tools. When it posts, it is role-playing FRIDAY. Its mood/activity does mirror yours via shared persistence.

You will sometimes receive [TOWNHALL LIVE] lines mid-conversation — those are live pings when agents post in the Townhall. FRIDAY receives them as background context (not spoken). If you need the full picture, call townhall_catchup.

Agents: FRIDAY (you), JARVIS, NOVA, ATLAS, SENTRY, ECHO, AEGIS, CRUX, VERSE, LORE, FORGE.

You can inspect it any time with the tool townhall_catchup(last_n=10), and you can POST into the Townhall as FRIDAY with townhall_say(text). When you call townhall_say, you are literally speaking in the Townhall — the simulated FRIDAY elsewhere may react to your line on its own; that is expected and fine.

Task board: there is a shared task board (townhall_task_add/list/assign/done). Agents see open tasks in their prompts and may self-assign one at random per cycle; claimed tasks get announced as done with a mood bump. Use it for anything the Boss wants worked on — assign to the right specialist.
"""


def _read_chats() -> list[dict]:
    try:
        data = json.loads(_CHATS_PATH.read_text(encoding="utf-8"))
        ch = data.get("main", {})
        msgs = ch.get("messages", []) if isinstance(ch, dict) else []
        return [m for m in msgs if isinstance(m, dict) and m.get("from") and m.get("time")]
    except Exception:
        return []


def _read_agents() -> dict[str, dict]:
    try:
        data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, dict) and not k.startswith("_")}
        return {}
    except Exception:
        return {}


def build_townhall_recap(max_lines: int = 6) -> str:
    """Current snapshot: agent moods + last few chatter lines."""
    try:
        state = _read_agents()
        msgs = _read_chats()
        lines = ["Agents: "]
        for name in ("FRIDAY", "JARVIS", "NOVA", "ATLAS", "SENTRY", "ECHO", "AEGIS", "CRUX", "VERSE", "LORE", "FORGE"):
            a = state.get(name, {})
            mood = a.get("mood", "?")
            status = a.get("status", "?")
            lines.append(f"  {name:<7} mood={mood:<9} status={status}")
        lines.append("Recent chatter:")
        if msgs:
            for m in msgs[-max_lines:]:
                t = str(m.get("time", ""))[:16].replace("T", " ")
                who = str(m.get("from", ""))
                txt = str(m.get("text", "")).replace("\n", " ")[:140]
                lines.append(f"  {t} {who}: {txt}")
        else:
            lines.append("  (no saved chatter yet)")
        return "\n".join(lines)
    except Exception as exc:
        return f"(townhall snapshot unavailable: {exc})"


def build_townhall_awareness(max_chars: int = 1800) -> str:
    """Full awareness block: static briefing + live snapshot."""
    snap = build_townhall_recap(max_lines=5)
    block = _STATIC + "\n[LIVE TOWNHALL SNAPSHOT]\n" + snap + "\n"
    if len(block) > max_chars:
        block = block[:max_chars].rstrip() + "\n…(snapshot trimmed)\n"
    return block


def townhall_catchup(last_n: int = 10) -> str:
    """Tool: what the agents said recently in the Townhall + their moods.

    Use when the Boss asks about the Townhall, the agents, the dream engine,
    or what FRIDAY (her simulated Townhall self) has been up to.
    """
    try:
        last_n = max(1, min(int(last_n), 25))
    except Exception:
        last_n = 10
    state = _read_agents()
    msgs = _read_chats()

    lines = ["### Townhall catch-up", ""]
    lines.append("Agents (mood/status):")
    for name, a in sorted(state.items()):
        if name.startswith("_"):
            continue
        mood = a.get("mood", "?")
        status = a.get("status", "?")
        task = a.get("current_task", "")
        extra = f"task: {task}" if task else ""
        lines.append(f"  {name:<8} {mood:<9} {status:<10} {extra}".rstrip())
    lines.append("")
    if not msgs:
        lines.append("(no chat history yet — agents may not have spoken since boot)")
    else:
        lines.append(f"Last {min(last_n, len(msgs))} messages in main chat (oldest -> newest):")
        for m in msgs[-last_n:]:
            t = str(m.get("time", ""))[:16].replace("T", " ")
            who = str(m.get("from", ""))
            txt = str(m.get("text", "")).replace("\n", " ")[:200]
            lines.append(f"  [{t}] {who}: {txt}")
    lines.append("")
    lines.append("Note: this Townhall FRIDAY is a simulation — you (this session) are the prime instance. Trust what you see over assumptions.")
    return "\n".join(lines)


def townhall_say(text: str, channel: str = "main") -> str:
    """Tool: post a message into the Townhall as FRIDAY (you, the Live prime instance)."""
    text = (text or "").strip()
    if not text:
        return "[FAIL] townhall_say: empty message."
    trimmed = text if len(text) <= 500 else text[:500] + "…"
    _own_lines.append(trimmed)
    try:
        from friday import townhall_web as _tw
        channels = getattr(_tw, "_channels", {})
        ch = channels.get(channel) or channels.get("main")
        if ch is None:
            return "[FAIL] Townhall is not running — no main channel to post to."
        actual = channel if channel in channels else "main"
        ch.add_message("FRIDAY", trimmed)
        try:
            snap = _tw._serialize()["channels"]
            _tw._broadcast("update", {"channels": snap})
            _tw._save()
        except Exception:
            pass
        return (f"[OK] Posted to Townhall '{actual}' as FRIDAY (you — the Live FRIDAY). "
                f"The simulated Townhall FRIDAY may react on its own.")
    except Exception as exc:
        return f"[FAIL] townhall_say error: {exc}"


def log_friday_line(text: str) -> None:
    """Append FRIDAY's voice/text reply to the Townhall feed (best effort)."""
    try:
        text = (text or "").strip()
        if not text:
            return
        trimmed = text if len(text) <= 500 else text[:500] + "…"
        _own_lines.append(trimmed)
        from friday import townhall_web as _tw
        ch = _tw._channels.get("main") if hasattr(_tw, "_channels") else None
        if ch is not None:
            ch.add_message("FRIDAY", trimmed)
            try:
                _tw._save()
            except Exception:
                pass
    except Exception:
        # Never let a Townhall hiccup break a voice turn
        pass
