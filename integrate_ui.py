"""Integrate UI with friday_live.py."""

with open('friday_live.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add UI import after other imports
ui_import = '''
# ─── UI Dashboard ──────────────────────────────────────────────────────────
try:
    from friday_ui import ui_queue, update_ui, add_thought, add_tool_call, update_status, add_conversation_message
    UI_AVAILABLE = True
except Exception as e:
    print(f"UI Dashboard not available: {e}")
    UI_AVAILABLE = False
'''

# Find where to insert (after last import)
lines = content.split('\n')
last_import = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        last_import = i

lines.insert(last_import + 1, ui_import)
content = '\n'.join(lines)

# Add UI update calls in receive_loop where thoughts are generated
# Find where thoughts are printed and add UI update
if 'in_thought' in content and 'UI_AVAILABLE' not in content.split('in_thought')[1].split('def ')[0]:
    # Add UI update after thought printing
    old = "                if not in_thought and thought_text:"
    new = """                if not in_thought and thought_text:
                    if UI_AVAILABLE:
                        add_thought(thought_text)"""
    content = content.replace(old, new)
    print('Added thought UI update')

# Add UI update for tool calls
# Find where tools are executed
old_tool = "            print(f\"\\033[35mEXECUTING: {name}\\033[0m\")"
new_tool = """            print(f\"\\033[35mEXECUTING: {name}\\033[0m\")
            if UI_AVAILABLE:
                add_tool_call(name, args)"""
content = content.replace(old_tool, new_tool)
print('Added tool call UI update')

# Add UI update for conversation messages
# Find where Friday's responses are printed
old_resp = "                print(f\"\\nFriday: {text}\\n\")"
new_resp = """                print(f\"\\nFriday: {text}\\n\")
                if UI_AVAILABLE:
                    add_conversation_message('friday', text)"""
if old_resp in content:
    content = content.replace(old_resp, new_resp)
    print('Added conversation UI update')

# Write back
with open('friday_live.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Integrated UI with friday_live.py')

# Verify syntax
import py_compile
try:
    py_compile.compile('friday_live.py', doraise=True)
    print('Syntax OK!')
except py_compile.PyCompileError as e:
    print(f'Syntax error: {e}')
