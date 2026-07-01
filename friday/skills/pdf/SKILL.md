---
name: pdf
description: Use this skill whenever creating, reading, editing, or manipulating PDF files
---

# Skill: PDF — Professional PDF Document Design

## Overview
FRIDAY creates print-ready PDF documents using **reportlab** (complex layouts) or **fpdf2** (simpler docs). **Use `create_pdf()` in `tools_flat.py` for high-level document creation with sections array.** For custom layouts, use reportlab's platypus framework directly.

Every PDF should look like a professionally designed document — consistent typography, generous margins, clear hierarchy, and proper metadata. PDF is the final output format; ensure everything renders correctly before delivery.

## QUALITY CRITICAL — READ BEFORE WRITING CODE

YOU ARE A DOCUMENT DESIGNER. Build every PDF as if it will be printed or presented to senior stakeholders. Every page must earn its place — no filler, no placeholder text, no single-table pages.

### EXACT PAGE BLUEPRINT (5 pages minimum)

Every PDF MUST have 5+ pages with this EXACT structure:

**Page 1 - Title Page**: A4, 2.5cm margins. Title 24pt bold #0C447C centered at 40% from top. Accent line: 2pt thick, #378ADD, 8cm wide, centered, 0.5cm below title. Subtitle 14pt #5F5E5A centered, 1cm below accent line. Date 11pt #888780 centered, 1.5cm below subtitle. "Prepared by FRIDAY AI" 10pt #888780 centered. NO header/footer on title page.

**Page 2 - Table of Contents**: Header: "Table of Contents" 18pt bold #185FA5. Body: entries with dot leaders. Level 0: 11pt bold #333333, left indent 0. Level 1: 10pt regular #5F5E5A, left indent 1.5cm. Each entry: "Section Title" + ". . . . . . ." + "3". Footer: page number centered, "Confidential" right-aligned, document title left-aligned, line above footer.

**Page 3 - Content Section 1**: Header "1. Executive Summary" 18pt bold #185FA5. Body text 11pt justified #333333, leading 15pt, space after 8pt. Key metrics in bold within body. Data table: 6+ rows x 4+ columns. Header row: bg #378ADD, text white bold 10pt. Data rows: 10pt #333333, alternating bg (#F1EFE8 / white). Column widths proportional to page width. Table caption below: "Table 1: ..." 9pt italic #888780 centered.

**Page 4 - Content Section 2**: Header "2. Data Analysis" 18pt bold #185FA5. Body text 11pt justified. Embedded matplotlib chart (bar or pie), sized 12cm x 7cm, centered. Chart must have: title 12pt bold, axis labels 10pt, data labels on bars, legend. Chart caption: "Figure 1: ..." 9pt italic #888780 centered. 1-2 body paragraphs below chart.

**Page 5 - Conclusion**: Header "3. Conclusions & Recommendations" 18pt bold #185FA5. Bullet list of 3-5 key findings (body_style with leftIndent 20pt, bulletIndent 0, spaceBefore 2pt). Summary paragraph. Final note 10pt italic #5F5E5A.

### TYPE SCALE (explicit — never default)
- Document title: 24pt bold
- Heading 1: 18pt bold
- Heading 2: 14pt bold
- Heading 3: 12pt bold
- Body text: 11pt regular, 15pt leading, justified
- Table header: 10pt bold
- Table data: 10pt regular
- Caption: 9pt italic
- Header/footer: 8pt regular

### COLOR SYSTEM (pick ONE, apply everywhere)
- **Professional Blue**: title #0C447C, H1 #185FA5, H2 #3C3489, table header #378ADD, body #333333, light bg #F1EFE8, accent #534AB7
- **Corporate**: title #1D9E75, H1 #0F6E56, H2 #085041, table header #639922, body #333333, light bg #E1F5EE
- **Dark Report**: title page #0a0a2e bg with white text, body pages white bg, headings #00d4ff, body #e0e0e0 on dark / #333333 on light

### EVERY PAGE MUST HAVE
- Explicit page size set (A4 default)
- 2.5cm margins (minimum 1.5cm)
- Metadata set (title, author, subject, keywords)
- NO pure black (#000) body text — use dark gray (#333333)
- Proper leading for body text (at least 1.35x font size)

### ANTI-PATTERNS — OUTPUTS THAT GET REJECTED
- Single-page table dump with no formatting, title, or context
- No title page or table of contents
- Missing headers/footers on content pages (except title page)
- No page numbers
- Default black (#000) text on white (#FFF) throughout
- No charts, images, or visual elements of any kind
- Tables without colored header rows or alternating row colors
- Missing document metadata
- Less than 4 content pages (excluding title page)
- Body text without explicit leading/line-spacing set
- Inconsistent heading styles across pages

## Triggers
- "create a PDF", "make a PDF", ".pdf file"
- "convert to PDF", "save as PDF"
- "report", "invoice", "certificate", "form"
- "fill PDF form", "merge PDFs", "split PDF"
- "print-ready", "high-quality PDF", "PDF/A"

## Libraries

### Primary Libraries
| Library | Use Case | Strengths | Limitations |
|---------|----------|-----------|-------------|
| **reportlab** | Complex layouts, tables, graphics, charts | Full control, page templates, graphics primitives | Steeper learning curve, larger output |
| **fpdf2** | Simple documents, invoices, labels | Lightweight, easy API, smaller files | Limited layout control, fewer features |
| **pdfplumber** | Reading/extracting text/tables | Handles most PDFs, table extraction | No creation capability |
| **pypdf** | DO NOT USE | — | Known issues with modern PDF features |

### Supporting Libraries
```python
import matplotlib.pyplot as plt
import cairosvg
from PIL import Image
```

## Design System

### Page Sizes
| Size | Width x Height | Usage |
|------|--------------|-------|
| A4 | 21.0cm x 29.7cm | Default — reports, letters, docs |
| Letter | 8.5" x 11" (21.59cm x 27.94cm) | US standard |
| A5 | 14.8cm x 21.0cm | Brochures, flyers |
| A3 | 29.7cm x 42.0cm | Posters, large tables |
| Legal | 21.59cm x 35.56cm | Contracts |
| A0-A6 | Standard ISO sizes | Posters, cards |
| TABLOID | 27.94cm x 43.18cm | Newspapers, large layouts |

### Margins
- **Default**: Top/Bottom = 2cm, Left/Right = 2.5cm (binding margin)
- **Binding**: Add 0.5cm extra on left for documents > 10 pages
- **Minimum**: Never less than 1.5cm on any side
- **Safe area**: Content within 0.5cm of margins

### Type Scale
| Role | Size | Weight | Leading |
|------|------|--------|---------|
| Document title | 24pt | Bold | 30pt |
| Heading 1 | 18pt | Bold | 24pt |
| Heading 2 | 14pt | Bold | 20pt |
| Heading 3 | 12pt | Bold | 17pt |
| Body text | 11pt | Regular | 15pt |
| Body text (small) | 10pt | Regular | 14pt |
| Caption / small | 9pt | Italic | 12pt |
| Table header | 10pt | Bold | 14pt |
| Table body | 10pt | Regular | 14pt |
| Footer / header | 8pt | Regular | 11pt |
| Footnote | 8pt | Regular | 11pt |

### Color System
| Role | Hex | RGB | Usage |
|------|-----|-----|-------|
| Title | #0C447C | (12, 68, 124) | Document title |
| Heading 1 | #185FA5 | (24, 95, 165) | Section headings |
| Heading 2 | #3C3489 | (60, 52, 137) | Sub-section headings |
| Heading 3 | #1D9E75 | (29, 158, 117) | Tertiary headings |
| Body text | #333333 | (51, 51, 51) | All body content |
| Muted text | #888780 | (136, 135, 128) | Captions, metadata |
| Table header bg | #378ADD | (55, 138, 221) | Table headers |
| Table header text | #FFFFFF | (255, 255, 255) | Table header text |
| Link | #185FA5 | (24, 95, 165) | Hyperlinks |
| Border / rule | #B4B2A9 | (180, 178, 169) | Lines and borders |
| Accent | #534AB7 | (83, 74, 183) | Accent elements |
| Light bg | #F1EFE8 | (241, 239, 232) | Alternating rows |
| Warning | #BA7517 | (186, 117, 23) | Warnings |
| Error | #E24B4A | (226, 75, 74) | Errors |
| Success | #639922 | (99, 153, 34) | Success indicators |

## Comprehensive ReportLab API Reference

### Core Imports
```python
from reportlab.lib.pagesizes import A4, letter, legal, A3, A5, landscape
from reportlab.lib.units import inch, cm, mm, pt
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image, ListFlowable, ListItem,
    PageTemplate, Frame, BaseDocTemplate, NextPageTemplate,
    KeepTogether, CondPageBreak, Flowable, Preformatted
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.lib.fonts import addMapping
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
```

### Document Setup
```python
doc = SimpleDocTemplate(
    "output.pdf",
    pagesize=A4,
    leftMargin=2.5*cm,
    rightMargin=2.5*cm,
    topMargin=2*cm,
    bottomMargin=2*cm,
    title="Document Title",
    author="FRIDAY AI",
    subject="Professional Report",
    keywords=["report", "professional", "pdf"],
    creator="FRIDAY AI Document System",
)

story = []
styles = getSampleStyleSheet()
```

### Custom Paragraph Styles
```python
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Title'],
    fontSize=24,
    leading=30,
    textColor=HexColor('#0C447C'),
    spaceAfter=12,
    spaceBefore=0,
    alignment=TA_LEFT,
    fontName='Helvetica-Bold',
)

heading1_style = ParagraphStyle(
    'DocH1',
    parent=styles['Heading1'],
    fontSize=18,
    leading=24,
    textColor=HexColor('#185FA5'),
    spaceBefore=24,
    spaceAfter=8,
    fontName='Helvetica-Bold',
)

heading2_style = ParagraphStyle(
    'DocH2',
    parent=styles['Heading2'],
    fontSize=14,
    leading=20,
    textColor=HexColor('#3C3489'),
    spaceBefore=18,
    spaceAfter=6,
    fontName='Helvetica-Bold',
)

heading3_style = ParagraphStyle(
    'DocH3',
    parent=styles['Heading3'],
    fontSize=12,
    leading=17,
    textColor=HexColor('#1D9E75'),
    spaceBefore=14,
    spaceAfter=4,
    fontName='Helvetica-Bold',
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontSize=11,
    leading=15,
    textColor=HexColor('#333333'),
    spaceAfter=8,
    spaceBefore=0,
    alignment=TA_JUSTIFY,
    fontName='Helvetica',
    firstLineIndent=0,
    leftIndent=0,
    rightIndent=0,
)

body_small_style = ParagraphStyle(
    'DocBodySmall',
    parent=body_style,
    fontSize=10,
    leading=14,
)

caption_style = ParagraphStyle(
    'Caption',
    parent=styles['Normal'],
    fontSize=9,
    leading=12,
    textColor=HexColor('#888780'),
    alignment=TA_CENTER,
    spaceBefore=4,
    spaceAfter=12,
    fontName='Helvetica-Oblique',
)

code_style = ParagraphStyle(
    'Code',
    parent=styles['Code'],
    fontSize=8,
    leading=11,
    textColor=HexColor('#333333'),
    fontName='Courier',
    leftIndent=10,
    spaceAfter=6,
    backColor=HexColor('#F1EFE8'),
)

bullet_style = ParagraphStyle(
    'DocBullet',
    parent=body_style,
    leftIndent=20,
    bulletIndent=0,
    spaceBefore=2,
    spaceAfter=2,
)
```

## Complete Document Structure

### Title Page
```python
story.append(Spacer(1, 6*cm))
story.append(Paragraph("Document Title", title_style))

accent_data = [['']]
accent_table = Table(accent_data, colWidths=[8*cm], rowHeights=[0.1*cm])
accent_table.setStyle(TableStyle([
    ('LINEBELOW', (0, 0), (-1, -1), 2, HexColor('#378ADD')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
]))
story.append(accent_table)
story.append(Spacer(1, 12))

story.append(Paragraph(
    "Subtitle or description",
    ParagraphStyle('Subtitle', parent=body_style,
                   fontSize=14, leading=18,
                   textColor=HexColor('#5F5E5A'),
                   alignment=TA_LEFT, spaceBefore=0, spaceAfter=18)
))
story.append(Paragraph(
    "June 2026",
    ParagraphStyle('Date', parent=body_style,
                   fontSize=11, leading=15,
                   textColor=HexColor('#888780'), alignment=TA_LEFT)
))
story.append(Paragraph(
    "Prepared by FRIDAY AI | Version 1.0",
    ParagraphStyle('Meta', parent=body_style,
                   fontSize=10, leading=14,
                   textColor=HexColor('#888780'), alignment=TA_LEFT)
))
story.append(PageBreak())
```

### Table of Contents
```python
story.append(Paragraph("Table of Contents", heading1_style))
story.append(Spacer(1, 0.5*cm))

def add_toc_entry(story, title, page, level=0):
    indent = level * 1.5*cm
    dots = ". " * (60 - len(title))
    text = f'{title} {dots} {page}'
    style = ParagraphStyle(
        f'TOCLevel{level}',
        parent=body_style,
        fontSize=11 if level == 0 else 10,
        leftIndent=indent,
        spaceBefore=4 if level == 0 else 2,
        spaceAfter=2,
        textColor=HexColor('#333333'),
        fontName='Helvetica-Bold' if level == 0 else 'Helvetica',
    )
    story.append(Paragraph(text, style))

add_toc_entry(story, "1. Introduction", 3, level=0)
add_toc_entry(story, "1.1 Background", 3, level=1)
add_toc_entry(story, "1.2 Scope", 4, level=1)
add_toc_entry(story, "2. Analysis", 5, level=0)
add_toc_entry(story, "3. Recommendations", 8, level=0)

story.append(PageBreak())
```

## Flowables Reference

### Paragraph
```python
story.append(Paragraph("Text content", body_style))

story.append(Paragraph(
    'This is <b>bold</b>, <i>italic</i>, '
    '<u>underline</u>, <strike>strikethrough</strike>, '
    '<font color="#378ADD" size="14">colored text</font>, '
    '<super>superscript</super>, <sub>subscript</sub>, '
    '<font face="Courier">monospace</font>',
    body_style
))

story.append(Paragraph(
    'Visit <a href="http://example.com" color="#185FA5">our website</a> for details.',
    body_style
))
```

### Spacer
```python
story.append(Spacer(1, 1*cm))
story.append(Spacer(1, 2*cm))
```

### PageBreak
```python
story.append(PageBreak())
```

### CondPageBreak
```python
story.append(CondPageBreak(5*cm))
```

### KeepTogether
```python
items = [
    Paragraph("Important block", heading2_style),
    Paragraph("This whole block should stay together", body_style),
]
story.append(KeepTogether(items))
```

### NextPageTemplate
```python
story.append(NextPageTemplate('Landscape'))
```

### FrameBreak
```python
from reportlab.platypus import FrameBreak
story.append(FrameBreak())
```

### Preformatted (Code)
```python
story.append(Preformatted(
    "def hello():\\n    print('Hello, World!')\\n    return True",
    code_style
))
```

## Advanced Table Styling

### Table with Full Styling
```python
data = [
    ['Metric', 'Q1', 'Q2', 'Q3', 'Q4'],
    ['Revenue', '$100K', '$200K', '$300K', '$400K'],
    ['Cost', '$60K', '$120K', '$180K', '$240K'],
    ['Profit', '$40K', '$80K', '$120K', '$160K'],
    ['Margin', '40%', '40%', '40%', '40%'],
]

col_widths = [4*cm, 3*cm, 3*cm, 3*cm, 3*cm]
table = Table(data, colWidths=col_widths, repeatRows=1)

table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#378ADD')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 10),
    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#B4B2A9')),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#F1EFE8'), white]),
    ('TOPPADDING', (0, 1), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]))

story.append(Spacer(1, 0.5*cm))
story.append(table)
story.append(Paragraph("Table 1: Quarterly financial summary", caption_style))
```

### TableStyle Commands Reference
```python
# All TableStyle commands:
# BACKGROUND, TEXTCOLOR, FONTNAME, FONTSIZE, ALIGN, VALIGN
# GRID, BOX, LINEBELOW, LINEABOVE, LINEBEFORE, LINEAFTER
# INNERGRID, ROWBACKGROUNDS, COLBACKGROUNDS
# TOPPADDING, BOTTOMPADDING, LEFTPADDING, RIGHTPADDING
# ROTATION, SPAN
# Format: (COMMAND, (col_start, row_start), (col_end, row_end), value)
```

### Column Widths
```python
col_widths = [4*cm, 3*cm, 3*cm, 3*cm]
page_width = A4[0] - 2*2.5*cm
col_widths = [page_width * 0.25] * 4
```

### Row Heights
```python
table = Table(data, colWidths=col_widths, rowHeights=[1*cm, 0.8*cm, 0.8*cm, 0.8*cm])
```

### Table with Images
```python
img = Image('logo.png', width=2*cm, height=1*cm)
data_with_img = [
    ['Logo', 'Description', 'Value'],
    [img, 'Company A', '$100K'],
]
```

## Chart Integration

### Matplotlib Charts to Images
```python
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

def create_bar_chart():
    fig, ax = plt.subplots(figsize=(6, 3), dpi=200)
    categories = ['Q1', 'Q2', 'Q3', 'Q4']
    values = [100, 200, 300, 400]
    bars = ax.bar(categories, values, color='#378ADD', edgecolor='white', width=0.6)
    ax.set_title('Quarterly Revenue', fontsize=12, fontweight='bold', color='#333333', pad=10)
    ax.set_ylabel('Revenue ($K)', fontsize=10, color='#666666')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.tick_params(colors='#666666', labelsize=9)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${height}K', ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    buf.seek(0)
    return Image(buf, width=12*cm, height=6*cm)

chart_img = create_bar_chart()
story.append(chart_img)
story.append(Paragraph("Figure 1: Quarterly revenue breakdown", caption_style))

def create_pie_chart():
    fig, ax = plt.subplots(figsize=(5, 4), dpi=200)
    sizes = [35, 30, 20, 15]
    labels = ['Product A', 'Product B', 'Product C', 'Product D']
    colors = ['#378ADD', '#1D9E75', '#D85A30', '#7F77DD']
    explode = (0.05, 0.05, 0.05, 0.05)
    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.0f%%', startangle=90, pctdistance=0.6,
        textprops={'fontsize': 9, 'color': '#333333'}
    )
    for t in autotexts:
        t.set_color('white')
        t.set_fontweight('bold')
    ax.axis('equal')
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return Image(buf, width=10*cm, height=8*cm)

def create_line_chart():
    fig, ax = plt.subplots(figsize=(6, 3), dpi=200)
    x = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    y1 = [100, 120, 140, 160, 200, 250]
    y2 = [80, 90, 100, 110, 130, 160]
    ax.plot(x, y1, marker='o', color='#378ADD', linewidth=2, label='Revenue', markersize=5)
    ax.plot(x, y2, marker='s', color='#1D9E75', linewidth=2, label='Profit', markersize=5)
    ax.legend(fontsize=9)
    ax.set_title('Monthly Trend', fontsize=12, fontweight='bold', color='#333333')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylabel('Amount ($K)', fontsize=10)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return Image(buf, width=12*cm, height=6*cm)
```

## SVG-to-PDF Embedding

```python
import cairosvg

def embed_svg_as_pdf(story, svg_content, width=10*cm, height=5*cm):
    png_data = cairosvg.svg2png(
        bytestring=svg_content.encode('utf-8') if isinstance(svg_content, str) else svg_content,
        output_width=int(width / cm * 300),
        output_height=int(height / cm * 300),
    )
    from io import BytesIO
    img = Image(BytesIO(png_data), width=width, height=height)
    story.append(img)
    return img

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

class VectorDrawing(Flowable):
    def __init__(self, drawing, width=400, height=200):
        Flowable.__init__(self)
        self.drawing = drawing
        self.width = width
        self.height = height
    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)

def create_vector_shape():
    d = Drawing(400, 200)
    d.add(Rect(50, 50, 300, 100, fillColor=HexColor('#E6F1FB'),
              strokeColor=HexColor('#378ADD'), strokeWidth=2))
    d.add(String(200, 120, 'Vector Shape', textAnchor='middle',
                 fontName='Helvetica', fontSize=20, fillColor=HexColor('#0C447C')))
    return d

drawing = create_vector_shape()
story.append(VectorDrawing(drawing, width=10*cm, height=5*cm))
```

## Headers and Footers

### Page Template with Header/Footer
```python
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

class NumberedDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self.page_count = 0
    def afterPage(self):
        self.page_count += 1

def header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(HexColor('#888780'))
    canvas_obj.drawString(2.5*cm, A4[1] - 1.5*cm, "Document Title")
    canvas_obj.drawRightString(A4[0] - 2.5*cm, A4[1] - 1.5*cm, "Confidential")
    canvas_obj.setStrokeColor(HexColor('#378ADD'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(2.5*cm, A4[1] - 1.7*cm, A4[0] - 2.5*cm, A4[1] - 1.7*cm)
    canvas_obj.line(2.5*cm, 1.5*cm, A4[0] - 2.5*cm, 1.5*cm)
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(HexColor('#888780'))
    canvas_obj.drawCentredString(A4[0] / 2, 1.2*cm, f"Page {doc.page}")
    canvas_obj.drawString(2.5*cm, 1.2*cm, "July 2026")
    canvas_obj.drawRightString(A4[0] - 2.5*cm, 1.2*cm, "Doc v1.0")
    canvas_obj.restoreState()

def first_page_header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(HexColor('#378ADD'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(2.5*cm, 1.5*cm, A4[0] - 2.5*cm, 1.5*cm)
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(HexColor('#888780'))
    canvas_obj.drawCentredString(A4[0] / 2, 1.2*cm, f"Page {doc.page}")
    canvas_obj.restoreState()
```

## Complex Layouts: Multi-Column, Frames, Templates

### Two-Column Layout
```python
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, NextPageTemplate

def create_two_column_document(output_path):
    frame_left = Frame(2.5*cm, 2*cm, 7*cm, 24.7*cm, id='left_column')
    frame_right = Frame(10*cm, 2*cm, 8.5*cm, 24.7*cm, id='right_column')
    title_frame = Frame(2.5*cm, 2*cm, 16*cm, 25.7*cm, id='title_frame')
    doc = BaseDocTemplate(output_path, pagesize=A4, title="Two-Column Report", author="FRIDAY")
    doc.addPageTemplates([
        PageTemplate(id='Title', frames=[title_frame], onPage=first_page_header_footer),
        PageTemplate(id='TwoColumn', frames=[frame_left, frame_right], onPage=header_footer),
    ])
    story = []
    story.append(Spacer(1, 6*cm))
    story.append(Paragraph("Two-Column Report", title_style))
    story.append(PageBreak())
    story.append(NextPageTemplate('TwoColumn'))
    for i in range(20):
        story.append(Paragraph(f"Section {i+1}", heading2_style))
        story.append(Paragraph("Body text flowing between columns automatically.", body_style))
    doc.build(story)
    return doc
```

### Three-Column Layout
```python
col_width = (A4[0] - 2*2.5*cm) / 3
frame1 = Frame(2.5*cm, 2*cm, col_width, 24.7*cm, id='col1')
frame2 = Frame(2.5*cm + col_width + 0.5*cm, 2*cm, col_width, 24.7*cm, id='col2')
frame3 = Frame(2.5*cm + 2*(col_width + 0.5*cm), 2*cm, col_width, 24.7*cm, id='col3')
```

### Landscape Mode
```python
landscape_doc = SimpleDocTemplate(
    "landscape.pdf",
    pagesize=landscape(A4),
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
)
```

## Hyperlinks and Bookmarks

### Internal Bookmarks
```python
def add_bookmark(story, name, title):
    story.append(Paragraph(f'<a name="{name}"/>{title}', heading1_style))

add_bookmark(story, 'ch1', 'Chapter 1: Introduction')
story.append(Paragraph(
    '<a href="#ch1" color="#185FA5">Go to Chapter 1</a>', body_style
))
```

### External Links
```python
story.append(Paragraph(
    'Visit <a href="https://example.com" color="#185FA5">Example</a> for details.',
    body_style
))
```

## Annotations and Form Fields

### Annotation via Canvas
```python
def add_annotation(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFillColor(HexColor('#E6F1FB'))
    canvas_obj.setStrokeColor(HexColor('#378ADD'))
    canvas_obj.rect(2.5*cm, 20*cm, 8*cm, 2*cm, fill=1, stroke=1)
    canvas_obj.setFont('Helvetica-Bold', 10)
    canvas_obj.setFillColor(HexColor('#0C447C'))
    canvas_obj.drawString(3*cm, 21*cm, "Note:")
    canvas_obj.setFont('Helvetica', 9)
    canvas_obj.setFillColor(HexColor('#333333'))
    canvas_obj.drawString(3*cm, 20.3*cm, "This is an annotation box.")
    canvas_obj.restoreState()
```

## Digital Signatures

```python
# reportlab supports basic signature field placement
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4

def add_signature_field(output_pdf_path):
    c = pdfcanvas.Canvas(output_pdf_path, pagesize=A4)
    c.drawString(100, 100, "Signature: ________________________")
    c.drawString(100, 80, "Date: ________________________")
    c.save()
# For actual digital signatures, use PyKCS11 or a dedicated signing library
```

## PDF/A Compliance

```python
# reportlab can produce PDF/A-1b compatible output
def create_pdfa_doc(output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        title="PDF/A Document", author="FRIDAY",
        subject="PDF/A-1b compliant",
    )
    story = []
    story.append(Paragraph("PDF/A-1b Document", title_style))
    story.append(Paragraph("Designed for archival compliance.", body_style))
    # Requirements: embedded fonts, no transparency, no encryption
    # Use Type 1 fonts (Helvetica) which are always embedded
    doc.build(story)
    return doc
```

## Metadata

```python
doc = SimpleDocTemplate(
    "output.pdf", pagesize=A4,
    title="Document Title",
    author="FRIDAY AI",
    subject="Professional Report",
    keywords=["report", "analysis", "2026"],
    creator="FRIDAY AI Document System",
)

# Custom metadata via internal document
def set_custom_metadata(doc, metadata_dict):
    pdf_doc = doc._pdf_doc
    for key, value in metadata_dict.items():
        from reportlab.pdfbase.pdfdoc import PDFString
        pdf_doc.info.dict[key] = PDFString(value)
```

## Compression and Optimization

```python
# ReportLab compresses by default (object streams, cross-ref streams)
# Image compression before embedding
from PIL import Image as PILImage
img = PILImage.open('large_photo.jpg')
img = img.resize((1200, 900), PILImage.LANCZOS)
img.save('optimized.jpg', quality=85, optimize=True)

# For large documents, split into chapters and merge later
```

## Watermarking and Encryption

### Text Watermark
```python
def add_watermark(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont('Helvetica', 48)
    canvas_obj.setFillColor(HexColor('#E0E0E0'))
    canvas_obj.translate(A4[0]/2, A4[1]/2)
    canvas_obj.rotate(45)
    canvas_obj.drawCentredString(0, 0, "DRAFT")
    canvas_obj.restoreState()
```

### Image Watermark
```python
def add_image_watermark(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.drawImage('logo_watermark.png',
                         2.5*cm, 2*cm, width=16*cm, height=25*cm,
                         preserveAspectRatio=True, mask='auto')
    canvas_obj.restoreState()
```

### Encryption (Password Protection)
```python
from reportlab.lib.pdfencrypt import StandardEncryption

enc = StandardEncryption(
    userPassword="user123",
    ownerPassword="owner456",
    canPrint=1,
    canModify=0,
    canCopy=0,
    canAnnotate=0,
)
doc = SimpleDocTemplate("encrypted.pdf", pagesize=A4, encrypt=enc)
```

## Merging and Splitting PDFs

### Merging
```python
# Use Ghostscript for reliable merging
# gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=output.pdf a.pdf b.pdf

# Or use pdfplumber with low-level page copy
import pdfplumber
from reportlab.pdfgen import canvas as pdfcanvas

def merge_pdfs_simple(pdf_list, output_path):
    """Simple merge by concatenating pages."""
    # For production, use PyMuPDF (fitz) or Ghostscript
    pass
```

### Splitting
```python
import pdfplumber
from reportlab.pdfgen import canvas as pdfcanvas

def split_pdf(input_path, output_dir):
    with pdfplumber.open(input_path) as pdf:
        for i, page in enumerate(pdf.pages):
            c = pdfcanvas.Canvas(f"{output_dir}/page_{i+1}.pdf")
            # Draw extracted content
            c.save()
```

## fpdf2 Approach

### Simple Document
```python
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", "B", 24)
pdf.set_text_color(12, 68, 124)
pdf.cell(0, 15, "Document Title", ln=True, align="L")
pdf.ln(10)

pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(51, 51, 51)
pdf.multi_cell(0, 5, "Body text content here with proper flow.")
pdf.ln(5)

pdf.set_font("Helvetica", "B", 14)
pdf.set_text_color(24, 95, 165)
pdf.cell(0, 10, "Section Header", ln=True)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(51, 51, 51)
pdf.multi_cell(0, 5, "More body text.")

pdf.output("output.pdf")
```

### fpdf2 Table
```python
from fpdf import FPDF

class PDF(FPDF):
    def styled_table(self, headers, data, col_widths):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(55, 138, 221)
        self.set_text_color(255, 255, 255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, border=1, align="C", fill=True)
        self.ln()
        self.set_font("Helvetica", "", 10)
        self.set_text_color(51, 51, 51)
        fill = False
        for row in data:
            for i, value in enumerate(row):
                self.cell(col_widths[i], 8, str(value), border=1, align="C", fill=fill)
            self.ln()
            fill = not fill

pdf = PDF()
pdf.add_page()
pdf.styled_table(
    ['Metric', 'Value', 'Change'],
    [['Revenue', '$2.4M', '+12%'], ['Users', '12,500', '+8%']],
    [6*cm, 4*cm, 4*cm]
)
pdf.output("table.pdf")
```

### fpdf2 Header/Footer
```python
class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(136, 135, 128)
        self.cell(0, 10, "Document Title", align="R")
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(136, 135, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

pdf = PDF()
pdf.alias_nb_pages()
```

## Reading PDFs

### Text and Table Extraction
```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    meta = pdf.metadata
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
        words = page.extract_words()
        images = page.images
        lines = page.lines

with pdfplumber.open("file.pdf") as pdf:
    page = pdf.pages[0]
    text = page.extract_text(layout=True)
```

## Troubleshooting

### Font Issues
- **Symptoms**: Characters render as "?" or boxes
- **Causes**: Missing font, unsupported character
- **Solutions**: Use Helvetica/Times/Courier (always available)
- **Custom fonts**: Register with TTFont
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('CustomFont', 'path/to/font.ttf'))
```

### Large Document Performance
- **Symptoms**: Slow generation or out of memory
- **Causes**: Too many flowables, high-res images
- **Solutions**: Compress images to < 1200px, avoid excessive KeepTogether blocks

### Encoding Problems
- **Symptoms**: Unicode characters not rendering
- **Causes**: Font lacks character support
- **Solutions**: Embed TTF with full Unicode coverage

### Alignment Issues
- **Symptoms**: Text or tables misaligned
- **Causes**: Inconsistent styles, column width mismatch
- **Solutions**: Always specify ALIGN and VALIGN in TableStyle

## Quality Checklist

### Content Quality
- [ ] Document has clear title and consistent heading hierarchy
- [ ] Body text uses justified alignment
- [ ] Tables have styled headers and proper alignment
- [ ] Charts have titles, legends, and source citations
- [ ] TOC page numbers are accurate
- [ ] All hyperlinks work correctly
- [ ] No placeholder text remains

### Design Quality
- [ ] Margins at least 2cm top/bottom, 2.5cm left/right
- [ ] Consistent typography (max 2 fonts)
- [ ] Body text is dark gray (#333), not pure black
- [ ] Sufficient contrast for all text elements
- [ ] Table alternating row colors for readability
- [ ] Headers/footers on all pages (except title page)
- [ ] Page numbers present and correct

### Technical Quality
- [ ] Page size set explicitly (A4 default)
- [ ] Fonts are standard (Helvetica/Times/Courier) or embedded
- [ ] Metadata set (title, author, subject, keywords)
- [ ] File compressed and optimized
- [ ] Vector elements maintained (not rasterized)
- [ ] PDF/A compliance if required
- [ ] Renders correctly in Adobe Acrobat and browsers

### Verification Process
1. Open the PDF and verify all pages render correctly
2. Check text is selectable (not rasterized)
3. Verify tables have correct borders and alignment
4. Confirm hyperlinks work (if any)
5. Check font embedding and rendering
6. Verify page size matches specification
7. Check headers and footers appear on correct pages
8. Verify table of contents page numbers are accurate
9. Print preview: check margins and page breaks
10. Test on different PDF viewers (Adobe, Chrome, Firefox, Edge)
11. Check file size is reasonable
12. Verify encryption/password protection if set

## Critical Rules — What to AVOID
- NEVER use `pypdf` — known issues with modern PDF features
- NEVER create PDFs without setting explicit page size and margins
- NEVER embed fonts that aren't standard PDF fonts (use Helvetica/Times/Courier)
- NEVER overlap text or elements at absolute coordinates
- NEVER use Unicode without proper font embedding
- NEVER skip adding metadata (title, author, subject)
- NEVER generate raster-only content — maintain vector elements
- NEVER use pure black (#000) for body text — use dark gray (#333)
- NEVER set margins smaller than 1.5cm
- NEVER add too many KeepTogether blocks — slows rendering
- NEVER use images larger than 2000px width — compress first
- NEVER build 50+ page documents without testing intermediate output
- NEVER assume all PDF viewers render identically
