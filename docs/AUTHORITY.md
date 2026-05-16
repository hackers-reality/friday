# FRIDAY Authority & Action Policy

## Overview

FRIDAY's authority system classifies every tool call by risk level and enforces a configurable policy. It prevents dangerous actions, logs all decisions, and supports dry-run modes for safe experimentation.

## Risk Levels

| Level | Classification | Examples |
|-------|---------------|---------|
| 0 | `read_only` | read_file, list_files, system_info |
| 1 | `local_write` | write_file, click, open_app |
| 2 | `destructive` | delete_file, remove_directory |
| 3 | `system_control` | run_cmd, shutdown, hotkey |
| 4 | `external_send` | send_email, send_instagram_dm |
| 5 | `credential` | gmail_authorize, exchange_oauth |
| 6 | `network_write` | github_write_file, github_create_pr |
| 7 | `self_modify` | github_self_modify, self_improve |
| 8 | `background_autonomy` | autonomy_tool |

## Policy

Stored in `friday_memory/authority_policy.json`:

- **mode**: `auto` | `ask` | `dry_run` | `block_all`
- **max_risk_level**: Maximum allowed risk (0-8)
- **blocked_tools**: Specific tools to always block
- **require_approval_tools**: Tools needing approval
- **snapshot_before_destructive**: Auto-snapshot before destructive ops
- **Per-risk permissions**: allow_read_only, allow_destructive, etc.

## Tool Actions (`authority_tool`)

- `status` — Current policy summary
- `policy` — Full policy dump
- `mode` — Change mode (auto/dry_run/block_all)
- `allow` — Allow a risk level
- `block` — Block a risk level or specific tool
- `max_level` — Set max risk level
- `classify` — Show classification for a tool
- `log` — Recent authority decisions

## Integration

Authority decisions are automatically logged to `friday_memory/authority_log.jsonl`. The system integrates with `tool_registry.py` for classification but falls back to name-pattern heuristics.

## Status: Stable
