# FRIDAY File-Generation Router

Enforcement layer only — no generation logic lives here. This tells FRIDAY
WHEN to stop and read a playbook before acting.

## The Core Rule

> Before writing any code, running any generation script, or creating any
> file of a type covered below, FRIDAY MUST first read the matching
> SKILL.md in full. Not conditional on task complexity — a one-line PDF
> still reads pdf/SKILL.md first. The read is cheap; skipping it isn't.

Why this matters mechanically: an LLM's training data contains thousands of
half-correct, outdated, or environment-mismatched examples for "how to make
a docx in Python." Without a forced read-first step, the model
pattern-matches to whatever it saw most often in training — usually NOT the
thing that renders correctly in FRIDAY's actual Windows environment (wrong
page-size default, wrong font substitution, banned-library trap, etc). The
SKILL.md exists to overwrite that default pattern-match with verified,
environment-specific truth.

## Trigger Table

| User says / implies | Read this first |
|---|---|
| "word doc", "report", "memo", "letter", ".docx", tracked changes, comments | `friday/skills/docx/SKILL.md` |
| "pdf", "invoice", "form", merge/split pages, encrypt, redact, OCR | `friday/skills/pdf/SKILL.md` |
| "spreadsheet", "excel", ".xlsx", budget, tracker, pivot table | `friday/skills/xlsx/SKILL.md` |
| "deck", "slides", "presentation", ".pptx", pitch, speaker notes | `friday/skills/pptx/SKILL.md` |
| "icon", "logo", "vector graphic", favicon | `friday/skills/svg/SKILL.md` |
| "website", "landing page", "dashboard", "webapp", calculator/tool | `friday/skills/html-web/SKILL.md` |
| "flowchart", "architecture diagram", "sequence diagram", "ER diagram", "gantt" | `friday/skills/diagrams/SKILL.md` |
| data charts/graphs specifically (bar, line, pie, scatter, etc — standalone or embedded) | `friday/skills/chart/SKILL.md` |

Multiple types in one request → read all relevant SKILL.md files before
starting ANY of them. Don't discover the second file type's gotchas mid-task.

## Non-Negotiable Sequence

1. **Detect** — match the request against the trigger table above.
2. **Read** — open the full SKILL.md(s). Not a skim.
3. **Scratch** — do all generation work in a scratch directory, never
   directly in the final output location.
4. **Verify** — every skill has a `scripts/check_env.py` (run once per
   session, or when a task in that filetype first comes up) and a
   `scripts/verify_*.py` (run after every generation). Do not skip this
   because the code "looks right." A clean execution and a correct-looking
   output are different claims — only the render/verify step confirms the
   second one.
5. **Deliver** — copy ONLY the final file(s) to the designated output
   folder. Never leave scratch files, intermediate renders, or debug output
   in the delivery folder.
6. **Present** — tell the user what was made and where, in one line. Don't
   re-explain the whole generation process unless asked.

## Anti-patterns this router exists to prevent

- Writing a generator from memory without checking the skill's gotchas
  section → file opens "broken" for reasons that were already documented
  and avoidable.
- Shipping a pptx/pdf/svg without ever rendering it to an image — overlap
  and overflow are invisible in code, obvious in a screenshot.
- Trusting a "NEVER use X library" rule inside a skill file without
  checking whether the skill actually provides a working replacement for
  the task that library was doing — a banned dependency with no functional
  substitute is a bug in the skill file, not a real constraint. (This
  happened once already — see pdf/SKILL.md §7 merge/split, which
  deliberately keeps pypdf because the alternative offered elsewhere was a
  non-functional stub.)
- Recalculating nothing in an Excel file with formulas — openpyxl writes
  formula strings but not computed values, file looks "empty" until
  something recalculates it.
- Treating SVG/HTML as "just markup" and skipping the design-quality
  pass — technically-valid output that still looks like a 2004 default.

## File Layout Convention

```
friday/
  skills/
    docx/SKILL.md            + scripts/
    pdf/SKILL.md              + scripts/
    xlsx/SKILL.md             + scripts/
    pptx/SKILL.md             + scripts/
    svg/SKILL.md              + scripts/
    html-web/SKILL.md         + scripts/
    diagrams/SKILL.md         + scripts/
    chart/SKILL.md            (external — see note below)
    ROUTER.md                 <- this file
  workspace/
    tmp/         <- scratch, generation happens here
    outputs/     <- final deliverables only
```

**Note on `chart/SKILL.md`**: not included in this delivery — you already
have a solid one from OpenCode. Drop it into `friday/skills/chart/` as-is;
it's genuinely good (colorblind-safe palettes, data-ink ratio rules, proper
`plt.close()` memory hygiene) and doesn't need the same rebuild the pdf/pptx
ones did. The trigger table above already routes to it.

Keep SKILL.md files as plain markdown, loaded via simple file read at the
top of whichever tool-call handler triggers on that filetype. No need for a
vector DB or embedding search for 7-8 files — a keyword match against the
trigger table is enough and is more predictable than semantic retrieval for
this use case.

## A note on trusting generated skill content

If any skill file (this set, a future one, or one pulled from another
source) contains an absolute rule like "NEVER use library X" with no
working alternative demonstrated nearby for the exact task X was doing —
treat that as a red flag, not gospel. Verify the replacement actually works
before trusting the rule. Skill files are reference material, not scripture
— they can be wrong, and a confident tone doesn't mean the content was
checked.
