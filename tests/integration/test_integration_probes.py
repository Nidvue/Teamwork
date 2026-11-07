"""Integration: the four M14 probes, executed by the suite instead of by hand.

`tests/integration/probes/` holds the area probes for `readme-layout` (README
renders as a docs page), `records` (every record family survives a round trip and
the ledger chain verifies), `social-preview` (the committed card regenerates
byte-for-byte) and `ui-readme` (the served README resolves its own images). They
are scripts, not `test_*.py` modules, so `pytest tests/integration` collected none
of them and the layer rested on one untracked venv (T-0002 review, finding 3).

This module is the gate. Each case runs its probe as a subprocess with `--repo`
pointing at this checkout, then requires exit 0 and the probe's own `RESULT PASS`
line - a probe that exits 0 without proving anything is a failure, not a pass.

One kind of absence is a skip that names the cause, never a pass: **a toolchain**.
`mkdocs` comes from the `dev` extra; `cairosvg` + `Pillow` come from the
`imaging` extra, which no CI job installs, so `social-preview` skips on every CI
leg and its record names the interpreter, versions and source it ran from. The
lookup is measured (import the module in the candidate interpreter), not read
from a requirements file.

The team tree is **not** an absence to skip. The `records` probe used to read the
live `.pi/Teamwork/Teams/<Team>/`, which is gitignored - so a clean checkout had
none - and which a running lane appends to while the suite reads it: on this host
the live read failed with `ledger verify` reporting `digest mismatch (record
altered)` for the record a lane was writing (T-0002). Each case now builds its
own throwaway team in `tmp_path` (`init --no-git`, one criterion, one task and
one test record) and points the probe at it with `--team-root`, so the probe is
hermetic, reproducible on a clean checkout, and cannot race a lane.

The empty store therefore becomes a case the suite measures on purpose instead of
an accident of the host: `criteria list` exits `3` (`# no criteria yet`) when the
store holds no criteria, and the probe accepts that code only when the files hold
none either - see `test_records_probe_accepts_the_documented_empty_store_code`.

Owner: tester. Task: T-0002.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from tests.tooling import skip_message

from teamwork import config, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBES = REPO_ROOT / "tests" / "integration" / "probes"
TIMEOUT_SECONDS = 900

SEED_AGENTS = "ceo,developer-1,tester-1,reviewer-1"

SEED_RECORDS = (
    (
        "criteria",
        "add",
        "--id",
        "AC-1",
        "--text",
        "the records probe round-trips every record family",
        "--owner",
        "developer",
        "--by",
        "ceo",
    ),
    (
        "task",
        "add",
        "developer",
        "the records probe reads a seeded task",
        "--priority",
        "P0",
        "--mandate",
        "explicit",
    ),
    (
        "tests",
        "add",
        "--layer",
        "unit",
        "--area",
        "records",
        "--command",
        "python -m pytest -q tests/unit/test_criteria.py",
    ),
)


def candidate_interpreters() -> list[str]:
    """This interpreter first, then the repo `.venv` of this checkout and its parents.

    The probes search the same order (`sys.executable`, then `<base>/.venv`), so a
    skip reported here is the same fact the probe would print.
    """
    candidates = [sys.executable]
    for base in (REPO_ROOT, *REPO_ROOT.parents):
        candidates.append(str(base / ".venv" / "bin" / "python"))
        candidates.append(str(base / ".venv" / "Scripts" / "python.exe"))
    return candidates


def imports(interpreter: str, modules: tuple[str, ...]) -> bool:
    """True when `interpreter` imports every module. A host mismatch is a no."""
    try:
        probe = subprocess.run(
            [interpreter, "-c", f"import {', '.join(modules)}"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def interpreter_with(modules: tuple[str, ...]) -> str | None:
    """The first interpreter that imports `modules`, or None when none does."""
    for candidate in candidate_interpreters():
        if Path(candidate).is_file() and imports(candidate, modules):
            return candidate
    return None


def team_root(project: Path) -> Path:
    """The tree `init` wrote for `project`, resolved the way `engine` resolves it."""
    return project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)


def seed_team(cli, project: Path, *, records: bool = True) -> Path:
    """A throwaway team in `project`; `records` fills one record per probe family.

    `--no-git` keeps the fixture off the repository's branch guard, and the seed is
    written through the same CLI the probe reads with, so the tree under test is
    produced by the shipped code rather than by a hand-built directory.
    """
    assert cli("--project", project, "init", "--agents", SEED_AGENTS, "--no-git") == 0
    root = team_root(project)
    assert (root / "Ledger.jsonl").is_file(), f"init wrote no ledger under {root}"
    if not records:
        return root
    for argv in SEED_RECORDS:
        assert cli("--project", project, *argv) == 0, argv
    return root


def run_probe(script: str, *argv: str) -> subprocess.CompletedProcess[str]:
    """Run one probe as a subprocess against this checkout."""
    probe = PROBES / script
    assert probe.is_file(), f"{probe} is missing"
    return subprocess.run(
        [sys.executable, str(probe), "--repo", str(REPO_ROOT), *argv],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


CASES = (
    (
        "readme_layout_probe.py",
        "readme-layout",
        ("mkdocs",),
        "mkdocs renders README.md through the same pipeline the docs site uses",
        False,
    ),
    (
        "records_probe.py",
        "records",
        (),
        "",
        True,
    ),
    (
        "social_preview_probe.py",
        "social-preview",
        ("cairosvg", "PIL"),
        "cairosvg and Pillow regenerate assets/social-preview.png with the committed generator",
        False,
    ),
    (
        "ui_readme_probe.py",
        "ui-readme",
        ("mkdocs",),
        "mkdocs builds the site the rendered README is fetched from",
        False,
    ),
)

EXTRAS = {"mkdocs": "dev", "cairosvg + PIL": "imaging"}


@pytest.mark.parametrize(
    ("script", "area", "modules", "reason", "needs_team"),
    CASES,
    ids=[case[1] for case in CASES],
)
def test_probe_passes(
    script: str,
    area: str,
    modules: tuple[str, ...],
    reason: str,
    needs_team: bool,
    tmp_path: Path,
    cli,
) -> None:
    """Run one area probe against this checkout and require its own PASS line."""
    team_argv: tuple[str, ...] = ()
    if needs_team:
        team_argv = ("--team-root", str(seed_team(cli, tmp_path / "SeedProject")))
    if modules:
        interpreter = interpreter_with(modules)
        if interpreter is None:
            name = " + ".join(modules)
            extra = EXTRAS[name]
            pytest.skip(skip_message(name, f"{reason}; `pip install -e '.[{extra}]'` installs it"))
    else:
        interpreter = sys.executable

    extra: tuple[str, ...] = ("--python", interpreter) if modules else ()
    run = run_probe(script, *team_argv, *extra)
    output = run.stdout + run.stderr
    assert run.returncode == 0, f"{area} probe exited {run.returncode}:\n{output}"
    assert "RESULT PASS" in output, f"{area} probe exited 0 with no PASS line:\n{output}"
    if needs_team:
        assert f"team tree: {team_argv[1]}" in output, output


def test_records_probe_accepts_the_documented_empty_store_code(tmp_path: Path, cli) -> None:
    """A store with no criteria yet: `criteria list` exits 3 and the probe says so.

    The empty store is a real state - a lane with nothing recorded yet - and the
    code for it is documented (`docs/guide/cli-records.md`). The probe is hermetic
    here too, so this case measures the contract instead of a host accident.
    """
    root = seed_team(cli, tmp_path / "EmptyProject", records=False)
    run = run_probe("records_probe.py", "--team-root", str(root))
    output = run.stdout + run.stderr
    assert run.returncode == 0, output
    assert "RESULT PASS" in output, output
    assert "cli criteria list: exit 3" in output, output
    assert "no criteria yet" in output, output
