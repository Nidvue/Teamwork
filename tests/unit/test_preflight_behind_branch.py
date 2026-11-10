"""Staleness is a reminder, not a deadlock, when the tree itself is sound.

T-0076: under a concurrent merge the "behind the base" failure and the evidence
binding were jointly unsatisfiable - the rebase that cleared one rewrote the
revision the other recorded. D-0017 keeps the failure for a genuinely stale tree
and downgrades it only when the merge tree is clean and the gate is not red.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from teamwork import engine


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *argv], check=True, capture_output=True, text=True
    ).stdout.strip()


def _check(name: str, status: str, detail: str = "") -> engine.PreflightCheck:
    return engine.PreflightCheck(name, status, detail)


def _behind() -> engine.PreflightCheck:
    return _check("branch", engine.PREFLIGHT_FAIL, "b is 2 commit(s) behind main: main has moved")


def _status(checks: list) -> dict:
    return {check.name: check.status for check in checks}


def test_a_clean_merge_and_a_green_gate_turn_staleness_into_a_warning() -> None:
    checks = [
        _behind(),
        _check("mergeable", engine.PREFLIGHT_OK),
        _check("gate", engine.PREFLIGHT_OK),
    ]
    engine._soften_behind_branch(checks, "main", 1)
    assert _status(checks)["branch"] == engine.PREFLIGHT_WARN
    assert "clean" in checks[0].detail


def test_a_conflicting_merge_keeps_the_failure() -> None:
    checks = [
        _behind(),
        _check("mergeable", engine.PREFLIGHT_FAIL),
        _check("gate", engine.PREFLIGHT_OK),
    ]
    engine._soften_behind_branch(checks, "main", 1)
    assert _status(checks)["branch"] == engine.PREFLIGHT_FAIL


def test_a_red_gate_keeps_the_failure() -> None:
    checks = [
        _behind(),
        _check("mergeable", engine.PREFLIGHT_OK),
        _check("gate", engine.PREFLIGHT_FAIL),
    ]
    engine._soften_behind_branch(checks, "main", 1)
    assert _status(checks)["branch"] == engine.PREFLIGHT_FAIL


def test_an_unmeasured_gate_still_warns_and_names_run() -> None:
    checks = [
        _behind(),
        _check("mergeable", engine.PREFLIGHT_OK),
        _check("gate", engine.PREFLIGHT_UNVERIFIED),
    ]
    engine._soften_behind_branch(checks, "main", 1)
    assert _status(checks)["branch"] == engine.PREFLIGHT_WARN
    assert "--run" in checks[0].detail


def test_an_empty_branch_behind_the_base_keeps_the_failure(tmp_path: Path) -> None:
    repo = tmp_path / "Repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "developer@agents.nidvue.com")
    _git(repo, "config", "user.name", "Developer")
    (repo / "a.txt").write_text("one\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    _git(repo, "branch", "b")
    (repo / "c.txt").write_text("other lane\n")
    _git(repo, "add", "c.txt")
    _git(repo, "commit", "-q", "-m", "other")

    branch = engine._preflight_branch(repo, "main", "b", "developer")
    mergeable = engine._preflight_mergeable(repo, "main", "b", "developer")
    ahead = engine._rev_count(repo, "main..b")
    assert ahead == 0
    assert branch.status == engine.PREFLIGHT_FAIL
    assert "behind" in branch.detail
    assert mergeable.status == engine.PREFLIGHT_OK

    checks = [branch, mergeable, _check("gate", engine.PREFLIGHT_OK)]
    engine._soften_behind_branch(checks, "main", ahead)
    assert _status(checks)["branch"] == engine.PREFLIGHT_FAIL


def test_a_real_clean_merge_over_a_moved_base_is_a_warning(tmp_path: Path) -> None:
    repo = tmp_path / "Repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "developer@agents.nidvue.com")
    _git(repo, "config", "user.name", "Developer")
    (repo / "a.txt").write_text("one\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "one")
    _git(repo, "branch", "b")
    _git(repo, "checkout", "-q", "b")
    (repo / "b.txt").write_text("lane\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "lane")
    _git(repo, "checkout", "-q", "main")
    (repo / "c.txt").write_text("other lane\n")
    _git(repo, "add", "c.txt")
    _git(repo, "commit", "-q", "-m", "other")

    branch = engine._preflight_branch(repo, "main", "b", "developer")
    mergeable = engine._preflight_mergeable(repo, "main", "b", "developer")
    assert branch.status == engine.PREFLIGHT_FAIL
    assert "behind" in branch.detail
    assert mergeable.status == engine.PREFLIGHT_OK

    checks = [branch, mergeable, _check("gate", engine.PREFLIGHT_OK)]
    engine._soften_behind_branch(checks, "main", 1)
    assert _status(checks)["branch"] == engine.PREFLIGHT_WARN
