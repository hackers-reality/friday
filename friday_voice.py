"""
Friday Voice - Speech recognition and text-to-speech.
Wake word detection, voice commands, TTS output.
"""
from __future__ import annotations__

import os
import sys
import json
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import tempfile
import wave


# ─── Speech-to-Text (STT) ────────────────────────────#

class SpeechToText:
    """Speech recognition using available libraries."""
    
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self.available = False
        self._initialize()
        
    def _initialize(self):
        """Initialize speech recognition."""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.available = True
        except ImportError:
            try:
                # Try alternative: use system SAPI (Windows)
                import win32com.client
                self.available = False  # STT not available, but TTS might work
            except ImportError:
                self.available = False
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> Dict[str, Any]:
        """Listen for speech and convert to text."""
        if not self.available:
            return {
                "success": False,
                "text": None,
                "error": "Speech recognition not available. Install: pip install SpeechRecognition pyaudio",
            }
        
        try:
            import speech_recognition as sr
            
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            
            # Recognize using Google (free)
            text = self.recognizer.recognize_google(audio)
            
            return {
                "success": True,
                "text": text,
                "error": None,
            }
            
        except Exception as e:
            return {
                "success": False,
                "text": None,
                "error": str(e),
            }
    
    def listen_from_file(self, audio_file: str) -> Dict[str, Any]:
        """Recognize speech from audio file."""
        if not self.available:
            return {
                "success": False,
                "text": None,
                "error": "Speech recognition not available.",
            }
        
        try:
            import speech_recognition as sr
            
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(audio)
            
            return {
                "success": True,
                "text": text,
                "error": None,
            }
            
        except Exception as e:
            return {
                "success": False,
                "text": None,
                "error": str(e),
            }


# ─── Text-to-Speech (TTS) ────────────────────────────#

class TextToSpeech:
    """Text-to-speech synthesis."""
    
    def __init__(self):
        self.engine = None
        self.available = False
        self.voice_id = None
        self._initialize()
        
    def _initialize(self):
        """Initialize TTS engine."""
        # Try pyttsx3 (offline)
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.available = True
            
            # Set properties
            self.engine.setProperty("rate", 180)  # Speed
            self.engine.setProperty("volume", 0.9)  # Volume
            
            # Get available voices
            voices = self.engine.getProperty("voices")
            if voices:
                # Try to find a good voice
                for voice in voices:
                    if "female" in voice.name.lower() or "zira" in voice.name.lower():
                        self.engine.setProperty("voice", voice.id)
                        break
        except ImportError:
            # Try gTTS (online)
            try:
                from gtts import gTTS
                self.gtts_available = True
                self.available = True  # gTTS works differently
            except ImportError:
                self.available = False
    
    def speak(self, text: str, block: bool = True) -> Dict[str, Any]:
        """Speak text."""
        if not self.available:
            return {
                "success": False,
                "error": "TTS not available. Install: pip install pyttsx3 or gtts",
            }
        
        try:
            # Try pyttsx3
            if hasattr(self, "engine") and self.engine:
                self.engine.say(text)
                if block:
                    self.engine.runAndWait()
                else:
                    threading.Thread(target=self.engine.runAndWait, daemon=True).start()
                
                return {
                    "success": True,
                    "method": "pyttsx3",
                    "error": None,
                }
            
            # Try gTTS
            elif hasattr(self, "gtts_available"):
                from gtts import gTTS
                import tempfile
                import os
                
                tts = gTTS(text=text, lang="en")
                temp_file = tempfile.mktemp(suffix=".mp3")
                tts.save(temp_file)
                
                # Play using system player
                os.system(f"start {temp_file}" if os.name == "nt" else f"mpg123 {temp_file}")
                
                return {
                    "success": True,
                    "method": "gtts",
                    "file": temp_file,
                    "error": None,
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def save_to_file(self, text: str, output_file: str) -> Dict[str, Any]:
        """Save speech to audio file."""
        if not self.available:
            return {
                "success": False,
                "error": "TTS not available.",
            }
        
        try:
            if hasattr(self, "engine") and self.engine:
                self.engine.save_to_file(text, output_file)
                self.engine.runAndWait()
                
                return {
                    "success": True,
                    "file": output_file,
                    "error": None,
                }
            
            elif hasattr(self, "gtts_available"):
                from gtts import gTTS
                tts = gTTS(text=text, lang="en")
                tts.save(output_file)
                
                return {
                    "success": True,
                    "file": output_file,
                    "error": None,
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def set_voice(self, voice_name: str) -> bool:
        """Set voice by name."""
        if not hasattr(self, "engine") or not self.engine:
            return False
        
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if voice_name.lower() in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                return True
        return False
    
    def set_rate(self, rate: int):
        """Set speech rate (words per minute)."""
        if hasattr(self, "engine") and self.engine:
            self.engine.setProperty("rate", rate)
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        if hasattr(self, "engine") and self.engine:
            self.engine.setProperty("volume", max(0.0, min(1.0, volume)))


# ─── Wake Word Detection ────────────────────────────#

class WakeWordDetector:
    """Detect wake word (e.g., 'Hey Friday')."""
    
    def __init__(self, wake_word: str = "hey friday"):
        self.wake_word = wake_word.lower()
        self.stt = SpeechToText()
        self.listening = False
        self.callback: Optional[Callable] = None
        
    def start_listening(self, callback: Callable = None):
        """Start listening for wake word."""
        self.callback = callback
        self.listening = True
        
        def listen_loop():
            while self.listening:
                result = self.stt.listen(timeout=2, phrase_time_limit=5)
                
                if result["success"] and result["text"]:
                    text = result["text"].lower()
                    if self.wake_word in text:
                        if self.callback:
                            self.callback()
                        else:
                            print("🎤 Wake word detected!")
                
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()
    
    def stop_listening(self):
        """Stop listening for wake word."""
        self.listening = False


# ─── Voice Command Processor ────────────────────────────#

class VoiceCommandProcessor:
    """Process voice commands."""
    
    def __init__(self):
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.wake_detector = WakeWordDetector()
        
    def listen_for_command(self) -> Dict[str, Any]:
        """Listen for a voice command."""
        # Listen
        result = self.stt.listen()
        
        if not result["success"]:
            return {
                "success": False,
                "command": None,
                "error": result["error"],
            }
        
        command = result["text"]
        
        return {
            "success": True,
            "command": command,
            "error": None,
        }
    
    def speak_response(self, text: str):
        """Speak a response."""
        self.tts.speak(text)
    
    def process_voice_command(self, friday_core=None) -> Dict[str, Any]:
        """Listen, process, and respond to voice command."""
        # Listen
        listen_result = self.listen_for_command()
        
        if not listen_result["success"]:
            return listen_result
        
        command = listen_result["command"]
        
        # Process with Friday Core if available
        if friday_core:
            response = friday_core.process_command(command)
        else:
            response = f"Command received: {command}"
        
        # Speak response
        # Simplify response for speech
        speech_text = self._simplify_for_speech(response)
        self.speak_response(speech_text)
        
        return {
            "success": True,
            "command": command,
            "response": response,
            "error": None,
        }
    
    def _simplify_for_speech(self, text: str) -> str:
        """Simplify text for speech output."""
        # Remove markdown
        import re
        text = re.sub(r'[#*`]', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove links
        
        # Limit length
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text


# ─── Friday Voice Tool ────────────────────────────#

def voice_tool(
    action: str = "status",
    text: str = None,
    wake_word: str = "hey friday",
    rate: int = None,
    volume: float = None,
) -> str:
    """
    Friday tool for voice operations.
    Actions: status, speak, listen, save, wake_start, wake_stop, set_voice
    """
    if action == "status":
        stt = SpeechToText()
        tts = TextToSpeech()
        
        lines = ["### VOICE STATUS", ""]
        lines.append(f"**Speech-to-Text**: {'✅ Available' if stt.available else '❌ Not available'}")
        lines.append(f"**Text-to-Speech**: {'✅ Available' if tts.available else '❌ Not available'}")
        
        if tts.available and hasattr(tts, "engine") and tts.engine:
            voices = tts.engine.getProperty("voices")
            lines.append(f"**Available Voices**: {len(voices) if voices else 0}")
            rate = tts.engine.getProperty("rate")
            vol = tts.engine.getProperty("volume")
            lines.append(f"**Rate**: {rate} wpm")
            lines.append(f"**Volume**: {vol}")
        
        return "\n".join(lines)
    
    if action == "speak":
        if not text:
            return "❌ Text required for speech."
        tts = TextToSpeech()
        result = tts.speak(text)
        return f"### SPEAK\n\n{'✅ Spoke text' if result['success'] else f'❌ {result[\"error\"]}'}"
    
    if action == "listen":
        stt = SpeechToText()
        result = stt.listen()
        if result["success"]:
            return f"### LISTEN\n\n**Heard**: {result['text']}"
        else:
            return f"❌ Listen error: {result['error']}"
    
    if action == "save":
        if not text:
            return "❌ Text required."
        tts = TextToSpeech()
        output_file = f"friday_speech_{int(time.time())}.mp3"
        result = tts.save_to_file(text, output_file)
        if result["success"]:
            return f"### SAVE\n\n✅ Saved to {result['file']}"
        else:
            return f"❌ Save error: {result['error']}"
    
    if action == "wake_start":
        detector = WakeWordDetector(wake_word)
        detector.start_listening()
        return f"### WAKE WORD\n\n🎤 Listening for '{wake_word}'..."
    
    if action == "wake_stop":
        detector = WakeWordDetector(wake_word)
        detector.stop_listening()
        return "### WAKE WORD\n\n⏹ Stopped listening."
    
    if action == "set_voice":
        if not text:
            return "❌ Voice name required."
        tts = TextToSpeech()
        success = tts.set_voice(text)
        return f"### SET VOICE\n\n{'✅ Voice set' if success else '❌ Voice not found'}"
    
    if action == "set_rate" and rate is not None:
        tts = TextToSpeech()
        tts.set_rate(rate)
        return f"### SET RATE\n\n✅ Rate set to {rate} wpm"
    
    if action == "set_volume" and volume is not None:
        tts = TextToSpeech()
        tts.set_volume(volume)
        return f"### SET VOLUME\n\n✅ Volume set to {volume}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Voice...\n")
    
    # Test TTS
    print("--- Text-to-Speech ---")
    print(voice_tool("status"))
    
    # Test STT (if available)
    print("\n--- Speech-to-Text ---")
    print("Say something...")
    result = voice_tool("listen")
    print(result)
