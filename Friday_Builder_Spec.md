# Friday Builder Technical Specification & Implementation Blueprint

> **Primary Engine**: Gemini 3.1 Flash Live Preview API (bidirectional streaming, native STT/TTS)
> **Reference Architecture**: [Jarvis Repository](https://github.com/vierisid/jarvis) (desktop AI patterns)
> **Voice Wake Word**: Porcupine ("Friday" - not "Hey Friday")
> **Screen Capture**: PIL ImageGrab (no webcam)
> **Language Policy**: English-only responses; reject Hindi/Hinglish

---

## Table of Contents
1. [System Architecture Diagram](#1-system-architecture-diagram)
2. [Data Flow Specification](#2-data-flow-specification)
3. [API Integration List](#3-api-integration-list)
4. [URI Scheme Reference & Natural Language Mapping](#4-uri-scheme-reference--natural-language-mapping)
5. [Database Schema for Memory & Vault Layer](#5-database-schema-for-memory--vault-layer)
6. [UI/Dashboard Design Specification](#6-uidashboard-design-specification)
7. [Command Parser Logic & Natural Language Intent Recognition](#7-command-parser-logic--natural-language-intent-recognition)
8. [Permission & Risk Assessment Matrix](#8-permission--risk-assessment-matrix)
9. [Real-Time Progress Feedback & Streaming Architecture](#9-real-time-progress-feedback--streaming-architecture)
10. [Notification System](#10-notification-system)
11. [Voice Interface Architecture](#11-voice-interface-architecture)
12. [Screen Capture & Visual Analysis](#12-screen-capture--visual-analysis)
13. [Background Task Scheduler & Autonomous Operation](#13-background-task-scheduler--autonomous-operation)
14. [Keyboard & Mouse Automation System](#14-keyboard--mouse-automation-system)
15. [Multi-LLM Orchestration](#15-multi-llm-orchestration)
16. [Implementation Roadmap](#16-implementation-roadmap)
17. [Configuration Template](#17-configuration-template)
18. [Special Technical Considerations](#18-special-technical-considerations)
19. [Core Operating Principles](#19-core-operating-principles)
20. [Appendix: User Requirement Mapping](#20-appendix-user-requirement-mapping)
21. [Ethical Decision Engine & Safety Framework](#21-ethical-decision-engine--safety-framework)
22. [Behavioral Prediction & Adaptive Permission System](#22-behavioral-prediction--adaptive-permission-system)
23. [Adaptive Behavioral Prediction Engine](#23-adaptive-behavioral-prediction-engine)

---

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRIDAY DESKTOP AGENT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────── VOICE INTERFACE ─────────────────────────────┐   │
│  │  Porcupine Wake Word → Gemini 3.1 Flash Live (Native STT/TTS)       │   │
│  │  Bidirectional Streaming (Sub-500ms Latency)                        │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── CENTRAL REASONING ───────────────────────────┐   │
│  │  Gemini 3.1 Flash Live (Primary)                                   │   │
│  │  ↓ Fallback: Claude, ChatGPT, Local Models                         │   │
│  │  Intent Parsing → Context Retrieval → Action Selection             │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── ACTION LAYER ───────────────────────────────┐   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │ URI Schemes │  │ Automation  │  │ API Calls   │  │ File/OS   │ │   │
│  │  │ (Primary)   │  │ (Fallback)  │  │ (Spotify,   │  │ Control   │ │   │
│  │  │             │  │ Keyboard/   │  │ Google,     │  │           │ │   │
│  │  │ Roblox,     │  │ Mouse       │  │ GitHub,     │  │           │ │   │
│  │  │ Spotify     │  │ Simulation  │  │ Alexa)      │  │           │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── SCREEN AWARENESS ───────────────────────────┐   │
│  │  PIL ImageGrab → OCR → UI Element Recognition                      │   │
│  │  Gemini Multimodal Vision Analysis                                 │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── MEMORY SYSTEM ──────────────────────────────┐   │
│  │  Layer 1: Passive Vault (Auto-Capture, Auto-Tagging)               │   │
│  │  Layer 2: Pattern Learning (Trust Tiers, Corrections)              │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── BACKGROUND TASKS ───────────────────────────┐   │
│  │  Scheduler → Progress Checkpoints (30min) → Intermediate Streaming │   │
│  │  Autonomous Operation (Sleep/Offline Periods)                      │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                         │
│  ┌─────────────────────── UI/DASHBOARD ───────────────────────────────┐   │
│  │  Claude/ChatGPT-Style Layout + Agentic Panels                      │   │
│  │  Real-Time Typing Streaming, Voice Indicators, Task Progress       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Data Flow Paths:
- Voice Input: Mic → Porcupine → Gemini STT → Intent Parsing → Action
- Screen Context: ImageGrab → OCR → Gemini Vision → Context Injection
- Response: Gemini TTS → Audio Playback + Real-Time Text Streaming
- Memory: All Interactions → Layer 1 (Auto-Tag) → Layer 2 (Pattern Learn)
```

---

## 2. Data Flow Specification

### End-to-End Voice Command Flow
```
1. [WAKE] Porcupine detects "Friday" → Audio capture starts
2. [STT] Audio stream → Gemini 3.1 Flash Live Native STT (real-time)
3. [INTENT] Gemini parses natural language → Extract entities/parameters
4. [CONTEXT] Retrieve relevant memory:
   - Layer 1: Company info, user preferences, recent commands (last 5)
   - Layer 2: Trust tiers, past corrections, behavioral patterns
5. [PERMISSION] Evaluate trust tier for action:
   - Routine: Execute immediately
   - Conditional: Check context/confidence
   - High-Risk: Prompt for confirmation
6. [ACTION SELECTION] Choose execution path:
   - URI Scheme (Primary): e.g., roblox://games/[ID]
   - API Call (Spotify/Google/GitHub)
   - Keyboard/Mouse Automation (Fallback)
   - File/OS Direct Execution
7. [EXECUTE] Run action with real-time progress streaming:
   - Stream intermediate findings (research tasks)
   - Stream progress percentages (downloads/loading)
   - Voice + Text updates via Gemini bidirectional streaming
8. [RESPONSE] Gemini generates response → Native TTS + Real-Time Text Typing
9. [MEMORY UPDATE] Auto-capture interaction:
   - Tag conversation, entities, outcome
   - Update Layer 2 patterns if correction received
10. [AUDIO END] Silence detected → activity_end → Stop sending audio
```

### Decision Points & Fallbacks
- **Wake Word Missed**: No audio sent to Gemini (privacy-preserving)
- **STT Failure**: Fallback to alternative STT if configured
- **Intent Ambiguity**:
  - Confidence >75%: Execute best guess
  - 60-75%: Offer multiple choice
  - <60%: Ask clarifying question
- **URI Unavailable**: Fall back to keyboard/mouse automation
- **API Failure**: Retry → Fallback to alternative method → Report error
- **Gemini Unavailable**: Switch to configured fallback LLM (Claude/ChatGPT/Local)

---

## 3. API Integration List

### Entertainment Integrations
| Service | Auth Method | Primary Control | Fallback | Example Commands |
|---------|-------------|-----------------|----------|------------------|
| **Spotify** | Spotify Client ID + Client Secret | API Playback + `spotify:track:[ID]` URI | Keyboard shortcuts (Space, Next, Vol) | "play x on spot" |
| **Roblox** | None (Public URI) | `roblox://games/[GameID]` | UI automation | "play bloxfruits on roblox" |
| **Netflix** | None | Keyboard navigation (Up/Down/Enter) | UI automation | "play my hero academia on netflix" |
| **YouTube** | None | Direct URL `youtube.com/search?q=[query]` | Keyboard navigation | "search Python tutorials on YouTube" |

### Productivity Integrations
| Service | Auth Method | Capabilities | Example Commands |
|---------|-------------|--------------|------------------|
| **Gmail/Calendar** | Google Cloud Console Credentials | Read/write emails, draft with company context, send with confirmation, event create | "send a job letter from my company to x@x.com" |
| **GitHub** | Personal Access Token (PAT) | Repo CRUD, issue management, commit code, **self-modify Friday toolkit** | "update your toolkit to control GitHub with my PAT" |
| **File Management** | OS Native (Trust Tier Gated) | Navigate, create, move, delete (confirmation required), search | "find my project files" |
| **Web Research** | None (Gemini Native) | Autonomous research, real-time intermediate findings streaming, report generation | "research this website and generate a full report" |

### Communication Integrations
| Service | Auth Method | Capabilities | Example Commands |
|---------|-------------|--------------|------------------|
| **Instagram** | None (UI Automation) | Draft/send messages, navigate profiles | "msg mangesh on insta saying i will be back soon" |
| **Alexa/Smart Home** | Alexa Account Link | Translate commands to Alexa format, control lights/thermostats | "tell alexa to switch off my lights" / "switch off my lights" |
| **Email (Gmail)** | Google Cloud | Professional drafting with company context, external recipient confirmation | "send a job letter from my company" |

### System Integrations
| Service | Method | Capabilities |
|---------|--------|--------------|
| **Application Launcher** | URI/CLI/Automation | Launch any installed app by name |
| **Screen Capture** | PIL ImageGrab | Real-time desktop monitoring, OCR, error detection |
| **Keyboard/Mouse** | PyAutoGUI (Fallback) | Universal control when URI/API unavailable |
| **File System** | OS Native + Trust Tiers | Hierarchical access, protected directory gating |

---

## 4. URI Scheme Reference & Natural Language Mapping

### Supported URI Schemes
| Application | URI Format | Natural Language Example | Fallback Path |
|-------------|------------|--------------------------|---------------|
| **Roblox** | `roblox://games/[GameID]` | "play bloxfruits on roblox" → Lookup GameID → Construct URI | UI automation: Open Roblox → Search → Click |
| **Spotify** | `spotify:track:[ID]`<br>`spotify:album:[ID]`<br>`spotify:playlist:[ID]` | "play x on spot" → Search Spotify API → Get ID → Play via API/URI | Keyboard: Ctrl+Space (Play/Pause), Next/Prev |
| **YouTube** | `https://youtube.com/search?q=[query]` | "play my hero academia on YouTube" → Construct URL → Navigate | Keyboard: Tab/Enter to select result |
| **Netflix** | None (UI Navigation) | "play my hero academia on netflix" → Open Netflix → Search → Select | Keyboard: Up/Down/Enter, Space (Play) |
| **Microsoft Store** | `ms-windows-store://search/?query=[query]` | "find VS Code in Microsoft Store" | CLI: `winget search VS Code` |
| **Generic Apps** | `[AppName].exe` / `[AppName]://` | "open Chrome" → `chrome://` or `C:\Program Files\Google\Chrome\Application\chrome.exe` | Start menu search simulation |

### Natural Language → URI Mapping Logic
```python
# Example: "play bloxfruits on roblox"
1. Extract entities: game="bloxfruits", platform="roblox"
2. Query Roblox API/database for "bloxfruits" → GameID=123456
3. Construct URI: roblox://games/123456
4. Execute: os.startfile(uri)  # Windows default handler
5. Fallback: If URI fails → PyAutoGUI open Roblox → search "bloxfruits" → click play
```

---

## 5. Database Schema for Memory & Vault Layer

### Layer 1: Passive Automatic Capture (SQLite)
```sql
-- Conversation Logs (Auto-Tagged)
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    user_input TEXT,
    friday_response TEXT,
    tags TEXT  -- Auto-inferred: ["project", "company", "roblox", "email"]
);

-- Knowledge Vault (Auto-Captured Facts)
CREATE TABLE vault_facts (
    id INTEGER PRIMARY KEY,
    entity TEXT,  -- "company_name", "user_preference", "contact_mangesh"
    value TEXT,
    source TEXT,  -- "conversation", "email_signature", "user_correction"
    tags TEXT,  -- Auto-inferred: ["professional", "contact", "preference"]
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Executed Commands (Auto-Logged)
CREATE TABLE command_history (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    command TEXT,  -- Natural language input
    action_type TEXT,  -- "uri", "api", "automation", "file"
    target TEXT,  -- "roblox", "spotify", "instagram"
    outcome TEXT,  -- "success", "failed", "fallback_used"
    tags TEXT
);
```

### Layer 2: Pattern Learning & Dynamic Trust Tiers
*Trust tiers evolve as user develops conversation and patterns over time*
```sql
-- User Corrections (Learning from Mistakes)
CREATE TABLE corrections (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    original_command TEXT,
    corrected_action TEXT,
    pattern TEXT  -- Inferred: "always_confirm_external_email"
);

-- Trust Tier Assignments
CREATE TABLE trust_tiers (
    id INTEGER PRIMARY KEY,
    category TEXT,  -- "file_delete", "external_email", "smart_home"
    tier INTEGER,  -- 0=Always Confirm, 1=Auto-Approve After First Auth, 2=Auto-Approve
    first_approved_timestamp DATETIME,
    last_used DATETIME
);

-- Behavioral Patterns
CREATE TABLE behavior_patterns (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,  -- "report_depth", "notification_preference"
    value TEXT,  -- "brief", "immediate"
    confidence FLOAT,  -- 0.0-1.0
    last_observed DATETIME
);
```

### Auto-Tagging System
- **Trigger**: Every conversation, command, and outcome is auto-tagged
- **Inference**: Gemini 3.1 Flash Live extracts entities and context to assign tags
- **Retrieval**: Fuse.js fuzzy search across tags for fast context injection

---

## 6. UI/Dashboard Design Specification

### Layout (Claude/ChatGPT Aesthetic + Agentic Panels)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Friday Logo  [Settings] [Memory] [Integrations]                           │
├──────────────────────────────────┬──────────────────────────────────────────┤
│                                  │                                          │
│  MAIN CONVERSATION PANE          │  SIDEBAR: COMMAND HISTORY                │
│  (Real-Time Typing Streaming)    │  - "play bloxfruits on roblox"           │
│                                  │  - "send job letter to x@x.com"          │
│  > Friday, play bloxfruits   │  - "msg mangesh on insta"                │
│    on roblox                      │                                          │
│  > [EXECUTING: roblox_launch]     │  BACKGROUND TASK PANEL                   │
│  > Opening Bloxfruits...          │  🔄 Research Project X (45% complete)    │
│  > Done! Game launched.           │     - Intermediate: Found 3 sources     │
│                                  │     - Next: Synthesize findings          │
│  [Voice Indicator: 🎤 Listening] │                                          │
│                                  │  INTEGRATION STATUS                       │
│                                  │  ✅ Gemini 3.1 Flash Live                │
│                                  │  ✅ Spotify API                           │
│                                  │  ✅ Google Cloud                          │
│                                  │  ⚠️ GitHub PAT (Not Configured)          │
├──────────────────────────────────┴──────────────────────────────────────────┤
│  MEMORY VAULT SUMMARY: Company=Acme Inc, Contacts=5, Projects=3 [Expand]   │
│  VOICE: 🔊 Speaking | 🎤 Listening | ⏸️ Idle                               │
│  CONTROLS: [Stop] [Repeat] [Background Tasks] [Trust Tiers]                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key UI Features
- **Real-Time Typing**: Responses stream character-by-character via Gemini bidirectional streaming
- **Voice Indicators**: Visual feedback for listening (🎤), speaking (🔊), idle (⏸️)
- **Agentic Panels**: Background task progress, intermediate findings, execution status
- **Memory Expandable**: Quick view of stored company info, contacts, preferences
- **Integration Lights**: Green/Yellow/Red status for all connected services

---

## 7. Command Parser Logic & Natural Language Intent Recognition

### Powered by Gemini 3.1 Flash Live API
```python
# Intent Parsing Workflow
def parse_intent(user_input: str) -> Intent:
    # 1. Retrieve context from Layer 1/2 memory
    context = memory.retrieve_relevant(user_input)
    
    # 2. Gemini parses intent with context injection
    prompt = f"""
    Context: {context}
    User Input: {user_input}
    Extract: verb, entities (app, contact, query), parameters, confidence
    """
    response = gemini.chat(prompt)
    
    # 3. Ambiguity resolution
    if response.confidence > 0.75:
        return response.intent  # Execute best guess
    elif response.confidence > 0.60:
        return present_choices(response.options)  # Offer multiple choice
    else:
        return ask_clarification()  # Full question
```

### Example Parsing Workflows
#### "send a job letter from my company to x@x.com"
1. **Intent**: `send_email`
2. **Entities**: recipient=`x@x.com`, template=`job_letter`
3. **Context Retrieval**: Layer 1 auto-captured company name, email signature, professional tone
4. **Draft**: Gemini generates job letter using company context
5. **Permission**: External recipient → Require confirmation
6. **Execute**: Gmail API send after approval

#### "play bloxfruits on roblox"
1. **Intent**: `launch_game`
2. **Entities**: game=`bloxfruits`, platform=`roblox`
3. **Lookup**: Query Roblox API for "bloxfruits" → GameID=123456
4. **Action**: Construct `roblox://games/123456` → Execute URI
5. **Fallback**: If URI fails → PyAutoGUI automation

---

## 8. Permission & Risk Assessment Matrix

### High-Risk Actions (Always Explicit Permission)
- Delete files/folders
- Send emails to external recipients
- Post to public social media
- Modify system settings
- Install software
- Access password managers

### Conditional Actions (Trust Tier Gated)
| Action | Trust Tier 0 (Always Confirm) | Trust Tier 1 (Auto-Approve After First Auth) | Trust Tier 2 (Auto-Approve) |
|--------|-------------------------------|------------------------------------------------|----------------------------|
| Protected directory access | ✅ Confirm | ✅ Auto-approve after first auth | ✅ Auto-approve |
| Financial app access | ✅ Confirm | ✅ Auto-approve known operations | ✅ Auto-approve |
| Smart home control | ✅ Confirm | ✅ Auto-approve routine commands | ✅ Auto-approve |
| GitHub self-modification | ✅ Confirm | ✅ Auto-approve with PAT | ✅ Auto-approve |

### Routine Actions (Execute Immediately)
- Open applications
- Play music/videos
- Search web
- Launch games
- Screen capture/analysis
- Internal messaging
- Read files/emails

### Ambiguity Rules
- **>75% Confidence**: Execute best guess (e.g., "play it" → last searched song)
- **60-75% Confidence**: Offer 2-3 choices
- **<60% Confidence**: Ask full clarifying question

---

## 9. Real-Time Progress Feedback & Streaming Architecture

### Streaming via Gemini 3.1 Flash Live Bidirectional API
```python
# Research Task Streaming Example
async def research_task(query: str):
    await friday.stream_text("🔍 Starting research...")  # Real-time text
    await friday.stream_voice("Starting research, I'll update you as I go.")  # Voice
    
    # Stream intermediate findings
    for source in search(query):
        await friday.stream_text(f"📄 Found: {source.title}")  # Progressive text
        await friday.stream_voice(f"Found a source about {source.topic}")  # Voice update
    
    # Stream synthesis progress
    await friday.stream_text("✍️ Synthesizing findings...")
    report = synthesize(sources)
    
    # Stream final report section-by-section
    for section in report.sections:
        await friday.stream_text(section)  # Real-time typing
```

### Progress Update Triggers
- **Long tasks (>2s)**: Stream every 1-2 seconds
- **Background tasks**: Checkpoints every 5 minutes with intermediate findings
- **Downloads/Loading**: Percentage updates every 5%
- **Research**: Stream each search result, synthesis step, partial conclusion

---

## 10. Notification System

### Urgency Detection Logic
```python
def classify_urgency(task: Task) -> Urgency:
    if task.type in ["alert", "time_sensitive", "error"]:
        return Urgency.IMMEDIATE
    elif task.type in ["download", "routine_research", "scheduled"]:
        return Urgency.ROUTINE
    else:
        return Urgency.PER_TASK  # User-configured
```

### Delivery Rules
- **Immediate**: Voice alert + Dashboard notification + Push (if configured)
- **Routine**: Batch overnight → Deliver on user wake/session open
- **Per-Task**: Respect user override (e.g., "notify me every 10 minutes for this research")

### Progress Checkpoints
- Background tasks: Update every 5 minutes with intermediate findings
- Partial results exposed progressively (never wait for task completion)
- User can query "what's the status of my research?" anytime

---

## 11. Voice Interface Architecture

### Pipeline
```
Mic → Porcupine Wake Word → Audio Buffer → Gemini 3.1 Flash Live STT (Native)
→ Intent Parsing → Action → Gemini TTS (Native) → Audio Playback
```

### Key Features
- **Wake Word Only**: Audio sent to Gemini *only* after Porcupine detects "Friday"
- **Native STT/TTS**: No third-party services required (Gemini 3.1 Flash Live built-in)
- **Sub-500ms Latency**: Pre-buffering + streaming optimization
- **English-Only Enforcement**: Gemini rejects Hindi/Hinglish input with polite message
- **Noise Handling**: Gemini native noise suppression
- **Real-Time Voice Feedback**: Voice updates during long tasks (not just at completion)

---

## 12. Screen Capture & Visual Analysis

### Implementation
```python
from PIL import ImageGrab
import pytesseract  # OCR
from gemini import multimodal_vision

def see_screen(query: str = None):
    # 1. Capture screen
    screenshot = ImageGrab.grab()  # Full desktop, no webcam
    
    # 2. OCR text extraction
    text = pytesseract.image_to_string(screenshot)
    
    # 3. Gemini multimodal analysis
    if query:
        response = gemini.vision(screenshot, f"{query}\n\nOCR Text: {text}")
    else:
        response = gemini.vision(screenshot, "Describe what you see on this screen")
    
    return response
```

### Supported Queries
- "see my screen and tell me if you see any errors"
- "find the word msconfig here"
- "what do you see on my screen"
- "is there a loading spinner on my screen?"

---

## 13. Background Task Scheduler & Autonomous Operation

### Operation During Sleep/Offline
```python
class BackgroundScheduler:
    def __init__(self):
        self.queue = []  # Tasks queued for offline execution
        self.progress_interval = 5 * 60  # 5 minutes
    
    def run_offline(self):
        # Execute queued tasks without excessive battery drain
        for task in self.queue:
            task.execute()
            # Checkpoint every 5 minutes
            if time.time() - task.start_time > self.progress_interval:
                self.stream_intermediate_findings(task)
    
    def stream_intermediate_findings(self, task):
        # Expose partial results as discovered
        findings = task.get_partial_results()
        friday.stream_text(f"📊 Background Task Update: {findings}")
```

### Features
- **Resource Throttling**: Reduce CPU usage during sleep
- **Progress Checkpoints**: 30-minute intervals with intermediate findings
- **Notification Batching**: Routine tasks deliver on wake; urgent tasks notify immediately
- **Task Prioritization**: High-priority tasks execute first

---

## 14. Keyboard & Mouse Automation System

### Fallback for Non-URI Scenarios
```python
import pyautogui

def fallback_automation(action: str, target: str):
    if action == "type_message":
        pyautogui.click(instagram_chat_coordinates)
        pyautogui.write(target.message)
        pyautogui.press("enter")
    elif action == "netflix_search":
        pyautogui.press("Tab")  # Focus search bar
        pyautogui.write(target.query)
        pyautogui.press("Enter")
```

### Safety Features
- **Confirmation**: High-risk automation requires approval
- **Screen Verification**: Capture screen after action to verify success
- **Error Detection**: OCR check for error messages post-action

---

## 15. Multi-LLM Orchestration

### Abstraction Layer
```python
class LLMManager:
    primary = "gemini-3.1-flash-live"
    fallbacks = ["claude", "chatgpt", "local-llama"]
    
    def chat(self, prompt: str, model: str = None):
        model = model or self.primary
        try:
            return self.providers[model].chat(prompt)
        except Exception:
            for fallback in self.fallbacks:
                return self.providers[fallback].chat(prompt)
```

### Seamless Switching
- User configures API keys for alternative LLMs
- Friday routes tasks based on preference or availability
- Gemini 3.1 Flash Live remains primary for voice streaming and vision

---

## 16. Implementation Roadmap

### Phase 1: Core Foundations (MVP)
- ✅ Gemini 3.1 Flash Live voice interface (bidirectional streaming)
- ✅ Porcupine wake word integration
- ✅ Basic screen capture (PIL ImageGrab)
- ✅ URI-based app launching (Roblox, Spotify)
- ✅ Spotify API control + keyboard fallback
- ✅ Layer 1 memory (passive capture, auto-tagging)
- ✅ Simple permission model (high-risk confirmation)

### Phase 2: Autonomous Operation
- [ ] Layer 2 memory (dynamic trust tiers, pattern learning)
- [ ] Background task scheduler (5-min checkpoints)
- [ ] Real-time progress streaming for research
- [ ] Instagram/social messaging integration
- [ ] Gmail/Google Cloud integration
- [ ] Notification system (urgency detection)
- [ ] Keyboard/mouse automation fallback
- [ ] Multi-LLM switching

### Phase 3+: Advanced Autonomy
- [ ] GitHub integration + self-modification
- [ ] Smart home/Alexa control
- [ ] Trust tier machine learning
- [ ] Command chaining (multi-step workflows)
- [ ] Advanced dashboard with agentic panels
- [ ] Autonomous research optimization

---

## 17. Configuration Template

### `friday_config.yaml`
```yaml
# Core AI
primary_llm: "gemini-3.1-flash-live-preview"
fallback_llms: ["claude", "chatgpt"]
gemini_api_key: "your_gemini_key"
wake_word: "Friday"  # Porcupine model

# Integrations
spotify:
  client_id: "your_spotify_client_id"
  client_secret: "your_spotify_client_secret"
  playback_device: "default"
google_cloud:
  credentials_path: "~/.friday/google_credentials.json"
  scopes: ["gmail", "calendar"]
github:
  pat_key: "your_github_pat"  # Enables self-modification

# Voice
tts: "gemini-native"  # Fallback: elevenlabs, edge-tts
stt: "gemini-native"  # Fallback: whisper, groq
language: "en-only"  # Reject Hindi/Hinglish

# Memory
layer1_auto_tag: true
layer2_learning: true

# Notifications
urgent_delivery: "immediate"
routine_delivery: "batched"
progress_checkpoint_interval: 300  # 5 minutes (seconds)

# Trust Tiers
file_delete: "always_confirm"
external_email: "confirm_first_then_auto_approve"
smart_home: "auto_approve"

# UI
theme: "dark"
dashboard_layout: "claude-style"
streaming_typing: true
```

---

## 18. Special Technical Considerations

### Performance Targets
- Voice response initiation: <500ms
- STT latency: <1s
- Command feedback: <2s
- Long task streaming update: <5s intervals

### Jarvis Repository Patterns (Reference)
- **Daemon-Sidecar Separation**: Adapt for Friday's local-only operation
- **JWT WebSocket RPC**: Use for secure local service communication
- **Provider Abstraction**: Apply to LLM/STT/TTS switching
- **Vault Knowledge Graph**: Adapt SQLite schema for Friday's Layer 1/2 memory
- **Awareness Pipeline**: Adapt screen capture → OCR → context tracking

### Autonomous Operation
- Battery throttling during sleep
- Memory management for queued tasks
- Partial results exposure (never batch until completion)

---

## 19. Core Operating Principles

1. **Voice Confirmation**: Respond to voice commands with voice + text confirmation
2. **Context Persistence**: Remember company info, preferences, projects across sessions
3. **Permission with Trust Tiers**: High-risk confirm, routine auto-execute, conditional context-based
4. **Resilience**: Try URI → API → Automation → Report failure (multiple workarounds)
5. **Command Chaining**: Support sequential commands with context flow
6. **Real-Time Feedback**: Never stay silent during long tasks; stream progress
7. **Autonomous Offline**: Execute background tasks, checkpoint every 5min, batch routine notifications
8. **Model Flexibility**: Switch LLMs/TTS/STT seamlessly
9. **Continuous Learning**: Auto-capture interactions, learn from corrections
10. **Complete Desktop Control**: URI primary, automation fallback, all apps/files in scope
11. **English-Only**: Reject Hindi/Hinglish with polite message
12. **Ambiguity Resolution**: High confidence execute, low confidence ask, mid offer choice

---

## 20. Appendix: User Requirement Mapping

| User Requirement | Specification Section |
|------------------|----------------------|
| Open any apps when called | URI Scheme Reference, Automation System |
| Text on Insta: "msg mangesh on insta" | API Integration (Instagram), Command Parser |
| See screen: "find msconfig", "see errors" | Screen Capture & Visual Analysis |
| Play Roblox: "play bloxfruits on roblox" | URI Scheme (Roblox), Natural Language Mapping |
| Realtime research + report generation | Web Research Integration, Streaming Architecture |
| Work while sleeping | Background Task Scheduler |
| Play Spotify via keys: "play x on spot" | Spotify Integration, Automation Fallback |
| Control Alexa: "tell alexa to switch lights" | Smart Home Integration |
| Send job letter from company | Gmail Integration, Context Retrieval (Layer 1) |
| Access files with authority | Permission Matrix, Trust Tiers |
| Edit own code with GitHub PAT | GitHub Integration, Self-Modification |
| Play Netflix: "play my hero academia" | Netflix Integration, UI Automation |
| Realtime typing responses | UI Dashboard, Streaming Architecture |
| Speak/hear voice | Voice Interface Architecture |
| Switch LLMs/TTS/STT | Multi-LLM Orchestration |
| Dashboard like Claude/ChatGPT | UI/Dashboard Design |
| Memory vault (LLM + chat knowledge) | Database Schema (Layer 1/2) |
| Control everything said | Core Operating Principles |

---

*Specification Version: 1.0*
*Last Updated: 2026-05-05*
*Reference: [Jarvis Repository](https://github.com/vierisid/jarvis)*

---

## 21. Ethical Decision Engine & Safety Framework

### 21.1 Risk Classification System

**Low-Risk Actions** (Execute Immediately)
- Entertainment: Play music on Spotify, adjust volume, launch games (Roblox), play videos (Netflix/YouTube)
- Comfort: Launch applications, search web, screen capture/analysis
- Communication: Read emails, draft messages, internal messaging
- Navigation: Open browsers, navigate to URLs, file browsing (non-sensitive)

**Medium-Risk Actions** (Voice Confirmation Required)
- Communication: Send emails to internal recipients, post to private social channels, send drafted messages
- Content Creation: Generate reports, create documents, draft professional letters (with company context)
- File Operations: Move/copy files, organize directories, search across file systems
- Research: Autonomous web research, synthesize findings, generate reports

**High-Risk Actions** (Explicit User Confirmation + Voice Approval)
- System Modifications: Change system settings, install/uninstall software, modify registry
- Sensitive Data: Access financial records, password managers, banking folders
- External Communications: Send emails to external recipients, post to public social media
- System Access: GitHub PAT integration, access protected directories, modify Friday's own source code
- Bulk Operations: Mass file deletions, batch downloads, export user data

**Scenario-Based Decision Examples:**

| User Command | Risk Tier | Action | Confirmation Type |
|--------------|-----------|-------|-------------------|
| "Friday play bloxfruits on roblox" | Low | Launch `roblox://games/[ID]` | None (execute immediately) |
| "Update your toolkit to control github with my PAT" | High | Store credential securely, enable GitHub API | Voice: "I'm adding GitHub PAT integration—this is high-risk. Confirm?" |
| "Send a job letter from my company to x@x.com" | Medium→High | Draft letter with company context → Show draft → Send after confirmation | Voice: "I've drafted your job letter using Acme Inc. signature. Should I send to x@x.com?" |
| "Access all files on my computer" | High | Flag as unusual, require confirmation | Voice: "You're requesting access to all files including protected directories—this is outside your normal pattern. Confirm?" |

---

### 21.2 Contextual Permission Rules

**Dynamic Trust Tiers** (Evolve Through Conversation)
```python
# Trust tier adjusts based on user behavior over time
class DynamicTrustTier:
    def __init__(self, category: str):
        self.category = category  # "github", "external_email", "file_delete"
        self.interaction_count = 0
        self.confirmed_count = 0
        self.current_tier = 0  # 0=Always Confirm, 1=Auto-Approve After First Auth, 2=Auto-Approve
    
    def evaluate_action(self, context: dict) -> bool:
        # Tier 0: Always ask
        if self.current_tier == 0:
            return self.request_confirmation(context)
        
        # Tier 1: Auto-approve if previously confirmed in similar context
        elif self.current_tier == 1:
            if self._is_similar_context(context):
                return True  # Auto-approve
            else:
                return self.request_confirmation(context)
        
        # Tier 2: Auto-approve
        elif self.current_tier == 2:
            return True
    
    def update_tier(self, user_feedback: str):
        # User says "just send it" after 5 approvals → escalate to Tier 1
        # User says "always do this" → escalate to Tier 2
        # User says "don't do this" → revert to Tier 0
        pass
```

**Edge Case Handling:**
- **Draft vs. Send**: "Send a job letter" → Medium-risk (draft first, show user, then ask "Should I send?")
- **File Access Scope**: "Access all files" → High-risk (flag unusual scope, require explicit "yes, all files including Banking folder")
- **GitHub PAT**: First-time → High-risk confirmation; After 3 approvals in work hours → Tier 1 auto-approve

---

### 21.3 Anomaly Detection

**Behavioral Baseline Definition:**
```python
normal_patterns = {
    "file_access": ["Documents", "Projects", "Desktop"],  # Rarely accesses other folders
    "email_behavior": "usually drafts, seldom sends without review",
    "github_access": "Monday-Friday, 9am-5pm, during active dev tasks",
    "system_settings": "never modifies without explicit request",
    "external_communication": "requires confirmation for new recipients"
}
```

**Anomaly Triggers:**
- Accessing `Banking/` folder when user never has (threshold: 2+ std deviations from baseline)
- Requesting GitHub PAT integration for the first time (first-time system access)
- Sending email to `x@x.com` when user typically only emails `@company.com` (new external recipient)
- Bulk download of 50+ files in 3 minutes (velocity anomaly)
- Requesting action at 11pm when user pattern shows 9am-6pm activity (time anomaly)

**Flagging Logic:**
```python
def detect_anomaly(action: Action, user_history: History) -> bool:
    if action.category == "file_access":
        if action.target not in user_history.common_folders:
            return True  # Flag: "You usually access Documents, not Banking—proceed?"
    
    if action.category == "github" and action.first_time:
        return True  # Flag: "First-time GitHub PAT integration—confirm?" 
    
    if action.time.hour not in range(9, 18):  # Outside 9-6 pattern
        return True  # Flag: "You're requesting this at 11pm—unusual. Confirm?"
    
    return False
```

---

### 21.4 Audit Logging

**Log Structure:**
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT,  -- "email_send", "file_access", "github_push"
    risk_tier TEXT,  -- "low", "medium", "high"
    triggered_by TEXT,  -- "voice_command", "scheduled_task", "contextual_inference"
    user_confirmed BOOLEAN,
    reasoning TEXT,  -- "User authorized GitHub access 3 times previously"
    outcome TEXT,  -- "executed", "denied", "modified"
    session_id TEXT
);
```

**User-Facing Audit Summary (While User Was Away):**
```
📊 While you were asleep (8 hours):
  ✅ Drafted 3 emails (internal team updates)
  🎵 Played music for 2 hours (Spotify)
  ⚠️ Flagged: Attempted access to Banking folder (denied—outside normal pattern)
  📋 Completed research task: "AI trends 2026" (report saved to Documents)
```

**Retention Policy:** Logs retained for 90 days, purged automatically. User can export anytime.

---

### 21.5 Transparency & Explainability

**Friday's Explanation Prompts (10 Examples):**

1. **Denying Action**: "I'm not accessing your banking folder because that wasn't in your permitted file access list. If you'd like to allow this, please confirm."
2. **Executing with Reasoning**: "I drafted your email to hr@company.com using your standard professional signature and saved it as a draft for your review."
3. **Flagging Anomaly**: "This looks unusual—you're asking me to access your system files, which isn't in your normal pattern. Should I proceed?"
4. **Permission Decision**: "I'm sending this email without showing you first because you previously authorized me to send routine communications to your team."
5. **Trust Tier Escalation**: "You've now confirmed GitHub access 5 times during work hours—should I auto-approve future requests in this context?"
6. **Batching Explanation**: "I have 3 emails to send and 1 report to generate—all are internal team communications. Approve all?"
7. **Confidence Disclosure**: "I'm 92% confident you want to send this weekly status email, but I'm less certain about the recipient—should I verify first?"
8. **Correction Acknowledgment**: "Noted—I won't auto-send emails to external recipients without showing you first. Learning: external_email requires confirmation."
9. **Pattern Recognition**: "I've noticed you typically authorize GitHub pushes on Tuesday mornings during sprint planning—should I prepare for that?"
10. **Safety Override**: "You asked me to delete all files in Documents, but that includes your active projects. I'm denying this and asking: Did you mean a specific subfolder?"

---

### 21.6 Learning & Adaptation

**Feedback Loop Mechanism:**
```python
def process_user_feedback(feedback: str, context: dict):
    if feedback == "just send it":
        # Escalate trust tier after 5 occurrences
        trust_tier[context['category']].increment_confirmed()
        if trust_tier[context['category']].confirmed_count >= 5:
            trust_tier[context['category']].escalate_to_tier(1)
    
    elif feedback == "don't do this":
        # Revert to Tier 0, remember this constraint
        trust_tier[context['category']].revert_to_tier(0)
        trust_tier[context['category']].add_constraint(context)
    
    elif feedback == "always do this":
        # Escalate to Tier 2 (auto-approve)
        trust_tier[context['category']].escalate_to_tier(2)
```

**3 Realistic Adaptation Scenarios:**

1. **Email Sending**: User initially confirms every internal email → After 10 approvals, Friday suggests: "You've confirmed 10 internal emails—should I auto-send to @company.com recipients?" → User says "yes" → Friday escalates to Tier 2 for internal, remains Tier 0 for external.

2. **GitHub Access**: First PAT integration requires confirmation → User approves 3 Tuesday morning pushes → Friday learns: "GitHub access OK on Tue 9-11am during sprint planning" → Escalates to Tier 1 for that time window.

3. **File Deletion**: User always confirms deletion of temp files → After 5 approvals, Friday suggests batching: "I have 3 temp files to delete—approve all?" → User says "yes, always for temp files" → Friday auto-deletes temp files (Tier 2), but still confirms for project files (Tier 0).

**Safeguards:**
- Friday never unilaterally escalates permissions beyond Tier 1 without explicit "always do this" from user
- Users can roll back trust levels: "Friday, reset trust tier for external email"
- All escalations are logged and visible in Audit Log

---

## 22. Behavioral Prediction & Adaptive Permission System

### 22.1 Prediction Engine Architecture

**Data Sources for Pattern Recognition:**
```python
prediction_features = {
    "frequency": "How often does action X occur? (e.g., weekly status email = every Friday)",
    "temporal_patterns": "Time of day, day of week, seasonal rhythms",
    "contextual_triggers": "Location (home/office), preceding actions, detected user state",
    "recency": "Is this pattern current or from months ago?",
    "consistency": "How much variation across examples?"
}
```

**Confidence Scoring Formula:**
```
Confidence = (Frequency_Weight × 0.3) + (Consistency_Weight × 0.25) + (Recency_Weight × 0.2) + (Context_Alignment × 0.25)

Where:
- Frequency_Weight: 0.0-1.0 (based on occurrence count)
- Consistency_Weight: 0.0-1.0 (how similar past occurrences are)
- Recency_Weight: 0.0-1.0 (how recent the pattern is)
- Context_Alignment: 0.0-1.0 (does current context match past occurrences?)
```

**Prediction Examples:**

| Scenario | Confidence | Friday's Action |
|----------|-------------|------------------|
| "Every Friday at 4pm you send status email to team" (18/19 occurrences) | 95% | "Should I draft and queue your weekly status email for confirmation?" |
| "You're at office on Tuesday morning—typically open Slack + Calendar" | 78% | "I noticed you usually open Slack and Calendar now—should I launch them?" |
| "URGENT email from manager" (trigger-based) | 85% | "You received an urgent email from your manager—should I flag this and draft a response?" |
| "Play some music" (no context, occasional action) | 45% | Suppress suggestion, log for learning |

---

### 22.2 Dynamic Permission Profiles

**Profile Dimensions:**
```python
class PermissionProfile:
    def __init__(self):
        self.location = None  # "home", "office", "other"
        self.time_of_day = None  # "morning", "afternoon", "evening", "night"
        self.day_of_week = None  # "weekday", "weekend"
        self.user_state = None  # "working", "in_meeting", "on_break" (from calendar/activity)
        self.recent_feedback = []  # Last 10 user corrections
    
    def adjust_permissions(self):
        if self.location == "office" and self.time_of_day == "morning":
            return "more_permissive"  # Work-related actions auto-approve
        
        if self.location == "home" and self.time_of_day == "night":
            return "more_restrictive"  # Don't auto-send emails at 11pm
        
        if self.user_state == "in_meeting":
            return "defer_actions"  # Queue non-urgent tasks
```

**Profile Evolution Examples:**

| User | Context | Permission Adjustment |
|------|---------|----------------------|
| User 1 | At home (evenings) | Stricter: Require confirmation for file access, email sending |
| User 1 | At office (business hours) | Permissive: Auto-approve internal communications, GitHub pushes |
| User 2 | Weekends | Strict for financial apps, loose for personal communications |
| User 3 | Monday-Friday, 9-5pm | GitHub access auto-approved; after 5pm → require confirmation |

**Feedback Integration:**
- User rejects "Should I access financial files on weekend?" → Friday learns: `profile.add_rule("no_financial_weekends")`
- User approves "Open Slack + Calendar at office morning" → Friday learns: `profile.add_pattern("office_morning_routine")`

---

### 22.3 Intelligent Confirmation Batching

**Related Action Grouping Logic:**
```python
def group_related_actions(actions: List[Action]) -> List[List[Action]]:
    batches = []
    
    # Group by risk category
    by_risk = group_by(actions, key=lambda a: a.risk_tier)
    
    # Group by time window (actions within 5 minutes)
    by_time = group_by_time_window(actions, window_minutes=5)
    
    # Group by functional goal
    by_goal = group_by(actions, key=lambda a: a.context.get("goal"))
    
    # Combine: same risk + same time + same goal = batch together
    return combine_overlapping(by_risk, by_time, by_goal)
```

**Batching Examples:**

| Actions | Batched? | Presentation |
|---------|-----------|--------------|
| Draft status email, send to team lead, add to archive, close weekly tracker | ✅ Yes | "I have 4 end-of-week tasks: draft email, send, archive, close tracker. Approve all?" |
| Send email + Restart system | ❌ No | Different risk profiles—present separately |
| 3 internal emails + 1 report generation | ✅ Yes | "I have 3 emails to send and 1 report to generate—all internal team communications. Approve all?" |

**Edge Cases:**
- User approves batch but changes mind mid-execution → Friday pauses, asks: "You want to skip the archive step?"
- One action in batch fails → Friday continues others, reports: "Email sent, but archive failed—should I retry?"

---

### 22.4 Confidence Scoring and Thresholds

**User-Configurable Thresholds:**
```yaml
confidence_thresholds:
  low_risk: 60    # Suggest action if >60% confident
  medium_risk: 80  # Suggest action if >80% confident
  high_risk: 90    # Suggest action if >90% confident
  batch_approval: 85  # Batch actions if >85% confident all will be approved
```

**Threshold Application:**

| Confidence | Action |
|------------|--------|
| >85% | Proactively suggest: "Should I draft your weekly status email?" |
| 60-85% | Mention informally: "I noticed you usually send this around now" (no formal ask) |
| <60% | Suppress suggestion, log for learning |

**Transparency:** Friday shows confidence: "I'm 92% confident you want to send this email, but only 65% sure about the recipient—should I verify first?"

---

### 22.5 Anomaly Detection and Learning

**Statistical Baseline:**
```python
baseline = {
    "file_access_distribution": {"Documents": 80%, "Projects": 15%, "Banking": 0%, "System": 5%},
    "permission_requests": {"internal_email": 50%, "external_email": 5%, "github": 20%},
    "communication_frequency": {"emails_per_day": 5, "slack_messages": 20},
    "system_interactions": {"app_launches": 10, "settings_changes": 0}
}
```

**Anomaly Flags:**

| Anomaly Type | Detection Method | Flag Threshold | Friday's Response |
|--------------|------------------|----------------|-------------------|
| Financial files on weekend | Context mismatch (0% occurrence) | 2+ std deviations | "You normally don't access financial files on weekends—confirm?" |
| First-time GitHub PAT | Permission escalation | First-time access | "First-time GitHub integration—confirm you authorized this?" |
| Bulk download (50+ files/3min) | Velocity anomaly | >3 std deviations from mean | "Bulk download detected—this is outside your normal pattern. Confirm?" |
| Email to new external recipient | Context mismatch | New recipient domain | "New external recipient x@y.com—confirm send?" |

**Learning from False Positives:**
- User says "yes, this is fine" → Friday adjusts baseline: `baseline["file_access_distribution"]["Banking"] += 5%`
- User says "no, never do this" → Friday adds rule: `never_allow["financial_weekends"] = True`

---

### 22.6 Feedback Loop and Model Refinement

**Correction Capture:**
```python
def capture_correction(user_feedback: str, context: dict):
    correction = {
        "timestamp": now(),
        "feedback": user_feedback,  # "That wasn't what I wanted"
        "context": context,  # {time, location, preceding_actions, intent}
        "correction_type": "negative_reinforcement"
    }
    corrections_db.insert(correction)
    
    # Immediate model adjustment
    if "don't suggest this" in user_feedback:
        confidence_model.penalize(context["action_type"], weight=0.5)
    
    if "only on weekdays" in user_feedback:
        permission_profile.add_rule("no_action_on_weekends", context["action_type"])
```

**Refinement Process:**
- **Single correction**: Reduces confidence for similar predictions by 10-20%
- **Multiple corrections (3+)**: Adds explicit rule to never suggest that action in similar context
- **Positive reinforcement**: User says "good job" → Increases confidence for similar predictions by 5-10%

**Decay Mechanism:**
- Corrections fade over time: After 90 days, correction weight reduced by 50%
- User can explicitly reset: "Friday, forget my past corrections for email sending"

---

### 22.7 Complex Scenario: GitHub PAT Integration (End-to-End)

**Phase 1: Initial Request**
- User: "Update your toolkit to control GitHub with my PAT"
- Detection: High-risk (credential exposure), first-time system access
- Friday: "You're adding a new high-risk integration (GitHub PAT) for the first time. I'll need explicit confirmation. Should I proceed?"
- User confirms → Friday securely stores credential, logs action, sets trust tier to 0 (always confirm)

**Phase 2: Learning Pattern**
- Friday observes: User authorizes GitHub pushes on Tue/Thu 10-11am during sprint planning
- Pattern analysis: 3 approvals in same context → confidence 75%
- Friday: "I've detected you authorize GitHub pushes ~75% of the time during sprint planning. Should I prepare for this?"

**Phase 3: Predictive Phase**
- Context matches: Tuesday 10am, user says "starting dev work"
- Friday: "I detected you're starting dev work—should I prepare GitHub push capability?" (confidence 85%)
- User says "yes" → Friday batches: [push code, review PR, update docs] → single approval

**Phase 4: Anomaly Detection**
- User requests GitHub access on Sunday 11pm → Context mismatch (0% historical occurrence)
- Friday: "You're requesting GitHub access at 11pm on Sunday—this is outside your normal pattern (Tue/Thu 10-11am). Confirm?"

**Phase 5: Feedback Loop**
- User: "Don't authorize GitHub access after 5pm even if I ask"
- Friday: Immediately learns `no_github_after_5pm = True`
- Future: Even if confidence 90%, Friday blocks Sunday 11pm request due to explicit rule

---

### 22.8 System State Diagram

```
[Observation] → [Pattern Extraction] → [Confidence Scoring] → [Threshold Check]
                                                                  |
                                                                  ↓
[Suppress Suggestion] ← (Confidence < Threshold)                [Suggest Action] → [User Decision]
                                                                                    |
                                                                                    ↓
                                                                          [Approve] / [Reject]
                                                                              |           |
                                                                              ↓           ↓
                                                                     [Execute & Log]  [Capture Correction]
                                                                              |           |
                                                                              ↓           ↓
                                                                     [Update Baseline] ← [Refine Model]
                                                                              |
                                                                              ↓
                                                                     [Evolve Trust Tier]
```

**Example Trace: Weekly Status Email**
1. **Observation**: Friday notices it's Friday 4pm (18/19 occurrences)
2. **Pattern Extraction**: "Weekly status email to team" pattern detected
3. **Confidence Scoring**: Frequency=95%, Consistency=90%, Recency=100%, Context=90% → Overall 94%
4. **Threshold Check**: 94% > 85% threshold → Proceed
5. **Suggest Action**: "Should I draft and queue your weekly status email?"
6. **User Decision**: "Yes, send it"
7. **Execute & Log**: Draft email, send to team, log action in audit trail
8. **Update Baseline**: Reinforces pattern (19/20 occurrences now)
9. **Evolve Trust Tier**: After 10 approvals, Friday suggests: "Should I auto-send this weekly?"

---

## 23. Adaptive Behavioral Prediction Engine

### 23.1 Intent Prediction from Historical Patterns

**Temporal Pattern Recognition:**
```python
class TemporalPatternDetector:
    def detect_routines(self, history: List[Action]) -> List[Pattern]:
        patterns = []
        
        # Day-of-week patterns
        friday_emails = [a for a in history if a.day == "Friday" and a.hour == 16]
        if len(friday_emails) >= 3:
            patterns.append(Pattern(
                trigger="Friday 4pm",
                action="send_status_email",
                confidence=len(friday_emails) / total_fridays
            ))
        
        # Seasonal patterns
        month_patterns = group_by_month(history)
        if month_patterns["January"]["backup_files"] > 0:
            patterns.append(Pattern(
                trigger="January",
                action="backup_files",
                confidence=0.8
            ))
        
        return patterns
```

**Contextual Triggers:**
- **Location-based**: "At office → open Slack + Calendar"
- **Preceding actions**: "Opened IDE → likely to push to GitHub"
- **User state**: "Calendar shows 'Sprint Planning' → expect GitHub activity"

**Learning Window:**
- Minimum data: 3 occurrences before offering predictions
- Adaptation speed: Pattern changes detected within 2 occurrences of new behavior
- Distinguishing one-time vs. pattern: 3+ occurrences with 80%+ consistency = genuine pattern

---

### 23.2 Dynamic Permission Profiles (Real-Time Evolution)

**Real-Time Adjustment:**
```python
def adjust_permissions_realtime(context: dict):
    profile = get_current_profile()
    
    # Location shift
    if context["location"] == "office" and 9 <= context["hour"] <= 17:
        profile.set_permissive_for(["internal_email", "github", "file_access"])
    
    # Time shift
    if context["hour"] >= 22 or context["hour"] <= 6:
        profile.set_restrictive_for(["external_email", "system_settings"])
    
    # User state shift
    if context["calendar"] == "In Meeting":
        profile.defer_actions(["non_urgent_emails", "notifications"])
    
    # Feedback integration
    if context["last_feedback"] == "don't do this":
        profile.add_temporary_restriction(context["action_type"], duration_hours=24)
```

**Communication of Permission Shifts:**
- Friday: "I'm now at your office during work hours—I'll be more permissive for work-related actions."
- Friday: "It's 11pm and you're at home—I'm being more restrictive with external communications tonight."
- Friday: "You said not to access financial files on weekends—I'm blocking those requests."

---

### 23.3 Intelligent Confirmation Batching (Advanced Logic)

**Batching Rules:**
```python
def should_batch(actions: List[Action]) -> bool:
    # Rule 1: Same risk level
    if not all(a.risk_tier == actions[0].risk_tier for a in actions):
        return False  # Don't batch mixed risk levels
    
    # Rule 2: Close temporal proximity
    time_span = max(a.timestamp for a in actions) - min(a.timestamp for a in actions)
    if time_span > 5 * 60:  # 5 minutes
        return False
    
    # Rule 3: Same functional goal
    if not all(a.context.get("goal") == actions[0].context.get("goal") for a in actions):
        return False
    
    # Rule 4: User hasn't rejected similar batches before
    if has_rejected_batch_similar(actions):
        return False
    
    return True
```

**Presentation Formats:**
1. **Natural Language**: "I have 3 emails to send and 1 report—approve all?"
2. **Detailed Breakdown**: 
   ```
   📋 Batch Approval (4 actions):
   1. Draft weekly status email
   2. Send to team lead
   3. Archive in project folder
   4. Close weekly tracker
   Approve all? [Yes] [Review Each] [Reject]
   ```
3. **Granular**: User can approve 3/4, reject 1 → Friday executes approved, asks about rejected

**Edge Case: Mid-Execution Change of Mind**
- User approves batch → Friday starts executing → User says "wait, skip the archive step"
- Friday: Pauses, skips archive, continues with remaining actions

---

### 23.4 Confidence Scoring and Thresholds (Detailed Formula)

**Confidence Calculation:**
```python
def calculate_confidence(prediction: Prediction) -> float:
    # Frequency weight (0.0-1.0)
    freq_weight = min(prediction.occurrences / 10, 1.0)  # Cap at 10 occurrences
    
    # Consistency weight (0.0-1.0)
    consistency = prediction.similar_occurrences / prediction.total_occurrences
    cons_weight = consistency
    
    # Recency weight (0.0-1.0)
    days_since_last = (now() - prediction.last_occurrence).days
    recency_weight = max(0, 1.0 - (days_since_last / 30))  # Decay over 30 days
    
    # Context alignment (0.0-1.0)
    context_match = compare_context(prediction.context, current_context)
    context_weight = context_match
    
    # Weighted average
    confidence = (freq_weight * 0.3) + (consistency * 0.25) + (recency_weight * 0.2) + (context_weight * 0.25)
    
    return confidence
```

**Transparency in Confidence Reporting:**
- Friday: "I'm 92% confident because: this pattern occurred 12 times (30%), with 95% consistency (25%), recent (20%), and current context matches (25%)."
- User: "Why did you suggest that?"
- Friday: "I calculated 92% confidence based on: 12 Friday 4pm occurrences, 95% consistent recipients, last occurred 3 days ago, and current time is Friday 3:58pm."

---

### 23.5 Anomaly Detection and Behavioral Learning (Statistical + Contextual)

**Behavioral Baseline (Statistical):**
```python
baseline = {
    "file_access": {
        "Documents": {"mean": 20, "std": 5, "probability": 0.80},
        "Projects": {"mean": 10, "std": 3, "probability": 0.15},
        "Banking": {"mean": 0, "std": 0, "probability": 0.00},
        "System": {"mean": 2, "std": 1, "probability": 0.05}
    },
    "communication": {
        "emails_per_day": {"mean": 5, "std": 2},
        "external_recipients": {"mean": 0.5, "std": 0.5}
    }
}
```

**Anomaly Detection Rules:**
```python
def detect_anomaly(action: Action) -> Tuple[bool, str]:
    # Statistical anomaly
    if action.category == "file_access":
        expected = baseline["file_access"].get(action.target, {"mean": 0, "std": 0})
        if action.count > expected["mean"] + (2 * expected["std"]):
            return True, f"Accessing {action.target} {action.count} times—unusual (expected {expected['mean']})"
    
    # Contextual anomaly
    if action.category == "github" and action.hour == 23:
        return True, "GitHub access at 11pm—outside learned pattern (Tue/Thu 10-11am)"
    
    # Permission escalation
    if action.first_time_access and action.risk == "high":
        return True, f"First-time access to {action.system}—high-risk integration"
    
    # Velocity anomaly
    if action.rate > baseline["communication"]["emails_per_day"]["mean"] * 2:
        return True, f"Bulk action detected: {action.rate} actions/min—outside normal pattern"
    
    return False, ""
```

**Learning from False Positives:**
```python
def adjust_baseline(user_confirmed: bool, action: Action):
    if user_confirmed and action.anomaly_detected:
        # User said "yes, this is fine" → Adjust baseline
        baseline[action.category][action.target]["probability"] += 0.05
        baseline[action.category][action.target]["mean"] = (baseline[action.category][action.target]["mean"] + action.count) / 2
    
    elif not user_confirmed:
        # User said "no" → Reinforce anomaly detection
        anomaly_rules.append(f"never_allow_{action.category}_{action.target}")
```

---

### 23.6 Real-Time Feedback Loop and Model Refinement

**Immediate Capture:**
```python
def capture_feedback(user_response: str, prediction: Prediction):
    feedback = {
        "timestamp": now(),
        "prediction": prediction,
        "user_response": user_response,  # "Yes", "No", "That wasn't what I wanted"
        "context": current_context
    }
    feedback_db.insert(feedback)
    
    # Immediate model adjustment
    if "wasn't what I wanted" in user_response:
        # Negative reinforcement
        prediction_model.penalize(prediction.features, penalty=0.3)
        # Learn what NOT to do
        prediction_model.add_negative_example(prediction.features)
    
    if "only on weekdays" in user_response:
        # Add explicit rule
        permission_rules.add("no_" + prediction.action + "_on_weekends")
```

**Refinement Process:**
- **Single correction**: `confidence_model.adjust_weight(prediction, delta=-0.15)`
- **Multiple corrections (3+)**: `prediction_model.add_rule("never_predict_X_in_context_Y")`
- **Positive reinforcement**: "Good job" → `confidence_model.adjust_weight(prediction, delta=+0.05)`

**Context Encoding:**
```python
def encode_context(full_context: dict) -> ContextVector:
    return ContextVector(
        time_of_day=full_context["hour"],
        day_of_week=full_context["day"],
        location=full_context["location"],
        preceding_actions=full_context["last_3_actions"],
        user_state=full_context["calendar_state"],
        last_correction=full_context["last_feedback"]
    )
```

**Confidence Penalties:**
- After correction: Confidence for similar predictions reduced by 30%
- Penalty decays: 10% reduction per successful prediction (recovery over ~3 correct predictions)
- User can override: "Friday, restore confidence for email predictions"

**"Why Did You Suggest That?" Mechanism:**
- User: "Why did you suggest GitHub push?"
- Friday: "Because: 1) You're at office on Tuesday 10am (matches 8/10 past approvals), 2) You just opened IDE (preceding action matches), 3) Calendar shows 'Sprint Planning' (context matches). Overall confidence: 85%."

---

### 23.7 Integrated Scenario: GitHub PAT (Complete Trace)

**Step 1: Pattern Learning**
- Friday observes: User authorizes GitHub pushes on Tue/Thu 10-11am during sprint planning
- Data: 5 occurrences in 3 weeks, 100% consistency (same context)
- Pattern stored: `github_push_tue_thu_morning`

**Step 2: Dynamic Permissions**
- Context: Tuesday 10am, "Sprint Planning" on calendar
- Friday sets: `permission_profile.grant("github", level="permissive")`
- Context: Sunday 11pm
- Friday sets: `permission_profile.grant("github", level="restrictive")`

**Step 3: Confidence Scoring**
- Tuesday 10am request: Frequency=5/6 (0.83), Consistency=1.0, Recency=1.0 (1 day ago), Context=1.0 → Confidence = 95%
- Sunday 11pm request: Frequency=0/6 (0.0), Consistency=N/A, Recency=N/A, Context=0.0 → Confidence = 30%

**Step 4: Anomaly Detection**
- Request from new IP → Flag: "New IP address detected—confirm GitHub access?"
- Request unusual scopes (delete repo) → Flag: "Requesting delete permission—unusual. Confirm?"
- Request outside Tue/Thu 10-11am → Flag: "Outside learned pattern. Confirm?"

**Step 5: Batching**
- User has pending: [push code, create PR, update docs, close issue]
- All same risk level (medium), same goal ("sprint completion"), within 3 minutes
- Friday batches: "I have 4 sprint completion tasks—approve all?"

**Step 6: Feedback Loop**
- User: "Never auto-approve database credential access"
- Friday: `permission_rules.add("never_auto_approve_database_credentials")`
- Future: Even if confidence 95%, Friday blocks due to explicit rule

---

### 23.8 Implementation Specifications

**Prediction Engine Algorithm (Pseudocode):**
```
FOR EACH historical_action IN user_history:
    Extract features: time, location, preceding_actions, outcome
    Group by similarity (clustering)
    Calculate occurrence_count, consistency, recency
    
    FOR EACH cluster:
        IF occurrence_count >= 3:
            confidence = CalculateConfidence(cluster)
            IF confidence >= user_threshold:
                Store prediction: cluster → confidence
```

**Permission Profile Structure:**
```yaml
profiles:
  office_working_hours:
    location: "office"
    time: "9-17"
    permissions:
      internal_email: "auto_approve"
      github: "auto_approve"
      external_email: "confirm"
      system_settings: "confirm"
  
  home_evenings:
    location: "home"
    time: "18-23"
    permissions:
      internal_email: "confirm"
      github: "confirm"
      entertainment: "auto_approve"
      system_settings: "deny"
```

**Batching Decision Tree:**
```
Is action_risk consistent across all actions?
├─ NO → Do NOT batch (present separately)
├─ YES → Is time_span <= 5 minutes?
    ├─ NO → Do NOT batch
    ├─ YES → Is functional_goal same?
        ├─ NO → Do NOT batch
        ├─ YES → Has user rejected similar batches?
            ├─ YES → Do NOT batch
            ├─ NO → BATCH and present for approval
```

**Confidence Formula (Final):**
```
Confidence = min(1.0, 
    (occurrences / 10) * 0.3 +
    (consistent_occurrences / total_occurrences) * 0.25 +
    max(0, 1 - (days_since_last / 30)) * 0.2 +
    context_match_score * 0.25
)
```

**Anomaly Detection Thresholds:**
- Statistical: `value > mean + (2 * std)` → Flag
- Contextual: `context_match < 0.3` → Flag
- Velocity: `rate > 2 * baseline_rate` → Flag
- Permission: `first_time_high_risk = True` → Flag

**Feedback Loop Flow:**
```
User Correction → Store in feedback_db → Adjust confidence weights → Add negative example → Update permission rules → (Decay over time) → Model refinement
```

**Graceful Degradation:**
- Low confidence → Ask instead of guess
- Conflicting signals → Present options to user
- Multiple predictions compete → Show top 2 with confidence scores

**Transparency Principle:**
- Every prediction includes: confidence score + reasoning
- Every permission change announced: "I'm adjusting permissions because..."
- Every anomaly explained: "I flagged this because..."

**Rollback Capability:**
- User: "Friday, reset all learned patterns"
- Friday: `prediction_model.reset()`, `permission_profile.reset()`, `confidence_model.reset()`
- User: "Disable predictive features"
- Friday: `prediction_engine.disable()`, `batching.disable()`

**Uncertainty Handling:**
- Multiple competing predictions → "I'm unsure: Did you mean A (75%) or B (70%)?"
- Conflicting signals → "I'm getting mixed signals—can you clarify?"
- Low confidence all around → "I'm not confident enough to suggest—what would you like me to do?"

