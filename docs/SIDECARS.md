# FRIDAY Sidecar System

## Overview

Sidecars are helper processes that extend FRIDAY's reach. Each sidecar is registered with a type, heartbeat, and capability list.

## Sidecar Types

| Type | Description |
|------|-------------|
| `desktop` | Desktop automation helper |
| `browser` | Browser automation daemon |
| `filesystem` | Filesystem watcher |
| `system_monitor` | System performance monitor |
| `code_workspace` | Code workspace agent |
| `smart_home` | Smart home bridge |
| `mobile_placeholder` | Mobile device placeholder |
| `cloud_placeholder` | Cloud service placeholder |

## API

| Function | Description |
|----------|-------------|
| `register_sidecar()` | Register a new sidecar |
| `heartbeat_sidecar()` | Record heartbeat |
| `list_sidecars()` | List all sidecars |
| `sidecar_status()` | Get specific sidecar status |
| `dispatch_sidecar_command()` | Dispatch command to sidecar |

## Tool Actions (`sidecar_tool`)

- `status` — Summary of all sidecars
- `list` — Detailed sidecar list
- `register` — Register a new sidecar
- `heartbeat` — Record heartbeat
- `info` — Get sidecar details
- `dispatch` — Send command to sidecar

## Persistence

Sidecars are stored in `friday_memory/sidecars.json`.

## Status: Stable

Sidecar dispatch currently returns placeholder responses (local/remote dispatch skeleton not fully implemented). Registry, heartbeat, and listing are fully functional.
