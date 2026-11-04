"""Single source of truth for the version string.

Kept in its own module so that ``--version`` and packaging metadata agree, and so
that importing ``teamwork`` stays cheap.
"""

from __future__ import annotations

__version__ = "1.5.2"

DIST_NAME = "teamwork-agents"
