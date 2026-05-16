# FRIDAY Memory System

## Overview

FRIDAY's memory system transforms raw chat history into a structured, confident, and safe user profile. It answers not just *what* FRIDAY knows, but *why* she knows it, *where* it came from, *how confident* it is, whether it *conflicts*, and whether it is *safe* to inject.

## Architecture

```
Import → Extract → TF-IDF → Audit → Profile → Clean → Confidence → Inject
                                                                    │
                                                    ┌───────────────┘
                                                    ▼
                                           [USER MEMORY] in prompt
                                           [RELEVANT MEMORY] per query
```

## Profile Structure

Stored in `friday_memory/user_profile.json`:

```python
{
  # Scalars (with confidence gating)
  "name": str | None,
  "age_grade": str | None,
  "location": str | None,

  # Lists (per-item confidence)
  "education": [str],
  "projects": [str],
  "tech_stack": [str],
  "goals": [str],
  "skills": [str],
  "languages": [str],
  "achievements": [str],
  "challenges": [str],
  "personality_traits": [str],
  "relationships": [str],

  # Dict-of-lists
  "preferences": {subkey: [str]},
  "interests_hobbies": {subkey: [str]},
  "career": {subkey: [str]},
  "learning": {subkey: [str]},
  "devices_os": {subkey: [str]},

  # System
  "version": int,
  "audits": [{timestamp, conversations, findings}],
  "last_updated": str,
  "last_tfidf_topics": [str],
  "_confidence": { field: float | {item: float} },
  "_pinned": [str],
  "_review_queue": [dict],
}
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `load_profile()` | Load profile with .bak fallback |
| `save_profile()` | Atomic write + .bak + readback validation |
| `clean_profile()` | Remove garbage, normalize casing, reset suspicious scalars |
| `_inject_confidence()` | Score every field and item (0.0-0.95) |
| `validate_profile()` | Check for suspicious values, structural warnings |
| `build_user_memory_context()` | Build [USER MEMORY] block for system prompt |
| `build_relevant_memory_context()` | Per-query context from vector + episodic + profile |
| `detect_profile_conflicts()` | Find conflicting ages, locations, names |
| `resolve_profile_conflicts()` | Deduplicate and resolve conflicts |
| `decay_profile_memory()` | Remove old items, spare pinned |
| `build_memory_review_queue()` | Items needing human review |
| `redact_sensitive_text()` | Strip secrets before storage |
| `_index_profile_to_vector_memory()` | Push profile to ChromaDB |

## Confidence Scoring

- **Scalar fields**: 0.0-0.95 based on format/patterns
- **List items**: 0.0-0.95 per item
- **Injection gates**: scalar >= 0.5, list item >= 0.3
- **Review threshold**: items < 0.4 flagged for review

## Memory Actions (via `memory_import_tool`)

| Action | Description |
|--------|-------------|
| `status` | Profile version, fields, audit count |
| `import_file` | Import JSON/text chat export |
| `import_dir` | Import all files from directory |
| `audit` | Re-audit all stored imports → update profile |
| `profile` | Show profile summary |
| `repair_profile` | Clean + validate + re-inject confidence |
| `doctor` | Full diagnostic report |
| `review_profile` | List review queue items |
| `approve_memory` | Approve and pin a memory item |
| `reject_memory` | Reject and remove a memory item |
| `pin_memory` | Protect item from decay |
| `unpin_memory` | Remove pin protection |
| `decay_profile` | Apply memory decay |

## Redaction

`redact_sensitive_text()` redacts before memory storage:
- Emails → `[REDACTED_EMAIL]`
- API keys/tokens → `[REDACTED_CREDENTIAL]`
- JWT tokens → `[REDACTED_JWT]`
- Private IPs → `[REDACTED_IP_PRIVATE]`
- GitHub tokens → `[REDACTED_GITHUB_TOKEN]`
- Slack tokens/webhooks → `[REDACTED_SLACK_TOKEN]`
- Phone numbers → `[REDACTED_PHONE]`
- Credit cards → `[REDACTED_CC]`
- SSNs → `[REDACTED_SSN]`

## Quality Controls

- Atomic save with `.bak` fallback
- Suspicious scalar detection (40+ non-locations, 100+ generic names)
- List item garbage filtering (<3 chars, URLs, fragments, verbs)
- Tech name normalization (80+ canonical forms)
- Per-audit conflict tracking
- Pinned items exempt from decay
- Review queue for low-confidence/conflicting items

## Tests

- `test_memory_context.py`: 18 tests (profile, context, cleaning, confidence, repair)
- `test_memory_advanced.py`: 24 tests (redaction, conflicts, decay, review, pin/approve/reject, doctor)
