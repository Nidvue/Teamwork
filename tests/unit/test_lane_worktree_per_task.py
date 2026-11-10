"""One lane, one checkout: a second task of one instance gets its own worktree."""

from __future__ import annotations

from pathlib import Path

from teamwork.engine import lane_worktree
from teamwork.layout import work_repo


def _mark_worktree(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").write_text("gitdir: /nowhere\n", encoding="utf-8")
    return path


def test_lane_worktree_is_per_task(tmp_path):
    root = tmp_path / "Team"
    first = lane_worktree(root, "Developer-2", "T-0009")
    second = lane_worktree(root, "Developer-2", "T-0010")
    assert first != second
    assert first.parent == second.parent
    assert first.parent.name == "Developer-2"
    assert first.parent.parent.name == "Worktrees"
    assert first.name == "T-0009"
    assert second.name == "T-0010"


def test_lane_worktree_is_per_instance(tmp_path):
    root = tmp_path / "Team"
    assert lane_worktree(root, "Developer-2", "T-0009") != lane_worktree(
        root, "Developer-3", "T-0009"
    )


def test_lane_worktree_is_stable_on_the_second_call(tmp_path):
    root = tmp_path / "Team"
    assert lane_worktree(root, "Developer-2", "T-0029") == lane_worktree(
        root, "Developer-2", "T-0029"
    )


def test_work_repo_finds_the_nested_lane_worktree(tmp_path):
    root = tmp_path / "Team"
    lane = _mark_worktree(lane_worktree(root, "Developer-2", "T-0029"))
    inside = lane / "src" / "teamwork"
    inside.mkdir(parents=True)
    assert work_repo(root, cwd=inside) == lane


def test_work_repo_finds_the_flat_lane_worktree(tmp_path):
    root = tmp_path / "Team"
    lane = _mark_worktree(root / "Runtime" / "Worktrees" / "Dev")
    assert work_repo(root, cwd=lane / "tests") == lane
