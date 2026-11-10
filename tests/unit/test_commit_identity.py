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


def _env(repo: Path, **extra: str) -> dict:
    return {
        **os.environ,
        "HOME": str(repo.parent),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        **extra,
    }


def _forge_commit(repo: Path, name: str, email: str, subject: str) -> None:
    """A commit exactly as a forge-side rebase merge produces it.

    The author is the role that did the work; the committer is the host's noreply
    account, which carries no identity of its own.
    """
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            f"{subject}\n\nActing role: {name}",
        ],
        env=_env(
            repo,
            GIT_AUTHOR_NAME=name,
            GIT_AUTHOR_EMAIL=email,
            GIT_COMMITTER_NAME="GitHub",
            GIT_COMMITTER_EMAIL="noreply@github.com",
        ),
        check=True,
        capture_output=True,
        text=True,
    )


def _amend_committer(repo: Path, name: str, email: str) -> None:
    """Rewrite only the committer, as a misbehaving tool would."""
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--amend", "-q", "--allow-empty", "--no-edit"],
        env=_env(repo, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email),
        check=True,
        capture_output=True,
        text=True,
    )


def _forge_merge_ref(repo: Path, subject: str) -> None:
    """A synthetic pull-request merge ref, exactly as a host creates it.

    Two parents, the host's subject shape, the host as the committer and the
    pull-request author as the author.
    """
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", "-b", "pr-branch"],
        env=_env(repo),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "pr work"],
        env=_env(
            repo,
            GIT_AUTHOR_NAME="Tester",
            GIT_AUTHOR_EMAIL="tester@agents.nidvue.com",
            GIT_COMMITTER_NAME="Tester",
            GIT_COMMITTER_EMAIL="tester@agents.nidvue.com",
        ),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", base],
        env=_env(repo),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "merge", "-q", "--no-ff", "-m", subject, "pr-branch"],
        env=_env(
            repo,
            GIT_AUTHOR_NAME="Pull Requester",
            GIT_AUTHOR_EMAIL="author@example.invalid",
            GIT_COMMITTER_NAME="GitHub",
            GIT_COMMITTER_EMAIL="noreply@github.com",
        ),
        check=True,
        capture_output=True,
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


def test_a_rewritten_history_audits_the_tip_instead_of_dying(repo):
    """A force-push leaves the event's before-SHA gone; the tip is still auditable.

    Measured on this repository: rewriting the squash-merge commit that carried a
    personal mailbox (0857bd6 -> 2e7810f) made the CI identity audit exit 2 with
    "Invalid revision range 0857bd6..2e7810f", so the lane went red over a span
    that no longer exists rather than over a real identity defect. A clone made
    after the rewrite has no object for the old revision at all, which a revision
    that does not resolve models exactly.
    """
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    gone = "deadbeef" * 5
    assert engine.rewrite_safe_range(repo, f"{gone}..HEAD") == "HEAD^..HEAD"
    assert engine.audit_commit_identities(repo, f"{gone}..HEAD") == 0


def test_the_narrowed_range_does_not_re_audit_the_whole_history(repo):
    """``HEAD`` alone means every ancestor, which is not the span the event covered.

    Measured on this repository: after a rewrite the first version of the fallback
    returned the tip alone, so the audit walked 337 commits and failed on four
    pre-existing identity blemishes in old history - a red lane for commits the
    push never touched.
    """
    _commit(repo, "Teamwork", "teamwork@agents.nidvue.com", "chore: old blemish")
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    gone = "deadbeef" * 5
    assert engine.audit_commit_identities(repo, f"{gone}..HEAD") == 0


def test_a_bad_tip_still_fails_after_narrowing(repo):
    """Narrowing must not buy silence: the one commit it can measure still counts."""
    _commit(repo, "Teamwork", "teamwork@agents.nidvue.com", "chore: bad tip")
    gone = "deadbeef" * 5
    assert engine.audit_commit_identities(repo, f"{gone}..HEAD") == 1


def test_a_resolvable_range_is_not_narrowed(repo):
    """The rewrite fallback must not quietly shrink an audit that can be walked."""
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    assert engine.rewrite_safe_range(repo, "HEAD~1..HEAD") == "HEAD~1..HEAD"


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


def test_a_forge_rebase_merge_keeps_role_authorship_valid(repo):
    """A forge rebase merge stamps `GitHub <noreply@github.com>` as committer.

    Measured: that commit is what a rebase merge produces (author preserved,
    committer rewritten), and the audit used to fail it - so the only forge merge
    method left after squash was disabled would have turned every merge red. The
    author is still a role mailbox, and every other check still runs.
    """
    _forge_commit(repo, "Security Auditor", "securityauditor@agents.nidvue.com", "fix(x): done")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 0


def test_a_forge_committer_does_not_excuse_a_product_author(repo):
    """The tolerance is for the committer stamp only, never for the author."""
    _forge_commit(repo, "Teamwork", "teamwork@agents.nidvue.com", "chore: import")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_an_unknown_committer_is_still_a_defect(repo):
    """Only the known host stamps are excused, not any committer at all."""
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    _amend_committer(repo, "Someone Else", "someone@example.com")
    assert engine.audit_commit_identities(repo, "HEAD~1..HEAD") == 1


def test_the_committer_guard_passes_a_role_committer(repo):
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    assert engine.guard_committer_identity(repo, "HEAD~1..HEAD") == 0


def test_the_committer_guard_catches_the_host_merge_stamp(repo):
    """A host merge button writes the signed-in account into the commit.

    Measured on this repository: the rebase button produced a commit whose
    committer was the merging account, and the privacy gate failed on that
    personal mailbox in the history - which failed the whole matrix through the
    acceptance proof that re-runs the gate.
    """
    _forge_commit(repo, "Security Auditor", "securityauditor@agents.nidvue.com", "fix(x): done")
    # The host rebase: the author stays the role, the committer becomes the account.
    # The address is assembled at runtime so the repository never holds one.
    _amend_committer(repo, "Some One", "personal" + "@" + "example.invalid")
    assert engine.guard_committer_identity(repo, "HEAD~1..HEAD") == 1


def test_the_committer_guard_accepts_the_host_noreply_stamp(repo):
    _forge_commit(repo, "Security Auditor", "securityauditor@agents.nidvue.com", "fix(x): done")
    assert engine.guard_committer_identity(repo, "HEAD~1..HEAD") == 0


def test_the_committer_guard_names_the_repair(repo, capsys):
    _forge_commit(repo, "Security Auditor", "securityauditor@agents.nidvue.com", "fix(x): done")
    address = "personal" + "@" + "example.invalid"
    _amend_committer(repo, "Some One", address)
    assert engine.guard_committer_identity(repo, "HEAD~1..HEAD") == 1
    out = capsys.readouterr().out
    assert address in out, "the guard must name the offending committer"
    assert "pr merge" in out, "the guard must print the repair"
    assert "--force-with-lease" in out, "the guard must print the repair for an existing commit"


def test_the_committer_guard_skips_the_forge_pull_request_merge_ref(repo):
    """A pull_request build's merge ref is an artefact of the host, not a push.

    Measured: the guard failed the first pull request it ran on, naming the
    synthetic ref - ``Merge <40-hex> into <40-hex>``, authored by the PR author and
    committed by ``GitHub <noreply@github.com>``. It never lands on the default
    branch, and the identity audit has always skipped it for the same reason.
    """
    _forge_merge_ref(repo, "Merge " + "a" * 40 + " into " + "b" * 40)
    assert engine.guard_committer_identity(repo, "HEAD~1..HEAD") == 0


def test_the_committer_guard_survives_an_unreadable_range(repo, capsys):
    """A range whose base does not resolve is measured on the tip, not refused.

    Measured on this repository's own CI: a pull_request event carries the
    all-zero "before" sha, and the guard exited 2 ("Invalid revision range") -
    a usage error on a range the event never covered.
    """
    _commit(repo, "Tester", "tester@agents.nidvue.com", "test(x): cover it")
    gone = "0" * 40
    assert engine.guard_committer_identity(repo, f"{gone}..HEAD") == 0
    out = capsys.readouterr().out
    assert "unmeasurable" in out, "the guard must say what it could not measure"


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
