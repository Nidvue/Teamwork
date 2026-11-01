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

The probe puts this checkout's ``src`` on its own path, exactly as
``tests/conftest.py`` does for the suite (T-0019). It used to inherit whatever
``teamwork`` the interpreter had installed, and that measured a different tree
than the one under test: on this host the venv's editable ``.pth`` named
``D:\\Code\\Nidvue\\Teamwork\\src`` (a moved checkout, measured at the baseline),
and in a lane worktree a healthy editable install still resolves to the base
checkout's ``src``, never to the branch being tested.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
SRC_DIR = REPO_ROOT / "src"

_PROBE = """
import sys
sys.path.insert(0, {unit_dir!r})
sys.path.insert(0, {src_dir!r})
import teamwork
package = getattr(teamwork, "__file__", None) or ""
before = list(sys.path)
import {module}
after = list(sys.path)
scripts = {scripts!r}
print("LEAKED", scripts in after)
print("ADDED", [p for p in after if p not in before])
print("PACKAGE", package)
"""


def _probe(module: str, unit_dir: Path | None = None) -> tuple[bool, list[str], str]:
    """Import ``module`` in a fresh interpreter and report what it added.

    Returns ``(leaked, added, package)``, where ``package`` is the ``teamwork``
    module file the probe resolved - ``""`` when it resolved to a namespace
    package, the shape a stale editable install leaves behind.
    """
    code = _PROBE.format(
        module=module,
        scripts=str(SCRIPTS),
        unit_dir=str(unit_dir or (REPO_ROOT / "tests" / "unit")),
        src_dir=str(SRC_DIR),
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
    package = ""
    for line in proc.stdout.splitlines():
        if line.startswith("LEAKED "):
            leaked = line.split(" ", 1)[1] == "True"
        elif line.startswith("ADDED "):
            added = ast.literal_eval(line.split(" ", 1)[1])
        elif line.startswith("PACKAGE "):
            package = line.split(" ", 1)[1]
    return leaked, added, package


def test_importing_the_skill_sync_tests_does_not_put_scripts_on_sys_path() -> None:
    """The regression: the module must not leave ``scripts/`` on ``sys.path``."""
    leaked, added, _package = _probe("test_skill_sync")
    assert not leaked, f"importing test_skill_sync put {SCRIPTS} on sys.path"
    assert added == [], f"importing test_skill_sync changed sys.path: {added}"


def test_importing_the_skill_refresh_tests_does_not_put_scripts_on_sys_path() -> None:
    """The same contract for the module that imports the build tools."""
    leaked, added, _package = _probe("test_skill_refresh")
    assert not leaked, f"importing test_skill_refresh put {SCRIPTS} on sys.path"
    assert added == [], f"importing test_skill_refresh changed sys.path: {added}"


def test_the_probe_resolves_the_package_from_this_checkout() -> None:
    """The guard measures this tree, not whatever the interpreter has installed.

    T-0019: the probe inherited the ambient ``teamwork``. At the baseline that
    was a stale editable install (``ImportError`` before any ``sys.path``
    assertion ran); with the install repaired it is the base checkout's ``src``,
    which is still not the branch under test in a lane worktree. Either way the
    guard was measuring the wrong tree.
    """
    _leaked, _added, package = _probe("test_skill_refresh")
    resolved = Path(package).resolve() if package else None
    assert resolved is not None, (
        "the probe imported teamwork as a namespace package (no __file__), so it did "
        "not measure this checkout's src"
    )
    assert SRC_DIR.resolve() in resolved.parents, (
        f"the probe imported {resolved}, not this checkout's {SRC_DIR}"
    )


def test_the_probe_still_reports_a_module_that_leaks(tmp_path: Path) -> None:
    """The teeth: a module that inserts ``scripts/`` at import must be reported."""
    (tmp_path / "test_leaky.py").write_text(
        f"import sys\n\nsys.path.insert(0, {str(SCRIPTS)!r})\n", encoding="utf-8"
    )
    leaked, added, _package = _probe("test_leaky", unit_dir=tmp_path)
    assert leaked, f"the probe missed a module that inserted {SCRIPTS}"
    assert str(SCRIPTS) in added, f"the probe reported {added} as added"


def test_the_scripts_directory_is_not_on_the_path_of_a_fresh_interpreter() -> None:
    """Baseline: without the test modules, ``scripts/`` is not on ``sys.path``."""
    assert str(SCRIPTS) not in sys.path
