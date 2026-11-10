# OpenCode-as-Brain — Feasibility Notes (NOT approved, do not build)

**Status 2026-11-10:** the owner floated this as a possibility but has NOT approved it.
Nothing is wired for it. This document records what it would actually take so a future
decision is informed. Do not implement without explicit per-feature approval.

## What already exists (approved, working today)

FRIDAY's backup brain is a **text-mode fallback**, not an OpenCode session:

1. Gemini Live API (voice) — primary.
2. On 429 / quota / 1007 audio failure / Live unavailability → `_fallback_text_mode()`
   in `friday/live.py` speaks through the text chain: **NVIDIA NIM** (deepseek-v4-flash
   and friends, multi-key, rate-limited, `friday/nim_client.py`) → **OpenCode Zen**
   (`big-pickle`, `mimo-v2.5-free`) → **Google Gemini** (`flash`).
   Tools are exposed as OpenAI-style function definitions (`_build_openai_tools()` from
   TOOL_MAP) plus a plain-text "call name(args)" tier for models that don't do native
   tool calling.
3. TTS underneath it: Edge → **voice chain** (`friday/voice_engine.py`):
   gemini-live → kitten (local, offline) → fish (cloud, owner key) → sarvam.

So "OpenCode-as-brain" is distinct from what ships: it would mean **OpenCode itself
(the harness with its own tools/agents) becomes FRIDAY's cognition layer**, not merely a
Zen inference endpoint.

## What it would take

| Piece | Detail |
|---|---|
| Session host | Run OpenCode as a long-lived service (`opencode serve` / ACP-over-stdio) and keep one FRIDAY-facing session alive, mirroring how `friday.opencode_bridge` currently spawns sub-agents on demand. |
| Tool surface | FRIDAY has ~500 TOOL_MAP handlers + ~650 auto-registered descriptors + ~480 OSINT helpers. OpenCode would need equivalent reach (MCP registration of FRIDAY's own tool set, i.e. the inverse of `mcp_tool`) or it silently loses capabilities (computer control, CV, sidecars, memory). |
| Persona/context | FRIDAY's SYSTEM_INSTRUCTION (~1,100 lines, onboarding/KYU/memory injection) must ride every turn — token cost is the least of the problems; cache-friendliness of a 200k system prompt is the real one. |
| Auth/keys | Zen key already exists (`OPENCODE_ZEN_API_KEY`). A full harness login is heavier — it needs the owner's OpenCode auth state, refresh handling, and per-machine sandboxing. Not inventable, not self-served. |
| Streaming semantics | Live API gives full-duplex audio + tool-call streaming. OpenCode sessions are request/response text turns; voice UX degrades unless a streaming voice loop is bolted on top (Gemini-Live-style audio in/out is lost). |
| Failure modes | If OpenCode serve dies mid-turn, FRIDAY has zero local cognition unless the NIM/Zen/Gemini text chain remains as second fallback — it does, so the marginal value of the full harness is mostly OpenCode's *planner + self-editing tool ecosystem*, not raw answering. |
| Safety | OpenCode can edit/execute repo files under its own permissions. Wiring that to the spoken UI collapses FRIDAY's authority.py risk tiers unless every harness action is re-gated through authority policy + hooks. That is a real design project, not a flag flip. |
| Effort estimate | ~1–2 days for a minimal bridge behind `FRIDAY_BRAIN=opencode`, plus a week of authority/hook plumbing to make it safe, plus eval parity testing of voice UX. |

## Recommendation recorded for the owner

Keep **text-fallback (NIM → Zen → Gemini)** as the backup brain — it is already
implemented, tested, and cheap. Treat OpenCode-as-brain only if text-fallback proves
insufficient in practice; if approved, scope it as: `friday/opencode_brain.py` behind
`FRIDAY_BRAIN=opencode-zen-harness`, reusing `friday.opencode_bridge` for the session,
routing *all* tool calls through `_invoke_tool` (authority + hooks), with the text chain
preserved as tertiary fallback. Stop and ask the owner before any of that is built.
