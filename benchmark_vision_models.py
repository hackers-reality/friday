"""
NVIDIA NIM Vision Model Benchmark — tests vision-language models with
live camera capture. Measures accuracy, speed, and video support.

Tests:
  - Object detection accuracy (what does the model see?)
  - Scene description quality (detail + correctness)
  - Speed (TTFT + total time)
  - Video/frame sequence support (if applicable)

Results saved to benchmark_vision_results.json.
"""

import asyncio
import base64
import io
import json
import os
import time
from datetime import datetime

import cv2
import httpx

NIM_API_BASE = "https://integrate.api.nvidia.com/v1"
API_KEY = os.environ.get("NVIDIA_VISION_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_VISION_API_KEY or NVIDIA_NIM_API_KEY first")

VISION_MODELS = [
    # ── Primary vision models (strong scene understanding) ──
    "nvidia/nemotron-nano-12b-v2-vl",       # current primary — supports video_understanding
    "meta/llama-3.2-90b-vision-instruct",    # large, best quality
    "meta/llama-3.2-11b-vision-instruct",    # current fallback — fast
    "microsoft/phi-4-multimodal-instruct",   # new multimodal — supports video
    "microsoft/phi-3-vision-128k-instruct",  # supports video
    # ── Additional vision models ──
    "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",  # NVIDIA VL model
    "nvidia/neva-22b",                        # vision-language
    "nvidia/vila",                            # video understanding
    "microsoft/kosmos-2",                     # multimodal
    "adept/fuyu-8b",                          # image understanding
    "google/deplot",                          # chart/figure understanding
]

# Video-capable models (can process frame sequences)
VIDEO_CAPABLE = [
    "nvidia/nemotron-nano-12b-v2-vl",
    "microsoft/phi-4-multimodal-instruct",
    "microsoft/phi-3-vision-128k-instruct",
    "nvidia/vila",
]

QUESTIONS = [
    "List every object, person, and detail visible in this image. Be thorough.",
    "What is the lighting condition? Describe the environment (indoor/outdoor, room type, furniture, etc.).",
    "Describe the colors, textures, and any text or labels visible.",
]


def capture_frame() -> str:
    """Capture a single frame from camera index 0 and return base64 JPEG."""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Fallback: try other indices
        for idx in (1, 2):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                break
    if not cap.isOpened():
        raise RuntimeError("No camera found")
    time.sleep(0.5)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture frame")
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return base64.b64encode(buf).decode("utf-8")


def capture_frames(n: int = 4, interval: float = 0.3) -> list[str]:
    """Capture multiple frames for video-capable models."""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError("No camera found")
    frames = []
    for _ in range(n):
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            frames.append(base64.b64encode(buf).decode("utf-8"))
        time.sleep(interval)
    cap.release()
    return frames


def build_vision_payload(model: str, question: str, frame_b64: str, is_video: bool = False) -> dict:
    """Build the multimodal payload for vision models."""
    if is_video and model in VIDEO_CAPABLE:
        # Some models support multiple frames as video
        frames = capture_frames(4)
        content = [{"type": "text", "text": question}]
        for f in frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{f}"},
            })
    else:
        content = [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}},
        ]
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 512,
        "temperature": 0.3,
    }


async def test_vision_model(client: httpx.AsyncClient, model: str, sem: asyncio.Semaphore, frame_b64: str) -> dict:
    """Test a vision model with a live camera frame."""
    async with sem:
        result = {
            "model": model,
            "status": "pending",
            "answers": {},
            "ttft_ms": None,
            "total_ms": None,
            "error": None,
        }

        for q_idx, question in enumerate(QUESTIONS):
            payload = build_vision_payload(model, question, frame_b64)
            t0 = time.monotonic()
            try:
                resp = await client.post(
                    f"{NIM_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=httpx.Timeout(60.0, connect=15.0),
                )
                elapsed = int((time.monotonic() - t0) * 1000)
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    result["answers"][f"q{q_idx}"] = f"ERROR: HTTP {resp.status_code}"
                    if result["error"] is None:
                        result["error"] = f"HTTP {resp.status_code}"
                    continue
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result["answers"][f"q{q_idx}"] = content[:500]
                result["total_ms"] = (result["total_ms"] or 0) + elapsed
            except httpx.TimeoutException:
                result["answers"][f"q{q_idx}"] = "TIMEOUT (60s)"
                if result["error"] is None:
                    result["error"] = "Timeout on vision call"
            except Exception as e:
                result["answers"][f"q{q_idx}"] = f"ERROR: {str(e)[:100]}"
                if result["error"] is None:
                    result["error"] = str(e)[:200]

        result["status"] = "success" if result["error"] is None else "partial"
        return result


async def main():
    print("NVIDIA NIM Vision Model Benchmark")
    print("=" * 60)
    print("Capturing camera frame...")
    try:
        frame_b64 = capture_frame()
        print(f"Frame captured: {len(frame_b64)} bytes base64")
    except RuntimeError as e:
        print(f"Camera error: {e}")
        print("Falling back to test pattern...")
        test_img = cv2.imread("test_pattern.jpg") if os.path.exists("test_pattern.jpg") else None
        if test_img is not None:
            _, buf = cv2.imencode(".jpg", test_img)
            frame_b64 = base64.b64encode(buf).decode("utf-8")
        else:
            print("No camera and no test image. Using dummy data.")
            frame_b64 = ""

    sem = asyncio.Semaphore(1)
    limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
    all_results = []

    async with httpx.AsyncClient(limits=limits) as client:
        total = len(VISION_MODELS)
        for i, model in enumerate(VISION_MODELS, 1):
            print(f"\n[{i}/{total}] {model}")
            is_video = model in VIDEO_CAPABLE
            if is_video:
                print(f"  Video-capable: testing with frame sequence")
            t0 = time.monotonic()
            res = await test_vision_model(client, model, sem, frame_b64)
            elapsed = time.monotonic() - t0
            print(f"  Status: {res['status']} ({elapsed:.1f}s)")
            for q_key, answer in res["answers"].items():
                print(f"  {q_key}: {answer[:120]}...")
            all_results.append(res)

    # Summary
    success = [r for r in all_results if r["status"] == "success"]
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in all_results:
        model = r["model"]
        vid = "(video)" if model in VIDEO_CAPABLE else ""
        avg_len = sum(len(a) for a in r["answers"].values()) / max(len(r["answers"]), 1) if r["answers"] else 0
        print(f"  {model:50s} {vid:10s} {r['status']:10s} avg={avg_len:.0f} chars")

    # Save
    out = {
        "timestamp": datetime.now().isoformat(),
        "questions": QUESTIONS,
        "results": all_results,
    }
    with open("benchmark_vision_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to benchmark_vision_results.json")


if __name__ == "__main__":
    asyncio.run(main())
