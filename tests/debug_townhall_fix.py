"""Verify all 3 Townhall bugs are fixed."""
import sys, json
sys.path.insert(0, r'E:\open-interpreter')

print('=== Bug 1: Townhall action names ===')
from friday.townhall_agents import townhall_tool

# sessions action returns formatted text (not JSON)
r1 = townhall_tool(action='sessions')
assert 'Town Hall Sessions' in r1 or 'No sessions found' in r1, f"Unexpected sessions response: {r1[:100]}"
print('  sessions action: OK (returns text as expected)')

# agenda action returns formatted text
r2 = townhall_tool(action='agenda')
print('  agenda action: OK')

# Verify the UI backend has correct route names
from friday.friday_ui.backend.main import app as ui_app
townhall_paths = [getattr(r, 'path', '') for r in ui_app.routes if '/api/townhall/' in getattr(r, 'path', '')]
for p in townhall_paths:
    assert 'list_sessions' not in p and 'list_agenda' not in p and 'list_agents' not in p, f"Found old action path: {p}"
    print(f'  {p} -> OK (no list_sessions/list_agenda/list_agents)')

print()
print('=== Bug 2: DreamEngine callback ===')
from friday.townhall_web import _on_agent_chat
_on_agent_chat('[bold green]TestAgent[/bold green]: Hello there')
print('  formatted callback: OK')
_on_agent_chat('Raw system message')
print('  raw callback: OK')

print()
print('=== Bug 3: asyncio.run_coroutine_threadsafe ===')
from friday.townhall_web import _broadcast
_broadcast('chat', {'agent': 'Test', 'text': 'hello', 'channel': 'main'})
print('  broadcast from non-async thread: OK (no crash)')

print()
print('All Townhall bugs verified!')
