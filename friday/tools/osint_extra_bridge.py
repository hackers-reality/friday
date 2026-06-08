"""
Dynamic bridge to register all ~460 osint_extra functions as Google FunctionDeclaration tools.
Uses AST introspection — no module import, zero-cost loading.
"""
import ast
from typing import Any

OSINT_EXTRA_PATH = None  # lazy-loaded

def _get_osint_extra_path() -> str:
    global OSINT_EXTRA_PATH
    if OSINT_EXTRA_PATH is None:
        from friday.paths import get_osint_extra_path
        OSINT_EXTRA_PATH = str(get_osint_extra_path())
    return OSINT_EXTRA_PATH

_OSINT_FUNCTIONS: list[dict[str, Any]] | None = None

PYTYPE_MAP = {
    "str": "STRING", "int": "INTEGER", "float": "NUMBER",
    "bool": "BOOLEAN", "list": "ARRAY", "dict": "OBJECT",
    "tuple": "ARRAY", "Any": "STRING", "None": "STRING",
}


def _pytype_to_schema(raw: str) -> str:
    clean = raw.replace("Optional[", "").rstrip("]")
    clean = clean.replace("List[", "").replace("Dict[", "").replace("Tuple[", "")
    clean = clean.replace("Set[", "").split("[")[0].split(" | ")[0].split(" ")[0]
    return PYTYPE_MAP.get(clean.strip(), "STRING")


def _get_type_from_annotation(annotation) -> str:
    if annotation is None:
        return "STRING"
    if isinstance(annotation, ast.Name):
        return _pytype_to_schema(annotation.id)
    if isinstance(annotation, ast.Constant) and annotation.value:
        return _pytype_to_schema(str(annotation.value))
    return "STRING"


def _parse_osint_functions() -> list[dict[str, Any]]:
    path = _get_osint_extra_path()
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    seen = set()
    funcs = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = node.name
        if name.startswith("_") or name in seen:
            continue
        seen.add(name)
        params = {}
        required = []
        n_defaults = len(node.args.defaults)
        all_args = node.args.args
        n_required = len(all_args) - n_defaults
        for i, arg in enumerate(all_args):
            params[arg.arg] = {
                "type": _get_type_from_annotation(arg.annotation),
                "description": "",
            }
            if i < n_required and arg.arg != "self":
                required.append(arg.arg)
        doc = (ast.get_docstring(node) or "").replace("\n", " ")[:200]
        funcs.append({
            "name": name,
            "description": doc or f"OSINT: {name}",
            "params": params,
            "required": required or None,
        })
    return funcs


def get_osint_functions() -> list[dict[str, Any]]:
    global _OSINT_FUNCTIONS
    if _OSINT_FUNCTIONS is None:
        _OSINT_FUNCTIONS = _parse_osint_functions()
    return _OSINT_FUNCTIONS


def build_osint_extra_tools(types_module) -> list:
    declarations = []
    for func in get_osint_functions():
        schema = None
        if func["params"]:
            schema = types_module.Schema(
                type="OBJECT",
                properties={p: types_module.Schema(type=t["type"], description=t["description"])
                            for p, t in func["params"].items()},
                required=func.get("required") or [],
            )
        declarations.append(
            types_module.FunctionDeclaration(name=func["name"], description=func["description"], parameters=schema)
        )
    return declarations


def build_osint_extra_tool_map() -> dict[str, Any]:
    from friday.tools.registry import _LazyToolFunc
    return {func["name"]: _LazyToolFunc("friday.tools_osint_extra", func["name"])
            for func in get_osint_functions()}
