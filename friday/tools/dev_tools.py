"""
Developer Tools module — Ruff, ripgrep, ast-grep, Tree-sitter, Pyright.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

# ── Lazy dependency flags ──

HAS_TREE_SITTER = False
try:
    import tree_sitter  # noqa: F401
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:
    pass

# ── Result types ──


@dataclass
class LintDiagnostic:
    line: int
    column: int
    code: str
    message: str
    severity: str  # error, warning, info


@dataclass
class LintResult:
    path: str
    diagnostics: list[LintDiagnostic] = field(default_factory=list)
    fixed: bool = False
    error: Optional[str] = None


@dataclass
class FormatResult:
    path: str
    formatted: bool = False
    files_changed: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class GrepMatch:
    file: str
    line: int
    column: int
    content: str


@dataclass
class GrepResult:
    pattern: str
    matches: list[GrepMatch] = field(default_factory=list)
    count: int = 0
    error: Optional[str] = None


@dataclass
class AstGrepMatch:
    file: str
    line: int
    column: int
    text: str


@dataclass
class AstGrepResult:
    pattern: str
    matches: list[AstGrepMatch] = field(default_factory=list)
    count: int = 0
    error: Optional[str] = None


@dataclass
class CodeFunction:
    name: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None


@dataclass
class CodeClass:
    name: str
    start_line: int
    end_line: int
    methods: list[CodeFunction] = field(default_factory=list)


@dataclass
class CodeAstResult:
    file: str
    language: str
    functions: list[CodeFunction] = field(default_factory=list)
    classes: list[CodeClass] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class TypeDiagnostic:
    file: str
    line: int
    column: int
    message: str
    severity: str


@dataclass
class TypeCheckResult:
    path: str
    diagnostics: list[TypeDiagnostic] = field(default_factory=list)
    error: Optional[str] = None


# ── Helpers ──


def _run_sync(cmd: list[str], cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a subprocess synchronously (wrapped via executor for async callers)."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )


# ── 1. Ruff linter ──


async def lint_code(path: str, fix: bool = False) -> LintResult:
    """Run Ruff linter on a file or directory.

    Parameters
    ----------
    path : str
        File or directory path to lint.
    fix : bool
        If True, auto-fix fixable issues in-place.

    Returns
    -------
    LintResult
        Structured lint diagnostics.
    """
    try:
        cmd = ["ruff", "check", "--output-format", "json"]
        if fix:
            cmd.append("--fix")
        cmd.append(path)

        proc = await asyncio.get_event_loop().run_in_executor(
            None, _run_sync, cmd, None, 120
        )

        if proc.returncode not in (0, 1):
            return LintResult(path=path, error=proc.stderr.strip() or proc.stdout.strip())

        diagnostics: list[LintDiagnostic] = []
        if proc.stdout.strip():
            try:
                raw = json.loads(proc.stdout)
                for item in raw:
                    diagnostics.append(
                        LintDiagnostic(
                            line=item.get("location", {}).get("row", 0),
                            column=item.get("location", {}).get("column", 0),
                            code=item.get("code", ""),
                            message=item.get("message", ""),
                            severity=item.get("severity", "error"),
                        )
                    )
            except json.JSONDecodeError:
                pass

        return LintResult(path=path, diagnostics=diagnostics, fixed=fix)
    except FileNotFoundError:
        return LintResult(path=path, error="ruff not found. Install with: pip install ruff")
    except subprocess.TimeoutExpired:
        return LintResult(path=path, error="ruff timed out")
    except Exception as e:
        logger.exception("lint_code failed")
        return LintResult(path=path, error=str(e))


# ── 2. Ruff formatter ──


async def format_code(path: str, check: bool = False) -> FormatResult:
    """Run Ruff formatter on a file or directory.

    Parameters
    ----------
    path : str
        File or directory path to format.
    check : bool
        If True, only check formatting without modifying files.

    Returns
    -------
    FormatResult
        Whether formatted and list of changed files.
    """
    try:
        cmd = ["ruff", "format", "--output-format", "json"]
        if check:
            cmd.append("--check")
        cmd.append(path)

        proc = await asyncio.get_event_loop().run_in_executor(
            None, _run_sync, cmd, None, 120
        )

        files_changed: list[str] = []
        formatted = False

        if proc.stdout.strip():
            try:
                raw = json.loads(proc.stdout)
                if isinstance(raw, list):
                    for entry in raw:
                        if isinstance(entry, dict):
                            fname = entry.get("file", entry.get("filename", ""))
                            if fname:
                                files_changed.append(fname)
                elif isinstance(raw, dict):
                    fname = raw.get("file", raw.get("filename", ""))
                    if fname:
                        files_changed.append(fname)
            except json.JSONDecodeError:
                pass

        if check:
            formatted = proc.returncode == 0
        else:
            formatted = True

        error: Optional[str] = None
        if proc.returncode != 0 and not check:
            error = proc.stderr.strip() or "formatting failed"
        elif proc.returncode != 0 and check:
            formatted = False

        return FormatResult(path=path, formatted=formatted, files_changed=files_changed, error=error)
    except FileNotFoundError:
        return FormatResult(path=path, error="ruff not found. Install with: pip install ruff")
    except subprocess.TimeoutExpired:
        return FormatResult(path=path, error="ruff timed out")
    except Exception as e:
        logger.exception("format_code failed")
        return FormatResult(path=path, error=str(e))


# ── 3. ripgrep code search ──


async def search_code(
    pattern: str,
    path: str = ".",
    glob: str | None = None,
    json_output: bool = True,
) -> GrepResult:
    """Search code with ripgrep (rg).

    Parameters
    ----------
    pattern : str
        Regex pattern to search for.
    path : str
        Directory or file to search in.
    glob : str | None
        File glob filter (e.g. "*.py").
    json_output : bool
        Parse rg JSON output for structured results.

    Returns
    -------
    GrepResult
        Matching lines with file, line, column, content.
    """
    try:
        cmd = ["rg", "--no-heading"]
        if json_output:
            cmd.extend(["--json"])
        if glob:
            cmd.extend(["--glob", glob])
        cmd.extend([pattern, path])

        proc = await asyncio.get_event_loop().run_in_executor(
            None, _run_sync, cmd, None, 60
        )

        if proc.returncode not in (0, 1):
            return GrepResult(pattern=pattern, error=proc.stderr.strip())

        matches: list[GrepMatch] = []

        if json_output and proc.stdout.strip():
            for line in proc.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "match":
                        data = obj.get("data", {})
                        mtext = data.get("lines", {}).get("text", "")
                        matches.append(
                            GrepMatch(
                                file=data.get("path", {}).get("text", ""),
                                line=data.get("line_number", 0),
                                column=data.get("submatches", [{}])[0].get("start", 0) + 1 if data.get("submatches") else 0,
                                content=mtext.rstrip("\n"),
                            )
                        )
                except json.JSONDecodeError:
                    continue
        elif not json_output and proc.stdout.strip():
            for line in proc.stdout.strip().split("\n"):
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    fpath = parts[0]
                    try:
                        lnum = int(parts[1])
                    except ValueError:
                        lnum = 0
                    content = parts[2]
                    matches.append(
                        GrepMatch(file=fpath, line=lnum, column=0, content=content.rstrip())
                    )

        return GrepResult(pattern=pattern, matches=matches, count=len(matches))
    except FileNotFoundError:
        return GrepResult(pattern=pattern, error="ripgrep (rg) not found. Install from https://github.com/BurntSushi/ripgrep")
    except subprocess.TimeoutExpired:
        return GrepResult(pattern=pattern, error="ripgrep timed out")
    except Exception as e:
        logger.exception("search_code failed")
        return GrepResult(pattern=pattern, error=str(e))


# ── 4. ast-grep structural search ──


async def search_ast(pattern: str, path: str = ".") -> AstGrepResult:
    """Search code by AST pattern using ast-grep (sg).

    Parameters
    ----------
    pattern : str
        AST pattern to match (ast-grep pattern syntax).
    path : str
        Directory or file to search in.

    Returns
    -------
    AstGrepResult
        Matched AST nodes with file, line, column, text.
    """
    try:
        cmd = ["sg", "--pattern", pattern, "--json"]
        cmd.append(path)

        proc = await asyncio.get_event_loop().run_in_executor(
            None, _run_sync, cmd, None, 60
        )

        if proc.returncode not in (0, 1):
            return AstGrepResult(pattern=pattern, error=proc.stderr.strip())

        matches: list[AstGrepMatch] = []
        if proc.stdout.strip():
            try:
                raw = json.loads(proc.stdout)
                items = raw if isinstance(raw, list) else []
                for item in items:
                    pos = item.get("position", {})
                    matches.append(
                        AstGrepMatch(
                            file=item.get("file", ""),
                            line=pos.get("line", 0),
                            column=pos.get("column", 0),
                            text=item.get("text", ""),
                        )
                    )
            except json.JSONDecodeError:
                pass

        return AstGrepResult(pattern=pattern, matches=matches, count=len(matches))
    except FileNotFoundError:
        return AstGrepResult(pattern=pattern, error="ast-grep (sg) not found. Install: npm install -g @ast-grep/cli")
    except subprocess.TimeoutExpired:
        return AstGrepResult(pattern=pattern, error="ast-grep timed out")
    except Exception as e:
        logger.exception("search_ast failed")
        return AstGrepResult(pattern=pattern, error=str(e))


# ── 5. Tree-sitter code parsing ──


_LANGUAGE_MAP: dict[str, tuple[Any, Any]] = {}


def _get_ts_lang(language: str) -> Any:
    """Lazily load a Tree-sitter Language by name."""
    key = language.lower()
    if key in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[key][0]

    lib_path = None
    for candidate in [
        f"tree-sitter-{key}.dll",
        f"tree-sitter-{key}.so",
        os.path.expanduser(f"~/.tree-sitter/bin/tree-sitter-{key}.dll"),
        os.path.expanduser(f"~/.tree-sitter/bin/tree-sitter-{key}.so"),
    ]:
        if os.path.isfile(candidate):
            lib_path = candidate
            break

    if lib_path is None:
        try:
            import importlib
            mod = importlib.import_module(f"tree_sitter_{key}")
            lang_func = getattr(mod, f"language_{key}")
            lang = Language(lang_func())
            _LANGUAGE_MAP[key] = (lang, mod)
            return lang
        except (ImportError, AttributeError):
            raise ImportError(
                f"Tree-sitter language '{language}' not found. "
                f"Install: pip install tree-sitter-{key}"
            )

    lang = Language(lib_path, key)
    _LANGUAGE_MAP[key] = (lang, None)
    return lang


_SOURCE_EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".php": "php",
    ".r": "r",
    ".m": "objective_c",
    ".mm": "objective_c",
    ".sql": "sql",
    ".bash": "bash",
    ".sh": "bash",
    ".zsh": "bash",
    ".fish": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    ".astro": "astro",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".zig": "zig",
    ".nim": "nim",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".edn": "clojure",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".fs": "fsharp",
    ".fsx": "fsharp",
    ".v": "verilog",
    ".vh": "verilog",
    ".sv": "systemverilog",
    ".svh": "systemverilog",
    ".proto": "protobuf",
    ".gradle": "groovy",
    ".groovy": "groovy",
    ".dart": "dart",
    ".tex": "latex",
}


_QUERY_FUNCTIONS: dict[str, str] = {}
_QUERY_CLASSES: dict[str, str] = {}
_QUERY_IMPORTS: dict[str, str] = {}

_QUERY_FUNCTIONS["python"] = """
(function_definition
  name: (identifier) @name
  body: (block . (expression_statement (string))? @doc)
) @func
"""
_QUERY_FUNCTIONS["javascript"] = """
(function_declaration
  name: (identifier) @name
  body: (statement_block . (expression_statement (string))? @doc)
) @func
(generator_function_declaration
  name: (identifier) @name) @func
(arrow_function
  name: (identifier) @name) @func
"""
_QUERY_FUNCTIONS["typescript"] = _QUERY_FUNCTIONS["javascript"]
_QUERY_FUNCTIONS["go"] = """
(function_declaration
  name: (identifier) @name) @func
(method_declaration
  name: (field_identifier) @name) @func
"""
_QUERY_FUNCTIONS["rust"] = """
(function_item
  name: (identifier) @name) @func
"""
_QUERY_FUNCTIONS["java"] = """
(method_declaration
  name: (identifier) @name) @func
"""

_QUERY_CLASSES["python"] = """
(class_definition
  name: (identifier) @name
  body: (block) @body) @class
"""
_QUERY_CLASSES["javascript"] = """
(class_declaration
  name: (identifier) @name
  body: (class_body) @body) @class
"""
_QUERY_CLASSES["typescript"] = _QUERY_CLASSES["javascript"]
_QUERY_CLASSES["go"] = _QUERY_CLASSES["javascript"]
_QUERY_CLASSES["rust"] = """
(struct_item
  name: (type_identifier) @name) @struct
(enum_item
  name: (type_identifier) @name) @enum
"""
_QUERY_CLASSES["java"] = """
(class_declaration
  name: (identifier) @name) @class
"""

_QUERY_IMPORTS["python"] = """
(import_statement) @imp
(import_from_statement) @imp
"""
_QUERY_IMPORTS["javascript"] = """
(import_statement) @imp
"""
_QUERY_IMPORTS["typescript"] = _QUERY_IMPORTS["javascript"]


def _extract_ts_text(node: Any, source_bytes: bytes) -> str:
    """Extract source text for a Tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_ts_docstring(node: Any, source_bytes: bytes, lang: str) -> Optional[str]:
    """Extract a docstring comment if present."""
    if not node:
        return None
    text = _extract_ts_text(node, source_bytes).strip()
    if lang == "python":
        if text.startswith(('"""', "'''")):
            text = text[3:-3].strip()
    elif lang in ("javascript", "typescript", "java"):
        if text.startswith("/*"):
            text = text[2:-2].strip()
        elif text.startswith("//"):
            text = text[2:].strip()
    elif lang == "go":
        if text.startswith("/*"):
            text = text[2:-2].strip()
    elif lang == "rust":
        if text.startswith("///"):
            text = text[3:].strip()
        elif text.startswith("//!"):
            text = text[3:].strip()
        elif text.startswith("/*"):
            text = text[2:-2].strip()
    return text if text else None


async def parse_code(file_path: str, language: str | None = None) -> CodeAstResult:
    """Parse a code file with Tree-sitter and extract functions, classes, imports.

    Parameters
    ----------
    file_path : str
        Path to the source file.
    language : str | None
        Language name (e.g. "python", "javascript"). Auto-detected from extension if None.

    Returns
    -------
    CodeAstResult
        Extracted AST information.
    """
    if not os.path.isfile(file_path):
        return CodeAstResult(file=file_path, language=language or "unknown", error=f"File not found: {file_path}")

    if language is None:
        ext = os.path.splitext(file_path)[1].lower()
        language = _SOURCE_EXT_MAP.get(ext)
        if language is None:
            return CodeAstResult(
                file=file_path,
                language="unknown",
                error=f"Unknown file extension '{ext}'. Specify language parameter.",
            )

    if not HAS_TREE_SITTER:
        return CodeAstResult(
            file=file_path, language=language,
            error="tree-sitter not installed. Install with: pip install tree-sitter",
        )

    try:
        ts_lang = _get_ts_lang(language)
    except ImportError as e:
        return CodeAstResult(file=file_path, language=language, error=str(e))

    try:
        with open(file_path, "rb") as f:
            source_bytes = f.read()
    except Exception as e:
        return CodeAstResult(file=file_path, language=language, error=f"Cannot read file: {e}")

    try:
        parser = Parser()
        parser.set_language(ts_lang)

        tree = await asyncio.get_event_loop().run_in_executor(
            None, lambda: parser.parse(source_bytes)
        )
        root = tree.root_node

        functions: list[CodeFunction] = []
        classes: list[CodeClass] = []
        imports: list[str] = []

        # Extract functions
        func_query_str = _QUERY_FUNCTIONS.get(language)
        if func_query_str:
            func_query = ts_lang.query(func_query_str)
            func_captures = func_query.captures(root)
            for node, tag in func_captures:
                if tag == "name":
                    name = _extract_ts_text(node, source_bytes)
                    func_node = node.parent if node.parent else node
                    doc_node = None
                    for n2, t2 in func_captures:
                        if t2 == "doc" and n2.start_byte > func_node.start_byte and n2.end_byte <= func_node.end_byte:
                            doc_node = n2
                            break
                    docstring = _extract_ts_docstring(doc_node, source_bytes, language) if doc_node else None
                    functions.append(
                        CodeFunction(
                            name=name,
                            start_line=func_node.start_point[0] + 1,
                            end_line=func_node.end_point[0] + 1,
                            docstring=docstring,
                        )
                    )

        # Extract classes
        class_query_str = _QUERY_CLASSES.get(language)
        if class_query_str:
            class_query = ts_lang.query(class_query_str)
            class_captures = class_query.captures(root)
            current_class: Optional[CodeClass] = None
            for node, tag in class_captures:
                if tag == "name":
                    name = _extract_ts_text(node, source_bytes)
                    current_class = CodeClass(
                        name=name,
                        start_line=node.parent.start_point[0] + 1 if node.parent else 0,
                        end_line=node.parent.end_point[0] + 1 if node.parent else 0,
                    )
                    classes.append(current_class)
                elif tag == "body" and current_class is not None:
                    if language == "python":
                        body_text = _extract_ts_text(node, source_bytes)
                        method_query = ts_lang.query("""
                            (function_definition
                              name: (identifier) @mname
                              body: (block . (expression_statement (string))? @mdoc)
                            ) @method
                        """)
                        method_caps = method_query.captures(node)
                        method_map: dict[str, CodeFunction] = {}
                        for mnode, mtag in method_caps:
                            if mtag == "mname":
                                mname = _extract_ts_text(mnode, source_bytes)
                                mfunc_node = mnode.parent if mnode.parent else mnode
                                method_map[mname] = CodeFunction(
                                    name=mname,
                                    start_line=mfunc_node.start_point[0] + 1,
                                    end_line=mfunc_node.end_point[0] + 1,
                                )
                            elif mtag == "mdoc":
                                for mn in method_map:
                                    if method_map[mn].docstring is None:
                                        method_map[mn].docstring = _extract_ts_docstring(mnode, source_bytes, language)
                        current_class.methods = list(method_map.values())

        # Extract imports
        import_query_str = _QUERY_IMPORTS.get(language)
        if import_query_str:
            import_query = ts_lang.query(import_query_str)
            import_captures = import_query.captures(root)
            seen: set[str] = set()
            for node, tag in import_captures:
                if tag == "imp":
                    text = _extract_ts_text(node, source_bytes)
                    if text not in seen:
                        seen.add(text)
                        imports.append(text)

        return CodeAstResult(
            file=file_path,
            language=language,
            functions=functions,
            classes=classes,
            imports=imports,
        )
    except Exception as e:
        logger.exception("parse_code failed")
        return CodeAstResult(file=file_path, language=language, error=str(e))


# ── 6. Pyright type checking ──


async def type_check(path: str) -> TypeCheckResult:
    """Run Pyright for Python type checking.

    Parameters
    ----------
    path : str
        File or directory path to type check.

    Returns
    -------
    TypeCheckResult
        Type diagnostics with file, line, column, message, severity.
    """
    try:
        cmd = ["pyright", "--outputjson", path]

        proc = await asyncio.get_event_loop().run_in_executor(
            None, _run_sync, cmd, None, 120
        )

        diagnostics: list[TypeDiagnostic] = []
        error: Optional[str] = None

        if proc.stdout.strip():
            try:
                raw = json.loads(proc.stdout)
                for diag in raw.get("generalDiagnostics", []):
                    file_path = diag.get("file", "")
                    range_info = diag.get("range", {})
                    start = range_info.get("start", {})
                    diagnostics.append(
                        TypeDiagnostic(
                            file=file_path,
                            line=start.get("line", 0) + 1,
                            column=start.get("column", 0) + 1,
                            message=diag.get("message", ""),
                            severity=diag.get("severity", "error"),
                        )
                    )
            except json.JSONDecodeError:
                error = "Failed to parse pyright JSON output"
        elif proc.stderr.strip():
            error = proc.stderr.strip()
        elif proc.returncode != 0:
            error = f"pyright exited with code {proc.returncode}"

        return TypeCheckResult(path=path, diagnostics=diagnostics, error=error)
    except FileNotFoundError:
        return TypeCheckResult(path=path, error="pyright not found. Install: npm install -g pyright or pip install pyright")
    except subprocess.TimeoutExpired:
        return TypeCheckResult(path=path, error="pyright timed out")
    except Exception as e:
        logger.exception("type_check failed")
        return TypeCheckResult(path=path, error=str(e))
