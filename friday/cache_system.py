"""FRIDAY Cache System — multi-tier caching with LRU, TTL, and persistence."""
import os
import json
import time
import hashlib
import threading
import pickle
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import OrderedDict
from pathlib import Path


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    size_bytes: int = 0
    tier: str = "memory"
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "key": self.key,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "size_bytes": self.size_bytes,
            "tier": self.tier,
            "tags": self.tags,
        }


class LRUCache:
    def __init__(self, max_size: int = 1000, max_bytes: int = 100 * 1024 * 1024):
        self.max_size = max_size
        self.max_bytes = max_bytes
        self._cache: OrderedDict = OrderedDict()
        self._sizes: Dict[str, int] = {}
        self._total_bytes = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                entry = self._cache[key]
                entry.access_count += 1
                entry.last_accessed = time.time()
                return entry.value
            return None

    def put(self, key: str, entry: CacheEntry, size_bytes: int = 0):
        with self._lock:
            if key in self._cache:
                old_size = self._sizes.get(key, 0)
                self._total_bytes -= old_size
                self._cache.move_to_end(key)
            else:
                old_size = 0

            self._cache[key] = entry
            self._sizes[key] = size_bytes
            self._total_bytes += size_bytes

            while (len(self._cache) > self.max_size or
                   self._total_bytes > self.max_bytes):
                if not self._cache:
                    break
                oldest_key, oldest_entry = self._cache.popitem(last=False)
                removed_size = self._sizes.pop(oldest_key, 0)
                self._total_bytes -= removed_size

    def remove(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._sizes.pop(key, None)
                return True
            return False

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._sizes.clear()
            self._total_bytes = 0

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def bytes(self) -> int:
        with self._lock:
            return self._total_bytes

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def values(self) -> List[Any]:
        with self._lock:
            return [e.value for e in self._cache.values()]

    def items(self) -> List[Tuple[str, Any]]:
        with self._lock:
            return [(k, e.value) for k, e in self._cache.items()]

    def get_or_none(self, key: str) -> Tuple[bool, Any]:
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.expires_at > 0 and time.time() > entry.expires_at:
                    del self._cache[key]
                    self._sizes.pop(key, None)
                    return False, None
                self._cache.move_to_end(key)
                entry.access_count += 1
                entry.last_accessed = time.time()
                return True, entry.value
            return False, None

    def cleanup_expired(self) -> int:
        with self._lock:
            now = time.time()
            expired = [k for k, e in self._cache.items()
                       if e.expires_at > 0 and now > e.expires_at]
            for key in expired:
                del self._cache[key]
                self._sizes.pop(key, None)
            return len(expired)

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "bytes": self._total_bytes,
                "max_bytes": self.max_bytes,
            }


class DiskCache:
    def __init__(self, cache_dir: str, max_size: int = 1000):
        self.cache_dir = cache_dir
        self.max_size = max_size
        os.makedirs(cache_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _key_path(self, key: str) -> str:
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")

    def get(self, key: str) -> Optional[Any]:
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            if data.get("expires_at", 0) > 0 and time.time() > data["expires_at"]:
                os.remove(path)
                return None
            data["access_count"] = data.get("access_count", 0) + 1
            data["last_accessed"] = time.time()
            with open(path, "wb") as f:
                pickle.dump(data, f)
            return data["value"]
        except Exception:
            return None

    def put(self, key: str, value: Any, ttl: int = 0, tags: List[str] = None):
        path = self._key_path(key)
        now = time.time()
        data = {
            "key": key,
            "value": value,
            "created_at": now,
            "expires_at": now + ttl if ttl > 0 else 0,
            "access_count": 0,
            "last_accessed": now,
            "tags": tags or [],
        }
        try:
            with open(path, "wb") as f:
                pickle.dump(data, f)
        except Exception:
            pass

    def remove(self, key: str) -> bool:
        path = self._key_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def clear(self):
        with self._lock:
            for f in os.listdir(self.cache_dir):
                if f.endswith(".cache"):
                    os.remove(os.path.join(self.cache_dir, f))

    def size(self) -> int:
        with self._lock:
            return len([f for f in os.listdir(self.cache_dir) if f.endswith(".cache")])

    def cleanup_expired(self) -> int:
        with self._lock:
            count = 0
            now = time.time()
            for f in os.listdir(self.cache_dir):
                if f.endswith(".cache"):
                    path = os.path.join(self.cache_dir, f)
                    try:
                        with open(path, "rb") as fh:
                            data = pickle.load(fh)
                        if data.get("expires_at", 0) > 0 and now > data["expires_at"]:
                            os.remove(path)
                            count += 1
                    except Exception:
                        os.remove(path)
                        count += 1
            return count

    def get_stats(self) -> Dict:
        return {
            "size": self.size(),
            "max_size": self.max_size,
            "cache_dir": self.cache_dir,
        }


class CacheManager:
    def __init__(self, cache_dir: str = None, memory_max: int = 1000, disk_max: int = 5000):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".friday", "cache")
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        self.memory = LRUCache(max_size=memory_max)
        self.disk = DiskCache(os.path.join(cache_dir, "disk"), max_size=disk_max)

        self._stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0,
            "sets": 0,
            "deletes": 0,
        }
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            self._stats["hits"] += 1

        hit, value = self.memory.get_or_none(key)
        if hit:
            with self._lock:
                self._stats["memory_hits"] += 1
            return value

        value = self.disk.get(key)
        if value is not None:
            with self._lock:
                self._stats["disk_hits"] += 1
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=0,
                tier="memory",
            )
            self.memory.put(key, entry, len(str(value).encode()))
            return value

        with self._lock:
            self._stats["misses"] += 1
        return default

    def set(self, key: str, value: Any, ttl: int = 3600, tags: List[str] = None,
            memory_only: bool = False):
        now = time.time()
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + ttl if ttl > 0 else 0,
            tier="memory",
            tags=tags or [],
        )
        size_bytes = len(str(value).encode())
        self.memory.put(key, entry, size_bytes)

        if not memory_only:
            self.disk.put(key, value, ttl, tags)

        with self._lock:
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        mem_removed = self.memory.remove(key)
        disk_removed = self.disk.remove(key)
        if mem_removed or disk_removed:
            with self._lock:
                self._stats["deletes"] += 1
            return True
        return False

    def exists(self, key: str) -> bool:
        hit, _ = self.memory.get_or_none(key)
        if hit:
            return True
        return self.disk.get(key) is not None

    def clear(self, tier: str = "all"):
        if tier in ("all", "memory"):
            self.memory.clear()
        if tier in ("all", "disk"):
            self.disk.clear()

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, items: Dict[str, Any], ttl: int = 3600):
        for key, value in items.items():
            self.set(key, value, ttl)

    def cleanup(self) -> Dict[str, int]:
        mem_expired = self.memory.cleanup_expired()
        disk_expired = self.disk.cleanup_expired()
        return {"memory_expired": mem_expired, "disk_expired": disk_expired}

    def get_stats(self) -> Dict:
        with self._lock:
            stats = dict(self._stats)
        stats["memory"] = self.memory.get_stats()
        stats["disk"] = self.disk.get_stats()
        total_requests = stats["hits"] + stats["misses"]
        stats["hit_rate"] = round(stats["hits"] / total_requests * 100, 2) if total_requests > 0 else 0
        return stats

    def keys(self, pattern: str = None) -> List[str]:
        keys = self.memory.keys()
        if pattern:
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        return keys


_cache = None


def _get_cache() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache


def cache_system_tool(action: str = "get", **kwargs) -> Any:
    """Cache system tool dispatcher."""
    try:
        cache = _get_cache()

        if action == "get":
            key = kwargs.get("key", "")
            default = kwargs.get("default")
            if not key:
                return {"error": "No key provided"}
            value = cache.get(key, default)
            return {"key": key, "value": value, "hit": value is not default or default is None}

        elif action == "set":
            key = kwargs.get("key", "")
            value = kwargs.get("value")
            ttl = kwargs.get("ttl", 3600)
            tags = kwargs.get("tags", [])
            if not key or value is None:
                return {"error": "key and value required"}
            cache.set(key, value, ttl, tags)
            return {"success": True}

        elif action == "set_many":
            items = kwargs.get("items", {})
            ttl = kwargs.get("ttl", 3600)
            if not items:
                return {"error": "No items provided"}
            cache.set_many(items, ttl)
            return {"success": True, "count": len(items)}

        elif action == "delete":
            key = kwargs.get("key", "")
            if not key:
                return {"error": "No key provided"}
            ok = cache.delete(key)
            return {"success": ok}

        elif action == "exists":
            key = kwargs.get("key", "")
            return {"exists": cache.exists(key)}

        elif action == "clear":
            tier = kwargs.get("tier", "all")
            cache.clear(tier)
            return {"success": True}

        elif action == "cleanup":
            result = cache.cleanup()
            return result

        elif action == "keys":
            pattern = kwargs.get("pattern")
            return {"keys": cache.keys(pattern), "count": len(cache.keys(pattern))}

        elif action == "stats":
            return cache.get_stats()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
