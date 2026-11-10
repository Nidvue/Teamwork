"""Throwaway work trees and subprocess helpers for the gate-acceptance tests.

The acceptance layer judges the gates the way a user meets them: as a command run
against a tree. This module only builds the *subjects* - a disposable git work
tree holding the release facts (``version.py``, ``CHANGELOG.md``, tags, the
exceptions record) - and runs the shipped script as a subprocess. Nothing here
imports the engine or the checker, so a test cannot accidentally accept an
internal call the user never makes.

No network: ``GITHUB_TOKEN``/``GH_TOKEN`` are removed from every child
environment, and the acceptance tests only ever pass ``--offline``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from cli_harness import REPO_ROOT, build_env

#: The release gate a user runs locally (the same command the CI job runs).
CHECKER = REPO_ROOT / "scripts" / "check_release_consistency.py"
#: Where CI runs that gate offline, and where the tag-triggered release runs it
#: online. Both are parsed as text: a YAML parser is not a stdlib module and the
#: project ships zero runtime dependencies.
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"

#: A fixed git identity and clock, and no ambient git config: a fixture commit
#: must not depend on the machine it runs on, and a user's ``commit.gpgsign``
#: must not make an acceptance test fail for a reason unrelated to the gate.
_GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "acceptance",
    "GIT_AUTHOR_EMAIL": "acceptance@fixtures.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
    "GIT_COMMITTER_NAME": "acceptance",
    "GIT_COMMITTER_EMAIL": "acceptance@fixtures.invalid",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run one git command inside ``repo`` and fail loudly if it fails."""
    env = build_env(_GIT_ENV)
    env.pop("GITHUB_TOKEN", None)
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *map(str, args)],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert proc.returncode == 0, f"git {' '.join(map(str, args))} failed in {repo}:\n{proc.stderr}"
    return proc


def make_repo(root: Path) -> Path:
    """Initialise an empty git work tree at ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    return root


def write_release_facts(
    root: Path,
    *,
    version: str | None = "1.0.0",
    changelog_sections: Sequence[str] = ("1.0.0",),
    exceptions: bool = True,
) -> Path:
    """Write the release facts the gate reads into ``root``.

    ``version=None`` omits ``src/teamwork/version.py``, which is the
    *unreadable input* case the gate must exit ``2`` on rather than pass.
    ``exceptions=True`` writes the empty exception record: without the file the
    gate refuses outright (exit ``2``), so a fixture that spells every fact out
    must include it or it would be testing the wrong failure.
    """
    src = root / "src" / "teamwork"
    src.mkdir(parents=True, exist_ok=True)
    if version is not None:
        (src / "version.py").write_text(
            f'__version__ = "{version}"\nDIST_NAME = "teamwork-agents"\n', encoding="utf-8"
        )
    changelog = ["# Changelog", "", "Owner: acceptance fixture.", ""]
    for section in changelog_sections:
        changelog += [f"## [{section}] - 2026-01-01", "", f"- release {section}", ""]
    (root / "CHANGELOG.md").write_text("\n".join(changelog), encoding="utf-8")
    if exceptions:
        (root / "release-exceptions.json").write_text("[]\n", encoding="utf-8")
    (root / "README.md").write_text("# fixture\n\nOwner: acceptance fixture.\n", encoding="utf-8")
    return root


def commit_all(root: Path, message: str = "release facts", *, allow_empty: bool = False) -> Path:
    """Commit everything currently in ``root``.

    ``allow_empty`` commits a new revision with no tree change, which is how a
    fixture moves HEAD off a tag without touching the release facts.
    """
    git(root, "add", "-A")
    extra = ["--allow-empty"] if allow_empty else []
    git(root, "commit", "-qm", message, *extra)
    return root


def checkout(dest: Path) -> Path:
    """A clone-like copy of this repository at ``dest``: tracked files only.

    A user meets the gates in a clone, not in this team's worktree - and the
    engine's link check skips every directory named ``.pi``, which is exactly
    where each worktree lives. Copying the *tracked* set gives both properties:
    no ``.git``/``.pi``/caches, and the working-tree content a mutation can bite
    on (an archive of ``HEAD`` would silently ignore an uncommitted edit).
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(REPO_ROOT),
        env=build_env(),
        capture_output=True,
        check=True,
    ).stdout
    dest.mkdir(parents=True, exist_ok=True)
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        rel = Path(raw.decode("utf-8"))
        source = REPO_ROOT / rel
        if not source.is_file():
            continue  # a deleted-but-tracked path is not part of a clean checkout
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return dest


def run_checker(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the shipped gate script as a user does, from ``cwd``."""
    env = build_env()
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    return subprocess.run(
        [sys.executable, str(CHECKER), *map(str, args)],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
