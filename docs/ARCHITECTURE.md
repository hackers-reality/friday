# FRIDAY Architecture

## Overview

FRIDAY is a Windows-native, Iron-Man-inspired personal AI OS assistant. It runs as a persistent background agent with voice, vision, desktop control, memory, and self-improvement capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Gemini Live API                     │
│          (voice, function calling, context)           │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                   live.py                            │
│    Main event loop: audio ↔ text ↔ tools ↔ memory    │
│    _build_session_config() → [USER MEMORY] injection  │
│    _inject_memory_context() → per-query memory        │
│    TOOL_MAP → tool dispatch                            │
│    _invoke_tool() → hook execution                    │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────┼───────────┬──────────────────┐
         ▼           ▼           ▼                  ▼
   ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────────────┐
   │ tools.py │ │hooks.py│ │ memory*  │ │ authority.py   │
   │ Wrapper  │ │ Pre/   │ │ import   │ │ Risk class.    │
   │ handlers │ │ Post/  │ │ context  │ │ Policy engine  │
   └──────────┘ │ Error  │ │ vector   │ │ Audit log      │
                │ hooks  │ │ episodic │ └────────────────┘
                └────────┘ │ KG       │
                           └──────────┘
```

## Core Loop

1. **Audio/Text Input** → Gemini Live API → functionCall or text response
2. **Function Calls** → `_invoke_tool()` → pre-hooks → tool execution → post-hooks
3. **Memory Injection** → `[USER MEMORY]` at session start + `[RELEVANT MEMORY]` per query
4. **Background** → reflection, dreaming, proactivity, monitoring

## Module Map

| Path | Role | Status |
|------|------|--------|
| `live.py` | Main event loop, session management, tool dispatch | Stable |
| `tools.py` | Tool implementations (150+ wrappers) | Stable |
| `memory_import.py` | Profile extraction, TF-IDF, cleaning, confidence, review, decay, doctor, redaction | Stable |
| `memory_context.py` | Relevant memory context retrieval (vector + episodic + keywords) | Stable |
| `vector_memory.py` | ChromaDB wrapper | Stable |
| `episodic.py` | SQLite FTS5 session memory | Stable |
| `knowledge_graph.py` | Entity-relation triple store | Stable |
| `authority.py` | Tool risk classification, policy, decision engine | Stable |
| `snapshots.py` | File/memory snapshots, restore, diff | Stable |
| `sidecar.py` | Sidecar registry, heartbeat, dispatch | Stable |
| `autonomy.py` | Task queue, retry, reflection | Stable |
| `tool_registry.py` | Central tool metadata (150+ tools) | Stable |
| `capabilities.py` | Capability matrix, report generator | Stable |
| `dashboard.py` | HTML dashboard (port 8080) | Stable |
| `dashboard_api.py` | REST API (port 8090, 17 endpoints) | Stable |
| `hooks.py` | Pre/post/error hook system | Stable |
| `kyu.py` | Personality adaptation | Stable |
| `goals.py` | OKR/goal management | Stable |
| `scheduler.py` | Cron-like task scheduling | Stable |
| `self_modify.py` | Self-code modification with safety validation | Stable |
| `skills.py` | Custom skill management | Stable |
| `workflow.py` | Multi-step workflow engine | Stable |
| `protector.py` | Anti-shutdown, anti-sleep, lid-close | Stable |

## Data Flow

```
User Input → Gemini Live API → live.py → _invoke_tool()
                                         ├── pre_hooks (log, block)
                                         ├── TOOL_MAP lookup
                                         ├── authority check
                                         ├── execute tool
                                         └── post_hooks (KG, KYU, episodic)
```

## Memory Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    user_profile.json                        │
│  (scalars + lists + dicts + TF-IDF + _confidence + _pinned)│
└──────────────────────┬─────────────────────────────────────┘
                       │
         ┌─────────────┼───────────────┐
         ▼             ▼               ▼
   ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ ChromaDB │ │ SQLite   │ │ memory.json  │
   │ Vector   │ │ FTS5     │ │ Keywords     │
   │ Search   │ │ Session  │ │              │
   └──────────┘ │ Search   │ └──────────────┘
                └──────────┘
```

## Safety Layers

1. **Authority Policy** — classify tool risk (9 levels), block/dry-run modes
2. **Pre-hooks** — can block tool execution entirely
3. **Snapshots** — auto-snapshot before destructive operations
4. **Protector** — prevent shutdown/sleep
5. **Validator** — AST-level code safety for self-modification
6. **Memory Redaction** — strip secrets before storage
