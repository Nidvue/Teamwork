"""The commit and merge identity, executed against a real repository.

Layer ``integration``, area ``merge-identity``, owner Tester (T-0014). The unit
layer pins the resolver; this layer proves the *git* outcome, which is what a
published history carries:

1. A commit made with ``names.git_identity_env`` is authored **and** committed by
   the identity the engine resolved, even when the ambient ``GIT_AUTHOR_NAME`` /
   ``GIT_COMMITTER_EMAIL`` a wrapper shell left behind says otherwise.
2. A real ``git merge --no-ff`` run with that environment - the shape ``pr merge``
   produces - carries the same pair on the merge commit, not the operator's.
3. ``TEAMWORK_COMMIT_IDENTITY=role`` opts into the role mailbox and nothing else
   does, so a default commit never names a role.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import names

HOSTILE = {
    "GIT_AUTHOR_NAME": "Operator Ops",
    "GIT_AUTHOR_EMAIL": "ops@example.invalid",
    "GIT_COMMITTER_NAME": "Operator Ops",
    "GIT_COMMITTER_EMAIL": "ops@example.invalid",
}


def git(repo: Path, *argv: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(
        ["git", *argv],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, f"git {' '.join(argv)}: {done.stderr}"
    return done


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository that declares its own commit identity."""
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "teamwork.identity.name", "Nidvue Team")
    git(path, "config", "teamwork.identity.email", "team@nidvue.example")
    (path / "file.txt").write_text("one\n", encoding="utf-8")
    git(path, "add", "-A")
    return path


def committed_pair(repo: Path, revision: str = "HEAD") -> tuple[str, str]:
    done = git(repo, "log", "-1", "--format=%an|%ae|%cn|%ce", revision)
    author_name, author_email, committer_name, committer_email = done.stdout.strip().split("|")
    assert (author_name, author_email) == (committer_name, committer_email), done.stdout
    return author_name, author_email


def test_the_ambient_identity_never_authors_a_commit(repo: Path, monkeypatch) -> None:
    monkeypatch.setenv(names.IDENTITY_MODE_ENV, "")
    env = {**os.environ, **HOSTILE, **names.git_identity_env("developer", repo)}
    git(repo, "commit", "-qm", "one", env=env)
    assert committed_pair(repo) == ("Nidvue Team", "team@nidvue.example")


def test_a_merge_commit_carries_the_same_pair(repo: Path, monkeypatch) -> None:
    monkeypatch.setenv(names.IDENTITY_MODE_ENV, "")
    env = {**os.environ, **HOSTILE, **names.git_identity_env("developer", repo)}
    git(repo, "commit", "-qm", "one", env=env)
    git(repo, "checkout", "-q", "-b", "side")
    (repo / "file.txt").write_text("two\n", encoding="utf-8")
    git(repo, "commit", "-qam", "two", env=env)
    git(repo, "checkout", "-q", "main")
    (repo / "other.txt").write_text("other\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "other", env=env)

    git(repo, "merge", "--no-ff", "-m", "merge side", "side", env=env)

    assert committed_pair(repo) == ("Nidvue Team", "team@nidvue.example")
    assert len(git(repo, "rev-list", "--parents", "-1", "HEAD").stdout.split()) == 3


def test_the_role_mailbox_is_opt_in_only(repo: Path, monkeypatch) -> None:
    monkeypatch.setenv(names.IDENTITY_MODE_ENV, "")
    assert names.commit_identity("developer", repo) == ("Nidvue Team", "team@nidvue.example")

    monkeypatch.setenv(names.IDENTITY_MODE_ENV, "role")
    assert names.commit_identity("developer", repo) == (
        "Developer",
        "developer@agents.nidvue.com",
    )
