---
name: pptx
description: Use this skill any time a PowerPoint presentation (.pptx) is involved
---

# PPTX Creation Guide

## Overview
FRIDAY uses python-pptx to create professional slide decks, presentations, and pitch decks. **Use `create_pptx()` in `tools_flat.py` for high-level slide creation with type:"chart" slides supporting all 23 chart types.** Low-level python-pptx API is used for custom layouts.

All 23 chart types supported in `create_pptx(sections=[{"type":"chart", "chart_type":"...", ...}])`: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar.

## Triggers
- "make a presentation", "create slides", "slide deck", "pitch deck"
- Any mention of .pptx, "PowerPoint", "slides", "deck"
- "presentation", "slide show", "keynote"

## Libraries
- **python-pptx** — primary library
- Presentation() — main class
- Slide layouts, shapes, text frames, tables, charts, images

## Code Patterns

### Basic Presentation
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Title slide
slide = prs.slides.add_slide(prs.slide_layouts[0])
title = slide.shapes.title
title.text = "Presentation Title"
subtitle = slide.placeholders[1]
subtitle.text = "Subtitle"

# Content slide with bullet points
slide = prs.slides.add_slide(prs.slide_layouts[1])
for placeholder in slide.placeholders:
    if placeholder.placeholder_format.idx == 0:
        placeholder.text = "Section Title"
    elif placeholder.placeholder_format.idx == 1:
        tf = placeholder.text_frame
        tf.text = "Main point"
        p = tf.add_paragraph()
        p.text = "Sub point"
        p.level = 1

# Add shape
shape = slide.shapes.add_shape(
    MSO_SHAPE.ROUNDED_RECTANGLE,
    Inches(1), Inches(1), Inches(4), Inches(3)
)
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0, 191, 255)
tf = shape.text_frame
tf.text = "Custom shape text"
tf.paragraphs[0].alignment = PP_ALIGN.CENTER

prs.save('output.pptx')
```

### Adding Tables
```python
from pptx.util import Inches
table_shape = slide.shapes.add_table(rows=3, cols=3, left=Inches(1), top=Inches(2), width=Inches(8), height=Inches(2))
table = table_shape.table
table.cell(0, 0).text = "Header 1"
table.cell(0, 1).text = "Header 2"
```

### Adding Charts
```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Revenue', (100, 200, 300, 400))

chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(2), Inches(6), Inches(4),
    chart_data
).chart
chart.has_legend = True
chart.chart_title.has_text_frame = True
chart.chart_title.text_frame.text = "Quarterly Revenue"
```

## Critical Rules — What to AVOID
- NEVER leave default placeholder text ("Click to add title") — always replace
- NEVER use unicode bullets — use paragraph level=1 for sub-bullets
- NEVER mix slide layouts from different templates without careful testing
- NEVER create slides with overlapping shapes
- NEVER use font sizes smaller than 14pt for body text
- NEVER use more than 2 fonts per presentation
- NEVER embed external images as links — always embed
- NEVER skip setting explicit slide dimensions

## Color System for Presentations
Use semantic color mapping:
- Title text: White or light (#FFFFFF, #E0E0E0)
- Body text: Dark gray (#333333) on light backgrounds
- Accent/highlight: Theme primary (#00BFFF for tech, #FFB000 for warm)
- Data colors: Use 4-6 distinct hues (blue, teal, coral, amber, green, purple)
- Background: Dark (#050510) for tech themes, White (#FFFFFF) for corporate

## Verification
1. Open the .pptx and verify slide count and order
2. Check text rendering on all slides (no overflow)
3. Verify tables and charts display correctly
4. Confirm images are embedded and visible
5. Check font sizes meet minimum requirements
