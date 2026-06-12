"""
Self-verification and reflection system for FRIDAY — inspired by Fable 5's
ability to validate its own work before returning results.  Provides code
syntax checking, artifact validation, HTML/CSS linting, tool-output review,
image verification, and structured reflection analysis.
"""
from __future__ import annotations

import ast
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from friday.logging_utils import configure_logging
from friday._paths import FRIDAY_MEMORY

logger = configure_logging("verification_tools")

ARTIFACT_DIR = os.path.join(FRIDAY_MEMORY, "artifacts")
PRESENTATION_DIR = os.path.join(FRIDAY_MEMORY, "presentations")

_HAS_PIL = False
try:
    from PIL import Image as PILImage
    _HAS_PIL = True
except ImportError:
    pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_get_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 1. verify_code ───────────────────────────────────────────────────────────

def verify_code(code: str, language: str = "python") -> dict[str, Any]:
    """Verify syntax and basic correctness of code in the given language.

    Supported languages: ``python``, ``javascript``, ``html``, ``css``.

    Returns ``{success, is_valid, errors: [{line, message}], warnings,
    valid_until}``.
    """
    lang = language.strip().lower()
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []

    if lang == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append({
                "line": e.lineno or 0,
                "message": e.msg,
            })
        except Exception as e:
            errors.append({"line": 0, "message": str(e)})
        else:
            # Heuristic: warn if an exec/eval call is found
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if func in ("exec", "eval", "compile"):
                        warnings.append(
                            f"Line {node.lineno}: use of {func}() — possible security risk"
                        )

    elif lang == "javascript":
        try:
            proc = subprocess.run(
                ["node", "--check", "--"],
                input=code,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.returncode != 0:
                stderr = proc.stderr.strip()
                for line in stderr.split("\n"):
                    match = re.search(r"(\S+):(\d+):?\s*(.*)", line)
                    if match:
                        errors.append({
                            "line": int(match.group(2)),
                            "message": match.group(3).strip(),
                        })
                    else:
                        errors.append({"line": 0, "message": line.strip()})
        except FileNotFoundError:
            errors.append({"line": 0, "message": "Node.js is not installed; cannot validate JavaScript"})
        except subprocess.TimeoutExpired:
            errors.append({"line": 0, "message": "Syntax check timed out"})
        except Exception as e:
            errors.append({"line": 0, "message": str(e)})

    elif lang == "html":
        return verify_html(code)

    elif lang == "css":
        # Simple CSS property/value regex check
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
                continue
            # Skip selectors and braces
            if stripped.endswith("{") or stripped.endswith("}") or "{" not in stripped:
                continue
            if ":" not in stripped and "@" not in stripped:
                warnings.append(f"Line {i}: possible missing colon in property declaration")
    else:
        errors.append({"line": 0, "message": f"Unsupported language: {language}"})

    is_valid = len(errors) == 0
    return {
        "success": True,
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "valid_until": _now_iso(),
    }


# ── 2. verify_artifact ───────────────────────────────────────────────────────

def verify_artifact(artifact_id: str) -> dict[str, Any]:
    """Verify a stored artifact by its ID.

    Opens the artifact file from ``FRIDAY_MEMORY/artifacts/<slug>-<id>/``,
    validates its content, and returns suggestions.

    Returns ``{success, artifact_id, is_valid, errors, warnings,
    suggestions}``.
    """
    if not os.path.isdir(ARTIFACT_DIR):
        return {
            "success": False,
            "artifact_id": artifact_id,
            "is_valid": False,
            "errors": ["Artifact directory does not exist"],
            "warnings": [],
            "suggestions": [],
        }

    target_dir: str | None = None
    for name in os.listdir(ARTIFACT_DIR):
        if name.endswith(f"-{artifact_id}") or name.startswith(artifact_id):
            candidate = os.path.join(ARTIFACT_DIR, name)
            if os.path.isdir(candidate):
                target_dir = candidate
                break

    if not target_dir:
        return {
            "success": False,
            "artifact_id": artifact_id,
            "is_valid": False,
            "errors": [f"Artifact '{artifact_id}' not found"],
            "warnings": [],
            "suggestions": [],
        }

    index_path = os.path.join(target_dir, "index.html")
    if not os.path.isfile(index_path):
        return {
            "success": False,
            "artifact_id": artifact_id,
            "is_valid": False,
            "errors": ["No index.html found in artifact folder"],
            "warnings": [],
            "suggestions": ["The artifact folder exists but is missing index.html"],
        }

    content = ""
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {
            "success": False,
            "artifact_id": artifact_id,
            "is_valid": False,
            "errors": [f"Cannot read artifact file: {e}"],
            "warnings": [],
            "suggestions": [],
        }

    html_result = verify_html(content)
    suggestions: list[str] = []
    errors = list(html_result.get("errors", []))
    warnings = list(html_result.get("warnings", []))

    if errors:
        suggestions.append("Fix the HTML syntax errors identified above")
    if len(content) < 50:
        warnings.append("Artifact content is very short")
        suggestions.append("Add meaningful HTML content to the artifact")
    if "<script>" in content and "</script>" in content:
        # Extract inline JS and try a light check
        js_blocks = re.findall(r"<script[^>]*>(.*?)</script>", content, re.DOTALL | re.IGNORECASE)
        for block in js_blocks:
            stripped = block.strip()
            if stripped:
                js_result = verify_code(stripped, language="javascript")
                if not js_result.get("is_valid"):
                    warnings.append(f"Inline JS has syntax issues: {js_result.get('errors', [{}])[0].get('message', 'unknown')}")
                    suggestions.append("Fix inline JavaScript syntax errors")
                    break

    return {
        "success": True,
        "artifact_id": artifact_id,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
    }


# ── 3. verify_html ───────────────────────────────────────────────────────────

_HTML_VOID_ELEMENTS: set[str] = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

_HTML_DANGEROUS_ATTRS: set[str] = {
    "onload", "onerror", "onclick", "onmouseover", "onfocus",
    "onchange", "onsubmit", "onkeydown", "onkeyup", "oninput",
    "onpointerdown", "onpointermove",
}

_HTML_DANGEROUS_PROTOCOLS: list[str] = [
    "javascript:", "data:", "vbscript:",
]


def verify_html(html_content: str) -> dict[str, Any]:
    """Validate HTML structure via regex/string heuristics.

    Checks for: doctype, matching tags, valid attributes, and
    common XSS vectors.

    Returns ``{success, is_valid, errors, warnings}``.
    """
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []
    lines = html_content.split("\n")

    # 1. Doctype
    has_doctype = bool(re.search(r"<!DOCTYPE\s+html", html_content, re.IGNORECASE))
    if not has_doctype:
        warnings.append("Missing <!DOCTYPE html> declaration")

    # 2. Tag matching
    tag_stack: list[tuple[str, int]] = []
    tag_pattern = re.compile(r"</?(\w+)[^>]*>", re.IGNORECASE)
    for lineno, line in enumerate(lines, 1):
        for match in tag_pattern.finditer(line):
            tag_name = match.group(1).lower()
            full_tag = match.group(0)

            if full_tag.startswith("</"):
                # Closing tag
                if tag_stack and tag_stack[-1][0] == tag_name:
                    tag_stack.pop()
                else:
                    if tag_name not in _HTML_VOID_ELEMENTS:
                        expected = tag_stack[-1][0] if tag_stack else "none"
                        errors.append({
                            "line": lineno,
                            "message": f"Unexpected closing tag </{tag_name}> (expected </{expected}>)",
                        })
            elif not full_tag.endswith("/>"):
                if tag_name not in _HTML_VOID_ELEMENTS:
                    tag_stack.append((tag_name, lineno))

    if tag_stack:
        for name, ln in tag_stack:
            errors.append({
                "line": ln,
                "message": f"Unclosed tag <{name}>",
            })

    # 3. Dangerous attribute patterns (XSS)
    attr_pattern = re.compile(r"\b(on\w+)\s*=", re.IGNORECASE)
    for lineno, line in enumerate(lines, 1):
        for match in attr_pattern.finditer(line):
            attr = match.group(1).lower()
            if attr in _HTML_DANGEROUS_ATTRS:
                errors.append({
                    "line": lineno,
                    "message": f"Potentially unsafe event handler attribute: {attr}",
                })

    # 4. Dangerous protocol in href/src
    for lineno, line in enumerate(lines, 1):
        for proto in _HTML_DANGEROUS_PROTOCOLS:
            if proto in line.lower():
                errors.append({
                    "line": lineno,
                    "message": f"Potentially unsafe protocol in attribute: {proto}",
                })

    # 5. Unescaped angle brackets inside <script> or <style> may indicate issues
    inside_script_style = False
    for lineno, line in enumerate(lines, 1):
        if re.search(r"<(script|style)\b", line, re.IGNORECASE):
            inside_script_style = True
        if re.search(r"</(script|style)>", line, re.IGNORECASE):
            inside_script_style = False
        if not inside_script_style:
            # These are usually fine if they are inside content, flag them as warnings
            pass

    return {
        "success": True,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ── 4. verify_presentation ───────────────────────────────────────────────────

def verify_presentation(presentation_id: str) -> dict[str, Any]:
    """Verify that a presentation file exists and has valid content.

    For HTML slide decks, each slide section is validated.  For PPTX
    files only existence and size are checked (no deep binary parsing).

    Returns ``{success, presentation_id, is_valid, errors}``.
    """
    errors: list[str] = []
    fpath = os.path.join(PRESENTATION_DIR, os.path.basename(presentation_id))

    if not os.path.isfile(fpath):
        return {
            "success": False,
            "presentation_id": presentation_id,
            "is_valid": False,
            "errors": [f"Presentation file not found: {fpath}"],
        }

    file_size = _safe_get_size(fpath)
    if file_size == 0:
        return {
            "success": True,
            "presentation_id": presentation_id,
            "is_valid": False,
            "errors": ["Presentation file is empty"],
        }

    ext = os.path.splitext(fpath)[1].lower()

    if ext in (".html", ".htm"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {
                "success": False,
                "presentation_id": presentation_id,
                "is_valid": False,
                "errors": [f"Cannot read presentation: {e}"],
            }

        # Validate overall HTML
        html_result = verify_html(content)
        errors.extend(
            f"HTML error at line {e.get('line', '?'):s}: {e['message']}"
            if isinstance(e.get("line"), int)
            else e["message"]
            for e in html_result.get("errors", [])
        )

        # Check for slide sections
        slide_sections = re.findall(r'<div class="slide[^"]*"', content)
        if not slide_sections:
            errors.append("No slide sections found in HTML presentation")

    elif ext == ".pptx":
        # Basic check: PPTX is a ZIP archive, look for magic bytes
        try:
            with open(fpath, "rb") as f:
                header = f.read(4)
            if header != b"PK\x03\x04":
                errors.append("File does not appear to be a valid PPTX (ZIP archive)")
        except Exception:
            errors.append("Failed to read PPTX header")

    return {
        "success": True,
        "presentation_id": presentation_id,
        "is_valid": len(errors) == 0,
        "errors": errors,
    }


# ── 5. reflection_analyze ────────────────────────────────────────────────────

def reflection_analyze(task_description: str, tool_results: str) -> dict[str, Any]:
    """Analyze a tool execution result and produce a structured reflection.

    This is the core F5-style reflection loop: given what was attempted and
    what came back, determine whether the goal was achieved, what went wrong,
    and what to try next.

    Returns ``{success, goal_achieved, issues_found, recommended_fix,
    confidence_score}``.
    """
    issues_found: list[str] = []
    recommended_fix: str | None = None
    confidence_score: float = 1.0

    results_lower = tool_results.lower()

    # Detect common failure signals
    failure_signals = [
        ("error", "error"),
        ("exception", "exception"),
        ("traceback", "exception"),
        ("failed", "failure"),
        ("timeout", "timeout"),
        ("not found", "missing resource"),
        ("permission denied", "permission error"),
        ("syntaxerror", "syntax error"),
        ("importerror", "missing import"),
        ("modulenotfounderror", "missing module"),
        ("connection refused", "connection refused"),
        ("connection reset", "connection reset"),
        ("does not exist", "missing resource"),
        ("no such file", "missing file"),
        ("access denied", "permission error"),
        ("unexpected token", "syntax error"),
        ("invalid syntax", "syntax error"),
        ("cannot find module", "missing module"),
    ]

    for phrase, category in failure_signals:
        if phrase in results_lower:
            issues_found.append(category)

    is_empty = not tool_results.strip() or tool_results.strip() in ("{}", "[]", "None")
    if is_empty:
        issues_found.append("empty result")

    goal_achieved = len(issues_found) == 0 and not is_empty

    # Build recommended fix
    unique_issues = list(dict.fromkeys(issues_found))
    if unique_issues:
        if "syntax error" in unique_issues:
            recommended_fix = "Review and fix syntax errors in the generated code before retrying"
        elif "missing module" in unique_issues:
            recommended_fix = "Install the required Python package with pip"
        elif "missing import" in unique_issues:
            recommended_fix = "Add the missing import statement at the top of the file"
        elif "permission error" in unique_issues:
            recommended_fix = "Retry with elevated permissions or choose a different location"
        elif "timeout" in unique_issues:
            recommended_fix = "Increase the timeout limit or simplify the operation"
        elif "missing resource" in unique_issues or "missing file" in unique_issues:
            recommended_fix = "Ensure the required resource/file exists before proceeding"
        elif "connection refused" in unique_issues or "connection reset" in unique_issues:
            recommended_fix = "Check network connectivity and verify the service is running"
        elif "empty result" in unique_issues:
            recommended_fix = "Verify input parameters and ensure the data source contains results"
        elif "error" in unique_issues or "exception" in unique_issues:
            recommended_fix = "Examine the error details, fix the root cause, and retry"
        elif "failure" in unique_issues:
            recommended_fix = "Review the tool's requirements and adjust parameters"
        else:
            recommended_fix = f"Address the following issues: {', '.join(unique_issues)}"

    # Adjust confidence
    if not goal_achieved:
        confidence_score = max(0.1, 1.0 - len(unique_issues) * 0.2)

    return {
        "success": True,
        "goal_achieved": goal_achieved,
        "issues_found": unique_issues,
        "recommended_fix": recommended_fix,
        "confidence_score": round(confidence_score, 2),
    }


# ── 6. verify_image ──────────────────────────────────────────────────────────

def verify_image(image_path: str) -> dict[str, Any]:
    """Verify a local image file exists, has valid format, and has content.

    Uses PIL/Pillow when available for deeper inspection; otherwise
    falls back to extension-based checks.

    Returns ``{success, is_valid, format, dimensions, file_size}``.
    """
    result: dict[str, Any] = {
        "success": True,
        "is_valid": False,
        "format": None,
        "dimensions": None,
        "file_size": 0,
    }

    if not os.path.isfile(image_path):
        result["success"] = False
        result["is_valid"] = False
        result["error"] = f"File not found: {image_path}"
        return result

    result["file_size"] = _safe_get_size(image_path)
    if result["file_size"] == 0:
        result["error"] = "File is empty"
        return result

    if _HAS_PIL:
        try:
            with PILImage.open(image_path) as img:
                result["format"] = img.format.lower() if img.format else None
                result["dimensions"] = {"width": img.width, "height": img.height}
                result["is_valid"] = True
                img.verify()
        except Exception as e:
            result["error"] = f"Invalid or corrupted image: {e}"
    else:
        # Fallback: check extension
        valid_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".tif"}
        ext = os.path.splitext(image_path)[1].lower()
        if ext in valid_exts:
            result["is_valid"] = True
            result["format"] = ext.lstrip(".")
            result["warning"] = "PIL/Pillow not available; format validated by extension only"
        else:
            result["error"] = f"Unrecognized image extension: {ext}"

    return result


# ── 7. self_review_tool_output ───────────────────────────────────────────────

def self_review_tool_output(tool_name: str, input_params: dict[str, Any],
                            output: Any) -> dict[str, Any]:
    """Review a tool's output for correctness and well-formedness.

    Checks performed:
      - Did the tool return an error?
      - Is the output a dict with expected keys?
      - Does the output contain useful, non-empty content?
      - Heuristic confidence estimate.

    Returns ``{success, passed, issues, confidence}``.
    """
    issues: list[str] = []
    review: dict[str, Any] = {
        "success": True,
        "passed": True,
        "issues": issues,
        "confidence": 1.0,
    }

    # 1. Error check
    if output is None:
        issues.append("Output is None")
        review["passed"] = False
        review["confidence"] = 0.0
        review["success"] = False
        return review

    if isinstance(output, dict):
        success_val = output.get("success")
        if success_val is False:
            issues.append("Tool returned success=False")
            review["passed"] = False
        elif success_val is None:
            issues.append("Output dict missing 'success' key")

        error_val = output.get("error")
        if error_val:
            issues.append(f"Tool returned error: {error_val}")
            review["passed"] = False

        # Check for expected keys (basic pattern)
        if len(output) == 0:
            issues.append("Output dict is empty")
            review["passed"] = False
        elif len(output) <= 2 and success_val is True:
            issues.append("Output has very few fields — may lack useful information")

        # Inspect string values for emptiness
        empty_string_values = 0
        for key, val in output.items():
            if isinstance(val, str) and not val.strip() and key not in ("warning",):
                empty_string_values += 1
        if empty_string_values > len(output) // 2:
            issues.append("Most string values in output are empty")
            review["passed"] = False

    elif isinstance(output, str):
        if not output.strip():
            issues.append("Output is an empty string")
            review["passed"] = False
        elif output.strip().startswith("Error"):
            issues.append(f"Output starts with 'Error': {output[:100]}")
            review["passed"] = False

    elif isinstance(output, (list, tuple)):
        if len(output) == 0:
            issues.append("Output is an empty list/tuple")
            review["passed"] = False

    else:
        issues.append(f"Unexpected output type: {type(output).__name__}")

    # Compute confidence
    if not review["passed"]:
        review["confidence"] = max(0.1, 1.0 - len(issues) * 0.25)
    else:
        review["confidence"] = 1.0

    review["confidence"] = round(review["confidence"], 2)
    return review
