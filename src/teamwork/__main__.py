"""``python -m teamwork`` runs the same CLI as the installed console script."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
