---
name: svg
location: friday/skills/svg/SKILL.md
trigger: icon, logo, vector graphic, illustration, simple diagram shape, favicon
platform: Windows (FRIDAY host machine)
---

# SVG — FRIDAY Playbook (Full)

SVG is text (XML). No compiler, no safety net — bad markup renders wrong
silently. Verification by actual rendering is not optional here.

## 0. Environment setup

```powershell
pip install svgwrite cairosvg Pillow
# rsvg-convert (faster, more standards-compliant SVG->raster) is Linux/macOS-first;
# on Windows, cairosvg is the more reliable pip-installable renderer for verify.
```

```bash
python friday/skills/svg/scripts/check_env.py
```

## 1. Structure baseline

```xml
<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
  <!-- content -->
</svg>
```

- **Always set `viewBox`.** This is what makes the SVG scale cleanly in any
  container — a fixed `width`/`height` without viewBox breaks responsive use.
- Work in the viewBox's own coordinate space; don't tie shape coordinates to
  a specific expected screen size.
- If the SVG needs a transparent background (most icon/logo use cases),
  don't add a background `<rect>` at all — absence of one is transparency.
  If a solid background is wanted, add it as the FIRST child so nothing
  paints under other elements accidentally.

## 2. Color and theming

- Define palette as literal hex values used consistently — don't let colors
  drift by even one shade between elements meant to match.
- Decide the palette before writing paths/shapes, not after — retrofitting
  color onto finished geometry usually looks patched-together rather than
  designed.
- For icons meant to sit inside HTML/CSS-controlled UI, use `currentColor`
  so CSS controls fill/stroke color instead of hardcoding it:
  ```xml
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="..."/>
  </svg>
  ```
- For a dark-neon aesthetic specifically (per FRIDAY's usual visual
  direction — only apply when a request implies it, not as a default): favor
  saturated accent colors (electric blue `#00D4FF`, neon magenta `#FF2E9A`,
  acid green `#39FF88`) against near-black backgrounds `#0A0A0F`–`#111318`,
  and consider a subtle glow via `<feGaussianBlur>` (see §6).

## 3. Primitives vs paths

Use primitives whenever the shape allows — far more readable/editable than
raw path data:

```xml
<rect x="10" y="10" width="100" height="60" rx="8" fill="#1E2761"/>
<circle cx="50" cy="50" r="40" fill="#00D4FF"/>
<line x1="0" y1="0" x2="100" y2="100" stroke="#FFFFFF" stroke-width="2"/>
<polygon points="50,10 90,90 10,90" fill="#FF2E9A"/>
<polyline points="0,50 25,25 50,50 75,25 100,50" fill="none" stroke="#39FF88" stroke-width="3"/>
```

Reach for `<path>` only for genuinely custom curves:
```xml
<path d="M10,80 C40,10 65,10 95,80" stroke="#00D4FF" stroke-width="3" fill="none"/>
```

If generating path data programmatically (e.g. from Python for a data-driven
shape), round coordinates to 1-2 decimal places — excess precision bloats
file size with zero visual benefit:
```python
def fmt(n): return f"{round(n, 2):g}"
```

## 4. Text in SVG — the #1 source of broken output

**SVG text does not auto-wrap.** A long string in a single `<text>` element
runs straight off the canvas edge. Manually split into `<tspan>` elements
with explicit line-height offsets:

```xml
<text x="20" y="40" font-family="Arial" font-size="18" fill="#FFFFFF">
  <tspan x="20" dy="0">First line of text</tspan>
  <tspan x="20" dy="24">Second line continues here</tspan>
</text>
```

For programmatic wrapping (Python), estimate character width and break
manually before emitting tspans:

```python
def wrap_text(text, max_chars_per_line):
    words = text.split()
    lines, current = [], []
    for word in words:
        current.append(word)
        if len(" ".join(current)) > max_chars_per_line:
            current.pop()
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines
```

- Don't assume custom/downloaded fonts are available to whoever views the
  raw `.svg` file directly — stick to web-safe fonts (`Arial`, `Helvetica`,
  `sans-serif`) unless the SVG is embedded in an HTML page with `@font-face`
  guaranteeing the font loads.
- `text-anchor="middle"` centers on the given x — useful for centered
  labels without manual width calculation:
  ```xml
  <text x="200" y="40" text-anchor="middle" font-size="24">Centered Title</text>
  ```

## 5. Icons specifically

- Keep icon SVGs on a square viewBox — `0 0 24 24` is the standard
  convention (matches most icon systems, drops into UI slots without extra
  transform math).
- Consistent stroke width across an icon SET matters more than within one
  icon — if building multiple icons for the same UI, fix `stroke-width` as a
  shared constant.
- Export a favicon-ready version separately if needed — favicons typically
  want a simplified/bolder version of a logo, not a direct shrink of a
  detailed one (fine details disappear at 16x16/32x32).

## 6. Gradients and filters — use sparingly, verify rendering

```xml
<defs>
  <linearGradient id="neonGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#00D4FF"/>
    <stop offset="100%" stop-color="#FF2E9A"/>
  </linearGradient>
  <filter id="glow">
    <feGaussianBlur stdDeviation="4" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
<circle cx="50" cy="50" r="30" fill="url(#neonGrad)" filter="url(#glow)"/>
```

Gradients/filters render inconsistently across some consumers (older PDF
converters, some print pipelines, some older image viewers). If the SVG must
be reliable across many contexts (e.g. it'll get embedded in a generated PDF
via §7 below), prefer flat color and add glow/gradient only after confirming
the target renderer handles it — check by actually converting and viewing.

## 7. Embedding SVG into other formats

- **Into HTML**: inline directly (`<svg>...</svg>` in the markup) for full
  CSS/JS control (color via `currentColor`, hover states, animation), or
  `<img src="icon.svg">` for simplicity when interactivity isn't needed.
- **Into PDF (via reportlab)**: reportlab doesn't render SVG natively —
  convert to PNG first, then embed as an image (see pdf/SKILL.md §4 chart
  pattern, same technique):
  ```python
  import cairosvg
  cairosvg.svg2png(url="icon.svg", write_to="icon.png", output_width=400)
  ```
- **Into DOCX/PPTX**: same story — python-docx/python-pptx need a raster
  image, convert first via cairosvg.

## 8. Verify before delivering (mandatory)

There's no compile step — the only way to catch a broken SVG is to actually
render and look at it:

```bash
python friday/skills/svg/scripts/verify_svg.py output.svg
```

This converts to PNG at a few sizes (to catch icon-scaling issues
specifically) and reports file structure issues (missing viewBox, empty
document, unclosed tags via XML parse).

Manual equivalent:
```python
import cairosvg
cairosvg.svg2png(url="output.svg", write_to="preview.png", output_width=800)
```

Check for: text clipped/overflowing, elements misaligned vs intended
layout, colors not matching the target palette, icon illegible at small
size (render at 24px and 16px too if it's meant to be an icon).

## Dependencies

`svgwrite` `cairosvg` `Pillow` (pip). `svgwrite` is optional convenience for
programmatic generation from data — hand-written/templated XML strings work
fine without it for most FRIDAY use cases.

## Scripts in this skill

- `scripts/check_env.py` — verifies cairosvg/Pillow availability
- `scripts/verify_svg.py` — parses the SVG for structural issues (missing
  viewBox, malformed XML), renders to PNG at multiple sizes for visual
  review, especially useful for icon legibility-at-small-size checks
