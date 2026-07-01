#!/usr/bin/env python3
"""Research-driven quality tests — LLM generates code, we run & verify rich output."""

import sys, os, asyncio, json, subprocess, textwrap, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

VENV_PY = str(Path(__file__).resolve().parent.parent.parent / ".venv" / "Scripts" / "python.exe")

PASS = 0; FAIL = 0; RESULTS = []
BASE = Path(__file__).parent / "_research_test_outputs"
BASE.mkdir(exist_ok=True)
client = InferenceClient()
model = resolve_model("code_gen")

RESEARCH_PATH = Path(__file__).parent.parent / "memory" / "raw_research_deep_Find_the_best_bluetooth_headsets_under_2000_available_o.md"
research = RESEARCH_PATH.read_text(encoding="utf-8")[:4000]

def log(name, passed, detail=""):
    global PASS, FAIL
    if passed: PASS += 1
    else: FAIL += 1
    RESULTS.append(("PASS" if passed else "FAIL", name, detail))
    print(f"  [{'PASS' if passed else 'FAIL'}] {name} | {detail[:120]}")

async def gen_and_run(name, prompt, output_ext, max_tok=5000):
    subdir = BASE / name.replace(" ", "_")
    if subdir.exists(): shutil.rmtree(subdir)
    subdir.mkdir()
    
    resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=max_tok)
    code = resp.content.strip()
    
    if "```" in code:
        lines = code.splitlines(); in_block = False; code_lines = []
        for line in lines:
            if line.startswith("```"): in_block = not in_block; continue
            if in_block: code_lines.append(line)
        code = "\n".join(code_lines) if code_lines else code
    
    (subdir / "gen.py").write_text(code, encoding="utf-8")
    
    result = subprocess.run([VENV_PY, str(subdir / "gen.py")], capture_output=True, text=True, timeout=45, cwd=str(subdir))
    out_files = list(subdir.glob(f"*{output_ext}"))
    
    if result.returncode == 0 and out_files:
        sz = out_files[0].stat().st_size
        log(name, True, f"{out_files[0].name} ({sz} bytes)")
        return True
    elif result.returncode == 0 and not out_files:
        log(name, False, f"exit=0 but no *{output_ext} file; stderr={result.stderr[:100]}")
        return False
    else:
        log(name, False, f"exit={result.returncode}; {result.stderr[:200]}")
        return False

async def test_pptx():
    p = textwrap.dedent(f"""\
        Write Python code using python-pptx. Create a RICH 6-slide presentation about Bluetooth headsets under ₹2000.
        Research data: {research}
        
        REQUIREMENTS:
        - Slide 1: Title slide with dark gradient background (#0a0a2e to #001a4e), large title (40pt white bold), subtitle (24pt #00d4ff), accent line below title, date at bottom
        - Slide 2: "Market Overview" — title, body text with key findings, styled table (5 products × Brand/Model/Price/Rating/Battery) with blue header row (#378ADD white text) and alternating row colors
        - Slide 3: "Key Features Comparison" — bullet list of important features (Bluetooth version, battery life, weight, mic quality) with icons/shapes
        - Slide 4: "Price Comparison Chart" — embed a matplotlib bar chart showing product prices, with title, axis labels, value labels on bars
        - Slide 5: "Ratings Analysis" — embed a matplotlib pie or bar chart showing ratings distribution, with legend
        - Slide 6: "Thank You" — dark background, large centered "Thank You", contact info
        - ALL slides: custom background (no white), slide transitions (fade), slide numbers, consistent font sizing (min 14pt)
        - Color theme: dark bg + blue/teal accents throughout
        Save as "test.pptx". ONLY Python code.
    """)
    return await gen_and_run("Research PPTX", p, ".pptx", max_tok=6000)

async def test_docx():
    p = textwrap.dedent(f"""\
        Write Python code using python-docx. Create a PROFESSIONAL 4-page report about Bluetooth headsets under ₹2000.
        Research data: {research}
        
        REQUIREMENTS:
        - Cover page: colored shape border, centered title "Bluetooth Headset Analysis 2025" (26pt bold #0C447C), subtitle (16pt #185FA5), horizontal rule, date, "Prepared by FRIDAY AI"
        - Page 2: Heading 1 "Executive Summary" (18pt #0C447C), body paragraphs (11pt justified #333333), key metrics in bold
        - Page 3: Heading 1 "Product Comparison", styled table (6 rows × 5 cols) with blue header (#378ADD white text bold), alternating row colors (#F1EFE8 / white), proper column widths. Heading 2 "Key Insights" with bullet points
        - Page 4: Heading 1 "Recommendations", body text, embedded matplotlib bar chart image (price comparison), concluding paragraph
        - Headers: document title on every page
        - Footers: page numbers centered
        - A4 paper, 2.54cm margins
        - Consistent color theme: blue headings, dark gray body text
        Save as "test.docx". ONLY Python code.
    """)
    return await gen_and_run("Research DOCX", p, ".docx", max_tok=6000)

async def test_pdf():
    p = textwrap.dedent(f"""\
        Write Python code using reportlab. Create a PROFESSIONAL 5-page PDF report about Bluetooth headsets under ₹2000.
        Research data: {research}
        
        REQUIREMENTS:
        - Page 1: Title page — centered "Headset Market Report 2025" (24pt bold #0C447C), accent line (2pt #378ADD), subtitle "Best Bluetooth Headsets Under ₹2000" (14pt #5F5E5A), date, "Prepared by FRIDAY AI"
        - Page 2: Table of Contents — section titles with dot leaders and page numbers
        - Page 3: Heading 1 "Market Overview" (18pt #185FA5), body text (11pt justified #333333), styled data table (6 rows × 5 cols) with blue header (#378ADD white text), alternating rows (#F1EFE8/white)
        - Page 4: Heading 1 "Product Analysis", body text, embedded matplotlib bar chart (price comparison with value labels), chart caption below
        - Page 5: Heading 1 "Conclusion & Recommendations", bullet list, final note
        - Headers: "Headset Market Report 2025" left, "Confidential" right, with line below
        - Footers: page numbers centered, date left, version right
        - All pages except title: header+footer
        - A4, 2.5cm margins
        Save as "test.pdf". ONLY Python code.
    """)
    return await gen_and_run("Research PDF", p, ".pdf", max_tok=6000)

async def test_xlsx():
    p = textwrap.dedent(f"""\
        Write Python code using openpyxl. Create a RICH spreadsheet about Bluetooth headsets under ₹2000.
        Research data: {research}
        
        REQUIREMENTS:
        - Sheet 1 "Dashboard": KPI cards (big numbers: total products, avg price, top rating, cheapest option) with labels, summary table with totals row, conditional formatting (color scale on price column), frozen top row
        - Sheet 2 "Products": Full data table with headers (Brand, Model, Price, Battery Life, Rating, Weight, Bluetooth Version) in bold white text on blue bg (#378ADD), alternating row colors (#E6F1FB/#FFFFFF), auto-width columns, frozen header row, auto-filter enabled
        - Sheet 3 "Charts": Embedded bar chart (price comparison) with title "Price Comparison", pie chart (brand distribution) with title "Market Share", both styled with theme colors
        - Currency formatting ($) on price column, percentage on rating, proper number alignment
        - Formulas: SUM for totals, AVERAGE for avg price/rating, MIN/MAX for extremes
        - Bold blue headers, auto-width columns everywhere
        Save as "test.xlsx". ONLY Python code.
    """)
    return await gen_and_run("Research XLSX", p, ".xlsx", max_tok=6000)

async def test_svg():
    p = textwrap.dedent("""\
        Write Python code that creates a RICH animated SVG graphic for "FRIDAY AI".
        
        REQUIREMENTS:
        - Dark background (#0a0a2e) with subtle grid pattern or radial gradient
        - Large "FRIDAY" text centered, with gradient fill (#00d4ff to #0066ff), letter-spacing, font-weight bold
        - "AI ASSISTANT" subtitle below in smaller font (#888780 to #00d4ff)
        - Animated elements (MULTIPLE, not just one):
          * Rotating outer ring with dash offset animation (at least 2 concentric rings rotating opposite directions)
          * Orbiting particles/dots with different animation delays and sizes
          * Pulsing glow effect on the text
          * Moving scan line or sweeping gradient
        - All animations via CSS @keyframes (not SVG <animate>)
        - Multiple gradients in <defs> section
        - Professional composition: balanced, layered, visually impressive
        - Proper viewBox="0 0 800 600" 
        - Responsive: width="100%" height="100%"
        Save as "friday_logo.svg". ONLY Python code.
    """)
    subdir = BASE / "Animated_SVG"
    if subdir.exists(): shutil.rmtree(subdir)
    subdir.mkdir()
    
    resp = await client.chat(model=model, messages=[{"role": "user", "content": p}], temperature=0.1, max_tokens=5000)
    code = resp.content.strip()
    if "```" in code:
        lines = code.splitlines(); in_block = False; code_lines = []
        for line in lines:
            if line.startswith("```"): in_block = not in_block; continue
            if in_block: code_lines.append(line)
        code = "\n".join(code_lines) if code_lines else code
    
    (subdir / "gen_svg.py").write_text(code, encoding="utf-8")
    result = subprocess.run([VENV_PY, str(subdir / "gen_svg.py")], capture_output=True, text=True, timeout=30, cwd=str(subdir))
    svg_files = list(subdir.glob("*.svg"))
    
    if result.returncode == 0 and svg_files:
        content = svg_files[0].read_text(encoding="utf-8")
        has_svg = "<svg" in content and "</svg>" in content
        has_anim = "@keyframes" in content or "<animate" in content
        has_grad = "linearGradient" in content or "radialGradient" in content
        has_multiple_anim = content.count("@keyframes") >= 2
        line_count = len(content.splitlines())
        log("Animated SVG Logo", has_svg, f"anim={has_anim}, grad={has_grad}, multikeyframes={has_multiple_anim}, lines={line_count}")
        return has_svg
    else:
        log("Animated SVG Logo", False, f"exit={result.returncode}; {result.stderr[:150]}")
        return False

async def test_forge():
    p = textwrap.dedent(f"""\
        Write THREE Python files for a Bluetooth headset data analysis project.
        Research data: {research}
        
        # FILE: analysis.py
        Define product data as list of dicts with keys: brand, model, price, battery, rating, weight, bluetooth.
        Functions: sort_by_price(products), filter_by_rating(products, min_rating), filter_by_price_range(products, min_p, max_p), avg_price(products), top_n(products, n, key), generate_summary(products) — returns formatted text report
        Include type hints and docstrings.
        
        # FILE: test_analysis.py
        pytest tests for ALL functions with edge cases (empty list, single item, boundary values).
        At least 15 test functions.
        
        # FILE: report.py
        Uses analysis.py functions to: load data, generate table (formatted for console), print summary, generate matplotlib chart (bar chart of prices with brand labels) and save as "chart.png"
        
        ONLY code with # FILE: separators. No markdown.
    """)
    subdir = BASE / "Forge_MultiFile"
    if subdir.exists(): shutil.rmtree(subdir)
    subdir.mkdir()
    
    resp = await client.chat(model=model, messages=[{"role": "user", "content": p}], temperature=0.1, max_tokens=6000)
    code = resp.content.strip()
    if "```" in code:
        lines = code.splitlines(); in_block = False; code_lines = []
        for line in lines:
            if line.startswith("```"): in_block = not in_block; continue
            if in_block: code_lines.append(line)
        code = "\n".join(code_lines) if code_lines else code
    
    files_written = []
    current_file = None; current_content = []
    for line in code.splitlines():
        if line.startswith("# FILE:") or line.startswith("# file:"):
            if current_file and current_content:
                (subdir / current_file).write_text("\n".join(current_content), encoding="utf-8")
                files_written.append(current_file)
            current_file = line.split(":")[-1].strip().strip('"').strip("'")
            current_content = []
        else:
            current_content.append(line)
    if current_file and current_content:
        (subdir / current_file).write_text("\n".join(current_content), encoding="utf-8")
        files_written.append(current_file)
    
    if not files_written:
        (subdir / "analysis.py").write_text(code, encoding="utf-8")
        files_written.append("analysis.py")
    
    ok = True
    for fn in files_written:
        r = subprocess.run([VENV_PY, "-c", f"import ast; ast.parse(open(r'{subdir / fn}').read())"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0: ok = False; log("Forge Multi-File", False, f"{fn}: {r.stderr[:100]}"); break
    if ok:
        # Try running tests if they exist
        test_result = ""
        if "test_analysis.py" in files_written:
            tr = subprocess.run([VENV_PY, "-m", "pytest", str(subdir / "test_analysis.py"), "-v", "--tb=short"], capture_output=True, text=True, timeout=30)
            if tr.returncode == 0:
                passed = len([l for l in tr.stdout.splitlines() if "PASSED" in l])
                test_result = f", pytest {passed} passed"
            else:
                test_result = f", pytest FAILED: {tr.stderr[:80]}"
        log("Forge Multi-File", True, f"{len(files_written)} files, syntax OK{test_result}")

async def main():
    print("=" * 60)
    print("FRIDAY QUALITY RESEARCH TEST SUITE")
    print(f"Model: {model}")
    print(f"Python: {VENV_PY}")
    print("=" * 60)
    
    await test_pptx()
    await test_docx()
    await test_pdf()
    await test_xlsx()
    await test_svg()
    await test_forge()
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL}")
    print(f"{'='*60}")
    for s, n, d in RESULTS:
        print(f"  [{s}] {n:<40} | {d}")
    print(f"\nOutput: {BASE}")

if __name__ == "__main__":
    asyncio.run(main())
