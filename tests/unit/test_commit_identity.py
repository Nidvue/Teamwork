"""The acting role commits its own work: audit the author, committer and trailer."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import engine


def _git(repo: Path, *args: str, ident: tuple[str, str] | None = None):
    command = ["git", "-C", str(repo)]
    if ident:
        command += ["-c", f"user.name={ident[0]}", "-c", f"user.email={ident[1]}"]
    return subprocess.run(
        command + list(args),
        env={
            **os.environ,
            "HOME": str(repo.parent),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main", ".")
    _commit(path, "Developer", "developer@agents.nidvue.com", "feat(x): base")
    return path


def _commit(repo: Path, name: str, email: str, subject: str) -> None:
    _git(
        repo,
        "commit",
        "--allow-empty",
        "-m",
        f"{subject}\n\nActing role: {name}",
        ident=(name, email),
    )


def test_role_commit_passes(repo):
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 0


def test_product_identity_is_rejected(repo):
    _commit(repo, "Teamwork", "teamwork@agents.nidvue.com", "chore: import")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_acting_role_must_match_the_author(repo):
    # A Developer-authored commit that claims the Tester role is misattributed.
    _git(
        repo,
        "commit",
        "--allow-empty",
        "-m",
        "test(x): claim another role\n\nActing role: Tester",
        ident=("Developer", "developer@agents.nidvue.com"),
    )
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_missing_trailer_fails(repo):
    _git(
        repo,
        "commit",
        "--allow-empty",
        "-m",
        "feat(x): no trailer",
        ident=("Developer", "developer@agents.nidvue.com"),
    )
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_bot_dependency_update_is_allowed(repo):
    _commit(
        repo,
        "dependabot[bot]",
        "49699333+" + "dependabot[bot]@users.noreply.github.com",
        "chore: bump",
    )
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 0


def test_option_shaped_range_is_rejected(repo):
    assert engine.audit_commit_identities(repo, "--all") == 2


def test_bot_name_with_a_non_noreply_address_fails(repo):
    _commit(repo, "dependabot[bot]", "dependabot@example.com", "chore: bump")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_forge_merge_commit_is_skipped(repo):
    base = _git(repo, "rev-parse", "main").stdout.strip()
    _git(repo, "switch", "-q", "-c", "feature")
    _commit(repo, "Developer", "developer@agents.nidvue.com", "feat(x): branch")
    feature = _git(repo, "rev-parse", "feature").stdout.strip()
    _git(repo, "switch", "-q", "main")
    _git(
        repo,
        "merge",
        "--no-ff",
        "-m",
        f"Merge {feature} into {base}",
        "feature",
        ident=("Private Person", "someone@" + "private-mail.example"),
    )
    assert engine.audit_commit_identities(repo, "HEAD") == 0


def test_committer_must_match_the_author(repo):
    env = {
        **os.environ,
        "HOME": str(repo.parent),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "Developer",
        "GIT_AUTHOR_EMAIL": "developer@agents.nidvue.com",
        "GIT_COMMITTER_NAME": "Private Person",
        "GIT_COMMITTER_EMAIL": "someone@" + "private-mail.example",
    }
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "--allow-empty",
            "-m",
            "feat(x): wrong committer\n\nActing role: Developer",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert engine.audit_commit_identities(repo, "HEAD") == 1
