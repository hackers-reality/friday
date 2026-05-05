with open('friday_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

print('deep_search_streaming in TOOL_MAP:', 'deep_search_streaming' in content)
print('deep_research_streaming in TOOL_MAP:', 'deep_research_streaming' in content)
print('send_notification in TOOL_MAP:', 'send_notification' in content)

# Check if we need to add it
if 'deep_research_streaming' not in content:
    print('Need to add deep_research_streaming to friday_live.py')
    
    # Add to TOOL_MAP
    content = content.replace(
        "    'send_notification': ft.send_notification,",
        "    'send_notification': ft.send_notification,\n    'deep_research_streaming': ft.deep_research_streaming,"
    )
    
    # Add function declaration
    decl = '''
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
    ),'''
    
    # Find where to insert (after send_notification declaration)
    last_idx = content.rfind('name="send_notification"')
    if last_idx != -1:
        # Find the closing paren of this declaration
        depth = 0
        for i in range(last_idx, len(content)):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    content = content[:i+1] + ',' + decl + content[i+1:]
                    break
    
    with open('friday_live.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated friday_live.py')
else:
    print('deep_research_streaming already in friday_live.py')
