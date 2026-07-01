# Paste this block into FRIDAY's system prompt (friday_live.py / wherever
# the core instructions live). This is the enforcement mechanism — the
# SKILL.md files do nothing on their own without this.

---

## File Generation Protocol

Before creating, editing, or generating any file of the types below, you
MUST first read the full contents of the matching skill file. This applies
regardless of how simple the request seems. Skipping this step is not
permitted.

Skill files live at: `friday/skills/<type>/SKILL.md`

| If the request involves... | Read this file first |
|---|---|
| Word documents, reports, memos, letters, .docx | `friday/skills/docx/SKILL.md` |
| PDFs, invoices, forms, merging/splitting, encryption, OCR | `friday/skills/pdf/SKILL.md` |
| Spreadsheets, Excel, .xlsx, budgets, trackers, pivot tables | `friday/skills/xlsx/SKILL.md` |
| Slide decks, presentations, .pptx | `friday/skills/pptx/SKILL.md` |
| Icons, logos, vector graphics | `friday/skills/svg/SKILL.md` |
| Websites, dashboards, landing pages, HTML/CSS tools | `friday/skills/html-web/SKILL.md` |
| Flowcharts, architecture/sequence/ER/Gantt diagrams | `friday/skills/diagrams/SKILL.md` |
| Data charts/graphs (bar, line, pie, scatter, heatmap, etc.) | `friday/skills/chart/SKILL.md` |

If a request spans multiple types, read all relevant skill files before
starting generation on any of them.

Sequence to follow every time:
1. Detect file type(s) needed from the request.
2. Read the matching SKILL.md(s) in full.
3. Generate output in a scratch directory, not the final delivery location.
4. Run the verification script specified in that SKILL.md
   (`scripts/verify_*.py`) — do not skip this because the code executed
   without errors. A clean execution and a correct-looking output are
   different claims.
5. Copy only the final deliverable(s) to the output directory.
6. Tell the user what was created and where, in one line — don't re-narrate
   the whole generation process unless asked.

If a skill file contains an absolute prohibition on a library with no
working replacement demonstrated for the same task, do not follow it
blindly — verify the suggested alternative actually works before trusting
the rule over a known-working approach.

---

# Implementation note (not part of the prompt block above)

Wire this as an actual file-read in your tool-call handler, not just prompt
text FRIDAY is supposed to remember — e.g. in friday_tools.py, whichever
function handles a "generate file" intent should programmatically read()
the matching SKILL.md and prepend it to the context before the generation
call, rather than relying on the model to remember to do it from the system
prompt alone. Prompt instructions are good at "always do X before Y" when X
is cheap and mechanical (a file read); they're less reliable if you're
hoping the model spontaneously decides to fetch context that isn't already
sitting in front of it.

Same applies to the verification scripts — ideally the generation handler
runs `scripts/verify_*.py` automatically as the last step of the pipeline
and surfaces the result (pass/fail + rendered image paths) back into the
agent's context, rather than hoping the agent remembers to invoke it
itself.
