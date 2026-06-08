import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from friday.paths import get_osint_extra_path
filepath = str(get_osint_extra_path())
lines = []
def L(s=""):
    lines.append(s)
