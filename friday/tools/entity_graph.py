import re
import socket
import asyncio
from typing import Any
try:
    import networkx as nx
except ImportError:
    nx = None


ENTITY_TYPES = {
    "username": {"color": "#00ffcc", "icon": "user"},
    "email": {"color": "#ff6600", "icon": "mail"},
    "domain": {"color": "#0066ff", "icon": "globe"},
    "ip": {"color": "#9933ff", "icon": "server"},
    "phone": {"color": "#ffcc00", "icon": "phone"},
    "social_profile": {"color": "#ff3366", "icon": "users"},
    "threat": {"color": "#ff003c", "icon": "alert-triangle"},
    "breach": {"color": "#ff0000", "icon": "shield-off"},
    "organization": {"color": "#33ccff", "icon": "building"},
    "location": {"color": "#66ff99", "icon": "map-pin"},
}


class EntityGraph:
    def __init__(self):
        self._graph = nx.MultiDiGraph() if nx else None

    def add_entity(self, entity_id: str, label: str, entity_type: str = "username", attributes: dict | None = None) -> str:
        eid = entity_id or f"ent_{abs(hash(label)) % 10**8}"
        attrs = dict(attributes or {})
        attrs.update({"label": label, "type": entity_type, **ENTITY_TYPES.get(entity_type, {})})
        if self._graph:
            self._graph.add_node(eid, **attrs)
        return eid

    def add_relation(self, source: str, target: str, label: str = "RELATED_TO", attributes: dict | None = None):
        if self._graph:
            self._graph.add_edge(source, target, label=label, **(attributes or {}))

    def expand_domain(self, domain: str) -> dict[str, Any]:
        eid = self.add_entity(None, domain, "domain")
        results = {"domain": domain, "ips": [], "subdomains": [], "mx": [], "ns": []}
        try:
            ips = set()
            for info in socket.getaddrinfo(domain, 80):
                ips.add(info[4][0])
            results["ips"] = list(ips)
            for ip in ips:
                ip_id = self.add_entity(None, ip, "ip", {"domain": domain})
                self.add_relation(eid, ip_id, "RESOLVES_TO")
        except Exception:
            pass
        try:
            import dns.resolver
            for rtype in ("MX", "NS", "TXT"):
                try:
                    for ans in dns.resolver.resolve(domain, rtype):
                        rid = self.add_entity(None, str(ans.target if rtype == "MX" else ans),
                                              "domain" if rtype in ("MX", "NS") else "text")
                        self.add_relation(eid, rid, rtype)
                        results[rtype.lower()].append(str(ans))
                except Exception:
                    pass
        except ImportError:
            pass
        return results

    def expand_email(self, email: str) -> dict[str, Any]:
        eid = self.add_entity(None, email, "email")
        results = {"email": email, "domain": None, "breaches": []}
        match = re.match(r"[^@]+@(.+)", email)
        if match:
            domain = match.group(1)
            results["domain"] = domain
            did = self.add_entity(None, domain, "domain")
            self.add_relation(eid, did, "USES_DOMAIN")
        return results

    def expand_username(self, username: str) -> dict[str, Any]:
        eid = self.add_entity(None, username, "username")
        return {"username": username, "profiles": [], "emails": []}

    def expand_ip(self, ip_str: str) -> dict[str, Any]:
        eid = self.add_entity(None, ip_str, "ip")
        results = {"ip": ip_str, "hostname": None, "ports": []}
        try:
            hostname = socket.gethostbyaddr(ip_str)[0]
            results["hostname"] = hostname
            hid = self.add_entity(None, hostname, "domain")
            self.add_relation(eid, hid, "HOSTNAME")
        except Exception:
            pass
        return results

    def merge_graph(self, other: "EntityGraph"):
        if self._graph and other._graph:
            self._graph = nx.compose(self._graph, other._graph)

    def to_cytoscape(self) -> dict:
        if not self._graph:
            return {"nodes": [], "edges": []}
        nodes = []
        for nid, data in self._graph.nodes(data=True):
            nodes.append({"id": nid, **{k: v for k, v in data.items() if k != "label"}, "label": data.get("label", nid)})
        edges = []
        for u, v, k, data in self._graph.edges(data=True, keys=True):
            edges.append({"source": u, "target": v, "label": data.get("label", "RELATED_TO")})
        return {"nodes": nodes, "edges": edges}

    def stats(self) -> dict:
        if not self._graph:
            return {"entities": 0, "relationships": 0}
        return {"entities": self._graph.number_of_nodes(), "relationships": self._graph.number_of_edges()}

    def reset(self):
        if self._graph:
            self._graph.clear()


_shared_graph = None


def get_entity_graph() -> EntityGraph:
    global _shared_graph
    if _shared_graph is None:
        _shared_graph = EntityGraph()
    return _shared_graph


async def run_entity_expand(entity_value: str, entity_type: str = "auto") -> dict:
    g = get_entity_graph()
    if entity_type == "auto":
        if re.match(r"[^@]+@[^@]+\.[^@]+", entity_value):
            entity_type = "email"
        elif re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", entity_value):
            entity_type = "ip"
        elif re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$", entity_value):
            entity_type = "domain"
        elif re.match(r"^\+?\d{7,15}$", entity_value):
            entity_type = "phone"
        else:
            entity_type = "username"
    expanders = {
        "domain": lambda: g.expand_domain(entity_value),
        "email": lambda: g.expand_email(entity_value),
        "username": lambda: g.expand_username(entity_value),
        "ip": lambda: g.expand_ip(entity_value),
    }
    expander = expanders.get(entity_type, expanders["username"])
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, expander)
    return {"entity": entity_value, "type": entity_type, "graph": g.to_cytoscape(), "stats": g.stats(), **result}
