"""Acceptance-layer fixtures.

The shared test contract (Architecture.md section 8) says the suite points the
engine at the checkout with ``TEAMWORK_SKILL_DIR`` and isolates every test in
``tmp_path``. The top-level ``tests/conftest.py`` owns that for the whole suite;
this file repeats the guarantee locally so the acceptance layer stays correct
even when it is run on its own.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

REPO_ROOT = HERE.parents[1]
os.environ.setdefault("TEAMWORK_SKILL_DIR", str(REPO_ROOT))
