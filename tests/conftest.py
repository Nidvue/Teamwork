"""Shared pytest configuration for the Teamwork suite.

Responsibilities (see ``docs/Team/Architecture.md`` section 8):

1. make ``import teamwork`` work from a git checkout - put ``src/`` on
   ``sys.path`` before any test module imports the engine;
2. point the engine's bundle resolution at the repository root via
   ``TEAMWORK_SKILL_DIR`` *before* ``teamwork.engine`` is first imported
   (``engine.SKILL_DIR`` is frozen at import time);
3. give every test an isolated ``tmp_path`` workspace and no ambient team state
   (``TEAMWORK_ROOT`` / ``TEAMWORK_TEAM`` are cleared, the cwd is the tmp dir).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

# 1 + 2: import path and bundle root. Force the override (do not setdefault) so a
# stale value inherited from the caller can never redirect the engine elsewhere.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.environ["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository checkout (the skill bundle root)."""
    return REPO_ROOT


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """3: every test gets its own workspace and clean team environment.

    Autouse, so no test can accidentally act on the developer's real team tree
    or on the repository itself.
    """
    monkeypatch.delenv("TEAMWORK_ROOT", raising=False)
    monkeypatch.delenv("TEAMWORK_TEAM", raising=False)
    monkeypatch.setenv("TEAMWORK_SKILL_DIR", str(REPO_ROOT))
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def cli():
    """Run the CLI in-process; return its exit code (``die`` -> ``SystemExit``)."""
    from teamwork import engine

    def run(*argv) -> int:
        args = [str(a) for a in argv]
        try:
            return engine.main(args)
        except SystemExit as exc:  # ``die()`` raises SystemExit(code)
            code = exc.code
            return code if isinstance(code, int) else 1

    return run


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty project directory to bootstrap a team workspace in."""
    path = tmp_path / "SampleProject"
    path.mkdir()
    return path
