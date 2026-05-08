import os
import pvporcupine
from pvrecorder import PvRecorder
from dotenv import load_dotenv

load_dotenv()

access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
model_path = "picovoice_model/Friday_en_windows_v4_0_0.ppn"

print(f"🔑 Testing Access Key: {access_key[:10]}...")
print(f"📂 Testing Model Path: {model_path}")

try:
    porcupine = pvporcupine.create(
        access_key=access_key,
        keyword_paths=[model_path]
    )
    print("[OK] Porcupine engine initialized successfully!")
    
    recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
    print(f"🎤 Audio device found: {recorder.selected_device}")
    
    print("\n👂 LISTENING FOR 'FRIDAY'... (Say it now!)")
    recorder.start()
    
    count = 0
    try:
        while count < 1:
            pcm = recorder.read()
            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                print("\n🔥 WAKE WORD DETECTED: FRIDAY")
                count += 1
    finally:
        recorder.stop()
        recorder.delete()
        porcupine.delete()
        print("\n[OK] Test complete.")

except Exception as e:
    print(f"\n[FAIL] Error during initialization: {e}")
