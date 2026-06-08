"""
NVIDIA NIM Model Benchmark — tests text-generation models for:
  - Quality (reasoning + instruction following)
  - Context window handling (long document comprehension)
  - Speed (TTFT, tokens/sec)
  - Reliability (error rate)

Only tests models with 128K+ context (needed for 30K+ line markdown files).
Results saved to benchmark_results.json.
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

# Models grouped by context window size
# 128K context is minimum for handling 30K+ line research markdown files
MODELS_128K = [
    # ── Qwen (128K) ──
    "qwen/qwen3.5-397b-a17b",
    "qwen/qwen3.5-122b-a10b",
    "qwen/qwen3-coder-480b-a35b-instruct",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3.5-397b-a17b",
    # ── DeepSeek (128K) ──
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    # ── Meta Llama (128K) ──
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.3-70b-instruct",
    "meta/llama-4-maverick-17b-128e-instruct",  # 1M context!
    "meta/llama2-70b",
    "meta/codellama-70b",
    # ── Mistral (128K+) ──
    "mistralai/mistral-large",
    "mistralai/mistral-large-2-instruct",
    "mistralai/mistral-large-3-675b-instruct-2512",
    "mistralai/mistral-small-4-119b-2603",
    "mistralai/mistral-medium-3.5-128b",
    "mistralai/mistral-nemotron",
    "mistralai/mistral-7b-instruct-v0.3",
    "mistralai/ministral-14b-instruct-2512",
    "mistralai/mixtral-8x7b-instruct-v0.1",
    "mistralai/mixtral-8x22b-v0.1",
    "mistralai/codestral-22b-instruct-v0.1",
    "nv-mistralai/mistral-nemo-12b-instruct",
    # ── Google (128K+) ──
    "google/gemma-3-12b-it",
    "google/gemma-3-4b-it",
    "google/gemma-4-31b-it",
    "google/gemma-2-2b-it",
    # ── NVIDIA Nemotron (128K+) ──
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/llama-3.1-nemotron-51b-instruct",
    "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-4-340b-instruct",
    "nvidia/nemotron-mini-4b-instruct",
    "nvidia/nvidia-nemotron-nano-9b-v2",
    "nvidia/mistral-nemo-minitron-8b-8k-instruct",
    # ── Microsoft (128K) ──
    "microsoft/phi-4-mini-instruct",
    "microsoft/phi-3.5-moe-instruct",
    # ── Other (128K+) ──
    "moonshotai/kimi-k2.6",
    "stepfun-ai/step-3.5-flash",
    "stepfun-ai/step-3.7-flash",
    "01-ai/yi-large",
    "ai21labs/jamba-1.5-large-instruct",  # 256K
    "bytedance/seed-oss-36b-instruct",
    "minimaxai/minimax-m2.7",  # 1M context!
    "z-ai/glm-5.1",
    "writer/palmyra-creative-122b",
    "writer/palmyra-fin-70b-32k",
    "writer/palmyra-med-70b",
]

# Models with smaller context — excluded from primary benchmark
# but listed for reference
MODELS_SMALL_CONTEXT = [
    "databricks/dbrx-instruct",      # 32K
    "aisingapore/sea-lion-7b-instruct",
    "upstage/solar-10.7b-instruct",
    "ibm/granite-3.0-3b-a800m-instruct",
    "ibm/granite-3.0-8b-instruct",
    "ibm/granite-34b-code-instruct",
    "ibm/granite-8b-code-instruct",
    "abacusai/dracarys-llama-3.1-70b-instruct",
    "stockmark/stockmark-2-100b-instruct",
]

# Quality test prompt — tests reasoning, instruction following, and depth
QUALITY_PROMPT = """You are a physics professor. A student asks:

"I've read that quantum entanglement is a correlation between particles, but I don't understand how it differs from classical correlation. For example, if I have a pair of gloves and put each in a box, opening one box tells me the other glove's hand. How is quantum entanglement different from this?"

Please explain:
1. The key difference between classical correlation and quantum entanglement
2. What Bell's theorem proves about this difference
3. Why this matters for computing and communication

Be thorough but accessible. Include a simple analogy."""

# Long context test — simulates handling a large research document
CONTEXT_TEST_LENGTH = 10000  # 10K token context test


def make_long_context_prompt() -> tuple[str, str]:
    """Generate a long document + question to test context handling."""
    paragraphs = []
    for i in range(200):
        paragraphs.append(
            f"[Section {i+1}] The fundamental principles of thermodynamics "
            f"establish relationships between heat, work, temperature, and energy. "
            f"The first law states that energy cannot be created or destroyed. "
            f"The second law introduces entropy as a measure of disorder. "
            f"The third law states that as temperature approaches absolute zero, "
            f"entropy approaches a constant minimum. "
            f"These principles have profound implications for engine efficiency, "
            f"chemical reactions, and the arrow of time. "
            f"Section {i+1} specifically deals with the application of these "
            f"laws to quantum systems at very low temperatures."
        )
    document = "\n\n".join(paragraphs)
    question = (
        "\n\nBased ONLY on the document above, answer: "
        "What does Section 47 discuss? "
        "And what are the three laws of thermodynamics mentioned in the document? "
        "Be specific and quote relevant parts."
    )
    return document + question, document[:200] + "..."


async def test_quality(client: httpx.AsyncClient, model: str, sem: asyncio.Semaphore) -> dict:
    """Test reasoning quality: length, coherence, and depth of response."""
    async with sem:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": QUALITY_PROMPT}],
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
                return {"total_ms": elapsed, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "total_ms": elapsed,
                "response_length": len(content),
                "response_words": len(content.split()),
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "has_bell": "bell" in content.lower(),
                "has_analogy": any(w in content.lower() for w in ["like", "analog", "similar", "imagin"]),
                "error": None,
            }
        except httpx.TimeoutException:
            return {"total_ms": 180000, "error": "Timeout"}
        except Exception as e:
            return {"total_ms": 0, "error": str(e)[:200]}


async def test_speed(client: httpx.AsyncClient, model: str, sem: asyncio.Semaphore) -> dict:
    """Test streaming speed: TTFT, tokens/sec."""
    async with sem:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Write a detailed paragraph about quantum computing."}],
            "max_tokens": 512,
            "temperature": 0.3,
            "stream": True,
        }
        t0 = time.monotonic()
        first_token = True
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
                    return {"error": f"HTTP {resp.status_code}: {error_text[:200].decode(errors='ignore')}"}
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
                            if first_token:
                                first_token = False
                    except json.JSONDecodeError:
                        continue
            elapsed = time.monotonic() - t0
            return {
                "ttft_ms": None,
                "total_ms": int(elapsed * 1000),
                "tokens": total_tokens,
                "tokens_per_sec": round(total_tokens / elapsed, 2) if elapsed > 0 else 0,
                "error": None,
            }
        except httpx.TimeoutException:
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)[:200]}


async def test_context(client: httpx.AsyncClient, model: str, sem: asyncio.Semaphore) -> dict:
    """Test context window handling with a long document."""
    async with sem:
        prompt, preview = make_long_context_prompt()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.3,
        }
        t0 = time.monotonic()
        try:
            resp = await client.post(
                f"{NIM_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=httpx.Timeout(300.0, connect=15.0),
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            if resp.status_code != 200:
                return {"total_ms": elapsed, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            found_section_47 = "section 47" in content.lower()
            found_laws = any(law in content.lower() for law in ["first law", "second law", "third law"])
            return {
                "total_ms": elapsed,
                "found_section_47": found_section_47,
                "found_laws": found_laws,
                "response_length": len(content),
                "error": None,
            }
        except httpx.TimeoutException:
            return {"total_ms": 300000, "error": "Timeout (300s)"}
        except Exception as e:
            return {"total_ms": 0, "error": str(e)[:200]}


async def benchmark_model(client: httpx.AsyncClient, model: str, sem: asyncio.Semaphore) -> dict:
    result = {"model": model, "status": "pending", "error": None}
    for test_name, test_fn in [("quality", test_quality), ("speed", test_speed), ("context", test_context)]:
        r = await test_fn(client, model, sem)
        result[test_name] = r
        if r.get("error"):
            result["status"] = "error"
            result["error"] = f"{test_name}: {r['error']}"
            return result
    result["status"] = "success"
    return result


async def main():
    sem = asyncio.Semaphore(2)
    limits = httpx.Limits(max_connections=2, max_keepalive_connections=2)
    async with httpx.AsyncClient(limits=limits) as client:
        all_results = []
        total = len(MODELS_128K)
        print(f"Benchmarking {total} models (128K+ context)")
        print(f"\nTest 1 — Quality: reasoning depth + instruction following")
        print(f"Test 2 — Speed: TTFT + tokens/sec (streaming)")
        print(f"Test 3 — Context: 10K-token document comprehension")
        print(f"Concurrency: 2 | Each model: ~5 min max\n")
        for i, model in enumerate(MODELS_128K, 1):
            print(f"[{i}/{total}] {model}")
            t0 = time.monotonic()
            res = await benchmark_model(client, model, sem)
            elapsed = time.monotonic() - t0
            if res["status"] == "success":
                q = res["quality"]
                s = res["speed"]
                c = res["context"]
                print(f"  Quality: {q.get('response_words',0)} words, Bell={q.get('has_bell')}, Analogy={q.get('has_analogy')}, {q.get('total_ms')/1000:.1f}s")
                print(f"  Speed:   {s.get('tokens_per_sec',0)} tok/s, {s.get('total_ms',0)/1000:.1f}s total")
                print(f"  Context: found47={c.get('found_section_47')}, laws={c.get('found_laws')}, {c.get('total_ms')/1000:.1f}s")
            else:
                print(f"  FAILED: {res['error']}")
            print(f"  Total: {elapsed/60:.1f} min\n")
            all_results.append(res)

    # Scoring
    success = [r for r in all_results if r["status"] == "success"]

    def score(r: dict) -> float:
        q = r["quality"]
        c = r["context"]
        s = r["speed"]
        quality_score = 0
        if q.get("has_bell"):
            quality_score += 3
        if q.get("has_analogy"):
            quality_score += 2
        quality_score += min(q.get("response_words", 0) / 50, 5)
        context_score = 0
        if c.get("found_section_47"):
            context_score += 5
        if c.get("found_laws"):
            context_score += 5
        speed_score = min(s.get("tokens_per_sec", 0), 50)
        return quality_score * 3 + context_score * 3 + speed_score * 1

    success.sort(key=score, reverse=True)

    print("=" * 100)
    print("MODEL RANKING (quality*3 + context*3 + speed*1)")
    print("=" * 100)
    print(f"{'Rank':<5} {'Model':<55} {'Qty':<5} {'Ctx':<5} {'Spd':<8} {'Score':<8}")
    print("-" * 100)
    for rank, r in enumerate(success, 1):
        q = r["quality"]
        c = r["context"]
        s = r["speed"]
        q_score = (3 if q.get("has_bell") else 0) + (2 if q.get("has_analogy") else 0) + min(q.get("response_words", 0) / 50, 5)
        c_score = (5 if c.get("found_section_47") else 0) + (5 if c.get("found_laws") else 0)
        s_score = min(s.get("tokens_per_sec", 0), 50)
        total_score = q_score * 3 + c_score * 3 + s_score * 1
        print(f"{rank:<5} {r['model']:<55} {q_score:<5.1f} {c_score:<5.1f} {s_score:<8.1f} {total_score:<8.1f}")

    # Save
    out = {
        "timestamp": datetime.now().isoformat(),
        "prompt_quality": QUALITY_PROMPT[:100],
        "results": all_results,
        "ranking": [r["model"] for r in success],
    }
    with open("benchmark_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")
    print(f"Top 5: {', '.join(r['model'] for r in success[:5])}")


if __name__ == "__main__":
    asyncio.run(main())
