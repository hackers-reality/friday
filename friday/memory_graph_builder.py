"""
Memory Knowledge Graph Builder — builds a Maltego-style interactive graph
from ALL of FRIDAY's memory sources: ChromaDB, episodic archive, chat history.

Uses networkx DiGraph internally, exports cytoscape.js JSON for the dashboard.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

import networkx as nx

from friday._paths import FRIDAY_MEMORY
from friday.episodic import _get_conn as _get_episodic_conn
from friday.knowledge_graph import get_knowledge_graph
from friday.logging_utils import configure_logging
from friday.nlp_pipeline import NLPPipeline
from friday.vector_memory import get_vector_memory
from friday.context_bus import get_bus

logger = configure_logging(__name__)

# Graph storage path
_GRAPH_STORAGE = os.path.join(FRIDAY_MEMORY, "memory_graph.json")


class MemoryGraphBuilder:
    """
    Builds a semantic knowledge graph from all FRIDAY memory sources.

    Node types: CONCEPT, ENTITY, PERSON, EMOTION, ACTION, TIME, CHAT, MEMORY
    Edge types: INTERESTED_IN, MENTIONED, RELATED_TO, OCCURRED_AT, PERFORMED,
                ABOUT, STRENGTHENED_BY, CO_OCCURS_WITH
    """

    NODE_TYPES = frozenset({"CONCEPT", "ENTITY", "PERSON", "EMOTION",
                             "ACTION", "TIME", "CHAT", "MEMORY"})

    EDGE_TYPES = frozenset({"INTERESTED_IN", "MENTIONED", "RELATED_TO",
                             "OCCURRED_AT", "PERFORMED", "ABOUT",
                             "STRENGTHENED_BY", "CO_OCCURS_WITH"})

    SEMANTIC_THRESHOLD = 0.75
    CO_OCCUR_THRESHOLD = 3
    HIGH_FREQ_THRESHOLD = 5
    MAX_NODES = 500
    CACHE_TTL = 60

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nlp = NLPPipeline()
        self._concept_embeddings: dict[str, list[float]] = {}
        self._last_built: Optional[float] = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Load graph from disk if exists."""
        if not os.path.exists(_GRAPH_STORAGE):
            return
        try:
            with open(_GRAPH_STORAGE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for node_data in data.get("nodes", []):
                self.graph.add_node(node_data["id"], **node_data.get("data", {}))
            for edge_data in data.get("edges", []):
                self.graph.add_edge(
                    edge_data["source"],
                    edge_data["target"],
                    **edge_data.get("data", {}),
                )
            self._last_built = data.get("last_built")
            logger.info("Loaded memory graph: %d nodes, %d edges",
                        self.graph.number_of_nodes(), self.graph.number_of_edges())
        except Exception as e:
            logger.warning("Failed to load memory graph: %s", e)

    def save(self):
        """Save graph to disk."""
        os.makedirs(os.path.dirname(_GRAPH_STORAGE), exist_ok=True)
        with self._lock:
            elements = self._export_cytoscape()
            data = {
                "nodes": [{"id": n, "data": self.graph.nodes[n]} for n in self.graph.nodes],
                "edges": [{"source": u, "target": v, "data": self.graph.edges[u, v]}
                         for u, v in self.graph.edges],
                "elements": elements,
                "last_built": self._last_built,
                "stats": self.get_stats(),
            }
        with open(_GRAPH_STORAGE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def build_from_all_sources(self) -> dict:
        """Build graph from ALL memory sources in parallel."""
        start = time.time()
        self.graph.clear()

        await asyncio.gather(
            self._process_chroma_memories(),
            self._process_episodic_memories(),
            self._process_chat_history(limit=200),
            self._process_knowledge_graph(),
        )

        await self._compute_semantic_relationships()

        self._last_built = time.time()
        self.save()

        stats = self.get_stats()
        elapsed = time.time() - start
        logger.info("Graph built in %.1fs: %d nodes, %d edges",
                    elapsed, stats["total_nodes"], stats["total_edges"])

        return stats

    async def _process_chroma_memories(self):
        """Process all ChromaDB memory chunks into graph nodes."""
        vm = get_vector_memory()
        if not vm.is_available() or not vm.collection:
            return

        try:
            all_docs = vm.collection.get()
            if not all_docs or not all_docs.get("documents"):
                return

            documents = all_docs["documents"]
            metadatas = all_docs.get("metadatas", [{}] * len(documents))
            ids = all_docs.get("ids", [str(i) for i in range(len(documents))])

            for i, doc in enumerate(documents):
                if not doc or not doc.strip():
                    continue

                mem_id = ids[i] if i < len(ids) else f"mem_{i}"
                meta = metadatas[i] if i < len(metadatas) else {}

                preview = doc[:100] + "..." if len(doc) > 100 else doc
                self.graph.add_node(mem_id, type="MEMORY", label=preview,
                                    content=doc[:500], source=meta.get("source", "chroma"),
                                    timestamp=meta.get("timestamp", _now_iso()))

                entities = self.nlp.extract_entities(doc)
                concepts = self.nlp.extract_concepts(doc)

                for ent in entities:
                    node_id = self._normalize_concept(ent["text"])
                    node_type = self._ner_to_node_type(ent["label"])
                    self.add_concept_node(node_id, node_type, ent["text"])
                    self.graph.add_edge(mem_id, node_id, relationship="ABOUT",
                                        weight=1.0)

                for concept in concepts[:10]:
                    node_id = self._normalize_concept(concept)
                    self.add_concept_node(node_id, "CONCEPT", concept)
                    self.graph.add_edge(mem_id, node_id, relationship="ABOUT",
                                        weight=0.8)
        except Exception as e:
            logger.warning("Error processing Chroma memories: %s", e)

    async def _process_episodic_memories(self):
        """Process episodic SQLite archive into graph nodes."""
        try:
            conn = _get_episodic_conn()
            cursor = conn.execute(
                "SELECT id, session_id, timestamp, speaker, content, tool_name "
                "FROM episodes ORDER BY timestamp DESC LIMIT 500"
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                row_dict = dict(row)
                content = row_dict.get("content", "")
                if not content or not content.strip():
                    continue

                ep_id = f"ep_{row_dict['id']}"
                speaker = row_dict.get("speaker", "unknown")
                timestamp = row_dict.get("timestamp", _now_iso())

                preview = content[:100] + "..." if len(content) > 100 else content
                self.graph.add_node(ep_id, type="MEMORY", label=preview,
                                    content=content[:500], source=f"episodic/{speaker}",
                                    timestamp=timestamp,
                                    tool_name=row_dict.get("tool_name", ""))

                entities = self.nlp.extract_entities(content)
                concepts = self.nlp.extract_concepts(content)
                sentiment = self.nlp.get_sentiment(content)

                for ent in entities[:5]:
                    node_id = self._normalize_concept(ent["text"])
                    node_type = self._ner_to_node_type(ent["label"])
                    self.add_concept_node(node_id, node_type, ent["text"])
                    self.graph.add_edge(ep_id, node_id, relationship="ABOUT", weight=1.0)

                for concept in concepts[:5]:
                    node_id = self._normalize_concept(concept)
                    self.add_concept_node(node_id, "CONCEPT", concept)
                    self.graph.add_edge(ep_id, node_id, relationship="ABOUT", weight=0.7)

                if sentiment != "neutral":
                    emotion_id = f"emotion_{sentiment}"
                    if not self.graph.has_node(emotion_id):
                        self.graph.add_node(emotion_id, type="EMOTION",
                                            label=sentiment.capitalize(),
                                            mention_count=1)
                    else:
                        self.graph.nodes[emotion_id]["mention_count"] += 1
                    self.graph.add_edge(ep_id, emotion_id, relationship="HAS_SENTIMENT")

        except Exception as e:
            logger.warning("Error processing episodic memories: %s", e)

    async def _process_chat_history(self, limit: int = 200):
        """Process chat history from conversation store."""
        try:
            conv_db = os.path.join(FRIDAY_MEMORY, "conversations.db")
            if not os.path.exists(conv_db):
                return

            import sqlite3
            conn = sqlite3.connect(conv_db)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT id, role, content, timestamp FROM messages "
                    "ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
            except Exception:
                rows = []
            conn.close()

            for row in rows:
                row_dict = dict(row)
                content = row_dict.get("content", "")
                if not content or not content.strip():
                    continue

                chat_id = f"chat_{row_dict['id']}"
                role = row_dict.get("role", "user")
                timestamp = row_dict.get("timestamp", _now_iso())

                preview = content[:80] + "..." if len(content) > 80 else content
                self.graph.add_node(chat_id, type="CHAT", label=preview,
                                    speaker=role, timestamp=timestamp,
                                    content=content[:200])

                entities = self.nlp.extract_entities(content)
                concepts = self.nlp.extract_concepts(content)
                sentiment = self.nlp.get_sentiment(content)
                temporals = self.nlp.extract_temporal(content)
                actions = self.nlp.extract_action_verbs(content)

                for ent in entities[:3]:
                    node_id = self._normalize_concept(ent["text"])
                    node_type = self._ner_to_node_type(ent["label"])
                    self.add_concept_node(node_id, node_type, ent["text"])
                    self.graph.add_edge(chat_id, node_id,
                                        relationship="MENTIONED", weight=1.0)

                for concept in concepts[:5]:
                    node_id = self._normalize_concept(concept)
                    self.add_concept_node(node_id, "CONCEPT", concept)
                    self.graph.add_edge(chat_id, node_id,
                                        relationship="MENTIONED", weight=0.7)

                for t in temporals[:3]:
                    time_id = self._normalize_concept(t)
                    self.add_concept_node(time_id, "TIME", t)
                    self.graph.add_edge(chat_id, time_id,
                                        relationship="OCCURRED_AT", weight=1.0)

                if sentiment != "neutral":
                    emotion_id = f"emotion_{sentiment}"
                    if not self.graph.has_node(emotion_id):
                        self.graph.add_node(emotion_id, type="EMOTION",
                                            label=sentiment.capitalize(),
                                            mention_count=1)
                    else:
                        self.graph.nodes[emotion_id]["mention_count"] += 1
                    self.graph.add_edge(chat_id, emotion_id,
                                        relationship="EXPRESSES")

                for action in actions[:3]:
                    action_id = f"action_{action}"
                    self.add_concept_node(action_id, "ACTION", action,
                                          single_instance=True)
                    self.graph.add_edge(chat_id, action_id,
                                        relationship="PERFORMED", weight=0.6)

                if role == "user" and len(content) > 20:
                    for ent in entities[:2]:
                        node_id = self._normalize_concept(ent["text"])
                        self.graph.add_edge(chat_id, node_id,
                                            relationship="INTERESTED_IN", weight=1.2)
        except Exception as e:
            logger.warning("Error processing chat history: %s", e)

    async def _process_knowledge_graph(self):
        """Import existing knowledge graph nodes."""
        try:
            kg = get_knowledge_graph()
            for node_id, kgnode in kg.nodes.items():
                if not self.graph.has_node(node_id):
                    node_type = kgnode.type.upper()
                    if node_type not in self.NODE_TYPES:
                        node_type = "ENTITY"
                    self.graph.add_node(node_id, type=node_type,
                                        label=kgnode.properties.get("label", node_id),
                                        mention_count=1,
                                        source="knowledge_graph")
        except Exception as e:
            logger.warning("Error importing knowledge graph: %s", e)

    async def _compute_semantic_relationships(self):
        """Compute semantic relationships between all CONCEPT nodes."""
        concept_nodes = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("type") in ("CONCEPT", "ENTITY", "PERSON")
        ]

        if len(concept_nodes) < 2:
            return

        for node_id in concept_nodes:
            label = self.graph.nodes[node_id].get("label", node_id)
            try:
                from sentence_transformers import SentenceTransformer
                embedder = SentenceTransformer("all-MiniLM-L6-v2")
                emb = embedder.encode(label)
                self._concept_embeddings[node_id] = emb.tolist()
            except ImportError:
                pass

        import numpy as np
        node_ids = list(self._concept_embeddings.keys())
        if len(node_ids) < 2:
            return
        embeddings = np.array([self._concept_embeddings[nid] for nid in node_ids])

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarity = embeddings @ embeddings.T / (norms @ norms.T + 1e-8)

        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                if similarity[i][j] >= self.SEMANTIC_THRESHOLD:
                    if not self.graph.has_edge(node_ids[i], node_ids[j]):
                        self.graph.add_edge(
                            node_ids[i], node_ids[j],
                            relationship="RELATED_TO",
                            weight=float(similarity[i][j]),
                        )

        self._compute_co_occurrences()

    def _compute_co_occurrences(self):
        """Find concepts that frequently appear together."""
        source_nodes = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("type") in ("CHAT", "MEMORY")
        ]

        concept_pairs = defaultdict(int)
        for src in source_nodes:
            concepts = [
                n for n in self.graph.successors(src)
                if self.graph.nodes[n].get("type") in ("CONCEPT", "ENTITY", "PERSON")
            ]
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    pair = tuple(sorted([concepts[i], concepts[j]]))
                    concept_pairs[pair] += 1

        for (c1, c2), count in concept_pairs.items():
            if count >= self.CO_OCCUR_THRESHOLD:
                if not self.graph.has_edge(c1, c2):
                    self.graph.add_edge(c1, c2, relationship="CO_OCCURS_WITH",
                                        weight=min(count / 10, 1.0))

    def add_concept_node(self, node_id: str, node_type: str, label: str,
                         single_instance: bool = False):
        """Add or update a concept node with deduplication."""
        with self._lock:
            if self.graph.has_node(node_id):
                if not single_instance:
                    current_count = self.graph.nodes[node_id].get("mention_count", 1)
                    self.graph.nodes[node_id]["mention_count"] = current_count + 1
                return

            if node_type not in self.NODE_TYPES:
                node_type = "ENTITY"

            category = self.nlp.classify_concept_type(label)

            self.graph.add_node(
                node_id,
                type=node_type,
                label=label,
                mention_count=1,
                category=category,
            )

    def _normalize_concept(self, concept: str) -> str:
        """Normalize concept string for deduplication."""
        c = concept.lower().strip()
        c = re.sub(r"[^a-z0-9\s]", "", c)
        return c.replace(" ", "_")[:50]

    def _ner_to_node_type(self, ner_label: str) -> str:
        mapping = {
            "PERSON": "PERSON",
            "ORG": "ENTITY",
            "GPE": "ENTITY",
            "PRODUCT": "ENTITY",
            "EVENT": "CONCEPT",
            "WORK_OF_ART": "ENTITY",
            "DATE": "TIME",
            "TIME": "TIME",
        }
        return mapping.get(ner_label, "ENTITY")

    def get_node_neighborhood(self, node_id: str, depth: int = 2) -> dict:
        """Get subgraph around a node (for detail panel)."""
        if not self.graph.has_node(node_id):
            return {"error": f"Node not found: {node_id}"}

        visited = set()
        subgraph_nodes = []
        subgraph_edges = []

        def dfs(current: str, d: int):
            if d > depth or current in visited:
                return
            visited.add(current)
            node_data = dict(self.graph.nodes[current])
            subgraph_nodes.append({"id": current, **node_data})
            for neighbor in self.graph.successors(current):
                edge_data = dict(self.graph.edges[current, neighbor])
                subgraph_edges.append({"source": current, "target": neighbor, **edge_data})
                dfs(neighbor, d + 1)
            for neighbor in self.graph.predecessors(current):
                if neighbor not in visited:
                    edge_data = dict(self.graph.edges[neighbor, current])
                    subgraph_edges.append({"source": neighbor, "target": current, **edge_data})
                    dfs(neighbor, d + 1)

        dfs(node_id, 0)
        return {"center": node_id, "nodes": subgraph_nodes, "edges": subgraph_edges}

    def search_nodes(self, query: str) -> list[dict]:
        """Semantic search across graph nodes."""
        query_lower = query.lower()
        results = []

        for nid, data in self.graph.nodes(data=True):
            label = data.get("label", nid).lower()
            if query_lower in label:
                results.append({"id": nid, "label": data.get("label", nid),
                                "type": data.get("type"), "score": 1.0})
                continue
            category = data.get("category", "").lower()
            if query_lower in category:
                results.append({"id": nid, "label": data.get("label", nid),
                                "type": data.get("type"), "score": 0.8})

        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            query_emb = embedder.encode(query)
            for nid, data in self.graph.nodes(data=True):
                label = data.get("label", nid)
                label_emb = embedder.encode(label)
                import numpy as np
                sim = np.dot(query_emb, label_emb) / (
                    np.linalg.norm(query_emb) * np.linalg.norm(label_emb) + 1e-8
                )
                if sim > 0.6 and not any(r["id"] == nid for r in results):
                    results.append({"id": nid, "label": label,
                                    "type": data.get("type"), "score": float(sim)})
        except ImportError:
            pass

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:20]

    def get_stats(self) -> dict:
        """Get graph statistics."""
        with self._lock:
            total_nodes = self.graph.number_of_nodes()
            total_edges = self.graph.number_of_edges()

            type_counts = defaultdict(int)
            category_counts = defaultdict(int)
            mention_dist = []

            for _, data in self.graph.nodes(data=True):
                nt = data.get("type", "unknown")
                type_counts[nt] += 1
                cat = data.get("category", "general")
                category_counts[cat] += 1
                mention_dist.append(data.get("mention_count", 1))

            degree = list(self.graph.degree())
            degree.sort(key=lambda x: x[1], reverse=True)
            most_connected = [
                {"id": nid, "degree": d,
                 "label": self.graph.nodes[nid].get("label", nid),
                 "type": self.graph.nodes[nid].get("type")}
                for nid, d in degree[:10]
            ]

            concepts = [
                {"id": nid, "count": data.get("mention_count", 1),
                 "label": data.get("label", nid)}
                for nid, data in self.graph.nodes(data=True)
                if data.get("type") in ("CONCEPT", "ENTITY")
            ]
            concepts.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": dict(type_counts),
            "categories": dict(category_counts),
            "top_concepts": concepts[:15],
            "most_connected": most_connected,
            "last_built": self._last_built,
        }

    def _export_cytoscape(self) -> dict:
        """Convert networkx graph to cytoscape.js elements JSON."""
        elements = {"nodes": [], "edges": []}
        edge_counter = [0]

        with self._lock:
            node_ids = set()
            for nid, data in self.graph.nodes(data=True):
                if data.get("mention_count", 1) >= 1:
                    node_ids.add(nid)

            if len(node_ids) > self.MAX_NODES:
                sorted_nodes = sorted(
                    [(nid, self.graph.nodes[nid].get("mention_count", 1))
                     for nid in node_ids],
                    key=lambda x: x[1],
                    reverse=True,
                )
                node_ids = set(nid for nid, _ in sorted_nodes[:self.MAX_NODES])

            for nid in node_ids:
                data = self.graph.nodes[nid]
                elements["nodes"].append({
                    "data": {
                        "id": nid,
                        "label": data.get("label", nid),
                        "type": data.get("type", "ENTITY"),
                        "mention_count": data.get("mention_count", 1),
                        "category": data.get("category", "general"),
                        "timestamp": data.get("timestamp", ""),
                    }
                })

            for u, v, data in self.graph.edges(data=True):
                if u in node_ids and v in node_ids:
                    edge_counter[0] += 1
                    elements["edges"].append({
                        "data": {
                            "id": f"e{edge_counter[0]}",
                            "source": u,
                            "target": v,
                            "relationship": data.get("relationship", "RELATED_TO"),
                            "weight": data.get("weight", 1.0),
                        }
                    })

        return elements

    def get_cytoscape_graph(self) -> dict:
        """Get full graph in cytoscape.js format for the dashboard."""
        return self._export_cytoscape()

    async def incremental_update(self, text: str, source_id: str):
        """Process new text incrementally (after each chat turn)."""
        if not text or not text.strip():
            return

        entities = self.nlp.extract_entities(text)
        concepts = self.nlp.extract_concepts(text)
        sentiment = self.nlp.get_sentiment(text)
        temporals = self.nlp.extract_temporal(text)

        for ent in entities[:3]:
            node_id = self._normalize_concept(ent["text"])
            node_type = self._ner_to_node_type(ent["label"])
            self.add_concept_node(node_id, node_type, ent["text"])
            self.graph.add_edge(source_id, node_id, relationship="MENTIONED", weight=1.0)

        for concept in concepts[:5]:
            node_id = self._normalize_concept(concept)
            self.add_concept_node(node_id, "CONCEPT", concept)
            self.graph.add_edge(source_id, node_id, relationship="MENTIONED", weight=0.7)

        if sentiment != "neutral":
            emotion_id = f"emotion_{sentiment}"
            if not self.graph.has_node(emotion_id):
                self.graph.add_node(emotion_id, type="EMOTION",
                                    label=sentiment.capitalize(), mention_count=1)
            else:
                self.graph.nodes[emotion_id]["mention_count"] += 1
            self.graph.add_edge(source_id, emotion_id, relationship="EXPRESSES")

        for t in temporals[:2]:
            time_id = self._normalize_concept(t)
            self.add_concept_node(time_id, "TIME", t)
            self.graph.add_edge(source_id, time_id, relationship="OCCURRED_AT")

        self.save()

        try:
            bus = get_bus()
            bus.publish("graph.node.added", {"source_id": source_id})
        except Exception:
            pass


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


_builder_instance: Optional[MemoryGraphBuilder] = None


def get_memory_graph_builder() -> MemoryGraphBuilder:
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = MemoryGraphBuilder()
    return _builder_instance
