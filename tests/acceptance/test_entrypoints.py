"""AC-2: the three documented entrypoints are equivalent and stdlib-only.

    python3 scripts/teamwork.py --version
    PYTHONPATH=src python3 -m teamwork --version
    teamwork --version            # installed console script, when present

All must print ``teamwork 1.0.0`` and exit 0. The shim must work from a bare
environment (it inserts ``src/`` itself); the module must work from a foreign
working directory; the console script is checked whenever it is installed.
"""

from __future__ import annotations

import os
import sys

import pytest
from cli_harness import (
    EXPECTED_VERSION,
    REPO_ROOT,
    build_env,
    console_script_path,
    run_console,
    run_module,
    run_shim,
)


def _assert_version(result) -> str:
    assert result.returncode == 0, result
    assert result.stdout.strip() == EXPECTED_VERSION, result
    assert result.stderr == "", result
    return result.stdout


def test_shim_version():
    """`python3 scripts/teamwork.py --version` prints teamwork 1.0.0."""
    _assert_version(run_shim(["--version"]))


def test_shim_works_without_pythonpath():
    """The shim bootstraps ``src/`` itself: no PYTHONPATH needed."""
    env = os.environ.copy()
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env.pop("PYTHONPATH", None)
    env.pop("TEAMWORK_ROOT", None)
    _assert_version(run_shim(["--version"], env=env))


def test_module_version():
    """`PYTHONPATH=src python3 -m teamwork --version` prints teamwork 1.0.0."""
    _assert_version(run_module(["--version"]))


def test_module_works_from_a_foreign_directory(tmp_path):
    """The package entrypoint must not depend on the checkout as cwd."""
    _assert_version(run_module(["--version"], cwd=tmp_path))


def test_module_runs_without_site(tmp_path):
    """No third-party runtime dependency: imports work under ``python -S``."""
    import subprocess

    env = os.environ.copy()
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import teamwork, teamwork.engine as e; print(teamwork.__version__)",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "1.0.0", proc.stdout


def test_console_script_version_when_installed():
    """`teamwork --version` when the console script is on PATH (skipped if not)."""
    if console_script_path() is None:
        pytest.skip("console script not installed; covered by scripts/verify_release.py")
    _assert_version(run_console(["--version"]))


def test_three_entrypoints_are_equivalent():
    """Every available entrypoint produces byte-identical version output."""
    shim = _assert_version(run_shim(["--version"]))
    module = _assert_version(run_module(["--version"]))
    assert shim == module

    console = run_console(["--version"])
    if console is not None:
        assert _assert_version(console) == shim


def test_shim_also_works_when_pythonpath_contains_src():
    """The shim must win over its own directory even when src/ is already on
    sys.path (the editable-install / PYTHONPATH=src case)."""
    env = build_env()  # PYTHONPATH = <repo>/src
    _assert_version(run_shim(["--version"], env=env))
