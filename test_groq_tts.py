# -*- coding: utf-8 -*-
"""Groq Orpheus TTS Voice Tester — Female Voices"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

from groq import Groq
import subprocess

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# All 3 female voices with different sentence styles
tests = [
    # --- AUTUMN ---
    ("autumn", "Hello! I'm Autumn. This is my natural speaking voice with no special directions.", "01_autumn_natural"),
    ("autumn", "[cheerful] Good morning Boss! Systems are online and everything looks absolutely perfect today!", "02_autumn_cheerful"),
    ("autumn", "[whisper] Hey, I found something interesting in the logs. You might want to take a look at this.", "03_autumn_whisper"),
    ("autumn", "[confidently] Mission complete. All targets neutralized. Returning to base.", "04_autumn_confident"),

    # --- DIANA ---
    ("diana", "Hello! I'm Diana. This is my natural speaking voice with no special directions.", "05_diana_natural"),
    ("diana", "[professionally] Welcome to your daily briefing. Three critical tasks require your attention.", "06_diana_professional"),
    ("diana", "[excited] Oh my god, it actually worked! The build passed on the first try!", "07_diana_excited"),
    ("diana", "[warm] Don't worry about that error. I've already fixed it for you.", "08_diana_warm"),

    # --- HANNAH ---
    ("hannah", "Hello! I'm Hannah. This is my natural speaking voice with no special directions.", "09_hannah_natural"),
    ("hannah", "[sarcastic] Oh great, another syntax error. What a surprise.", "10_hannah_sarcastic"),
    ("hannah", "[dramatic] The server is down. I repeat, the server is down! All hands on deck!", "11_hannah_dramatic"),
    ("hannah", "[friendly] Hey there! I just finished setting everything up. Ready when you are!", "12_hannah_friendly"),
]

os.makedirs("tts_test", exist_ok=True)

for voice, text, filename in tests:
    print(f"🎤 Generating: {filename} ({voice})...")
    try:
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice=voice,
            input=text,
            response_format="wav"
        )
        path = f"tts_test/{filename}.wav"
        response.write_to_file(path)
        print(f"   ✅ Saved: {path}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n🎧 All done! Playing samples back-to-back...")

# Auto-play each file
import time
for voice, text, filename in tests:
    path = os.path.abspath(os.path.join("tts_test", f"{filename}.wav"))
    if os.path.exists(path):
        print(f"\n▶ [{voice.upper()}] {text[:80]}...")
        os.startfile(path)
        time.sleep(5)  # Wait between clips

print("\n✨ Test complete! Check the tts_test/ folder for all WAV files.")
