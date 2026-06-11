"""
FRIDAY Voice-Use Bridge — unified voice input/output via microphone and speakers.
Parallel to browser_use_bridge.py and desktop_use_bridge.py.

Provides: record, transcribe, TTS with playback, wake-word detection, audio analysis.
All sync on the surface (async internals run in background thread).
"""
from __future__ import annotations

import json
import os
import base64
import tempfile
import time
from datetime import datetime
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging
from friday.bridge_utils import _run_async

logger = configure_logging(__name__)

_VOICE_AVAILABLE = False

try:
    import sounddevice as sd
    _VOICE_AVAILABLE = True
except ImportError:
    sd = None

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "voice_use_state.json")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_actions": 0}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _increment_actions() -> None:
    state = _load_state()
    state["total_actions"] += 1
    _save_state(state)


# ── Capability detection ──────────────────────────────────────

def _check_backends() -> dict:
    """Return which voice backends are available."""
    backends = {}
    # sounddevice
    try:
        import sounddevice
        backends["sounddevice"] = True
    except ImportError:
        backends["sounddevice"] = False
    # faster-whisper
    try:
        import faster_whisper
        backends["faster_whisper"] = True
    except ImportError:
        backends["faster_whisper"] = False
    # gtts
    try:
        import gtts
        backends["gtts"] = True
    except ImportError:
        backends["gtts"] = False
    # edge-tts
    try:
        import edge_tts
        backends["edge_tts"] = True
    except ImportError:
        backends["edge_tts"] = False
    # pyttsx3
    try:
        import pyttsx3
        backends["pyttsx3"] = True
    except ImportError:
        backends["pyttsx3"] = False
    # soundfile (write WAV)
    try:
        import soundfile
        backends["soundfile"] = True
    except ImportError:
        backends["soundfile"] = False
    # playsound (play audio)
    try:
        import playsound
        backends["playsound"] = True
    except ImportError:
        backends["playsound"] = False
    # pyaudio (alternative)
    try:
        import pyaudio
        backends["pyaudio"] = True
    except ImportError:
        backends["pyaudio"] = False
    return backends


# ── Public API ────────────────────────────────────────────────

def voice_use_status() -> str:
    backends = _check_backends()
    state = _load_state()
    try:
        devices = sd.query_devices() if sd else []
        mic_count = sum(1 for d in devices if d.get("max_input_channels", 0) > 0)
        speaker_count = sum(1 for d in devices if d.get("max_output_channels", 0) > 0)
    except Exception:
        mic_count = speaker_count = 0
    return json.dumps({
        "available": _VOICE_AVAILABLE,
        "backends": backends,
        "microphones": mic_count,
        "speakers": speaker_count,
        "total_actions": state["total_actions"],
    }, indent=2)


def voice_list_devices() -> str:
    if not _VOICE_AVAILABLE:
        return json.dumps({"error": "sounddevice not installed"})
    try:
        devices = sd.query_devices()
        results = []
        for i, d in enumerate(devices):
            results.append({
                "index": i,
                "name": d.get("name", ""),
                "inputs": d.get("max_input_channels", 0),
                "outputs": d.get("max_output_channels", 0),
                "samplerate": d.get("default_samplerate", 0),
            })
        default_input = sd.default.device[0] if sd.default.device else None
        default_output = sd.default.device[1] if sd.default.device else None
        return json.dumps({
            "devices": results,
            "count": len(results),
            "default_input": default_input,
            "default_output": default_output,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_record(duration: float = 5.0, samplerate: int = 16000, device: int | None = None) -> str:
    if not _VOICE_AVAILABLE:
        return json.dumps({"error": "sounddevice not installed"})
    try:
        import soundfile as sf
        logger.info("Recording for %.1f seconds...", duration)
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, device=device)
        sd.wait()
        path = os.path.join(tempfile.gettempdir(), f"friday_recording_{int(time.time())}.wav")
        sf.write(path, recording, samplerate)
        _increment_actions()
        return json.dumps({
            "success": True,
            "path": path,
            "duration": duration,
            "samplerate": samplerate,
            "samples": len(recording),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_transcribe(audio_path: str, engine: str = "whisper") -> str:
    if not _VOICE_AVAILABLE:
        return json.dumps({"error": "sounddevice not installed"})
    try:
        if engine == "groq":
            from friday.tools.voice_tools import transcribe_audio_groq
            result = _run_async(transcribe_audio_groq(audio_path))
        else:
            from friday.tools.voice_tools import transcribe_audio
            result = _run_async(transcribe_audio(audio_path, engine="whisper"))
        _increment_actions()
        if isinstance(result, dict):
            return json.dumps({"success": True, "text": result.get("text", ""), "segments": result.get("segments", [])}, indent=2)
        return json.dumps({"success": True, "text": str(result)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_record_and_transcribe(duration: float = 5.0, engine: str = "whisper") -> str:
    rec_result = json.loads(voice_record(duration))
    if rec_result.get("error"):
        return json.dumps(rec_result)
    path = rec_result.get("path", "")
    if not path or not os.path.exists(path):
        return json.dumps({"error": "Recording failed, no file produced"})
    trans_result = json.loads(voice_transcribe(path, engine))
    return json.dumps({
        "success": trans_result.get("success", False),
        "text": trans_result.get("text", ""),
        "audio_path": path,
        "duration": duration,
    }, indent=2)


def voice_speak(text: str, engine: str = "gtts", voice: str | None = None, lang: str = "en") -> str:
    try:
        from friday.tools.voice_tools import speak_text
        from friday.bridge_utils import _run_async
        result = _run_async(speak_text(text, engine=engine, voice=voice, lang=lang))
        if "error" in result and not result.get("path"):
            return json.dumps({"success": False, "error": result["error"], "engine": engine})
        path = result.get("path", result.get("file_path", ""))
        # Try to play the audio file
        if path and os.path.exists(path):
            try:
                voice_play(path)
            except Exception:
                pass
        _increment_actions()
        return json.dumps({
            "success": True,
            "text": text[:200],
            "engine": engine,
            "path": path,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_play(audio_path: str) -> str:
    if not os.path.exists(audio_path):
        return json.dumps({"error": f"File not found: {audio_path}"})
    try:
        try:
            from playsound import playsound
            playsound(audio_path)
            _increment_actions()
            return json.dumps({"success": True, "played": audio_path}, indent=2)
        except ImportError:
            import winsound
            winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            _increment_actions()
            return json.dumps({"success": True, "played": audio_path, "backend": "winsound"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_detect_wake_word(keyword: str = "computer", sensitivity: float = 0.5, timeout: float = 10.0) -> str:
    try:
        from friday.tools.voice_tools import init_wake_word
        result = _run_async(init_wake_word(keyword=keyword, sensitivity=sensitivity))
        _increment_actions()
        if isinstance(result, dict):
            return json.dumps({"success": True, "keyword": keyword, "result": result.get("status", "initialized")}, indent=2)
        return json.dumps({"success": True, "keyword": keyword}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def voice_analyze(audio_path: str) -> str:
    try:
        from friday.tools.voice_tools import analyze_audio
        result = _run_async(analyze_audio(audio_path))
        _increment_actions()
        if isinstance(result, dict):
            return json.dumps({"success": True, **result}, indent=2)
        return json.dumps({"success": True, "result": str(result)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
