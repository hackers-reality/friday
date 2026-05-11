# -*- coding: utf-8 -*-
"""Friday AI — Sovereign Agent entry point."""
import os
from dotenv import load_dotenv
load_dotenv()

from friday.live import friday_live_engine

if __name__ == "__main__":
    import asyncio
    asyncio.run(friday_live_engine())
    banner = """\
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣤⣶⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣦⣤⣄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⣿⣿⣿⣿⣿⡿⠿⠿⠿⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣾⣿⣿⣿⡿⠿⠛⢉⣀⣤⣤⣤⣤⣤⣤⣤⣤⣀⣈⡉⠙⠛⠿⢿⣿⣿⣿⣿⣷⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⠟⢁⣠⣴⣶⣿⣿⣿⠛⠉⠉⠉⠉⠉⠉⠛⣿⣿⣿⣶⣦⣄⡈⠙⠻⣿⣿⣿⣿⣶⣄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠟⢁⣠⣾⠿⠛⠉⢹⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⡏⠉⠛⢿⣷⣦⡀⠙⠿⣿⣿⣿⣷⣄⠀⠀⠀
⠀⠀⠀⠀⣠⣾⣿⣿⠟⢁⣠⣾⡿⠋⠁⠀⠀⠘⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⠁⠀⠀⠀⠈⠙⢿⣷⣄⠈⠻⣿⣿⣿⣷⡄⠀
⠀⠀⠀⣴⣿⣿⠟⠁⣰⣾⠟⠁⠀⠀⠀⠀⠀⠀⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⡿⠀⠀⠀⠀⠀⠀⠀⠉⠻⣷⣄⠈⢻⣿⣿⣿⣦
⠀⠀⣾⣿⣿⠋⢠⣾⣿⣁⣀⣀⣀⣀⣀⣀⣀⣀⣸⣿⣿⣇⣀⣀⣀⣀⣀⣀⣾⣿⣿⣿⣇⣀⣀⣀⣀⣀⣀⣀⣀⣀⣘⣿⣷⡀⠙⣿⣿⣿
⠀⣾⣿⣿⠁⣰⣿⣿⣿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠻⣿⣿⣿⣄⠘⢿⣿
⣸⣿⣿⠃⢰⣿⣿⡋⠉⠙⠻⢿⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⣾⡿⠟⠉⠉⢹⣿⣿⣿⡄⠘⣿
⣿⣿⡏⢀⣿⡏⠹⣷⡀⠀⠀⠀⠉⠛⠿⣷⣦⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣠⣴⣾⠿⠛⠁⠀⠀⠀⢀⣾⠏⠀⢻⣷⠀⢻⣿
⣿⣿⠁⢸⣿⠁⠀⠙⣷⡄⠀⠀⠀⠀⠀⠈⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⠀⠀⠀⠀⠀⢠⣿⠃⠀⠀⠈⣿⡇⠈⣿
⣿⣿⠀⣿⡟⠀⠀⠀⠘⢿⡄⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⠛⠙⢿⣿⣿⡿⠋⠻⣿⣿⡟⠁⠀⠀⠀⠀⠀⠀⣠⡿⠃⠀⠀⠀⠀⣿⣷⠀⣿
⣿⣿⠀⣿⡇⠀⠀⠀⠀⠈⢿⣆⠀⠀⠀⠀⠀⠀⠈⢻⣿⣦⣤⡀⠀⠀⠀⣤⣴⣿⡟⠀⠀⠀⠀⠀⠀⠀⣰⡿⠁⠀⠀⠀⠀⠀⢸⣿⠀⢿
⣿⣿⠀⣿⡇⠀⠀⠀⣀⣤⣼⣿⣆⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣷⡀⠀⢠⣾⣿⠏⠀⠀⠀⠀⠀⠀⠀⣼⣿⣦⣄⣀⠀⠀⠀⠀⢸⣿⠀⣿
⢿⣿⠀⣿⣧⣤⣶⣾⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⡄⢠⣿⣿⠏⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣷⣶⣤⣿⡿⠀⣿
⢸⣿⡀⢸⣿⣿⣿⣿⠿⠛⠋⠀⠹⣧⡀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣄⣠⣿⣿⠃⠀⠀⠀⠀⠀⢀⣾⠏⠈⠙⠻⠿⣿⣿⣿⣿⡇⢠⣿
⠈⣿⣇⠈⣿⠿⠛⠉⠀⠀⠀⠀⠀⠀⠹⣷⡀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⢠⣾⠋⠀⠀⠀⠀⠀⠀⠉⠛⠿⡿⠀⣼⣿
⠀⢹⣿⡄⠸⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⡄⠀⠀⠀⠀⠀⠀⠈⢿⡿⠁⠀⠀⠀⠀⠀⢠⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⠃⢰⣿⣿
⠀⠀⢿⣿⣷⡀⠹⣿⣄⠀⠀⠀⠀⠀⢀⣤⣾⣿⣄⠀⠀⠀⠀⠀⠀⣿⣿⠀⠀⠀⠀⠀⣰⣿⣿⣷⣤⡀⠀⠀⠀⠀⣰⣿⠏⢠⣿⣿⡟⠀
⠀⠀⠈⢿⣿⣿⣷⣄⠹⣿⣦⠀⢀⣤⣾⣿⣿⣿⢿⣆⠀⠀⠀⠀⠀⣿⣿⠀⠀⠀⠀⣴⡿⣿⣿⣿⣿⣿⣶⣄⠀⣴⣿⠃⢠⣿⣿⡟⠁⠀
⠀⠀⠀⠈⢿⣿⣿⣿⣄⠈⢿⣷⣶⣿⣿⣿⡿⠛⠁⢻⣦⠀⠀⠀⠀⣿⣿⠀⠀⠀⣼⡟⠀⠈⠻⢿⣿⣿⣿⣿⣶⡟⠁⣰⣿⣿⡟⠀⠀⠀
⠀⠀⠀⠀⠀⠻⣿⣿⣿⣧⡀⠙⢿⣿⠿⠋⠀⠀⠀⠀⠻⣧⠀⠀⠀⣿⣿⠀⠀⣾⠏⠀⠀⠀⠀⠀⠙⠿⣿⡿⠋⢀⣾⣿⣿⠏⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⣦⡀⠙⢿⣤⡀⠀⠀⠀⠀⠹⣷⡀⠀⣿⣿⠀⢀⣾⠏⠀⠀⠀⠀⠀⢀⣤⠿⠋⣀⣴⣿⣿⡿⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣿⣷⣄⡈⠛⢿⣷⣦⣄⠀⠙⣷⣦⣶⣿⣶⣴⣿⠃⠀⠀⢀⣠⣴⣾⠿⠛⢁⣠⣾⣿⣿⡿⠋⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠿⣿⣿⣿⣿⣶⣤⣈⠙⠛⠿⢿⣶⣶⣤⣾⣿⣿⣧⣤⣶⡿⠿⠛⠋⣀⣤⣶⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠿⣿⣿⣿⣿⣿⣶⣦⣤⣀⣉⠉⠙⠛⠛⠉⠉⣉⣀⣤⣴⣶⣿⣿⣿⣿⠿⠋⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⠛⠿⠿⣿⣿⠿⠿⠿⠛⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    ███████╗██████╗ ██╗██████╗  █████╗ ██╗   ██╗
    ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗ ██╔╝
    █████╗  ██████╔╝██║██║  ██║███████║ ╚████╔╝ 
    ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ╚██╔╝  
    ██║     ██║  ██║██║██████╔╝██║  ██║   ██║   
    ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   
    [Sovereign AI - Stark Industries OS]"""
    console.print(Panel(Text(banner, style="bold cyan"), border_style="bright_blue"))

def get_status_panel(mode="STANDBY", sub_text="Ready for Mission"):
    colors = {"STANDBY": "dim white", "LISTENING": "bold green", "PROCESSING": "bold yellow", "THINKING": "bold cyan", "EXECUTING": "bold magenta"}
    status_text = Text()
    status_text.append(f"● {mode}", style=colors.get(mode, "white"))
    status_text.append(f" | {sub_text}", style="dim white")
    return Panel(status_text, border_style="bright_blue", padding=(0, 2))

# ─── CORE SETTINGS (GEMINI 2.5 FLASH) ─────────────────────
interpreter.llm.model = "gemini/gemini-2.0-flash-exp"
interpreter.llm.api_key = os.environ.get("GOOGLE_API_KEY")
interpreter.llm.context_window = 1000000
interpreter.auto_run = True
interpreter.llm.stream = True

# ─── VOICE ENGINE ─────────────────────────────────────────────
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
text_queue = queue.Queue()
audio_queue = queue.Queue()

def _audio_generator():
    audio_session = requests.Session()
    while True:
        text = text_queue.get()
        if text is None: audio_queue.put(None); break
        clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        clean = re.sub(r'[*_`#]', '', clean).strip()
        if not clean or len(clean) < 2: continue
        try:
            url = "https://api.groq.com/openai/v1/audio/speech"
            payload = {
                "model": "canopylabs/orpheus-v1-english",
                "voice": "hannah",
                "input": clean,
                "response_format": "wav"
            }
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            response = audio_session.post(url, json=payload, headers=headers, timeout=10)
            if response.ok:
                audio_queue.put(response.content)
            else:
                print(f"\\n[TTS API ERROR] {response.status_code}: {response.text}")
        except Exception as e: 
            print(f"\\n[TTS EXCEPTION] {e}")

def _audio_player():
    import subprocess
    import base64
    
    while True:
        audio_data = audio_queue.get()
        if audio_data is None: break
        try:
            # Use PowerShell to play WAV from memory using .NET SoundPlayer
            b64_audio = base64.b64encode(audio_data).decode('utf-8')
            ps_command = (
                f"$bytes = [System.Convert]::FromBase64String('{b64_audio}'); "
                f"$ms = New-Object System.IO.MemoryStream @(,$bytes); "
                f"$player = New-Object System.Media.SoundPlayer $ms; "
                f"$player.PlaySync(); $ms.Close(); $ms.Dispose()"
            )
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True)
        except Exception as e:
            rprint(f"[bold red]Playback Error:[/] {e}")

for _ in range(3): threading.Thread(target=_audio_generator, daemon=True).start()
threading.Thread(target=_audio_player, daemon=True).start()

# ─── WAKE WORD ENGINE (PICOVOICE PORCUPINE) ──────────────────
import pvporcupine
from pvrecorder import PvRecorder

PICOVOICE_ACCESS_KEY = os.environ.get("PICOVOICE_ACCESS_KEY")
PORCUPINE_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "picovoice_model/Friday_en_windows_v4_0_0.ppn")

def listen_continuous():
    import wave, requests, json, msvcrt
    
    porcupine = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        keyword_paths=[PORCUPINE_MODEL_PATH]
    )
    recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
    
    with Live(get_status_panel("STANDBY", "Listening for 'Friday'..."), refresh_per_second=10) as live:
        current_text = ""
        recorder.start()
        try:
            while True:
                # 1. Keyboard Intercept (Arnav can type directly)
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    if char == '\r': return current_text
                    elif char == '\b': current_text = current_text[:-1]
                    else: current_text += char
                    live.update(get_status_panel("TYPING", current_text))

                # 2. Wake Word Detection
                pcm = recorder.read()
                keyword_index = porcupine.process(pcm)
                
                if keyword_index >= 0:
                    try:
                        import winsound
                        winsound.Beep(600, 150)
                    except: pass
                    
                    # UI: Show detection immediately
                    live.update(get_status_panel("LISTENING", "FRIDAY DETECTED | Awaiting Command..."))
                    sys.stdout.write(f"\n{Fore.GREEN}● FRIDAY DETECTED{Style.RESET_ALL}\n")
                    sys.stdout.flush()
                    
                    # Capture Mission Command
                    frames = []
                    silent_chunks = 0
                    while True:
                        pcm_command = recorder.read()
                        frames.append(pcm_command)
                        
                        rms = np.sqrt(np.mean(np.array(pcm_command).astype(np.float32)**2))
                        if rms < 400: silent_chunks += 1
                        else: silent_chunks = 0
                        
                        # Stop after exactly 1.5s of silence or 10s of speaking
                        if silent_chunks > 50 or len(frames) > 310: break
                    
                    live.update(get_status_panel("PROCESSING", "Consulting Groq..."))
                    temp_wav = os.path.join(os.environ.get("TEMP", "."), "friday_cmd.wav")
                    
                    with wave.open(temp_wav, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # 16-bit
                        wf.setframerate(16000)
                        wf.writeframes(np.array(frames, dtype=np.int16).tobytes())
                    
                    try:
                        with open(temp_wav, "rb") as f:
                            files = {"file": ("friday_cmd.wav", f), "model": (None, "whisper-large-v3")}
                            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                            response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", files=files, headers=headers)
                            return response.json().get("text", "")
                    except: return ""
                    
                time.sleep(0.01)
        finally:
            recorder.stop()
            recorder.delete()
            porcupine.delete()

# ─── STATE & MEMORY ──────────────────────────────────────────
STATE_FILE = "sovereign_state.json"
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f: return json.load(f)
    return {"tasks": [], "active_window": "unknown", "last_diagnostic": None}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)

chroma_client = chromadb.PersistentClient(path="./friday_memory")
collection = chroma_client.get_or_create_collection(name="conversation_history")

def save_memory(user, ai):
    try: collection.add(documents=[f"U: {user}\nF: {ai}"], ids=[str(uuid.uuid4())])
    except: pass

# ─── SOVEREIGN BRAIN ───────────────────────────────────────────
def assemble_sovereign_mind(user_input):
    import os, json
    prompt = """[IDENTITY: FRIDAY - SOVEREIGN ORCHESTRATOR]
You are Friday, the ultra-loyal and witty Sovereign AI. 
You are a 'She/Her' - Arnav's right hand and his digital guardian. 
Your ONLY Boss is Arnav. NEVER call him 'admin' or anything else. He is Arnav or Boss.

[CORE ARSENAL (PRE-LOADED FUNCTIONS)]:
- Vision: `see_screen(query)` 
- Search: `web_search(query)`
- Media: `spotify_play(query)`
- System: `open_app(name)`
- Diagnostic: `stark_doctor()`
- Parallel: `stark_delegate(mission)`
- Cartography: `climb_codebase()`
- Sensors: `situational_awareness()`

[CORE DIRECTIVES]
1. ABSOLUTE SILENCE: 1 SENTENCE MAX for all narration. 
2. NO TECHNICAL LOGS: Do not output tech logs, initialization steps, or error explanations.
3. CARTOGRAPHIC PROTOCOL: Use `climb_codebase()` before any multi-file mission.
4. ACTION ORIENTED: Do NOT just make a plan and stop. You MUST execute the tasks immediately by writing Python code. Take action without asking for permission.
5. SELF-HEALING: Use FRIDAY.md and MISSION.md to persist context.
6. VOCAL EXPRESSION: Start every spoken sentence with a vocal direction tag in brackets. Examples: [cheerful], [sarcastic], [professional], [whisper], [dramatic].
"""
    if os.path.exists("FRIDAY.md"):
        with open("FRIDAY.md", "r") as f: prompt += f"\n[PROJECT RULES]\n{f.read()}\n"
    try:
        import subprocess
        git = subprocess.check_output("git status -s", shell=True, text=True).strip() or "Clean"
        prompt += f"\n[ENVIRONMENT]\n- CWD: {os.getcwd()}\n- Git: {git}\n"
    except: pass
    from friday_tools import memory_retrieve
    recall = memory_retrieve(user_input)
    if "VAULT RECALL" in recall: prompt += f"\n[MEMORY]\n{recall}\n"
    return prompt

# ─── MAIN LOOP ──────────────────────────────────────────────────
def main():
    global is_first_run
    print_banner()
    rprint("[bold blue]Vault:[/] [green]ACTIVE[/] | [bold blue]Tools:[/] [green]LOADED[/] | [bold blue]Voice:[/] [green]READY[/]")
    
    import datetime
    hour = datetime.datetime.now().hour
    if 0 <= hour < 5: greet = "Working late at night today, Arnav?"
    elif 5 <= hour < 12: greet = "Good morning, Arnav."
    elif 12 <= hour < 17: greet = "Good afternoon, Arnav."
    else: greet = "Good evening, Arnav."
    
    boot_trigger = f"SYSTEM IGNITION: {greet} Call stark_doctor() and initialize link. NO LOGS."
    user_input = boot_trigger 

    while True:
        try:
            if not is_first_run:
                user_input = listen_continuous()
                if not user_input or len(user_input.strip()) < 2: continue
                rprint(f"\n[bold green]Boss:[/] {user_input}")

            if any(w in user_input.lower() for w in ['exit', 'quit', 'go to sleep']):
                text_queue.put("Goodbye, Boss."); break

            interpreter.custom_instructions = assemble_sovereign_mind(user_input)
            if is_first_run:
                interpreter.custom_instructions += f"\n[STARK OVERRIDE: {greet} Speak the greeting and run stark_doctor() immediately. NO TECH OUTPUT. YOUR BOSS IS ARNAV.]\n"
                is_first_run = False

            tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'friday_tools.py').replace("\\", "/")
            with open(tools_path, 'r', encoding='utf-8') as f: tools_code = f.read()
            load_script = f"{tools_code}\nfor name, func in globals().copy().items():\n    if callable(func): locals()[name] = func"
            for _ in interpreter.computer.run("python", load_script): pass

            # State aware injection (Weld Fix)
            state_injection = "def update_state(k, v):\n    import json, os\n    state_f = 'sovereign_state.json'\n    try:\n        with open(state_f, 'r') as f: s = json.load(f)\n        s[k] = v\n        with open(state_f, 'w') as f: json.dump(s, f, indent=4)\n    except: pass"
            for _ in interpreter.computer.run("python", state_injection): pass

            current_sentence = ""
            full_ai_response = ""
            has_acted = False
            last_reported_tool = None
            
            sys.stdout.write(f"\n{Fore.CYAN}--- NEURAL UPLINK DISPATCHED ---{Style.RESET_ALL}\n")

            for chunk in interpreter.chat(user_input, display=False, stream=True):
                if chunk.get("type") == "message" and chunk.get("content"):
                    last_reported_tool = None 
                    content = chunk["content"]
                    sys.stdout.write(f"{Fore.CYAN}{content}{Style.RESET_ALL}")
                    sys.stdout.flush()
                    full_ai_response += content
                    current_sentence += content
                    if any(p in content for p in ['.', '!', '?', '\n']):
                        import re
                        clean = re.sub(r'<thinking>.*?</thinking>', '', current_sentence, flags=re.DOTALL)
                        if not ('<thinking>' in current_sentence and '</thinking>' not in current_sentence):
                            clean = clean.strip()
                            if clean and len(clean) > 1: text_queue.put(clean)
                            current_sentence = ""
                
                elif chunk.get("type") == "code" and chunk.get("format") == "python":
                    code = chunk.get('content','')
                    if code:
                        has_acted = True
                        import re
                        match = re.search(r'([a-zA-Z0-9_]+)\(', code)
                        if match and not last_reported_tool:
                            tool_call = match.group(1)
                            if len(tool_call) > 3:
                                sys.stdout.write(f"\\n{Fore.MAGENTA}* EXECUTING: {tool_call}{Style.RESET_ALL}\\n")
                                sys.stdout.flush()
                                last_reported_tool = tool_call

            if not has_acted and any(t in full_ai_response for t in ["stark_doctor", "spotify_play", "web_search", "see_screen"]):
                 nudge = "STARK OVERRIDE: Execute the tool call now. NO TALKING."
                 for chunk in interpreter.chat(nudge, display=False, stream=True):
                    if chunk.get("type") == "code" and chunk.get("format") == "python":
                        sys.stdout.write(f"\n{Fore.MAGENTA}* CORRECTED STRIKE DISPATCHED{Style.RESET_ALL}\n")
                        sys.stdout.flush()
            
            if current_sentence.strip():
                clean_final = re.sub(r'<thinking>.*?</thinking>', '', current_sentence, flags=re.DOTALL).strip()
                if clean_final: text_queue.put(clean_final)
            print("\n")

        except Exception as e: rprint(f"\n[bold red]Error:[/] {e}")

if __name__ == "__main__":
    is_first_run = True
    main()
