# 🤖 Friday - Ultimate Open-Source AI Agent

> *"Hello, Friday!"* - Your personal AI assistant inspired by Iron Man's JARVIS, built to surpass Claude and OpenClaw.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Features

Friday is a next-generation AI agent that combines the best of LangGraph orchestration, Google Gemini intelligence, and proactive assistance.

### ✅ Completed Phases

| Phase | Feature | Status |
|-------|---------|--------|
| **1.1-1.3** | **LangGraph StateGraph** with SQLite checkpoints + MCP Server | ✅ Done |
| **2.1-2.4** | **Screen Awareness** - Active window detection, screenshots, proactive commentary | ✅ Done |
| **3.1-3.4** | **Browser History Search** - Cross-browser (Chrome, Brave, Edge, Firefox, Vivaldi) | ✅ Done |
| **4.1-4.6** | **Goal Memory System** - Google Calendar sync, enforcement, user profile | ✅ Done |
| **5.1-5.3** | **Universal File Generator** - 15+ templates, multi-file generation | ✅ Done |
| **6.1-6.4** | **Desktop App** - PyTauri framework, UI, PyInstaller packaging | ✅ Done |
| **7.1** | **Multi-Agent System** - Supervisor + specialized sub-agents | ✅ Done |
| **7.2** | **Voice Wake Word** - Porcupine/openwakeword integration | ✅ Done |
| **7.3** | **Message Channels** - WhatsApp/Telegram/Discord integration | ✅ Done |
| **7.4** | **Coding Sub-Agent** - Claude Code-style with file ops, testing | ✅ Done |
| **7.5** | **Self-Improvement Loop** - Performance metrics, auto-improvement | ✅ Done |

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/friday.git
cd friday
```

### 2. Run the Install Script

**PowerShell (Recommended):**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**CMD:**
```cmd
install.cmd
```

**Manual Install:**
```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys

Edit the `.env` file with your API keys:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
GROQ_API_KEY=your_groq_api_key_here
PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

Get your Google API key from: https://aistudio.google.com/app/apikey

### 4. Run Friday

```bash
# Check status
python friday_master.py status

# Start multi-agent system
python friday_master.py multi-agent

# Start screen watcher
python friday_master.py screen

# Start voice wake detection
python friday_master.py voice
```

---

## 📁 Project Structure

```
friday/
├── friday_master.py          # Master entry point
├── friday_graph.py           # LangGraph StateGraph + checkpoints
├── friday_mcp.py             # MCP server (30+ tools)
├── friday_live.py            # Live engine with Gemini
├── screen_watcher.py         # Screen awareness
├── proactive_commentary.py   # Vision + LLM commentary
├── browser_history_tools.py  # Cross-browser history search
├── goal_memory.py            # Goals + Google Calendar
├── file_generator.py         # Universal file generator
├── multi_agent.py            # Multi-agent supervisor
├── voice_wake.py             # Voice wake word detection
├── message_channels.py       # WhatsApp/Telegram/Discord
├── coding_agent.py           # Claude Code-style coding agent
├── self_improvement.py       # Self-improvement loop
├── startup_integration.py    # Windows startup integration
├── desktop_app.py            # PyTauri desktop app
├── ui/
│   └── index.html            # Desktop UI
├── friday_memory/            # Persistent memory storage
│   ├── goals.json
│   ├── user_profile.json
│   └── metrics.json
├── install.ps1               # PowerShell install script
├── install.cmd               # CMD install script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 🛠️ Available Commands

```bash
python friday_master.py <command> [options]

Commands:
  status        Check component status
  mcp           Start MCP server
  multi-agent   Start multi-agent system
  screen        Start screen watcher
  goals         Run goal check
  coding        Run coding agent (requires --task)
  improve       Run self-improvement analysis
  voice         Start voice wake detection
  messages      Check message channel status
  all           Start all subsystems
```

---

## 🔧 Key Components

### LangGraph Agent Orchestration
- StateGraph with persistent SQLite checkpoints
- Multi-agent supervisor pattern
- Human-in-the-loop support
- Retry logic and error recovery

### Screen Awareness
- Real-time active window detection (pywinctl)
- Continuous screenshot capture
- Vision-powered contextual commentary
- Proactive assistance based on screen content

### Browser History Intelligence
- Search across Chrome, Brave, Edge, Firefox, Vivaldi, Opera
- Natural language queries
- Time-ordered results
- Goal verification (detect distractions)

### Goal System
- Persistent goal storage
- Google Calendar synchronization
- Automated enforcement (process termination, URL blocking)
- Progress tracking and reminders

### Coding Agent
- Read/write/edit files
- Run shell commands
- Execute tests (pytest/unittest)
- LangGraph-powered workflow

---

## 📋 Requirements

- **Python**: 3.10 or higher
- **OS**: Windows 10/11 (primary), Linux/macOS (secondary)
- **RAM**: 4GB minimum (8GB recommended)
- **API Keys**: Google Gemini API key (required)

### Python Packages
```
langgraph>=1.0
langchain>=0.2
langchain-google-genai>=1.0
mcp>=1.0
pywinctl>=0.0.52
pycaw>=1.5
psutil>=5.9
browser-history>=0.5
google-auth>=2.28
Pillow>=10.0
```

---

## 🔐 Security

- API keys stored in `.env` file (never commit to git)
- `.env` is excluded via `.gitignore`
- SQLite checkpoints stored locally
- No data sent to third parties (except configured APIs)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LangGraph** - Agent orchestration framework
- **Google Gemini** - AI model powering Friday's brain
- **LangChain** - LLM application framework
- **JARVIS (Iron Man)** - Inspiration for the ultimate AI assistant

---

## 📞 Support

- **Issues**: https://github.com/yourusername/friday/issues
- **Discussions**: https://github.com/yourusername/friday/discussions

---

## 🏆 Roadmap

- [ ] Package as standalone `.exe` using PyInstaller
- [ ] Build native desktop app with PyTauri
- [ ] Add more voice wake word options
- [ ] Implement full WhatsApp Web automation
- [ ] Add more coding agent capabilities
- [ ] Create plugin system for custom tools
- [ ] Mobile companion app

---

**Built with ❤️ for the open-source community**
