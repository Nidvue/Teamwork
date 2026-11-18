"""A rebase moves the commit, not the change, so a measured patch stays measured.

The evidence gate refuses a record that names an older revision than the branch
head, because the tree moved after the run and the counts no longer reproduce.
That reason does not hold for a rebase, a restack or an `--amend` that only moves
the commit: the branch's own diff against its base is byte-identical, so the run
reproduces and re-running it would re-measure the same change at a new SHA.

The escape hatch is `git patch-id --stable`, and these tests pin both halves of it:
the same patch at a new SHA passes and says so, and a patch that really changed -
new content, or an older revision of a different change - still fails.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamwork import engine, gitutil


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
    (path / "base.txt").write_text("base\n")
    _git(path, "add", "base.txt")
    _git(path, "commit", "-q", "-m", "base")
    _git(path, "checkout", "-q", "-b", "task/T-0001")
    return path


def _commit(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", text.strip())
    return _git(repo, "rev-parse", "HEAD")


def _reword(repo: Path, message: str = "reworded") -> str:
    _git(repo, "commit", "-q", "--amend", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _amend(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "--amend", "-m", text.strip())
    return _git(repo, "rev-parse", "HEAD")


def _task(evidence: str, note: str, base: str = "main") -> dict:
    return {"id": "T-0001", "base": base, "evidence": evidence, "self_note": note}


def _recorded(sha: str) -> dict:
    return _task(
        f"pytest @{sha} -> 2 passed",
        f"[pass] re-read | test: pytest @{sha} -> 2 passed",
    )


def test_a_moved_commit_with_the_same_patch_passes_and_says_so(repo: Path) -> None:
    old = _commit(repo, "a.txt", "one\n")
    new = _reword(repo)
    assert old != new
    assert gitutil.patch_id(repo, "main", old) == gitutil.patch_id(repo, "main", new)
    check = engine._preflight_evidence(repo, _recorded(old), head_rev=new)
    assert check.status == engine.PREFLIGHT_OK
    assert old[:7] in check.detail
    assert "same patch" in check.detail


def test_a_changed_patch_at_the_head_still_fails(repo: Path) -> None:
    old = _commit(repo, "a.txt", "one\n")
    new = _amend(repo, "a.txt", "one\ntwo\n")
    check = engine._preflight_evidence(repo, _recorded(old), head_rev=new)
    assert check.status == engine.PREFLIGHT_FAIL
    assert "same patch" not in check.detail


def test_an_older_revision_of_another_change_still_fails(repo: Path) -> None:
    other = _commit(repo, "b.txt", "other\n")
    head = _commit(repo, "a.txt", "one\n")
    check = engine._preflight_evidence(repo, _recorded(other), head_rev=head)
    assert check.status == engine.PREFLIGHT_FAIL


def test_a_rebase_onto_a_moved_base_keeps_the_record_green(repo: Path) -> None:
    old = _commit(repo, "a.txt", "one\n")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "upstream.txt", "upstream\n")
    _git(repo, "checkout", "-q", "task/T-0001")
    _git(repo, "rebase", "-q", "main")
    new = _git(repo, "rev-parse", "HEAD")
    assert new != old
    check = engine._preflight_evidence(repo, _recorded(old), head_rev=new)
    assert check.status == engine.PREFLIGHT_OK
    assert "same patch" in check.detail


def test_an_unknown_base_is_not_a_pass(repo: Path) -> None:
    old = _commit(repo, "a.txt", "one\n")
    new = _reword(repo)
    assert gitutil.patch_id(repo, "no-such-base", new) == ""
    task = _task(f"pytest @{old} -> 2 passed", "", base="no-such-base")
    assert engine._preflight_evidence(repo, task, head_rev=new).status == engine.PREFLIGHT_FAIL
