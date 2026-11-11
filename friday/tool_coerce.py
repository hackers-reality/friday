"""Shared argument binding & coercion for FRIDAY's tool dispatch paths.

Two paths call ``func(**args)`` with whatever the LLM emitted:
  - ``friday.live._invoke_tool`` — direct TOOL_MAP dispatch
  - ``friday.tools.registry._LazyToolFunc`` — lazy registry dispatch

Voice models send numbers as strings (``"5"`` for ``int``) and invent kwargs.
Both paths now bind args against the signature and coerce primitives instead of
crashing with ``TypeError: '<' not supported between instances of 'int' and 'str'``.

Rules:
  - ``int`` / ``float`` / ``bool`` params accept numeric strings / bool-ish strings.
  - ``list[X]`` / ``dict`` params accept JSON-string input.
  - ``Optional[X]`` unwraps to X. ``Any`` / missing annotation is left alone.
  - ``None``-valued params are dropped (an omitted optional beats an explicit null).
  - Unknown kwargs are dropped and logged (unless the function takes ``**kwargs``).
  - Coercion never raises — a value that fails conversion is passed through unchanged.
"""

from __future__ import annotations

import ast
import inspect
import json
import logging

_log = logging.getLogger("friday.tool_coerce")

_INT_STR_OK = (int,)
_FLOAT_STR_OK = (int, float)
_TRUE_STRINGS = {"true", "1", "yes", "on", "y"}
_FALSE_STRINGS = {"false", "0", "no", "off", "n", ""}


_STR_ANN_MAP = {
    "int": int, "float": float, "bool": bool, "str": str, "bytes": bytes,
    "list": list, "List": list, "tuple": tuple, "Tuple": tuple,
    "dict": dict, "Dict": dict, "bool": bool,
    "Any": None, "any": None,
}


def _unwrap_optional(ann):
    if ann is inspect.Parameter.empty:
        return None
    if isinstance(ann, str):
        s = ann.replace(" ", "").replace("typing.", "")
        if s.startswith(("Optional[", "Union[")):
            inner = s[s.index("[") + 1:-1].split(",")[0]
            return _unwrap_optional(inner)
        return _STR_ANN_MAP.get(s, None)
    origin = getattr(ann, "__origin__", None)
    if origin is not None:
        try:
            args = [a for a in inspect.get_args(ann) if a is not type(None)]
        except Exception:
            return None
        return args[0] if len(args) == 1 else None
    return ann


def _ann_origin(ann):
    if isinstance(ann, str):
        s = ann.replace(" ", "").replace("typing.", "")
        if s.startswith(("Optional[", "Union[")):
            s = s[s.index("[") + 1:-1].split(",")[0]
        if s.startswith(("list", "List", "tuple", "Tuple")):
            return list
        if s.startswith(("dict", "Dict")):
            return dict
        return None
    return getattr(ann, "__origin__", None)


def _to_int(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if float(v).is_integer() else v
    if isinstance(v, str):
        s = v.strip()
        try:
            return int(s)
        except ValueError:
            try:
                f = float(s)
                return int(f) if f.is_integer() else v
            except ValueError:
                return v
    return v


def _to_float(v):
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return v
    return v


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return False
        return v
    return v


def _to_jsonish(v):
    if isinstance(v, str):
        s = v.strip()
        if s and s[0] in "[{":
            try:
                return json.loads(s)
            except Exception:
                return v
    return v


def _coerce_ann(value, annotation):
    if value is None:
        return None
    ann = _unwrap_optional(annotation)
    origin = _ann_origin(ann) if ann is not None else None

    if ann is None or ann is inspect.Parameter.empty:
        # No usable annotation — but try obvious numeric/bool strings only when asked
        return value

    base = ann if ann is not None else None

    if ann is int:
        return _to_int(value)
    if ann is float:
        return _to_float(value)
    if ann is bool:
        return _to_bool(value)
    if ann is str or ann is bytes:
        return value

    if origin in (list, tuple):
        return _to_jsonish(value) if isinstance(value, str) else value
    if origin is dict or ann is dict:
        return _to_jsonish(value) if isinstance(value, str) else value
    return value


def coerce_args(func, args):
    """Bind ``args`` against ``func``'s signature, coercing primitives.

    Returns a new dict. Unknown kwargs are dropped (logged) unless the function
    takes ``**kwargs``. ``None``-valued params are dropped unless they have no
    default and no ``**kwargs`` headroom (so the caller gets the normal missing-
    argument error instead of silent None leakage into Google API params).
    """
    if not isinstance(args, dict):
        args = dict(args) if args else {}
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return args

    params = sig.parameters
    var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    out = {}
    for name, param in params.items():
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        if name in args:
            out[name] = _coerce_ann(args[name], param.annotation)

    # Drop None-valued params (explicit nulls)
    dropped_none = [k for k, v in out.items() if v is None]
    for k in dropped_none:
        param = params[k]
        if param.default is inspect.Parameter.empty and not var_kw:
            # Required param passed as null — keep it so the caller errors clearly
            continue
        out.pop(k)
    if dropped_none:
        _log.debug("[tool_coerce] dropped null params for %s: %s", getattr(func, "__qualname__", func), dropped_none)

    if var_kw:
        for k, v in args.items():
            if k not in out:
                out[k] = v
    else:
        unknown = [k for k in args if k not in out and k not in params]
        if unknown:
            _log.info("[tool_coerce] dropping unknown kwargs for %s: %s",
                      getattr(func, "__qualname__", func), unknown)
    return out


# ─── Schema generation (shared with tools/registry.build_new_tools) ──────────

_FILE_AST_CACHE: dict[str, object] = {}


def _parse_file(target):
    key = str(target)
    cached = _FILE_AST_CACHE.get(key)
    if cached is not None:
        return cached
    tree = ast.parse(target.read_text(encoding="utf-8", errors="replace"))
    _FILE_AST_CACHE[key] = tree
    return tree


def schema_for_source(module_path, func_name):
    """Statically parse ``module_path.func_name`` and build a Schema.

    No imports — safe for boot-critical paths. Falls back to a permissive
    STRING-map schema when the file/function can't be parsed."""
    from pathlib import Path
    try:
        base = Path(__file__).resolve().parent.parent  # repo root (friday/..)
        target = base.joinpath(*module_path.split(".")).with_suffix(".py")
        tree = _parse_file(target)
    except Exception:
        return _permissive_schema()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return _schema_from_functiondef(node)
    return _permissive_schema()


def _permissive_schema(types_module=None):
    prop = {"input": {"type": "STRING", "description": "free-form input"}}
    if types_module is not None:
        return types_module.Schema(type="OBJECT", properties=prop, required=[])
    return {"__permissive__": True, "properties": prop}


def _ann_to_prop_str(ann_src: str):
    s = (ann_src or "").replace(" ", "")
    if not s or s in ("Any", "any", "Optional[Any]"):
        return {"type": "STRING"}
    if s.startswith("Optional[") and s.endswith("]"):
        s = s[len("Optional["):-1]
    if s.startswith(("Union[", "typing.Union[")):
        inner = s.split("[", 1)[1].rsplit("]", 1)[0].split(",")[0]
        return _ann_to_prop_str(inner)
    if s in ("int",):
        return {"type": "INTEGER"}
    if s in ("float", "complex"):
        return {"type": "NUMBER"}
    if s == "bool":
        return {"type": "BOOLEAN"}
    if s in ("str", "bytes"):
        return {"type": "STRING"}
    if s.startswith(("list", "tuple")):
        inner = s.split("[", 1)[1].rsplit("]", 1)[0] if "[" in s else "str"
        return {"type": "ARRAY", "items": _ann_to_prop_str(inner)}
    if s.startswith(("dict", "Dict", "Map")):
        return {"type": "OBJECT"}
    return {"type": "STRING"}


def _schema_from_functiondef(fn):
    import ast

    def _src(node):
        try:
            return ast.unparse(node)
        except Exception:
            return ""

    properties = {}
    req = []
    has_var_keyword = False
    for arg in fn.args.args + fn.args.kwonlyargs:
        if arg.arg == "self":
            continue
        properties[arg.arg] = _ann_to_prop_str(_src(arg.annotation) if arg.annotation else "")
    if fn.args.vararg:
        pass  # *args — no named property possible
    if fn.args.kwarg:
        has_var_keyword = True
        properties["input"] = {"type": "STRING", "description": "free-form input (arbitrary arguments as JSON)"}
    # required = args without defaults (positional-only tail + kwonly without defaults)
    n_defaults = len(fn.args.defaults)
    pos = fn.args.args
    for i, arg in enumerate(pos):
        if arg.arg == "self":
            continue
        if i < len(pos) - n_defaults:
            req.append(arg.arg)
    n_kw_defaults = len(fn.args.kw_defaults)
    for i, arg in enumerate(fn.args.kwonlyargs):
        if i < n_kw_defaults and fn.args.kw_defaults[i] is None:
            req.append(arg.arg)
    if not properties:
        return _permissive_schema()
    return {"properties": properties, "required": req}



def schema_dict_for_descriptor(module_path, func_name):
    """Static schema for a descriptor: returns ``(properties, required)``.

    Never returns None schemas — the Google API rejects parameter-less declarations
    for tools that visibly take arguments. Unparseable functions get a permissive
    STRING-map schema."""
    d = schema_for_source(module_path, func_name)
    if d.get("__permissive__"):
        return d["properties"], []
    return d["properties"], d["required"]
