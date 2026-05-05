import re

with open('friday_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

# New tools to add
new_tools = {
    'switch_llm': 'ft.switch_llm',
    'list_llms': 'ft.list_llms',
    'github_list_files': 'ft.github_list_files',
    'github_read_file': 'ft.github_read_file',
    'github_write_file': 'ft.github_write_file',
    'github_create_branch': 'ft.github_create_branch',
    'github_create_pr': 'ft.github_create_pr',
    'chain_commands': 'ft.chain_commands',
    'save_workflow': 'ft.save_workflow',
    'list_workflows': 'ft.list_workflows',
    'run_workflow': 'ft.run_workflow',
    'optimize_research': 'ft.optimize_research',
    'analyze_topic': 'ft.analyze_topic',
    'learn_trust': 'ft.learn_trust',
    'get_trust_profile': 'ft.get_trust_profile',
}

# Add to TOOL_MAP
for tool_name, tool_ref in new_tools.items():
    if tool_name not in content:
        # Add after last tool in TOOL_MAP
        content = content.replace(
            "    'deep_research_streaming': ft.deep_research_streaming,",
            f"    'deep_research_streaming': ft.deep_research_streaming,\n    '{tool_name}': {tool_ref},"
        )
        print(f'Added {tool_name} to TOOL_MAP')

# Add function declarations for new tools
new_declarations = '''
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
    # GitHub Integration
    types.FunctionDeclaration(
        name="github_list_files",
        description="List files in GitHub repository.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING, description="Path in repo (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="github_read_file",
        description="Read a file from GitHub repository.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING, description="File path in repo"),
            },
            required=["path"],
        ),
    ),
    types.FunctionDeclaration(
        name="chain_commands",
        description="Execute chained commands (supports &&, ||, | operators).",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "chain": types.Schema(type=types.Type.STRING, description="Chained command string"),
            },
            required=["chain"],
        ),
    ),
    types.FunctionDeclaration(
        name="optimize_research",
        description="Optimize research strategy using ML.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(type=types.Type.STRING, description="Research topic"),
                "depth": types.Schema(type=types.Type.INTEGER, description="Initial depth (1-5)"),
            },
            required=["topic"],
        ),
    ),
    types.FunctionDeclaration(
        name="learn_trust",
        description="Learn from interaction to update trust ML model.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user": types.Schema(type=types.Type.STRING, description="User name"),
                "command": types.Schema(type=types.Type.STRING, description="Command executed"),
                "success": types.Schema(type=types.Type.BOOLEAN, description="Success status"),
                "sentiment": types.Schema(type=types.Type.STRING, description="Sentiment: positive/neutral/negative"),
            },
            required=["user", "command"],
        ),
    ),
'''

# Find where to insert declarations (after deep_research_streaming declaration)
if 'deep_research_streaming' in content and new_declarations.strip() not in content:
    # Find last closing paren of deep_research_streaming declaration
    idx = content.find('name="deep_research_streaming"')
    if idx != -1:
        depth = 0
        for i in range(idx, len(content)):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    content = content[:i+1] + ',' + new_declarations + content[i+1:]
                    print('Added function declarations')
                    break

with open('friday_live.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated friday_live.py with all new tools')
