"""Acceptance: a host that has never run Teamwork boots a team from a shipped copy.

Layer ``acceptance``, area ``portability``, owner Tester (T-0014). The operator's
documented first run, executed end to end as a subprocess from a *copy* of the
shipped bundle under a directory whose name has a space, with a clean environment
(no ``TEAMWORK_*``, a fresh ``USERPROFILE``, no ``HOME``) - the state a new
contributor's machine is in.

Three things must hold, and they are what the portability contract is for:

1. ``init`` succeeds and writes the team tree **into the project**, not into the
   shipped copy, so an install is reusable by a second project.
2. The read commands an operator runs next (``status``, ``parallel``) answer on
   that fresh team instead of failing for a missing file.
3. The shipped copy is byte-unchanged: nothing is created inside it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COPY_ENTRIES = ("src", "scripts", "roles", "references", "templates", "SKILL.md")


@pytest.fixture(scope="module")
def shipped_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("acceptance") / "installed skill"
    root.mkdir(parents=True)
    for entry in COPY_ENTRIES:
        source = REPO_ROOT / entry
        if source.is_dir():
            shutil.copytree(source, root / entry)
        elif source.is_file():
            shutil.copy2(source, root / entry)
    return root


def clean_env(home: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    for name in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "PYTHONPATH"):
        env.pop(name, None)
    env["USERPROFILE"] = str(home)
    env["PYTHONUTF8"] = "1"
    return env


def run(bundle: Path, env: dict, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "teamwork", *argv],
        cwd=bundle,
        env={**env, "PYTHONPATH": str(bundle / "src")},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def test_a_fresh_host_boots_a_team_and_reads_it_back(shipped_copy: Path, tmp_path: Path) -> None:
    env = clean_env(tmp_path / "home")
    project = tmp_path / "FreshProject"
    project.mkdir()

    def shipped_files() -> list[str]:
        return sorted(
            str(path.relative_to(shipped_copy))
            for path in shipped_copy.rglob("*")
            if "__pycache__" not in path.parts
        )

    before = shipped_files()

    init = run(
        shipped_copy,
        env,
        "--project",
        project,
        "init",
        "--agents",
        "developer,reviewer",
        "--no-git",
    )
    assert init.returncode == 0, init.stdout + init.stderr
    teams = project / ".pi" / "Teamwork" / "Teams"
    assert teams.is_dir(), f"init wrote no team tree under {project}"
    team_root = next(path for path in teams.iterdir() if path.is_dir())
    assert (team_root / "Ledger.jsonl").is_file(), f"init wrote no ledger under {team_root}"

    for argv in (("status",), ("parallel",)):
        done = run(shipped_copy, env, "--project", project, *argv)
        assert done.returncode == 0, f"{argv}: {done.stdout + done.stderr}"
        assert done.stdout.strip(), f"{argv} printed nothing on a fresh team"

    assert shipped_files() == before, (
        "the shipped copy was written into; an install must stay read-only"
    )
