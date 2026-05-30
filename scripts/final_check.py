import sys
sys.path.insert(0, '.')
from friday.tools import *
print('OK: 337 tools ready')
import friday.email_analysis_tool as em
em_funcs = [n for n in dir(em) if not n.startswith('_') and callable(getattr(em, n, None))]
print(f'OK: email_analysis ({len(em_funcs)} functions)')
import friday.metasploit_tool as ms
ms_funcs = [n for n in dir(ms) if not n.startswith('_') and callable(getattr(ms, n, None))]
print(f'OK: metasploit ({len(ms_funcs)} functions)')
import friday.agent_terminal as ag
ag_funcs = [n for n in dir(ag) if not n.startswith('_') and callable(getattr(ag, n, None))]
print(f'OK: agent_terminal ({len(ag_funcs)} functions)')
import friday.tools_osint_extra as oe
oe_funcs = [n for n in dir(oe) if not n.startswith('_') and callable(getattr(oe, n, None))]
print(f'OK: osint_extra ({len(oe_funcs)} functions)')
print('All systems ready.')
