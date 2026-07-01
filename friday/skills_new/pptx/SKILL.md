---
name: pptx
location: friday/skills/pptx/SKILL.md
trigger: deck, slides, presentation, pitch, .pptx, speaker notes, template
platform: Windows (FRIDAY host machine)
---

# PPTX — FRIDAY Playbook (Full)

## QUALITY CRITICAL — READ BEFORE WRITING CODE

Build every deck as if it will be projected in a boardroom to senior
executives. Every slide is both a layout exercise and a copywriting
exercise — clarity and back-of-the-room readability are non-negotiable.

### Exact slide blueprint (6 slides minimum, for a standard deck)

**Slide 1 — Title**: Dark gradient bg (`#0a0a2e` → `#001a4e`). Title 40pt
bold white. Subtitle 24pt accent `#00d4ff`. Accent line 2pt `#00d4ff`, 6cm
wide, centered below title. Date 12pt gray bottom-right. Slide number
bottom-left. No header/footer.

**Slide 2 — Agenda**: Light bg `#F1EFE8`. Title 32pt bold `#0C447C`
top-left. 4-6 numbered items in two columns, icon/shape + 18pt `#333333`
text each. Footer: slide number, date, deck title.

**Slide 3 — Data/Table**: Dark bg `#0C447C` or white. Table header row
`#378ADD` bg, white bold 16pt centered. Data rows 14pt `#333333`,
alternating `#F1EFE8`/white. Proportional column widths. Title above table
28pt. Source citation below, 10pt gray.

**Slide 4 — Chart/Visual**: White bg. Embedded matplotlib chart (see §6 —
use image embedding, not native scatter/complex charts). Chart: title 18pt
bold, axis labels 12pt, data labels, legend bottom-right, sized ~8×4.5in.
Source note below.

**Slide 5 — Key Insights**: Dark bg `#0a0a2e`. 3-4 KPI cards in a grid:
big number 44pt bold `#00d4ff`, label 16pt `#e0e0e0`, small icon above.
Separator lines between cards. Bottom: takeaway text 18pt italic.

**Slide 6 — Closing**: Dark gradient matching slide 1. "Thank You" 48pt
white bold centered. Contact info 16pt `#888780`. Company name 14pt
`#5F5E5A`.

### Type scale (set explicitly — never rely on defaults)

| Role | Size | Weight |
|---|---|---|
| Title text (slide 1) | 36-44pt | Bold |
| Slide title | 28-32pt | Bold |
| Subtitle | 24pt | SemiBold |
| Body text | 18pt regular | (14pt absolute floor) |
| Table header | 16pt | Bold |
| Table data | 14pt | Regular |
| Caption / source | 10-12pt | Regular |
| KPI numbers | 44pt | Bold |
| Slide number | 10pt | — |

### Color theme — pick ONE, apply to every slide

| Theme | Bg | Title | Body | Accent | Secondary |
|---|---|---|---|---|---|
| Dark Tech | `#0a0a2e` | `#ffffff` | `#e0e0e0` | `#00d4ff` | `#0066ff` |
| Professional Blue | `#0C447C` | `#ffffff` | `#E6F1FB` | `#378ADD` | `#185FA5` |
| Corporate Teal | `#04342C` | `#E1F5EE` | `#9FE1CB` | `#1D9E75` | `#0F6E56` |
| Modern Purple | `#26215C` | `#EEEDFE` | `#CECBF6` | `#7F77DD` | `#534AB7` |

Max 2 fonts per deck. Preferred: Calibri (headings) + Calibri Light (body),
or Segoe UI throughout (see §3 safe font list — don't deviate for QA
reliability).

### Every slide must have

- Custom background (gradient, solid, or image) — zero blank white slides
- Slide number (bottom-right, 10pt gray)
- Meaningful title (never "Slide 2" or empty)
- Consistent margins: left/right 0.8in, top 0.5in, bottom 0.75in

### Anti-patterns that get a deck rejected

- Single table on white background with no title/theme
- Default "Click to add title" placeholder text left in
- Pure black `#000000` text on white — use dark gray `#333333` or theme color
- Missing slide numbers, dates, or source citations on data slides
- Charts without data labels, titles, or legends
- Inconsistent theming between slides (different colors/fonts each slide)
- Large empty areas — content should fill the slide's content region

## 0. Environment setup

```powershell
pip install python-pptx matplotlib Pillow
# LibreOffice for headless PDF conversion (verify render)
# or, if PowerPoint is installed, prefer COM-based conversion for fidelity
```

If MS PowerPoint is installed on the host, prefer COM-based export for
verification — matches exactly what the user will see, unlike LibreOffice's
approximate rendering (font substitution differences especially):

```python
import win32com.client
powerpoint = win32com.client.Dispatch("PowerPoint.Application")
deck = powerpoint.Presentations.Open(r"C:\path\output.pptx", WithWindow=False)
deck.SaveAs(r"C:\path\output.pdf", 32)   # 32 = ppSaveAsPDF
deck.Close()
powerpoint.Quit()
```

## 1. Library map

| Task | Library |
|---|---|
| Create from scratch | `python-pptx` |
| Edit existing / template-based | `python-pptx` (load existing .pptx) |
| Read/extract text | `python-pptx` iterate shapes, or `pandoc`/unzip+XML for raw text dump |
| Charts inside slides | matplotlib → PNG → `add_picture` (see §6 — do NOT use native pptx charts for anything non-trivial) |
| Verify render | LibreOffice `soffice` (portable) or PowerPoint COM (accurate) |

## 2. Basic slide construction — full worked example

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9
prs.slide_height = Inches(7.5)

blank_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(blank_layout)

# title
title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.3), Inches(1.2))
tf = title_box.text_frame
tf.text = "Q3 Revenue Overview"
tf.paragraphs[0].font.size = Pt(40)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = RGBColor(0x1E, 0x27, 0x61)
tf.paragraphs[0].alignment = PP_ALIGN.LEFT

# icon-in-circle motif
circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.5), Inches(2), Inches(0.8), Inches(0.8))
circle.fill.solid()
circle.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
circle.line.fill.background()

# body text block
body_box = slide.shapes.add_textbox(Inches(1.6), Inches(2), Inches(6), Inches(3))
body_tf = body_box.text_frame
body_tf.word_wrap = True
p = body_tf.paragraphs[0]
p.text = "Revenue grew 24% quarter-over-quarter."
p.font.size = Pt(16)
p.alignment = PP_ALIGN.LEFT

prs.save("output.pptx")
```

## 3. Don't make boring slides — design rules (non-negotiable)

The single most common AI-deck failure: a wall of bullets on a white
background. Every slide needs a genuine visual element — image, chart, icon
shape, or a deliberate multi-block layout.

**Palette**: pick one that fits the actual topic, not generic corporate
blue. One dominant color (60-70% weight), 1-2 supporting tones, one sharp
accent.

| Theme | Primary | Secondary | Accent |
|---|---|---|---|
| Midnight Executive | `#1E2761` | `#CADCFC` | `#FFFFFF` |
| Forest & Moss | `#2C5F2D` | `#97BC62` | `#F5F5F5` |
| Charcoal Minimal | `#36454F` | `#F2F2F2` | `#212121` |
| Ocean Gradient | `#065A82` | `#1C7293` | `#21295C` |
| Coral Energy | `#F96167` | `#F9E795` | `#2F3C7E` |

**Layout variety** — rotate between slides, don't repeat the same template:
- Two-column (text left, image/chart right)
- Icon + text rows (icon in colored circle, header, description below)
- Big stat callout (60-72pt number, small label under it)
- Comparison columns (before/after, pros/cons)
- 2x2 or 2x3 grid

**Typography — safe font list matters for QA reliability:**

| Safe (renders true-to-width in LibreOffice AND ships with Office) | Risky (font substitution breaks overflow QA) |
|---|---|
| Arial, Calibri, Cambria, Times New Roman, Courier New | Georgia, Trebuchet MS, Impact, Arial Black, Garamond, Consolas |

Never default to Aptos — no metric-compatible substitute in LibreOffice, and
missing entirely from older Office installs.

| Element | Size |
|---|---|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

**Hard avoid list:**
- Accent line under titles — reads as AI-generated
- Color bar/stripe on any slide/card edge — same tell
- Centered body text/bullets — left-align always, center only titles
- Cream/beige default backgrounds — use white or the chosen palette
- Text overflowing its container — fix by shrinking font, splitting slides,
  or enlarging the box; never ship clipped text

## 4. Working with templates (.potx or existing branded .pptx)

When a template exists, edit it rather than building from a blank layout —
preserves the brand's actual master slide styling.

```python
prs = Presentation("company_template.pptx")

# inspect available layouts first
for i, layout in enumerate(prs.slide_master.slide_layouts):
    print(i, layout.name)

slide = prs.slides.add_slide(prs.slide_master.slide_layouts[1])  # "Title and Content" etc

# fill placeholder text rather than adding new text boxes, to inherit template styling
for shape in slide.placeholders:
    print(shape.placeholder_format.idx, shape.placeholder_format.type, shape.name)

slide.placeholders[0].text = "New Title"
slide.placeholders[1].text = "New body content"
```

Check for leftover placeholder/lorem-ipsum text after filling — this is the
most common template-editing bug:
```python
import re
for slide in prs.slides:
    for shape in slide.shapes:
        if shape.has_text_frame:
            text = shape.text_frame.text
            if re.search(r"\bx{3,}\b|lorem|ipsum|\bTODO\b|\[insert", text, re.IGNORECASE):
                print(f"Leftover placeholder text found: {text!r}")
```

## 5. Speaker notes

```python
notes_slide = slide.notes_slide
notes_slide.notes_text_frame.text = "Remember to mention the Q4 forecast here."
```

## 6. Charts — the scatter-chart lesson, generalized

**Native pptx chart objects (`python-pptx`'s `chart_data` API) are workable
only for simple bar/line/pie with default styling.** For anything with
custom colors, scatter plots, dual axes, or any real design intent — native
charts fight you every step and often render inconsistently between
PowerPoint and LibreOffice's preview.

**The reliable pattern**: generate with matplotlib, save as a transparent
PNG, embed as a picture. This applies with extra force to scatter charts
specifically — python-pptx's native `XL_CHART_TYPE.XY_SCATTER` has known
rendering inconsistencies (this is the exact bug you hit on the DS500
project — worth remembering as the general rule, not a one-off fix).

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
ax.scatter(x, y, color="#1E2761", s=40, alpha=0.7, edgecolors="none")
ax.spines[["top", "right"]].set_visible(False)
ax.set_xlabel("Debt-to-Income Ratio", fontsize=11)
ax.set_ylabel("Savings Rate", fontsize=11)
fig.savefig("chart.png", dpi=150, bbox_inches="tight", transparent=True)
plt.close(fig)

from pptx.util import Inches
slide.shapes.add_picture("chart.png", Inches(1), Inches(1.8), width=Inches(8))
```

If a genuinely native/editable chart is required (user wants to tweak data
in PowerPoint later), native charts are fine for **bar, line, and pie only**:

```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = CategoryChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("Revenue", (19.2, 21.4, 25.1, 27.8))

slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1.8), Inches(8), Inches(4.5), chart_data
)
```

## 7. Tables

```python
rows, cols = 4, 3
table_shape = slide.shapes.add_table(rows, cols, Inches(1), Inches(2), Inches(10), Inches(3))
table = table_shape.table

table.columns[0].width = Inches(4)
table.columns[1].width = Inches(3)
table.columns[2].width = Inches(3)

headers = ["Metric", "Q2", "Q3"]
for i, h in enumerate(headers):
    cell = table.cell(0, i)
    cell.text = h
    cell.text_frame.paragraphs[0].font.bold = True
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
    cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
```

## 8. Animations and transitions — real limitation

python-pptx has **no API for animations or slide transitions** — these live
in parts of the OOXML schema the library doesn't expose. Two options if
truly required:

1. Raw XML injection into `ppt/slides/slideN.xml` under the `<p:timing>`
   element — genuinely fiddly, only worth it for a single specific effect
   the user insists on.
2. Build the deck in python-pptx, then apply animations manually in
   PowerPoint afterward, or drive PowerPoint via COM (`win32com`) which
   *does* expose the animation object model:
   ```python
   shape_range = slide.Shapes.Range([1])
   effect = slide.TimeLine.MainSequence.AddEffect(
       Shape=shape_range, effectId=1  # msoAnimEffectFade, etc — see MSO enum
   )
   ```
Flag this limitation to the user up front rather than silently shipping a
static deck when animation was requested — don't let them discover it missing.

## 9. Verify before delivering (mandatory)

```bash
python friday/skills/pptx/scripts/verify_pptx.py output.pptx
```

This renders every slide to JPEG and runs the placeholder-text/overflow
checks. Actually view the rendered images — don't trust "the script ran" as
proof the deck looks right.

Manual render (what the script does under the hood, for reference):
```bash
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

QA checklist while viewing:
- Text overflowing its box or clipped at slide edges — check this FIRST, most common defect
- Overlapping shapes/text
- Inconsistent alignment across similar elements (columns, cards)
- Low-contrast text
- Gaps under 0.3" between blocks, or under 0.5" from slide edges
- Leftover placeholder/lorem-ipsum text (grep as shown in §4)

## 10. Windows-specific gotchas

- File locks: PowerPoint keeps `.pptx` open exclusively — catch
  `PermissionError` and ask the user to close the file rather than crashing.
- COM-based PowerPoint automation (`win32com`) requires PowerPoint actually
  installed and can hang on an unexpected dialog — always wrap in
  try/finally and call `.Quit()`:
  ```python
  powerpoint = win32com.client.Dispatch("PowerPoint.Application")
  try:
      ...
  finally:
      powerpoint.Quit()
  ```
- Leftover invisible `POWERPNT.EXE` processes from crashed COM scripts can
  lock files — check Task Manager if a "file in use" error persists after a
  script failure.

## Dependencies

`python-pptx` `matplotlib` `Pillow` (pip) · `pywin32` (optional, enables COM
automation for animations/accurate export) · LibreOffice `soffice` +
Poppler `pdftoppm` (verify render, no PowerPoint required) · MS PowerPoint
(optional, higher-fidelity verify render + animation support)

## Scripts in this skill

- `scripts/check_env.py` — verifies packages + PowerPoint COM / LibreOffice
  availability
- `scripts/verify_pptx.py` — renders every slide to JPEG, scans for
  leftover placeholder text, reports rendered image paths for visual review
