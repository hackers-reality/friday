"""
Friday Self-Modification System - Friday can analyze and improve its own code.
IMPORTANT: This allows Friday to modify itself under strict safety constraints.
"""
from __future__ import annotations

import os
import ast
import inspect
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


# ─── Safety Validator ────────────────────────────────────#

class SafetyValidator:
    """Validates code changes for safety before applying."""
    
    FORBIDDEN_PATTERNS = [
        "import os",
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "eval(",
        "exec(",
        "open(",
        "__import__",
        "globals()",
        "locals()",
        "setattr(",
        "delattr(",
        "import shutil",
    ]
    
    FORBIDDEN_IMPORTS = [
        "shutil",
        "sys",
        "builtins",
        "ctypes",
    ]
    
    @classmethod
    def validate_code(cls, code: str) -> Dict[str, Any]:
        """Validate code for safety. Returns {safe: bool, issues: List[str]}."""
        issues = []
        
        # Check for forbidden patterns
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern in code:
                issues.append(f"Forbidden pattern: {pattern}")
        
        # Parse AST for deeper analysis
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in cls.FORBIDDEN_IMPORTS:
                            issues.append(f"Forbidden import: {alias.name}")
                
                # Check function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["eval", "exec", "__import__"]:
                            issues.append(f"Forbidden function call: {node.func.id}")
                            
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
        }


# ─── Code Analyzer ────────────────────────────────────#

class CodeAnalyzer:
    """Analyzes Friday's own code for improvement opportunities."""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.dirname(__file__))
        
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a Python file for improvements."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            analysis = {
                "file": filepath,
                "lines": len(code.splitlines()),
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "complexity": 0,
                "improvements": [],
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"] += 1
                    analysis["complexity"] += self._calculate_complexity(node)
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    analysis["imports"] += 1
            
            # Check for improvement opportunities
            if analysis["complexity"] > 10:
                analysis["improvements"].append("High complexity - consider refactoring")
            if analysis["lines"] > 500:
                analysis["improvements"].append("Large file - consider splitting")
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def find_all_friday_files(self) -> List[str]:
        """Find all Friday-related Python files."""
        files = []
        for py_file in self.base_path.glob("*.py"):
            if py_file.name.startswith("friday") or py_file.name.endswith("_tools.py"):
                files.append(str(py_file))
        return files
    
    def analyze_all(self) -> List[Dict[str, Any]]:
        """Analyze all Friday files."""
        results = []
        for filepath in self.find_all_friday_files():
            results.append(self.analyze_file(filepath))
        return results


# ─── Self-Modification Engine ────────────────────────────────────#

class SelfModificationEngine:
    """Allows Friday to safely modify its own code."""
    
    def __init__(self):
        self.validator = SafetyValidator()
        self.analyzer = CodeAnalyzer()
        self.backup_dir = Path("friday_memory/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def propose_improvement(self, filepath: str) -> Dict[str, Any]:
        """Analyze a file and propose improvements."""
        analysis = self.analyzer.analyze_file(filepath)
        
        if "error" in analysis:
            return analysis
        
        proposals = []
        
        # Propose based on analysis
        for improvement in analysis.get("improvements", []):
            proposals.append({
                "type": "refactor",
                "description": improvement,
                "target": filepath,
            })
        
        return {
            "file": filepath,
            "analysis": analysis,
            "proposals": proposals,
        }
    
    def apply_modification(self, filepath: str, new_code: str, reason: str = "") -> Dict[str, Any]:
        """Apply a code modification after safety checks."""
        # Validate safety
        safety = self.validator.validate_code(new_code)
        if not safety["safe"]:
            return {
                "success": False,
                "error": "Safety check failed",
                "issues": safety["issues"],
            }
        
        # Create backup
        backup_path = self._create_backup(filepath)
        
        try:
            # Write new code
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            # Verify it compiles
            with open(filepath, 'r', encoding='utf-8') as f:
                compile(f.read(), filepath, 'exec')
            
            return {
                "success": True,
                "backup": backup_path,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            # Rollback
            self._restore_backup(filepath, backup_path)
            return {
                "success": False,
                "error": str(e),
                "rolled_back": True,
            }
    
    def _create_backup(self, filepath: str) -> str:
        """Create a backup of a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(filepath).name
        backup_path = self.backup_dir / f"{filename}.{timestamp}.bak"
        
        with open(filepath, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return str(backup_path)
    
    def _restore_backup(self, filepath: str, backup_path: str):
        """Restore a file from backup."""
        with open(backup_path, 'r', encoding='utf-8') as src:
            with open(filepath, 'w', encoding='utf-8') as dst:
                dst.write(src.read())


# ─── Singleton Engine ────────────────────────────────────#

_engine: Optional[SelfModificationEngine] = None

def get_self_mod_engine() -> SelfModificationEngine:
    """Get or create the self-modification engine."""
    global _engine
    if _engine is None:
        _engine = SelfModificationEngine()
    return _engine


# ─── Tool Function for Friday ────────────────────────────────────#

def self_mod_tool(
    action: str = "analyze",
    filepath: str = None,
    new_code: str = None,
    reason: str = None,
) -> str:
    """
    Friday tool for self-modification (with safety checks).
    Actions: analyze, propose, apply, list_backups, restore
    """
    engine = get_self_mod_engine()
    
    if action == "analyze":
        if not filepath:
            # Analyze all files
            results = engine.analyzer.analyze_all()
            lines = ["### CODE ANALYSIS (ALL FILES)", ""]
            for r in results:
                if "error" in r:
                    lines.append(f"[FAIL] {r['file']}: {r['error']}")
                else:
                    lines.append(f"**{Path(r['file']).name}**")
                    lines.append(f"  Lines: {r['lines']} | Functions: {r['functions']} | Classes: {r['classes']}")
                    lines.append(f"  Complexity: {r['complexity']}")
                    if r["improvements"]:
                        lines.append(f"  Improvements: {len(r['improvements'])}")
                    lines.append("")
            return "\n".join(lines)
        
        result = engine.analyzer.analyze_file(filepath)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return json.dumps(result, indent=2)
    
    if action == "propose":
        if not filepath:
            return "[FAIL] Filepath required."
        result = engine.propose_improvement(filepath)
        return json.dumps(result, indent=2)
    
    if action == "apply":
        if not filepath or not new_code:
            return "[FAIL] Filepath and new_code required."
        result = engine.apply_modification(filepath, new_code, reason or "Manual update")
        if result["success"]:
            return f"[OK] Modification applied to {filepath}\nBackup: {result.get('backup', 'None')}"
        return f"[FAIL] Failed: {result.get('error', 'Unknown')}"
    
    if action == "list_backups":
        backups = list(engine.backup_dir.glob("*.bak"))
        if not backups:
            return "No backups found."
        lines = ["### BACKUPS", ""]
        for b in sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            lines.append(f"- {b.name}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Self-Modification System...")
    
    # Analyze all files
    print("\n--- Code Analysis ---")
    print(self_mod_tool("analyze"))
    
    # Test safety validator
    print("\n--- Safety Check ---")
    test_code = "print('hello')"
    result = SafetyValidator.validate_code(test_code)
    print(f"Safe: {result['safe']}, Issues: {result['issues']}")
    
    # Test unsafe code
    test_code_unsafe = "import os; os.system('rm -rf /')"
    result = SafetyValidator.validate_code(test_code_unsafe)
    print(f"Safe: {result['safe']}, Issues: {result['issues']}")
