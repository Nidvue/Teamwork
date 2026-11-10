"""Unit tests for task records: new_task, parse_tasks, render_tasks."""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def test_new_task_defaults() -> None:
    task = engine.new_task("  Build the thing  ")
    assert task["title"] == "Build the thing"
    assert task["priority"] == "P2"
    assert task["status"] == "todo"
    assert task["review"] == "required"
    assert task["review_status"] == "pending"
    assert task["self_check"] == "pending"
    assert task["review_fails"] == 0
    assert task["id"] == ""
    assert task["claimed_by"] == ""


def test_new_task_strips_optional_fields() -> None:
    task = engine.new_task(
        "x",
        priority="P0",
        deps=" T-0002 ",
        shared=" issue ",
        tags=" a ",
        body=" body ",
        evidence=" ev ",
    )
    assert task["deps"] == "T-0002"
    assert task["shared"] == "issue"
    assert task["tags"] == "a"
    assert task["body"] == "body"
    assert task["evidence"] == "ev"


def test_new_task_coerces_invalid_priority_and_status() -> None:
    task = engine.new_task("x", priority="P9", status="bogus")
    assert task["priority"] == "P2"
    assert task["status"] == "todo"


def test_new_task_no_review_marks_gates_na() -> None:
    task = engine.new_task("chore", review="na")
    assert task["review"] == "na"
    assert task["review_status"] == "na"
    assert task["self_check"] == "na"


def test_parse_tasks_missing_file_is_empty(tmp_path: Path) -> None:
    assert engine.parse_tasks(tmp_path / "missing.md") == []


def test_task_roundtrip_preserves_fields(tmp_path: Path) -> None:
    path = tmp_path / "TaskQueue.md"
    task = engine.new_task(
        "Implement parser",
        priority="P0",
        deps="T-0002",
        shared="PR-7",
        tags="core,api",
        body="line one\nline two",
        evidence="pytest -> 3 passed",
    )
    engine.write_tasks(path, [task], "developer")

    out = engine.parse_tasks(path)
    assert len(out) == 1
    assert out[0]["id"] == "T-0001"
    assert out[0]["title"] == "Implement parser"
    assert out[0]["priority"] == "P0"
    assert out[0]["deps"] == "T-0002"
    assert out[0]["shared"] == "PR-7"
    assert out[0]["tags"] == "core,api"
    assert out[0]["evidence"] == "pytest -> 3 passed"
    assert "line one" in out[0]["body"]
    assert "line two" in out[0]["body"]


def test_render_tasks_orders_by_priority_then_id(tmp_path: Path) -> None:
    path = tmp_path / "TaskQueue.md"
    tasks = [
        engine.new_task("low", priority="P2"),
        engine.new_task("high", priority="P0"),
        engine.new_task("mid", priority="P1"),
    ]
    text = engine.render_tasks(tasks, "developer", path)
    assert text.index("high") < text.index("mid") < text.index("low")


def test_render_assigns_stable_sequential_ids(tmp_path: Path) -> None:
    path = tmp_path / "TaskQueue.md"
    tasks = [engine.new_task("one")]
    engine.write_tasks(path, tasks, "developer")
    assert engine.parse_tasks(path)[0]["id"] == "T-0001"

    again = engine.parse_tasks(path)
    again.append(engine.new_task("two"))
    engine.write_tasks(path, again, "developer")
    ids = [t["id"] for t in engine.parse_tasks(path)]
    assert ids == ["T-0001", "T-0002"]


def test_parse_tasks_drops_entries_without_title_or_body(tmp_path: Path) -> None:
    path = tmp_path / "TaskQueue.md"
    path.write_text(
        "# Task queue\n\n## T-0001 · \n- priority: P2\n- status: todo\n\n",
        encoding="utf-8",
    )
    # An entry with neither title nor body is not a real task.
    assert engine.parse_tasks(path) == []


def test_find_task_by_id_and_substring() -> None:
    tasks = [engine.new_task("alpha"), engine.new_task("beta")]
    tasks[0]["id"] = "T-0001"
    tasks[1]["id"] = "T-0002"
    assert engine.find_task(tasks, "T-0002") == 1
    assert engine.find_task(tasks, "alpha") == 0
    assert engine.find_task(tasks, "nope") is None
