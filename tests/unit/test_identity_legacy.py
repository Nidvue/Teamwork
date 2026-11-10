"""One published commit without the trailer passes by exact id, and only it."""

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
LEGACY = "f709c4ce3eebd1689bef5982aa559564f8867895"


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


def commit(project: Path, message: str) -> str:
    (project / "note.txt").write_text(message + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.txt"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", *IDENTITY, "commit", "--no-verify", "-q", "-m", message],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=project, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_a_records_commit_without_the_trailer_fails_by_default(tmp_path: Path) -> None:
    project = repo(tmp_path)
    commit(project, "chore(records): append the review entry")

    code, output = audit(project, "HEAD")

    assert code == 1, output
    assert "message has no 'Acting role:' line" in output


def test_the_exempt_sha_passes(tmp_path: Path, monkeypatch) -> None:
    project = repo(tmp_path)
    first = commit(project, "chore(records): append the review entry")
    monkeypatch.setattr(engine, "LEGACY_MESSAGE_EXEMPT", {first: "legacy"})

    code, output = audit(project, "HEAD")

    assert code == 0, output
    assert "(legacy message exemption)" in output


def test_a_different_commit_with_the_same_shape_still_fails(tmp_path: Path, monkeypatch) -> None:
    project = repo(tmp_path)
    first = commit(project, "chore(records): append the review entry")
    second = commit(project, "chore(records): append another entry")
    monkeypatch.setattr(engine, "LEGACY_MESSAGE_EXEMPT", {first: "legacy"})

    code, output = audit(project, "HEAD")

    assert code == 1, output
    assert second[:12] in output
    assert "message has no 'Acting role:' line" in output


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
    assert not engine.LEGACY_MESSAGE_EXEMPT, "the rewrite fixed the fabricated authors"
