"""
Higgsfield AI Video Generation Tools.

Endpoints:
  - Video generation (text-to-video): https://videogenapi.com/api/v1/generate
  - Status polling:                 https://videogenapi.com/api/v1/status/{id}
  - Image-to-video:                 https://videogenapi.com/api/v1/image-to-video
  - Alternative:                    https://cloud.higgsfield.ai/api/v1/
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Optional

import requests

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging("higgsfield_tools")
HIGGSFIELD_DIR = os.path.join(FRIDAY_MEMORY, "higgsfield")

# ── API endpoints ──

API_BASE = "https://videogenapi.com/api/v1"
ALT_API_BASE = "https://cloud.higgsfield.ai/api/v1"

# ── Motion presets ──

MOTION_PRESETS = {
    "orbit": {
        "name": "Orbit",
        "description": "Camera orbits around the subject in a circular motion",
        "preview_url": "",
    },
    "zoom_in": {
        "name": "Zoom In",
        "description": "Camera slowly zooms into the center of the image",
        "preview_url": "",
    },
    "zoom_out": {
        "name": "Zoom Out",
        "description": "Camera slowly zooms out from the center of the image",
        "preview_url": "",
    },
    "pan_left": {
        "name": "Pan Left",
        "description": "Camera pans horizontally from right to left",
        "preview_url": "",
    },
    "pan_right": {
        "name": "Pan Right",
        "description": "Camera pans horizontally from left to right",
        "preview_url": "",
    },
    "pan_up": {
        "name": "Pan Up",
        "description": "Camera pans vertically from bottom to top",
        "preview_url": "",
    },
    "pan_down": {
        "name": "Pan Down",
        "description": "Camera pans vertically from top to bottom",
        "preview_url": "",
    },
    "subtle": {
        "name": "Subtle",
        "description": "Gentle micro-movement for a living-photo effect",
        "preview_url": "",
    },
}

# ── Helpers ──


def _ensure_storage():
    os.makedirs(HIGGSFIELD_DIR, exist_ok=True)


def _resolve_api_key(api_key: str = "") -> str:
    key = api_key or os.environ.get("HIGGSFIELD_API_KEY", "")
    return key


def _format_missing_key_instructions() -> str:
    return (
        "Higgsfield API key is not set.\n\n"
        "To get an API key:\n"
        "  1. Sign up at https://www.higgsfield.ai/ (free credits available)\n"
        "  2. Go to your dashboard and generate an API key\n"
        "  3. Set it: set HIGGSFIELD_API_KEY=your_key_here (or export on Linux/Mac)\n"
        "Alternatively, pass the api_key parameter directly."
    )


# ── Tool functions ──


def higgsfield_generate_video(
    prompt: str,
    duration: int = 10,
    resolution: str = "480p",
    model: str = "higgsfield_v1",
    api_key: str = "",
) -> dict:
    """Generate an AI video from a text prompt using the Higgsfield API.

    Args:
        prompt: Text description of the desired video.
        duration: Video length in seconds (default 10).
        resolution: Output resolution — "480p", "720p", or "1080p" (default "480p").
        model: Model ID to use (default "higgsfield_v1").
        api_key: Higgsfield API key. Falls back to ``HIGGSFIELD_API_KEY`` env var.

    Returns:
        Dict with keys ``success``, ``file_path``, ``prompt``, ``duration``,
        ``resolution``, ``model``, ``status``, ``error``.
    """
    _ensure_storage()
    key = _resolve_api_key(api_key)
    if not key:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "model": model,
            "status": "",
            "error": _format_missing_key_instructions(),
        }

    url = f"{API_BASE}/generate"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
    }

    try:
        logger.info("Sending generation request to Higgsfield API (prompt=%.60s...)", prompt)
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "model": model,
            "status": "",
            "error": "Generation request timed out after 30 seconds",
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
            "duration": duration,
            "resolution": resolution,
            "model": model,
            "status": "",
            "error": f"API request failed: {exc}{' - ' + detail if detail else ''}",
        }

    generation_id = data.get("generation_id") or data.get("id")
    if not generation_id:
        return {
            "success": False,
            "file_path": "",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "model": model,
            "status": "",
            "error": f"No generation ID in response: {json.dumps(data)[:500]}",
        }

    # ── Poll for completion ──
    status_url = f"{API_BASE}/status/{generation_id}"
    poll_interval = 5
    deadline = time.time() + 180  # 3 minutes max

    while time.time() < deadline:
        try:
            poll_resp = requests.get(status_url, headers=headers, timeout=15)
            poll_resp.raise_for_status()
            status_data = poll_resp.json()
        except requests.exceptions.RequestException:
            time.sleep(poll_interval)
            continue

        state = (status_data.get("status") or status_data.get("state") or "").lower()

        if state in ("completed", "done", "succeeded", "ready"):
            video_url = (
                status_data.get("video_url")
                or status_data.get("output_url")
                or status_data.get("result_url")
                or status_data.get("url")
                or ""
            )
            if not video_url:
                return {
                    "success": False,
                    "file_path": "",
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": resolution,
                    "model": model,
                    "status": "completed",
                    "error": "Video generation completed but no video URL in response",
                }

            # Download the video
            try:
                video_resp = requests.get(video_url, timeout=60)
                video_resp.raise_for_status()
            except requests.exceptions.RequestException as exc:
                return {
                    "success": False,
                    "file_path": "",
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": resolution,
                    "model": model,
                    "status": "completed",
                    "error": f"Failed to download video from {video_url}: {exc}",
                }

            filename = f"higgsfield_{int(time.time())}.mp4"
            output_path = os.path.join(HIGGSFIELD_DIR, filename)
            try:
                with open(output_path, "wb") as f:
                    f.write(video_resp.content)
            except OSError as exc:
                return {
                    "success": False,
                    "file_path": "",
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": resolution,
                    "model": model,
                    "status": "completed",
                    "error": f"Failed to save video: {exc}",
                }

            return {
                "success": True,
                "file_path": os.path.normpath(output_path),
                "prompt": prompt,
                "duration": duration,
                "resolution": resolution,
                "model": model,
                "status": "completed",
                "error": None,
            }

        if state in ("failed", "error", "timeout"):
            error_msg = status_data.get("error") or status_data.get("message") or "Unknown error"
            return {
                "success": False,
                "file_path": "",
                "prompt": prompt,
                "duration": duration,
                "resolution": resolution,
                "model": model,
                "status": state,
                "error": f"Generation failed: {error_msg}",
            }

        time.sleep(poll_interval)

    return {
        "success": False,
        "file_path": "",
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "model": model,
        "status": "timeout",
        "error": "Video generation timed out after 180 seconds",
    }


def higgsfield_generate_from_image(
    image_path: str,
    prompt: str = "",
    motion: str = "orbit",
    api_key: str = "",
) -> dict:
    """Create a video from a static image using the Higgsfield image-to-video API.

    Args:
        image_path: Local path to the source image file.
        prompt: Optional text description to guide the animation.
        motion: Motion preset — one of: orbit, zoom_in, zoom_out,
            pan_left, pan_right, pan_up, pan_down, subtle (default "orbit").
        api_key: Higgsfield API key. Falls back to ``HIGGSFIELD_API_KEY`` env var.

    Returns:
        Dict with keys ``success``, ``file_path``, ``motion``, ``error``.
    """
    _ensure_storage()
    key = _resolve_api_key(api_key)
    if not key:
        return {
            "success": False,
            "file_path": "",
            "motion": motion,
            "error": _format_missing_key_instructions(),
        }

    if motion not in MOTION_PRESETS:
        return {
            "success": False,
            "file_path": "",
            "motion": motion,
            "error": f"Unknown motion '{motion}'. Available: {list(MOTION_PRESETS)}",
        }

    if not os.path.isfile(image_path):
        return {
            "success": False,
            "file_path": "",
            "motion": motion,
            "error": f"Image file not found: {image_path}",
        }

    url = f"{API_BASE}/image-to-video"
    headers = {
        "Authorization": f"Bearer {key}",
    }

    try:
        with open(image_path, "rb") as img_file:
            files = {
                "image": img_file,
            }
            data = {"motion": motion}
            if prompt:
                data["prompt"] = prompt

            logger.info("Sending image-to-video request (motion=%s, image=%s)", motion, image_path)
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)
            resp.raise_for_status()
            result = resp.json()
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "file_path": "",
            "motion": motion,
            "error": "Image-to-video request timed out after 120 seconds",
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
            "motion": motion,
            "error": f"API request failed: {exc}{' - ' + detail if detail else ''}",
        }

    generation_id = result.get("generation_id") or result.get("id")
    if generation_id:
        # Poll for completion
        status_url = f"{API_BASE}/status/{generation_id}"
        deadline = time.time() + 180

        while time.time() < deadline:
            try:
                poll_resp = requests.get(
                    status_url,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=15,
                )
                poll_resp.raise_for_status()
                status_data = poll_resp.json()
            except requests.exceptions.RequestException:
                time.sleep(5)
                continue

            state = (status_data.get("status") or status_data.get("state") or "").lower()

            if state in ("completed", "done", "succeeded", "ready"):
                video_url = (
                    status_data.get("video_url")
                    or status_data.get("output_url")
                    or status_data.get("result_url")
                    or status_data.get("url")
                    or ""
                )
                if not video_url:
                    return {
                        "success": False,
                        "file_path": "",
                        "motion": motion,
                        "error": "Generation completed but no video URL in response",
                    }

                try:
                    video_resp = requests.get(video_url, timeout=60)
                    video_resp.raise_for_status()
                except requests.exceptions.RequestException as exc:
                    return {
                        "success": False,
                        "file_path": "",
                        "motion": motion,
                        "error": f"Failed to download video: {exc}",
                    }

                filename = f"higgsfield_img_{int(time.time())}.mp4"
                output_path = os.path.join(HIGGSFIELD_DIR, filename)
                try:
                    with open(output_path, "wb") as f:
                        f.write(video_resp.content)
                except OSError as exc:
                    return {
                        "success": False,
                        "file_path": "",
                        "motion": motion,
                        "error": f"Failed to save video: {exc}",
                    }

                return {
                    "success": True,
                    "file_path": os.path.normpath(output_path),
                    "motion": motion,
                    "error": None,
                }

            if state in ("failed", "error", "timeout"):
                error_msg = status_data.get("error") or status_data.get("message") or "Unknown error"
                return {
                    "success": False,
                    "file_path": "",
                    "motion": motion,
                    "error": f"Generation failed: {error_msg}",
                }

            time.sleep(5)

        return {
            "success": False,
            "file_path": "",
            "motion": motion,
            "error": "Image-to-video generation timed out after 180 seconds",
        }

    video_url = result.get("video_url") or result.get("output_url") or result.get("url") or ""
    if video_url:
        try:
            video_resp = requests.get(video_url, timeout=60)
            video_resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            return {
                "success": False,
                "file_path": "",
                "motion": motion,
                "error": f"Failed to download video: {exc}",
            }

        filename = f"higgsfield_img_{int(time.time())}.mp4"
        output_path = os.path.join(HIGGSFIELD_DIR, filename)
        try:
            with open(output_path, "wb") as f:
                f.write(video_resp.content)
        except OSError as exc:
            return {
                "success": False,
                "file_path": "",
                "motion": motion,
                "error": f"Failed to save video: {exc}",
            }

        return {
            "success": True,
            "file_path": os.path.normpath(output_path),
            "motion": motion,
            "error": None,
        }

    return {
        "success": False,
        "file_path": "",
        "motion": motion,
        "error": f"Unexpected response: {json.dumps(result)[:500]}",
    }


def higgsfield_list_motions() -> dict:
    """Return available motion presets with descriptions.

    Returns:
        Dict with keys ``success``, ``motions`` (list of dicts with
        ``name``, ``description``, ``preview_url``), ``error``.
    """
    motions = []
    for key, preset in MOTION_PRESETS.items():
        motions.append({
            "name": key,
            "description": preset["description"],
            "preview_url": preset["preview_url"],
        })

    return {
        "success": True,
        "motions": motions,
        "error": None,
    }


def higgsfield_check_mcp() -> dict:
    """Check if the Higgsfield MCP server is available.

    Looks for the ``@higgsfield/mcp-server`` npm package and the
    ``HIGGSFIELD_MCP_URL`` environment variable.

    Returns:
        Dict with keys ``success``, ``mcp_available``, ``mcp_url``,
        ``instructions``.
    """
    mcp_available = False
    mcp_url = os.environ.get("HIGGSFIELD_MCP_URL", "")

    # Check npm package
    try:
        result = subprocess.run(
            ["npx", "--yes", "@higgsfield/mcp-server", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            shell=True,
        )
        if result.returncode == 0:
            mcp_available = True
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    # Also treat MCP_URL as available if set
    if mcp_url:
        try:
            resp = requests.get(mcp_url, timeout=5)
            mcp_available = resp.status_code < 500
        except requests.exceptions.RequestException:
            pass

    instructions = (
        "To set up the Higgsfield MCP server:\n\n"
        "  1. Install the package: npm install -g @higgsfield/mcp-server\n"
        "  2. Set the URL: set HIGGSFIELD_MCP_URL=https://your-mcp-server (or export)\n"
        "  3. Verify: npx @higgsfield/mcp-server --version\n"
        "The MCP server provides Model Context Protocol integration for AI agents."
    )

    return {
        "success": True,
        "mcp_available": mcp_available,
        "mcp_url": mcp_url or "",
        "instructions": instructions if not mcp_available else "",
    }


def higgsfield_status() -> dict:
    """Overall status check for Higgsfield tools.

    Checks API key presence, API reachability, MCP availability, and
    lists recent generations.

    Returns:
        Dict with keys ``success``, ``api_key_set``, ``api_reachable``,
        ``mcp_available``, ``recent_generations``, ``error``.
    """
    key = _resolve_api_key()
    api_key_set = bool(key)

    result = {
        "success": True,
        "api_key_set": api_key_set,
        "api_reachable": False,
        "mcp_available": False,
        "recent_generations": [],
        "error": None,
    }

    # Check API reachability
    if api_key_set:
        try:
            resp = requests.get(
                f"{API_BASE}/status/ping",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10,
            )
            result["api_reachable"] = resp.status_code in (200, 400, 401, 404)
        except requests.exceptions.RequestException:
            result["api_reachable"] = False
    else:
        result["error"] = "HIGGSFIELD_API_KEY is not set"

    # Check MCP
    mcp_check = higgsfield_check_mcp()
    result["mcp_available"] = mcp_check.get("mcp_available", False)

    # List recent generations
    try:
        _ensure_storage()
        entries = []
        for fname in sorted(os.listdir(HIGGSFIELD_DIR), reverse=True)[:10]:
            fpath = os.path.join(HIGGSFIELD_DIR, fname)
            if os.path.isfile(fpath) and fname.endswith(".mp4"):
                stat = os.stat(fpath)
                entries.append({
                    "filename": fname,
                    "size_bytes": stat.st_size,
                    "modified": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
                    ),
                })
        result["recent_generations"] = entries
    except OSError:
        pass

    return result
