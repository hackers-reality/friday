"""Async OpenAI-compatible client for NVIDIA NIM agent calls.

Uses the free NVIDIA NIM API endpoint, in-memory token bucket rate
limiting, multi-key load balancing, and Gemini fallback after repeated
NIM failures.
"""
from __future__ import annotations

import asyncio
import itertools
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence

try:
    import httpx
except ImportError:  # pragma: no cover - dependency is optional at import time
    httpx = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback when python-dotenv is absent
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False

from friday.logging_utils import configure_logging


logger = configure_logging(__name__)


class NIMError(RuntimeError):
    """Base error raised by the NIM client."""


class NIMRateLimitError(NIMError):
    """Raised when the NIM endpoint returns rate-limit pressure."""


class NIMModelUnavailableError(NIMError):
    """Raised when a model returns 404/503 and should be skipped."""


class NIMAuthError(NIMError):
    """Raised when no usable NVIDIA API key is available."""


class _TokenBucket:
    """Simple in-memory token bucket used per model endpoint."""

    def __init__(self, rate_limit_rpm: int) -> None:
        self.capacity = float(rate_limit_rpm)
        self.tokens = float(rate_limit_rpm)
        self.refill_rate = float(rate_limit_rpm) / 60.0
        self.updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.updated_at
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                self.updated_at = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait_for = max((1.0 - self.tokens) / self.refill_rate, 0.05)
            await asyncio.sleep(wait_for)


def _collect_api_keys() -> List[str]:
    """Collect NVIDIA API keys from the environment in load-balanced order."""
    load_dotenv()

    keys: List[str] = []
    ordered_names = ["NVIDIA_API_KEY", "NIM_API_KEY", "NIM_KEY"]
    for name in ordered_names:
        value = os.getenv(name)
        if value:
            keys.append(value.strip())

    numbered = []
    for key_name, value in os.environ.items():
        if re.fullmatch(r"NIM_KEY_\d+", key_name) and value.strip():
            numbered.append((int(key_name.rsplit("_", 1)[1]), value.strip()))
    for _, value in sorted(numbered, key=lambda item: item[0]):
        keys.append(value)

    unique = []
    seen = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


def _normalize_messages(messages: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure messages are plain OpenAI chat dictionaries."""
    normalized: List[Dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        normalized.append({"role": role, "content": content})
    return normalized


@dataclass(slots=True)
class NIMCompletion:
    """Structured response returned by the client."""

    model: str
    content: str
    tokens_used: int
    raw: Dict[str, Any]


class NIMClient:
    """Async NVIDIA NIM client with retry, key rotation, and fallback hooks."""

    def __init__(
        self,
        api_base: str = "https://integrate.api.nvidia.com/v1",
        rate_limit_rpm: int = 40,
        api_keys: Optional[Iterable[str]] = None,
        timeout: float = 60.0,
    ) -> None:
        if httpx is None:
            raise NIMError("httpx is required for the NVIDIA NIM client")
        self.api_base = api_base.rstrip("/")
        self.rate_limit_rpm = int(rate_limit_rpm)
        self._api_keys = [key for key in (api_keys or _collect_api_keys()) if key]
        if not self._api_keys:
            raise NIMAuthError("No NVIDIA API keys found in NVIDIA_API_KEY or NIM_KEY_* environment variables")

        for key in self._api_keys:
            if not key.startswith("nvapi-"):
                logger.warning("NIM key does not have the expected nvapi- prefix")

        self._timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.api_base, timeout=self._timeout)
        self._key_cycle = itertools.cycle(self._api_keys)
        self._key_lock = asyncio.Lock()
        self._buckets: Dict[str, _TokenBucket] = {}

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "NIMClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def _next_key(self) -> str:
        async with self._key_lock:
            return next(self._key_cycle)

    def _bucket_for(self, model_id: str) -> _TokenBucket:
        bucket = self._buckets.get(model_id)
        if bucket is None:
            bucket = _TokenBucket(self.rate_limit_rpm)
            self._buckets[model_id] = bucket
        return bucket

    async def list_models(self) -> List[Dict[str, Any]]:
        """Return the current model catalog from NVIDIA NIM."""
        headers = {"Authorization": f"Bearer {self._api_keys[0]}"}
        response = await self._client.get("/models", headers=headers)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, list):
            return data
        return []

    async def _post_chat_completion(
        self,
        model_id: str,
        messages: Sequence[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        bucket = self._bucket_for(model_id)
        await bucket.acquire()

        api_key = await self._next_key()
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": _normalize_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if extra_payload:
            payload.update(extra_payload)

        response = await self._client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )

        if response.status_code in (404, 503):
            raise NIMModelUnavailableError(f"Model unavailable: {model_id} ({response.status_code})")
        if response.status_code == 429:
            raise NIMRateLimitError(f"Rate limited by NVIDIA NIM for model {model_id}")
        if response.status_code in (401, 403):
            raise NIMAuthError(f"Authentication failed for one of the NIM keys ({response.status_code})")

        response.raise_for_status()
        return response.json()

    async def complete_chat(
        self,
        *,
        model_id: str,
        messages: Sequence[Dict[str, Any]],
        fallback_models: Optional[Sequence[str]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        task_type: str = "general",
        fallback_handler: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> NIMCompletion:
        """Run a chat completion with retry, model fallback, and Gemini fallback."""
        attempts: List[str] = []
        candidates = [model_id]
        if fallback_models:
            for candidate in fallback_models:
                if candidate not in candidates:
                    candidates.append(candidate)

        last_error: Optional[Exception] = None
        for candidate in candidates:
            attempts.append(candidate)
            for retry_index, delay_seconds in enumerate((1.0, 2.0, 4.0), start=1):
                try:
                    raw = await self._post_chat_completion(
                        candidate,
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    choice = (raw.get("choices") or [{}])[0]
                    message = choice.get("message") or {}
                    content = message.get("content") or ""
                    usage = raw.get("usage") or {}
                    tokens_used = int(usage.get("total_tokens") or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0) or 0)
                    return NIMCompletion(model=candidate, content=content, tokens_used=tokens_used, raw=raw)
                except NIMModelUnavailableError as exc:
                    last_error = exc
                    logger.info("Skipping unavailable NIM model %s for %s", candidate, task_type)
                    break
                except NIMRateLimitError as exc:
                    last_error = exc
                    logger.warning("NIM rate limit hit for %s (attempt %s/3)", candidate, retry_index)
                    if retry_index < 3:
                        await asyncio.sleep(delay_seconds)
                        continue
                    break
                except (httpx.ReadTimeout, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                    last_error = exc
                    logger.warning("Transient NIM transport error for %s (attempt %s/3): %s", candidate, retry_index, exc)
                    if retry_index < 3:
                        await asyncio.sleep(delay_seconds)
                        continue
                    break
                except Exception as exc:  # pragma: no cover - defensive fallback
                    last_error = exc
                    logger.exception("Unexpected NIM error for %s", candidate)
                    break

        if fallback_handler is not None:
            logger.info("Falling back to Gemini after NIM failures on %s", attempts)
            fallback_result = await fallback_handler(messages=messages, task_type=task_type, max_tokens=max_tokens)
            if isinstance(fallback_result, NIMCompletion):
                return fallback_result
            if isinstance(fallback_result, dict):
                return NIMCompletion(
                    model=str(fallback_result.get("model", "gemini-fallback")),
                    content=str(fallback_result.get("content", "")),
                    tokens_used=int(fallback_result.get("tokens_used", 0) or 0),
                    raw=fallback_result,
                )
            return NIMCompletion(model="gemini-fallback", content=str(fallback_result), tokens_used=0, raw={"content": str(fallback_result)})

        raise last_error or NIMError("All NIM candidates failed")
