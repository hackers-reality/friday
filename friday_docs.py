"""
Friday Docs - Documentation generator.
Auto-generate documentation from code, markdown support.
"""
from __future__ import annotations

import os
import sys
import json
import ast
import inspect
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import re


# ─── Docstring Parser ────────────────────────────#

class DocstringParser:
    """Parse Python docstrings."""
    
    def parse(self, obj: Any) -> Dict[str, Any]:
        """Parse docstring from object."""
        docstring = inspect.getdoc(obj)
        
        if not docstring:
            return {"success": True, "description": "", "params": [], "returns": None}
        
        lines = docstring.split("\n")
        
        # Simple parsing
        description = []
        params = []
        returns = None
        examples = []
        in_example = False
        
        current_param = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Args:") or line.startswith("Parameters:"):
                continue
            elif line.startswith("Returns:"):
                in_example = False
                returns = ""
                continue
            elif line.startswith("Example") or line.startswith("Examples:"):
                in_example = True
                continue
            
            if in_example:
                examples.append(line)
                continue
            
            if line.startswith(":param") or line.startswith("param "):
                # Format: :param name: description
                match = re.match(r':?param\s+(\w+)\s*:\s*(.*)', line)
                if match:
                    current_param = {"name": match.group(1), "description": match.group(2), "type": None}
                    params.append(current_param)
            elif line.startswith(":type") or line.startswith("type "):
                match = re.match(r':?type\s+(\w+)\s*:\s*(.*)', line)
                if match and current_param and match.group(1) == current_param["name"]:
                    current_param["type"] = match.group(2)
            elif returns is not None and isinstance(returns, str):
                returns += line + "\n"
            else:
                description.append(line)
        
        return {
            "success": True,
            "description": " ".join(description).strip(),
            "params": params,
            "returns": returns.strip() if isinstance(returns, str) else returns,
            "examples": examples,
        }


# ─── Code Analyzer ────────────────────────────#

class CodeAnalyzer:
    """Analyze Python code for documentation."""
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a Python file."""
        try:
            with open(file_path, "r") as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(self._analyze_class(node))
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    if node.col_offset == 0:  # Top-level function
                        functions.append(self._analyze_function(node))
            
            return {
                "success": True,
                "classes": classes,
                "functions": functions,
                "file": file_path,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Analyze a class node."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                methods.append(self._analyze_function(item))
        
        return {
            "name": node.name,
            "methods": methods,
            "docstring": ast.get_docstring(node),
        }
    
    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function node."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        return {
            "name": node.name,
            "args": args,
            "docstring": ast.get_docstring(node),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        }


# ─── Documentation Generator ────────────────────────────#

class DocGenerator:
    """Generate documentation in various formats."""
    
    def generate_markdown(
        self,
        analysis: Dict[str, Any],
        title: str = None,
    ) -> str:
        """Generate Markdown documentation."""
        lines = []
        
        # Title
        title = title or Path(analysis.get("file", "module")).stem
        lines.append(f"# {title}")
        lines.append("")
        
        # Classes
        for cls in analysis.get("classes", []):
            lines.append(f"## Class: `{cls['name']}`")
            lines.append("")
            
            if cls.get("docstring"):
                lines.append(cls["docstring"])
                lines.append("")
            
            # Methods
            if cls.get("methods"):
                lines.append("### Methods")
                lines.append("")
                for method in cls["methods"]:
                    lines.append(f"#### `{method['name']}({', '.join(method['args'])})`")
                    if method.get("docstring"):
                        lines.append(method["docstring"])
                    lines.append("")
        
        # Functions
        for func in analysis.get("functions", []):
            lines.append(f"## Function: `{func['name']}({', '.join(func['args'])})`")
            lines.append("")
            
            if func.get("docstring"):
                lines.append(func["docstring"])
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_rst(self, analysis: Dict[str, Any], title: str = None) -> str:
        """Generate reStructuredText documentation."""
        lines = []
        
        title_text = title or Path(analysis.get("file", "module")).stem
        lines.append(title_text)
        lines.append("=" * len(title_text))
        lines.append("")
        
        # Classes
        for cls in analysis.get("classes", []):
            lines.append(f".. class:: {cls['name']}")
            lines.append("")
            
            if cls.get("docstring"):
                lines.append(f"    {cls['docstring']}")
                lines.append("")
            
            # Methods
            for method in cls.get("methods", []):
                lines.append(f"    .. method:: {method['name']}({', '.join(method['args'])})")
                if method.get("docstring"):
                    lines.append(f"        {method['docstring']}")
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_json(self, analysis: Dict[str, Any]) -> str:
        """Generate JSON documentation."""
        return json.dumps(analysis, indent=2)


# ─── Module Documentation ────────────────────────────#

class ModuleDocGenerator:
    """Generate documentation for Friday modules."""
    
    MODULES = [
        "friday_core",
        "friday_assistant",
        "friday_voice",
        "friday_web",
        "friday_automation",
        "friday_database",
        "friday_ai",
        "friday_tools",
        "friday_vision",
        "friday_security",
        "friday_monitor",
        "friday_scheduler",
        "friday_api",
        "friday_cloud",
        "friday_iot",
        "friday_dashboard",
        "friday_analytics",
        "friday_config",
        "friday_backup",
        "friday_nlp",
        "friday_integrations",
        "advanced_networking",
        "advanced_crypto",
    ]
    
    def generate_all(self, output_dir: str = "docs") -> Dict[str, Any]:
        """Generate documentation for all modules."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        generated = []
        
        for module_name in self.MODULES:
            try:
                import importlib
                module = importlib.import_module(module_name)
                
                # Analyze
                analyzer = CodeAnalyzer()
                # This is simplified - in reality, analyze the file
                
                # Generate docs
                generator = DocGenerator()
                
                # Find tool function
                tool_func = None
                for attr_name in dir(module):
                    if "tool" in attr_name.lower():
                        attr = getattr(module, attr_name)
                        if callable(attr):
                            tool_func = attr
                            break
                
                if tool_func:
                    # Generate doc for tool function
                    doc = inspect.getdoc(tool_func)
                    if doc:
                        lines = [
                            f"# {module_name}",
                            "",
                            f"Tool function: `{tool_func.__name__}`",
                            "",
                            doc,
                        ]
                        
                        output_file = output_path / f"{module_name}.md"
                        with open(output_file, "w") as f:
                            f.write("\n".join(lines))
                        
                        generated.append(str(output_file))
            except ImportError:
                continue
            except Exception as e:
                print(f"Error generating docs for {module_name}: {e}")
        
        return {
            "success": True,
            "generated": generated,
            "count": len(generated),
        }


# ─── Docs Tool for Friday ────────────────────────────#

def docs_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for documentation operations.
    Actions: status, generate_markdown, generate_rst, generate_json,
            module_docs, readme_update
    """
    params = params or {}
    
    if action == "status":
        lines = ["### DOCS STATUS", ""]
        lines.append("**Available Generators**:")
        lines.append("  - Markdown")
        lines.append("  - reStructuredText (rst)")
        lines.append("  - JSON")
        lines.append("")
        lines.append("**Available Features**:")
        lines.append("  - Python code analysis (AST)")
        lines.append("  - Docstring parsing")
        lines.append("  - Module documentation generation")
        return "\n".join(lines)
    
    if action == "generate_markdown":
        if not target:
            return "❌ File path required."
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(target)
        if not result["success"]:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
        
        generator = DocGenerator()
        title = params.get("title")
        md = generator.generate_markdown(result, title)
        
        output = params.get("output", f"{Path(target).stem}.md")
        with open(output, "w") as f:
            f.write(md)
        
        return f"### MARKDOWN DOCS\n\n✅ Generated: {output}"
    
    if action == "generate_rst":
        if not target:
            return "❌ File path required."
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(target)
        if not result["success"]:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
        
        generator = DocGenerator()
        title = params.get("title")
        rst = generator.generate_rst(result, title)
        
        output = params.get("output", f"{Path(target).stem}.rst")
        with open(output, "w") as f:
            f.write(rst)
        
        return f"### RST DOCS\n\n✅ Generated: {output}"
    
    if action == "generate_json":
        if not target:
            return "❌ File path required."
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(target)
        if not result["success"]:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
        
        generator = DocGenerator()
        json_doc = generator.generate_json(result)
        
        output = params.get("output", f"{Path(target).stem}.json")
        with open(output, "w") as f:
            f.write(json_doc)
        
        return f"### JSON DOCS\n\n✅ Generated: {output}"
    
    if action == "module_docs":
        output_dir = params.get("output_dir", "docs")
        generator = ModuleDocGenerator()
        result = generator.generate_all(output_dir)
        if result["success"]:
            lines = [f"### MODULE DOCS ({result['count']})", ""]
            for file in result["generated"][:10]:
                lines.append(f"  - {file}")
            return "\n".join(lines)
        else:
            return f"❌ Generation error: {result.get('error', 'Unknown')}"
    
    if action == "readme_update":
        # Simplified: update README with module list
        modules = ModuleDocGenerator.MODULES
        lines = ["# Friday", "", "## Modules", ""]
        for module in modules:
            lines.append(f"- {module}")
        
        with open("README.md", "w") as f:
            f.write("\n".join(lines))
        
        return "### README UPDATE\n\n✅ Updated README.md with module list"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Docs...\n")
    
    # Test status
    print("--- Docs Status ---")
    print(docs_tool("status"))
    
    # Test module docs generation
    print("\n--- Module Docs ---")
    print(docs_tool("module_docs", params={"output_dir": "docs"}))
