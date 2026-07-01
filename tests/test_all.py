"""Thorough testing of all FRIDAY modules — edge cases, errors, correctness."""
import json, sys, os, time

PASS = 0
FAIL = 0

def test(name, func, expect=None):
    global PASS, FAIL
    try:
        result = func()
        if expect is not None:
            ok = result == expect
        else:
            ok = result
        if ok:
            PASS += 1
            print('  OK  ' + name)
        else:
            FAIL += 1
            print('  FAIL ' + name + ' (got: ' + repr(result)[:80] + ')')
    except Exception as e:
        FAIL += 1
        print('  FAIL ' + name + ' - EXCEPTION: ' + str(e)[:100])


# =============================================
# 1. BOOTSTRAP
# =============================================
print('\n## 1. BOOTSTRAP')
from friday.bootstrap import bootstrap_tool

r = bootstrap_tool('status')
d = json.loads(r) if isinstance(r, str) else r
test('status has services', lambda: 'services' in d)
test('status has version', lambda: 'version' in d)
test('status has pid', lambda: 'pid' in d)
r = bootstrap_tool('nonexistent_action')
d = json.loads(r) if isinstance(r, str) else {}
test('invalid action handled', lambda: 'error' in d or 'FAIL' in str(r))


# =============================================
# 2. VALIDATION
# =============================================
print('\n## 2. VALIDATION')
from friday.validation_middleware import validation_tool

# Empty
r = validation_tool('verify_python', code='')
d = json.loads(r) if isinstance(r, str) else r
test('empty code', lambda: isinstance(d, dict) and 'passed' in d)

# None
try:
    r = validation_tool('verify_python', code=None)
    d = json.loads(r) if isinstance(r, str) else r
    test('None code', lambda: isinstance(d, dict) and 'error' in d or 'FAIL' in str(r))
except:
    test('None code', lambda: False)

# Syntax error
r = validation_tool('verify_python', code='def foo(:\n  pass')
d = json.loads(r) if isinstance(r, str) else r
test('syntax error detected', lambda: d.get('passed') == False)

# Valid complex
r = validation_tool('verify_python', code='class Foo:\n    def bar(self): return 42')
d = json.loads(r) if isinstance(r, str) else r
test('complex valid', lambda: d.get('passed') == True)

# HTML with script tag
r = validation_tool('verify_html', html_content='<html><body><script>alert(1)</script></body></html>')
d = json.loads(r) if isinstance(r, str) else r
test('HTML script tag detected', lambda: d.get('passed') == False)

# Empty HTML
r = validation_tool('verify_html', html_content='')
d = json.loads(r) if isinstance(r, str) else r
test('empty HTML', lambda: isinstance(d, dict) and 'passed' in d)

# Valid JSON
r = validation_tool('verify_json', code='{"key": [1, 2, 3]}')
d = json.loads(r) if isinstance(r, str) else r
test('valid JSON', lambda: d.get('passed') == True)

# Invalid JSON
r = validation_tool('verify_json', code='{"a": 1,}')
d = json.loads(r) if isinstance(r, str) else r
test('invalid JSON', lambda: d.get('passed') == False)

# CSV
r = validation_tool('verify_csv', code='name,age\nAlice,30')
d = json.loads(r) if isinstance(r, str) else r
test('valid CSV', lambda: d.get('passed') == True)


# =============================================
# 3. TOWNHALL
# =============================================
print('\n## 3. TOWNHALL')
from friday.townhall_agents import townhall_tool

r = townhall_tool(action='status')
d = json.loads(r) if isinstance(r, str) else r
test('status structure', lambda: 'agents_available' in d and 'total_sessions' in d)

r = townhall_tool(action='post', session_id='nonexistent', message='hi', agent='x')
test('post bad session', lambda: 'FAIL' in str(r) or 'not found' in str(r).lower())

r = townhall_tool(action='add_agenda', title='T', description='D', priority='high')
test('add agenda', lambda: '[OK]' in str(r))

r = townhall_tool(action='resolve_agenda', item_id='nonexistent')
test('resolve nonexistent', lambda: 'FAIL' in str(r) or 'not found' in str(r).lower())

r = townhall_tool(action='deliberate', topic='T', rounds=1)
test('deliberate', lambda: r is not None)


# =============================================
# 4. DASHBOARD
# =============================================
print('\n## 4. DASHBOARD')
from friday.dashboard_cli import dashboard_cli_tool

r = dashboard_cli_tool('status')
test('status text', lambda: isinstance(r, str) and len(r) > 20)
test('status has CPU', lambda: 'CPU' in r or 'cpu' in r)

r = dashboard_cli_tool('json')
d = json.loads(r) if isinstance(r, str) else r
test('json has data', lambda: 'system' in d or 'timestamp' in d)


# =============================================
# 5. MEMORY
# =============================================
print('\n## 5. MEMORY')
from friday.autonomous_memory import autonomous_memory_tool

r = autonomous_memory_tool(action='learn', text='')
d = json.loads(r) if isinstance(r, str) else r
test('learn empty', lambda: d.get('stored', 0) == 0)

r = autonomous_memory_tool(action='learn', text='hi')
d = json.loads(r) if isinstance(r, str) else r
test('learn short', lambda: d.get('stored', 0) == 0)

r = autonomous_memory_tool(action='learn', text='Python is a programming language.')
d = json.loads(r) if isinstance(r, str) else r
test('learn normal', lambda: d.get('stored', 0) > 0)

r = autonomous_memory_tool(action='recall', query='')
d = json.loads(r) if isinstance(r, str) else r
test('recall empty', lambda: isinstance(d, dict) and 'memories' in d)

r = autonomous_memory_tool(action='stats')
d = json.loads(r) if isinstance(r, str) else r
test('stats structure', lambda: 'total_memories' in d)


# =============================================
# 6. CODEBASE ANALYZER
# =============================================
print('\n## 6. CODEBASE ANALYZER')
from friday.codebase_analyzer import codebase_analyzer_tool

r = codebase_analyzer_tool(action='stats')
d = json.loads(r) if isinstance(r, str) else r
test('stats structure', lambda: 'total_files' in d and 'total_lines_of_code' in d)


# =============================================
# 7. TOWNHALL WEB
# =============================================
print('\n## 7. TOWNHALL WEB')
from friday.townhall_web import app as townhall_app, AgentNode, ChatChannel

# Module-level globals exist
test('app created', lambda: townhall_app is not None)
test('agent node model', lambda: callable(AgentNode))
test('chat channel model', lambda: callable(ChatChannel))

# Verify callback can handle formatted and raw strings
from friday.townhall_web import _on_agent_chat
try:
    _on_agent_chat("[bold green]TestAgent[/bold green]: Hello world")
    test('agent chat callback', lambda: True)
except Exception as e:
    test('agent chat callback', lambda: f"EXCEPTION: {e}" == "" and False)

try:
    _on_agent_chat("Raw system message")
    test('raw chat fallback', lambda: True)
except Exception as e:
    test('raw chat fallback', lambda: f"EXCEPTION: {e}" == "" and False)


print("\n## 7b. TOWNHALL ENGINE DREAM")
from friday.townhall_engine import DreamEngine
from friday.townhall_web import AgentNode
_test_channels = {"main": type('obj', (object,), {'messages': [], 'add_message': lambda s,a,m: None})()}
engine = DreamEngine({}, _test_channels, lambda msg: None)
test('engine created', lambda: engine is not None)
test('engine log', lambda: callable(engine.log))
test('engine start', lambda: callable(engine.start))
test('engine stop', lambda: callable(engine.stop))


# =============================================
# 8. API SERVER
# =============================================
print('\n## 8. API SERVER')
from friday.api_server import api_server_tool

r = api_server_tool('status')
test('status check', lambda: 'Running:' in r)



# =============================================
# 9. PLUGIN
# =============================================
print('\n## 9. PLUGIN')
from friday.plugins import plugin_tool

r = plugin_tool('load', plugin_name='nonexistent_xyz')
test('load bad plugin', lambda: 'FAIL' in r or 'not found' in r.lower())

r = plugin_tool('call', plugin_name='nonexistent', tool_name='foo')
test('call bad plugin', lambda: 'FAIL' in r or 'not loaded' in r.lower())

r = plugin_tool('list')
test('list', lambda: isinstance(r, str))

r = plugin_tool('stats')
test('stats', lambda: isinstance(r, str) and len(r) > 10)


# =============================================
# 10. CODE REVIEW
# =============================================
print('\n## 10. CODE REVIEW')
from friday.code_review import code_review_tool

r = code_review_tool('review', code='x = eval(input())\n', filename='bad.py')
d = json.loads(r)
test('eval detected', lambda: any('eval' in i.get('message', '').lower() for i in d.get('issues', [])))

r = code_review_tool('review', code='def add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n', filename='good.py')
d = json.loads(r)
test('clean code few issues', lambda: len(d.get('issues', [])) < 5)

r = code_review_tool('security_scan', code='API_KEY = "sk-1234567890"\n')
d = json.loads(r)
test('secrets detected', lambda: len(d.get('issues', [])) > 0)


# =============================================
# 11. WORKFLOW
# =============================================
print('\n## 11. WORKFLOW')
from friday.workflow_engine import workflow_tool, WorkflowEngine, TemplateLibrary

r = workflow_tool('list')
d = json.loads(r)
test('list ok', lambda: d.get('status') == 'ok')

r = workflow_tool('templates')
d = json.loads(r)
test('8+ templates', lambda: len(d.get('templates', [])) >= 8)

engine = WorkflowEngine()
wf = engine.create_workflow(
    name='Test', description='T',
    steps_config=[
        {'name': 's1', 'tool_name': 'validation_tool', 'tool_args': {'action': 'verify_python', 'code': 'x=1'}},
    ]
)
errors = wf.validate()
test('valid workflow', lambda: len(errors) == 0)

result = engine.run_workflow(wf.id)
test('run workflow', lambda: result.status == 'completed')

d = wf.to_json()
wf2 = type(wf).from_json(d)
test('serialize roundtrip', lambda: wf2.name == wf.name)

step = wf.steps[0]
step.condition = 'x > 5'
test('condition true', lambda: step.evaluate_condition({'x': 10}))
test('condition false', lambda: not step.evaluate_condition({'x': 2}))


# =============================================
# SUMMARY
# =============================================
print('\n' + '=' * 50)
print('RESULTS: %d passed, %d failed' % (PASS, FAIL))
