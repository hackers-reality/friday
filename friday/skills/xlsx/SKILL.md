---
name: xlsx
description: Use this skill whenever creating, reading, editing, or manipulating spreadsheet files
---

# XLSX Creation Guide

## Overview
FRIDAY uses openpyxl to create and manipulate Excel spreadsheets. **Use `create_xlsx_chart()` for embedded chart images, `create_excel()` for data-only sheets.** Spreadsheets include .xlsx, .xlsm, .csv, .tsv files.

All 23 chart types supported in `create_xlsx_chart()`: bar, hbar, grouped_bar, stacked_bar, line, multi_line, area, pie, donut, scatter, bubble, histogram, box, violin, heatmap, radar, candlestick, kmeans, contour, 3d_scatter, 3d_surface, 3d_bar.

## Triggers
- "create a spreadsheet", "make an Excel file", ".xlsx file"
- "add data to a sheet", "format cells", "create pivot table", "add chart"
- Any tabular data that needs organized output
- "CSV file", "TSV file", "export to Excel"

## Libraries
- **openpyxl** — primary library for .xlsx files (read/write)
- Workbook(), load_workbook() — main classes
- Charts, formulas, styles, conditional formatting, data validation

## Code Patterns

### Basic Workbook
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.chart import BarChart, Reference, PieChart, LineChart
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule, DataBarRule

wb = Workbook()
ws = wb.active
ws.title = "Sheet1"

# Headers
headers = ["Name", "Value", "Date", "Status"]
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="00BFFF", end_color="00BFFF", fill_type="solid")
    cell.alignment = Alignment(horizontal="center")

# Data
data = [("Item A", 100, "2026-01-01", "Active"),
        ("Item B", 200, "2026-02-01", "Inactive")]
for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)

# Auto-width columns
for col in range(1, len(headers) + 1):
    max_length = max(len(str(ws.cell(row=r, column=col).value or ""))
                     for r in range(1, len(data) + 2))
    ws.column_dimensions[get_column_letter(col)].width = max_length + 3

# Add chart
chart = BarChart()
chart.title = "Values by Item"
chart.y_axis.title = "Value"
data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data) + 1)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data) + 1)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.shape = 4
ws.add_chart(chart, "E2")

wb.save('output.xlsx')
```

### Conditional Formatting
```python
ws.conditional_formatting.add('A1:D100',
    CellIsRule(operator='greaterThan', formula=['100'],
              fill=PatternFill(start_color='FF6666', end_color='FF6666', fill_type='solid')))
```

## Critical Rules — What to AVOID
- NEVER use string concatenation for cell references — use `get_column_letter()`
- NEVER skip setting column widths — auto-fit is essential
- NEVER leave default sheet name "Sheet" — rename with meaningful names
- NEVER use pandas to_excel() without explicit formatting — it loses styles
- NEVER create charts without title and axis labels
- NEVER use merged cells in data columns (breaks sorting/filtering)
- NEVER skip header row formatting (bold, colored background)
- NEVER use `.value = None` to clear — use `del` or `.value = ""`

## Verification
1. Open the .xlsx file and verify all sheets exist
2. Check column widths are reasonable
3. Verify charts render with data
4. Confirm formulas calculate correctly
5. Check conditional formatting rules apply
6. Verify CSV exports have correct delimiters and encoding
