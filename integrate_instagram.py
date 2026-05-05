"""Integrate Instagram messaging into friday_tools.py."""

with open('friday_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import for instagram_bot
import_section = """
# ─── Instagram Messaging ────────────────────────────────────────────────
try:
    from instagram_bot import instagram_message, instagram_search_and_message
except Exception as e:
    print(f"Instagram messaging not available: {e}")
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

print('Added Instagram messaging import to friday_tools.py')

# Verify
import sys
sys.path.insert(0, '.')
try:
    import friday_tools as ft
    print('friday_tools: OK')
    print('instagram_message:', hasattr(ft, 'instagram_message'))
except Exception as e:
    print(f'Error: {e}')
