import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from friday.paths import get_friday_dir
import friday.email_analysis_tool as m
funcs = sorted([n for n in dir(m) if not n.startswith('_') and callable(getattr(m, n, None))])
print(f'{len(funcs)} functions in email_analysis_tool.py')
for f in funcs:
    print(f'  {f}')
email_path = str(get_friday_dir() / "email_analysis_tool.py")
print(f'File size: {os.path.getsize(email_path)} bytes')
