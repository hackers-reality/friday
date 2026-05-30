"""
Knowledge Graph tools
Libraries: neo4j, pyvis, networkx
"""
import asyncio
import json
import os
import tempfile
from typing import Any

HAS_NEO4J = False
HAS_PYVIS = False
HAS_NETWORKX = False
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    pass
try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    pass
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    pass


# ── Neo4j ──
_neo4j_driver = None


def _get_neo4j():
    global _neo4j_driver
    if _neo4j_driver is None and HAS_NEO4J:
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        _neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
    return _neo4j_driver


async def neo4j_run_query(query: str, params: dict | None = None) -> dict[str, Any]:
    if not HAS_NEO4J:
        return {"error": "neo4j not installed"}
    try:
        driver = _get_neo4j()
        session = driver.session()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(session.run(query, parameters=params or {})))
        records = []
        for r in result:
            records.append({k: str(v) for k, v in r.data().items()})
        session.close()
        return {"query": query[:200], "records": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e)}


async def neo4j_create_entity(label: str, properties: dict) -> dict[str, Any]:
    if not HAS_NEO4J:
        return {"error": "neo4j not installed"}
    try:
        driver = _get_neo4j()
        session = driver.session()
        props = json.dumps(properties)
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(session.run(f"CREATE (n:{label} $props) RETURN id(n) AS id, n", props=properties)))
        session.close()
        if result:
            return {"label": label, "id": result[0].data()["id"], "properties": properties}
        return {"error": "Failed to create entity"}
    except Exception as e:
        return {"error": str(e)}


async def neo4j_find_entities(label: str, limit: int = 50) -> dict[str, Any]:
    if not HAS_NEO4J:
        return {"error": "neo4j not installed"}
    try:
        driver = _get_neo4j()
        session = driver.session()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(session.run(f"MATCH (n:{label}) RETURN n LIMIT {limit}")))
        session.close()
        records = [r.data()["n"] for r in result]
        return {"label": label, "entities": [{k: str(v) for k, v in r.items()} for r in records], "count": len(records)}
    except Exception as e:
        return {"error": str(e)}


# ── PyVis ──
async def create_graph_visualization(nodes: list[dict], edges: list[dict],
                                      output_path: str | None = None, title: str = "Knowledge Graph") -> dict[str, Any]:
    if not HAS_PYVIS:
        return {"error": "pyvis not installed"}
    try:
        net = Network(height="600px", width="100%", directed=True, notebook=False)
        for n in nodes:
            net.add_node(n["id"], label=n.get("label", n["id"]), title=n.get("label", n["id"]),
                        color=n.get("color", "#00ffcc"))
        for e in edges:
            net.add_edge(e["source"], e["target"], title=e.get("label", ""), label=e.get("label", ""))
        out = output_path or os.path.join(tempfile.gettempdir(), "friday_knowledge_graph.html")
        net.show(out)
        return {"path": out, "nodes": len(nodes), "edges": len(edges), "title": title}
    except Exception as e:
        return {"error": str(e)}


# ── NetworkX ──
async def analyze_graph(nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
    if not HAS_NETWORKX:
        return {"error": "networkx not installed"}
    try:
        G = nx.Graph()
        for n in nodes:
            G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
        for e in edges:
            G.add_edge(e["source"], e["target"], label=e.get("label", ""))
        centrality = nx.degree_centrality(G)
        communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_edges() > 0 else []
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {}
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": nx.density(G),
            "connected_components": nx.number_connected_components(G),
            "communities": len(communities),
            "most_central": sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10],
            "most_between": sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10],
        }
    except Exception as e:
        return {"error": str(e)}


# ── RDF / SPARQL helper ──
async def sparql_query(endpoint: str, query: str) -> dict[str, Any]:
    try:
        import requests
        headers = {"Accept": "application/sparql-results+json"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(endpoint, params={"query": query}, headers=headers, timeout=30))
        data = r.json()
        return {"endpoint": endpoint, "results": data.get("results", {}).get("bindings", [])[:50],
                "count": len(data.get("results", {}).get("bindings", []))}
    except ImportError:
        return {"error": "requests not installed"}
    except Exception as e:
        return {"error": str(e)}
