---
name: html-web
location: friday/skills/html-web/SKILL.md
trigger: website, landing page, dashboard, webapp, html/css page, single-page tool, calculator
platform: Windows (FRIDAY host machine)
---

# HTML/CSS/JS — FRIDAY Playbook (Full)

Covers standalone deliverables — landing pages, dashboards, single-file
tools, small interactive widgets. Not a framework/build-pipeline guide;
default to single-file unless the user needs a real multi-file project.

## 0. Environment setup

```powershell
pip install playwright
python -m playwright install chromium
```

`playwright` gives FRIDAY headless screenshot capability for the verify
step — mandatory for anything visual, not optional.

```bash
python friday/skills/html-web/scripts/check_env.py
```

## 1. Single-file convention

Keep CSS and JS inline in one `.html` file unless the user needs a real
multi-file project structure. Simpler to hand off, nothing can go missing
between files, works the instant it's opened.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>...</title>
  <style>/* all CSS here */</style>
</head>
<body>
  ...
  <script>/* all JS here */</script>
</body>
</html>
```

## 2. Design quality — the failure mode to avoid

Technically-correct HTML that still looks like an unstyled decade-old
Bootstrap template. Concrete levers that actually change this:

- **Real spacing scale**: pick a base unit (4px or 8px) and use multiples of
  it consistently. Random one-off values (`padding: 13px 7px`) is what
  makes a layout feel accidental rather than designed.
- **Type scale, not one font-size everywhere**: establish a small ramp
  (e.g. 14/16/20/28/40px) and stick to it across the whole page.
- **Intentional color, not framework defaults**: don't ship unmodified
  Bootstrap blue (`#007bff`) or default Tailwind palette as if it were a
  deliberate choice — pick colors that fit the actual content/brand. For
  FRIDAY's dark-neon direction specifically (only when the request implies
  it): near-black backgrounds (`#0A0A0F`–`#111318`), electric accent colors
  (`#00D4FF`, `#FF2E9A`, `#39FF88`), high-contrast white/near-white text.
- **Contrast and hierarchy**: one element should clearly be the visual
  anchor per section — a stat, a headline, a CTA — not everything competing
  at equal visual weight.

Consult `frontend-design`-equivalent design notes before shipping anything
user-facing, if FRIDAY has (or builds) its own such doc.

## 3. CSS architecture for a single-file deliverable

Use CSS custom properties for the palette/spacing scale so the whole page
stays consistent and easy to retheme:

```css
:root {
  --bg: #0A0A0F;
  --surface: #16181D;
  --text: #F2F2F2;
  --text-muted: #9A9CA3;
  --accent: #00D4FF;
  --accent-2: #FF2E9A;
  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --space-4: 40px;
  --radius: 12px;
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: Arial, sans-serif; }
```

## 4. Responsiveness

At minimum, no horizontal scroll on mobile widths:

```css
img, video { max-width: 100%; height: auto; }

@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
  h1 { font-size: 28px; }
}
```

Test at three widths minimum during verify: 375px (mobile), 768px (tablet),
1280px (desktop) — see §8.

## 5. JS — vanilla by default

For a single-file deliverable, vanilla JS is almost always right — no build
step, works instantly. Reach for a framework only when the user explicitly
wants React/Vue or the interactivity genuinely needs component state
management beyond what plain DOM manipulation handles cleanly.

```javascript
document.querySelectorAll("[data-tab]").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-panel").forEach(p => p.hidden = true);
    document.getElementById(btn.dataset.tab).hidden = false;
  });
});
```

## 6. Forms and validation

Client-side validation with clear inline error states, not silent failure
or a generic browser tooltip only:

```html
<form id="signupForm" novalidate>
  <label for="email">Email</label>
  <input type="email" id="email" required>
  <span class="error-msg" id="emailError" hidden>Enter a valid email address.</span>
  <button type="submit">Sign up</button>
</form>

<script>
document.getElementById("signupForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const email = document.getElementById("email");
  const err = document.getElementById("emailError");
  const valid = email.checkValidity();
  err.hidden = valid;
  email.setAttribute("aria-invalid", String(!valid));
  if (valid) {
    // proceed
  }
});
</script>
```

## 7. State persistence — critical restriction

**Never use `localStorage`/`sessionStorage`** if there's any chance this
runs inside a sandboxed preview (Claude artifacts, some embedded browser
contexts) — these fail silently there. For FRIDAY's own delivered files
opened directly in a real browser, localStorage IS fine and appropriate —
this restriction is specifically about sandboxed preview environments, not
a blanket rule. Use judgment based on where the file will actually run; if
unsure, default to in-memory JS state (variables/objects) for maximum
compatibility, and note to the user that persistence isn't wired if that
matters for their use case.

## 8. Interactive widgets / calculators — worked example

```html
<div class="calculator">
  <label>Loan amount <input type="number" id="principal" value="10000"></label>
  <label>Interest rate (%) <input type="number" id="rate" value="5" step="0.1"></label>
  <label>Years <input type="number" id="years" value="10"></label>
  <div class="result" id="result">Monthly payment: —</div>
</div>

<script>
function calculate() {
  const p = parseFloat(document.getElementById("principal").value);
  const r = parseFloat(document.getElementById("rate").value) / 100 / 12;
  const n = parseFloat(document.getElementById("years").value) * 12;
  if (!p || !r || !n) return;
  const payment = (p * r) / (1 - Math.pow(1 + r, -n));
  document.getElementById("result").textContent =
    `Monthly payment: $${payment.toFixed(2)}`;
}
document.querySelectorAll(".calculator input").forEach(inp =>
  inp.addEventListener("input", calculate)
);
calculate();
</script>
```

## 9. Charts/data viz in HTML

For anything beyond trivial, use Chart.js (CDN, no build step) rather than
hand-rolling SVG/canvas chart code:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<canvas id="myChart"></canvas>
<script>
new Chart(document.getElementById("myChart"), {
  type: "bar",
  data: {
    labels: ["Q1", "Q2", "Q3", "Q4"],
    datasets: [{ label: "Revenue", data: [19.2, 21.4, 25.1, 27.8], backgroundColor: "#00D4FF" }],
  },
  options: { responsive: true, plugins: { legend: { labels: { color: "#F2F2F2" } } } },
});
</script>
```

Note: CDN dependency means this needs an internet connection to render —
flag this if the deliverable needs to work fully offline, in which case
download Chart.js and inline it or reference a local copy instead.

## 10. Accessibility basics — don't skip these, they're cheap

```html
<img src="logo.png" alt="Company logo">
<button aria-label="Close dialog">×</button>
<input type="email" id="email" aria-describedby="emailHelp">
<nav aria-label="Main navigation">...</nav>
```

- Every interactive element must be reachable by keyboard (native `<button>`
  and `<a>` are keyboard-accessible by default — a `<div onclick>` is not,
  avoid that pattern).
- Color contrast: body text against background should meet roughly 4.5:1
  contrast ratio — don't ship light-gray-on-white or similarly low-contrast
  combinations for anything meant to be read, not just glanced at.

## 11. Verify before delivering (mandatory)

```bash
python friday/skills/html-web/scripts/verify_html.py output.html
```

This screenshots the page at desktop (1280px), tablet (768px), and mobile
(375px) widths, and checks for console errors during page load.

Manual equivalent:
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, name in [(1280, "desktop"), (768, "tablet"), (375, "mobile")]:
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(f"file:///{Path('output.html').resolve()}")
        page.screenshot(path=f"preview_{name}.png", full_page=True)
        page.close()
    browser.close()
```

Check for: overlapping elements, text overflow, broken layout at narrow
widths, unstyled default-looking form elements, low contrast text, JS
console errors (playwright can capture these via `page.on("console", ...)`).

## 12. Windows-specific gotchas

- `file:///` URLs on Windows need the drive letter and correct slash
  handling — `Path.resolve().as_uri()` in Python handles this correctly,
  don't hand-construct the URI string.
- Playwright's first run needs `playwright install chromium` — this
  downloads a browser binary (~150MB) and will fail silently if skipped;
  `check_env.py` verifies this.

## Dependencies

`playwright` (pip, plus `playwright install chromium`) for verification.
No dependencies for the HTML/CSS/JS output itself beyond whatever CDN
libraries (Chart.js etc.) are explicitly included.

## Scripts in this skill

- `scripts/check_env.py` — verifies playwright + chromium browser install
- `scripts/verify_html.py` — screenshots at 3 breakpoints, captures console
  errors during load, reports all findings
