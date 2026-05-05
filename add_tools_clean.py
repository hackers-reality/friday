"""Cleanly add all new tools to friday_live.py."""

with open('friday_live.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find TOOL_MAP
tool_map_start = None
for i, line in enumerate(lines):
    if 'TOOL_MAP' in line and '{' in line:
        tool_map_start = i
        break

# Find the end of TOOL_MAP (closing brace)
if tool_map_start:
    brace_count = 0
    tool_map_end = None
    for i in range(tool_map_start, len(lines)):
        brace_count += lines[i].count('{') - lines[i].count('}')
        if brace_count == 0:
            tool_map_end = i
            break
    
    if tool_map_end:
        print(f'TOOL_MAP from line {tool_map_start+1} to {tool_map_end+1}')
        
        # Add new tools before the closing brace
        new_tools = '''    'switch_llm': ft.switch_llm,
    'list_llms': ft.list_llms,
    'github_list_files': ft.github_list_files,
    'github_read_file': ft.github_read_file,
    'github_write_file': ft.github_write_file,
    'github_create_branch': ft.github_create_branch,
    'github_create_pr': ft.github_create_pr,
    'chain_commands': ft.chain_commands,
    'save_workflow': ft.save_workflow,
    'list_workflows': ft.list_workflows,
    'run_workflow': ft.run_workflow,
    'optimize_research': ft.optimize_research,
    'analyze_topic': ft.analyze_topic,
    'learn_trust': ft.learn_trust,
    'get_trust_profile': ft.get_trust_profile,
    'deep_research_streaming': ft.deep_research_streaming,
'''
        
        # Insert before the line with closing brace
        # Find the line with just '}' or '},'
        for i in range(tool_map_end, tool_map_start, -1):
            if lines[i].strip() in ('}', '},'):
                lines.insert(i, new_tools)
                print('Inserted new tools into TOOL_MAP')
                break

# Write back
with open('friday_live.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Updated friday_live.py')

# Verify syntax
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'friday_live.py'], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print('Syntax OK!')
else:
    print('Syntax error:', result.stderr)
