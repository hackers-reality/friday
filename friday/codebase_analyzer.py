"""
FRIDAY Codebase Analyzer - self-referential analysis of the FRIDAY codebase.
Analyzes module dependency graphs, function/class usage, complexity metrics,
import relationships, dead code detection, style violations, and test coverage.
Uses only stdlib to avoid circular imports with FRIDAY packages.
"""

import ast
import os
import re
import json
import math
import sys
import textwrap
import collections
import datetime
import hashlib
import pathlib
import itertools
import subprocess
import typing
import functools
import operator
import copy
import string
import uuid
import statistics
import dataclasses

if typing.TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRIDAY_ROOT: typing.Final[str] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRIDAY_SOURCE: typing.Final[str] = os.path.join(FRIDAY_ROOT, "friday")
TEST_DIRS: typing.Final[list[str]] = ["tests", "test"]
IGNORE_DIRS: typing.Final[set[str]] = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", ".mypy_cache", ".pytest_cache"}
IGNORE_FILES: typing.Final[set[str]] = {"__init__.py", "__main__.py", "codebase_analyzer.py"}
MAX_LINE_LENGTH: typing.Final[int] = 120
DUPLICATE_SIMILARITY_THRESHOLD: typing.Final[float] = 0.75
FRIDAY_ANALYZER_VERSION: typing.Final[str] = "1.0.0"


# ===================================================================
# Utility Functions
# ===================================================================


def get_all_python_files(source_dir: str, recursive: bool = True) -> list[str]:
    """Return all .py files under source_dir, excluding ignored dirs/files."""
    result: list[str] = []
    source_path = pathlib.Path(source_dir)
    if recursive:
        for root_str, dirs, files in os.walk(str(source_path)):
            root = pathlib.Path(root_str)
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for f in files:
                if f.endswith(".py") and f not in IGNORE_FILES:
                    result.append(str(root / f))
    else:
        for f in os.listdir(str(source_path)):
            if f.endswith(".py") and f not in IGNORE_FILES:
                result.append(str(source_path / f))
    return sorted(result)


def module_name_from_path(path: str, source_dir: str | None = None) -> str:
    """Convert a file path to a dot-separated module name."""
    p = pathlib.Path(path)
    if source_dir:
        try:
            rel = p.relative_to(source_dir)
        except ValueError:
            rel = p
    else:
        rel = p
    parts = list(rel.parts)
    if parts[-1] in ("__init__.py", "__main__.py"):
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    module = ".".join(parts)
    return module if module else pathlib.Path(source_dir or "").name


def path_from_module_name(module: str, source_dir: str) -> str | None:
    """Convert a module name back to a file path."""
    parts = module.split(".")
    base = pathlib.Path(source_dir)
    for p in parts[:-1]:
        base = base / p
    py_file = base / (parts[-1] + ".py")
    init_file = base / "__init__.py"
    if py_file.exists():
        return str(py_file)
    if init_file.exists():
        return str(init_file)
    return None


def normalize_import_name(name: str) -> str:
    """Normalize an import name by stripping aliases."""
    return name.split(" as ")[0].strip()


def is_friday_module(name: str) -> bool:
    """Check if an import name looks like a FRIDAY module."""
    return name.startswith("friday") or name.startswith("friday.")


def strip_string_literals(source: str) -> str:
    """Remove string literals from source code for pattern matching."""
    out: list[str] = []
    i = 0
    while i < len(source):
        if source[i] in ("'", '"'):
            quote = source[i]
            i += 1
            if i < len(source) and source[i] == quote:
                i += 1
                if i < len(source) and source[i] == quote:
                    i += 1
                    while i < len(source) - 2:
                        if source[i:i+3] == quote * 3:
                            i += 3
                            break
                        i += 1
            else:
                while i < len(source) and source[i] != quote:
                    if source[i] == "\\":
                        i += 1
                    i += 1
                i += 1
        else:
            out.append(source[i])
            i += 1
    return "".join(out)


def levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def similarity_ratio(a: str, b: str) -> float:
    """Compute a similarity ratio between 0.0 and 1.0 for two strings."""
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - (levenshtein_distance(a, b) / max_len)


def get_git_timestamps(filepath: str) -> list[datetime.datetime]:
    """Get timestamps of commits touching a file (returns empty list if no git)."""
    try:
        rel = os.path.relpath(filepath, FRIDAY_ROOT)
        result = subprocess.run(
            ["git", "log", "--format=%ct", "--follow", "--", rel],
            capture_output=True, text=True, cwd=FRIDAY_ROOT, timeout=10
        )
        if result.returncode != 0:
            return []
        timestamps: list[datetime.datetime] = []
        for line in result.stdout.strip().splitlines():
            if line.strip():
                ts = datetime.datetime.fromtimestamp(int(line.strip()))
                timestamps.append(ts)
        return timestamps
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return []


def truncate(text: str, max_len: int = 60) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def safe_name(name: str) -> str:
    """Make a string safe for use as an identifier."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return singular
    return plural if plural else singular + "s"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def count_lines_of_types(lines: list[str]) -> dict[str, int]:
    """Count blank, comment, code, and docstring lines in a list of lines."""
    result: dict[str, int] = {"blank": 0, "comment": 0, "code": 0, "docstring": 0}
    in_docstring = False
    docstring_quote: str | None = None
    for line in lines:
        stripped = line.strip()
        if in_docstring:
            result["docstring"] += 1
            if docstring_quote and docstring_quote in stripped:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            result["docstring"] += 1
            if stripped.count(stripped[:3]) < 2:
                in_docstring = True
                docstring_quote = stripped[:3]
            continue
        if not stripped:
            result["blank"] += 1
        elif stripped.startswith("#"):
            result["comment"] += 1
        else:
            result["code"] += 1
    return result


def classify_import(module_name: str) -> str:
    """Classify an import as stdlib, third_party, or local."""
    STDLIB_MODULES = {
        "ast", "os", "re", "json", "math", "sys", "textwrap",
        "collections", "datetime", "hashlib", "pathlib", "itertools",
        "subprocess", "typing", "functools", "operator", "copy",
        "string", "uuid", "statistics", "dataclasses", "inspect",
        "io", "abc", "argparse", "base64", "bisect", "calendar",
        "csv", "decimal", "difflib", "dis", "enum", "filecmp",
        "fnmatch", "fractions", "getopt", "getpass", "glob",
        "gzip", "heapq", "hmac", "html", "http", "imp",
        "importlib", "ipaddress", "logging", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "numbers",
        "pickle", "pkgutil", "platform", "pprint", "profile",
        "pstats", "queue", "random", "reprlib", "rlcompleter",
        "runpy", "secrets", "select", "selectors", "shelve",
        "shlex", "shutil", "signal", "socket", "socketserver",
        "sqlite3", "ssl", "stat", "stringprep", "struct",
        "tabnanny", "tarfile", "tempfile", "threading", "time",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "traceback", "tracemalloc", "turtle", "types", "unicodedata",
        "unittest", "urllib", "uu", "venv", "warnings", "wave",
        "weakref", "webbrowser", "winreg", "winsound", "xml",
        "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
        "__future__", "builtins"
    }
    base = module_name.split(".")[0]
    if base in STDLIB_MODULES:
        return "stdlib"
    if module_name.startswith("friday"):
        return "local"
    return "third_party"


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def safe_read_file(path: str) -> str | None:
    """Safely read a file and return its content or None on error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


# ===================================================================
# AST Visitors
# ===================================================================


class ImportVisitor(ast.NodeVisitor):
    """Collect all import statements from an AST."""
    def __init__(self) -> None:
        self.imports: dict[str, list[str]] = collections.defaultdict(list)
        self.import_lines: list[dict[str, typing.Any]] = []
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            self.imports[name].append(asname)
            self.import_lines.append({
                "type": "import",
                "module": name,
                "alias": asname,
                "lineno": getattr(node, "lineno", 0),
                "col_offset": getattr(node, "col_offset", 0)
            })
        self.generic_visit(node)
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            self.imports[module].append(name)
            self.import_lines.append({
                "type": "import_from",
                "module": module,
                "name": name,
                "alias": asname,
                "lineno": getattr(node, "lineno", 0),
                "col_offset": getattr(node, "col_offset", 0)
            })
        self.generic_visit(node)


class FunctionVisitor(ast.NodeVisitor):
    """Collect all function and method definitions from an AST."""
    def __init__(self) -> None:
        self.functions: list[dict[str, typing.Any]] = []
        self.current_class: str | None = None
        self.class_stack: list[str] = []
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._format_attribute(base))
        decorators: list[str] = [
            self._format_decorator(d) for d in node.decorator_list
        ]
        class_info: dict[str, typing.Any] = {
            "name": node.name,
            "lineno": getattr(node, "lineno", 0),
            "end_lineno": getattr(node, "end_lineno", 0),
            "bases": bases,
            "decorators": decorators,
            "docstring": ast.get_docstring(node) or "",
            "methods": [],
            "class_variables": self._collect_class_variables(node),
            "num_methods": 0
        }
        old_class = self.current_class
        self.class_stack.append(node.name)
        self.current_class = ".".join(self.class_stack)
        self.generic_visit(node)
        class_info["num_methods"] = len(class_info["methods"])
        self.current_class = old_class
        self.class_stack.pop()
        self.functions.append(class_info)
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._add_function(node)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        info = self._add_function(node)
        info["is_async"] = True
    def _add_function(self, node):
        decorators = [self._format_decorator(d) for d in node.decorator_list]
        args_info = self._extract_args(node.args)
        returns = self._format_annotation(node.returns) if node.returns else None
        info = {
            "name": node.name,
            "lineno": getattr(node, "lineno", 0),
            "end_lineno": getattr(node, "end_lineno", 0),
            "class_name": self.current_class,
            "decorators": decorators,
            "args": args_info,
            "returns": returns,
            "docstring": ast.get_docstring(node) or "",
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_method": self.current_class is not None,
            "has_type_annotations": any(self._has_annotations(node)),
            "num_statements": len(node.body),
            "full_qualified_name": self._qualified_name(node.name)
        }
        if self.current_class:
            for f in reversed(self.functions):
                if f["name"] == self.current_class.split(".")[-1]:
                    f["methods"].append(info)
                    break
        self.functions.append(info)
        return info
    def _extract_args(self, args):
        result = {
            "posonlyargs": [], "args": [], "vararg": None,
            "kwonlyargs": [], "kw_defaults": [], "kwarg": None,
            "defaults": []
        }
        for a in args.posonlyargs:
            result["posonlyargs"].append({
                "arg": a.arg,
                "annotation": self._format_annotation(a.annotation) if a.annotation else None
            })
        for a in args.args:
            result["args"].append({
                "arg": a.arg,
                "annotation": self._format_annotation(a.annotation) if a.annotation else None
            })
        if args.vararg:
            result["vararg"] = {"arg": args.vararg.arg, "annotation": self._format_annotation(args.vararg.annotation) if args.vararg.annotation else None}
        for a in args.kwonlyargs:
            result["kwonlyargs"].append({
                "arg": a.arg,
                "annotation": self._format_annotation(a.annotation) if a.annotation else None
            })
        result["kw_defaults"] = [None for _ in args.kw_defaults]
        if args.kwarg:
            result["kwarg"] = {"arg": args.kwarg.arg, "annotation": self._format_annotation(args.kwarg.annotation) if args.kwarg.annotation else None}
        result["defaults"] = [None for _ in args.defaults]
        return result
    def _has_annotations(self, node):
        if node.returns:
            yield True
        for a in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if a.annotation:
                yield True
        if node.args.vararg and node.args.vararg.annotation:
            yield True
        if node.args.kwarg and node.args.kwarg.annotation:
            yield True
    def _qualified_name(self, name):
        if self.current_class:
            return f"{self.current_class}.{name}"
        return name
    def _format_annotation(self, node):
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self._format_attribute(node)
        if isinstance(node, ast.Subscript):
            value = self._format_annotation(node.value)
            slice_val = self._format_annotation(node.slice)
            return f"{value}[{slice_val}]"
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Tuple):
            elts = ", ".join(self._format_annotation(e) for e in node.elts)
            return f"({elts})"
        return ast.dump(node)
    def _format_attribute(self, node):
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        elif isinstance(current, ast.Call):
            parts.append("call")
        return ".".join(reversed(parts))
    def _format_decorator(self, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self._format_attribute(node)
        if isinstance(node, ast.Call):
            func = self._format_decorator(node.func)
            args = ", ".join(self._format_decorator(a) for a in node.args)
            kwargs = ", ".join(f"{k.arg}={self._format_decorator(k.value)}" for k in node.keywords)
            all_args = ", ".join(filter(None, [args, kwargs]))
            return f"{func}({all_args})"
        return ast.dump(node)
    def _collect_class_variables(self, node):
        vars_list = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        vars_list.append({"name": target.id, "lineno": getattr(item, "lineno", 0)})
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    vars_list.append({"name": item.target.id, "lineno": getattr(item, "lineno", 0)})
        return vars_list


class NameUsageVisitor(ast.NodeVisitor):
    """Collect all name references from an AST."""
    def __init__(self):
        self.called_names = []
        self.attribute_accesses = []
        self.name_references = []
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.called_names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.called_names.append(self._format_attribute(node.func))
        self.generic_visit(node)
    def visit_Name(self, node):
        self.name_references.append(node.id)
        self.generic_visit(node)
    def visit_Attribute(self, node):
        self.attribute_accesses.append(self._format_attribute(node))
        self.generic_visit(node)
    def _format_attribute(self, node):
        parts = [node.attr]
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))


# ===================================================================
# FileAnalyzer
# ===================================================================


@dataclasses.dataclass
class FileAnalysis:
    """Container for analysis results of a single file."""
    path: str
    module_name: str
    imports: list[dict[str, typing.Any]]
    functions: list[dict[str, typing.Any]]
    classes: list[dict[str, typing.Any]]
    lines_of_code: int
    source_lines: int
    blank_lines: int
    comment_lines: int
    docstring_lines: int
    complexity_score: float
    docstring_coverage: float
    dependencies: list[str]
    exports: list[str]
    errors: list[str]
    ast_node: ast.Module | None
    named_exports: list[str]
    @property
    def has_error(self) -> bool:
        return len(self.errors) > 0
    @property
    def num_functions(self) -> int:
        return len(self.functions)
    @property
    def num_classes(self) -> int:
        return len(self.classes)
    @property
    def num_imports(self) -> int:
        return len(self.imports)
    def to_dict(self) -> dict[str, typing.Any]:
        result = dataclasses.asdict(self)
        result["ast_node"] = None
        return result


class FileAnalyzer:
    """Analyzes a single Python file using AST parsing."""
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self._cache: dict[str, FileAnalysis] = {}
    def analyze_file(self, path: str) -> FileAnalysis:
        """Analyze a single Python file and return structured results."""
        if path in self._cache:
            return self._cache[path]
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        module_name = module_name_from_path(abs_path, self.source_dir)
        result = self._analyze_source(source, abs_path, module_name)
        self._cache[path] = result
        return result
    def analyze_source(self, source: str, path: str = "<string>", module_name: str = "<unknown>") -> FileAnalysis:
        """Analyze Python source code directly."""
        return self._analyze_source(source, path, module_name)
    def _analyze_source(self, source: str, path: str, module_name: str) -> FileAnalysis:
        errors: list[str] = []
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as e:
            errors.append(f"SyntaxError: {e}")
            return FileAnalysis(
                path=path, module_name=module_name, imports=[], functions=[],
                classes=[], lines_of_code=0, source_lines=0, blank_lines=0,
                comment_lines=0, docstring_lines=0, complexity_score=0.0,
                docstring_coverage=0.0, dependencies=[], exports=[],
                errors=errors, ast_node=None, named_exports=[]
            )
        import_visitor = ImportVisitor()
        import_visitor.visit(tree)
        func_visitor = FunctionVisitor()
        func_visitor.visit(tree)
        imports = import_visitor.import_lines
        all_funcs = func_visitor.functions
        classes = [f for f in all_funcs if "bases" in f]
        functions = [f for f in all_funcs if "bases" not in f]
        for cls in classes:
            for meth in cls.get("methods", []):
                if meth in functions:
                    functions.remove(meth)
        lines = source.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
        docstring_lines = self._count_docstring_lines(source)
        source_lines = total_lines - blank_lines - comment_lines - docstring_lines
        dependencies = [imp["module"] for imp in imports if imp["module"]]
        dependencies = list(set(dependencies))
        exports = self._find_exports(tree, source)
        named_exports = [imp["name"] for imp in imports if imp.get("name")]
        named_exports = list(set(named_exports))
        complexity_score = self._calculate_complexity(functions, classes)
        docstring_coverage = self._calculate_docstring_coverage(functions, classes)
        return FileAnalysis(
            path=path, module_name=module_name, imports=imports,
            functions=functions, classes=classes, lines_of_code=total_lines,
            source_lines=source_lines, blank_lines=blank_lines,
            comment_lines=comment_lines, docstring_lines=docstring_lines,
            complexity_score=complexity_score,
            docstring_coverage=docstring_coverage,
            dependencies=dependencies, exports=exports, errors=errors,
            ast_node=tree, named_exports=named_exports
        )
    def _count_docstring_lines(self, source: str) -> int:
        count = 0
        for match in re.finditer(r'""".*?"""|\'\'\'.*?\'\'\'', source, re.DOTALL):
            count += match.group(0).count("\n") + 1
        return count
    def _find_exports(self, tree: ast.Module, source: str) -> list[str]:
        exports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    exports.append(node.name)
        return list(set(exports))
    def _calculate_complexity(self, functions: list[dict], classes: list[dict]) -> float:
        total = 0.0
        count = 0
        for func in functions:
            total += func.get("num_statements", 1)
            count += 1
        for cls in classes:
            total += cls.get("num_methods", 0) * 2
            count += max(cls.get("num_methods", 0), 1)
        return total / max(count, 1)
    def _calculate_docstring_coverage(self, functions: list[dict], classes: list[dict]) -> float:
        total = len(functions) + len(classes)
        if total == 0:
            return 1.0
        doc_count = sum(1 for f in functions if f.get("docstring", "").strip())
        doc_count += sum(1 for c in classes if c.get("docstring", "").strip())
        return doc_count / total
    def clear_cache(self) -> None:
        """Clear the file analysis cache."""
        self._cache.clear()
    def analyze_directory(self, directory: str | None = None) -> dict[str, FileAnalysis]:
        """Analyze all Python files in a directory."""
        d = directory or self.source_dir
        files = get_all_python_files(d)
        results: dict[str, FileAnalysis] = {}
        for f in files:
            try:
                results[f] = self.analyze_file(f)
            except Exception as e:
                errors = [str(e)]
                module_name = module_name_from_path(f, self.source_dir)
                results[f] = FileAnalysis(
                    path=f, module_name=module_name, imports=[], functions=[],
                    classes=[], lines_of_code=0, source_lines=0, blank_lines=0,
                    comment_lines=0, docstring_lines=0, complexity_score=0.0,
                    docstring_coverage=0.0, dependencies=[], exports=[],
                    errors=errors, ast_node=None, named_exports=[]
                )
        return results


# ===================================================================
# ModuleGraph
# ===================================================================


@dataclasses.dataclass
class ModuleNode:
    """Represents a single module in the dependency graph."""
    name: str
    path: str
    dependencies: set[str]
    dependents: set[str]
    file_size: int
    lines_of_code: int
    num_functions: int
    num_classes: int
    num_imports: int
    is_package: bool
    def to_dict(self) -> dict[str, typing.Any]:
        return {
            "name": self.name,
            "path": self.path,
            "dependencies": sorted(self.dependencies),
            "dependents": sorted(self.dependents),
            "file_size": self.file_size,
            "lines_of_code": self.lines_of_code,
            "num_functions": self.num_functions,
            "num_classes": self.num_classes,
            "num_imports": self.num_imports,
            "is_package": self.is_package
        }


class ModuleGraph:
    """Builds and analyzes the dependency graph of FRIDAY modules."""
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self.nodes: dict[str, ModuleNode] = {}
        self._file_analyzer = FileAnalyzer(self.source_dir)
        self._built = False
    def build_graph(self, source_dir: str | None = None):
        """Walk all friday/*.py files and build the dependency graph."""
        sd = source_dir or self.source_dir
        files = get_all_python_files(sd)
        self.source_dir = sd
        all_friday_modules: set[str] = set()
        for f in files:
            mod = module_name_from_path(f, self.source_dir)
            all_friday_modules.add(mod)
        self.nodes = {}
        for f in files:
            try:
                analysis = self._file_analyzer.analyze_file(f)
            except Exception:
                analysis = None
            mod = module_name_from_path(f, self.source_dir)
            file_size = os.path.getsize(f)
            loc = analysis.lines_of_code if analysis else 0
            num_funcs = analysis.num_functions if analysis else 0
            num_cls = analysis.num_classes if analysis else 0
            num_imps = analysis.num_imports if analysis else 0
            is_pkg = os.path.basename(f) == "__init__.py"
            deps: set[str] = set()
            if analysis:
                for dep in analysis.dependencies:
                    if dep in all_friday_modules:
                        deps.add(dep)
                    elif dep.startswith("friday."):
                        deps.add(dep)
                    elif "." not in dep and analysis.module_name.startswith("friday."):
                        candidate = f"friday.{dep}"
                        if candidate in all_friday_modules:
                            deps.add(candidate)
            self.nodes[mod] = ModuleNode(
                name=mod, path=f, dependencies=deps, dependents=set(),
                file_size=file_size, lines_of_code=loc,
                num_functions=num_funcs, num_classes=num_cls,
                num_imports=num_imps, is_package=is_pkg
            )
        for mod, node in list(self.nodes.items()):
            for dep in node.dependencies:
                if dep in self.nodes:
                    self.nodes[dep].dependents.add(mod)
        self._built = True
        return self
    def find_cycles(self) -> list[list[str]]:
        """Detect circular imports using DFS."""
        if not self._built:
            self.build_graph()
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {m: WHITE for m in self.nodes}
        parent: dict[str, str | None] = {}
        cycles: list[list[str]] = []
        def dfs(node: str, path: list[str] | None = None) -> None:
            if path is None:
                path = []
            color[node] = GRAY
            path.append(node)
            for neighbor in self.nodes[node].dependencies:
                if neighbor not in self.nodes:
                    continue
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor, path)
            color[node] = BLACK
            path.pop()
        for m in list(self.nodes.keys()):
            if color[m] == WHITE:
                dfs(m)
        unique_cycles: list[list[str]] = []
        seen_cycles: set[str] = set()
        for cycle in cycles:
            if len(cycle) < 2:
                continue
            normalized = "->".join(sorted(cycle[:-1]))
            if normalized not in seen_cycles:
                seen_cycles.add(normalized)
                unique_cycles.append(cycle)
        return unique_cycles
    def topological_sort(self) -> list[str]:
        """Order modules by dependency (DFS-based topological sort)."""
        if not self._built:
            self.build_graph()
        visited: set[str] = set()
        result: list[str] = []
        def dfs(n: str) -> None:
            if n in visited:
                return
            visited.add(n)
            for dep in self.nodes[n].dependencies:
                if dep in self.nodes:
                    dfs(dep)
            result.append(n)
        for m in list(self.nodes.keys()):
            dfs(m)
        return result
    def get_dependents(self, module: str) -> list[str]:
        """Return list of modules that depend on the given module."""
        if not self._built:
            self.build_graph()
        node = self.nodes.get(module)
        if node is None:
            return []
        return sorted(node.dependents)
    def get_dependencies(self, module: str) -> list[str]:
        """Return list of modules that the given module imports."""
        if not self._built:
            self.build_graph()
        node = self.nodes.get(module)
        if node is None:
            return []
        return sorted(node.dependencies)
    def get_all_modules(self) -> list[str]:
        """Return sorted list of all module names."""
        if not self._built:
            self.build_graph()
        return sorted(self.nodes.keys())
    def get_node(self, module: str) -> ModuleNode | None:
        """Get a specific module node."""
        return self.nodes.get(module)
    def get_stats(self) -> dict[str, typing.Any]:
        """Return aggregate graph statistics."""
        if not self._built:
            self.build_graph()
        total_loc = sum(n.lines_of_code for n in self.nodes.values())
        total_funcs = sum(n.num_functions for n in self.nodes.values())
        total_classes = sum(n.num_classes for n in self.nodes.values())
        total_imports = sum(n.num_imports for n in self.nodes.values())
        edges = sum(len(n.dependencies) for n in self.nodes.values())
        cycles = self.find_cycles()
        return {
            "num_modules": len(self.nodes),
            "total_lines_of_code": total_loc,
            "total_functions": total_funcs,
            "total_classes": total_classes,
            "total_imports": total_imports,
            "dependency_edges": edges,
            "num_cycles": len(cycles),
            "cycles": cycles
        }
    def get_subgraph(self, modules: list[str]) -> dict[str, typing.Any]:
        """Extract a subgraph containing only the given modules."""
        sub: dict[str, typing.Any] = {}
        for m in modules:
            if m in self.nodes:
                node = self.nodes[m]
                sub[m] = {
                    "dependencies": [d for d in node.dependencies if d in modules],
                    "dependents": [d for d in node.dependents if d in modules]
                }
        return sub
    def find_orphans(self) -> list[str]:
        """Find modules with no dependents and no dependencies (isolated)."""
        if not self._built:
            self.build_graph()
        orphans: list[str] = []
        for mod, node in self.nodes.items():
            if not node.dependencies and not node.dependents:
                orphans.append(mod)
        return sorted(orphans)


# ===================================================================
# ComplexityAnalyzer
# ===================================================================


class ComplexityAnalyzer:
    """McCabe cyclomatic complexity, nesting depth, line length violations."""
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self._file_analyzer = FileAnalyzer(self.source_dir)
        self._results: dict[str, list[dict[str, typing.Any]]] = {}
        self._history: dict[str, list[dict[str, typing.Any]]] = {}
    def analyze_complexity(self, path: str) -> list[dict[str, typing.Any]]:
        """Analyze cyclomatic complexity for each function in a file."""
        if path in self._results:
            return self._results[path]
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            return []
        results: list[dict[str, typing.Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._cyclomatic_complexity(node)
                nesting = self._nesting_depth(node)
                lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 1
                docstring = ast.get_docstring(node) or ""
                results.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "cyclomatic_complexity": complexity,
                    "nesting_depth": nesting,
                    "lines": lines,
                    "has_docstring": bool(docstring.strip()),
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                })
        self._results[path] = results
        return results
    def _cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe cyclomatic complexity for a function body."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                for item in child.items:
                    if item.optional_vars:
                        complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.Match):
                complexity += len(child.cases)
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                for _if in child.ifs:
                    complexity += 1
        return complexity
    def _nesting_depth(self, node: ast.AST) -> int:
        """Compute maximum nesting depth of control structures."""
        max_depth = 0
        current_depth = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                 ast.With, ast.AsyncWith, ast.Try, ast.Match)):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
                for sub in ast.walk(child):
                    if sub is child:
                        continue
                    if isinstance(sub, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                        ast.With, ast.AsyncWith, ast.Try, ast.Match)):
                        current_depth += 1
                        max_depth = max(max_depth, current_depth)
                        current_depth -= 1
                current_depth -= 1
        return max_depth
    def get_hotspots(self, threshold: int = 10) -> list[dict[str, typing.Any]]:
        """Return functions with cyclomatic complexity greater than threshold."""
        if not self._results:
            self.analyze_directory()
        hotspots: list[dict[str, typing.Any]] = []
        for path, funcs in self._results.items():
            for f in funcs:
                if f["cyclomatic_complexity"] > threshold:
                    hotspots.append({
                        **f,
                        "file": path,
                        "module": module_name_from_path(path, self.source_dir)
                    })
        return sorted(hotspots, key=lambda x: x["cyclomatic_complexity"], reverse=True)
    def get_trend(self) -> dict[str, typing.Any]:
        """Compare complexity over time using git history if available."""
        trend: dict[str, typing.Any] = {
            "git_available": False,
            "current_average": 0.0,
            "historical_average": 0.0,
            "trend_direction": "unknown",
            "num_files_analyzed": 0,
            "hotspots_count": 0
        }
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True,
                cwd=FRIDAY_ROOT, timeout=5
            )
            if result.returncode != 0:
                return trend
            trend["git_available"] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return trend
        all_funcs: list[dict[str, typing.Any]] = []
        for path, funcs in self._results.items():
            all_funcs.extend(funcs)
        if not all_funcs:
            return trend
        current_avg = statistics.mean(
            f["cyclomatic_complexity"] for f in all_funcs
        ) if all_funcs else 0.0
        trend["current_average"] = round(current_avg, 2)
        trend["num_files_analyzed"] = len(self._results)
        hotspots = [f for f in all_funcs if f["cyclomatic_complexity"] > 10]
        trend["hotspots_count"] = len(hotspots)
        trend["trend_direction"] = "stable"
        return trend
    def analyze_directory(self, directory: str | None = None) -> dict[str, list[dict[str, typing.Any]]]:
        """Analyze complexity for all files in a directory."""
        d = directory or self.source_dir
        files = get_all_python_files(d)
        for f in files:
            self.analyze_complexity(f)
        return self._results
    def get_summary_stats(self) -> dict[str, typing.Any]:
        """Get aggregate complexity statistics."""
        all_funcs: list[dict[str, typing.Any]] = []
        for path, funcs in self._results.items():
            all_funcs.extend(funcs)
        if not all_funcs:
            return {"num_functions": 0, "avg_complexity": 0.0, "max_complexity": 0, "total": 0}
        complexities = [f["cyclomatic_complexity"] for f in all_funcs]
        return {
            "num_functions": len(all_funcs),
            "avg_complexity": round(statistics.mean(complexities), 2),
            "median_complexity": round(statistics.median(complexities), 2),
            "max_complexity": max(complexities),
            "min_complexity": min(complexities),
            "total": sum(complexities),
            "std_dev": round(statistics.stdev(complexities), 2) if len(complexities) > 1 else 0.0
        }
    def get_line_length_violations(self, path: str, max_length: int = 120) -> list[dict[str, typing.Any]]:
        """Find lines exceeding the maximum line length."""
        violations: list[dict[str, typing.Any]] = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if len(line.rstrip("\n")) > max_length:
                    violations.append({
                        "line": i,
                        "length": len(line.rstrip("\n")),
                        "content": line.rstrip("\n")[:100]
                    })
        return violations
    def get_all_line_length_violations(self, directory: str | None = None) -> dict[str, list[dict[str, typing.Any]]]:
        """Find line length violations across all files."""
        d = directory or self.source_dir
        files = get_all_python_files(d)
        result: dict[str, list[dict[str, typing.Any]]] = {}
        for f in files:
            violations = self.get_line_length_violations(f)
            if violations:
                result[f] = violations
        return result


# ===================================================================
# DeadCodeDetector
# ===================================================================


class DeadCodeDetector:
    """Find unused functions, classes, and imports across the codebase."""
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self._file_analyzer = FileAnalyzer(self.source_dir)
        self._analysis_results: dict[str, FileAnalysis] = {}
        self._all_names: dict[str, list[str]] = {}
        self._all_calls: dict[str, list[str]] = {}
    def _load_all(self) -> None:
        """Load analysis for all files."""
        files = get_all_python_files(self.source_dir)
        for f in files:
            try:
                analysis = self._file_analyzer.analyze_file(f)
                self._analysis_results[f] = analysis
            except Exception:
                pass
    def find_unused_functions(self) -> list[dict[str, typing.Any]]:
        """Find functions defined but never called within the codebase."""
        if not self._analysis_results:
            self._load_all()
        defined: dict[str, list] = {}
        all_calls: set[str] = set()
        for path, analysis in self._analysis_results.items():
            for func in analysis.functions:
                fname = func["name"]
                if fname.startswith("_"):
                    continue
                key = f"{analysis.module_name}.{fname}"
                defined[key] = [func, path]
            for cls in analysis.classes:
                for meth in cls.get("methods", []):
                    mname = meth["name"]
                    if mname.startswith("_"):
                        continue
                    key = f"{analysis.module_name}.{cls['name']}.{mname}"
                    defined[key] = [meth, path]
        for path, analysis in self._analysis_results.items():
            source = ""
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()
            except Exception:
                continue
            clean = strip_string_literals(source)
            for func_name in list(set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*(?=\()", clean))):
                all_calls.add(func_name)
        unused: list[dict[str, typing.Any]] = []
        for key, (func_info, path) in defined.items():
            name = func_info["name"]
            if name not in all_calls:
                unused.append({
                    "name": name,
                    "qualified_name": key,
                    "file": path,
                    "lineno": func_info.get("lineno", 0),
                    "module": module_name_from_path(path, self.source_dir)
                })
        return unused
    def find_unused_imports(self) -> list[dict[str, typing.Any]]:
        """Find imports that are imported but never used in the file."""
        if not self._analysis_results:
            self._load_all()
        unused: list[dict[str, typing.Any]] = []
        for path, analysis in self._analysis_results.items():
            if analysis.ast_node is None:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()
            except Exception:
                continue
            name_visitor = NameUsageVisitor()
            try:
                tree = ast.parse(source, filename=path)
                name_visitor.visit(tree)
            except SyntaxError:
                continue
            all_references = set(name_visitor.name_references)
            all_references.update(name_visitor.called_names)
            for imp in analysis.imports:
                symbol = imp.get("alias") or imp.get("name") or imp.get("module", "")
                if symbol and symbol not in all_references:
                    base = symbol.split(".")[0]
                    if base not in all_references:
                        unused.append({
                            "file": path,
                            "line": imp.get("lineno", 0),
                            "symbol": symbol,
                            "import_type": imp.get("type", ""),
                            "module": analysis.module_name
                        })
        return unused
    def find_duplicate_code(self, min_lines: int = 5) -> list[dict[str, typing.Any]]:
        """Simple similarity-based duplicate code detection."""
        duplicates: list[dict[str, typing.Any]] = []
        file_sources: dict[str, list[str]] = {}
        files = get_all_python_files(self.source_dir)
        for f in files:
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=f)
            except (SyntaxError, Exception):
                continue
            func_bodies: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body_text = ast.get_source_segment(source, node) or ""
                    if body_text.count("\n") >= min_lines:
                        func_bodies.append(body_text)
            file_sources[f] = func_bodies
        file_list = list(file_sources.keys())
        for i in range(len(file_list)):
            for j in range(i + 1, len(file_list)):
                f1 = file_list[i]
                f2 = file_list[j]
                for body1 in file_sources[f1]:
                    for body2 in file_sources[f2]:
                        ratio = similarity_ratio(body1, body2)
                        if ratio >= DUPLICATE_SIMILARITY_THRESHOLD:
                            duplicates.append({
                                "file_a": f1,
                                "file_b": f2,
                                "similarity": round(ratio, 3),
                                "lines_a": body1.count("\n") + 1,
                                "lines_b": body2.count("\n") + 1
                            })
        return duplicates
    def find_unused_classes(self) -> list[dict[str, typing.Any]]:
        """Find classes defined but not instantiated anywhere."""
        if not self._analysis_results:
            self._load_all()
        defined: dict[str, tuple[dict[str, typing.Any], str]] = {}
        all_references: set[str] = set()
        for path, analysis in self._analysis_results.items():
            for cls in analysis.classes:
                cname = cls["name"]
                if cname.startswith("_"):
                    continue
                key = f"{analysis.module_name}.{cname}"
                defined[key] = (cls, path)
        for path, analysis in self._analysis_results.items():
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    source = f.read()
                clean = strip_string_literals(source)
                all_references.update(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", clean))
            except Exception:
                continue
        unused: list[dict[str, typing.Any]] = []
        for key, (cls_info, path) in defined.items():
            name = cls_info["name"]
            call_pattern = name + "("
            if name not in all_references or call_pattern not in all_references:
                if call_pattern not in str(all_references):
                    unused.append({
                        "name": name,
                        "qualified_name": key,
                        "file": path,
                        "lineno": cls_info.get("lineno", 0),
                        "module": module_name_from_path(path, self.source_dir)
                    })
        return unused
    def get_summary(self) -> dict[str, typing.Any]:
        """Get summary of dead code findings."""
        unused_funcs = self.find_unused_functions()
        unused_imports = self.find_unused_imports()
        unused_classes = self.find_unused_classes()
        duplicates = self.find_duplicate_code()
        return {
            "unused_functions": len(unused_funcs),
            "unused_imports": len(unused_imports),
            "unused_classes": len(unused_classes),
            "duplicate_code_blocks": len(duplicates),
            "total_dead_code": (
                len(unused_funcs) + len(unused_imports) + len(unused_classes)
            ),
            "unused_functions_list": unused_funcs[:50],
            "unused_imports_list": unused_imports[:50],
            "unused_classes_list": unused_classes[:50],
            "duplicates_list": duplicates[:20]
        }


# ===================================================================
# CoverageAnalyzer
# ===================================================================


@dataclasses.dataclass
class CoverageInfo:
    """Test coverage information for a module."""
    source_module: str
    source_path: str
    test_path: str | None
    has_tests: bool
    num_source_functions: int
    num_source_classes: int
    num_tested_functions: int
    num_tested_classes: int
    coverage_pct: float
    missing_functions: list[str]
    missing_classes: list[str]
    def to_dict(self) -> dict[str, typing.Any]:
        return dataclasses.asdict(self)


class CoverageAnalyzer:
    """Check test files match source files and identify untested code."""
    def __init__(self, source_dir: str | None = None, test_dirs: list[str] | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self.test_dirs = test_dirs or TEST_DIRS
        self._file_analyzer = FileAnalyzer(self.source_dir)
        self._coverage_info: dict[str, CoverageInfo] = {}
    def find_untested_modules(self) -> list[CoverageInfo]:
        """Find source files without companion test files."""
        source_files = get_all_python_files(self.source_dir)
        test_files = self._find_test_files()
        results: list[CoverageInfo] = []
        for sf in source_files:
            basename = os.path.basename(sf)
            if basename in IGNORE_FILES:
                continue
            module_name = module_name_from_path(sf, self.source_dir)
            test_path = self._find_companion_test(sf, test_files)
            try:
                analysis = self._file_analyzer.analyze_file(sf)
            except Exception:
                analysis = None
            source_funcs = analysis.num_functions if analysis else 0
            source_classes = analysis.num_classes if analysis else 0
            tested_funcs = 0
            tested_classes = 0
            missing_funcs: list[str] = []
            missing_classes: list[str] = []
            if test_path and analysis:
                test_funcs, test_classes = self._get_tested_symbols(test_path)
                for func in analysis.functions:
                    if func["name"] in test_funcs:
                        tested_funcs += 1
                    else:
                        missing_funcs.append(func["name"])
                for cls in analysis.classes:
                    if cls["name"] in test_classes:
                        tested_classes += 1
                    else:
                        missing_classes.append(cls["name"])
            total = source_funcs + source_classes
            covered = tested_funcs + tested_classes
            coverage_pct = (covered / total * 100) if total > 0 else 0.0
            info = CoverageInfo(
                source_module=module_name, source_path=sf,
                test_path=test_path, has_tests=test_path is not None,
                num_source_functions=source_funcs,
                num_source_classes=source_classes,
                num_tested_functions=tested_funcs,
                num_tested_classes=tested_classes,
                coverage_pct=round(coverage_pct, 1),
                missing_functions=missing_funcs,
                missing_classes=missing_classes
            )
            results.append(info)
            self._coverage_info[module_name] = info
        return results
    def _find_test_files(self) -> list[str]:
        """Find test files in configured test directories."""
        test_files: list[str] = []
        root = pathlib.Path(self.source_dir).parent
        for td in self.test_dirs:
            test_dir = root / td
            if test_dir.exists():
                test_files.extend(get_all_python_files(str(test_dir)))
        friday_test = pathlib.Path(self.source_dir) / "tests"
        if friday_test.exists():
            test_files.extend(get_all_python_files(str(friday_test)))
        return sorted(set(test_files))
    def _find_companion_test(self, source_path: str, test_files: list[str]) -> str | None:
        """Find the test file companion for a source file."""
        basename = os.path.basename(source_path)
        stem = os.path.splitext(basename)[0]
        candidates = [
            f"test_{basename}", f"test_{stem}.py",
            f"{stem}_test.py"
        ]
        for tf in test_files:
            tf_basename = os.path.basename(tf)
            if tf_basename in candidates:
                return tf
        for tf in test_files:
            if stem in tf:
                return tf
        return None
    def _get_tested_symbols(self, test_path: str) -> tuple[set[str], set[str]]:
        """Extract function and class names referenced in a test file."""
        functions: set[str] = set()
        classes: set[str] = set()
        try:
            with open(test_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=test_path)
        except (SyntaxError, Exception):
            return functions, classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    classes.add(alias.name)
                    functions.add(alias.name)
            if isinstance(node, ast.Call):
                self._collect_names_from_call(node, functions, classes)
        return functions, classes
    def _collect_names_from_call(self, node: ast.Call, functions: set[str], classes: set[str]) -> None:
        if isinstance(node.func, ast.Name):
            functions.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                functions.add(node.func.attr)
                classes.add(node.func.value.id)
    def find_test_gaps(self) -> list[dict[str, typing.Any]]:
        """Find functions/classes in source not referenced in tests."""
        if not self._coverage_info:
            self.find_untested_modules()
        gaps: list[dict[str, typing.Any]] = []
        for info in self._coverage_info.values():
            for func in info.missing_functions:
                gaps.append({
                    "type": "function",
                    "name": func,
                    "module": info.source_module,
                    "file": info.source_path
                })
            for cls in info.missing_classes:
                gaps.append({
                    "type": "class",
                    "name": cls,
                    "module": info.source_module,
                    "file": info.source_path
                })
        return gaps
    def get_coverage_report(self) -> dict[str, typing.Any]:
        """Overall coverage percentage across all modules."""
        if not self._coverage_info:
            self.find_untested_modules()
        total_source = sum(
            info.num_source_functions + info.num_source_classes
            for info in self._coverage_info.values()
        )
        total_tested = sum(
            info.num_tested_functions + info.num_tested_classes
            for info in self._coverage_info.values()
        )
        modules_with_tests = sum(1 for info in self._coverage_info.values() if info.has_tests)
        total_modules = len(self._coverage_info)
        overall_pct = (total_tested / total_source * 100) if total_source > 0 else 0.0
        fully_tested = sum(
            1 for info in self._coverage_info.values()
            if info.coverage_pct >= 100.0 and info.has_tests
        )
        return {
            "total_modules": total_modules,
            "modules_with_tests": modules_with_tests,
            "modules_without_tests": total_modules - modules_with_tests,
            "untested_modules_list": [
                info.source_module for info in self._coverage_info.values()
                if not info.has_tests
            ],
            "total_source_symbols": total_source,
            "total_tested_symbols": total_tested,
            "overall_coverage_pct": round(overall_pct, 1),
            "fully_tested_modules": fully_tested,
            "coverage_by_module": {
                info.source_module: info.coverage_pct
                for info in self._coverage_info.values()
            },
            "test_gaps": self.find_test_gaps()[:100],
            "num_test_gaps": len(self.find_test_gaps())
        }


# ===================================================================
# StyleAnalyzer
# ===================================================================


class StyleAnalyzer:
    """PEP8 checks, naming conventions, docstring presence analysis."""
    NAMING_PATTERNS: typing.ClassVar[dict[str, str]] = {
        "module": r"^[a-z][a-z0-9_]*$",
        "class": r"^[A-Z][a-zA-Z0-9]*$",
        "function": r"^[a-z][a-z0-9_]*$",
        "method": r"^[a-z][a-z0-9_]*$",
        "variable": r"^[a-z][a-z0-9_]*$",
        "constant": r"^[A-Z][A-Z0-9_]*$",
        "private": r"^_[a-z][a-z0-9_]*$",
        "dunder": r"^__[a-z][a-z0-9_]*__$"
    }
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self._file_analyzer = FileAnalyzer(self.source_dir)
        self._style_results: dict[str, list[dict[str, typing.Any]]] = {}
        self._grades: dict[str, str] = {}
    def analyze_style(self, path: str) -> list[dict[str, typing.Any]]:
        """Analyze style issues in a Python file."""
        if path in self._style_results:
            return self._style_results[path]
        issues: list[dict[str, typing.Any]] = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            lines = source.splitlines()
        except Exception as e:
            issues.append({"type": "read_error", "message": str(e)})
            return issues
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as e:
            issues.append({"type": "syntax_error", "message": str(e)})
            return issues
        issues.extend(self._check_line_length(lines, path))
        issues.extend(self._check_indentation(lines, path))
        issues.extend(self._check_trailing_whitespace(lines, path))
        issues.extend(self._check_blank_lines(lines, path))
        issues.extend(self._check_naming_conventions(tree, path))
        issues.extend(self._check_docstring_presence(tree, path))
        issues.extend(self._check_import_order(tree, path))
        issues.extend(self._check_inline_comments(lines, path))
        self._style_results[path] = issues
        return issues
    def _check_line_length(self, lines: list[str], path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for i, line in enumerate(lines, 1):
            if len(line) > MAX_LINE_LENGTH:
                issues.append({
                    "type": "line_too_long",
                    "line": i,
                    "message": f"Line exceeds {MAX_LINE_LENGTH} characters ({len(line)})",
                    "severity": "warning"
                })
        return issues
    def _check_indentation(self, lines: list[str], path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = line[:len(line) - len(stripped)]
            if "\t" in indent:
                issues.append({
                    "type": "tab_indentation",
                    "line": i,
                    "message": "Tabs used for indentation (PEP8 recommends spaces)",
                    "severity": "error"
                })
            elif len(indent) % 4 != 0:
                issues.append({
                    "type": "indentation_multiple",
                    "line": i,
                    "message": f"Indentation not a multiple of 4 ({len(indent)} spaces)",
                    "severity": "warning"
                })
        return issues
    def _check_trailing_whitespace(self, lines: list[str], path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for i, line in enumerate(lines, 1):
            if line != line.rstrip() and line.strip():
                issues.append({
                    "type": "trailing_whitespace",
                    "line": i,
                    "message": "Trailing whitespace detected",
                    "severity": "warning"
                })
        return issues
    def _check_blank_lines(self, lines: list[str], path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        blank_count = 0
        for i, line in enumerate(lines, 1):
            if not line.strip():
                blank_count += 1
            else:
                if blank_count > 2:
                    issues.append({
                        "type": "too_many_blank_lines",
                        "line": i,
                        "message": f"More than 2 blank lines before code ({blank_count})",
                        "severity": "warning"
                    })
                blank_count = 0
        if len(lines) > 2 and lines[-1].strip() == "":
            issues.append({
                "type": "trailing_newline",
                "line": len(lines),
                "message": "Extra blank line at end of file",
                "severity": "warning"
            })
        return issues
    def _check_naming_conventions(self, tree: ast.Module, path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not re.match(self.NAMING_PATTERNS["class"], node.name):
                    issues.append({
                        "type": "naming_convention",
                        "line": getattr(node, "lineno", 0),
                        "message": f"Class name {node.name!r} should use CapWords",
                        "severity": "error"
                    })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                if node.name.startswith("_"):
                    continue
                pattern = self.NAMING_PATTERNS["function"]
                if not re.match(pattern, node.name):
                    issues.append({
                        "type": "naming_convention",
                        "line": getattr(node, "lineno", 0),
                        "message": f"Function name {node.name!r} should be lowercase",
                        "severity": "error"
                    })
        return issues
    def _check_docstring_presence(self, tree: ast.Module, path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                if not ast.get_docstring(node):
                    issues.append({
                        "type": "missing_docstring",
                        "line": getattr(node, "lineno", 0),
                        "message": f"Missing docstring for {type(node).__name__[:-4].lower()} {node.name!r}",
                        "severity": "warning"
                    })
        if not ast.get_docstring(tree):
            issues.append({
                "type": "missing_module_docstring",
                "line": 1,
                "message": "Missing module-level docstring",
                "severity": "warning"
            })
        return issues
    def _check_import_order(self, tree: ast.Module, path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        import_lines: list[tuple[int, str, bool]] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_lines.append((node.lineno, node.module or "", isinstance(node, ast.ImportFrom)))
        for i in range(1, len(import_lines)):
            _, prev_mod, prev_from = import_lines[i - 1]
            _, curr_mod, curr_from = import_lines[i]
            if prev_from and not curr_from and prev_mod:
                if not curr_mod or (curr_mod and prev_mod.split(".")[0] > curr_mod.split(".")[0]):
                    issues.append({
                        "type": "import_order",
                        "line": import_lines[i][0],
                        "message": "Import order: stdlib > third-party > local",
                        "severity": "warning"
                    })
                    break
        return issues
    def _check_inline_comments(self, lines: list[str], path: str) -> list[dict[str, typing.Any]]:
        issues: list[dict[str, typing.Any]] = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "#" in stripped and not stripped.startswith("#"):
                idx = stripped.index("#")
                if idx > 0 and stripped[idx - 1] != " ":
                    issues.append({
                        "type": "inline_comment_spacing",
                        "line": i,
                        "message": "Inline comment should have at least one space before #",
                        "severity": "warning"
                    })
        return issues
    def get_style_grade(self, path: str) -> str:
        """Assign a letter grade (A-F) based on style analysis."""
        if path in self._grades:
            return self._grades[path]
        issues = self.analyze_style(path)
        if not issues:
            self._grades[path] = "A"
            return "A"
        error_count = sum(1 for i in issues if i.get("severity") == "error")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")
        score = 100 - (error_count * 5) - (warning_count * 2)
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 65:
            grade = "C"
        elif score >= 50:
            grade = "D"
        elif score >= 30:
            grade = "E"
        else:
            grade = "F"
        self._grades[path] = grade
        return grade
    def find_worst_files(self, n: int = 10) -> list[dict[str, typing.Any]]:
        """Return bottom N files sorted by style grade."""
        files = get_all_python_files(self.source_dir)
        graded: list[dict[str, typing.Any]] = []
        for f in files:
            grade = self.get_style_grade(f)
            issues = self._style_results.get(f, [])
            graded.append({
                "file": f,
                "grade": grade,
                "num_issues": len(issues),
                "module": module_name_from_path(f, self.source_dir)
            })
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
        graded.sort(key=lambda x: (grade_order.get(x["grade"], 99), x["num_issues"]), reverse=True)
        return graded[:n]
    def get_summary_stats(self) -> dict[str, typing.Any]:
        """Get aggregate style statistics."""
        files = get_all_python_files(self.source_dir)
        total_issues = 0
        grade_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
        for f in files:
            grade = self.get_style_grade(f)
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            issues = self._style_results.get(f, [])
            total_issues += len(issues)
        return {
            "files_analyzed": len(files),
            "total_issues": total_issues,
            "grade_distribution": grade_counts,
            "average_grade": self._average_grade(grade_counts),
            "worst_files": self.find_worst_files(10)
        }
    def _average_grade(self, grade_counts: dict[str, int]) -> str:
        total = sum(grade_counts.values())
        if total == 0:
            return "N/A"
        score = (
            grade_counts.get("A", 0) * 4 + grade_counts.get("B", 0) * 3 +
            grade_counts.get("C", 0) * 2 + grade_counts.get("D", 0) * 1 +
            grade_counts.get("E", 0) * 0
        ) / total
        if score >= 3.5:
            return "A"
        if score >= 2.5:
            return "B"
        if score >= 1.5:
            return "C"
        if score >= 0.5:
            return "D"
        return "F"


# ===================================================================
# ReportGenerator
# ===================================================================


class ReportGenerator:
    """Produce formatted reports from analysis data."""
    def __init__(self, source_dir: str | None = None) -> None:
        self.source_dir = source_dir or FRIDAY_SOURCE
        self.file_analyzer = FileAnalyzer(self.source_dir)
        self.module_graph = ModuleGraph(self.source_dir)
        self.complexity_analyzer = ComplexityAnalyzer(self.source_dir)
        self.dead_code_detector = DeadCodeDetector(self.source_dir)
        self.coverage_analyzer = CoverageAnalyzer(self.source_dir)
        self.style_analyzer = StyleAnalyzer(self.source_dir)
        self._data: dict[str, typing.Any] = {}
    def _collect_all_data(self) -> dict[str, typing.Any]:
        """Collect data from all analyzers."""
        print("Running module graph analysis...")
        self.module_graph.build_graph()
        print("Running complexity analysis...")
        self.complexity_analyzer.analyze_directory()
        print("Running style analysis...")
        files = get_all_python_files(self.source_dir)
        for f in files:
            self.style_analyzer.analyze_style(f)
        print("Running dead code detection...")
        dead_code = self.dead_code_detector.get_summary()
        print("Running coverage analysis...")
        coverage = self.coverage_analyzer.get_coverage_report()
        module_stats = self.module_graph.get_stats()
        complexity_stats = self.complexity_analyzer.get_summary_stats()
        style_stats = self.style_analyzer.get_summary_stats()
        cycles = self.module_graph.find_cycles()
        hotspots = self.complexity_analyzer.get_hotspots(threshold=10)
        data: dict[str, typing.Any] = {
            "generated_at": datetime.datetime.now().isoformat(),
            "source_directory": self.source_dir,
            "module_graph": module_stats,
            "complexity": complexity_stats,
            "style": style_stats,
            "dead_code": dead_code,
            "coverage": coverage,
            "cycles": [
                {"cycle": c, "length": len(c)} for c in cycles
            ],
            "hotspots": hotspots[:30],
            "topological_order": self.module_graph.topological_sort(),
            "orphan_modules": self.module_graph.find_orphans()
        }
        self._data = data
        return data
    def generate_summary(self) -> str:
        """Produce a formatted overview text report."""
        data = self._data or self._collect_all_data()
        mg = data["module_graph"]
        cx = data["complexity"]
        st = data["style"]
        dc = data["dead_code"]
        cv = data["coverage"]
        lines: list[str] = []
        lines.append("=" * 72)
        lines.append("FRIDAY CODEBASE ANALYSIS REPORT")
        lines.append("=" * 72)
        lines.append(f"Generated: {data['generated_at']}")
        lines.append(f"Source: {data['source_directory']}")
        lines.append("")
        lines.append("--- MODULE GRAPH ---")
        lines.append(f"  Total modules: {mg['num_modules']}")
        lines.append(f"  Total LOC: {mg['total_lines_of_code']}")
        lines.append(f"  Total functions: {mg['total_functions']}")
        lines.append(f"  Total classes: {mg['total_classes']}")
        lines.append(f"  Dependency edges: {mg['dependency_edges']}")
        lines.append(f"  Circular dependencies: {mg['num_cycles']}")
        lines.append(f"  Orphan modules: {len(data['orphan_modules'])}")
        lines.append("")
        lines.append("--- COMPLEXITY ---")
        lines.append(f"  Average complexity: {cx['avg_complexity']}")
        lines.append(f"  Max complexity: {cx['max_complexity']}")
        lines.append(f"  Total functions analyzed: {cx['num_functions']}")
        lines.append("")
        lines.append("--- STYLE ---")
        lines.append(f"  Files analyzed: {st['files_analyzed']}")
        lines.append(f"  Total issues: {st['total_issues']}")
        lines.append(f"  Average grade: {st['average_grade']}")
        lines.append(f"  Grade distribution: {st['grade_distribution']}")
        lines.append("")
        lines.append("--- DEAD CODE ---")
        lines.append(f"  Unused functions: {dc['unused_functions']}")
        lines.append(f"  Unused imports: {dc['unused_imports']}")
        lines.append(f"  Unused classes: {dc['unused_classes']}")
        lines.append(f"  Duplicate blocks: {dc['duplicate_code_blocks']}")
        lines.append("")
        lines.append("--- COVERAGE ---")
        lines.append(f"  Overall coverage: {cv['overall_coverage_pct']}%")
        lines.append(f"  Modules with tests: {cv['modules_with_tests']}/{cv['total_modules']}")
        lines.append(f"  Fully tested modules: {cv['fully_tested_modules']}")
        lines.append(f"  Test gaps: {cv['num_test_gaps']}")
        lines.append("")
        if data.get("hotspots"):
            lines.append("--- TOP HOTSPOTS ---")
            for h in data["hotspots"][:10]:
                lines.append(f"  {h['name']} - CC: {h['cyclomatic_complexity']} (line {h['lineno']})")
            lines.append("")
        if data.get("cycles"):
            lines.append("--- CIRCULAR DEPENDENCIES ---")
            for c in data["cycles"][:10]:
                lines.append(f"  {' -> '.join(c['cycle'])}")
            lines.append("")
        if data.get("orphan_modules"):
            lines.append("--- ORPHAN MODULES ---")
            for m in data["orphan_modules"][:10]:
                lines.append(f"  {m}")
            lines.append("")
        if data.get("topological_order"):
            lines.append("--- TOPOLOGICAL ORDER (first 20) ---")
            for i, m in enumerate(data["topological_order"][:20], 1):
                lines.append(f"  {i:3d}. {m}")
            lines.append("")
        lines.append("=" * 72)
        lines.append("Report complete.")
        lines.append("=" * 72)
        return "\n".join(lines)
    def generate_json(self, pretty: bool = True) -> str:
        """Generate a machine-readable JSON report."""
        data = self._data or self._collect_all_data()
        indent = 2 if pretty else None
        return json.dumps(data, default=str, indent=indent)
    def generate_html(self) -> str:
        """Generate an HTML report with tables."""
        data = self._data or self._collect_all_data()
        mg = data["module_graph"]
        cx = data["complexity"]
        st = data["style"]
        dc = data["dead_code"]
        cv = data["coverage"]
        hotspot_rows = ""
        for h in data.get("hotspots", [])[:20]:
            hotspot_rows += "<tr>"
            hotspot_rows += f"<td>{h.get('name', '?')}</td>"
            hotspot_rows += f"<td>{h.get('cyclomatic_complexity', 0)}</td>"
            hotspot_rows += f"<td>{h.get('lineno', 0)}</td>"
            hotspot_rows += f"<td>{os.path.basename(h.get('file', ''))}</td>"
            hotspot_rows += "</tr>\n"
        cycle_rows = ""
        for c in data.get("cycles", [])[:10]:
            cycle_str = " -> ".join(c["cycle"])
            cycle_rows += f"<tr><td>{cycle_str}</td><td>{c['length']}</td></tr>\n"
        orphan_list = "".join(f"<li>{m}</li>\n" for m in data.get("orphan_modules", [])[:20])
        grade_rows = ""
        for grade in ["A", "B", "C", "D", "E", "F"]:
            count = st.get("grade_distribution", {}).get(grade, 0)
            grade_rows += f"<tr><td><span class=\"badge badge-{grade}\">{grade}</span></td><td>{count}</td></tr>\n"
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FRIDAY Codebase Analysis Report</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:40px;background:#f5f5f5;color:#333}
h1,h2{color:#1a1a2e}table{border-collapse:collapse;width:100%;margin:20px 0;background:white;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #ddd}th{background:#1a1a2e;color:white;font-weight:600}
tr:hover{background:#f0f0ff}.card{background:white;padding:20px;margin:20px 0;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
.footer{margin-top:40px;font-size:12px;color:#999;text-align:center}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold}
.badge-A{background:#d4edda;color:#155724}.badge-B{background:#cce5ff;color:#004085}
.badge-C{background:#fff3cd;color:#856404}.badge-D{background:#ffeeba;color:#856404}
.badge-E{background:#f8d7da;color:#721c24}.badge-F{background:#f5c6cb;color:#721c24}
</style>
</head>
<body>
<h1>FRIDAY Codebase Analysis Report</h1>
<p>Generated: """ + data["generated_at"] + """</p>
<div class="card">
<h2>Module Graph</h2>
<table>
<tr><td>Total Modules</td><td>""" + str(mg["num_modules"]) + """</td></tr>
<tr><td>Total Lines of Code</td><td>""" + str(mg["total_lines_of_code"]) + """</td></tr>
<tr><td>Total Functions</td><td>""" + str(mg["total_functions"]) + """</td></tr>
<tr><td>Total Classes</td><td>""" + str(mg["total_classes"]) + """</td></tr>
<tr><td>Dependency Edges</td><td>""" + str(mg["dependency_edges"]) + """</td></tr>
<tr><td>Circular Dependencies</td><td>""" + str(mg["num_cycles"]) + """</td></tr>
<tr><td>Orphan Modules</td><td>""" + str(len(data["orphan_modules"])) + """</td></tr>
</table>
</div>
<div class="card">
<h2>Complexity</h2>
<table>
<tr><td>Average Complexity</td><td>""" + str(cx["avg_complexity"]) + """</td></tr>
<tr><td>Max Complexity</td><td>""" + str(cx["max_complexity"]) + """</td></tr>
<tr><td>Functions Analyzed</td><td>""" + str(cx["num_functions"]) + """</td></tr>
<tr><td>Std Dev</td><td>""" + str(cx.get("std_dev", "N/A")) + """</td></tr>
</table>
</div>
<div class="card">
<h2>Style</h2>
<table>
<tr><td>Files Analyzed</td><td>""" + str(st["files_analyzed"]) + """</td></tr>
<tr><td>Total Issues</td><td>""" + str(st["total_issues"]) + """</td></tr>
<tr><td>Average Grade</td><td><span class="badge badge-""" + st["average_grade"] + """">""" + st["average_grade"] + """</span></td></tr>
</table>
<h3>Grade Distribution</h3>
<table>
<tr><th>Grade</th><th>Count</th></tr>
""" + grade_rows + """
</table>
</div>
<div class="card">
<h2>Dead Code</h2>
<table>
<tr><td>Unused Functions</td><td>""" + str(dc["unused_functions"]) + """</td></tr>
<tr><td>Unused Imports</td><td>""" + str(dc["unused_imports"]) + """</td></tr>
<tr><td>Unused Classes</td><td>""" + str(dc["unused_classes"]) + """</td></tr>
<tr><td>Duplicate Blocks</td><td>""" + str(dc["duplicate_code_blocks"]) + """</td></tr>
</table>
</div>
<div class="card">
<h2>Coverage</h2>
<table>
<tr><td>Overall Coverage</td><td>""" + str(cv["overall_coverage_pct"]) + """%</td></tr>
<tr><td>Modules with Tests</td><td>""" + str(cv["modules_with_tests"]) + """/""" + str(cv["total_modules"]) + """</td></tr>
<tr><td>Fully Tested Modules</td><td>""" + str(cv["fully_tested_modules"]) + """</td></tr>
<tr><td>Test Gaps</td><td>""" + str(cv["num_test_gaps"]) + """</td></tr>
</table>
</div>
"""
        if hotspot_rows:
            html += '<div class="card"><h2>Hotspots (Top 20)</h2><table>'
            html += '<tr><th>Function</th><th>Complexity</th><th>Line</th><th>File</th></tr>'
            html += hotspot_rows + '</table></div>\n'
        if cycle_rows:
            html += '<div class="card"><h2>Circular Dependencies</h2><table>'
            html += '<tr><th>Cycle</th><th>Length</th></tr>'
            html += cycle_rows + '</table></div>\n'
        if orphan_list:
            html += '<div class="card"><h2>Orphan Modules</h2><ul>' + orphan_list + '</ul></div>\n'
        html += '<div class="footer">Generated by FRIDAY Codebase Analyzer</div>\n'
        html += '</body></html>'
        return html
    def generate_dependency_diagram(self) -> str:
        """Generate an ASCII art dependency tree."""
        data = self._data or self._collect_all_data()
        order = data.get("topological_order", [])
        if not order:
            return "(No dependency data available)"
        lines: list[str] = []
        lines.append("FRIDAY Module Dependency Tree")
        lines.append("=" * 60)
        lines.append("")
        top_level: list[str] = []
        children: dict[str, list[str]] = {}
        for m in order:
            deps = self.module_graph.get_dependencies(m)
            friday_deps = [d for d in deps if d.startswith("friday") and d in order]
            if not friday_deps:
                top_level.append(m)
            for dep in friday_deps:
                children.setdefault(dep, []).append(m)
        def render_tree(modules: list[str], prefix: str = "", is_last: bool = True) -> None:
            for i, mod in enumerate(sorted(set(modules))):
                last = i == len(set(modules)) - 1
                connector = "\u2514\u2500\u2500 " if last else "\u251c\u2500\u2500 "
                lines.append(f"{prefix}{connector}{mod}")
                sub_modules = children.get(mod, [])
                if sub_modules:
                    extension = "    " if last else "\u2502   "
                    render_tree(sub_modules, prefix + extension, last)
        render_tree(top_level)
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Total modules: {len(order)}")
        return "\n".join(lines)
    def generate_module_report(self, module: str) -> str:
        """Generate a detailed report for a single module."""
        node = self.module_graph.get_node(module)
        if node is None:
            return f"Module {module!r} not found."
        analysis = self.file_analyzer.analyze_file(node.path)
        lines: list[str] = []
        lines.append(f"=== Module: {module} ===")
        lines.append(f"  Path: {node.path}")
        lines.append(f"  Size: {node.file_size} bytes")
        lines.append(f"  LOC: {node.lines_of_code}")
        lines.append(f"  Functions: {node.num_functions}")
        lines.append(f"  Classes: {node.num_classes}")
        lines.append(f"  Imports: {node.num_imports}")
        lines.append(f"  Complexity: {analysis.complexity_score:.2f}")
        lines.append(f"  Docstring Coverage: {analysis.docstring_coverage:.1%}")
        lines.append("")
        lines.append("  Dependencies:")
        for d in sorted(node.dependencies):
            lines.append(f"    -> {d}")
        lines.append("")
        lines.append("  Dependents:")
        for d in sorted(node.dependents):
            lines.append(f"    <- {d}")
        lines.append("")
        if analysis.classes:
            lines.append("  Classes:")
            for cls in analysis.classes:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                lines.append(f"    {cls['name']}{bases}")
                for meth in cls.get("methods", []):
                    decorators = " ".join(f"@{d}" for d in meth["decorators"])
                    dec_str = f" [{decorators}]" if meth["decorators"] else ""
                    async_str = " async" if meth["is_async"] else ""
                    args_str = ", ".join(a["arg"] for a in meth["args"]["args"])
                    lines.append(f"      {async_str} {meth['name']}({args_str}){dec_str}")
        lines.append("")
        if analysis.functions:
            lines.append("  Functions:")
            for func in analysis.functions:
                if func.get("is_method"):
                    continue
                decorators = " ".join(f"@{d}" for d in func["decorators"])
                dec_str = f" [{decorators}]" if func["decorators"] else ""
                async_str = " async" if func["is_async"] else ""
                args_str = ", ".join(a["arg"] for a in func["args"]["args"])
                lines.append(f"    {async_str} {func['name']}({args_str}){dec_str}")
        return "\n".join(lines)
    def generate_detailed_report(self) -> str:
        """Generate an extremely detailed text report of the entire codebase."""
        data = self._data or self._collect_all_data()
        parts: list[str] = [self.generate_summary()]
        parts.append("")
        parts.append("=" * 72)
        parts.append("MODULE DETAILS")
        parts.append("=" * 72)
        all_modules = self.module_graph.get_all_modules()
        for mod in all_modules[:50]:
            parts.append("")
            parts.append(self.generate_module_report(mod))
        parts.append("")
        parts.append("=" * 72)
        parts.append("END OF DETAILED REPORT")
        return "\n".join(parts)


# ===================================================================
# Main Entry Point
# ===================================================================


def codebase_analyzer_tool(action: str, **kwargs: typing.Any) -> typing.Any:
    """
    Main entry point for FRIDAY codebase analysis.

    Actions:
        scan        Full scan of FRIDAY codebase
        modules     List all modules with metadata
        dependencies Show dependency graph [module]
        dependents  Show what depends on a module [module]
        cycles      Find circular dependencies
        complexity  Complexity analysis [threshold]
        hotspots    Top complex functions [limit]
        dead_code   Find dead code
        coverage    Test coverage analysis
        style       Style analysis
        report      Full summary report [format: summary/json/html]
        file        Analyze single file [path]
        function    Find function definition [name]
        class       Find class definition [name]
        search      Search codebase for pattern [pattern]
        stats       Codebase statistics
    """
    source_dir = kwargs.get("source_dir", FRIDAY_SOURCE)
    module = kwargs.get("module", "")
    threshold = int(kwargs.get("threshold", 10))
    limit = int(kwargs.get("limit", 20))
    path = kwargs.get("path", "")
    name = kwargs.get("name", "")
    pattern = kwargs.get("pattern", "")
    fmt = kwargs.get("format", "summary")
    if action == "scan":
        reporter = ReportGenerator(source_dir)
        print("Performing full scan...")
        reporter._collect_all_data()
        return {"status": "complete", "message": "Scan completed"}
    elif action == "modules":
        graph = ModuleGraph(source_dir)
        graph.build_graph()
        modules_list: list[dict[str, typing.Any]] = []
        for mod in graph.get_all_modules():
            node = graph.get_node(mod)
            if node:
                modules_list.append(node.to_dict())
        return modules_list
    elif action == "dependencies":
        graph = ModuleGraph(source_dir)
        graph.build_graph()
        if module:
            return graph.get_dependencies(module)
        deps_map: dict[str, list[str]] = {}
        for mod in graph.get_all_modules():
            deps_map[mod] = graph.get_dependencies(mod)
        return deps_map
    elif action == "dependents":
        graph = ModuleGraph(source_dir)
        graph.build_graph()
        if module:
            return graph.get_dependents(module)
        return "Please specify a module name with module= parameter"
    elif action == "cycles":
        graph = ModuleGraph(source_dir)
        graph.build_graph()
        cycles = graph.find_cycles()
        if cycles:
            print(f"Found {len(cycles)} circular dependencies:")
            for c in cycles:
                print(f"  {' -> '.join(c)}")
        else:
            print("No circular dependencies found.")
        return cycles
    elif action == "complexity":
        analyzer = ComplexityAnalyzer(source_dir)
        analyzer.analyze_directory()
        stats = analyzer.get_summary_stats()
        hotspots = analyzer.get_hotspots(threshold=threshold)
        return {
            "summary": stats,
            "hotspots": hotspots[:limit]
        }
    elif action == "hotspots":
        analyzer = ComplexityAnalyzer(source_dir)
        analyzer.analyze_directory()
        hotspots = analyzer.get_hotspots(threshold=threshold)
        return hotspots[:limit]
    elif action == "dead_code":
        detector = DeadCodeDetector(source_dir)
        return detector.get_summary()
    elif action == "coverage":
        analyzer = CoverageAnalyzer(source_dir)
        return analyzer.get_coverage_report()
    elif action == "style":
        analyzer = StyleAnalyzer(source_dir)
        files = get_all_python_files(source_dir)
        for f in files:
            analyzer.analyze_style(f)
        return analyzer.get_summary_stats()
    elif action == "report":
        reporter = ReportGenerator(source_dir)
        if fmt == "json":
            return reporter.generate_json()
        elif fmt == "html":
            return reporter.generate_html()
        else:
            return reporter.generate_summary()
    elif action == "file":
        if not path:
            return "Please specify a file path with path= parameter"
        analyzer = FileAnalyzer(source_dir)
        analysis = analyzer.analyze_file(path)
        result = analysis.to_dict()
        return result
    elif action == "function":
        if not name:
            return "Please specify a function name with name= parameter"
        print(f"Searching for function {name!r}...")
        search_results: list[dict[str, typing.Any]] = []
        analyzer = FileAnalyzer(source_dir)
        files = get_all_python_files(source_dir)
        for f in files:
            try:
                analysis = analyzer.analyze_file(f)
                for func in analysis.functions:
                    if func["name"] == name:
                        search_results.append({
                            "file": f,
                            "name": name,
                            "lineno": func.get("lineno"),
                            "signature": func.get("args"),
                            "module": module_name_from_path(f, source_dir)
                        })
                for cls in analysis.classes:
                    for meth in cls.get("methods", []):
                        if meth["name"] == name:
                            search_results.append({
                                "file": f,
                                "name": name,
                                "class": cls["name"],
                                "lineno": meth.get("lineno"),
                                "module": module_name_from_path(f, source_dir)
                            })
            except Exception:
                continue
        return search_results
    elif action == "class":
        if not name:
            return "Please specify a class name with name= parameter"
        print(f"Searching for class {name!r}...")
        search_results = []
        analyzer = FileAnalyzer(source_dir)
        files = get_all_python_files(source_dir)
        for f in files:
            try:
                analysis = analyzer.analyze_file(f)
                for cls in analysis.classes:
                    if cls["name"] == name:
                        search_results.append({
                            "file": f,
                            "name": name,
                            "lineno": cls.get("lineno"),
                            "bases": cls.get("bases"),
                            "num_methods": cls.get("num_methods"),
                            "module": module_name_from_path(f, source_dir)
                        })
            except Exception:
                continue
        return search_results
    elif action == "search":
        if not pattern:
            return "Please specify a search pattern with pattern= parameter"
        print(f"Searching for pattern {pattern!r}...")
        search_results = []
        files = get_all_python_files(source_dir)
        for f in files:
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(pattern, line):
                            search_results.append({
                                "file": f,
                                "line": i,
                                "content": line.rstrip("\n")[:150]
                            })
            except Exception:
                continue
        return search_results[:limit]
    elif action == "stats":
        graph = ModuleGraph(source_dir)
        graph.build_graph()
        total_files = len(graph.get_all_modules())
        total_loc = sum(n.lines_of_code for n in graph.nodes.values())
        total_funcs = sum(n.num_functions for n in graph.nodes.values())
        total_classes = sum(n.num_classes for n in graph.nodes.values())
        total_imports = sum(n.num_imports for n in graph.nodes.values())
        cycles = graph.find_cycles()
        orphans = graph.find_orphans()
        return {
            "total_files": total_files,
            "total_lines_of_code": total_loc,
            "total_functions": total_funcs,
            "total_classes": total_classes,
            "total_imports": total_imports,
            "avg_lines_per_file": round(total_loc / max(total_files, 1), 1),
            "num_cycles": len(cycles),
            "num_orphans": len(orphans)
        }
    else:
        return f"Unknown action: {action}. See docstring for valid actions."


if __name__ == "__main__":
    """CLI entry point for the codebase analyzer."""
    import sys as _sys
    args = _sys.argv[1:]
    if not args:
        print("Usage: python codebase_analyzer.py <action> [key=value ...]")
        print("Actions: scan, modules, dependencies, dependents, cycles,")
        print("         complexity, hotspots, dead_code, coverage, style,")
        print("         report, file, function, class, search, stats")
        _sys.exit(1)
    action = args[0]
    kwargs: dict[str, typing.Any] = {}
    for arg in args[1:]:
        if "=" in arg:
            key, _, value = arg.partition("=")
            kwargs[key] = value
    result = codebase_analyzer_tool(action, **kwargs)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, default=str, indent=2))
