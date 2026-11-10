"""Unit tests for the task stage table.

The table is read top to bottom and the first matching row wins; a ``person``
stage means the task cannot continue without human input. Every test here builds
the record(s) a row is about and asserts the stage, so a row that stops being
reachable - or a reordering that silently changes a verdict - fails the suite.

Owner: developer. Layer: unit. Area: stage.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from teamwork import attention, engine

ROSTER = "ceo,developer-1,reviewer-1"

NOW = datetime.datetime(2026, 11, 1, 12, 0)

STAGE_ROWS = (
    "person/answer",
    "person/review",
    "person/blocked-failed",
    "working/queued",
    "person/review-lane",
    "idle",
    "working",
)


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def task(**fields) -> dict:
    """A stored task record with the fields a row reads set explicitly."""
    record = engine.new_task(fields.pop("title", "a task"))
    record["id"] = fields.pop("id", "T-0001")
    record.update(fields)
    return record


def stage(record: dict, **kwargs) -> str:
    return engine.stage_of(record, now=kwargs.pop("now", NOW), **kwargs)[0]


def test_person_answer_when_an_open_attention_item_names_the_task() -> None:
    record = task(status="doing")
    item = engine.new_attention("grant the push", kind="authorization", by="CEO", task="T-0001")

    assert stage(record, open_items=[item], deps_ready=True) == "person/answer"


def test_person_review_when_the_self_check_passed_and_review_is_pending() -> None:
    record = task(status="review", self_check="passed", review_status="pending")

    assert stage(record) == "person/review"


def test_person_blocked_failed_when_the_status_is_blocked() -> None:
    assert stage(task(status="blocked")) == "person/blocked-failed"


def test_person_blocked_failed_when_review_failed_three_times() -> None:
    assert stage(task(status="doing", review_fails=3)) == "person/blocked-failed"
    assert stage(task(status="doing", review_fails=2)) == "working"


def test_person_blocked_failed_when_a_review_claim_expired_past_its_lease() -> None:
    record = task(
        status="doing",
        review_claim="Reviewer-1",
        review_claim_ts=(NOW - datetime.timedelta(minutes=45)).isoformat(timespec="minutes"),
        review_claim_lease="20",
    )

    stage_of_record = engine.stage_of(record, now=NOW)

    assert stage_of_record[0] == "person/blocked-failed"
    assert "expired" in stage_of_record[1]


def test_a_live_review_claim_is_not_expired() -> None:
    record = task(
        status="doing",
        review_claim="Reviewer-1",
        review_claim_ts=(NOW - datetime.timedelta(minutes=19)).isoformat(timespec="minutes"),
        review_claim_lease="20",
    )

    assert stage(record) == "working"


def test_working_queued_when_a_todo_task_has_every_dependency_done() -> None:
    assert stage(task(status="todo", deps="T-0009"), deps_ready=True) == "working/queued"


def test_person_review_lane_when_a_submission_has_no_live_claim() -> None:
    """A record in review whose self-check is not recorded and that no lane holds."""
    record = task(status="review", self_check="pending", review_status="pending")

    assert stage(record) == "person/review-lane"


def test_idle_when_a_doing_task_was_not_updated_for_more_than_24h() -> None:
    assert stage(task(status="doing", updated="2026-10-31")) == "idle"
    assert stage(task(status="doing", updated="2026-11-01")) == "working"
    assert stage(task(status="doing", updated="2026-10-31T12:01")) == "working"
    assert engine.stage_of(task(status="doing", updated="2026-10-31T12:00"), now=NOW)[0] == "idle"


def test_working_for_everything_else() -> None:
    assert stage(task(status="doing", updated="2026-11-01")) == "working"
    record = task(status="todo", deps="T-0009", updated="2026-11-01")
    assert stage(record, deps_ready=False) == "working"


def test_the_table_is_read_top_to_bottom_and_the_first_row_wins() -> None:
    """A record that matches several rows is classified by the first one."""
    item = engine.new_attention("grant the push", kind="authorization", by="CEO", task="T-0001")
    record = task(status="blocked", self_check="passed", review_status="pending", review_fails=3)

    assert stage(record, open_items=[item]) == "person/answer"
    assert stage(record) == "person/review"

    record = task(status="blocked", review_status="pending", review_fails=3)
    assert stage(record) == "person/blocked-failed"


def test_every_row_of_the_table_is_reachable() -> None:
    item = engine.new_attention("grant the push", kind="authorization", by="CEO", task="T-0001")
    cases = {
        "person/answer": (dict(status="doing"), {"open_items": [item]}),
        "person/review": (dict(status="review", self_check="passed"), {}),
        "person/blocked-failed": (dict(status="blocked"), {}),
        "working/queued": (dict(status="todo"), {"deps_ready": True}),
        "person/review-lane": (dict(status="review", self_check="pending"), {}),
        "idle": (dict(status="doing", updated="2026-10-31"), {}),
        "working": (dict(status="doing", updated="2026-11-01"), {}),
    }

    assert tuple(cases) == STAGE_ROWS
    assert tuple(attention.STAGE_ROWS) == STAGE_ROWS
    for row, (fields, kwargs) in cases.items():
        assert stage(task(**fields), **kwargs) == row


def test_the_stage_never_depends_on_the_clock_beyond_the_idle_rule() -> None:
    record = task(status="review", self_check="passed")

    first = engine.stage_of(record, now=NOW)
    second = engine.stage_of(record, now=NOW + datetime.timedelta(days=40))

    assert first == second


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, True), (19, True), (21, False), (300, False)],
)
def test_claim_state_agrees_with_the_engine_rule(minutes: int, expected: bool) -> None:
    """Two implementations of the same lease must not drift apart."""
    record = task(
        review_claim="Reviewer-1",
        review_claim_ts=(datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat(
            timespec="minutes"
        ),
        review_claim_lease="20",
    )

    lane, _age, live = attention.claim_state(record)
    engine_lane, _engine_age, engine_live = engine.review_claim_state(record)

    assert (lane, live) == (engine_lane, engine_live)
    assert live is expected


def _write_queue(root: Path, records: list) -> None:
    engine.write_tasks(root / "Roles" / "Developer" / engine.F_TASKS, records, "developer")


def test_stage_command_prints_one_line_per_in_flight_task_in_person_first_order(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project)
    engine.write_attention(
        engine.attention_path(root),
        [engine.new_attention("grant the push", kind="authorization", by="CEO", task="T-0001")],
    )
    _write_queue(
        root,
        [
            task(id="T-0001", title="needs a person", status="doing", updated="2026-11-01"),
            task(id="T-0002", title="waiting", status="todo", updated="2026-11-01"),
            task(id="T-0003", title="closed", status="done", updated="2026-11-01"),
            task(id="T-0004", title="dropped", status="dropped", updated="2026-11-01"),
        ],
    )
    capsys.readouterr()

    assert cli("--project", project, "stage", "--now", "2026-11-01T12:00") == 0
    lines = capsys.readouterr().out.strip().splitlines()

    assert lines == [
        "T-0001 developer person/answer - open attention A-0001 (authorization) names it",
        "T-0002 developer working/queued - todo, every dependency done",
    ]


def test_stage_command_is_repeatable_and_writes_nothing(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    _write_queue(root, [task(id="T-0001", status="doing", updated="2026-10-01")])
    queue = root / "Roles" / "Developer" / engine.F_TASKS
    before = queue.read_bytes()
    capsys.readouterr()

    cli("--project", project, "stage", "--now", "2026-11-01T12:00")
    first = capsys.readouterr().out
    cli("--project", project, "stage", "--now", "2026-11-01T12:00")
    second = capsys.readouterr().out

    assert first == second
    assert "T-0001 developer idle - doing, updated 2026-10-01" in first
    assert queue.read_bytes() == before
    assert not engine.attention_path(root).exists()


def test_stage_command_refuses_an_unreadable_now(cli, project: Path) -> None:
    init(cli, project)

    assert cli("--project", project, "stage", "--now", "yesterday") != 0
