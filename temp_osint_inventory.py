"""Comprehensive OSINT tool inventory across all files"""
import re, os, ast, sys

def get_functions_with_signatures(filepath):
    """Parse Python file and extract function names and their arg lists."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    tree = ast.parse(content)
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            args = [arg.arg for arg in node.args.args]
            functions.append((node.name, node.lineno, args, node))
        elif isinstance(node, ast.AsyncFunctionDef):
            args = [arg.arg for arg in node.args.args]
            functions.append((node.name, node.lineno, args, node))
    return functions

files = [
    ('friday/tools_osint_extra.py', 'OSINT Utilities'),
    ('friday/email_analysis_tool.py', 'Email Forensics'),
    ('friday/tools/telegram_osint_tool.py', 'Telegram OSINT'),
    ('friday/tools/github_osint_tool.py', 'GitHub OSINT'),
    ('friday/tools/osint_enhanced_tools.py', 'Enhanced OSINT'),
    ('friday/tools/osint_advanced_tools.py', 'Advanced OSINT'),
    ('friday/tools/wifi_tools.py', 'WiFi Tools'),
    ('friday/tools/wifi_advanced_tools.py', 'Advanced WiFi'),
    ('friday/osint_summarizer.py', 'OSINT Summarizer'),
]

total = 0
for fp, label in files:
    if not os.path.exists(fp):
        continue
    funcs = get_functions_with_signatures(fp)
    print(f'=== {fp} ({label}) - {len(funcs)} functions ===')
    for name, lineno, args, _ in funcs:
        print(f'  L{lineno}: {name}({", ".join(args)})')
    print()
    total += len(funcs)

print(f'Total OSINT functions across all files: {total}')

# Check osint_agent.py for GhostAgent methods
fp = 'friday/osint_agent.py'
if os.path.exists(fp):
    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in ast.iter_child_nodes(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            print(f'=== {fp} ===')
            print(f'  Class {node.name}: methods = {methods}')
