---
name: xlsx
description: Use this skill whenever creating, reading, editing, or manipulating spreadsheet files
---

# XLSX Creation Guide — Professional Spreadsheet Design

## Overview
FRIDAY uses openpyxl to create production-grade Excel spreadsheets. **Use `create_excel()` for data-only sheets, `create_xlsx_chart()` for embedded chart images.** Spreadsheets include .xlsx, .xlsm, .csv, .tsv files.

Every spreadsheet should be immediately usable by a business user: clear headers, proper column widths, formatted numbers, semantic colors, and frozen title rows.

## QUALITY CRITICAL — READ BEFORE WRITING CODE

YOU ARE A SPREADSHEET DESIGNER. Build every Excel file as if it will be used by a data analyst in a business review. Clean headers, proper formatting, formulas, and visual hierarchy are mandatory.

### EXACT SHEET BLUEPRINT (3 sheets minimum)

Every XLSX MUST have 3+ sheets with this EXACT structure:

**Sheet 1 "Dashboard"**: Title row: merge A1:F1, "DASHBOARD" 16pt bold #0C447C on white bg, center aligned. Row 2: 4 KPI cards in columns A-F (each card = title cell merged 2 rows + value cell merged 2 rows). KPI titles 10pt bold #5F5E5A, values 24pt bold #0C447C. Conditional formatting: Green fill (#C6EFCE) for positive, Red fill (#FFC7CE) for negative on KPI values. Summary table below KPIs (starting row 8): headers in #378ADD white text bold, alternating row colors (#E6F1FB / #FFFFFF), totals row with SUM formula. Frozen at row 8 (below KPIs). Auto-filter on summary table headers.

**Sheet 2 "Data"**: Row 1: headers bold 11pt white on #378ADD bg, center aligned, row height 25pt. Data rows: 10pt #333333, alternating colors (#E6F1FB / #FFFFFF). Column widths: auto-fit to content (set explicitly, not default). Frozen at row 2 (header row visible on scroll). Auto-filter enabled on header row. Number formatting: currency columns = $#,##0.00, percentage columns = 0.0%, general numbers = #,##0. Tab color: #378ADD.

**Sheet 3 "Charts"**: Title row: merge A1:L1, "CHARTS" 14pt bold #0C447C. Embedded bar chart (category comparison): data sourced from Sheet2, title "Price Comparison by Brand" 14pt bold, x-axis labels 10pt, y-axis title "Price ($)" 10pt, data labels on bars, legend right, chart style matches theme (blue/teal palette). Embedded pie chart: distribution by brand, title "Market Share by Brand" 14pt bold, data labels with percentage and category, legend right. Embedded line chart (optional): trend line, title "Price Trends" 14pt bold. All charts sized 14cm x 9cm. Tab color: #1D9E75.

### TYPE SCALE
- Dashboard title: 16pt bold
- KPI values: 24pt bold
- Section headers: 14pt bold
- Table headers: 11pt bold
- Data cells: 10pt regular
- KPI labels: 10pt bold

### COLOR SYSTEM (pick ONE)
- **Blue Professional**: header #378ADD white text, alt rows #E6F1FB/#FFFFFF, accent #0C447C
- **Green Financial**: header #1D9E75 white text, alt rows #E1F5EE/#FFFFFF, accent #0F6E56
- **Dark Dashboard**: header #0C447C white text, alt rows #E8F0FE/#FFFFFF, accent #185FA5

### EVERY SHEET MUST HAVE
- Frozen panes on header row
- Auto-filter on data tables
- Column widths set explicitly (never leave default)
- Number formatting on all numeric cells
- Tab color set
- Row heights appropriate to content (header 25pt, data 18pt)

### ANTI-PATTERNS — OUTPUTS THAT GET REJECTED
- Single sheet with unformatted data dump
- No header styling beyond default bold
- Default column widths truncating content
- Zero charts or visual data representation
- No conditional formatting or formulas
- Missing frozen panes or auto-filter
- Raw unformatted numbers without $/%/commas
- No tab colors or sheet organization
- Data without any formulas (SUM, AVERAGE, etc.)

## Triggers
- "create a spreadsheet", "make an Excel file", ".xlsx file"
- "add data to a sheet", "format cells", "create pivot table", "add chart"
- Any tabular data that needs organized output
- "CSV file", "TSV file", "export to Excel"
- "formulas", "conditional formatting", "data validation"
- "financial report", "data export", "spreadsheet"

## Libraries
- **openpyxl** — primary library for .xlsx files (read/write)
- `Workbook()`, `load_workbook()` — main classes
- Charts, formulas, styles, conditional formatting, data validation, pivot tables

## Complete openpyxl API Reference

### Core Classes
| Class | Module | Purpose |
|-------|--------|---------|
| `Workbook` | `openpyxl` | Create new workbook |
| `load_workbook` | `openpyxl` | Load existing workbook |
| `Worksheet` | `openpyxl.worksheet` | Single sheet |
| `Cell` | `openpyxl.cell` | Single cell |
| `Font` | `openpyxl.styles` | Text formatting |
| `PatternFill` | `openpyxl.styles` | Cell background fill |
| `GradientFill` | `openpyxl.styles` | Gradient background |
| `Border`, `Side` | `openpyxl.styles` | Cell borders |
| `Alignment` | `openpyxl.styles` | Text alignment |
| `Protection` | `openpyxl.styles` | Cell lock/unlock |
| `NamedStyle` | `openpyxl.styles` | Reusable cell style |
| `NumberFormat` | `openpyxl.styles` | Number formatting |
| `DataValidation` | `openpyxl.worksheet.datavalidation` | Input validation |
| `ConditionalFormatting` | `openpyxl.formatting` | Conditional rules |
| `Chart` | `openpyxl.chart` | Chart objects |
| `PivotTable` | `openpyxl.pivot` | Pivot tables |
| `Image` | `openpyxl.drawing.image` | Embedded images |
| `Comment` | `openpyxl.comments` | Cell comments |

### Import Pattern
```python
from openpyxl import Workbook, load_workbook
from openpyxl.styles import (
    Font, PatternFill, GradientFill, Border, Side,
    Alignment, Protection, NamedStyle, numbers
)
from openpyxl.chart import (
    BarChart, LineChart, PieChart, ScatterChart,
    AreaChart, RadarChart, BubbleChart, DoughnutChart,
    StockChart, SurfaceChart, Reference, Series
)
from openpyxl.chart.series import DataPoint
from openpyxl.chart.label import DataLabelList
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.formatting.rule import (
    CellIsRule, FormulaRule, DataBarRule,
    ColorScaleRule, IconSetRule
)
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.page import PageMargins
from openpyxl.drawing.image import Image
from openpyxl.comments import Comment
```

## Design System

### Type Scale
| Role | Size | Weight | Color |
|------|------|--------|-------|
| Title / report header | 16pt | Bold | #2C2C2A (Gray 900) |
| Sheet title row | 14pt | Bold | #FFFFFF on blue |
| Column headers | 11pt | Bold | #FFFFFF on blue |
| Body data | 10pt | Regular | #333333 |
| Small / footnotes | 9pt | Regular | #5F5E5A |
| Section headers | 12pt | Bold | #185FA5 |

### Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Header bg primary | #378ADD | Blue — main sheet headers |
| Header bg secondary | #185FA5 | Dark blue — section headers |
| Header text | #FFFFFF | White on colored headers |
| Body text | #333333 | Dark gray — readable |
| Alternating row 1 | #E6F1FB | Light blue — zebra striping |
| Alternating row 2 | #F1EFE8 | Light gray — alternate |
| Positive | #1D9E75 | Green — good values |
| Negative | #D85A30 | Coral — bad values |
| Warning | #EF9F27 | Amber — warnings |
| Border | #B4B2A9 | Medium gray — borders |
| Grid | #D3D1C7 | Light gray — gridlines |
| Total row text | #2C2C2A | Dark — text |

## Workbook and Worksheet Management

### Creating a New Workbook
```python
wb = Workbook()
ws = wb.active
ws.title = "Dashboard"

# Create additional sheets
ws2 = wb.create_sheet("Raw Data", 0)  # Insert at position 0
ws3 = wb.create_sheet("Summary")      # Appends at end
ws4 = wb.create_sheet("Charts")
```

### Loading an Existing Workbook
```python
wb = load_workbook('input.xlsx')
wb = load_workbook('input.xlsx', data_only=True)   # Values, not formulas
wb = load_workbook('input.xlsx', read_only=True)   # Read-only, faster
wb = load_workbook('input.xlsx', keep_vba=True)    # Keep macros
```

### Worksheet Operations
```python
print(wb.sheetnames)
ws = wb['Dashboard']
ws = wb[wb.sheetnames[0]]
wb.copy_worksheet(ws)
del wb['Sheet1']
wb.move_sheet('Dashboard', offset=-1)
ws.sheet_properties.tabColor = '378ADD'
```

### Column and Row Management
```python
from openpyxl.utils import get_column_letter

# Column widths
ws.column_dimensions['A'].width = 20
ws.column_dimensions[get_column_letter(5)].width = 15

# Row heights
ws.row_dimensions[1].height = 30

# Insert/delete
ws.insert_rows(3, 2)
ws.insert_cols(2, 1)
ws.delete_rows(10, 5)
ws.delete_cols(3, 2)

# Hide
ws.row_dimensions[5].hidden = True
ws.column_dimensions['C'].hidden = True
```

### Merged Cells
```python
ws.merge_cells('A1:D1')
ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=4)
ws.unmerge_cells('A1:D1')
```
**Rules**: Only merge header/title rows. NEVER merge data columns (breaks sorting, filtering). Only top-left cell retains value after merge.

## Cell Styling

### Fonts
```python
from openpyxl.styles import Font

header_font = Font(name='Calibri', size=11, bold=True, italic=False, color='FFFFFF')
body_font = Font(name='Calibri', size=10, color='333333')
title_font = Font(name='Calibri', size=16, bold=True, color='2C2C2A')
section_font = Font(name='Calibri', size=12, bold=True, color='185FA5')
positive_font = Font(name='Calibri', size=10, color='1D9E75', bold=True)
negative_font = Font(name='Calibri', size=10, color='D85A30', bold=True)
warning_font = Font(name='Calibri', size=10, color='EF9F27', bold=True)
```

### Fills
```python
from openpyxl.styles import PatternFill, GradientFill

header_fill = PatternFill(start_color='378ADD', end_color='378ADD', fill_type='solid')
alt_fill = PatternFill(start_color='E6F1FB', end_color='E6F1FB', fill_type='solid')
positive_fill = PatternFill(start_color='EAF3DE', end_color='EAF3DE', fill_type='solid')
negative_fill = PatternFill(start_color='FCEBEB', end_color='FCEBEB', fill_type='solid')
warning_fill = PatternFill(start_color='FAEEDA', end_color='FAEEDA', fill_type='solid')
total_fill = PatternFill(start_color='2C2C2A', end_color='2C2C2A', fill_type='solid')

gradient_fill = GradientFill(
    stop=['378ADD', '185FA5'], gradient_type='linear', degree=90
)
no_fill = PatternFill(fill_type=None)
```

### Borders
```python
from openpyxl.styles import Border, Side

thin_border = Border(
    left=Side(style='thin', color='B4B2A9'),
    right=Side(style='thin', color='B4B2A9'),
    top=Side(style='thin', color='B4B2A9'),
    bottom=Side(style='thin', color='B4B2A9')
)
medium_border = Border(
    left=Side(style='medium', color='378ADD'),
    right=Side(style='medium', color='378ADD'),
    top=Side(style='medium', color='378ADD'),
    bottom=Side(style='medium', color='378ADD')
)
bottom_border = Border(bottom=Side(style='double', color='333333'))
```
Available styles: 'thin', 'medium', 'thick', 'dashed', 'dotted', 'double', 'hair', 'mediumDashed', 'dashDot', 'mediumDashDot', 'dashDotDot', 'mediumDashDotDot', 'slantDashDot'.

### Alignment
```python
from openpyxl.styles import Alignment

center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
left_align = Alignment(horizontal='left', vertical='center')
right_align = Alignment(horizontal='right', vertical='center')
```
Available horizontal: 'general', 'left', 'center', 'right', 'fill', 'justify', 'centerContinuous', 'distributed'.
Available vertical: 'top', 'center', 'bottom', 'justify', 'distributed'.

### Number Formats
```python
NUMBER_FORMATS = {
    'general': 'General',
    'integer': '#,##0',
    'decimal_2': '#,##0.00',
    'currency': '$#,##0.00',
    'currency_int': '$#,##0',
    'percent': '0%',
    'percent_2': '0.00%',
    'date_short': 'YYYY-MM-DD',
    'date_long': 'DD MMM YYYY',
    'date_time': 'YYYY-MM-DD HH:MM',
    'time': 'HH:MM:SS',
    'scientific': '0.00E+00',
    'accounting': '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)',
}
cell.number_format = '$#,##0.00'
```

### Applying Styles Efficiently
```python
for col_idx, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_idx, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = center_align
    cell.border = thin_border
```

## Conditional Formatting

### Color Scales
```python
from openpyxl.formatting.rule import ColorScaleRule

# 2-color scale
ws.conditional_formatting.add('B2:B100',
    ColorScaleRule(start_type='min', start_color='E24B4A',
                   end_type='max', end_color='1D9E75'))

# 3-color scale
ws.conditional_formatting.add('B2:B100',
    ColorScaleRule(start_type='min', start_color='E24B4A',
                   mid_type='percentile', mid_value=50, mid_color='EF9F27',
                   end_type='max', end_color='1D9E75'))
```

### Data Bars
```python
from openpyxl.formatting.rule import DataBarRule

ws.conditional_formatting.add('B2:B100',
    DataBarRule(start_type='min', end_type='max',
                color='378ADD', showValue=True))

ws.conditional_formatting.add('C2:C100',
    DataBarRule(start_type='min', end_type='max',
                color='1D9E75', showValue=True, gradient=True))
```

### Icon Sets
```python
from openpyxl.formatting.rule import IconSetRule

# 3Arrows: up=green, flat=amber, down=red
ws.conditional_formatting.add('B2:B100',
    IconSetRule(icon_style='3Arrows', type='percent', values=[0, 33, 67]))

# 3TrafficLights
ws.conditional_formatting.add('C2:C100',
    IconSetRule(icon_style='3TrafficLights1', type='percent', values=[33, 67]))
```
Available icon styles: '3Arrows', '3ArrowsGray', '3Flags', '3TrafficLights1', '3TrafficLights2', '3Signs', '3Symbols', '3Symbols2', '4Arrows', '4ArrowsGray', '4Rating', '4RedToBlack', '4TrafficLights', '5Arrows', '5ArrowsGray', '5Rating', '5Quarters'.

### Formula-Based Rules
```python
from openpyxl.formatting.rule import CellIsRule, FormulaRule

# Greater than
ws.conditional_formatting.add('B2:B100',
    CellIsRule(operator='greaterThan', formula=['100'],
               fill=PatternFill(start_color='EAF3DE', end_color='EAF3DE', fill_type='solid'),
               font=Font(color='1D9E75', bold=True)))

# Negative values
ws.conditional_formatting.add('B2:B100',
    CellIsRule(operator='lessThan', formula=['0'],
               fill=PatternFill(start_color='FCEBEB', end_color='FCEBEB', fill_type='solid'),
               font=Font(color='E24B4A', bold=True)))

# Highlight entire row based on status
ws.conditional_formatting.add('A2:E100',
    FormulaRule(formula=['$D2="Inactive"'],
               fill=PatternFill(start_color='F1EFE8', end_color='F1EFE8', fill_type='solid'),
               font=Font(color='888780', strike=True)))

# Highlight duplicates
ws.conditional_formatting.add('A2:A100',
    FormulaRule(formula=['COUNTIF($A$2:$A$100,$A2)>1'],
               fill=PatternFill(start_color='FBEAF0', end_color='FBEAF0', fill_type='solid'),
               font=Font(color='D4537E', bold=True)))

# Top 10%
ws.conditional_formatting.add('B2:B100',
    FormulaRule(formula=['B2>=PERCENTILE($B$2:$B$100,0.9)'],
               fill=PatternFill(start_color='1D9E75', end_color='1D9E75', fill_type='solid'),
               font=Font(color='FFFFFF', bold=True)))
```

Available operators: 'equal', 'notEqual', 'greaterThan', 'lessThan', 'greaterThanOrEqual', 'lessThanOrEqual', 'between', 'notBetween', 'containsText', 'notContains', 'beginsWith', 'endsWith'.

## Data Validation

### List Validation (Dropdown)
```python
from openpyxl.worksheet.datavalidation import DataValidation

dv = DataValidation(type="list", formula1='"Active,Inactive,Pending,Archived"',
                    allow_blank=True, showErrorMessage=True, showInputMessage=True)
dv.error = "Please select a valid status"
dv.errorTitle = "Invalid Status"
dv.prompt = "Select a status"
dv.promptTitle = "Row Status"
dv.add('D2:D100')
ws.add_data_validation(dv)
```

### Range Validation
```python
# Number between 0 and 100
dv_num = DataValidation(type="decimal", formula1="0", formula2="100",
                        operator="between", allow_blank=True)
dv_num.error = "Value must be between 0 and 100"
dv_num.add('B2:B100')
ws.add_data_validation(dv_num)

# Date in 2026
dv_date = DataValidation(type="date", formula1="2026-01-01", formula2="2026-12-31",
                         operator="between")
dv_date.add('C2:C100')
ws.add_data_validation(dv_date)

# Text length 1-50
dv_text = DataValidation(type="textLength", formula1="1", formula2="50",
                         operator="between")
dv_text.add('A2:A100')
ws.add_data_validation(dv_text)

# Custom formula
dv_custom = DataValidation(type="custom", formula1="=ISNUMBER(B2)")
dv_custom.add('B2:B100')
ws.add_data_validation(dv_custom)
```

Validation operators: 'between', 'notBetween', 'equal', 'notEqual', 'greaterThan', 'lessThan', 'greaterThanOrEqual', 'lessThanOrEqual'.

## Formulas and Functions

```python
# Basic aggregation
ws['B10'] = '=SUM(B2:B9)'
ws['B11'] = '=AVERAGE(B2:B9)'
ws['B12'] = '=MAX(B2:B9)'
ws['B13'] = '=MIN(B2:B9)'
ws['B14'] = '=COUNT(B2:B9)'
ws['B15'] = '=MEDIAN(B2:B9)'

# Conditional
ws['C10'] = '=COUNTIF(D2:D9,"Active")'
ws['C11'] = '=SUMIF(D2:D9,"Active",B2:B9)'
ws['C12'] = '=COUNTIFS(D2:D9,"Active",B2:B9,">100")'

# Lookup
ws['D10'] = '=VLOOKUP(A2,Sheet2!$A$2:$B$100,2,FALSE)'
ws['D11'] = '=XLOOKUP(A2,Sheet2!$A$2:$A$100,Sheet2!$B$2:$B$100)'
ws['D12'] = '=INDEX(Sheet2!$B$2:$B$100,MATCH(A2,Sheet2!$A$2:$A$100,0))'

# IF statements
ws['E10'] = '=IF(B2>100,"Above Target","Below Target")'
ws['E11'] = '=IFS(B2>150,"Excellent",B2>100,"Good",TRUE,"Poor")'
ws['E12'] = '=IFERROR(VLOOKUP(A2,Sheet2!$A$2:$B$100,2,FALSE),"Not Found")'

# String
ws['F10'] = '=CONCATENATE(A2," ",B2)'
ws['F11'] = '=TEXT(B2,"$#,##0.00")'
ws['F12'] = '=LEFT(A2,3)'

# Date
ws['G10'] = '=TODAY()'
ws['G11'] = '=NOW()'
ws['G12'] = '=YEAR(C2)'

# Math
ws['H10'] = '=ROUND(B2,2)'
ws['H11'] = '=RANDBETWEEN(1,100)'
```

**Important**: Formulas stored as strings with '=' prefix. openpyxl does NOT evaluate formulas — use `data_only=True` to read cached values.

## Named Ranges
```python
from openpyxl.workbook.defined_name import DefinedName

dn = DefinedName("RevenueData", attr_text="Sheet1!$B$2:$B$100")
wb.defined_names.add(dn)

# Scoped named range
dn_scoped = DefinedName("LocalData", attr_text="Sheet1!$A$1:$C$50")
dn_scoped.localSheetId = 0
wb.defined_names.add(dn_scoped)

# Usage in formulas
ws['A20'] = '=SUM(RevenueData)'
```

## Charts

### Bar Chart
```python
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList

chart = BarChart()
chart.type = "col"
chart.title = "Revenue by Quarter"
chart.y_axis.title = "Revenue ($)"
chart.style = 10
chart.width = 20
chart.height = 12

data_ref = Reference(ws, min_col=2, min_row=1, max_row=5, max_col=3)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=5)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)

# Color series
colors = ['378ADD', '1D9E75', '7F77DD', 'D85A30']
for i, s in enumerate(chart.series):
    s.graphicalProperties.solidFill = colors[i % len(colors)]

# Data labels
chart.dataLabels = DataLabelList()
chart.dataLabels.showVal = True
chart.dataLabels.numFmt = '$#,##0'

ws.add_chart(chart, "E2")
```

### Line Chart
```python
chart = LineChart()
chart.title = "Trend Analysis"
chart.y_axis.title = "Value"
chart.style = 10
chart.width = 20
chart.height = 12
data_ref = Reference(ws, min_col=2, min_row=1, max_row=13, max_col=4)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=13)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
for s in chart.series:
    s.graphicalProperties.line.solidFill = '378ADD'
    s.graphicalProperties.line.width = 25000
ws.add_chart(chart, "E2")
```

### Pie Chart
```python
chart = PieChart()
chart.title = "Distribution"
chart.style = 10
chart.width = 16
chart.height = 12
data_ref = Reference(ws, min_col=2, min_row=1, max_row=6)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=6)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
chart.firstSliceAng = 90
colors = ['378ADD', '1D9E75', '7F77DD', 'D85A30', 'EF9F27']
for i, pt in enumerate(chart.series[0].data_points):
    pt.graphicalProperties.solidFill = colors[i % len(colors)]
chart.dataLabels = DataLabelList()
chart.dataLabels.showPercent = True
chart.dataLabels.showCatName = True
ws.add_chart(chart, "E2")
```

### Chart Styling
```python
chart.legend.position = 'b'     # top, bottom, left, right
chart.legend.includeInLayout = False
chart.y_axis.numFmt = '$#,##0'
chart.y_axis.scaling.min = 0
chart.x_axis.tickLblPos = 'low'
chart.title = "Revenue Analysis"
chart.plot_area.graphicalProperties.solidFill = 'FFFFFF'
```

## Freeze Panes, Split Panes, Zoom

```python
ws.freeze_panes = 'A2'       # Row 1 frozen
ws.freeze_panes = 'B1'       # Column A frozen
ws.freeze_panes = 'B2'       # Row 1 + Column A frozen
ws.freeze_panes = None       # No freeze

ws.split_panes = 'C5'        # Split at C5
ws.sheet_view.zoomScale = 100
ws.sheet_view.zoomScaleNormal = 100
```

## Print Settings

```python
from openpyxl.worksheet.page import PageMargins

ws.page_setup.orientation = 'landscape'
ws.page_setup.paperSize = 1  # 1=Letter, 5=Legal, 9=A4
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.page_setup.fitToPage = True
ws.page_setup.scale = 85
ws.print_area = 'A1:H50'
ws.print_title_rows = '1:2'
ws.print_title_cols = 'A:B'

# Margins
ws.page_margins = PageMargins(
    left=0.75, right=0.75, top=0.75, bottom=0.75,
    header=0.5, footer=0.5
)

# Headers and footers
ws.oddHeader.center.text = "&[Tab]"
ws.oddHeader.right.text = "Page &[Page] of &[Pages]"
ws.oddFooter.left.text = "Confidential"
ws.oddFooter.center.text = "&[Date]"
ws.oddFooter.right.text = "&[Time]"
```

### Header/Footer Format Codes
`&[Page]` = page number, `&[Pages]` = total pages, `&[Date]` = date, `&[Time]` = time, `&[File]` = filename, `&[Tab]` = sheet name, `&[Path]` = file path, `&B` = bold, `&I` = italic, `&U` = underline, `&L`/`&C`/`&R` = align.

## Filtering and Auto-Filters

```python
from openpyxl.utils import get_column_letter

# Auto-filter on header row
ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
ws.auto_filter.ref = "A1:E100"

# Remove
ws.auto_filter.ref = None

# Advanced filter
ws.auto_filter.add_sort_condition("B2:B100")
ws.auto_filter.add_filter_column(1, ["Active", "Pending"])
```

## Images in Worksheets

```python
from openpyxl.drawing.image import Image
from io import BytesIO

# From file
img = Image('chart.png')
img.anchor = 'E2'
img.width = 400
img.height = 300
ws.add_image(img)

# From bytes (chart skill integration)
chart_bytes = _make_chart('bar', chart_data, 'png')
img = Image(BytesIO(chart_bytes))
img.anchor = 'A10'
ws.add_image(img)
```

## Hyperlinks

```python
cell = ws['A1']
cell.value = "Open Website"
cell.hyperlink = "https://example.com"
cell.font = Font(color='378ADD', underline='single')

cell = ws['A2']
cell.value = "Send Email"
cell.hyperlink = "mailto:user@example.com"

cell = ws['A3']
cell.value = "Go to Summary"
cell.hyperlink = "#Summary!A1"
```

## Comments and Notes

```python
from openpyxl.comments import Comment

comment = Comment("This value requires quarterly review", "Analyst")
comment.width = 200
comment.height = 100
ws['B2'].comment = comment

# Remove
ws['B2'].comment = None
```

## Protection

### Worksheet Protection
```python
from openpyxl.styles import Protection

# Unlock data entry cells
for row in range(2, 100):
    for col in range(1, 6):
        ws.cell(row=row, column=col).protection = Protection(locked=False)

# Protect the worksheet
ws.protection.sheet = True
ws.protection.password = 'password123'
ws.protection.formatColumns = False
ws.protection.formatRows = False
ws.protection.insertColumns = False
ws.protection.insertRows = False
ws.protection.deleteColumns = False
ws.protection.deleteRows = False
ws.protection.sort = False
ws.protection.autoFilter = False
ws.protection.objects = False
```

### Workbook Protection
```python
wb.security.lockStructure = True
wb.security.lockWindows = True
```

## Tables

```python
from openpyxl.worksheet.table import Table, TableStyleInfo

table = Table(displayName="SalesData", ref="A1:E100")
table.tableStyleInfo = TableStyleInfo(
    name="TableStyleMedium9",
    showFirstColumn=False,
    showLastColumn=False,
    showRowStripes=True,
    showColumnStripes=False
)
ws.add_table(table)
```
Table style names: "TableStyleLight1-21", "TableStyleMedium1-28", "TableStyleDark1-11".

## Performance Optimization

### Write-Only Mode (for large files)
```python
from openpyxl.writer.write_only import WriteOnlyWorkbook

wb = WriteOnlyWorkbook()
ws = wb.create_sheet()
ws.append(["Name", "Value", "Date", "Status"])
for row_data in large_dataset:
    ws.append(row_data)
wb.save('large_output.xlsx')

# Limitations: no cell formatting, no charts, ~50-80% memory reduction
```

### Read-Only Mode (iterate large files)
```python
wb = load_workbook('large.xlsx', read_only=True)
ws = wb.active
for row in ws.iter_rows():
    for cell in row:
        print(cell.value)
wb.close()  # MUST close in read-only mode
```

### Data Only Mode
```python
wb = load_workbook('report.xlsx', data_only=True)
# Returns cached values instead of formulas
```

### Performance Tips
1. Use `write_only=True` for files > 10MB
2. Use `data_only=True` for values, not formulas
3. Use `read_only=True` for reading large files
4. `ws.append()` is faster than `ws.cell()`
5. Disable calculation: `wb.calculation.calcMode = 'manual'`
6. Avoid merged cells in large datasets
7. Use Excel tables for better formula performance
8. Close read-only workbooks with `wb.close()`

## Basic Workbook Pattern (Complete)

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.worksheet.datavalidation import DataValidation

wb = Workbook()
ws = wb.active
ws.title = "Dashboard"

# Styles
header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
header_fill = PatternFill(start_color='378ADD', end_color='378ADD', fill_type='solid')
header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
body_font = Font(name='Calibri', size=10, color='333333')
alt_fill = PatternFill(start_color='E6F1FB', end_color='E6F1FB', fill_type='solid')
thin_border = Border(
    left=Side(style='thin', color='B4B2A9'),
    right=Side(style='thin', color='B4B2A9'),
    top=Side(style='thin', color='B4B2A9'),
    bottom=Side(style='thin', color='B4B2A9')
)

# Column widths
for col, w in {'A': 25, 'B': 18, 'C': 15, 'D': 15, 'E': 20}.items():
    ws.column_dimensions[col].width = w

# Headers
headers = ["Product Name", "Revenue", "Growth %", "Status", "Launch Date"]
for col_idx, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_idx, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align
    cell.border = thin_border

ws.freeze_panes = 'A2'
ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

# Data
data = [
    ("Product Alpha", 150000, 0.15, "Active", "2026-01-15"),
    ("Product Beta", 85000, -0.05, "Inactive", "2026-02-20"),
    ("Product Gamma", 220000, 0.28, "Active", "2026-03-10"),
    ("Product Delta", 45000, 0.08, "Pending", "2026-04-01"),
]
for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.font = body_font
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center') if col_idx > 1 else Alignment(horizontal='left')
        if row_idx % 2 == 0:
            cell.fill = alt_fill
    ws.cell(row=row_idx, column=2).number_format = '$#,##0'
    ws.cell(row=row_idx, column=3).number_format = '0.0%'
    ws.cell(row=row_idx, column=5).number_format = 'YYYY-MM-DD'

# Conditional formatting
ws.conditional_formatting.add('B2:B100',
    ColorScaleRule(start_type='min', start_color='FCEBEB',
                   end_type='max', end_color='EAF3DE'))

# Data validation
dv = DataValidation(type="list", formula1='"Active,Inactive,Pending,Archived"', allow_blank=True)
dv.error = "Select a valid status"
dv.add('D2:D100')
ws.add_data_validation(dv)

wb.save('dashboard.xlsx')
```

## Integration with Chart Skill

```python
# Method 1: Generate chart image and embed
chart_bytes = _make_chart('bar', chart_data, 'png')
img = Image(BytesIO(chart_bytes))
img.anchor = 'A15'
img.width = 600
img.height = 400
ws.add_image(img)

# Method 2: Native openpyxl chart
chart = BarChart()
chart.title = "Revenue"
data_ref = Reference(ws, min_col=2, min_row=1, max_row=6)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=6)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
ws.add_chart(chart, "A15")

# Method 3: Using create_xlsx_chart convenience function
create_xlsx_chart(chart_type='bar', data=chart_data, sheet_name='Charts')
```

## Troubleshooting

### File Won't Open
1. Check file extension is .xlsx not .xls
2. Ensure `wb.save()` is called before file transfer
3. Verify file path exists and is writable
4. Try `wb.save()` with full path

### Formulas Not Calculating
1. Formulas recalculate when opened in Excel
2. Use `data_only=True` to read cached values
3. Check formula syntax (English locale required)
4. Ensure cell references are correct

### Memory Issues
1. Use `write_only=True` for exports
2. Use `read_only=True` for imports
3. Disable calculation: `wb.calculation.calcMode = 'manual'`
4. Use `ws.append()` instead of `ws.cell()`

### Conditional Formatting Not Applied
1. Verify rule range is correct
2. Check formula references are absolute (`$A$1`)
3. Ensure rule is added to worksheet via `ws.conditional_formatting.add()`

### Charts Not Showing
1. Verify data references are valid
2. Ensure chart type is compatible with data
3. Check chart position isn't hidden
4. Verify `ws.add_chart()` was called

## Quality Checklist

### Structure
1. All sheets have meaningful names (not "Sheet1")
2. Column widths are set for all data columns
3. Header row is frozen for tables > 20 rows
4. Auto-filter is applied when table has headers
5. Alternating row colors are applied
6. Title/header row has colored background

### Data
7. All numeric columns have proper number formats
8. No merged cells in data columns
9. Data validation dropdowns work correctly
10. Conditional formatting rules are correctly scoped

### Visual
11. Header font is bold, white on blue background
12. Body text is dark gray (#333333), not black
13. Alternating rows use light blue (#E6F1FB)
14. Positive values are green, negative are coral
15. Borders are thin and gray (#B4B2A9)
16. Font sizes: headers 11pt, body 10pt

### Charts
17. Chart has a clear title
18. Chart axes are labeled
19. Chart data labels are visible
20. Chart style is consistent (style 10)
21. Chart colors match the report color palette

### Printing
22. Page orientation is set
23. Print area is defined
24. Fit to page width (fitToWidth=1)
25. Margins are 0.75in default

### Performance
26. Write-only mode used for files > 10MB
27. Read-only mode for reading large files
28. Memory-efficient data loading

## Critical Rules — What to AVOID
- NEVER use string concatenation for cell references — use `get_column_letter()`
- NEVER skip setting column widths
- NEVER leave default sheet name "Sheet" — rename them
- NEVER use pandas to_excel() without explicit formatting
- NEVER create charts without title and axis labels
- NEVER use merged cells in data columns
- NEVER skip header row formatting
- NEVER use `.value = None` to clear — use `del` or set to ""
- NEVER skip freezing panes for tables with headers
- NEVER forget number formats for currency/percentage/date columns
- NEVER use pure black (#000) for body text — use dark gray (#333)
- NEVER use `ws.cell()` in loops for large datasets — use `ws.append()`
- NEVER forget to close read-only workbooks
- NEVER load full workbook in memory for files > 50MB
- NEVER skip `wb.save()` — no auto-save in openpyxl

## Advanced Cell Operations

### Iterating Over Cells
```python
# Iterate by rows
for row in ws.iter_rows(min_row=1, max_row=10, min_col=1, max_col=5, values_only=False):
    for cell in row:
        print(cell.value, cell.coordinate)

# Iterate by columns
for col in ws.iter_cols(min_row=1, max_row=10, min_col=1, max_col=5):
    for cell in col:
        print(cell.value)

# Values only (faster)
for row in ws.iter_rows(min_row=2, max_row=100, values_only=True):
    name, revenue, growth, status, date = row
    print(name, revenue)
```

### Cell Ranges and Slicing
```python
# Access cell range
cell_range = ws['A1:E100']

# Access specific cells
cell = ws.cell(row=5, column=3)

# Row and column objects
row_data = ws[2]           # Entire row 2
col_data = ws['B']         # Entire column B
col_range = ws['B:D']      # Columns B through D
row_range = ws['2:5']      # Rows 2 through 5

# Max row/col
last_row = ws.max_row
last_col = ws.max_column

# Delete cells and shift
ws.delete_cells('A1', shift='up')     # Shift cells up
ws.delete_cells('A1', shift='left')   # Shift cells left
```

### Clearing Cells
```python
# Clear cell content
ws['A1'].value = None

# Clear cell completely (content + formatting)
from openpyxl.cell import Cell
from openpyxl.utils import get_column_letter

def clear_cell(ws, cell_reference):
    cell = ws[cell_reference]
    cell.value = None
    cell.font = Font()
    cell.fill = PatternFill()
    cell.border = Border()
    cell.alignment = Alignment()
    cell.number_format = 'General'
    cell.protection = Protection()

# Clear entire row
for cell in ws[5]:
    cell.value = None

# Clear sheet data
for row in ws.iter_rows():
    for cell in row:
        cell.value = None
```

## Pivot Tables (Advanced)

### Creating Pivot Tables
```python
from openpyxl.pivot.table import PivotTable, PivotField, PivotFilter
from openpyxl.pivot.fields import Missing
from openpyxl.worksheet.table import Table

# Step 1: Create source data table
table = Table(displayName="SourceData", ref="A1:E100")
table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2")
ws.add_table(table)

# Step 2: Create pivot cache (cache is automatically created from table)
# Note: openpyxl pivot table support is limited.
# For production pivot tables, consider using:
# - xlwings (Windows, Excel automation)
# - win32com (Windows, full Excel API)
# - Creating pivot table from template
```

### Template-Based Pivot Table
```python
# Create pivot table from template with pre-defined structure
import shutil

# Copy template, then fill with data
shutil.copy2('pivot_template.xlsx', 'report.xlsx')
wb = load_workbook('report.xlsx')
ws = wb['PivotData']
# Write data to the pivot source range
# Refresh pivot: must be done manually when file is opened in Excel
```

## CSV and TSV Operations

### Reading CSV
```python
import csv

# Read CSV and write to worksheet
with open('data.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row_idx, row in enumerate(reader, 1):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
```

### Writing CSV
```python
import csv

# Write from worksheet to CSV
with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in ws.iter_rows(values_only=True):
        writer.writerow(row)
```

### Reading/TSV
```python
# TSV (tab-separated)
with open('data.tsv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    for row_idx, row in enumerate(reader, 1):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
```

## Advanced Formatting Patterns

### Alternating Row Colors with Group Headers
```python
def write_grouped_table(ws, headers, groups, start_row=1):
    """Write grouped data with section headers and alternating colors.
    groups: [(group_name, [row1, row2, ...]), ...]
    """
    alt_colors = [
        PatternFill(start_color='E6F1FB', end_color='E6F1FB', fill_type='solid'),
        PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid'),
    ]
    row = start_row

    # Write headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color='FFFFFF', size=11)
        cell.fill = PatternFill(start_color='378ADD', end_color='378ADD', fill_type='solid')
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    row += 1

    color_idx = 0
    for group_name, rows in groups:
        # Group header
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = PatternFill(start_color='185FA5', end_color='185FA5', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF', size=10)
            cell.border = thin_border
        ws.cell(row=row, column=1, value=group_name)
        row += 1

        # Data rows
        for data_row in rows:
            for col, value in enumerate(data_row, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.font = Font(size=10, color='333333')
                cell.fill = alt_colors[color_idx % 2]
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center' if col > 1 else 'left')
            color_idx += 1
            row += 1

    return row
```

### Conditional Formatting for Entire Worksheet
```python
def add_professional_formatting(ws, data_range, header_row=True):
    """Apply professional formatting to an entire data range."""
    # Remove gridlines
    ws.sheet_view.showGridLines = False

    # Style 1: Column widths auto-fit (approximate)
    for col_cells in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length + 3, 40)

    # Style 2: Thin borders on all data cells
    for row in ws[data_range]:
        for cell in row:
            cell.border = thin_border

    # Style 3: Alternate row colors
    start = 2 if header_row else 1
    alt_fills = [
        PatternFill(start_color='E6F1FB', end_color='E6F1FB', fill_type='solid'),
        PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid'),
    ]
    for i, row in enumerate(ws.iter_rows(min_row=start, max_row=ws.max_row)):
        for cell in row:
            cell.fill = alt_fills[i % 2]
```

## Utility Functions

### Auto-Fit Column Widths
```python
def auto_fit_columns(ws, min_width=8, max_width=50):
    """Auto-fit column widths based on content."""
    for col_cells in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            try:
                val = str(cell.value) if cell.value else ""
                max_length = max(max_length, len(val))
            except:
                pass
        adjusted_width = min(max(max_length + 2, min_width), max_width)
        ws.column_dimensions[col_letter].width = adjusted_width
```

### Color Scale by Value
```python
def add_heatmap(ws, cell_range, min_color='FCEBEB', max_color='EAF3DE'):
    """Add a 2-color heatmap conditional format."""
    ws.conditional_formatting.add(cell_range,
        ColorScaleRule(start_type='min', start_color=min_color,
                       end_type='max', end_color=max_color))
```

### Data Bar by Column
```python
def add_data_bars(ws, column_letter, data_start=2, data_end=100, color='378ADD'):
    """Add data bars to a column."""
    cell_range = f'{column_letter}{data_start}:{column_letter}{data_end}'
    ws.conditional_formatting.add(cell_range,
        DataBarRule(start_type='min', end_type='max',
                    color=color, showValue=True))
```

## Error Handling Patterns

### Safe Cell Reading
```python
def safe_read(ws, row, col, default=""):
    """Read cell value safely, returning default if empty or error."""
    try:
        val = ws.cell(row=row, column=col).value
        return val if val is not None else default
    except:
        return default

def safe_write(ws, row, col, value, font=None, fill=None):
    """Write cell value with error handling."""
    try:
        cell = ws.cell(row=row, column=col, value=value)
        if font:
            cell.font = font
        if fill:
            cell.fill = fill
        return True
    except:
        return False
```

### Workbook Validation
```python
def validate_workbook(wb):
    """Check workbook for common issues."""
    issues = []
    for ws in wb.worksheets:
        if ws.title == "Sheet":
            issues.append(f"Sheet '{ws.title}' has default name")
        if ws.freeze_panes is None and ws.max_row > 20:
            issues.append(f"Sheet '{ws.title}' has no freeze panes")
        if ws.auto_filter.ref is None and ws.max_row > 5:
            issues.append(f"Sheet '{ws.title}' has no auto-filter")
        if ws.column_dimensions:
            # Check if any column widths are set
            if not any(dim.width for dim in ws.column_dimensions.values() if dim.width):
                issues.append(f"Sheet '{ws.title}' has no column widths")
    return issues
```

## Integration Examples

### Financial Report Pattern
```python
def create_financial_report(wb, data, period):
    """Create a standardized financial report with formatting."""
    ws = wb.active
    ws.title = f"{period} Financials"

    # Title
    ws.merge_cells('A1:F1')
    ws['A1'] = f"Financial Report - {period}"
    ws['A1'].font = Font(name='Calibri', size=16, bold=True, color='2C2C2A')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 35

    # Headers
    headers = ['Category', 'Budget', 'Actual', 'Variance', 'Variance %', 'Status']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
        cell.fill = PatternFill(start_color='185FA5', end_color='185FA5', fill_type='solid')
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    ws.freeze_panes = 'A4'

    # Data
    for i, row in enumerate(data, 4):
        for j, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=j, value=val)
            cell.font = Font(name='Calibri', size=10)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center')
            if i % 2 == 0:
                cell.fill = PatternFill(start_color='E6F1FB', end_color='E6F1FB', fill_type='solid')

        # Format variance columns
        ws.cell(row=i, column=2).number_format = '$#,##0'
        ws.cell(row=i, column=3).number_format = '$#,##0'
        ws.cell(row=i, column=4).number_format = '$#,##0'
        ws.cell(row=i, column=5).number_format = '0.0%'

        # Color status cell
        status = row[5]
        if status == 'Over Budget':
            ws.cell(row=i, column=6).font = Font(color='D85A30', bold=True, size=10)
            ws.cell(row=i, column=6).fill = PatternFill(start_color='FCEBEB', end_color='FCEBEB', fill_type='solid')
        elif status == 'Under Budget':
            ws.cell(row=i, column=6).font = Font(color='1D9E75', bold=True, size=10)
            ws.cell(row=i, column=6).fill = PatternFill(start_color='EAF3DE', end_color='EAF3DE', fill_type='solid')

    # Total row
    total_row = 4 + len(data)
    for col in range(1, 7):
        cell = ws.cell(row=total_row, column=col)
        cell.font = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
        cell.fill = PatternFill(start_color='2C2C2A', end_color='2C2C2A', fill_type='solid')
        cell.border = thin_border
    ws.cell(row=total_row, column=1, value='Total')
    ws.cell(row=total_row, column=2, value=f'=SUM(B4:B{total_row-1})')
    ws.cell(row=total_row, column=3, value=f'=SUM(C4:C{total_row-1})')

    # Auto-fit
    auto_fit_columns(ws)

    return ws
```

### Export Summary Statistics
```python
def write_summary_stats(ws, data_start, data_end, value_col='B'):
    """Write summary statistics below data range."""
    stats_start = data_end + 2
    stats = [
        ('Count', f'=COUNT({value_col}{data_start}:{value_col}{data_end})'),
        ('Sum', f'=SUM({value_col}{data_start}:{value_col}{data_end})'),
        ('Average', f'=AVERAGE({value_col}{data_start}:{value_col}{data_end})'),
        ('Median', f'=MEDIAN({value_col}{data_start}:{value_col}{data_end})'),
        ('Min', f'=MIN({value_col}{data_start}:{value_col}{data_end})'),
        ('Max', f'=MAX({value_col}{data_start}:{value_col}{data_end})'),
        ('Std Dev', f'=STDEV({value_col}{data_start}:{value_col}{data_end})'),
    ]
    for i, (label, formula) in enumerate(stats):
        row = stats_start + i
        ws.cell(row=row, column=1, value=label).font = Font(bold=True, size=10)
        ws.cell(row=row, column=2, value=formula).font = Font(size=10)
        ws.cell(row=row, column=2).number_format = '#,##0.00'
