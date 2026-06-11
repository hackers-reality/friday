"""
NVIDIA NIM Tools — free-tier image generation & chat via NVIDIA's API.
Endpoints:
  - Image gen: https://ai.api.nvidia.com/v1/genai/{provider}/{model}
  - Chat:      https://integrate.api.nvidia.com/v1/chat/completions
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Optional

import requests

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("nvidia_tools")

NVIDIA_STORAGE = os.path.join(FRIDAY_MEMORY, "nvidia")

IMAGE_API_BASE = "https://ai.api.nvidia.com/v1/genai"
CHAT_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# ── Model maps ──

IMAGE_MODEL_MAP = {
    "sdxl": "stabilityai/sdxl",
    "playground-v2.5": "playgroundai/playground-v2.5",
    "stable-diffusion-3.5-medium": "stabilityai/stable-diffusion-3.5-medium",
    "flux.1-schnell": "black-forest-labs/flux-schnell",
    "flux.1-dev": "black-forest-labs/flux-dev",
    "kandinsky-3": "kandinsky-community/kandinsky-3",
}

CHAT_MODEL_MAP = {
    "meta/llama-3.3-70b-instruct": "meta/llama-3.3-70b-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1": "mistralai/mixtral-8x22b-instruct-v0.1",
    "nvidia/nemotron-4-340b-instruct": "nvidia/nemotron-4-340b-instruct",
    "deepseek-ai/deepseek-r1": "deepseek-ai/deepseek-r1",
    "qwen/qwen2.5-72b-instruct": "qwen/qwen2.5-72b-instruct",
}

# ── Helpers ──


def _ensure_storage():
    os.makedirs(NVIDIA_STORAGE, exist_ok=True)


# ── Tool functions ──


def nvidia_list_models() -> dict:
    """Return available NVIDIA NIM free models grouped by category."""
    return {
        "image": {
            name: {
                "id": name,
                "provider_path": path,
                "endpoint": f"{IMAGE_API_BASE}/{path}",
            }
            for name, path in IMAGE_MODEL_MAP.items()
        },
        "chat": {
            name: {
                "id": name,
                "endpoint": CHAT_API_URL,
            }
            for name in CHAT_MODEL_MAP
        },
    }


def nvidia_image_gen(
    prompt: str,
    model: str = "flux.1-schnell",
    output_path: Optional[str] = None,
) -> dict:
    """Generate an image using NVIDIA NIM's free image-gen API.

    Args:
        prompt: Text description of the desired image.
        model: One of the image models listed in ``nvidia_list_models()``.
        output_path: Filename (relative to the nvidia storage dir) or
            absolute path.  Auto-named if omitted.

    Returns:
        Dict with keys ``success``, ``file_path``, ``prompt``, ``model``,
        ``width``, ``height``, ``seed``, ``error``.
    """
    _ensure_storage()

    api_key = os.environ.get("NVIDIA_API_KEY")

    if model not in IMAGE_MODEL_MAP:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": f"Unknown model '{model}'. Available: {list(IMAGE_MODEL_MAP)}",
        }

    if not api_key:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": (
                "NVIDIA_API_KEY environment variable is not set.\n\n"
                "To get a free API key:\n"
                "  1. Go to https://build.nvidia.com/explore/ (sign up for free)\n"
                "  2. Pick any model, hit 'Get API Key' and generate a key\n"
                "  3. Set it: set NVIDIA_API_KEY=your_key_here (or export on Linux/Mac)\n"
            ),
        }

    provider_path = IMAGE_MODEL_MAP[model]
    url = f"{IMAGE_API_BASE}/{provider_path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": "Request timed out after 120 seconds",
        }
    except requests.exceptions.RequestException as exc:
        detail = ""
        try:
            detail = exc.response.text[:500] if exc.response is not None else ""
        except Exception:
            pass
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": f"API request failed: {exc}{' - ' + detail if detail else ''}",
        }

    # Parse response — NVIDIA returns artifacts[].base64 with the image
    artifacts = data.get("artifacts", [])
    if not artifacts:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": "No image artifacts in response",
        }

    b64_data = artifacts[0].get("base64", "")
    if not b64_data:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": "Empty base64 data in response",
        }

    # Determine output path
    if output_path is None:
        filename = f"nvidia_{model}_{int(time.time())}.png"
        output_path = os.path.join(NVIDIA_STORAGE, filename)
    elif not os.path.isabs(output_path):
        output_path = os.path.join(NVIDIA_STORAGE, output_path)

    # Decode and write
    try:
        image_bytes = base64.b64decode(b64_data)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
    except Exception as exc:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "model": model,
            "width": None,
            "height": None,
            "seed": None,
            "error": f"Failed to decode/save image: {exc}",
        }

    # Optional metadata from response
    width = data.get("width") or artifacts[0].get("width")
    height = data.get("height") or artifacts[0].get("height")
    seed = data.get("seed") or artifacts[0].get("seed")

    return {
        "success": True,
        "file_path": os.path.normpath(output_path),
        "prompt": prompt,
        "model": model,
        "width": width,
        "height": height,
        "seed": seed,
        "error": None,
    }


def nvidia_chat(
    prompt: str,
    model: str = "meta/llama-3.3-70b-instruct",
    system_prompt: str = "",
    max_tokens: int = 1024,
) -> dict:
    """Chat with an LLM via NVIDIA NIM's free inference endpoint.

    Args:
        prompt: User message text.
        model: Model identifier (e.g. ``"meta/llama-3.3-70b-instruct"``).
        system_prompt: Optional system-level instruction.
        max_tokens: Maximum tokens in the response.

    Returns:
        Dict with keys ``success``, ``response``, ``model``, ``usage``,
        ``error``.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {
            "success": False,
            "response": "",
            "model": model,
            "usage": None,
            "error": (
                "NVIDIA_API_KEY environment variable is not set.\n\n"
                "Get a free key at https://build.nvidia.com/ and set the env var."
            ),
        }

    if model not in CHAT_MODEL_MAP:
        available = list(CHAT_MODEL_MAP)
        return {
            "success": False,
            "response": "",
            "model": model,
            "usage": None,
            "error": f"Unknown model '{model}'. Available: {available}",
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "top_p": 0.95,
    }

    try:
        resp = requests.post(CHAT_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": "",
            "model": model,
            "usage": None,
            "error": "Request timed out after 60 seconds",
        }
    except requests.exceptions.RequestException as exc:
        detail = ""
        try:
            detail = exc.response.text[:500] if exc.response is not None else ""
        except Exception:
            pass
        return {
            "success": False,
            "response": "",
            "model": model,
            "usage": None,
            "error": f"API request failed: {exc}{' - ' + detail if detail else ''}",
        }

    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage")
    except (KeyError, IndexError) as exc:
        return {
            "success": False,
            "response": "",
            "model": model,
            "usage": None,
            "error": f"Unexpected response format: {exc}",
        }

    return {
        "success": True,
        "response": content,
        "model": model,
        "usage": usage,
        "error": None,
    }


def nvidia_status() -> dict:
    """Check if the NVIDIA NIM API is accessible and configured.

    Returns:
        Dict with keys ``api_key_set``, ``api_reachable``,
        ``image_models``, ``chat_models``, ``error``.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    result = {
        "api_key_set": bool(api_key),
        "api_reachable": False,
        "image_models": list(IMAGE_MODEL_MAP),
        "chat_models": list(CHAT_MODEL_MAP),
        "error": None,
    }

    if not api_key:
        result["error"] = "NVIDIA_API_KEY is not set"
        return result

    try:
        resp = requests.get(
            f"{IMAGE_API_BASE}/black-forest-labs/flux-schnell",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        result["api_reachable"] = resp.status_code in (200, 400, 401, 404)
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Cannot reach API: {exc}"

    return result
