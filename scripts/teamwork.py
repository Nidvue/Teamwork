#!/usr/bin/env python3
"""Compatibility shim: run the Teamwork CLI straight from a git checkout.

``pip install .`` provides the ``teamwork`` console script and
``python -m teamwork``; this file keeps ``python3 scripts/teamwork.py ...``
working with nothing but the standard library, which is how the skill and the
team constitutions reference the engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir():
    _HERE = str(Path(__file__).resolve().parent)
    while _HERE in sys.path:
        sys.path.remove(_HERE)
    sys.path.insert(0, str(_SRC))

from teamwork.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
