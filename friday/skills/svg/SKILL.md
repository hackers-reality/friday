---
name: svg
description: Use this skill when creating SVG diagrams, infographics, charts, flowcharts, or any visual illustration
---

# SVG Diagram & Infographic Creation Guide — Production-Grade Visuals

## Overview
FRIDAY creates inline SVG diagrams as a primary visualization engine. SVG diagrams are resolution-independent, themable (light/dark), and can be embedded in any HTML/Markdown output. Design every diagram as if it will be projected on a screen or printed in a report — clean, readable, visually cohesive.

SVG (Scalable Vector Graphics) is an XML-based vector image format that supports interactivity and animation. All modern browsers render SVG natively. FRIDAY generates SVG directly as Python f-strings, with no external dependencies.

## QUALITY CRITICAL — READ BEFORE WRITING CODE

YOU ARE A VECTOR DESIGNER. Build every SVG as if it will be featured on a landing page or presentation. Professional composition, sophisticated gradients, and precise typography are mandatory. NO simple text-plus-circle logos.

### EXACT SVG BLUEPRINT (animated logo)

An animated SVG logo MUST have this EXACT structure:

**viewBox**: "0 0 800 600", responsive: width="100%" height="100%"

**defs section** (MUST contain at minimum):
1. Two linearGradients: primary (#00d4ff → #0066ff), secondary (#7F77DD → #534AB7)
2. One radialGradient for glow effect (center transparent → edge semi-transparent)
3. Drop shadow filter: `<filter id="glow"> <feGaussianBlur stdDeviation="3" result="coloredBlur"/> <feMerge> <feMergeNode in="coloredBlur"/> <feMergeNode in="SourceGraphic"/> </feMerge> </filter>`
4. At least 3 CSS @keyframes:
   - `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`
   - `@keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }`
   - `@keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-15px); } }`

**Background**: Dark rect (#0a0a2e, full viewBox, rx="20") with subtle radial gradient overlay for depth.

**Center composition** (positioned around 400, 300):
- Ring 1: outer circle r=150, stroke=url(#primary), stroke-width=3, fill=none, className="spin" (4s linear infinite), stroke-dasharray="100 800"
- Ring 2: inner circle r=120, stroke=url(#secondary), stroke-width=2, fill=none, className="spin-reverse" (6s linear infinite), stroke-dasharray="50 700"
- Text "FRIDAY": x=400 y=280 text-anchor="middle", font-family="Arial,Helvetica", font-size=64, font-weight=bold, fill=url(#primary), filter="url(#glow)", className="pulse" (3s ease-in-out infinite)
- Text "AI ASSISTANT": x=400 y=330 text-anchor="middle", font-family="Arial", font-size=20, fill="#888780", letter-spacing=4

**Orbiting elements** (4+ dots with different positions and timing):
- Circle r=8, cx=400+Math, cy=300+Math (orbiting), fill=url(#primary), className="orbit1" (8s linear infinite)
- Circle r=5, fill=url(#secondary), className="orbit2" (10s linear infinite)
- Circle r=6, fill="#00d4ff", className="orbit3" (12s linear infinite reverse)
- Circle r=4, fill="#7F77DD", className="float" (4s ease-in-out infinite)

**Decorative layers**:
- Grid pattern or subtle dot matrix in background (opacity 0.1)
- Scanning line or horizontal gradient sweep (opacity 0.05 to 0.15)
- Corner accents or decorative arcs

### COLOR SYSTEM
- **Dark Futuristic**: bg #0a0a2e, accent1 #00d4ff, accent2 #0066ff, accent3 #7F77DD, text #ffffff, muted #888780
- **Corporate Light**: bg #F5F7FA, accent1 #378ADD, accent2 #185FA5, accent3 #534AB7, text #333333, muted #888780
- **Neon Dark**: bg #0d0d0d, accent1 #ff0080, accent2 #7928ca, accent3 #00d4ff, text #ffffff, muted #666666

### EVERY SVG MUST HAVE
- Proper viewBox with responsive width/height
- <defs> section with gradients and animations
- Multiple animated elements (different speeds, delays, and directions)
- Semantic <g> grouping with descriptive ids
- Professional typography (text-anchor, font-family, proper sizing)
- Visual depth through gradients, shadows, or layering

### ANTI-PATTERNS — OUTPUTS THAT GET REJECTED
- Just text + one circle/rectangle — no composition or depth
- No gradients, shadows, filters, or visual effects
- Single @keyframes animation or none at all
- Missing <defs> section
- Poor typography (no text-anchor, default font, wrong size)
- Single flat color throughout with no variation
- No <g> organization or semantic structure
- Missing viewBox attribute
- Animation that doesn't loop or is imperceptible
- Text that's unreadable against background (poor contrast)

## Triggers
- "diagram", "flowchart", "infographic", "illustration", "architecture diagram"
- "chart", "graph", "visualization"
- "show me how X works", "visualize this data"
- "make a diagram of", "create an infographic about"
- "timeline", "org chart", "mind map", "wireframe"
- "loading spinner", "animated logo", "progress indicator"

## SVG Specification Reference

### ViewBox and Coordinate System
```svg
viewBox="min-x min-y width height"
```
- `viewBox="0 0 680 400"` — defines a 680x400 coordinate system
- Without viewBox: SVG scales based on width/height attributes
- Coordinates: origin (0,0) is top-left, x increases right, y increases down

**preserveAspectRatio**:
```svg
preserveAspectRatio="xMidYMid meet"  <!-- Default: center, fit entirely -->
preserveAspectRatio="xMinYMin slice" <!-- Align top-left, cover area -->
preserveAspectRatio="none"           <!-- Stretch to fill (distort) -->
```

### Transforms
```svg
<g transform="translate(x, y)">           <!-- Move coordinate origin -->
<g transform="scale(sx, sy)">              <!-- Scale coordinates -->
<g transform="rotate(angle, cx, cy)">      <!-- Rotate around center -->
<g transform="skewX(angle)">               <!-- Skew horizontally -->
<g transform="skewY(angle)">               <!-- Skew vertically -->
<g transform="matrix(a, b, c, d, e, f)">   <!-- Full transform matrix -->
```

**Transform composition** (applied right-to-left):
```svg
<g transform="translate(100, 50) rotate(45)"><!-- Rotate, then translate -->
```

## All Shape Elements

### Rectangle `<rect>`
```svg
<rect x="10" y="10" width="200" height="100" rx="8" ry="8"
      fill="#378ADD" stroke="#185FA5" stroke-width="2" opacity="0.9"/>
```
- `rx`, `ry`: Corner radius (rounded rectangles)
- `fill`: Fill color (use 'none' for transparent)
- `stroke`: Border color
- `stroke-width`: Border thickness
- `stroke-dasharray`: Dashed lines, e.g., `"6,3"` = 6px dash, 3px gap
- `stroke-linejoin`: `miter`, `round`, `bevel`
- `opacity`: Overall opacity (0-1)

### Circle `<circle>`
```svg
<circle cx="100" cy="100" r="50" fill="#1D9E75" stroke="#0F6E56" stroke-width="2"/>
```

### Ellipse `<ellipse>`
```svg
<ellipse cx="100" cy="100" rx="80" ry="40" fill="#DC267F" stroke="#993556" stroke-width="2"/>
```

### Line `<line>`
```svg
<line x1="10" y1="10" x2="200" y2="150" stroke="#888780" stroke-width="2"
      stroke-linecap="round"/>
```
- `stroke-linecap`: `butt` (default), `round`, `square`

### Polyline `<polyline>`
```svg
<polyline points="10,10 50,50 100,30 150,80" fill="none" stroke="#648FFF" stroke-width="2"/>
```

### Polygon `<polygon>`
```svg
<polygon points="100,10 190,190 10,190" fill="#7F77DD" stroke="#534AB7" stroke-width="2"/>
```

### Path `<path>` (most powerful element)
```svg
<path d="M10 10 L50 50 L100 30 L150 80 Z" fill="none" stroke="#648FFF" stroke-width="2"/>
```

## Path Commands Complete Reference

### Moveto (M/m)
- `M x y`: Absolute moveto (lift pen, move to x,y)
- `m dx dy`: Relative moveto

### Lineto (L/l, H/h, V/v)
- `L x y`: Absolute lineto (draw line to x,y)
- `l dx dy`: Relative lineto
- `H x`: Horizontal lineto (absolute x)
- `h dx`: Horizontal lineto (relative)
- `V y`: Vertical lineto (absolute y)
- `v dy`: Vertical lineto (relative)

### Cubic Bezier (C/c, S/s)
- `C x1 y1, x2 y2, x y`: Cubic bezier to (x,y) with control points (x1,y1) and (x2,y2)
- `c dx1 dy1, dx2 dy2, dx dy`: Relative cubic bezier
- `S x2 y2, x y`: Smooth cubic bezier (reflects previous control point)
- `s dx2 dy2, dx dy`: Relative smooth cubic bezier

**Example**:
```svg
<!-- Cubic bezier curve -->
<path d="M10 100 C 40 10, 120 10, 150 100"
      fill="none" stroke="#DC267F" stroke-width="3"/>
```

### Quadratic Bezier (Q/q, T/t)
- `Q x1 y1, x y`: Quadratic bezier to (x,y) with control point (x1,y1)
- `q dx1 dy1, dx dy`: Relative quadratic bezier
- `T x y`: Smooth quadratic bezier (reflects previous control point)
- `t dx dy`: Relative smooth quadratic bezier

**Example**:
```svg
<!-- Quadratic bezier curve -->
<path d="M10 100 Q 80 10, 150 100"
      fill="none" stroke="#FE6100" stroke-width="3"/>
```

### Arc (A/a)
- `A rx ry x-axis-rotation large-arc-flag sweep-flag x y`
- `a rx ry x-axis-rotation large-arc-flag sweep-flag dx dy`

Parameters:
- `rx`: X-radius of ellipse
- `ry`: Y-radius of ellipse
- `x-axis-rotation`: Rotation of ellipse in degrees
- `large-arc-flag`: 0 = small arc, 1 = large arc
- `sweep-flag`: 0 = counter-clockwise, 1 = clockwise
- `x/y`: End point

**Example**:
```svg
<!-- Arc from (20,100) to (100,20) -->
<path d="M20 100 A 60 60 0 0 1 100 20"
      fill="none" stroke="#FFB000" stroke-width="3"/>
```

### Close Path (Z/z)
- `Z` or `z`: Close current path (draw line back to start)

### Complete Path Example — Heart Shape
```svg
<path d="M100 30
         C 100 10, 60 10, 60 30
         C 60 50, 100 80, 100 100
         C 100 80, 140 50, 140 30
         C 140 10, 100 10, 100 30 Z"
      fill="#DC267F"/>
```

### Path Construction Patterns

**Rounded Rectangle**:
```svg
<path d="M10 40 L10 30 A10 10 0 0 1 20 20 L180 20 A10 10 0 0 1 190 30
         L190 170 A10 10 0 0 1 180 180 L20 180 A10 10 0 0 1 10 170 Z"
      fill="#E6F1FB" stroke="#378ADD" stroke-width="2"/>
```

**Chevron Arrow**:
```svg
<path d="M5 30 L30 5 L55 30" fill="none" stroke="#888780" stroke-width="2" stroke-linecap="round"/>
```

**Curved Connector**:
```svg
<path d="M100 200 C 100 250, 300 150, 300 200"
      fill="none" stroke="#888780" stroke-width="1.5" marker-end="url(#arrow)"/>
```

## CSS Styling in SVG

### Inline Styles
```svg
<rect x="10" y="10" width="100" height="50"
      style="fill: #378ADD; stroke: #185FA5; stroke-width: 2; rx: 6;"/>
```

### Internal Stylesheet
```svg
<svg ...>
  <style>
    .box { fill: #F1EFE8; stroke: #888780; stroke-width: 1.5; rx: 6; }
    .primary { fill: #378ADD; }
    .text-title { font-family: system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #2C2C2A; }
    .text-body { font-family: system-ui, sans-serif; font-size: 14px; fill: #5F5E5A; }
    .text-caption { font-family: system-ui, sans-serif; font-size: 12px; fill: #888780; }
    .node:hover .box { stroke: #185FA5; stroke-width: 2.5; cursor: pointer; }
    .fade-in { animation: fadeIn 0.5s ease-in; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .pulse { animation: pulse 2s ease-in-out infinite; }
    @keyframes slideIn { from { transform: translateY(20px); opacity: 0; }
                         to { transform: translateY(0); opacity: 1; } }
    .slide-in { animation: slideIn 0.6s ease-out; }
    .progress-bar { transition: width 1s ease-in-out; }
  </style>
  <rect class="box" x="20" y="20" width="200" height="80"/>
</svg>
```

### External CSS
```html
<link rel="stylesheet" href="diagram-styles.css">
```

### CSS Selectors in SVG
- `.classname` — class selector
- `#id` — id selector
- `element` — tag name selector
- `parent child` — descendant selector
- `element:hover` — hover pseudo-class
- `element:focus` — focus pseudo-class
- `element:active` — active pseudo-class
- `element:nth-child(n)` — nth child selector

### CSS Custom Properties (Theming)
```css
:root {
  --fill-primary: #378ADD;
  --fill-secondary: #1D9E75;
  --text-primary: #2C2C2A;
  --text-secondary: #5F5E5A;
  --bg-card: #FFFFFF;
  --border: #D3D1C7;
}

@media (prefers-color-scheme: dark) {
  :root {
    --fill-primary: #85B7EB;
    --fill-secondary: #5DCAA5;
    --text-primary: #F1EFE8;
    --text-secondary: #D3D1C7;
    --bg-card: #2C2C2A;
    --border: #5F5E5A;
  }
}

.box { fill: var(--bg-card); stroke: var(--border); }
.title { fill: var(--text-primary); }
```

## SVG Animations

### CSS Keyframe Animations
```svg
<style>
  @keyframes drawLine {
    from { stroke-dashoffset: 1000; }
    to { stroke-dashoffset: 0; }
  }
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes pulse {
    0%, 100% { r: 8; }
    50% { r: 12; }
  }
  @keyframes rotate360 {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  @keyframes dashOffset {
    from { stroke-dashoffset: 200; }
    to { stroke-dashoffset: 0; }
  }
  @keyframes scaleIn {
    from { transform: scale(0); }
    to { transform: scale(1); }
  }
  .line-draw { stroke-dasharray: 1000; stroke-dashoffset: 1000; animation: drawLine 2s ease-out forwards; }
  .node-enter { animation: fadeSlideIn 0.5s ease-out forwards; animation-delay: 0.2s; opacity: 0; }
  .pulse-dot { animation: pulse 2s ease-in-out infinite; }
  .spin { animation: rotate360 2s linear infinite; transform-origin: center; }
</style>
```

### SMIL Animations (Synchronized Multimedia Integration Language)

**`<animate>`** — Animate a single attribute:
```svg
<circle cx="100" cy="100" r="10" fill="#378ADD">
  <animate attributeName="r" values="10;20;10" dur="2s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
</circle>
```

**`<animateTransform>`** — Animate transforms:
```svg
<rect x="0" y="0" width="40" height="40" fill="#1D9E75">
  <animateTransform attributeName="transform" type="rotate"
                    from="0 100 100" to="360 100 100"
                    dur="3s" repeatCount="indefinite"/>
</rect>
```

**`<animateMotion>`** — Animate along a path:
```svg
<circle cx="0" cy="0" r="8" fill="#DC267F">
  <animateMotion dur="4s" repeatCount="indefinite"
    path="M100 100 C 150 50, 250 150, 300 100 C 350 50, 450 150, 500 100"/>
</circle>
```

**SMIL with multiple attributes**:
```svg
<rect x="50" y="50" width="100" height="60" rx="6" fill="#7F77DD">
  <animate attributeName="width" values="100;150;100" dur="3s" repeatCount="indefinite"/>
  <animate attributeName="height" values="60;80;60" dur="3s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="1;0.6;1" dur="3s" repeatCount="indefinite"/>
</rect>
```

**Sequential animations with `begin`**:
```svg
<circle cx="100" cy="100" r="10" fill="#378ADD">
  <animate attributeName="cy" values="100;50;100" dur="1s" begin="0s" fill="freeze"/>
</circle>
<circle cx="200" cy="100" r="10" fill="#1D9E75">
  <animate attributeName="cy" values="100;50;100" dur="1s" begin="0.5s" fill="freeze"/>
</circle>
<circle cx="300" cy="100" r="10" fill="#DC267F">
  <animate attributeName="cy" values="100;50;100" dur="1s" begin="1s" fill="freeze"/>
</circle>
```

## Interactive SVG

### JavaScript Event Handlers
```svg
<svg xmlns="http://www.w3.org/2000/svg" onload="init(evt)">
  <script type="text/javascript"><![CDATA[
    function init(evt) {
      var svg = evt.target;
      var nodes = svg.querySelectorAll('.interactive');
      nodes.forEach(function(node) {
        node.addEventListener('click', function(e) {
          var detail = this.getAttribute('data-detail');
          var tooltip = svg.getElementById('tooltip');
          tooltip.textContent = detail;
          tooltip.setAttribute('opacity', 1);
        });
      });
    }
  ]]></script>
  <rect class="interactive" x="20" y="20" width="100" height="50" rx="6"
        fill="#378ADD" data-detail="Clicked: Item A"/>
  <text id="tooltip" x="50" y="200" class="ts" opacity="0" transition="opacity 0.3s"/>
</svg>
```

### Hover Effects with CSS
```svg
<style>
  .hover-box { transition: all 0.3s ease; }
  .hover-box:hover { fill: #185FA5; stroke: #0C447C; stroke-width: 2.5; transform: translateY(-2px); }
  .hover-text { transition: fill 0.3s ease; }
  .group:hover .hover-text { fill: #185FA5; }
  .clickable { cursor: pointer; }
</style>
<g class="group">
  <rect class="hover-box" x="20" y="20" width="150" height="60" rx="6"
        fill="#378ADD" stroke="#185FA5" stroke-width="1.5"/>
  <text class="hover-text" x="95" y="55" class="th" text-anchor="middle" fill="white">Hover Me</text>
</g>
```

### Tooltip Implementation
```svg
<style>
  .tooltip { opacity: 0; transition: opacity 0.2s; pointer-events: none; }
  .tooltip-bg { fill: #2C2C2A; rx: 4; }
  .tooltip-text { fill: #F1EFE8; font-size: 12px; font-family: system-ui; }
  .has-tooltip:hover + .tooltip, .tooltip:hover { opacity: 1; }
</style>
<g>
  <rect class="has-tooltip" x="50" y="50" width="80" height="40" rx="4" fill="#378ADD" cursor="pointer"/>
  <g class="tooltip" transform="translate(40, 100)">
    <rect class="tooltip-bg" x="-5" y="-20" width="110" height="30"/>
    <text class="tooltip-text" x="50" y="0" text-anchor="middle">Click for details</text>
  </g>
</g>
```

## Text and Typography

### Text Elements
```svg
<text x="100" y="50" font-family="system-ui, sans-serif" font-size="16"
      font-weight="bold" fill="#2C2C2A" text-anchor="middle">Title Text</text>
```

### Text Attributes
- `font-family`: Font stack
- `font-size`: Size in px (prefer 12px, 14px, 16px)
- `font-weight`: `normal`, `bold`, or numeric (300, 400, 500, 600, 700)
- `font-style`: `normal`, `italic`
- `text-anchor`: `start`, `middle`, `end`
- `dominant-baseline`: `auto`, `central`, `hanging`, `middle`, `text-after-edge`, `text-before-edge`
- `letter-spacing`: Character spacing
- `fill`: Text color
- `opacity`: Text opacity

### Multi-Line Text with `<tspan>`
```svg
<text x="100" y="50" class="t" text-anchor="middle">
  <tspan x="100" dy="0">Line 1: Main Title</tspan>
  <tspan x="100" dy="20" font-size="12" fill="#5F5E5A">Line 2: Subtitle text here</tspan>
  <tspan x="100" dy="18" font-size="12" fill="#888780">Line 3: Additional details</tspan>
</text>
```

### `<tspan>` Attributes
- `x`: Absolute X position (can reset per line)
- `dx`: Relative X offset
- `dy`: Relative Y offset (use for line spacing)
- `rotate`: Rotate individual characters
- `textLength`: Stretch text to exact width

### `<textPath>` — Text Along a Path
```svg
<defs>
  <path id="curve" d="M50 100 C 150 20, 250 20, 350 100" fill="none"/>
</defs>
<text font-size="14" fill="#534AB7">
  <textPath href="#curve" startOffset="50%" text-anchor="middle">
    Text following a curved path
  </textPath>
</text>
```

### Font Size System
- `t-xl`: 18px, bold — section headings
- `t-l`: 16px, bold — card titles
- `t`: 14px, regular — body text (primary)
- `th`: 14px, medium 500 — headings
- `ts`: 12px, regular — secondary/caption
- `txs`: 10px, regular — small labels (use sparingly)

## Gradients

### Linear Gradient
```svg
<defs>
  <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#648FFF"/>
    <stop offset="100%" stop-color="#378ADD"/>
  </linearGradient>
  <linearGradient id="grad-teal" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="#1D9E75"/>
    <stop offset="100%" stop-color="#0F6E56"/>
  </linearGradient>
  <linearGradient id="grad-warm" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#FE6100"/>
    <stop offset="50%" stop-color="#FFB000"/>
    <stop offset="100%" stop-color="#F0E442"/>
  </linearGradient>
</defs>

<rect x="20" y="20" width="200" height="80" rx="8" fill="url(#grad-blue)"/>
<rect x="240" y="20" width="200" height="80" rx="8" fill="url(#grad-teal)"/>
<rect x="20" y="120" width="420" height="40" rx="6" fill="url(#grad-warm)"/>
```

### Radial Gradient
```svg
<defs>
  <radialGradient id="radial-glow" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#648FFF" stop-opacity="0.8"/>
    <stop offset="100%" stop-color="#648FFF" stop-opacity="0"/>
  </radialGradient>
</defs>

<circle cx="100" cy="100" r="80" fill="url(#radial-glow)"/>
<circle cx="100" cy="100" r="20" fill="#648FFF"/>
```

### Pattern Fill
```svg
<defs>
  <pattern id="dots" patternUnits="userSpaceOnUse" width="10" height="10">
    <circle cx="5" cy="5" r="2" fill="#888780"/>
  </pattern>
  <pattern id="stripes" patternUnits="userSpaceOnUse" width="20" height="20"
           patternTransform="rotate(45)">
    <rect width="10" height="20" fill="#378ADD" opacity="0.3"/>
  </pattern>
  <pattern id="crosshatch" patternUnits="userSpaceOnUse" width="16" height="16">
    <path d="M0 8 L16 8 M8 0 L8 16" stroke="#888780" stroke-width="1" opacity="0.3"/>
  </pattern>
</defs>

<rect x="20" y="20" width="150" height="100" rx="6" fill="url(#dots)"/>
<rect x="190" y="20" width="150" height="100" rx="6" fill="url(#stripes)"/>
<rect x="360" y="20" width="150" height="100" rx="6" fill="url(#crosshatch)"/>
```

## Filters

### Drop Shadow
```svg
<defs>
  <filter id="drop-shadow" x="-10%" y="-10%" width="130%" height="130%">
    <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.15"/>
  </filter>
  <filter id="shadow-heavy" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.25"/>
  </filter>
</defs>

<rect x="50" y="50" width="200" height="80" rx="8" fill="white" filter="url(#drop-shadow)"/>
```

### Blur
```svg
<defs>
  <filter id="blur-light">
    <feGaussianBlur stdDeviation="2"/>
  </filter>
  <filter id="blur-heavy">
    <feGaussianBlur stdDeviation="8"/>
  </filter>
</defs>

<rect x="50" y="50" width="100" height="80" fill="#378ADD" filter="url(#blur-light)"/>
```

### Color Matrix
```svg
<defs>
  <filter id="grayscale">
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <filter id="sepia">
    <feColorMatrix type="matrix"
      values="0.393 0.769 0.189 0 0
              0.349 0.686 0.168 0 0
              0.272 0.534 0.131 0 0
              0     0     0     1 0"/>
  </filter>
  <filter id="brightness">
    <feComponentTransfer>
      <feFuncR type="linear" slope="1.2"/>
      <feFuncG type="linear" slope="1.2"/>
      <feFuncB type="linear" slope="1.2"/>
    </feComponentTransfer>
  </filter>
</defs>

<g filter="url(#grayscale)"><rect x="20" y="20" width="100" height="80" fill="#378ADD"/></g>
<g filter="url(#sepia)"><rect x="140" y="20" width="100" height="80" fill="#1D9E75"/></g>
```

### feMerge (Composite Filter)
```svg
<defs>
  <filter id="glow">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  <filter id="neon">
    <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1"/>
    <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur2"/>
    <feMerge>
      <feMergeNode in="blur2"/>
      <feMergeNode in="blur1"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>

<text x="100" y="100" font-size="24" font-weight="bold" fill="#378ADD" filter="url(#glow)">Glow Effect</text>
<text x="100" y="140" font-size="24" font-weight="bold" fill="#DC267F" filter="url(#neon)">Neon Effect</text>
```

## Masking and Clipping

### Clipping Path
```svg
<defs>
  <clipPath id="clip-circle">
    <circle cx="100" cy="100" r="80"/>
  </clipPath>
  <clipPath id="clip-rounded">
    <rect x="0" y="0" width="200" height="150" rx="12"/>
  </clipPath>
</defs>

<image x="0" y="0" width="200" height="200" href="photo.jpg"
       clip-path="url(#clip-circle)"/>
```

### Masking
```svg
<defs>
  <linearGradient id="fade-mask" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="white"/>
    <stop offset="100%" stop-color="black"/>
  </linearGradient>
  <mask id="fade">
    <rect x="0" y="0" width="100%" height="100%" fill="url(#fade-mask)"/>
  </mask>
</defs>

<rect x="20" y="20" width="300" height="100" fill="#378ADD" mask="url(#fade)"/>
```

## Responsive SVG

### Making SVGs Responsive
```svg
<!-- Approach 1: viewBox + 100% width -->
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg"
     style="width: 100%; max-width: 680px; height: auto; display: block;">
```

### Fluid Layout Within SVG (Percentages)
```svg
<!-- Use percentage-based positioning for responsive internal layout -->
<rect x="5%" y="5%" width="90%" height="30%" rx="8" fill="#E6F1FB"/>
<text x="50%" y="20%" class="th" text-anchor="middle" fill="#0C447C">Responsive Title</text>

<!-- Two-column responsive layout -->
<rect x="5%" y="40%" width="43%" height="50%" rx="6" fill="#EEEDFE"/>
<rect x="52%" y="40%" width="43%" height="50%" rx="6" fill="#E1F5EE"/>
```

### preserveAspectRatio Values
| Value | Behavior |
|-------|----------|
| `xMidYMid meet` | Center, fit entirely (default) |
| `xMinYMin meet` | Align top-left, fit entirely |
| `xMaxYMax meet` | Align bottom-right, fit entirely |
| `xMidYMid slice` | Center, cover area (may crop) |
| `xMinYMin slice` | Align top-left, cover area |
| `none` | Stretch to fill dimensions |

## Accessibility

### ARIA Labels and Roles
```svg
<svg viewBox="0 0 680 400" role="img"
     aria-label="Quarterly revenue chart showing Q1 $30M through Q4 $240M">
  <title>Revenue by Quarter - 2026</title>
  <desc>A bar chart displaying quarterly revenue for 2026. Q1: $30M, Q2: $90M,
        Q3: $180M, Q4: $240M, showing consistent growth throughout the year.</desc>
</svg>
```

### Accessible Elements
```svg
<g role="button" tabindex="0" aria-label="View details for North America region"
   onclick="showDetails('na')" onkeypress="if(event.key==='Enter')showDetails('na')">
  <rect x="50" y="50" width="100" height="60" rx="6" fill="#378ADD"/>
  <text x="100" y="85" class="th" text-anchor="middle" fill="white">NA</text>
</g>
```

## Accessibility Checklist
- Every SVG has `role="img"` and `aria-label`
- Every SVG has `<title>` and `<desc>` elements
- Interactive elements have `tabindex="0"` and keyboard handlers
- Color is never the sole means of conveying information
- Text contrast ratio >= 4.5:1
- Focus indicators are visible for keyboard navigation

## Optimization

### Minification Rules
1. Remove comments (`<!-- ... -->`)
2. Remove unnecessary whitespace between attributes
3. Combine adjacent `<path>` elements
4. Remove default attribute values
5. Remove empty `<g>` groups
6. Remove `xmlns` if SVG is inline in HTML5

### Precision Reduction
```python
def optimize_svg(svg_content):
    import re
    svg_content = re.sub(r'(\d+\.\d{2,})', lambda m: f'{float(m.group(1)):.1f}', svg_content)
    svg_content = re.sub(r'>\s+<', '><', svg_content)
    svg_content = re.sub(r'\.0(\s|,|")', r'\1', svg_content)
    return svg_content
```

### SVG Size Budget
- Inline in Markdown: < 20KB
- In HTML dashboard: < 50KB per diagram
- Complex infographic: < 100KB
- Animated SVG: < 200KB (consider GIF/WebP fallback)

## Color Ramps (9 Ramps, 7 Stops Each) — EXACT, DO NOT MODIFY

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
- Color encodes MEANING, not sequence
- Purple, teal, coral, pink → general categories / themes
- Blue, green, amber, red → semantic meaning (info, success, warning, error)
- Gray → neutral/structural elements, borders, arrows
- **Max 2 color ramps per diagram** (one primary + one accent maximum)
- Text on colored backgrounds: use 800/900 stops from the SAME ramp
- Never use more than 4 hues in a single diagram
- Use 50/100 stops for background fills
- Use 400/600 stops for interactive/hoverable elements
- Use 800/900 stops for text and icons

### Light/Dark Mode Mapping
| Element | Light Mode | Dark Mode |
|---------|-----------|-----------|
| Background fill | 50 | 900 |
| Card/box fill | white (or 50) | 800 |
| Primary stroke | 400 | 200 |
| Title text | 900 | 50 |
| Body text | 600 | 200 |
| Secondary text | 400 | 400 |
| Border lines | 200 | 600 |
| Hover state | 400 | 400 |
| Accent elements | 400 | 400 |

```css
:root {
  --bg-fill: var(--gray-50);
  --card-fill: #FFFFFF;
  --primary-stroke: var(--blue-400);
  --title-text: var(--gray-900);
  --body-text: var(--gray-600);
  --border: var(--gray-200);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-fill: var(--gray-900);
    --card-fill: var(--gray-800);
    --primary-stroke: var(--blue-200);
    --title-text: var(--gray-50);
    --body-text: var(--gray-200);
    --border: var(--gray-600);
  }
}
```

## SVG Canvas Setup
```svg
viewBox="0 0 680 {HEIGHT}"  -- fixed 680px wide, flexible height
xmlns="http://www.w3.org/2000/svg"
style="font-family: system-ui, sans-serif;"
```

### Font System (CSS Classes)
```css
text.t-xl { font-family: system-ui, sans-serif; font-size: 18px; font-weight: 600; fill: currentColor; }
text.t-l { font-family: system-ui, sans-serif; font-size: 16px; font-weight: 600; fill: currentColor; }
text.t { font-family: system-ui, sans-serif; font-size: 14px; fill: currentColor; }
text.th { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: currentColor; }
text.ts { font-family: system-ui, sans-serif; font-size: 12px; fill: currentColor; }
text.txs { font-family: system-ui, sans-serif; font-size: 10px; fill: currentColor; }
```

### Standard CSS Classes
```css
text.t { font-family: system-ui, sans-serif; font-size: 14px; fill: currentColor; }
text.ts { font-family: system-ui, sans-serif; font-size: 12px; fill: currentColor; }
text.th { font-family: system-ui, sans-serif; font-size: 14px; font-weight: 500; fill: currentColor; }
.box { fill: var(--fill, #F1EFE8); stroke: var(--stroke, #888780); stroke-width: 1.5; rx: 6; }
.node { cursor: pointer; }
.node:hover .box { stroke-width: 2.5; }
.arr { fill: none; stroke: var(--stroke, #888780); stroke-width: 1.5; marker-end: url(#arrow); }
.arr-dashed { fill: none; stroke: #888780; stroke-width: 1.5; stroke-dasharray: 6,4; marker-end: url(#arrow); }
.card { fill: white; stroke: #D3D1C7; stroke-width: 1; rx: 8; }
.card:hover { stroke: #378ADD; stroke-width: 1.5; }
.badge { font-size: 11px; font-weight: 600; }
```

## Diagram Types

### 1. Flowchart
**Best for**: Process flows, decision trees, workflows, algorithms.

```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10" fill="#888780"/>
    </marker>
  </defs>
  <rect x="240" y="20" width="200" height="50" rx="25" fill="#E6F1FB" stroke="#378ADD" stroke-width="1.5"/>
  <text x="340" y="50" class="th" text-anchor="middle" fill="#0C447C">Start</text>
  <line x1="340" y1="70" x2="340" y2="110" class="arr"/>
  <rect x="240" y="110" width="200" height="50" rx="6" fill="#EEEDFE" stroke="#7F77DD" stroke-width="1.5"/>
  <text x="340" y="140" class="th" text-anchor="middle" fill="#3C3489">Process Step</text>
  <line x1="340" y1="160" x2="340" y2="200" class="arr"/>
  <polygon points="340,200 440,245 340,290 240,245" fill="#FAEEDA" stroke="#BA7517" stroke-width="1.5"/>
  <text x="340" y="250" class="ts" text-anchor="middle" fill="#633806">Decision</text>
  <line x1="440" y1="245" x2="520" y2="245" class="arr"/>
  <rect x="520" y="220" width="120" height="50" rx="6" fill="#EAF3DE" stroke="#639922" stroke-width="1.5"/>
  <text x="580" y="250" class="ts" text-anchor="middle" fill="#3B6D11">Yes Path</text>
  <line x1="340" y1="290" x2="340" y2="340" class="arr"/>
  <rect x="240" y="340" width="200" height="50" rx="25" fill="#FCEBEB" stroke="#E24B4A" stroke-width="1.5"/>
  <text x="340" y="370" class="th" text-anchor="middle" fill="#A32D2D">End</text>
</svg>
```

**Flowchart shapes guide**: Pill (rx=25): Start/End, Rounded rect (rx=6): Process/Action, Diamond: Decision, Parallelogram: Input/Output, Document: Report, Circle: Connector.

### 2. Architecture / System Diagram
**Best for**: System architecture, cloud infrastructure, software components, network diagrams.

**Conventions**: Dashed borders = logical groupings, Solid borders = actual components, Colors per tier (Blue=Network, Purple=App, Green=Data, Coral=External), Arrows = data flow direction.

```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="20" width="640" height="360" rx="12" fill="none" stroke="#B4B2A9" stroke-dasharray="8,4" stroke-width="1.5"/>
  <text x="40" y="50" class="th" fill="#5F5E5A">System Boundary</text>
  <rect x="190" y="70" width="300" height="50" rx="8" fill="#E6F1FB" stroke="#378ADD" stroke-width="1.5"/>
  <text x="340" y="97" class="th" text-anchor="middle" fill="#0C447C">Load Balancer</text>
  <rect x="50" y="150" width="260" height="200" rx="8" fill="none" stroke="#D3D1C7" stroke-dasharray="6,3" stroke-width="1"/>
  <text x="180" y="175" class="ts" text-anchor="middle" fill="#5F5E5A">App Tier</text>
  <rect x="65" y="185" width="100" height="50" rx="6" fill="#EEEDFE" stroke="#7F77DD" stroke-width="1.5"/>
  <text x="115" y="210" class="ts" text-anchor="middle" fill="#3C3489">Server 1</text>
  <rect x="185" y="185" width="100" height="50" rx="6" fill="#EEEDFE" stroke="#7F77DD" stroke-width="1.5"/>
  <text x="235" y="210" class="ts" text-anchor="middle" fill="#3C3489">Server 2</text>
  <rect x="370" y="150" width="260" height="200" rx="8" fill="none" stroke="#D3D1C7" stroke-dasharray="6,3" stroke-width="1"/>
  <text x="500" y="175" class="ts" text-anchor="middle" fill="#5F5E5A">Data Tier</text>
  <rect x="385" y="185" width="100" height="50" rx="6" fill="#E1F5EE" stroke="#1D9E75" stroke-width="1.5"/>
  <text x="435" y="210" class="ts" text-anchor="middle" fill="#0F6E56">Primary DB</text>
  <rect x="505" y="185" width="100" height="50" rx="6" fill="#E1F5EE" stroke="#1D9E75" stroke-width="1.5"/>
  <text x="555" y="210" class="ts" text-anchor="middle" fill="#0F6E56">Replica DB</text>
  <line x1="340" y1="120" x2="115" y2="185" class="arr"/>
  <line x1="340" y1="120" x2="235" y2="185" class="arr"/>
  <line x1="115" y1="235" x2="435" y2="185" class="arr"/>
  <line x1="235" y1="235" x2="555" y2="185" class="arr"/>
</svg>
```

### 3. Timeline / Gantt Chart
**Best for**: Project timelines, roadmaps, milestones.

**Best practices**: Sort chronologically, use consistent intervals, mark "Today" with dashed red line, 2-4 word labels, group related phases with color.

```svg
<svg viewBox="0 0 680 320" xmlns="http://www.w3.org/2000/svg">
  <text x="340" y="30" class="t-l" text-anchor="middle" fill="#0C447C">Project Timeline 2026</text>
  <text x="90" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">Jan</text>
  <text x="190" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">Mar</text>
  <text x="290" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">May</text>
  <text x="390" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">Jul</text>
  <text x="490" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">Sep</text>
  <text x="590" y="60" class="ts" text-anchor="middle" fill="#5F5E5A">Nov</text>
  <text x="50" y="100" class="ts" text-anchor="end" fill="#5F5E5A">Phase 1</text>
  <text x="50" y="140" class="ts" text-anchor="end" fill="#5F5E5A">Phase 2</text>
  <text x="50" y="180" class="ts" text-anchor="end" fill="#5F5E5A">Phase 3</text>
  <text x="50" y="220" class="ts" text-anchor="end" fill="#5F5E5A">Phase 4</text>
  <text x="50" y="260" class="ts" text-anchor="end" fill="#5F5E5A">Phase 5</text>
  <rect x="60" y="88" width="200" height="16" rx="3" fill="#378ADD"/>
  <rect x="130" y="128" width="210" height="16" rx="3" fill="#1D9E75"/>
  <rect x="240" y="168" width="240" height="16" rx="3" fill="#7F77DD"/>
  <rect x="340" y="208" width="160" height="16" rx="3" fill="#D85A30"/>
  <rect x="200" y="248" width="280" height="16" rx="3" fill="#EF9F27"/>
  <line x1="350" y1="65" x2="350" y2="280" stroke="#E24B4A" stroke-width="2" stroke-dasharray="4,4"/>
  <text x="350" y="65" class="txs" text-anchor="middle" fill="#E24B4A">Today</text>
</svg>
```

### 4. Organization Chart
**Best for**: Team structures, reporting lines, hierarchy.

**Conventions**: Root at top, children below, same level = same box size, reporting lines = vertical lines, max 4 levels, include name + title.

```svg
<svg viewBox="0 0 680 350" xmlns="http://www.w3.org/2000/svg">
  <style>
    .org-box { fill: #E6F1FB; stroke: #378ADD; stroke-width: 1.5; rx: 6; }
    .org-box-sub { fill: #EEEDFE; stroke: #7F77DD; stroke-width: 1.5; rx: 6; }
    .org-line { fill: none; stroke: #888780; stroke-width: 1.5; }
  </style>
  <rect x="240" y="20" width="200" height="50" rx="6" class="org-box"/>
  <text x="340" y="44" class="th" text-anchor="middle" fill="#0C447C">CEO</text>
  <path d="M340 70 L340 90 L170 90 L170 110" class="org-line"/>
  <path d="M340 70 L340 90 L510 90 L510 110" class="org-line"/>
  <path d="M340 70 L340 130 L340 150" class="org-line"/>
  <rect x="80" y="110" width="180" height="50" rx="6" class="org-box-sub"/>
  <text x="170" y="134" class="ts" text-anchor="middle" fill="#3C3489">VP Engineering</text>
  <rect x="420" y="110" width="180" height="50" rx="6" class="org-box-sub"/>
  <text x="510" y="134" class="ts" text-anchor="middle" fill="#3C3489">VP Product</text>
  <rect x="250" y="150" width="180" height="50" rx="6" class="org-box-sub"/>
  <text x="340" y="174" class="ts" text-anchor="middle" fill="#3C3489">VP Operations</text>
  <path d="M170 160 L170 180 L110 180 L110 200" class="org-line"/>
  <path d="M170 160 L170 180 L230 180 L230 200" class="org-line"/>
  <rect x="50" y="200" width="120" height="40" rx="4" fill="#E1F5EE" stroke="#1D9E75" stroke-width="1"/>
  <text x="110" y="225" class="txs" text-anchor="middle" fill="#0F6E56">Eng Mgr</text>
  <rect x="170" y="200" width="120" height="40" rx="4" fill="#E1F5EE" stroke="#1D9E75" stroke-width="1"/>
  <text x="230" y="225" class="txs" text-anchor="middle" fill="#0F6E56">QA Mgr</text>
</svg>
```

### 5. Mind Map
**Best for**: Brainstorming, topic exploration.

**Rules**: Center pill = main concept, curved branches (quadratic bezier), Level 1 = rounded rects, Max 6 branches, spread evenly around center, 2-5 words per node.

```svg
<svg viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg">
  <style>
    .mind-center { fill: #378ADD; stroke: #185FA5; stroke-width: 2; rx: 30; }
    .mind-node { fill: #E6F1FB; stroke: #378ADD; stroke-width: 1.5; rx: 8; }
  </style>
  <rect x="240" y="160" width="200" height="60" class="mind-center"/>
  <text x="340" y="190" class="t" text-anchor="middle" fill="white" font-weight="bold">Main Topic</text>
  <text x="340" y="208" class="txs" text-anchor="middle" fill="#B5D4F4">Central Theme</text>
  <path d="M440 170 Q 500 110, 530 110" fill="none" stroke="#378ADD" stroke-width="1.5"/>
  <rect x="500" y="80" width="150" height="60" class="mind-node"/>
  <text x="575" y="108" class="ts" text-anchor="middle" fill="#0C447C">Topic A</text>
  <path d="M240 170 Q 180 110, 150 110" fill="none" stroke="#7F77DD" stroke-width="1.5"/>
  <rect x="30" y="80" width="150" height="60" rx="8" fill="#EEEDFE" stroke="#7F77DD" stroke-width="1.5"/>
  <text x="105" y="108" class="ts" text-anchor="middle" fill="#3C3489">Topic B</text>
  <path d="M340 220 Q 340 300, 240 310" fill="none" stroke="#1D9E75" stroke-width="1.5"/>
  <rect x="170" y="280" width="150" height="60" rx="8" fill="#E1F5EE" stroke="#1D9E75" stroke-width="1.5"/>
  <text x="245" y="308" class="ts" text-anchor="middle" fill="#0F6E56">Topic C</text>
  <path d="M440 190 Q 520 300, 460 310" fill="none" stroke="#D85A30" stroke-width="1.5"/>
  <rect x="390" y="280" width="150" height="60" rx="8" fill="#FAECE7" stroke="#D85A30" stroke-width="1.5"/>
  <text x="465" y="308" class="ts" text-anchor="middle" fill="#993C1D">Topic D</text>
</svg>
```

### 6. Wireframe / UI Mockup
**Best for**: Screen mockups, layout prototypes, app wireframes.

**Best practices**: Gray-scale layout, system-ui font, card-based design (8px grid), realistic mock content, screen sizes: 375x812 (iPhone), 1280x800 (Desktop).

```svg
<svg viewBox="0 0 360 650" xmlns="http://www.w3.org/2000/svg">
  <style>
    .wf-card { fill: white; stroke: #D3D1C7; stroke-width: 1; rx: 8; }
    .wf-header { fill: #378ADD; }
    .wf-text { font-family: system-ui; font-size: 12px; fill: #5F5E5A; }
    .wf-title { font-family: system-ui; font-size: 14px; font-weight: bold; fill: #2C2C2A; }
    .wf-label { font-family: system-ui; font-size: 10px; fill: #888780; }
  </style>
  <rect x="10" y="10" width="340" height="630" rx="20" fill="#2C2C2A"/>
  <rect x="15" y="15" width="330" height="620" rx="16" fill="#F1EFE8"/>
  <rect x="15" y="15" width="330" height="30" rx="16" fill="#2C2C2A"/>
  <text x="30" y="35" font-size="10" fill="white" font-family="system-ui">9:41</text>
  <rect x="20" y="50" width="320" height="60" rx="8" class="wf-header"/>
  <text x="180" y="85" class="th" text-anchor="middle" fill="white">Dashboard</text>
  <rect x="30" y="125" width="300" height="36" rx="18" class="wf-card"/>
  <text x="50" y="148" class="wf-label">Search...</text>
  <rect x="25" y="175" width="310" height="100" rx="8" class="wf-card"/>
  <rect x="35" y="185" width="290" height="35" rx="4" fill="#E6F1FB"/>
  <text x="180" y="208" class="wf-title" text-anchor="middle">Analytics Summary</text>
  <rect x="40" y="230" width="80" height="30" rx="4" fill="#E1F5EE"/>
  <text x="80" y="250" class="txs" text-anchor="middle" fill="#0F6E56">+12.5%</text>
  <rect x="135" y="230" width="80" height="30" rx="4" fill="#EEEDFE"/>
  <text x="175" y="250" class="txs" text-anchor="middle" fill="#534AB7">$45.2K</text>
  <rect x="25" y="290" width="310" height="80" rx="8" class="wf-card"/>
  <text x="40" y="315" class="wf-title">Recent Activity</text>
  <line x1="40" y1="325" x2="320" y2="325" stroke="#F1EFE8" stroke-width="1"/>
  <text x="40" y="345" class="wf-text">User logged in · 2 min ago</text>
  <text x="40" y="360" class="wf-text">Report generated · 15 min ago</text>
</svg>
```

### Animated Loading Spinner
```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <style>
    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes dash {
      0% { stroke-dasharray: 1, 200; stroke-dashoffset: 0; }
      50% { stroke-dasharray: 90, 200; stroke-dashoffset: -35px; }
      100% { stroke-dasharray: 90, 200; stroke-dashoffset: -124px; }
    }
    .spinner { animation: spin 2s linear infinite; transform-origin: 50px 50px; }
    .spinner-track { stroke: #F1EFE8; fill: none; stroke-width: 6; }
    .spinner-arc { stroke: #378ADD; fill: none; stroke-width: 6; stroke-linecap: round;
                   animation: dash 1.5s ease-in-out infinite; }
  </style>
  <circle cx="50" cy="50" r="40" class="spinner-track"/>
  <g class="spinner"><circle cx="50" cy="50" r="40" class="spinner-arc"/></g>
</svg>
```

### Animated Progress Indicator
```svg
<svg viewBox="0 0 300 30" xmlns="http://www.w3.org/2000/svg">
  <style>
    .progress-bg { fill: #F1EFE8; rx: 15; }
    .progress-fill { fill: #378ADD; rx: 15; animation: fillBar 3s ease-out forwards; }
    @keyframes fillBar { from { width: 0; } to { width: 220; } }
  </style>
  <rect x="10" y="5" width="280" height="20" class="progress-bg"/>
  <rect x="10" y="5" width="0" height="20" class="progress-fill"/>
  <text x="150" y="19" class="txs" text-anchor="middle" fill="white" font-weight="bold">75%</text>
</svg>
```

## Integration with Other Skills

### With Chart Skill
```python
result = _make_chart('bar', {'categories': ['Q1','Q2','Q3','Q4'], 'values': [100,200,150,300]}, 'svg')
```

### With PDF Skill
```python
create_pdf(sections=[
    {'type': 'svg', 'svg_content': svg_string, 'width': 500, 'height': 300},
])
```

### With PPTX Skill
```python
create_pptx(sections=[
    {'type': 'svg_slide', 'svg': svg_string},
])
```

## Troubleshooting

### SVG Not Rendering
1. Check viewBox attribute is present
2. Verify XML is well-formed (no unclosed tags)
3. Check xmlns="http://www.w3.org/2000/svg"
4. Verify closing </svg> tag exists

### Text Overflow
1. Reduce font size
2. Use `<tspan>` with `dy` for multi-line
3. Increase container width

### Scaled Incorrectly
1. Verify viewBox matches content coordinates
2. Check preserveAspectRatio setting
3. Ensure width/height attributes are set

### Animation Not Running
1. Check CSS @keyframes syntax
2. Verify animation property syntax
3. Ensure element exists at animation start

### Accessibility Issues
1. Add role="img" and aria-label to root SVG
2. Add `<title>` and `<desc>` elements
3. Ensure text contrast >= 4.5:1

## Quality Checklist

### Structure
1. viewBox is set correctly (0 0 WIDTH HEIGHT)
2. xmlns attribute is present
3. Closing </svg> tag exists
4. All tags are properly closed
5. No empty <g> groups
6. No duplicate IDs

### Design
7. Max 2 color ramps used
8. Max 4 hues in diagram
9. Text size >= 12px (ts or larger)
10. Text contrast >= 4.5:1
11. No pure black (#000) or pure white (#FFF)
12. Consistent font sizes (t, th, ts)
13. No text overlapping elements
14. Proper spacing between elements

### Diagram Logic
15. Flow direction is clear (top-to-bottom or left-to-right)
16. Arrows point in logical direction
17. All branches/connections are labeled
18. Legend or labels explain all colors
19. Hierarchical levels are visually distinct

### Accessibility
20. role="img" and aria-label on root SVG
21. `<title>` element present
22. `<desc>` element describes content
23. Interactive elements have keyboard handlers
24. Color is not the only visual differentiator

### Optimization
25. No unnecessary whitespace
26. No commented-out code
27. Decimal precision reduced to 1 place
28. SVG file size within budget
29. No embedded raster images
30. CSS classes used instead of inline styles

## Critical Rules — What to AVOID
- NEVER use more than 2 color ramps per diagram
- NEVER exceed 4 boxes per row
- NEVER use font sizes smaller than 12px (ts) or 14px (t/th)
- NEVER use rainbow cycling for data — use semantic color mapping
- NEVER overlap text elements
- NEVER create SVG without proper viewBox
- NEVER omit stroke-width on lines/arrows
- NEVER use black (#000) or pure white (#FFF) for text
- NEVER use emoji in diagrams (replace with shapes/icons)
- NEVER use `<foreignObject>` which breaks in many renderers
- NEVER use 3D transforms in SVG (use SMIL or CSS 2D transforms only)

## Advanced Pattern: SVG to PNG Conversion
```python
import cairosvg

def svg_to_png(svg_string, output_path, scale=2):
    """Convert SVG string to PNG with high DPI."""
    cairosvg.svg2png(
        bytestring=svg_string.encode('utf-8'),
        write_to=output_path,
        scale=scale,
        output_width=None,
        output_height=None
    )

# Alternative via svglib + reportlab
# from svglib.svglib import svg2rlg
# from reportlab.graphics import renderPM
# drawing = svg2rlg(StringIO(svg_string))
# renderPM.drawToFile(drawing, "output.png", fmt="PNG")
```

## SVG Embedding Patterns

### In Markdown (GitHub-Flavored)
```markdown
<!-- Direct SVG embed (works in most renderers) -->
![Diagram](diagram.svg)

<!-- Raw HTML embed (for inline SVG with styles) -->
<div align="center">
  <img src="data:image/svg+xml;utf8,<svg ...>...</svg>" alt="Diagram">
</div>
```

### In HTML
```html
<!-- Inline SVG (preferred for interactivity) -->
<div class="svg-container">
  <svg viewBox="0 0 680 400">...</svg>
</div>

<!-- As image source -->
<img src="diagram.svg" alt="Diagram" width="680" height="400">
```

### In PDF via create_pdf
```python
create_pdf(sections=[
    {'type': 'svg', 'svg_content': svg_str, 'width': 500, 'height': 300},
])
```

## SVG Fallback Strategy
For email clients or legacy systems that don't support SVG:
1. Generate PNG fallback: `svg_to_png(svg_string, 'fallback.png')`
2. Use `<picture>` element: `<picture><source srcset="diagram.svg" type="image/svg+xml"><img src="fallback.png"></picture>`
3. For email: inline base64 PNG as fallback

## SVG Security Considerations
- Sanitize user-provided SVG to prevent XSS (remove `<script>`, `on*` attributes)
- Use `DOMPurify` or similar library for user-uploaded SVGs
- Never render untrusted SVG with JavaScript enabled
- Strip external resources (fonts, images) from SVGs used in untrusted contexts

## Performance Optimization for Complex SVGs
1. Use `<use>` elements for repeated shapes
2. Flatten nested `<g>` groups
3. Remove unused defs
4. Convert paths to relative coordinates where shorter
5. Use integer coordinates where possible (no decimals)
6. Avoid complex filters on mobile renderers
7. Limit SMIL animations to 3 concurrent elements
