"""
Friday File Generator - Phase 5.1-5.3
Universal file generator with template library and coding sub-agent support.
"""
from __future__ import annotations__

import os
import json
import re
from typing import Optional, Dict, Any, List

# ─── Template Library (Phase 5.2) ──────────────────────────────────

_TEMPLATES = {
    # Python
    "python": {
        "extension": ".py",
        "template": '''#!/usr/bin/env python3
"""
{description}
"""
from __future__ import annotations__

import os
import sys

def main():
    """Main entry point."""
    print("Hello from {name}!")
    {body}

if __name__ == "__main__":
    main()
''',
    },
    "python_class": {
        "extension": ".py",
        "template": '''#!/usr/bin/env python3
"""
{name} - {description}
"""
from __future__ import annotations__

from typing import Any, Dict, List, Optional

class {class_name}:
    """{description}"""

    def __init__(self{init_params}):
        """Initialize {name}."""
        {init_body}

    def __repr__(self):
        return f"{class_name}({repr_params})"
''',
    },
    "python_test": {
        "extension": ".py",
        "template": '''#!/usr/bin/env python3
"""
Tests for {name}
"""
import pytest
from {module} import {function}

def test_{function}():
    """Test {function}."""
    result = {function}({test_args})
    assert result is not None
    {test_body}
''',
    },

    # JavaScript/TypeScript
    "javascript": {
        "extension": ".js",
        "template": '''/**
 * {description}
 */
{imports}

{export}function {name}({params}) {{
    {body}
}}

module.exports = {{ {name} }};
''',
    },
    "typescript": {
        "extension": ".ts",
        "template": '''/**
 * {description}
 */
{imports}

export interface {interface_name} {{
    {interface_body}
}}

export function {name}({params}): {return_type} {{
    {body}
}}
''',
    },
    "react_component": {
        "extension": ".tsx",
        "template": '''import React from 'react';

interface {name}Props {{
    {props_interface}
}}

/**
 * {description}
 */
export function {name}({{ {props} }}: {name}Props) {{
    return (
        <div className="{className}">
            {children}
        </div>
    );
}}
''',
    },

    # Web
    "html": {
        "extension": ".html",
        "template": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {styles}
    </style>
</head>
<body>
    {body}
</body>
</html>
''',
    },
    "css": {
        "extension": ".css",
        "template": '''/**
 * {description}
 */
{selector} {{
    {properties}
}}
''',
    },

    # Config/Data
    "json": {
        "extension": ".json",
        "template": '''{{
    "name": "{name}",
    "description": "{description}",
    {json_body}
}}
''',
    },
    "yaml": {
        "extension": ".yaml",
        "template": '''# {description}
name: {name}
description: {description}
{yaml_body}
''',
    },
    "toml": {
        "extension": ".toml",
        "template": '''# {description}

[package]
name = "{name}"
description = "{description}"
{config_body}
''',
    },
    "dockerfile": {
        "extension": "Dockerfile",
        "template": '''FROM {base_image}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {port}

CMD [{command}]
''',
    },
    "docker_compose": {
        "extension": ".yml",
        "template": '''version: '3.8'

services:
  {service_name}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      {env_vars}
    volumes:
      - .:/app
''',
    },

    # Documentation
    "markdown": {
        "extension": ".md",
        "template": '''# {name}

{description}

## Overview

{overview}

## Installation

{installation}

## Usage

{usage}

## API

{api_docs}
''',
    },
    "readme": {
        "extension": "README.md",
        "template": '''# {name}

{description}

## 🚀 Features

{features}

## 📦 Installation

```bash
{installation}
```

## 💡 Usage

```bash
{usage}
```

## 🤝 Contributing

{contributing}

## 📄 License

{license}
''',
    },

    # Shell
    "bash": {
        "extension": ".sh",
        "template": '''#!/bin/bash
# {description}

set -e

{script_body}
''',
    },
    "powershell": {
        "extension": ".ps1",
        "template": '''# {description}

Set-StrictMode -Version Latest

{script_body}
''',
    },

    # Database
    "sql": {
        "extension": ".sql",
        "template": '''-- {description}

-- Create table
{create_table}

-- Insert sample data
{insert_data}

-- Query
{queries}
''',
    },
    "migration": {
        "extension": ".sql",
        "template": '''-- Migration: {name}
-- Created: {timestamp}

BEGIN TRANSACTION;

{up_migration}

COMMIT;

-- Rollback
-- {down_migration}
''',
    },
}

# ─── File Type Detection ──────────────────────────────────────────────

def detect_file_type(filename: str, content_hint: str = "") -> str:
    """Detect the type of file to generate based on filename or content hint."""
    ext = os.path.splitext(filename)[1].lower()
    
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "react_component",
        ".jsx": "react_component",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".sh": "bash",
        ".ps1": "powershell",
        ".sql": "sql",
        ".dockerfile": "dockerfile",
        "dockerfile": "dockerfile",
    }
    
    if ext in ext_map:
        return ext_map[ext]
    
    # Check filename patterns
    basename = os.path.basename(filename).lower()
    if "dockerfile" in basename:
        return "dockerfile"
    if "compose" in basename and "yml" in basename:
        return "docker_compose"
    if "test_" in basename or "_test" in basename:
        return "python_test"
    if "migration" in basename:
        return "migration"
    if "readme" in basename:
        return "readme"
    
    # Check content hint
    if content_hint:
        if "class " in content_hint and "def " in content_hint:
            return "python"
        if "import " in content_hint and ("export " in content_hint or "function " in content_hint):
            return "javascript"
        if "interface " in content_hint or ": " in content_hint:
            return "typescript"
    
    return "python"  # Default


# ─── Universal File Generator (Phase 5.1) ──────────────────────

def generate_file(
    filename: str,
    description: str = "",
    template_name: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    content: Optional[str] = None,
) -> str:
    """
    Generate a file based on template or provided content.
    Returns the path to the generated file.
    """
    variables = variables or {}
    
    # Determine template
    if not template_name:
        template_name = detect_file_type(filename, content or "")
    
    # Get template
    template_data = _TEMPLATES.get(template_name)
    if not template_data and not content:
        return f"❌ Template '{template_name}' not found and no content provided."
    
    # Prepare variables
    base_name = os.path.splitext(os.path.basename(filename))[0]
    ext = template_data["extension"] if template_data else os.path.splitext(filename)[1] or ".txt"
    
    defaults = {
        "name": base_name,
        "class_name": "".join(word.capitalize() for word in base_name.split("_")),
        "module": base_name,
        "function": base_name,
        "description": description or f"{base_name} file",
        "title": base_name.replace("_", " ").title(),
        "body": content or "# TODO: Add implementation",
        "params": "",
        "return_type": "void",
        "imports": "",
        "export": "module.exports = ",
        "interface_name": base_name.capitalize() + "Props",
        "interface_body": "  // TODO: Define interface",
        "props": "",
        "props_interface": "// TODO: Define props",
        "className": base_name,
        "children": "",
        "styles": "/* TODO: Add styles */",
        "selector": ".container",
        "properties": "  /* TODO: Add properties */",
        "json_body": '  "version": "1.0.0"',
        "yaml_body": "# TODO: Add configuration",
        "config_body": 'version = "1.0.0"',
        "base_image": "python:3.12-slim",
        "port": "8000",
        "command": '"python", "app.py"',
        "service_name": base_name,
        "env_vars": '  - DEBUG=true',
        "overview": "TODO: Add overview",
        "installation": "pip install -r requirements.txt",
        "usage": "python main.py",
        "api_docs": "TODO: Add API documentation",
        "features": "- Feature 1\n- Feature 2",
        "contributing": "Pull requests welcome!",
        "license": "MIT",
        "script_body": "# TODO: Add script logic",
        "create_table": f"CREATE TABLE {base_name} (\n  id INTEGER PRIMARY KEY,\n  name TEXT\n);",
        "insert_data": f"INSERT INTO {base_name} (name) VALUES ('sample');",
        "queries": f"SELECT * FROM {base_name};",
        "timestamp": "2026-01-01",
        "up_migration": "-- TODO: Add migration steps",
        "down_migration": "-- TODO: Add rollback steps",
        "test_args": "",
        "test_body": "assert True",
        "init_params": ", **kwargs",
        "init_body": "pass",
        "repr_params": "**kwargs",
    }
    
    # Merge with user variables
    defaults.update(variables)
    
    # Generate content
    if template_data and not content:
        try:
            generated = template_data["template"].format(**defaults)
        except KeyError as e:
            return f"❌ Template formatting error: missing variable {e}"
    else:
        generated = content or defaults["body"]
    
    # Write file
    try:
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(generated)
        return f"✅ File generated: {filename}"
    except Exception as e:
        return f"❌ File write error: {e}"


def list_templates() -> str:
    """List all available templates."""
    lines = ["### FILE TEMPLATES", ""]
    for name, data in _TEMPLATES.items():
        lines.append(f"- **{name}** ({data['extension']})")
    return "\n".join(lines)


# ─── Coding Sub-Agent (Phase 5.3) ──────────────────────────────

def spawn_coding_agent(
    task: str,
    language: Optional[str] = None,
    framework: Optional[str] = None,
) -> str:
    """
    Spawn a coding sub-agent to handle complex multi-file generation.
    Uses LangGraph sub-graph or external agent (Claude Code style).
    """
    # This is a stub - in production, this would:
    # 1. Use LangGraph to create a specialized coding sub-agent
    # 2. Or spawn Claude Code / Codex CLI
    # 3. Return the generated code/files
    
    # For now, use Friday's existing tools + LLM
    try:
        from friday_tools import write_file
        from friday_graph import get_agent
        
        agent = get_agent()
        
        prompt = f"""You are a coding agent. Task: {task}
"""
        if language:
            prompt += f"Language: {language}\n"
        if framework:
            prompt += f"Framework: {framework}\n"
        
        prompt += """
Generate all necessary files with complete, working code.
Use the write_file tool to create each file.
"""
        
        # This would be handled by the LangGraph agent
        return f"🤖 Coding agent would process: {task}\n(LangGraph sub-agent integration pending)"
    
    except Exception as e:
        return f"❌ Coding agent error: {e}"


def multi_file_generate(specs: List[Dict[str, Any]]) -> str:
    """
    Generate multiple files based on specs.
    Each spec: {"filename": "app.py", "template": "python", "variables": {...}}
    """
    results = []
    for spec in specs:
        filename = spec.get("filename", "output.txt")
        template = spec.get("template")
        variables = spec.get("variables", {})
        description = spec.get("description", "")
        
        result = generate_file(
            filename=filename,
            description=description,
            template_name=template,
            variables=variables,
        )
        results.append(result)
    
    return "\n".join(results)


# ─── Integration with Friday Tools ─────────────────────────────────

def file_generator_tool(
    filename: str,
    description: str = "",
    template: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """Friday tool wrapper for file generation."""
    return generate_file(filename, description, template, content=content)


def coding_agent_tool(task: str) -> str:
    """Friday tool wrapper for coding agent."""
    return spawn_coding_agent(task)


if __name__ == "__main__":
    # Test
    print("Testing File Generator...")
    
    # Test Python file
    print(generate_file("test_app.py", "A test application"))
    
    # Test with template
    print(generate_file(
        "api_service.py",
        "REST API service",
        template_name="python_class",
        variables={"class_name": "APIService", "description": "REST API service class"}
    ))
    
    # List templates
    print("\n" + list_templates())
