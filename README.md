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
[![Version](https://img.shields.io/badge/Version-1.2.0-blueviolet?style=flat-square)](https://github.com/hackers-reality/friday/releases/tag/v1.2.0)

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
| Gemini Live native audio | [OK] Working | Primary voice interface via `friday_live.py` |
| Groq Whisper STT | [OK] Working | Fallback speech-to-text |
| Porcupine wake word | [OK] Working | "Hey Friday" detection via `voice_wake.py` |
| Multi-TTS engine support | 🔧 In Progress | ElevenLabs, Google TTS, pyttsx3 |
| Typing effect output | [OK] Working | Terminal typing effect for responses |

### 👁️ Vision & Screen Awareness
| Feature | Status | Details |
|---------|--------|---------|
| Real-time screen capture | [OK] Working | `friday_vision.py` via PIL/mss |
| Active window detection | [OK] Working | `screen_watcher.py` via pywinctl |
| Gemini Vision analysis | [OK] Working | Screen-to-description pipeline |
| Vision-grounded clicking | [OK] Working | `vision_click()` — finds elements by description |
| Background monitor with proactivity | [OK] Working | Unsolicited observations via Gemini proactivity |
| Error detection on screen | 🔧 In Progress | Detects visible Python/JS errors |
| Visual search | [OK] Working | "Friday find the word X on screen" |

### 🖥️ Desktop Automation & Control
| Feature | Status | Details |
|---------|--------|---------|
| Mouse & keyboard control | [OK] Working | pyautogui-based via `friday_tools.py` |
| App launching & closing | [OK] Working | `open_app()`, `close_app()` |
| Spotify control | [OK] Working (Web API + keyboard fallback) | Full Spotify API (Client ID + Secret) — search, play, queue, volume |
| Netflix/streaming control | 🔧 In Progress | Vision-based navigation |
| File system access | [OK] Working | With authority checks |
| RPA workflows | [OK] Working | `friday_automation.py` |
| Game launching | 🔧 In Progress | e.g., "Play Bloxfruits on Roblox" |

### 🌐 Browser Integration
| Feature | Status | Details |
|---------|--------|---------|
| Cross-browser history search | [OK] Working | Chrome, Brave, Edge, Opera SQLite |
| History-based recall & open | [OK] Working | "Open that Jarvis repo I was looking at" |
| OpenCLI browser automation | [OK] Working | CDP-based + `@jackwener/opencli` |
| Browser navigation by voice | [OK] Working | Opens URLs, searches |

### 🎯 Goals & Productivity Enforcement
| Feature | Status | Details |
|---------|--------|---------|
| Goal tracking & persistence | [OK] Working | `goal_memory.py` + `friday_memory/goals.json` |
| Course/deadline tracking | [OK] Working | Monitors browser history for progress |
| Google Calendar integration | [OK] Working | List events + sync to goals via `calendar_tool_handler` |
| Escalating intervention system | [OK] Working | Scolding counts + enforcement actions |
| Tab closing enforcement | [OK] Working | Closes distracting tabs, reopens course URL |
| StayFree integration | [OK] Working | Reads local usage data, triggers blocks |

### 📬 Communication & Messaging
| Feature | Status | Details |
|---------|--------|---------|
| Gmail read/send | [OK] Working | `friday_gmail.py` via Gmail API |
| Instagram DM | [OK] Working | `instagram_messenger.py` via OpenCLI |
| Alexa smart home | [OK] Working | `alexa_webhook_server.py` |
| WhatsApp messaging | 📋 Planned | Via web automation |

### 🤖 AI & LLM
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live (primary) | [OK] Working | Cloud-hosted, real-time audio (only LLM supported right now) |
| Other LLMs (Claude, GPT, Groq, Ollama) | 🔧 Coming Soon | Use Gemini API key for now |
| Multi-LLM switching | 📋 Planned | `llm_manager.py` — coming soon |
| LangGraph orchestration | 🔧 In Progress | `friday_langgraph.py` (syntax fixed) |
| [OK] Working | [OK] Working | Real-time web research + reports |
| Self-modifying code | 🔧 In Progress | `self_modification.py` |

### 🧠 Memory & User Understanding
| Feature | Status | Details |
|---------|--------|---------|
| Cross-chatbot history import | [OK] Working | Import chats from Claude, ChatGPT, Gemini — Friday reads and learns from them |
| Preference extraction | [OK] Working | Parses imported conversations to build a user profile: likes, dislikes, habits, tone |
| Personality adaptation | [OK] Working | Friday adjusts how she speaks based on your learned profile — no cold starts |
| Persistent memory vault | 🔧 In Progress | `vector_memory.py` — stores facts, preferences, patterns across sessions |
| Semantic memory search | 🔧 In Progress | Pulls relevant past context before every response |
| Knowledge vault | 🔧 In Progress | Combined LLM knowledge + everything Friday has learned about you |


### 📄 File Generation
| Feature | Status | Details |
|---------|--------|---------|
| Universal file generator | [OK] Working | `file_generator.py` — all formats |
| Code files | [OK] Working | .py, .js, .ts, .html, .css, .sh, .yaml |
| Documents | 🔧 In Progress | .md, .txt, .docx, .pdf |
| Config/server files | 🔧 In Progress | Dockerfile, nginx.conf, .env |

### 🚀 System & Startup
| Feature | Status | Details |
|---------|--------|---------|
| Windows startup on boot | [OK] Working | `startup_integration.py` via Task Scheduler |
| Keepalive (prevents GOAWAY) | [OK] Working | `keepalive_task()` pings every 45s |
| Auto-reconnect | [OK] Working | 5s reconnect loop on disconnect |
| Background operation | [OK] Working | asyncio task-based |

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
D:\F.R.I.D.A.Y\
│
├── friday_live.py          ← PRIMARY ENTRY POINT
│   ├── Gemini Live session (native audio)
│   ├── keepalive_task() — prevents GOAWAY timeout
│   ├── background_monitor() — screen watcher loop
│   └── execute_tool() — routes voice commands to tools
│
├── friday_tools.py         ← TOOL EXECUTION ENGINE
│   ├── Desktop automation (mouse, keyboard, apps)
│   ├── Browser control (OpenCLI + CDP)
│   ├── File operations
│   ├── Spotify, Netflix, email, Instagram
│   └── vision_click() — Gemini Vision-grounded clicking
│
├── friday_vision.py        ← VISION PIPELINE
│   ├── Screen capture (mss + PIL)
│   ├── Gemini Vision analysis
│   ├── vision_find_element() — locates UI elements
│   ├── vision_describe_screen() — proactive commentary
│   └── OCR, QR, face detection
│
├── friday_automation.py    ← RPA & BROWSER AUTOMATION
│   ├── BrowserAutomation (Selenium/Playwright)
│   ├── FileAutomation (batch ops, organizer)
│   ├── SystemAutomation (commands, scheduler)
│   └── RPA workflow engine
│
├── opencli_integration.py  ← BROWSER CONTROL
│   ├── Real @jackwener/opencli binary calls
│   ├── Instagram DM via OpenCLI
│   └── CDP fallback
│
├── goal_memory.py          ← GOAL & PRODUCTIVITY SYSTEM
│   ├── Persistent goal storage (friday_memory/goals.json)
│   ├── Browser history cross-reference
│   ├── Escalating scolding (levels 0-3)
│   └── Tab enforcement
│
├── browser_history_tools.py ← HISTORY SEARCH
│   ├── Chrome, Brave, Edge, Opera SQLite reading
│   ├── Fuzzy search across all browsers
│   └── find_repo_in_history()
│
├── llm_manager.py          ← MULTI-LLM SWITCHER
│   ├── Gemini, Claude, GPT, Groq, Ollama
│   └── Auto-detects available keys
│
├── proactive_screen_monitor.py ← BACKGROUND WATCHER
│   ├── Screenshot every 30s
│   ├── Gemini Vision analysis
│   └── Unsolicited commentary engine
│
├── stayfree_bridge.py      ← STAYFREE INTEGRATION
│   ├── Reads local StayFree data files
│   ├── Chrome extension storage bridge
│   └── Goal enforcement + site blocking
│
├── friday_langgraph.py     ← AGENT ORCHESTRATION
│   └── LangGraph-based multi-step reasoning
│
├── friday_memory/          ← PERSISTENT MEMORY
│   ├── goals.json
│   ├── memory.json
│   └── research_history/
│
└── friday_reports/         ← GENERATED REPORTS
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
ALEXA_WEBHOOK_URL=your_alexa_webhook_url

# Home Assistant (alternative to Alexa)
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_token

# GitHub (optional) — enables code/PR tools
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=owner/repo_name
```

### Google Calendar Setup (optional)

For `calendar_tool_handler` to work:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API**
3. Go to **Credentials** → Create OAuth 2.0 Client ID (Desktop app)
4. Download the JSON and save as `credentials.json` in the project root
5. First run auto-generates the token at `friday_memory/calendar_token.json`

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

```bash
# Run as Administrator
python startup_integration.py --add

# Verify
python startup_integration.py --status

# Remove from startup
python startup_integration.py --remove
```

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
"Friday, open the Jarvis repo I was looking at — the one by vierisid"
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
| `friday_live.py` | Primary entry point. Gemini Live session, keepalive, tool routing |
| `friday_tools.py` | All tool implementations — desktop, browser, files, media |
| `friday_vision.py` | Vision pipeline — capture, Gemini analysis, click targeting |
| `friday_automation.py` | RPA engine, Selenium/Playwright browser automation |
| `opencli_integration.py` | OpenCLI binary wrapper for browser control |
| `browser_history_tools.py` | Cross-browser SQLite history reader |
| `goal_memory.py` | Goal tracking, persistence, enforcement |
| `proactive_screen_monitor.py` | Background screen watcher + commentary |
| `stayfree_bridge.py` | StayFree screen time data reader |
| `llm_manager.py` | Multi-LLM provider switcher |
| `friday_langgraph.py` | LangGraph agent orchestration |
| `friday_gmail.py` | Gmail read/draft/send |
| `instagram_messenger.py` | Instagram DM via OpenCLI |
| `alexa_webhook_server.py` | Alexa integration webhook |
| `file_generator.py` | Universal file generation via LLM |
| `startup_integration.py` | Windows Task Scheduler startup registration |
| `self_modification.py` | Self-editing toolkit |
| `vector_memory.py` | Semantic memory with vector search |
| `friday_scheduler.py` | Recurring task scheduler |
| `desktop_app.py` | Dashboard UI (in progress) |
| `friday_config.py` | Configuration management |
| `friday_security.py` | Security scanning tools |
| `screen_watcher.py` | Active window detection |

---

## Development Roadmap

### v1.0 — Foundation [OK]
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

### v1.1 — Intelligence Layer [OK]
- [x] Active window detection (stable)
- [x] Proactive screen commentary (non-command-triggered)
- [x] Vision-grounded clicking (`vision_click`)
- [x] Cross-browser history search
- [x] Goal memory + enforcement system
- [x] Real OpenCLI browser control (95 tools)
- [x] StayFree integration
- [x] Instagram DM (working)
- [x] Gmail integration

### v1.2 — Autonomy [OK]
- [x] Google Calendar integration
- [x] Windows startup (Task Scheduler)
- [x] Semantic memory (vector search with ChromaDB)
- [x] Self-modification system (safety-validated code editing)
- [x] LangGraph orchestration (graph-based agent routing)
- [ ] Multi-LLM switching (skipped — Gemini Live is the primary interface)

### v2.0 — Desktop App 🚀
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
| Gemini GOAWAY timeout on long idle | Fixed | keepalive_task() sends ping every 45s |
| Chrome SQLite locked when browser open | Fixed | Copy to temp before reading |
| pyautogui coordinates break on resolution change | In Progress | Use vision_click() instead |
| friday_langgraph.py syntax errors | Fixed | Trailing quotes removed |
| OpenCLI not installed (autocli.exe mistake) | Fixed | `npm install -g @jackwener/opencli` |
| Spotify "No active device" error | In Progress | Open Spotify app first, then retry |
| See_screen Gemini API 429 (rate limit) | Workaround | Falls back to Gemini 1.5 Flash automatically |
| close_app fails if process name has wrong extension | Fixed | Now tries both with/without .exe suffix |

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
