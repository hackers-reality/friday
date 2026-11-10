# FRIDAY Voice Engines

Selected via `config.yaml → voice.engine` (or `FRIDAY_VOICE_ENGINE`). Default: `gemini-live`.
When Gemini Live is unavailable (429 / quota / audio-1007 / text-fallback mode), FRIDAY
speaks through the remainder of the chain, in order:

**gemini-live → fish (Selene) → kitten → sarvam** (Edge TTS is a final safety net)

Selene is the Fish Official English voice (owner-selected 2026-11-10): reference id
`b347db033a6549378b48d00acb0d06cd`.

## Engines

| Engine | Type | Cost | Needs | Notes |
|---|---|---|---|---|
| `gemini-live` | Gemini Live native audio (bidirectional) | free-tier + billing | `GOOGLE_API_KEY` | Default. Voice handled inside the Live session; falls through on 429/quota. |
| `fish` | Fish Audio cloud TTS, Selene voice, 2M+ voices with emotion tags, 30+ langs | free tier | `FISH_API_KEY` (owner-provided) | REST `POST https://api.fish.audio/v1/tts`. **Free tier works only with the literal model id `s2.1-pro-free` — paid models return HTTP 402 without credit.** Sent as an HTTP **header** `model: s2.1-pro-free` (per the 402 body) plus in the JSON body. `FISH_AUDIO_MODEL` unset/blank → defaults to `s2.1-pro-free`; a configured paid id that returns 402 is auto-retried with `s2.1-pro-free`. `FISH_REFERENCE_ID` pins the voice (Selene). Sample: `tts_test/selene_fish_sample2.wav` (44.1kHz / 16-bit mono, canonicalized header). |
| `kitten` | KittenTTS Nano 0.8 — local, 15M params, ~50MB, Apache-2.0 | free | Python 3.12 (KittenTTS requires <3.13) | Runs in a dedicated side venv `.venv-kitten/` via `scripts/kitten_synth.py`. 24kHz, CPU-fine, offline. Voices: Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki, Leo (`FRIDAY_KITTEN_VOICE`). |
| `sarvam` | Sarvam AI bulbul:v3 | free tier | `SARVAM_API_KEY` | en-IN, speaker `priya` (override `SARVAM_SPEAKER`). |

Fish note: the API streams WAVs with placeholder size fields (RIFF/data sizes ≈ 0xFFFF0000).
`friday/voice_engine.py` normalizes them (`_normalize_wav`) before playback/probing —
Python's `wave` module trusts those sizes otherwise.

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
- fish (Selene): **VERIFIED** — `FISH_API_KEY` in `.env` + `FISH_REFERENCE_ID=b347...` +
  `FISH_AUDIO_MODEL=s2.1-pro-free`. Synthesized "FRIDAY online. Selene voice check, one two three."
  in ~9–14s → `tts_test/selene_fish_sample2.wav` (44.1kHz/16-bit mono, ~4.8s, canonical header).
  402-retry path verified by forcing `FISH_AUDIO_MODEL=s2.1` inline → 402 → auto-retry with
  `s2.1-pro-free` → 200 WAV.
- kitten: **VERIFIED** — side venv built (Python 3.12), model downloaded,
  `scripts/kitten_synth.py` synthesized a 24kHz mono WAV (jasper, ~155KB) via the CLI helper.
- sarvam: pre-existing path; key-gated. (Unprobed this pass.)

## NIM fallback brain (companion config, 2026-11-10)

`friday/nim_client.py` + `friday/nim_router.py` use the owner-approved chain only:
`nvidia/nemotron-3-ultra-550b-a55b` → `nvidia/nemotron-3.5-lightning-30b-a3b` →
`minimaxai/minimax-m3.1-flash` (best-effort, 2-minute budget) → `gemini-2.5-flash`
(→ `gemini-flash-lite-latest`). OpenCode Zen tier removed at owner's request.
`.env`'s `NVIDIA_NIM_MODEL` (`deepseek-ai/deepseek-v4-flash`) and `GEMINI_MODEL`
(`gemini-2.0-flash`) are stale and intentionally ignored by the code.
