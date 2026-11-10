# FRIDAY Voice Engines

Selected via `config.yaml → voice.engine` (or `FRIDAY_VOICE_ENGINE`). Default: `gemini-live`.
When Gemini Live is unavailable (429 / quota / audio-1007 / text-fallback mode), FRIDAY
speaks through the remainder of the chain, in order:

**gemini-live → kitten → fish → sarvam** (Edge TTS is a final safety net)

## Engines

| Engine | Type | Cost | Needs | Notes |
|---|---|---|---|---|
| `gemini-live` | Gemini Live native audio (bidirectional) | free-tier + billing | `GOOGLE_API_KEY` | Default. Voice handled inside the Live session; falls through on 429/quota. |
| `kitten` | KittenTTS Nano 0.8 — local, 15M params, ~50MB, Apache-2.0 | free | Python 3.12 (KittenTTS requires <3.13) | Runs in a dedicated side venv `.venv-kitten/` via `scripts/kitten_synth.py`. 24kHz, CPU-fine, offline. Voices: Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki, Leo (`FRIDAY_KITTEN_VOICE`). |
| `fish` | Fish Audio cloud TTS, 2M+ voices with emotion tags, 30+ langs, S2.1 | free tier | `FISH_API_KEY` (owner-provided) | REST `POST https://api.fish.audio/v1/tts`. Model via `FISH_AUDIO_MODEL` (default `s2.1`), optional `FISH_REFERENCE_ID` for a specific voice. |
| `sarvam` | Sarvam AI bulbul:v3 | free tier | `SARVAM_API_KEY` | en-IN, speaker `priya` (override `SARVAM_SPEAKER`). |

## One-time setup (KittenTTS)

FRIDAY's venv is Python 3.13; KittenTTS wheels target <3.13, so synthesis runs in a
side venv (same pattern as the `agent-desktop` subprocess):

```powershell
& 'C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe' -m venv .venv-kitten
.\.venv-kitten\Scripts\python.exe -m pip install "https://github.com/KittenML/KittenTTS/releases/download/0.8/kittentts-0.8.0-py3-none-any.whl"
```

`.venv-kitten/` is gitignored. The first synthesis downloads the model (~50MB) from HF.

List status at runtime: `python -c "from friday.voice_engine import voice_engine_status; import json; print(json.dumps(voice_engine_status(), indent=2))"`

## Verification status (2026-11-10)

- gemini-live: pending owner launch test (engine itself never started in this session).
- kitten: **VERIFIED** — side venv built (Python 3.12), model downloaded, `scripts/kitten_synth.py` synthesized a 24kHz mono WAV (jasper, ~155KB) via the CLI helper.
- fish: NOT usable until the owner provides `FISH_API_KEY` (never invented).
- sarvam: pre-existing path; key-gated.
