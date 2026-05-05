"""Final build script - properly construct friday_tools.py."""

import sys
import os

# Step 1: Restore from last good commit
print("[1/4] Restoring friday_tools.py from a23da80...")
os.system('git checkout a23da80 -- friday_tools.py')

# Step 2: Read the restored file
with open('friday_tools.py', 'r', encoding='utf-8') as f:
    original = f.read()

# Step 3: Add imports for new modules (insert before last line)
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

# Find where to insert (before the last line which is usually empty or a comment)
lines = original.split('\n')
# Find the second-to-last non-empty line
insert_idx = len(lines) - 1
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip():
        insert_idx = i
        break

# Insert the new imports before the end
lines.insert(insert_idx, new_imports)
content = '\n'.join(lines)

# Step 4: Append deep_search_streaming function (properly formatted)
with open('deep_search_streaming.py', 'r', encoding='utf-8') as f:
    ds_lines = f.readlines()

# Fix: make sure the function def is at 0-indent and body at 4-indent
fixed_ds = []
for line in ds_lines:
    stripped = line.rstrip('\n')
    if not stripped:
        fixed_ds.append('')
        continue
    # Calculate current indent
    indent = len(stripped) - len(stripped.lstrip())
    content_part = stripped.lstrip()
    
    # If this is the module docstring (first line), it should be at 0 indent
    if stripped.strip().startswith('"""') and not fixed_ds:
        fixed_ds.append(stripped)
    # If this is the function def, it should be at 0 indent
    elif content_part.startswith('def '):
        fixed_ds.append(content_part)
    # Everything else should be at 4-indent (function body)
    else:
        fixed_ds.append('    ' + content_part)

ds_content = '\n'.join(fixed_ds)

# Append to content
content += '\n\n# ─── DEEP RESEARCH STREAMING ────────────────────────────────\n\n'
content += ds_content
content += '\n'

# Step 5: Write back
with open('friday_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[2/4] friday_tools.py updated")

# Step 6: Verify import
sys.path.insert(0, '.')
try:
    import friday_tools as ft
    print("[3/4] Import OK!")
    check_items = ['llm_manager', 'github', 'chainer', 'researcher', 'trust_ml', 'deep_research_streaming']
    for item in check_items:
        status = "OK" if hasattr(ft, item) else "MISSING"
        print(f"  {item}: {status}")
except Exception as e:
    print(f"[3/4] Import FAILED: {e}")

print("[4/4] Build complete!")
