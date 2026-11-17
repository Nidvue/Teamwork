"""A finished lane leaves nothing behind: its worktree, its merged branch, its Scratch.

Why this test exists: measured on this host (2026-11-17) the lane runtime left 24
worktrees behind, 18 of them belonging to finished or retired lanes, one of them on
a branch that was already merged. Neither ``refresh`` nor ``_recycle_finished``
removed any of it, so the tree only got clean when a human swept it by hand. What
must never regress: the cleanup removes the lane's own paths, keeps a dirty
worktree and an unmerged branch with a printed reason, never touches a live lane,
and is idempotent (T-0088).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from teamwork import engine, gitutil, lanes
from teamwork.layout import agent_dir

ROSTER = "ceo,developer-1,tester-1,reviewer-1,reviewer-2"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def git(cwd: Path, *argv: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *argv], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER) == 0
    return team_root(project)


def finished_lane(
    cli,
    project: Path,
    *,
    state: str = "exited",
    merged: bool = True,
    dirty: bool = False,
    agent: str = "Developer-1",
    task: str = "T-0001",
) -> tuple:
    root = team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "cleanup probe") == 0
    branch = f"{agent.lower()}/{task.lower()}-cleanup-probe"
    git(project, "branch", branch)
    worktree = engine.lane_worktree(root, agent, task)
    git(project, "worktree", "add", str(worktree), branch)
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            task,
            "--branch",
            branch,
            "--force",
            "probe worktree",
        )
        == 0
    )
    (worktree / "work.txt").write_text("done\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "-m", "work")
    if dirty:
        (worktree / "uncommitted.txt").write_text("kept\n", encoding="utf-8")
    if merged:
        git(project, "merge", "--no-ff", "--no-edit", branch)
    scratch = agent_dir(root, agent) / "Scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "probe.tmp").write_text("junk\n", encoding="utf-8")
    lanes.write_run(
        root,
        {
            "id": "L-0001",
            "agent": agent,
            "role": "developer",
            "task": task,
            "state": state,
            "pid": 0,
            "provider": "deepinfra",
            "log": str(root / "Runtime" / "Lanes" / "L-0001.log"),
        },
    )
    return root, worktree, branch, scratch


def test_a_finished_lane_leaves_no_worktree_branch_or_scratch(cli, project: Path) -> None:
    root, worktree, branch, scratch = finished_lane(cli, project)
    assert worktree.is_dir() and gitutil.branch_exists(project, branch)

    lanes.settle(root, fold=True)

    assert not worktree.exists(), "the finished lane's worktree is still there"
    assert not gitutil.branch_exists(project, branch), "the merged branch is still there"
    assert not (scratch / "probe.tmp").exists(), "the lane's Scratch was not emptied"


def test_the_cleanup_is_idempotent(cli, project: Path) -> None:
    root, worktree, branch, _scratch = finished_lane(cli, project)
    first = lanes.cleanup_finished(root)
    second = lanes.cleanup_finished(root)
    assert first, "the first pass removed nothing"
    assert second == [], f"a second pass is not a no-op: {second}"
    assert not worktree.exists() and not gitutil.branch_exists(project, branch)


def test_a_dirty_worktree_and_its_branch_are_kept_with_a_reason(cli, project: Path) -> None:
    root, worktree, branch, _scratch = finished_lane(cli, project, dirty=True)

    lines = lanes.cleanup_finished(root)

    assert worktree.is_dir(), "a dirty worktree was removed and its work lost"
    assert gitutil.branch_exists(project, branch)
    assert any("uncommitted work" in line for line in lines), lines


def test_an_unmerged_branch_is_kept_with_a_reason(cli, project: Path) -> None:
    root, worktree, branch, _scratch = finished_lane(cli, project, merged=False)

    lines = lanes.cleanup_finished(root)

    assert worktree.is_dir(), "a worktree holding unmerged commits was removed"
    assert gitutil.branch_exists(project, branch)
    assert any(f"not in {gitutil.DEFAULT_BASE}" in line for line in lines), lines


def test_a_terminal_run_keeps_the_scratch_of_a_live_lane_of_its_instance(
    cli, project: Path
) -> None:
    root, _worktree, _branch, scratch = finished_lane(cli, project)
    live = scratch / "in-flight.tmp"
    live.write_text("a live lane is writing this\n", encoding="utf-8")
    live_run = {
        "id": "L-0002",
        "agent": "Developer-1",
        "role": "developer",
        "task": "T-0002",
        "state": "running",
        "pid": 4242,
        "provider": "deepinfra",
        "log": str(root / "Runtime" / "Lanes" / "L-0002.log"),
    }
    lanes.write_run(root, live_run)

    lanes.cleanup_finished(root)

    assert live.exists(), "a terminal run emptied the Scratch of a LIVE lane of its instance"

    lanes.write_run(root, {**live_run, "state": "exited"})
    lanes.cleanup_finished(root)

    assert not live.exists(), "the Scratch was never emptied once no live lane held it"


def test_a_live_lane_is_never_touched(cli, project: Path) -> None:
    root, worktree, branch, _scratch = finished_lane(cli, project, state="running")

    assert lanes.cleanup_finished(root) == []

    assert worktree.is_dir()
    assert gitutil.branch_exists(project, branch)
