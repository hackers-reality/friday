"""Add imports for new modules to friday_tools.py."""

with open('friday_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_section = """
# ─── LLM Manager ────────────────────────────────────────────────────────────
try:
    from llm_manager import llm_manager, switch_llm, list_llms
except Exception as e:
    print(f"LLM Manager not available: {e}")
    llm_manager = None

# ─── GitHub Integration ────────────────────────────────────────────────────
try:
    from friday_github import (github, github_list_files, github_read_file,
                              github_write_file, github_create_branch,
                              github_create_pr, github_self_modify)
except Exception as e:
    print(f"GitHub integration not available: {e}")

# ─── Command Chainer ───────────────────────────────────────────────────────
try:
    from command_chainer import (chainer, chain_commands, save_workflow,
                                list_workflows, run_workflow)
except Exception as e:
    print(f"Command chainer not available: {e}")

# ─── Autonomous Research ────────────────────────────────────────────────────
try:
    from autonomous_research import (researcher, optimize_research,
                                    analyze_topic, synthesize_research)
except Exception as e:
    print(f"Autonomous research not available: {e}")

# ─── Trust ML ───────────────────────────────────────────────────────────────
try:
    from trust_ml import (trust_ml, learn_trust, get_trust_profile,
                         adjust_trust_weights)
except Exception as e:
    print(f"Trust ML not available: {e}")
"""

# Find last import line
lines = content.split('\n')
last_import = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

lines.insert(last_import + 1, import_section)
content = '\n'.join(lines)

with open('friday_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added imports to friday_tools.py')

# Verify
import sys
sys.path.insert(0, '.')
try:
    import friday_tools as ft
    print('Import OK!')
    for attr in ['llm_manager', 'github', 'chainer', 'researcher', 'trust_ml']:
        print(f'  {attr}: {hasattr(ft, attr)}')
except Exception as e:
    print(f'Import failed: {e}')
