"""A rewrite after a self-check must not poison the task's evidence gate.

Two rules are pinned here: the append-only self-check note is read at its newest
segment only, and a revision the record itself marks ``superseded`` may be gone
from every ref without failing the gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamwork import engine

ABSENT = "0" * 39 + "1"


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *argv], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "Repo"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "developer@agents.nidvue.com")
    _git(path, "config", "user.name", "Developer")
    (path / "a.txt").write_text("one\n")
    _git(path, "add", "a.txt")
    _git(path, "commit", "-q", "-m", "one")
    return path


def _commit(repo: Path, text: str) -> str:
    (repo / "a.txt").write_text(text)
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", text.strip())
    return _git(repo, "rev-parse", "HEAD")


def _amend(repo: Path, text: str) -> str:
    (repo / "a.txt").write_text(text)
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "--amend", "-m", text.strip())
    return _git(repo, "rev-parse", "HEAD")


def _task(evidence: str, note: str) -> dict:
    return {"id": "T-0001", "evidence": evidence, "self_note": note}


def test_an_amended_away_revision_fails_until_the_evidence_is_re_pointed(
    repo: Path,
) -> None:
    old = _commit(repo, "one\ntwo\n")
    new = _amend(repo, "one\ntwo\nthree\n")
    assert old != new
    stale = _task(f"pytest @{old} -> 1 passed", f"[pass] re-read | test: pytest @{old} -> 1 passed")
    assert engine._preflight_evidence(repo, stale).status == engine.PREFLIGHT_FAIL
    fresh = _task(f"pytest @{new} -> 2 passed", f"[pass] re-read | test: pytest @{new} -> 2 passed")
    assert engine._preflight_evidence(repo, fresh).status == engine.PREFLIGHT_OK


def test_a_fresh_note_clears_the_gate_without_touching_the_older_segment(repo: Path) -> None:
    old = _commit(repo, "one\ntwo\n")
    new = _amend(repo, "one\ntwo\nthree\n")
    note = f"[pass] re-read | test: pytest @{new} -> 2 passed"
    task = _task(f"pytest @{new} -> 2 passed", f"[pass] re-read | test: pytest @{old} -> 1 passed")
    assert engine._preflight_evidence(repo, task, extra_text=note).status == engine.PREFLIGHT_OK
    task["self_note"] = task["self_note"] + " || " + note
    assert engine._preflight_evidence(repo, task).status == engine.PREFLIGHT_OK


def test_a_revision_marked_superseded_may_be_deleted_entirely(repo: Path) -> None:
    new = _commit(repo, "one\ntwo\n")
    note = (
        f"[pass] re-read: @{ABSENT} superseded by @{new}, the branch was amended"
        f" | test: pytest @{new} -> 2 passed"
    )
    task = _task(f"pytest @{new} -> 2 passed", note)
    check = engine._preflight_evidence(repo, task)
    assert check.status == engine.PREFLIGHT_OK
    assert ABSENT[:7] in check.detail


def test_the_marker_is_what_forgives_a_missing_revision(repo: Path) -> None:
    new = _commit(repo, "one\ntwo\n")
    note = f"[pass] measured at @{ABSENT}, then at @{new} | test: pytest @{new} -> 2 passed"
    assert engine._preflight_evidence(repo, _task(f"pytest @{new} -> 2", note)).status == (
        engine.PREFLIGHT_FAIL
    )


def test_a_superseded_marker_in_the_evidence_field_is_honoured(repo: Path) -> None:
    new = _commit(repo, "one\ntwo\n")
    evidence = f"pytest @{ABSENT} (superseded by @{new}) -> 2 passed"
    task = _task(evidence, f"[pass] re-read | test: pytest @{new} -> 2 passed")
    assert engine._preflight_evidence(repo, task).status == engine.PREFLIGHT_OK
