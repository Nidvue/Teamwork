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
LEGACY = "50f810b48010947a0606f5ab2d8be4a9809bb385"
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
    """No published commit needs an exemption any more: the rewrite fixed them."""
    code, output = audit(REPO_ROOT, "HEAD")

    assert code == 0, output
    assert LEGACY[:12] in output


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


def test_every_shipped_author_exemption_is_a_full_object_id_with_a_reason() -> None:
    assert engine.LEGACY_AUTHOR_EXEMPT
    for sha, reason in engine.LEGACY_AUTHOR_EXEMPT.items():
        assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
        assert len(reason) > 20, sha


def test_the_shipped_author_exemptions_are_the_measured_pre_policy_commits() -> None:
    code, output = strict_audit(REPO_ROOT, "HEAD")

    assert code == 0, output
    for sha in engine.LEGACY_AUTHOR_EXEMPT:
        assert sha[:12] in output, sha
