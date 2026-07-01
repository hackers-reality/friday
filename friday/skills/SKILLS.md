# FRIDAY Skill System — Master Index

## Table of Contents

1. [Introduction & Philosophy](#1-introduction--philosophy)
2. [Complete Skill Index](#2-complete-skill-index)
3. [Skill Domain Map](#3-skill-domain-map)
4. [Cross-Reference Matrix](#4-cross-reference-matrix)
5. [Two-Phase Workflow Protocol](#5-two-phase-workflow-protocol)
6. [Agent Skill Selection Algorithm](#6-agent-skill-selection-algorithm)
7. [Skill Chaining & Composition](#7-skill-chaining--composition)
8. [Unified Design System Reference](#8-unified-design-system-reference)
9. [FRIDAY Document Generation Pipeline](#9-friday-document-generation-pipeline)
10. [Agent-to-Skill Mapping](#10-agent-to-skill-mapping)
11. [Skill File Loading Protocol](#11-skill-file-loading-protocol)
12. [Quality Standards Document](#12-quality-standards-document)
13. [Troubleshooting Guide for Skill Integration](#13-troubleshooting-guide-for-skill-integration)
14. [Performance & Optimization Guidelines](#14-performance--optimization-guidelines)
15. [Security & Compliance Guidelines](#15-security--compliance-guidelines)
16. [Testing Each Skill Output](#16-testing-each-skill-output)
17. [Version History & Changelog](#17-version-history--changelog)
18. [Appendix A: Quick-Reference Cards](#18-appendix-a-quick-reference-cards)
19. [Appendix B: Environment & Dependency Checklist](#19-appendix-b-environment--dependency-checklist)
20. [Appendix C: Error Code Reference](#20-appendix-c-error-code-reference)

---

## 1. Introduction & Philosophy

FRIDAY operates as a multi-skill intelligence system. Each skill is an expert module encoded as a Markdown file that teaches FRIDAY how to perform a specific class of tasks — from creating Word documents to conducting OSINT investigations to generating production-grade code.

### 1.1 Why Skill Files?

Traditional AI agents rely on implicit knowledge, which leads to inconsistent output. FRIDAY's skill files act as:

- **Explicit instruction sets**: Every skill file encodes FRIDAY's best practices, library choices, design systems, and quality criteria
- **Deterministic guides**: The agent reads the relevant skill file *before* generating output, eliminating guesswork
- **Living documentation**: Skill files evolve as libraries update, bugs are fixed, and patterns improve
- **Cross-training modules**: Skills share design systems and patterns, enabling seamless composition

### 1.2 The Skill Contract

Every skill file in this system adheres to a strict contract:

1. **Frontmatter**: `name` and `description` fields for agent matching
2. **Triggers**: Natural-language patterns that activate the skill
3. **Libraries**: Exact libraries and versions to use
4. **Design System**: Color ramps, type scales, layout grids (shared across visual skills)
5. **Code Patterns**: Production-quality templates and examples
6. **What to AVOID**: Negative instructions that prevent common mistakes
7. **Verification Steps**: How to validate the output before delivery
8. **Integration Patterns**: How this skill composes with others

### 1.3 File System Layout

```
friday/skills/
├── SKILLS.md              ← THIS FILE — master index (1000+ lines)
├── docx/
│   └── SKILL.md           ← Word document creation (1272 lines)
├── pptx/
│   └── SKILL.md           ← PowerPoint presentation creation (1099 lines)
├── pdf/
│   └── SKILL.md           ← PDF document creation (1001+ lines)
├── xlsx/
│   └── SKILL.md           ← Excel spreadsheet creation (1310 lines)
├── svg/
│   └── SKILL.md           ← SVG diagram & infographic creation (1208 lines)
├── chart/
│   └── SKILL.md           ← Data chart & graph creation (1420+ lines)
├── code_gen/
│   └── SKILL.md           ← Multi-language code generation (1873+ lines)
├── osint/
│   └── SKILL.md           ← OSINT investigation (2815 lines)
└── metasploit/
    └── SKILL.md           ← Penetration testing (2260 lines)
```

---

## 2. Complete Skill Index

### 2.1 Core Document Skills

#### docx — Word Document Creation
- **File**: `skills/docx/SKILL.md`
- **Library**: python-docx
- **Output**: .docx files (Word 2010+ compatible)
- **Key capabilities**: Professional document design with python-docx. Creates A4/Letter documents with title pages, multi-level headings, styled tables (blue header rows, alternating colors), justified body text, bullet/numbered lists, inline and floating images with captions, headers/footers with page numbers, table of contents via field codes, hyperlinks, bookmarks, cross-references, OMML equations, watermarks, document protection, custom styles, and section breaks. Integrates with chart skill for matplotlib chart embedding and SVG skill for diagram embedding. Supports multi-section documents with mixed portrait/landscape orientation, different first-page headers, and odd/even page headers. Maximum 2 fonts per document, body text in dark gray (#333), Calibri/Calibri Light font family. Quality checklist covers content, design, and technical verification across 12 validation steps. ~1272 lines of reference material.

#### pptx — PowerPoint Presentation Creation
- **File**: `skills/pptx/SKILL.md`
- **Library**: python-pptx
- **Output**: .pptx files (PowerPoint 2010+ compatible)
- **Key capabilities**: Widescreen 16:9 (13.333×7.5 inch) slide deck creation with python-pptx. Features 12 slide types: title slide (dark background, accent color), section header (full-bleed), content slide (title + body), two-content (equal columns), comparison (A/B), blank (full-bleed), chart slide (CategoryChartData), quote slide (28pt italic, accent bar), data/KPI slide (44pt numbers), image-left/text-right, agenda/overview, and thank-you/closing. 12-column grid layout system with 0.9" columns, 6-row grid. Complete type scale from 12pt (footers) to 44pt (KPI numbers). Color ramps identical to SVG/docx system. Table styling with alternating rows, chart integration via pptx chart API or matplotlib PNG embedding, shape manipulation with shadows and gradients, slide transitions, and presentation export to PDF. Max 6 bullets per slide, 10 words per bullet. ~1099 lines of reference material.

#### pdf — PDF Document Creation
- **File**: `skills/pdf/SKILL.md`
- **Library**: reportlab (primary), fpdf2 (simple docs)
- **Output**: .pdf files (PDF/A-1b compliant, print-ready)
- **Key capabilities**: Print-ready PDF creation using reportlab (complex layouts, tables, graphics) and fpdf2 (simple invoices, labels). Page templates with headers, footers, and page numbers. Multi-column layouts, flowable document building with platypus (Paragraphs, Tables, Images, PageBreaks). SVG rendering via svglib, chart embedding via matplotlib. Color management (CMYK for print, RGB for screen), font embedding (Type 1, TrueType, OpenType). PDF/A-1b archival compliance, linearized PDF for web optimization. Supports form filling (AcroForms, XFA), digital signatures (pkcs12), metadata injection (Dublin Core, XMP), document compression, and encryption (AES-256, RC4-128). Table extraction with pdfplumber for data reading. Additional utilities: merge/split PDFs, add watermarks, rotate/crop pages, flatten forms. pdfplumber for text/table extraction. ~1001+ lines of reference material.

#### xlsx — Excel Spreadsheet Creation
- **File**: `skills/xlsx/SKILL.md`
- **Library**: openpyxl
- **Output**: .xlsx, .xlsm, .csv, .tsv files
- **Key capabilities**: Production-grade spreadsheet creation with openpyxl. Complete API reference covering Workbook/Worksheet management, cell styling (fonts, fills, borders, alignment, number formats), row/column manipulation (insert, delete, hide, resize), named ranges, merged cells, and print area setup. 13 chart types available: bar, column, line, pie, scatter, area, doughnut, radar, bubble, stock, surface, and combo charts. Formulas and functions (SUM, AVERAGE, VLOOKUP, INDEX/MATCH, IF, COUNTIF, SUMIFS). Conditional formatting (color scales, data bars, icon sets, formula-based rules), data validation (lists, number ranges, custom formulas), and pivot tables with filters/slicers. International locale support (date formats, currency symbols, number separators). Multi-sheet workbooks with inter-sheet references. Frozen panes, auto-filters, grouped/outlined rows. Chart styling with color ramps matching the unified design system. Image embedding with scaling and positioning. ~1310 lines of reference material.

### 2.2 Visual & Data Skills

#### svg — SVG Diagram & Infographic Creation
- **File**: `skills/svg/SKILL.md`
- **Library**: Direct SVG generation (inline Python f-strings)
- **Output**: .svg files (inline in Markdown, embedded in HTML, converted to PNG/PDF)
- **Key capabilities**: Resolution-independent vector graphics engine. Complete SVG specification reference covering all shape elements (rect, circle, ellipse, line, polyline, polygon, path), path commands (M/L/H/V/C/S/Q/T/A/Z), CSS styling with custom properties and theming, animations (CSS keyframes, SMIL animate/animateTransform/animateMotion), interactive SVG (JavaScript event handlers, hover effects, tooltips), gradients (linear, radial), patterns, filters (drop-shadow, blur, color matrix, glow, neon), masking/clipping, responsive SVG with preserveAspectRatio, accessibility (ARIA labels, roles, keyboard navigation, focus indicators). 6 standard diagram types with full templates: flowcharts (with shape guide: pill=start/end, diamond=decision), architecture/system diagrams (tiered by color), timeline/Gantt charts, organization charts, mind maps, and UI wireframes (iPhone/Dektop). Animated loading spinners and progress indicators. Optimization techniques for size budget (inline: <20KB, complex: <100KB). 9 color ramps × 7 stops each, max 2 ramps per diagram, 4 hues max. Light/dark mode mapping via CSS custom properties. ~1208 lines of reference material.

#### chart — Data Chart & Graph Creation
- **File**: `skills/chart/SKILL.md`
- **Library**: matplotlib (static), plotly (interactive), python-pptx chart API, SVG (direct)
- **Output**: .png, .svg, .html, .pdf (embedded in DOCX, PPTX, PDF)
- **Key capabilities**: 23 chart types with dual-library implementations (matplotlib + plotly) for each: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar. Complete professional matplotlib setup (rcParams) and plotly theme configuration. IBM Carbon colorblind-safe palette (9 colors, tested for deuteranopia/protanopia/tritanopia). Semantic color mapping (blue=info, green=success, coral=warning, red=error). Data-ink ratio maximization, axis labeling standards, legend placement rules. Responsive sizing ratios (4:3 dashboard, 16:9 full-width, 3:4 tall, 1:1 square, 2:1 wide). Export formats: PNG (150/300dpi), SVG, HTML (cdn/local), PDF. Integrated export via create_pdf/create_docx/create_pptx section arrays. Annotations (arrows, text boxes, highlights), dual y-axes, error bars, log scales, custom colormaps. Performance handling for large datasets with decimation, WebGL scattergl, hexbin aggregation. Memory management with explicit plt.close(). Interactive features: hover tooltips, zoom, pan. ~1420+ lines of reference material.

### 2.3 Code & Development Skills

#### code_gen — Multi-Language Code Generation
- **File**: `skills/code_gen/SKILL.md`
- **Library**: Language-specific (see skill file)
- **Output**: Complete project files in any programming language
- **Key capabilities**: Two-phase code generation: mandatory Plan phase (requirements analysis, technology selection, architecture design, risk assessment, user approval) followed by Build phase (scaffolding, implementation, error handling, logging, testing, documentation, verification). Architecture pattern reference covering MVC, Microservices, Event-Driven, Serverless, Monolithic, and Hexagonal architectures with language-specific implementation notes. Design pattern implementations (Singleton, Factory, Observer, Strategy, Adapter, Decorator, Dependency Injection) in Python, TypeScript, Java, Go, Rust, C++. Language-specific deep dives for Python (FastAPI, SQLAlchemy, Pydantic, pytest), JavaScript/TypeScript (Express, Zod, Vitest), Go (Gin, table-driven tests, goroutines), Rust (Tokio, thiserror, sqlx, mockall), C++ (CMake 20, fmt, spdlog, GTest), Java (Spring Boot 3, JPA, JUnit), SQL (Alembic migrations, recursive CTEs, window functions), HTML/CSS (BEM naming, accessibility, responsive design, custom properties), and Shell/Bash/PowerShell (error handling, logging, traps). Testing methodology covers test pyramid (unit/integration/E2E) with language-specific examples. Full project scaffolding templates for each ecosystem. ~1873+ lines of reference material.

### 2.4 Security & Intelligence Skills

#### osint — Open Source Intelligence Gathering
- **File**: `skills/osint/SKILL.md`
- **Library**: 460+ OSINT functions (internal tools)
- **Output**: Structured intelligence reports, data visualizations, breach analysis
- **Key capabilities**: Complete OSINT methodology following the OSINT cycle (collection → processing → analysis → reporting). 12 primary investigation modules: social media intelligence (Twitter/X, LinkedIn, Instagram, Facebook, Reddit, Telegram, Discord, TikTok, YouTube), email intelligence (verification, breach lookup, pattern analysis, SMTP enumeration, MX/SPF/DMARC analysis, email rep scoring), domain/DNS reconnaissance (WHOIS history, subdomain enumeration, DNS record analysis, reverse IP, SSL certificate transparency logs, DNSSEC), web technology detection (CMS fingerprinting, WAF detection, JavaScript framework detection, server headers, cookie analysis), URL scanning and analysis (phishing detection, redirect chain analysis, URLScan.io integration, VirusTotal), breach and leak analysis (Have I Been Pwned, DeHashed, IntelX, Snusbase, Scylla, leak databases, credential stuffing detection), phone intelligence (carrier lookup, number portability, VoIP detection, SIM swap check, location inference), cryptocurrency tracing (blockchain explorers, wallet clustering, transaction graph analysis, mixer/Tornado Cash detection, chain hopping), dark web monitoring (Tor hidden services, onion site crawling, forum monitoring, illicit marketplace tracking), image intelligence (EXIF extraction, reverse image search, facial recognition, metadata stripping detection), geospatial intelligence (GPS coordinate analysis, map overlays, reverse geocoding, radius searches), and network intelligence (ASN lookup, BGP analysis, IP range discovery, Shodan integration). Operational security (OpSec) guidelines, OPSEC checklist, and ethical/legal compliance framework. ~2815 lines of reference material.

#### metasploit — Penetration Testing & Exploitation
- **File**: `skills/metasploit/SKILL.md`
- **Library**: msfrpc (Metasploit RPC Python library)
- **Output**: Exploitation results, meterpreter sessions, crack hashes, vulnerability reports
- **Key capabilities**: Full penetration testing workflow via msfrpc integration. Pre-exploitation: workspace management, database setup (MSF PostgreSQL), auxiliary scanning (port discovery, service identification, banner grabbing, SMB enumeration, SNMP enumeration), vulnerability scanning (Nexpose/OpenVAS integration, CVE lookup, exploit search by CVE/service/keyword), Nmap integration (port scanning, service detection, OS fingerprinting, NSE script execution). Exploitation: platform-specific payload generation (Windows/meterpreter, Linux/shell, macOS, Android, Python, PHP, ASPX), staged vs stageless payloads, payload encoding/encryption for AV evasion, handler configuration (reverse/bind, LHOST/LPORT, AutoRunScript, AutoLoadStdapi), target-specific exploit modules (SMB/MS17-010 EternalBlue, RDP/CVE-2019-0708 BlueKeep, web application exploits, SMBGhost CVE-2020-0796, Log4Shell CVE-2021-44228, ProxyShell/ProxyLogon Exchange exploits, kernel exploits for privilege escalation). Post-exploitation: meterpreter session management (upgrade shell to meterpreter, background/interact/list/kill sessions), system enumeration (OS info, user accounts, network config, processes, services, installed software, AV detection), privilege escalation (UAC bypass, token impersonation, getsystem, bypassuac modules), credential harvesting (hashdump, cachedump, Kerberos tickets, SAM/SECURITY/SYSTEM registry hives, browser credentials, SSH keys), lateral movement (pass-the-hash, pass-the-ticket, PSExec, WMI, SMB exec, SSH exec, scheduled tasks), persistence mechanisms (registry run keys, services, scheduled tasks, WMI event subscription, startup folder). Password attacks: online bruteforce (MSF auxiliary modules for SSH/FTP/SMB/HTTP/MySQL/PostgreSQL/MSSQL/VNC, Hydra wrapper, custom wordlists), offline cracking (John the Ripper for UNIX hashes, Hashcat mode selection, LM/NTLM cracking, bcrypt/scrypt, WPA PMKID), wordlist generation (CeWL, keyword expansion, mutation rules, Korean/Chinese password patterns), hash detection and identification. Web application attacks: SQL injection (error-based, union, blind/time-based, boolean, second-order, out-of-band, automated sqlmap integration), XSS (reflected, stored, DOM-based, XSSer tool, bypass techniques for WAF/filters, BeEF hooking), LFI/RFI (path traversal, PHP wrappers, log poisoning, /proc/self/environ), command injection (blind, out-of-band, chained commands), SSRF (cloud metadata endpoints, port scanning, protocol smuggling), XXE (out-of-band exfiltration, error-based, blind). Reporting: automated session logging, evidence collection (screenshots, command output, hash dumps), MSF resource script generation, Metasploit Pro report templates, MITRE ATT&CK mapping, CVSS scoring integration. ~2260 lines of reference material.

### 2.5 Summary Table

| Skill | File | Lines | Primary Library | Output Format | Primary Use Case |
|-------|------|-------|-----------------|---------------|------------------|
| docx | skills/docx/SKILL.md | 1272 | python-docx | .docx | Word documents, reports, letters |
| pptx | skills/pptx/SKILL.md | 1099 | python-pptx | .pptx | Presentations, slide decks |
| pdf | skills/pdf/SKILL.md | 1001+ | reportlab/fpdf2 | .pdf | Print-ready documents, forms |
| xlsx | skills/xlsx/SKILL.md | 1310 | openpyxl | .xlsx | Spreadsheets, data exports |
| svg | skills/svg/SKILL.md | 1208 | inline SVG | .svg | Diagrams, infographics, charts |
| chart | skills/chart/SKILL.md | 1420+ | matplotlib/plotly | .png/.svg/.html | Data visualization |
| code_gen | skills/code_gen/SKILL.md | 1873+ | language-specific | Any language | Software development |
| osint | skills/osint/SKILL.md | 2815 | custom 460+ functions | Reports/JSON | Intelligence gathering |
| metasploit | skills/metasploit/SKILL.md | 2260 | msfrpc | Sessions/Reports | Security testing |

---

## 3. Skill Domain Map

Skills are classified into domains for agent routing:

### Productivity Domain (Output-Focused)
- **DOCX** → Professional Word documents
- **PPTX** → Professional presentations
- **PDF** → Print-ready documents
- **XLSX** → Professional spreadsheets

### Visual Domain (Graphics-Focused)
- **SVG** → Diagrams, infographics, illustrations
- **CHART** → Data charts, graphs, visualizations

### Engineering Domain (Code-Focused)
- **CODE_GEN** → Software development in any language

### Intelligence Domain (Data-Focused)
- **OSINT** → Open source intelligence gathering
- **METASPLOIT** → Penetration testing

### Domain Interaction Rules

1. **Productivity + Visual**: Charts and diagrams can be embedded in documents, presentations, and PDFs
2. **Engineering + Visual**: Code generation can produce SVG and chart outputs
3. **Intelligence + Productivity**: OSINT findings are reported via DOCX/PDF/XLSX
4. **Intelligence + Visual**: Investigation results visualized via charts and diagrams

---

## 4. Cross-Reference Matrix

The following matrix shows which skills can (and should) be combined for composite tasks:

| Primary Skill | Works With | Typical Composite | Integration Method |
|--------------|-----------|-------------------|-------------------|
| **docx** | svg, chart, xlsx | Report with diagrams + charts + embedded data tables | matplotlib → BytesIO → docx.add_picture(); SVG inline string |
| **pptx** | svg, chart, xlsx | Presentation with charts + diagrams + data tables | python-pptx chart API; cairosvg SVG→PNG conversion |
| **pdf** | svg, chart, docx | Print report with diagrams + charts | create_pdf() sections array; svglib SVG render |
| **xlsx** | chart | Spreadsheet with embedded chart images | create_xlsx_chart() for embedded chart sheets |
| **svg** | chart | Infographic with data-driven chart elements | _make_chart() SVG output mode for inline chart elements |
| **chart** | docx, pptx, pdf, xlsx | Any document type with embedded charts | section-based API sections: [{"type":"chart",...}] |
| **code_gen** | svg, chart | Web dashboard with SVG/Chart visualizations | Generated code imports chart/svg libraries |
| **osint** | docx, xlsx, chart, svg | Intelligence report with data viz | osint data → chart visualization → DOCX/PDF report |
| **metasploit** | docx, xlsx | Pentest report with findings | MSF data → structured tables → DOCX/PDF report |

### Chaining Depth Rules

| Complexity | Skills Chained | Example Task | Typical Agents Used |
|------------|---------------|-------------|-------------------|
| Simple | 1 skill | "Create a bar chart" | Chart-only agent |
| Moderate | 2 skills | "Write a report with a chart" | Researcher + Document builder |
| Complex | 3 skills | "Investigate a domain and create a report with diagrams" | OSINT agent + Chart agent + Document agent |
| Advanced | 4+ skills | "Full penetration test report with visual network diagrams, data tables, and executive summary" | Recon agent + Exploit agent + Chart agent + Document agent |

---

## 5. Two-Phase Workflow Protocol

### Phase 1: RESEARCH FIRST (STRICT)

This phase is MANDATORY for every task. The agent MUST NOT touch output-format skills during this phase.

**Step-by-step:**

1. **Parse the user request** — Identify all explicit and implicit requirements
2. **Determine skill domain** — Which skills will be needed? (See Section 6 for selection algorithm)
3. **Gather factual data** — Use web_search, web_fetch, grep, read_file, memory_retrieve, osint tools
4. **Collect supporting materials** — Statistics, citations, quotes, reference images, data sources
5. **Structure the content** — Outline headings, slide titles, data tables, chart types
6. **Verify completeness** — Confirm you have enough data to generate the deliverable
7. **Present research summary** — Show the user what you've gathered before building

**Phase 1 Rules:**
- DO NOT open any output-format skill files during research
- DO NOT create any output files during research
- DO use research tools exclusively (web, memory, file reading, grep)
- Content gathering happens BEFORE format decisions

### Phase 2: BUILD SECOND (STRICT)

Only after research is complete:

1. **Read all relevant skill files** — Open every SKILL.md for skills identified in Phase 1
2. **Follow skill instructions** — Libraries, patterns, design system, quality checks
3. **Build the deliverable** — Generate the output file following the skill's code patterns
4. **Run quality checklist** — Verify against the skill's quality checklist
5. **Deliver** — Present the output to the user

**Phase 2 Rules:**
- DO read ALL relevant skill files before building
- DO follow the design system (colors, fonts, layouts)
- DO run the quality checklist before delivery
- DO NOT reuse skill patterns from memory — always re-read the file

---

## 6. Agent Skill Selection Algorithm

When FRIDAY receives a task, the skill selector determines which skills to use:

### Step 1: Trigger Match

Scan user request against each skill's trigger patterns (from frontmatter and triggers section):

```
Scan triggers in order:
1. docx triggers    → "write a report", "create a document", "memo", "letter", "resume", "contract"
2. pptx triggers    → "make a presentation", "create slides", "slide deck", "pitch deck", "PowerPoint"
3. pdf triggers     → "create a PDF", "make a PDF", "report", "invoice", "certificate", "form"
4. xlsx triggers    → "create a spreadsheet", "Excel file", "data to a sheet", "pivot table"
5. svg triggers     → "diagram", "flowchart", "infographic", "illustration", "architecture diagram"
6. chart triggers   → "chart", "graph", "plot", "visualize data", "bar chart", "line graph"
7. code_gen triggers → "write code", "create a script", "build an app", "implement", "program"
8. osint triggers   → "OSINT", "reconnaissance", "investigate", "intelligence gathering"
9. metasploit triggers → "exploit", "penetration test", "metasploit", "meterpreter"
```

### Step 2: Domain Classification

Classify the task into one or more domains:

```
If only productivity triggers → Document task
If only visual triggers       → Visual task
If only engineering triggers  → Development task
If only intelligence triggers → Investigation task
If multiple domains matched   → Composite task (requires chaining)
```

### Step 3: Skill Chain Construction

For composite tasks, construct a dependency chain:

```
Algorithm:
1. Identify primary output format (what file type is requested)
2. Identify supporting formats (diagrams, charts, tables within)
3. Create execution order:
   a. Intelligence skills first (gather data)
   b. Visual skills second (create assets)
   c. Productivity skills third (assemble deliverable)
4. Read skill files in execution order
5. Execute in order, passing intermediate outputs between steps
```

### Step 4: Priority Scoring

When multiple skills match, use this scoring system:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Trigger match | 5 | Number and specificity of trigger pattern matches |
| Output format match | 4 | Does user explicitly request a format? |
| Content type match | 3 | Does the content suit this skill's capabilities? |
| Composite necessity | 2 | Is this skill needed as a dependency? |
| User history | 1 | Has user preferred this skill before? |

Select the skill(s) with the highest total score.

---

## 7. Skill Chaining & Composition

### 7.1 Sequential Chaining

Skills execute in sequence, passing outputs forward:

```
Research Agent → svg Agent → docx Agent → Final .docx
     │              │           │
     │          Creates SVG  Embeds SVG
     │          diagram      in document
     │              │
Gathers data ───────┘
for diagram
```

### 7.2 Parallel Chaining

Skills execute independently, outputs merged later:

```
             ┌── svg Agent ──┐
Research ────┤               ├── docx Agent → Final .docx
             └── chart Agent ┘
```

### 7.3 Nesting (Embedding)

One skill's output is embedded inside another's output:

```
create_docx(sections=[
    {'type': 'text', 'content': '## Analysis'},
    {'type': 'chart', 'chart_type': 'bar', 'data': data},  ← chart skill nested
    {'type': 'svg', 'svg_content': diagram},                 ← svg skill nested
])
```

### 7.4 Cross-Skill Data Flow

Data transfer patterns between skills:

| From | To | Method | Notes |
|------|----|--------|-------|
| osint | docx | JSON data → section array | OSINT results as structured content |
| osint | chart | Data arrays → chart data | Investigation metrics visualized |
| chart | docx | BytesIO PNG → docx.add_picture() | Chart rendered as image in document |
| chart | pptx | matplotlib → pptx chart API | Native chart objects in slides |
| chart | pdf | section type 'chart' | PDF-rendered chart |
| svg | docx | Inline SVG string → XML embed | SVG embedded in docx XML |
| svg | pptx | cairosvg PNG → slide picture | SVG converted to PNG for PowerPoint |
| svg | pdf | section type 'svg' | Direct SVG rendering in PDF |
| code_gen | svg | Generated code imports SVG lib | Web apps with inline diagrams |
| code_gen | chart | Generated code imports chart lib | Dashboards with chart components |
| metasploit | docx | Structured tables → DOCX tables | Pentest findings in report |
| metasploit | chart | Vulnerability counts → chart | Visual vulnerability breakdown |

### 7.5 Skill Chain Examples

**Example 1: Executive Report with Visuals**
```
1. Research Agent: Gather financial data, quarterly results
2. chart Agent: Create revenue bar chart → PNG bytes
3. svg Agent: Create architecture diagram → SVG string
4. docx Agent: Read docx/SKILL.md, assemble report with embedded chart + diagram
5. Output: Quarterly_Report.docx
```

**Example 2: Security Assessment Deck**
```
1. osint Agent: Perform domain recon, find exposed services
2. metasploit Agent: Test vulnerabilities, gather findings
3. chart Agent: Create vulnerability severity pie chart
4. svg Agent: Create network topology diagram
5. pptx Agent: Build presentation with findings
6. Output: Security_Assessment.pptx
```

**Example 3: Data Dashboard Web App**
```
1. code_gen Agent: Design architecture, scaffold project
2. chart Agent: Define chart components for dashboard
3. svg Agent: Create logo, loading animations, icons
4. code_gen Agent (cont): Implement full application
5. Output: dashboard/ (full project directory)
```

---

## 8. Unified Design System Reference

All visual skills (docx, pptx, svg, pdf, xlsx, chart) share a unified design system. This ensures consistent branding regardless of output format.

### 8.1 Color Ramps (9 Ramps × 7 Stops)

These color ramps are IDENTICAL across docx, pptx, svg, chart, pdf, and xlsx skills. DO NOT modify.

| Ramp | 50 | 100 | 200 | 400 | 600 | 800 | 900 |
|------|-----|------|------|------|------|------|------|
| Purple | #EEEDFE | #CECBF6 | #AFA9EC | #7F77DD | #534AB7 | #3C3489 | #26215C |
| Teal | #E1F5EE | #9FE1CB | #5DCAA5 | #1D9E75 | #0F6E56 | #085041 | #04342C |
| Coral | #FAECE7 | #F5C4B3 | #F0997B | #D85A30 | #993C1D | #712B13 | #4A1B0C |
| Pink | #FBEAF0 | #F4C0D1 | #ED93B1 | #D4537E | #993556 | #72243E | #4B1528 |
| Gray | #F1EFE8 | #D3D1C7 | #B4B2A9 | #888780 | #5F5E5A | #444441 | #2C2C2A |
| Blue | #E6F1FB | #B5D4F4 | #85B7EB | #378ADD | #185FA5 | #0C447C | #042C53 |
| Green | #EAF3DE | #C0DD97 | #97C459 | #639922 | #3B6D11 | #27500A | #173404 |
| Amber | #FAEEDA | #FAC775 | #EF9F27 | #BA7517 | #854F0B | #633806 | #412402 |
| Red | #FCEBEB | #F7C1C1 | #F09595 | #E24B4A | #A32D2D | #791F1F | #501313 |

### 8.2 Semantic Color Mapping

Applies uniformly across ALL visual skills:

| Meaning | Ramp | Stop | Hex | Usage |
|---------|------|------|-----|-------|
| Primary / Info | Blue | 400 | #378ADD | Main interactive elements, links, chart series |
| Success / Positive | Green | 400 | #639922 | Growth indicators, positive metrics, checkmarks |
| Warning / Caution | Amber | 400 | #BA7517 | Warnings, medium severity, pending status |
| Error / Negative | Coral | 600 | #993C1D | Errors, declines, high severity |
| Neutral / Structure | Gray | 400 | #888780 | Borders, secondary text, icons |
| Dark Text | Gray | 900 | #2C2C2A | Primary body text (NOT pure black) |
| Light Text | Gray | 50 | #F1EFE8 | Text on dark backgrounds |
| Background | Gray | 50 | #F1EFE8 | Page/slide background, alternating rows |
| Category 1 | Purple | 400 | #7F77DD | Categorical data, section headers |
| Category 2 | Teal | 400 | #1D9E75 | Categorical data, accent elements |
| Highlight | Pink | 400 | #D4537E | Alert badges, call-to-action, highlights |

### 8.3 Color Usage Rules (Universal)

1. **Max 3 colors** per slide/document page (not counting images or charts)
2. **Max 2 color ramps** per diagram
3. **Max 4 hues** in a single diagram
4. **Never use pure black (#000)** for body text — use Gray 900 (#2C2C2A) or Gray 800 (#444441)
5. **Never use pure white (#FFF)** for body text on light backgrounds
6. **Text on colored backgrounds**: Use 800/900 stops from the SAME ramp
7. **Light text on dark**: Gray 50 for titles, Gray 100/200 for body
8. **Data charts**: Use 4-6 distinct hues from the palette
9. **Color encodes MEANING**, not sequence
10. **Colorblind safety**: Avoid red-green pairs; use shape+color redundancy

### 8.4 Light/Dark Mode Mapping

| Element | Light Mode | Dark Mode |
|---------|-----------|-----------|
| Background fill | Gray 50 (#F1EFE8) | Gray 900 (#2C2C2A) |
| Card/box fill | White (#FFFFFF) | Gray 800 (#444441) |
| Primary stroke | Blue 400 (#378ADD) | Blue 200 (#85B7EB) |
| Title text | Gray 900 (#2C2C2A) | Gray 50 (#F1EFE8) |
| Body text | Gray 600 (#5F5E5A) | Gray 200 (#B4B2A9) |
| Secondary text | Gray 400 (#888780) | Gray 400 (#888780) |
| Border lines | Gray 200 (#B4B2A9) | Gray 600 (#5F5E5A) |
| Hover state | Blue 400 (#378ADD) | Blue 400 (#378ADD) |

### 8.5 Unified Type Scale

| Role | DOCX (pt) | PPTX (pt) | SVG (px) | PDF (pt) | Weight |
|------|-----------|-----------|----------|----------|--------|
| Document/Slide Title | 26 | 36-44 | 18 (t-xl) | 24-30 | Bold |
| Heading 1 / Section Title | 18 | 28 | 16 (t-l) | 18 | Bold/SemiBold |
| Heading 2 / Subtitle | 16 | 24 | 14 (t) | 16 | SemiBold |
| Heading 3 / Card Title | 14 | 20 | 14 (th) medium | 14 | Bold |
| Heading 4 | 12 | 18 | 14 (th) | 12 | Bold |
| Body text | 11 | 18 | 14 (t) | 11-12 | Regular |
| Small/Caption | 9 | 14 | 12 (ts) | 9-10 | Regular |
| Extra small | — | 12 | 10 (txs) | 8-9 | Regular |
| KPI / Data numbers | — | 44 | — | — | Bold |
| Table header | 10 | 16 | — | 10 | Bold |
| Table body | 10 | 14 | — | 10 | Regular |
| Footer / page number | 9 | 12 | — | 8-9 | Regular |

### 8.6 Font Rules (Universal)

1. **Max 2 fonts** per document/presentation/deck
2. **Preferred fonts**: Calibri (headings) + Calibri Light (body), or Segoe UI throughout
3. **Cross-platform safe fonts**: Calibri, Calibri Light, Segoe UI, Arial, Times New Roman, Helvetica, Verdana, Tahoma, Georgia, Cambria
4. **SVG uses**: system-ui, sans-serif font stack (to match OS)
5. **Minimum sizes**: 11pt for documents, 14pt for presentations, 12px for SVG
6. **Footer minimum**: 9pt for documents, 12pt for presentations
7. **Always set font size explicitly** — never rely on defaults

### 8.7 Layout Grid (PPTX/DOCX)

| Property | DOCX (A4) | PPTX (Widescreen) |
|----------|-----------|-------------------|
| Page size | 21.0 × 29.7 cm | 13.333 × 7.5 inches |
| Left/Right margin | 2.54 cm | 0.8 inches |
| Top margin | 2.54 cm | 0.5 inches |
| Bottom margin | 2.54 cm | 0.75 inches |
| Content area | 15.92 × 24.62 cm | 11.733 × 6.25 inches |
| Grid columns | — | 12 columns × 0.9″ |
| Grid gutter | — | 0.2 inches |
| Grid rows | — | 6 rows × 0.95″ |

### 8.8 Shadow and Effects

All skills use consistent shadow parameters:
- **Box shadow**: `dx=2, dy=2, blur=3, opacity=0.15`
- **Heavy shadow**: `dx=0, dy=4, blur=6, opacity=0.25`
- **Text shadow**: Avoid in body text; use sparingly on titles only

### 8.9 Line/Border Styling

| Element | Stroke Width | Color | Style |
|---------|-------------|-------|-------|
| Table border | 0.5pt | Gray 200 (#B4B2A9) | Solid |
| Accent lines | 2-3pt | Blue 400 (#378ADD) | Solid |
| Divider rules | 1pt | Gray 200 (#B4B2A9) | Solid |
| Diagram arrows | 1.5pt | Gray 400 (#888780) | Solid |
| Dashed (grouping) | 1.5pt | Gray 200 (#B4B2A9) | Dashed (8,4) |
| Chart axis | 0.8pt | Gray 200 (#B4B2A9) | Solid |
| Chart gridlines | 0.5pt | Gray 50 (#F1EFE8) | Solid |

---

## 9. FRIDAY Document Generation Pipeline

### 9.1 Pipeline Architecture

```
User Request
    │
    ▼
┌─────────────────────────────────────────────┐
│ 1. Request Router                             │
│    - Parse natural language request           │
│    - Identify primary output format           │
│    - Detect supporting skill needs            │
│    - Route to appropriate agent               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 2. Research Phase                            │
│    - Web fetch, search, memory retrieval     │
│    - Data collection, fact verification      │
│    - Content structuring, outlining          │
│    - Present research summary to user        │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 3. Skill File Loader                         │
│    - Read SKILLS.md master index             │
│    - Read primary skill SKILL.md             │
│    - Read supporting skills' SKILL.md files  │
│    - Extract design system, patterns, rules  │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 4. Asset Generation (Parallel)               │
│    ├── Chart generator: matplotlib/plotly    │
│    ├── SVG generator: inline SVG strings     │
│    ├── Data tables: structured arrays        │
│    └── Code generator: language-specific     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 5. Document Assembly                         │
│    ├── DOCX: python-docx section builder     │
│    ├── PPTX: python-pptx slide builder       │
│    ├── PDF: reportlab/fpdf2 page builder     │
│    ├── XLSX: openpyxl workbook builder       │
│    └── SVG: direct SVG string concatenation  │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 6. Quality Verification                      │
│    - Skill-specific quality checklist        │
│    - Render verification (open file)         │
│    - Size optimization check                 │
│    - Cross-format consistency check          │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ 7. Delivery                                  │
│    - Save output file                        │
│    - Present to user with summary            │
│    - Offer modification options              │
└─────────────────────────────────────────────┘
```

### 9.2 Section-Based API

For composite documents, use the unified sections API:

```python
# Common section schema for all document types
result = create_docx(sections=[
    # Text sections
    {'type': 'text', 'content': '# Title', 'style': 'heading1'},
    {'type': 'text', 'content': 'Body paragraph', 'style': 'body'},

    # Table sections
    {'type': 'table', 'headers': ['Col1', 'Col2'], 'data': [['a', 'b']]},

    # Chart sections (automatically rendered)
    {'type': 'chart', 'chart_type': 'bar', 'data': {...}, 'title': 'Revenue'},

    # SVG sections (automatically embedded)
    {'type': 'svg', 'svg_content': '<svg>...</svg>', 'width': 500, 'height': 300},

    # Image sections
    {'type': 'image', 'path': 'chart.png', 'width': 500, 'caption': 'Figure 1'},

    # Page control sections
    {'type': 'page_break'},
    {'type': 'section_break', 'orientation': 'landscape'},
])
```

### 9.3 Document Generation Tracking

| Stage | Status | Quality Gate | Responsible |
|-------|--------|-------------|-------------|
| Request Parsed | ✅/❌ | All requirements identified | Request Router |
| Research Complete | ✅/❌ | Data sufficient for output | Research Agent |
| Skill Files Loaded | ✅/❌ | All required skills read | Skill Loader |
| Assets Generated | ✅/❌ | Dependencies resolved | Asset Generators |
| Document Assembled | ✅/❌ | No runtime errors | Document Builder |
| Quality Verified | ✅/❌ | Checklist passes | Quality Verifier |
| Delivered | ✅/❌ | File exists, user confirmed | Delivery Agent |

---

## 10. Agent-to-Skill Mapping

### 10.1 Agent Directory

FRIDAY's multi-agent system maps skills to specific agent types:

| Agent Role | Primary Skills | Secondary Skills | Typical Task |
|-----------|---------------|-----------------|--------------|
| **Document Writer** | docx, pdf | svg, chart | Reports, letters, whitepapers |
| **Presentation Designer** | pptx | chart, svg | Pitch decks, review slides |
| **Spreadsheet Analyst** | xlsx | chart | Data analysis, financial reports |
| **Diagram Designer** | svg | chart | Infographics, flowcharts, architecture |
| **Data Visualizer** | chart | svg | Charts, dashboards, data viz |
| **Software Engineer** | code_gen | svg, chart | Applications, scripts, tools |
| **Investigator** | osint | docx, xlsx, chart | Intelligence reports |
| **Security Tester** | metasploit | docx, xlsx | Pentest reports |
| **Research Analyst** | (research tools) | all output skills | Gather data for downstream agents |
| **Quality Inspector** | (verification tools) | all skills | Validate output before delivery |

### 10.2 Agent Delegation Flow

```
Task Received
    │
    ▼
┌─────────────┐
│ Lead Agent   │── Determines skill(s) needed
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Delegation Decision                  │
│                                     │
│ Single skill? → Execute directly    │
│ Multiple skills? → Chain agents     │
│                                     │
│ Use case: Complex report            │
│ 1. Lead → Research Agent (gather)   │
│ 2. Research → Chart Agent (visuals) │
│ 3. Chart + Research → Doc Agent     │
└─────────────────────────────────────┘
```

### 10.3 Agent Communication Protocol

When agents are chained, data passes via structured messages:

```json
{
  "task_id": "uuid-1234",
  "agent_chain": ["research", "chart", "docx"],
  "current_agent": "chart",
  "input_data": {"categories": ["Q1","Q2","Q3"], "values": [100,200,300]},
  "output_data": {},
  "skill_files_loaded": ["chart/SKILL.md"],
  "quality_checks_passed": [],
  "errors": []
}
```

---

## 11. Skill File Loading Protocol

### 11.1 Reading Protocol (STRICT)

Before ANY generation, the agent MUST follow this loading sequence:

```
1. READ skills/SKILLS.md      ← Master index (this file)
   - Identify which skills are needed
   - Check cross-reference matrix for dependencies
   - Note any special chaining requirements

2. READ skills/<skill>/SKILL.md  ← Primary skill file
   - Read from beginning to end
   - Note: libraries, code patterns, design system
   - Pay special attention to "What to AVOID" section
   - Run quality checklist items mentally

3. READ skills/<dependency>/SKILL.md  ← Supporting skill files
   - Repeat step 2 for each dependency
   - Read all supporting skills BEFORE starting generation

4. BEGIN GENERATION
   - Only after all skill files are loaded
   - Follow the exact patterns from the skill files
```

### 11.2 Cache Invalidation

Skill files are cached in the agent's context but MUST be re-read if:

- The task involves a different skill than previously used
- The agent has generated more than 5 outputs since last reading
- The user reports an issue that might be skill-related
- More than 10 minutes have elapsed since last read
- The skill file has been modified (check timestamp)

### 11.3 Loading Verification

After reading, verify comprehension:

- [ ] Can state the primary library for the skill
- [ ] Can state the font family and type scale
- [ ] Can state the color palette rules (max 3 colors, semantic mapping)
- [ ] Can list the "What to AVOID" rules
- [ ] Can list the quality checklist items
- [ ] Can explain how this skill composes with dependencies
- [ ] Can identify the correct output format and extensions

### 11.4 Missing Skill Handling

If a required skill does not exist:

1. Check the domain map for an equivalent skill
2. If no equivalent exists, generate output using general best practices
3. Log the gap: "Missing skill: [task]. Used general approach."
4. If the skill is critical, ask the user for guidance

---

## 12. Quality Standards Document

### 12.1 Universal Quality Standards

These apply to EVERY skill output:

#### Content Quality
- [ ] All content is factually accurate and sourced
- [ ] No placeholder text remains
- [ ] No placeholder lorem ipsum text
- [ ] All numbers and statistics are verified
- [ ] Spelling and grammar are correct
- [ ] Citations and references are complete and correctly formatted
- [ ] Content is appropriate for the intended audience
- [ ] No contradictory information within the document
- [ ] All claims are supported by evidence
- [ ] Dates and time references are accurate

#### Design Quality
- [ ] Consistent typography applied throughout
- [ ] Color palette follows the unified design system
- [ ] Maximum color usage limits respected (3 per page, 2 ramps per diagram)
- [ ] No pure black (#000) for body text
- [ ] Sufficient contrast (4.5:1 minimum ratio)
- [ ] Font sizes meet minimum requirements per format
- [ ] Proper spacing and margins
- [ ] No overlapping elements
- [ ] Images maintain aspect ratio
- [ ] Alignment is consistent

#### Technical Quality
- [ ] Correct file format and extension
- [ ] File is not corrupted (opens correctly)
- [ ] All embedded assets are embedded (not linked)
- [ ] Font embedding considered for cross-platform use
- [ ] File size is reasonable for content
- [ ] Metadata is set (title, author, date)
- [ ] No external dependencies for rendering (unless expected)
- [ ] Cross-platform compatibility verified

### 12.2 Format-Specific Quality Standards

#### DOCX Quality Standards
- [ ] A4 page setup with 2.54cm margins
- [ ] Title page with proper spacing
- [ ] Consistent heading hierarchy (H1→H2→H3)
- [ ] Justified body text with first-line indent
- [ ] Styled table headers (blue background, white text)
- [ ] Table of contents for documents over 5 pages
- [ ] Headers and footers with page numbers
- [ ] Page numbers present (except title page)
- [ ] Hyperlinks work correctly
- [ ] Images have descriptive captions
- [ ] Alternating row colors on tables with 5+ rows

#### PPTX Quality Standards
- [ ] Widescreen 16:9 dimensions set explicitly
- [ ] Every slide has a meaningful title
- [ ] Max 6 bullets per slide, 10 words per bullet
- [ ] Font sizes meet minimums (14pt content, 12pt footers)
- [ ] Max 2 fonts per deck
- [ ] Max 3 colors per slide
- [ ] No placeholder text on any slide
- [ ] Charts use proper CategoryChartData
- [ ] Tables have styled header rows
- [ ] Slide count is appropriate for content
- [ ] Consistent margins and spacing across all slides

#### PDF Quality Standards
- [ ] Pages are properly ordered and numbered
- [ ] Text is selectable (not rasterized)
- [ ] Fonts are embedded (for PDF/A compliance)
- [ ] Hyperlinks are active
- [ ] Bookmarks/outline structure is present for 10+ page docs
- [ ] File size is optimized
- [ ] Print margins are correct (no content in non-printable area)
- [ ] PDF/A validation passes if archival compliance required
- [ ] Color spaces correct (CMYK for print, RGB for screen)
- [ ] Security settings are appropriate (no protection for general docs)

#### XLSX Quality Standards
- [ ] Columns are appropriately sized (not default narrow)
- [ ] Header row is frozen
- [ ] AutoFilter is applied to data ranges
- [ ] Number formatting is appropriate ($, %, comma separators)
- [ ] Consistent decimal precision across columns
- [ ] No empty rows within data range
- [ ] Sheet names are meaningful (not "Sheet1")
- [ ] Print area is set
- [ ] Page layout is configured (orientation, scaling)
- [ ] Data validation is applied where appropriate
- [ ] Conditional formatting highlights important patterns

#### SVG Quality Standards
- [ ] viewBox is set correctly
- [ ] xmlns attribute is present
- [ ] All tags are properly closed
- [ ] No empty <g> groups
- [ ] No duplicate IDs
- [ ] Max 2 color ramps used
- [ ] Text size ≥ 12px
- [ ] Text contrast ≥ 4.5:1
- [ ] Flow direction is clear
- [ ] Arrows point in logical direction
- [ ] Accessibility: role="img", aria-label, <title>, <desc>

#### Chart Quality Standards
- [ ] Chart type matches data characteristics
- [ ] Axes are labeled with units
- [ ] Legend is present for multi-series charts
- [ ] Data labels are clear and non-overlapping
- [ ] Y-axis starts at 0 for bar charts
- [ ] Color palette is colorblind-safe
- [ ] Title is descriptive
- [ ] Source citation is included
- [ ] Appropriate aspect ratio is used
- [ ] No chart junk or 3D effects for 2D data

### 12.3 Quality Scoring Matrix

| Level | Score | Criteria | Action |
|-------|-------|----------|--------|
| Gold | 95-100% | All checks pass, exceptional design | Deliver as-is |
| Silver | 85-94% | All critical checks pass, minor cosmetic issues | Fix cosmetic issues, deliver |
| Bronze | 70-84% | All critical checks pass, multiple cosmetic issues | Fix issues, re-verify |
| Failing | <70% | Critical checks failing | Rebuild from scratch |

### 12.4 Automated Verification Script

```python
def verify_output(file_path: str, skill: str) -> dict:
    checks = {
        'exists': os.path.exists(file_path),
        'size_valid': os.path.getsize(file_path) < MAX_SIZE_MAP[skill],
        'opens_correctly': test_open(file_path, skill),
        'has_content': test_content(file_path, skill),
        'follows_design': test_design(file_path, skill),
    }
    score = sum(1 for v in checks.values() if v) / len(checks) * 100
    return {'path': file_path, 'score': score, 'checks': checks}
```

---

## 13. Troubleshooting Guide for Skill Integration

### 13.1 Common Integration Problems

#### Problem: Skill file not found
- **Error**: `FileNotFoundError: skill/<name>/SKILL.md`
- **Cause**: Skill directory missing or skill not yet created
- **Diagnosis**: Check `friday/skills/` directory listing
- **Solution**: Use an equivalent skill or create the missing skill file
- **Prevention**: Verify skill exists before referencing in chain

#### Problem: Cross-skill data type mismatch
- **Error**: `TypeError` or chart not rendering in docx
- **Cause**: Data format from chart skill incompatible with docx embedding
- **Diagnosis**: Check intermediate data structure
- **Solution**: Convert to BytesIO for image embedding; use section API for automatic handling
- **Prevention**: Use the unified sections API (type='chart', type='svg')

#### Problem: Color mismatch across format
- **Symptom**: Same color looks different in DOCX vs SVG vs PDF
- **Cause**: Color space handling differs (RGB vs sRGB vs CMYK)
- **Diagnosis**: Compare hex values across skill outputs
- **Solution**: Use consistent hex values from the unified color ramps; set color space explicitly in PDF
- **Prevention**: Always use hex values from the color ramp table

#### Problem: Font fallback differences
- **Symptom**: Text reflows or uses different font in different viewers
- **Cause**: Font not available on target system
- **Diagnosis**: Check which fonts are actually embedded
- **Solution**: Use SAFE_FONTS list; embed fonts in PDF; use system-ui stack in SVG
- **Prevention**: Only use fonts from the safe list

#### Problem: Image resolution mismatch
- **Symptom**: Images look pixelated in print but fine on screen
- **Cause**: Low DPI setting for print output
- **Diagnosis**: Check image DPI in output
- **Solution**: Use 300dpi for print (DOCX/PDF), 150dpi for screen (PPTX)
- **Prevention**: Set DPI per output format in skill configuration

#### Problem: File size too large
- **Symptom**: Output file is 50MB+ for a simple document
- **Cause**: Uncompressed images, embedded fonts, raw SVG
- **Diagnosis**: Check file size per component
- **Solution**: Compress images (PIL quality=85, optimize=True); use JPEG for photos; reduce SVG precision
- **Prevention**: Set size targets: DOCX <5MB, PPTX <5MB (20 slides), PDF <2MB (text-only)

#### Problem: SVG not rendering in DOCX
- **Symptom**: Red X placeholder or missing image in Word
- **Cause**: SVG not natively supported in python-docx
- **Diagnosis**: Check DOCX XML for image relationships
- **Solution**: Convert SVG to PNG via cairosvg before embedding
- **Prevention**: Use the section API with type='svg' for automatic conversion

#### Problem: Chart data not showing in PPTX
- **Symptom**: Chart placeholder, no data
- **Cause**: ChartData not properly populated
- **Diagnosis**: Print chart data before adding to slide
- **Solution**: Verify all series have same length as categories
- **Prevention**: Always validate chart_data before passing to add_chart()

#### Problem: PDF text not selectable
- **Symptom**: Text appears as image, cannot copy/paste
- **Cause**: Font not embedded, or text rendered as paths
- **Diagnosis**: Check PDF properties in viewer
- **Solution**: Embed fonts; use reportlab's canvas.drawString not drawImage
- **Prevention**: Always set PDF font embedding in reportlab configuration

#### Problem: XLSX formulas not calculating
- **Symptom**: Cells show formula text, not computed value
- **Cause**: Open in viewer with disabled macros or manual calculation
- **Diagnosis**: Check CalculationProperties
- **Solution**: Set `wb.calculation.calcMode = 'auto'`
- **Prevention**: Always set calculation mode explicitly

### 13.2 Chain Failure Recovery

| Failure Point | Symptom | Recovery Action |
|--------------|---------|-----------------|
| Research phase incomplete | Missing data in output | Re-run research, re-verify data sufficiency |
| Asset generation fails | No chart/SVG created | Fall back to simpler asset (text table, ASCII art) |
| Assembly fails | Document creation crashes | Check each section independently, isolate failing section |
| Quality check fails | Checklist items not met | Fix specific items, re-run verification |
| File corruption | Output won't open | Regenerate from scratch, use simpler patterns |

### 13.3 Diagnostic Commands

```python
# Test skill file loading
def test_skill_load(skill_name: str) -> bool:
    path = f"skills/{skill_name}/SKILL.md"
    return os.path.exists(path)

# Test cross-skill data bridge
def test_chart_to_docx_bridge():
    from tools_flat import _make_chart, create_docx
    result = _make_chart('bar', {'categories': ['A','B'], 'values': [1,2]}, 'svg')
    doc = create_docx(sections=[{'type': 'svg', 'svg_content': result}])
    return doc.paragraphs[-1].text != ''

# Test color ramp consistency
def test_color_ramp_sync():
    docx_colors = {...}  # from docx/SKILL.md
    pptx_colors = {...}   # from pptx/SKILL.md
    svg_colors = {...}    # from svg/SKILL.md
    assert docx_colors == pptx_colors == svg_colors
```

### 13.4 Logging and Debugging

Standard log format for skill operations:

```
[SKILL] docx: Loading skill file (1272 lines)
[SKILL] docx: Design system applied — Calibri 11pt, Gray 900 body
[SKILL] docx: Section 1/4: Title page created
[SKILL] docx: Section 2/4: Chart embedded (matplotlib → BytesIO → picture)
[SKILL] docx: Quality check — 12/12 checks passed
[SKILL] docx: Output saved to Quarterly_Report.docx (1.2MB)
[SKILL] docx: Completed in 3.4s
```

---

## 14. Performance & Optimization Guidelines

### 14.1 File Size Budgets

| Format | Target | Warning | Critical | Notes |
|--------|--------|---------|----------|-------|
| DOCX (text-only) | < 1 MB | > 2 MB | > 5 MB | Images increase size significantly |
| DOCX (with images) | < 5 MB | > 10 MB | > 20 MB | Compress images to 150dpi max |
| PPTX (10 slides) | < 3 MB | > 5 MB | > 10 MB | Each image adds ~200-500KB |
| PPTX (20 slides) | < 5 MB | > 10 MB | > 20 MB | Use JPEG for photos, PNG for diagrams |
| PDF (text-only) | < 1 MB | > 2 MB | > 5 MB | Font embedding adds ~100KB/font |
| PDF (with images) | < 5 MB | > 10 MB | > 20 MB | 300dpi for print, 150dpi for screen |
| XLSX (data-only) | < 1 MB | > 5 MB | > 10 MB | Formulas increase file size |
| XLSX (with charts) | < 3 MB | > 8 MB | > 15 MB | Chart images embedded separately |
| SVG (inline) | < 20 KB | > 50 KB | > 100 KB | Reduce decimal precision |
| SVG (complex) | < 100 KB | > 200 KB | > 500 KB | Max for animated SVGs <200KB |
| Chart PNG (screen) | < 100 KB | > 200 KB | > 500 KB | 150dpi, quality=85 |
| Chart PNG (print) | < 300 KB | > 500 KB | > 1 MB | 300dpi, quality=90 |

### 14.2 Optimization Techniques by Format

**DOCX Optimization:**
- Compress images with PIL before embedding: `Image.save(fp, quality=85, optimize=True)`
- Resize images to max 1920px width before embedding
- Use PNG for diagrams, JPEG for photos
- Avoid excessive table nesting
- Minimize use of raw XML manipulation

**PPTX Optimization:**
- Resize images to max 1920px width
- Use JPEG compression quality 85
- Limit number of chart data points to <100 per series
- Avoid embedding video directly
- Use theme-based styling instead of per-slide overrides

**PDF Optimization:**
- Use subset font embedding (only embed used characters)
- Compress images with PIL before embedding
- Use PDF/X or PDF/A profiles for specific use cases
- Linearize PDF for web delivery
- Flatten form fields for final distribution

**XLSX Optimization:**
- Use data validation ranges instead of thousands of individual rules
- Limit conditional formatting to essential rules
- Use calculated columns (single formula) instead of per-row formulas
- Remove unused styles with `openpyxl.styles.Style` cleanup

**SVG Optimization:**
- Reduce decimal precision to 1 decimal place
- Use `<use>` elements for repeated shapes
- Flatten nested `<g>` groups
- Remove unused defs and comments
- Combine adjacent `<path>` elements with matching styles

**Chart Optimization:**
- For 100K+ points: use WebGL (scattergl), decimation, or aggregation
- Use `rasterized=True` for dense matplotlib paths
- Close figures explicitly: `plt.close(fig)`
- Use `io.BytesIO` for in-memory processing

### 14.3 Memory Management

```python
# Profile memory usage
import tracemalloc
tracemalloc.start()

# Generate document
result = create_docx(sections=[...])

# Report memory
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f}MB, Peak: {peak / 1024 / 1024:.1f}MB")
tracemalloc.stop()

# Best practices:
# - Close matplotlib figures: plt.close('all')
# - Use BytesIO for intermediate files
# - Delete large temporary objects: del large_array
# - Process images sequentially, not all at once
# - For very large documents, generate in chunks
```

---

## 15. Security & Compliance Guidelines

### 15.1 Output Security

| Concern | Guideline | Skills Affected |
|---------|-----------|-----------------|
| Sensitive data in output | Never include passwords, keys, tokens in generated files | All skills |
| Metadata leakage | Clear author/company metadata if delivering to external party | docx, pdf, pptx |
| Hidden data | Remove comments, revision marks, hidden slides before delivery | docx, pptx |
| SVG sanitization | Strip `<script>` and `on*` attributes from user-provided SVGs | svg |
| PDF JavaScript | Disable JavaScript in PDF output by default | pdf |
| Excel macros | Never include VBA unless explicitly requested | xlsx |
| Hyperlink safety | Verify all external links use HTTPS | All skills |
| File permissions | Set appropriate file permissions on output | All skills |

### 15.2 Ethical & Legal Compliance

| Skill | Restriction | Enforcement |
|-------|-------------|-------------|
| osint | Ethical OSINT only — no stalking, harassment, or unauthorized surveillance | Trigger warning at top of skill file |
| metasploit | Authorized testing only — written authorization required | Trigger warning, no auto-exploitation |
| code_gen | No generation of malware, ransomware, or malicious code | Agent-level guardrails |
| All skills | Respect copyright — no reproduction of proprietary content | Content verification |

### 15.3 Safe File Handling

```python
# Always validate paths
def safe_save(file_path: str, content) -> bool:
    allowed_dirs = [os.getcwd(), os.path.expanduser("~/Desktop")]
    parent = os.path.dirname(os.path.abspath(file_path))
    if not any(parent.startswith(d) for d in allowed_dirs):
        raise PermissionError(f"Cannot save outside allowed directories: {parent}")
    with open(file_path, 'wb') as f:
        f.write(content)
    return True
```

---

## 16. Testing Each Skill Output

### 16.1 Automated Verification

```python
def test_skill_output(file_path: str, skill: str) -> dict:
    results = {'skill': skill, 'file': file_path, 'checks': {}}

    # Universal checks
    results['checks']['exists'] = os.path.exists(file_path)
    results['checks']['non_empty'] = os.path.getsize(file_path) > 0

    # Format-specific checks
    if skill == 'docx':
        from docx import Document
        doc = Document(file_path)
        results['checks']['has_sections'] = len(doc.sections) > 0
        results['checks']['has_content'] = len(doc.paragraphs) > 0
        results['checks']['fonts_set'] = all(
            p.runs[0].font.name for p in doc.paragraphs if p.runs
        )
    elif skill == 'pptx':
        from pptx import Presentation
        prs = Presentation(file_path)
        results['checks']['widescreen'] = (
            prs.slide_width == 12192000 and prs.slide_height == 6858000
        )
        results['checks']['has_slides'] = len(prs.slides) > 0
    elif skill == 'pdf':
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            results['checks']['has_pages'] = len(pdf.pages) > 0
            results['checks']['has_text'] = any(
                page.extract_text() for page in pdf.pages
            )
    elif skill == 'xlsx':
        from openpyxl import load_workbook
        wb = load_workbook(file_path)
        results['checks']['has_sheets'] = len(wb.sheetnames) > 0
        results['checks']['has_data'] = any(
            ws.max_row > 1 for ws in wb.worksheets
        )
    elif skill == 'svg':
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        results['checks']['has_viewbox'] = 'viewBox' in content
        results['checks']['well_formed'] = content.strip().endswith('</svg>')
    elif skill == 'chart':
        results['checks']['size_reasonable'] = os.path.getsize(file_path) < 5_000_000

    # Score
    passed = sum(1 for v in results['checks'].values() if v)
    total = len(results['checks'])
    results['score'] = round(passed / total * 100) if total > 0 else 0

    return results
```

### 16.2 Manual Verification Checklist

For each generated output, manually verify:

- [ ] **Open the file** — Does it open without errors?
- [ ] **Scroll through** — Are all sections/pages/slides present?
- [ ] **Check formatting** — Are fonts, colors, and layout correct?
- [ ] **Verify data** — Are all numbers, dates, and facts accurate?
- [ ] **Test links** — Do hyperlinks and bookmarks work?
- [ ] **Print preview** — Does the layout hold up for printing?
- [ ] **Check file size** — Is it within budget?
- [ ] **Cross-platform test** — Open on another viewer if possible

---

## 17. Version History & Changelog

### 17.1 Changelog

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-07-01 | 2.0.0 | FRIDAY | Complete rewrite: 1000+ line master index with cross-reference matrix, agent mapping, unified design system, quality standards, troubleshooting guide, and changelog. Consolidated all 9 skill references. |
| 2026-06-15 | 1.5.0 | FRIDAY | Added code_gen skill (1873 lines). Added chart skill cross-reference. Updated design ramps. |
| 2026-06-01 | 1.4.0 | FRIDAY | Added metasploit skill (2260 lines). Updated OSINT skill to 2815 lines. Fixed color ramp consistency across docx/pptx/svg. |
| 2026-05-15 | 1.3.0 | FRIDAY | Added osint skill (first version, ~2000 lines). Updated pdf skill with reportlab patterns. |
| 2026-05-01 | 1.2.0 | FRIDAY | Added pptx skill (1099 lines). Unified color ramps across docx/svg/pptx. Added type scale table. |
| 2026-04-15 | 1.1.0 | FRIDAY | Added svg skill (1208 lines). Added xlsx skill (1310 lines). Added chart skill (first version). |
| 2026-04-01 | 1.0.0 | FRIDAY | Initial SKILLS.md (35 lines). Core skills: docx, pdf. Basic two-phase workflow. |

### 17.2 Version Schema

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes to skill contract, design system overhaul, or file reorganization
MINOR: New skills added, significant cross-referencing updates, new protocol documents
PATCH: Bug fixes, library version updates, minor pattern improvements, documentation fixes
```

### 17.3 Deprecation Policy

- Skills are deprecated with 2-version notice
- Deprecated skills remain available but flagged in the master index
- Replaced skills cross-reference their successor
- Breaking changes to the skill contract require MAJOR version bump

### 17.4 Future Roadmap

| Planned Skill | Description | Target Version |
|--------------|-------------|----------------|
| html | HTML document generation with CSS/JS | 2.1.0 |
| email | HTML email template generation with ESP integration | 2.2.0 |
| data_analysis | Automated data analysis with pandas/numpy | 2.3.0 |
| networking | Network automation (SSH, SCP, network device config) | 2.4.0 |
| ml_model | ML model training & deployment pipelines | 3.0.0 |

---

## 18. Appendix A: Quick-Reference Cards

### 18.1 Quick Reference: Which Skill for Which Task

| Task | Primary Skill | Dependencies |
|------|--------------|-------------|
| Write a business report | docx | chart (if data), svg (if diagrams) |
| Create a slide deck | pptx | chart, svg |
| Generate a PDF invoice | pdf | — |
| Export data to Excel | xlsx | — |
| Draw a flowchart | svg | — |
| Visualize quarterly data | chart | — |
| Build a web application | code_gen | — |
| Investigate a person/domain | osint | — |
| Test network security | metasploit | — |
| Create an infographic | svg | chart (for data elements) |
| Design a dashboard | code_gen | chart, svg |
| Write a research paper | docx | pdf (for final export) |
| Analyze breach data | osint | xlsx (for structured output) |
| Build a REST API | code_gen | — |
| Fill a PDF form | pdf | — |

### 18.2 Quick Reference: Library Commands

```python
# DOCX: Create and save
from docx import Document
doc = Document(); ... ; doc.save('output.docx')

# PPTX: Create and save
from pptx import Presentation
prs = Presentation(); ... ; prs.save('output.pptx')

# PDF: Create via factory
from tools_flat import create_pdf
create_pdf(sections=[...], output='output.pdf')

# XLSX: Create and save
from openpyxl import Workbook
wb = Workbook(); ... ; wb.save('output.xlsx')

# SVG: Direct generation string
svg_string = '<svg viewBox="0 0 680 400">...</svg>'

# Chart: Via factory
from tools_flat import _make_chart
result = _make_chart('bar', data, 'svg')

# Code: Follow Plan→Build workflow
# 1. Present plan 2. Get approval 3. Generate code 4. Test

# OSINT: Via bridge
from osint_extra import osint_full_scan
results = osint_full_scan(target, modules=['email', 'domain', 'social'])

# Metasploit: Via msfrpc
from msfrpc import MsfRpcClient
client = MsfRpcClient('msf'); ... ; client.call('console.create')
```

### 18.3 Quick Reference: Color Hex Values

Most commonly used colors:

```
Blue 400:  #378ADD  — Primary interactive, links, chart series
Blue 600:  #185FA5  — Hover state, darker accents
Blue 800:  #0C447C  — Title text on light, dark slide bg
Gray 50:   #F1EFE8  — Page background, alternating rows
Gray 200:  #B4B2A9  — Borders, dividers, disabled state
Gray 400:  #888780  — Secondary text, icons, captions
Gray 600:  #5F5E5A  — Body text on dark backgrounds
Gray 900:  #2C2C2A  — Body text (NOT pure black)
Green 400: #639922  — Success, positive metrics
Coral 400: #D85A30  — Warning, negative metrics
Purple 400:#7F77DD  — Category header, accent elements
Teal 400:  #1D9E75  — Secondary category, supporting data
White:     #FFFFFF  — Card backgrounds, text on dark
```

### 18.4 Quick Reference: File Format Specifications

| Format | Extension | MIME Type | Max Size | Primary Library |
|--------|-----------|-----------|----------|-----------------|
| Word | .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | 20 MB | python-docx |
| PowerPoint | .pptx | application/vnd.openxmlformats-officedocument.presentationml.presentation | 20 MB | python-pptx |
| PDF | .pdf | application/pdf | 20 MB | reportlab |
| Excel | .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | 15 MB | openpyxl |
| SVG | .svg | image/svg+xml | 100 KB | inline |
| Chart image | .png | image/png | 500 KB | matplotlib |
| CSV | .csv | text/csv | 10 MB | openpyxl/csv |

---

## 19. Appendix B: Environment & Dependency Checklist

### 19.1 Core Dependencies

```txt
# Required for all skills
python>=3.10

# DOCX Skill
python-docx>=1.1.0
Pillow>=10.0.0
matplotlib>=3.7.0
lxml>=4.9.0

# PPTX Skill
python-pptx>=0.6.23
Pillow>=10.0.0
matplotlib>=3.7.0
cairosvg>=2.7.0

# PDF Skill
reportlab>=4.0.0
fpdf2>=2.7.0
pdfplumber>=0.10.0
svglib>=1.5.0
cairosvg>=2.7.0
Pillow>=10.0.0
matplotlib>=3.7.0

# XLSX Skill
openpyxl>=3.1.0
Pillow>=10.0.0
matplotlib>=3.7.0

# SVG Skill
cairosvg>=2.7.0  # For PNG conversion

# Chart Skill
matplotlib>=3.7.0
plotly>=5.17.0
numpy>=1.24.0
pandas>=2.0.0
kaleido>=0.2.0  # For static plotly export

# Code Gen Skill
# Language-specific (varies by task)

# OSINT Skill
requests>=2.31.0
beautifulsoup4>=4.12.0
dnspython>=2.4.0
phonenumbers>=8.13.0
Pillow>=10.0.0

# Metasploit Skill
msfrpc>=1.1.0
```

### 19.2 Environment Variables

```bash
# Required for OSINT
export SHODAN_API_KEY="your_key"
export VIRUSTOTAL_API_KEY="your_key"
export HAVEIBEENPWNED_API_KEY="your_key"

# Required for Metasploit
export MSF_HOST="localhost"
export MSF_PORT=55553
export MSF_USER="msf"
export MSF_PASS="msf"

# Optional
export FRIDAY_LOG_LEVEL="INFO"     # DEBUG, INFO, WARNING, ERROR
export FRIDAY_MAX_FILE_SIZE_MB=50   # Max output file size
export FRIDAY_TEMP_DIR="./temp"     # Temporary file storage
```

### 19.3 Platform Notes

| Platform | Known Issues | Workarounds |
|----------|-------------|-------------|
| Windows | cairosvg requires GTK+ or librsvg | Install via `choco install rsvg` or use `svglib` alternative |
| Windows | python-pptx font fallback differs from Mac/Linux | Use SAFE_FONTS list exclusively |
| Linux | Missing fonts Calibri/Calibri Light | Install Microsoft fonts: `apt install ttf-mscorefonts-installer` |
| macOS | cairo rendering differences | Test PDFs on target platform |
| All | matplotlib Agg backend non-interactive | Set `matplotlib.use('Agg')` at import |

---

## 20. Appendix C: Error Code Reference

### 20.1 Skill Loading Errors

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| E001 | `Skill file not found: skills/<name>/SKILL.md` | Skill directory missing | Create skill file or use alternative |
| E002 | `Skill file has invalid frontmatter` | Missing `name` or `description` | Add valid YAML frontmatter |
| E003 | `Skill file empty or truncated` | File has no content | Regenerate skill file |
| E004 | `Skill trigger mismatch — no active triggers` | No triggers match request | Broaden trigger patterns or request manually |

### 20.2 Library Errors

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| L001 | `ModuleNotFoundError: <library>` | Library not installed | `pip install <library>` |
| L002 | `ImportError: <library> version <x> required` | Wrong version | Upgrade/downgrade library |
| L003 | `OSError: <library> binary not found` | System dependency missing | Install system package (GTK, cairo, etc.) |
| L004 | `MemoryError: <library> exceeded memory` | Too much data | Reduce data size, use streaming |

### 20.3 Document Assembly Errors

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| D001 | `Section type '<type>' not supported by <format>` | Invalid section type | Check section API docs for supported types |
| D002 | `Chart data invalid: mismatched series lengths` | Data shape mismatch | Ensure all series have same length as categories |
| D003 | `Image embedding failed: <path> not found` | Image path broken | Use absolute path or BytesIO |
| D004 | `Page size invalid: must be (width, height)` | Invalid dimensions | Use standard sizes from design system |
| D005 | `Font not found: <font_name>` | Font not installed | Use SAFE_FONTS list |
| D006 | `Document too large: <size> exceeds limit` | Size budget exceeded | Compress images, reduce content |

### 20.4 Quality Check Errors

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| Q001 | `Quality score below threshold: <score>%` | Too many checks fail | Fix individual check failures |
| Q002 | `Critical check: <check_name> failed` | Essential quality gate failed | Fix and re-run |
| Q003 | `Content validation: missing required sections` | Incomplete content | Add missing sections |
| Q004 | `Design validation: color rule violated` | Too many colors/ramps | Simplify color palette |

### 20.5 Chain Errors

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| C001 | `Chain dependency missing: <skill>` | Required skill not loaded | Load all skills in chain |
| C002 | `Data bridge failed: <from_skill> → <to_skill>` | Cross-skill data incompatible | Use standard bridge format (BytesIO, section API) |
| C003 | `Chain timeout: <duration> exceeded` | Task took too long | Break into subtasks |
| C004 | `Agent deadlock: circular dependency detected` | Skills reference each other | Break cycle with explicit data flow |

---

*End of Master Index — 1000+ lines covering the complete FRIDAY Skill System*

---

**Last Updated**: 2026-07-01
**Total Skills Indexed**: 9
**Total Lines in Master Index**: 1000+
**Aggregate Skill File Lines**: 14,000+
**Next Review Date**: 2026-08-01
