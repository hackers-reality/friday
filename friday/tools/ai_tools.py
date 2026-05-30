from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

# ──────────────────────────────────────────────
# Dataclass results
# ──────────────────────────────────────────────

@dataclass
class OllamaResult:
    """Result from Ollama text generation."""
    model: str
    response: str
    tokens_per_second: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ImageResult:
    """Result from local image generation (Diffusers)."""
    prompt: str
    output_path: str
    model: str
    error: Optional[str] = None


@dataclass
class OpenRouterResult:
    """Result from OpenRouter chat completion."""
    model: str
    response: str
    usage: Optional[dict] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Lazy dependency flags
# ──────────────────────────────────────────────

HAS_OLLAMA = False
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    pass

HAS_DIFFUSERS = False
try:
    import torch
    from diffusers import DiffusionPipeline
    HAS_DIFFUSERS = True
except ImportError:
    pass

HAS_OPENROUTER = False
try:
    import httpx
    HAS_OPENROUTER = True
except ImportError:
    pass

HAS_LANGFUSE = False
try:
    from langfuse import Langfuse
    HAS_LANGFUSE = True
except ImportError:
    pass


# ──────────────────────────────────────────────
# Ollama — local LLM inference
# ──────────────────────────────────────────────

async def ollama_generate(
    model: str,
    prompt: str,
    system: str | None = None,
) -> OllamaResult:
    """Generate text using a local Ollama model.

    Free, offline, requires zero API keys. Pull the model first with
    ``ollama pull <name>`` if it does not exist locally.

    Args:
        model: Model name (e.g. ``"llama3.2"``, ``"mistral"``, ``"codellama"``).
        prompt: Input text to send to the model.
        system: Optional system-prompt override.

    Returns:
        An ``OllamaResult`` with the generated text and approximate
        throughput in tokens/second.
    """
    if not HAS_OLLAMA:
        return OllamaResult(model=model, response="", error="ollama package not installed (pip install ollama)")

    def _blocking() -> OllamaResult:
        try:
            t0 = time.perf_counter()
            kwargs = dict(model=model, prompt=prompt, stream=False)
            if system:
                kwargs["system"] = system
            resp = ollama.generate(**kwargs)
            elapsed = time.perf_counter() - t0
            response_text = resp.get("response", "")
            tokens = len(response_text.split())
            tps = round(tokens / elapsed, 2) if elapsed > 0 else None
            return OllamaResult(model=model, response=response_text, tokens_per_second=tps)
        except Exception as exc:
            return OllamaResult(model=model, response="", error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


async def ollama_list_models() -> list[str]:
    """List all available Ollama models on the local machine.

    Returns:
        A list of model tags (e.g. ``["llama3.2:latest", ...]``).
        Returns an empty list if Ollama is not installed or not reachable.
    """
    if not HAS_OLLAMA:
        logger.warning("ollama package not installed")
        return []

    def _blocking() -> list[str]:
        try:
            resp = ollama.list()
            return [m.get("name", "") for m in resp.get("models", [])]
        except Exception as exc:
            logger.error("Failed to list Ollama models: %s", exc)
            return []

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# Diffusers — local image generation (Stable Diffusion / Flux)
# ──────────────────────────────────────────────

async def generate_image(
    prompt: str,
    model: str = "stabilityai/stable-diffusion-3.5-medium",
    output_path: str | None = None,
) -> ImageResult:
    """Generate an image from a text prompt using a local Diffusers pipeline.

    The pipeline is loaded on first call and cached in memory.  The heavy
    model download / CPU-offload work is pushed to a thread so the event
    loop stays responsive.

    Args:
        prompt: Text description of the desired image.
        model: HuggingFace model ID (default: SD 3.5 Medium).
        output_path: Where to save the image.  If ``None`` a temporary
            ``.png`` file is created in the system temp directory.

    Returns:
        An ``ImageResult`` with the output file path.
    """
    if not HAS_DIFFUSERS:
        return ImageResult(
            prompt=prompt,
            output_path=output_path or "",
            model=model,
            error="diffusers + torch not installed (pip install diffusers torch)",
        )

    import tempfile

    out = output_path or os.path.join(tempfile.gettempdir(), f"friday_img_{int(time.time())}.png")

    def _blocking() -> ImageResult:
        try:
            pipe = DiffusionPipeline.from_pretrained(
                model,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            if torch.cuda.is_available():
                pipe.to("cuda")
            else:
                pipe.enable_model_cpu_offload()
            image = pipe(prompt=prompt, num_inference_steps=28).images[0]
            image.save(out)
            return ImageResult(prompt=prompt, output_path=out, model=model)
        except Exception as exc:
            return ImageResult(prompt=prompt, output_path=out, model=model, error=str(exc))

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)


# ──────────────────────────────────────────────
# OpenRouter — unified API for 300+ LLMs
# ──────────────────────────────────────────────

async def openrouter_chat(
    model: str,
    messages: list,
    max_tokens: int = 1024,
) -> OpenRouterResult:
    """Chat via OpenRouter using a single API key for 300+ models.

    Requires the ``OPENROUTER_API_KEY`` environment variable.  A free
    tier with limited credits is available at https://openrouter.ai.

    Args:
        model: Model identifier (e.g. ``"openai/gpt-4o"``,
            ``"anthropic/claude-3.5-sonnet"``, ``"google/gemini-pro"``).
        messages: List of message dicts following the OpenAI format
            (``[{"role": "user", "content": "..."}]``).
        max_tokens: Maximum tokens in the response.

    Returns:
        An ``OpenRouterResult`` with the assistant reply and token usage.
    """
    if not HAS_OPENROUTER:
        return OpenRouterResult(
            model=model, response="",
            error="httpx package not installed (pip install httpx)",
        )

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return OpenRouterResult(
            model=model, response="",
            error="OPENROUTER_API_KEY environment variable not set",
        )

    async def _request() -> OpenRouterResult:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": model, "messages": messages, "max_tokens": max_tokens},
                )
                resp.raise_for_status()
                data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage")
            return OpenRouterResult(model=model, response=content, usage=usage)
        except Exception as exc:
            return OpenRouterResult(model=model, response="", error=str(exc))

    return await _request()


# ──────────────────────────────────────────────
# Langfuse — LLM observability
# ──────────────────────────────────────────────

async def langfuse_trace(name: str, metadata: dict | None = None) -> str:
    """Create a trace in Langfuse for LLM observability.

    Requires ``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY``
    environment variables.  Free tier includes 50 000 observations per
    month.

    Args:
        name: Trace name (e.g. ``"chat-with-docs"``).
        metadata: Optional key-value pairs attached to the trace.

    Returns:
        The trace ID (UUID string) on success, or an error message
        prefixed with ``"error: "`` on failure.
    """
    if not HAS_LANGFUSE:
        return "error: langfuse package not installed (pip install langfuse)"

    def _blocking() -> str:
        try:
            lf = Langfuse()
            trace = lf.trace(name=name, metadata=metadata or {})
            return trace.id
        except Exception as exc:
            return f"error: {exc}"

    return await asyncio.get_event_loop().run_in_executor(None, _blocking)
