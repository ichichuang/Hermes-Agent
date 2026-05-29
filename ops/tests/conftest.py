from __future__ import annotations

import sys
from pathlib import Path

LIB_ROOT = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
