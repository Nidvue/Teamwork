"""`task archive`: closed evidence leaves the queue, the id stays resolvable.

The queue is a startup read; a closed review's long evidence costs every run.
Archiving moves that text to the role's `TaskArchive.md` and leaves the task id
and a pointer in the queue, so `trace`, the board and the audit still resolve it.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import config, engine, records


def team_root(project: Path) -> Path:
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def seed_done_task(root: Path) -> str:
    path = engine.task_file(root, "ceo")
    tasks = records.parse_tasks(path)
    task = records.new_task(
        "A closed review with long evidence", evidence="pytest @abc1234 -> 3 passed"
    )
    task["status"] = "done"
    task["self_note"] = "self note " * 400
    task["review_evidence"] = "review evidence " * 400
    tasks.append(task)
    records.write_tasks(path, tasks, "ceo")
    return engine.parse_tasks(path)[-1]["id"]


def test_archive_moves_the_long_fields_and_keeps_the_id(cli, project, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    task_id = seed_done_task(root)
    queue = engine.task_file(root, "ceo")
    before = queue.stat().st_size

    assert cli("--project", project, "task", "archive", "ceo") == 0
    out = capsys.readouterr().out
    assert "archived 1 closed task(s)" in out

    after = engine.parse_tasks(queue)
    archived = [t for t in after if t["id"] == task_id][0]
    assert archived["archived"] == f"{config.F_TASK_ARCHIVE}#{task_id.lower()}"
    assert archived["self_note"] == ""
    assert archived["review_evidence"] == ""
    assert queue.stat().st_size < before

    archive = engine.role_dir(root, "ceo") / config.F_TASK_ARCHIVE
    text = archive.read_text(encoding="utf-8")
    assert f"## {task_id} " in text
    assert "self note " in text and "review evidence " in text


def test_archive_is_idempotent(cli, project, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    seed_done_task(root)
    assert cli("--project", project, "task", "archive", "ceo") == 0
    capsys.readouterr()

    assert cli("--project", project, "task", "archive", "ceo") == 0
    assert "nothing to archive" in capsys.readouterr().out


def test_the_audit_resolves_evidence_through_the_pointer(cli, project, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    task_id = seed_done_task(root)
    assert cli("--project", project, "task", "archive", "ceo") == 0
    capsys.readouterr()

    assert cli("--project", project, "audit") in (0, 1)
    out = capsys.readouterr().out
    section = out.split("## done without evidence", 1)[1].split("\n## ", 1)[0]
    assert task_id not in section, section
    assert "- none" in section, section


def test_a_pointer_without_a_section_is_not_evidence() -> None:
    """A pointer is not a claim: the archive section has to exist."""
    assert (
        engine._archived_evidence(
            Path("/nonexistent"), "ceo", {"id": "T-1", "archived": "TaskArchive.md#t-1"}
        )
        is False
    )
    assert engine._archived_evidence(Path("/nonexistent"), "ceo", {"id": "T-1"}) is False


def test_a_done_task_without_evidence_is_not_archived(cli, project, capsys) -> None:
    """Archiving must not move an audit finding out of the queue that reports it."""
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    path = engine.task_file(root, "ceo")
    tasks = records.parse_tasks(path)
    task = records.new_task("Done without proof")
    task["status"] = "done"
    tasks.append(task)
    records.write_tasks(path, tasks, "ceo")
    task_id = engine.parse_tasks(path)[-1]["id"]
    capsys.readouterr()

    assert cli("--project", project, "task", "archive", "ceo") == 1
    assert "done without execution evidence" in capsys.readouterr().out

    kept = [t for t in engine.parse_tasks(path) if t["id"] == task_id][0]
    assert kept["archived"] == ""
    assert not (engine.role_dir(root, "ceo") / config.F_TASK_ARCHIVE).exists()


def test_a_pointer_with_only_a_status_is_not_evidence(tmp_path: Path) -> None:
    root = tmp_path / "team"
    role_dir = engine.role_dir(root, "ceo")
    role_dir.mkdir(parents=True)
    archive = role_dir / config.F_TASK_ARCHIVE
    archive.write_text("## T-1 · x\n\n- status: done\n", encoding="utf-8")
    task = {"id": "T-1", "archived": f"{config.F_TASK_ARCHIVE}#t-1"}

    assert engine._archived_evidence(root, "ceo", task) is False

    archive.write_text("## T-1 · x\n\n- status: done\n- self_note: tested\n", encoding="utf-8")
    assert engine._archived_evidence(root, "ceo", task) is True
