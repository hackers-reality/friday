"""Build script: Fix friday_tools.py with all modules."""

import sys
import os

# Step 1: Restore friday_tools.py from last good commit
print("Restoring friday_tools.py from a23da80...")
os.system('git checkout a23da80 -- friday_tools.py')

# Step 2: Read the restored file
with open('friday_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 3: Add imports for new modules after the last import line
new_imports = '''
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

# Find where to insert imports (after last import statement)
lines = content.split('\n')
last_import_idx = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import_idx = i

# Insert new imports after last import
lines.insert(last_import_idx + 1, new_imports)
content = '\n'.join(lines)

# Step 4: Append deep_search_streaming.py content
with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    ds_content = f.read()

content += '\n\n# ─── DEEP RESEARCH STREAMING ────────────────────────────────\n\n'
content += ds_content
content += '\n'

# Step 5: Write back
with open('friday_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("friday_tools.py updated with all modules")

# Step 6: Verify import
sys.path.insert(0, '.')
try:
    import friday_tools as ft
    print("Import OK!")
    # Check all modules
    modules = ['llm_manager', 'github', 'chainer', 'researcher', 'trust_ml', 'deep_research_streaming']
    for m in modules:
        print(f"  {m}: {hasattr(ft, m)}")
except Exception as e:
    print(f"Import failed: {e}")
