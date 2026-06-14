#!/usr/bin/env python3
"""F.R.I.D.A.Y. — Type 'friday' to launch."""
import sys
import os

here = os.path.dirname(os.path.abspath(__file__))
ui_dir = os.path.join(here, "friday", "friday_ui")
sys.path.insert(0, ui_dir)
os.chdir(ui_dir)

from start import main
main()
