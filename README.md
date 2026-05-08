<div align="center">

# F.R.I.D.A.Y.
### *Female Replacement Intelligent Digital Assistant Youth*

**A fully autonomous, Iron Man-inspired AI agent for Windows**  
Built by [Arnav](https://github.com/hackers-reality) â”¬â•– Co-leader of [NexSemble](https://github.com/hackers-reality)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Gemini Live](https://img.shields.io/badge/Gemini-Live%20Audio-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)](https://github.com/hackers-reality/friday)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.0.0-blueviolet?style=flat-square)](https://github.com/hackers-reality/friday/releases/tag/v1.0.0)

---

*"Sometimes you gotta run before you can walk."* Î“Ã‡Ã¶ Tony Stark

</div>

---

## Index

- [What is Friday?](#what-is-friday)
- [Feature Overview](#feature-overview)
  - [â‰¡Æ’Ã„Ã–âˆ©â••Ã… Voice & Audio](#âˆ©â••Ã…-voice--audio)
  - [â‰¡Æ’Ã¦Ã¼âˆ©â••Ã… Vision & Screen Awareness](#âˆ©â••Ã…-vision--screen-awareness)
  - [â‰¡Æ’Ã»Ã‘âˆ©â••Ã… Desktop Automation & Control](#âˆ©â••Ã…-desktop-automation--control)
  - [â‰¡Æ’Ã®Ã‰ Browser Integration](#-browser-integration)
  - [â‰¡Æ’Ã„Â» Goals & Productivity Enforcement](#-goals--productivity-enforcement)
  - [â‰¡Æ’Ã´Â¼ Communication & Messaging](#-communication--messaging)
  - [â‰¡Æ’Ã±Ã» AI & LLM](#-ai--llm)
  - [â‰¡Æ’ÂºÃ¡ Memory & User Understanding](#-memory--user-understanding)
  - [â‰¡Æ’ÃœÃ‡ System & Startup](#-system--startup)
  - [â‰¡Æ’Ã»â•âˆ©â••Ã… Dashboard & UI](#-dashboard--ui)
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
- [Community Î“Ã‡Ã¶ Join NexSemble](#community--join-nexsemble)

---

## What is Friday?

Friday is not a chatbot. It is a **fully autonomous desktop AI agent** that lives on your Windows machine, watches your screen, listens to your voice, understands your goals, and takes action Î“Ã‡Ã¶ [...]

Think of it as having a real-world version of Tony Stark's FRIDAY running on your PC. It monitors what you're doing, proactively comments and helps, controls your entire desktop via voice, manages[...]

What makes Friday different from other agents: **she learns who you are**. Import your conversation history from Claude, ChatGPT, or Gemini and Friday extracts your preferences, communication styl[...]

Friday is **open source**, **Windows-native**, **self-hosted**, and built to eventually compete with commercial agents like Devin, Cline, and Claude Code.

---

## Feature Overview

### â‰¡Æ’Ã„Ã–âˆ©â••Ã… Voice & Audio
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live native audio | Î“Â£Ã  Working | Primary voice interface via `friday_live.py` |
| Groq Whisper STT | Î“Â£Ã  Working | Fallback speech-to-text |
| Porcupine wake word | Î“Â£Ã  Working | "Hey Friday" detection via `voice_wake.py` |
| Multi-TTS engine support | â‰¡Æ’Ã¶Âº In Progress | ElevenLabs, Google TTS, pyttsx3 |
| Real-time streaming response | â‰¡Æ’Ã¶Âº In Progress | Typing effect output |

### â‰¡Æ’Ã¦Ã¼âˆ©â••Ã… Vision & Screen Awareness
| Feature | Status | Details |
|---------|--------|---------|
| Real-time screen capture | Î“Â£Ã  Working | `friday_vision.py` via PIL/mss |
| Active window detection | Î“Â£Ã  Working | `screen_watcher.py` via pywinctl |
| Gemini Vision analysis | Î“Â£Ã  Working | Screen-to-description pipeline |
| Vision-grounded clicking | â‰¡Æ’Ã¶Âº In Progress | `vision_click()` Î“Ã‡Ã¶ finds elements by description |
| Proactive screen commentary | ✅ Working | Background monitor with unsolicited observations |
| Error detection on screen | â‰¡Æ’Ã¶Âº In Progress | Detects visible Python/JS errors |
| Visual search | Î“Â£Ã  Working | "Friday find the word X on screen" |

### â‰¡Æ’Ã»Ã‘âˆ©â••Ã… Desktop Automation & Control
| Feature | Status | Details |
|---------|--------|---------|
| Mouse & keyboard control | Î“Â£Ã  Working | pyautogui-based via `friday_tools.py` |
| App launching & closing | Î“Â£Ã  Working | `open_app()`, `close_app()` |
| Spotify control | Î“Â£Ã  Working | Full Spotify API (Client ID + Secret) Î“Ã‡Ã¶ search, play, queue, volume |
| Netflix/streaming control | â‰¡Æ’Ã¶Âº In Progress | Vision-based navigation |
| File system access | Î“Â£Ã  Working | With authority checks |
| RPA workflows | Î“Â£Ã  Working | `friday_automation.py` |
| Game launching | â‰¡Æ’Ã¶Âº In Progress | e.g., "Play Bloxfruits on Roblox" |

### â‰¡Æ’Ã®Ã‰ Browser Integration
| Feature | Status | Details |
|---------|--------|---------|
| Cross-browser history search | ✅ Working | Chrome, Brave, Edge, Opera SQLite |
| Open URL from history by voice | ✅ Working | "Open that Jarvis repo I was looking at" |
| OpenCLI browser automation | Î“Â£Ã  Working | CDP-based + `@jackwener/opencli` |
| Browser navigation by voice | Î“Â£Ã  Working | Opens URLs, searches |

### â‰¡Æ’Ã„Â» Goals & Productivity Enforcement
| Feature | Status | Details |
|---------|--------|---------|
| Goal memory (persistent) | ✅ Working | `goal_memory.py` + `friday_memory/goals.json` |
| Course/deadline tracking | â‰¡Æ’Ã¶Âº In Progress | Monitors browser history for progress |
| Google Calendar integration | â‰¡Æ’Ã´Ã¯ Planned | Class times, exams, events |
| Proactive scolding | ✅ Working | Escalating intervention system |
| Tab closing enforcement | â‰¡Æ’Ã¶Âº In Progress | Closes distracting tabs, reopens course URL |
| StayFree integration | â‰¡Æ’Ã¶Âº In Progress | Reads local usage data, triggers blocks |

### â‰¡Æ’Ã´Â¼ Communication & Messaging
| Feature | Status | Details |
|---------|--------|---------|
| Email read/draft/send | ✅ Working | `friday_gmail.py` via Gmail API |
| Instagram DM | ✅ Working | `instagram_messenger.py` via OpenCLI |
| Alexa/smart home control | ✅ Working | `alexa_webhook_server.py` |
| WhatsApp messaging | â‰¡Æ’Ã´Ã¯ Planned | Via web automation |

### â‰¡Æ’Ã±Ã» AI & LLM
| Feature | Status | Details |
|---------|--------|---------|
| Gemini Live (primary) | Î“Â£Ã  Working | Cloud-hosted, real-time audio (only LLM supported right now) |
| Other LLMs (Claude, GPT, Groq, Ollama) | â‰¡Æ’Ã¶Âº Coming Soon | Use Gemini API key for now |
| Multi-LLM switching | â‰¡Æ’Ã´Ã¯ Planned | `llm_manager.py` Î“Ã‡Ã¶ coming soon |
| LangGraph orchestration | â‰¡Æ’Ã¶Âº In Progress | `friday_langgraph.py` (syntax fixed) |
| Deep research tool | Î“Â£Ã  Working | Real-time web research + reports |
| Self-modifying code | â‰¡Æ’Ã¶Âº In Progress | `self_modification.py` |

### â‰¡Æ’ÂºÃ¡ Memory & User Understanding
| Feature | Status | Details |
|---------|--------|---------|
| Cross-chatbot history import | Î“Â£Ã  Working | Import chats from Claude, ChatGPT, Gemini Î“Ã‡Ã¶ Friday reads and learns from them |
| Preference extraction | Î“Â£Ã  Working | Parses imported conversations to build a user profile: likes, dislikes, habits, tone |
| Personality adaptation | Î“Â£Ã  Working | Friday adjusts how she speaks based on your learned profile Î“Ã‡Ã¶ no cold starts |
| Persistent memory vault | â‰¡Æ’Ã¶Âº In Progress | `vector_memory.py` Î“Ã‡Ã¶ stores facts, preferences, patterns across sessions |
| Semantic memory search | â‰¡Æ’Ã¶Âº In Progress | Pulls relevant past context before every response |
| Knowledge vault | â‰¡Æ’Ã¶Âº In Progress | Combined LLM knowledge + everything Friday has learned about you |


| Feature | Status | Details |
|---------|--------|---------|
| Universal file generator | ✅ Working | `file_generator.py` Î“Ã‡Ã¶ all formats |
| Code files | Î“Â£Ã  Working | .py, .js, .ts, .html, .css, .sh, .yaml |
| Documents | â‰¡Æ’Ã¶Âº In Progress | .md, .txt, .docx, .pdf |
| Config/server files | â‰¡Æ’Ã¶Âº In Progress | Dockerfile, nginx.conf, .env |

### â‰¡Æ’ÃœÃ‡ System & Startup
| Feature | Status | Details |
|---------|--------|---------|
| Windows startup on boot | â‰¡Æ’Ã¶Âº In Progress | `startup_integration.py` via Task Scheduler |
| Session keepalive | Î“Â£Ã  Working | `keepalive_task()` prevents Gemini timeout |
| Auto-reconnect on drop | ✅ Working | 5s reconnect loop |
| Background operation | Î“Â£Ã  Working | asyncio task-based |

### â‰¡Æ’Ã»â•âˆ©â••Ã… Dashboard & UI
| Feature | Status | Details |
|---------|--------|---------|
| Desktop UI | â‰¡Æ’Ã¶Âº In Progress | `desktop_app.py` Î“Ã‡Ã¶ PyQt6/Tkinter |
| Dark neon theme | â‰¡Æ’Ã¶Âº In Progress | Navy/cyan/teal aesthetic |
| Memory/knowledge panel | â‰¡Æ’Ã´Ã¯ Planned | Shows goals, active LLM, memory |
| Settings panel | â‰¡Æ’Ã´Ã¯ Planned | LLM switching, API keys, toggles |

---

## Architecture

```
D:\F.R.I.D.A.Y\
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_live.py          Î“Ã¥Ã‰ PRIMARY ENTRY POINT
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Gemini Live session (native audio)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ keepalive_task() Î“Ã‡Ã¶ prevents GOAWAY timeout
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ background_monitor() Î“Ã‡Ã¶ screen watcher loop
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ execute_tool() Î“Ã‡Ã¶ routes voice commands to tools
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_tools.py         Î“Ã¥Ã‰ TOOL EXECUTION ENGINE
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Desktop automation (mouse, keyboard, apps)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Browser control (OpenCLI + CDP)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ File operations
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Spotify, Netflix, email, Instagram
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ vision_click() Î“Ã‡Ã¶ Gemini Vision-grounded clicking
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_vision.py        Î“Ã¥Ã‰ VISION PIPELINE
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Screen capture (mss + PIL)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Gemini Vision analysis
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ vision_find_element() Î“Ã‡Ã¶ locates UI elements
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ vision_describe_screen() Î“Ã‡Ã¶ proactive commentary
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ OCR, QR, face detection
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_automation.py    Î“Ã¥Ã‰ RPA & BROWSER AUTOMATION
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ BrowserAutomation (Selenium/Playwright)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ FileAutomation (batch ops, organizer)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ SystemAutomation (commands, scheduler)
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ RPA workflow engine
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ opencli_integration.py  Î“Ã¥Ã‰ BROWSER CONTROL
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Real @jackwener/opencli binary calls
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Instagram DM via OpenCLI
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ CDP fallback
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ goal_memory.py          Î“Ã¥Ã‰ GOAL & PRODUCTIVITY SYSTEM
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Persistent goal storage (friday_memory/goals.json)
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Browser history cross-reference
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Escalating scolding (levels 0-3)
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ Tab enforcement
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ browser_history_tools.py Î“Ã¥Ã‰ HISTORY SEARCH
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Chrome, Brave, Edge, Opera SQLite reading
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Fuzzy search across all browsers
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ find_repo_in_history()
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ llm_manager.py          Î“Ã¥Ã‰ MULTI-LLM SWITCHER
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Gemini, Claude, GPT, Groq, Ollama
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ Auto-detects available keys
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ proactive_screen_monitor.py Î“Ã¥Ã‰ BACKGROUND WATCHER
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Screenshot every 30s
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Gemini Vision analysis
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ Unsolicited commentary engine
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ stayfree_bridge.py      Î“Ã¥Ã‰ STAYFREE INTEGRATION
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Reads local StayFree data files
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ Chrome extension storage bridge
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ Goal enforcement + site blocking
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_langgraph.py     Î“Ã¥Ã‰ AGENT ORCHESTRATION
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ LangGraph-based multi-step reasoning
Î“Ã¶Ã©
Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_memory/          Î“Ã¥Ã‰ PERSISTENT MEMORY
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ goals.json
Î“Ã¶Ã©   Î“Ã¶Â£Î“Ã¶Ã‡Î“Ã¶Ã‡ memory.json
Î“Ã¶Ã©   Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ research_history/
Î“Ã¶Ã©
Î“Ã¶Ã¶Î“Ã¶Ã‡Î“Ã¶Ã‡ friday_reports/         Î“Ã¥Ã‰ GENERATED REPORTS
```

---

## Quick Start

### Prerequisites

- Windows 10 or 11
- Python 3.11+
- Node.js 21+ (for OpenCLI)
- [Google API key (Gemini Live)](https://ai.google.dev/) Î“Ã‡Ã¶ required
- [Picovoice Access Key](https://console.picovoice.ai/) Î“Ã‡Ã¶ required
- [Spotify API credentials](https://developer.spotify.com/dashboard) Î“Ã‡Ã¶ required
- [Groq API key](https://console.groq.com/) (optional, for Whisper STT)

Other LLM providers (Claude, OpenAI, Groq text, Ollama) are coming soon Î“Ã‡Ã¶ use your Gemini API key for now.

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

# Spotify (required) Î“Ã‡Ã¶ https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Optional Î“Ã‡Ã¶ enables additional features
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
OPENAI_API_KEY=your_openai_key_here

# Ollama (coming soon; never localhost Î“Ã‡Ã¶ use actual IP or hostname)
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
"Friday, open the Jarvis repo I was looking at Î“Ã‡Ã¶ the one by vierisid"
"Friday, what was I reading about LangGraph earlier?"
"Friday, open my IITM course"
```

### Messaging & Communication
```
"Friday, message Mangesh on Instagram Î“Ã‡Ã¶ tell him I'll be back soon"
"Friday, send an email to dev@example.com with a job offer letter from NexSemble"
"Friday, read my latest emails"
```

### Goals & Productivity
```
"Friday, I have an IITM 8-week course ending May 31st at iitm.course.url Î“Ã‡Ã¶ track it"
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
"Friday, I've imported my Claude chat history Î“Ã‡Ã¶ learn from it"
"Friday, what do you know about me?"
"Friday, update your understanding of my preferences"
"Friday, forget what I told you about X"
```

---

## Module Reference

| File | Purpose |
|------|---------|
| `friday_live.py` | Primary entry point. Gemini Live session, keepalive, tool routing |
| `friday_tools.py` | All tool implementations Î“Ã‡Ã¶ desktop, browser, files, media |
| `friday_vision.py` | Vision pipeline Î“Ã‡Ã¶ capture, Gemini analysis, click targeting |
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

### v1.0 Î“Ã‡Ã¶ Foundation Î“Â£Ã 
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

### v1.1 Î“Ã‡Ã¶ Intelligence Layer â‰¡Æ’Ã¶Âº
- [ ] Active window detection (stable)
- [x] Proactive screen commentary (non-command-triggered)
- [ ] Vision-grounded clicking (`vision_click`)
- [x] Cross-browser history search
- [x] Goal memory + enforcement system
- [x] Real OpenCLI browser control
- [x] StayFree integration
- [x] Instagram DM (working)
- [x] Gmail integration

### v1.2 Î“Ã‡Ã¶ Autonomy â‰¡Æ’Ã´Ã¯
- [ ] Google Calendar integration
- [ ] Windows startup (Task Scheduler)
- [ ] Multi-LLM switching (all providers)
- [ ] LangGraph orchestration
- [ ] Semantic memory with pruning
- [ ] Self-modification system

### v2.0 Î“Ã‡Ã¶ Desktop App â‰¡Æ’ÃœÃ‡
- [ ] Native Windows app (PyQt6 or Tauri)
- [ ] Dark neon dashboard UI
- [ ] Settings panel with key vault
- [ ] Plugin system
- [ ] Packaged installer (.exe)

---

## Contributing

Friday is an open source project built solely by Arnav, shared publicly through [NexSemble](https://github.com/hackers-reality) Î“Ã‡Ã¶ a peer-learning and collaborative tech community in Pune, India[...]

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
- Never hardcode `localhost` Î“Ã‡Ã¶ use `OLLAMA_BASE_URL` from env
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

MIT License Î“Ã‡Ã¶ see [LICENSE](LICENSE) for details.

---

## Author

**Friday is solely built by Arnav** ([@hackers-reality](https://github.com/hackers-reality))  
Co-leader of [NexSemble](https://github.com/hackers-reality) Î“Ã‡Ã¶ a peer-learning and collaborative tech community based in Pune, Maharashtra, India.

> *"This is not a chatbot . This is Friday Î“Ã‡Ã¶ the real one."*

---

## Community Î“Ã‡Ã¶ Join NexSemble

Friday is built in public and shared through **NexSemble** Î“Ã‡Ã¶ a community of builders, hackers, and learners who ship real projects together. Come talk Friday, AI agents, and whatever you're bui[...]

<div align="center">

[![Discord](https://img.shields.io/discord/1483417587034493009?style=for-the-badge&logo=discord&logoColor=white&label=NexSemble%20Discord&color=5865F2)](https://discord.gg/Ttqz3jHGk2)

**[Î“Ã¥Ã† Join the NexSemble Discord](https://discord.gg/Ttqz3jHGk2)**

</div>

---

<div align="center">

**Star the repo if Friday helped you. She deserves it.**

[![GitHub stars](https://img.shields.io/github/stars/hackers-reality/friday?style=social)](https://github.com/hackers-reality/friday/stargazers)

</div>

