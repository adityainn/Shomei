"""Unit test suite for Shomei Deletion Audit Engine."""

import sys
from pathlib import Path

code_dir = Path(__file__).resolve().parent.parent
if str(code_dir) not in sys.path:
    sys.path.insert(0, str(code_dir))
