"""A review-failed task must come back to its owner's queue (T-0138).

Why these tests exist: a failed verdict left the task at ``status=doing`` with its
claim intact, and dispatch only takes ``status=todo`` - so neither `swarm run` nor
`pulse --commit` saw it ("assigned: 0 unit(s) claimed with no live lane") and the
rework stalled until a human ran `task set --status todo` (K-0050, T-0134). The
verdict is a hand-back, so the record has to say the work is available again.

Pinned here: a fail puts the task back in the executable set of its role, the
claim stays with the owner instance (nobody else's lane can pick up a peer's
rework), a second fail does the same thing, and a task that never failed a review
is untouched by the rule.

Owner: developer. Layer: unit. Area: dispatch.
"""

from __future__ import annotations

from pathlib import Path

from test_review_credit import seed, team_root

from teamwork import engine, lanes, records

DEFECT = "the limit check uses > where it must use >="
DETECTOR = "a request exactly at the limit is rejected instead of accepted"


def fail(cli, project: Path, findings: str = DEFECT) -> int:
    return cli(
        "--project",
        project,
        "review",
        "developer",
        "T-0001",
        "--by",
        "reviewer-1",
        "--result",
        "fail",
        "--detects",
        DETECTOR,
        "--findings",
        findings,
    )


def task_record(project: Path) -> dict:
    return engine.parse_tasks(engine.task_file(team_root(project), "developer"))[0]


def ready_ids(project: Path, role: str = "developer") -> list:
    return [task["id"] for task in engine._ready_for_role(team_root(project), role)]


def test_a_failed_verdict_puts_the_task_back_in_the_owner_queue(cli, project) -> None:
    """The defect: doing + claimed_by left the rework invisible to dispatch."""
    seed(cli, project)
    assert ready_ids(project) == []

    assert fail(cli, project) == 0

    task = task_record(project)
    assert task["review_status"] == "failed"
    assert task["status"] == "todo", task["status"]
    assert task["claimed_by"] == "Developer-1", task["claimed_by"]
    assert records.executable(task, {}, {}, team_root(project)) is True
    assert ready_ids(project) == ["T-0001"]


def test_the_rework_stays_with_the_owner_instance(cli, project) -> None:
    """A second fail repeats the hand-back, and no other lane may take it."""
    seed(cli, project)
    assert fail(cli, project) == 0
    assert fail(cli, project, findings="still wrong") == 0

    task = task_record(project)
    assert task["review_fails"] == 2
    assert task["status"] == "todo"
    assert task["claimed_by"] == "Developer-1"
    assert ready_ids(project) == ["T-0001"]


def test_the_dispatch_plan_hands_the_rework_to_its_owner_only(cli, project) -> None:
    """A second idle developer instance must not take a peer's hand-back."""
    seed(cli, project)
    assert cli("--project", project, "instance", "add", "developer", "--count", 2) == 0
    assert fail(cli, project) == 0
    root = team_root(project)
    path = engine.task_file(root, "developer")

    def plan() -> dict:
        return {
            item.task: item.instance for item in lanes.dispatch_plan(root) if not item.review_owner
        }

    assert plan().get("T-0001") == "Developer-1", plan()

    tasks = engine.parse_tasks(path)
    busy = dict(tasks[0], id="T-0002", title="hold the owner's slot", status="doing")
    engine.write_tasks(path, [*tasks, busy], "developer")

    assert "T-0001" not in plan(), plan()
    assert "Developer-2" not in plan().values(), plan()


def test_a_task_that_never_failed_is_not_dispatched_again(cli, project) -> None:
    """The empty case: the rule keys on the verdict, not on the claim."""
    seed(cli, project)
    root = team_root(project)
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    tasks[0]["status"] = "doing"
    tasks[0]["review_status"] = "pending"
    engine.write_tasks(engine.task_file(root, "developer"), tasks, "developer")

    assert ready_ids(project) == []
