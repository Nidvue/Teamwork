"""One published commit without the trailer passes, and no commit needs one."""

from __future__ import annotations

import io
import re
import subprocess
from contextlib import redirect_stdout
from pathlib import Path

from teamwork import engine

REPO_ROOT = Path(__file__).resolve().parents[2]
IDENTITY = [
    "-c",
    "user.name=Reviewer",
    "-c",
    "user.email=reviewer@agents.nidvue.com",
    "-c",
    "commit.gpgsign=false",
]
OUTSIDE = [
    "-c",
    "user.name=Outside Contributor",
    "-c",
    "user.email=outside@example.org",
    "-c",
    "commit.gpgsign=false",
]


def audit(project: Path, rev_range: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = engine.audit_commit_identities(project, rev_range)
    return code, buffer.getvalue()


def repo(tmp_path: Path) -> Path:
    project = tmp_path / "fixture"
    project.mkdir()
    for argv in (["init", "-q", "-b", "main"], ["config", "user.name", "Reviewer"]):
        subprocess.run(["git", *argv], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "reviewer@agents.nidvue.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return project


def commit(project: Path, message: str, identity: list[str] | None = None) -> str:
    (project / "note.txt").write_text(message + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.txt"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", *(identity or IDENTITY), "commit", "--no-verify", "-q", "-m", message],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=project, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_a_records_commit_without_the_trailer_passes_by_default(tmp_path: Path) -> None:
    project = repo(tmp_path)
    commit(project, "chore(records): append the review entry")

    code, output = audit(project, "HEAD")

    assert code == 0, output
    assert "problems: 0" in output


def test_the_exempt_sha_passes(tmp_path: Path, monkeypatch) -> None:
    project = repo(tmp_path)
    first = commit(project, "chore(records): append the review entry")
    monkeypatch.setattr(engine, "LEGACY_MESSAGE_EXEMPT", {first: "legacy"})

    code, output = audit(project, "HEAD")

    assert code == 0, output
    assert "(legacy message exemption)" in output


def test_a_second_commit_with_the_same_shape_passes_too(tmp_path: Path, monkeypatch) -> None:
    project = repo(tmp_path)
    first = commit(project, "chore(records): append the review entry")
    second = commit(project, "chore(records): append another entry")
    monkeypatch.setattr(engine, "LEGACY_MESSAGE_EXEMPT", {first: "legacy"})

    code, output = audit(project, "HEAD")

    assert code == 0, output
    assert second[:12] in output and "problems: 0" in output


def test_every_shipped_exemption_is_one_full_object_id_with_a_reason() -> None:
    """The list is published history, so each entry is a SHA and a written reason.

    The count is deliberately not pinned: an entry is added only for a commit that
    is already published and cannot be rewritten, and each one carries the reason
    the audit prints.
    """
    for sha, reason in engine.LEGACY_MESSAGE_EXEMPT.items():
        assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
        assert len(reason) > 20, (sha, reason)


def test_the_whole_history_is_clean() -> None:
    """Every commit the audit reads passes, and nothing after the boundary is skipped.

    The boundary is the reconciliation merge that joined the two published lines,
    so the replayed commits before it are exempt by the rule that already covered
    pre-policy history. The pin is the property that matters, not one object id:
    at least one commit is skipped as predating the rule (the exemption is
    exercised and prints its reason) and at least one commit after the boundary is
    audited rather than skipped (the exemption cannot spread to new work).
    """
    code, output = audit(REPO_ROOT, "HEAD")

    assert code == 0, output
    assert "skipped: predates the role-mailbox rule" in output, output[:2000]
    boundary = engine.LEGACY_IDENTITY_BEFORE
    after = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-list", f"{boundary}..HEAD"],
        capture_output=True,
        text=True,
    ).stdout.split()
    assert after, f"{boundary} is HEAD: no commit is held to the rule"
    audited = [
        line for line in output.splitlines() if line.startswith("- ") and "skipped" not in line
    ]
    assert len(audited) >= len(after), (len(audited), len(after), output[-2000:])


def strict_audit(project: Path, rev_range: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = engine.audit_commit_identities(project, rev_range, strict_authors=True)
    return code, buffer.getvalue()


def test_a_published_identity_from_before_the_policy_passes_strict_mode(
    tmp_path: Path, monkeypatch
) -> None:
    """Strict mode is a policy, and a policy cannot apply to a commit older than it."""
    project = repo(tmp_path)
    first = commit(project, "chore: hand edit")
    monkeypatch.setattr(engine, "LEGACY_AUTHOR_EXEMPT", {first: "before the policy"})

    code, output = strict_audit(project, "HEAD")

    assert code == 0, output
    assert "legacy author (before the policy)" in output


def test_another_commit_by_the_same_author_still_fails_strict_mode(
    tmp_path: Path, monkeypatch
) -> None:
    project = repo(tmp_path)
    first = commit(project, "chore: hand edit")
    second = commit(project, "chore: hand edit again", OUTSIDE)
    monkeypatch.setattr(engine, "LEGACY_AUTHOR_EXEMPT", {first: "before the policy"})

    code, output = strict_audit(project, "HEAD")

    assert code == 1, output
    assert second[:12] in output
    assert "not a role mailbox" in output


def test_the_shipped_exemption_maps_are_empty_after_the_rewrite() -> None:
    """Both maps exist to accept published history that cannot be rewritten.

    The D-20261115-CEO-3 rewrite replaced the four pre-policy operator commits and
    the one trailer-less commit, so every entry they held now names a commit that
    carries a role mailbox and the full block. An entry kept past that point would
    excuse nothing while telling a reader the history still needs it, so the maps
    ship empty and the mechanism stays for the next published-history repair.
    """
    assert engine.LEGACY_AUTHOR_EXEMPT == {}
    assert engine.LEGACY_MESSAGE_EXEMPT == {}


def test_the_repository_history_needs_no_exemption() -> None:
    """The audit and the guard are green on this tree.

    Published history before ``LEGACY_IDENTITY_BEFORE`` is exempt with a printed
    reason: it predates the role-mailbox merge rule, the default branch is
    protected, and rewriting it is a red line. The boundary is the reconciliation
    merge ``34384c63`` because the tree carries two published lines joined there:
    a boundary on one line alone left 1659 replayed commits on the other line
    failing an audit they predate. Every commit after the boundary is held to the
    rule, which is what keeps the exemption from spreading.
    """
    code, output = strict_audit(REPO_ROOT, "HEAD")

    assert code == 0, output
    assert engine.guard_committer_identity(REPO_ROOT, "HEAD") == 0
    boundary = engine.LEGACY_IDENTITY_BEFORE
    assert boundary, "the boundary must name a revision, not be empty"
    assert (
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{boundary}^{{commit}}"],
            capture_output=True,
        ).returncode
        == 0
    ), f"LEGACY_IDENTITY_BEFORE {boundary} is not a commit in this repository"
