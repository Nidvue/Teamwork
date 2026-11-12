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
    assert engine.parse_tasks(path) == []


def test_find_task_by_id_and_substring() -> None:
    tasks = [engine.new_task("alpha"), engine.new_task("beta")]
    tasks[0]["id"] = "T-0001"
    tasks[1]["id"] = "T-0002"
    assert engine.find_task(tasks, "T-0002") == 1
    assert engine.find_task(tasks, "alpha") == 0
    assert engine.find_task(tasks, "nope") is None


def test_review_fails_survives_a_round_trip_as_an_int(tmp_path: Path) -> None:
    """`new_task` seeds `review_fails` as int; the renderer writes text.

    Every reader used to have to remember `int(...)` because the parser handed the
    field back as a string, so a reloaded queue changed the field's type and a
    direct comparison raised `TypeError` on the second read only.
    """
    path = tmp_path / "TaskQueue.md"
    task = engine.new_task("failing review")
    task["review_fails"] = 2
    engine.write_tasks(path, [task], "developer")

    reloaded = engine.parse_tasks(path)[0]
    assert reloaded["review_fails"] == 2
    assert isinstance(reloaded["review_fails"], int), type(reloaded["review_fails"])


def test_a_corrupt_review_fails_line_parses_to_zero(tmp_path: Path) -> None:
    """A hand-edited queue must not turn a counter into a string that never compares."""
    path = tmp_path / "TaskQueue.md"
    path.write_text(
        "# Task queue\n\n"
        "## T-0001 · hand edited\n"
        "- priority: P2\n"
        "- status: todo\n"
        "- review_fails: garbage\n"
        "\n"
        "body\n",
        encoding="utf-8",
    )
    assert engine.parse_tasks(path)[0]["review_fails"] == 0


def test_a_new_task_round_trips_through_the_renderer(tmp_path: Path) -> None:
    """Every field the renderer writes must have a `new_task` default.

    A field added to the renderer alone reappears as a new key after
    parse -> render -> parse, which is what the records probe measures on the live
    tree. The probe skips in CI (no team tree), so the default set is pinned here.
    """
    task = engine.new_task("Round trip")
    path = tmp_path / "TaskQueue.md"
    engine.write_tasks(path, [task], "developer")
    reparsed = engine.parse_tasks(path)[0]

    assert set(reparsed) == set(task), set(reparsed) ^ set(task)
    for field in ("dropped_under_live", "review_claim_profile", "review_claim_lease"):
        assert task[field] == ""


def test_task_set_repairs_an_area_but_refuses_a_test_file_path(cli, tmp_path: Path) -> None:
    """A done task's area carries into `tests plan`, so the task record needs the guard.

    The phantom `tests-unit-test-ci-contr` area survived a repair of the test record
    because `areas_in_use` unions the area of every done task (T-0107) with the
    record areas: the carrier was the task, and no task write path refused a path.
    """
    assert cli("init", "--no-git", "--agents", "ceo,developer-1") == 0
    assert cli("task", "add", "developer-1", "a task with no area") == 0

    assert (
        cli(
            "task",
            "set",
            "developer-1",
            "a task with no area",
            "--area",
            "tests-unit-test-ci-contr",
        )
        != 0
    )
    assert (
        cli("task", "set", "developer-1", "a task with no area", "--area", "tests/unit/test_ci.py")
        != 0
    )

    assert cli("task", "set", "developer-1", "a task with no area", "--area", "ci-contracts") == 0
    queue = next((tmp_path / ".pi" / "Teamwork" / "Teams").glob("*/Roles/Developer/TaskQueue.md"))
    assert "- area: ci-contracts" in queue.read_text(encoding="utf-8")


def test_commit_refuses_a_path_shaped_area_on_the_task_field(cli, tmp_path: Path) -> None:
    """`commit --area` is the third writer of the task area and needs the same guard.

    It slugifies to 24 chars, so the phantom `tests-unit-test-ci-contr` (23) survived
    the two guarded paths (task set --area, tests add --area) and could be re-created
    by a commit whose area named a test file.
    """
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main", "."], check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "config", "user.email", "tester@agents.nidvue.com"], check=True)
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], check=True)
    subprocess.run(["git", "commit", "-qm", "base"], check=True)

    assert cli("init", "--agents", "ceo,developer-1") == 0
    assert cli("task", "add", "developer-1", "a task with no area") == 0
    queue = next((tmp_path / ".pi" / "Teamwork" / "Teams").glob("*/Roles/Developer/TaskQueue.md"))
    task_id = engine.parse_tasks(queue)[0]["id"]

    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    subprocess.run(["git", "switch", "-q", "-c", "developer-1/t-0001"], check=True)

    def commit(area: str) -> int:
        return cli(
            "commit",
            "--role",
            "developer",
            "--type",
            "test",
            "--task",
            task_id,
            "--area",
            area,
            "--goal",
            "g",
            "--deliverable",
            "d",
            "--why",
            "w",
            "--status",
            "s",
            "--result",
            "r",
            "--paths",
            "b.txt",
        )

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout
    assert commit("tests-unit-test-ci-contr") != 0
    assert "- area: tests-unit-test-ci-contr" not in queue.read_text(encoding="utf-8")
    assert (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout
        == head
    )
    assert commit("ci-contracts") == 0
    assert "- area: ci-contracts" in queue.read_text(encoding="utf-8")
