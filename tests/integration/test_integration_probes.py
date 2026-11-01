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

Two kinds of absence are skips that name the cause, never passes:

* **A toolchain.** `mkdocs` comes from the `dev` extra; `cairosvg` + `Pillow`
  come from the `imaging` extra, which no CI job installs, so `social-preview`
  skips on every CI leg and its record names the interpreter, versions and
  source it ran from. The lookup is measured (import the module in the candidate
  interpreter), not read from a requirements file.
* **The live team tree.** The `records` probe reads `.pi/Teamwork/Teams/<Team>/`,
  which is gitignored, so a clean checkout - every CI leg, a fresh clone, the
  release tarball - has none. The guard is the one the unit layer already uses
  (`tests/unit/test_board_matches_tool.py`): a skip saying the tree is absent.

Owner: tester. Task: T-0002.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from tests.tooling import skip_message

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBES = REPO_ROOT / "tests" / "integration" / "probes"
TEAM = "Teamwork"
TIMEOUT_SECONDS = 900


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


def team_tree() -> Path | None:
    """This checkout's live team tree, or None when it has none.

    `.pi/` is gitignored working state: a clean checkout carries no ledger, no
    queues and no tests record, so the `records` probe has nothing to read. The
    lookup matches the probe's own (`.pi/Teamwork/Teams/<team>` up the ancestors,
    then a bare team directory) so the skip fires exactly when the probe would
    fail for that reason.
    """
    for base in (REPO_ROOT, *REPO_ROOT.parents):
        candidate = base / ".pi" / "Teamwork" / "Teams" / TEAM
        if (candidate / "Ledger.jsonl").is_file():
            return candidate
        if (base / "Ledger.jsonl").is_file() and (base / "Roles").is_dir():
            return base
    return None


#: probe script, area, modules it needs, why, and whether it reads the team tree.
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

#: Which extra installs each probe's toolchain, as pyproject.toml declares it.
EXTRAS = {"mkdocs": "dev", "cairosvg + PIL": "imaging"}


@pytest.mark.parametrize(
    ("script", "area", "modules", "reason", "needs_team"),
    CASES,
    ids=[case[1] for case in CASES],
)
def test_probe_passes(
    script: str, area: str, modules: tuple[str, ...], reason: str, needs_team: bool
) -> None:
    """Run one area probe against this checkout and require its own PASS line."""
    if needs_team and team_tree() is None:
        pytest.skip(
            "no local team tree in this checkout (gitignored working state):"
            " the records probe reads the live task, tests, review and ledger tree"
        )
    if modules:
        interpreter = interpreter_with(modules)
        if interpreter is None:
            name = " + ".join(modules)
            extra = EXTRAS[name]
            pytest.skip(skip_message(name, f"{reason}; `pip install -e '.[{extra}]'` installs it"))
    else:
        interpreter = sys.executable

    probe = PROBES / script
    assert probe.is_file(), f"{probe} is missing"

    argv = [interpreter, str(probe), "--repo", str(REPO_ROOT)]
    if modules:
        argv += ["--python", interpreter]
    run = subprocess.run(
        argv,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    output = run.stdout + run.stderr
    assert run.returncode == 0, f"{area} probe exited {run.returncode}:\n{output}"
    assert "RESULT PASS" in output, f"{area} probe exited 0 with no PASS line:\n{output}"
