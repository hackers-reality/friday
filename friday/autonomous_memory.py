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

Expanded features:
  - SemanticIndex: hash-based embedding semantic search
  - MemoryDecayScheduler: automatic importance decay
  - TagManager: memory tagging and tag-based retrieval
  - ConversationMemory: structured conversation tracking
  - Memory Import/Export: JSON, JSONL formats
  - DetailedStats: comprehensive memory analytics
  - Memory linking: explicit typed links between memories
  - SpatialIndex: location-tagged memories with proximity search
  - TemporalIndex: time-based memory queries
  - Conflict detection: contradiction detection and resolution
  - Importance heuristics: multi-factor importance calculation
  - Reminders: time-based memory-triggered notifications
  - Batch learning: file/directory/conversation log processing
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
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
    """Initialize all database tables. Idempotent — uses CREATE TABLE IF NOT EXISTS."""
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id TEXT,
                tag TEXT,
                PRIMARY KEY (memory_id, tag)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id TEXT PRIMARY KEY,
                memory_id_a TEXT,
                memory_id_b TEXT,
                link_type TEXT,
                created REAL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_locations (
                id TEXT PRIMARY KEY,
                name TEXT,
                latitude REAL,
                longitude REAL,
                description TEXT,
                created REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                content TEXT,
                trigger_time REAL,
                created REAL,
                dismissed INTEGER DEFAULT 0,
                notified INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id TEXT PRIMARY KEY,
                embedding TEXT,
                updated REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id TEXT PRIMARY KEY,
                memory_id_a TEXT,
                memory_id_b TEXT,
                description TEXT,
                conflict_type TEXT,
                detected_at REAL,
                resolved_at REAL,
                resolution TEXT,
                superseded_id TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_links_a ON memory_links(memory_id_a)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_links_b ON memory_links(memory_id_b)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_trigger ON reminders(trigger_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_conflicts_a ON memory_conflicts(memory_id_a)")
        conn.commit()
        conn.close()


_init_db()


# ── Core Memory Classes ──

class MemoryEntry:
    """Represents a single memory with content, source, type, and importance."""

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
    """Represents an entity in the knowledge graph."""

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
    """Represents a typed relationship between two entities."""

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
    """Extract named entities from text using regex patterns."""
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
    """Detect topics present in text using keyword matching."""
    text_lower = text.lower()
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)
    return topics


def extract_key_points(text: str, max_points: int = 5) -> list[str]:
    """Extract key points from text based on importance keywords."""
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
    """Store a memory entry in the database and return its ID."""
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
    """Search memories by text content with optional type and importance filters."""
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
    """Get memories from the last N hours."""
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
    """Get basic memory system statistics."""
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


def _touch_memory(memory_id: str):
    """Update access count and last_accessed timestamp for a memory."""
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
            (time.time(), memory_id),
        )
        conn.commit()
        conn.close()


# ── Knowledge Graph ──

def add_entity(name: str, entity_type: str = "concept", description: str = "") -> str:
    """Add or update an entity in the knowledge graph."""
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
    """Add or strengthen a relationship between two entities."""
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
    """Query the knowledge graph centered on an entity with BFS up to max_depth."""
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
    """Auto-learn from a text: extract entities, topics, key points, and store memories."""
    if not text or len(text.strip()) < 10:
        return {"stored": 0, "entities": 0}

    result = {"stored": 0, "entities": 0, "topics": [], "key_points": []}

    topics = detect_topics(text)
    result["topics"] = topics

    points = extract_key_points(text)
    result["key_points"] = points

    entities = extract_entities(text)
    for ent in entities:
        add_entity(ent["name"], ent["type"])
        result["entities"] += 1

    importance = 0.8 if any(kw in text.lower() for kw in
                             ["important", "critical", "remember", "key", "essential"]) else 0.5

    store_memory(
        content=text[:500],
        source=source,
        entity=", ".join(e["name"] for e in entities[:3]),
        memory_type="conversation",
        importance=importance,
    )
    result["stored"] = 1

    for point in points:
        store_memory(
            content=point[:500],
            source=source,
            memory_type="key_point",
            importance=importance * 0.8,
        )
        result["stored"] += 1

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
    """Learn from a tool call by extracting meaningful information."""
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
    """Summarize and prune old memories. Removes low-importance old entries, summarizes medium ones."""
    result = {"summarized": 0, "pruned": 0}

    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        cutoff = time.time() - (hours_threshold * 3600)

        old = list(conn.execute(
            "SELECT id, content FROM memories WHERE timestamp < ? AND importance < 0.4 ORDER BY importance ASC LIMIT 100",
            (cutoff,),
        ))

        pruned = 0
        for mid, content in old:
            conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
            conn.execute("DELETE FROM memory_tags WHERE memory_id = ?", (mid,))
            conn.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (mid,))
            pruned += 1
        result["pruned"] = pruned

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


# ── Embedding-based Semantic Search ──

def compute_embedding(text: str, dimensions: int = 256) -> list[float]:
    """Compute a hash-based embedding vector using character n-gram hashing."""
    vec = [0.0] * dimensions
    text_lower = text.lower()
    for n in [2, 3, 4]:
        for i in range(len(text_lower) - n + 1):
            gram = text_lower[i:i + n]
            h = int(hashlib.md5(gram.encode()).hexdigest()[:8], 16)
            idx = h % dimensions
            vec[idx] += 1.0
    mag = math.sqrt(sum(v * v for v in vec))
    if mag > 0:
        vec = [v / mag for v in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(ai * bi for ai, bi in zip(a, b))
    na = math.sqrt(sum(ai * ai for ai in a))
    nb = math.sqrt(sum(bi * bi for bi in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticIndex:
    """In-memory embedding index for semantic memory search.

    Builds from stored memories and provides cosine-similarity ranked search.
    """

    def __init__(self):
        self.embeddings: dict[str, list[float]] = {}
        self.content_cache: dict[str, str] = {}
        self._built = False

    def build(self) -> int:
        """Build the index from all stored memory embeddings."""
        self.embeddings.clear()
        self.content_cache.clear()
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            cached = conn.execute("SELECT memory_id, embedding FROM memory_embeddings").fetchall()
            rows = conn.execute("SELECT id, content FROM memories").fetchall()
            conn.close()
        stored_emb = {row[0]: json.loads(row[1]) for row in cached}
        for mid, content in rows:
            self.content_cache[mid] = content
            if mid in stored_emb:
                self.embeddings[mid] = stored_emb[mid]
            else:
                emb = compute_embedding(content)
                self.embeddings[mid] = emb
                with _memory_lock:
                    c = sqlite3.connect(MEMORY_DB)
                    c.execute(
                        "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, updated) VALUES (?,?,?)",
                        (mid, json.dumps(emb), time.time()),
                    )
                    c.commit()
                    c.close()
        self._built = True
        return len(self.embeddings)

    def add_memory(self, memory_id: str, content: str):
        """Add a single memory to the index."""
        self.content_cache[memory_id] = content
        emb = compute_embedding(content)
        self.embeddings[memory_id] = emb
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, updated) VALUES (?,?,?)",
                (memory_id, json.dumps(emb), time.time()),
            )
            conn.commit()
            conn.close()

    def remove_memory(self, memory_id: str):
        """Remove a memory from the index."""
        self.embeddings.pop(memory_id, None)
        self.content_cache.pop(memory_id, None)
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,))
            conn.commit()
            conn.close()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search memories by semantic similarity to the query."""
        if not self._built:
            self.build()
        query_emb = compute_embedding(query)
        scored = []
        for mid, emb in self.embeddings.items():
            sim = cosine_similarity(query_emb, emb)
            scored.append((sim, mid))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, mid in scored[:limit]:
            content = self.content_cache.get(mid, "")
            results.append({
                "id": mid,
                "content": content,
                "similarity": round(sim, 4),
            })
        return results

    def rebuild(self) -> int:
        """Force a full rebuild of the index from the database."""
        self._built = False
        return self.build()


# ── Memory Decay ──

def apply_decay(days_per_decay: float = 1.0, decay_amount: float = 0.1,
                prune_below: float = 0.1) -> dict:
    """Apply importance decay to old or unaccessed memories.

    Memories lose `decay_amount` importance per `days_per_decay` since last access.
    Those falling below `prune_below` are deleted.
    """
    result = {"decayed": 0, "pruned": 0}
    now = time.time()
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute(
            "SELECT id, importance, last_accessed, timestamp FROM memories"
        ).fetchall()
        for mid, imp, last_acc, ts in rows:
            last = last_acc or ts
            days_since = (now - last) / 86400.0
            if days_since >= days_per_decay:
                decay_steps = int(days_since / days_per_decay)
                new_imp = imp - (decay_steps * decay_amount)
                new_imp = max(0.0, new_imp)
                if new_imp < prune_below:
                    conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
                    conn.execute("DELETE FROM memory_tags WHERE memory_id = ?", (mid,))
                    conn.execute("DELETE FROM memory_embeddings WHERE memory_id = ?", (mid,))
                    result["pruned"] += 1
                else:
                    conn.execute(
                        "UPDATE memories SET importance = ? WHERE id = ?",
                        (new_imp, mid),
                    )
                    result["decayed"] += 1
        conn.commit()
        conn.close()
    return result


class MemoryDecayScheduler:
    """Background thread that periodically applies memory decay.

    Runs `apply_decay` at a configurable interval. Designed to run as a daemon.
    """

    def __init__(self, interval: int = 3600, days_per_decay: float = 1.0,
                 decay_amount: float = 0.1, prune_below: float = 0.1):
        self.interval = interval
        self.days_per_decay = days_per_decay
        self.decay_amount = decay_amount
        self.prune_below = prune_below
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _run(self):
        while not self._stop.is_set():
            try:
                apply_decay(self.days_per_decay, self.decay_amount, self.prune_below)
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        """Start the decay scheduler in a daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="memory-decay")
        self._thread.start()

    def stop(self):
        """Signal the scheduler thread to stop."""
        self._stop.set()

    def is_running(self) -> bool:
        """Check if the scheduler thread is alive."""
        return self._thread is not None and self._thread.is_alive()


# ── Memory Tagging System ──

class TagManager:
    """Manages tagging of memories with string tags for categorization and retrieval."""

    def add_tag(self, memory_id: str, tag: str) -> bool:
        """Add a tag to a memory. Returns True if added, False if already exists."""
        tag = tag.strip().lower().replace(" ", "_")
        if not tag:
            return False
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            exists = conn.execute(
                "SELECT 1 FROM memory_tags WHERE memory_id = ? AND tag = ?",
                (memory_id, tag),
            ).fetchone()
            if exists:
                conn.close()
                return False
            conn.execute(
                "INSERT INTO memory_tags (memory_id, tag) VALUES (?,?)",
                (memory_id, tag),
            )
            conn.commit()
            conn.close()
        return True

    def remove_tag(self, memory_id: str, tag: str) -> bool:
        """Remove a tag from a memory. Returns True if removed."""
        tag = tag.strip().lower().replace(" ", "_")
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            cur = conn.execute(
                "DELETE FROM memory_tags WHERE memory_id = ? AND tag = ?",
                (memory_id, tag),
            )
            removed = cur.rowcount > 0
            conn.commit()
            conn.close()
        return removed

    def search_by_tag(self, tag: str, limit: int = 20) -> list[dict]:
        """Find all memories with a given tag."""
        tag = tag.strip().lower().replace(" ", "_")
        results = []
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                """SELECT m.id, m.content, m.source, m.memory_type, m.importance,
                          m.timestamp, m.metadata
                   FROM memories m
                   JOIN memory_tags t ON m.id = t.memory_id
                   WHERE t.tag = ?
                   ORDER BY m.importance DESC, m.timestamp DESC
                   LIMIT ?""",
                (tag, limit),
            ).fetchall()
            conn.close()
        for row in rows:
            results.append({
                "id": row[0], "content": row[1], "source": row[2],
                "memory_type": row[3], "importance": row[4],
                "timestamp": row[5], "metadata": json.loads(row[6] or "{}"),
            })
        return results

    def get_all_tags(self) -> list[str]:
        """Get a list of all unique tags."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT DISTINCT tag FROM memory_tags ORDER BY tag"
            ).fetchall()
            conn.close()
        return [r[0] for r in rows]

    def get_popular_tags(self, limit: int = 10) -> list[dict]:
        """Get the most frequently used tags with counts."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT tag, COUNT(*) as cnt FROM memory_tags GROUP BY tag ORDER BY cnt DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
        return [{"tag": r[0], "count": r[1]} for r in rows]

    def get_memory_tags(self, memory_id: str) -> list[str]:
        """Get all tags for a specific memory."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT tag FROM memory_tags WHERE memory_id = ? ORDER BY tag",
                (memory_id,),
            ).fetchall()
            conn.close()
        return [r[0] for r in rows]

    def clear_tags(self, memory_id: str) -> int:
        """Remove all tags from a memory. Returns number of tags removed."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            cur = conn.execute(
                "DELETE FROM memory_tags WHERE memory_id = ?",
                (memory_id,),
            )
            count = cur.rowcount
            conn.commit()
            conn.close()
        return count


# ── Conversation Memory ──

class ConversationMemory:
    """Groups messages into conversations, tracks participants, generates summaries."""

    def __init__(self):
        self.current_conversation_id: Optional[str] = None
        self.messages: list[dict] = []
        self.participants: set[str] = set()
        self.start_time: float = time.time()
        self.topics: list[str] = []

    def start_conversation(self, metadata: Optional[dict] = None) -> str:
        """Start a new conversation and return its ID."""
        self.current_conversation_id = uuid.uuid4().hex[:12]
        self.messages = []
        self.participants = set()
        self.start_time = time.time()
        self.topics = []
        conv_data = {
            "id": self.current_conversation_id,
            "summary": "",
            "entity_mentions": json.dumps([]),
            "key_points": json.dumps([]),
            "timestamp": self.start_time,
            "duration_seconds": 0,
            "message_count": 0,
            "metadata": json.dumps(metadata or {}),
        }
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute(
                """INSERT INTO conversations
                   (id, summary, entity_mentions, key_points, timestamp,
                    duration_seconds, message_count, metadata)
                   VALUES (:id, :summary, :entity_mentions, :key_points,
                           :timestamp, :duration_seconds, :message_count, :metadata)""",
                conv_data,
            )
            conn.commit()
            conn.close()
        return self.current_conversation_id

    def add_message(self, role: str, content: str, participant: str = "") -> dict:
        """Add a message to the current conversation and auto-extract entities/topics."""
        if not self.current_conversation_id:
            self.start_conversation()
        message = {
            "role": role,
            "content": content,
            "participant": participant or role,
            "timestamp": time.time(),
        }
        self.messages.append(message)
        if participant:
            self.participants.add(participant)

        entities = extract_entities(content)
        for ent in entities:
            add_entity(ent["name"], ent["type"])

        topics = detect_topics(content)
        for t in topics:
            if t not in self.topics:
                self.topics.append(t)

        key_points = extract_key_points(content)
        learned = learn_from_text(content, source="conversation")

        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute(
                "UPDATE conversations SET message_count = ?, metadata = ? WHERE id = ?",
                (
                    len(self.messages),
                    json.dumps({
                        "participants": list(self.participants),
                        "topics": self.topics,
                        "last_message": content[:100],
                    }),
                    self.current_conversation_id,
                ),
            )
            conn.commit()
            conn.close()

        return {
            "conversation_id": self.current_conversation_id,
            "message_index": len(self.messages) - 1,
            "entities_found": len(entities),
            "topics_found": topics,
            "key_points": key_points,
            "memories_stored": learned.get("stored", 0),
        }

    def end_conversation(self, summary: str = "") -> dict:
        """End the current conversation, save summary, and return conversation record."""
        if not self.current_conversation_id:
            return {"error": "No active conversation"}
        duration = time.time() - self.start_time
        final_summary = summary or self._generate_summary()
        all_entities = set()
        for msg in self.messages:
            for ent in extract_entities(msg["content"]):
                all_entities.add(ent["name"])
        all_points = []
        for msg in self.messages:
            all_points.extend(extract_key_points(msg["content"]))

        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute(
                """UPDATE conversations SET
                   summary = ?, entity_mentions = ?, key_points = ?,
                   duration_seconds = ?, message_count = ?, timestamp = ?
                   WHERE id = ?""",
                (
                    final_summary,
                    json.dumps(list(all_entities)),
                    json.dumps(all_points[:10]),
                    duration,
                    len(self.messages),
                    self.start_time,
                    self.current_conversation_id,
                ),
            )
            conn.commit()
            conn.close()

        result = {
            "conversation_id": self.current_conversation_id,
            "summary": final_summary,
            "duration_seconds": duration,
            "message_count": len(self.messages),
            "participants": list(self.participants),
            "topics": self.topics,
            "entities": list(all_entities),
        }
        self.current_conversation_id = None
        self.messages = []
        self.participants = set()
        self.topics = []
        return result

    def _generate_summary(self) -> str:
        """Generate a simple summary from key points and topics."""
        parts = []
        if self.topics:
            parts.append(f"Topics: {', '.join(self.topics)}")
        if self.participants:
            parts.append(f"Participants: {', '.join(self.participants)}")
        all_points = []
        for msg in self.messages:
            all_points.extend(extract_key_points(msg["content"], max_points=2))
        if all_points:
            parts.append(f"Key points: {'; '.join(all_points[:5])}")
        parts.append(f"{len(self.messages)} messages exchanged.")
        return " | ".join(parts) if parts else "Conversation with no extracted content."

    def get_conversation_summary(self, conversation_id: str) -> Optional[dict]:
        """Retrieve a saved conversation summary by ID."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            row = conn.execute(
                """SELECT id, summary, entity_mentions, key_points,
                          timestamp, duration_seconds, message_count, metadata
                   FROM conversations WHERE id = ?""",
                (conversation_id,),
            ).fetchone()
            conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "summary": row[1],
            "entities": json.loads(row[2] or "[]"),
            "key_points": json.loads(row[3] or "[]"),
            "timestamp": row[4],
            "duration_seconds": row[5],
            "message_count": row[6],
            "metadata": json.loads(row[7] or "{}"),
        }

    def list_conversations(self, limit: int = 20) -> list[dict]:
        """List recent conversations with summaries."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                """SELECT id, summary, timestamp, duration_seconds,
                          message_count
                   FROM conversations
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            conn.close()
        return [
            {
                "id": r[0],
                "summary": r[1][:100],
                "timestamp": r[2],
                "duration_seconds": r[3],
                "message_count": r[4],
            }
            for r in rows
        ]


# ── Memory Import / Export ──

def export_memories(format: str = "json", path: str = "") -> dict:
    """Export all memories to a file in JSON or JSONL format."""
    if not path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(AUTOMEM_DIR, f"memory_export_{ts}.{format}")
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute(
            "SELECT id, content, source, entity, memory_type, importance, timestamp, access_count, last_accessed, metadata FROM memories"
        ).fetchall()
        conn.close()
    memories = []
    for r in rows:
        memories.append({
            "id": r[0], "content": r[1], "source": r[2], "entity": r[3],
            "memory_type": r[4], "importance": r[5], "timestamp": r[6],
            "access_count": r[7], "last_accessed": r[8],
            "metadata": json.loads(r[9] or "{}"),
        })
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if format == "jsonl":
        with open(path, "w", encoding="utf-8") as f:
            for m in memories:
                f.write(json.dumps(m) + "\n")
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
    return {"exported": len(memories), "path": path, "format": format}


def import_memories(path: str) -> dict:
    """Import memories from a JSON or JSONL file."""
    if not os.path.exists(path):
        return {"error": f"File not found: {path}", "imported": 0}
    imported = 0
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext == ".jsonl":
            entries = [json.loads(line) for line in f if line.strip()]
        else:
            entries = json.load(f)
    for entry in entries:
        if isinstance(entry, dict) and "content" in entry:
            store_memory(
                content=entry["content"],
                source=entry.get("source", "imported"),
                entity=entry.get("entity", ""),
                memory_type=entry.get("memory_type", "fact"),
                importance=float(entry.get("importance", 0.5)),
                metadata=entry.get("metadata"),
            )
            imported += 1
    return {"imported": imported, "source": path}


def export_graph(path: str = "") -> dict:
    """Export the knowledge graph (entities + relationships) as JSON."""
    if not path:
        path = KNOWLEDGE_GRAPH_FILE
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        entities = conn.execute(
            "SELECT id, name, type, description, first_seen, last_seen, mention_count FROM entities"
        ).fetchall()
        relationships = conn.execute(
            "SELECT id, source_entity, target_entity, relation_type, strength, first_seen, last_seen FROM relationships"
        ).fetchall()
        conn.close()
    graph = {
        "entities": [
            {"id": e[0], "name": e[1], "type": e[2], "description": e[3],
             "first_seen": e[4], "last_seen": e[5], "mention_count": e[6]}
            for e in entities
        ],
        "relationships": [
            {"id": r[0], "source": r[1], "target": r[2], "type": r[3],
             "strength": r[4], "first_seen": r[5], "last_seen": r[6]}
            for r in relationships
        ],
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    return {"exported": len(graph["entities"]) + len(graph["relationships"]), "path": path}


# ── Memory Statistics (Detailed) ──

def detailed_stats() -> dict:
    """Generate comprehensive memory statistics beyond the basic get_memory_stats()."""
    stats = {}
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)

        entity_type_dist = {}
        for row in conn.execute("SELECT type, COUNT(*) FROM entities GROUP BY type ORDER BY COUNT(*) DESC"):
            entity_type_dist[row[0]] = row[1]
        stats["entity_type_distribution"] = entity_type_dist

        rel_type_dist = {}
        for row in conn.execute("SELECT relation_type, COUNT(*) FROM relationships GROUP BY relation_type ORDER BY COUNT(*) DESC"):
            rel_type_dist[row[0]] = row[1]
        stats["relationship_type_distribution"] = rel_type_dist

        memory_trends_day = {}
        for row in conn.execute(
            "SELECT DATE(timestamp, 'unixepoch') as d, COUNT(*) FROM memories GROUP BY d ORDER BY d"
        ):
            memory_trends_day[row[0]] = row[1]
        stats["memory_trends_by_day"] = memory_trends_day

        memory_trends_week = {}
        for row in conn.execute(
            "SELECT strftime('%Y-W%W', datetime(timestamp, 'unixepoch')) as w, COUNT(*) FROM memories GROUP BY w ORDER BY w"
        ):
            memory_trends_week[row[0]] = row[1]
        stats["memory_trends_by_week"] = memory_trends_week

        memory_trends_month = {}
        for row in conn.execute(
            "SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as m, COUNT(*) FROM memories GROUP BY m ORDER BY m"
        ):
            memory_trends_month[row[0]] = row[1]
        stats["memory_trends_by_month"] = memory_trends_month

        top_accessed = []
        for row in conn.execute(
            "SELECT id, content, access_count, importance FROM memories ORDER BY access_count DESC LIMIT 10"
        ):
            top_accessed.append({
                "id": row[0],
                "content": row[1][:100],
                "access_count": row[1],
                "importance": row[2],
            })
        stats["top_accessed_memories"] = top_accessed

        now = time.time()
        day_counts = []
        for i in range(7, 0, -1):
            start = now - (i * 86400)
            end = now - ((i - 1) * 86400)
            cnt = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE timestamp >= ? AND timestamp < ?",
                (start, end),
            ).fetchone()[0]
            day_counts.append({"days_ago": i, "count": cnt})
        stats["memory_growth_7day"] = day_counts

        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        week_ago = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE timestamp >= ?",
            (now - 604800,),
        ).fetchone()[0]
        stats["growth_rate_weekly"] = round(week_ago / max(total, 1) * 100, 1) if total else 0

        conn.close()

    base = get_memory_stats()
    base["detailed"] = stats
    return base


# ── Memory Linking ──

LINK_TYPES = ["supplement", "contradicts", "depends_on", "extends", "example_of"]


def link_memories(memory_id_a: str, memory_id_b: str,
                  link_type: str = "supplement") -> str:
    """Create an explicit typed link between two memories.

    Link types: supplement, contradicts, depends_on, extends, example_of.
    """
    if link_type not in LINK_TYPES:
        link_type = "supplement"
    link_id = uuid.uuid4().hex[:12]
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute(
            "INSERT INTO memory_links (id, memory_id_a, memory_id_b, link_type, created) VALUES (?,?,?,?,?)",
            (link_id, memory_id_a, memory_id_b, link_type, time.time()),
        )
        conn.commit()
        conn.close()
    return link_id


def get_linked_memories(memory_id: str) -> list[dict]:
    """Get all memories linked to the given memory, with link type."""
    results = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute(
            """SELECT l.id, l.memory_id_a, l.memory_id_b, l.link_type, l.created,
                      m.content, m.memory_type, m.importance, m.timestamp
               FROM memory_links l
               JOIN memories m ON m.id = CASE WHEN l.memory_id_a = ? THEN l.memory_id_b ELSE l.memory_id_a END
               WHERE l.memory_id_a = ? OR l.memory_id_b = ?""",
            (memory_id, memory_id, memory_id),
        ).fetchall()
        conn.close()
    for r in rows:
        results.append({
            "link_id": r[0],
            "memory_id_a": r[1],
            "memory_id_b": r[2],
            "link_type": r[3],
            "created": r[4],
            "content": r[5],
            "memory_type": r[6],
            "importance": r[7],
            "timestamp": r[8],
        })
    return results


def remove_link(link_id: str) -> bool:
    """Remove a memory link by its ID."""
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        cur = conn.execute("DELETE FROM memory_links WHERE id = ?", (link_id,))
        removed = cur.rowcount > 0
        conn.commit()
        conn.close()
    return removed


# ── Spatial Memory ──

class SpatialIndex:
    """Index for location-tagged memories with proximity search."""

    def store_location(self, name: str, latitude: float, longitude: float,
                       description: str = "") -> str:
        """Store a named location with coordinates."""
        loc_id = uuid.uuid4().hex[:12]
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            conn.execute(
                "INSERT INTO memory_locations (id, name, latitude, longitude, description, created) VALUES (?,?,?,?,?,?)",
                (loc_id, name, latitude, longitude, description, time.time()),
            )
            conn.commit()
            conn.close()
        return loc_id

    def find_nearby(self, latitude: float, longitude: float,
                    radius_km: float = 10.0) -> list[dict]:
        """Find locations within radius_km of the given coordinates using Haversine."""
        results = []
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT id, name, latitude, longitude, description, created FROM memory_locations"
            ).fetchall()
            conn.close()
        for r in rows:
            lat2, lng2 = r[2], r[3]
            dist = self._haversine(latitude, longitude, lat2, lng2)
            if dist <= radius_km:
                results.append({
                    "id": r[0],
                    "name": r[1],
                    "latitude": r[2],
                    "longitude": r[3],
                    "description": r[4],
                    "created": r[5],
                    "distance_km": round(dist, 3),
                })
        results.sort(key=lambda x: x["distance_km"])
        return results

    def get_location_memories(self, name: str) -> list[dict]:
        """Get all memories associated with a named location."""
        results = []
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT id, name, latitude, longitude, description, created FROM memory_locations WHERE name = ?",
                (name,),
            ).fetchall()
            conn.close()
        for r in rows:
            results.append({
                "id": r[0],
                "name": r[1],
                "latitude": r[2],
                "longitude": r[3],
                "description": r[4],
                "created": r[5],
            })
        return results

    def list_locations(self) -> list[dict]:
        """List all stored locations."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT id, name, latitude, longitude, description, created FROM memory_locations ORDER BY name"
            ).fetchall()
            conn.close()
        return [
            {
                "id": r[0], "name": r[1], "latitude": r[2],
                "longitude": r[3], "description": r[4], "created": r[5],
            }
            for r in rows
        ]

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Compute great-circle distance in km between two lat/lng points."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


# ── Temporal Memory ──

class TemporalIndex:
    """Index for time-based memory queries."""

    def memories_on_date(self, date_str: str) -> list[dict]:
        """Get all memories from a specific date (YYYY-MM-DD)."""
        results = []
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                """SELECT id, content, source, entity, memory_type, importance,
                          timestamp, access_count, metadata
                   FROM memories
                   WHERE DATE(timestamp, 'unixepoch') = ?
                   ORDER BY timestamp DESC""",
                (date_str,),
            ).fetchall()
            conn.close()
        for r in rows:
            results.append({
                "id": r[0], "content": r[1], "source": r[2],
                "entity": r[3], "memory_type": r[4],
                "importance": r[5], "timestamp": r[6],
                "access_count": r[7], "metadata": json.loads(r[8] or "{}"),
            })
        return results

    def memories_between(self, start_date: str, end_date: str) -> list[dict]:
        """Get all memories between two dates (YYYY-MM-DD)."""
        results = []
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                """SELECT id, content, source, entity, memory_type, importance,
                          timestamp, access_count, metadata
                   FROM memories
                   WHERE DATE(timestamp, 'unixepoch') >= ?
                     AND DATE(timestamp, 'unixepoch') <= ?
                   ORDER BY timestamp DESC""",
                (start_date, end_date),
            ).fetchall()
            conn.close()
        for r in rows:
            results.append({
                "id": r[0], "content": r[1], "source": r[2],
                "entity": r[3], "memory_type": r[4],
                "importance": r[5], "timestamp": r[6],
                "access_count": r[7], "metadata": json.loads(r[8] or "{}"),
            })
        return results

    def memories_by_hour(self) -> dict[str, int]:
        """Get a histogram of memories by hour of day (0-23)."""
        hourly = {str(i).zfill(2): 0 for i in range(24)}
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as h, COUNT(*) FROM memories GROUP BY h ORDER BY h"
            ).fetchall()
            conn.close()
        for h, cnt in rows:
            hourly[str(h).zfill(2)] = cnt
        return hourly

    def memories_by_day_of_week(self) -> dict[str, int]:
        """Get a histogram of memories by day of week (Mon-Sun)."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result = {d: 0 for d in days}
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT CAST(strftime('%w', datetime(timestamp, 'unixepoch')) AS INTEGER) as d, COUNT(*) FROM memories GROUP BY d ORDER BY d"
            ).fetchall()
            conn.close()
        for d, cnt in rows:
            result[days[d]] = cnt
        return result

    def memories_by_month(self) -> dict[str, int]:
        """Get a histogram of memories by month (YYYY-MM)."""
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            rows = conn.execute(
                "SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as m, COUNT(*) FROM memories GROUP BY m ORDER BY m"
            ).fetchall()
            conn.close()
        return {r[0]: r[1] for r in rows}


# ── Memory Conflict Detection ──

def detect_contradictions() -> list[dict]:
    """Find memories that contain contradictory information about the same entity.

    Uses keyword heuristics: opposite-polarity terms, negations, and numerical
    conflicts about the same entity.
    """
    contradictions = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute(
            "SELECT id, content, entity FROM memories WHERE entity != '' ORDER BY entity"
        ).fetchall()
        conn.close()

    by_entity: dict[str, list[dict]] = defaultdict(list)
    for mid, content, entity in rows:
        entities_list = [e.strip() for e in entity.split(",")]
        for ent in entities_list:
            if ent:
                by_entity[ent].append({"id": mid, "content": content})

    negation_words = ["not", "cannot", "can't", "never", "no", "isn't", "aren't",
                      "wasn't", "weren't", "doesn't", "don't", "didn't", "won't"]
    opposite_pairs = [
        ("enabled", "disabled"), ("active", "inactive"), ("on", "off"),
        ("true", "false"), ("yes", "no"), ("start", "stop"), ("begin", "end"),
        ("open", "closed"), ("running", "stopped"), ("installed", "uninstalled"),
        ("increase", "decrease"), ("up", "down"), ("high", "low"),
        ("present", "absent"), ("available", "unavailable"),
    ]

    checked_pairs = set()
    for entity, mems in by_entity.items():
        for i in range(len(mems)):
            for j in range(i + 1, len(mems)):
                pair_key = tuple(sorted([mems[i]["id"], mems[j]["id"]]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                ci = mems[i]["content"].lower()
                cj = mems[j]["content"].lower()

                has_neg_i = any(w in ci for w in negation_words)
                has_neg_j = any(w in cj for w in negation_words)

                if has_neg_i != has_neg_j:
                    base_i = set(ci.split())
                    base_j = set(cj.split())
                    common = base_i & base_j
                    if len(common) >= 3:
                        contradictions.append({
                            "memory_id_a": mems[i]["id"],
                            "memory_id_b": mems[j]["id"],
                            "entity": entity,
                            "type": "negation_conflict",
                            "description": f"Opposing statements about '{entity}'",
                            "content_a": mems[i]["content"][:200],
                            "content_b": mems[j]["content"][:200],
                        })
                        continue

                for a, b in opposite_pairs:
                    if (a in ci and b in cj) or (b in ci and a in cj):
                        contradictions.append({
                            "memory_id_a": mems[i]["id"],
                            "memory_id_b": mems[j]["id"],
                            "entity": entity,
                            "type": "opposite_term",
                            "description": f"Contradictory terms '{a}'/'{b}' about '{entity}'",
                            "content_a": mems[i]["content"][:200],
                            "content_b": mems[j]["content"][:200],
                        })
                        break

    return contradictions


def resolve_conflict(memory_id_a: str, memory_id_b: str,
                     resolution: str = "superseded") -> str:
    """Resolve a detected conflict by marking one memory as superseded.

    resolution: 'superseded' marks memory_id_b as superseded by memory_id_a,
                or specify 'keep_a' / 'keep_b'.
    """
    conflict_id = uuid.uuid4().hex[:12]
    superseded = ""
    if resolution == "superseded" or resolution == "keep_a":
        superseded = memory_id_b
    elif resolution == "keep_b":
        superseded = memory_id_a
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute(
            """INSERT INTO memory_conflicts
               (id, memory_id_a, memory_id_b, description, conflict_type,
                detected_at, resolved_at, resolution, superseded_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                conflict_id, memory_id_a, memory_id_b,
                f"Resolved: {resolution}", "manual_resolution",
                time.time(), time.time(), resolution, superseded,
            ),
        )
        if superseded:
            conn.execute(
                "UPDATE memories SET importance = GREATEST(importance * 0.3, 0.05) WHERE id = ?",
                (superseded,),
            )
        conn.commit()
        conn.close()
    return conflict_id


# ── Memory Importance Heuristics ──

def calculate_importance(content: str, source: str = "",
                         recency: Optional[float] = None) -> float:
    """Calculate a memory importance score using multiple heuristics.

    Factors:
      - Keyword density (presence of importance-signaling words)
      - Source credibility (tool calls > conversation > system)
      - Recency decay (newer = more important)
      - Mention frequency of contained entities
      - Entity centrality in the knowledge graph
    Returns a float between 0.0 and 1.0.
    """
    score = 0.5

    importance_keywords = {
        "critical": 0.3, "important": 0.25, "essential": 0.25, "vital": 0.25,
        "key": 0.2, "significant": 0.2, "major": 0.15, "crucial": 0.3,
        "urgent": 0.2, "warning": 0.2, "error": 0.15, "failed": 0.1,
        "remember": 0.15, "note": 0.1, "required": 0.15, "mandatory": 0.2,
        "never": 0.1, "always": 0.1, "must": 0.15, "should": 0.1,
    }
    content_lower = content.lower()
    for kw, boost in importance_keywords.items():
        if kw in content_lower:
            score += boost
    count = sum(1 for kw in importance_keywords if kw in content_lower)
    density = count / max(len(content.split()), 1)
    if density > 0.1:
        score += 0.1

    source_weights = {
        "tool": 0.15, "tool:": 0.15, "conversation": 0.05,
        "system": 0.0, "manual": 0.1, "imported": 0.05,
    }
    for prefix, bonus in source_weights.items():
        if source.lower().startswith(prefix):
            score += bonus
            break

    if recency is not None:
        hours_old = (time.time() - recency) / 3600
        if hours_old < 1:
            score += 0.1
        elif hours_old < 24:
            score += 0.05
        elif hours_old > 720:
            score -= 0.1
        elif hours_old > 168:
            score -= 0.05

    entities = extract_entities(content)
    if entities:
        with _memory_lock:
            conn = sqlite3.connect(MEMORY_DB)
            for ent in entities[:3]:
                row = conn.execute(
                    "SELECT mention_count FROM entities WHERE name = ?",
                    (ent["name"],),
                ).fetchone()
                if row and row[0] > 5:
                    score += 0.05
            conn.close()

    length_factor = min(len(content.split()) / 100, 1.0) * 0.05
    score += length_factor

    score = max(0.0, min(1.0, score))
    return score


# ── Memory Notifications / Reminders ──

def set_reminder(content: str, trigger_time: float,
                 metadata: Optional[dict] = None) -> str:
    """Set a time-based reminder that will trigger at trigger_time."""
    rid = uuid.uuid4().hex[:12]
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        conn.execute(
            "INSERT INTO reminders (id, content, trigger_time, created, dismissed, notified, metadata) VALUES (?,?,?,?,?,?,?)",
            (rid, content, trigger_time, time.time(), 0, 0, json.dumps(metadata or {})),
        )
        conn.commit()
        conn.close()
    return rid


def list_reminders(include_dismissed: bool = False) -> list[dict]:
    """List all reminders, optionally including dismissed ones."""
    results = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        if include_dismissed:
            rows = conn.execute(
                "SELECT id, content, trigger_time, created, dismissed, notified, metadata FROM reminders ORDER BY trigger_time ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, content, trigger_time, created, dismissed, notified, metadata FROM reminders WHERE dismissed = 0 ORDER BY trigger_time ASC"
            ).fetchall()
        conn.close()
    for r in rows:
        results.append({
            "id": r[0],
            "content": r[1],
            "trigger_time": r[2],
            "created": r[3],
            "dismissed": bool(r[4]),
            "notified": bool(r[5]),
            "metadata": json.loads(r[6] or "{}"),
        })
    return results


def dismiss_reminder(reminder_id: str) -> bool:
    """Mark a reminder as dismissed."""
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        cur = conn.execute(
            "UPDATE reminders SET dismissed = 1 WHERE id = ?",
            (reminder_id,),
        )
        success = cur.rowcount > 0
        conn.commit()
        conn.close()
    return success


def check_for_reminders() -> list[dict]:
    """Find all undismissed reminders whose trigger_time has passed."""
    now = time.time()
    due = []
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute(
            "SELECT id, content, trigger_time, created, metadata FROM reminders WHERE dismissed = 0 AND notified = 0 AND trigger_time <= ? ORDER BY trigger_time ASC",
            (now,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE reminders SET notified = 1 WHERE id = ?",
                (r[0],),
            )
            due.append({
                "id": r[0],
                "content": r[1],
                "trigger_time": r[2],
                "created": r[3],
                "metadata": json.loads(r[4] or "{}"),
            })
        conn.commit()
        conn.close()
    return due


def clear_reminders() -> int:
    """Delete all dismissed reminders. Returns count of deleted reminders."""
    with _memory_lock:
        conn = sqlite3.connect(MEMORY_DB)
        rows = conn.execute("DELETE FROM reminders WHERE dismissed = 1")
        count = rows.rowcount
        conn.commit()
        conn.close()
    return count


# ── Batch Learning ──

def learn_from_file(path: str, source: str = "file") -> dict:
    """Read a text file and learn from its contents."""
    if not os.path.exists(path):
        return {"error": f"File not found: {path}", "stored": 0, "entities": 0}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e), "stored": 0, "entities": 0}
    if not content.strip():
        return {"stored": 0, "entities": 0, "message": "Empty file"}
    result = learn_from_text(content, source=f"{source}:{os.path.basename(path)}")
    result["file"] = path
    return result


def learn_from_directory(dir_path: str, pattern: str = "*.txt",
                         source: str = "batch") -> dict:
    """Batch learn from all files matching a pattern in a directory."""
    if not os.path.isdir(dir_path):
        return {"error": f"Directory not found: {dir_path}", "total_files": 0, "total_stored": 0}
    total_stored = 0
    total_entities = 0
    processed = 0
    files = glob.glob(os.path.join(dir_path, pattern))
    for filepath in files:
        if os.path.isfile(filepath):
            result = learn_from_file(filepath, source=source)
            if "error" not in result:
                total_stored += result.get("stored", 0)
                total_entities += result.get("entities", 0)
                processed += 1
    return {
        "total_files": processed,
        "total_stored": total_stored,
        "total_entities": total_entities,
        "directory": dir_path,
        "pattern": pattern,
    }


def learn_from_conversation_log(source: str = "conversation_log") -> dict:
    """Read FRIDAY's own conversation log file and learn from each entry."""
    if not os.path.exists(CONVERSATION_LOG):
        return {"error": f"Conversation log not found: {CONVERSATION_LOG}", "stored": 0}
    total_stored = 0
    total_entities = 0
    processed = 0
    try:
        with open(CONVERSATION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    text = entry.get("content", entry.get("text", entry.get("message", "")))
                    if isinstance(text, str) and len(text.strip()) >= 10:
                        result = learn_from_text(text, source=source)
                        total_stored += result.get("stored", 0)
                        total_entities += result.get("entities", 0)
                        processed += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as e:
        return {"error": str(e), "stored": total_stored, "processed": processed}
    return {
        "processed": processed,
        "total_stored": total_stored,
        "total_entities": total_entities,
        "source": CONVERSATION_LOG,
    }


def learn_from_jsonl(path: str, source: str = "jsonl_import") -> dict:
    """Learn from a JSONL file where each line is a JSON object with a 'text' or 'content' field."""
    if not os.path.exists(path):
        return {"error": f"File not found: {path}", "stored": 0}
    total_stored = 0
    total_entities = 0
    processed = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    text = entry.get("content") or entry.get("text") or entry.get("message", "")
                    if isinstance(text, str) and len(text.strip()) >= 10:
                        result = learn_from_text(text, source=source)
                        total_stored += result.get("stored", 0)
                        total_entities += result.get("entities", 0)
                        processed += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as e:
        return {"error": str(e), "stored": total_stored, "processed": processed}
    return {
        "processed": processed,
        "total_stored": total_stored,
        "total_entities": total_entities,
        "source": path,
    }


# ── Main Tool ──

def autonomous_memory_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Autonomous Memory System.

    Core actions:
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

    Semantic search:
      semantic_search - Semantic similarity search (query, limit)
      rebuild_index   - Rebuild the semantic embedding index

    Decay:
      apply_decay      - Apply memory importance decay
      start_decay      - Start background decay scheduler (interval)
      stop_decay       - Stop background decay scheduler

    Tagging:
      add_tag         - Tag a memory (memory_id, tag)
      remove_tag      - Remove a tag from a memory (memory_id, tag)
      search_by_tag   - Search memories by tag (tag, limit)
      get_all_tags    - List all unique tags
      get_popular_tags - List tags by popularity (limit)
      get_memory_tags  - List tags for a specific memory (memory_id)

    Conversations:
      start_conversation      - Start a new conversation
      add_message             - Add a message to current conversation (role, content, participant)
      end_conversation        - End current conversation (summary)
      get_conversation_summary - Get conversation by ID (conversation_id)
      list_conversations      - List recent conversations (limit)

    Import/Export:
      export_memories - Export memories (format=json|jsonl, path)
      import_memories - Import memories (path)
      export_graph    - Export knowledge graph (path)

    Statistics:
      detailed_stats - Comprehensive memory analytics
      stats          - Basic memory stats (alias)

    Memory linking:
      link_memories      - Link two memories (memory_id_a, memory_id_b, link_type)
      get_linked_memories - Get linked memories (memory_id)
      remove_link        - Remove a link (link_id)

    Spatial:
      store_location  - Store a location (name, lat, lng, description)
      find_nearby     - Find locations near coordinates (lat, lng, radius_km)
      get_location    - Get location memories by name (name)
      list_locations  - List all stored locations

    Temporal:
      memories_on_date - Get memories for a date (date=YYYY-MM-DD)
      memories_between - Get memories between dates (start, end)
      memories_by_hour - Get memory count histogram by hour
      memories_by_dow  - Get memory count by day of week
      memories_by_month - Get memory count by month

    Conflict detection:
      detect_contradictions - Find contradictory memories
      resolve_conflict      - Resolve a conflict (memory_id_a, memory_id_b, resolution)

    Importance:
      calculate_importance - Calculate importance score for text (content, source)

    Reminders:
      set_reminder    - Set a reminder (text, trigger_time)
      list_reminders  - List pending reminders
      dismiss_reminder - Dismiss a reminder (reminder_id)
      check_reminders - Check for due reminders

    Batch learning:
      learn_from_file             - Learn from a text file (path)
      learn_from_directory        - Learn from all files in a directory (dir_path, pattern)
      learn_from_conversation_log - Learn from FRIDAY's conversation log
      learn_from_jsonl            - Learn from a JSONL file (path)
    """
    try:
        if action == "status" or action == "stats":
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
                for tbl in ["memories", "entities", "relationships", "memory_tags",
                            "memory_links", "memory_locations", "reminders",
                            "memory_embeddings", "memory_conflicts"]:
                    conn.execute(f"DELETE FROM {tbl}")
                conn.commit()
                conn.close()
            return json.dumps({"cleared": True}, indent=2)

        elif action == "semantic_search":
            query = kwargs.get("query", "")
            limit = int(kwargs.get("limit", 10))
            index = SemanticIndex()
            results = index.search(query, limit)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "rebuild_index":
            index = SemanticIndex()
            count = index.rebuild()
            return json.dumps({"rebuilt": True, "indexed_memories": count}, indent=2)

        elif action == "apply_decay":
            days = float(kwargs.get("days", 1.0))
            amount = float(kwargs.get("amount", 0.1))
            prune = float(kwargs.get("prune_below", 0.1))
            result = apply_decay(days, amount, prune)
            return json.dumps(result, indent=2)

        elif action == "start_decay":
            interval = int(kwargs.get("interval", 3600))
            if not hasattr(autonomous_memory_tool, '_decay_scheduler') \
                    or not autonomous_memory_tool._decay_scheduler.is_running():
                scheduler = MemoryDecayScheduler(interval=interval)
                scheduler.start()
                autonomous_memory_tool._decay_scheduler = scheduler
            return json.dumps({"started": True, "interval": interval}, indent=2)

        elif action == "stop_decay":
            if hasattr(autonomous_memory_tool, '_decay_scheduler'):
                autonomous_memory_tool._decay_scheduler.stop()
                return json.dumps({"stopped": True}, indent=2)
            return json.dumps({"stopped": False, "message": "No running scheduler"}, indent=2)

        elif action == "add_tag":
            mid = kwargs.get("memory_id", "")
            tag = kwargs.get("tag", "")
            tm = TagManager()
            ok = tm.add_tag(mid, tag)
            return json.dumps({"added": ok}, indent=2)

        elif action == "remove_tag":
            mid = kwargs.get("memory_id", "")
            tag = kwargs.get("tag", "")
            tm = TagManager()
            ok = tm.remove_tag(mid, tag)
            return json.dumps({"removed": ok}, indent=2)

        elif action == "search_by_tag":
            tag = kwargs.get("tag", "")
            limit = int(kwargs.get("limit", 20))
            tm = TagManager()
            results = tm.search_by_tag(tag, limit)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "get_all_tags":
            tm = TagManager()
            tags = tm.get_all_tags()
            return json.dumps({"tags": tags, "count": len(tags)}, indent=2)

        elif action == "get_popular_tags":
            limit = int(kwargs.get("limit", 10))
            tm = TagManager()
            tags = tm.get_popular_tags(limit)
            return json.dumps({"tags": tags}, indent=2)

        elif action == "get_memory_tags":
            mid = kwargs.get("memory_id", "")
            tm = TagManager()
            tags = tm.get_memory_tags(mid)
            return json.dumps({"memory_id": mid, "tags": tags}, indent=2)

        elif action == "start_conversation":
            cm = ConversationMemory()
            cid = cm.start_conversation()
            return json.dumps({"conversation_id": cid}, indent=2)

        elif action == "add_message":
            cm = ConversationMemory()
            if cm.current_conversation_id is None:
                cid = cm.start_conversation()
            result = cm.add_message(
                role=kwargs.get("role", "user"),
                content=kwargs.get("content", ""),
                participant=kwargs.get("participant", ""),
            )
            return json.dumps(result, indent=2)

        elif action == "end_conversation":
            cm = ConversationMemory()
            summary = kwargs.get("summary", "")
            result = cm.end_conversation(summary)
            return json.dumps(result, indent=2)

        elif action == "get_conversation_summary":
            cm = ConversationMemory()
            cid = kwargs.get("conversation_id", "")
            result = cm.get_conversation_summary(cid)
            if result is None:
                return json.dumps({"error": f"Conversation not found: {cid}"}, indent=2)
            return json.dumps(result, indent=2)

        elif action == "list_conversations":
            cm = ConversationMemory()
            limit = int(kwargs.get("limit", 20))
            results = cm.list_conversations(limit)
            return json.dumps({"conversations": results, "count": len(results)}, indent=2)

        elif action == "export_memories":
            fmt = kwargs.get("format", "json")
            path = kwargs.get("path", "")
            result = export_memories(fmt, path)
            return json.dumps(result, indent=2)

        elif action == "import_memories":
            path = kwargs.get("path", "")
            result = import_memories(path)
            return json.dumps(result, indent=2)

        elif action == "export_graph":
            path = kwargs.get("path", "")
            result = export_graph(path)
            return json.dumps(result, indent=2)

        elif action == "detailed_stats":
            stats = detailed_stats()
            return json.dumps(stats, indent=2, default=str)

        elif action == "link_memories":
            mid_a = kwargs.get("memory_id_a", "")
            mid_b = kwargs.get("memory_id_b", "")
            lt = kwargs.get("link_type", "supplement")
            lid = link_memories(mid_a, mid_b, lt)
            return json.dumps({"linked": True, "link_id": lid}, indent=2)

        elif action == "get_linked_memories":
            mid = kwargs.get("memory_id", "")
            results = get_linked_memories(mid)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "remove_link":
            lid = kwargs.get("link_id", "")
            ok = remove_link(lid)
            return json.dumps({"removed": ok}, indent=2)

        elif action == "store_location":
            name = kwargs.get("name", "")
            lat = float(kwargs.get("lat", 0))
            lng = float(kwargs.get("lng", 0))
            desc = kwargs.get("description", "")
            si = SpatialIndex()
            lid = si.store_location(name, lat, lng, desc)
            return json.dumps({"stored": True, "location_id": lid}, indent=2)

        elif action == "find_nearby":
            lat = float(kwargs.get("lat", 0))
            lng = float(kwargs.get("lng", 0))
            radius = float(kwargs.get("radius_km", 10))
            si = SpatialIndex()
            results = si.find_nearby(lat, lng, radius)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "get_location":
            name = kwargs.get("name", "")
            si = SpatialIndex()
            results = si.get_location_memories(name)
            return json.dumps({"results": results}, indent=2)

        elif action == "list_locations":
            si = SpatialIndex()
            results = si.list_locations()
            return json.dumps({"locations": results, "count": len(results)}, indent=2)

        elif action == "memories_on_date":
            date_str = kwargs.get("date", "")
            ti = TemporalIndex()
            results = ti.memories_on_date(date_str)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "memories_between":
            start = kwargs.get("start", "")
            end = kwargs.get("end", "")
            ti = TemporalIndex()
            results = ti.memories_between(start, end)
            return json.dumps({"results": results, "count": len(results)}, indent=2)

        elif action == "memories_by_hour":
            ti = TemporalIndex()
            results = ti.memories_by_hour()
            return json.dumps({"results": results}, indent=2)

        elif action == "memories_by_dow":
            ti = TemporalIndex()
            results = ti.memories_by_day_of_week()
            return json.dumps({"results": results}, indent=2)

        elif action == "memories_by_month":
            ti = TemporalIndex()
            results = ti.memories_by_month()
            return json.dumps({"results": results}, indent=2)

        elif action == "detect_contradictions":
            results = detect_contradictions()
            return json.dumps({"contradictions": results, "count": len(results)}, indent=2)

        elif action == "resolve_conflict":
            mid_a = kwargs.get("memory_id_a", "")
            mid_b = kwargs.get("memory_id_b", "")
            resolution = kwargs.get("resolution", "superseded")
            cid = resolve_conflict(mid_a, mid_b, resolution)
            return json.dumps({"resolved": True, "conflict_id": cid}, indent=2)

        elif action == "calculate_importance":
            content = kwargs.get("content", "")
            source = kwargs.get("source", "")
            imp = calculate_importance(content, source)
            return json.dumps({"importance": round(imp, 4)}, indent=2)

        elif action == "set_reminder":
            text = kwargs.get("text", "")
            trigger = float(kwargs.get("trigger_time", time.time() + 3600))
            mid = set_reminder(text, trigger)
            return json.dumps({"created": True, "reminder_id": mid}, indent=2)

        elif action == "list_reminders":
            include = kwargs.get("include_dismissed", "false").lower() == "true"
            reminders = list_reminders(include)
            return json.dumps({"reminders": reminders, "count": len(reminders)}, indent=2)

        elif action == "dismiss_reminder":
            rid = kwargs.get("reminder_id", "")
            ok = dismiss_reminder(rid)
            return json.dumps({"dismissed": ok}, indent=2)

        elif action == "check_reminders":
            results = check_for_reminders()
            return json.dumps({"due": results, "count": len(results)}, indent=2)

        elif action == "clear_reminders":
            count = clear_reminders()
            return json.dumps({"cleared": count}, indent=2)

        elif action == "learn_from_file":
            path = kwargs.get("path", "")
            result = learn_from_file(path)
            return json.dumps(result, indent=2)

        elif action == "learn_from_directory":
            dir_path = kwargs.get("dir_path", "")
            pattern = kwargs.get("pattern", "*.txt")
            result = learn_from_directory(dir_path, pattern)
            return json.dumps(result, indent=2)

        elif action == "learn_from_conversation_log":
            result = learn_from_conversation_log()
            return json.dumps(result, indent=2)

        elif action == "learn_from_jsonl":
            path = kwargs.get("path", "")
            result = learn_from_jsonl(path)
            return json.dumps(result, indent=2)

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
