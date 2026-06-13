"""
FRIDAY Workflow Engine
Multi-step workflow system for defining pipelines combining FRIDAY tools
into automated sequences. Each workflow has steps that can run tools,
transform data, and branch based on conditions.
"""

import json
import uuid
import time
import copy
import threading
import ast
import operator
import re
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed


# ---------------------------------------------------------------------------
# Safe builtins for condition evaluation
# ---------------------------------------------------------------------------

SAFE_BUILTINS = {
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
}

SAFE_OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "truediv": operator.truediv,
    "floordiv": operator.floordiv,
    "mod": operator.mod,
    "pow": operator.pow,
    "and_": operator.and_,
    "or_": operator.or_,
    "not_": operator.not_,
    "contains": operator.contains,
}


# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

VALID_ON_FAILURE = ("skip", "abort", "continue")
VALID_STEP_STATUSES = ("pending", "running", "completed", "failed", "skipped")
VALID_WORKFLOW_STATUSES = ("pending", "running", "completed", "failed", "partial")


# ---------------------------------------------------------------------------
# Data transformers
# ---------------------------------------------------------------------------


def _json_extract(data: Any, path: str) -> Any:
    """Extract value from nested dict/list using dot notation path.

    Args:
        data: Source data structure (dict or list).
        path: Dot-separated path like 'a.b.c' or 'a.0.b'.

    Returns:
        Extracted value.

    Raises:
        KeyError: If a key in the path does not exist.
        IndexError: If a numeric index is out of range.
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current[key]
        elif isinstance(current, (list, tuple)):
            current = current[int(key)]
        else:
            raise KeyError(
                f"Cannot traverse into {type(current).__name__} with key '{key}'"
            )
    return current


def _split(data: str, delim: str = ",") -> List[str]:
    """Split string into list by delimiter.

    Args:
        data: Input string.
        delim: Delimiter character(s).

    Returns:
        List of substrings.
    """
    if not isinstance(data, str):
        data = str(data)
    return data.split(delim)


def _join(data: Any, delim: str = ",") -> str:
    """Join list into string by delimiter.

    Args:
        data: List or tuple of items.
        delim: Delimiter to join with.

    Returns:
        Joined string.
    """
    if isinstance(data, (list, tuple)):
        return delim.join(str(item) for item in data)
    return str(data)


def _upper(data: str) -> str:
    """Convert string to uppercase.

    Args:
        data: Input string.

    Returns:
        Uppercase string.
    """
    return str(data).upper()


def _lower(data: str) -> str:
    """Convert string to lowercase.

    Args:
        data: Input string.

    Returns:
        Lowercase string.
    """
    return str(data).lower()


def _strip(data: str) -> str:
    """Remove leading and trailing whitespace.

    Args:
        data: Input string.

    Returns:
        Stripped string.
    """
    return str(data).strip()


def _truncate(data: str, max_len: int = 100) -> str:
    """Truncate string to maximum length with ellipsis.

    Args:
        data: Input string.
        max_len: Maximum character count.

    Returns:
        Truncated string.
    """
    s = str(data)
    if len(s) <= max_len:
        return s
    return s[:max_len] + "..."


def _prefix(data: str, p: str = "") -> str:
    """Add prefix to string.

    Args:
        data: Input string.
        p: Prefix to prepend.

    Returns:
        Prefixed string.
    """
    return str(p) + str(data)


def _suffix(data: str, s: str = "") -> str:
    """Add suffix to string.

    Args:
        data: Input string.
        s: Suffix to append.

    Returns:
        Suffixed string.
    """
    return str(data) + str(s)


def _to_json(data: Any) -> str:
    """Convert object to JSON string.

    Args:
        data: Any JSON-serializable object.

    Returns:
        JSON string representation.
    """
    return json.dumps(data, default=str)


def _from_json(data: str) -> Any:
    """Parse JSON string to Python object.

    Args:
        data: JSON string.

    Returns:
        Parsed Python object.
    """
    if isinstance(data, str):
        return json.loads(data)
    return data


def _filter_keys(data: Any, keys: List[str]) -> Any:
    """Keep only specified keys from dict.

    Args:
        data: Input dictionary.
        keys: List of keys to keep.

    Returns:
        Filtered dictionary.
    """
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in keys}
    return data


def _rename_keys(data: Any, mapping: Dict[str, str]) -> Any:
    """Rename dict keys using a mapping.

    Args:
        data: Input dictionary.
        mapping: Mapping from old keys to new keys.

    Returns:
        Dictionary with renamed keys.
    """
    if isinstance(data, dict):
        return {mapping.get(k, k): v for k, v in data.items()}
    return data


TRANSFORM_FUNCTIONS = {
    "json_extract": _json_extract,
    "split": _split,
    "join": _join,
    "upper": _upper,
    "lower": _lower,
    "strip": _strip,
    "truncate": _truncate,
    "prefix": _prefix,
    "suffix": _suffix,
    "to_json": _to_json,
    "from_json": _from_json,
    "filter_keys": _filter_keys,
    "rename_keys": _rename_keys,
}


def apply_transform(data: Any, transform_str: str) -> Any:
    """Apply a transform string to data.

    Transform strings look like: 'upper()', 'split(,)',
    'json_extract(a.b.c)', 'truncate(50)', 'prefix(hello_)'.

    Args:
        data: Data to transform.
        transform_str: Transform expression string.

    Returns:
        Transformed data.

    Raises:
        ValueError: If transform is unknown or fails.
    """
    if not transform_str or not transform_str.strip():
        return data

    transform_str = transform_str.strip()

    paren_idx = transform_str.find("(")
    if paren_idx == -1:
        func_name = transform_str
        args = ()
    else:
        func_name = transform_str[:paren_idx]
        args_str = transform_str[paren_idx + 1 :].rstrip(")")
        if args_str:
            args = tuple(a.strip().strip("'\"") for a in args_str.split(","))
        else:
            args = ()

    if func_name not in TRANSFORM_FUNCTIONS:
        raise ValueError(f"Unknown transform: {func_name}")

    func = TRANSFORM_FUNCTIONS[func_name]
    try:
        if args:
            return func(data, *args)
        return func(data)
    except TypeError as exc:
        raise ValueError(f"Transform {func_name} failed: {exc}")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    """Result of executing a single workflow step.

    Attributes:
        step_id: Identifier of the step that was executed.
        name: Human-readable step name.
        status: One of pending, running, completed, failed, skipped.
        output: The output produced by the step.
        error: Error message if the step failed.
        started_at: ISO timestamp when execution started.
        completed_at: ISO timestamp when execution completed.
        duration_ms: Wall-clock duration in milliseconds.
    """

    step_id: str
    name: str
    status: str = "pending"
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the step result.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StepResult":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with step result fields.

        Returns:
            StepResult instance.
        """
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class WorkflowResult:
    """Result of executing an entire workflow.

    Attributes:
        workflow_id: Identifier of the executed workflow.
        name: Workflow name.
        status: Overall execution status.
        steps_results: List of individual step results.
        started_at: ISO timestamp when execution started.
        completed_at: ISO timestamp when execution completed.
        total_duration_ms: Total wall-clock duration in milliseconds.
        context: Final context snapshot after execution.
    """

    workflow_id: str
    name: str
    status: str = "pending"
    steps_results: List[StepResult] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_ms: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the workflow result.
        """
        d = asdict(self)
        d["steps_results"] = [sr.to_dict() for sr in self.steps_results]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowResult":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with workflow result fields.

        Returns:
            WorkflowResult instance.
        """
        steps = [StepResult.from_dict(s) for s in data.get("steps_results", [])]
        return cls(
            workflow_id=data.get("workflow_id", ""),
            name=data.get("name", ""),
            status=data.get("status", "pending"),
            steps_results=steps,
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            total_duration_ms=data.get("total_duration_ms"),
            context=data.get("context", {}),
        )


# ---------------------------------------------------------------------------
# Context Manager
# ---------------------------------------------------------------------------


class ContextManager:
    """Thread-safe context manager for workflow execution.

    Maintains a dictionary of key-value pairs that are passed between steps.
    Supports template resolution for dynamic data flow using {key} syntax.
    All operations are protected by a threading lock for safe concurrent use.
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        """Initialize context manager.

        Args:
            initial: Optional initial context data.
        """
        self._data: Dict[str, Any] = dict(initial) if initial else {}
        self._lock = threading.Lock()
        self._snapshots: List[Dict[str, Any]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context.

        Args:
            key: Key to look up.
            default: Default value if key not found.

        Returns:
            Value associated with key, or default.
        """
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in context.

        Args:
            key: Key to set.
            value: Value to associate with key.
        """
        with self._lock:
            self._data[key] = value

    def update(self, data: Dict[str, Any]) -> None:
        """Batch set multiple key-value pairs.

        Args:
            data: Dictionary of key-value pairs to set.
        """
        with self._lock:
            self._data.update(data)

    def resolve_template(self, template: str) -> str:
        """Replace {key} placeholders in strings with context values.

        Supports nested dot notation like {step1.output.name}.

        Args:
            template: String with {key} placeholders.

        Returns:
            Resolved string with values substituted.
        """
        if not isinstance(template, str):
            return str(template)

        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            with self._lock:
                try:
                    value = _json_extract(self._data, key)
                except (KeyError, TypeError, IndexError, ValueError):
                    return match.group(0)
            return str(value) if value is not None else ""

        return re.sub(r"\{([^}]+)\}", _replacer, template)

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of the full context.

        Returns:
            Copy of context dictionary.
        """
        with self._lock:
            return copy.deepcopy(self._data)

    def validate_keys(self, required_keys: List[str]) -> List[str]:
        """Check that required keys exist in context.

        Args:
            required_keys: List of keys that must be present.

        Returns:
            List of missing key names.
        """
        with self._lock:
            return [k for k in required_keys if k not in self._data]

    def clear(self) -> None:
        """Clear all context data."""
        with self._lock:
            self._data.clear()

    def keys(self) -> List[str]:
        """Return list of all keys in context.

        Returns:
            List of key strings.
        """
        with self._lock:
            return list(self._data.keys())

    def items(self) -> Dict[str, Any]:
        """Return copy of all context items.

        Returns:
            Dictionary copy of context.
        """
        with self._lock:
            return dict(self._data)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context.

        Args:
            key: Key to check.

        Returns:
            True if key exists.
        """
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        """Return number of items in context.

        Returns:
            Item count.
        """
        with self._lock:
            return len(self._data)

    def __repr__(self) -> str:
        """String representation."""
        with self._lock:
            return f"ContextManager({self._data})"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def context_manager_resolve(value: str, context: Dict[str, Any]) -> Any:
    """Resolve a context reference string against a context dict.

    If the value starts with '$', it is treated as a context key lookup
    using dot notation. If the value contains {key} patterns, they are
    resolved via template substitution. Otherwise the original value is
    returned unchanged.

    Args:
        value: String value potentially containing references.
        context: Context dictionary.

    Returns:
        Resolved value.
    """
    if not isinstance(value, str):
        return value

    if value.startswith("$"):
        key = value[1:]
        keys = key.split(".")
        current = context
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return value
        return current

    if "{" in value:
        cm = ContextManager(context)
        return cm.resolve_template(value)

    return value


def _execute_tool_call(
    tool_name: str, tool_action: str, args: Dict[str, Any], timeout: int
) -> Any:
    """Execute a tool call with timeout enforcement.

    Runs the tool dispatch in a separate thread and joins with the
    specified timeout. Raises TimeoutError if the tool does not return
    in time.

    Args:
        tool_name: Name of the tool to call.
        tool_action: Action/subcommand.
        args: Arguments dictionary.
        timeout: Maximum seconds to wait.

    Returns:
        Tool output.

    Raises:
        TimeoutError: If execution exceeds timeout.
        RuntimeError: If tool execution fails.
    """
    result_container: List[Any] = [None]
    error_container: List[Optional[Exception]] = [None]

    def _target():
        try:
            result_container[0] = _dispatch_tool(tool_name, tool_action, args)
        except Exception as exc:
            error_container[0] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(
            f"Tool '{tool_name}.{tool_action}' exceeded timeout of {timeout}s"
        )

    if error_container[0] is not None:
        raise RuntimeError(f"Tool error: {error_container[0]}")

    return result_container[0]


def _dispatch_tool(
    tool_name: str, tool_action: str, args: Dict[str, Any]
) -> Any:
    """Dispatch a tool call to the appropriate handler.

    This is a stub that returns structured data representing the
    tool call. In a real FRIDAY integration, this would route to
    the actual tool implementations based on tool_name.

    Args:
        tool_name: Tool name.
        tool_action: Tool action.
        args: Tool arguments.

    Returns:
        Simulated tool output dictionary.
    """
    return {
        "tool": tool_name,
        "action": tool_action,
        "args": args,
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"Executed {tool_name}.{tool_action}",
    }


def _compute_duration_ms(start_iso: str, end_iso: str) -> float:
    """Compute duration in milliseconds between two ISO timestamps.

    Args:
        start_iso: Start timestamp string.
        end_iso: End timestamp string.

    Returns:
        Duration in milliseconds, or 0.0 on parse failure.
    """
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        delta = end - start
        return delta.total_seconds() * 1000.0
    except (ValueError, TypeError):
        return 0.0


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string.

    Returns:
        ISO timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


class Step:
    """A single step in a workflow.

    Each step references a tool to execute, optional conditions for
    branching, transforms to apply to outputs, retry behavior, and
    dependency constraints.

    Attributes:
        id: Unique step identifier.
        name: Human-readable step name.
        tool_name: Name of the tool to invoke.
        tool_action: Action/subcommand for the tool.
        tool_args: Arguments to pass to the tool.
        condition: Python expression that must evaluate true to run.
        transform: Transform expression to apply to output.
        timeout: Maximum seconds to wait for completion.
        retry_count: Number of retry attempts on failure.
        on_failure: Behavior on failure: skip, abort, or continue.
        dependencies: Step IDs that must complete before this step.
    """

    def __init__(
        self,
        step_id: Optional[str] = None,
        name: str = "",
        tool_name: str = "",
        tool_action: str = "",
        tool_args: Optional[Dict[str, Any]] = None,
        condition: Optional[str] = None,
        transform: Optional[str] = None,
        timeout: int = 30,
        retry_count: int = 0,
        on_failure: str = "continue",
        dependencies: Optional[List[str]] = None,
    ):
        """Initialize a workflow step.

        Args:
            step_id: Unique identifier. Generated if not provided.
            name: Human-readable step name.
            tool_name: Name of the tool to invoke.
            tool_action: Action/subcommand for the tool.
            tool_args: Arguments to pass to the tool.
            condition: Python expression that must be true for step to run.
            transform: Transform to apply to step output.
            timeout: Maximum seconds to wait for step completion.
            retry_count: Number of times to retry on failure.
            on_failure: Action on failure: 'skip', 'abort', or 'continue'.
            dependencies: List of step IDs that must complete first.
        """
        self.id = step_id or str(uuid.uuid4())[:8]
        self.name = name or f"Step-{self.id}"
        self.tool_name = tool_name
        self.tool_action = tool_action
        self.tool_args = tool_args or {}
        self.condition = condition
        self.transform = transform
        self.timeout = max(1, timeout)
        self.retry_count = max(0, retry_count)
        self.on_failure = on_failure if on_failure in VALID_ON_FAILURE else "continue"
        self.dependencies = dependencies or []

    def evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """Evaluate the step's condition expression against context.

        Uses a restricted eval with only safe builtins to prevent
        arbitrary code execution. The context dict is available as
        local variables in the expression.

        Args:
            context: Context dictionary for variable resolution.

        Returns:
            True if condition passes or no condition is set.
        """
        if not self.condition:
            return True

        eval_globals = {"__builtins__": {}}
        eval_globals.update(SAFE_BUILTINS)
        eval_globals.update(SAFE_OPERATORS)
        eval_locals = dict(context)

        try:
            result = eval(self.condition, eval_globals, eval_locals)
            return bool(result)
        except Exception:
            return False

    def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute this step by calling the associated tool.

        Resolves tool arguments using context, evaluates conditions,
        applies transforms, and handles retries with exponential
        backoff.

        Args:
            context: Current workflow context.

        Returns:
            StepResult with output or error information.
        """
        result = StepResult(
            step_id=self.id,
            name=self.name,
            status="running",
            started_at=_now_iso(),
        )

        if not self.evaluate_condition(context):
            result.status = "skipped"
            result.completed_at = _now_iso()
            return result

        resolved_args = {}
        for key, value in self.tool_args.items():
            if isinstance(value, str):
                resolved_args[key] = context_manager_resolve(value, context)
            else:
                resolved_args[key] = value

        last_error = None
        for attempt in range(1 + self.retry_count):
            try:
                output = _execute_tool_call(
                    self.tool_name, self.tool_action, resolved_args, self.timeout
                )

                if self.transform:
                    output = apply_transform(output, self.transform)

                result.output = output
                result.status = "completed"
                result.completed_at = _now_iso()
                result.duration_ms = _compute_duration_ms(
                    result.started_at, result.completed_at
                )
                return result

            except Exception as exc:
                last_error = str(exc)
                if attempt < self.retry_count:
                    time.sleep(min(2 ** attempt, 10))

        result.status = "failed"
        result.error = last_error
        result.completed_at = _now_iso()
        result.duration_ms = _compute_duration_ms(
            result.started_at, result.completed_at
        )
        return result

    def to_dict(self) -> dict:
        """Serialize step to dictionary.

        Returns:
            Dictionary representation of the step.
        """
        return {
            "id": self.id,
            "name": self.name,
            "tool_name": self.tool_name,
            "tool_action": self.tool_action,
            "tool_args": self.tool_args,
            "condition": self.condition,
            "transform": self.transform,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "on_failure": self.on_failure,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Step":
        """Deserialize step from dictionary.

        Args:
            data: Dictionary with step configuration.

        Returns:
            Step instance.
        """
        return cls(
            step_id=data.get("id"),
            name=data.get("name", ""),
            tool_name=data.get("tool_name", ""),
            tool_action=data.get("tool_action", ""),
            tool_args=data.get("tool_args", {}),
            condition=data.get("condition"),
            transform=data.get("transform"),
            timeout=data.get("timeout", 30),
            retry_count=data.get("retry_count", 0),
            on_failure=data.get("on_failure", "continue"),
            dependencies=data.get("dependencies", []),
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"Step(id={self.id!r}, name={self.name!r}, tool={self.tool_name!r})"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class Workflow:
    """A named collection of steps forming an automation pipeline.

    Workflows are serializable to/from JSON and can be validated
    for structural correctness before execution.

    Attributes:
        id: Unique workflow identifier.
        name: Human-readable workflow name.
        description: Workflow description.
        steps: Ordered list of Step instances.
        version: Semantic version string.
        created_at: ISO timestamp of creation.
        tags: List of tag strings for categorization.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        steps: Optional[List[Step]] = None,
        version: str = "1.0.0",
        created_at: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Initialize a workflow.

        Args:
            workflow_id: Unique identifier. Generated if not provided.
            name: Human-readable workflow name.
            description: Workflow description.
            steps: List of Step instances.
            version: Semantic version string.
            created_at: ISO timestamp of creation.
            tags: List of tag strings.
        """
        self.id = workflow_id or str(uuid.uuid4())[:12]
        self.name = name or f"Workflow-{self.id}"
        self.description = description
        self.steps: List[Step] = list(steps) if steps else []
        self.version = version
        self.created_at = created_at or _now_iso()
        self.tags = list(tags) if tags else []

    def add_step(self, step: Step) -> None:
        """Add a step to the workflow.

        Args:
            step: Step instance to add.

        Raises:
            ValueError: If step ID already exists in the workflow.
        """
        existing_ids = {s.id for s in self.steps}
        if step.id in existing_ids:
            raise ValueError(f"Step with id '{step.id}' already exists")
        self.steps.append(step)

    def remove_step(self, step_id: str) -> bool:
        """Remove a step by ID.

        Args:
            step_id: ID of the step to remove.

        Returns:
            True if step was found and removed, False otherwise.
        """
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(i)
                return True
        return False

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID.

        Args:
            step_id: ID of the step to find.

        Returns:
            Step instance if found, None otherwise.
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def validate(self) -> List[str]:
        """Validate the workflow structure.

        Checks for:
        - Unique step IDs
        - Non-empty tool names
        - Valid condition syntax
        - No circular dependencies
        - Positive timeouts
        - Valid on_failure values
        - Valid dependency references

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors: List[str] = []

        if not self.name:
            errors.append("Workflow name is required")

        if not self.steps:
            errors.append("Workflow must have at least one step")
            return errors

        seen_ids: Dict[str, int] = {}
        all_step_ids = set()

        for idx, step in enumerate(self.steps):
            if step.id in seen_ids:
                errors.append(
                    f"Duplicate step id '{step.id}' at positions "
                    f"{seen_ids[step.id]} and {idx}"
                )
            seen_ids[step.id] = idx
            all_step_ids.add(step.id)

            if not step.tool_name:
                errors.append(
                    f"Step '{step.name}' ({step.id}) has empty tool_name"
                )

            if step.condition:
                try:
                    compile(step.condition, "<condition>", "eval")
                except SyntaxError as exc:
                    errors.append(
                        f"Step '{step.name}' has invalid condition "
                        f"syntax: {exc}"
                    )

            if step.timeout < 1:
                errors.append(
                    f"Step '{step.name}' has invalid timeout: "
                    f"{step.timeout}"
                )

            if step.on_failure not in VALID_ON_FAILURE:
                errors.append(
                    f"Step '{step.name}' has invalid on_failure: "
                    f"{step.on_failure}"
                )

            for dep in step.dependencies:
                if dep not in all_step_ids:
                    errors.append(
                        f"Step '{step.name}' depends on unknown "
                        f"step '{dep}'"
                    )

        if self._has_circular_deps():
            errors.append(
                "Workflow has circular dependencies between steps"
            )

        return errors

    def _has_circular_deps(self) -> bool:
        """Check for circular dependencies using depth-first search.

        Returns:
            True if a cycle is detected in the dependency graph.
        """
        step_map = {s.id: s for s in self.steps}
        visited: set = set()
        rec_stack: set = set()

        def _dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            node = step_map.get(node_id)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        if _dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            rec_stack.discard(node_id)
            return False

        for step in self.steps:
            if step.id not in visited:
                if _dfs(step.id):
                    return True
        return False

    def to_json(self) -> dict:
        """Serialize workflow to dictionary for JSON encoding.

        Returns:
            Dictionary representation of the workflow.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "version": self.version,
            "created_at": self.created_at,
            "tags": self.tags,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Workflow":
        """Deserialize workflow from dictionary.

        Args:
            data: Dictionary with workflow configuration.

        Returns:
            Workflow instance.
        """
        steps = [Step.from_dict(s) for s in data.get("steps", [])]
        return cls(
            workflow_id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at"),
            tags=data.get("tags", []),
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Workflow(id={self.id!r}, name={self.name!r}, "
            f"steps={len(self.steps)})"
        )


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """Core engine for managing and executing workflows.

    Provides methods to create, run, validate, save, load, and
    clone workflows. Supports both sequential and parallel execution
    using thread pools. All state is protected by threading locks.
    """

    def __init__(self):
        """Initialize the workflow engine."""
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.active_executions: Dict[str, WorkflowResult] = {}
        self._lock = threading.Lock()

    def create_workflow(
        self,
        name: str,
        description: str,
        steps_config: List[dict],
    ) -> Workflow:
        """Create a workflow from a list of step configuration dicts.

        Each dict in steps_config is passed to Step.from_dict() to
        create Step instances.

        Args:
            name: Workflow name.
            description: Workflow description.
            steps_config: List of step config dictionaries.

        Returns:
            Created Workflow instance.
        """
        steps = [Step.from_dict(cfg) for cfg in steps_config]
        workflow = Workflow(name=name, description=description, steps=steps)
        with self._lock:
            self.workflows[workflow.id] = workflow
        return workflow

    def run_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute a workflow's steps sequentially.

        Steps are run in list order. Each step receives the accumulated
        context from previous steps. Failed steps with on_failure='abort'
        halt the entire workflow immediately.

        Args:
            workflow_id: ID of the workflow to run.
            initial_context: Optional starting context.

        Returns:
            WorkflowResult with all step results.

        Raises:
            KeyError: If workflow_id is not found.
        """
        workflow = self._get_workflow_or_raise(workflow_id)
        ctx = ContextManager(initial_context)
        result = WorkflowResult(
            workflow_id=workflow.id,
            name=workflow.name,
            status="running",
            started_at=_now_iso(),
        )

        with self._lock:
            self.active_executions[workflow_id] = result

        completed_steps: set = set()

        for step in workflow.steps:
            deps_met = all(d in completed_steps for d in step.dependencies)
            if not deps_met:
                unmet = [d for d in step.dependencies if d not in completed_steps]
                dep_result = StepResult(
                    step_id=step.id,
                    name=step.name,
                    status="skipped",
                    error=f"Dependencies not met: {', '.join(unmet)}",
                    started_at=_now_iso(),
                    completed_at=_now_iso(),
                )
                result.steps_results.append(dep_result)
                continue

            step_result = step.execute(ctx.snapshot())
            result.steps_results.append(step_result)
            completed_steps.add(step.id)

            if step_result.status == "completed":
                ctx.set(f"{step.id}.output", step_result.output)
                ctx.set(f"{step.name}.output", step_result.output)
            elif step_result.status == "failed":
                if step.on_failure == "abort":
                    result.status = "failed"
                    break

        if result.status == "running":
            all_terminal = all(
                sr.status in ("completed", "skipped")
                for sr in result.steps_results
            )
            result.status = "completed" if all_terminal else "partial"

        result.completed_at = _now_iso()
        result.total_duration_ms = _compute_duration_ms(
            result.started_at, result.completed_at
        )
        result.context = ctx.snapshot()

        with self._lock:
            self.active_executions.pop(workflow_id, None)
            self.execution_history.append(result.to_dict())

        return result

    def run_step(
        self,
        workflow_id: str,
        step_id: str,
        context: Dict[str, Any],
    ) -> StepResult:
        """Execute a single step from a workflow.

        Useful for testing individual steps or running a specific
        step outside the normal workflow execution order.

        Args:
            workflow_id: ID of the workflow containing the step.
            step_id: ID of the step to execute.
            context: Context for execution.

        Returns:
            StepResult for the executed step.
        """
        workflow = self._get_workflow_or_raise(workflow_id)
        step = workflow.get_step(step_id)
        if step is None:
            return StepResult(
                step_id=step_id,
                name="unknown",
                status="failed",
                error=f"Step '{step_id}' not found in workflow "
                      f"'{workflow_id}'",
            )
        return step.execute(context)

    def parallel_run_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute workflow with independent steps running in parallel.

        Steps with no unmet dependencies are grouped into waves and
        executed concurrently using a ThreadPoolExecutor. Each wave
        completes before the next is scheduled.

        Args:
            workflow_id: ID of the workflow to run.
            initial_context: Optional starting context.

        Returns:
            WorkflowResult with all step results.
        """
        workflow = self._get_workflow_or_raise(workflow_id)
        ctx = ContextManager(initial_context)
        result = WorkflowResult(
            workflow_id=workflow.id,
            name=workflow.name,
            status="running",
            started_at=_now_iso(),
        )

        with self._lock:
            self.active_executions[workflow_id] = result

        completed_steps: Dict[str, StepResult] = {}
        result_lock = threading.Lock()

        def _run_one(step: Step, snap: Dict[str, Any]) -> StepResult:
            return step.execute(snap)

        max_workers = min(len(workflow.steps), 8) or 1
        remaining = list(workflow.steps)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while remaining:
                ready = []
                for step in remaining:
                    deps_met = all(
                        d in completed_steps
                        and completed_steps[d].status in ("completed", "skipped")
                        for d in step.dependencies
                    )
                    if deps_met:
                        ready.append(step)

                if not ready:
                    for step in remaining:
                        sr = StepResult(
                            step_id=step.id,
                            name=step.name,
                            status="skipped",
                            error="Unresolvable dependencies",
                            started_at=_now_iso(),
                            completed_at=_now_iso(),
                        )
                        with result_lock:
                            result.steps_results.append(sr)
                            completed_steps[step.id] = sr
                    break

                futures = {}
                for step in ready:
                    snap = ctx.snapshot()
                    future = executor.submit(_run_one, step, snap)
                    futures[future] = step

                for future in as_completed(futures):
                    step = futures[future]
                    try:
                        step_result = future.result()
                    except Exception as exc:
                        step_result = StepResult(
                            step_id=step.id,
                            name=step.name,
                            status="failed",
                            error=str(exc),
                            started_at=_now_iso(),
                            completed_at=_now_iso(),
                        )

                    with result_lock:
                        result.steps_results.append(step_result)
                        completed_steps[step.id] = step_result

                    if step_result.status == "completed":
                        ctx.set(f"{step.id}.output", step_result.output)
                        ctx.set(f"{step.name}.output", step_result.output)
                    elif step_result.status == "failed":
                        if step.on_failure == "abort":
                            result.status = "failed"

                    remaining.remove(step)

        if result.status == "running":
            all_ok = all(
                sr.status in ("completed", "skipped")
                for sr in result.steps_results
            )
            result.status = "completed" if all_ok else "partial"

        result.completed_at = _now_iso()
        result.total_duration_ms = _compute_duration_ms(
            result.started_at, result.completed_at
        )
        result.context = ctx.snapshot()

        with self._lock:
            self.active_executions.pop(workflow_id, None)
            self.execution_history.append(result.to_dict())

        return result

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            Workflow instance or None if not found.
        """
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[dict]:
        """List all registered workflows.

        Returns:
            List of workflow summary dictionaries.
        """
        with self._lock:
            return [
                {
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "version": wf.version,
                    "created_at": wf.created_at,
                    "tags": wf.tags,
                    "step_count": len(wf.steps),
                }
                for wf in self.workflows.values()
            ]

    def get_history(
        self, workflow_id: Optional[str] = None
    ) -> List[dict]:
        """Get execution history.

        Args:
            workflow_id: Optional filter by workflow ID. If None,
                        returns all execution history.

        Returns:
            List of WorkflowResult dictionaries.
        """
        with self._lock:
            if workflow_id:
                return [
                    h
                    for h in self.execution_history
                    if h.get("workflow_id") == workflow_id
                ]
            return list(self.execution_history)

    def save_workflow(self, workflow_id: str, path: str) -> None:
        """Save a workflow to a JSON file.

        Args:
            workflow_id: ID of workflow to save.
            path: File path to write to.

        Raises:
            KeyError: If workflow not found.
        """
        workflow = self._get_workflow_or_raise(workflow_id)
        data = workflow.to_json()
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def load_workflow(self, path: str) -> Workflow:
        """Load a workflow from a JSON file.

        The loaded workflow is registered in the engine's workflow
        dictionary for future operations.

        Args:
            path: File path to read from.

        Returns:
            Loaded Workflow instance.

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        workflow = Workflow.from_json(data)
        with self._lock:
            self.workflows[workflow.id] = workflow
        return workflow

    def clone_workflow(
        self, workflow_id: str, new_name: str
    ) -> Workflow:
        """Deep copy a workflow with a new name and ID.

        All steps are deep-copied so modifications to the clone
        do not affect the original.

        Args:
            workflow_id: ID of workflow to clone.
            new_name: Name for the cloned workflow.

        Returns:
            New Workflow instance with copied steps.

        Raises:
            KeyError: If workflow not found.
        """
        original = self._get_workflow_or_raise(workflow_id)
        cloned_data = copy.deepcopy(original.to_json())
        cloned_data["id"] = str(uuid.uuid4())[:12]
        cloned_data["name"] = new_name
        cloned_data["created_at"] = _now_iso()
        cloned = Workflow.from_json(cloned_data)
        with self._lock:
            self.workflows[cloned.id] = cloned
        return cloned

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID.

        Args:
            workflow_id: ID of workflow to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if workflow_id in self.workflows:
                del self.workflows[workflow_id]
                return True
            return False

    def _get_workflow_or_raise(self, workflow_id: str) -> Workflow:
        """Get a workflow or raise KeyError.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            Workflow instance.

        Raises:
            KeyError: If workflow not found.
        """
        wf = self.workflows.get(workflow_id)
        if wf is None:
            raise KeyError(f"Workflow '{workflow_id}' not found")
        return wf


# ---------------------------------------------------------------------------
# Template Library
# ---------------------------------------------------------------------------


class TemplateLibrary:
    """Pre-built workflow templates for common automation tasks.

    Provides ready-to-use step configurations that can be customized
    and instantiated as full Workflow objects. Templates cover common
    development, analysis, and system administration workflows.
    """

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "code_review": {
            "description": (
                "Review code for quality, style, and best practices"
            ),
            "steps": [
                {
                    "id": "review_read",
                    "name": "Read source file",
                    "tool_name": "file_ops",
                    "tool_action": "read",
                    "tool_args": {"path": "$file_path"},
                    "timeout": 15,
                },
                {
                    "id": "review_analyze",
                    "name": "Analyze code quality",
                    "tool_name": "code_review_tool",
                    "tool_action": "analyze",
                    "tool_args": {
                        "code": "{review_read.output}",
                        "language": "$language",
                    },
                    "timeout": 60,
                    "dependencies": ["review_read"],
                },
                {
                    "id": "review_report",
                    "name": "Generate review report",
                    "tool_name": "report_generator",
                    "tool_action": "create",
                    "tool_args": {
                        "title": "Code Review Report",
                        "content": "{review_analyze.output}",
                        "format": "markdown",
                    },
                    "timeout": 30,
                    "dependencies": ["review_analyze"],
                },
            ],
        },
        "security_scan": {
            "description": (
                "Scan code for security vulnerabilities and "
                "generate findings report"
            ),
            "steps": [
                {
                    "id": "sec_read",
                    "name": "Read codebase",
                    "tool_name": "file_ops",
                    "tool_action": "read",
                    "tool_args": {"path": "$file_path"},
                    "timeout": 15,
                },
                {
                    "id": "sec_scan",
                    "name": "Security vulnerability scan",
                    "tool_name": "security_scanner",
                    "tool_action": "scan",
                    "tool_args": {
                        "code": "{sec_read.output}",
                        "scan_type": "full",
                        "severity_threshold": "$min_severity",
                    },
                    "timeout": 120,
                    "dependencies": ["sec_read"],
                },
                {
                    "id": "sec_findings",
                    "name": "Generate security findings report",
                    "tool_name": "report_generator",
                    "tool_action": "create",
                    "tool_args": {
                        "title": "Security Scan Results",
                        "content": "{sec_scan.output}",
                        "format": "json",
                    },
                    "timeout": 30,
                    "dependencies": ["sec_scan"],
                },
            ],
        },
        "file_backup": {
            "description": (
                "Read a file and create a timestamped backup copy"
            ),
            "steps": [
                {
                    "id": "backup_read",
                    "name": "Read original file",
                    "tool_name": "file_ops",
                    "tool_action": "read",
                    "tool_args": {"path": "$file_path"},
                    "timeout": 15,
                },
                {
                    "id": "backup_create",
                    "name": "Create timestamped backup",
                    "tool_name": "file_ops",
                    "tool_action": "write",
                    "tool_args": {
                        "path": "$backup_path",
                        "content": "{backup_read.output}",
                    },
                    "timeout": 30,
                    "dependencies": ["backup_read"],
                },
                {
                    "id": "backup_verify",
                    "name": "Verify backup integrity",
                    "tool_name": "file_ops",
                    "tool_action": "read",
                    "tool_args": {"path": "$backup_path"},
                    "timeout": 15,
                    "dependencies": ["backup_create"],
                },
            ],
        },
        "web_research": {
            "description": (
                "Search the web, extract content, and produce "
                "a summary"
            ),
            "steps": [
                {
                    "id": "research_search",
                    "name": "Web search",
                    "tool_name": "web_search_tool",
                    "tool_action": "search",
                    "tool_args": {
                        "query": "$search_query",
                        "num_results": "$num_results",
                    },
                    "timeout": 30,
                },
                {
                    "id": "research_extract",
                    "name": "Extract content from top results",
                    "tool_name": "web_extract_tool",
                    "tool_action": "extract",
                    "tool_args": {
                        "urls": "{research_search.output}",
                    },
                    "timeout": 60,
                    "dependencies": ["research_search"],
                },
                {
                    "id": "research_summarize",
                    "name": "Summarize extracted content",
                    "tool_name": "summarizer",
                    "tool_action": "summarize",
                    "tool_args": {
                        "content": "{research_extract.output}",
                        "max_length": "$max_summary_length",
                    },
                    "timeout": 45,
                    "dependencies": ["research_extract"],
                },
            ],
        },
        "git_analysis": {
            "description": (
                "Analyze git repository status, history, and "
                "contributors"
            ),
            "steps": [
                {
                    "id": "git_status",
                    "name": "Get git status",
                    "tool_name": "git_tool",
                    "tool_action": "status",
                    "tool_args": {"repo_path": "$repo_path"},
                    "timeout": 15,
                },
                {
                    "id": "git_log",
                    "name": "Get recent commit history",
                    "tool_name": "git_tool",
                    "tool_action": "log",
                    "tool_args": {
                        "repo_path": "$repo_path",
                        "max_commits": "$max_commits",
                    },
                    "timeout": 15,
                },
                {
                    "id": "git_summary",
                    "name": "Generate git analysis summary",
                    "tool_name": "report_generator",
                    "tool_action": "create",
                    "tool_args": {
                        "title": "Git Repository Analysis",
                        "status": "{git_status.output}",
                        "history": "{git_log.output}",
                        "format": "markdown",
                    },
                    "timeout": 30,
                    "dependencies": ["git_status", "git_log"],
                },
            ],
        },
        "system_health": {
            "description": (
                "Check system health metrics and generate a "
                "status report"
            ),
            "steps": [
                {
                    "id": "health_cpu",
                    "name": "Check CPU usage",
                    "tool_name": "system_monitor",
                    "tool_action": "cpu",
                    "tool_args": {"interval": "$cpu_interval"},
                    "timeout": 30,
                },
                {
                    "id": "health_memory",
                    "name": "Check memory usage",
                    "tool_name": "system_monitor",
                    "tool_action": "memory",
                    "tool_args": {},
                    "timeout": 15,
                },
                {
                    "id": "health_disk",
                    "name": "Check disk usage",
                    "tool_name": "system_monitor",
                    "tool_action": "disk",
                    "tool_args": {"path": "$disk_path"},
                    "timeout": 15,
                },
                {
                    "id": "health_report",
                    "name": "Generate health report",
                    "tool_name": "report_generator",
                    "tool_action": "create",
                    "tool_args": {
                        "title": "System Health Report",
                        "cpu": "{health_cpu.output}",
                        "memory": "{health_memory.output}",
                        "disk": "{health_disk.output}",
                        "format": "json",
                    },
                    "timeout": 30,
                    "dependencies": [
                        "health_cpu",
                        "health_memory",
                        "health_disk",
                    ],
                },
            ],
        },
        "memory_consolidate": {
            "description": (
                "Search memories, deduplicate entries, and "
                "store cleaned results"
            ),
            "steps": [
                {
                    "id": "mem_search",
                    "name": "Search all memories",
                    "tool_name": "memory_tool",
                    "tool_action": "search",
                    "tool_args": {
                        "query": "$search_query",
                        "limit": "$search_limit",
                    },
                    "timeout": 30,
                },
                {
                    "id": "mem_dedup",
                    "name": "Deduplicate memory entries",
                    "tool_name": "memory_tool",
                    "tool_action": "deduplicate",
                    "tool_args": {"entries": "{mem_search.output}"},
                    "timeout": 30,
                    "dependencies": ["mem_search"],
                },
                {
                    "id": "mem_store",
                    "name": "Store cleaned memories",
                    "tool_name": "memory_tool",
                    "tool_action": "store",
                    "tool_args": {
                        "entries": "{mem_dedup.output}",
                        "namespace": "$memory_namespace",
                    },
                    "timeout": 30,
                    "dependencies": ["mem_dedup"],
                },
            ],
        },
        "code_formatter": {
            "description": (
                "Lint, format, and verify code formatting"
            ),
            "steps": [
                {
                    "id": "fmt_read",
                    "name": "Read source code",
                    "tool_name": "file_ops",
                    "tool_action": "read",
                    "tool_args": {"path": "$file_path"},
                    "timeout": 15,
                },
                {
                    "id": "fmt_lint",
                    "name": "Lint code for issues",
                    "tool_name": "linter",
                    "tool_action": "lint",
                    "tool_args": {
                        "code": "{fmt_read.output}",
                        "language": "$language",
                    },
                    "timeout": 30,
                    "dependencies": ["fmt_read"],
                },
                {
                    "id": "fmt_format",
                    "name": "Format code",
                    "tool_name": "formatter",
                    "tool_action": "format",
                    "tool_args": {
                        "code": "{fmt_read.output}",
                        "language": "$language",
                        "style": "$format_style",
                    },
                    "timeout": 30,
                    "dependencies": ["fmt_lint"],
                },
                {
                    "id": "fmt_verify",
                    "name": "Verify formatting",
                    "tool_name": "formatter",
                    "tool_action": "verify",
                    "tool_args": {
                        "code": "{fmt_format.output}",
                        "language": "$language",
                    },
                    "timeout": 15,
                    "dependencies": ["fmt_format"],
                },
            ],
        },
    }

    def list_templates(self) -> List[dict]:
        """List all available templates.

        Returns:
            List of dicts with template name, description, and
            step count.
        """
        return [
            {
                "name": name,
                "description": info["description"],
                "step_count": len(info["steps"]),
            }
            for name, info in self.TEMPLATES.items()
        ]

    def get_template(self, name: str) -> List[dict]:
        """Get step configurations for a template.

        Args:
            name: Template name.

        Returns:
            Deep copy of step config list.

        Raises:
            KeyError: If template not found.
        """
        if name not in self.TEMPLATES:
            raise KeyError(
                f"Template '{name}' not found. "
                f"Available: {list(self.TEMPLATES.keys())}"
            )
        return copy.deepcopy(self.TEMPLATES[name]["steps"])

    def create_from_template(
        self,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Create a workflow from a named template.

        Optional overrides can modify specific step configurations
        by step_id.

        Args:
            name: Template name.
            overrides: Optional dict of step_id -> key -> value
                      to override in the step configs.

        Returns:
            New Workflow instance based on the template.

        Raises:
            KeyError: If template not found.
        """
        if name not in self.TEMPLATES:
            raise KeyError(
                f"Template '{name}' not found. "
                f"Available: {list(self.TEMPLATES.keys())}"
            )

        template = self.TEMPLATES[name]
        steps_config = copy.deepcopy(template["steps"])

        if overrides:
            for step_cfg in steps_config:
                step_id = step_cfg.get("id", "")
                if step_id in overrides:
                    step_cfg.update(overrides[step_id])

        wf = Workflow(
            name=f"Template: {name}",
            description=template["description"],
            steps=[Step.from_dict(s) for s in steps_config],
            tags=["template", name],
        )
        return wf


# ---------------------------------------------------------------------------
# Global engine and library instances
# ---------------------------------------------------------------------------

_engine: Optional[WorkflowEngine] = None
_library: Optional[TemplateLibrary] = None
_engine_lock = threading.Lock()


def _get_engine() -> WorkflowEngine:
    """Get or create the global workflow engine singleton.

    Returns:
        The global WorkflowEngine instance.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = WorkflowEngine()
    return _engine


def _get_library() -> TemplateLibrary:
    """Get or create the global template library singleton.

    Returns:
        The global TemplateLibrary instance.
    """
    global _library
    if _library is None:
        with _engine_lock:
            if _library is None:
                _library = TemplateLibrary()
    return _library


# ---------------------------------------------------------------------------
# workflow_tool dispatcher
# ---------------------------------------------------------------------------


def workflow_tool(action: str = "list", **kwargs) -> str:
    """Dispatcher for the FRIDAY workflow tool system.

    Provides a unified interface for managing workflows through
    a single entry point. All actions return JSON strings.

    Supported actions:
        list - List all registered workflows.
        create - Create a workflow from step configs.
        run - Run a workflow by ID.
        status - Get workflow status and last execution.
        history - Get execution history.
        templates - List available templates.
        create_from_template - Create from a template.
        save - Save workflow to JSON file.
        load - Load workflow from JSON file.
        delete - Delete a workflow.
        clone - Clone a workflow.
        validate - Validate workflow structure.
        step_info - Get info about a specific step.

    Args:
        action: The action to perform.
        **kwargs: Action-specific parameters.

    Returns:
        JSON string with the action result.
    """
    engine = _get_engine()
    library = _get_library()

    try:
        if action == "list":
            result = engine.list_workflows()
            return json.dumps(
                {"status": "ok", "workflows": result}, default=str
            )

        elif action == "create":
            name = kwargs.get("name", "Unnamed Workflow")
            description = kwargs.get("description", "")
            steps_json = kwargs.get("steps_json", "[]")
            if isinstance(steps_json, str):
                steps_config = json.loads(steps_json)
            else:
                steps_config = steps_json
            wf = engine.create_workflow(name, description, steps_config)
            errors = wf.validate()
            if errors:
                return json.dumps({"status": "error", "errors": errors})
            return json.dumps(
                {"status": "ok", "workflow": wf.to_json()}, default=str
            )

        elif action == "run":
            workflow_id = kwargs.get("workflow_id", "")
            initial_ctx = kwargs.get("initial_context_json", "{}")
            if isinstance(initial_ctx, str):
                initial_context = json.loads(initial_ctx)
            else:
                initial_context = initial_ctx
            result = engine.run_workflow(workflow_id, initial_context)
            return json.dumps(
                {"status": "ok", "result": result.to_dict()},
                default=str,
            )

        elif action == "status":
            workflow_id = kwargs.get("workflow_id", "")
            wf = engine.get_workflow(workflow_id)
            if wf is None:
                return json.dumps({
                    "status": "error",
                    "error": f"Workflow '{workflow_id}' not found",
                })
            history = engine.get_history(workflow_id)
            latest = history[-1] if history else None
            return json.dumps({
                "status": "ok",
                "workflow": wf.to_json(),
                "last_execution": latest,
            }, default=str)

        elif action == "history":
            workflow_id = kwargs.get("workflow_id")
            history = engine.get_history(workflow_id)
            return json.dumps(
                {"status": "ok", "history": history}, default=str
            )

        elif action == "templates":
            templates = library.list_templates()
            return json.dumps(
                {"status": "ok", "templates": templates}, default=str
            )

        elif action == "create_from_template":
            template_name = kwargs.get("template_name", "")
            overrides_raw = kwargs.get("overrides_json", "{}")
            if isinstance(overrides_raw, str):
                overrides = json.loads(overrides_raw)
            else:
                overrides = overrides_raw
            wf = library.create_from_template(template_name, overrides)
            with _engine_lock:
                engine.workflows[wf.id] = wf
            return json.dumps(
                {"status": "ok", "workflow": wf.to_json()}, default=str
            )

        elif action == "save":
            workflow_id = kwargs.get("workflow_id", "")
            path = kwargs.get("path", "")
            engine.save_workflow(workflow_id, path)
            return json.dumps({
                "status": "ok",
                "message": f"Workflow saved to {path}",
            })

        elif action == "load":
            path = kwargs.get("path", "")
            wf = engine.load_workflow(path)
            return json.dumps(
                {"status": "ok", "workflow": wf.to_json()}, default=str
            )

        elif action == "delete":
            workflow_id = kwargs.get("workflow_id", "")
            deleted = engine.delete_workflow(workflow_id)
            if deleted:
                return json.dumps({
                    "status": "ok",
                    "message": f"Workflow '{workflow_id}' deleted",
                })
            return json.dumps({
                "status": "error",
                "error": f"Workflow '{workflow_id}' not found",
            })

        elif action == "clone":
            workflow_id = kwargs.get("workflow_id", "")
            new_name = kwargs.get("new_name", "Cloned Workflow")
            cloned = engine.clone_workflow(workflow_id, new_name)
            return json.dumps(
                {"status": "ok", "workflow": cloned.to_json()},
                default=str,
            )

        elif action == "validate":
            workflow_id = kwargs.get("workflow_id", "")
            wf = engine.get_workflow(workflow_id)
            if wf is None:
                return json.dumps({
                    "status": "error",
                    "error": f"Workflow '{workflow_id}' not found",
                })
            errors = wf.validate()
            return json.dumps({
                "status": "ok",
                "valid": len(errors) == 0,
                "errors": errors,
            })

        elif action == "step_info":
            workflow_id = kwargs.get("workflow_id", "")
            step_id = kwargs.get("step_id", "")
            wf = engine.get_workflow(workflow_id)
            if wf is None:
                return json.dumps({
                    "status": "error",
                    "error": f"Workflow '{workflow_id}' not found",
                })
            step = wf.get_step(step_id)
            if step is None:
                return json.dumps({
                    "status": "error",
                    "error": f"Step '{step_id}' not found",
                })
            return json.dumps(
                {"status": "ok", "step": step.to_dict()}, default=str
            )

        else:
            return json.dumps({
                "status": "error",
                "error": f"Unknown action: {action}",
                "valid_actions": [
                    "list", "create", "run", "status", "history",
                    "templates", "create_from_template", "save",
                    "load", "delete", "clone", "validate",
                    "step_info",
                ],
            })

    except json.JSONDecodeError as exc:
        return json.dumps({
            "status": "error",
            "error": f"JSON decode error: {exc}",
        })
    except KeyError as exc:
        return json.dumps({
            "status": "error",
            "error": f"Key error: {exc}",
        })
    except FileNotFoundError as exc:
        return json.dumps({
            "status": "error",
            "error": f"File not found: {exc}",
        })
    except Exception as exc:
        return json.dumps({
            "status": "error",
            "error": f"Unexpected error: {exc}",
        })


# ---------------------------------------------------------------------------
# Module convenience exports
# ---------------------------------------------------------------------------

__all__ = [
    "StepResult",
    "WorkflowResult",
    "Step",
    "Workflow",
    "WorkflowEngine",
    "TemplateLibrary",
    "ContextManager",
    "workflow_tool",
    "apply_transform",
    "TRANSFORM_FUNCTIONS",
]
