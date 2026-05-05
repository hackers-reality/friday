import sys

# Read friday_tools.py (clean from git)
with open('friday_tools.py', 'r', encoding='utf-8') as f:
    tools = f.read()

# Read deep_search_streaming.py
with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    ds = f.read()

# Append with section header
with open('friday_tools.py', 'a', encoding='utf-8') as f:
    f.write('\n\n# ─── DEEP RESEARCH STREAMING ────────────────────────────────\n\n')
    f.write(ds)
    f.write('\n')

print('Done')
