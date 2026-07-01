---
name: xlsx
location: friday/skills/xlsx/SKILL.md
trigger: spreadsheet, excel, .xlsx, .xlsm, .csv, budget, tracker, financial model, pivot table, chart
platform: Windows (FRIDAY host machine)
---

# XLSX — FRIDAY Playbook (Full)

## 0. Environment setup

```powershell
pip install openpyxl pandas xlsxwriter xlwings pywin32
# LibreOffice for headless recalculation if Excel itself isn't installed
# https://www.libreoffice.org/download/download/
```

If MS Excel is actually installed on the FRIDAY host (likely, given it's a
Windows dev machine), **`xlwings` via COM is the most reliable recalculation
and verification path** — it drives real Excel, not a LibreOffice
approximation, so formula behavior is guaranteed identical to what the user
will see:

```python
import xlwings as xw
app = xw.App(visible=False)
wb = app.books.open("output.xlsx")
wb.save()   # forces full recalculation on save
app.quit()
```

## 1. Library map

| Task | Library | Notes |
|---|---|---|
| Bulk data load/export, quick analysis | `pandas` | Fast, but loses formatting on round-trip |
| Formulas, cell styling, multi-sheet, charts | `openpyxl` | Most control, most commonly needed |
| Large-file write performance (100k+ rows) | `xlsxwriter` | Faster writes than openpyxl, write-only (can't edit existing) |
| Real Excel-driven recalc/verification | `xlwings` (COM) | Requires Excel installed; most accurate |
| Reading .xls (legacy) | `pandas` with `xlrd` engine, or convert via LibreOffice first | openpyxl doesn't read old .xls |

## 2. Core rule: formulas, not hardcoded values

If a cell's value depends on other cells, write a live formula — never
compute in Python and hardcode the result. A spreadsheet that can't
recalculate when inputs change isn't a spreadsheet.

```python
# WRONG
total = df["Sales"].sum()
sheet["B10"] = total          # dead value, 5000 forever

# RIGHT
sheet["B10"] = "=SUM(B2:B9)"  # live formula
```

## 3. Creating a workbook — full worked example

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule

wb = Workbook()
sheet = wb.active
sheet.title = "Data"

headers = ["Item", "Qty", "Unit Price", "Total"]
for col, h in enumerate(headers, start=1):
    cell = sheet.cell(row=1, column=col, value=h)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color="1E2761")
    cell.alignment = Alignment(horizontal="center")

data = [("Widget", 10, 5.00), ("Gadget", 3, 12.00), ("Gizmo", 7, 8.50)]
for row_i, (item, qty, price) in enumerate(data, start=2):
    sheet.cell(row=row_i, column=1, value=item)
    sheet.cell(row=row_i, column=2, value=qty)
    sheet.cell(row=row_i, column=3, value=price).number_format = "$#,##0.00"
    sheet.cell(row=row_i, column=4, value=f"=B{row_i}*C{row_i}").number_format = "$#,##0.00"

last_row = 1 + len(data)
sheet.cell(row=last_row + 1, column=3, value="Total").font = Font(bold=True)
sheet.cell(row=last_row + 1, column=4, value=f"=SUM(D2:D{last_row})").number_format = "$#,##0.00"

for col in range(1, 5):
    sheet.column_dimensions[get_column_letter(col)].width = 15

# conditional formatting: highlight totals over $50
sheet.conditional_formatting.add(
    f"D2:D{last_row}",
    CellIsRule(operator="greaterThan", formula=["50"], fill=PatternFill("solid", start_color="FFFF00")),
)

# chart
chart = BarChart()
chart.title = "Line Item Totals"
data_ref = Reference(sheet, min_col=4, min_row=1, max_row=last_row)
cats_ref = Reference(sheet, min_col=1, min_row=2, max_row=last_row)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
sheet.add_chart(chart, "F2")

wb.save("output.xlsx")
```

## 4. Mandatory: recalculate after writing formulas

openpyxl writes formula **strings** but does not evaluate them — the file
shows blank/stale values until something computes them. Excel itself
recalculates on open by default, but don't rely on that for FRIDAY's own
verification step; force it explicitly:

**Option A — real Excel via COM (best fidelity, needs Excel installed):**
```python
import xlwings as xw
app = xw.App(visible=False)
wb = app.books.open(r"C:\path\to\output.xlsx")
wb.save()
app.quit()
```

**Option B — LibreOffice headless (works without Excel installed):**
```bash
soffice --headless --convert-to xlsx --outdir ./recalc_out output.xlsx
```
Note: LibreOffice's formula engine has small differences from Excel's for
some functions (esp. newer dynamic array functions like `XLOOKUP`,
`FILTER`) — treat this as good-enough for verification, not a guarantee of
byte-identical Excel behavior.

## 5. Scanning for formula errors — zero-error requirement

Every delivered workbook must have zero `#REF!`, `#DIV/0!`, `#VALUE!`,
`#N/A`, `#NAME?` errors. Scan after recalculation:

```python
from openpyxl import load_workbook

wb = load_workbook("output.xlsx", data_only=True)  # reads last-computed values
errors = []
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("#"):
                errors.append(f"{ws.title}!{cell.coordinate}: {cell.value}")
if errors:
    print("Formula errors found:", errors)
```

**Warning**: loading with `data_only=True` and then *saving* strips all
formulas permanently, replacing them with their last-computed values — only
ever use `data_only=True` for read/verify, never as the working copy you
continue editing.

Common causes to check for:
- Off-by-one range errors — Excel is 1-indexed; a pandas DataFrame's row 5
  becomes Excel row 6 once a header row is added.
- Division without a zero-guard: `=IF(B2=0,"-",A2/B2)`, not raw `=A2/B2`.
- Cross-sheet reference syntax: `Sheet1!A1`, not `Sheet1.A1`.
- Deleted/renamed sheet still referenced by a formula elsewhere.

## 6. Financial model formatting conventions

Apply when the deliverable is explicitly a financial model, or user context
implies it — don't force this styling onto a casual list/tracker.

| Element | Convention |
|---|---|
| Hardcoded inputs | Blue text `RGB(0,0,255)` |
| Formulas / calculations | Black text |
| Cross-sheet links | Green text `RGB(0,128,0)` |
| External file links | Red text `RGB(255,0,0)` |
| Key assumptions needing attention | Yellow background `RGB(255,255,0)` |
| Years | Text string `"2024"`, never numeric `2,024` |
| Currency | `$#,##0` with units specified in the header, e.g. "Revenue ($mm)" |
| Zeros | Format as `"-"` via number format `"$#,##0;($#,##0);-"` |
| Percentages | `0.0%` — one decimal by default |
| Multiples (EV/EBITDA etc) | `0.0x` |
| Negative numbers | Parentheses `(123)`, never a leading minus |

```python
from openpyxl.styles import Font
INPUT = Font(color="0000FF")
FORMULA = Font(color="000000")
LINK = Font(color="008000")
EXTERNAL = Font(color="FF0000")

sheet["B2"].font = INPUT   # 0.05, a hardcoded growth-rate assumption
sheet["B3"] = "=B2*(1+$B$4)"
sheet["B3"].font = FORMULA
```

Always place assumptions in dedicated cells and reference them — never bury
a magic number inside a formula:
```python
# WRONG
sheet["C5"] = "=B5*1.05"
# RIGHT
sheet["B6"] = 0.05                       # labeled "Growth Rate" assumption cell
sheet["C5"] = "=B5*(1+$B$6)"
```

## 7. Pivot tables

openpyxl cannot create native Excel pivot tables (it can only preserve ones
that already exist in a loaded file). Two real options:

**Option A — pandas pivot as a static summary table** (simplest, works
everywhere, but not an interactive Excel PivotTable):
```python
pivot = df.pivot_table(index="Region", columns="Quarter", values="Revenue", aggfunc="sum")
pivot.to_excel("summary.xlsx")
```

**Option B — real interactive PivotTable via Excel COM** (needs Excel
installed):
```python
import xlwings as xw
app = xw.App(visible=False)
wb = app.books.open("data.xlsx")
sheet = wb.sheets["Data"]
data_range = sheet.range("A1").expand()

pivot_sheet = wb.sheets.add("Pivot")
pc = wb.api.PivotCaches().Create(SourceType=1, SourceData=data_range.api)
pt = pc.CreatePivotTable(TableDestination=pivot_sheet.range("A1").api, TableName="MyPivot")
pt.PivotFields("Region").Orientation = 1   # xlRowField
pt.PivotFields("Quarter").Orientation = 2  # xlColumnField
pt.PivotFields("Revenue").Orientation = 4  # xlDataField

wb.save()
app.quit()
```

Use Option B only when the user genuinely needs an interactive/refreshable
PivotTable in the delivered file — otherwise Option A is simpler and has no
Excel-installed dependency.

## 8. Data validation (dropdowns, input restrictions)

```python
from openpyxl.worksheet.datavalidation import DataValidation

dv = DataValidation(type="list", formula1='"Low,Medium,High"', allow_blank=True)
sheet.add_data_validation(dv)
dv.add(sheet["E2:E100"])

# numeric range restriction
dv_num = DataValidation(type="whole", operator="between", formula1=0, formula2=100)
dv_num.error = "Enter a value between 0 and 100"
sheet.add_data_validation(dv_num)
dv_num.add(sheet["F2:F100"])
```

## 9. Conditional formatting beyond basic cell rules

```python
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule, IconSetRule

# heatmap
sheet.conditional_formatting.add(
    "D2:D100",
    ColorScaleRule(start_type="min", start_color="FF0000",
                    end_type="max", end_color="00FF00"),
)

# data bars
sheet.conditional_formatting.add(
    "D2:D100",
    DataBarRule(start_type="min", end_type="max", color="638EC6"),
)
```

## 10. Freezing panes, autofilter, print setup

```python
sheet.freeze_panes = "A2"                       # freeze header row
sheet.auto_filter.ref = sheet.dimensions          # enable filter dropdowns

sheet.print_title_rows = "1:1"                    # repeat header row when printing
sheet.page_setup.orientation = "landscape"
sheet.page_setup.fitToWidth = 1
sheet.print_area = "A1:F50"
```

## 11. CSV / TSV handling

```python
import pandas as pd
df = pd.read_csv("input.csv", dtype=str)          # dtype=str avoids silent numeric coercion of e.g. leading-zero IDs
df.to_excel("output.xlsx", index=False, sheet_name="Data")
```

Watch for: mixed encodings (`encoding="utf-8-sig"` handles a BOM from
Excel-exported CSVs), and delimiter guessing when the source isn't
comma-delimited (`sep=None, engine="python"` auto-detects).

## 12. Verify before delivering (mandatory)

```bash
python friday/skills/xlsx/scripts/recalc_and_check.py output.xlsx
```

This script recalculates (via xlwings if Excel is present, else
LibreOffice), scans for formula errors, and prints a summary. Fix any
reported errors and re-run before delivering.

## 13. Windows-specific gotchas

- File locks: Excel keeps `.xlsx` open exclusively — writing to a path the
  user has open will throw `PermissionError`. Catch it, tell the user to
  close the file.
- `xlwings` COM calls are synchronous and can hang if a dialog box pops up
  in the invisible Excel instance (e.g. a "keep this format?" prompt on
  save) — always set `app.display_alerts = False` before scripted saves:
  ```python
  app.display_alerts = False
  app.screen_updating = False
  ```
- Leftover invisible Excel processes: if a script crashes before
  `app.quit()` runs, a hidden `EXCEL.EXE` process can linger in Task
  Manager and lock files. Wrap COM operations in try/finally:
  ```python
  app = xw.App(visible=False)
  try:
      ...
  finally:
      app.quit()
  ```

## Dependencies

`openpyxl` `pandas` `xlsxwriter` `xlwings` `pywin32` (pip) · MS Excel
(optional but recommended — enables accurate recalc + real PivotTables via
xlwings) · LibreOffice `soffice` (fallback recalc without Excel installed)

## Scripts in this skill

- `scripts/check_env.py` — verifies packages + Excel/LibreOffice presence
- `scripts/recalc_and_check.py` — recalculates formulas (xlwings if
  available, else LibreOffice) and scans for formula errors, printing a
  pass/fail summary
