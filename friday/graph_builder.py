"""
FRIDAY Graph Builder — extends knowledge_graph.py with typed OSINT entities
and relationships. Adds entity-relationship graph with networkx-style operations
for the Ghost OSINT agent.

Stores entity types: PERSON, USERNAME, EMAIL, IP, DOMAIN, PHONE, LOCATION,
SOCIAL_PROFILE, DEVICE, IMAGE.

Edge types: OWNS, LINKED_TO, APPEARED_ON, LEAKED_FROM, LOCATED_AT, USED_DEVICE,
CAPTURED_BY.

Exports cytoscape.js compatible JSON for the dashboard.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from friday.knowledge_graph import KnowledgeGraph, get_knowledge_graph
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)

# ─── Entity Types ───────────────────────────────────────────

ENTITY_TYPES = frozenset({
    "PERSON", "USERNAME", "EMAIL", "IP", "DOMAIN", "PHONE",
    "LOCATION", "SOCIAL_PROFILE", "DEVICE", "IMAGE", "ORGANIZATION",
})

EDGE_TYPES = frozenset({
    "OWNS", "LINKED_TO", "APPEARED_ON", "LEAKED_FROM",
    "LOCATED_AT", "USED_DEVICE", "CAPTURED_BY", "MENTIONS",
})


def _graph_persist_path() -> Path:
    cfg = ensure_config()
    p = cfg.get("osint", {}).get("graph_persist_path", "data/osint_graph.json")
    return Path(p)


class GraphBuilder:
    """
    Extends the existing KnowledgeGraph with OSINT-specific typed entities
    and relationships. Persists to a separate JSON file for dashboard
    consumption.

    Wraps the global KnowledgeGraph singleton from knowledge_graph.py.
    """

    def __init__(self):
        self._kg: KnowledgeGraph = get_knowledge_graph()
        self._persist_path = _graph_persist_path()
        self._adj: dict[str, dict[str, list[dict]]] = {}  # node_id -> {target -> [edges]}
        self._loaded = False
        self.load_graph()

    # ── Persistence ──────────────────────────────────────────

    def load_graph(self):
        """Load adjacency graph from disk if exists."""
        if self._loaded:
            return
        if self._persist_path.exists():
            try:
                data = json.loads(self._persist_path.read_text(encoding="utf-8"))
                self._adj = data.get("adjacency", {})
                # Rebuild KG nodes from stored entities
                for node_id, node_data in data.get("entities", {}).items():
                    if node_id not in self._kg.nodes:
                        self._kg.add_node(
                            node_id,
                            node_data.get("entity_type", "entity"),
                            node_data.get("attributes", {}),
                        )
                logger.info("Loaded OSINT graph from %s (%d entities)",
                            self._persist_path, len(self._adj))
            except Exception as exc:
                logger.warning("Failed to load OSINT graph: %s", exc)
        self._loaded = True

    def save_graph(self):
        """Persist adjacency graph to disk (networkx-style JSON)."""
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)

        # Build entity dict for cytoscape.js compatibility
        entities = {}
        for nid, node in self._kg.nodes.items():
            entities[nid] = {
                "entity_type": node.type.upper(),
                "attributes": node.properties,
            }

        data = {
            "adjacency": self._adj,
            "entities": entities,
            "elements": self.export_cytoscape_json(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        self._persist_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── Entity Management ───────────────────────────────────

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        attributes: dict | None = None,
    ) -> dict:
        """
        Add a typed entity node. Returns the node dict.
        If entity already exists, updates attributes.
        """
        normalized_type = entity_type.upper()
        if normalized_type not in ENTITY_TYPES:
            normalized_type = "entity"

        if entity_id in self._kg.nodes:
            existing = self._kg.nodes[entity_id]
            if attributes:
                existing.properties.update(attributes)
        else:
            self._kg.add_node(entity_id, normalized_type.lower(), attributes or {})

        if entity_id not in self._adj:
            self._adj[entity_id] = {}

        self.save_graph()
        return self._kg.nodes[entity_id].to_dict()

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        metadata: dict | None = None,
    ) -> bool:
        """
        Add a typed relationship between two entities.
        Creates missing entities as stubs.
        """
        normalized_edge = edge_type.upper()
        if normalized_edge not in EDGE_TYPES:
            normalized_edge = "LINKED_TO"

        # Ensure both nodes exist
        if source_id not in self._kg.nodes:
            self._kg.add_node(source_id, "entity", {"label": source_id})
        if target_id not in self._kg.nodes:
            self._kg.add_node(target_id, "entity", {"label": target_id})

        # Add to KnowledgeGraph
        self._kg.add_edge(source_id, target_id, normalized_edge.lower(), 1.0)

        # Add to adjacency
        if source_id not in self._adj:
            self._adj[source_id] = {}
        if target_id not in self._adj:
            self._adj[target_id] = {}

        edge_entry = {
            "type": normalized_edge,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Bidirectional adjacency
        self._adj[source_id].setdefault(target_id, []).append(edge_entry)
        self._adj[target_id].setdefault(source_id, []).append({
            "type": normalized_edge,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "_reversed": True,
        })

        self.save_graph()
        return True

    def add_social_profile(self, username: str, platform: str, url: str) -> dict:
        """Convenience: add a SOCIAL_PROFILE entity linked to a USERNAME."""
        profile_id = f"social_{platform}_{username}"
        self.add_entity(profile_id, "SOCIAL_PROFILE", {
            "username": username,
            "platform": platform,
            "url": url,
        })
        self.add_entity(f"user_{username}", "USERNAME", {"username": username})
        self.add_relationship(
            f"user_{username}", profile_id, "APPEARED_ON",
            {"platform": platform, "url": url},
        )
        return profile_id

    # ── Query ────────────────────────────────────────────────

    def query_entity(self, entity_id: str) -> dict:
        """
        Return entity details including all neighbors and relationships.
        """
        node = self._kg.get_node(entity_id)
        if not node:
            return {"error": f"Entity not found: {entity_id}"}

        neighbors = self._kg.get_neighbors(entity_id)
        relationships = []
        for neighbor_id, rel, weight in neighbors:
            neighbor_node = self._kg.get_node(neighbor_id)
            relationships.append({
                "target_id": neighbor_id,
                "target_type": neighbor_node.type if neighbor_node else "unknown",
                "relation": rel,
                "weight": weight,
            })

        return {
            "entity": node.to_dict(),
            "relationships": relationships,
            "relationship_count": len(relationships),
        }

    def find_connections(self, entity_a: str, entity_b: str) -> list[list[str]]:
        """
        Find all paths between two entities (shortest path via BFS).
        Returns list of paths (each path is list of node IDs).
        """
        if entity_a not in self._adj or entity_b not in self._adj:
            return []

        # BFS for shortest path
        queue: deque[list[str]] = deque([[entity_a]])
        visited = {entity_a}
        paths = []

        while queue and len(paths) < 5:
            path = queue.popleft()
            current = path[-1]

            if current == entity_b:
                paths.append(path)
                continue

            for neighbor in self._adj.get(current, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return paths

    # ── Export ───────────────────────────────────────────────

    def export_cytoscape_json(self) -> dict:
        """
        Export graph as cytoscape.js elements JSON for dashboard.
        Format:
          { nodes: [{ data: { id, label, entity_type, ... } }],
            edges: [{ data: { id, source, target, label } }] }
        """
        elements = {"nodes": [], "edges": []}
        edge_id = 0

        for nid, node in self._kg.nodes.items():
            elements["nodes"].append({
                "data": {
                    "id": nid,
                    "label": node.properties.get("label", node.properties.get("username", nid)),
                    "entity_type": node.type.upper(),
                    **{k: v for k, v in node.properties.items() if k not in ("label", "username")},
                }
            })

        for src, targets in self._adj.items():
            for tgt, edge_list in targets.items():
                for edge in edge_list:
                    if edge.get("_reversed"):
                        continue
                    edge_id += 1
                    elements["edges"].append({
                        "data": {
                            "id": f"e{edge_id}",
                            "source": src,
                            "target": tgt,
                            "label": edge["type"],
                        }
                    })

        return elements

    # ── Stats ────────────────────────────────────────────────

    def get_stats(self) -> dict:
        kg_stats = self._kg.get_stats()
        return {
            **kg_stats,
            "adjacency_edges": sum(len(t) for t in self._adj.values()),
            "entity_types": dict(ENTITY_TYPES),
        }

    def export_graph_json(self) -> dict:
        """Full graph export for dashboard panel."""
        return self.export_cytoscape_json()


# ── Singleton ────────────────────────────────────────────────

_builder_instance: Optional[GraphBuilder] = None


def get_graph_builder() -> GraphBuilder:
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = GraphBuilder()
    return _builder_instance
