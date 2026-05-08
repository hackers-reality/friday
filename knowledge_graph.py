"""
Friday Knowledge Graph - Semantic knowledge representation.
Stores entities, relationships, and facts for advanced reasoning.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


# ─── Knowledge Graph Node ────────────────────────────#

class KGNode:
    """A node in the knowledge graph."""
    
    def __init__(self, node_id: str, node_type: str, properties: Dict[str, Any] = None):
        self.id = node_id
        self.type = node_type  # person, place, thing, concept, etc.
        self.properties = properties or {}
        self.embeddings = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "properties": self.properties,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGNode':
        return cls(data["id"], data["type"], data.get("properties"))


# ─── Knowledge Graph Edge ────────────────────────────#

class KGEdge:
    """An edge in the knowledge graph."""
    
    def __init__(self, source: str, target: str, relation: str, weight: float = 1.0):
        self.source = source
        self.target = target
        self.relation = relation  # is_a, part_of, located_in, knows, etc.
        self.weight = weight
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGEdge':
        return cls(data["source"], data["target"], data["relation"], data.get("weight", 1.0))


# ─── Knowledge Graph ────────────────────────────#

class KnowledgeGraph:
    """Main knowledge graph implementation."""
    
    def __init__(self, storage_path: str = "friday_memory/knowledge_graph.json"):
        self.storage_path = Path(storage_path)
        self.nodes: Dict[str, KGNode] = {}
        self.edges: List[KGEdge] = []
        self._load()
        
    def _load(self):
        """Load graph from storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for node_data in data.get("nodes", []):
                node = KGNode.from_dict(node_data)
                self.nodes[node.id] = node
                
            for edge_data in data.get("edges", []):
                edge = KGEdge.from_dict(edge_data)
                self.edges.append(edge)
                
        except Exception as e:
            print(f"[KnowledgeGraph] Load error: {e}")
    
    def save(self):
        """Save graph to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "last_updated": datetime.now().isoformat(),
        }
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any] = None) -> bool:
        """Add a node to the graph."""
        if node_id in self.nodes:
            return False
        
        self.nodes[node_id] = KGNode(node_id, node_type, properties)
        self.save()
        return True
    
    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0) -> bool:
        """Add an edge to the graph."""
        if source not in self.nodes or target not in self.nodes:
            return False
        
        # Check if edge already exists
        for edge in self.edges:
            if edge.source == source and edge.target == target and edge.relation == relation:
                edge.weight = weight
                self.save()
                return True
        
        self.edges.append(KGEdge(source, target, relation, weight))
        self.save()
        return True
    
    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_neighbors(self, node_id: str, relation: str = None) -> List[Tuple[str, str, float]]:
        """
        Get neighboring nodes.
        Returns list of (node_id, relation, weight)
        """
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                if relation is None or edge.relation == relation:
                    neighbors.append((edge.target, edge.relation, edge.weight))
            elif edge.target == node_id:
                if relation is None or edge.relation == relation:
                    neighbors.append((edge.source, f"inverse_{edge.relation}", edge.weight))
        return neighbors
    
    def search_nodes(self, query: str, node_type: str = None) -> List[KGNode]:
        """Search nodes by query."""
        results = []
        query_lower = query.lower()
        
        for node in self.nodes.values():
            if node_type and node.type != node_type:
                continue
                
            # Search in ID
            if query_lower in node.id.lower():
                results.append(node)
                continue
                
            # Search in properties
            prop_str = json.dumps(node.properties).lower()
            if query_lower in prop_str:
                results.append(node)
                
        return results
    
    def find_path(self, source_id: str, target_id: str) -> List[str]:
        """Find shortest path between two nodes using BFS."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        
        from collections import deque
        queue = deque([[source_id]])
        visited = {source_id}
        
        while queue:
            path = queue.popleft()
            current = path[-1]
            
            if current == target_id:
                return path
            
            for neighbor_id, _, _ in self.get_neighbors(current):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])
        
        return []  # No path found
    
    def get_subgraph(self, node_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get subgraph around a node."""
        visited = set()
        nodes_in_subgraph = []
        edges_in_subgraph = []
        
        def dfs(current: str, depth: int):
            if depth > max_depth or current in visited:
                return
            visited.add(current)
            nodes_in_subgraph.append(current)
            
            for neighbor_id, relation, weight in self.get_neighbors(current):
                edges_in_subgraph.append({
                    "source": current,
                    "target": neighbor_id,
                    "relation": relation,
                })
                dfs(neighbor_id, depth + 1)
        
        dfs(node_id, 0)
        
        return {
            "center": node_id,
            "nodes": [self.nodes[n].to_dict() for n in nodes_in_subgraph if n in self.nodes],
            "edges": edges_in_subgraph,
            "node_count": len(nodes_in_subgraph),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        # Count by type
        type_counts = {}
        for node in self.nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": type_counts,
            "density": len(self.edges) / (len(self.nodes) ** 2) if self.nodes else 0,
        }


# ─── Singleton Graph ────────────────────────────#

_graph_instance: Optional[KnowledgeGraph] = None

def get_knowledge_graph() -> KnowledgeGraph:
    """Get or create the global knowledge graph."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = KnowledgeGraph()
    return _graph_instance


# ─── Text to Graph ────────────────────────────#

def extract_knowledge_from_text(text: str) -> Dict[str, Any]:
    """
    Extract knowledge (entities and relations) from text.
    Uses basic NLP patterns (can be enhanced with LLM).
    """
    import re
    
    # Simple pattern matching for relationships
    patterns = [
        (r'(\w+)\s+is\s+a\s+(\w+)', 'is_a'),
        (r'(\w+)\s+has\s+(\w+)', 'has'),
        (r'(\w+)\s+lives\s+in\s+(\w+)', 'lives_in'),
        (r'(\w+)\s+works\s+at\s+(\w+)', 'works_at'),
        (r'(\w+)\s+knows\s+(\w+)', 'knows'),
    ]
    
    entities = set()
    relations = []
    
    for pattern, relation in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            source, target = match
            entities.add(source.lower())
            entities.add(target.lower())
            relations.append((source.lower(), target.lower(), relation))
    
    return {
        "entities": list(entities),
        "relations": relations,
    }


# ─── Tool Function for Friday ────────────────────────────#

def knowledge_graph_tool(
    action: str = "stats",
    node_id: str = None,
    target_id: str = None,
    relation: str = None,
    properties: str = None,  # JSON string
    text: str = None,
) -> str:
    """
    Friday tool for knowledge graph operations.
    Actions: stats, add_node, add_edge, get, neighbors, search, path, subgraph, extract
    """
    graph = get_knowledge_graph()
    
    if action == "stats":
        stats = graph.get_stats()
        lines = ["### KNOWLEDGE GRAPH STATS", ""]
        lines.append(f"**Nodes**: {stats['total_nodes']}")
        lines.append(f"**Edges**: {stats['total_edges']}")
        lines.append(f"**Density**: {stats['density']:.3f}")
        if stats['node_types']:
            lines.append("")
            lines.append("**By Type**:")
            for node_type, count in stats['node_types'].items():
                lines.append(f"  - {node_type}: {count}")
        return "\n".join(lines)
    
    if action == "add_node":
        if not node_id:
            return "[FAIL] node_id required."
        
        props = {}
        if properties:
            try:
                props = json.loads(properties)
            except:
                pass
        
        # Try to determine type from node_id
        node_type = "concept"
        if any(word in node_id.lower() for word in ["person", "people", "mr", "ms", "dr"]):
            node_type = "person"
        elif any(word in node_id.lower() for word in ["city", "country", "place", "location"]):
            node_type = "place"
        elif any(word in node_id.lower() for word in ["company", "org", "corp"]):
            node_type = "organization"
        
        if graph.add_node(node_id, node_type, props):
            return f"[OK] Added node: {node_id}"
        return f"Node already exists: {node_id}"
    
    if action == "add_edge":
        if not node_id or not target_id or not relation:
            return "[FAIL] node_id, target_id, and relation required."
        
        if graph.add_edge(node_id, target_id, relation):
            return f"[OK] Added edge: {node_id} -[{relation}]-> {target_id}"
        return f"[FAIL] Failed to add edge. Check node IDs exist."
    
    if action == "get":
        if not node_id:
            return "[FAIL] node_id required."
        
        node = graph.get_node(node_id)
        if not node:
            return f"[FAIL] Node not found: {node_id}"
        
        lines = [f"### NODE: {node.id}", ""]
        lines.append(f"**Type**: {node.type}")
        if node.properties:
            lines.append("**Properties**:")
            for k, v in node.properties.items():
                lines.append(f"  - {k}: {v}")
        return "\n".join(lines)
    
    if action == "neighbors":
        if not node_id:
            return "[FAIL] node_id required."
        
        neighbors = graph.get_neighbors(node_id, relation)
        if not neighbors:
            return f"No neighbors found for: {node_id}"
        
        lines = [f"### NEIGHBORS: {node_id}", ""]
        for neighbor_id, rel, weight in neighbors:
            lines.append(f"- {neighbor_id} ({rel}, weight: {weight:.1f})")
        return "\n".join(lines)
    
    if action == "search":
        if not node_id:  # Using node_id as query here
            return "[FAIL] query required (use node_id parameter)."
        
        results = graph.search_nodes(node_id)
        if not results:
            return f"No nodes found matching: {node_id}"
        
        lines = [f"### SEARCH: {node_id} ({len(results)} found)", ""]
        for node in results[:20]:
            lines.append(f"- {node.id} ({node.type})")
        return "\n".join(lines)
    
    if action == "path":
        if not node_id or not target_id:
            return "[FAIL] source (node_id) and target (target_id) required."
        
        path = graph.find_path(node_id, target_id)
        if not path:
            return f"[FAIL] No path found from {node_id} to {target_id}"
        
        return f"### PATH: {node_id} -> {target_id}\n" + " -> ".join(path)
    
    if action == "subgraph":
        if not node_id:
            return "[FAIL] center node (node_id) required."
        
        subgraph = graph.get_subgraph(node_id)
        lines = [f"### SUBGRAPH: {subgraph['center']}", ""]
        lines.append(f"**Nodes**: {subgraph['node_count']}")
        lines.append("")
        lines.append("**Nodes**:")
        for node_data in subgraph["nodes"][:20]:
            lines.append(f"  - {node_data['id']} ({node_data['type']})")
        return "\n".join(lines)
    
    if action == "extract":
        if not text:
            return "[FAIL] text required for extraction."
        
        result = extract_knowledge_from_text(text)
        lines = ["### EXTRACTED KNOWLEDGE", ""]
        lines.append(f"**Entities**: {len(result['entities'])}")
        for entity in result["entities"][:20]:
            lines.append(f"  - {entity}")
        lines.append("")
        lines.append(f"**Relations**: {len(result['relations'])}")
        for source, target, rel in result["relations"][:20]:
            lines.append(f"  - {source} -[{rel}]-> {target}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Knowledge Graph...\n")
    
    # Add some test data
    graph = get_knowledge_graph()
    
    print("\n--- Adding Nodes ---")
    print(knowledge_graph_tool("add_node", node_id="apple", properties='{"type": "company", "industry": "tech"}'))
    print(knowledge_graph_tool("add_node", node_id="tim_cook", properties='{"title": "CEO"}'))
    print(knowledge_graph_tool("add_node", node_id="iphone", properties='{"type": "product"}'))
    
    print("\n--- Adding Edges ---")
    print(knowledge_graph_tool("add_edge", node_id="tim_cook", target_id="apple", relation="works_at"))
    print(knowledge_graph_tool("add_edge", node_id="apple", target_id="iphone", relation="produces"))
    
    print("\n--- Stats ---")
    print(knowledge_graph_tool("stats"))
    
    print("\n--- Path ---")
    print(knowledge_graph_tool("path", node_id="tim_cook", target_id="iphone"))
