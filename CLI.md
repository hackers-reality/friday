# FRIDAY CLI Reference

FRIDAY provides a command-line interface for system management, diagnostics, and configuration.

## Usage

```bash
python -m friday.cli <command> [options]
```

Or use the `friday` entry point if installed as a package.

## Commands

### `doctor` — System Diagnostics

```bash
python -m friday.cli doctor            # Standard report
python -m friday.cli doctor --verbose  # Verbose (all checks)
python -m friday.cli doctor --json     # JSON output
```

Checks: Python version, OS, module imports, disk space, config files, user profile validity, schema validation.

### `status` — System Overview

```bash
python -m friday.cli status
```

Shows: memory paths, user profile info, Memory Tree stats.

### `memory-tree` — Knowledge Base

Alias: `mt`

```bash
python -m friday.cli mt                          # Status overview
python -m friday.cli mt read people              # Read a page
python -m friday.cli mt write -n projects -c "## Active\n- Project X"  # Write
python -m friday.cli mt search "goals"           # Full-text search
python -m friday.cli mt daily-note               # Today's note
python -m friday.cli mt daily-notes              # Recent notes
python -m friday.cli mt update                   # Sync from profile
python -m friday.cli mt context                  # Build injection context
python -m friday.cli mt build-index              # Rebuild index
```

### `sidecar` — Sidecar Network

Alias: `sc`

```bash
python -m friday.cli sc                          # Status
python -m friday.cli sc discover                 # Discover sidecars
python -m friday.cli sc generate -l "my-pc"      # Generate JWT token
python -m friday.cli sc verify -t TOKEN -h HOST  # Verify token
python -m friday.cli sc list                     # List registered
python -m friday.cli sc health                   # Health check
```

### `snapshots` — Memory Snapshots

Alias: `snap`

```bash
python -m friday.cli snap                        # List snapshots
python -m friday.cli snap create -l "before-update"  # Create
python -m friday.cli snap restore -i SNAP_ID     # Restore
python -m friday.cli snap delete -i SNAP_ID      # Delete
python -m friday.cli snap info -i SNAP_ID        # Show info
```

### `autonomy` — Autonomy Level

Alias: `aut`

```bash
python -m friday.cli aut                         # Current level
python -m friday.cli aut set --level medium      # Set level (off/low/medium/high/full)
```

### `suit-check` — Pre-Flight Verification

```bash
python -m friday.cli suit-check
python -m friday.cli suit-check --json
```

Verifies all FRIDAY subsystems, user profile, policy config, and returns a readiness score.

### `damage-report` — System Risk Audit

```bash
python -m friday.cli damage-report
python -m friday.cli damage-report --json
```

Reports CPU/memory/disk usage, memory/task health, and assigns a risk score (LOW/MEDIUM/HIGH).

### `morning` — Daily Planning

```bash
python -m friday.cli morning
```

Generates a morning briefing: system status, weather-ish diagnostics, goal reminders.

### `evening` — Daily Review

```bash
python -m friday.cli evening
```

End-of-day summary: what happened, system health, reflection.

### `dashboard` — Dashboard Control

```bash
python -m friday.cli dashboard start      # Start dashboard
python -m friday.cli dashboard stop       # Stop dashboard
python -m friday.cli dashboard url        # Show dashboard URL
```

### `config` — Configuration

```bash
python -m friday.cli config               # Show all config
python -m friday.cli config path          # Show config directory path
```

## Global Options

| Option | Description |
|--------|-------------|
| `--json` | Output results as JSON (supported by doctor, suit-check, damage-report) |
| `-h, --help` | Show help for any command |

## Aliases

| Full | Alias |
|------|-------|
| `memory-tree` | `mt` |
| `sidecar` | `sc` |
| `snapshots` | `snap` |
| `autonomy` | `aut` |
| `suit-check` | `check` |
| `damage-report` | `damage` |
| `dashboard` | `dash` |
| `config` | `cfg` |

## Examples

```bash
# Quick system health check
python -m friday.cli doctor

# Read your goals from memory tree
python -m friday.cli mt read goals

# Generate a sidecar token for a laptop
python -m friday.cli sc generate -l "laptop"

# Check everything before an important session
python -m friday.cli suit-check
```
