"""
FRIDAY Cookbook — Hardware scanner + model recommendations.
Scans local GPU/CPU/RAM and recommends the best local AI models to run.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_COOKBOOK_CACHE_PATH = os.path.join(FRIDAY_MEMORY, "cookbook_cache.json")

# Tiered model recommendations based on VRAM
_MODEL_RECOMMENDATIONS = {
    "tiny": {  # < 4GB VRAM
        "description": "Integrated graphics or low-end GPU",
        "llm": [
            {"name": "Phi-3-mini-4k-instruct (3.8B, Q4_K_M)", "vram_gb": 2.5, "provider": "llama.cpp / ollama"},
            {"name": "Gemma-2-2B (Q4_K_M)", "vram_gb": 1.8, "provider": "llama.cpp / ollama"},
            {"name": "Qwen2.5-1.5B-Instruct (Q4_K_M)", "vram_gb": 1.2, "provider": "llama.cpp / ollama"},
            {"name": "TinyLlama-1.1B (Q4_K_M)", "vram_gb": 0.8, "provider": "llama.cpp / ollama"},
        ],
        "vision": [{"name": "Florence-2-base (~0.3B)", "vram_gb": 2.0, "provider": "transformers"}],
        "embedding": [{"name": "all-MiniLM-L6-v2", "vram_gb": 0.5, "provider": "sentence-transformers"}],
        "stt": [{"name": "Whisper base", "vram_gb": 1.0, "provider": "openai-whisper / faster-whisper"}],
    },
    "small": {  # 4-8 GB VRAM
        "description": "Entry-level discrete GPU (GTX 1650, RTX 3050, Arc A380)",
        "llm": [
            {"name": "Llama-3.2-8B (Q4_K_M)", "vram_gb": 5.5, "provider": "llama.cpp / ollama / vLLM"},
            {"name": "Mistral-7B-v0.3 (Q4_K_M)", "vram_gb": 4.5, "provider": "llama.cpp / ollama"},
            {"name": "Gemma-2-9B (Q4_K_M)", "vram_gb": 6.0, "provider": "llama.cpp / ollama"},
            {"name": "Qwen2.5-7B-Instruct (Q4_K_M)", "vram_gb": 5.0, "provider": "llama.cpp / ollama"},
            {"name": "DeepSeek-Coder-V2-Lite (Q4_K_M)", "vram_gb": 6.0, "provider": "llama.cpp / ollama"},
        ],
        "vision": [{"name": "Florence-2-large (0.2B)", "vram_gb": 2.5, "provider": "transformers"}],
        "embedding": [{"name": "BGE-base-en-v1.5", "vram_gb": 1.0, "provider": "sentence-transformers"}],
        "stt": [{"name": "Whisper medium", "vram_gb": 3.0, "provider": "faster-whisper"}],
    },
    "medium": {  # 8-16 GB VRAM
        "description": "Mid-range GPU (RTX 3060/4060, Arc A770, RX 6700)",
        "llm": [
            {"name": "Llama-3.3-70B (Q3_K_M)", "vram_gb": 14.0, "provider": "llama.cpp / ollama"},
            {"name": "Mistral-Small-22B (Q4_K_M)", "vram_gb": 13.0, "provider": "llama.cpp / ollama"},
            {"name": "Qwen2.5-14B-Instruct (Q4_K_M)", "vram_gb": 8.5, "provider": "llama.cpp / ollama"},
            {"name": "DeepSeek-Coder-V2 (Q4_K_M)", "vram_gb": 14.0, "provider": "llama.cpp / ollama"},
            {"name": "Command-R-35B (Q3_K_M)", "vram_gb": 15.0, "provider": "llama.cpp / ollama"},
        ],
        "vision": [
            {"name": "Qwen2-VL-7B (Q4_K_M)", "vram_gb": 6.0, "provider": "llama.cpp / ollama"},
            {"name": "Florence-2-large (0.2B)", "vram_gb": 2.5, "provider": "transformers"},
        ],
        "embedding": [{"name": "BGE-large-en-v1.5", "vram_gb": 1.5, "provider": "sentence-transformers"}],
        "stt": [{"name": "Whisper large-v3", "vram_gb": 5.0, "provider": "faster-whisper"}],
    },
    "large": {  # 16-24 GB VRAM
        "description": "High-end GPU (RTX 3090/4090, A4000, RX 7900 XTX)",
        "llm": [
            {"name": "Llama-3.3-70B (Q4_K_M)", "vram_gb": 18.0, "provider": "llama.cpp / ollama / vLLM"},
            {"name": "Qwen2.5-32B-Instruct (Q4_K_M)", "vram_gb": 18.0, "provider": "llama.cpp / ollama"},
            {"name": "Command-R+ (Q4_K_M)", "vram_gb": 20.0, "provider": "llama.cpp / ollama"},
            {"name": "Mixtral-8x7B (Q4_K_M)", "vram_gb": 16.0, "provider": "llama.cpp / ollama"},
            {"name": "DeepSeek-Coder-V2-Instruct (Q4_K_M)", "vram_gb": 18.0, "provider": "llama.cpp / vLLM"},
        ],
        "vision": [
            {"name": "Qwen2-VL-7B (Q4_K_M)", "vram_gb": 6.0, "provider": "llama.cpp / ollama"},
            {"name": "LLaVA-NeXT-34B (Q4_K_M)", "vram_gb": 18.0, "provider": "llama.cpp / ollama"},
        ],
        "embedding": [{"name": "BGE-large-en-v1.5", "vram_gb": 1.5, "provider": "sentence-transformers"}],
        "stt": [{"name": "Whisper large-v3", "vram_gb": 5.0, "provider": "faster-whisper"}],
    },
    "ultra": {  # > 24 GB VRAM
        "description": "Enterprise GPU (A100, H100, RTX 6000 Ada, dual 4090s)",
        "llm": [
            {"name": "Llama-3.3-70B (Q8_0)", "vram_gb": 28.0, "provider": "llama.cpp / vLLM"},
            {"name": "Qwen2.5-72B-Instruct (Q4_K_M)", "vram_gb": 24.0, "provider": "llama.cpp / vLLM"},
            {"name": "Mixtral-8x22B (Q4_K_M)", "vram_gb": 28.0, "provider": "llama.cpp / vLLM"},
        ],
        "vision": [
            {"name": "LLaVA-NeXT-34B (Q8_0)", "vram_gb": 24.0, "provider": "llama.cpp / vLLM"},
            {"name": "InternVL2-40B (Q4_K_M)", "vram_gb": 22.0, "provider": "llama.cpp"},
        ],
        "embedding": [{"name": "BGE-large-en-v1.5", "vram_gb": 1.5, "provider": "sentence-transformers"}],
        "stt": [{"name": "Whisper large-v3 (distil)", "vram_gb": 3.0, "provider": "faster-whisper"}],
    },
}


def _detect_nvidia_gpu() -> dict[str, Any]:
    """Detect NVIDIA GPU(s) using nvidia-smi."""
    result = {"available": False, "gpus": [], "total_vram_gb": 0}
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            timeout=10, text=True,
        )
        for line in output.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                try:
                    total_mb = float(parts[2])
                    free_mb = float(parts[3])
                except ValueError:
                    continue
                gpu = {
                    "index": parts[0],
                    "name": parts[1],
                    "total_vram_gb": round(total_mb / 1024, 1),
                    "free_vram_gb": round(free_mb / 1024, 1),
                }
                result["gpus"].append(gpu)
                result["total_vram_gb"] += gpu["total_vram_gb"]
        result["available"] = bool(result["gpus"])
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return result


def _detect_amd_gpu() -> dict[str, Any]:
    """Detect AMD GPU using rocm-smi or Windows WMI."""
    result = {"available": False, "gpus": [], "total_vram_gb": 0}
    try:
        if sys.platform == "win32":
            import ctypes
            try:
                # Try using DXGI to find VRAM
                import win32com.client
                wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                service = wbi.ConnectServer(".", "root/cimv2")
                gpus_wmi = service.ExecQuery("SELECT * FROM Win32_VideoController")
                for gpu in gpus_wmi:
                    name = gpu.Name or "Unknown AMD GPU"
                    vram_str = gpu.AdapterRAM or "0"
                    try:
                        vram_gb = round(int(vram_str) / (1024**3), 1)
                    except (ValueError, TypeError):
                        vram_gb = 0
                    if vram_gb > 0:
                        gpu_info = {"index": len(result["gpus"]), "name": name, "total_vram_gb": vram_gb, "free_vram_gb": vram_gb}
                        result["gpus"].append(gpu_info)
                        result["total_vram_gb"] += vram_gb
            except Exception:
                pass
        else:
            output = subprocess.check_output(["rocm-smi", "--showmeminfo", "vram"], timeout=10, text=True)
            result["available"] = True
            result["_raw"] = output[:500]
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    result["available"] = bool(result["gpus"])
    return result


def _detect_apple_silicon() -> dict[str, Any]:
    """Detect Apple Silicon and unified memory."""
    result = {"available": False, "gpus": [], "total_vram_gb": 0}
    if platform.system() != "Darwin":
        return result
    try:
        import subprocess
        output = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=5, text=True)
        total_ram_bytes = int(output.strip())
        total_ram_gb = round(total_ram_bytes / (1024**3), 1)
        chip = platform.processor() or "Apple Silicon"
        result["gpus"].append({
            "index": 0, "name": f"Apple {chip} (Unified Memory)",
            "total_vram_gb": total_ram_gb,
            "free_vram_gb": round(total_ram_gb * 0.7, 1),
        })
        result["total_vram_gb"] = total_ram_gb
        result["available"] = True
    except Exception:
        pass
    return result


def _detect_gpu() -> dict[str, Any]:
    """Detect any available GPU. Tries NVIDIA, AMD, Apple Silicon."""
    result = _detect_nvidia_gpu()
    if result["available"]:
        result["type"] = "nvidia"
        return result
    result = _detect_amd_gpu()
    if result["available"]:
        result["type"] = "amd"
        return result
    result = _detect_apple_silicon()
    if result["available"]:
        result["type"] = "apple"
        return result
    return {"available": False, "type": "none", "gpus": [], "total_vram_gb": 0}


def _get_system_ram_gb() -> float:
    """Get total system RAM in GB."""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.GlobalMemoryStatusEx(ctypes.byref(ctypes.c_uint64(0)))
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_uint32),
                    ("dwMemoryLoad", ctypes.c_uint32),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return round(mem.ullTotalPhys / (1024**3), 1)
        else:
            import psutil
            return round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        return 0


def _detect_vulkan_gpu() -> dict[str, Any]:
    """Detect GPU via Vulkan API as a fallback."""
    result = {"available": False, "gpus": [], "total_vram_gb": 0}
    try:
        import subprocess
        output = subprocess.check_output(
            ["vulkaninfo", "--summary"],
            timeout=10, text=True, stderr=subprocess.DEVNULL,
        )
        result["_raw"] = output[:500]
        result["available"] = True
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    return result


def cookbook_scan(force: bool = False) -> str:
    """
    Scan local hardware (GPU, VRAM, RAM) and cache the results.
    Use force=True to re-scan instead of using cached results.
    """
    if not force and os.path.exists(_COOKBOOK_CACHE_PATH):
        try:
            with open(_COOKBOOK_CACHE_PATH) as f:
                cached = json.load(f)
            age = time.time() - cached.get("_cached_at", 0)
            if age < 3600:
                return _format_scan(cached)
        except Exception:
            pass

    gpu = _detect_gpu()
    ram_gb = _get_system_ram_gb()
    os_name = f"{platform.system()} {platform.release()}"
    python_ver = sys.version.split()[0]
    is_cuda = False
    try:
        import torch
        is_cuda = torch.cuda.is_available()
    except ImportError:
        pass

    scan = {
        "os": os_name,
        "python": python_ver,
        "ram_gb": ram_gb,
        "gpu": gpu,
        "cuda_available": is_cuda,
        "_cached_at": time.time(),
    }

    os.makedirs(os.path.dirname(_COOKBOOK_CACHE_PATH), exist_ok=True)
    try:
        with open(_COOKBOOK_CACHE_PATH, "w") as f:
            json.dump(scan, f, indent=2)
    except Exception:
        pass

    return _format_scan(scan)


def _format_scan(scan: dict) -> str:
    lines = ["### COOKBOOK — HARDWARE SCAN", ""]
    lines.append(f"**OS**: {scan.get('os', 'Unknown')}")
    lines.append(f"**Python**: {scan.get('python', 'Unknown')}")
    lines.append(f"**System RAM**: {scan.get('ram_gb', 0)} GB")

    gpu = scan.get("gpu", {})
    if gpu.get("available"):
        lines.append(f"**GPU Type**: {gpu.get('type', 'unknown')}")
        for g in gpu.get("gpus", []):
            lines.append(f"  - {g.get('name')}: {g.get('total_vram_gb', 0)} GB VRAM ({g.get('free_vram_gb', 0)} GB free)")
    else:
        lines.append("**GPU**: No discrete GPU detected (running on integrated graphics)")

    lines.append(f"**CUDA Available**: {'Yes' if scan.get('cuda_available') else 'No'}")
    return "\n".join(lines)


def _get_tier(vram_gb: float) -> str:
    if vram_gb < 4:
        return "tiny"
    elif vram_gb < 8:
        return "small"
    elif vram_gb < 16:
        return "medium"
    elif vram_gb < 24:
        return "large"
    else:
        return "ultra"


def cookbook_recommend() -> str:
    """
    Recommend the best local AI models based on detected hardware.
    Scans GPU/VRAM and matches against tiered model database.
    """
    gpu = _detect_gpu()
    ram_gb = _get_system_ram_gb()

    total_vram = gpu.get("total_vram_gb", 0)
    if total_vram == 0:
        total_vram = ram_gb * 0.3

    tier = _get_tier(total_vram)
    models = _MODEL_RECOMMENDATIONS.get(tier, _MODEL_RECOMMENDATIONS["tiny"])

    lines = ["### COOKBOOK — MODEL RECOMMENDATIONS", ""]
    lines.append(f"**Detected VRAM**: {total_vram} GB")
    lines.append(f"**Tier**: {tier.upper()} — {models['description']}")
    lines.append(f"**System RAM**: {ram_gb} GB")
    lines.append("")

    lines.append("**Recommended LLMs:**")
    for m in models.get("llm", []):
        lines.append(f"  - {m['name']} (~{m['vram_gb']} GB) — via {m['provider']}")

    lines.append("")
    lines.append("**Vision Models:**")
    for m in models.get("vision", []):
        lines.append(f"  - {m['name']} (~{m['vram_gb']} GB) — via {m['provider']}")

    lines.append("")
    lines.append("**Embedding Models:**")
    for m in models.get("embedding", []):
        lines.append(f"  - {m['name']} (~{m['vram_gb']} GB) — via {m['provider']}")

    lines.append("")
    lines.append("**Speech-to-Text:**")
    for m in models.get("stt", []):
        lines.append(f"  - {m['name']} (~{m['vram_gb']} GB) — via {m['provider']}")

    lines.append("")
    lines.append("**Installation:**")
    lines.append("  ollama:  https://ollama.com/download")
    lines.append("  vLLM:    pip install vllm")
    lines.append("  whisper: pip install faster-whisper")

    return "\n".join(lines)


def cookbook_ollama_check() -> str:
    """Check if Ollama is installed and list available models."""
    try:
        output = subprocess.check_output(["ollama", "list"], timeout=10, text=True, stderr=subprocess.DEVNULL)
        if output.strip():
            return f"### OLLAMA STATUS\n\nOllama is installed.\n\n```\n{output.strip()}\n```"
        return "### OLLAMA STATUS\n\nOllama is installed but no models found. Run `ollama pull llama3.2` to get started."
    except FileNotFoundError:
        return "[FAIL] Ollama not installed. Download from https://ollama.com/download"
    except subprocess.TimeoutExpired:
        return "[FAIL] Ollama list timed out."
    except subprocess.CalledProcessError as e:
        return f"[FAIL] Ollama error: {e}"
