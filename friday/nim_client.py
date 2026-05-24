"""
FRIDAY Inference Client — async OpenAI-compatible client with rate limiting,
key load balancing, exponential backoff, and layered fallback chain.

Fallback chain:
  1. NVIDIA NIM (https://integrate.api.nvidia.com/v1)
  2. OpenCode Zen API (https://api.opencode.ai/v1)
  3. Google Gemini (google-genai SDK)
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

NIM_API_BASE = os.getenv("NIM_API_BASE", "https://integrate.api.nvidia.com/v1")
ZEN_API_BASE = os.getenv("ZEN_API_BASE", "https://api.opencode.ai/v1")


def _collect_nim_keys() -> list[str]:
    """Collect all NVIDIA API keys from .env: NVIDIA_API_KEY, NIM_KEY_1..N."""
    keys: list[str] = []
    primary = os.getenv("NVIDIA_API_KEY", "")
    if primary:
        keys.append(primary)
    i = 1
    while True:
        k = os.getenv(f"NIM_KEY_{i}", "")
        if not k:
            break
        keys.append(k)
        i += 1
    return keys


@dataclass
class NIMResult:
    model: str
    content: str
    usage: dict
    duration_ms: int
    cached: bool = False


class TokenBucket:
    """Simple in-memory token bucket rate limiter (per model endpoint)."""

    def __init__(self, rate: int, per_seconds: int = 60):
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = float(rate)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per_seconds))
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0.0
            wait = (1 - self.tokens) * (self.per_seconds / self.rate)
            self.tokens = 0.0
            return wait


class InferenceClient:
    """
    Async inference client with 3-tier fallback chain:

    1. NVIDIA NIM  — multi-key, rate-limited, OpenAI-compatible
    2. OpenCode Zen — single-key, OpenAI-compatible (opencode/big-pickle, etc.)
    3. Google Gemini — google-genai SDK (gemini-2.0-flash)
    """

    def __init__(self, nim_api_base: str = NIM_API_BASE, zen_api_base: str = ZEN_API_BASE):
        self.nim_api_base = nim_api_base.rstrip("/")
        self.zen_api_base = zen_api_base.rstrip("/")
        self._keys = _collect_nim_keys()
        self._key_index = 0
        self._key_lock = asyncio.Lock()
        self._buckets: dict[str, TokenBucket] = {}
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        self._zen_key = os.getenv("ZEN_API_KEY", "")

    def _bucket(self, model: str) -> TokenBucket:
        if model not in self._buckets:
            self._buckets[model] = TokenBucket(rate=40, per_seconds=60)
        return self._buckets[model]

    async def _next_key(self) -> str:
        async with self._key_lock:
            key = self._keys[self._key_index % max(len(self._keys), 1)]
            self._key_index += 1
            return key

    async def chat(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> NIMResult:
        """
        Send a chat completion request. Fallback chain:

          1. NVIDIA NIM  (rate-limited, multi-key)
          2. OpenCode Zen (single-key, big-pickle etc.)
          3. Google Gemini (google-genai SDK)
        """
        # ── Tier 1: NVIDIA NIM ──
        if self._keys:
            result = await self._nim_chat(model, messages, max_tokens, temperature)
            if result and not result.content.startswith("[NIM"):
                return result
            reason = result.content[:200] if result else "No NIM keys"
        else:
            reason = "No NIM keys configured"

        # ── Tier 2: OpenCode Zen ──
        if self._zen_key:
            result = await self._zen_chat(model, messages, max_tokens, temperature)
            if result and not result.content.startswith("[ZEN"):
                return result
            reason += f"; Zen: {result.content[:100] if result else 'no key'}"

        # ── Tier 3: Google Gemini ──
        return await self._gemini_fallback(model, messages, reason)

    async def _nim_chat(self, model: str, messages: list[dict],
                        max_tokens: int, temperature: float) -> Optional[NIMResult]:
        """Tier 1: NVIDIA NIM with retries and rate limiting."""
        key = await self._next_key()
        bucket = self._bucket(model)
        wait = await bucket.acquire()
        if wait > 0:
            await asyncio.sleep(wait)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        for attempt in range(4):
            t0 = time.monotonic()
            try:
                resp = await self._client.post(
                    f"{self.nim_api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                )
                duration = int((time.monotonic() - t0) * 1000)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code == 404:
                    return NIMResult(model=model,
                                     content=f"[NIM 404] Model '{model}' not available.",
                                     usage={}, duration_ms=duration)
                resp.raise_for_status()
                data = resp.json()
                choice = data["choices"][0]
                return NIMResult(model=model, content=choice.get("message", {}).get("content", ""),
                                 usage=data.get("usage", {}), duration_ms=duration)
            except httpx.TimeoutException:
                if attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return NIMResult(model=model, content="[NIM timeout after 3 retries]",
                                 usage={}, duration_ms=0)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (502, 503) and attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return NIMResult(model=model,
                                 content=f"[NIM {e.response.status_code}] {e.response.text[:300]}",
                                 usage={}, duration_ms=int((time.monotonic() - t0) * 1000))
            except Exception as e:
                return NIMResult(model=model, content=f"[NIM error] {e}",
                                 usage={}, duration_ms=0)
        return NIMResult(model=model, content="[NIM rate limited after 3 retries]",
                         usage={}, duration_ms=0)

    async def _zen_chat(self, model: str, messages: list[dict],
                        max_tokens: int, temperature: float) -> Optional[NIMResult]:
        """Tier 2: OpenCode Zen API (OpenAI-compatible)."""
        t0 = time.monotonic()
        try:
            zen_model = "opencode/big-pickle"
            resp = await self._client.post(
                f"{self.zen_api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self._zen_key}", "Content-Type": "application/json"},
                json={"model": zen_model, "messages": messages,
                      "max_tokens": max_tokens, "temperature": temperature},
            )
            duration = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 401:
                return NIMResult(model=zen_model, content="[ZEN 401] Invalid ZEN_API_KEY",
                                 usage={}, duration_ms=duration)
            if resp.status_code == 404:
                return NIMResult(model=zen_model,
                                 content=f"[ZEN 404] Model '{zen_model}' not available.",
                                 usage={}, duration_ms=duration)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return NIMResult(model=zen_model, content=choice.get("message", {}).get("content", ""),
                             usage=data.get("usage", {}), duration_ms=duration)
        except httpx.TimeoutException:
            return NIMResult(model="opencode/big-pickle", content="[ZEN timeout]",
                             usage={}, duration_ms=int((time.monotonic() - t0) * 1000))
        except Exception as e:
            return NIMResult(model="opencode/big-pickle", content=f"[ZEN error] {e}",
                             usage={}, duration_ms=int((time.monotonic() - t0) * 1000))

    async def _gemini_fallback(self, model: str, messages: list[dict], reason: str) -> NIMResult:
        """Tier 3: Google Gemini via google-genai SDK (synchronous, blocking)."""
        try:
            from google import genai
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
            prompt = f"{sys_msg}\n\n{user_msg}" if sys_msg else user_msg
            t0 = time.monotonic()
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            duration = int((time.monotonic() - t0) * 1000)
            return NIMResult(
                model="gemini-2.0-flash",
                content=resp.text,
                usage={"prompt_tokens": 0, "completion_tokens": 0},
                duration_ms=duration,
            )
        except Exception as e:
            return NIMResult(
                model="fallback_error",
                content=f"[ALL TIERS FAILED] Prior: {reason}. Gemini: {e}",
                usage={},
                duration_ms=0,
            )

    async def health_check(self, model: str) -> bool:
        """Quick check if a model is reachable via NIM."""
        try:
            resp = await self._client.get(f"{self.nim_api_base}/models/{model}", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()


_INFERENCE_CLIENT: Optional[InferenceClient] = None


def get_inference_client() -> InferenceClient:
    global _INFERENCE_CLIENT
    if _INFERENCE_CLIENT is None:
        _INFERENCE_CLIENT = InferenceClient()
    return _INFERENCE_CLIENT
