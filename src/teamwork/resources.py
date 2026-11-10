"""Locate the Nidvue Teamwork skill bundle.

The engine needs ``SKILL.md``, ``roles/``, ``references/``, ``templates/`` and a
runnable copy of itself. Those live in different places depending on how the
project was installed, so every lookup goes through this module.

Resolution order (first hit wins):

1. ``$TEAMWORK_SKILL_DIR`` - explicit override (used by the test suite)
2. ``teamwork/data``      - the packaged bundle inside an installed wheel
3. the repository root    - a normal git checkout (``<repo>/src/teamwork/``)
4. the package's parent   - a flattened copy of the package next to the bundle
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ENV_VAR = "TEAMWORK_SKILL_DIR"

#: A directory counts as the skill root when at least one of these is present.
_MARKERS = ("SKILL.md", "roles", "references", "templates")


def _looks_like_skill(path: Path | None) -> bool:
    if path is None or not path.is_dir():
        return False
    return any((path / marker).exists() for marker in _MARKERS)


def _packaged_data() -> Path | None:
    """``teamwork/data/`` inside an installed wheel; ``None`` when unavailable."""
    try:
        from importlib.resources import files  # Python 3.9+
    except ImportError:  # pragma: no cover - 3.9 always has it
        return None
    try:
        return Path(str(files("teamwork").joinpath("data")))
    except (ModuleNotFoundError, TypeError, ValueError, AttributeError, OSError):
        return None


def _checkout_root() -> Path:
    """``<repo>/src/teamwork/resources.py`` -> ``<repo>``."""
    here = Path(__file__).resolve()
    parents = here.parents
    return parents[2] if len(parents) > 2 else here.parent


def _candidates() -> list[Path]:
    raw = [
        _packaged_data(),
        _checkout_root(),
        Path(__file__).resolve().parent.parent,
    ]
    return [path for path in raw if path is not None]


def skill_root() -> Path:
    """Return the directory that holds ``SKILL.md`` and the bundle folders."""
    override = os.environ.get(ENV_VAR)
    if override:
        path = Path(override).expanduser()
        if path.is_dir():
            return path.resolve()
        raise FileNotFoundError(f"{ENV_VAR}={override!r} does not point at a directory")
    for candidate in _candidates():
        if _looks_like_skill(candidate):
            return candidate.resolve()
    # Nothing matched: fall back to the first existing candidate so that the
    # failure surfaces as "missing asset" on the command that needs it, not as
    # an ImportError while loading the package.
    for candidate in _candidates():
        if candidate.is_dir():
            return candidate.resolve()
    return Path(__file__).resolve().parent


def asset(*parts: str) -> Path:
    """A path inside the skill bundle, e.g. ``asset("roles", "developer.md")``."""
    return skill_root().joinpath(*parts)


def has_asset(name: str) -> bool:
    return asset(name).exists()


def self_invocation() -> str:
    """The command prefix a teammate should use to run this CLI, machine-local.

    Returns an absolute path when running from a checkout, so it is only safe for
    files that are never committed (``.pi/`` state such as ``StartHere.md``).
    For anything that lands in the repository use :func:`portable_invocation`.

    Preference order:

    1. the ``teamwork`` console script, when it is on ``PATH``;
    2. ``python3 <repo>/scripts/teamwork.py`` when running from a checkout;
    3. ``python3 -m teamwork`` for an installed package.
    """
    script = shutil.which("teamwork")
    if script:
        return "teamwork"
    shim = asset("scripts", "teamwork.py")
    if shim.is_file():
        return f"{sys.executable} {shim}"
    return f"{sys.executable} -m teamwork"


def portable_invocation() -> str:
    """A command prefix that is safe to commit - never a machine path.

    The team constitution (``AGENTS.md``) is committed and may be published, so
    it must not embed an absolute home path. Teammates on another machine install
    the package; a checkout runs the shim relative to the project root.
    """
    return "teamwork"
