"""Integration tests: cross-role task-graph dependency resolution on the real CLI.

A downstream lane must stay blocked while its ``role:T-id`` dependency is open,
be released exactly when that role's queue says the task is ``done``, and never
be released by a same-numbered task in another role's queue.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

AGENTS = ("ceo", "developer-1", "tester-1", "reviewer-1")


def team_root(project: Path) -> Path:
    """The hidden tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init_team(cli, project: Path) -> Path:
    code = cli("--project", project, "init", "--agents", ",".join(AGENTS), "--no-git")
    assert code == 0, f"init returned {code}"
    root = team_root(project)
    assert root.is_dir()
    return root


def queue(root: Path, role_dir: str) -> list:
    return engine.parse_tasks(root / "Roles" / role_dir / "TaskQueue.md")


def task(tasks: list, task_id: str) -> dict:
    found = [t for t in tasks if t["id"] == task_id]
    assert len(found) == 1, f"expected exactly one {task_id}, got {found}"
    return found[0]


def test_open_cross_role_dependency_blocks_the_downstream_lane(cli, project: Path, capsys) -> None:
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build the API",
            "--priority",
            "P0",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Test the API",
            "--priority",
            "P0",
            "--deps",
            "developer-1:T-0001",
        )
        == 0
    )
    capsys.readouterr()

    # The dependency is open, so nothing is executable and nothing is claimed.
    assert cli("--project", project, "task", "next", "tester-1") == 3
    out = capsys.readouterr().out
    assert "no unclaimed executable task" in out, out
    assert "deps=developer-1:T-0001" in out, out
    tester = queue(root, "Tester")
    assert task(tester, "T-0001")["status"] == "todo"
    assert task(tester, "T-0001")["claimed_by"] == ""
    assert task(tester, "T-0001")["deps"] == "developer-1:T-0001"


def test_done_cross_role_dependency_releases_the_downstream_lane(cli, project: Path) -> None:
    """Closing the developer task through the documented path releases the tester.

    The engine's accepted path for a chore with ``--no-review`` is
    ``task set <agent> <T-id> --status done --evidence '<cmd @rev -> result>'``:
    the evidence gate still applies, the independent-review gate does not.
    """
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build the API",
            "--priority",
            "P0",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Test the API",
            "--priority",
            "P0",
            "--deps",
            "developer-1:T-0001",
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "tester-1") == 3

    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer-1",
            "T-0001",
            "--status",
            "done",
            "--evidence",
            "true @test-rev -> ok",
        )
        == 0
    )
    assert task(queue(root, "Developer"), "T-0001")["status"] == "done"

    assert cli("--project", project, "task", "next", "tester-1") == 0
    released = task(queue(root, "Tester"), "T-0001")
    assert released["status"] == "doing"
    assert released["claimed_by"] == "tester-1"


def test_role_qualified_dependency_does_not_match_another_roles_task_id(cli, project: Path) -> None:
    """``developer-1:T-0001`` releases, ``reviewer-1:T-0001`` does not.

    Both queues use the number ``T-0001``; only the role the dependency names may
    satisfy it. The reviewer's T-0001 exists but stays ``todo``, so that
    dependency is satisfied by nothing and its task stays blocked.
    """
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build the API",
            "--priority",
            "P0",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Test the API",
            "--priority",
            "P0",
            "--deps",
            "developer-1:T-0001",
        )
        == 0
    )
    # The reviewer's own T-0001 exists but is never closed in this test, so only
    # the developer dependency may release the tester.
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "reviewer-1",
            "Review the API",
            "--priority",
            "P1",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Blocked on a reviewer task",
            "--priority",
            "P1",
            "--deps",
            "reviewer-1:T-0001",
        )
        == 0
    )
    assert [t["id"] for t in queue(root, "Reviewer")] == ["T-0001"]
    assert task(queue(root, "Reviewer"), "T-0001")["status"] == "todo"

    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer-1",
            "T-0001",
            "--status",
            "done",
            "--evidence",
            "true @test-rev -> ok",
        )
        == 0
    )

    assert cli("--project", project, "task", "next", "tester-1") == 0
    tester = queue(root, "Tester")
    assert task(tester, "T-0001")["status"] == "doing"
    # Same number, different role: the reviewer-qualified task must stay blocked.
    assert task(tester, "T-0002")["status"] == "todo"
    assert cli("--project", project, "task", "next", "tester-1") == 3


def test_unknown_role_dependency_is_refused_before_the_task_is_written(
    cli, project: Path, capsys
) -> None:
    """A dependency that names no task is refused at the write, exit 2.

    It used to be stored verbatim and read as an unsatisfied dependency, so the
    task was unexecutable forever while the queue looked healthy: `task next`
    reported the lane as idle and never the reference as dangling.
    """
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Dangling dependency",
            "--priority",
            "P0",
            "--deps",
            "nosuchrole:T-0099",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "nosuchrole:T-0099" in err, err
    assert "names no task" in err, err
    assert not (root / "Roles" / "Nosuchrole").exists()
    # Nothing was written: the queue is empty, so the deadlock never existed.
    assert queue(root, "Tester") == []


def test_a_self_dependency_is_refused_before_the_queue_deadlocks(
    cli, project: Path, capsys
) -> None:
    """`task add developer second --deps T-0002` used to exit 0 and deadlock the queue."""
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer-1", "first", "--no-review") == 0
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "second",
            "--deps",
            "T-0002",
            "--no-review",
        )
        == 2
    )
    assert "depends on itself" in capsys.readouterr().err

    tasks = queue(root, "Developer")
    assert [t["id"] for t in tasks] == ["T-0001"]
    # The queue still runs: the one task is executable and claimable.
    assert task(tasks, "T-0001")["status"] == "todo"
    assert cli("--project", project, "task", "next", "developer-1") == 0


def test_a_cross_role_cycle_is_refused_before_the_queue_deadlocks(
    cli, project: Path, capsys
) -> None:
    """The T-0001 <-> T-0002 cycle the audit reproduced is now exit 2, with its path."""
    root = init_team(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build the API",
            "--priority",
            "P0",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester-1",
            "Test the API",
            "--priority",
            "P0",
            "--deps",
            "developer:T-0001",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli("--project", project, "task", "set", "developer-1", "T-0001", "--deps", "tester:T-0001")
        == 2
    )
    err = capsys.readouterr().err
    assert "dependency cycle: developer:T-0001 -> tester:T-0001 -> developer:T-0001" in err, err

    # Both queues are exactly as they were; the downstream task is still blocked
    # for the honest reason (its dependency is open), not by a cycle.
    assert task(queue(root, "Developer"), "T-0001")["deps"] == ""
    assert task(queue(root, "Tester"), "T-0001")["deps"] == "developer:T-0001"
    assert cli("--project", project, "task", "check") == 0
