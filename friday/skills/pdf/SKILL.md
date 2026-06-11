---
name: pdf
description: Use this skill whenever creating, reading, editing, or manipulating PDF files
---

# PDF Creation Guide

## Overview
FRIDAY creates and manipulates PDF files using `create_pdf()` in `tools_flat.py`. Use reportlab or fpdf2 for creation. **Create rich PDFs with charts inline using the `sections` array:**
```python
create_pdf(
    title="Report Title",
    author="FRIDAY",
    sections=[
        {"type": "heading", "text": "Introduction"},
        {"type": "paragraph", "text": "Analysis results."},
        {"type": "chart", "chart_type": "bar",
         "title": "Revenue by Quarter",
         "data": ["Q1","Q2","Q3","Q4"], "data2": [100, 200, 150, 300]},
        {"type": "table", "headers": ["Metric","Value"], "rows": [["A","42"]]},
    ]
)
```
All 23 chart types supported: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar.

NEVER use pypdf. Use reportlab or fpdf2 for creation.

## Triggers
- "create a PDF", "make a PDF", ".pdf file"
- "convert to PDF", "save as PDF"
- "fill PDF form", "merge PDFs", "split PDF"
- Any request mentioning "PDF" or "document as PDF"

## Libraries
- **reportlab** — for creating PDFs with complex layouts, tables, graphics
- **fpdf2** — simpler alternative for basic PDFs
- **pdfplumber** — for reading/extracting text and tables from PDFs (preferred)
- **pypdf** — DO NOT USE (known issues)

## Code Patterns

### Creating a PDF with reportlab
```python
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, Image, PageBreak)
from reportlab.lib import colors

doc = SimpleDocTemplate("output.pdf", pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm)

story = []
styles = getSampleStyleSheet()

# Title
title_style = ParagraphStyle(
    'CustomTitle', parent=styles['Title'],
    fontSize=24, textColor=HexColor('#00BFFF'),
    spaceAfter=12
)
story.append(Paragraph("Document Title", title_style))
story.append(Spacer(1, 12))

# Body text
story.append(Paragraph("Normal paragraph text.", styles['Normal']))
story.append(Spacer(1, 6))

# Table
data = [['Header 1', 'Header 2', 'Header 3'],
        ['Cell 1', 'Cell 2', 'Cell 3']]
table = Table(data, colWidths=[4*cm, 4*cm, 4*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#00BFFF')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
]))
story.append(table)

doc.build(story)
```

### Creating a PDF with fpdf2 (simpler)
```python
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", "B", 16)
pdf.cell(0, 10, "Document Title", ln=True, align="C")
pdf.set_font("Arial", "", 12)
pdf.cell(0, 10, "This is body text.", ln=True)
pdf.output("output.pdf")
```

### Reading PDFs
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
```

## Critical Rules — What to AVOID
- NEVER use `pypdf` — it has known issues with modern PDF features
- NEVER create PDFs without setting explicit page size and margins
- NEVER embed fonts that aren't standard PDF fonts (use Arial/Helvetica/Times)
- NEVER put text at absolute coordinates that overlap
- NEVER use Unicode characters without proper font embedding
- NEVER skip adding metadata (title, author, subject)
- NEVER generate PDFs with raster-only content — maintain vector elements

## Color System
- Headers: #00BFFF (cyan/tech) or #FFB000 (amber/warm)
- Body text: #333333 (dark) or #000000
- Links: #0066CC
- Table headers: colored background with white text
- Alternating table rows: light gray (#F5F5F5) / white

## Verification
1. Open the PDF and verify all pages render correctly
2. Check text is selectable (not rasterized)
3. Verify tables have correct borders and alignment
4. Confirm hyperlinks work (if any)
5. Check font embedding and rendering
6. Verify page size matches specification
