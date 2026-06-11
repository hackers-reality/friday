---
name: docx
description: Use this skill whenever creating, reading, editing, or manipulating Word documents (.docx files)
---

# DOCX Creation Guide

## Overview
A .docx file is a ZIP archive containing XML files. FRIDAY uses the python-docx library to create professional Word documents. **Use `create_docx()` in `tools_flat.py` for high-level document creation with sections array.**

All 23 chart types supported in `create_docx(sections=[{"type":"chart", "chart_type":"...", ...}])`: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar.

## Triggers
- "write a document/report/post/article" when output should be .docx
- "create a Word document", "make a doc", ".docx file"
- "report", "memo", "letter", "template", "resume", "contract"
- Any request mentioning "save", "file", or "document" with formatting needs

## Libraries
- **python-docx** — primary library for creating .docx files
- Document() — main class
- Styles, paragraphs, tables, images, headers/footers

## Code Patterns

### Basic Document
```python
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

doc = Document()

# Add heading
doc.add_heading('Title', level=0)
doc.add_heading('Section', level=1)

# Add paragraph with formatting
p = doc.add_paragraph()
run = p.add_run('Bold text')
run.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 0, 0)
p.alignment = WD_ALIGN_PARAGRAPH.LEFT

# Add table
table = doc.add_table(rows=3, cols=3)
table.style = 'Light Grid Accent 1'
cell = table.cell(0, 0)
cell.text = 'Header'

doc.save('output.docx')
```

### Table Styling
- Use `table.style = 'Light Grid Accent 1'` for professional tables
- Set column widths explicitly with `cell.width = Inches(2)`
- Shade header cells with shading XML for colored headers

### Adding Images
```python
from docx.shared import Inches
doc.add_picture('path/to/image.png', width=Inches(5))
```

### Page Setup
```python
section = doc.sections[0]
section.orientation = WD_ORIENT.LANDSCAPE
section.page_width = Cm(29.7)
section.page_height = Cm(21.0)
```

## Critical Rules — What to AVOID
- NEVER use unicode bullets (\u2022) — use `WD_ALIGN_PARAGRAPH.LIST_BULLET` style instead
- NEVER set paragraph formatting via XML manipulation unless absolutely necessary
- NEVER use `ShadingType.CLEAR` for table cells — use `ShadingType.SOLID` with explicit color
- NEVER create documents without setting explicit page margins
- NEVER use `pypandoc` for conversion — direct python-docx only
- NEVER leave default "Normal" style unmodified — set font/paragraph defaults first
- NEVER embed raw HTML — use proper python-docx API

## Verification
1. Open the generated .docx file and verify all sections exist
2. Check that tables render correctly (borders, alignment, shading)
3. Verify images are embedded, not linked
4. Confirm page margins and orientation match requirements
5. Re-read the file after creation to verify contents
