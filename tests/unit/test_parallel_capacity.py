"""Why these tests exist: the team serialised itself. One lane took one task, sat
in review, and every other lane idled - measured on a real run where 12 tasks were
open, one agent was working and nine lanes were waiting. Two changes fix the
mechanics: a lane may hold more than one unit of work (LANE_WIP), and a dependency
can release at *submit* time instead of waiting for the whole task to be `done`.

Pinned here: `task next --capacity N` claims N tasks at once, a second call does
not double-claim, `role:T-id@review` and `@started` unblock earlier than `done`,
and one pulse fills a lane up to its WIP limit instead of handing it one task.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def add(cli, project: Path, role: str, title: str, deps: str = "") -> None:
    args = ["--project", project, "task", "add", role, title]
    if deps:
        args += ["--deps", deps]
    assert cli(*args) == 0


def test_task_next_capacity_claims_several_at_once(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    for i in range(3):
        add(cli, project, "developer", f"unit {i}")

    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "3") == 0
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert [t["status"] for t in tasks] == ["doing", "doing", "doing"]
    assert {t["claimed_by"].lower() for t in tasks} == {"developer-1"}

    # nothing left: a second call must not re-claim or invent work
    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "3") == 3


def test_dependency_can_release_at_review_or_started(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    add(cli, project, "developer", "produce the contract")
    add(cli, project, "tester", "test against it", "developer:T-0001@review")
    add(cli, project, "tester", "shadow the work", "developer:T-0001@started")

    # not started yet: both downstream tasks wait
    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert [t["status"] for t in tester] == ["todo", "todo"]

    assert cli("--project", project, "task", "next", "developer-1") == 0
    # started: the shadow task may begin, the review-gated one still waits
    assert cli("--project", project, "task", "next", "tester-1", "--capacity", "2") == 0
    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert tester[1]["status"] == "doing" and tester[0]["status"] == "todo"

    # submitted: the review-gated task unblocks without waiting for `done`
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
            "re-read the contract",
            "--test",
            "true @rev -> ok",
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "tester-1") == 0
    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert tester[0]["status"] == "doing"


def test_pulse_fills_a_lane_up_to_its_wip_limit(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    for i in range(3):
        add(cli, project, "developer", f"unit {i}")

    assert cli("--project", project, "pulse", "--commit") == 0
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    claimed = [t for t in tasks if t["status"] == "doing"]
    assert len(claimed) == engine.LANE_WIP, [t["status"] for t in tasks]
    assert {t["claimed_by"].lower() for t in claimed} == {"developer-1"}

    # a full lane means there is nothing to dispatch (exit 3), and it never
    # over-claims: the limit holds across wakes
    assert cli("--project", project, "pulse", "--commit") in (0, 3)
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert len([t for t in tasks if t["status"] == "doing"]) == engine.LANE_WIP
    assert len([t for t in tasks if t["status"] == "todo"]) == len(tasks) - engine.LANE_WIP
