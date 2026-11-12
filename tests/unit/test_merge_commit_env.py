"""The merge path's own commits carry the default-branch override.

The R1 pre-commit hook refuses a commit on the default branch so no lane can land
work there directly. A merge's records, board render and archive rewrite are the
one exception the rule names, and the engine sets the marker itself: a Reviewer
lane has no human to export `TEAMWORK_ALLOW_MAIN` before its pass lands.

The same environment pins the author and committer: the merge passes
`-c user.name`, which loses to an exported `GIT_AUTHOR_NAME` left by a rebase, a
forge runner or a wrapper shell.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import engine

HOSTILE_IDENTITY = ("Hostile Operator", "hostile@example.invalid")


def test_the_merge_environment_marks_the_default_branch_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEAMWORK_ALLOW_MAIN", raising=False)
    env = engine._merge_commit_env()
    assert env["TEAMWORK_ALLOW_MAIN"] == "1"


def test_the_merge_environment_keeps_the_ambient_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEAMWORK_MARKER", "kept")
    env = engine._merge_commit_env()
    assert env["TEAMWORK_MARKER"] == "kept"
    assert os.environ["TEAMWORK_MARKER"] == "kept"


def test_the_merge_environment_never_leaks_into_the_calling_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEAMWORK_ALLOW_MAIN", raising=False)
    engine._merge_commit_env()
    assert "TEAMWORK_ALLOW_MAIN" not in os.environ


def test_the_merge_environment_pins_the_identity_over_an_exported_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_AUTHOR_NAME", HOSTILE_IDENTITY[0])
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", HOSTILE_IDENTITY[1])
    monkeypatch.setenv("GIT_COMMITTER_NAME", HOSTILE_IDENTITY[0])
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", HOSTILE_IDENTITY[1])
    env = engine._merge_commit_env()
    name, email = engine.commit_identity("reviewer")
    assert (env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"]) == (name, email)
    assert (env["GIT_COMMITTER_NAME"], env["GIT_COMMITTER_EMAIL"]) == (name, email)
    assert env["TEAMWORK_ALLOW_MAIN"] == "1"


def _merge_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True
        )

    git("init", "-q", "-b", "main", ".")
    git("config", "user.name", "Operator")
    git("config", "user.email", "operator@example.invalid")
    git("commit", "-q", "--allow-empty", "-m", "feat(x): base")
    git("checkout", "-q", "-b", "pr-branch")
    git("commit", "-q", "--allow-empty", "-m", "feat(x): work")
    git("checkout", "-q", "main")
    return repo


def test_a_merge_commit_lands_as_the_pinned_pair_despite_an_exported_pair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = _merge_repo(tmp_path)
    monkeypatch.setenv("GIT_AUTHOR_NAME", HOSTILE_IDENTITY[0])
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", HOSTILE_IDENTITY[1])
    monkeypatch.setenv("GIT_COMMITTER_NAME", HOSTILE_IDENTITY[0])
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", HOSTILE_IDENTITY[1])
    subprocess.run(
        ["git", "-C", str(repo)]
        + engine.git_identity_args("reviewer", repo)
        + ["merge", "--no-ff", "-m", "chore(merge): integrate P-0001", "pr-branch"],
        env=engine._merge_commit_env(repo),
        check=True,
        capture_output=True,
        text=True,
    )
    landed = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%an <%ae>|%cn <%ce>"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    name, email = engine.commit_identity("reviewer", repo)
    assert landed == f"{name} <{email}>|{name} <{email}>"


class _Completed:
    returncode = 0
    stdout = ""
    stderr = ""


def _pin_base_entry_commit(monkeypatch: pytest.MonkeyPatch, tmp_path, seen: list) -> None:
    monkeypatch.setattr(engine, "archive_write_repo", lambda root, t: tmp_path)
    monkeypatch.setattr(engine, "current_branch", lambda repo: engine.DEFAULT_BASE)
    monkeypatch.setattr(engine, "merge_record_paths", lambda: ["docs/Team/Archive.md"])
    monkeypatch.setattr(engine, "_uncommitted_paths", lambda here, *paths: ["docs/Team/Archive.md"])
    monkeypatch.setattr(engine, "run_git", lambda *a, **k: _Completed())

    def fake_run(*args, **kwargs):
        seen.append(kwargs)
        return _Completed()

    monkeypatch.setattr(engine.subprocess, "run", fake_run)


def test_the_accepted_results_entry_commit_carries_the_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("TEAMWORK_ALLOW_MAIN", raising=False)
    seen: list = []
    _pin_base_entry_commit(monkeypatch, tmp_path, seen)
    line = engine.commit_records_entry(
        tmp_path, {"id": "T-0001", "review_status": "pass"}, "Reviewer-1"
    )
    assert "committed the accepted-results entry" in line
    assert seen and seen[-1]["env"]["TEAMWORK_ALLOW_MAIN"] == "1"


def test_the_accepted_results_entry_commit_keeps_the_ambient_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("TEAMWORK_MARKER", "kept")
    seen: list = []
    _pin_base_entry_commit(monkeypatch, tmp_path, seen)
    engine.commit_records_entry(tmp_path, {"id": "T-0002"}, "Reviewer-1")
    assert seen[-1]["env"]["TEAMWORK_MARKER"] == "kept"
