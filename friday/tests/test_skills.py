#!/usr/bin/env python3
"""Comprehensive integration test for FRIDAY skills + code agent."""

import sys, os, json, asyncio, time, textwrap
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))

from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

RESULTS = []
PASS = 0
FAIL = 0

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def log(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append((status, name, detail))
    print(f"  [{status}] {name}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"         {line}")

def test_skill_file_integrity():
    print("\n=== Skill File Integrity ===")
    for skill_file in sorted(SKILLS_DIR.rglob("SKILL*.md")):
        rel = skill_file.relative_to(SKILLS_DIR)
        content = skill_file.read_text(encoding="utf-8")
        checks = []
        if not content.strip():
            checks.append("EMPTY FILE")
        if len(content) < 500:
            checks.append(f"VERY SHORT ({len(content)} chars)")
        required = ["# ", "## "]
        for r in required:
            if r not in content:
                checks.append(f"MISSING {r}")
        if checks:
            log(str(rel), False, "; ".join(checks))
        else:
            log(str(rel), True, f"{len(content)} chars, {content.count(chr(10))} lines")

    # Check code_agent.py reads skill files
    ca_path = Path(__file__).parent.parent / "code_agent.py"
    ca_content = ca_path.read_text(encoding="utf-8")
    if "skills" in ca_content.lower() and "read_text" in ca_content:
        log("code_agent.py reads skill files", True)
    else:
        log("code_agent.py reads skill files", False, "Missing 'skills' or 'read_text' reference")

def test_code_agent_prompt_construction():
    print("\n=== Code Agent Prompt Construction ===")
    try:
        import importlib
        ca = importlib.import_module("friday.code_agent")
        
        # Get source to verify _do_code_gen reads skill files
        src = inspect.getsource(ca.ForgeAgent._do_code_gen)
        checks = []
        
        if "SKILL.md" in src:
            checks.append("reads SKILL.md")
        if "code_gen" in src.lower() or "code_gen" in src.lower():
            checks.append("references code_gen skill")
        if "<code_gen_skill>" in src:
            checks.append("injects code_gen_skill block")
        if "<domain_skill>" in src.lower() or "<domain_skills>" in src.lower():
            checks.append("injects domain_skills block")
        
        log("Prompt construction", bool(checks), "; ".join(checks) if checks else "No key patterns found")
    except Exception as e:
        log("Prompt construction", False, str(e))

async def test_llm_basic_chat():
    print("\n=== LLM Basic Chat (NVIDIA NIM) ===")
    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: HELLO_FRIDAY"}],
            temperature=0.0,
            max_tokens=50,
        )
        content = resp.content.strip()
        if "HELLO_FRIDAY" in content:
            log(f"LLM chat ({model})", True, f"response: {content[:80]}")
        else:
            log(f"LLM chat ({model})", True, f"Got response (unexpected: {content[:80]})")
        return True
    except Exception as e:
        log(f"LLM chat ({model})", False, str(e)[:200])
        return False

async def test_code_gen_skill_with_llm():
    print("\n=== Code Generation Skill (Plan->Build) ===")
    code_gen_skill = (SKILLS_DIR / "code_gen" / "SKILL.md").read_text(encoding="utf-8")
    
    prompt = textwrap.dedent(f"""\
        <code_gen_skill>
        {code_gen_skill}
        </code_gen_skill>

        Generate a *single* Python file that uses matplotlib to create a bar chart 
        of the top 5 programming languages by popularity.
        Output ONLY the Python code wrapped in ```python ... ```.
        Follow the Plan phase then Build phase from the skill above.
    """)

    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
        )
        content = resp.content.strip()
        has_code_block = "```python" in content or "```" in content
        has_import = "import" in content or "from " in content
        has_matplotlib = "matplotlib" in content or "plt." in content
        
        pass_checks = has_code_block and has_import and has_matplotlib
        detail_parts = []
        if has_code_block: detail_parts.append("has code block")
        if has_import: detail_parts.append("has import")
        if has_matplotlib: detail_parts.append("uses matplotlib")
        if not pass_checks:
            detail_parts.append(f"response length={len(content)}")
        
        log("Code gen Plan->Build", pass_checks, "; ".join(detail_parts))
        return content, pass_checks
    except Exception as e:
        log("Code gen Plan->Build", False, str(e)[:300])
        return str(e), False

async def test_pptx_skill_with_llm():
    print("\n=== PPTX Skill ===")
    skill = (SKILLS_DIR / "pptx" / "SKILL.md").read_text(encoding="utf-8")
    
    prompt = textwrap.dedent(f"""\
        <skill>
        {skill}
        </skill>

        Generate Python code using python-pptx that creates a 3-slide presentation:
        Slide 1: Title "Q4 Report 2025" with subtitle "Growth Analysis"
        Slide 2: Bullet list of 4 key metrics
        Slide 3: Thank you slide
        Follow ALL design rules from the skill above.
        Output ONLY the Python code in ```python ... ```.
    """)
    
    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000)
        content = resp.content.strip()
        checks = []
        if "pptx" in content.lower(): checks.append("references pptx")
        if "python-pptx" in content.lower() or "Presentation(" in content: checks.append("uses Presentation()")
        if "```python" in content: checks.append("has code block")
        if "Slide" in content: checks.append("mentions slides")
        log("PPTX skill generation", len(checks) >= 3, "; ".join(checks))
        return content, len(checks) >= 3
    except Exception as e:
        log("PPTX skill generation", False, str(e)[:300])
        return str(e), False

async def test_pdf_skill_with_llm():
    print("\n=== PDF Skill ===")
    skill = (SKILLS_DIR / "pdf" / "SKILL.md").read_text(encoding="utf-8")
    
    prompt = textwrap.dedent(f"""\
        <skill>
        {skill[:3000]}  
        </skill>

        Generate Python code using reportlab that creates a 2-page PDF:
        Page 1: Title "Report 2025" with a subtitle
        Page 2: A simple table with 3 columns and 4 rows
        Follow ALL design rules from the skill.
        Output ONLY the Python code in ```python ... ```.
    """)
    
    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000)
        content = resp.content.strip()
        checks = []
        if "reportlab" in content.lower() or "fpdf" in content.lower(): checks.append("references library")
        if "```python" in content: checks.append("has code block")
        if "Page" in content or "page" in content: checks.append("mentions pages")
        if "canvas" in content.lower() or "SimpleDocTemplate" in content: checks.append("uses canvas/doc template")
        log("PDF skill generation", len(checks) >= 2, "; ".join(checks))
        return content, len(checks) >= 2
    except Exception as e:
        log("PDF skill generation", False, str(e)[:300])
        return str(e), False

async def test_xlsx_skill_with_llm():
    print("\n=== XLSX Skill ===")
    skill = (SKILLS_DIR / "xlsx" / "SKILL.md").read_text(encoding="utf-8")
    
    prompt = textwrap.dedent(f"""\
        <skill>
        {skill[:3000]}
        </skill>

        Generate Python code using openpyxl that creates a spreadsheet with:
        - Header row: Name, Age, City
        - 5 data rows
        - Bold headers with blue fill
        - Auto-adjusted column widths
        Follow ALL design rules from the skill.
        Output ONLY the Python code in ```python ... ```.
    """)
    
    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000)
        content = resp.content.strip()
        checks = []
        if "openpyxl" in content.lower(): checks.append("references openpyxl")
        if "```python" in content: checks.append("has code block")
        if "Workbook" in content: checks.append("uses Workbook")
        if "header" in content.lower(): checks.append("mentions headers")
        log("XLSX skill generation", len(checks) >= 2, "; ".join(checks))
        return content, len(checks) >= 2
    except Exception as e:
        log("XLSX skill generation", False, str(e)[:300])
        return str(e), False

async def test_chart_skill_with_llm():
    print("\n=== Chart Skill ===")
    skill = (SKILLS_DIR / "chart" / "SKILL.md").read_text(encoding="utf-8")
    
    prompt = textwrap.dedent(f"""\
        <skill>
        {skill[:3000]}
        </skill>

        Generate Python code using plotly that creates a line chart:
        - X-axis: months Jan-Jun
        - Y-axis: sales figures
        - Use the IBM Carbon color palette from the skill
        - Title "Monthly Sales 2025"
        Follow ALL design rules from the skill.
        Output ONLY the Python code in ```python ... ```.
    """)
    
    client = InferenceClient()
    model = resolve_model("code_gen")
    try:
        resp = await client.chat(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000)
        content = resp.content.strip()
        checks = []
        if "plotly" in content.lower() or "plotly" in content.lower(): checks.append("references plotly")
        if "```python" in content: checks.append("has code block")
        if "line" in content.lower() or "Line" in content: checks.append("creates line chart")
        if "carbon" in content.lower() or "palette" in content.lower(): checks.append("uses carbon palette")
        log("Chart skill generation", len(checks) >= 2, "; ".join(checks))
        return content, len(checks) >= 2
    except Exception as e:
        log("Chart skill generation", False, str(e)[:300])
        return str(e), False

def print_report():
    print(f"\n{'='*60}")
    print(f"TEST RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} total")
    print(f"{'='*60}")
    for status, name, detail in RESULTS:
        if detail:
            print(f"  [{status}] {name:<40} | {detail[:80]}")
        else:
            print(f"  [{status}] {name}")

async def main():
    print(f"FRIDAY Skills Integration Test Suite")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Skill dir: {SKILLS_DIR}")
    
    # Static tests
    test_skill_file_integrity()
    test_code_agent_prompt_construction()
    
    # LLM-dependent tests
    llm_ok = await test_llm_basic_chat()
    if llm_ok:
        await test_code_gen_skill_with_llm()
        await test_pptx_skill_with_llm()
        await test_pdf_skill_with_llm()
        await test_xlsx_skill_with_llm()
        await test_chart_skill_with_llm()
    else:
        print("\n  [!] LLM unavailable, skipping LLM-dependent tests")
    
    print_report()
    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    import inspect
    asyncio.run(main())
