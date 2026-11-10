"""Acceptance: the developer entrypoint (`make`) behaves from the outside.

A contributor meets this project through the ``Makefile``. This file accepts the
promises the documentation makes about it:

1. ``make help`` exits ``0`` and lists the targets a contributor needs, read from
   the Makefile itself rather than hard-coded;
2. ``make -n ci`` (a dry run: no command is executed) expands without error and
   names the gate commands the release pipeline claims to run;
3. a failing recipe is a failing ``make`` - proved on a throwaway ``-f`` Makefile
   so nothing in this repository is touched.

Every test that executes ``make`` guards on it: on a host without GNU make the
skip names the tool instead of failing with ``FileNotFoundError [WinError 2]
'make'`` (``T-0003``). The one test that only reads the Makefile as text needs no
tool and is not guarded, so it still runs there.

Owner: reviewer. Task: T-0003. Requirement: acceptance layer, area ``makefile``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from cli_harness import REPO_ROOT, build_env
from tests.tooling import require_tool

AREA = "makefile"
MAKEFILE = REPO_ROOT / "Makefile"

#: Targets a contributor needs before they can contribute at all. They are
#: asserted to be *defined* in the Makefile and *documented* by ``make help``.
REQUIRED_TARGETS = ("test", "lint", "build", "ci")

#: Commands the documented one-shot pipeline must name, because the release
#: documentation tells a reader those gates run.
REQUIRED_GATE_COMMANDS = (
    "ruff check",
    "pytest",
    "check_release_consistency.py",
    "privacy_scan.py",
    "teamwork.py links",
)


def run_make(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    """Run ``make`` with an explicit environment and no shell."""
    return subprocess.run(
        ["make", "--no-print-directory", *map(str, args)],
        cwd=str(cwd),
        env=build_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


#: ``make help`` colourises the target column; strip the escapes before matching.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _documented_targets() -> dict[str, str]:
    """The ``## description`` targets the Makefile advertises to ``make help``."""
    found = {}
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z_-]+):.*?## (.+)$", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def test_help_exits_0_and_lists_the_contributor_targets():
    """ACCEPT: `make help` -> exit 0, one line per documented target."""
    require_tool("make")
    proc = run_make("help")

    assert proc.returncode == 0, f"make help failed:\n{proc.stdout}\n{proc.stderr}"
    plain = ANSI.sub("", proc.stdout)
    assert "available targets" in plain, plain
    documented = _documented_targets()
    missing = [target for target in REQUIRED_TARGETS if target not in documented]
    assert not missing, f"the Makefile documents no {missing}: {sorted(documented)}"
    listed = {
        match.group(1) for match in re.finditer(r"^  ([a-z][a-z0-9_-]*)\s+\S", plain, re.MULTILINE)
    }
    for target in REQUIRED_TARGETS:
        assert target in listed, f"`make help` does not list {target!r}, it lists {sorted(listed)}"


def test_ci_dry_run_names_the_gate_commands():
    """ACCEPT: `make -n ci` -> exit 0 and prints every gate command, running none."""
    require_tool("make")
    proc = run_make("-n", "ci")

    assert proc.returncode == 0, f"make -n ci failed:\n{proc.stdout}\n{proc.stderr}"
    for command in REQUIRED_GATE_COMMANDS:
        assert command in proc.stdout, (
            f"`make -n ci` never runs {command!r}; the documented pipeline is incomplete:\n"
            + proc.stdout
        )
    # A dry run prints commands; it does not run them (proved separately below).
    assert proc.stdout.strip(), proc.stdout


def test_dry_run_prints_without_executing(tmp_path):
    """ACCEPT: `make -n` expands a recipe and produces none of its effects."""
    require_tool("make")
    marker = tmp_path / "executed.marker"
    (tmp_path / "Makefile").write_text(
        f"gate:\n\t@printf '%s' ran > '{marker.as_posix()}'\n",
        encoding="utf-8",
    )

    dry = run_make("-n", "gate", cwd=tmp_path)

    assert dry.returncode == 0, dry.stderr
    assert marker.as_posix() in dry.stdout, dry.stdout
    assert not marker.exists(), "make -n executed the recipe"

    real = run_make("gate", cwd=tmp_path)

    assert real.returncode == 0, real.stderr
    assert marker.exists(), "the same recipe does not execute when the dry run is dropped"


def test_a_failing_recipe_exits_non_zero(tmp_path):
    """ACCEPT: a recipe that fails is a `make` that fails - the gate is real."""
    require_tool("make")
    broken = tmp_path / "Makefile"
    broken.write_text(
        "ok:\n\t@true\n\nbroken:\n\t@false\n\nchain: ok broken\n",
        encoding="utf-8",
    )
    env = build_env()

    passing = subprocess.run(
        ["make", "-f", str(broken), "ok"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    failing = subprocess.run(
        ["make", "-f", str(broken), "chain"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert passing.returncode == 0, passing.stderr
    assert failing.returncode != 0, (
        "a failing recipe exited 0, so a `make` gate in this project proves nothing:\n"
        f"{failing.stdout}{failing.stderr}"
    )


def test_the_real_pipeline_is_the_ci_alias():
    """ACCEPT: `ci` is the documented one-shot pipeline, not an empty alias.

    Read from the Makefile's text, so this one needs no tool and is not guarded.
    """
    text = MAKEFILE.read_text(encoding="utf-8")
    assert re.search(r"^ci:\s+release-check\b", text, re.MULTILINE), (
        "`ci` is not the release-check pipeline:\n" + text
    )
    assert re.search(r"^release-check:.*\blint\b.*\btest\b.*\bverify\b", text, re.MULTILINE), text
    assert sys.executable  # the interpreter the dry run above will use exists
