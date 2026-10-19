"""Unit tests for structured evidence packets and the repro gate primitives.

An evidence packet binds a claim to four things: the baseline state, the action,
the observed result, and an artifact a later agent can re-open. The repro gate
adds the fifth: proof that the defect failed before the fix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamwork import engine


def make_root(project: Path) -> Path:
    """Build the ``.pi/Teamwork/Teams/<Team>`` shape ``project_of`` expects."""
    root = project / ".pi" / "Teamwork" / "Teams" / "Sample"
    root.mkdir(parents=True)
    return root


def git(project: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(project), *argv],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def init_repo(project: Path) -> None:
    git(project, "init", "-q")
    git(project, "config", "user.name", "Tester")
    git(project, "config", "user.email", "tester@agents.nidvue.com")
    git(project, "config", "commit.gpgsign", "false")


def commit(project: Path, message: str) -> str:
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", message)
    return git(project, "rev-parse", "--short", "HEAD")


# --------------------------------------------------------------------------- #
# records
# --------------------------------------------------------------------------- #


def test_new_test_record_starts_with_an_empty_packet() -> None:
    record = engine.new_test_record("unit", "parser")

    for field in ("baseline", "artifacts", "replay"):
        assert record[field] == ""


def test_test_record_roundtrip_keeps_the_packet(tmp_path: Path) -> None:
    path = tmp_path / "Tests.md"
    record = engine.new_test_record("unit", "parser", owner="developer-1")
    record["baseline"] = "empty cache, 0 entries"
    record["artifacts"] = "Reports/run.log:abc123:4096"
    record["replay"] = "pytest tests/unit/test_parser.py -q"

    engine.write_tests(path, [record])
    out = engine.parse_tests(path)

    assert len(out) == 1
    assert out[0]["baseline"] == "empty cache, 0 entries"
    assert out[0]["artifacts"] == "Reports/run.log:abc123:4096"
    assert out[0]["replay"] == "pytest tests/unit/test_parser.py -q"


def test_new_task_records_kind_and_artifact_fields() -> None:
    task = engine.new_task("fix the parser crash")

    assert task["kind"] == ""
    assert task["repro"] == ""
    assert task["repro_artifacts"] == ""
    assert task["repro_by"] == ""
    assert task["self_artifacts"] == ""
    assert task["review_artifacts"] == ""


def test_task_roundtrip_keeps_kind_and_artifacts(tmp_path: Path) -> None:
    path = tmp_path / "TaskQueue.md"
    task = engine.new_task("fix the parser crash")
    task["kind"] = "bug"
    task["repro"] = "pre @aaa111 -> 3 failed | post @bbb222 -> 12 passed"
    task["repro_artifacts"] = "Reports/repro.log:def456:12"
    task["repro_by"] = "developer-1"
    task["self_artifacts"] = "Reports/self.log:def456:12"
    task["review_artifacts"] = "Reports/review.log:0a1b2c:8"

    engine.write_tasks(path, [task], "developer")
    out = engine.parse_tasks(path)

    assert out[0]["kind"] == "bug"
    assert out[0]["repro"] == "pre @aaa111 -> 3 failed | post @bbb222 -> 12 passed"
    assert out[0]["repro_artifacts"] == "Reports/repro.log:def456:12"
    assert out[0]["repro_by"] == "developer-1"
    assert out[0]["self_artifacts"] == "Reports/self.log:def456:12"
    assert out[0]["review_artifacts"] == "Reports/review.log:0a1b2c:8"


# --------------------------------------------------------------------------- #
# artifacts
# --------------------------------------------------------------------------- #


def test_artifact_digest_is_relative_bounded_and_stable(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    (project / "Reports").mkdir()
    (project / "Reports" / "run.log").write_bytes(b"12 passed\n")

    first = engine.artifact_digest(root, "Reports/run.log")
    second = engine.artifact_digest(root, str(project / "Reports" / "run.log"))

    assert first == second
    path, digest, size = first.split(":")
    assert path == "Reports/run.log"
    assert len(digest) == 16
    assert size == str(len(b"12 passed\n"))


def test_artifact_digest_changes_when_the_file_changes(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    artifact = project / "run.log"
    artifact.write_text("3 failed\n", encoding="utf-8")
    before = engine.artifact_digest(root, "run.log")

    artifact.write_text("12 passed\n", encoding="utf-8")

    assert engine.artifact_digest(root, "run.log") != before


def test_artifact_digest_refuses_a_missing_file(tmp_path: Path) -> None:
    root = make_root(tmp_path / "SampleProject")

    with pytest.raises(SystemExit) as exc:
        engine.artifact_digest(root, "Reports/missing.log")

    assert exc.value.code == 1


def test_artifact_digest_refuses_a_path_outside_the_project(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    outside = tmp_path / "elsewhere.log"
    outside.write_text("proof\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        engine.artifact_digest(root, str(outside))


def test_artifact_digests_is_empty_without_artifacts(tmp_path: Path) -> None:
    root = make_root(tmp_path / "SampleProject")

    assert engine.artifact_digests(root, None) == ""
    assert engine.artifact_digests(root, []) == ""


# --------------------------------------------------------------------------- #
# repro ancestry
# --------------------------------------------------------------------------- #


def test_require_ancestor_is_a_no_op_outside_git(tmp_path: Path) -> None:
    engine.require_ancestor(tmp_path, "abc123", "def456")


def test_require_ancestor_accepts_failure_before_fix(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "bug.txt").write_text("broken\n", encoding="utf-8")
    pre = commit(tmp_path, "pre")
    (tmp_path / "bug.txt").write_text("fixed\n", encoding="utf-8")
    post = commit(tmp_path, "post")

    engine.require_ancestor(tmp_path, pre, post)


def test_require_ancestor_rejects_the_fix_before_the_failure(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "bug.txt").write_text("broken\n", encoding="utf-8")
    first = commit(tmp_path, "pre")
    (tmp_path / "bug.txt").write_text("fixed\n", encoding="utf-8")
    second = commit(tmp_path, "post")

    with pytest.raises(SystemExit):
        engine.require_ancestor(tmp_path, second, first)


def test_require_ancestor_rejects_an_unknown_revision(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "bug.txt").write_text("broken\n", encoding="utf-8")
    head = commit(tmp_path, "only")

    with pytest.raises(SystemExit):
        engine.require_ancestor(tmp_path, "deadbeef", head)


# --------------------------------------------------------------------------- #
# task lookup for repro
# --------------------------------------------------------------------------- #


def test_find_task_anywhere_finds_the_owning_queue(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    for role in ("Developer", "Tester"):
        (root / "Roles" / role).mkdir(parents=True)
        task = engine.new_task(f"{role} work")
        task["id"] = "T-0001"
        engine.write_tasks(root / "Roles" / role / "TaskQueue.md", [task], role)

    task, path, role, idx = engine._find_task_anywhere(root, "T-0001")

    assert role == "developer" and task["id"] == "T-0001"
    assert path == root / "Roles" / "Developer" / "TaskQueue.md" and idx == 0


def test_find_task_anywhere_reports_a_miss(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    (root / "Roles" / "Developer").mkdir(parents=True)
    engine.write_tasks(root / "Roles" / "Developer" / "TaskQueue.md", [], "developer")

    assert engine._find_task_anywhere(root, "T-4040") == (None, None, None, None)


def test_matching_tasks_reports_every_queue_hit(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    for role in ("Developer", "Tester"):
        (root / "Roles" / role).mkdir(parents=True)
        task = engine.new_task(f"{role} work")
        task["id"] = "T-0001"
        engine.write_tasks(root / "Roles" / role / "TaskQueue.md", [task], role)

    hits = engine.matching_tasks(root, "T-0001")

    assert [role for _t, _p, role, _i in hits] == ["developer", "tester"]


def test_matching_tasks_honours_the_role_hint(tmp_path: Path) -> None:
    project = tmp_path / "SampleProject"
    root = make_root(project)
    for role in ("Developer", "Tester"):
        (root / "Roles" / role).mkdir(parents=True)
        task = engine.new_task(f"{role} work")
        task["id"] = "T-0001"
        engine.write_tasks(root / "Roles" / role / "TaskQueue.md", [task], role)

    hits = engine.matching_tasks(root, "T-0001", "tester")

    assert [role for _t, _p, role, _i in hits] == ["tester"]
