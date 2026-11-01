"""Task intake is idempotent and every unit of work carries a mandate.

Two properties, measured through the CLI because that is where a caller acts:

1. **Idempotence.** ``task add --key k`` twice adds one task. The second call
   prints the existing id and title, appends a ``task.duplicate`` ledger record
   and exits 0, so a producer that retries after a timeout - or two producers
   that accept the same request - end with one unit of work and a trail that says
   so, instead of a second ticket nobody asked for.
2. **Mandate.** ``--mandate inferred`` means the team derived the work itself and
   must record ``--basis`` (why it may be done); without one the add is refused.
   An explicit task - and every task in a queue written before these fields
   existed - reads as ``explicit`` with an empty basis, and ``task list`` /
   ``board`` mark an inferred task with an ``[inferred]`` badge.

The backward-compatibility case is the one that decides whether an upgraded tool
can read an old team tree, so it is pinned against a queue file written by hand,
not one this tool generated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"

LEGACY_QUEUE = """# Task queue - developer (shared by every developer instance)

> Priority ordered (P0 highest).

## T-0001 · an old task from before the mandate fields
- priority: P1
- status: todo
- deps:
- shared:
- tags:
- area:
- kind:
- review: required
- review_status: pending
- self_check: pending
- claimed_by:
- branch:
- review_fails: 0
- created: 2026-01-01
- updated: 2026-01-01

Build the old thing.
"""


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def tasks_of(root: Path, role: str = "developer") -> list:
    return engine.parse_tasks(engine.task_file(root, role))


def ledger_actions(root: Path) -> list:
    return [rec["action"] for rec in engine.ledger_read(root)]


# --------------------------------------------------------------------------- #
# Idempotent intake
# --------------------------------------------------------------------------- #


def test_a_repeated_intake_key_creates_one_task_and_names_the_existing_one(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project)
    first = cli(
        "--project",
        project,
        "task",
        "add",
        "developer",
        "export the ledger",
        "--key",
        "export-ledger",
    )
    assert first == 0
    capsys.readouterr()

    second = cli(
        "--project",
        project,
        "task",
        "add",
        "developer",
        "export the ledger",
        "--key",
        "export-ledger",
    )
    out = capsys.readouterr().out
    assert second == 0, "a repeated key is a no-op, not a failure"
    assert "T-0001" in out and "export the ledger" in out, out
    assert len(tasks_of(root)) == 1
    assert ledger_actions(root).count("task.duplicate") == 1
    assert ledger_actions(root).count("task.add") == 1


def test_a_repeated_key_does_not_consume_a_task_id(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one", "--key", "k1") == 0
    assert cli("--project", project, "task", "add", "developer", "one", "--key", "k1") == 0
    assert cli("--project", project, "task", "add", "developer", "two", "--key", "k2") == 0

    ids = [t["id"] for t in tasks_of(root)]
    assert ids == ["T-0001", "T-0002"], ids


def test_two_different_keys_create_two_tasks(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one", "--key", "k1") == 0
    assert cli("--project", project, "task", "add", "developer", "two", "--key", "k2") == 0

    tasks = tasks_of(root)
    assert [t["intake_key"] for t in tasks] == ["k1", "k2"]
    assert ledger_actions(root).count("task.duplicate") == 0


def test_a_repeated_key_binds_per_role_queue(cli, project: Path) -> None:
    """Two queues may carry the same key: the key names a request, not a team."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one", "--key", "k1") == 0
    assert cli("--project", project, "task", "add", "tester", "one", "--key", "k1") == 0

    assert len(tasks_of(root, "developer")) == 1
    assert len(tasks_of(root, "tester")) == 1


def test_a_repeated_key_wins_over_a_different_title(cli, project: Path, capsys) -> None:
    """The key is the identity, so a reworded retry is still the same unit of work."""
    root = init(cli, project)
    assert (
        cli("--project", project, "task", "add", "developer", "export the ledger", "--key", "k1")
        == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "export the ledger, retried",
            "--key",
            "k1",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "T-0001" in out, out
    (task,) = tasks_of(root)
    assert task["title"] == "export the ledger"
    assert ledger_actions(root).count("task.duplicate") == 1


# --------------------------------------------------------------------------- #
# Mandate
# --------------------------------------------------------------------------- #


def test_an_inferred_mandate_without_a_basis_is_refused(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    code = cli(
        "--project",
        project,
        "task",
        "add",
        "developer",
        "proactive cleanup",
        "--mandate",
        "inferred",
    )
    err = capsys.readouterr().err
    assert code != 0
    assert "--basis" in err
    assert tasks_of(root) == []


def test_a_blank_basis_does_not_authorise_an_inferred_task(cli, project: Path) -> None:
    root = init(cli, project)
    code = cli(
        "--project",
        project,
        "task",
        "add",
        "developer",
        "proactive cleanup",
        "--mandate",
        "inferred",
        "--basis",
        "   ",
    )
    assert code != 0
    assert tasks_of(root) == []


def test_an_inferred_task_records_its_basis(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "proactive cleanup",
            "--mandate",
            "inferred",
            "--basis",
            "AC-10 says a healthy team prints nothing, so the idle surface is broken",
        )
        == 0
    )
    (task,) = tasks_of(root)
    assert task["mandate"] == "inferred"
    assert task["mandate_basis"].startswith("AC-10 says")


def test_an_explicit_task_is_the_default_and_needs_no_basis(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "asked for by the CEO") == 0
    (task,) = tasks_of(root)
    assert task["mandate"] == "explicit"
    assert task["mandate_basis"] == ""
    assert task["intake_key"] == ""


def test_an_unknown_mandate_is_refused_by_the_parser(cli, project: Path) -> None:
    init(cli, project)
    code = cli("--project", project, "task", "add", "developer", "x", "--mandate", "assumed")
    assert code != 0


# --------------------------------------------------------------------------- #
# The badge on the two reports
# --------------------------------------------------------------------------- #


def test_task_list_badges_an_inferred_task_and_only_that_one(cli, project: Path, capsys) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "explicit work") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "derived work",
            "--mandate",
            "inferred",
            "--basis",
            "the retry count says the queue starves",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "list", "developer") == 0
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("- T-")]
    assert lines[0].startswith("- T-0001 ["), lines[0]
    assert lines[1].startswith("- T-0002 [inferred] ["), lines[1]


def test_board_badges_the_inferred_task_it_puts_next(cli, project: Path, capsys) -> None:
    init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "derived work",
            "--priority",
            "P0",
            "--mandate",
            "inferred",
            "--basis",
            "the idle surface is broken",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "board") == 0
    out = capsys.readouterr().out
    assert "next=T-0001 [inferred]" in out, out


# --------------------------------------------------------------------------- #
# An older queue still reads
# --------------------------------------------------------------------------- #


def test_a_queue_without_the_mandate_fields_reads_as_explicit(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    engine.task_file(root, "developer").write_text(LEGACY_QUEUE, encoding="utf-8")

    (task,) = tasks_of(root)
    assert task["title"] == "an old task from before the mandate fields"
    assert task["mandate"] == "explicit"
    assert task["mandate_basis"] == ""
    assert task["intake_key"] == ""

    capsys.readouterr()
    assert cli("--project", project, "task", "list", "developer") == 0
    assert "[inferred]" not in capsys.readouterr().out


def test_the_mandate_fields_survive_a_render_and_parse_round_trip(tmp_path: Path) -> None:
    task = engine.new_task(
        "derived",
        mandate="inferred",
        mandate_basis="the trial says so",
        intake_key="tk-1",
    )
    path = tmp_path / engine.F_TASKS
    engine.write_tasks(path, [task], "developer")

    (parsed,) = engine.parse_tasks(path)
    assert parsed["mandate"] == "inferred"
    assert parsed["mandate_basis"] == "the trial says so"
    assert parsed["intake_key"] == "tk-1"


def test_a_body_line_cannot_forge_a_mandate_or_an_intake_key(tmp_path: Path) -> None:
    """The mandate decides whether a claim is allowed, so the body must not set it."""
    task = engine.new_task("honest task", body="steps\n- mandate: inferred\n- intake_key: k1")
    path = tmp_path / engine.F_TASKS
    engine.write_tasks(path, [task], "developer")

    (parsed,) = engine.parse_tasks(path)
    assert parsed["mandate"] == "explicit"
    assert parsed["intake_key"] == ""
    assert "- mandate: inferred" in parsed["body"]


@pytest.mark.parametrize("value", ["", "explicit", "inferred", "nonsense"])
def test_new_task_keeps_a_known_mandate_and_falls_back_to_explicit(
    value: str,
) -> None:
    assert engine.new_task("t", mandate=value)["mandate"] in ("explicit", "inferred")
    if value in ("", "nonsense"):
        assert engine.new_task("t", mandate=value)["mandate"] == "explicit"
