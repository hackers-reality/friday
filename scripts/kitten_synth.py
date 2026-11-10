"""KittenTTS synthesis helper — runs inside the Python 3.12 side venv (.venv-kitten).

KittenTTS (Apache-2.0, https://github.com/KittenML/kitten-tts-nano-0.8-fp32)
requires Python <3.13; FRIDAY's main venv is 3.13, so synthesis runs in a
dedicated side venv and exchanges audio via a WAV file.

Usage:
    <venv-kitten>/python scripts/kitten_synth.py --voice Jasper --out out.wav
Reads JSON {"text": "..."} from stdin. Prints one JSON line:
    {"ok": true, "path": "...", "sample_rate": 24000, "bytes": N}
    {"ok": false, "error": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys

MODEL_ID = "KittenML/kitten-tts-nano-0.8-fp32"
VALID_VOICES = ("Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="Jasper")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=MODEL_ID)
    args = parser.parse_args()

    voice = args.voice if args.voice in VALID_VOICES else "Jasper"
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "error": "invalid JSON on stdin"}))
        return 1
    text = (payload or {}).get("text") or ""
    if not text.strip():
        print(json.dumps({"ok": False, "error": "empty text"}))
        return 1
    try:
        from kittentts import KittenTTS
        import soundfile as sf
        model = KittenTTS(args.model)
        audio = model.generate(text, voice=voice)
        sf.write(args.out, audio, 24000)
        import os
        print(json.dumps({"ok": True, "path": args.out, "sample_rate": 24000,
                          "bytes": os.path.getsize(args.out), "voice": voice}))
        return 0
    except Exception as e:  # noqa: BLE001 — report any synth failure as JSON
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
