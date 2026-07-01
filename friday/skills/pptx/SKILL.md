---
name: pptx
description: Use this skill any time a PowerPoint presentation (.pptx) is involved
---

# Skill: PPTX — Professional PowerPoint Presentation Design

## Overview
FRIDAY uses python-pptx to create production-grade slide decks. **Use `create_pptx()` in `tools_flat.py` for high-level slide creation.** For custom layouts, advanced shape manipulation, or template-based decks, use python-pptx directly.

Every slide is 13.333″×7.5″ (widescreen 16:9). Design each slide as if it will be projected in a boardroom — generous whitespace, strong typography, cohesive palette.

## QUALITY CRITICAL — READ BEFORE WRITING CODE

YOU ARE A PRESENTATION DESIGNER. Build every slide deck as if it will be projected in a boardroom to senior executives. Clarity, narrative flow, and back-of-the-room readability are non-negotiable. Every slide is an exercise in both layout design AND copywriting.

### EXACT SLIDE BLUEPRINT (6 slides minimum)

Every deck MUST have 6+ slides with this EXACT structure:

**Slide 1 - Title**: Dark gradient bg (#0a0a2e to #001a4e), title 40pt bold white, subtitle 24pt accent (#00d4ff), accent line (2pt #00d4ff, 6cm wide, centered below title), date 12pt gray at bottom-right, slide number bottom-left. NO header/footer on title slide.

**Slide 2 - Agenda/Overview**: Light bg (#F1EFE8), title 32pt bold #0C447C top-left. 4-6 numbered items in two columns, each with icon/shape + text 18pt #333333. Current section highlighted in #378ADD. Footer: slide number, date, presentation title.

**Slide 3 - Data/Table**: Dark bg (#0C447C) or white bg. Table with blue header row (#378ADD bg, white text bold 16pt, center aligned). Data rows: 14pt #333333, alternating colors (#F1EFE8 / #FFFFFF). Column widths proportional. Title above table in 28pt. Source citation below in 10pt gray.

**Slide 4 - Chart/Visual**: White bg. Embedded matplotlib chart (bar chart for comparisons, pie for distribution, line for trends). Chart must have: title 18pt bold, axis labels 12pt, data labels on bars/points, legend bottom-right. Chart colors match theme palette. Chart sized to fill content area (8in x 4.5in). Source note below.

**Slide 5 - Key Insights**: Dark bg (#0a0a2e). 3-4 KPI cards in a grid, each with: big number 44pt bold #00d4ff, label 16pt #e0e0e0, small icon above. Separator lines between cards. Bottom: key takeaway text 18pt italic.

**Slide 6 - Closing**: Dark gradient bg matching title slide. Large "Thank You" 48pt white bold centered. Contact info: name, email 16pt #888780. Company name 14pt #5F5E5A. Consistent branding with slide 1.

### TYPE SCALE (explicitly set EVERY font size — never use defaults)
- Title text: 36-44pt bold
- Slide title: 28-32pt bold  
- Subtitle: 24pt semibold
- Body text: 18pt regular (14pt minimum absolute floor)
- Table header: 16pt bold
- Table data: 14pt regular
- Caption/source: 10-12pt regular
- Slide number: 10pt
- KPI numbers: 44pt bold

### COLOR THEME RULES
Pick ONE theme and apply to ALL slides consistently:
- **Dark Tech**: bg #0a0a2e, title #ffffff, body #e0e0e0, accent #00d4ff, secondary #0066ff
- **Professional Blue**: bg #0C447C, title #ffffff, body #E6F1FB, accent #378ADD, secondary #185FA5  
- **Corporate Teal**: bg #04342C, title #E1F5EE, body #9FE1CB, accent #1D9E75, secondary #0F6E56
- **Modern Purple**: bg #26215C, title #EEEDFE, body #CECBF6, accent #7F77DD, secondary #534AB7

MAX 2 fonts per deck. Preferred: Calibri (headings) + Calibri Light (body). NEVER default fonts without specifying size/color.

### EVERY SLIDE MUST HAVE
- Custom background (gradient, solid color, or image) — ZERO white/blank backgrounds
- Slide transition (fade 500ms or push 400ms — apply to ALL slides via loop)
- Slide number (bottom-right, 10pt gray)
- Meaningful title (no empty titles, no "Slide 2")
- Consistent margins (left/right 0.8in, top 0.5in, bottom 0.75in)

### ANTI-PATTERNS — OUTPUTS THAT GET REJECTED
- Single table on white background with no title or theme
- Empty slides, placeholder text, or default "Click to add title"
- Default black text (#000000) on white — use dark gray (#333333) or theme color
- NO transitions between slides
- Tables without colored headers or alternating rows
- Missing slide numbers, dates, or source citations
- Charts without data labels, titles, or legends
- Inconsistent theming (different colors/fonts each slide)
- Text smaller than 14pt (except footers at 10pt)
- Content that doesn't fill the slide (large empty areas)
- Using shapes to fake charts instead of proper CategoryChartData

## Triggers
- "make a presentation", "create slides", "slide deck", "pitch deck", "PowerPoint", "keynote"
- "presentation template", "slide master", "convert report to slides"

## Libraries
- **python-pptx** — primary library for creating and manipulating .pptx files
- **Pillow (PIL)** — image preprocessing (resize, crop, convert formats) before embedding
- **matplotlib** / **plotly** — chart generation, rendered to PNG/SVG then embedded
- **cairosvg** — SVG-to-PNG conversion for chart integration

## Design System

### Type Scale (applied in Points for pptx)
| Role | Size | Weight | Tracking |
|------|------|--------|----------|
| Slide title | 36pt | Bold | -5% |
| Section header / subtitle | 28pt | SemiBold | 0% |
| Body text | 18pt | Regular | 0% |
| Small / caption | 14pt | Regular | +2% |
| Data / KPI numbers | 44pt | Bold | -10% |
| Chart label | 14pt | Regular | 0% |
| Table header | 16pt | Bold | +5% |
| Table body | 14pt | Regular | 0% |
| Footer / page number | 12pt | Light | 0% |

**Font size floor: 14pt minimum for content text, 12pt for footers and page numbers ONLY.** Always set size explicitly — never rely on defaults.

Maximum 2 fonts per deck. Preferred pair: **Calibri** (headings) + **Calibri Light** (body) or **Segoe UI** throughout. For branded decks, use the company typeface.

### Color Ramps (9 ramps, 7 stops each)
Each ramp follows a consistent naming scheme (50 = lightest, 900 = darkest). Use these for all slide elements.

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
- **Semantic**: Blue → info/reference, Green → success/positive, Amber → warning/caution, Red → error/negative
- **Theme**: Purple/Teal/Coral → general categories, category headers
- **Data charts**: use 4-6 distinct hues (Blue 400, Teal 400, Coral 400, Amber 400, Green 400, Purple 400)
- **Text on colored backgrounds**: use 800/900 stops from the **same** ramp for contrast
- **Max 3 colors per slide** (not counting images or charts)
- **Dark slides** (#050510 bg): title = 50 stop, body = 100/200 stop
- **Light slides** (#FFFFFF bg): title = 800/900 stop, body = 600 stop
- **Links**: always Blue 400 (#378ADD) with underline

### Layout Grid
All slides follow a modular grid system:
- **Columns**: 12-column grid, each column = 0.9″ wide, gutter = 0.2″
- **Rows**: 6-row grid, each row = 0.95″ tall, gutter = 0.15″
- **Margins**: Left/Right = 0.8″, Top = 0.5″, Bottom = 0.75″
- **Content area**: 11.733″ × 6.25″
- **Safe zone**: keep all content within 0.3″ of margins

```
┌─────────────────────────────────────┐
│  ┌─ Padding Top (0.5″)            │
│  │  TITLE (36pt, top-left aligned)  │
│  │  Subtitle / meta (28pt, dimmer)  │
│  │  ──── divider line ────          │
│  │                                  │
│  │  Content area (center-weighted)  │
│  │  • Bullets / text               │
│  │  • Charts / tables / images     │
│  │                                  │
│  └─ Padding Bottom (0.75″)         │
│     Footer / page numbers (small)  │
└─────────────────────────────────────┘
```

## Complete Slide Type Catalog

### 1. Title Slide (Layout 5)
Dark background with accent color. Big title (36-44pt), subtitle (24pt), date/metadata.
- Background: Blue 800 or Purple 800
- Title: White, 40pt, bold, centered
- Subtitle: Blue 100 or Purple 100, 24pt
- Accent line: 2pt horizontal rule below title (Teal 400 or Coral 400)
- Optional: company logo top-left, date bottom-right

### 2. Section Header (Layout 6)
Full-bleed background color, centered title (48pt), subtitle-liner.
- Used to divide deck into major sections
- Large centered title, smaller descriptive text below
- Background: solid color or gradient from ramp
- No content area — purely transitional

### 3. Content Slide (Layout 1)
Standard title + body with bullets, tables, or images.
- Title: 32pt, bold, dark color
- Body: 18pt with proper hierarchy
- Bullets: nested (primary, secondary) with consistent indentation
- Max 6 bullets, 10 words each

### 4. Two-Content Slide (Layout 3)
Equal columns for comparison or text + visual.
- Left column: text or list
- Right column: image, chart, or table
- Vertical divider line between columns (Gray 200, 1pt)
- Column widths: 48% each, 4% gutter

### 5. Comparison Slide (Layout 4)
Two columns with headers for A/B comparison.
- Column headers with icon/color coding
- Pro/con or before/after format
- Equal column widths

### 6. Blank Slide (Layout 6)
For full-bleed images, full-screen charts, quote slides, custom layouts.
- No predefined placeholders
- Full control over positioning
- Use for hero images, data dashboards, quote slides

### 7. Chart Slide
Dedicated slide with embedded chart. Always use `CategoryChartData` — never approximate charts with geometric shapes.
- Chart centered in content area
- Title above chart
- Legend right or bottom
- Source citation below at 12pt

### 8. Quote Slide
Large centered quote text (28pt italic), attribution below (18pt). Dark bg + accent left border.
- Quote in quotation marks, 28pt, italic, light color on dark bg
- Attribution: 18pt, regular, accent color
- Left accent bar: 4pt thick, accent color

### 9. Data / KPI Slide
Big numbers (44pt) with small labels (14pt) in a grid layout.
- Use Green 400 for positive, Red 400 for negative
- Grid: 2×2 or 4×1 depending on slide dimensions
- Number: 44pt bold, label: 14pt Gray 400

### 10. Image-Left / Text-Right
Layout with image occupying left 40%, text on right 60%.
- Image fills left portion
- Title and bullets on right
- Clean divider between sections

### 11. Agenda / Overview Slide
List of sections with visual progress indicators.
- Numbered or icon-based section markers
- Current/highlighted section in accent color
- Past sections in gray

### 12. Thank You / Closing Slide
Minimal design with thank you message and contact info.
- Large "Thank You" (44pt)
- Contact details: name, email, phone
- Company logo and website
- Dark background preferred

## Comprehensive python-pptx API Reference

### Core Objects
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTOSIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR_TYPE
from pptx.chart.data import CategoryChartData, ChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn, nsdecls
from pptx.oxml import parse_xml
from pptx.table import Table, _Cell, _Row, _Column
from pptx.shapes.autoshape import Shape
from pptx.shapes.picture import Picture
from pptx.shapes.group import GroupShapes
from pptx.slide import Slide, SlideLayout, SlideMaster
```

### Presentation Setup
```python
# Widescreen 16:9
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Standard 4:3
# prs.slide_width = Inches(10)
# prs.slide_height = Inches(7.5)

# Custom size
# prs.slide_width = Cm(33.867)
# prs.slide_height = Cm(19.05)
```

### Utility Functions
```python
def hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def rgb_to_hex(color: RGBColor) -> str:
    return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

def set_shape_fill(shape, hex_color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = hex_to_rgb(hex_color)

def set_shape_outline(shape, hex_color, width=Pt(1)):
    shape.line.color.rgb = hex_to_rgb(hex_color)
    shape.line.width = width

def add_rounded_rect(slide, left, top, width, height, radius=Inches(0.15)):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.adjustments[0] = radius / min(width, height)
    return shape
```

### Slide Layouts
The default template has 9 built-in layouts. Access by index:
```python
# 0: Title Slide (centered title + subtitle)
# 1: Title and Content (title + content placeholder)
# 2: Section Header (section title + text)
# 3: Two Content (title + two content placeholders)
# 4: Comparison (title + two content + two subheaders)
# 5: Title Only (title placeholder only)
# 6: Blank (no placeholders)
# 7: Content with Caption
# 8: Picture with Caption

# Safe choices for custom builds:
# Layout 5 (Title Only) or Layout 6 (Blank) — minimal interference
slide = prs.slides.add_slide(prs.slide_layouts[6])
```

### Placeholder System
```python
# Available placeholders vary by layout. Common indices:
# idx=0: Title placeholder
# idx=1: Body/content placeholder (on layout 1, 3, 4)
# idx=2: Second content placeholder (on layout 3, 4)
# idx=3: Left subheader (on layout 4)
# idx=4: Right subheader (on layout 4)

# Populate placeholder
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "Slide Title"

# Check if content placeholder exists
for ph in slide.placeholders:
    if ph.placeholder_format.idx == 1:
        ph.text = "Content text"
        ph.font.size = Pt(18)

# Detect placeholder types
for ph in slide.placeholders:
    ph_type = ph.placeholder_format.type  # TITLE, BODY, etc.
```

### Text Frames and Paragraphs
```python
# Text frame basics
txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(4))
tf = txBox.text_frame
tf.word_wrap = True
tf.auto_size = MSO_AUTOSIZE.NONE  # Prevent auto-shrinking

# Single paragraph
p = tf.paragraphs[0]
p.text = "First paragraph"
p.font.size = Pt(18)
p.font.color.rgb = RGBColor(51, 51, 51)
p.alignment = PP_ALIGN.LEFT
p.space_after = Pt(12)
p.space_before = Pt(6)
p.line_spacing = Pt(24)  # Fixed line spacing

# Multiple paragraphs
tf.clear()
items = ["First point", "Second point", "Third point"]
for i, item in enumerate(items):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = item
    p.level = 0  # Indentation level (0-9)
    p.font.size = Pt(18)
    p.font.color.rgb = hex_to_rgb("#333333")
    p.space_after = Pt(8)
    p.space_before = Pt(4)

# Nested bullets
p1 = tf.paragraphs[0]
p1.text = "Main point"
p1.level = 0
p2 = tf.add_paragraph()
p2.text = "Sub point"
p2.level = 1  # Indented
p2.font.size = Pt(16)  # One step smaller for nested

# Paragraph with multiple runs (mixed formatting)
p = tf.paragraphs[0]
run1 = p.add_run()
run1.text = "Bold text "
run1.font.bold = True
run1.font.size = Pt(18)
run2 = p.add_run()
run2.text = "normal text"
run2.font.size = Pt(18)

# Run-level formatting
run = p.add_run()
run.text = "Formatted text"
run.font.name = "Calibri"
run.font.size = Pt(18)
run.font.bold = True
run.font.italic = False
run.font.underline = True  # Use sparingly
run.font.color.rgb = RGBColor(55, 138, 221)
# Strikethrough
run.font.strike = True  # MMSO_STRIKE.SINGLE_STRIKE
# Superscript/subscript
# run.font.superscript = True
# run.font.subscript = True
```

### Table Creation and Styling
```python
# Create table
rows, cols = 5, 4
table_shape = slide.shapes.add_table(rows, cols, Inches(1), Inches(2), Inches(10), Inches(4))
table = table_shape.table

# Set column widths
table.columns[0].width = Inches(2.5)
table.columns[1].width = Inches(2.5)
table.columns[2].width = Inches(2.5)
table.columns[3].width = Inches(2.5)

# Header row styling
def style_header_cell(cell, text):
    cell.text = text
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    # Background
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="378ADD"/>')
    cell._tc.get_or_add_tcPr().append(shading)
    for paragraph in cell.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        for run in paragraph.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(16)
            run.font.name = "Calibri"

# Data cell styling
def style_data_cell(cell, text, font_size=Pt(14)):
    cell.text = text
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for paragraph in cell.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        for run in paragraph.runs:
            run.font.size = font_size
            run.font.name = "Calibri"
            run.font.color.rgb = hex_to_rgb("#333333")

# Apply alternating row colors
def apply_alternating_rows(table, start_row=1, color1="F1EFE8", color2="FFFFFF"):
    for row_idx in range(start_row, len(table.rows)):
        bg = color1 if (row_idx - start_row) % 2 == 0 else color2
        for col_idx in range(len(table.columns)):
            cell = table.cell(row_idx, col_idx)
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>')
            cell._tc.get_or_add_tcPr().append(shading)

# Merge cells
table.cell(0, 0).merge(table.cell(0, 3))  # Merge all header cells

# Set row height
table.rows[0].height = Inches(0.6)

# Cell margins
cell.margin_left = Inches(0.1)
cell.margin_right = Inches(0.1)
cell.margin_top = Inches(0.05)
cell.margin_bottom = Inches(0.05)
```

### Chart Integration
```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION

chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Revenue', (100, 200, 300, 400))
chart_data.add_series('Cost', (60, 120, 180, 240))

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,  # Or: COLUMN_STACKED, BAR_CLUSTERED, LINE_MARKERS,
                                      # PIE, PIE_EXPLODED, DOUGHNUT, RADAR, XY_SCATTER,
                                      # AREA, STOCK_HLC
    Inches(0.5), Inches(2), Inches(8), Inches(4.5), chart_data
)
chart = chart_frame.chart

# Chart styling
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(12)

# Title
chart.has_title = True
chart.chart_title.has_text_frame = True
chart.chart_title.text_frame.text = "Quarterly Revenue vs Cost"
chart.chart_title.text_frame.paragraphs[0].font.size = Pt(16)
chart.chart_title.text_frame.paragraphs[0].font.bold = True

# Chart style (1-48)
chart.chart_style = 2

# Series formatting
series = chart.series[0]
series.format.fill.solid()
series.format.fill.fore_color.rgb = hex_to_rgb("#378ADD")

# Data labels
plot = chart.plots[0]
plot.has_data_labels = True
data_labels = plot.data_labels
data_labels.font.size = Pt(11)
data_labels.number_format = '#,##0'
data_labels.position = XL_LABEL_POSITION.OUTSIDE_END

# Axis styling
value_axis = chart.value_axis
value_axis.has_title = True
value_axis.axis_title.text_frame.text = "Amount ($)"
value_axis.axis_title.text_frame.paragraphs[0].font.size = Pt(12)
value_axis.major_gridlines.format.line.color.rgb = hex_to_rgb("#D3D1C7")

category_axis = chart.category_axis
category_axis.tick_labels.font.size = Pt(12)

# Pie chart with data labels
chart_data2 = CategoryChartData()
chart_data2.categories = ['Product A', 'Product B', 'Product C', 'Product D']
chart_data2.add_series('Share', (35, 30, 20, 15))
chart_frame2 = slide.shapes.add_chart(
    XL_CHART_TYPE.PIE, Inches(0.5), Inches(2), Inches(6), Inches(4.5), chart_data2
)
chart2 = chart_frame2.chart
chart2.has_legend = True
chart2.legend.position = XL_LEGEND_POSITION.RIGHT
plot2 = chart2.plots[0]
plot2.has_data_labels = True
data_labels2 = plot2.data_labels
data_labels2.number_format = '0%"'
data_labels2.position = XL_LABEL_POSITION.OUTSIDE_END
data_labels2.font.size = Pt(12)
```

### Matplotlib Chart Integration
```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import io
from PIL import Image

# Generate chart
fig, ax = plt.subplots(figsize=(10, 5))
categories = ['Q1', 'Q2', 'Q3', 'Q4']
values = [100, 200, 300, 400]
bars = ax.bar(categories, values, color='#378ADD', edgecolor='white', linewidth=0.5)
ax.set_title('Quarterly Revenue', fontsize=14, fontweight='bold', color='#333333', pad=12)
ax.set_xlabel('Quarter', fontsize=11, color='#666666')
ax.set_ylabel('Revenue ($)', fontsize=11, color='#666666')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')
ax.tick_params(colors='#666666', labelsize=10)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'${height}K', ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()

# Save to bytes
img_buf = io.BytesIO()
plt.savefig(img_buf, format='png', dpi=200, bbox_inches='tight', transparent=False)
plt.close()
img_buf.seek(0)

# Embed in slide
slide.shapes.add_picture(img_buf, Inches(1), Inches(2), Inches(8), Inches(4.5))

# Or save to file first
# plt.savefig('chart.png', dpi=200, bbox_inches='tight')
# slide.shapes.add_picture('chart.png', Inches(1), Inches(2), Inches(8), Inches(4.5))
```

### Image Handling
```python
from PIL import Image as PILImage

# Insert image with specific dimensions
pic = slide.shapes.add_picture('image.jpg', Inches(1), Inches(2), Inches(5), Inches(4))

# Insert with proportional scaling
from pptx.util import Inches
pic = slide.shapes.add_picture('image.jpg', Inches(1), Inches(2))
# Width/height will be image's native size; use Inches() to override

# Image positioning modes
pic.left = Inches(0.5)
pic.top = Inches(1.5)
pic.width = Inches(6)
pic.height = Inches(4.5)

# Crop image (using pillow preprocessing)
img = PILImage.open('source.jpg')
# Crop to center square
width, height = img.size
new_size = min(width, height)
left = (width - new_size) // 2
top = (height - new_size) // 2
img_cropped = img.crop((left, top, left + new_size, top + new_size))
img_cropped.save('cropped.jpg', quality=95)

pic = slide.shapes.add_picture('cropped.jpg', Inches(1), Inches(2), Inches(4), Inches(4))

# Image effects via PIL
from PIL import ImageEnhance, ImageFilter

# Adjust brightness
enhancer = ImageEnhance.Brightness(img)
img_bright = enhancer.enhance(0.7)
img_bright.save('darkened.jpg', quality=95)

# Add shadow by composite
from PIL import ImageFilter, ImageDraw
shadow = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(shadow)
draw.rectangle([0, 0, img.width, img.height], fill=(0, 0, 0, 40))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=5))
# Composite is complex; simpler to handle shadow natively

# Embedded vs linked images
# python-pptx always embeds images — no need for setting
# Use add_picture — never set external references manually

# Supported formats: .png, .jpg, .jpeg, .gif, .bmp, .tiff
# For transparent backgrounds: use .png with alpha channel
# For photos: use .jpg (smaller file size)
# For vector/logos: convert SVG to PNG at 2x resolution first

# Full-bleed background image
slide = prs.slides.add_slide(prs.slide_layouts[6])
pic = slide.shapes.add_picture('background.jpg', 0, 0, prs.slide_width, prs.slide_height)
# Send to back (move to first position in shape tree)
sp = pic._element
sp.getparent().remove(sp)
slide.shapes._spTree.insert(2, sp)  # After background

# Image compression optimization
from PIL import Image
img = Image.open('large_photo.jpg')
# Resize to slide width max (1920px for 200dpi on 13.333" slide)
max_width = 1920
if img.width > max_width:
    ratio = max_width / img.width
    img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
img.save('optimized.jpg', quality=85, optimize=True)
```

### Shape Manipulation
```python
# Add rectangle
shape = slide.shapes.add_shape(
    MSO_SHAPE.RECTANGLE, Inches(1), Inches(1), Inches(4), Inches(3)
)
shape.fill.solid()
shape.fill.fore_color.rgb = hex_to_rgb("#E6F1FB")
shape.line.color.rgb = hex_to_rgb("#378ADD")
shape.line.width = Pt(1.5)
shape.shadow.inherit = False  # Disable default shadow

# Rounded rectangle
shape = add_rounded_rect(slide, Inches(1), Inches(1), Inches(4), Inches(3), Inches(0.2))
shape.fill.solid()
shape.fill.fore_color.rgb = hex_to_rgb("#EEEDFE")

# Oval / circle
shape = slide.shapes.add_shape(
    MSO_SHAPE.OVAL, Inches(1), Inches(1), Inches(2), Inches(2)
)

# Line
connector = slide.shapes.add_shape(
    MSO_SHAPE.RECTANGLE, Inches(1), Inches(3.5), Inches(10), Inches(0.02)  # Thin rectangle as line
)
connector.fill.solid()
connector.fill.fore_color.rgb = hex_to_rgb("#D3D1C7")
connector.line.fill.background()  # No outline

# Connector (actual line)
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsmap
connector = slide.shapes.add_connector(
    MSO_CONNECTOR_TYPE.STRAIGHT, Inches(1), Inches(1), Inches(5), Inches(1)
)
connector.line.color.rgb = hex_to_rgb("#378ADD")
connector.line.width = Pt(2)

# Freeform shape via XML
from lxml import etree
# Build custom path
nsmap = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
         'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
         'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
# Complex freeform requires direct XML manipulation

# Shape properties
shape.rotation = 45.0  # Degrees clockwise
shape.left = Inches(2)
shape.top = Inches(2)
shape.width = Inches(5)
shape.height = Inches(3)

# Z-order (bring to front / send to back)
# move to end (front)
sp = shape._element
sp.getparent().remove(sp)
slide.shapes._spTree.append(sp)
# move to beginning (back)
sp.getparent().remove(sp)
slide.shapes._spTree.insert(2, sp)
```

### Group Shapes
```python
# python-pptx does not support group shapes directly.
# Workaround: manage shapes individually in a logical group.

# Alternative: use XML manipulation to create group shapes
from lxml import etree

def create_group_shape(slide, name="Group 1"):
    grp_sp = parse_xml(f'''
        <p:grpSpPr {nsdecls("p")} {nsdecls("a")}>
            <a:xfrm>
                <a:off x="0" y="0"/>
                <a:ext cx="0" cy="0"/>
                <a:chOff x="0" y="0"/>
                <a:chExt cx="0" cy="0"/>
            </a:xfrm>
        </p:grpSpPr>
    ''')
    # Create group shape XML element
    nvgrpsppr = parse_xml(f'''
        <p:nvGrpSpPr>
            <p:cNvPr id="0" name="{name}"/>
            <p:cNvGrpSpPr/>
            <p:nvPr/>
        </p:nvGrpSpPr>
    ''')
    grp_sp_element = etree.SubElement(slide.shapes._spTree, 'p:grpSp')
    grp_sp_element.append(nvgrpsppr)
    grp_sp_element.append(grp_sp)
    return grp_sp_element

# Then add child shapes under the group element
# Note: This is advanced XML-level manipulation
```

### Video and Audio Embedding
```python
# Video
movie = slide.shapes.add_movie(
    'video.mp4',  # Path to video file
    Inches(1), Inches(1.5), Inches(8), Inches(4.5),
    poster_frame_image='poster.jpg'  # Optional poster image
)
# Set video options (via XML)
video_element = movie._element
# Set playback options:
# Loop: <p:video> -> <a:videoFile r:link="..."/>
# Full screen: <p:extLst>

# Audio
# Audio embedding is not directly supported by python-pptx.
# Workaround: add audio via XML or use a clickable shape.
```

### Animation and Transitions
```python
# Slide transition (set on slide XML)
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn

def set_slide_transition(slide, transition_type='fade', duration=500):
    """
    transition_type: 'fade', 'push', 'wipe', 'split', 'uncover', 'cover', 'random'
    duration in milliseconds
    """
    transition = parse_xml(f'''
        <p:transition {nsdecls("p")} dur="{duration}" advTm="{duration}">
            <p:{transition_type}/>
        </p:transition>
    ''')

    # Remove existing transition
    existing = slide._element.find(qn('p:transition'))
    if existing is not None:
        slide._element.remove(existing)
    slide._element.append(transition)

# Set for all slides
for slide in prs.slides:
    set_slide_transition(slide, 'fade', 500)

# Animation effects (requires XML manipulation)
# python-pptx doesn't have a high-level API for animations
# Use the following XML approach for basic animations:

def add_fly_in_animation(shape, slide):
    """Add 'fly in from bottom' animation to a shape"""
    timing = slide._element.find(qn('p:timing'))
    if timing is None:
        timing = parse_xml(f'<p:timing {nsdecls("p")}/>')
        # Find correct insertion point in XML tree
        # This is complex and version-dependent

# Animation XML is complex. For full control, use a library like
# python-pptx-template or direct XML manipulation.
```

### Slide Master and Layout Customization
```python
# Access slide master
slide_master = prs.slide_masters[0]

# Access layouts
layouts = slide_master.slide_layouts
for i, layout in enumerate(layouts):
    print(f"Layout {i}: {layout.name}")

# Customize layout (advanced XML)
layout = slide_master.slide_layouts[6]  # Blank
# Modify layout background
layout.background.fill.solid()
layout.background.fill.fore_color.rgb = hex_to_rgb("#FFFFFF")

# Custom slide master background
slide_master.background.fill.solid()
slide_master.background.fill.fore_color.rgb = hex_to_rgb("#FFFFFF")

# Add placeholder to a layout (requires XML manipulation)
# For most cases, use default layouts and add shapes programmatically
```

### Template System
```python
# Method 1: Copy template file
import shutil
shutil.copy2('template.pptx', 'output.pptx')
prs = Presentation('output.pptx')
# Now modify slides in prs

# Method 2: Save and reload
prs.save('deck.pptx')
prs2 = Presentation('deck.pptx')  # Reload to preserve slide master

# Method 3: Extract and reuse slide master
def apply_template(source_path, target_prs):
    """Copy slide master from source to target presentation"""
    # This requires deep XML copying — complex but possible
    source_prs = Presentation(source_path)
    # Copy slideMaster, theme, etc. from source to target
    # Not straightforward with python-pptx
    pass

# Practical approach: always start from a template
def create_from_template(template_path, output_path):
    shutil.copy2(template_path, output_path)
    prs = Presentation(output_path)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs
```

### Font Embedding Strategy
```python
# python-pptx does not support font embedding natively.
# Workaround: use widely available fonts

# Safe fonts for cross-platform rendering:
SAFE_FONTS = ['Calibri', 'Calibri Light', 'Segoe UI', 'Arial', 'Times New Roman',
              'Helvetica', 'Verdana', 'Tahoma', 'Georgia', 'Cambria']

def set_font_safe(run, font_name='Calibri', size=Pt(18)):
    """Set font with fallback strategy"""
    run.font.name = font_name
    # Set east-asian font for CJK support
    rPr = run._r.get_or_add_rPr()
    ea_font = parse_xml(f'<a:ea {nsdecls("a")} typeface="Calibri"/>')
    # This ensures CJK characters render with fallback
    cs_font = parse_xml(f'<a:cs {nsdecls("a")} typeface="Calibri"/>')

# Font fallback note:
# PowerPoint will fallback to system fonts if the specified font is unavailable.
# Always test on target machine. For guaranteed rendering, use common fonts.
```

### Export to PDF / Images
```python
# python-pptx does not export to PDF/images natively.
# Use COM interop on Windows or LibreOffice on Linux/Mac:

# Windows COM (PowerPoint must be installed)
def pptx_to_pdf(input_path, output_path):
    import win32com.client
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = False
    deck = powerpoint.Presentations.Open(input_path)
    deck.SaveAs(output_path, 32)  # 32 = ppSaveAsPDF
    deck.Close()
    powerpoint.Quit()

# LibreOffice (cross-platform)
def pptx_to_pdf_libre(input_path, output_path):
    import subprocess
    cmd = ['soffice', '--headless', '--convert-to', 'pdf', '--outdir',
           os.path.dirname(output_path), input_path]
    subprocess.run(cmd, check=True)

# Export slides as images (LibreOffice)
def pptx_to_images(input_path, output_dir):
    import subprocess, os
    cmd = ['soffice', '--headless', '--convert-to', 'png',
           '--outdir', output_dir, input_path]
    subprocess.run(cmd, check=True)
```

## Advanced Design Patterns

### Gradient Background
```python
# Gradient fill via XML
from lxml import etree

def add_gradient_background(slide, color1="#0C447C", color2="#042C53"):
    bg = slide.background
    bg._element.find(qn('p:bgPr')).remove(
        bg._element.find(qn('p:bgPr')).find(qn('a:solidFill'))
    )
    grad = parse_xml(f'''
        <a:gradFill {nsdecls("a")} rotWithShape="1">
            <a:gsLst>
                <a:gs pos="0">
                    <a:srgbClr val="{color1.lstrip('#')}"/>
                </a:gs>
                <a:gs pos="100000">
                    <a:srgbClr val="{color2.lstrip('#')}"/>
                </a:gs>
            </a:gsLst>
            <a:lin ang="2700000" scaled="0"/>
        </a:gradFill>
    ''')
    bg._element.find(qn('p:bgPr')).append(grad)
```

### Shadow Effects
```python
# Add shadow to a shape
def add_shadow(shape, color="#000000", blur_radius=914400, offset_x=91440, offset_y=91440):
    """Add drop shadow to shape. Values in EMU. 914400 EMU = 1pt"""
    spPr = shape._element.find(qn('p:spPr'))
    if spPr is None:
        spPr = shape._element.find(qn('a:spPr'))

    shadow = parse_xml(f'''
        <a:effectLst {nsdecls("a")}>
            <a:outerShdw blurRad="{blur_radius}" dist="0" dir="2700000"
                         algn="tl" rotWithShape="0">
                <a:srgbClr val="{color.lstrip('#')}">
                    <a:alpha val="50000"/>
                </a:srgbClr>
            </a:outerShdw>
        </a:effectLst>
    ''')
    existing = spPr.find(qn('a:effectLst'))
    if existing is not None:
        spPr.remove(existing)
    spPr.append(shadow)
```

### Accent Divider Line
```python
def add_accent_line(slide, top=Inches(1.6), color="#378ADD", width=Inches(2)):
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), top, width, Pt(3)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = hex_to_rgb(color)
    line.line.fill.background()
    return line
```

### Slide Number
```python
def add_slide_number(slide, number, total=None):
    text = f"{number}" if total is None else f"{number} / {total}"
    txBox = slide.shapes.add_textbox(
        Inches(11.5), Inches(7.0), Inches(1.5), Inches(0.4)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(10)
    p.font.color.rgb = hex_to_rgb("#888780")
    p.alignment = PP_ALIGN.RIGHT
```

### Date and Logo
```python
def add_date(slide, date_str="July 2026"):
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(4), Inches(0.4))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = date_str
    p.font.size = Pt(10)
    p.font.color.rgb = hex_to_rgb("#888780")

def add_logo(slide, logo_path, left=Inches(0.5), top=Inches(0.3), width=Inches(1.5)):
    pic = slide.shapes.add_picture(logo_path, left, top, width)
    # Maintain aspect ratio
    return pic
```

## Integration Patterns

### With Chart Skill
When generating charts with matplotlib, pass chart parameters to generate high-quality PNG:
```python
def generate_chart_image(chart_type, data, output_path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    # ... chart rendering code ...
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path

chart_path = generate_chart_image('bar', data, 'temp_chart.png')
slide.shapes.add_picture(chart_path, Inches(1), Inches(2), Inches(8), Inches(4.5))
```

### With SVG Skill
Convert SVG to PNG for embedding:
```python
import cairosvg

def svg_to_png(svg_path, png_path, scale=2):
    with open(svg_path, 'rb') as f:
        svg_data = f.read()
    cairosvg.svg2png(bytestring=svg_data, write_to=png_path, scale=scale)
    return png_path
```

### With Word Skill
Transfer content from DOCX to PPTX by extracting paragraphs:
```python
from docx import Document
doc = Document('report.docx')
# Extract headings and body for slide titles and content
```

## Troubleshooting

### Missing Fonts
- **Symptom**: PowerPoint shows "missing font" warning on open
- **Cause**: Using uncommon fonts not installed on target machine
- **Solution**: Only use SAFE_FONTS list above. For brand fonts, embed manually.
- **Fallback**: PowerPoint will auto-substitute, but layout may shift

### Image Format Issues
- **Symptom**: Image doesn't display or causes corruption
- **Cause**: Unsupported format or corrupted image file
- **Solution**: Convert to PNG or JPEG before embedding
- **Fix**: Use PIL to re-save image: `Image.open('bad.svg').convert('RGB').save('fixed.png')`

### Chart Data Not Displaying
- **Symptom**: Chart shows placeholder, no data
- **Cause**: Chart data not properly populated
- **Solution**: Debug with `print(chart_data.categories)` and `print(chart_data.series_data)`
- **Fix**: Ensure all series have same number of data points as categories

### File Size Too Large
- **Cause**: High-resolution images, many slides, embedded video
- **Solution**:
  - Resize images to max 1920px width before embedding
  - Use JPEG compression quality 85
  - For video, link instead of embed (COM API required)
- **Target**: Under 5MB for 20-slide deck without video

### Corrupted PPTX
- **Cause**: Manual XML manipulation errors, invalid shape references
- **Solution**: Always validate with `prs.slides`, `slide.shapes` iterators
- **Recovery**: Rename .pptx to .zip, check `ppt/slides/slide1.xml` for errors
- **Fix**: Remove invalid XML elements and re-zip

### Text Overflow
- **Symptom**: Text clipped or overflowing text box
- **Solution**: Set `tf.word_wrap = True`, check available height
- **Fix**: Reduce font size or split content across multiple slides

## Quality Checklist

### Content Quality
- [ ] Every slide has a meaningful title
- [ ] No default placeholder text remains
- [ ] Content is scannable — bullet points, not paragraphs
- [ ] Max 6 bullets per slide, max 10 words per bullet
- [ ] Data is accurate and sourced
- [ ] All charts have titles and legends
- [ ] All images have alt text consideration

### Design Quality
- [ ] Font sizes meet minimum (14pt for content, 12pt for footers)
- [ ] No more than 2 fonts per deck
- [ ] Max 3 colors per slide
- [ ] Text has sufficient contrast (4.5:1 minimum ratio)
- [ ] Body text is left-aligned (never centered)
- [ ] No ALL CAPS for more than 3 words
- [ ] Consistent spacing and margins throughout
- [ ] No overlapping shapes or text boxes
- [ ] Images are not stretched — aspect ratio maintained

### Technical Quality
- [ ] Slide dimensions set explicitly (13.333×7.5 for widescreen)
- [ ] Images are embedded (not linked)
- [ ] Charts use proper `CategoryChartData` (not geometric shapes)
- [ ] Tables have styled header rows
- [ ] No pure black (#000) or pure white (#FFF) for body text
- [ ] File size is reasonable for content (< 5MB typical)
- [ ] Fonts are widely available or embedded

### Verification Process
1. Open the .pptx and verify slide count and order matches outline
2. Check text rendering — no overflow, no clipping
3. Verify tables and charts display correctly — check legends, titles, data labels
4. Confirm images are embedded (not linked)
5. Check font sizes meet minimum (14pt for everything except footers at 12pt)
6. Verify color contrast on projected slides
7. Check that each slide follows the composition blueprint
8. Verify no overlapping shapes or text boxes
9. After editing existing slides, verify no collateral damage to adjacent content
10. Check file doesn't exceed size limits
11. Verify hyperlinks work (if any)
12. Print test: convert to PDF and verify page layout

## Critical Rules — What to AVOID
- NEVER leave default placeholder text
- NEVER use font sizes smaller than 14pt (12pt for footers only)
- NEVER use more than 2 fonts or 3 colors per slide
- NEVER overlap shapes or text boxes
- NEVER embed external images as links — always embed
- NEVER skip setting explicit slide dimensions
- NEVER put too much text on a single slide (max 6 bullets, 10 words each)
- NEVER use rainbow colors for data — use semantic color mapping
- NEVER use black (#000) or pure white (#FFF) for body text
- NEVER center-align body text — always left-align
- NEVER use ALL CAPS for more than 3 words
- NEVER use geometric shapes to approximate charts — always use proper chart API
- NEVER delete-and-rebuild slides — edit in place to preserve comments, bookmarks, objects
- NEVER build 10+ slides without first proposing storyline and getting approval
- NEVER use `pypdf` for any PDF work
- NEVER embed videos directly — prefer linking for large files
- NEVER assume slide layout indices are same across templates
- NEVER modify slide master without testing on all slide types
- NEVER save to the same file path while Presentation object is open
