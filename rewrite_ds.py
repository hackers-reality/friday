import re

# Read original file
with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Split into lines
lines = content.split('\n')
new_lines = []
i = 0
base_indent = 0  # Function def at 0 indent
func_indent = 4  # Function body
try_indent = 8   # Inside try/except

while i < len(lines):
    line = lines[i]
    
    # Skip the module docstring at top
    if i == 0 and line.strip().startswith('"""'):
        new_lines.append(line)
        i += 1
        continue
    
    # Skip empty lines
    if not line.strip():
        new_lines.append('')
        i += 1
        continue
    
    # Function definition
    if line.strip().startswith('def deep_research_streaming'):
        new_lines.append(line.strip())
        i += 1
        continue
    
    # Docstring (right after def)
    if line.strip().startswith('"""'):
        # This is the function docstring - indent by func_indent
        new_lines.append(' ' * func_indent + line.strip())
        i += 1
        continue
    
    # try:
    if line.strip().startswith('try:'):
        new_lines.append(' ' * func_indent + 'try:')
        i += 1
        continue
    
    # except:
    if line.strip().startswith('except'):
        new_lines.append(' ' * func_indent + line.strip())
        i += 1
        continue
    
    # Inside try/except - indent more
    if i > 0:
        prev_line = lines[i-1].strip() if i > 0 else ''
        if prev_line in ('try:', 'except Exception as e:') or prev_line.startswith('except'):
            new_lines.append(' ' * try_indent + line.strip())
            i += 1
            continue
    
    # Default: indent by func_indent
    new_lines.append(' ' * func_indent + line.strip())
    i += 1

# Write back
with open('deep_search_streaming.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print('Done - checking...')
# Quick check
with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if i <= 15:
            print(f'{i}: {repr(line)}')
