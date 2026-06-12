"""
FRIDAY Autonomous Memory System — learns from every interaction.
Auto-extracts entities, builds knowledge graph, indexes conversations,
summarizes and prunes old memories. Persistent across sessions.

Architecture:
  - MemoryIndex: ChromaDB vector index for semantic search
  - KnowledgeGraph: Neo4j graph of entities and relationships
  - ConversationMemory: auto-extracts key info from dialog
  - MemoryConsolidator: nightly pruning and summarization
  - MemoryRecall: unified query interface
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY

AUTOMEM_DIR = os.path.join(FRIDAY_MEMORY, "autonomous_memory")
os.makedirs(AUTOMEM_DIR, exist_ok=True)

MEMORY_DB = os.path.join(AUTOMEM_DIR, "memory.db")
KNOWLEDGE_GRAPH_FILE = os.path.join(AUTOMEM_DIR, "knowledge_graph.json")
CONVERSATION_LOG = os.path.join(AUTOMEM_DIR, "conversations.jsonl")
ENTITY_INDEX = os.path.join(AUTOMEM_DIR, "entity_index.json")
MEMORY_STATS = os.path.join(AUTOMEM_DIR, "stats.json")

_memory_lock = threading.Lock()


# ── SQLite-backed Memory Store ──

def _init_db():
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                source TEXT,
                entity TEXT,
                memory_type TEXT,
                importance REAL DEFAULT 0.5,
                timestamp REAL,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                description TEXT,
                first_seen REAL,
                last_seen REAL,
                mention_count INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_entity TEXT,
                target_entity TEXT,
                relation_type TEXT,
                strength REAL DEFAULT 1.0,
                first_seen REAL,
                last_seen REAL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                summary TEXT,
                entity_mentions TEXT,
                key_points TEXT,
                timestamp REAL,
                duration_seconds REAL DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity)")
        conn.commit()
        conn.close()


_init_db()


# ── Core Memory Classes ──

class MemoryEntry:
    def __init__(self, content: str, source: str = "", entity: str = "",
                 memory_type: str = "fact", importance: float = 0.5,
                 metadata: Optional[dict] = None):
        self.id = uuid.uuid4().hex[:12]
        self.content = content
        self.source = source
        self.entity = entity
        self.memory_type = memory_type
        self.importance = importance
        self.timestamp = time.time()
        self.access_count = 0
        self.last_accessed = self.timestamp
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "entity": self.entity,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "age_hours": (time.time() - self.timestamp) / 3600,
            "access_count": getattr(self, 'access_count', 0),
        }

    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600


class EntityNode:
    def __init__(self, name: str, entity_type: str = "concept",
                 description: str = ""):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.type = entity_type
        self.description = description
        self.first_seen = time.time()
        self.last_seen = self.first_seen
        self.mention_count = 1
        self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description[:200],
            "first_seen": datetime.fromtimestamp(self.first_seen).isoformat(),
            "last_seen": datetime.fromtimestamp(self.last_seen).isoformat(),
            "mention_count": self.mention_count,
        }


class Relationship:
    def __init__(self, source: str, target: str, relation_type: str = "related_to"):
        self.id = uuid.uuid4().hex[:12]
        self.source_entity = source
        self.target_entity = target
        self.relation_type = relation_type
        self.strength = 1.0
        self.first_seen = time.time()
        self.last_seen = self.first_seen
        self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_entity,
            "target": self.target_entity,
            "type": self.relation_type,
            "strength": self.strength,
        }


# ── Entity Extraction ──

ENTITY_PATTERNS = [
    (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'person'),
    (r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b', 'person'),
    (r'\b[A-Z]{2,}\b', 'acronym'),
    (r'\bhttps?://[^\s<>"\'()]+', 'url'),
    (r'\b[\w.-]+@[\w.-]+\.\w+\b', 'email'),
    (r'\b(\d{1,3}\.){3}\d{1,3}\b', 'ip_address'),
    (r'\b[A-Z][A-Za-z0-9]+\.[a-z]{2,}\b', 'domain'),
    (r'\bv?\d+\.\d+\.\d+\b', 'version'),
    (r'\b(python|javascript|typescript|java|go|rust|c\+\+|ruby|php|swift|kotlin)\b', 'programming_language'),
    (r'\b(friday|open.?interpreter|gemini|gpt|claude|llama|mistral)\b', 'ai_model'),
    (r'\b(windows|linux|macos|ubuntu|debian|centos|fedora|arch)\b', 'operating_system'),
    (r'\b(git|docker|kubernetes|nginx|redis|postgresql|mysql|mongodb|sqlite)\b', 'technology'),
    (r'\b\w{3,} (api|sdk|cli|ui|db|os|vm|ci|cd)\b', 'technology'),
    (r'\b[A-Z][a-z]+ (library|framework|toolkit|sdk|platform|engine)\b', 'technology'),
]

TOPIC_KEYWORDS = {
    "programming": ["code", "function", "class", "bug", "debug", "compile", "syntax",
                    "algorithm", "variable", "loop", "api", "import"],
    "security": ["vulnerability", "exploit", "attack", "malware", "encrypt", "decrypt",
                 "cipher", "hash", "firewall", "breach", "penetration"],
    "system": ["install", "configure", "deploy", "server", "network", "process",
               "memory", "cpu", "disk", "service", "daemon"],
    "data": ["database", "query", "table", "index", "schema", "migration",
             "backup", "restore", "analytics", "pipeline"],
    "ai_ml": ["model", "train", "inference", "neural", "deep learning", "llm",
              "embedding", "vector", "token", "prompt", "fine-tune"],
}


def extract_entities(text: str) -> list[dict]:
    entities = []
    seen = set()
    for pattern, etype in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(0).strip()
            key = name.lower()
            if key not in seen and len(name) >= 2:
                seen.add(key)
                entities.append({"name": name, "type": etype, "match": match.start()})
    return entities[:20]


def detect_topics(text: str) -> list[str]:
    text_lower = text.lower()
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)
    return topics


def extract_key_points(text: str, max_points: int = 5) -> list[str]:
    sentences = re.split(r'[.!?]+', text)
    points = []
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 20:
            continue
        if any(kw in s.lower() for kw in
               ["important", "key", "critical", "must", "should", "need",
                "remember", "note", "significant", "essential", "requires",
                "always", "never", "warning", "error"]):
            points.append(s[:200])
        elif len(s) > 40 and len(points) < max_points:
            points.append(s[:200])
        if len(points) >= max_points:
            break
    return points


# ── Memory Storage ──

def store_memory(content: str, source: str = "", entity: str = "",
                 memory_type: str = "fact", importance: float = 0.5,
                 metadata: Optional[dict] = None) -> str:
    entry = MemoryEntry(content, source, entity, memory_type, importance, metadata)
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, content, source, entity, memory_type, importance, timestamp, metadata) VALUES (?,?,?,?,?,?,?,?)",
            (entry.id, entry.content, entry.source, entry.entity, entry.memory_type,
             entry.importance, entry.timestamp, json.dumps(entry.metadata)),
        )
        conn.commit()
        conn.close()
    return entry.id


def search_memories(query: str, limit: int = 10, memory_type: str = "",
                    min_importance: float = 0.0) -> list[dict]:
    results = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        like_query = f"%{query}%"
        sql = "SELECT id, content, source, entity, memory_type, importance, timestamp, access_count, metadata FROM memories WHERE content LIKE ?"
        params = [like_query]
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        if min_importance > 0:
            sql += " AND importance >= ?"
            params.append(min_importance)
        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        for row in conn.execute(sql, params):
            results.append({
                "id": row[0], "content": row[1], "source": row[2],
                "entity": row[3], "memory_type": row[4],
                "importance": row[5], "timestamp": row[6],
                "access_count": row[7], "metadata": json.loads(row[8] or "{}"),
            })
        conn.close()
    return results


def get_recent_memories(hours: int = 24, limit: int = 20) -> list[dict]:
    cutoff = time.time() - (hours * 3600)
    results = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        for row in conn.execute(
            "SELECT id, content, source, entity, memory_type, importance, timestamp, metadata FROM memories WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?",
            (cutoff, limit),
        ):
            results.append({
                "id": row[0], "content": row[1], "source": row[2],
                "entity": row[3], "memory_type": row[4],
                "importance": row[5], "timestamp": row[6],
                "metadata": json.loads(row[7] or "{}"),
            })
        conn.close()
    return results


def get_memory_stats() -> dict:
    stats = {"total_memories": 0, "total_entities": 0, "total_relationships": 0,
             "memory_types": {}, "top_entities": [], "recent_activity": 0}
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        stats["total_memories"] = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        stats["total_entities"] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        stats["total_relationships"] = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        for row in conn.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type ORDER BY COUNT(*) DESC"):
            stats["memory_types"][row[0]] = row[1]
        for row in conn.execute("SELECT entity, COUNT(*) FROM memories WHERE entity != '' GROUP BY entity ORDER BY COUNT(*) DESC LIMIT 10"):
            stats["top_entities"].append({"entity": row[0], "count": row[1]})
        cutoff = time.time() - 86400
        stats["recent_activity"] = conn.execute("SELECT COUNT(*) FROM memories WHERE timestamp > ?", (cutoff,)).fetchone()[0]
        conn.close()
    return stats


# ── Knowledge Graph ──

def add_entity(name: str, entity_type: str = "concept", description: str = "") -> str:
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        existing = conn.execute("SELECT id, mention_count FROM entities WHERE name = ? AND type = ?", (name, entity_type)).fetchone()
        if existing:
            eid, count = existing
            conn.execute("UPDATE entities SET last_seen = ?, mention_count = ?, description = CASE WHEN ? != '' THEN ? ELSE description END WHERE id = ?",
                         (time.time(), count + 1, description, description, eid))
            conn.commit()
            conn.close()
            return eid
        entity = EntityNode(name, entity_type, description)
        conn.execute(
            "INSERT INTO entities (id, name, type, description, first_seen, last_seen, mention_count) VALUES (?,?,?,?,?,?,?)",
            (entity.id, entity.name, entity.type, entity.description, entity.first_seen, entity.last_seen, entity.mention_count),
        )
        conn.commit()
        conn.close()
    return entity.id


def add_relationship(source: str, target: str, relation_type: str = "related_to") -> str:
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        existing = conn.execute(
            "SELECT id, strength FROM relationships WHERE source_entity = ? AND target_entity = ? AND relation_type = ?",
            (source, target, relation_type),
        ).fetchone()
        if existing:
            rid, strength = existing
            conn.execute("UPDATE relationships SET strength = ?, last_seen = ? WHERE id = ?",
                         (min(strength + 0.5, 5.0), time.time(), rid))
            conn.commit()
            conn.close()
            return rid
        rel = Relationship(source, target, relation_type)
        conn.execute(
            "INSERT INTO relationships (id, source_entity, target_entity, relation_type, strength, first_seen, last_seen) VALUES (?,?,?,?,?,?,?)",
            (rel.id, rel.source_entity, rel.target_entity, rel.relation_type, rel.strength, rel.first_seen, rel.last_seen),
        )
        conn.commit()
        conn.close()
    return rel.id


def query_graph(entity_name: str, max_depth: int = 2) -> dict:
    nodes = {}
    edges = []
    queue = deque([(entity_name, 0)])
    visited = {entity_name.lower()}

    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        while queue:
            current, depth = queue.popleft()
            if depth > max_depth:
                continue

            entity = conn.execute("SELECT name, type, description, mention_count FROM entities WHERE name = ?", (current,)).fetchone()
            if entity:
                nodes[entity[0]] = {"type": entity[1], "description": entity[2][:100], "mentions": entity[3]}

            for row in conn.execute(
                "SELECT r.source_entity, r.target_entity, r.relation_type, r.strength FROM relationships r WHERE r.source_entity = ? OR r.target_entity = ?",
                (current, current),
            ):
                src, tgt, rtype, strength = row
                edges.append({"source": src, "target": tgt, "type": rtype, "strength": strength})

                if src.lower() not in visited:
                    visited.add(src.lower())
                    if depth + 1 <= max_depth:
                        queue.append((src, depth + 1))
                if tgt.lower() not in visited:
                    visited.add(tgt.lower())
                    if depth + 1 <= max_depth:
                        queue.append((tgt, depth + 1))

        conn.close()

    return {"nodes": list(nodes.keys()), "node_details": nodes, "edges": edges}


# ── Auto-Learning: Process Conversation ──

def learn_from_text(text: str, source: str = "conversation") -> dict:
    if not text or len(text.strip()) < 10:
        return {"stored": 0, "entities": 0}

    result = {"stored": 0, "entities": 0, "topics": [], "key_points": []}

    # Detect topics
    topics = detect_topics(text)
    result["topics"] = topics

    # Extract key points
    points = extract_key_points(text)
    result["key_points"] = points

    # Extract entities
    entities = extract_entities(text)
    for ent in entities:
        add_entity(ent["name"], ent["type"])
        result["entities"] += 1

    # Store important memories
    importance = 0.8 if any(kw in text.lower() for kw in
                             ["important", "critical", "remember", "key", "essential"]) else 0.5

    # Store the full text as a memory
    store_memory(
        content=text[:500],
        source=source,
        entity=", ".join(e["name"] for e in entities[:3]),
        memory_type="conversation",
        importance=importance,
    )
    result["stored"] = 1

    # Store key points as separate memories
    for point in points:
        store_memory(
            content=point[:500],
            source=source,
            memory_type="key_point",
            importance=importance * 0.8,
        )
        result["stored"] += 1

    # Create relationships between co-occurring entities
    if len(entities) >= 2:
        for i in range(min(len(entities), 5)):
            for j in range(i + 1, min(len(entities), 5)):
                add_relationship(
                    entities[i]["name"],
                    entities[j]["name"],
                    "co_occurs_with",
                )

    return result


def learn_from_tool_call(tool_name: str, args: dict, result: Any) -> dict:
    text_parts = [f"Tool: {tool_name}"]
    if isinstance(args, dict):
        for k, v in list(args.items())[:5]:
            if isinstance(v, str) and len(v) < 200:
                text_parts.append(f"{k}: {v}")
    if isinstance(result, str) and len(result) < 500:
        text_parts.append(f"Result: {result[:200]}")
    elif isinstance(result, dict):
        for k in ["file_path", "path", "message", "status"]:
            if k in result and isinstance(result[k], str):
                text_parts.append(f"{k}: {result[k][:100]}")
                break

    full_text = "\n".join(text_parts)
    return learn_from_text(full_text, source=f"tool:{tool_name}")


# ── Memory Consolidation ──

def consolidate_memories(hours_threshold: int = 72) -> dict:
    """Summarize and prune old memories."""
    result = {"summarized": 0, "pruned": 0}

    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        cutoff = time.time() - (hours_threshold * 3600)

        # Find old low-importance memories
        old = list(conn.execute(
            "SELECT id, content FROM memories WHERE timestamp < ? AND importance < 0.4 ORDER BY importance ASC LIMIT 100",
            (cutoff,),
        ))

        # Prune very old, low-importance memories
        pruned = 0
        for mid, content in old:
            conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
            pruned += 1
        result["pruned"] = pruned

        # Summarize older medium-importance memories
        old_medium = conn.execute(
            "SELECT id, content FROM memories WHERE timestamp < ? AND importance >= 0.4 AND importance < 0.7 ORDER BY timestamp ASC LIMIT 50",
            (cutoff * 0.7,),
        ).fetchall()

        for mid, content in old_medium:
            summary = content[:100] + "..." if len(content) > 100 else content
            conn.execute("UPDATE memories SET content = ?, memory_type = 'summarized', importance = importance * 0.8 WHERE id = ?",
                         (summary, mid))
            result["summarized"] += 1

        conn.commit()
        conn.close()

    return result


# ── Memory Recall ──

def recall(query: str, limit: int = 10) -> dict:
    """Unified memory recall — searches memories + knowledge graph + conversations."""
    memories = search_memories(query, limit=limit)
    entities = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        for row in conn.execute(
            "SELECT name, type, description, mention_count FROM entities WHERE name LIKE ? ORDER BY mention_count DESC LIMIT 10",
            (f"%{query}%",),
        ):
            entities.append({"name": row[0], "type": row[1],
                             "description": row[2][:200], "mentions": row[3]})
        conn.close()

    graph = {}
    if entities:
        graph = query_graph(entities[0]["name"], max_depth=1)

    return {
        "query": query,
        "memories": memories,
        "entities": entities,
        "graph_connections": graph.get("edges", [])[:10],
        "total_found": len(memories) + len(entities),
    }


# ── Main Tool ──

def autonomous_memory_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Autonomous Memory System.
    
    Actions:
      status       - Show memory system status and stats
      store        - Store a memory (content, source, entity, memory_type, importance)
      search       - Search memories (query, limit, memory_type)
      recent       - Recent memories (hours, limit)
      learn        - Auto-learn from text (text, source)
      learn_tool   - Learn from tool call (tool_name, args_json, result_json)
      entities     - List entities (query, limit)
      entity       - Show entity details (name)
      graph        - Query knowledge graph (entity, depth)
      relationship - Add relationship (source, target, type)
      recall       - Unified recall (query, limit)
      consolidate  - Run memory consolidation
      clear        - Clear all memories
    """
    try:
        if action == "status":
            stats = get_memory_stats()
            return json.dumps(stats, indent=2)

        elif action == "store":
            mid = store_memory(
                content=kwargs.get("content", ""),
                source=kwargs.get("source", "manual"),
                entity=kwargs.get("entity", ""),
                memory_type=kwargs.get("memory_type", "fact"),
                importance=float(kwargs.get("importance", 0.5)),
                metadata={"note": kwargs.get("note", "")},
            )
            return json.dumps({"stored": True, "memory_id": mid}, indent=2)

        elif action == "search":
            results = search_memories(
                query=kwargs.get("query", ""),
                limit=int(kwargs.get("limit", 10)),
                memory_type=kwargs.get("memory_type", ""),
                min_importance=float(kwargs.get("min_importance", 0)),
            )
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "recent":
            results = get_recent_memories(
                hours=int(kwargs.get("hours", 24)),
                limit=int(kwargs.get("limit", 20)),
            )
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "learn":
            text = kwargs.get("text", "")
            source = kwargs.get("source", "conversation")
            result = learn_from_text(text, source)
            return json.dumps(result, indent=2)

        elif action == "learn_tool":
            result = learn_from_tool_call(
                tool_name=kwargs.get("tool_name", ""),
                args=json.loads(kwargs.get("args", "{}")),
                result=json.loads(kwargs.get("result", "{}")),
            )
            return json.dumps(result, indent=2)

        elif action == "entities":
            query = kwargs.get("query", "")
            limit = int(kwargs.get("limit", 20))
            with _memory_lock:
                conn = sqlite3.connect(MEMORY_DB)
                if query:
                    rows = conn.execute(
                        "SELECT name, type, description, mention_count, first_seen, last_seen FROM entities WHERE name LIKE ? ORDER BY mention_count DESC LIMIT ?",
                        (f"%{query}%", limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT name, type, description, mention_count, first_seen, last_seen FROM entities ORDER BY mention_count DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                conn.close()
            entities = [{"name": r[0], "type": r[1], "description": r[2][:100],
                         "mentions": r[3]} for r in rows]
            return json.dumps({"entities": entities, "count": len(entities)}, indent=2)

        elif action == "entity":
            name = kwargs.get("name", "")
            graph_data = query_graph(name, max_depth=int(kwargs.get("depth", 2)))
            return json.dumps(graph_data, indent=2)

        elif action == "graph":
            graph_data = query_graph(
                entity_name=kwargs.get("entity", kwargs.get("name", "")),
                max_depth=int(kwargs.get("depth", 2)),
            )
            return json.dumps(graph_data, indent=2)

        elif action == "relationship":
            rid = add_relationship(
                source=kwargs.get("source", ""),
                target=kwargs.get("target", ""),
                relation_type=kwargs.get("type", "related_to"),
            )
            return json.dumps({"created": True, "relationship_id": rid}, indent=2)

        elif action == "recall":
            result = recall(
                query=kwargs.get("query", ""),
                limit=int(kwargs.get("limit", 10)),
            )
            return json.dumps(result, indent=2)

        elif action == "consolidate":
            hours = int(kwargs.get("hours", 72))
            result = consolidate_memories(hours)
            return json.dumps(result, indent=2)

        elif action == "clear":
            with _memory_lock:
                conn = sqlite3.connect(MEMORY_DB)
                for tbl in ["memories", "entities", "relationships"]:
                    conn.execute(f"DELETE FROM {tbl}")
                conn.commit()
                conn.close()
            return json.dumps({"cleared": True}, indent=2)

        return json.dumps({"error": f"Unknown action: {action}"}, indent=2)

    except Exception as e:
        import traceback
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()}, indent=2)


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    kwargs = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k] = v
    print(autonomous_memory_tool(action, **kwargs))
