"""Benchmark all available model endpoints: NIM, Zen, Big-Pickle, Gemini Live (HTTP)."""
import asyncio, httpx, json, time, os, sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

PING = "Reply in 10 words or fewer: What is 2+2?"

NIM_KEY = os.getenv("NVIDIA_NIM_API_KEY") or os.getenv("NVIDIA_API_KEY") or ""
ZEN_KEY = os.getenv("ZEN_API_KEY") or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENCODE_ZEN_API_KEY") or ""
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY") or ""

NIM_BASE = os.getenv("NIM_API_BASE", "https://integrate.api.nvidia.com/v1")
ZEN_BASE = os.getenv("ZEN_API_BASE", "https://opencode.ai/zen/v1")

NIM_MODELS = [
    ("DeepSeek V4 Flash", "deepseek-ai/deepseek-v4-flash"),
    ("DeepSeek V4 Pro", "deepseek-ai/deepseek-v4-pro"),
    ("Kimi K2.6", "moonshotai/kimi-k2.6"),
    ("Llama 3.3 70B", "meta/llama-3.3-70b-instruct"),
    ("Mistral Large 3", "mistralai/mistral-large-3-675b-instruct-2512"),
]

ZEN_MODELS = [
    ("MiMo V2.5 Free", "mimo-v2.5-free"),
    ("Big-Pickle", os.getenv("OPENCODE_ZEN_MODEL", "big-pickle")),
]

GEMINI_MODELS = [
    "gemini-3.1-flash-live-preview",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-2.5-flash-native-audio-preview-09-2025",
]

def trunc(s, n=80):
    return s[:n].replace("\n", " ") + ("..." if len(s) > n else "")

async def test_nim(name, model_id, http):
    start = time.time()
    try:
        resp = await http.post(
            f"{NIM_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {NIM_KEY}", "Content-Type": "application/json"},
            json={"model": model_id, "messages": [{"role": "user", "content": PING}],
                  "max_tokens": 50, "temperature": 0.1},
        )
        elapsed = time.time() - start
        if resp.status_code != 200:
            return (name, model_id, "FAIL", f"HTTP {resp.status_code}", elapsed, "")
        data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        return (name, model_id, "OK", f"TTFT ~{elapsed:.1f}s", elapsed, content.strip())
    except Exception as e:
        return (name, model_id, "ERR", str(e)[:60], time.time() - start, "")

async def test_zen(name, model_id, http):
    start = time.time()
    try:
        resp = await http.post(
            f"{ZEN_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {ZEN_KEY}", "Content-Type": "application/json"},
            json={"model": model_id, "messages": [{"role": "user", "content": PING}],
                  "max_tokens": 50, "temperature": 0.1},
        )
        elapsed = time.time() - start
        if resp.status_code != 200:
            body = await resp.aread()
            return (name, model_id, "FAIL", f"HTTP {resp.status_code} {body[:80]}", elapsed, "")
        data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        return (name, model_id, "OK", f"TTFT ~{elapsed:.1f}s", elapsed, content.strip())
    except Exception as e:
        return (name, model_id, "ERR", str(e)[:60], time.time() - start, "")

async def test_gemini(name, model_id):
    """Test Gemini models via REST generateContent endpoint."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            for version in ("v1alpha", "v1beta", "v1"):
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model_id}:generateContent"
                resp = await http.post(
                    f"{url}?key={GOOGLE_KEY}",
                    json={"contents": [{"parts": [{"text": PING}]}],
                          "generationConfig": {"maxOutputTokens": 50, "temperature": 0.1}},
                )
                elapsed = time.time() - start
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = " ".join(p.get("text", "") for p in parts)
                        return (name, model_id, "OK", f"API v{version[-1]} TTFT ~{elapsed:.1f}s", elapsed, text.strip())
                    return (name, model_id, "WARN", f"no candidates (v{version[-1]})", elapsed, "")
                if resp.status_code != 404:
                    elapsed = time.time() - start
                    body = await resp.aread()
                    return (name, model_id, "FAIL", f"HTTP {resp.status_code} (v{version[-1]}) {body[:60]}", elapsed, "")
        return (name, model_id, "SKIP", "not found on any API version", time.time() - start, "")
    except Exception as e:
        return (name, model_id, "ERR", str(e)[:60], time.time() - start, "")

async def main():
    print(f"\n{'='*90}")
    print(f"  MODEL BENCHMARK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*90}\n")
    print(f"Prompt: {PING}")
    print(f"{'='*90}\n")

    results = []

    # --- NIM ---
    print(f"[NIM] Testing {len(NIM_MODELS)} models via {NIM_BASE}")
    nim_key_ok = bool(NIM_KEY)
    print(f"      API key: {'SET' if nim_key_ok else 'MISSING'}")
    print()
    if nim_key_ok:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as http:
            tasks = [test_nim(name, mid, http) for name, mid in NIM_MODELS]
            for coro in asyncio.as_completed(tasks):
                r = await coro
                results.append(r)
                icon = {"OK": "PASS", "FAIL": "FAIL", "ERR": "ERR"}.get(r[2], "????")
                print(f"  [{icon}] {r[0]:22s} | {r[1]:40s} | {r[3]:45s} | {r[4]:5.1f}s")
                if r[5]:
                    print(f"       -> {trunc(r[5])}")
    else:
        print("  [SKIP] No NIM API key\n")

    # --- ZEN ---
    print(f"\n[ZEN] Testing {len(ZEN_MODELS)} models via {ZEN_BASE}")
    zen_key_ok = bool(ZEN_KEY)
    print(f"      API key: {'SET' if zen_key_ok else 'MISSING'}")
    print()
    if zen_key_ok:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as http:
            tasks = [test_zen(name, mid, http) for name, mid in ZEN_MODELS]
            for coro in asyncio.as_completed(tasks):
                r = await coro
                results.append(r)
                icon = {"OK": "PASS", "FAIL": "FAIL", "ERR": "ERR"}.get(r[2], "????")
                print(f"  [{icon}] {r[0]:22s} | {r[1]:40s} | {r[3]:45s} | {r[4]:5.1f}s")
                if r[5]:
                    print(f"       -> {trunc(r[5])}")
    else:
        print("  [SKIP] No Zen API key\n")

    # --- Gemini ---
    print(f"\n[GEMINI] Testing {len(GEMINI_MODELS)} models via HTTP REST")
    gemini_key_ok = bool(GOOGLE_KEY)
    print(f"       API key: {'SET' if gemini_key_ok else 'MISSING'}")
    print()
    if gemini_key_ok:
        tasks = [test_gemini(mid, mid) for mid in GEMINI_MODELS]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            icon = {"OK": "PASS", "FAIL": "FAIL", "ERR": "ERR", "WARN": "WARN", "SKIP": "SKIP"}.get(r[2], "????")
            print(f"  [{icon}] {r[0]:50s} | {r[3]:45s} | {r[4]:5.1f}s")
            if r[5]:
                print(f"       -> {trunc(r[5])}")
    else:
        print("  [SKIP] No Google API key\n")

    # --- Summary ---
    print(f"\n{'='*90}")
    print("  SUMMARY")
    print(f"{'='*90}")
    passed = [r for r in results if r[2] == "OK"]
    failed = [r for r in results if r[2] != "OK"]
    print(f"  Total: {len(results)}  |  Passed: {len(passed)}  |  Failed/Err/Skip: {len(failed)}")
    if passed:
        fastest = min(passed, key=lambda r: r[4])
        slowest = max(passed, key=lambda r: r[4])
        print(f"\n  Fastest: {fastest[0]} ({fastest[4]:.1f}s)")
        print(f"  Slowest: {slowest[0]} ({slowest[4]:.1f}s)")
    if failed:
        print(f"\n  Failures:")
        for r in failed:
            print(f"    - {r[0]:22s} ({r[1]}): {r[3]}")
    print(f"\n{'='*90}\n")

if __name__ == "__main__":
    asyncio.run(main())
