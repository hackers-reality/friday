---
name: svg
description: Use this skill when creating SVG diagrams, infographics, charts, flowcharts, or any visual illustration
---

# SVG Diagram & Infographic Creation Guide

## Overview
FRIDAY creates inline SVG diagrams as a primary visualization engine. SVG diagrams are resolution-independent, themable (light/dark), and can be embedded in any HTML/Markdown output.

## Triggers
- "diagram", "flowchart", "infographic", "illustration"
- "chart", "graph", "visualization", "architecture diagram"
- "show me how X works", "visualize this data"
- "make a diagram of", "create an infographic about"

## Libraries
- **Direct SVG string generation** — no external libraries needed
- SVG is XML — construct as a Python f-string or template
- Color ramps are defined below (matching Claude's system)

## Color Ramps (9 ramps, 7 stops each)

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

### Color Mapping Rules
- Color encodes MEANING, not sequence
- Purple, teal, coral, pink → general categories
- Blue, green, amber, red → semantic meaning (info, success, warning, error)
- Gray → neutral/structural elements
- Max 2 color ramps per diagram
- Text on colored backgrounds: use 800/900 stops from SAME ramp

### Light/Dark Mode
- **Light mode**: 50 fill + 600 stroke + 800 title
- **Dark mode**: 800 fill + 200 stroke + 100 title

## SVG Canvas Setup
```
viewBox="0 0 680 {HEIGHT}"  -- fixed 680px wide, flexible height
xmlns="http://www.w3.org/2000/svg"
```

### Font System
- `t` — sans-serif, 14px, primary text (#333 / #E0E0E0)
- `ts` — sans-serif, 12px, secondary text (#666 / #999)
- `th` — sans-serif, 14px, medium weight 500, headings

### Pre-built CSS Classes
```css
text.t { font-family: system-ui, sans-serif; font-size: 14px; fill: currentColor; }
text.ts { font-family: system-ui, sans-serif; font-size: 12px; fill: currentColor; }
text.th { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: currentColor; }
.box { fill: var(--fill, #F1EFE8); stroke: var(--stroke, #888780); stroke-width: 1.5; rx: 6; }
.node { cursor: pointer; }
.node:hover .box { stroke-width: 2.5; }
.arr { fill: none; stroke: #888780; stroke-width: 1.5; marker-end: url(#arrow); }
```

## Diagram Types

### Flowchart
```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10" fill="#888780"/>
    </marker>
  </defs>
  <!-- Step 1 -->
  <rect x="240" y="20" width="200" height="50" rx="25" class="box" fill="#E6F1FB" stroke="#378ADD"/>
  <text x="340" y="50" class="th" text-anchor="middle" fill="#0C447C">Step 1</text>
  <!-- Arrow -->
  <line x1="340" y1="70" x2="340" y2="110" class="arr"/>
  <!-- Step 2 -->
  <rect x="240" y="110" width="200" height="50" rx="6" class="box" fill="#EEEDFE" stroke="#7F77DD"/>
  <text x="340" y="140" class="th" text-anchor="middle" fill="#3C3489">Step 2</text>
</svg>
```

### Structural Diagram (containers inside containers)
```svg
<rect x="30" y="20" width="620" height="300" rx="10" class="box" fill="none" stroke="#D3D1C7" stroke-dasharray="6,3"/>
<text x="50" y="50" class="th" fill="#5F5E5A">Container</text>
<rect x="60" y="70" width="250" height="200" rx="8" class="box" fill="#E1F5EE" stroke="#1D9E75"/>
<text x="185" y="100" class="th" text-anchor="middle" fill="#0F6E56">Sub-Component A</text>
```

### Data Chart (SVG bar chart)
```svg
<g transform="translate(60, 30)">
  <!-- Y axis -->
  <line x1="40" y1="0" x2="40" y2="200" stroke="#888780"/>
  <!-- Bars -->
  <rect x="50" y="180" width="40" height="20" fill="#378ADD" rx="2"/>
  <text x="70" y="215" class="ts" text-anchor="middle">Q1</text>
  <rect x="110" y="140" width="40" height="60" fill="#1D9E75" rx="2"/>
  <text x="130" y="215" class="ts" text-anchor="middle">Q2</text>
  <rect x="170" y="100" width="40" height="100" fill="#D85A30" rx="2"/>
  <text x="190" y="215" class="ts" text-anchor="middle">Q3</text>
</g>
```

## Critical Rules — What to AVOID
- NEVER use more than 2 color ramps per diagram
- NEVER exceed 4 boxes per row
- NEVER use subtitles longer than 5 words
- NEVER use font sizes smaller than 12px (ts) or 14px (t/th)
- NEVER use rainbow cycling for data — use semantic color mapping
- NEVER overlap text elements — always check positioning
- NEVER create SVG without proper viewBox (causes scaling issues)
- NEVER omit stroke-width on lines/arrows
- NEVER use black (#000) or pure white (#FFF) for text — use ramp-appropriate colors

## Verification
1. Render the SVG in a browser and check positioning
2. Verify all text is readable (contrast, size)
3. Check arrows/diagram flow direction
4. Confirm light/dark mode color contrast
5. Verify viewBox aspect ratio is correct
