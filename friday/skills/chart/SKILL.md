---
name: chart
description: Use this skill when creating data charts, graphs, and visualizations
---

# Charts & Graphs Creation Guide

## Overview
FRIDAY creates charts and graphs using Python visualization libraries. **All 23 chart types are accessible via `_make_chart()`, `create_pdf()`, `create_docx()`, `create_pptx()`, and `create_xlsx_chart()`.** Choose the library based on output context:
- **Inline/Markdown**: SVG (direct string generation) or matplotlib
- **In presentations**: python-pptx chart API
- **Interactive**: plotly (HTML output)
- **In documents**: matplotlib embedded via python-docx, or use `create_docx(sections=[{"type":"chart",...}])`
- **In PDFs**: use `create_pdf(sections=[{"type":"chart",...}])` with built-in chart rendering
- **In Excel**: use `create_xlsx_chart()` for data sheets + chart image sheets

## All 23 Chart Types

| `chart_type` | Description | Data Params |
|-------------|-------------|-------------|
| `bar` | Vertical bar chart | `data` (categories), `data2` (values) |
| `hbar` | Horizontal bar chart | `data` (categories), `data2` (values) |
| `grouped_bar` | Grouped bar chart (multi-series) | `data` (cats), `data2`/`data3`/`data4` (series) |
| `stacked_bar` | Stacked bar chart | `data` (cats), `data2`/`data3` (layers) |
| `line` | Line chart | `data` (x), `data2` (y) |
| `multi_line` | Multiple line series | `data` (x labels), `data2`/`data3` (series) |
| `area` | Area fill chart | `data` (x), `data2` (y) |
| `pie` | Pie chart | `data` (labels), `data2` (values) |
| `donut` | Donut chart | `data` (labels), `data2` (values) |
| `scatter` | Scatter plot | `data` (x), `data2` (y) |
| `bubble` | Bubble chart | `data` (x), `data2` (y), `data3` (size) |
| `histogram` | Histogram | `data` (values) |
| `box` | Box plot | `data` (values per category) |
| `violin` | Violin plot | `data` (values per category) |
| `heatmap` | Heatmap (2D color grid) | `data` (2D array) |
| `radar` | Radar / spider chart | `data` (labels), `data2` (values) |
| `candlestick` | OHLC candlestick chart | `data` (dates), `data2` (OHLC tuples) |
| `kmeans` | K-means clustering scatter | `data` (x), `data2` (y), `data3` (k clusters) |
| `contour` | Contour plot | `data` (x), `data2` (y), `data3` (z) |
| `3d_scatter` | 3D scatter plot | `data` (x), `data2` (y), `data3` (z) |
| `3d_surface` | 3D surface plot | `data` (x), `data2` (y), `data3` (z) |
| `3d_bar` | 3D bar chart | `data` (x cats), `data2` (z cats), `data3` (values) |

## Triggers
- "chart", "graph", "plot", "visualize data"
- "bar chart", "line graph", "pie chart", "scatter plot"
- "distribution", "trend", "comparison"
- "data visualization", "dashboard"

## Libraries
- **matplotlib** — for static charts in any context
- **plotly** — for interactive charts in HTML
- **python-pptx chart API** — for charts in presentations
- **SVG (direct)** — for inline diagrams

## Matplotlib Code Patterns

### Basic Chart
```python
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Style
plt.style.use('seaborn-v0_8-darkgrid')
fig, ax = plt.subplots(figsize=(10, 6))

# Data
categories = ['Q1', 'Q2', 'Q3', 'Q4']
values = [100, 200, 150, 300]

# Bar chart
bars = ax.bar(categories, values, color=['#378ADD', '#1D9E75', '#D85A30', '#534AB7'],
              edgecolor='white', linewidth=1.5)

# Labels
ax.set_title('Quarterly Results', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Quarter', fontsize=12)
ax.set_ylabel('Value', fontsize=12)

# Value labels on bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}', ha='center', va='bottom', fontsize=11)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('chart.png', dpi=150, bbox_inches='tight')
plt.close()
```

### Line Chart with Multiple Series
```python
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(1, 13)
ax.plot(x, revenue, 'o-', color='#378ADD', linewidth=2.5, markersize=6, label='Revenue')
ax.plot(x, costs, 's--', color='#D85A30', linewidth=2, markersize=5, label='Costs')
ax.fill_between(x, revenue, costs, alpha=0.1, color='#1D9E75')
ax.legend(fontsize=11)
ax.set_xlabel('Month')
ax.set_ylabel('Amount ($)')
ax.set_title('Revenue vs Costs - 2026')
```

### Pie Chart
```python
fig, ax = plt.subplots(figsize=(8, 8))
sizes = [35, 25, 20, 15, 5]
labels = ['Category A', 'Category B', 'Category C', 'Category D', 'Other']
colors = ['#378ADD', '#1D9E75', '#D85A30', '#534AB7', '#B4B2A9']
explode = (0.05, 0.05, 0.05, 0.05, 0.05)

wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels,
                                   colors=colors, autopct='%1.1f%%',
                                   startangle=90, pctdistance=0.85)
for t in autotexts: t.set_fontsize(11)
for t in texts: t.set_fontsize(12)
ax.set_title('Distribution by Category', fontsize=16, fontweight='bold', pad=20)
```

## Plotly for Interactive Charts
```python
import plotly.express as px
import plotly.graph_objects as go

# Simple bar
fig = px.bar(x=categories, y=values, title='Quarterly Results',
             color=categories, color_discrete_sequence=['#378ADD', '#1D9E75', '#D85A30', '#534AB7'])
fig.show()

# Save as HTML
fig.write_html('chart.html')
```

## Python-PPTX Chart
```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = CategoryChartData()
chart_data.categories = categories
chart_data.add_series('Values', values)
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1), Inches(2), Inches(8), Inches(5),
    chart_data
).chart
chart.has_legend = True
chart.chart_title.has_text_frame = True
chart.chart_title.text_frame.text = "Title"
```

## Critical Rules — What to AVOID
- NEVER use default matplotlib colors — always specify semantic color palette
- NEVER create charts without titles and axis labels
- NEVER save at resolution below 150 DPI
- NEVER skip closing plt (plt.close()) — causes memory leaks
- NEVER use more than 6 colors in a single chart
- NEVER create 3D charts — they distort perception of data
- NEVER overlay too many data series (max 4 per chart)
- NEVER use rainbow colormaps for sequential data
- NEVER embed raw matplotlib figures in HTML — use plotly for interactivity

## Color Palette for Charts
- Primary data: #378ADD (blue), #1D9E75 (teal), #D85A30 (coral), #534AB7 (purple)
- Secondary data: #E24B4A (red), #639922 (green), #EF9F27 (amber)
- Background grid: #F1EFE8 (light) / #2C2C2A (dark)
- Axis lines: #888780

## Verification
1. Verify all axis labels are readable
2. Check data values match the source data
3. Verify legend entries match chart colors
4. Confirm chart size is appropriate for output context
5. For presentations: verify chart fits within slide boundaries
