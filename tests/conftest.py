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
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.environ["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)


TEAM_ENV = ("TEAMWORK_ROOT", "TEAMWORK_TEAM")


@pytest.fixture(scope="session", autouse=True)
def hermetic_team_environment() -> Iterator[None]:
    """3: no fixture, whatever its scope, is built with a lane's team environment.

    A lane process exports ``TEAMWORK_ROOT`` and ``TEAMWORK_TEAM``, and
    ``engine.team_slug`` reads ``TEAMWORK_TEAM``, so an in-process team lookup made
    from a module- or session-scoped fixture - which pytest builds *before* the
    function-scoped ``isolated_workspace`` below - resolved the live team instead
    of the fixture's throwaway project. Session scope is the earliest point that
    sees every other fixture, and it is restored on teardown so an outer run keeps
    its environment.
    """
    saved = {name: os.environ.pop(name) for name in TEAM_ENV if name in os.environ}
    yield
    os.environ.update(saved)


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
    for name in TEAM_ENV:
        monkeypatch.delenv(name, raising=False)
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
        except SystemExit as exc:
            code = exc.code
            return code if isinstance(code, int) else 1

    return run


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty project directory to bootstrap a team workspace in."""
    path = tmp_path / "SampleProject"
    path.mkdir()
    return path
