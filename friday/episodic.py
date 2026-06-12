"""Friday Episodic Archive — SQLite-backed full-text session memory.
Records tool calls, user messages, and Friday responses for searchable
long-term episodic recall using FTS5 (fallback to LIKE search)."""

from __future__ import annotations
import os
import json
import uuid
import sqlite3
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_DB_PATH = os.path.join(FRIDAY_MEMORY, "episodic.db")
_fts_available: Optional[bool] = None


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection):
    global _fts_available
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            speaker TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_name TEXT,
            metadata TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_session ON episodes(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_ts ON episodes(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_speaker ON episodes(speaker)")

    if _fts_available is None:
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts "
                "USING fts5(content, content='episodes', content_rowid='id')"
            )
            _fts_available = True
        except Exception:
            _fts_available = False

    if _fts_available:
        try:
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS ep_fts_ai AFTER INSERT ON episodes
                BEGIN
                    INSERT INTO episodes_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)
        except Exception:
            pass


def record(
    session_id: Optional[str] = None,
    speaker: str = "tool",
    content: str = "",
    tool_name: Optional[str] = None,
    metadata: Optional[dict] = None,
    embed: bool = True,
) -> str:
    """Record an episodic entry. Returns the session_id.
    If embed=True, also stores a semantic embedding in vector memory."""
    sid = session_id or str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO episodes (session_id, timestamp, speaker, content, tool_name, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, datetime.now().isoformat(), speaker, content, tool_name,
             json.dumps(metadata) if metadata else None),
        )
        conn.commit()
    finally:
        conn.close()

    if embed and len(content) > 20:
        try:
            from friday.vector_memory import get_vector_memory
            vm = get_vector_memory()
            if vm.is_available():
                import hashlib
                embed_id = hashlib.md5(f"{sid}_{datetime.now().isoformat()}_{content[:100]}".encode()).hexdigest()
                vm.add(
                    text=f"[{tool_name or speaker}] {content[:1500]}",
                    metadata={
                        "source": speaker,
                        "tool": tool_name or "",
                        "session": sid[:8],
                        "timestamp": datetime.now().isoformat(),
                    },
                    id=embed_id,
                )
        except Exception:
            pass

    return sid


def get_current_session() -> str:
    """Get or create a persistent session ID for this boot cycle."""
    sid_file = os.path.join(FRIDAY_MEMORY, ".episodic_session")
    try:
        if os.path.exists(sid_file):
            with open(sid_file) as f:
                sid = f.read().strip()
                if sid:
                    return sid
    except Exception:
        pass
    sid = str(uuid.uuid4())
    try:
        with open(sid_file, "w") as f:
            f.write(sid)
    except Exception:
        pass
    return sid


def _format_rows(rows: list) -> str:
    if not rows:
        return "No episodes found."
    lines = [f"### EPISODIC MEMORY ({len(rows)} found)"]
    for r in rows:
        d = dict(r)
        ts = d.get("timestamp", "?")[:19]
        sp = d.get("speaker", "?")
        content = d.get("content", "")[:200]
        tn = d.get("tool_name", "")
        label = f"[{tn}] " if tn else ""
        lines.append(f"  [{ts}] {sp}: {label}{content}")
    return "\n".join(lines)


def search(query: str, limit: int = 10) -> str:
    """Full-text search across all episodes."""
    conn = _get_conn()
    try:
        if _fts_available:
            rows = conn.execute(
                "SELECT e.* FROM episodes_fts f JOIN episodes e ON f.rowid = e.id "
                "WHERE episodes_fts MATCH ? ORDER BY e.timestamp DESC LIMIT ?",
                (query, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
    finally:
        conn.close()
    return _format_rows(rows)


def recent(limit: int = 20, speaker: Optional[str] = None) -> str:
    """Get most recent episodes."""
    conn = _get_conn()
    try:
        if speaker:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE speaker = ? ORDER BY timestamp DESC LIMIT ?",
                (speaker, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return _format_rows(rows)


def get_session(session_id: str) -> str:
    """Get all entries for a specific session."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM episodes WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return f"No session found: {session_id}"
    lines = [f"### SESSION {session_id[:8]}... ({len(rows)} entries)"]
    for r in rows:
        d = dict(r)
        ts = d["timestamp"][:19]
        sp = d["speaker"]
        content = d["content"][:300]
        tn = d.get("tool_name", "")
        label = f"[{tn}] " if tn else ""
        lines.append(f"  [{ts}] {sp}: {label}{content}")
    return "\n".join(lines)


def stats() -> str:
    """Get archive statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) as c FROM episodes").fetchone()["c"]
        sessions = conn.execute("SELECT COUNT(DISTINCT session_id) as c FROM episodes").fetchone()["c"]
        by_speaker = conn.execute(
            "SELECT speaker, COUNT(*) as c FROM episodes GROUP BY speaker ORDER BY c DESC"
        ).fetchall()
        by_tool = conn.execute(
            "SELECT tool_name, COUNT(*) as c FROM episodes WHERE tool_name IS NOT NULL "
            "GROUP BY tool_name ORDER BY c DESC LIMIT 10"
        ).fetchall()
        latest = conn.execute("SELECT MAX(timestamp) as c FROM episodes").fetchone()["c"]
    finally:
        conn.close()

    lines = [f"Episodic Archive: {total} entries across {sessions} sessions"]
    if by_speaker:
        lines.append("  By speaker: " + ", ".join(f"{r['speaker']}={r['c']}" for r in by_speaker))
    if by_tool:
        lines.append("  Top tools: " + ", ".join(f"{r['tool_name']}({r['c']})" for r in by_tool[:5]))
    if latest:
        lines.append(f"  Latest entry: {latest[:19]}")
    return "\n".join(lines)


def episodic_tool(action: str = "status", **kwargs) -> str:
    """Episodic memory: record and search past sessions with full-text + semantic search.
    Actions: search (FTS query), search_semantic (vector/meaning-based query), recent (last N),
    record (manual entry), session (full session by id), stats, status."""
    try:
        if action == "search":
            q = kwargs.get("query", "")
            if not q:
                return "[FAIL] Query required for search."
            return search(q, limit=kwargs.get("limit", 10))
        elif action == "search_semantic":
            q = kwargs.get("query", "")
            if not q:
                return "[FAIL] Query required for semantic search."
            return search_semantic(q, limit=kwargs.get("limit", 10))
        elif action == "recent":
            return recent(limit=kwargs.get("limit", 20), speaker=kwargs.get("speaker"))
        elif action == "record":
            sid = record(
                session_id=kwargs.get("session_id"),
                speaker=kwargs.get("speaker", "user"),
                content=kwargs.get("content", ""),
                tool_name=kwargs.get("tool_name"),
            )
            return f"[OK] Recorded to session {sid[:8]}..."
        elif action == "session":
            sid = kwargs.get("session_id", "")
            if not sid:
                return "[FAIL] session_id required."
            return get_session(sid)
        elif action == "stats":
            return stats()
        elif action == "status":
            s = stats()
            # Also show whether FTS is active
            fts = "enabled" if _fts_available else "disabled (fallback LIKE search)"
            return s + f"\nFTS5: {fts}"
        else:
            return f"[FAIL] Unknown action: {action}"
    except Exception as e:
        return f"[FAIL] Episodic error: {e}"


def search_semantic(query: str, limit: int = 10) -> str:
    """Semantic search across episodes using vector embeddings."""
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        if vm.is_available():
            results = vm.search(query, n_results=limit)
            if results and "error" not in results[0]:
                lines = [f"### SEMANTIC EPISODIC MEMORY ({len(results)} found)"]
                for i, r in enumerate(results, 1):
                    text = r["text"][:200]
                    meta = r.get("metadata", {})
                    ts = meta.get("timestamp", "")[:19]
                    src = meta.get("source", "")
                    lines.append(f"  {i}. [{ts}] {src}: {text}")
                return "\n".join(lines)
        return search(query, limit=limit)
    except Exception:
        return search(query, limit=limit)


def auto_record_tool_call(name: str, args: dict, result: str, session=None) -> None:
    """Post-hook: auto-record every tool call to episodic memory."""
    no_record = {"episodic_tool", "get_time", "system_cpu", "system_memory",
                 "system_disk", "system_network", "scroll", "move_mouse",
                 "opencli_screenshot", "system_processes", "status_check",
                 "get_active_window", "list_running_apps", "clock_tool"}
    if name in no_record:
        return
    try:
        sid = get_current_session()
        result_str = str(result)[:500]
        speaker = "user" if name == "text_input" else "tool"
        content = f"{name}({json.dumps({k: str(v)[:80] for k, v in args.items()})}) -> {result_str}"
        record(session_id=sid, speaker=speaker, content=content, tool_name=name,
               metadata={"args": str(args)[:200], "result": result_str[:200]})
    except Exception:
        pass
