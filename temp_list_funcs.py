import re, os, sys

files = [
    'friday/tools_osint_extra.py',
    'friday/email_analysis_tool.py',
    'friday/tools/telegram_osint_tool.py',
    'friday/tools/osint_extra_bridge.py',
    'friday/tools/osint_enhanced_tools.py',
    'friday/tools/osint_advanced_tools.py',
    'friday/tools/github_osint_tool.py',
    'friday/tools/wifi_tools.py',
    'friday/tools/wifi_advanced_tools.py',
    'friday/osint_summarizer.py',
    'friday/osint_agent.py',
]
for fp in files:
    if not os.path.exists(fp):
        print(f'{fp}: NOT FOUND')
        continue
    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    funcs = re.findall(r'^def (\w+)\s*\(', content, re.MULTILINE)
    classes = re.findall(r'^class (\w+)', content, re.MULTILINE)
    print(f'=== {fp} ===')
    print(f'  Classes: {classes}')
    print(f'  Functions ({len(funcs)}):')
    for fn in funcs:
        print(f'    - {fn}')
    print()
