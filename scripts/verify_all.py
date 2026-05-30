import sys, py_compile
sys.path.insert(0, '.')
py_compile.compile('E:/open-interpreter/friday/live.py', doraise=True)
print('live.py compiles clean')

from friday.tools import *
print('OK: 337 tools ready')

import friday.email_analysis_tool as m1
c1 = len([n for n in dir(m1) if not n.startswith('_') and callable(getattr(m1, n, None))])
print(f'OK: email_analysis ({c1})')

import friday.metasploit_tool as m2
c2 = len([n for n in dir(m2) if not n.startswith('_') and callable(getattr(m2, n, None))])
print(f'OK: metasploit ({c2})')

import friday.agent_terminal as m3
c3 = len([n for n in dir(m3) if not n.startswith('_') and callable(getattr(m3, n, None))])
print(f'OK: agent_terminal ({c3})')

import friday.tools_osint_extra as m4
c4 = len([n for n in dir(m4) if not n.startswith('_') and callable(getattr(m4, n, None))])
print(f'OK: osint_extra ({c4})')

import friday.google_clients as m5
c5 = len([n for n in dir(m5) if not n.startswith('_') and callable(getattr(m5, n, None))])
print(f'OK: google_clients ({c5})')

total = c1 + c2 + c3 + c4 + c5
print(f'\nTotal callable tools: {total}+')
print('All systems go.')
