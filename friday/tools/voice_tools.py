"""
Voice & Audio tools module
Libraries: pyaudio, sounddevice, porcupine, faster-whisper, groq, google-speech,
azure-speech, gtts, elevenlabs, pyttsx3, edge-tts, pydub, librosa, mutagen
"""
import asyncio
import io
import os
import tempfile
from typing import Any

# ── Audio I/O ──

HAS_PYAUDIO = False
HAS_SOUNDDEVICE = False
try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pass
try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    pass


async def list_audio_devices() -> dict[str, Any]:
    devices = []
    if HAS_SOUNDDEVICE:
        info = await asyncio.get_event_loop().run_in_executor(None, sd.query_devices)
        devices = [{"index": i, "name": d["name"], "channels": d["max_input_channels"], "sr": int(d["default_samplerate"])} for i, d in enumerate(info)]
    elif HAS_PYAUDIO:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            d = p.get_device_info_by_index(i)
            if d["maxInputChannels"] > 0:
                devices.append({"index": i, "name": d["name"], "channels": d["maxInputChannels"], "sr": int(d["defaultSampleRate"])})
        p.terminate()
    return {"devices": devices, "count": len(devices)}


async def record_audio(duration: float = 5.0, samplerate: int = 16000, device: int | None = None) -> dict[str, Any]:
    if not HAS_SOUNDDEVICE:
        return {"error": "sounddevice not installed", "duration": duration}
    try:
        recording = await asyncio.get_event_loop().run_in_executor(
            None, lambda: sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, device=device, dtype="float32")
        )
        await asyncio.get_event_loop().run_in_executor(None, lambda: sd.wait())
        path = os.path.join(tempfile.gettempdir(), "friday_recording.wav")
        import scipy.io.wavfile as wav
        wav.write(path, samplerate, (recording * 32767).astype(np.int16))
        return {"path": path, "duration": duration, "samplerate": samplerate, "samples": len(recording)}
    except Exception as e:
        return {"error": str(e)}


# ── Wake Word (Porcupine) ──

HAS_PORCUPINE = False
try:
    import pvporcupine
    HAS_PORCUPINE = True
except ImportError:
    pass


async def init_wake_word(keyword: str = "computer", sensitivity: float = 0.5) -> dict[str, Any]:
    if not HAS_PORCUPINE:
        return {"error": "pvporcupine not installed. Install: pip install pvporcupine", "keyword": keyword}
    return {"status": "ready", "keyword": keyword, "sensitivity": sensitivity, "library": "porcupine"}


# ── Speech-to-Text ──

HAS_WHISPER = False
try:
    import faster_whisper
    HAS_WHISPER = True
except ImportError:
    pass

HAS_GROQ = False
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    pass


async def transcribe_audio(audio_path: str, engine: str = "whisper") -> dict[str, Any]:
    if engine == "whisper" and HAS_WHISPER:
        try:
            model = await asyncio.get_event_loop().run_in_executor(None, lambda: faster_whisper.WhisperModel("base"))
            segments, info = await asyncio.get_event_loop().run_in_executor(None, lambda: model.transcribe(audio_path))
            text = " ".join([s.text for s in segments])
            return {"text": text, "engine": "faster-whisper", "language": info.language, "duration": info.duration}
        except Exception as e:
            return {"error": str(e), "engine": "faster-whisper"}
    return {"error": "No STT engine available", "engine": engine}


async def transcribe_audio_groq(audio_path: str) -> dict[str, Any]:
    if not HAS_GROQ:
        return {"error": "groq not installed"}
    try:
        client = Groq()
        with open(audio_path, "rb") as f:
            transcript = await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.audio.transcriptions.create(file=(audio_path, f.read()), model="whisper-large-v3")
            )
        return {"text": transcript.text, "engine": "groq-whisper"}
    except Exception as e:
        return {"error": str(e)}


# ── Text-to-Speech ──

HAS_GTTS = False
HAS_PYTTSX3 = False
HAS_EDGETTS = False
HAS_ELEVENLABS = False
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    pass
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    pass
try:
    import edge_tts
    HAS_EDGETTS = True
except ImportError:
    pass


async def speak_text(text: str, engine: str = "gtts", voice: str | None = None, lang: str = "en") -> dict[str, Any]:
    path = os.path.join(tempfile.gettempdir(), "friday_tts_output.mp3")
    if engine == "gtts" and HAS_GTTS:
        try:
            tts = await asyncio.get_event_loop().run_in_executor(None, lambda: gTTS(text=text, lang=lang, slow=False))
            await asyncio.get_event_loop().run_in_executor(None, lambda: tts.save(path))
            return {"path": path, "engine": "gtts", "text_length": len(text)}
        except Exception as e:
            return {"error": str(e), "engine": "gtts"}
    elif engine == "edge" and HAS_EDGETTS:
        try:
            voice = voice or "en-US-AriaNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(path)
            return {"path": path, "engine": "edge-tts", "voice": voice, "text_length": len(text)}
        except Exception as e:
            return {"error": str(e), "engine": "edge-tts"}
    elif engine == "pyttsx3" and HAS_PYTTSX3:
        try:
            def _speak():
                tts = pyttsx3.init()
                tts.save_to_file(text, path)
                tts.runAndWait()
            await asyncio.get_event_loop().run_in_executor(None, _speak)
            return {"path": path, "engine": "pyttsx3", "text_length": len(text)}
        except Exception as e:
            return {"error": str(e), "engine": "pyttsx3"}
    return {"error": f"No TTS engine available for {engine}"}


async def list_tts_voices(engine: str = "edge") -> dict[str, Any]:
    if engine == "edge" and HAS_EDGETTS:
        try:
            voices = await edge_tts.list_voices()
            return {"voices": [{"name": v["Name"], "locale": v["Locale"], "gender": v["Gender"]} for v in voices], "count": len(voices)}
        except Exception as e:
            return {"error": str(e)}
    return {"voices": [], "count": 0}


# ── Audio Manipulation (pydub) ──

HAS_PYDUB = False
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    pass


async def convert_audio(input_path: str, output_format: str = "wav") -> dict[str, Any]:
    if not HAS_PYDUB:
        return {"error": "pydub not installed"}
    try:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.{output_format}"
        audio = await asyncio.get_event_loop().run_in_executor(None, lambda: AudioSegment.from_file(input_path))
        await asyncio.get_event_loop().run_in_executor(None, lambda: audio.export(output_path, format=output_format))
        return {"input": input_path, "output": output_path, "format": output_format}
    except Exception as e:
        return {"error": str(e)}


async def merge_audio(file1: str, file2: str, output_path: str | None = None) -> dict[str, Any]:
    if not HAS_PYDUB:
        return {"error": "pydub not installed"}
    try:
        a1 = await asyncio.get_event_loop().run_in_executor(None, lambda: AudioSegment.from_file(file1))
        a2 = await asyncio.get_event_loop().run_in_executor(None, lambda: AudioSegment.from_file(file2))
        combined = a1 + a2
        out = output_path or os.path.join(tempfile.gettempdir(), "merged_audio.mp3")
        await asyncio.get_event_loop().run_in_executor(None, lambda: combined.export(out, format=out.split(".")[-1]))
        return {"output": out, "duration_ms": len(combined)}
    except Exception as e:
        return {"error": str(e)}


# ── Audio Analysis (librosa) ──

HAS_LIBROSA = False
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    pass


async def analyze_audio(audio_path: str) -> dict[str, Any]:
    if not HAS_LIBROSA:
        return {"error": "librosa not installed"}
    try:
        y, sr = await asyncio.get_event_loop().run_in_executor(None, lambda: librosa.load(audio_path, sr=None))
        tempo = await asyncio.get_event_loop().run_in_executor(None, lambda: librosa.beat.tempo(y=y, sr=sr))
        spectral = await asyncio.get_event_loop().run_in_executor(None, lambda: float(librosa.feature.spectral_centroid(y=y, sr=sr).mean()))
        rms = await asyncio.get_event_loop().run_in_executor(None, lambda: float(librosa.feature.rms(y=y).mean()))
        return {"duration": float(len(y) / sr), "sample_rate": sr, "tempo": float(tempo[0]), "spectral_centroid": spectral, "rms_energy": rms}
    except Exception as e:
        return {"error": str(e)}


# ── Audio Metadata (mutagen) ──

HAS_MUTAGEN = False
try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    pass


async def get_audio_metadata(audio_path: str) -> dict[str, Any]:
    if not HAS_MUTAGEN:
        return {"error": "mutagen not installed"}
    try:
        audio = await asyncio.get_event_loop().run_in_executor(None, lambda: MutagenFile(audio_path))
        if audio is None:
            return {"error": "Could not read audio metadata"}
        tags = {}
        for k, v in (audio.tags or {}).items():
            tags[k] = str(v)
        return {"path": audio_path, "format": str(type(audio).__name__), "length": getattr(audio.info, "length", 0), "bitrate": getattr(audio.info, "bitrate", 0), "tags": tags}
    except Exception as e:
        return {"error": str(e)}
