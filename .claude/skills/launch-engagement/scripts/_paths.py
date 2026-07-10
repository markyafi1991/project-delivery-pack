"""Import path bootstrap for launch-engagement scripts."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parents[3]

for path in (SCRIPT_DIR, VAULT_ROOT / "scripts"):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
