<div align="center">

# F.R.I.D.A.Y.
### *Female Replacement Intelligent Digital Assistant Youth*

**A fully autonomous, Iron Man-inspired AI agent for Windows**  
Built by [hackers-reality](https://github.com/hackers-reality) · [NexSemble](https://github.com/hackers-reality)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gemini Live](https://img.shields.io/badge/Gemini-Live%20Audio-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/hackers-reality/friday)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.0.0-blueviolet?style=flat-square)](https://github.com/hackers-reality/friday/releases/tag/v1.0.0)

---

*"Sometimes you gotta run before you can walk."* — Tony Stark

</div>

---

## What is Friday?

Friday is not a chatbot. It is a **fully autonomous desktop AI agent** that lives on your Windows machine, watches your screen, listens to your voice, understands your goals, and takes action — without you needing to type a single command.

Think of it as having a real-world version of Tony Stark's FRIDAY running on your PC. It monitors what you're doing, proactively comments and helps, controls your entire desktop via voice, manages your goals and deadlines, integrates with your browser history, smart home devices, email, and social media — and it does all of this continuously in the background.

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
| Real-time streaming response | 🔧 In Progress | Typing effect output |

### 👁️ Vision & Screen Awareness
| Feature | Status | Details |
|---------|--------|---------|
| Real-time screen capture | ✅ Working | `friday_vision.py` via PIL/mss |
| Active window detection | ✅ Working | `screen_watcher.py` via pywinctl |
| Gemini Vision analysis | ✅ Working | Screen-to-description pipeline |
| Vision-grounded clicking | 🔧 In Progress | `vision_click()` — finds elements by description |
| Proactive screen commentary | 🔧 In Progress | Background monitor with unsolicited observations |
| Error detection on screen | 🔧 In Progress | Detects visible Python/JS errors |
| Visual search | ✅ Working | "Friday find the word X on screen" |

### 🖥️ Desktop Automation & Control
| Feature | Status | Details |
|---------|--------|---------|
| Mouse & keyboard control | ✅ Working | pyautogui-based via `friday_tools.py` |
| App launching & closing | ✅ Working | `open_app()`, `close_app()` |
| Spotify control | ✅ Working | Full Spotify API (Client ID + Secret) — search, play, queue, volume |
| Netflix/streaming control | 🔧 In Progress | Vision-based navigation |
| File system access | ✅ Working | With authority checks |
| RPA workflows | ✅ Working | `friday_automation.py` |
| Game launching | 🔧 In Progress | e.g., "Play Bloxfruits on Roblox" |

### 🌐 Browser Integration
| Feature | Status | Details |
|---------|--------|---------|
| Cross-browser history search | 🔧 In Progress | Chrome, Brave, Edge, Opera SQLite |
| Open URL from history by voice | 🔧 In Progress | "Open that Jarvis repo I was looking at" |
| OpenCLI browser automation | ✅ Working | CDP-based + `@jackwener/opencli` |
| Browser navigation by voice | ✅ Working | Opens URLs, searches |

### 🎯 Goals & Productivity Enforcement
| Feature | Status | Details |
|---------|--------|---------|
| Goal memory (persistent) | 🔧 In Progress | `goal_memory.py` + `friday_memory/goals.json` |
| Course/deadline tracking | 🔧 In Progress | Monitors browser history for progress |
| Google Calendar integration | 📋 Planned | Class times, exams, events |
| Proactive scolding | 🔧 In Progress | Escalating intervention system |
| Tab closing enforcement | 🔧 In Progress | Closes distracting tabs, reopens course URL |
| StayFree integration | 🔧 In Progress | Reads local usage data, triggers blocks |

### 📬 Communication & Messaging
| Feature | Status | Details |
|---------|--------|---------|
| Email read/draft/send | 🔧 In Progress | `friday_gmail.py` via Gmail API |
| Instagram DM | 🔧 In Progress | `instagram_messenger.py` via OpenCLI |
| Alexa/smart home control | 🔧 In Progress | `alexa_webhook_server.py` |
| WhatsApp messaging | 📋 Planned | Via web automation |

### 🤖 AI & LLM
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live (primary) | ✅ Working | Cloud-hosted, real-time audio |
| Ollama (local LLMs) | ✅ Working | Via `OLLAMA_BASE_URL` env var |
| Multi-LLM switching | 🔧 In Progress | `llm_manager.py` — Claude, GPT, Groq |
| LangGraph orchestration | 🔧 In Progress | `friday_langgraph.py` (syntax fixed) |
| Deep research tool | ✅ Working | Real-time web research + reports |
| Self-modifying code | 🔧 In Progress | `self_modification.py` |

### 📁 File Generation
| Feature | Status | Details |
|---------|--------|---------|
| Universal file generator | 🔧 In Progress | `file_generator.py` — all formats |
| Code files | ✅ Working | .py, .js, .ts, .html, .css, .sh, .yaml |
| Documents | 🔧 In Progress | .md, .txt, .docx, .pdf |
| Config/server files | 🔧 In Progress | Dockerfile, nginx.conf, .env |

### 🚀 System & Startup
| Feature | Status | Details |
|---------|--------|---------|
| Windows startup on boot | 🔧 In Progress | `startup_integration.py` via Task Scheduler |
| Session keepalive | ✅ Working | `keepalive_task()` prevents Gemini timeout |
| Auto-reconnect on drop | ✅ Working | 5s reconnect loop |
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
- Google API key (Gemini Live)
- Groq API key (optional, for Whisper STT)

### Installation

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
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional — enables additional features
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here
PICOVOICE_ACCESS_KEY=your_porcupine_key_here

# Ollama (never localhost — use actual IP or hostname)
OLLAMA_BASE_URL=http://192.168.1.x:11434

# Spotify (get from https://developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Smart home
ALEXA_WEBHOOK_URL=your_alexa_webhook_url

# Home Assistant (alternative to Alexa)
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HA_TOKEN=your_long_lived_access_token
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

### v1.0 — Foundation ✅
- [x] Gemini Live voice interface
- [x] Groq Whisper STT
- [x] Porcupine wake word detection
- [x] Screen capture & vision
- [x] Desktop automation (mouse, keyboard)
- [x] App launching
- [x] Deep research tool
- [x] File generation
- [x] Spotify API integration (Client ID + Secret)

### v1.1 — Intelligence Layer 🔧
- [ ] Active window detection (stable)
- [ ] Proactive screen commentary (non-command-triggered)
- [ ] Vision-grounded clicking (`vision_click`)
- [ ] Cross-browser history search
- [ ] Goal memory + enforcement system
- [ ] Real OpenCLI browser control
- [ ] StayFree integration
- [ ] Instagram DM (working)
- [ ] Gmail integration

### v1.2 — Autonomy 📋
- [ ] Google Calendar integration
- [ ] Windows startup (Task Scheduler)
- [ ] Multi-LLM switching (all providers)
- [ ] LangGraph orchestration
- [ ] Semantic memory with pruning
- [ ] Self-modification system

### v2.0 — Desktop App 🚀
- [ ] Native Windows app (PyQt6 or Tauri)
- [ ] Dark neon dashboard UI
- [ ] Settings panel with key vault
- [ ] Plugin system
- [ ] Packaged installer (.exe)

---

## Contributing

Friday is a community-driven open source project built under [NexSemble](https://github.com/hackers-reality) — a peer-learning and collaborative tech community based in Pune, India.

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

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

Built by **Arnav** ([@hackers-reality](https://github.com/hackers-reality))  
Co-lead of **NexSemble** — a peer-learning and collaborative tech community based in Pune, Maharashtra, India.

> *"This is not Open Interpreter. This is Friday — the real one."*

---

## Community — Join NexSemble

Friday is built in public as part of **NexSemble** — a community of builders, hackers, and learners who ship real projects together. Come talk Friday, AI agents, and whatever you're building.

<div align="center">

<iframe src="https://discord.com/widget?id=1483417587034493009&theme=dark" width="350" height="500" allowtransparency="true" frameborder="0" sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts"></iframe>

**→ [Join the Discord](https://discord.gg/nexsemble) to chat, contribute, and get help with Friday**

</div>

---

<div align="center">

**Star the repo if Friday helped you. She deserves it.**

[![GitHub stars](https://img.shields.io/github/stars/hackers-reality/friday?style=social)](https://github.com/hackers-reality/friday/stargazers)

</div>
