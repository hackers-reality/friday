#!/usr/bin/env python3
"""F.R.I.D.A.Y. — CLI launcher. Type 'friday' to start."""
import sys
import os

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)

from friday.__main__ import main

main()
