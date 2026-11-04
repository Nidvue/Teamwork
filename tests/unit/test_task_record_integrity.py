"""A blank handle is not a task, and a self-check cannot reopen closed work.

Re-filed from the T-0019 audit rows A1/A6 after the dep half moved to T-0026.
Each test pins a defect that was reproduced before the fix.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.gitenv import child_env

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def git(project: Path, *args: str) -> None:
    env = child_env(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    result = subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def task_path(root: Path) -> Path:
    return root / "Roles" / "Developer" / engine.F_TASKS


def test_an_empty_handle_is_not_found(cli, project: Path) -> None:
    """A1: ``"" in text`` is True, so a blank handle selected the first task."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "keep me") == 0
    tasks = engine.parse_tasks(task_path(root))
    assert engine.find_task(tasks, "") is None
    assert engine.find_task(tasks, "   ") is None
    assert engine.find_dispute([engine.new_dispute("topic")], "") is None
    assert engine._find_entry([engine.new_entry("fact")], "") is None

    code = cli("--project", project, "task", "rm", "developer", "", "--by", "developer-1")
    assert code == 2, "a blank handle is a usage error, not a task"
    assert [t["id"] for t in engine.parse_tasks(task_path(root))] == ["T-0001"]


def test_a_self_check_cannot_resurrect_a_closed_task(cli, project: Path) -> None:
    """A6: a passing self-check wrote status=review unconditionally."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "dropped work") == 0
    assert cli("--project", project, "task", "add", "developer", "finished work") == 0
    tasks = engine.parse_tasks(task_path(root))
    tasks[0]["status"] = "dropped"
    tasks[1]["status"] = "done"
    engine.write_tasks(task_path(root), tasks, "developer")

    for handle in ("T-0001", "T-0002"):
        code = cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            handle,
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "pytest @rev -> 3 passed",
        )
        assert code == 2, f"{handle} must not be resurrected by a self-check"

    after = {t["id"]: t for t in engine.parse_tasks(task_path(root))}
    assert after["T-0001"]["status"] == "dropped"
    assert after["T-0002"]["status"] == "done"

    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--note",
            "reopening after a mistaken close",
            "--test",
            "pytest @rev -> 3 passed",
            "--force",
            "the close was a mistake",
        )
        == 0
    )
    reopened = {t["id"]: t for t in engine.parse_tasks(task_path(root))}
    assert reopened["T-0001"]["status"] == "review"
    assert "the close was a mistake" in reopened["T-0001"]["forced"]


def test_a_claimed_task_cannot_be_dropped_without_a_force_reason(cli, project, capsys):
    """A claimed task is live work: a sweep may not close it with a canned reason."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "live claimed work") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--claimed-by",
            "Developer-1",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "dropped") != 0
    )
    err = capsys.readouterr().err
    assert "it is live work" in err, err
    assert "claimed_by Developer-1" in err, err
    assert engine.parse_tasks(task_path(root))[0]["status"] != "dropped"


def test_a_review_gate_task_cannot_be_dropped_without_a_force_reason(cli, project, capsys):
    """A task in the review gate is live work too, even without a branch."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "in review") == 0
    tasks = engine.parse_tasks(task_path(root))
    tasks[0]["status"] = "review"
    tasks[0]["self_check"] = "passed"
    engine.write_tasks(task_path(root), tasks, "developer")
    capsys.readouterr()

    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "dropped") != 0
    )
    assert "in the review gate" in capsys.readouterr().err


def test_a_task_with_an_open_branch_cannot_be_dropped_without_a_force_reason(cli, project, capsys):
    """The branch is the second live signal; a merged branch names no live work."""
    git(project, "init", "-q", "-b", "main")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-qm", "base")
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "live branch") == 0
    assert (
        cli("--project", project, "branch", "start", "--agent", "Developer", "--task", "T-0001")
        == 0
    )
    (project / "README.md").write_text("base\nwork\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-qm", "work")
    capsys.readouterr()

    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "dropped") != 0
    )
    assert "open branch" in capsys.readouterr().err
    assert engine.parse_tasks(task_path(root))[0]["status"] != "dropped"


def test_a_forced_drop_records_the_blockers_and_audit_shows_them(cli, project, capsys):
    """The escape hatch exists, but it leaves a visible record instead of a silent one."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "abandoned work") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--claimed-by",
            "Developer-1",
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--status",
            "dropped",
            "--force",
            "the owner is gone and the work is abandoned",
        )
        == 0
    )
    task = engine.parse_tasks(task_path(root))[0]
    assert task["status"] == "dropped"
    assert "claimed_by Developer-1" in task["dropped_under_live"]
    assert "the owner is gone" in task["forced"]

    assert cli("--project", project, "audit") == 1
    out = capsys.readouterr().out
    assert "## dropped under a live claim" in out
    assert "developer T-0001: claimed_by Developer-1" in out


def test_a_plain_todo_task_can_be_dropped(cli, project):
    """The guard is about live work, not about making every drop a chore."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "stale idea") == 0
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "dropped") == 0
    )
    task = engine.parse_tasks(task_path(root))[0]
    assert task["status"] == "dropped"
    assert task["dropped_under_live"] == ""
