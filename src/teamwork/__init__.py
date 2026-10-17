"""Teamwork - an autonomous multi-agent company driven from one prompt.

The user talks only to the CEO; the CEO staffs the rest of the org and keeps the
lanes running until the goal is verified with evidence.

This package bundles both halves of the project:

* the workspace/engine (``teamwork.engine``) that every teammate runs, and
* the skill bundle (``SKILL.md``, ``roles/``, ``references/``, ``templates/``)
  that describes how the team works, shipped as package data under
  ``teamwork/data/`` when installed from a wheel.
"""

from __future__ import annotations

from .version import __version__

__all__ = ["__version__"]
