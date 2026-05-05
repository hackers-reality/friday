with open('friday_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add to TOOL_MAP
if 'deep_search_streaming' not in content:
    # Add after send_notification in TOOL_MAP
    content = content.replace(
        "    'send_notification': ft.send_notification,",
        "    'send_notification': ft.send_notification,\n    'deep_search_streaming': ft.deep_search_streaming,"
    )
    print('Added to TOOL_MAP')
    
    # Add function declaration
    decl = '''
    types.FunctionDeclaration(
        name="deep_search_streaming",
        description="Deep research with real-time progress streaming. Use progress_callback for updates.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(type=types.Type.STRING, description="Research topic"),
                "url": types.Schema(type=types.Type.STRING, description="Optional starting URL"),
                "depth": types.Schema(type=types.Type.INTEGER, description="Search depth 1-5"),
            },
            required=["topic"],
        ),
    ),'''
    
    # Find last FunctionDeclaration and add after it
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
                    # Insert after this
                    content = content[:i+1] + ',' + decl + content[i+1:]
                    print('Added function declaration')
                    break
    
    with open('friday_live.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated friday_live.py')
else:
    print('Already present')
