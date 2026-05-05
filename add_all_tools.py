"""Add all new tools to friday_live.py properly."""

with open('friday_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New tools for TOOL_MAP
new_tools_map = '''
    'deep_research_streaming': ft.deep_research_streaming,
    'switch_llm': ft.switch_llm,
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
'''

# Find TOOL_MAP and add new tools before closing brace
# Find last tool in TOOL_MAP to add after
last_tool = "'send_notification': ft.send_notification,"
if last_tool in content:
    content = content.replace(
        last_tool,
        last_tool + new_tools_map
    )
    print('Added tools to TOOL_MAP')

# Now add function declarations for new tools
new_declarations = '''
    # Deep Research Streaming
    types.FunctionDeclaration(
        name="deep_research_streaming",
        description="Deep research with real-time progress streaming. Use progress_callback for updates.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(type=types.Type.STRING, description="Research topic"),
                "url": types.Schema(type=types.Type.STRING, description="Optional starting URL"),
                "depth": types.Schema(type=types.Type.INTEGER, description="Search depth 1-5", default=3),
            },
            required=["topic"],
        ),
    ),
    # LLM Manager
    types.FunctionDeclaration(
        name="switch_llm",
        description="Switch to a different LLM backend (gemini, claude, chatgpt, local).",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "llm_name": types.Schema(type=types.Type.STRING, description="LLM name: gemini, claude, chatgpt, local"),
            },
            required=["llm_name"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_llms",
        description="List available LLM backends.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
'''

# Find a good place to insert declarations (after send_notification declaration)
insert_after = 'name="send_notification"'
if insert_after in content and 'deep_research_streaming' not in content:
    # Find the end of send_notification declaration
    idx = content.find(insert_after)
    if idx != -1:
        # Find matching closing paren
        depth = 0
        for i in range(idx, len(content)):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    # Insert after this closing paren
                    insert_pos = i + 1
                    content = content[:insert_pos] + ',' + new_declarations + content[insert_pos:]
                    print('Added function declarations')
                    break

with open('friday_live.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated friday_live.py')

# Verify syntax
import py_compile
try:
    py_compile.compile('friday_live.py', doraise=True)
    print('Syntax OK!')
except py_compile.PyCompileError as e:
    print(f'Syntax error: {e}')
