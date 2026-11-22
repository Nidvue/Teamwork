"""A superseded repro override must not hold its gate open forever.

``tests repro --force <why>`` records why the fail -> pass pair is missing, and
``audit`` counts that note as a gate override in force. When the pair is later
recorded for real, the old note has to go: a task whose defect is now proved
cannot keep failing the project gate on an override that names a revision the
history no longer holds.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    )
    return team_root(project)


def developer_task(root: Path) -> dict:
    return engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]


def add_bug_task(cli, project: Path) -> None:
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "the bus address cannot exist on Windows",
            "--priority",
            "P1",
            "--bug",
        )
        == 0
    )


def record_repro(cli, project: Path, force: str = "") -> int:
    argv = [
        "--project",
        project,
        "tests",
        "repro",
        "T-0001",
        "--by",
        "developer-1",
        "--pre-rev",
        "aaa111",
        "--pre-evidence",
        "pytest tests/unit/test_bus.py @aaa111 -> 1 failed",
        "--post-rev",
        "bbb222",
        "--post-evidence",
        "pytest tests/unit/test_bus.py @bbb222 -> 45 passed",
    ]
    if force:
        argv += ["--force", force]
    return cli(*argv)


def test_a_forced_repro_record_holds_the_override(cli, project: Path) -> None:
    init(cli, project)
    add_bug_task(cli, project)

    assert record_repro(cli, project, force="the defect cannot be reproduced here") == 0
    task = developer_task(team_root(project))
    assert "repro by Developer-1" in task["forced"]


def test_a_clean_repro_record_supersedes_the_older_override(cli, project: Path) -> None:
    init(cli, project)
    add_bug_task(cli, project)
    record_repro(cli, project, force="the defect cannot be reproduced here")
    root = team_root(project)
    before = developer_task(root)["forced"]
    assert before

    assert record_repro(cli, project) == 0

    task = developer_task(root)
    assert "repro by Developer-1" not in task["forced"], before
    assert task["repro_by"] == "Developer-1"
    assert task["forced"] == ""
    actions = [entry["action"] for entry in engine.ledger_read(root)]
    assert actions.count("tests.repro") == 2
    assert actions.count("tests.repro.supersede") == 1


def test_an_unrelated_override_survives_a_clean_repro_record(cli, project: Path) -> None:
    init(cli, project)
    add_bug_task(cli, project)
    root = team_root(project)
    path = root / "Roles" / "Developer" / "TaskQueue.md"
    tasks = engine.parse_tasks(path)
    tasks[0]["forced"] = "repro by Developer-1: no repro possible | audit override: kept open"
    engine.write_tasks(path, tasks, "developer")

    assert record_repro(cli, project) == 0

    assert developer_task(root)["forced"] == "audit override: kept open"
