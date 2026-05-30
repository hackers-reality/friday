"""
Document Processing tools
Libraries: python-docx, openpyxl, pandas, polars, pdfplumber, pypdf, reportlab, python-pptx
"""
import asyncio
import os
import tempfile
from typing import Any

# ── Word (python-docx) ──
HAS_DOCX = False
try:
    from docx import Document
    from docx.shared import Inches, Pt
    HAS_DOCX = True
except ImportError:
    pass


async def read_docx(path: str) -> dict[str, Any]:
    if not HAS_DOCX:
        return {"error": "python-docx not installed"}
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    try:
        doc = await asyncio.get_event_loop().run_in_executor(None, lambda: Document(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return {"path": path, "paragraphs": len(paragraphs), "text": "\n".join(paragraphs[:500]),
                "tables": len(doc.tables), "sections": len(doc.sections)}
    except Exception as e:
        return {"error": str(e)}


async def create_docx(content: str, output_path: str | None = None) -> dict[str, Any]:
    if not HAS_DOCX:
        return {"error": "python-docx not installed"}
    try:
        doc = Document()
        for line in content.split("\n"):
            doc.add_paragraph(line)
        out = output_path or os.path.join(tempfile.gettempdir(), "friday_document.docx")
        await asyncio.get_event_loop().run_in_executor(None, lambda: doc.save(out))
        return {"path": out, "characters": len(content)}
    except Exception as e:
        return {"error": str(e)}


# ── Excel (openpyxl) ──
HAS_OPENPYXL = False
try:
    from openpyxl import load_workbook, Workbook
    HAS_OPENPYXL = True
except ImportError:
    pass


async def read_excel(path: str, sheet: str | None = None) -> dict[str, Any]:
    if not HAS_OPENPYXL:
        return {"error": "openpyxl not installed"}
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    try:
        wb = await asyncio.get_event_loop().run_in_executor(None, lambda: load_workbook(path, data_only=True))
        sheets = wb.sheetnames
        target = sheet or sheets[0]
        ws = wb[target]
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append([str(c) if c is not None else "" for c in row])
        return {"path": path, "sheets": sheets, "active_sheet": target, "rows": len(rows), "columns": len(rows[0]) if rows else 0, "data": rows[:100]}
    except Exception as e:
        return {"error": str(e)}


async def create_excel(data: list[list[Any]], headers: list[str] | None = None, output_path: str | None = None) -> dict[str, Any]:
    if not HAS_OPENPYXL:
        return {"error": "openpyxl not installed"}
    try:
        wb = Workbook()
        ws = wb.active
        if headers:
            ws.append(headers)
        for row in data:
            ws.append(row)
        out = output_path or os.path.join(tempfile.gettempdir(), "friday_workbook.xlsx")
        await asyncio.get_event_loop().run_in_executor(None, lambda: wb.save(out))
        return {"path": out, "rows": len(data), "headers": headers}
    except Exception as e:
        return {"error": str(e)}


# ── Data Frames (pandas) ──
HAS_PANDAS = False
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pass


async def analyze_csv(path: str) -> dict[str, Any]:
    if not HAS_PANDAS:
        return {"error": "pandas not installed"}
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    try:
        df = await asyncio.get_event_loop().run_in_executor(None, lambda: pd.read_csv(path))
        desc = df.describe(include="all").to_dict()
        return {"path": path, "rows": len(df), "columns": len(df.columns), "col_names": list(df.columns),
                "dtypes": {c: str(df[c].dtype) for c in df.columns}, "null_counts": df.isnull().sum().to_dict(),
                "summary": {c: {k: str(v) for k, v in desc[c].items()} for c in desc}}
    except Exception as e:
        return {"error": str(e)}


async def query_csv(path: str, query: str) -> dict[str, Any]:
    if not HAS_PANDAS:
        return {"error": "pandas not installed"}
    try:
        df = await asyncio.get_event_loop().run_in_executor(None, lambda: pd.read_csv(path))
        result = await asyncio.get_event_loop().run_in_executor(None, lambda: df.query(query))
        return {"query": query, "matches": len(result), "data": result.head(100).to_dict(orient="records") if len(result) > 0 else []}
    except Exception as e:
        return {"error": str(e)}


# ── PDF (pdfplumber / pypdf) ──
HAS_PDFPLUMBER = False
HAS_PYPDF = False
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    pass
try:
    import PyPDF2
    HAS_PYPDF = True
except ImportError:
    pass


async def read_pdf(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    if HAS_PDFPLUMBER:
        try:
            text = ""
            tables = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    tables.extend(page.extract_tables() or [])
            return {"path": path, "pages": len(pdf.pages), "text": text[:50000], "tables": len(tables)}
        except Exception as e:
            return {"error": str(e)}
    if HAS_PYPDF:
        try:
            text = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return {"path": path, "pages": len(reader.pages), "text": text[:50000]}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pdfplumber or PyPDF2 not installed"}


# ── PDF Generation (reportlab) ──
HAS_REPORTLAB = False
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except ImportError:
    pass


async def create_pdf(content: str, output_path: str | None = None) -> dict[str, Any]:
    if not HAS_REPORTLAB:
        return {"error": "reportlab not installed"}
    try:
        out = output_path or os.path.join(tempfile.gettempdir(), "friday_document.pdf")
        doc = SimpleDocTemplate(out, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for line in content.split("\n"):
            if line.strip():
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 6))
        await asyncio.get_event_loop().run_in_executor(None, lambda: doc.build(story))
        return {"path": out, "characters": len(content)}
    except Exception as e:
        return {"error": str(e)}


# ── PowerPoint (python-pptx) ──
HAS_PPTX = False
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    HAS_PPTX = True
except ImportError:
    pass


async def read_pptx(path: str) -> dict[str, Any]:
    if not HAS_PPTX:
        return {"error": "python-pptx not installed"}
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    try:
        prs = await asyncio.get_event_loop().run_in_executor(None, lambda: Presentation(path))
        slides = []
        for slide in prs.slides:
            slide_text = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        slide_text.append(para.text)
            slides.append({"text": "\n".join(slide_text)[:500]})
        return {"path": path, "slides": len(slides), "slide_width": prs.slide_width, "slide_height": prs.slide_height,
                "content": slides[:50]}
    except Exception as e:
        return {"error": str(e)}


async def create_pptx(title: str, slides: list[dict[str, Any]], output_path: str | None = None) -> dict[str, Any]:
    if not HAS_PPTX:
        return {"error": "python-pptx not installed"}
    try:
        prs = Presentation()
        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = title
        for s in slides:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = s.get("title", "")
            slide.placeholders[1].text = s.get("content", "")
        out = output_path or os.path.join(tempfile.gettempdir(), "friday_presentation.pptx")
        await asyncio.get_event_loop().run_in_executor(None, lambda: prs.save(out))
        return {"path": out, "slides": len(slides) + 1}
    except Exception as e:
        return {"error": str(e)}
