"""FRIDAY API Gateway — rate limiting, auth, routing, logging, and middleware."""
import os
import json
import time
import uuid
import hashlib
import hmac
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque


@dataclass
class APIRoute:
    path: str
    method: str
    target: str
    description: str = ""
    auth_required: bool = False
    rate_limit: int = 0
    timeout: int = 30
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class APIKey:
    key_id: str
    key_hash: str
    name: str
    scopes: List[str]
    created_at: float
    expires_at: float = 0.0
    enabled: bool = True
    last_used: float = 0.0
    usage_count: int = 0

    def to_dict(self):
        d = asdict(self)
        d.pop("key_hash", None)
        return d


@dataclass
class GatewayLog:
    timestamp: float
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: str = ""
    api_key_id: str = ""
    error: str = ""

    def to_dict(self):
        return asdict(self)


class APIGateway:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "gateway")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._routes: Dict[str, APIRoute] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._logs: deque = deque(maxlen=10000)
        self._rate_buckets: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._middleware: List[Callable] = []
        self._lock = threading.Lock()

        self._load_routes()
        self._load_keys()

    def _routes_file(self) -> str:
        return os.path.join(self.data_dir, "routes.json")

    def _keys_file(self) -> str:
        return os.path.join(self.data_dir, "keys.json")

    def _load_routes(self):
        if os.path.exists(self._routes_file()):
            try:
                with open(self._routes_file(), "r") as f:
                    data = json.load(f)
                for key, rdata in data.items():
                    self._routes[key] = APIRoute(**rdata)
            except Exception:
                pass

    def _save_routes(self):
        try:
            data = {k: r.to_dict() for k, r in self._routes.items()}
            with open(self._routes_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _load_keys(self):
        if os.path.exists(self._keys_file()):
            try:
                with open(self._keys_file(), "r") as f:
                    data = json.load(f)
                for kid, kdata in data.items():
                    self._api_keys[kid] = APIKey(**kdata)
            except Exception:
                pass

    def _save_keys(self):
        try:
            data = {k: k.to_dict() for k, k in self._api_keys.items()}
            with open(self._keys_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def generate_api_key(self, name: str, scopes: List[str] = None,
                        expires_in: int = 0) -> Dict:
        key_id = f"key-{uuid.uuid4().hex[:12]}"
        raw_key = f"friday-{uuid.uuid4().hex}"
        key_hash = self._hash_key(raw_key)
        expires_at = time.time() + expires_in if expires_in > 0 else 0

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes or ["*"],
            created_at=time.time(),
            expires_at=expires_at,
        )

        with self._lock:
            self._api_keys[key_id] = api_key
            self._save_keys()

        return {"key_id": key_id, "key": raw_key, "name": name, "scopes": api_key.scopes}

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        key_hash = self._hash_key(raw_key)
        for key in self._api_keys.values():
            if key.key_hash == key_hash and key.enabled:
                if key.expires_at > 0 and time.time() > key.expires_at:
                    return None
                key.last_used = time.time()
                key.usage_count += 1
                return key
        return None

    def revoke_key(self, key_id: str) -> bool:
        with self._lock:
            if key_id in self._api_keys:
                self._api_keys[key_id].enabled = False
                self._save_keys()
                return True
            return False

    def add_route(self, route: APIRoute):
        key = f"{route.method}:{route.path}"
        with self._lock:
            self._routes[key] = route
            self._save_routes()

    def remove_route(self, path: str, method: str = None) -> bool:
        with self._lock:
            if method:
                key = f"{method}:{path}"
                if key in self._routes:
                    del self._routes[key]
                    self._save_routes()
                    return True
            else:
                removed = False
                keys_to_remove = [k for k in self._routes if k.endswith(f":{path}")]
                for k in keys_to_remove:
                    del self._routes[k]
                    removed = True
                if removed:
                    self._save_routes()
                return removed
            return False

    def list_routes(self) -> List[Dict]:
        with self._lock:
            return [r.to_dict() for r in self._routes.values()]

    def check_rate_limit(self, client_id: str, limit: int = 100, window: int = 60) -> bool:
        now = time.time()
        bucket = self._rate_buckets[client_id]
        while bucket and bucket[0] < now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    def log_request(self, method: str, path: str, status_code: int,
                   duration_ms: float, client_ip: str = "", api_key_id: str = ""):
        log = GatewayLog(
            timestamp=time.time(),
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            api_key_id=api_key_id,
        )
        self._logs.append(log)

    def get_logs(self, limit: int = 100, status_code: int = None,
                path: str = None) -> List[Dict]:
        logs = list(self._logs)
        if status_code:
            logs = [l for l in logs if l.status_code == status_code]
        if path:
            logs = [l for l in logs if path in l.path]
        return [l.to_dict() for l in logs[-limit:]]

    def get_stats(self) -> Dict:
        logs = list(self._logs)
        total = len(logs)
        if total == 0:
            return {"total_requests": 0}

        status_counts = defaultdict(int)
        method_counts = defaultdict(int)
        path_counts = defaultdict(int)
        total_duration = 0

        for log in logs:
            status_counts[log.status_code] += 1
            method_counts[log.method] += 1
            path_counts[log.path] += 1
            total_duration += log.duration_ms

        return {
            "total_requests": total,
            "avg_duration_ms": round(total_duration / total, 2),
            "status_codes": dict(status_counts),
            "methods": dict(method_counts),
            "top_paths": dict(sorted(path_counts.items(), key=lambda x: -x[1])[:10]),
            "error_rate": round(
                sum(1 for l in logs if l.status_code >= 400) / total * 100, 2
            ),
        }

    def add_middleware(self, middleware: Callable):
        self._middleware.append(middleware)

    def export_config(self) -> Dict:
        return {
            "routes": self.list_routes(),
            "api_keys": [k.to_dict() for k in self._api_keys.values()],
            "stats": self.get_stats(),
        }


_gateway = None


def _get_gateway() -> APIGateway:
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway


def api_gateway_tool(action: str = "routes", **kwargs) -> Any:
    """API gateway tool dispatcher."""
    try:
        gateway = _get_gateway()

        if action == "routes":
            return {"routes": gateway.list_routes()}

        elif action == "add_route":
            route_data = kwargs.get("route", {})
            route = APIRoute(**route_data)
            gateway.add_route(route)
            return {"success": True}

        elif action == "remove_route":
            path = kwargs.get("path", "")
            method = kwargs.get("method")
            ok = gateway.remove_route(path, method)
            return {"success": ok}

        elif action == "generate_key":
            name = kwargs.get("name", "")
            scopes = kwargs.get("scopes", ["*"])
            expires_in = kwargs.get("expires_in", 0)
            if not name:
                return {"error": "No name provided"}
            return gateway.generate_api_key(name, scopes, expires_in)

        elif action == "validate_key":
            key = kwargs.get("key", "")
            if not key:
                return {"error": "No key provided"}
            api_key = gateway.validate_key(key)
            if api_key:
                return {"valid": True, "key": api_key.to_dict()}
            return {"valid": False}

        elif action == "revoke_key":
            key_id = kwargs.get("key_id", "")
            ok = gateway.revoke_key(key_id)
            return {"success": ok}

        elif action == "keys":
            return {"keys": [k.to_dict() for k in gateway._api_keys.values()]}

        elif action == "check_rate":
            client_id = kwargs.get("client_id", "default")
            limit = kwargs.get("limit", 100)
            window = kwargs.get("window", 60)
            allowed = gateway.check_rate_limit(client_id, limit, window)
            return {"allowed": allowed}

        elif action == "logs":
            limit = kwargs.get("limit", 100)
            status_code = kwargs.get("status_code")
            path = kwargs.get("path")
            return {"logs": gateway.get_logs(limit, status_code, path)}

        elif action == "stats":
            return gateway.get_stats()

        elif action == "export":
            return gateway.export_config()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
