import sys, os
sys.path.insert(0, 'E:/open-interpreter')
import friday.email_analysis_tool as m
funcs = sorted([n for n in dir(m) if not n.startswith('_') and callable(getattr(m, n, None))])
print(f'{len(funcs)} functions in email_analysis_tool.py')
for f in funcs:
    print(f'  {f}')
print(f'File size: {os.path.getsize("E:/open-interpreter/friday/email_analysis_tool.py")} bytes')
