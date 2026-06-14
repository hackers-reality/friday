"""Test codebase analyzer on sample_code folder."""
from friday.codebase_analyzer import codebase_analyzer_tool
import json

print('=== ANALYZE GOOD MODULE ===')
r = codebase_analyzer_tool(action='file', path='tests/sample_code/good_module.py')
print('Type:', type(r).__name__)
if isinstance(r, dict):
    print('Keys:', list(r.keys()))
    if 'issues' in r:
        print('Issues:', len(r['issues']))
elif isinstance(r, list):
    print('Issues:', len(r))
else:
    print('Result:', str(r)[:200])

print('\n=== ANALYZE BAD MODULE ===')
r = codebase_analyzer_tool(action='file', path='tests/sample_code/bad_module.py')
if isinstance(r, dict):
    print('Issues:', len(r.get('issues', [])))
    for i in r.get('issues', [])[:5]:
        print('  L%s: %s' % (i.get('line', '?'), i.get('message', '?')[:60]))
elif isinstance(r, list):
    print('Issues:', len(r))
    for i in r[:5]:
        print('  ', str(i)[:80])

print('\n=== ANALYZE PERF MODULE ===')
r = codebase_analyzer_tool(action='file', path='tests/sample_code/perf_module.py')
if isinstance(r, dict):
    print('Issues:', len(r.get('issues', [])))
elif isinstance(r, list):
    print('Issues:', len(r))

print('\n=== ANALYZE BUGGY MODULE ===')
r = codebase_analyzer_tool(action='file', path='tests/sample_code/buggy_module.py')
if isinstance(r, dict):
    print('Issues:', len(r.get('issues', [])))
elif isinstance(r, list):
    print('Issues:', len(r))

print('\n=== STATS ===')
r = codebase_analyzer_tool(action='stats')
print('Stats:', str(r)[:300])
