"""A blank handle is not a task, and a self-check cannot reopen closed work.

Re-filed from the T-0019 audit rows A1/A6 after the dep half moved to T-0026.
Each test pins a defect that was reproduced before the fix.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


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
