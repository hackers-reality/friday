# FRIDAY Capabilities

## Overview

FRIDAY has 40+ documented capabilities across voice, vision, desktop, browser, memory, code, GitHub, smart home, and self-improvement domains.

## Status Key

| Status | Meaning |
|--------|---------|
| **stable** | Works reliably in production |
| **partial** | Works but has known limitations |
| **experimental** | Recently added, may have rough edges |
| **planned** | Not yet implemented |

## Current Coverage

| Status | Count |
|--------|-------|
| Stable | ~35 |
| Partial | ~6 |
| Experimental | ~2 |
| Planned | ~2 |
| **Total** | **~45** |

## Full Report

A complete capability report is auto-generated at:

→ `friday_reports/capability_report.md`

To regenerate:

```python
from friday.capabilities import generate_capability_report
generate_capability_report()
```

## Key Systems

- **Voice**: Gemini Live bidirectional audio streaming
- **Vision**: Screen capture, analysis, vision-click
- **Desktop**: Mouse, keyboard, app/window management
- **Browser**: Full OpenCLI automation (click, type, navigate, tabs, eval)
- **Memory**: Profile extraction, TF-IDF, vector, episodic, KG, confidence, decay, review, doctor
- **Sidecars**: 8 types, heartbeat, dispatch skeleton
- **Autonomy**: Task queue, retry, reflection
- **Authority**: 9 risk levels, policy engine, audit log
- **Snapshots**: File/directory snapshot, restore, diff
- **Tool Registry**: Central metadata for 150+ tools
- **Code**: Deep code review, file generation, self-modification
- **GitHub**: Full API (files, PRs, issues, repos, search)
- **Smart Home**: Alexa, Home Assistant, IoT
- **Spotify**: Playback control
- **Gmail**: Read, send, draft
- **Dashboard**: HTML UI + REST API (17 endpoints)
- **Self-Improvement**: Skill auto-creation, reflection, improvement queue
