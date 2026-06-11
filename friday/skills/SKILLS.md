# FRIDAY Skill System

## Overview
FRIDAY has access to a set of "skills" — markdown files containing expert instructions for specific tasks. Before creating any file, FRIDAY MUST read the relevant SKILL.md file and follow its instructions.

## Available Skills

| Skill | Path | Use When |
|-------|------|----------|
| docx | skills/docx/SKILL.md | Creating Word documents (.docx) |
| pptx | skills/pptx/SKILL.md | Creating PowerPoint presentations (.pptx) |
| pdf | skills/pdf/SKILL.md | Creating PDF files (.pdf) |
| xlsx | skills/xlsx/SKILL.md | Creating Excel spreadsheets (.xlsx) |
| svg | skills/svg/SKILL.md | Creating SVG diagrams, infographics, charts |
| chart | skills/chart/SKILL.md | Creating charts and graphs using libraries |
| osint | skills/osint/SKILL.md | OSINT recon, social media intelligence, email/domain/phone/breach analysis |
| code_gen | skills/code_gen/SKILL.md | Generating code in ANY programming language |
| metasploit | skills/metasploit/SKILL.md | Metasploit exploitation, meterpreter, password cracking, SQLi, XSS |

## Two-Phase Workflow (STRICT)
1. **RESEARCH FIRST** — Gather all facts, figures, citations, and data using web_search, web_fetch, grep, read_file, memory_retrieve etc. Do NOT touch output-format skills during this phase.
2. **BUILD SECOND** — Only AFTER research is complete, read the relevant SKILL.md and build the deliverable from researched facts.

## Composition
Multiple skills may be required for complex tasks (e.g., docx + svg for a report with diagrams). Read all relevant skills before starting.

## Skill File Format
Each SKILL.md contains:
- Frontmatter (name, description, triggers)
- Overview of the task
- Libraries and tools to use
- Code patterns and best practices
- What to AVOID (negative instructions)
- Color system and layout rules (for visuals)
- Verification steps
