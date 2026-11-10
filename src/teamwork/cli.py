"""Console entry point: ``teamwork`` and ``python -m teamwork``."""

from __future__ import annotations

import sys

from .engine import main as _engine_main


def main(argv=None) -> int:
    """Run the Teamwork CLI and return its exit code."""
    return _engine_main(argv)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
