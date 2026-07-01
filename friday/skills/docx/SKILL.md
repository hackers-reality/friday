---
name: docx
description: Use this skill whenever creating, reading, editing, or manipulating Word documents (.docx files)
---

# Skill: DOCX — Professional Word Document Design

## Overview
FRIDAY uses python-docx to create production-grade Word documents. **Use `create_docx()` in `tools_flat.py` for high-level document creation.** For custom layouts, advanced table styling, or template-based documents, use python-docx directly.

Every document should look like it came from a professional studio — consistent typography, clean layout, proper margins, and visual hierarchy. Documents default to A4 with 2.54cm margins.

## QUALITY CRITICAL — READ BEFORE WRITING CODE

YOU ARE A DOCUMENT DESIGNER. Build every Word document as if it will be printed or submitted professionally. Consistent typography, proper hierarchy, and visual breaks between sections are non-negotiable.

### EXACT PAGE BLUEPRINT (4 pages minimum)

Every DOCX MUST have 4+ pages with this EXACT structure:

**Cover Page**: Section break (next page). No header/footer on cover. Colored rectangle shape at top (full width, 2cm tall, #0C447C bg). Title 26pt bold #0C447C centered, 6cm from top. Horizontal rule 2pt #378ADD, 8cm wide centered. Subtitle 16pt #185FA5 centered, 1cm below rule. Date 12pt #888780 centered. "Prepared by FRIDAY AI" 11pt #888780 centered. Page break after.

**Page 2 - Executive Summary**: Header "EXECUTIVE SUMMARY" 18pt bold #0C447C (Heading 1 style). Body text 11pt justified #333333, line spacing 1.15. Key metrics highlighted with bold runs within paragraph. 2-3 paragraphs of content. Footer: page number centered, document title left-aligned.

**Page 3 - Data Analysis**: Header "DATA ANALYSIS" 18pt bold #0C447C (Heading 1). Subheading "Product Comparison" 14pt bold #185FA5 (Heading 2). Styled table: header row with bg #378ADD, white text bold 10pt, center aligned. Data rows 10pt #333333, alternating bg (#F1EFE8 / #FFFFFF). Cell padding 0.2cm. Column widths proportional. Heading 2 "Key Findings" with bullet list (11pt #333333, hanging indent 0.5cm). Embedded matplotlib chart: bar chart of prices, saved as PNG, inserted with width 14cm, centered. Chart caption 9pt italic #888780 below.

**Page 4 - Recommendations**: Header "RECOMMENDATIONS" 18pt bold #0C447C. Numbered list of 3-5 recommendations (11pt #333333, bold lead-in). Body paragraph below each. Horizontal rule before concluding paragraph. Final text 11pt italic #5F5E5A.

### TYPE SCALE (explicit — never default)
- Document title: 26pt bold
- Heading 1: 18pt bold
- Heading 2: 14pt semibold
- Heading 3: 12pt bold
- Body text: 11pt regular, justified
- Table header: 10pt bold
- Table data: 10pt regular
- Caption: 9pt italic
- Header/footer: 9pt regular

### COLOR SYSTEM (pick ONE)
- **Professional Blue**: H1 #0C447C, H2 #185FA5, table header #378ADD, body #333333, light bg #F1EFE8
- **Corporate Green**: H1 #1D9E75, H2 #0F6E56, table header #639922, body #333333, light bg #E1F5EE
- **Modern Purple**: H1 #3C3489, H2 #534AB7, table header #7F77DD, body #333333, light bg #EEEDFE

### EVERY PAGE MUST HAVE
- A4 paper, 2.54cm margins
- Header with document title on every content page
- Footer with page number on every content page
- Explicit font sizes on every run (never default)
- Proper heading hierarchy (H1 → H2 → H3, never skip levels)

### ANTI-PATTERNS — OUTPUTS THAT GET REJECTED
- Single table with no surrounding explanation or formatting
- No cover page or section breaks
- All text in default font/size with no hierarchy
- No images, charts, or visual breaks
- Tables without colored header rows or alternating colors
- Missing page numbers or headers
- Less than 3 content pages
- Default paragraph spacing (0 before, 0 after) — always set explicitly
- No color applied to headings or accents

## Triggers
- "write a report", "create a document", "memo", "letter", "resume", "contract"
- "save as Word doc", ".docx file", "Word document"
- "invoice", "proposal", "whitepaper", "case study", "cover letter"

## Libraries
- **python-docx** — primary library for creating and manipulating .docx files
- **Pillow (PIL)** — image preprocessing before embedding
- **matplotlib** — chart generation as images for embedding
- **lxml** — XML-level manipulation for advanced features

## Design System

### Page Setup
**Default: A4** with 2.54cm (1") margins on all sides.

| Size | Width × Height | Usage |
|------|---------------|-------|
| A4 | 21.0cm × 29.7cm | Default — reports, letters, proposals |
| Letter | 21.59cm × 27.94cm | US standard |
| A5 | 14.8cm × 21.0cm | Brochures, flyers |
| Legal | 21.59cm × 35.56cm | Contracts, legal documents |
| Executive | 18.41cm × 26.67cm | Memos, internal docs |

### Type Scale
| Role | Size | Weight | Alignment |
|------|------|--------|-----------|
| Document Title | 26pt | Bold | Center |
| Heading 1 | 18pt | Bold | Left |
| Heading 2 | 16pt | SemiBold | Left |
| Heading 3 | 14pt | Bold | Left |
| Heading 4 | 12pt | Bold | Left |
| Body text | 11pt | Regular | Justified |
| Caption / small | 9pt | Regular, Italic | Center |
| Table header | 10pt | Bold | Center |
| Table body | 10pt | Regular | Left |
| Footer / header | 9pt | Regular | Center/Right |
| Bullet text | 11pt | Regular | Left |
| Figure label | 10pt | Bold, Italic | Center |

### Color Palette
| Role | Hex | RGB | Usage |
|------|-----|-----|-------|
| Title | #0C447C | (12, 68, 124) | Document title |
| Heading 1 | #185FA5 | (24, 95, 165) | Section headings |
| Heading 2 | #3C3489 | (60, 52, 137) | Sub-section headings |
| Heading 3 | #1D9E75 | (29, 158, 117) | Tertiary headings |
| Body text | #333333 | (51, 51, 51) | All body content |
| Muted text | #888780 | (136, 135, 128) | Captions, metadata |
| Header bg | #378ADD | (55, 138, 221) | Table headers |
| Header text | #FFFFFF | (255, 255, 255) | Table header text |
| Link | #185FA5 | (24, 95, 165) | Hyperlinks |
| Border | #B4B2A9 | (180, 178, 169) | Table borders, rules |
| Accent | #534AB7 | (83, 74, 183) | Accent elements |
| Light bg | #F1EFE8 | (241, 239, 232) | Alternating rows |

### Font Defaults
```python
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
font.color.rgb = RGBColor(0x33, 0x33, 0x33)
paragraph_format = style.paragraph_format
paragraph_format.space_after = Pt(6)
paragraph_format.line_spacing = 1.15
```

## Comprehensive python-docx API Reference

### Core Imports
```python
from docx import Document
from docx.shared import Inches, Pt, Cm, Mm, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml, OxmlElement
from docx.table import Table, _Cell, _Row, _Column
from docx.section import Section
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.opc.constants import RELATIONSHIP_TYPE as RT
```

### Document Setup
```python
doc = Document()

# Page setup (A4 with 2.54cm margins)
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.54)
section.bottom_margin = Cm(2.54)
section.left_margin = Cm(2.54)
section.right_margin = Cm(2.54)

# Style defaults
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)
style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.15

# Heading styles
for level, (size, color_hex) in {1: (18, '185FA5'), 2: (16, '3C3489'),
                                  3: (14, '1D9E75'), 4: (12, '333333')}.items():
    style = doc.styles[f'Heading {level}']
    style.font.name = 'Calibri Light'
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = hex_to_rgb(color_hex)
    style.paragraph_format.space_before = Pt(18 if level == 1 else 12)
    style.paragraph_format.space_after = Pt(6)
```

## Section Management

### Multiple Sections with Different Page Setups
```python
# Add a new section
new_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
# Or: WD_SECTION_START.CONTINUOUS (no page break)
# Or: WD_SECTION_START.ODD_PAGE / EVEN_PAGE (for booklets)

# Configure the new section
new_section.page_width = Cm(21.0)
new_section.page_height = Cm(29.7)
new_section.top_margin = Cm(2.54)
new_section.bottom_margin = Cm(2.54)
new_section.left_margin = Cm(2.54)
new_section.right_margin = Cm(2.54)
new_section.different_first_page_header_footer = True
new_section.orientation = WD_ORIENT.PORTRAIT

# Landscape section
landscape_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
landscape_section.orientation = WD_ORIENT.LANDSCAPE
landscape_section.page_width = Cm(29.7)
landscape_section.page_height = Cm(21.0)
```

### Section Properties
```python
section = doc.sections[0]
section.orientation = WD_ORIENT.PORTRAIT  # or LANDSCAPE

# Gutter margin (for binding)
section.gutter = Cm(1.0)

# Header distance from top
section.header_distance = Cm(1.5)

# Footer distance from bottom
section.footer_distance = Cm(1.5)

# Columns in section (newspaper-style)
# Requires XML manipulation
cols = parse_xml(f'<w:cols {nsdecls("w")} num="2" space="720"/>')
section._sectPr.append(cols)
```

## Paragraph Styling

### Alignment and Spacing
```python
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # LEFT, CENTER, RIGHT, JUSTIFY, DISTRIBUTE
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)
p.paragraph_format.line_spacing = 1.5  # or Pt(18) for exact spacing
p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE  # SINGLE, DOUBLE, EXACTLY, AT_LEAST
p.paragraph_format.first_line_indent = Cm(0.5)  # Paragraph indent
p.paragraph_format.left_indent = Cm(1.0)  # Left margin indent
p.paragraph_format.right_indent = Cm(0.5)  # Right margin indent

# Widow/orphan control
p.paragraph_format.widow_control = True

# Keep with next (prevent page break between this and next paragraph)
p.paragraph_format.keep_with_next = True

# Page break before
p.paragraph_format.page_break_before = True
```

### Paragraph Borders
```python
def set_paragraph_border(p, top=False, bottom=False, left=False, right=False,
                         color="B4B2A9", size=4):
    """Add borders to a paragraph. Size in eighths of a point."""
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    border_map = {'top': top, 'bottom': bottom, 'left': left, 'right': right}
    for side, enabled in border_map.items():
        if enabled:
            border = OxmlElement(f'w:{side}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), str(size))
            border.set(qn('w:space'), '1')
            border.set(qn('w:color'), color)
            pBdr.append(border)
    pPr.append(pBdr)

# Example: bottom border under heading
set_paragraph_border(doc.add_heading('Section Title', level=1),
                     bottom=True, color='378ADD', size=8)
```

### Paragraph Shading
```python
def set_paragraph_shading(p, color="E6F1FB"):
    pPr = p._element.get_or_add_pPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>')
    pPr.append(shd)

# Example: highlighted paragraph
p = doc.add_paragraph('This is a highlighted paragraph.')
set_paragraph_shading(p, 'E6F1FB')
```

### Tabs
```python
# Set tab stops on paragraph
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
pPr = p._element.get_or_add_pPr()
tabs = OxmlElement('w:tabs')
for pos, align, leader in [(Cm(2), 'left', 'none'), (Cm(10), 'right', 'dot')]:
    tab = OxmlElement('w:tab')
    tab.set(qn('w:val'), align)
    tab.set(qn('w:pos'), str(int(pos)))
    tab.set(qn('w:leader'), leader)
    tabs.append(tab)
pPr.append(tabs)
```

## Run Formatting

### Text Formatting
```python
run = p.add_run('Formatted text')

# Basic formatting
run.bold = True
run.italic = True
run.underline = True  # Use sparingly — confuses with hyperlinks
run.strike = True  # Strikethrough
run.double_strike = True  # Double strikethrough

# Font properties
run.font.name = 'Calibri'
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
run.font.color.theme_color = None  # Reset theme color to explicit

# Font features
run.font.superscript = True  # For footnotes, exponents
run.font.subscript = True     # For chemical formulas
run.font.small_caps = True    # Small caps
run.font.all_caps = True      # All caps (use VERY sparingly)
run.font.highlight_color = WD_COLOR_INDEX.YELLOW  # Highlight (text marker)

# Character spacing
# Requires XML manipulation
rPr = run._r.get_or_add_rPr()
spacing = OxmlElement('w:spacing')
spacing.set(qn('w:val'), '200')  # 200 = 2pt expanded
spacing.set(qn('w:kerning'), '1')  # Kerning at 1pt
rPr.append(spacing)

# Complex script (for non-Latin text)
# run.font.complex_script = True
# rFonts = rPr.find(qn('w:rFonts'))
# if rFonts is None:
#     rFonts = OxmlElement('w:rFonts')
#     rPr.insert(0, rFonts)
# rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
```

### Run Effects
```python
# Outline text
def set_text_outline(run, color="378ADD", width="400"):
    """Add text outline/contour effect."""
    rPr = run._r.get_or_add_rPr()
    outline = parse_xml(f'''
        <w:effectPr {nsdecls("w")}>
            <w:outlineLn w:val="single" w:sz="{width}" w:color="{color}"/>
        </w:effectPr>
    ''')
    rPr.append(outline)
```

### Field Codes (Dynamic Content)
```python
def add_field(run, field_code):
    """Add a Word field code (page number, date, etc.)"""
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    run._r.append(fld_begin)

    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = field_code
    run._r.append(instr)

    fld_separate = OxmlElement('w:fldChar')
    fld_separate.set(qn('w:fldCharType'), 'separate')
    run._r.append(fld_separate)

    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_end)

# Usage: add page number field
# add_field(run, ' PAGE ')
```

## Document Structure & Content

### Title Page
```python
# Empty paragraph for vertical spacing
for _ in range(6):
    doc.add_paragraph()

# Title
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Document Title')
run.font.size = Pt(26)
run.font.bold = True
run.font.name = 'Calibri Light'
run.font.color.rgb = RGBColor(0x0C, 0x44, 0x7C)

doc.add_paragraph()  # spacer

# Subtitle
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Subtitle or description')
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
run.font.name = 'Calibri Light'

doc.add_paragraph()  # spacer

# Meta information
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for part in [('June 2026', 0x5F5E5A), (' | ', 0x888780), ('Prepared by FRIDAY', 0x5F5E5A)]:
    run = p.add_run(part[0])
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(*[int(f'0x{v}{v}', 16) if isinstance(v, str) else 0 for v in [part[1]]])
    # Simpler:
    run.font.color.rgb = RGBColor(
        (part[1] >> 16) & 0xFF, (part[1] >> 8) & 0xFF, part[1] & 0xFF
    )

doc.add_page_break()
```

### Body Text with Headings
```python
doc.add_heading('1. Introduction', level=1)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.first_line_indent = Cm(0.5)
run = p.add_run('This is the first body paragraph. It uses justified alignment with a first-line indent for a professional book-style appearance. The font is 11pt Calibri with 1.15 line spacing for optimal readability.')
run.font.size = Pt(11)

doc.add_heading('1.1 Background', level=2)
p = doc.add_paragraph('More body text here.')

doc.add_heading('Detailed Analysis', level=3)
p = doc.add_paragraph('Level 3 heading content.')
```

### Bullet and Numbered Lists
```python
# Bullet list
items = ['First item with detailed explanation',
         'Second item with supporting data',
         'Third item with key insight']
for item in items:
    p = doc.add_paragraph(item, style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Cm(1.0)
    p.paragraph_format.first_line_indent = Cm(-0.5)

# Numbered list
items = ['Step one: prepare the environment',
         'Step two: configure the settings',
         'Step three: run the analysis']
for item in items:
    p = doc.add_paragraph(item, style='List Number')
    p.paragraph_format.space_after = Pt(3)

# Multi-level list (requires XML manipulation)
# python-docx doesn't directly support multi-level lists.
# Workaround: use custom indentation
p = doc.add_paragraph('Main point', style='List Bullet')
p.paragraph_format.left_indent = Cm(1.0)
p_sub = doc.add_paragraph('Sub-point', style='List Bullet')
p_sub.paragraph_format.left_indent = Cm(2.0)
p_sub.paragraph_format.first_line_indent = Cm(-0.5)
```

### Page Breaks and Section Breaks
```python
# Simple page break
doc.add_page_break()

# Section break (new page)
doc.add_section(WD_SECTION_START.NEW_PAGE)

# Section break (continuous — same page)
doc.add_section(WD_SECTION_START.CONTINUOUS)

# Section break (odd page — for book chapter starts)
doc.add_section(WD_SECTION_START.ODD_PAGE)

# Column break (requires XML)
def add_column_break(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    br = OxmlElement('w:br')
    br.set(qn('w:type'), 'column')
    run._r.append(br)
    return p
```

## Table Design

### Creating and Styling Tables
```python
# Create table
table = doc.add_table(rows=6, cols=4)
table.style = 'Table Grid'  # Start with base grid style
table.alignment = WD_TABLE_ALIGNMENT.CENTER  # CENTER, LEFT, RIGHT

# Auto-fit behavior
table.autofit = True  # Allow columns to auto-fit content

# Column widths
col_widths = [Cm(4), Cm(4), Cm(4), Cm(4)]
for i, width in enumerate(col_widths):
    table.columns[i].width = width

# Header row
headers = ['Metric', 'Q1', 'Q2', 'Q3']
for i, header in enumerate(headers):
    cell = table.cell(0, i)
    cell.text = header
    # Header shading
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="378ADD" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)
    # Header text formatting
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            run.font.size = Pt(10)
            run.font.name = 'Calibri'
    # Vertical alignment
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

# Data rows
data = [
    ['Revenue', '$100K', '$200K', '$300K'],
    ['Cost', '$60K', '$120K', '$180K'],
    ['Profit', '$40K', '$80K', '$120K'],
    ['Margin', '40%', '40%', '40%'],
    ['Growth', '—', '+100%', '+50%'],
]
for row_idx, row_data in enumerate(data):
    for col_idx, value in enumerate(row_data):
        cell = table.cell(row_idx + 1, col_idx)
        cell.text = value
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            for run in paragraph.runs:
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
                run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    # Alternating row colors
    if row_idx % 2 == 1:
        for col_idx in range(len(row_data)):
            cell = table.cell(row_idx + 1, col_idx)
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1EFE8" w:val="clear"/>')
            cell._tc.get_or_add_tcPr().append(shading)
```

### Advanced Table Features

#### Merge Cells
```python
# Horizontal merge
table.cell(0, 0).merge(table.cell(0, 3))  # Merge header row into one cell

# Vertical merge
table.cell(1, 0).merge(table.cell(3, 0))  # Merge cells in first column

# Set text on merged cell
merged_cell = table.cell(0, 0)
merged_cell.text = 'Consolidated Header'
```

#### Cell Borders
```python
def set_cell_border(cell, **kwargs):
    """Set cell borders. kwargs: top, bottom, left, right with (size, color) tuples."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge, (size, color) in kwargs.items():
        element = OxmlElement(f'w:{edge}')
        element.set(qn('w:val'), 'single')
        element.set(qn('w:sz'), str(size))
        element.set(qn('w:space'), '0')
        element.set(qn('w:color'), color)
        tcBorders.append(element)
    tcPr.append(tcBorders)

# Example: thick bottom border on header cells
for i in range(len(headers)):
    set_cell_border(table.cell(0, i), bottom=(12, '185FA5'))
```

#### Row Height
```python
# Set exact row height
table.rows[0].height = Cm(1.0)

# Minimum row height
table.rows[0].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
table.rows[0].height = Cm(0.8)
```

#### Header Row Repeat
```python
# Repeat header row on each page
from docx.oxml import OxmlElement
tblPr = table._tbl.find(qn('w:tblPr'))
if tblPr is None:
    tblPr = OxmlElement('w:tblPr')
    table._tbl.insert(0, tblPr)

tblHeader = OxmlElement('w:tblHeader')
tblHeader.set(qn('w:val'), 'true')
tblPr.append(tblHeader)
```

#### Cell Width
```python
# Set individual cell widths
for row in table.rows:
    row.cells[0].width = Cm(3)
    row.cells[1].width = Cm(5)
    row.cells[2].width = Cm(4)
```

## Images

### Inline Images
```python
# Add image at native size
doc.add_picture('chart.png')

# Add image with specific width (height auto-proportioned)
doc.add_picture('chart.png', width=Inches(5.5))

# Add image with specific dimensions
from docx.shared import Inches
doc.add_picture('chart.png', width=Inches(5.5), height=Inches(3.5))

# Center the image
last_paragraph = doc.paragraphs[-1]
last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

### Wrapped Images (Floating)
```python
# python-docx doesn't support floating images directly.
# Workaround: use inline images with runs
p = doc.add_paragraph()
run = p.add_run()
run.add_picture('logo.png', width=Cm(3))
# This creates inline image within paragraph

# For floating images, use XML manipulation:
def add_floating_image(doc, image_path, left=Cm(1), top=Cm(1), width=Cm(5), height=Cm(3)):
    """Add a floating image using XML manipulation."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    rel_type = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
    image_part = doc.part.get_or_add_image_part(image_path)
    rId = doc.part.relate_to(image_part, rel_type)

    # Create drawing XML
    drawing_xml = f'''
        <w:drawing xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                    xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                    xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
                    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <wp:anchor relativeHeight="0" behindDoc="0" locked="0" layoutInCell="1"
                       allowOverlap="1" simplePos="0" wrapNone="1">
                <wp:simplePos x="0" y="0"/>
                <wp:positionH relativeFrom="page">
                    <wp:posOffset>{int(left)}</wp:posOffset>
                </wp:positionH>
                <wp:positionV relativeFrom="page">
                    <wp:posOffset>{int(top)}</wp:posOffset>
                </wp:positionV>
                <wp:extent cx="{int(width)}" cy="{int(height)}"/>
                <wp:effectExtent l="0" t="0" r="0" b="0"/>
                <wp:wrapNone/>
                <wp:docPr id="1" name="Floating Image"/>
                <wp:cNxGraphicPr>
                    <a:graphicFrameLocks noChangeAspect="1"/>
                </wp:cNxGraphicPr>
                <a:graphic>
                    <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                        <pic:pic>
                            <pic:nvPicPr>
                                <pic:cNvPr id="0" name="Image"/>
                                <pic:cNvPicPr/>
                            </pic:nvPicPr>
                            <pic:blipFill>
                                <a:blip r:embed="{rId}"/>
                                <a:srcRect/>
                                <a:stretch>
                                    <a:fillRect/>
                                </a:stretch>
                            </pic:blipFill>
                            <pic:spPr>
                                <a:xfrm>
                                    <a:off x="0" y="0"/>
                                    <a:ext cx="{int(width)}" cy="{int(height)}"/>
                                </a:xfrm>
                                <a:prstGeom prst="rect">
                                    <a:avLst/>
                                </a:prstGeom>
                            </pic:spPr>
                        </pic:pic>
                    </a:graphicData>
                </a:graphic>
            </wp:anchor>
        </w:drawing>
    '''
    # Add to paragraph
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run._r.append(parse_xml(drawing_xml))
    return p
```

### Image with Caption
```python
# Add image
doc.add_picture('figure.png', width=Inches(5.0))
last_paragraph = doc.paragraphs[-1]
last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

# Add caption below
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(4)
p.paragraph_format.space_after = Pt(12)
run = p.add_run('Figure 1: Description of the figure')
run.font.size = Pt(9)
run.font.italic = True
run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
run.font.name = 'Calibri'
```

## Headers and Footers

### Basic Header/Footer
```python
section = doc.sections[0]

# Header
header = section.header
header.is_linked_to_previous = False  # Detach from previous section's header
p = header.paragraphs[0]
p.text = 'Document Title'
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
for run in p.runs:
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
    run.font.name = 'Calibri'

# Footer
footer = section.footer
footer.is_linked_to_previous = False
p = footer.paragraphs[0]
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Page ')
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
# Page number field
add_field(run, ' PAGE ')
run = p.add_run(' of ')
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
add_field(run, ' NUMPAGES ')
```

### Different First Page
```python
section.different_first_page_header_footer = True

# First page header (often empty)
first_header = section.first_page_header
first_header.is_linked_to_previous = False
# Leave empty for professional look

# First page footer
first_footer = section.first_page_footer
first_footer.is_linked_to_previous = False
```

### Odd/Even Page Headers
```python
section.different_first_page_header_footer = True
# Even page header
even_header = section.even_page_header
even_header.is_linked_to_previous = False
p = even_header.paragraphs[0]
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
p.text = 'Document Title (even)'
```

## Table of Contents

### TOC Field
```python
def add_table_of_contents(doc):
    """Add a TOC field to the document."""
    p = doc.add_paragraph()
    run = p.add_run()
    # TOC field
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    run._r.append(fld_begin)
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    run._r.append(instr)
    fld_separate = OxmlElement('w:fldChar')
    fld_separate.set(qn('w:fldCharType'), 'separate')
    run._r.append(fld_separate)
    # Default text (will be replaced by Word on update)
    run = p.add_run('[Table of Contents — update in Word]')
    run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
    run.font.size = Pt(11)
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_end)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

# Usage
doc.add_heading('Table of Contents', level=1)
add_table_of_contents(doc)
doc.add_page_break()
```

### Manual TOC
```python
def add_manual_toc(doc, entries):
    """Add a manual TOC with entries as (title, page) tuples."""
    doc.add_heading('Table of Contents', level=1)
    for title, page in entries:
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(15), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        run = p.add_run(title)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        run = p.add_run('\t')
        run = p.add_run(str(page))
        run.font.size = Pt(11)
        p.paragraph_format.space_after = Pt(2)
```

## Hyperlinks and Bookmarks

### Hyperlinks
```python
def add_hyperlink(paragraph, text, url):
    """Add a clickable hyperlink to a paragraph."""
    part = paragraph.part
    rId = part.relate_to(url, RT.HYPERLINK, is_external=True)

    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), rId)

    run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    # Style as link
    rStyle = OxmlElement('w:rStyle')
    rStyle.set(qn('w:val'), 'Hyperlink')
    rPr.append(rStyle)
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '185FA5')
    rPr.append(color)
    underline = OxmlElement('w:u')
    underline.set(qn('w:val'), 'single')
    rPr.append(underline)
    run.append(rPr)

    text_elem = OxmlElement('w:t')
    text_elem.text = text
    text_elem.set(qn('xml:space'), 'preserve')
    run.append(text_elem)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink

# Usage
p = doc.add_paragraph('Visit our ')
add_hyperlink(p, 'website', 'https://example.com')
p.add_run(' for more information.')
```

### Bookmarks
```python
def add_bookmark(paragraph, bookmark_name):
    """Add a bookmark target to a paragraph."""
    run = paragraph.add_run()
    bookmark_start = OxmlElement('w:bookmarkStart')
    bookmark_start.set(qn('w:id'), str(hash(bookmark_name) % 100000))
    bookmark_start.set(qn('w:name'), bookmark_name)
    run._r.append(bookmark_start)

    bookmark_end = OxmlElement('w:bookmarkEnd')
    bookmark_end.set(qn('w:id'), str(hash(bookmark_name) % 100000))
    run._r.append(bookmark_end)

# Usage
p = doc.add_heading('Important Section', level=2)
add_bookmark(p, 'Section_Important')
# Later: create link to bookmark
# add_hyperlink(p, 'jump to section', '#Section_Important')
```

### Internal Cross-Reference
```python
def add_cross_reference(paragraph, bookmark_name, text):
    """Add a cross-reference to a bookmark."""
    # Requires field code
    run = paragraph.add_run()
    add_field(run, f' REF {bookmark_name} \\h ')
    # Text after is display fallback
    run2 = paragraph.add_run(f' ({text})')
    run2.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
    run2.font.size = Pt(9)
```

## Equations

### Simple Equation via Unicode
```python
# Use Unicode math symbols for basic equations
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('E = mc²')
run.font.size = Pt(12)
run.font.italic = True
```

### OMML Equations (Professional Math)
```python
# OMML (Office Math Markup Language) requires XML manipulation
def add_equation(doc, latex_equivalent=None):
    """Add an empty equation placeholder.
    Full OMML generation is complex; use this for placeholder."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Create OMML paragraph
    pPr = p._element.get_or_add_pPr()
    pPr.set(qn('w:jc'), 'center')

    # Add math paragraph
    math_para = parse_xml(f'''
        <m:oMathPara {nsdecls("m")} {nsdecls("w")}>
            <m:oMath>
                <m:r>
                    <m:t>Equation placeholder — edit in Word</m:t>
                </m:r>
            </m:oMath>
        </m:oMathPara>
    ''')
    p._element.append(math_para)
    return p
```

## Watermarks

### Text Watermark
```python
def add_watermark(doc, text="DRAFT"):
    """Add a text watermark to every page."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import nsdecls, qn

    # Create watermark in header (appears on every page)
    for section in doc.sections:
        header = section.header
        header.is_linked_to_previous = False

        # Create watermark paragraph
        p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        pPr = p._element.get_or_add_pPr()

        # Make sure watermark is behind text
        run = p.add_run()
        rPr = run._r.get_or_add_rPr()

        # Create picture (or text box) watermark
        # Simple approach: use large rotated text
        drawing = parse_xml(f'''
            <w:r {nsdecls("w")}>
                <w:rPr>
                    <w:color w:val="C0C0C0"/>
                    <w:sz w:val="720"/> <!-- 36pt -->
                </w:rPr>
                <w:drawing>
                    <wp:anchor xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                               relativeHeight="-251658240" behindDoc="1" locked="1"
                               layoutInCell="1" allowOverlap="1" simplePos="0"
                               wrapNone="1" distT="0" distB="0" distL="0" distR="0">
                        <wp:simplePos x="0" y="0"/>
                        <wp:positionH relativeFrom="page">
                            <wp:posOffset>0</wp:posOffset>
                        </wp:positionH>
                        <wp:positionV relativeFrom="page">
                            <wp:posOffset>0</wp:posOffset>
                        </wp:positionV>
                        <wp:extent cx="9144000" cy="9144000"/>
                        <wp:effectExtent l="0" t="0" r="0" b="0"/>
                        <wp:wrapNone/>
                        <wp:docPr id="1" name="Watermark"/>
                        <wp:cNxGraphicPr>
                            <a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
                        </wp:cNxGraphicPr>
                        <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
                                <wow:wordprocessingDrawing xmlns:wow="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
                                    <wow:shape id="0" style="position:absolute;left:0;top:0;width:100%;height:100%;mso-wrap-style:tight;mso-position-horizontal:absolute;mso-position-vertical:absolute;rotation:-45deg;">
                                        <v:textbox xmlns:v="urn:schemas-microsoft-com:vml" inset="0,0,0,0">
                                            <w:txbxContent>
                                                <w:p>
                                                    <w:r>
                                                        <w:rPr>
                                                            <w:color w:val="C0C0C0"/>
                                                            <w:sz w:val="720"/>
                                                            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                                                        </w:rPr>
                                                        <w:t>{text}</w:t>
                                                    </w:r>
                                                </w:p>
                                            </w:txbxContent>
                                        </v:textbox>
                                    </wow:shape>
                                </wow:wordprocessingDrawing>
                            </a:graphicData>
                        </a:graphic>
                    </wp:anchor>
                </w:drawing>
            </w:r>
        ''')
        p._element.append(drawing)
```

## Document Protection

### Read-Only Protection
```python
def protect_document(doc, password="", edit_restriction="readOnly"):
    """
    Add document protection.
    edit_restriction: "readOnly", "comments", "trackedChanges", "forms", "noProtection"
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    # Create documentProtection element
    dp = OxmlElement('w:documentProtection')
    dp.set(qn('w:edit'), edit_restriction)
    dp.set(qn('w:enforcement'), 'true')
    if password:
        # Simple XOR hash (not cryptographically secure, but Word compatible)
        hash_value = 0
        for i, char in enumerate(password):
            hash_value ^= (ord(char) << (i % 4))
        dp.set(qn('w:cryptProviderType'), 'rsaAES')
        dp.set(qn('w:cryptAlgorithmSid'), '14')  # SHA-512
        # Hash calculation is complex; leave empty for no password
        pass

    # Append to settings
    settings = doc.settings.element
    existing = settings.find(qn('w:documentProtection'))
    if existing is not None:
        settings.remove(existing)
    settings.append(dp)
```

## Styles and Templates

### Create Custom Styles
```python
from docx.enum.style import WD_STYLE_TYPE

def create_custom_style(doc, name, base_style='Normal',
                        font_name='Calibri', font_size=Pt(11),
                        bold=False, color_hex='333333',
                        alignment=WD_ALIGN_PARAGRAPH.LEFT,
                        space_before=Pt(0), space_after=Pt(6)):
    """Create or modify a custom paragraph style."""
    style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles[base_style]
    style.font.name = font_name
    style.font.size = font_size
    style.font.bold = bold
    style.font.color.rgb = hex_to_rgb(color_hex)
    style.paragraph_format.alignment = alignment
    style.paragraph_format.space_before = space_before
    style.paragraph_format.space_after = space_after
    return style

# Usage
title_style = create_custom_style(doc, 'CustomTitle', 'Normal',
                                  font_size=Pt(26), bold=True, color_hex='0C447C',
                                  alignment=WD_ALIGN_PARAGRAPH.CENTER)
p = doc.add_paragraph('Custom Styled Text', style='CustomTitle')
```

### Character Styles
```python
char_style = doc.styles.add_style('HighlightText', WD_STYLE_TYPE.CHARACTER)
char_style.font.name = 'Calibri'
char_style.font.bold = True
char_style.font.size = Pt(11)
char_style.font.color.rgb = RGBColor(0xD8, 0x5A, 0x30)

# Usage
p = doc.add_paragraph('This is ')
run = p.add_run('highlighted text')
run.style = char_style
```

## Font Embedding

```python
# python-docx does not support font embedding natively.
# Use only widely available fonts:
SAFE_FONTS = ['Calibri', 'Calibri Light', 'Segoe UI', 'Arial',
              'Times New Roman', 'Helvetica', 'Verdana', 'Tahoma']

def set_font(run, font_name='Calibri', size=Pt(11)):
    """Set font with consistent naming."""
    run.font.name = font_name
    # Also set theme font for compatibility
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
```

## XML-Level Advanced Manipulation

### Direct XML Access
```python
# Access paragraph XML
p._element  # lxml element for <w:p>

# Access run XML
run._r  # lxml element for <w:r>

# Access table XML
table._tbl  # lxml element for <w:tbl>

# Access cell XML
cell._tc  # lxml element for <w:tc>

# Access section properties
section._sectPr  # <w:sectPr> element

# Modify XML directly
from lxml import etree
xml_str = etree.tostring(p._element, pretty_print=True, encoding='unicode')
```

### Add Custom XML Part
```python
# Add custom XML to document (limited use with python-docx)
# For complex features, consider using Open XML SDK templates
```

## Integration Patterns

### With Chart Skill
```python
import matplotlib.pyplot as plt
import io

def add_matplotlib_chart(doc, figsize=(6, 3)):
    """Generate chart and embed in document."""
    fig, ax = plt.subplots(figsize=figsize)
    # ... chart code ...
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    doc.add_picture(buf, width=Inches(5.5))
    return buf
```

### With Table Skill
```python
def add_data_table(doc, headers, data, col_widths=None):
    """Create a styled table from data array."""
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    # Apply header styling
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="378ADD" w:val="clear"/>')
        cell._tc.get_or_add_tcPr().append(shading)
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(10)
    # Fill data
    for row_idx, row_data in enumerate(data):
        for col_idx, value in enumerate(row_data):
            table.cell(row_idx + 1, col_idx).text = str(value)
    return table
```

## Troubleshooting

### Corrupted Documents
- **Symptom**: Word shows "corrupted file" or crashes on open
- **Cause**: Invalid XML, unclosed tags, invalid characters
- **Solution**: Validate with `lxml.etree.parse()` before saving
- **Recovery**: Rename .docx to .zip, examine document.xml for errors
- **Prevention**: Always use python-docx API, avoid raw XML manipulation

### Encoding Issues
- **Symptom**: Characters display as "?" or boxes
- **Cause**: Unicode characters without proper font support
- **Solution**: Use SAFE_FONTS, set east-asian fonts for CJK
- **Fix**: Check character encoding: `ord(char)` should be within font range

### Large File Handling
- **Symptom**: .docx file is excessively large (100MB+)
- **Cause**: Uncompressed images, embedded media
- **Solution**: Compress images before embedding: PIL `quality=85, optimize=True`
- **Target**: < 1MB for text-only document, < 5MB with images

### Table Rendering Issues
- **Symptom**: Columns misaligned, borders missing
- **Cause**: Inconsistent column widths, missing style
- **Solution**: Set `table.style = 'Table Grid'`, define all column widths
- **Fix**: Ensure all rows have same number of cells

### Page Break Not Working
- **Symptom**: Content appears on same page
- **Cause**: `keep_with_next` or `widow_control` interfering
- **Solution**: Check paragraph properties, use `doc.add_page_break()` at paragraph level
- **Alternative**: Add page break before specific paragraph

### Missing Images
- **Symptom**: Image placeholder with red X
- **Cause**: Image path broken, format not supported, linked not embedded
- **Solution**: Always use absolute paths or byte streams
- **Fix**: `doc.add_picture(io.BytesIO(img_data))` instead of file path

## Quality Checklist

### Content Quality
- [ ] Document has a clear title and consistent heading hierarchy
- [ ] No placeholder text remains
- [ ] Body text uses justified alignment (professional documents)
- [ ] Headings follow logical nesting (H1 → H2 → H3)
- [ ] Lists are properly formatted (bullet or numbered)
- [ ] Tables have headers and are easy to read
- [ ] Images have descriptive captions
- [ ] TOC is present for documents over 5 pages
- [ ] All hyperlinks work correctly
- [ ] Page numbers are present (except title page)

### Design Quality
- [ ] Consistent typography (max 2 fonts)
- [ ] Font sizes follow the type scale
- [ ] Body text is dark gray (#333), not pure black
- [ ] Headings use the color palette consistently
- [ ] Margins are at least 2cm on all sides
- [ ] Tables have styled header rows with white text on blue background
- [ ] Alternating row colors on tables with more than 5 rows
- [ ] Captions are in italic, muted color
- [ ] Page margins are consistent throughout

### Technical Quality
- [ ] Page size is set explicitly (A4 default)
- [ ] Fonts are from the SAFE_FONTS list
- [ ] Images are embedded (not linked)
- [ ] No raw HTML in document
- [ ] Section breaks used appropriately
- [ ] Headers/footers properly configured
- [ ] Different first page if title page exists
- [ ] Document metadata set (title, author, subject)

### Verification Process
1. Open the .docx and verify all sections exist in order
2. Check table rendering — borders, alignment, header shading
3. Verify images are embedded (not linked)
4. Confirm page margins and orientation
5. Check that headers/footers have correct page numbers
6. Verify font rendering — no fallback fonts on another machine
7. Test hyperlinks (internal and external)
8. Check TOC page numbers (update field if needed)
9. Print preview: verify page breaks are in reasonable locations
10. Test on different Word versions (Word 2016, 365, Google Docs)
11. Check file size is reasonable
12. Verify document protection works (if set)

## Critical Rules — What to AVOID
- NEVER use unicode bullets — use 'List Bullet' style instead
- NEVER leave default styles unmodified — set font defaults first
- NEVER set page margins smaller than 2cm
- NEVER embed raw HTML — use proper python-docx API
- NEVER skip setting explicit font sizes and colors
- NEVER use more than 2 fonts in a single document
- NEVER use pure black (#000) for body text — use dark gray (#333)
- NEVER create a table without styling the header row
- NEVER use `pypdf` for PDF operations
- NEVER embed images from network drives — use local paths or bytes
- NEVER modify style definitions after adding content
- NEVER add page break inside a table
- NEVER assume `tab_stops` are preserved across Word versions
- NEVER use hard-coded page numbers in TOC — use field codes
- NEVER delete or rearrange sections without updating TOC
- NEVER save to the same file while Document object is open
