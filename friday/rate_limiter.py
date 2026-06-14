"""FRIDAY Rate Limiter — token bucket, sliding window, and adaptive rate limiting."""
import time
import threading
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque


@dataclass
class RateLimitRule:
    name: str
    max_requests: int
    window_seconds: int
    burst_max: int = 0
    key_prefix: str = ""
    block_duration: int = 0
    adaptive: bool = False
    priority: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_at: float
    retry_after: int = 0
    rule: str = ""
    key: str = ""

    def to_dict(self):
        return asdict(self)


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                wait_time = (tokens - self.tokens) / self.refill_rate
                return False, wait_time

    def get_status(self) -> Dict:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            return {
                "capacity": self.capacity,
                "available": int(tokens),
                "refill_rate": self.refill_rate,
            }


class SlidingWindowCounter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: deque = deque()
        self._lock = threading.Lock()

    def allow(self) -> Tuple[bool, int, float]:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            count = len(self._requests)
            if count < self.max_requests:
                self._requests.append(now)
                return True, self.max_requests - count - 1, 0.0
            else:
                oldest = self._requests[0]
                retry_after = oldest + self.window_seconds - now
                return False, 0, max(0, retry_after)

    def get_status(self) -> Dict:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            return {
                "max_requests": self.max_requests,
                "current": len(self._requests),
                "remaining": max(0, self.max_requests - len(self._requests)),
                "window_seconds": self.window_seconds,
            }


class AdaptiveRateLimiter:
    def __init__(self, base_limit: int, window_seconds: int):
        self.base_limit = base_limit
        self.window_seconds = window_seconds
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._current_limits: Dict[str, int] = {}
        self._lock = threading.Lock()

    def record_error(self, key: str):
        with self._lock:
            self._error_counts[key] += 1
            errors = self._error_counts[key]
            if errors > 5:
                reduction = min(errors // 5, 10)
                self._current_limits[key] = max(1, self.base_limit - reduction)

    def record_success(self, key: str):
        with self._lock:
            self._success_counts[key] += 1
            self._error_counts[key] = max(0, self._error_counts.get(key, 0) - 1)
            if self._error_counts[key] == 0 and key in self._current_limits:
                current = self._current_limits[key]
                if current < self.base_limit:
                    self._current_limits[key] = min(self.base_limit, current + 1)

    def get_limit(self, key: str) -> int:
        with self._lock:
            return self._current_limits.get(key, self.base_limit)


class RateLimiter:
    def __init__(self):
        self._rules: Dict[str, RateLimitRule] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, SlidingWindowCounter] = {}
        self._adaptive: Dict[str, AdaptiveRateLimiter] = {}
        self._blocked: Dict[str, float] = {}
        self._request_log: deque = deque(maxlen=10000)
        self._stats: Dict[str, Dict] = defaultdict(lambda: {"allowed": 0, "denied": 0})
        self._lock = threading.Lock()
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            RateLimitRule("api_global", 1000, 60, 100, "api"),
            RateLimitRule("api_per_ip", 100, 60, 20, "ip"),
            RateLimitRule("chat", 30, 60, 10, "chat"),
            RateLimitRule("tool_call", 50, 60, 15, "tool"),
            RateLimitRule("auth", 5, 300, 2, "auth", block_duration=900),
            RateLimitRule("upload", 10, 60, 5, "upload"),
        ]
        for rule in defaults:
            self._rules[rule.name] = rule

    def _get_key(self, rule_name: str, client_id: str) -> str:
        rule = self._rules.get(rule_name)
        prefix = rule.key_prefix if rule else rule_name
        return f"{prefix}:{client_id}"

    def _ensure_bucket(self, key: str, rule: RateLimitRule) -> TokenBucket:
        if key not in self._buckets:
            refill_rate = rule.max_requests / rule.window_seconds
            self._buckets[key] = TokenBucket(rule.burst_max or rule.max_requests, refill_rate)
        return self._buckets[key]

    def _ensure_window(self, key: str, rule: RateLimitRule) -> SlidingWindowCounter:
        if key not in self._windows:
            self._windows[key] = SlidingWindowCounter(rule.max_requests, rule.window_seconds)
        return self._windows[key]

    def _ensure_adaptive(self, key: str, rule: RateLimitRule) -> AdaptiveRateLimiter:
        if key not in self._adaptive and rule.adaptive:
            self._adaptive[key] = AdaptiveRateLimiter(rule.max_requests, rule.window_seconds)
        return self._adaptive.get(key)

    def _check_blocked(self, key: str) -> bool:
        if key in self._blocked:
            if time.time() < self._blocked[key]:
                return True
            else:
                del self._blocked[key]
        return False

    def check(self, rule_name: str, client_id: str = "default", tokens: int = 1) -> RateLimitResult:
        with self._lock:
            rule = self._rules.get(rule_name)
            if not rule:
                return RateLimitResult(True, 999, 999, 0, rule=rule_name, key=client_id)

            key = self._get_key(rule_name, client_id)

            if self._check_blocked(key):
                self._stats[rule_name]["denied"] += 1
                return RateLimitResult(
                    False, 0, rule.max_requests,
                    time.time() + rule.block_duration,
                    retry_after=rule.block_duration,
                    rule=rule_name, key=key,
                )

            window = self._ensure_window(key, rule)
            allowed, remaining, retry_after = window.allow()

            if not allowed and rule.block_duration > 0:
                self._blocked[key] = time.time() + rule.block_duration

            if allowed:
                self._stats[rule_name]["allowed"] += 1
            else:
                self._stats[rule_name]["denied"] += 1

            reset_at = time.time() + rule.window_seconds

            self._request_log.append({
                "timestamp": time.time(),
                "rule": rule_name,
                "key": key,
                "allowed": allowed,
            })

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=rule.max_requests,
                reset_at=reset_at,
                retry_after=int(retry_after),
                rule=rule_name,
                key=key,
            )

    def add_rule(self, rule: RateLimitRule):
        with self._lock:
            self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        with self._lock:
            if name in self._rules:
                del self._rules[name]
                return True
            return False

    def get_rules(self) -> List[Dict]:
        with self._lock:
            return [r.to_dict() for r in self._rules.values()]

    def get_status(self, rule_name: str = None, client_id: str = "default") -> Any:
        with self._lock:
            if rule_name:
                rule = self._rules.get(rule_name)
                if not rule:
                    return {"error": f"Rule not found: {rule_name}"}
                key = self._get_key(rule_name, client_id)
                window = self._windows.get(key)
                bucket = self._buckets.get(key)
                return {
                    "rule": rule.to_dict(),
                    "window": window.get_status() if window else None,
                    "bucket": bucket.get_status() if bucket else None,
                    "is_blocked": self._check_blocked(key),
                }
            else:
                statuses = {}
                for name, rule in self._rules.items():
                    key = self._get_key(name, client_id)
                    window = self._windows.get(key)
                    statuses[name] = {
                        "rule": rule.to_dict(),
                        "window": window.get_status() if window else None,
                        "is_blocked": self._check_blocked(key),
                    }
                return statuses

    def get_stats(self) -> Dict:
        with self._lock:
            stats = {}
            for rule_name, counts in self._stats.items():
                total = counts["allowed"] + counts["denied"]
                stats[rule_name] = {
                    "total": total,
                    "allowed": counts["allowed"],
                    "denied": counts["denied"],
                    "allow_rate": round(counts["allowed"] / total * 100, 2) if total > 0 else 100,
                }
            return {
                "rules": len(self._rules),
                "active_buckets": len(self._buckets),
                "active_windows": len(self._windows),
                "blocked_keys": len(self._blocked),
                "total_requests": sum(s["total"] for s in stats.values()),
                "by_rule": stats,
            }

    def reset(self, rule_name: str = None, client_id: str = "default"):
        with self._lock:
            if rule_name:
                key = self._get_key(rule_name, client_id)
                if key in self._windows:
                    self._windows[key] = SlidingWindowCounter(
                        self._rules[rule_name].max_requests,
                        self._rules[rule_name].window_seconds,
                    )
                self._blocked.pop(key, None)
            else:
                self._windows.clear()
                self._buckets.clear()
                self._blocked.clear()

    def cleanup(self, max_age: int = 3600):
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._blocked.items() if v < now]
            for k in expired:
                del self._blocked[k]


_limiter = RateLimiter()


def rate_limiter_tool(action: str = "check", **kwargs) -> Any:
    """Rate limiter tool dispatcher."""
    try:
        if action == "check":
            rule = kwargs.get("rule", "api_global")
            client_id = kwargs.get("client_id", "default")
            tokens = kwargs.get("tokens", 1)
            result = _limiter.check(rule, client_id, tokens)
            return result.to_dict()

        elif action == "add_rule":
            rule_data = kwargs.get("rule", {})
            rule = RateLimitRule(**rule_data)
            _limiter.add_rule(rule)
            return {"success": True}

        elif action == "remove_rule":
            name = kwargs.get("name", "")
            ok = _limiter.remove_rule(name)
            return {"success": ok}

        elif action == "rules":
            return {"rules": _limiter.get_rules()}

        elif action == "status":
            rule_name = kwargs.get("rule")
            client_id = kwargs.get("client_id", "default")
            return _limiter.get_status(rule_name, client_id)

        elif action == "stats":
            return _limiter.get_stats()

        elif action == "reset":
            rule_name = kwargs.get("rule")
            client_id = kwargs.get("client_id", "default")
            _limiter.reset(rule_name, client_id)
            return {"success": True}

        elif action == "cleanup":
            max_age = kwargs.get("max_age", 3600)
            _limiter.cleanup(max_age)
            return {"success": True}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
