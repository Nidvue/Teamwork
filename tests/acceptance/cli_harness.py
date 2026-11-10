"""Black-box harness for the acceptance layer.

Acceptance tests drive the CLI as a *subprocess* - never by importing the
engine - so they prove what a real user experiences:

* the three documented entrypoints behave identically,
* the full gate loop reaches STOP on a freshly initialised workspace,
* paths with spaces / non-ASCII characters and byte-identical (LF) output work.

Everything here is standard library only. ``shell=True`` is never used; every
process is spawned with ``sys.executable`` and an explicit environment.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

# ``tests/acceptance/cli_harness.py`` -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"

#: The exact line both ``--version`` and the ``version`` subcommand must print.
#: Read from the source of truth rather than hard-coded, so a version bump cannot
#: leave a stale expectation behind (a black-box harness must not import the
#: package it is testing).
_VERSION = re.search(
    r'__version__ = "([^"]+)"',
    (SRC_DIR / "teamwork" / "version.py").read_text(encoding="utf-8"),
).group(1)
EXPECTED_VERSION = f"teamwork {_VERSION}"

#: Roster used by the AC-10 flow. It deliberately staffs every layer that the
#: core gate needs (goal/system/unit/integration/acceptance).
DEFAULT_ROSTER = "ceo,architect,developer-1,tester-1,reviewer-1"

#: Required layers the acceptance flow declares for its single area. This is the
#: exact set of layers owned by the DEFAULT_ROSTER above.
DEFAULT_LAYERS = "goal,system,unit,integration,acceptance"


class Result:
    """A finished CLI invocation, kept small and printable for assertions."""

    def __init__(self, argv: Sequence[str], proc: subprocess.CompletedProcess):
        self.argv: list[str] = list(argv)
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr

    @property
    def output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")

    def __repr__(self) -> str:  # keeps failure messages useful
        return (
            f"Result(argv={self.argv!r}, rc={self.returncode},\n"
            f"  stdout={self.stdout!r},\n"
            f"  stderr={self.stderr!r})"
        )


def build_env(extra: Mapping[str, str] | None = None) -> dict:
    """A deterministic environment that points the engine at this checkout."""
    env = os.environ.copy()
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(SRC_DIR), prior) if p)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.pop("TEAMWORK_ROOT", None)  # never let an outer team tree leak in
    if extra:
        env.update({key: str(value) for key, value in extra.items()})
    return env


def _invoke(argv: Sequence[str], cwd: Path, env: Mapping[str, str]) -> Result:
    proc = subprocess.run(
        list(argv),
        cwd=str(cwd),
        env=dict(env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    return Result(argv, proc)


def run_shim(
    args: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None
) -> Result:
    """``python3 scripts/teamwork.py ...`` (the checkout compatibility shim).

    The shim's contract is to work from a bare checkout with no ``PYTHONPATH``
    (it bootstraps ``src/`` itself), so by default the environment drops
    ``PYTHONPATH``. Pass ``env=`` explicitly to exercise other setups.
    """
    if env is None:
        env = build_env()
        env.pop("PYTHONPATH", None)
    return _invoke([sys.executable, str(CLI_SHIM), *map(str, args)], cwd or REPO_ROOT, env=env)


def run_module(
    args: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None
) -> Result:
    """``PYTHONPATH=src python3 -m teamwork ...`` (the package entrypoint)."""
    return _invoke(
        [sys.executable, "-m", "teamwork", *map(str, args)], cwd or REPO_ROOT, env or build_env()
    )


def console_script_path() -> str | None:
    """Path to the installed ``teamwork`` console script, or ``None``."""
    return shutil.which("teamwork")


def run_console(
    args: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None
) -> Result | None:
    """``teamwork ...`` when the console script is installed, else ``None``."""
    exe = console_script_path()
    if not exe:
        return None
    return _invoke([exe, *map(str, args)], cwd or REPO_ROOT, env or build_env())


def cli(
    project: Path,
    args: Sequence[str],
    *,
    team: str = "Acceptance",
    env: Mapping[str, str] | None = None,
) -> Result:
    """Run the module entrypoint against one isolated workspace."""
    argv = ["--project", str(project), "--team", team, *map(str, args)]
    return run_module(argv, cwd=project, env=env or build_env())


def assert_ok(result: Result, expected_rc: int = 0) -> Result:
    """Fail with the full command and captured output so defects are actionable."""
    assert result.returncode == expected_rc, (
        f"command {result.argv!r} exited {result.returncode}, expected {expected_rc}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result
