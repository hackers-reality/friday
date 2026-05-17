# FRIDAY — Getting Started

FRIDAY is a sovereign personal AI OS. This guide will get you from zero to running.

## Prerequisites

- Python 3.11+
- Windows 10/11 (primary target; Linux/macOS partial support)
- Google Gemini API key (set `GEMINI_API_KEY` in `.env`)
- Microphone (for voice mode)

## Quick Install

```bash
git clone https://github.com/hackers-reality/friday.git
cd friday
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API keys:

```env
GEMINI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## Running FRIDAY

### Voice Mode (Default)

```bash
python friday/live.py
```

- Starts FRIDAY with voice I/O (Gemini Live API)
- Wake word: "FRIDAY" (Porcupine)
- Speak naturally; FRIDAY responds with speech

### CLI Mode

```bash
python -m friday.cli status       # System status
python -m friday.cli doctor        # Run diagnostics
python -m friday.cli suit-check    # Pre-flight verification
python -m friday.cli damage-report # System health audit
```

### Dashboard

```bash
python -m friday.cli dashboard start
```

Then open http://localhost:8090 in a browser.

## Core Concepts

### Memory Tree
FRIDAY maintains a persistent Markdown knowledge base under `friday_memory/memory_tree/`. This is your shared memory — write notes, track goals, document preferences. All pages are plain `.md` files you can edit directly.

```bash
python -m friday.cli memory-tree status          # Overview
python -m friday.cli memory-tree read people     # Read a page
python -m friday.cli memory-tree search "goals"  # Full-text search
```

### Sidecar Network
FRIDAY can discover and control other devices on your LAN via a sidecar agent:

```bash
# On another machine: install the sidecar agent
cd sidecar_package
pip install .
friday-sidecar --server http://your-friday-ip:8090 --token YOUR_TOKEN
```

### Snapshots
FRIDAY can snapshot and restore files and directories:

```bash
python -m friday.cli snapshots list
python -m friday.cli snapshots create --label "before-upgrade"
```

### Camera CV
FRIDAY can use your webcam for real-time object detection, people tracking, and scene analysis. The first use auto-downloads a ~7MB MobileNet-SSD model. Camera is accessed via tool, not displayed.

## Directory Layout

```
friday/                        # Main FRIDAY package
  live.py                      # Main live engine (voice + tools)
  cli.py                       # CLI interface
  memory_tree.py               # Memory Tree knowledge base
  model_router.py              # Model provider router
  extension_registry.py        # Extension/MCP registry
  diagnostics.py               # System diagnostics + benchmarks
  cv_engine.py                 # Camera CV engine
  sidecar_network.py           # Sidecar discovery + auth
  ironman.py                   # System health + planning
  dashboard_api.py             # Dashboard HTTP API
  hooks.py                     # Pre/post execution hooks
  snapshots.py                 # Memory snapshots
  autonomy.py                  # Autonomous task queue
  ...

sidecar_package/               # Installable sidecar agent
  friday_sidecar/
    sidecar_agent.py           # Sidecar HTTP server + CLI

friday_memory/                 # Persistent data (DO NOT DELETE)
  memory_tree/                 # Knowledge base files (.md)
  snapshots/                   # File snapshots
  sidecar_network/             # JWT secrets + token registry
  cv/                          # CV state + model files
  ironman_reports/             # System health history
  user_profile.json            # Your profile data
```

## Configuration

FRIDAY stores configuration at `friday_memory/config/`. Key files:

- `model_router.json` — Default models per task type
- `extension_registry.json` — Registered extensions and MCP servers
- `autonomy.json` — Autonomy level settings

## Profile Setup

Create `friday_memory/user_profile.json`:

```json
{
  "name": "Your Name",
  "role": "Your Role",
  "goals": [{"item": "Learn Rust", "_confidence": 0.8}],
  "professional_skills": [{"item": "Python", "_confidence": 0.9}],
  "communication_style": [{"item": "Direct and concise"}],
  "preferences": [
    {"item": "Prefers terminal apps over GUI", "_confidence": 0.7}
  ]
}
```

Run `python -m friday.cli memory-tree update` to sync profile into Memory Tree pages.

## Troubleshooting

### FRIDAY says "Unknown tool"
Some tools (spotify, alexa, home assistant) require additional API keys. Set them in `.env`.

### Camera not working
FRIDAY auto-downloads the MobileNet-SSD model on first CV use. Ensure `friday_memory/cv/` is writable. Without the model, FRIDAY falls back to built-in HOG people detection.

### Sidecar discovery not working
Sidecar discovery uses UDP multicast on `239.255.42.69:42069`. Ensure your firewall allows UDP multicast traffic on your LAN.

### "No module named friday.*"
Run from the project root directory (`E:\open-interpreter`).

## Next Steps

- Read [CLI.md](CLI.md) for full command reference
- Read [EXTENSIONS.md](EXTENSIONS.md) for MCP server setup
- Customize `friday_memory/user_profile.json`
- Explore the dashboard at http://localhost:8090
- Install the sidecar agent on another machine
