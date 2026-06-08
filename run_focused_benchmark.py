"""
Focused benchmark: user's requested models + current models + top contenders.
Runs quality + speed + context tests and reports results.
"""

import asyncio
import json
import os
import time
from datetime import datetime

import httpx

NIM_API_BASE = "https://integrate.api.nvidia.com/v1"
API_KEY = os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_NIM_API_KEY first")

FOCUS_MODELS = [
    # ── User's specifically requested ──
    "moonshotai/kimi-k2.6",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "minimaxai/minimax-m2.7",
    "google/gemma-4-31b-it",
    # ── Currently used in config ──
    "qwen/qwen3.5-397b-a17b",
    "deepseek-ai/deepseek-v4-flash",
    "qwen/qwen3.5-122b-a10b",
    "qwen/qwen3-next-80b-a3b-instruct",
    # ── Top contenders (Nemotron super, Llama 4, Step) ──
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "meta/llama-4-maverick-17b-128e-instruct",
    "stepfun-ai/step-3.7-flash",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    # ── High-quality from Mistral ──
    "mistralai/mistral-large-3-675b-instruct-2512",
    "mistralai/mistral-small-4-119b-2603",
    "mistralai/mistral-nemotron",
    # ── DeepSeek ──
    "deepseek-ai/deepseek-v4-pro",
    # ── Qwen large ──
    "qwen/qwen3-coder-480b-a35b-instruct",
]

PROMPT = """You are a physics professor. A student asks:

"I've read that quantum entanglement is a correlation between particles, but I don't understand how it differs from classical correlation. For example, if I have a pair of gloves and put each in a box, opening one box tells me the other glove's hand. How is quantum entanglement different from this?"

Please explain:
1. The key difference between classical correlation and quantum entanglement
2. What Bell's theorem proves about this difference
3. Why this matters for computing and communication

Be thorough but accessible. Include a simple analogy."""


async def test_quality(client, model, sem):
    async with sem:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        t0 = time.monotonic()
        try:
            resp = await client.post(
                f"{NIM_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=httpx.Timeout(180.0, connect=15.0),
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "total_ms": elapsed,
                "response_words": len(content.split()),
                "has_bell": "bell" in content.lower(),
                "has_analogy": any(w in content.lower() for w in ["glove", "box", "coin", "like", "analog", "imagin", "suppose", "consider"]),
                "has_epr": "epr" in content.lower(),
                "has_computing": any(w in content.lower() for w in ["comput", "quantum computer", "cryptograph"]),
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "error": None,
            }
        except httpx.TimeoutException:
            return {"error": "Timeout (180s)"}
        except Exception as e:
            return {"error": str(e)[:200]}


async def test_speed(client, model, sem):
    async with sem:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Write a detailed paragraph about quantum computing architecture. Include discussions of superconducting qubits, trapped ions, and error correction."}],
            "max_tokens": 512,
            "temperature": 0.3,
            "stream": True,
        }
        t0 = time.monotonic()
        ttft = None
        total_tokens = 0
        try:
            async with client.stream(
                "POST",
                f"{NIM_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=httpx.Timeout(120.0, connect=15.0),
            ) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    return {"error": f"HTTP {resp.status_code}"}
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices and choices[0].get("delta", {}).get("content"):
                            total_tokens += 1
                            if ttft is None:
                                ttft = int((time.monotonic() - t0) * 1000)
                    except json.JSONDecodeError:
                        continue
            elapsed = time.monotonic() - t0
            return {
                "ttft_ms": ttft or int(elapsed * 1000),
                "total_ms": int(elapsed * 1000),
                "tokens": total_tokens,
                "tokens_per_sec": round(total_tokens / elapsed, 2) if elapsed > 0 else 0,
                "error": None,
            }
        except httpx.TimeoutException:
            return {"error": "Timeout (120s)"}
        except Exception as e:
            return {"error": str(e)[:200]}


async def main():
    sem = asyncio.Semaphore(2)
    limits = httpx.Limits(max_connections=2, max_keepalive_connections=2)
    results = []

    print("Focused Model Benchmark")
    print(f"Testing {len(FOCUS_MODELS)} models\n")

    async with httpx.AsyncClient(limits=limits) as client:
        for i, model in enumerate(FOCUS_MODELS, 1):
            print(f"[{i}/{len(FOCUS_MODELS)}] {model}")
            t0 = time.monotonic()
            q = await test_quality(client, model, sem)
            if q.get("error"):
                print(f"  QUALITY FAILED: {q['error']}")
                results.append({"model": model, "status": "error", "error": q["error"]})
                continue
            s = await test_speed(client, model, sem)
            if s.get("error"):
                print(f"  SPEED FAILED: {s['error']}")
                results.append({"model": model, "status": "error", "error": s["error"]})
                continue
            elapsed = time.monotonic() - t0
            print(f"  Words={q['response_words']} Bell={q['has_bell']} Analogy={q['has_analogy']} EPR={q['has_epr']} QC={q['has_computing']}")
            print(f"  Speed: {s['tokens_per_sec']} tok/s  TTFT={s['ttft_ms']}ms  Total={s['total_ms']}ms")
            print(f"  Time: {elapsed/60:.1f}min")
            results.append({
                "model": model, "status": "success",
                "quality": q, "speed": s,
            })

    # ── Scoring ──
    print("\n" + "=" * 110)
    print(f"{'Rank':<5} {'Model':<55} {'Words':<7} {'Bell':<6} {'Ana':<5} {'EPR':<5} {'QC':<5} {'tok/s':<8} {'TTFT':<8} {'Score':<8}")
    print("-" * 110)

    def score(r):
        q = r["quality"]
        s = r["speed"]
        sc = 0
        if q["has_bell"]: sc += 15
        if q["has_analogy"]: sc += 10
        if q["has_epr"]: sc += 10
        if q["has_computing"]: sc += 5
        sc += min(q["response_words"] / 20, 10)
        sc += min(s["tokens_per_sec"], 20)
        return sc

    scored = [r for r in results if r["status"] == "success"]
    scored.sort(key=lambda r: -score(r))

    for rank, r in enumerate(scored, 1):
        q = r["quality"]
        s = r["speed"]
        sc = score(r)
        print(f"{rank:<5} {r['model']:<55} {q['response_words']:<7} {str(q['has_bell']):<6} {str(q['has_analogy']):<5} {str(q['has_epr']):<5} {str(q['has_computing']):<5} {s['tokens_per_sec']:<8} {s['ttft_ms']:<8} {sc:<8.1f}")

    # Save
    out = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "ranking": [r["model"] for r in scored],
    }
    with open("benchmark_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")

    # Recommendation
    if scored:
        best = scored[0]
        print(f"\nRecommended primary model: {best['model']}")
        if len(scored) > 1:
            print(f"Runner-up: {scored[1]['model']}")

    return scored


if __name__ == "__main__":
    ranking = asyncio.run(main())
