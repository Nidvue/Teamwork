"""A test module must not leak ``scripts/`` onto ``sys.path`` (T-0014).

Why: ``scripts/teamwork.py`` is the CLI and ``src/teamwork/`` is the package.
Putting ``scripts/`` on ``sys.path`` makes every later ``import teamwork`` in the
session resolve to the script instead of the package - a global mutation of
interpreter state, invisible in the file that causes it.

Measured on ``main`` (``f4043b2``): ``tests/unit/test_skill_sync.py`` did
``sys.path.insert(0, ...)`` at import time and never removed it, which made
``tests/unit/test_release_consistency.py::test_the_checker_is_loaded_by_path_not_by_sys_path``
fail on a clean checkout - the suite was red for a reason that had nothing to do
with the code under test.

These tests run in a **subprocess**, because the damage is import-time: by the
time this module is collected the leak has already happened, and a same-process
assertion could not tell a fresh import from the one pytest already did.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

_PROBE = """
import sys
sys.path.insert(0, {unit_dir!r})
before = list(sys.path)
import {module}
after = list(sys.path)
scripts = {scripts!r}
print("LEAKED", scripts in after)
print("ADDED", [p for p in after if p not in before])
"""


def _probe(module: str) -> tuple[bool, list[str]]:
    """Import ``module`` in a fresh interpreter and report what it added."""
    code = _PROBE.format(
        module=module, scripts=str(SCRIPTS), unit_dir=str(REPO_ROOT / "tests" / "unit")
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    leaked = False
    added: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("LEAKED "):
            leaked = line.split(" ", 1)[1] == "True"
        elif line.startswith("ADDED "):
            added = ast.literal_eval(line.split(" ", 1)[1])
    return leaked, added


def test_importing_the_skill_sync_tests_does_not_put_scripts_on_sys_path() -> None:
    """The regression: the module must not leave ``scripts/`` on ``sys.path``."""
    leaked, added = _probe("test_skill_sync")
    assert not leaked, f"importing test_skill_sync put {SCRIPTS} on sys.path"
    assert added == [], f"importing test_skill_sync changed sys.path: {added}"


def test_importing_the_skill_refresh_tests_does_not_put_scripts_on_sys_path() -> None:
    """The same contract for the module that imports the build tools."""
    leaked, added = _probe("test_skill_refresh")
    assert not leaked, f"importing test_skill_refresh put {SCRIPTS} on sys.path"
    assert added == [], f"importing test_skill_refresh changed sys.path: {added}"


def test_the_scripts_directory_is_not_on_the_path_of_a_fresh_interpreter() -> None:
    """Baseline: without the test modules, ``scripts/`` is not on ``sys.path``."""
    assert str(SCRIPTS) not in sys.path
