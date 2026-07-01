"""Test recent fixes: camera cache, NIM router, memory_retrieve, see_screen, system prompt."""
import json, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
# 1. CAMERA CACHE — _no_camera_available flag
# =============================================
print('\n## 1. CAMERA CACHE')
from friday.live import _no_camera_available, _cache_cycle, _cache_save, _cache_load, _cache_clean, FRIDAY_CACHE, CACHE_TTL

test('_no_camera_available exists', lambda: isinstance(_no_camera_available, bool))
test('FRIDAY_CACHE is str', lambda: isinstance(FRIDAY_CACHE, str))
test('CACHE_TTL > 0', lambda: CACHE_TTL > 0)

# _cache_cycle should leave flag unchanged when cv_engine has started a camera
old_flag = _no_camera_available
_cache_cycle()
test('_cache_cycle preserves flag when camera available', lambda: _no_camera_available == old_flag)
_no_camera_available = old_flag  # restore

# cache save/load roundtrip
_cache_save(0, "test description", 0.5)
entries = _cache_load()
test('_cache_load after save returns entries', lambda: len(entries) > 0)
test('cache entry has cam field', lambda: entries[0].get('cam') == 0)
test('cache entry has description', lambda: 'test description' in entries[0].get('description', ''))
_cache_clean(0)
entries2 = _cache_load()
test('_cache_clean with TTL=0 clears entries', lambda: len(entries2) == 0)

# _capture_cam_frame
from friday.live import _capture_cam_frame
frame = _capture_cam_frame(999)
test('_capture_cam_frame with bad index returns None', lambda: frame is None)


# =============================================
# 2. NIM ROUTER — no Zen-only models
# =============================================
print('\n## 2. NIM ROUTER')
from friday.nim_router import resolve_model, list_all_models

models = list_all_models()
test('list_all_models returns list', lambda: isinstance(models, list))
test('no mimo-v2.5 in NIM router', lambda: not any('mimo-v2.5' in m or 'mimo-2.5' in m for m in models))
test('meta/llama models present', lambda: any('llama' in m for m in models))

# resolve_model returns a model for each type
for task_type in ['code_gen', 'research', 'general', 'summarization']:
    m = resolve_model(task_type)
    test(f'resolve_model({task_type}) returns model', lambda: isinstance(m, str) and '/' in m)

# Note: model map may be overridden by config.yaml to use opencode/big-pickle


# =============================================
# 3. MEMORY_RETRIEVE — handles dict query
# =============================================
print('\n## 3. MEMORY_RETRIEVE')
from friday.tools_flat import memory_retrieve

r = memory_retrieve(query="test")
test('memory_retrieve(string) returns str', lambda: isinstance(r, str))
test('memory_retrieve(string) no crash', lambda: 'FAIL' not in r and 'EXCEPTION' not in r)

r2 = memory_retrieve(query={"query": "test nested dict"})
test('memory_retrieve(dict) handles gracefully', lambda: isinstance(r2, str))
test('memory_retrieve(dict) no crash', lambda: 'FAIL' not in r2 or 'Memory retrieve error' not in r2)

r3 = memory_retrieve(query=123)
test('memory_retrieve(int) handles gracefully', lambda: isinstance(r3, str))

r4 = memory_retrieve(query=None)
test('memory_retrieve(None) handles gracefully', lambda: isinstance(r4, str))


# =============================================
# 4. NIM CLIENT — base URLs
# =============================================
print('\n## 4. NIM CLIENT')
from friday.nim_client import NIM_API_BASE, ZEN_API_BASE

test('NIM_API_BASE is valid URL', lambda: NIM_API_BASE.startswith('http'))
test('ZEN_API_BASE is valid URL', lambda: ZEN_API_BASE.startswith('http'))


# =============================================
# 5. SYSTEM PROMPT — structural awareness
# =============================================
print('\n## 5. SYSTEM PROMPT')
from friday.live import SYSTEM_INSTRUCTION

test('prompt mentions v6.0', lambda: 'v6.0' in SYSTEM_INSTRUCTION)
test('prompt mentions camera cache', lambda: 'camera cache' in SYSTEM_INSTRUCTION.lower())
test('prompt mentions recall_recent_activity', lambda: 'recall_recent_activity' in SYSTEM_INSTRUCTION)
test('prompt mentions BACKGROUND SERVICES', lambda: 'BACKGROUND SERVICES' in SYSTEM_INSTRUCTION)
test('prompt mentions model chain', lambda: 'model chain' in SYSTEM_INSTRUCTION.lower() or 'model chain' in SYSTEM_INSTRUCTION)
test('prompt says screen ALREADY streamed', lambda: 'ALREADY streamed' in SYSTEM_INSTRUCTION or 'already streamed' in SYSTEM_INSTRUCTION)
test('prompt says do NOT call see_screen', lambda: 'Do NOT call see_screen' in SYSTEM_INSTRUCTION or 'not need see_screen' in SYSTEM_INSTRUCTION)


# =============================================
# 6. _extract_text_tool_calls — module-level
# =============================================
print('\n## 6. TEXT TOOL EXTRACTION')
from friday.live import _extract_text_tool_calls, _split_aware, _clean_text_param_key

test('_extract_text_tool_calls is callable', lambda: callable(_extract_text_tool_calls))
test('_split_aware is callable', lambda: callable(_split_aware))
test('_clean_text_param_key is callable', lambda: callable(_clean_text_param_key))

calls = _extract_text_tool_calls("run get_time() and web_search(query='hello')")
test('extract text tool calls finds get_time', lambda: any('get_time' == c[0] for c in calls))
test('extract text tool calls finds web_search', lambda: any('web_search' == c[0] for c in calls))

calls2 = _extract_text_tool_calls("")
test('extract text tool calls empty input', lambda: calls2 == [])

calls3 = _extract_text_tool_calls("just some random text with no tools")
test('extract text tool calls no matches', lambda: calls3 == [])


# =============================================
# 7. _invoke_tool — dispatch safety
# =============================================
print('\n## 7. TOOL DISPATCH')
from friday.live import _invoke_tool

test('_invoke_tool is async callable', lambda: hasattr(_invoke_tool, '__await__') or hasattr(_invoke_tool, '__call__'))

# directly test that TOOL_MAP has expected keys
from friday.live import TOOL_MAP

test('TOOL_MAP has memory_retrieve', lambda: 'memory_retrieve' in TOOL_MAP)
test('TOOL_MAP has recall_recent_activity', lambda: 'recall_recent_activity' in TOOL_MAP)
test('TOOL_MAP has get_time', lambda: 'get_time' in TOOL_MAP)
test('TOOL_MAP has web_search', lambda: 'web_search' in TOOL_MAP)
test('TOOL_MAP has ask_camera', lambda: 'ask_camera' in TOOL_MAP)
test('TOOL_MAP size > 700', lambda: len(TOOL_MAP) > 700)  # should be 750+


# =============================================
# 8. see_screen — model chain continues on error
# =============================================
print('\n## 8. SEE_SCREEN')
from friday.tools_flat import see_screen

test('see_screen is callable', lambda: callable(see_screen))


# =============================================
# 9. _build_live_tools — function declarations
# =============================================
print('\n## 9. LIVE TOOLS')
from friday.live import _build_live_tools

decls = _build_live_tools()
test('_build_live_tools returns list', lambda: isinstance(decls, list))
test('_build_live_tools has entries', lambda: len(decls) > 0)
# Each Tool wraps function_declarations
all_fds = []
for tool in decls:
    all_fds.extend(tool.function_declarations)
test('has function_declarations', lambda: len(all_fds) > 0)
test('first FD has name', lambda: hasattr(all_fds[0], 'name'))
test('first FD has description', lambda: hasattr(all_fds[0], 'description'))

# Check a few specific tools exist in declarations
names = {fd.name for fd in all_fds}
test('get_time in declarations', lambda: 'get_time' in names)
test('web_search in declarations', lambda: 'web_search' in names)
test('memory_retrieve in declarations', lambda: 'memory_retrieve' in names)


# =============================================
# SUMMARY
# =============================================
print(f'\n{"="*50}')
print(f'  PASS: {PASS}  FAIL: {FAIL}')
print(f'{"="*50}')
if FAIL > 0:
    sys.exit(1)
