with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    stripped = line.rstrip('\n')
    if not stripped.strip():
        new_lines.append('')
        continue
    
    # Count leading spaces
    indent = len(stripped) - len(stripped.lstrip())
    content = stripped.lstrip()
    
    # Determine proper indentation
    if content.startswith('def deep_research_streaming'):
        proper_indent = 0
    elif content.startswith('try:') or content.startswith('except') or content.startswith('else:') or content.startswith('finally:'):
        proper_indent = 4
    elif content.startswith('class '):
        proper_indent = 4
    elif indent == 0 and not content.startswith('#'):
        # Inside function - default to 4
        proper_indent = 4
    else:
        proper_indent = indent
    
    new_lines.append(' ' * proper_indent + content)

with open('deep_search_streaming.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print('Fixed deep_search_streaming.py')

# Now update friday_tools.py
import subprocess
subprocess.run(['git', 'checkout', '0af39bf', '--', 'friday_tools.py'])

with open('friday_tools.py', 'r', encoding='utf-8') as f:
    tools = f.read()

with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    ds = f.read()

with open('friday_tools.py', 'a', encoding='utf-8') as f:
    f.write('\n\n# ─── DEEP RESEARCH STREAMING ────────────────────────────────\n\n')
    f.write(ds)
    f.write('\n')

print('Updated friday_tools.py')

# Verify
try:
    import sys
    sys.path.insert(0, '.')
    import friday_tools as ft
    print('Import OK! deep_search_streaming:', hasattr(ft, 'deep_search_streaming'))
except Exception as e:
    print('Import failed:', e)
