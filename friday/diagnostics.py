"""
FRIDAY Diagnostics & Benchmarks — system health checks, performance benchmarks,
and diagnostic report generation.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import time

from friday._paths import FRIDAY_MEMORY, FRIDAY_CONFIG


def _now() -> str:
    return datetime.now().isoformat()[:19]


def _check_path(name: str, path: str) -> dict:
    exists = os.path.exists(path)
    is_dir = os.path.isdir(path) if exists else False
    size = 0
    file_count = 0
    if exists and is_dir:
        try:
            for root, dirs, files in os.walk(path):
                file_count += len(files)
                size += sum(os.path.getsize(os.path.join(root, f)) for f in files if os.path.isfile(os.path.join(root, f)))
        except (PermissionError, OSError):
            pass
    return {
        "check": f"path:{name}",
        "status": "ok" if exists else "fail",
        "detail": f"{'Directory' if is_dir else 'File'} at {path}",
        "exists": exists,
        "is_dir": is_dir,
        "size_bytes": size,
        "file_count": file_count,
    }


def _check_module(name: str, import_path: str) -> dict:
    try:
        exec(f"import {import_path}")
        return {"check": f"module:{name}", "status": "ok", "detail": f"import {import_path}"}
    except ImportError as e:
        return {"check": f"module:{name}", "status": "fail", "detail": str(e)}


def _check_env_var(name: str) -> dict:
    val = os.environ.get(name)
    return {
        "check": f"env:{name}",
        "status": "ok" if val else "warn",
        "detail": val if val else "Not set",
    }


# ─── Core Diagnostics ────────────────────────────────────

def run_diagnostics() -> List[dict]:
    """Run all diagnostics checks. Returns list of check results."""
    results = []

    # Python / OS
    results.append({
        "check": "python_version",
        "status": "ok",
        "detail": sys.version.split()[0],
    })
    results.append({
        "check": "platform",
        "status": "ok",
        "detail": f"{platform.system()} {platform.release()}",
    })

    # Paths
    results.append(_check_path("FRIDAY_MEMORY", FRIDAY_MEMORY))
    results.append(_check_path("FRIDAY_CONFIG", FRIDAY_CONFIG))
    results.append(_check_path("memory_tree", os.path.join(FRIDAY_MEMORY, "memory_tree")))
    results.append(_check_path("snapshots", os.path.join(FRIDAY_MEMORY, "snapshots")))
    results.append(_check_path("sidecar_network", os.path.join(FRIDAY_MEMORY, "sidecar_network")))
    results.append(_check_path("cv_data", os.path.join(FRIDAY_MEMORY, "cv")))

    # Profile
    profile_path = os.path.join(FRIDAY_MEMORY, "user_profile.json")
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile = json.load(f)
        results.append({
            "check": "user_profile",
            "status": "ok",
            "detail": f"User: {profile.get('name', 'Unknown')}, "
                       f"Goals: {len(profile.get('goals', []))}, "
                       f"Skills: {len(profile.get('professional_skills', []))}",
        })
        # Schema validation
        try:
            from friday.profile_schema import validate_profile
            valid, errors = validate_profile(profile)
            results.append({
                "check": "profile_schema",
                "status": "ok" if valid else "fail",
                "detail": "Schema valid" if valid else f"Schema errors: {'; '.join(errors[:3])}",
            })
        except ImportError:
            results.append({"check": "profile_schema", "status": "warn", "detail": "Schema validator not available"})
    else:
        results.append({"check": "user_profile", "status": "fail", "detail": "Not found"})

    # Authority policy
    policy_path = os.path.join(FRIDAY_MEMORY, "authority_policy.json")
    if os.path.exists(policy_path):
        with open(policy_path) as f:
            policy = json.load(f)
        results.append({
            "check": "authority_policy",
            "status": "ok",
            "detail": f"Mode: {policy.get('mode', 'unknown')}, "
                       f"Approved tools: {len(policy.get('approved_tools', []))}",
        })
    else:
        results.append({"check": "authority_policy", "status": "warn", "detail": "Not configured (default: allow all)"})

    # Module imports
    modules = [
        ("friday", "friday"),
        ("live", "friday.live"),
        ("tools", "friday.tools"),
        ("cv_engine", "friday.cv_engine"),
        ("sidecar_network", "friday.sidecar_network"),
        ("ironman", "friday.ironman"),
        ("dashboard_api", "friday.dashboard_api"),
        ("memory_tree", "friday.memory_tree"),
        ("snapshots", "friday.snapshots"),
        ("autonomy", "friday.autonomy"),
        ("hooks", "friday.hooks"),
        ("caps", "friday.capabilities"),
    ]
    for name, import_path in modules:
        results.append(_check_module(name, import_path))

    # Hardware
    cpu_count = os.cpu_count() or 0
    results.append({"check": "cpu_cores", "status": "ok", "detail": str(cpu_count)})

    total, used, free = shutil.disk_usage(FRIDAY_MEMORY if os.path.exists(FRIDAY_MEMORY) else ".")
    results.append({
        "check": "disk_space",
        "status": "ok" if free > 100 * 1024 * 1024 else "warn",
        "detail": f"Free: {free // (1024**3)} GB, Total: {total // (1024**3)} GB",
    })

    # Config files
    config_files = ["model_router.json", "extension_registry.json", "autonomy.json"]
    for cf in config_files:
        cf_path = os.path.join(FRIDAY_CONFIG, cf)
        results.append(_check_path(f"config:{cf}", cf_path))

    return results


# ─── Report Formatting ───────────────────────────────────

def format_diagnostic_report(results: List[dict], verbose: bool = False) -> str:
    """Format diagnostic results into a human-readable report."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "ok")
    warnings = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")

    lines = [
        "=" * 60,
        "  FRIDAY DIAGNOSTIC REPORT",
        f"  Generated: {_now()}",
        "=" * 60,
        "",
        f"  Total checks: {total}",
        f"  Passed:       {passed}",
        f"  Warnings:     {warnings}",
        f"  Failed:       {failed}",
        "",
        "-" * 60,
    ]

    if failed:
        lines.append("  FAILURES:")
        for r in results:
            if r["status"] == "fail":
                lines.append(f"    ! {r['check']}: {r['detail']}")
        lines.append("")

    if warnings:
        lines.append("  WARNINGS:")
        for r in results:
            if r["status"] == "warn":
                lines.append(f"    ? {r['check']}: {r['detail']}")
        lines.append("")

    if verbose:
        lines.append("  ALL CHECKS:")
        for r in results:
            sym = "OK" if r["status"] == "ok" else ("WA" if r["status"] == "warn" else "!!")
            lines.append(f"    [{sym}] {r['check']}: {r['detail']}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ─── Benchmarks ──────────────────────────────────────────

def _measure_io_benchmark() -> dict:
    """Measure filesystem I/O performance."""
    import tempfile
    test_file = os.path.join(tempfile.gettempdir(), "_friday_bench_io.tmp")
    sizes = {
        "1KB": 1024,
        "1MB": 1024 * 1024,
        "10MB": 10 * 1024 * 1024,
    }
    results = {}

    for label, size in sizes.items():
        data = os.urandom(size)
        # Write
        start = time.perf_counter()
        with open(test_file, "wb") as f:
            f.write(data)
        write_time = time.perf_counter() - start

        # Read
        start = time.perf_counter()
        with open(test_file, "rb") as f:
            _ = f.read()
        read_time = time.perf_counter() - start

        results[label] = {
            "write_speed_mbps": round(size / write_time / (1024 * 1024), 2),
            "read_speed_mbps": round(size / read_time / (1024 * 1024), 2),
            "write_ms": round(write_time * 1000, 2),
            "read_ms": round(read_time * 1000, 2),
        }

    try:
        os.remove(test_file)
    except OSError:
        pass

    return results


def run_benchmarks() -> dict:
    """Run system benchmarks."""
    results = {
        "timestamp": _now(),
        "platform": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "cpu_cores": os.cpu_count(),
    }

    # I/O benchmark
    results["io"] = _measure_io_benchmark()

    # JSON serialization benchmark
    test_data = {"key": "value" * 1000, "numbers": list(range(1000))}
    start = time.perf_counter()
    for _ in range(100):
        json.dumps(test_data)
    results["json_serialize_ms"] = round((time.perf_counter() - start) * 10, 2)

    # Dict lookup benchmark
    big_dict = {str(i): i for i in range(10000)}
    start = time.perf_counter()
    for i in range(10000):
        _ = big_dict.get(str(i))
    results["dict_lookup_ns"] = round((time.perf_counter() - start) * 100, 2)

    return results


# ─── Tool Function ───────────────────────────────────────

def diagnostics_tool(action: str = "diagnostics", **kwargs) -> str:
    """FRIDAY tool: Diagnostics & Benchmarks.

    Actions:
        diagnostics    - Run system health checks
        benchmarks     - Run performance benchmarks
        report         - Run full diagnostics + benchmarks
    """
    if action == "diagnostics":
        results = run_diagnostics()
        verbose = kwargs.get("verbose", False)
        return format_diagnostic_report(results, verbose=verbose)

    if action == "benchmarks":
        results = run_benchmarks()
        import json as _json
        return _json.dumps(results, indent=2)

    if action == "report":
        diag = run_diagnostics()
        bench = run_benchmarks()
        report = {
            "timestamp": _now(),
            "diagnostics": {
                "total": len(diag),
                "passed": sum(1 for r in diag if r["status"] == "ok"),
                "warnings": sum(1 for r in diag if r["status"] == "warn"),
                "failed": sum(1 for r in diag if r["status"] == "fail"),
                "details": diag,
            },
            "benchmarks": bench,
        }
        import json as _json
        return _json.dumps(report, indent=2)

    return f"[FAIL] Unknown action: {action}"
