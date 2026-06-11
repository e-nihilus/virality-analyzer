from __future__ import annotations

import sys
from pathlib import Path


# Allow importing `app.*` modules when running tests from repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
