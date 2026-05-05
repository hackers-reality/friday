"""Integrate OpenCLI integration into friday_tools.py."""

with open('friday_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import for opencli_integration
import_section = """
# ─── OpenCLI Integration ────────────────────────────────────────────────
try:
    from opencli_integration import (opencli_navigate, opencli_click, 
                               opencli_type, opencli_extract, 
                               opencli_screenshot, instagram_message_opencli)
except Exception as e:
    print(f"OpenCLI integration not available: {e}")
"""

# Insert after last import
lines = content.split('\n')
last_import = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

lines.insert(last_import + 1, import_section)
content = '\n'.join(lines)

with open('friday_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added OpenCLI integration to friday_tools.py')

# Verify
import sys
sys.path.insert(0, '.')
try:
    import friday_tools as ft
    print('friday_tools: OK')
    print('opencli_navigate:', hasattr(ft, 'opencli_navigate'))
except Exception as e:
    print(f'Error: {e}')
