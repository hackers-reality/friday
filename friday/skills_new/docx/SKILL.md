---
name: docx
location: friday/skills/docx/SKILL.md
trigger: word doc, .docx, .dotx, report, memo, letter, contract, template, tracked changes, comments, mail merge
platform: Windows (FRIDAY host machine)
---

# DOCX — FRIDAY Playbook (Full)

## 0. Environment setup

```powershell
pip install python-docx docx2pdf pandas Pillow
# LibreOffice needed for verify-render and .doc -> .docx conversion
# https://www.libreoffice.org/download/download/ -> installs soffice.exe
# Default path: C:\Program Files\LibreOffice\program\soffice.exe -> add to PATH
```

Windows has a native alternative to LibreOffice for PDF conversion if MS
Word itself is installed: `docx2pdf` uses Word's COM interface directly and
is often more faithful to real Word rendering than LibreOffice's conversion.
Prefer it when Word is present on the host:

```python
from docx2pdf import convert
convert("output.docx", "output.pdf")   # uses installed MS Word via COM
```

Verify env:
```bash
python friday/skills/docx/scripts/check_env.py
```

## 1. Library map

| Task | Approach |
|---|---|
| Create new | `python-docx` |
| Edit existing (simple: text/style changes) | `python-docx` (load existing file) |
| Edit existing (surgical XML-level changes, tracked changes, comments) | Unpack zip → edit `word/document.xml` → repack |
| Read/extract content | `pandoc -t markdown file.docx` or `python-docx` for structured read |
| Mail merge / bulk generation | `python-docx` templating loop, or `docxtpl` (Jinja2-style templating) |
| .doc (legacy) → .docx | `soffice --headless --convert-to docx file.doc` first, always |

## 2. Creating a document — full worked example

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

doc = Document()

section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.left_margin = Inches(1)
section.right_margin = Inches(1)

title = doc.add_heading("Report Title", level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_heading("Section One", level=1)
p = doc.add_paragraph("Body text goes here. ")
p.add_run("This part is bold.").bold = True

doc.add_heading("Data", level=1)
table = doc.add_table(rows=1, cols=3)
table.style = "Light Grid Accent 1"
table.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = table.rows[0].cells
hdr[0].text, hdr[1].text, hdr[2].text = "Item", "Qty", "Price"

widths = [Inches(3), Inches(1.5), Inches(1.5)]
for row in table.rows:
    for cell, w in zip(row.cells, widths):
        cell.width = w

for item, qty, price in [("Widget", "10", "$5.00"), ("Gadget", "3", "$12.00")]:
    row = table.add_row().cells
    row[0].text, row[1].text, row[2].text = item, qty, price
    for cell, w in zip(row, widths):
        cell.width = w

doc.add_page_break()
doc.add_heading("Section Two", level=1)
doc.add_paragraph("Item one", style="List Bullet")
doc.add_paragraph("Item two", style="List Bullet")

doc.save("output.docx")
```

## 3. Gotchas — the ones that actually break things

- **Page size**: don't rely on defaults, set explicitly. python-docx defaults
  to Letter but be explicit anyway — cheap insurance.
- **Never insert literal bullet characters** (`•`, `-`). Use built-in list
  styles (`"List Bullet"`, `"List Number"`) — literal characters don't get
  proper indentation/numbering behavior and look wrong in Word's UI.
- **Table widths**: set width on every cell in every row, not just the
  header row and not just the table object. Inconsistent per-row widths is
  the #1 cause of "ugly misaligned table" bug reports.
- **Table shading**: never use raw XML `w:shd` with fill values that render
  as solid black — if hand-editing XML, always test the render.
- **Headings must use built-in `Heading 1`/`Heading 2` styles**, not manually
  bolded normal text, or a Table of Contents field will not pick them up.
- **Page breaks**: `doc.add_page_break()` on its own call — never embed a
  break mid-run of text.
- **Images**: always specify width or height, never both unless you've
  confirmed the aspect ratio matches — stretching distorts:
  ```python
  doc.add_picture("chart.png", width=Inches(6))  # height auto-scales
  ```
- **`\n` inside a single `run.text` does nothing in Word.** Use
  `run.add_break()` for a line break within a paragraph, or separate
  `add_paragraph()` calls for a new paragraph.
- **Font consistency**: set the Normal style's font explicitly, or Word's
  default (often Calibri) leaks through inconsistently across
  auto-generated headings vs manually-styled text:
  ```python
  style = doc.styles["Normal"]
  style.font.name = "Calibri"
  style.font.size = Pt(11)
  ```

## 4. Table of Contents (auto-updating field)

python-docx cannot compute TOC page numbers itself — it inserts a field that
Word populates on open. This requires raw XML injection:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_toc(doc):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    fldChar3 = OxmlElement("w:t")
    fldChar3.text = "Right-click and select 'Update Field' to generate the Table of Contents."
    fldChar4 = OxmlElement("w:fldChar")
    fldChar4.set(qn("w:fldCharType"), "end")
    for el in (fldChar1, instrText, fldChar2, fldChar3, fldChar4):
        run._r.append(el)
```

Tell the user the TOC needs a manual "Update Field" (F9 in Word) on first
open — this is a genuine Word limitation, not something scriptable around
without opening the file in Word/LibreOffice and triggering the field
update programmatically via COM (`docx2pdf`'s underlying Word COM object can
do this if truly needed).

## 5. Editing an existing document — XML-level surgery

Use this ONLY when python-docx's object model can't express the edit
(complex find-replace preserving formatting, tracked changes, comments).
For anything greenfield, use python-docx directly — it's less fragile.

Legacy `.doc` files must convert first:
```bash
soffice --headless --convert-to docx file.doc
```

```bash
unzip -q doc.docx -d unpacked/
# edit unpacked/word/document.xml directly — do NOT pretty-print/reformat,
# this breaks Word's whitespace-sensitive XML in subtle, hard-to-debug ways
cd unpacked && zip -Xr ../out.docx . && cd ..
```

### Find-and-replace preserving formatting (python-docx)

Naive `paragraph.text = paragraph.text.replace(...)` **destroys all run-level
formatting** (bold, color, font) because it collapses all runs into one.
Correct approach — replace within runs, only splitting when the target
string spans multiple runs:

```python
def replace_in_paragraph(paragraph, old, new):
    if old in paragraph.text:
        # simple case: search within each run first (preserves formatting)
        for run in paragraph.runs:
            if old in run.text:
                run.text = run.text.replace(old, new)
                return
        # complex case: text spans multiple runs — rebuild while keeping
        # the first run's formatting, drop the rest
        full = "".join(r.text for r in paragraph.runs)
        if old in full:
            new_full = full.replace(old, new)
            paragraph.runs[0].text = new_full
            for run in paragraph.runs[1:]:
                run.text = ""
```

## 6. Tracked changes

Wrap runs in `<w:ins>` (insertion) or `<w:del>` (deletion) with required
`w:id`, `w:author`, `w:date` attributes. Inside `<w:del>`, text elements are
`<w:delText>`, not `<w:t>`:

```xml
<w:ins w:id="1" w:author="FRIDAY" w:date="2026-07-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>
<w:del w:id="2" w:author="FRIDAY" w:date="2026-07-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

To produce a clean copy with all tracked changes accepted (strip markup,
keep insertions, drop deletions):
```bash
python friday/skills/docx/scripts/accept_changes.py in.docx out.docx
```

## 7. Comments

Comments require six cross-linked XML parts: `comments.xml`,
`commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml`,
relationships, and content-type overrides. Don't hand-write these — use the
helper script:

```bash
python friday/skills/docx/scripts/add_comment.py unpacked/ "This clause needs review"
python friday/skills/docx/scripts/add_comment.py unpacked/ "Agreed" --parent 0
```

The script auto-assigns comment IDs and prints the
`<w:commentRangeStart>`/`<w:commentRangeEnd>`/`<w:commentReference>` snippet
needed inside `word/document.xml` to anchor the comment to specific text —
without placing those markers manually, the comment exists in the file but
isn't visibly anchored to anything.

## 8. Mail merge / bulk document generation

For generating many similar documents from one template + a data source
(e.g. personalized letters, certificates), use `docxtpl` (Jinja2 templating
inside Word):

```bash
pip install docxtpl
```

```python
from docxtpl import DocxTemplate
import pandas as pd

tpl_path = "template.docx"   # contains {{ name }}, {{ amount }} etc as literal text in Word
df = pd.read_excel("recipients.xlsx")

for _, row in df.iterrows():
    doc = DocxTemplate(tpl_path)
    doc.render({"name": row["Name"], "amount": row["Amount"]})
    doc.save(f"output/letter_{row['Name'].replace(' ', '_')}.docx")
```

Template authoring note: `{{ variable }}` tags must be written as plain
unformatted text in Word (no mixed bold/italic mid-tag) or Jinja2 parsing
breaks — Word sometimes splits a single visual word across multiple XML
runs invisibly, which corrupts the tag. Type the tag, select it, and clear
formatting before saving the template.

## 9. Letterheads / headers / footers with page numbers

```python
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_page_numbers(doc):
    section = doc.sections[0]
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()

    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    for el in (fldChar1, instrText, fldChar2):
        run._r.append(el)
```

Letterhead image in header:
```python
header = doc.sections[0].header
p = header.paragraphs[0]
run = p.add_run()
run.add_picture("letterhead.png", width=Inches(6.5))
```

## 10. Verify before delivering (mandatory)

```bash
soffice --headless --convert-to pdf output.docx
pdftoppm -jpeg -r 100 output.pdf page
# view page-1.jpg, page-2.jpg, ... — actually look
```

Or, if MS Word is installed on the FRIDAY host, prefer the more accurate
COM-based render:
```python
from docx2pdf import convert
convert("output.docx", "verify.pdf")
```

Also run structural sanity checks:
```bash
python friday/skills/docx/scripts/verify_docx.py output.docx
```

Check visually for: text overflowing page margins, tables with columns that
don't line up, images that broke the layout, missing/broken TOC, font
inconsistency between sections.

## 11. Windows-specific gotchas

- File locks: Word keeps `.docx` files locked while open — writing to a path
  the user has open in Word will raise `PermissionError`. Catch this and
  tell the user to close the file rather than crashing silently.
- `docx2pdf`'s COM approach requires MS Word actually installed and
  activated — it will hang or fail silently on a machine without Word. Check
  for Word's presence before choosing this path over LibreOffice:
  ```python
  import winreg
  def word_installed():
      try:
          winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application")
          return True
      except FileNotFoundError:
          return False
  ```
- Temp files: `~$filename.docx` lock files are created by Word when a doc is
  open — if FRIDAY's file-watcher logic scans a folder for docx files, filter
  these out or it'll try to process a lock file as a document.

## Dependencies

`python-docx` `docxtpl` `docx2pdf` `pandas` `Pillow` (pip) · `pandoc` (CLI,
for reading) · LibreOffice `soffice` (verify render, .doc conversion) · MS
Word (optional, enables more accurate COM-based PDF conversion via docx2pdf)

## Scripts in this skill

- `scripts/check_env.py` — verifies pandoc/soffice/Word-COM availability
- `scripts/verify_docx.py` — renders + runs structural sanity checks
  (paragraph count, broken image refs, empty document detection)
- `scripts/accept_changes.py` — strips tracked-changes markup, keeping
  insertions and dropping deletions, to produce a clean final copy
- `scripts/add_comment.py` — adds a properly cross-linked Word comment to an
  unpacked docx directory
