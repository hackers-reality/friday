<div align="center">

# F.R.I.D.A.Y.
### *Female Replacement Intelligent Digital Assistant Youth*

**A fully autonomous, Iron Man-inspired AI agent for Windows**  
Built by [Arnav](https://github.com/hackers-reality) · Co-leader of [NexSemble](https://github.com/hackers-reality)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gemini Live](https://img.shields.io/badge/Gemini-Live%20Audio-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/hackers-reality/friday)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.4.0-blueviolet?style=flat-square)](https://github.com/hackers-reality/friday/releases/tag/v1.4.0)

---

*"Sometimes you gotta run before you can walk."* — Tony Stark

</div>

---

## Index

- [What is Friday?](#what-is-friday)
- [Feature Overview](#feature-overview)
  - [🎙️ Voice & Audio](#️-voice--audio)
  - [👁️ Vision & Screen Awareness](#️-vision--screen-awareness)
  - [🖥️ Desktop Automation & Control](#️-desktop-automation--control)
  - [🌐 Browser Integration](#-browser-integration)
  - [🎯 Goals & Productivity Enforcement](#-goals--productivity-enforcement)
  - [📬 Communication & Messaging](#-communication--messaging)
  - [🤖 AI & LLM](#-ai--llm)
  - [🧠 Memory & User Understanding](#-memory--user-understanding)
  - [🚀 System & Startup](#-system--startup)
  - [🖼️ Dashboard & UI](#-dashboard--ui)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [Fully Automatic Installation](#fully-automatic-installation)
    - [Manual](#manual)
  - [Environment Variables](#environment-variables)
  - [Launch Friday](#launch-friday)
  - [Add to Windows Startup](#add-to-windows-startup)
- [Voice Commands](#voice-commands)
- [Module Reference](#module-reference)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)
- [Known Issues](#known-issues)
- [License](#license)
- [Author](#author)
- [Community — Join NexSemble](#community--join-nexsemble)

---

## What is Friday?

Friday is not a chatbot. It is a **fully autonomous desktop AI agent** that lives on your Windows machine, watches your screen, listens to your voice, understands your goals, and takes action — [...]

Think of it as having a real-world version of Tony Stark's FRIDAY running on your PC. It monitors what you're doing, proactively comments and helps, controls your entire desktop via voice, manages[...]

What makes Friday different from other agents: **she learns who you are**. Import your conversation history from Claude, ChatGPT, or Gemini and Friday extracts your preferences, communication styl[...]

Friday is **open source**, **Windows-native**, **self-hosted**, and built to eventually compete with commercial agents like Devin, Cline, and Claude Code.

---

## Feature Overview

### 🎙️ Voice & Audio
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live native audio | ✅ Working | Primary voice interface via `friday_live.py` |
| Groq Whisper STT | ✅ Working | Fallback speech-to-text |
| Porcupine wake word | ✅ Working | "Hey Friday" detection via `voice_wake.py` |
| Multi-TTS engine support | 🔧 In Progress | ElevenLabs, Google TTS, pyttsx3 |
| Typing effect output | ✅ Working | Terminal typing effect for responses |
| Audio crackling fix | ✅ Fixed | Jitter buffer increased to 12 chunks (~2.4s), smoother drain, no discontinuity |

### 👁️ Vision & Screen Awareness
| Feature | Status | Details |
|---------|--------|---------|
| Live API native video feed | ✅ Working | Automatic ~1 FPS, 720p streaming — model sees screen without calling any tool |
| Active window detection | ✅ Working | `screen_watcher.py` via pywinctl |
| Gemini Vision analysis | ✅ Working | Screen-to-description pipeline |
| Vision-grounded clicking | ✅ Working | `vision_click()` — finds elements by description |
| Background monitor with proactivity | ✅ Working | Unsolicited observations via Gemini proactivity |
| Error detection on screen | 🔧 In Progress | Detects visible Python/JS errors |
| Visual search | ✅ Working | "Friday find the word X on screen" |

### 🖥️ Desktop Automation & Control
| Feature | Status | Details |
|---------|--------|---------|
| Mouse & keyboard control | ✅ Working | pyautogui-based via `friday/tools.py` |
| App launching & closing | ✅ Working | `open_app()`, `close_app()` — system discovery chain |
| Spotify control | ✅ Working (Web API + keyboard fallback) | Full Spotify API — search, play, queue, volume |
| Netflix/streaming control | 🔧 In Progress | Vision-based navigation |
| File system access | ✅ Working | With `run_cmd` + system access |
| Roblox launcher | ✅ Working | Web search place ID → `roblox://` URI |
| Microsoft Store launcher | ✅ Working | `ms-windows-store://` URI |
| Windows Clock (alarms, timers, stopwatch, reminders, focus) | ✅ Working | Persistent clock state, background thread scheduling, native notifications |

### 🌐 Browser Integration
| Feature | Status | Details |
|---------|--------|---------|
| Cross-browser history search | ✅ Working | Chrome, Brave, Edge, Opera SQLite (3650 days, 10000 limit) |
| History-based recall & open | ✅ Working | "Open that Jarvis repo I was looking at" |
| OpenCLI browser automation | ✅ Working | v1.7.18, `--session default`, persistent headless Chrome session |
| OpenCLI bind approach | ✅ Working | Opens URL via Chrome then `bind` — avoids automation window hang |
| Browser navigation by voice | ✅ Working | Opens URLs, searches, page interaction |

### 🎯 Goals & Productivity Enforcement
| Feature | Status | Details |
|---------|--------|---------|
| Goal tracking & persistence | ✅ Working | `friday/goals.py` + `friday_memory/goals.json` |
| Course/deadline tracking | ✅ Working | URL, deadline, description, verification method |
| OKR scoring engine | ✅ Working | `progress*0.5 + streak*0.3 + time_factor*0.2` |
| Morning plan + evening review | ✅ Working | Auto-advances streaks, flags gaps |
| Google Calendar integration | ✅ Working | List events + sync to goals via `calendar_tool_handler` |
| Escalating intervention (4 levels) | ✅ Working | L1:warn → L2:close → L3:URL+lock → L4:escalate |
| Tab closing enforcement | ✅ Working | Closes distracting tabs, reopens course URL |
| StayFree integration | ✅ Working | Reads local usage data (4 extension IDs, Edge/Brave/Chrome), process fallback |
| Knowledge graph auto-extraction | ✅ Working | Post-tool hook extracts entities + relationships |

### 📬 Communication & Messaging
| Feature | Status | Details |
|---------|--------|---------|
| Desktop toast notifications | ✅ Fixed | PowerShell `Windows.UI.Notifications` + plyer fallback — all messages deliver now |
| Gmail read/send | ✅ Working | `friday_gmail.py` via Gmail API |
| Instagram DM | ✅ Working | `instagram_messenger.py` via OpenCLI |
| Alexa smart home | ✅ Working | `alexa_webhoOK_server.py` |
| WhatsApp messaging | 📋 Planned | Via web automation |

### 🤖 AI & LLM
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live (primary) | ✅ Working | Cloud-hosted, real-time audio + native video feed |
| Multi-LLM switching | 📋 Deferred | Incompatible with Live WebSocket — postponed |
| LangGraph orchestration | 🔧 In Progress | `friday/reasoning.py` — reasoning engine promoted from archive |
| Research tool | ✅ Working | `friday/research.py` — real-time web research + reports |
| Reasoning engine | ✅ Working | `friday/reasoning.py` — multi-step reasoning |
| Self-modifying code | 🔧 In Progress | `friday/github.py` — GitHub API-based self-modification |
| Multi-agent delegation (9 roles) | ✅ Working | Same roster as Jarvis — research, coding, reasoning, etc. |
| KYU personality adaptation | ✅ Working | 4-stage interview → preference learning → system prompt injection |
| Dreaming / session analysis | ✅ NEW | `friday/dreaming.py` — analyzes past sessions while idle, extracts patterns, updates vector memory + knowledge graph |
| Cron scheduler | ✅ NEW | `friday/scheduler.py` — schedule autonomous tasks: status checks, goal reviews, dream cycles, custom commands |
| Seamless GitHub Device Flow auth | ✅ Fixed | Hardcoded GitHub App (friday-from-ironman) — zero config, just run and authorize. Auto-opens browser, permanent non-expiring token |
| GitHub App integration | ✅ NEW | `Iv23liuQ5XPhsBjONt9B` — full permissions: read/write repos, PRs, issues, actions, workflows, deployments, pages, secrets, admin projects, codespaces, gists, profile |

### 🧠 Memory & User Understanding
| Feature | Status | Details |
|---------|--------|---------|
| Cross-chatbot history import | ✅ Working | Import chats from Claude, ChatGPT, Gemini — Friday reads and learns from them |
| Preference extraction | ✅ Working | Parses imported conversations to build a user profile: likes, dislikes, habits, tone |
| KYU personality adaptation | ✅ Working | 4-stage interview → preference learning → `kyu_adapt()` → system prompt |
| Persistent memory vault | ✅ Working | `friday/vector_memory.py` — ChromaDB-based semantic memory |
| Knowledge graph | ✅ Working | `friday/knowledge_graph.py` — auto-extracts entities after every tool call |
| Semantic memory search | ✅ Working | Pulls relevant past context before every response |
| Memory import tool handler | ✅ Working | Processes chat exports into user profile + knowledge graph |


### 📄 File Generation
| Feature | Status | Details |
|---------|--------|---------|
| Universal file generator | ✅ Working | `file_generator.py` — all formats |

### 🐙 GitHub Integration
| Feature | Status | Details |
|---------|--------|---------|
| Pre-configured GitHub App | ✅ Done | `friday-from-ironman` — Client ID hardcoded, zero config needed |
| Device Flow authorization | ✅ Done | `github_authorize()` — auto-opens browser, just enter code and authorize |
| Token auto-refresh | ✅ Done | For expiring tokens; permanent tokens (no expiry) also supported |
| Repository operations | ✅ Working | Read/write files, create repos, list branches, commit history |
| Pull request operations | ✅ Working | Create, merge, list, review (AI-powered with Gemini) |
| Proactive PR manager | ✅ NEW | `pr_manager_tool` — polls GH repos for open PRs, auto-reviews new ones, background 5min polling |
| Issue tracking | ✅ Working | Create, list, search, label management |
| Code search | ✅ Working | Search across repos with GitHub code search API |
| Self-modification | ✅ Working | Read → modify → commit — Friday can edit her own code |
| Account permissions | ✅ Full | read/write: repos, actions, PRs, issues, workflows, deployments, pages, secrets, projects (admin), codespaces, gists, profile |
| Code files | ✅ Working | .py, .js, .ts, .html, .css, .sh, .yaml |
| Documents | 🔧 In Progress | .md, .txt, .docx, .pdf |
| Config/server files | 🔧 In Progress | Dockerfile, nginx.conf, .env |

### 🚀 System & Startup
| Feature | Status | Details |
|---------|--------|---------|
| Windows startup on boot | ✅ Working | `protector_tool(action='startup', startup_action='install')` via HKCU Run |
| System protector | ✅ NEW | `protector_tool` — prevents unauthorized shutdown/lid-close, monitors lid state, Win+X+U, Alt+F4, Ctrl+C, smart override based on uptime/resources |
| Keepalive (prevents GOAWAY) | ✅ Working | `keepalive_task()` pings every 45s |
| Auto-reconnect | ✅ Working | 5s reconnect loop on disconnect |
| Background operation | ✅ Working | asyncio task-based |

### 🖼️ Dashboard & UI
| Feature | Status | Details |
|---------|--------|---------|
| Desktop UI | 🔧 In Progress | `desktop_app.py` — PyQt6/Tkinter |
| Dark neon theme | 🔧 In Progress | Navy/cyan/teal aesthetic |
| Memory/knowledge panel | 📋 Planned | Shows goals, active LLM, memory |
| Settings panel | 📋 Planned | LLM switching, API keys, toggles |

---

## Architecture

```
E:\F.R.I.D.A.Y\
│
├── friday.py               ← PRIMARY ENTRY POINT (with 5x auto-restart loop)
│
├── friday/                 ← CORE PACKAGE (all modules)
│   ├── live.py             ← Main engine: Gemini Live session, 120+ tool declarations, TOOL_MAP
│   │   ├── Gemini Live audio/video (native WebSocket)
│   │   ├── keepalive_task() — prevents GOAWAY timeout
│   │   ├── _build_session_config() — system prompt with FRIDAY identity
│   │   └── Audio playback (jitter buffer, 4800 frames_per_buffer)
│   │
│   ├── tools.py            ← 120+ tool implementations (bridge to all modules)
│   │   ├── Desktop automation (mouse, keyboard, apps)
│   │   ├── Browser control (OpenCLI bind approach)
│   │   ├── File operations (generate, search, open)
│   │   ├── Spotify, Netflix, email, Instagram, Roblox, MS Store
│   │   └── GitHub (9+ operations), Clock, Goals, KYU, Research
│   │
│   ├── opencli.py          ← OpenCLI v1.7.18 wrapper (session-based browser automation)
│   │   ├── browser: navigate (bind), click, type, fill, extract, screenshot, scroll
│   │   ├── tabs: list, new, select, close
│   │   ├── site adapters: hackernews, reddit, twitter, 100+ more
│   │   └── bind/unbind to existing Chrome tab
│   │
│   ├── github.py           ← GitHub API + OAuth Device Flow
│   │   ├── 20+ operations (read/write files, branches, PRs, issues, search, repos)
│   │   ├── Device Flow OAuth (no redirect server needed)
│   │   └── PR review with Gemini AI
│   │
│   ├── goals.py            ← Goal/OKR system
│   │   ├── OKR scoring: progress*0.5 + streak*0.3 + time_factor*0.2
│   │   ├── 4-level progressive enforcement (L1-L4)
│   │   └── Morning plan + evening review
│   │
│   ├── clock.py            ← Windows Clock (alarms, timers, stopwatch, reminders, focus)
│   │
│   ├── stayfree.py         ← StayFree screen time (4 extension IDs, Edge/Brave, process fallback)
│   │
│   ├── gmail.py            ← Gmail + Calendar (unified OAuth via google_authorize)
│   │
│   ├── web.py              ← Browser history search (3650 days, 10000 limit)
│   │
│   ├── kyu.py              ← KYU personality adaptation (4-stage interview)
│   │
│   ├── knowledge_graph.py  ← Auto-extracts entities + relationships post-tool
│   │
│   ├── multi_agent.py      ← 9-role multi-agent delegation
│   │
│   ├── research.py         ← Autonomous web research
│   │
│   ├── reasoning.py        ← Multi-step reasoning engine
│   │
│   ├── hooks.py            ← Pre/post/error tool hooks (KG extraction, logging)
│   │
│   ├── notify.py           ← Desktop toast notifications
│   │
│   ├── vector_memory.py    ← ChromaDB semantic memory
│   │
│   ├── _paths.py           ← Centralized path resolution
│   │
│   └── workflow.py         ← Workflow engine
│       └── plugin.py       ← Plugin system
│
├── archive/                ← 23 experiment modules (available for promotion)
│
├── friday_memory/          ← RUNTIME DATA (gitignored)
│   ├── goals.json
│   ├── clock_state.json
│   ├── kyu_profile.json
│   ├── knowledge_graph.json
│   ├── chroma_db/
│   ├── workflow/
│   └── .gitkeep
│
├── friday.py               ← Root launcher
├── friday.cmd              ← Windows Command Prompt launcher
├── friday.ps1              ← PowerShell launcher
│
├── .env                    ← API keys (gitignored)
├── credentials.json        ← Google OAuth client (gitignored)
├── .gmail_token.json       ← Gmail+Calendar token (gitignored)
└── .github_token.json      ← GitHub OAuth token (gitignored)
```

---

## Quick Start

### Prerequisites

- Windows 10 or 11
- Python 3.11+
- Node.js 21+ (for OpenCLI)
- [Google API key (Gemini Live)](https://ai.google.dev/) — required
- [Picovoice Access Key](https://console.picovoice.ai/) — required
- [Spotify API credentials](https://developer.spotify.com/dashboard) — required
- [Groq API key](https://console.groq.com/) (optional, for Whisper STT)

Other LLM providers (Claude, OpenAI, Groq text, Ollama) are coming soon — use your Gemini API key for now.

## Installation


### Fully Automatic Installation
```powershell

# One-liner (PowerShell — installs everything needed)
powershell -ExecutionPolicy Bypass -NoProfile -Command "& { git clone https://github.com/hackers-reality/friday.git; Set-Location friday; pip install -r requirements.txt; npm install -g @jackwener/opencli; opencli browser install; .\install.ps1 }"
```
### Manual

```bash

# Clone the repo
git clone https://github.com/hackers-reality/friday.git
cd friday

# Install Python dependencies
pip install -r requirements.txt

# Install OpenCLI (browser automation)
npm install -g @jackwener/opencli

# Install Chrome bridge extension
opencli browser install

# Set up environment variables
copy .env.example .env
# Edit .env and add your API keys

# Run the Windows setup script (recommended)
# PowerShell:
.\install.ps1

# OR Command Prompt:
install.cmd

```

### Environment Variables

Gemini Live is the only supported LLM right now. Other LLM keys are stored for coming-soon support.

Get your keys/URLs here:
- Gemini API: https://ai.google.dev/
- Picovoice: https://console.picovoice.ai/
- Spotify: https://developer.spotify.com/dashboard
- Groq: https://console.groq.com/
- Anthropic: https://console.anthropic.com/ (coming soon)
- OpenAI: https://platform.openai.com/ (coming soon)
- Ollama: https://ollama.com/ (coming soon)
- Home Assistant: https://www.home-assistant.io/

Create a `.env` file in the root directory:

```env
# Required
GOOGLE_API_KEY=your_gemini_api_key_here
PICOVOICE_ACCESS_KEY=your_porcupine_key_here

# Spotify (required) — https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Optional — enables additional features
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here

# Ollama (coming soon; never localhost — use actual IP or hostname)
OLLAMA_BASE_URL=http://192.168.1.x:11434

# Smart home
ALEXA_WEBHOOK_URL=your_alexa_webhoOK_url

# Home Assistant (alternative to Alexa)
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_tOKen

# GitHub (optional) — enables code/PR tools
# NOTE: Client ID is HARDCODED — you don't need to add it to .env
# Just run github_authorize() and authorize the app.
GITHUB_REPO=owner/repo_name
```

### Google Calendar Setup (optional)

For `calendar_tool_handler` to work:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API**
3. Go to **Credentials** → Create OAuth 2.0 Client ID (Desktop app)
4. Download the JSON and save as `credentials.json` in the project root
5. First run auto-generates the tOKen at `friday_memory/calendar_tOKen.json`

```env
# In .env (not strictly required, Calendar uses credentials.json OAuth flow)
# But you still need GOOGLE_API_KEY for Gemini
```

### Launch Friday

```bash
# Option 1: Windows command (after install.ps1)
friday

# Option 2: Direct Python
python friday_live.py

# Option 3: PowerShell script
.\friday.ps1
```

### Add to Windows Startup

Friday can auto-start with Windows via the built-in `protector_tool`:

```bash
# Install Friday in Windows startup
python -c "from friday.protector import install_startup; print(install_startup())"

# Check status
python -c "from friday.protector import is_startup_installed; print('Startup:', is_startup_installed())"

# Remove from startup
python -c "from friday.protector import remove_startup; print(remove_startup())"
```

Or ask Friday: *"Friday, add yourself to Windows startup"* — she will call `protector_tool(action="startup", startup_action="install")`.

---

## Voice Commands

Friday responds to natural language. No rigid syntax required.

### Screen & Vision
```
"Friday, what do you see on my screen?"
"Friday, is there an error on my screen?"
"Friday, find the word msconfig on my screen"
"Friday, click the play button"
```

### Apps & Desktop
```
"Friday, open Spotify"
"Friday, play Naruto OST on Spotify"
"Friday, open VS Code"
"Friday, close Chrome"
"Friday, play Bloxfruits on Roblox"
```

### Browser & History
```
"Friday, open the Jarvis repo I was loOKing at — the one by vierisid"
"Friday, what was I reading about LangGraph earlier?"
"Friday, open my IITM course"
```

### Messaging & Communication
```
"Friday, message Mangesh on Instagram — tell him I'll be back soon"
"Friday, send an email to dev@example.com with a job offer letter from NexSemble"
"Friday, read my latest emails"
```

### Goals & Productivity
```
"Friday, I have an IITM 8-week course ending May 31st at iitm.course.url — track it"
"Friday, what are my goals today?"
"Friday, how long have I been on YouTube today?"
"Friday, what's my screen time?"
```

### Smart Home
```
"Friday, tell Alexa to switch off the lights"
"Friday, switch off my bedroom lights"
```

### LLM & System
```
"Friday, switch to Claude"
"Friday, what LLM are you using?"
"Friday, do a deep research on NVIDIA's new GPU architecture and generate a report"
"Friday, generate a Python Flask server file"
```

### Memory & Learning
```
"Friday, I've imported my Claude chat history — learn from it"
"Friday, what do you know about me?"
"Friday, update your understanding of my preferences"
"Friday, forget what I told you about X"
```

---

## Module Reference

| File | Purpose |
|------|---------|
| `friday.py` | Root entry point. Gemini Live session launch with 5x auto-restart |
| `friday/live.py` | Main engine. 120+ tool declarations, TOOL_MAP, audio playback, system prompt |
| `friday/tools.py` | 120+ tool bridge functions — desktop, browser, files, GitHub, clock, goals, etc. |
| `friday/opencli.py` | OpenCLI v1.7.18 wrapper — session-based browser automation + site adapters |
| `friday/github.py` | GitHub API (20+ ops) + Device Flow OAuth + AI PR review |
| `friday/goals.py` | Goal tracking, OKR scoring, 4-level progressive enforcement |
| `friday/clock.py` | Windows Clock — alarms, timers, stopwatch, reminders, focus mode |
| `friday/stayfree.py` | StayFree screen time detection (multi-browser, multi-extension) |
| `friday/gmail.py` | Gmail read/draft/send + Calendar + unified Google OAuth |
| `friday/web.py` | Cross-browser SQLite history search |
| `friday/kyu.py` | KYU personality adaptation — 4-stage interview + preference learning |
| `friday/knowledge_graph.py` | Auto-extracts entities + relationships after every tool call |
| `friday/multi_agent.py` | 9-role multi-agent delegation system |
| `friday/research.py` | Autonomous web research + report generation |
| `friday/reasoning.py` | Multi-step reasoning engine |
| `friday/hooks.py` | Pre/post/error tool hooks (knowledge graph, logging) |
| `friday/notify.py` | Desktop toast notifications (PowerShell + plyer) |
| `friday/dreaming.py` | Dreaming system — session analysis while idle |
| `friday/scheduler.py` | Cron scheduler for autonomous tasks |
| `friday/vector_memory.py` | ChromaDB semantic memory |
| `friday/_paths.py` | Centralized path resolution |
| `friday/workflow.py` | RPA workflow engine |
| `friday/plugin.py` | Plugin system |

---

## Development Roadmap

### v1.0 — Foundation OK
- [x] Gemini Live voice interface
- [x] Groq Whisper STT
- [x] Porcupine wake word detection
- [x] Screen capture & vision
- [x] Desktop automation (mouse, keyboard)
- [x] App launching
- [x] Deep research tool
- [x] File generation
- [x] Spotify API integration (Client ID + Secret)
- [x] Cross-chatbot history import (Claude, ChatGPT, Gemini)
- [x] User preference extraction from imported chats

### v1.1 — Intelligence Layer OK
- [x] Active window detection (stable)
- [x] Proactive screen commentary (non-command-triggered)
- [x] Vision-grounded clicking (`vision_click`)
- [x] Cross-browser history search
- [x] Goal memory + enforcement system
- [x] Real OpenCLI browser control (95 tools)
- [x] StayFree integration
- [x] Instagram DM (working)
- [x] Gmail integration

### v1.2 — Autonomy OK
- [x] Google Calendar integration
- [x] Windows startup (Task Scheduler)
- [x] Semantic memory (vector search with ChromaDB)
- [x] Self-modification system (GitHub API-based code editing)
- [x] LangGraph orchestration (graph-based agent routing)
- [ ] Multi-LLM switching (deferred — incompatible with Live WebSocket)

### v1.3 — Full Autonomy 🚀
- [x] Package reorganization (`friday/` package, `archive/` cleanup)
- [x] 120+ tools (up from 60)
- [x] OKR scoring engine (`progress*0.5 + streak*0.3 + time_factor*0.2`)
- [x] 4-level progressive goal enforcement (L1 warn → L4 escalate)
- [x] Morning plan + evening review auto-advancement
- [x] StayFree extended detection (4 extension IDs, Edge/Brave paths, process fallback)
- [x] Windows Clock integration (alarms, timers, stopwatches, reminders, focus mode)
- [x] GitHub OAuth Device Flow (no redirect server, polling-based)
- [x] GitHub 20+ API operations (create repo, issues, PR merge, search, branches, etc.)
- [x] Roblox + Microsoft Store URI launchers
- [x] OpenCLI v1.7.18 + bind approach (fixes `browser open` hang)
- [x] KYU personality adaptation (4-stage interview → preference learning)
- [x] 9-role multi-agent delegation (same as Jarvis roster)
- [x] Knowledge graph auto-extraction (post-tool hook)
- [x] Research + Reasoning engines promoted from archive
- [x] FRIDAY identity system prompt (she/her, witty, full autonomy)
- [x] Tool-call ceiling removed (all calls execute)
- [x] Audio crackling fixed (4800 frames_per_buffer, jitter buffer)
- [x] 1008 GoAway reconnection fixed (removed `pa.terminate()`)
- [x] Centralized path resolution (`friday/_paths.py`)

### v1.4 — Self-Improvement & Seamless Auth 🧠
- [x] Desktop notifications fixed (PowerShell toast + plyer fallback, no more silent failures)
- [x] Vision improved (1 FPS 720p automatic streaming, model sees screen without calling tools)
- [x] Audio crackling fixed (increased jitter buffer to 12 chunks, smoother drain)
- [x] Clock glitchiness fixed (notifications dependency resolved, display cleaned up)
- [x] Dreaming system — analyzes past sessions while idle, extracts patterns, updates memory + knowledge graph
- [x] Cron scheduler — schedule autonomous tasks (status checks, goal reviews, dream cycles, custom)
- [x] GitHub Device Flow simplified — only client ID needed (no secret), auto-opens browser
- [x] GitHub OAuth setup wizard — step-by-step guidance for creating the OAuth app
- [x] Episodic archive — SQLite FTS5 full-text search across all past sessions, auto-records all tool calls
- [x] Skill curator — auto-prunes failing skills, archives stale ones, suggests merges
- [x] Self-improvement pipeline — propose → review → apply code changes to own source
- [x] Crash watcher — real-time Windows Event Log crash monitoring, auto-detection + analysis
- [x] Proactive PR manager — polls GitHub repos for new PRs, auto-reviews with Gemini
- [x] System protector — prevents unauthorized shutdown/lid-close, detects Win+X+U/Alt+F4/Ctrl+C, smart override based on system health
- [x] Windows startup registration — `protector_tool` with HKCU Run key, install/remove/status

### v2.0 — Desktop App 🌟
- [ ] Native Windows app (PyQt6 or Tauri)
- [ ] Dark neon dashboard UI
- [ ] Settings panel with key vault
- [ ] Plugin system
- [ ] Packaged installer (.exe)

---

## Contributing

Friday is an open source project built solely by Arnav, shared publicly through [NexSemble](https://github.com/hackers-reality) — a peer-learning and collaborative tech community in Pune, India[...]

Pull requests are welcome. For major changes, open an issue first.

```bash
# Fork and clone
git clone https://github.com/your-username/friday.git

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, then push
git push origin feature/your-feature-name

# Open a Pull Request on GitHub
```

### Guidelines
- Keep Windows-native compatibility (no Docker, no mandatory WSL2)
- Never hardcode `localhost` — use `OLLAMA_BASE_URL` from env
- Every new tool must be registered in `friday_live.py`'s `execute_tool()`
- Test on Windows 10 and 11

---

## Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Gemini GOAWAY timeout on long idle | Fixed | keepalive_task() pings every 45s |
| Gemini 1008 GoAway on long tool sequences | Mitigated | Tool-ceiling removed; user accepts risk |
| Chrome SQLite locked when browser open | Fixed | Copy to temp before reading |
| pyautogui coordinates break on resolution change | In Progress | Use vision_click() instead |
| OpenCLI `browser open <url>` hangs on Windows | Fixed | Now opens via `webbrowser` + `bind` instead |
| Spotify "No active device" error | In Progress | Open Spotify app first, then retry |
| See_screen Gemini API 429 (rate limit) | Workaround | Falls back to Gemini 1.5 Flash automatically |
| SDK bug: `send_realtime_input` raises `ValueError` with >1 arg | Known | Only passes one argument at a time |
| SyncMutex lock_async log noise | Cosmetic | Non-fatal, safe to ignore |
| Audio crackling on long sessions | Fixed | Larger jitter buffer (12 chunks), smoother drain, exception_on_underflow=True |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Friday is solely built by Arnav** ([@hackers-reality](https://github.com/hackers-reality))  
Co-leader of [NexSemble](https://github.com/hackers-reality) — a peer-learning and collaborative tech community based in Pune, Maharashtra, India.

> *"This is not a chatbot . This is Friday — the real one."*

---

## Community — Join NexSemble

Friday is built in public and shared through **NexSemble** — a community of builders, hackers, and learners who ship real projects together. Come talk Friday, AI agents, and whatever you're bui[...]

<div align="center">

[![Discord](https://img.shields.io/discord/1483417587034493009?style=for-the-badge&logo=discord&logoColor=white&label=NexSemble%20Discord&color=5865F2)](https://discord.gg/Ttqz3jHGk2)

**[→ Join the NexSemble Discord](https://discord.gg/Ttqz3jHGk2)**

</div>

---

<div align="center">

**Star the repo if Friday helped you. She deserves it.**

[![GitHub stars](https://img.shields.io/github/stars/hackers-reality/friday?style=social)](https://github.com/hackers-reality/friday/stargazers)

</div>
