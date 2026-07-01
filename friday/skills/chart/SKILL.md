---
name: chart
description: Use this skill when creating data charts, graphs, and visualizations
---

# Charts & Graphs Creation Guide — Professional Data Visualization

## Overview
FRIDAY creates charts and graphs using Python visualization libraries. **All 23 chart types are accessible via `_make_chart()`, `create_pdf()`, `create_docx()`, `create_pptx()`, and `create_xlsx_chart()`.** Choose the library based on output context:
- **Inline/Markdown**: SVG (direct string generation) or matplotlib
- **In presentations**: python-pptx chart API
- **Interactive**: plotly (HTML output)
- **In documents**: matplotlib embedded via python-docx, or use `create_docx(sections=[{"type":"chart",...}])`
- **In PDFs**: use `create_pdf(sections=[{"type":"chart",...}])` with built-in chart rendering
- **In Excel**: use `create_xlsx_chart()` for data sheets + chart image sheets

## Design Principles

### Data-Ink Ratio
The data-ink ratio = (data-ink) / (total ink used to print the chart). Maximize data-ink, minimize non-data ink:
- Remove unnecessary gridlines (keep only horizontal reference lines)
- Remove chart borders and background colors
- Remove redundant labels
- Remove decorative gradients and 3D effects
- Remove unnecessary axis ticks

### Chart Junk Avoidance
Chart junk = visual elements that distract from data:
- **Moiré patterns**: avoid cross-hatching, dense patterns
- **Grid overload**: max 4-5 horizontal gridlines
- **3D perspective**: NEVER use 3D for 2D data — distorts perception
- **Duck decoration**: every element must serve data communication
- **Gradients**: avoid in bars/shapes unless encoding a second variable

### Proper Axis Labeling
- Always include units in axis labels: "Revenue ($M)", not just "Revenue"
- Use comma-separated thousands: "1,234" not "1234"
- Rotate x-axis labels 45° when categories are long
- Never abbreviate months/dates without legend
- Start y-axis at 0 for bar charts (but not necessarily for line charts)
- Use consistent decimal precision across all labels

### Legend Placement
- **Single chart**: legend above or below, not inside data area
- **Multi-chart**: consistent position across all charts
- **Small multiples**: shared legend outside the grid
- **Interactive**: collapsible/overlay legend
- Never use legend when only one series exists
- Order legend entries to match visual order (left-to-right or top-to-bottom)

## Interactive vs Static Charts

| Aspect | Static (matplotlib/SVG) | Interactive (plotly) |
|--------|------------------------|---------------------|
| Output | PNG, SVG, embedded in PDF/DOCX | HTML, embedded in web pages |
| Hover data | Data labels or none | Rich tooltips |
| Zoom | Not available | Pan, zoom, select |
| Animation | GIF/MP4 export | Built-in transitions |
| File size | Small (10-100KB) | Larger (100KB-2MB) |
| Accessibility | Screen reader via alt text | Limited screen reader support |
| Offline use | Always works | Needs browser/JS |
| Responsiveness | Fixed size | Auto-resize with layout |

## Color Theory for Data Visualization

### Color Perception Principles
1. **Hue**: Use for categorical data (different types/classes)
2. **Saturation**: Use for intensity/importance
3. **Lightness**: Use for sequential data (low to high)
4. **Temperature**: Warm = high/active, Cool = low/passive

### Colorblind Accessibility (Deuteranopia, Protanopia, Tritanopia)
- Avoid: red-green pairs, green-blue pairs, purple-blue pairs
- Use shape + color redundancy (markers + color)
- Test with Color Oracle or Coblis simulator
- **IBM Carbon colorblind-safe palette**:
  - `#648FFF` (Blue) — categorical
  - `#785EF0` (Purple) — categorical
  - `#DC267F` (Pink) — categorical
  - `#FE6100` (Orange) — categorical
  - `#FFB000` (Amber) — categorical
  - `#009E73` (Green) — categorical
  - `#004D43` (Dark Teal) — categorical
  - `#F0E442` (Yellow) — categorical
  - `#56B4E9` (Light Blue) — categorical

### Semantic Color Mapping
- **Blue** (#378ADD): Primary data, information
- **Green** (#1D9E75): Positive, growth, success
- **Red/Coral** (#D85A30): Negative, decline, warning
- **Amber** (#EF9F27): Caution, neutral
- **Purple** (#534AB7): Distinct category, premium
- **Pink** (#D4537E): Highlight, alert
- **Teal** (#0F6E56): Secondary data, supporting
- **Gray** (#888780): Structure, background, reference

## Responsive Sizing

### Matplotlib
```python
fig, ax = plt.subplots(figsize=(10, 6))  # 10:6 ratio
fig.set_size_inches(8, 4.8)  # Resize after creation
```

### Plotly
```python
fig.update_layout(
    autosize=True,
    width=None,
    height=None,
    margin=dict(l=50, r=50, t=80, b=50)
)
```

### SVG
```svg
viewBox="0 0 680 400"
style="width: 100%; max-width: 680px; height: auto;"
```

### Consistent Sizing Rules
- Dashboard tiles: 4:3 ratio
- Full-width charts: 16:9 ratio
- Tall charts (histogram): 3:4 ratio
- Square charts (pie/donut): 1:1 ratio
- Wide charts (timeline): 2:1 ratio

## Annotations and Text Overlays

### Matplotlib
```python
# Arrow annotation
ax.annotate('Peak', xy=(5, 300), xytext=(3, 350),
            arrowprops=dict(arrowstyle='->', color='#FE6100', lw=2),
            fontsize=11, color='#FE6100', fontweight='bold')

# Text box
ax.text(0.02, 0.98, 'Key Insight', transform=ax.transAxes,
        fontsize=12, verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#F1EFE8', edgecolor='#888780'))

# Highlight region
ax.axvspan(6, 9, alpha=0.1, color='#FE6100')
ax.axhline(y=100, color='#D85A30', linestyle='--', linewidth=1, alpha=0.7)
```

### Plotly
```python
fig.add_annotation(
    x=5, y=300,
    text="Peak",
    showarrow=True,
    arrowhead=2,
    ax=0, ay=-40,
    font=dict(size=12, color='#FE6100')
)
fig.add_vline(x=6, line_dash="dash", line_color="#D85A30", opacity=0.5)
fig.add_hline(y=100, line_dash="dot", line_color="#1D9E75", opacity=0.5)
```

## Multiple Subplots and Dashboards

### Matplotlib Subplots
```python
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
axes = axes.flatten()

# Chart 1: Bar
axes[0].bar(categories, values, color=CBF_PALETTE[:len(categories)])
axes[0].set_title('Revenue by Quarter')

# Chart 2: Line
axes[1].plot(x, revenue, color=CBF_PALETTE[0])
axes[1].plot(x, costs, color=CBF_PALETTE[2])
axes[1].set_title('Revenue vs Costs')

# Chart 3: Pie
axes[2].pie(sizes, labels=labels, colors=CBF_PALETTE, autopct='%1.1f%%')
axes[2].set_title('Distribution')

# Chart 4: Scatter
axes[3].scatter(x, y, c=CBF_PALETTE[0], s=50, alpha=0.6)
axes[3].set_title('Correlation')

plt.tight_layout(pad=3.0)
```

### Plotly Dashboard
```python
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Revenue by Quarter', 'Revenue vs Costs', 'Distribution', 'Correlation'),
    specs=[[{'type': 'bar'}, {'type': 'scatter'}],
           [{'type': 'pie'}, {'type': 'scatter'}]]
)
fig.add_trace(go.Bar(x=categories, y=values), row=1, col=1)
fig.add_trace(go.Scatter(x=x, y=revenue), row=1, col=2)
fig.add_trace(go.Pie(labels=labels, values=sizes), row=2, col=1)
fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='markers'), row=2, col=2)
fig.update_layout(height=800, width=1200, showlegend=False)
```

## Animations and Transitions

### Matplotlib Animation (to GIF/MP4)
```python
import matplotlib.animation as animation

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(10)
bars = ax.bar(x, np.zeros(10), color=CBF_PALETTE[0])

def update(frame):
    values = np.random.randint(1, 100, 10)
    for bar, val in zip(bars, values):
        bar.set_height(val)
    ax.set_title(f'Frame {frame+1}')
    return bars

ani = animation.FuncAnimation(fig, update, frames=20, interval=200, blit=True)
ani.save('animation.gif', writer='pillow', fps=5, dpi=100)
ani.save('animation.mp4', writer='ffmpeg', fps=5, dpi=100)
plt.close()
```

### Plotly Animation
```python
import plotly.express as px

df = px.data.gapminder()
fig = px.scatter(
    df, x='gdpPercap', y='lifeExp', size='pop', color='continent',
    animation_frame='year', animation_group='country',
    log_x=True, size_max=55,
    range_x=[100, 100000], range_y=[25, 90],
    title='Gapminder: GDP vs Life Expectancy (1952-2007)',
    color_discrete_sequence=CBF_PALETTE
)
fig.update_layout(hovermode='x unified')
fig.write_html('animated_scatter.html')
```

## Export Formats

### PNG (Static Raster)
```python
plt.savefig('chart.png', dpi=150, bbox_inches='tight', facecolor='white')
# For high-quality print
plt.savefig('chart_print.png', dpi=300, bbox_inches='tight', facecolor='white')
```

### SVG (Vector)
```python
plt.savefig('chart.svg', format='svg', bbox_inches='tight')
# Or generate SVG directly (preferred for inline)
```

### HTML (Interactive)
```python
fig.write_html('chart.html', include_plotlyjs='cdn', full_html=False)
fig.write_html('chart_full.html', include_plotlyjs='directory')
fig.to_html(full_html=False, include_plotlyjs='cdn')  # For inline embedding
```

### PDF (Vector)
```python
plt.savefig('chart.pdf', format='pdf', bbox_inches='tight')
# Or provide as section to create_pdf:
create_pdf(sections=[{'type': 'chart', 'chart_type': 'bar', 'data': {...}}])
```

### Integrated Export (using create_pdf / create_docx / create_pptx)
```python
# PDF with embedded chart
create_pdf(sections=[
    {'type': 'text', 'content': '# Quarterly Report'},
    {'type': 'chart', 'chart_type': 'bar', 'data': {'categories': categories, 'values': values},
     'title': 'Q1-Q4 Revenue'},
    {'type': 'chart', 'chart_type': 'line', 'data': {'x': x, 'series': [{'name': 'Revenue', 'y': revenue}]}}
])

# DOCX with embedded chart
create_docx(sections=[
    {'type': 'text', 'content': '## Revenue Analysis'},
    {'type': 'chart', 'chart_type': 'grouped_bar', 'data': {...}, 'width': 14, 'height': 8}
])

# PPTX with chart slide
create_pptx(sections=[
    {'type': 'title_slide', 'title': 'Q4 Review'},
    {'type': 'chart_slide', 'chart_type': 'pie', 'data': {...}}
])
```

## All 23 Chart Types

### Chart Type Quick Reference

| `chart_type` | Description | Best For | Data Shape | Min Data |
|-------------|-------------|----------|------------|----------|
| `bar` | Vertical bar chart | Comparing categories | 1D categorical + numeric | 2+ categories |
| `hbar` | Horizontal bar chart | Long category names, rankings | 1D categorical + numeric | 2+ categories |
| `grouped_bar` | Grouped bar (multi-series) | Comparing sub-groups across categories | 2D categorical + numeric | 2+ groups x 2+ series |
| `stacked_bar` | Stacked bar | Part-to-whole across categories | 2D categorical + numeric | 2+ groups x 2+ series |
| `line` | Line chart | Trends over time | Time series + numeric | 3+ time points |
| `multi_line` | Multiple line series | Comparing trends | Time series + multiple numeric | 3+ points x 2+ series |
| `area` | Area fill chart | Volume over time | Time series + numeric | 3+ time points |
| `pie` | Pie chart | Simple proportions (max 5 slices) | Categorical + proportion | 2-5 slices |
| `donut` | Donut chart | Proportions with center label | Categorical + proportion | 2-5 slices |
| `scatter` | Scatter plot | Correlation between 2 variables | 2 numeric variables | 5+ points |
| `bubble` | Bubble chart | 3 variables (x, y, size) | 3 numeric variables | 5+ points |
| `histogram` | Histogram | Distribution of values | 1 numeric variable | 10+ values |
| `box` | Box plot | Distribution with outliers | 1+ numeric variables | 5+ values per group |
| `violin` | Violin plot | Distribution shape + density | 1+ numeric variables | 10+ values per group |
| `heatmap` | Heatmap (2D color grid) | Matrix values, correlation | 2D numeric matrix | 3x3+ grid |
| `radar` | Radar / spider chart | Multi-attribute comparison | Multiple numeric attributes | 3+ attributes x 2+ entities |
| `candlestick` | OHLC candlestick | Financial price data | OHLC (open, high, low, close) | 5+ time periods |
| `kmeans` | K-means clustering | Cluster visualization | 2D numeric + cluster labels | 10+ points |
| `contour` | Contour plot | 3D surface contours | 2D grid of Z values | 5x5+ grid |
| `3d_scatter` | 3D scatter plot | 3-variable relationships | 3 numeric variables | 10+ points |
| `3d_surface` | 3D surface plot | Continuous 3D data | 2D grid of Z values | 10x10+ grid |
| `3d_bar` | 3D bar chart | 3-category comparison | 3 categorical + numeric | 2x2x2+ grid |

### 1. Bar Chart
**Use when**: Comparing values across distinct categories (sales by quarter, population by country).

**Data requirements**: Categories (list of strings) and values (list of numbers). Min 2, max 20 categories.

**Plotly**:
```python
fig = px.bar(x=categories, y=values, color=categories,
             color_discrete_sequence=CBF_PALETTE, text=values,
             title='Revenue by Quarter')
fig.update_traces(textposition='outside', textfont_size=11)
fig.update_layout(xaxis_title='Quarter', yaxis_title='Revenue ($)',
                  showlegend=False, plot_bgcolor='white')
fig.write_html('bar_chart.html')
```

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
colors = [CBF_PALETTE[i % len(CBF_PALETTE)] for i in range(len(categories))]
bars = ax.bar(categories, values, color=colors, edgecolor='white', linewidth=1.5, width=0.65)
ax.set_title('Quarterly Revenue', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Quarter', fontsize=12)
ax.set_ylabel('Revenue ($)', fontsize=12)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('$%d'))
ax.set_ylim(0, max(values) * 1.15)
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height, f'${int(height):,}',
            ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('bar_chart.png', dpi=150, bbox_inches='tight')
plt.close()
```

**Customization options**:
- `width`: Bar width (0.4-0.8, default 0.65)
- `edgecolor`: Bar border color
- `color`: Single color or list of colors
- `alpha`: Transparency (0-1)
- `orientation`: 'vertical' or 'horizontal'
- `error_y`: Error bars (dict with 'type', 'array')

### 2. Horizontal Bar Chart (hbar)
**Use when**: Category names are long, comparing rankings, or you have many categories.

**Data requirements**: Same as bar chart but categories plotted on y-axis.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
categories.reverse()
values.reverse()
bars = ax.barh(categories, values, color=CBF_PALETTE[:len(categories)],
               edgecolor='white', linewidth=1.5, height=0.6)
ax.set_title('Revenue by Quarter', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Revenue ($)', fontsize=12)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('$%d'))
for bar in bars:
    width = bar.get_width()
    ax.text(width + 5, bar.get_y() + bar.get_height()/2., f'${int(width):,}',
            ha='left', va='center', fontsize=10, fontweight='bold')
ax.invert_yaxis()
plt.tight_layout()
```

**Plotly**:
```python
fig = px.bar(y=categories, x=values, orientation='h', text=values,
             color=categories, color_discrete_sequence=CBF_PALETTE,
             title='Revenue by Quarter')
fig.update_traces(textposition='outside', textfont_size=11)
fig.update_layout(xaxis_title='Revenue ($)', showlegend=False)
```

### 3. Grouped Bar Chart (grouped_bar)
**Use when**: Comparing sub-groups across categories (sales by region and quarter).

**Data requirements**: Categories (list), series names (list), and 2D values (list of lists).

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(12, 6))
n_categories = len(categories)
n_series = len(series_names)
bar_width = 0.8 / n_series
offsets = np.arange(n_categories) * (1.0 / n_series)

for i, (name, vals) in enumerate(zip(series_names, values_2d)):
    x_pos = np.arange(n_categories) + offsets[i] - 0.4 + bar_width/2
    bars = ax.bar(x_pos, vals, bar_width, label=name,
                  color=CBF_PALETTE[i % len(CBF_PALETTE)],
                  edgecolor='white', linewidth=1)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height, str(height),
                ha='center', va='bottom', fontsize=8)

ax.set_xticks(np.arange(n_categories))
ax.set_xticklabels(categories)
ax.set_title('Revenue by Region and Quarter', fontsize=16, fontweight='bold')
ax.legend(frameon=False, fontsize=11)
ax.set_ylabel('Revenue ($)')
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, vals) in enumerate(zip(series_names, values_2d)):
    fig.add_trace(go.Bar(name=name, x=categories, y=vals,
                         marker_color=CBF_PALETTE[i % len(CBF_PALETTE)]))
fig.update_layout(barmode='group', title='Revenue by Region and Quarter',
                  xaxis_title='Quarter', yaxis_title='Revenue ($)')
```

### 4. Stacked Bar Chart (stacked_bar)
**Use when**: Showing part-to-whole relationships across categories.

**Data requirements**: Same as grouped_bar but bars are stacked.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(12, 6))
bottom = np.zeros(len(categories))
for i, (name, vals) in enumerate(zip(series_names, values_2d)):
    bars = ax.bar(categories, vals, bottom=bottom, label=name,
                  color=CBF_PALETTE[i % len(CBF_PALETTE)],
                  edgecolor='white', linewidth=1)
    for bar, val in zip(bars, vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2.,
                    bar.get_y() + bar.get_height()/2.,
                    str(val), ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    bottom += np.array(vals)
ax.set_title('Revenue Breakdown by Region', fontsize=16, fontweight='bold')
ax.legend(frameon=False, fontsize=11)
ax.set_ylabel('Revenue ($)')
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, vals) in enumerate(zip(series_names, values_2d)):
    fig.add_trace(go.Bar(name=name, x=categories, y=vals,
                         marker_color=CBF_PALETTE[i % len(CBF_PALETTE)]))
fig.update_layout(barmode='stack', title='Revenue Breakdown',
                  xaxis_title='Quarter', yaxis_title='Revenue ($)')
```

### 5. Line Chart (line)
**Use when**: Showing trends over continuous intervals (time series).

**Data requirements**: Continuous x values (dates, times) and y values. Min 3 data points.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(x, y, color=CBF_PALETTE[0], linewidth=2.5, marker='o', markersize=6,
        markerfacecolor='white', markeredgecolor=CBF_PALETTE[0], markeredgewidth=2)
ax.fill_between(x, y, alpha=0.08, color=CBF_PALETTE[0])
ax.set_title('Revenue Trend', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Date', fontsize=12)
ax.set_ylabel('Revenue ($)', fontsize=12)
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%d'))
ax.set_ylim(0, max(y) * 1.1)
for xi, yi in zip(x, y):
    ax.text(xi, yi + 5, f'{yi}', ha='center', va='bottom', fontsize=9, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
```

**Plotly**:
```python
fig = px.line(x=x, y=y, markers=True, title='Revenue Trend',
              labels={'x': 'Date', 'y': 'Revenue ($)'})
fig.update_traces(line=dict(color=CBF_PALETTE[0], width=3),
                  marker=dict(size=8, color=CBF_PALETTE[0]))
fig.update_layout(hovermode='x unified', plot_bgcolor='white')
```

### 6. Multi-Line Chart (multi_line)
**Use when**: Comparing multiple trends simultaneously.

**Data requirements**: x values, multiple y series with names.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(12, 6))
markers = ['o', 's', 'D', '^', 'v', '<', '>', 'p']
linestyles = ['-', '--', '-.', ':', '-', '--', '-.', ':']
for i, (name, y_vals) in enumerate(zip(series_names, values_2d)):
    ax.plot(x, y_vals,
            marker=markers[i % len(markers)],
            linestyle=linestyles[i % len(linestyles)],
            color=CBF_PALETTE[i % len(CBF_PALETTE)],
            linewidth=2, markersize=5, label=name)

ax.set_title('Multiple Series Comparison', fontsize=16, fontweight='bold')
ax.set_xlabel('Time Period', fontsize=12)
ax.set_ylabel('Value', fontsize=12)
ax.legend(frameon=False, fontsize=11, loc='upper left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max([max(v) for v in values_2d]) * 1.1)
plt.tight_layout()
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, y_vals) in enumerate(zip(series_names, values_2d)):
    fig.add_trace(go.Scatter(x=x, y=y_vals, mode='lines+markers',
                             name=name, line=dict(color=CBF_PALETTE[i], width=2),
                             marker=dict(size=6)))
fig.update_layout(title='Multiple Series', hovermode='x unified',
                  plot_bgcolor='white', xaxis=dict(showgrid=False))
```

### 7. Area Chart (area)
**Use when**: Showing volume or magnitude over time with filled area.

**Data requirements**: Same as line chart. Best with cumulative or volume data.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(12, 6))
ax.fill_between(x, y, alpha=0.3, color=CBF_PALETTE[0])
ax.plot(x, y, color=CBF_PALETTE[0], linewidth=2.5, marker='o', markersize=5)
ax.fill_between(x, y, alpha=0.15, color=CBF_PALETTE[0])
ax.set_title('Volume Over Time', fontsize=16, fontweight='bold')
ax.set_ylabel('Volume')
ax.set_ylim(0, max(y) * 1.1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

**Plotly**:
```python
fig = px.area(x=x, y=y, title='Volume Over Time',
              labels={'x': 'Date', 'y': 'Volume'})
fig.update_traces(line=dict(color=CBF_PALETTE[0], width=2),
                  fillcolor=f'rgba(100, 143, 255, 0.3)')
fig.update_layout(plot_bgcolor='white')
```

### 8. Pie Chart (pie)
**Use when**: Showing simple proportions. NEVER use for >5 slices.

**Data requirements**: Labels and values that sum to 100%.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(8, 8))
values = [35, 25, 20, 15, 5]
labels = ['Category A', 'Category B', 'Category C', 'Category D', 'Other']
colors = CBF_PALETTE[:len(values)]
explode = [0.05, 0.05, 0.05, 0.05, 0.05]
wedges, texts, autotexts = ax.pie(
    values, explode=explode, labels=labels, colors=colors,
    autopct='%1.1f%%', startangle=90, pctdistance=0.75,
    wedgeprops={'edgecolor': 'white', 'linewidth': 2})
for t in autotexts:
    t.set_fontsize(11)
    t.set_fontweight('bold')
    t.set_color('white')
for t in texts:
    t.set_fontsize(12)
ax.set_title('Distribution by Category', fontsize=16, fontweight='bold', pad=20)
```

**Plotly**:
```python
fig = px.pie(values=values, names=labels, title='Distribution',
             color_discrete_sequence=CBF_PALETTE)
fig.update_traces(textposition='inside', textinfo='percent+label',
                  hole=0, marker=dict(line=dict(color='white', width=2)))
fig.update_layout(showlegend=True, legend=dict(orientation='h', y=-0.1))
```

### 9. Donut Chart (donut)
**Use when**: Proportions with center label showing total or average.

**Data requirements**: Same as pie but with hole in center.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(8, 8))
wedges, texts, autotexts = ax.pie(
    values, labels=labels, colors=colors,
    autopct='%1.1f%%', startangle=90, pctdistance=0.78,
    wedgeprops={'edgecolor': 'white', 'linewidth': 2, 'width': 0.4})
for t in autotexts:
    t.set_fontsize(11); t.set_fontweight('bold')
for t in texts:
    t.set_fontsize(12)
# Center label
ax.text(0, 0, f'Total\n{sum(values):,}', ha='center', va='center',
        fontsize=14, fontweight='bold', color='#333333')
ax.set_title('Distribution', fontsize=16, fontweight='bold', pad=20)
```

**Plotly**:
```python
fig = px.pie(values=values, names=labels, title='Distribution',
             color_discrete_sequence=CBF_PALETTE, hole=0.4)
fig.update_traces(textposition='inside', textinfo='percent+label',
                  marker=dict(line=dict(color='white', width=2)))
fig.update_layout(annotations=[dict(text=f'Total: {sum(values):,}',
                                     x=0.5, y=0.5, font_size=16, showarrow=False)])
```

### 10. Scatter Plot (scatter)
**Use when**: Showing correlation between two numeric variables.

**Data requirements**: Two numeric arrays of equal length (x, y). Min 5 points.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
scatter = ax.scatter(x_data, y_data, c=CBF_PALETTE[0], s=80, alpha=0.7,
                     edgecolors='white', linewidth=0.5)
ax.set_title('Correlation Analysis', fontsize=16, fontweight='bold')
ax.set_xlabel('Variable X', fontsize=12)
ax.set_ylabel('Variable Y', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add trend line
z = np.polyfit(x_data, y_data, 1)
p = np.poly1d(z)
x_trend = np.linspace(min(x_data), max(x_data), 100)
ax.plot(x_trend, p(x_trend), color=CBF_PALETTE[2], linestyle='--', linewidth=1.5, alpha=0.8)

# Add correlation coefficient
corr = np.corrcoef(x_data, y_data)[0, 1]
ax.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax.transAxes,
        fontsize=12, fontweight='bold', verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#888780'))
```

**Plotly**:
```python
fig = px.scatter(x=x_data, y=y_data, title=f'Correlation (r={corr:.3f})',
                 labels={'x': 'Variable X', 'y': 'Variable Y'},
                 color_discrete_sequence=[CBF_PALETTE[0]],
                 trendline='ols', trendline_color_override=CBF_PALETTE[2])
fig.update_traces(marker=dict(size=8, opacity=0.7, line=dict(width=0.5, color='white')))
fig.update_layout(plot_bgcolor='white')
```

### 11. Bubble Chart (bubble)
**Use when**: Showing 3 variables: x position, y position, and size.

**Data requirements**: x, y, and size arrays of equal length.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
sizes_scaled = [max(s, 10) for s in size_data]  # Min size 10
scatter = ax.scatter(x_data, y_data, s=sizes_scaled, c=CBF_PALETTE[0],
                     alpha=0.6, edgecolors='white', linewidth=1)
ax.set_title('Bubble Chart: 3-Variable Analysis', fontsize=16, fontweight='bold')
ax.set_xlabel('Variable X', fontsize=12)
ax.set_ylabel('Variable Y', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

**Plotly**:
```python
fig = px.scatter(x=x_data, y=y_data, size=size_data, color=color_data,
                 hover_name=labels, size_max=60,
                 color_discrete_sequence=CBF_PALETTE,
                 title='Bubble Chart',
                 labels={'x': 'Variable X', 'y': 'Variable Y', 'size': 'Size'})
fig.update_layout(plot_bgcolor='white')
```

### 12. Histogram (histogram)
**Use when**: Showing the distribution of a continuous variable.

**Data requirements**: Single array of numeric values. Min 10 values.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
n, bins, patches = ax.hist(values, bins=20, color=CBF_PALETTE[0],
                           edgecolor='white', linewidth=1, alpha=0.8)
ax.set_title('Distribution of Values', fontsize=16, fontweight='bold')
ax.set_xlabel('Value', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add mean/median lines
mean_val = np.mean(values)
median_val = np.median(values)
ax.axvline(mean_val, color=CBF_PALETTE[2], linestyle='--', linewidth=2, label=f'Mean: {mean_val:.1f}')
ax.axvline(median_val, color=CBF_PALETTE[3], linestyle=':', linewidth=2, label=f'Median: {median_val:.1f}')
ax.legend(frameon=False, fontsize=11)
```

**Plotly**:
```python
fig = px.histogram(values, nbins=20, title='Distribution',
                   color_discrete_sequence=[CBF_PALETTE[0]],
                   labels={'value': 'Value', 'count': 'Frequency'})
fig.update_layout(plot_bgcolor='white', bargap=0.05)
fig.add_vline(x=mean_val, line_dash='dash', line_color=CBF_PALETTE[2],
              annotation_text=f'Mean: {mean_val:.1f}')
fig.add_vline(x=median_val, line_dash='dot', line_color=CBF_PALETTE[3],
              annotation_text=f'Median: {median_val:.1f}')
```

### 13. Box Plot (box)
**Use when**: Showing distribution statistics (median, quartiles, outliers) across groups.

**Data requirements**: One or more arrays of numeric values.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
bp = ax.boxplot(data_groups, labels=group_labels, patch_artist=True,
                showmeans=True, meanline=True, showfliers=True,
                medianprops=dict(color=CBF_PALETTE[2], linewidth=2),
                meanprops=dict(color=CBF_PALETTE[3], linewidth=2, linestyle='--'),
                flierprops=dict(marker='o', markerfacecolor=CBF_PALETTE[0],
                                markersize=6, linestyle='none'))

for i, patch in enumerate(bp['boxes']):
    patch.set_facecolor(CBF_PALETTE[i % len(CBF_PALETTE)])
    patch.set_alpha(0.7)

ax.set_title('Distribution Comparison', fontsize=16, fontweight='bold')
ax.set_ylabel('Value', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add stats annotations
for i, data in enumerate(data_groups):
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    ax.text(i + 1, q3 + 5, f'Q3={q3:.1f}', ha='center', fontsize=8, color='#5F5E5A')
    ax.text(i + 1, q1 - 8, f'Q1={q1:.1f}', ha='center', fontsize=8, color='#5F5E5A')
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, data) in enumerate(zip(group_labels, data_groups)):
    fig.add_trace(go.Box(y=data, name=name,
                         marker_color=CBF_PALETTE[i % len(CBF_PALETTE)],
                         boxmean='sd'))
fig.update_layout(title='Distribution Comparison', plot_bgcolor='white',
                  yaxis=dict(showgrid=True, gridcolor='#F1EFE8'))
```

### 14. Violin Plot (violin)
**Use when**: Showing distribution shape and density alongside box plot statistics.

**Data requirements**: Same as box plot but requires more data per group (10+ values).

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 6))
vp = ax.violinplot(data_groups, positions=range(1, len(data_groups) + 1),
                   showmeans=True, showmedians=True, widths=0.7)
for i, body in enumerate(vp['bodies']):
    body.set_facecolor(CBF_PALETTE[i % len(CBF_PALETTE)])
    body.set_alpha(0.6)
vp['cmeans'].set_color(CBF_PALETTE[2])
vp['cmedians'].set_color(CBF_PALETTE[3])
ax.set_xticks(range(1, len(data_groups) + 1))
ax.set_xticklabels(group_labels)
ax.set_title('Distribution Shape Comparison', fontsize=16, fontweight='bold')
ax.set_ylabel('Value', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, data) in enumerate(zip(group_labels, data_groups)):
    fig.add_trace(go.Violin(y=data, name=name,
                            marker_color=CBF_PALETTE[i % len(CBF_PALETTE)],
                            box_visible=True, meanline_visible=True))
fig.update_layout(title='Distribution Shape Comparison', plot_bgcolor='white',
                  yaxis=dict(showgrid=True, gridcolor='#F1EFE8'))
```

### 15. Heatmap (heatmap)
**Use when**: Visualizing a 2D matrix of values (correlation matrices, confusion matrices).

**Data requirements**: 2D list/array of numeric values.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(matrix_data, cmap='viridis', aspect='auto', interpolation='nearest')

# Add text annotations
for i in range(matrix_data.shape[0]):
    for j in range(matrix_data.shape[1]):
        text = ax.text(j, i, f'{matrix_data[i, j]:.2f}',
                       ha='center', va='center',
                       color='white' if matrix_data[i, j] > matrix_data.max() / 2 else 'black',
                       fontsize=9, fontweight='bold')

ax.set_xticks(range(len(col_labels)))
ax.set_yticks(range(len(row_labels)))
ax.set_xticklabels(col_labels, rotation=45, ha='right')
ax.set_yticklabels(row_labels)
ax.set_title('Correlation Matrix', fontsize=16, fontweight='bold', pad=20)
plt.colorbar(im, ax=ax, shrink=0.8, label='Correlation')
plt.tight_layout()
```

**Plotly**:
```python
fig = px.imshow(matrix_data, x=col_labels, y=row_labels,
                color_continuous_scale='viridis',
                title='Correlation Matrix',
                labels={'x': 'Variables', 'y': 'Variables', 'color': 'Value'})
fig.update_traces(text=matrix_data, texttemplate='%{text:.2f}')
fig.update_layout(plot_bgcolor='white')
```

### 16. Radar Chart (radar)
**Use when**: Comparing multiple attributes across entities (skill assessments, product comparison).

**Data requirements**: Multiple numeric attributes (3+), 2+ entities.

**Matplotlib**:
```python
# Polar axis
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
angles = np.linspace(0, 2 * np.pi, len(attributes), endpoint=False).tolist()
angles += angles[:1]

for i, (name, vals) in enumerate(zip(entity_names, values_2d)):
    vals_plot = vals + vals[:1]
    ax.plot(angles, vals_plot, 'o-', color=CBF_PALETTE[i % len(CBF_PALETTE)],
            linewidth=2, markersize=6, label=name)
    ax.fill(angles, vals_plot, alpha=0.1, color=CBF_PALETTE[i % len(CBF_PALETTE)])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(attributes, fontsize=11)
ax.set_title('Multi-Attribute Comparison', fontsize=16, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), frameon=False)
ax.set_ylim(0, max([max(v) for v in values_2d]) * 1.1)
```

**Plotly**:
```python
fig = go.Figure()
for i, (name, vals) in enumerate(zip(entity_names, values_2d)):
    fig.add_trace(go.Scatterpolar(r=vals + vals[:1],
                                  theta=attributes + [attributes[0]],
                                  fill='toself', name=name,
                                  marker_color=CBF_PALETTE[i % len(CBF_PALETTE)]))
fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                  title='Multi-Attribute Comparison', showlegend=True)
```

### 17. Candlestick Chart (candlestick)
**Use when**: Visualizing financial OHLC (Open, High, Low, Close) price data.

**Data requirements**: DataFrame with columns: date/time, open, high, low, close.

**Plotly**:
```python
fig = go.Figure(data=[go.Candlestick(
    x=dates,
    open=open_prices, high=high_prices,
    low=low_prices, close=close_prices,
    increasing_line_color=CBF_PALETTE[5],  # Green for up
    decreasing_line_color=CBF_PALETTE[3]   # Orange for down
)])
fig.update_layout(
    title='Stock Price - OHLC',
    xaxis_title='Date', yaxis_title='Price ($)',
    xaxis_rangeslider_visible=True,
    plot_bgcolor='white',
    hovermode='x unified'
)
fig.write_html('candlestick.html')

# Add moving average overlay
fig.add_trace(go.Scatter(x=dates, y=sma_20, mode='lines',
                         name='SMA 20', line=dict(color=CBF_PALETTE[0], width=1.5)))
fig.add_trace(go.Scatter(x=dates, y=sma_50, mode='lines',
                         name='SMA 50', line=dict(color=CBF_PALETTE[2], width=1.5)))
```

**Matplotlib equivalent** (using mplfinance):
```python
import mplfinance as mpf
mpf.plot(df, type='candle', style='charles',
         title='Stock Price', ylabel='Price ($)',
         volume=True, savefig='candlestick.png')
```

### 18. K-Means Clustering (kmeans)
**Use when**: Visualizing cluster assignments from k-means algorithm.

**Data requirements**: 2D points (x, y) and cluster labels.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
unique_labels = np.unique(cluster_labels)
for i, label in enumerate(unique_labels):
    mask = cluster_labels == label
    ax.scatter(x_data[mask], y_data[mask],
               c=[CBF_PALETTE[i % len(CBF_PALETTE)]],
               s=60, alpha=0.7, edgecolors='white', linewidth=0.5,
               label=f'Cluster {label + 1}')

# Plot centroids
centroids = np.array([x_data[cluster_labels == l].mean() for l in unique_labels])
# centroids_y similarly
for i, centroid in enumerate(centroids):
    ax.scatter(centroid[0], centroid[1],
               c=[CBF_PALETTE[i % len(CBF_PALETTE)]],
               s=200, marker='X', edgecolors='black', linewidth=2,
               zorder=5)

ax.set_title('K-Means Clustering (k={})'.format(len(unique_labels)),
             fontsize=16, fontweight='bold')
ax.set_xlabel('Feature 1', fontsize=12)
ax.set_ylabel('Feature 2', fontsize=12)
ax.legend(frameon=False, fontsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

**Plotly**:
```python
fig = px.scatter(x=x_data, y=y_data, color=cluster_labels.astype(str),
                 color_discrete_sequence=CBF_PALETTE,
                 title='K-Means Clustering',
                 labels={'x': 'Feature 1', 'y': 'Feature 2', 'color': 'Cluster'})
fig.update_traces(marker=dict(size=8, opacity=0.7, line=dict(width=0.5, color='white')))
fig.update_layout(plot_bgcolor='white')
```

### 19. Contour Plot (contour)
**Use when**: Showing 3D surface contours on a 2D plane (topography, density).

**Data requirements**: 2D grid of X, Y, Z values.

**Matplotlib**:
```python
fig, ax = plt.subplots(figsize=(10, 8))
X, Y = np.meshgrid(x_values, y_values)
Z = np.sin(np.sqrt(X**2 + Y**2))

contour = ax.contour(X, Y, Z, levels=20, cmap='viridis', linewidths=0.8)
ax.clabel(contour, inline=True, fontsize=9, fmt='%.2f')
ax.set_title('Contour Plot', fontsize=16, fontweight='bold')
ax.set_xlabel('X Axis', fontsize=12)
ax.set_ylabel('Y Axis', fontsize=12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Add filled contours
contour_filled = ax.contourf(X, Y, Z, levels=20, cmap='viridis', alpha=0.6)
plt.colorbar(contour_filled, ax=ax, shrink=0.8, label='Z Value')
```

**Plotly**:
```python
fig = go.Figure(data=go.Contour(
    z=Z, x=x_values, y=y_values,
    contours=dict(coloring='heatmap', showlabels=True),
    colorbar=dict(title='Z Value'),
    colorscale='Viridis'
))
fig.update_layout(title='Contour Plot',
                  xaxis_title='X Axis', yaxis_title='Y Axis',
                  plot_bgcolor='white')
```

### 20. 3D Scatter Plot (3d_scatter)
**Use when**: Showing relationships between 3 numeric variables.

**Data requirements**: x, y, z arrays of equal length.

**Matplotlib**:
```python
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

scatter = ax.scatter(x_data, y_data, z_data,
                     c=color_values, cmap='viridis',
                     s=size_values, alpha=0.7,
                     edgecolors='white', linewidth=0.5)

ax.set_title('3D Scatter Plot', fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('X Axis', fontsize=10, labelpad=10)
ax.set_ylabel('Y Axis', fontsize=10, labelpad=10)
ax.set_zlabel('Z Axis', fontsize=10, labelpad=10)
plt.colorbar(scatter, ax=ax, shrink=0.6, label='Color Value')
```

**Plotly**:
```python
fig = px.scatter_3d(x=x_data, y=y_data, z=z_data,
                    color=color_values, size=size_values,
                    color_continuous_scale='viridis',
                    title='3D Scatter Plot',
                    labels={'x': 'X Axis', 'y': 'Y Axis', 'z': 'Z Axis', 'color': 'Value'})
fig.update_layout(scene=dict(
    xaxis=dict(showgrid=True, gridcolor='#F1EFE8'),
    yaxis=dict(showgrid=True, gridcolor='#F1EFE8'),
    zaxis=dict(showgrid=True, gridcolor='#F1EFE8')))
fig.write_html('3d_scatter.html')
```

### 21. 3D Surface Plot (3d_surface)
**Use when**: Visualizing continuous 3D surfaces (terrain, mathematical functions).

**Data requirements**: 2D grid of X, Y, Z values.

**Matplotlib**:
```python
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
X, Y = np.meshgrid(x_values, y_values)
Z = np.sin(np.sqrt(X**2 + Y**2))

surface = ax.plot_surface(X, Y, Z, cmap='viridis',
                          linewidth=0, antialiased=True, alpha=0.9)
ax.set_title('3D Surface Plot', fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('X Axis', fontsize=10, labelpad=10)
ax.set_ylabel('Y Axis', fontsize=10, labelpad=10)
ax.set_zlabel('Z Axis', fontsize=10, labelpad=10)
fig.colorbar(surface, ax=ax, shrink=0.6, label='Z Value')
```

**Plotly**:
```python
fig = go.Figure(data=[go.Surface(z=Z, x=x_values, y=y_values,
                                  colorscale='Viridis',
                                  contours=dict(
                                      x=dict(show=True, color='white'),
                                      y=dict(show=True, color='white'),
                                      z=dict(show=True, color='white')))])
fig.update_layout(title='3D Surface Plot',
                  scene=dict(
                      xaxis_title='X Axis',
                      yaxis_title='Y Axis',
                      zaxis_title='Z Axis'),
                  autosize=True)
fig.write_html('3d_surface.html')
```

### 22. 3D Bar Chart (3d_bar)
**Use when**: Comparing values across 3 categorical dimensions.

**Data requirements**: 3 categorical arrays and 1 numeric array.

**Matplotlib**:
```python
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
x_labels = ['A', 'B', 'C']
y_labels = ['X', 'Y', 'Z']
x_pos, y_pos = np.meshgrid(np.arange(len(x_labels)), np.arange(len(y_labels)))
x_pos = x_pos.flatten()
y_pos = y_pos.flatten()
z_pos = np.zeros_like(x_pos)
dx = dy = 0.4
dz = np.random.randint(10, 100, len(x_pos))
colors = [CBF_PALETTE[i % len(CBF_PALETTE)] for i in range(len(x_pos))]
ax.bar3d(x_pos, y_pos, z_pos, dx, dy, dz, color=colors, alpha=0.8)
ax.set_xticks(np.arange(len(x_labels)))
ax.set_yticks(np.arange(len(y_labels)))
ax.set_xticklabels(x_labels)
ax.set_yticklabels(y_labels)
ax.set_title('3D Bar Chart', fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Category', fontsize=10)
ax.set_ylabel('Group', fontsize=10)
ax.set_zlabel('Value', fontsize=10)
```

**Plotly**:
```python
fig = go.Figure(data=[go.Scatter3d(
    x=x_cat_data, y=y_cat_data, z=z_values,
    mode='markers',
    marker=dict(size=12, symbol='square', color=z_values,
                colorscale='Viridis', opacity=0.8,
                line=dict(color='white', width=1))),
    go.Mesh3d(x=x_cat_data, y=y_cat_data, z=z_values, opacity=0.3,
              color='lightblue')])
fig.update_layout(title='3D Bar Chart',
                  scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'))
```

## Triggers
- "chart", "graph", "plot", "visualize data"
- "bar chart", "line graph", "pie chart", "scatter plot"
- "distribution", "trend", "comparison"
- "data visualization", "dashboard"
- "create a chart", "make a graph", "show me the data"
- "visualize", "plot this", "chart this data"
- "correlation", "histogram", "heatmap", "radar chart"
- "candlestick", "stock chart", "financial chart"
- "3d chart", "bubble chart", "contour plot"

## Libraries
- **matplotlib** — for static charts in any context
- **plotly** — for interactive charts in HTML
- **python-pptx chart API** — for charts in presentations
- **SVG (direct)** — for inline diagrams

## Matplotlib Professional Setup

### Complete Professional Configuration
```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': True,
    'axes.spines.bottom': True,
    'axes.linewidth': 0.8,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
    'axes.grid': False,
    'grid.alpha': 0.3,
    'grid.color': '#D3D1C7',
    'grid.linestyle': '-',
    'grid.linewidth': 0.5,
})

CBF_PALETTE = [
    '#648FFF', '#785EF0', '#DC267F', '#FE6100', '#FFB000',
    '#009E73', '#004D43', '#F0E442', '#56B4E9'
]

SEMANTIC_COLORS = {
    'primary': '#378ADD',
    'success': '#1D9E75',
    'danger': '#D85A30',
    'warning': '#EF9F27',
    'info': '#534AB7',
    'neutral': '#888780',
}
```

## Plotly Professional Setup

### Complete Plotly Configuration
```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

pio.templates.default = 'none'

THEME_LAYOUT = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family='sans-serif', size=12, color='#333333'),
    hovermode='x unified',
    xaxis=dict(
        showgrid=True,
        gridcolor='#F1EFE8',
        gridwidth=1,
        showline=True,
        linecolor='#D3D1C7',
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=10),
        title_font=dict(size=12),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='#F1EFE8',
        gridwidth=1,
        showline=True,
        linecolor='#D3D1C7',
        linewidth=1,
        zeroline=False,
        tickfont=dict(size=10),
        title_font=dict(size=12),
    ),
    margin=dict(l=60, r=30, t=80, b=60),
    legend=dict(
        orientation='h',
        y=-0.15,
        x=0.5,
        xanchor='center',
        font=dict(size=11),
    ),
)
```

## Python-PPTX Chart Integration

### Complete PPTX Chart Setup
```python
from pptx import Presentation
from pptx.chart.data import CategoryChartData, ChartData
from pptx.enum.chart import (
    XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
)
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

CHART_TYPE_MAP = {
    'bar': XL_CHART_TYPE.COLUMN_CLUSTERED,
    'hbar': XL_CHART_TYPE.BAR_CLUSTERED,
    'grouped_bar': XL_CHART_TYPE.COLUMN_CLUSTERED,
    'stacked_bar': XL_CHART_TYPE.COLUMN_STACKED,
    'line': XL_CHART_TYPE.LINE_MARKERS,
    'multi_line': XL_CHART_TYPE.LINE_MARKERS,
    'area': XL_CHART_TYPE.AREA,
    'pie': XL_CHART_TYPE.PIE,
    'donut': XL_CHART_TYPE.DOUGHNUT,
    'scatter': XL_CHART_TYPE.XY_SCATTER,
    'radar': XL_CHART_TYPE.RADAR,
}

def add_chart_to_slide(slide, chart_type, categories, values_2d, series_names=None,
                       title='Chart', left=1, top=2, width=8, height=5):
    chart_data = CategoryChartData()
    chart_data.categories = categories
    if series_names is None:
        series_names = ['Series'] if isinstance(values_2d[0], (int, float)) else [f'Series {i+1}' for i in range(len(values_2d))]

    if isinstance(values_2d[0], (int, float)):
        chart_data.add_series(series_names[0], values_2d)
    else:
        for name, vals in zip(series_names, values_2d):
            chart_data.add_series(name, vals)

    pptx_type = CHART_TYPE_MAP.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
    chart_frame = slide.shapes.add_chart(
        pptx_type, Inches(left), Inches(top),
        Inches(width), Inches(height), chart_data
    )
    chart = chart_frame.chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.TOP
    chart.legend.include_in_layout = False
    chart.chart_title.has_text_frame = True
    chart.chart_title.text_frame.text = title
    chart.chart_title.text_frame.paragraphs[0].font.size = Pt(14)
    chart.chart_title.text_frame.paragraphs[0].font.bold = True
    chart.chart_style = 2

    # Color the series
    for i, series in enumerate(chart.series):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = RGBColor(
            int(CBF_PALETTE[i % len(CBF_PALETTE)][1:3], 16),
            int(CBF_PALETTE[i % len(CBF_PALETTE)][3:5], 16),
            int(CBF_PALETTE[i % len(CBF_PALETTE)][5:7], 16)
        )

    return chart
```

## Advanced Patterns

### Data Labels with Formatting
```python
# Matplotlib
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.01,
            f'{int(height):,}', ha='center', va='bottom',
            fontsize=10, fontweight='bold',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=2))
```

### Log Scale
```python
ax.set_yscale('log')
ax.set_xscale('log')
fig.update_layout(yaxis_type='log', xaxis_type='log')
```

### Dual Y-Axis
```python
fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.bar(categories, values, color=CBF_PALETTE[0], alpha=0.7, label='Revenue')
ax1.set_ylabel('Revenue ($)', fontsize=12)

ax2 = ax1.twinx()
ax2.plot(categories, growth_rates, 'o-', color=CBF_PALETTE[2], linewidth=2, label='Growth %')
ax2.set_ylabel('Growth Rate (%)', fontsize=12, color=CBF_PALETTE[2])
ax2.tick_params(axis='y', colors=CBF_PALETTE[2])

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, fontsize=11)
ax1.set_title('Revenue and Growth Rate', fontsize=16, fontweight='bold')
```

### Error Bars
```python
ax.errorbar(x, y, yerr=errors, fmt='o', color=CBF_PALETTE[0],
            capsize=5, capthick=1.5, elinewidth=1.5, markersize=6)
ax.bar(x, y, yerr=errors, capsize=5, color=CBF_PALETTE[0], alpha=0.7)
```

### Custom Colormap
```python
colors = ['#648FFF', '#785EF0', '#DC267F', '#FE6100', '#FFB000']
cmap = LinearSegmentedColormap.from_list('custom', colors, N=256)
im = ax.imshow(data, cmap=cmap, aspect='auto')
```

## Troubleshooting

### Overlapping Labels
**Problem**: Data labels overlap, especially in dense charts.
**Solutions**:
1. Rotate labels: `ax.set_xticklabels(labels, rotation=45, ha='right')`
2. Reduce font size: `fontsize=8`
3. Use stagger: `ax.set_xticklabels(labels) + manual y-offsets`
4. Use `adjustText` library: `from adjustText import adjust_text`
5. Remove some labels: show every nth label
6. In plotly: `fig.update_traces(textposition='outside')`
7. In plotly: Use `automargin=True`

### Data Scaling Issues
**Problem**: Data with different scales makes some series invisible.
**Solutions**:
1. Use dual y-axis for different scales
2. Normalize data before plotting: `(x - min) / (max - min)`
3. Use log scale for exponential data
4. Use facet wrapping (small multiples)
5. Plot as percentages of total

### Performance with Large Datasets
**Problem**: Charts with 100K+ points render slowly or crash.
**Solutions**:
1. **Downsample**: Sample every nth point
2. **Aggregate**: Use hexbin for 2D density
3. **Decimation**: `ax.plot(x[::10], y[::10])`
4. **Plotly**: Use `scattergl` instead of `scatter`
5. **Plotly**: Enable WebGL: `fig = go.Figure(data=go.Scattergl(...))`
6. **Matplotlib**: Use `rasterized=True` for paths
7. **Matplotlib**: Use `ax.plot(x, y, linewidth=0.5)` for thin lines
8. **Histogram**: Use `np.histogram` + `ax.bar` for pre-binned data

**WebGL Scatter (Plotly)**:
```python
fig = go.Figure(data=go.Scattergl(
    x=x_large, y=y_large, mode='markers',
    marker=dict(color=CBF_PALETTE[0], size=3, opacity=0.5)))
```

### Memory Management
```python
# Always close figures
fig, ax = plt.subplots()
# ... plotting code ...
plt.close(fig)  # Explicit close
plt.close('all')  # Close all figures

# Context manager style (matplotlib 3.4+)
with plt.rc_context({'font.size': 11}):
    fig, ax = plt.subplots()
    ax.plot(x, y)
    fig.savefig('chart.png')
    plt.close(fig)
```

## Quality Checklist

### Data Integrity
1. Verify data values match the source data exactly
2. Check that all data points are visible (not clipped by axis limits)
3. Confirm that aggregations (sums, averages) are calculated correctly
4. Verify date/time parsing and timezone handling
5. Check for missing/null values and handle appropriately
6. Ensure decimal precision is consistent across all labels
7. Verify that pie chart percentages sum to 100%

### Visual Quality
8. Verify all axis labels are readable (min 10pt)
9. Check that title clearly describes the insight, not just the data
10. Confirm legend entries match chart colors exactly
11. Verify chart size is appropriate for output context
12. Check that data labels don't overlap
13. Confirm color contrast meets WCAG AA (4.5:1 for text)
14. Verify gridlines are subtle (not dominant)
15. Check that axis scales are appropriate (no misleading truncation)

### Format-Specific Checks
16. For presentations: verify chart fits within slide boundaries
17. For HTML: confirm interactive features work (hover, zoom)
18. For PDF: verify vector quality (no rasterization artifacts)
19. For DOCX: confirm chart is embedded (not linked)
20. For XLSX: verify chart data is on same or accessible sheet
21. For SVG: verify viewBox scaling works at different widths

### Accessibility
22. Check colorblind accessibility (no red-green pairs)
23. Verify chart has descriptive alt text or caption
24. Confirm text size is at least 10pt for body, 12pt for labels
25. Ensure no critical information is conveyed by color alone

### Code Quality
26. All plt.close() calls are present (no memory leaks)
27. Figure DPI is set to at least 150
28. Color palette is explicitly specified (never defaults)
29. Chart type is appropriate for the data structure
30. Output format matches the intended use case

## Integration Reference

### With create_pdf
```python
create_pdf(sections=[
    {'type': 'chart', 'chart_type': 'bar', 'data': {...},
     'width': 500, 'height': 300, 'title': 'Revenue'},
    {'type': 'chart', 'chart_type': 'line', 'data': {...},
     'width': 500, 'height': 300},
])
```

### With create_docx
```python
create_docx(sections=[
    {'type': 'heading', 'text': 'Q4 Analysis'},
    {'type': 'chart', 'chart_type': 'grouped_bar', 'data': {...},
     'width': 14, 'height': 8, 'title': 'Revenue by Region'},
    {'type': 'chart', 'chart_type': 'pie', 'data': {...},
     'width': 10, 'height': 10},
])
```

### With create_pptx
```python
create_pptx(sections=[
    {'type': 'slide', 'content': [
        {'type': 'title', 'text': 'Financial Overview'},
        {'type': 'chart', 'chart_type': 'line', 'data': {...}, 'pos': (1, 2, 8, 5)},
    ]},
])
```

### Standalone Chart Generation
```python
# Generate and return chart bytes
result = _make_chart('bar', chart_data, 'png')
# result is bytes of the PNG image
result_base64 = base64.b64encode(result).decode()

# For SVG output
result_svg = _make_chart('bar', chart_data, 'svg')
# result_svg is an SVG string
```

## Critical Rules — What to AVOID
- NEVER use default matplotlib colors — always specify semantic color palette
- NEVER create charts without titles and axis labels
- NEVER save at resolution below 150 DPI
- NEVER skip closing plt (plt.close()) — causes memory leaks
- NEVER use more than 6 colors in a single chart
- NEVER use 3D charts — they distort perception of data (except 3d_scatter for 3D point clouds)
- NEVER overlay too many data series (max 4 per chart)
- NEVER use rainbow/jet colormaps — use viridis, plasma, or custom diverging
- NEVER embed raw matplotlib figures in HTML — use plotly for interactivity
- NEVER create pie charts with more than 5 slices
- NEVER use red-green combinations (colorblind inaccessible)
- NEVER skip adding data labels for precision
- NEVER use chartjunk (unnecessary gridlines, borders, backgrounds, gradients)
- NEVER leave y-axis non-zero for bar charts (misleading)
- NEVER use area charts for non-cumulative data without clear labeling
- NEVER use radar charts with more than 8 axes (cluttered)
- NEVER skip checking data for NaN or infinite values
- NEVER use identical colors for different data series
- NEVER use line charts with unordered x-axis data
- NEVER forget to set figure DPI before saving
- NEVER use matplotlib default figure size (6.4x4.8) for production charts
- NEVER use stacked area charts without zero baseline
- NEVER use dual y-axes for unrelated metrics without clear labeling
- NEVER use smoothed lines (spline interpolation) unless data is continuous
- NEVER skip legend when there are multiple series
