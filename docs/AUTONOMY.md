# FRIDAY Autonomy Engine

## Overview

FRIDAY's autonomy engine provides a durable task queue with retry, reflection, pause/resume, and failure handling. It enables FRIDAY to plan, execute, and learn from autonomous actions.

## Task States

| State | Description |
|-------|-------------|
| `queued` | Waiting for execution |
| `running` | Currently executing |
| `blocked` | Waiting for dependency |
| `failed` | Failed after all retries |
| `completed` | Successfully finished |
| `paused` | Manually paused |

## Key Functions

| Function | Description |
|----------|-------------|
| `queue_task()` | Add a task with description, tool, args, priority, retry policy |
| `mark_running()` | Start execution |
| `mark_completed()` | Record success with result and reflection |
| `mark_failed()` | Record failure with auto-retry or escalation |
| `pause_task()` | Pause a queued/running task |
| `resume_task()` | Resume a paused task |
| `task_summary()` | Get counts by status |

## Retry Policy

Each task has `{"max_retries": N, "backoff": seconds}`. After failure:
1. Increment retry_count
2. If retry_count <= max_retries: re-queue
3. Else: mark failed permanently

## Tool Actions (`autonomy_tool`)

- `status` — Task summary (counts by status)
- `queue` — Queue a new task
- `list` — List tasks (optional status filter)
- `get` — Get task details
- `pause` — Pause a task
- `resume` — Resume a task
- `complete` — Mark task completed

## Persistence

Tasks are stored in `friday_memory/autonomy_queue.json`.

## Status: Stable
