"""Single source of truth for the version string.

Kept in its own module so that ``--version`` and packaging metadata agree, and so
that importing ``teamwork`` stays cheap.
"""

from __future__ import annotations

__version__ = "1.1.2"

#: Distribution name on PyPI. The name ``teamwork`` is already taken there, so
#: the project ships as ``teamwork-agents`` while importing as ``teamwork``.
DIST_NAME = "teamwork-agents"
