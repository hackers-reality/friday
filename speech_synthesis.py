"""
Friday Speech Synthesis - TTS engines and voice cloning.
Multiple TTS engines, voice management, SSML support.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import random
import time


# ─── Voice Profile ────────────────────────────#

class VoiceProfile:
    """Represents a voice profile."""
    
    def __init__(
        self,
        voice_id: str,
        name: str,
        language: str = "en-US",
        gender: str = "neutral",  # male, female, neutral
        pitch: float = 0.0,  # -20.0 to 20.0
        speed: float = 1.0,  # 0.25 to 4.0
        provider: str = "system",  # system, gtts, edge, elevenlabs
    ):
        self.voice_id = voice_id
        self.name = name
        self.language = language
        self.gender = gender
        self.pitch = pitch
        self.speed = speed
        self.provider = provider
        self.cloned_from: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender,
            "pitch": self.pitch,
            "speed": self.speed,
            "provider": self.provider,
            "cloned_from": self.cloned_from,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceProfile':
        profile = cls(
            data["voice_id"],
            data["name"],
            data.get("language", "en-US"),
            data.get("gender", "neutral"),
            data.get("pitch", 0.0),
            data.get("speed", 1.0),
            data.get("provider", "system"),
        )
        profile.cloned_from = data.get("cloned_from")
        return profile


# ─── TTS Engine (Base) ────────────────────────────#

class TTSEngine:
    """Base class for TTS engines."""
    
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.available = self._check_available()
        
    def _check_available(self) -> bool:
        """Check if engine is available."""
        return True  # Override in subclasses
        
    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: str,
    ) -> str:
        """
        Synthesize speech from text.
        Returns path to generated audio file.
        """
        raise NotImplementedError
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """Get list of available voices."""
        return []
    
    def clone_voice(self, audio_samples: List[str], new_voice_id: str) -> VoiceProfile:
        """Clone a voice from audio samples."""
        raise NotImplementedError


# ─── System TTS (Simplified - Windows SAPI) ────────────────────────────#

class SystemTTSEngine(TTSEngine):
    """Uses system TTS (Windows SAPI via PowerShell)."""
    
    def __init__(self):
        super().__init__("system")
        
    def _check_available(self) -> bool:
        """Check if Windows SAPI is available."""
        return os.name == "nt"  # Windows
        
    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: str,
    ) -> str:
        """Use Windows SAPI via PowerShell."""
        if not self.available:
            return "❌ System TTS not available (Windows only)."
        
        # Escape quotes in text
        safe_text = text.replace("'", "''")
        
        # PowerShell command
        ps_command = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.SetOutputToWaveFile('{output_path}')
        $synth.Speak('{safe_text}')
        """
        
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return f"✅ Audio saved: {output_path}"
            return f"❌ TTS error: {result.stderr.decode()}"
            
        except Exception as e:
            return f"❌ TTS error: {e}"
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """Get installed voices (simplified)."""
        voices = [
            VoiceProfile("en-US-Male", "Microsoft David", "en-US", "male"),
            VoiceProfile("en-US-Female", "Microsoft Zira", "en-US", "female"),
        ]
        return voices


# ─── GTTSEngine (Google Text-to-Speech) ────────────────────────────#

class GTTSEngine(TTSEngine):
    """Google TTS engine."""
    
    def __init__(self):
        super().__init__("gtts")
        self.available = self._check_available()
        
    def _check_available(self) -> bool:
        try:
            import gtts
            return True
        except ImportError:
            return False
        
    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: str,
    ) -> str:
        """Use gTTS for synthesis."""
        if not self.available:
            return "❌ gTTS not installed. Run: pip install gtts"
        
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            import tempfile
            
            # Generate with gTTS
            tts = gTTS(text=text, lang=voice.language[:2])  # Use base language code
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            
            tts.save(temp_path)
            
            # Convert to WAV if needed
            if output_path.endswith(".wav"):
                audio = AudioSegment.from_mp3(temp_path)
                audio.export(output_path, format="wav")
                os.unlink(temp_path)
            else:
                import shutil
                shutil.move(temp_path, output_path)
            
            return f"✅ Audio saved: {output_path}"
            
        except Exception as e:
            return f"❌ gTTS error: {e}"
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """gTTS doesn't have voice selection."""
        return [
            VoiceProfile("default", "gTTS Default", voice.language, "neutral"),
        ]


# ─── Edge TTS (Microsoft Edge) ────────────────────────────#

class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTS engine."""
    
    def __init__(self):
        super().__init__("edge")
        self.available = self._check_available()
        
    def _check_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False
        
    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        output_path: str,
    ) -> str:
        """Use edge-tts for synthesis."""
        if not self.available:
            return "❌ edge-tts not installed. Run: pip install edge-tts"
        
        try:
            import edge_tts
            import asyncio
            
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice.voice_id)
                await communicate.save(output_path)
            
            asyncio.run(_synthesize())
            return f"✅ Audio saved: {output_path}"
            
        except Exception as e:
            return f"❌ Edge TTS error: {e}"
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """Get Edge TTS voices (simplified)."""
        try:
            import edge_tts
            # In reality, would call edge_tts.list_voices()
            voices = [
                VoiceProfile("en-US-ChristopherNeural", "Christopher", "en-US", "male"),
                VoiceProfile("en-US-JennyNeural", "Jenny", "en-US", "female"),
            ]
            return voices
        except:
            return []


# ─── Multi-Engine TTS Manager ────────────────────────────#

class TTSManager:
    """Manages multiple TTS engines."""
    
    def __init__(self):
        self.engines: Dict[str, TTSEngine] = {}
        self.active_engine: Optional[str] = None
        self.voices: Dict[str, VoiceProfile] = {}
        self._init_engines()
        
    def _init_engines(self):
        """Initialize available engines."""
        # System TTS
        sys_engine = SystemTTSEngine()
        if sys_engine.available:
            self.engines["system"] = sys_engine
            self.active_engine = "system"
        
        # gTTS
        gtts_engine = GTTSEngine()
        if gtts_engine.available:
            self.engines["gtts"] = gtts_engine
            if not self.active_engine:
                self.active_engine = "gtts"
        
        # Edge TTS
        edge_engine = EdgeTTSEngine()
        if edge_engine.available:
            self.engines["edge"] = edge_engine
            if not self.active_engine:
                self.active_engine = "edge"
        
        # Load voices
        self._load_voices()
        
    def _load_voices(self):
        """Load all available voices."""
        for engine in self.engines.values():
            for voice in engine.get_available_voices():
                self.voices[voice.voice_id] = voice
        
    def synthesize(
        self,
        text: str,
        voice_id: str = None,
        output_path: str = None,
        engine_name: str = None,
    ) -> str:
        """Synthesize speech using specified or active engine."""
        # Choose engine
        if engine_name and engine_name in self.engines:
            engine = self.engines[engine_name]
        elif self.active_engine:
            engine = self.engines[self.active_engine]
        else:
            return "❌ No TTS engine available."
        
        # Choose voice
        voice = self.voices.get(voice_id) if voice_id else None
        if not voice:
            # Use default voice for engine
            voices = engine.get_available_voices()
            voice = voices[0] if voices else None
        
        if not voice:
            return "❌ No voices available."
        
        # Generate output path
        if not output_path:
            import tempfile
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"tts_output_{int(time.time())}.wav")
        
        return engine.synthesize(text, voice, output_path)
    
    def list_engines(self) -> str:
        """List available TTS engines."""
        lines = ["### TTS ENGINES", ""]
        for name, engine in self.engines.items():
            icon = "✅" if name == self.active_engine else "⚙"
            lines.append(f"{icon} {name}")
        return "\n".join(lines)
    
    def list_voices(self) -> str:
        """List all available voices."""
        lines = ["### AVAILABLE VOICES", ""]
        by_lang = {}
        for voice in self.voices.values():
            lang = voice.language
            if lang not in by_lang:
                by_lang[lang] = []
            by_lang[lang].append(voice)
        
        for lang, voices in sorted(by_lang.items()):
            lines.append(f"**{lang}**")
            for v in voices:
                lines.append(f"  - {v.name} ({v.gender}) [{v.voice_id}]")
            lines.append("")
        
        return "\n".join(lines)
    
    def clone_voice(
        self,
        audio_samples: List[str],
        new_voice_id: str,
        new_name: str,
    ) -> str:
        """Clone a voice (simplified)."""
        if not audio_samples:
            return "❌ Audio samples required."
        
        # Simplified: just create a profile
        cloned = VoiceProfile(
            new_voice_id,
            new_name,
            "en-US",
            "cloned",
        )
        cloned.cloned_from = audio_samples[0]
        self.voices[new_voice_id] = cloned
        
        return f"✅ Voice cloned: {new_name} (simplified)"
    
    def save_voices(self, path: str):
        """Save voices to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self.voices.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load_voices(self, path: str):
        """Load voices from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for vid, vdata in data.items():
                self.voices[vid] = VoiceProfile.from_dict(vdata)
        except FileNotFoundError:
            pass


# ─── Singleton Manager ────────────────────────────#

_manager: Optional[TTSManager] = None

def get_tts_manager() -> TTSManager:
    """Get or create TTS manager."""
    global _manager
    if _manager is None:
        _manager = TTSManager()
    return _manager


# ─── Tool Function for Friday ────────────────────────────#

def tts_tool(
    action: str = "status",
    text: str = None,
    voice_id: str = None,
    output_path: str = None,
    engine: str = None,
) -> str:
    """
    Friday tool for speech synthesis.
    Actions: status, synthesize, list_engines, list_voices, clone_voice
    """
    manager = get_tts_manager()
    
    if action == "status":
        lines = ["### TTS STATUS", ""]
        lines.append(f"**Active Engine**: {manager.active_engine or 'None'}")
        lines.append(f"**Available Engines**: {len(manager.engines)}")
        lines.append(f"**Available Voices**: {len(manager.voices)}")
        return "\n".join(lines)
    
    if action == "synthesize":
        if not text:
            return "❌ Text required for synthesis."
        
        result = manager.synthesize(text, voice_id, output_path, engine)
        return result
    
    if action == "list_engines":
        return manager.list_engines()
    
    if action == "list_voices":
        return manager.list_voices()
    
    if action == "clone_voice":
        if not text or not voice_id:  # Reuse text param for audio_samples JSON
            return "❌ voice_id and audio_samples (in text param as JSON) required."
        
        try:
            samples = json.loads(text)
        except:
            return "❌ audio_samples must be JSON array."
        
        return manager.clone_voice(samples, voice_id, output_path or "cloned_voice")
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Speech Synthesis...\n")
    
    manager = get_tts_manager()
    
    print("--- TTS Status ---")
    print(tts_tool("status"))
    
    print("\n--- Available Engines ---")
    print(tts_tool("list_engines"))
    
    print("\n--- Synthesize (if engine available) ---")
    if manager.active_engine:
        print(tts_tool("synthesize", text="Hello, I am Friday, your AI assistant."))
    else:
        print("No TTS engine available.")
