"""Integrate all new modules into friday_tools.py"""

import sys

# Read friday_tools.py
with open('friday_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if deep_search_streaming is accessible
try:
    sys.path.insert(0, '.')
    import friday_tools as ft
    print('friday_tools imported OK')
    print('deep_search_streaming accessible:', hasattr(ft, 'deep_search_streaming'))
except Exception as e:
    print('Import error:', e)
    sys.exit(1)

# Add imports for new modules after the last import line
import_section = '''
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
'''

# Find where to insert (after last import or at end of file)
lines = content.split('\n')
last_import_idx = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import_idx = i

# Insert after last import
lines.insert(last_import_idx + 1, import_section)
new_content = '\n'.join(lines)

with open('friday_tools.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Added imports to friday_tools.py')

# Verify again
try:
    # Need to reimport
    import importlib
    importlib.reload(ft)
    print('Reloaded friday_tools')
    print('New modules accessible:')
    for attr in ['llm_manager', 'github', 'chainer', 'researcher', 'trust_ml']:
        print(f'  {attr}: {hasattr(ft, attr)}')
except Exception as e:
    print('Verification error:', e)
