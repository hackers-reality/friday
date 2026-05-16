# FRIDAY Snapshot / Time Travel

## Overview

FRIDAY's snapshot system captures file and directory state before risky operations (writes, deletes, memory repairs), enabling restore and diff.

## Key Functions

| Function | Description |
|----------|-------------|
| `create_snapshot()` | Snapshot a file or directory with SHA-256 hash |
| `restore_snapshot()` | Restore to original or custom path |
| `diff_snapshot()` | Show differences (file or directory level) |
| `list_snapshots()` | List all snapshots, newest first |

## Tool Actions (`snapshot_tool`)

- `list` — List all snapshots
- `create` — Create a new snapshot (provide path)
- `restore` — Restore a snapshot by ID
- `diff` — Show diff between snapshot and current state
- `info` — Show snapshot metadata

## Storage

Snapshots are stored in `friday_memory/snapshots/snap_XXXXXX/` with an index at `friday_memory/snapshots/_index.json`.

## Integration

The authority system can auto-snapshot before destructive operations (`snapshot_before_destructive` flag).

## Status: Stable
