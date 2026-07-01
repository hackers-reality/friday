---
name: pdf
location: friday/skills/pdf/SKILL.md
trigger: pdf, invoice, form, merge/split/rotate pages, watermark, ocr, encrypt, sign, extract tables, accessibility/tagged pdf
platform: Windows (FRIDAY host machine)
---

# PDF — FRIDAY Playbook (Full)

## QUALITY CRITICAL — READ BEFORE WRITING CODE

Build every generated PDF report as if it will be printed and handed to a
senior stakeholder. Every page earns its place — no filler pages, no
placeholder text, no single-table-dump-with-no-context pages. This
blueprint applies to report-style PDFs (the most common FRIDAY request);
invoices/forms/labels are simpler and don't need all 5 sections.

### Exact page blueprint (5 pages minimum, for report-style PDFs)

**Page 1 — Title Page**: A4, 2.5cm margins. Title 24pt bold `#0C447C`
centered at 40% from top. Accent line: 2pt thick, `#378ADD`, 8cm wide,
centered, 0.5cm below title. Subtitle 14pt `#5F5E5A` centered, 1cm below
accent line. Date 11pt `#888780` centered. "Prepared by FRIDAY" 10pt
`#888780` centered. No header/footer on this page.

**Page 2 — Table of Contents**: Header "Table of Contents" 18pt bold
`#185FA5`. Entries with dot leaders: Level 0 = 11pt bold `#333333`, no
indent; Level 1 = 10pt regular `#5F5E5A`, 1.5cm indent. Footer from this
page onward: page number centered, document title left-aligned, thin rule
above footer.

**Page 3 — Content Section 1**: Header "1. [Section Name]" 18pt bold
`#185FA5`. Body 11pt justified `#333333`, 15pt leading, 8pt space-after.
Data table if relevant: header row bg `#378ADD` white bold 10pt, data rows
10pt `#333333` alternating `#F1EFE8`/white. Caption below table: 9pt
italic `#888780` centered.

**Page 4 — Content Section 2**: Header "2. [Section Name]" 18pt bold
`#185FA5`. Embedded chart (see §4), sized ~12cm×7cm, centered, with its own
caption "Figure 1: ..." 9pt italic centered. 1-2 body paragraphs below.

**Page 5 — Conclusion**: Header "3. Conclusions & Recommendations" 18pt
bold `#185FA5`. Bullet list of 3-5 key findings. Summary paragraph. Final
note 10pt italic `#5F5E5A`.

### Type scale (set explicitly — never rely on style defaults)

| Role | Size | Weight | Leading |
|---|---|---|---|
| Document title | 24pt | Bold | 30pt |
| Heading 1 | 18pt | Bold | 24pt |
| Heading 2 | 14pt | Bold | 20pt |
| Heading 3 | 12pt | Bold | 17pt |
| Body text | 11pt | Regular | 15pt |
| Body text (small) | 10pt | Regular | 14pt |
| Caption | 9pt | Italic | 12pt |
| Table header | 10pt | Bold | 14pt |
| Table body | 10pt | Regular | 14pt |
| Footer / header | 8pt | Regular | 11pt |

### Color system — pick ONE per document, apply everywhere

| Role | Hex |
|---|---|
| Title | `#0C447C` |
| Heading 1 | `#185FA5` |
| Heading 2 | `#3C3489` |
| Heading 3 | `#1D9E75` |
| Body text | `#333333` (never pure `#000`) |
| Muted text | `#888780` |
| Table header bg | `#378ADD` |
| Table header text | `#FFFFFF` |
| Border/rule | `#B4B2A9` |
| Accent | `#534AB7` |
| Light bg (alt rows) | `#F1EFE8` |
| Warning | `#BA7517` |
| Error | `#E24B4A` |
| Success | `#639922` |

Alternate palettes (swap whole set together, don't mix): **Corporate** —
title `#1D9E75`, H1 `#0F6E56`, table header `#639922`, light bg `#E1F5EE`.
**Dark Report** — title page dark bg `#0a0a2e` white text, body pages white
bg, headings `#00d4ff`.

### Every page must have

- Explicit page size set (A4 default for FRIDAY unless user specifies Letter)
- 2.5cm margins minimum (never below 1.5cm)
- Metadata set: title, author, subject, keywords
- No pure black `#000` body text — always dark gray `#333333`
- Leading at least 1.35× the font size

### Anti-patterns that get a report rejected

- Single-page table dump with no title/context
- No title page or TOC on a 5+ page report
- Missing headers/footers on content pages
- No page numbers
- Zero charts/images/visual elements in a data-driven report
- Tables without colored header rows or alternating row shading
- Missing document metadata
- Inconsistent heading colors/sizes across sections

## 0. Environment setup (do this once, check every session)

FRIDAY runs on Windows. Poppler and Tesseract are NOT bundled with pip installs
on Windows the way they are on Linux — this is the #1 silent-failure cause.

```powershell
# Poppler (needed for pdftoppm, pdftotext, pdfimages, pdf2image backend)
# Download prebuilt binaries: https://github.com/oschwartz10612/poppler-windows/releases
# Extract to C:\tools\poppler\ then add C:\tools\poppler\Library\bin to PATH

# Tesseract (OCR)
# Download installer: https://github.com/UB-Mannheim/tesseract/wiki
# Default install: C:\Program Files\Tesseract-OCR\tesseract.exe
# Add to PATH, or set explicitly in Python:
#   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# qpdf (CLI merge/split/rotate/encrypt)
# https://github.com/qpdf/qpdf/releases -> add extracted bin\ to PATH
```

```powershell
pip install reportlab pypdf pdfplumber matplotlib pytesseract pdf2image pikepdf fpdf2 pdfrw pymupdf
```

Verify before FRIDAY relies on any of this in a task:
```python
import shutil
for exe in ["pdftoppm", "pdftotext", "pdfimages", "tesseract", "qpdf"]:
    print(exe, shutil.which(exe) or "NOT FOUND — fix PATH first")
```

Run `friday/skills/pdf/scripts/check_env.py` — it does exactly this check
and prints actionable fix instructions per missing tool.

## 1. Library map — pick correctly, don't default to one tool for everything

| Task | Library | Notes |
|---|---|---|
| Create from scratch, text-heavy report | `reportlab` (Platypus) | Best pagination/flow handling |
| Create from scratch, simple/quick | `fpdf2` | Lighter weight, less boilerplate than reportlab for basic docs |
| Merge / split / rotate / basic encrypt | `pypdf` | Pure Python, no system dep |
| Merge / split / rotate at CLI speed | `qpdf` | Faster for batch/scripted ops, handles broken PDFs better |
| Text/table extraction, layout-aware | `pdfplumber` | Best table detection |
| Low-level page manipulation, overlays, redaction-adjacent | `pymupdf` (fitz) | Fastest, most powerful, steeper API |
| Strong encryption / permissions / linearization | `pikepdf` (wraps qpdf) | More control than pypdf's `.encrypt()` |
| Form fields (AcroForm) | `pypdf` (simple) or `pdf-lib` via Node (complex) | See §5 |
| OCR (scanned/image PDFs) | `pytesseract` + `pdf2image` | Requires Tesseract + Poppler installed |

## 2. Creating a PDF — full worked example (reportlab/Platypus)

```python
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def build_report(output_path: str, title: str, sections: list[dict]):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CustomTitle", parent=styles["Title"],
        fontSize=24, spaceAfter=20, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="Body", parent=styles["Normal"],
        fontSize=11, leading=16, alignment=TA_JUSTIFY,
    ))

    story = [Paragraph(title, styles["CustomTitle"]), Spacer(1, 12)]

    for section in sections:
        story.append(Paragraph(section["heading"], styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(section["body"], styles["Body"]))
        story.append(Spacer(1, 12))

        if "table" in section:
            t = Table(section["table"], hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E2761")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

        if "image" in section:
            story.append(Image(section["image"], width=5 * inch, height=3 * inch))
            story.append(Spacer(1, 12))

        if section.get("page_break_after"):
            story.append(PageBreak())

    doc.build(story)
```

## 3. Subscripts, superscripts, special characters

**Never use Unicode subscript/superscript glyphs** (₀₁₂₃, ⁰¹²³) — reportlab's
built-in fonts (Helvetica, Times) don't include them; they render as solid
black boxes. Use XML markup in `Paragraph`:

```python
Paragraph("H<sub>2</sub>O", styles["Normal"])
Paragraph("x<super>2</super> + y<super>2</super>", styles["Normal"])
Paragraph("Footnote reference<super>1</super>", styles["Normal"])
```

For Canvas-drawn text (not inside a Paragraph), there is no markup support —
manually shrink font size and offset the y-coordinate instead.

Non-ASCII/Unicode body text (e.g. rupee sign ₹, Devanagari) needs a font that
actually has those glyphs — reportlab's base-14 fonts don't. Register a
Unicode-capable TTF:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("NotoSans", "C:/Windows/Fonts/NotoSans-Regular.ttf"))
# then use fontName="NotoSans" in your ParagraphStyle
```

## 4. Charts inside PDFs

Don't fight reportlab's native chart flowables. Generate with matplotlib,
save PNG, embed as image — same rule as pptx.

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
ax.plot(x, y, color="#1E2761", linewidth=2)
ax.spines[["top", "right"]].set_visible(False)
fig.savefig("chart.png", bbox_inches="tight", transparent=True)
plt.close(fig)

story.append(Image("chart.png", width=5 * inch, height=3.3 * inch))
```

## 5. Filling PDF forms (AcroForms)

**Reading existing form field names first — mandatory, don't guess field names:**

```python
from pypdf import PdfReader
reader = PdfReader("form.pdf")
fields = reader.get_fields()
for name, f in (fields or {}).items():
    print(name, "->", f.get("/FT"), f.get("/V"))
```

**Filling with pypdf:**

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("form.pdf")
writer = PdfWriter()
writer.append(reader)

writer.update_page_form_field_values(
    writer.pages[0],
    {"full_name": "Arnav", "email": "you@example.com", "agree_checkbox": "/Yes"},
    auto_regenerate=False,  # important on Windows viewers — forces field appearance regen
)

with open("filled.pdf", "wb") as f:
    writer.write(f)
```

Checkboxes/radio buttons: the "on" value is usually `/Yes` or `/On`, not
`True` — check `fields[name]["/_States_"]` to get the exact accepted values,
they vary per form.

**If the form has no fillable fields** (flat/scanned form) — this needs
coordinate-based overlay instead:

```python
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
import io

buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=letter)
c.drawString(120, 700, "Arnav")   # x, y in points from bottom-left — measure from a rendered image
c.save()
buf.seek(0)

overlay = PdfReader(buf).pages[0]
base = PdfReader("blank_form.pdf")
writer = PdfWriter()
page = base.pages[0]
page.merge_page(overlay)
writer.add_page(page)
writer.write("filled.pdf")
```

To find coordinates: render the form to an image at known DPI, measure pixel
position, convert `points = pixels / dpi * 72`.

## 6. Encryption, passwords, permissions

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()
writer.append(reader)

writer.encrypt(
    user_password="viewpass",     # required to open
    owner_password="ownerpass",   # required to change permissions
    permissions_flag=(
        0b0100  # allow printing
    ),
)
with open("encrypted.pdf", "wb") as f:
    writer.write(f)
```

For finer-grained permission control (disallow copy but allow print, etc.)
use `pikepdf`, which exposes the full permission bitfield more clearly:

```python
import pikepdf
pdf = pikepdf.open("input.pdf")
pdf.save(
    "encrypted.pdf",
    encryption=pikepdf.Encryption(
        user="viewpass", owner="ownerpass",
        allow=pikepdf.Permissions(
            extract=False, modify_annotation=False, print_lowres=True, print_highres=False
        ),
    ),
)
```

Decrypt (removing a known password):
```python
reader = PdfReader("encrypted.pdf")
reader.decrypt("viewpass")
writer = PdfWriter()
writer.append(reader)
writer.write("decrypted.pdf")
```

## 7. Merge / split / rotate / reorder

```python
from pypdf import PdfReader, PdfWriter

# Merge
writer = PdfWriter()
for f in ["a.pdf", "b.pdf", "c.pdf"]:
    for page in PdfReader(f).pages:
        writer.add_page(page)
writer.write("merged.pdf")

# Split — one file per page
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    w = PdfWriter()
    w.add_page(page)
    w.write(f"page_{i+1:03d}.pdf")

# Split by range
w = PdfWriter()
for page in reader.pages[5:10]:   # pages 6-10
    w.add_page(page)
w.write("pages_6-10.pdf")

# Rotate (degrees clockwise)
page = reader.pages[0]
page.rotate(90)

# Reorder / delete pages
writer = PdfWriter()
order = [2, 0, 1, 3]   # 0-indexed new order, e.g. drop nothing, reorder first 3
for i in order:
    writer.add_page(reader.pages[i])
writer.write("reordered.pdf")
```

CLI equivalents (faster for batch, more tolerant of malformed PDFs):
```bash
qpdf --empty --pages a.pdf b.pdf c.pdf -- merged.pdf
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf output.pdf --rotate=+90:1
qpdf --password=pw --decrypt encrypted.pdf decrypted.pdf
```

## 8. Watermarking

```python
from pypdf import PdfReader, PdfWriter

watermark_page = PdfReader("watermark.pdf").pages[0]  # single-page PDF with your mark
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark_page)   # merges UNDER by default order of ops
    writer.add_page(page)

writer.write("watermarked.pdf")
```

To generate the watermark PDF itself (diagonal, semi-transparent):
```python
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

c = canvas.Canvas("watermark.pdf", pagesize=letter)
c.saveState()
c.translate(300, 400)
c.rotate(45)
c.setFillColorRGB(0.5, 0.5, 0.5, alpha=0.3)
c.setFont("Helvetica-Bold", 60)
c.drawCentredString(0, 0, "CONFIDENTIAL")
c.restoreState()
c.save()
```

## 9. Extracting text and tables

```python
import pdfplumber

with pdfplumber.open("doc.pdf") as pdf:
    full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    all_tables = []
    for page in pdf.pages:
        for table in page.extract_tables():
            all_tables.append(table)   # list of list-of-rows
```

Layout-preserving extraction (columns, spacing intact) — better for
re-parsing structured docs like invoices:
```bash
pdftotext -layout input.pdf output.txt
```

Tables to Excel directly:
```python
import pandas as pd
dfs = []
with pdfplumber.open("doc.pdf") as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            if table and len(table) > 1:
                dfs.append(pd.DataFrame(table[1:], columns=table[0]))
if dfs:
    pd.concat(dfs, ignore_index=True).to_excel("extracted.xlsx", index=False)
```

## 10. OCR for scanned / image-only PDFs

Detect if OCR is even needed first — don't OCR a text-native PDF, it's slow
and lossy compared to native extraction:

```python
import pdfplumber
with pdfplumber.open("maybe_scanned.pdf") as pdf:
    text = pdf.pages[0].extract_text()
    needs_ocr = not text or len(text.strip()) < 20
```

```python
import pytesseract
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

images = convert_from_path("scanned.pdf", dpi=300, poppler_path=r"C:\tools\poppler\Library\bin")
text = "\n\n".join(
    f"--- Page {i+1} ---\n{pytesseract.image_to_string(img)}"
    for i, img in enumerate(images)
)
```

Improve OCR accuracy on noisy scans — preprocess before OCR:
```python
from PIL import Image, ImageOps, ImageFilter

def preprocess(img):
    img = img.convert("L")                    # grayscale
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)
    return img.point(lambda p: 255 if p > 160 else 0)  # binarize
```

To produce a searchable PDF (OCR text layer over original scan, not just
plain text output):
```python
import pytesseract
pdf_bytes = pytesseract.image_to_pdf_or_hocr(image, extension="pdf")
with open("searchable_page.pdf", "wb") as f:
    f.write(pdf_bytes)
# then merge these per-page PDFs with pypdf as in §7
```

## 11. Extracting embedded images

```bash
pdfimages -j input.pdf output_prefix
# produces output_prefix-000.jpg, output_prefix-001.jpg, ...
```

Programmatically (with metadata) via pymupdf:
```python
import fitz  # pymupdf
doc = fitz.open("input.pdf")
for page_num, page in enumerate(doc):
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        base = doc.extract_image(xref)
        with open(f"p{page_num}_img{img_index}.{base['ext']}", "wb") as f:
            f.write(base["image"])
```

## 12. Redaction (actually removing content, not just drawing a black box)

**Critical**: `merge_page`-ing a black rectangle over text does NOT remove
the underlying text — it's still extractable via copy-paste or
`extract_text()`. True redaction needs pymupdf's redaction annotations,
which strip the content stream:

```python
import fitz
doc = fitz.open("input.pdf")
for page in doc:
    areas = page.search_for("SSN: 123-45-6789")  # or use explicit rects
    for rect in areas:
        page.add_redact_annot(rect, fill=(0, 0, 0))
    page.apply_redactions()  # this is what actually deletes the underlying content
doc.save("redacted.pdf")
```

If asked to redact sensitive info, always use this method — never the
overlay-rectangle trick, it's a false sense of security and a real data leak
risk if the output is ever shared.

## 13. Accessibility (tagged PDF)

Full tagged-PDF (PDF/UA compliant) generation is not well supported by
reportlab or pypdf directly. For accessibility-critical documents:
- Prefer generating from a tagged source (Word doc with proper heading
  styles → export to PDF via `soffice --headless --convert-to pdf`, which
  preserves some structure tags LibreOffice adds) over building raw PDF from
  scratch.
- At minimum, always set document metadata (title, language) — screen
  readers rely on this even without full tagging:
  ```python
  writer.add_metadata({"/Title": "Report Title", "/Lang": "en-US"})
  ```
- Alt text for images has no first-class API in reportlab; if this is a hard
  requirement, this is a case to flag to the user rather than silently
  ship an inaccessible PDF.

## 14. Verify before delivering (mandatory)

```bash
pdftoppm -jpeg -r 100 output.pdf page
# view page-1.jpg, page-2.jpg, ... — actually look, don't skip this
```

Also run the automated checklist script (checks page count, text
extractability, embedded font issues, file size sanity):
```bash
python friday/skills/pdf/scripts/verify_pdf.py output.pdf
```

Check visually for: text clipped at page edges, tables with misaligned
columns, images stretched/distorted, watermark obscuring real content,
inconsistent margins across pages.

## 15. Common Windows-specific gotchas

- Backslash paths in Python strings need raw strings or forward slashes:
  `r"C:\tools\poppler\Library\bin"` not `"C:\tools\poppler\..."` (the latter
  mangles `\t`).
- `pdf2image` needs `poppler_path=` passed explicitly on Windows unless
  Poppler's bin folder is genuinely on PATH — it will NOT find a
  pip-installed poppler because none exists for Windows via pip.
- File locks: Windows won't let you overwrite a PDF that's currently open in
  a viewer (Adobe/Edge) — catch `PermissionError` and tell the user to close
  the file, don't just crash silently.
- Long path issues (`>260` chars) can still bite on older Windows unless
  long path support is enabled — keep FRIDAY's output directory path short.

## Dependencies

`reportlab` `pypdf` `pdfplumber` `matplotlib` `pytesseract` `pdf2image`
`pikepdf` `fpdf2` `pymupdf` `pandas` (all pip) · Poppler (manual Windows
install, add to PATH) · Tesseract-OCR (manual Windows install) · qpdf
(manual Windows install, optional but recommended for CLI ops)

## Scripts in this skill

- `scripts/check_env.py` — verifies all required binaries are on PATH,
  prints fix instructions for anything missing
- `scripts/verify_pdf.py` — renders output to images + runs sanity checks
  (page count, extractable text, file size) after generation
- `scripts/fill_form.py` — CLI helper: lists form fields in a PDF, or fills
  them from a JSON file
- `scripts/redact.py` — CLI helper: true redaction via pymupdf given a list
  of search strings or explicit rectangles
