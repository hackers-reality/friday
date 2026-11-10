"""FRIDAY Voice Engine — one knob for the whole voice stack.

``config.yaml → voice.engine`` (or ``FRIDAY_VOICE_ENGINE``) selects the engine:

    gemini-live   Gemini 2.5 Flash Native Audio Live API (default; bidirectional voice)
    kitten        KittenTTS Nano 0.8 — local, offline, Apache-2.0 (Python 3.12 side venv)
    fish          Fish Audio cloud TTS (needs FISH_API_KEY; https://fish.audio)
    sarvam        Sarvam AI bulbul:v3 (needs SARVAM_API_KEY)

When Gemini Live is unavailable (429 / quota / audio 1007 / text-fallback mode) FRIDAY
speaks through the remainder of the chain, in this order:

    gemini-live  →  kitten  →  fish  →  sarvam

Edge TTS remains a last-resort safety net (kept for parity with the pre-existing
fallback path).

Fish Audio and Sarvam keys are read from the environment — they are never stored in
this module. Get a Fish key from the owner (never invented); see .env.example.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional

VOICE_ENGINE_ORDER = ("gemini-live", "kitten", "fish", "sarvam")
DEFAULT_VOICE = "Jasper"
REPO_ROOT = Path(__file__).resolve().parent.parent
KITTEN_HELPER = REPO_ROOT / "scripts" / "kitten_synth.py"
KITTEN_VENV_PYTHON = REPO_ROOT / ".venv-kitten" / "Scripts" / "python.exe"


# ─── Engine resolution ─────────────────────────────────────────────

def _config_engine() -> str:
    """Configured engine: env override → config.yaml voice.engine → default."""
    env_engine = os.getenv("FRIDAY_VOICE_ENGINE", "").strip().lower()
    if env_engine in VOICE_ENGINE_ORDER:
        return env_engine
    try:
        import yaml
        cfg_path = REPO_ROOT / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f) or {}
            engine = str(((cfg.get("voice") or {}).get("engine")) or "").strip().lower()
            if engine in VOICE_ENGINE_ORDER:
                return engine
    except Exception:
        pass
    return "gemini-live"


def get_voice_engine() -> str:
    """The configured engine (the chain still degrades gracefully)."""
    return _config_engine()


def voice_chain() -> list[str]:
    """Engines to try, in order, starting from the configured one."""
    engine = _config_engine()
    idx = VOICE_ENGINE_ORDER.index(engine) if engine in VOICE_ENGINE_ORDER else 0
    return list(VOICE_ENGINE_ORDER[idx:])


# ─── Engine availability ───────────────────────────────────────────

def kitten_available() -> bool:
    return KITTEN_VENV_PYTHON.exists() and KITTEN_HELPER.exists()


def fish_available() -> bool:
    return bool(os.getenv("FISH_API_KEY"))


def sarvam_available() -> bool:
    return bool(os.getenv("SARVAM_API_KEY"))


def voice_engine_status() -> dict[str, Any]:
    return {
        "configured": get_voice_engine(),
        "chain": voice_chain(),
        "engines": {
            "gemini-live": {"available": True, "note": "Live API voice (handled by friday.live)"},
            "kitten": {"available": kitten_available(),
                       "venv": str(KITTEN_VENV_PYTHON),
                       "model": "KittenML/kitten-tts-nano-0.8-fp32 (~50MB, 24kHz)",
                       "voice": os.getenv("FRIDAY_KITTEN_VOICE", DEFAULT_VOICE)},
            "fish": {"available": fish_available(),
                     "note": "Set FISH_API_KEY (owner-provided) — https://fish.audio",
                     "model": os.getenv("FISH_AUDIO_MODEL", "s2.1")},
            "sarvam": {"available": sarvam_available(), "note": "Set SARVAM_API_KEY (bulbul:v3)"},
        },
    }


# ─── Waveform plumbing ─────────────────────────────────────────────

def _play_wav_bytes(wav_bytes: bytes) -> None:
    """Play a WAV blob through the default output device (Windows)."""
    import pyaudio
    p = pyaudio.PyAudio()
    try:
        wf = wave.open(io.BytesIO(wav_bytes))
        try:
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            try:
                stream.write(wf.readframes(wf.getnframes()))
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            wf.close()
    finally:
        p.terminate()


def _synth_kitten(text: str) -> bytes:
    """Synthesize with KittenTTS via the Python 3.12 side venv. Returns WAV bytes."""
    if not kitten_available():
        raise RuntimeError("kitten side venv not found (.venv-kitten)")
    voice = os.getenv("FRIDAY_KITTEN_VOICE", DEFAULT_VOICE)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name
    try:
        proc = subprocess.run(
            [str(KITTEN_VENV_PYTHON), str(KITTEN_HELPER), "--voice", voice, "--out", out_path],
            input=json.dumps({"text": text}).encode("utf-8"),
            capture_output=True,
            timeout=180,
        )
        raw = proc.stdout.decode("utf-8", errors="replace").strip() or "{}"
        try:
            result = json.loads(raw.splitlines()[-1])
        except json.JSONDecodeError:
            raise RuntimeError(f"kitten helper returned non-JSON: {raw[:200]}")
        if not result.get("ok"):
            raise RuntimeError(f"kitten synth failed: {result.get('error', 'unknown')}")
        return Path(out_path).read_bytes()
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


async def _synth_fish(text: str) -> bytes:
    """Synthesize with Fish Audio (https://api.fish.audio/v1/tts). Returns audio bytes."""
    import httpx
    key = os.getenv("FISH_API_KEY")
    if not key:
        raise RuntimeError("FISH_API_KEY not set")
    payload: dict[str, Any] = {
        "text": text,
        "format": "wav",
        "model": os.getenv("FISH_AUDIO_MODEL", "s2.1"),
    }
    ref_id = os.getenv("FISH_REFERENCE_ID", "").strip()
    if ref_id:
        payload["reference_id"] = ref_id
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.fish.audio/v1/tts",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"fish.audio HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.content


async def _synth_sarvam(text: str) -> bytes:
    """Synthesize with Sarvam AI bulbul:v3. Returns WAV bytes."""
    import httpx
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        raise RuntimeError("SARVAM_API_KEY not set")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            json={"text": text, "speaker": os.getenv("SARVAM_SPEAKER", "priya"),
                  "model": "bulbul:v3", "target_language_code": os.getenv("SARVAM_LANG", "en-IN")},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"sarvam HTTP {resp.status_code}: {resp.text[:200]}")
    audios = resp.json().get("audios") or []
    if not audios:
        raise RuntimeError("sarvam returned no audio")
    return base64.b64decode(audios[0])


# ─── Public API ────────────────────────────────────────────────────

def _is_wav(data: bytes) -> bool:
    return data[:4] == b"RIFF" and data[8:12] == b"WAVE"


async def synthesize_and_play(text: str) -> dict[str, Any]:
    """Walk the voice chain from the configured engine; play the first WAV that
    synthesizes. Returns a result dict — never raises."""
    if not text or not text.strip():
        return {"ok": False, "error": "empty text"}
    attempts: list[dict[str, str]] = []
    for engine in voice_chain():
        if engine == "gemini-live":
            attempts.append({"engine": engine, "status": "skipped", "note": "handled by Live session"})
            continue
        try:
            if engine == "kitten":
                audio = await asyncio.get_running_loop().run_in_executor(None, _synth_kitten, text)
            elif engine == "fish":
                audio = await _synth_fish(text)
            elif engine == "sarvam":
                audio = await _synth_sarvam(text)
            else:
                continue
            if not _is_wav(audio):
                raise RuntimeError("engine returned non-WAV audio (Fish: set format='wav')")
            await asyncio.get_running_loop().run_in_executor(None, _play_wav_bytes, audio)
            return {"ok": True, "engine": engine, "attempts": attempts}
        except Exception as e:  # noqa: BLE001 — degrade down the chain
            attempts.append({"engine": engine, "status": "failed", "note": str(e)[:160]})
            continue

    # Last resort: Edge TTS (pre-existing fallback behavior)
    try:
        from friday.tools.voice_tools import speak_text
        await speak_text(text, engine="edge", voice="en-US-AriaNeural")
        return {"ok": True, "engine": "edge", "attempts": attempts}
    except Exception as e:
        attempts.append({"engine": "edge", "status": "failed", "note": str(e)[:160]})
        return {"ok": False, "error": "no voice engine available", "attempts": attempts}
