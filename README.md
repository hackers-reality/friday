<div align="center">

# F.R.I.D.A.Y.
### *Female Replacement Intelligent Digital Assistant Youth*

**A fully autonomous, Iron Man-inspired AI agent for Windows**  
Built by [Arnav](https://github.com/hackers-reality) ┬╖ Co-leader of [NexSemble](https://github.com/hackers-reality)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gemini Live](https://img.shields.io/badge/Gemini-Live%20Audio-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/hackers-reality/friday)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.0.0-blueviolet?style=flat-square)](https://github.com/hackers-reality/friday/releases/tag/v1.0.0)

---

*"Sometimes you gotta run before you can walk."* ΓÇö Tony Stark

</div>

---

## Index

- [What is Friday?](#what-is-friday)
- [Feature Overview](#feature-overview)
  - [≡ƒÄÖ∩╕Å Voice & Audio](#∩╕Å-voice--audio)
  - [≡ƒæü∩╕Å Vision & Screen Awareness](#∩╕Å-vision--screen-awareness)
  - [≡ƒûÑ∩╕Å Desktop Automation & Control](#∩╕Å-desktop-automation--control)
  - [≡ƒîÉ Browser Integration](#-browser-integration)
  - [≡ƒÄ» Goals & Productivity Enforcement](#-goals--productivity-enforcement)
  - [≡ƒô¼ Communication & Messaging](#-communication--messaging)
  - [≡ƒñû AI & LLM](#-ai--llm)
  - [≡ƒºá Memory & User Understanding](#-memory--user-understanding)
  - [≡ƒÜÇ System & Startup](#-system--startup)
  - [≡ƒû╝∩╕Å Dashboard & UI](#-dashboard--ui)
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
- [Community ΓÇö Join NexSemble](#community--join-nexsemble)

---

## What is Friday?

Friday is not a chatbot. It is a **fully autonomous desktop AI agent** that lives on your Windows machine, watches your screen, listens to your voice, understands your goals, and takes action ΓÇö [...]

Think of it as having a real-world version of Tony Stark's FRIDAY running on your PC. It monitors what you're doing, proactively comments and helps, controls your entire desktop via voice, manages[...]

What makes Friday different from other agents: **she learns who you are**. Import your conversation history from Claude, ChatGPT, or Gemini and Friday extracts your preferences, communication styl[...]

Friday is **open source**, **Windows-native**, **self-hosted**, and built to eventually compete with commercial agents like Devin, Cline, and Claude Code.

---

## Feature Overview

### ≡ƒÄÖ∩╕Å Voice & Audio
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live native audio | Γ£à Working | Primary voice interface via `friday_live.py` |
| Groq Whisper STT | Γ£à Working | Fallback speech-to-text |
| Porcupine wake word | Γ£à Working | "Hey Friday" detection via `voice_wake.py` |
| Multi-TTS engine support | ≡ƒöº In Progress | ElevenLabs, Google TTS, pyttsx3 |
| Real-time streaming response | ≡ƒöº In Progress | Typing effect output |

### ≡ƒæü∩╕Å Vision & Screen Awareness
| Feature | Status | Details |
|---------|--------|---------|
| Real-time screen capture | Γ£à Working | `friday_vision.py` via PIL/mss |
| Active window detection | Γ£à Working | `screen_watcher.py` via pywinctl |
| Gemini Vision analysis | Γ£à Working | Screen-to-description pipeline |
| Vision-grounded clicking | ≡ƒöº In Progress | `vision_click()` ΓÇö finds elements by description |
| Proactive screen commentary | ≡ƒöº In Progress | Background monitor with unsolicited observations |
| Error detection on screen | ≡ƒöº In Progress | Detects visible Python/JS errors |
| Visual search | Γ£à Working | "Friday find the word X on screen" |

### ≡ƒûÑ∩╕Å Desktop Automation & Control
| Feature | Status | Details |
|---------|--------|---------|
| Mouse & keyboard control | Γ£à Working | pyautogui-based via `friday_tools.py` |
| App launching & closing | Γ£à Working | `open_app()`, `close_app()` |
| Spotify control | Γ£à Working | Full Spotify API (Client ID + Secret) ΓÇö search, play, queue, volume |
| Netflix/streaming control | ≡ƒöº In Progress | Vision-based navigation |
| File system access | Γ£à Working | With authority checks |
| RPA workflows | Γ£à Working | `friday_automation.py` |
| Game launching | ≡ƒöº In Progress | e.g., "Play Bloxfruits on Roblox" |

### ≡ƒîÉ Browser Integration
| Feature | Status | Details |
|---------|--------|---------|
| Cross-browser history search | ≡ƒöº In Progress | Chrome, Brave, Edge, Opera SQLite |
| Open URL from history by voice | ≡ƒöº In Progress | "Open that Jarvis repo I was looking at" |
| OpenCLI browser automation | Γ£à Working | CDP-based + `@jackwener/opencli` |
| Browser navigation by voice | Γ£à Working | Opens URLs, searches |

### ≡ƒÄ» Goals & Productivity Enforcement
| Feature | Status | Details |
|---------|--------|---------|
| Goal memory (persistent) | ≡ƒöº In Progress | `goal_memory.py` + `friday_memory/goals.json` |
| Course/deadline tracking | ≡ƒöº In Progress | Monitors browser history for progress |
| Google Calendar integration | ≡ƒôï Planned | Class times, exams, events |
| Proactive scolding | ≡ƒöº In Progress | Escalating intervention system |
| Tab closing enforcement | ≡ƒöº In Progress | Closes distracting tabs, reopens course URL |
| StayFree integration | ≡ƒöº In Progress | Reads local usage data, triggers blocks |

### ≡ƒô¼ Communication & Messaging
| Feature | Status | Details |
|---------|--------|---------|
| Email read/draft/send | ≡ƒöº In Progress | `friday_gmail.py` via Gmail API |
| Instagram DM | ≡ƒöº In Progress | `instagram_messenger.py` via OpenCLI |
| Alexa/smart home control | ≡ƒöº In Progress | `alexa_webhook_server.py` |
| WhatsApp messaging | ≡ƒôï Planned | Via web automation |

### ≡ƒñû AI & LLM
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live (primary) | Γ£à Working | Cloud-hosted, real-time audio (only LLM supported right now) |
| Other LLMs (Claude, GPT, Groq, Ollama) | ≡ƒöº Coming Soon | Use Gemini API key for now |
| Multi-LLM switching | ≡ƒôï Planned | `llm_manager.py` ΓÇö coming soon |
| LangGraph orchestration | ≡ƒöº In Progress | `friday_langgraph.py` (syntax fixed) |
| Deep research tool | Γ£à Working | Real-time web research + reports |
| Self-modifying code | ≡ƒöº In Progress | `self_modification.py` |

### ≡ƒºá Memory & User Understanding
| Feature | Status | Details |
|---------|--------|---------|
| Cross-chatbot history import | Γ£à Working | Import chats from Claude, ChatGPT, Gemini ΓÇö Friday reads and learns from them |
| Preference extraction | Γ£à Working | Parses imported conversations to build a user profile: likes, dislikes, habits, tone |
| Personality adaptation | Γ£à Working | Friday adjusts how she speaks based on your learned profile ΓÇö no cold starts |
| Persistent memory vault | ≡ƒöº In Progress | `vector_memory.py` ΓÇö stores facts, preferences, patterns across sessions |
| Semantic memory search | ≡ƒöº In Progress | Pulls relevant past context before every response |
| Knowledge vault | ≡ƒöº In Progress | Combined LLM knowledge + everything Friday has learned about you |


| Feature | Status | Details |
|---------|--------|---------|
| Universal file generator | ≡ƒöº In Progress | `file_generator.py` ΓÇö all formats |
| Code files | Γ£à Working | .py, .js, .ts, .html, .css, .sh, .yaml |
| Documents | ≡ƒöº In Progress | .md, .txt, .docx, .pdf |
| Config/server files | ≡ƒöº In Progress | Dockerfile, nginx.conf, .env |

### ≡ƒÜÇ System & Startup
| Feature | Status | Details |
|---------|--------|---------|
| Windows startup on boot | ≡ƒöº In Progress | `startup_integration.py` via Task Scheduler |
| Session keepalive | Γ£à Working | `keepalive_task()` prevents Gemini timeout |
| Auto-reconnect on drop | Γ£à Working | 5s reconnect loop |
| Background operation | Γ£à Working | asyncio task-based |

### ≡ƒû╝∩╕Å Dashboard & UI
| Feature | Status | Details |
|---------|--------|---------|
| Desktop UI | ≡ƒöº In Progress | `desktop_app.py` ΓÇö PyQt6/Tkinter |
| Dark neon theme | ≡ƒöº In Progress | Navy/cyan/teal aesthetic |
| Memory/knowledge panel | ≡ƒôï Planned | Shows goals, active LLM, memory |
| Settings panel | ≡ƒôï Planned | LLM switching, API keys, toggles |

---

## Architecture

```
D:\F.R.I.D.A.Y\
Γöé
Γö£ΓöÇΓöÇ friday_live.py          ΓåÉ PRIMARY ENTRY POINT
Γöé   Γö£ΓöÇΓöÇ Gemini Live session (native audio)
Γöé   Γö£ΓöÇΓöÇ keepalive_task() ΓÇö prevents GOAWAY timeout
Γöé   Γö£ΓöÇΓöÇ background_monitor() ΓÇö screen watcher loop
Γöé   ΓööΓöÇΓöÇ execute_tool() ΓÇö routes voice commands to tools
Γöé
Γö£ΓöÇΓöÇ friday_tools.py         ΓåÉ TOOL EXECUTION ENGINE
Γöé   Γö£ΓöÇΓöÇ Desktop automation (mouse, keyboard, apps)
Γöé   Γö£ΓöÇΓöÇ Browser control (OpenCLI + CDP)
Γöé   Γö£ΓöÇΓöÇ File operations
Γöé   Γö£ΓöÇΓöÇ Spotify, Netflix, email, Instagram
Γöé   ΓööΓöÇΓöÇ vision_click() ΓÇö Gemini Vision-grounded clicking
Γöé
Γö£ΓöÇΓöÇ friday_vision.py        ΓåÉ VISION PIPELINE
Γöé   Γö£ΓöÇΓöÇ Screen capture (mss + PIL)
Γöé   Γö£ΓöÇΓöÇ Gemini Vision analysis
Γöé   Γö£ΓöÇΓöÇ vision_find_element() ΓÇö locates UI elements
Γöé   Γö£ΓöÇΓöÇ vision_describe_screen() ΓÇö proactive commentary
Γöé   ΓööΓöÇΓöÇ OCR, QR, face detection
Γöé
Γö£ΓöÇΓöÇ friday_automation.py    ΓåÉ RPA & BROWSER AUTOMATION
Γöé   Γö£ΓöÇΓöÇ BrowserAutomation (Selenium/Playwright)
Γöé   Γö£ΓöÇΓöÇ FileAutomation (batch ops, organizer)
Γöé   Γö£ΓöÇΓöÇ SystemAutomation (commands, scheduler)
Γöé   ΓööΓöÇΓöÇ RPA workflow engine
Γöé
Γö£ΓöÇΓöÇ opencli_integration.py  ΓåÉ BROWSER CONTROL
Γöé   Γö£ΓöÇΓöÇ Real @jackwener/opencli binary calls
Γöé   Γö£ΓöÇΓöÇ Instagram DM via OpenCLI
Γöé   ΓööΓöÇΓöÇ CDP fallback
Γöé
Γö£ΓöÇΓöÇ goal_memory.py          ΓåÉ GOAL & PRODUCTIVITY SYSTEM
Γöé   Γö£ΓöÇΓöÇ Persistent goal storage (friday_memory/goals.json)
Γöé   Γö£ΓöÇΓöÇ Browser history cross-reference
Γöé   Γö£ΓöÇΓöÇ Escalating scolding (levels 0-3)
Γöé   ΓööΓöÇΓöÇ Tab enforcement
Γöé
Γö£ΓöÇΓöÇ browser_history_tools.py ΓåÉ HISTORY SEARCH
Γöé   Γö£ΓöÇΓöÇ Chrome, Brave, Edge, Opera SQLite reading
Γöé   Γö£ΓöÇΓöÇ Fuzzy search across all browsers
Γöé   ΓööΓöÇΓöÇ find_repo_in_history()
Γöé
Γö£ΓöÇΓöÇ llm_manager.py          ΓåÉ MULTI-LLM SWITCHER
Γöé   Γö£ΓöÇΓöÇ Gemini, Claude, GPT, Groq, Ollama
Γöé   ΓööΓöÇΓöÇ Auto-detects available keys
Γöé
Γö£ΓöÇΓöÇ proactive_screen_monitor.py ΓåÉ BACKGROUND WATCHER
Γöé   Γö£ΓöÇΓöÇ Screenshot every 30s
Γöé   Γö£ΓöÇΓöÇ Gemini Vision analysis
Γöé   ΓööΓöÇΓöÇ Unsolicited commentary engine
Γöé
Γö£ΓöÇΓöÇ stayfree_bridge.py      ΓåÉ STAYFREE INTEGRATION
Γöé   Γö£ΓöÇΓöÇ Reads local StayFree data files
Γöé   Γö£ΓöÇΓöÇ Chrome extension storage bridge
Γöé   ΓööΓöÇΓöÇ Goal enforcement + site blocking
Γöé
Γö£ΓöÇΓöÇ friday_langgraph.py     ΓåÉ AGENT ORCHESTRATION
Γöé   ΓööΓöÇΓöÇ LangGraph-based multi-step reasoning
Γöé
Γö£ΓöÇΓöÇ friday_memory/          ΓåÉ PERSISTENT MEMORY
Γöé   Γö£ΓöÇΓöÇ goals.json
Γöé   Γö£ΓöÇΓöÇ memory.json
Γöé   ΓööΓöÇΓöÇ research_history/
Γöé
ΓööΓöÇΓöÇ friday_reports/         ΓåÉ GENERATED REPORTS
```

---

## Quick Start

### Prerequisites

- Windows 10 or 11
- Python 3.11+
- Node.js 21+ (for OpenCLI)
- [Google API key (Gemini Live)](https://ai.google.dev/) ΓÇö required
- [Picovoice Access Key](https://console.picovoice.ai/) ΓÇö required
- [Spotify API credentials](https://developer.spotify.com/dashboard) ΓÇö required
- [Groq API key](https://console.groq.com/) (optional, for Whisper STT)

Other LLM providers (Claude, OpenAI, Groq text, Ollama) are coming soon ΓÇö use your Gemini API key for now.

## Installation


### fully Automatic installtion
```bash

# One-liner (PowerShell, full install + prompts)
powershell -ExecutionPolicy Bypass -NoProfile -Command "& { git clone https://github.com/hackers-reality/friday.git; Set-Location friday; pip install -r requirements.txt; npm install -g @jackwene[...]
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

# Spotify (required) ΓÇö https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Optional ΓÇö enables additional features
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here

# Ollama (coming soon; never localhost ΓÇö use actual IP or hostname)
OLLAMA_BASE_URL=http://192.168.1.x:11434

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
"Friday, open the Jarvis repo I was looking at ΓÇö the one by vierisid"
"Friday, what was I reading about LangGraph earlier?"
"Friday, open my IITM course"
```

### Messaging & Communication
```
"Friday, message Mangesh on Instagram ΓÇö tell him I'll be back soon"
"Friday, send an email to dev@example.com with a job offer letter from NexSemble"
"Friday, read my latest emails"
```

### Goals & Productivity
```
"Friday, I have an IITM 8-week course ending May 31st at iitm.course.url ΓÇö track it"
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
"Friday, I've imported my Claude chat history ΓÇö learn from it"
"Friday, what do you know about me?"
"Friday, update your understanding of my preferences"
"Friday, forget what I told you about X"
```

---

## Module Reference

| File | Purpose |
|------|---------|
| `friday_live.py` | Primary entry point. Gemini Live session, keepalive, tool routing |
| `friday_tools.py` | All tool implementations ΓÇö desktop, browser, files, media |
| `friday_vision.py` | Vision pipeline ΓÇö capture, Gemini analysis, click targeting |
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

### v1.0 ΓÇö Foundation Γ£à
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

### v1.1 ΓÇö Intelligence Layer ≡ƒöº
- [ ] Active window detection (stable)
- [ ] Proactive screen commentary (non-command-triggered)
- [ ] Vision-grounded clicking (`vision_click`)
- [ ] Cross-browser history search
- [ ] Goal memory + enforcement system
- [ ] Real OpenCLI browser control
- [ ] StayFree integration
- [ ] Instagram DM (working)
- [ ] Gmail integration

### v1.2 ΓÇö Autonomy ≡ƒôï
- [ ] Google Calendar integration
- [ ] Windows startup (Task Scheduler)
- [ ] Multi-LLM switching (all providers)
- [ ] LangGraph orchestration
- [ ] Semantic memory with pruning
- [ ] Self-modification system

### v2.0 ΓÇö Desktop App ≡ƒÜÇ
- [ ] Native Windows app (PyQt6 or Tauri)
- [ ] Dark neon dashboard UI
- [ ] Settings panel with key vault
- [ ] Plugin system
- [ ] Packaged installer (.exe)

---

## Contributing

Friday is an open source project built solely by Arnav, shared publicly through [NexSemble](https://github.com/hackers-reality) ΓÇö a peer-learning and collaborative tech community in Pune, India[...]

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
- Never hardcode `localhost` ΓÇö use `OLLAMA_BASE_URL` from env
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

MIT License ΓÇö see [LICENSE](LICENSE) for details.

---

## Author

**Friday is solely built by Arnav** ([@hackers-reality](https://github.com/hackers-reality))  
Co-leader of [NexSemble](https://github.com/hackers-reality) ΓÇö a peer-learning and collaborative tech community based in Pune, Maharashtra, India.

> *"This is not a chatbot . This is Friday ΓÇö the real one."*

---

## Community ΓÇö Join NexSemble

Friday is built in public and shared through **NexSemble** ΓÇö a community of builders, hackers, and learners who ship real projects together. Come talk Friday, AI agents, and whatever you're bui[...]

<div align="center">

[![Discord](https://img.shields.io/discord/1483417587034493009?style=for-the-badge&logo=discord&logoColor=white&label=NexSemble%20Discord&color=5865F2)](https://discord.gg/Ttqz3jHGk2)

**[ΓåÆ Join the NexSemble Discord](https://discord.gg/Ttqz3jHGk2)**

</div>

---

<div align="center">

**Star the repo if Friday helped you. She deserves it.**

[![GitHub stars](https://img.shields.io/github/stars/hackers-reality/friday?style=social)](https://github.com/hackers-reality/friday/stargazers)

</div>


