"""Hermetic git invocation in the test fixtures (T-0002).

A future edit that forwards ``HOME``, ``GIT_CONFIG_GLOBAL`` or
``GIT_CONFIG_SYSTEM`` into the child would hand every fixture a foreign
``user.name``, a ``commit.gpgsign`` that fails each commit and an
``init.defaultBranch`` that renames the branch under test.

Owner: developer. Layer: unit. Area: skill-refresh.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from tests.gitenv import child_env

GIT_ENV = child_env(
    GIT_AUTHOR_NAME="Tester",
    GIT_AUTHOR_EMAIL="tester@agents.nidvue.com",
    GIT_COMMITTER_NAME="Tester",
    GIT_COMMITTER_EMAIL="tester@agents.nidvue.com",
)


def git_path() -> str:
    """The ambient PATH plus the usual bin directories.

    Hard-coding ``/usr/bin:/bin`` hides git on NixOS and Guix, where it lives in
    ``/run/current-system/sw/bin``: the tests need *a* git, not a specific one.
    """
    ambient = os.environ.get("PATH", "")
    return os.pathsep.join(p for p in (ambient, "/usr/bin", "/bin", "/usr/local/bin") if p)


def git(path: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(path), *argv],
        capture_output=True,
        text=True,
        env={**GIT_ENV, "PATH": git_path()},
    )
    assert done.returncode == 0, (argv, done.stderr)
    return done.stdout.strip()


def test_the_git_helper_ignores_the_callers_git_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hermetic must mean proof, not the accident of a missing ``HOME``."""
    hostile = tmp_path / ".gitconfig"
    hostile.write_text(
        "[user]\n\tname = Operator\n\temail = operator@example.com\n"
        "[commit]\n\tgpgsign = true\n[init]\n\tdefaultBranch = trunk\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(hostile))

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")

    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") != "trunk", "config leaked"
    assert git(repo, "log", "-1", "--format=%an <%ae>") == "Tester <tester@agents.nidvue.com>"
