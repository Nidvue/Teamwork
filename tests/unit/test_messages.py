"""The agent-to-agent mailbox: priority order, one taker, preemption, resume.

Why these tests exist: two agents could only coordinate through the board, so a
request either became a task (losing "do this before that") or sat in prose nobody
reads. The mailbox adds four properties that must not regress:

* a message is delivered in **priority order**, urgent before low, oldest first
  inside one priority - not arrival order;
* one message is taken by **one** lane, so a second lane of the same role does not
  do the work twice;
* an ``urgent`` message **preempts**: the supervisor stops the recipient's lane,
  the task it was working on becomes ``paused`` with the message id, and
  ``lane resume`` puts it back at ``doing``;
* an idle recipient with urgent mail gets a lane even when the board is empty.

The preemption tests use a real child process and the fake launcher the lane suite
already uses, so the stop, the pause and the resume run against the real runtime.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from teamwork import engine, lanes, messages

ROSTER = "ceo,developer-1,developer-2,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def launcher(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str) -> None:
    script = tmp_path / "fake_lane.py"
    script.write_text("import time\n" + body, encoding="utf-8")
    template = " ".join([shlex.quote(sys.executable), shlex.quote(str(script))])
    monkeypatch.setenv("TEAMWORK_LANE_CMD", template)
    monkeypatch.setenv("TEAMWORK_LANE_POLL", "0.05")


def add_task(cli, project: Path, title: str, *flags: str) -> None:
    assert cli("--project", project, "task", "add", "developer", title, *flags) == 0


def task_status(root: Path, handle: str = "T-0001") -> str:
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    return tasks[engine.find_task(tasks, handle)]["status"]


def test_messages_come_back_in_priority_order_then_oldest_first(cli, project: Path) -> None:
    root = init(cli, project)
    for priority, subject in (
        ("low", "low one"),
        ("urgent", "urgent one"),
        ("normal", "normal one"),
        ("high", "high one"),
        ("high", "high two"),
    ):
        messages.send(
            root, sender="CEO", recipient="Developer-1", subject=subject, priority=priority
        )
    order = [(m["priority"], m["subject"]) for m in messages.inbox(root, "Developer-1")]
    assert order == [
        ("urgent", "urgent one"),
        ("high", "high one"),
        ("high", "high two"),
        ("normal", "normal one"),
        ("low", "low one"),
    ]
    assert messages.counts(root, "Developer-1") == {
        "urgent": 1,
        "high": 2,
        "normal": 1,
        "low": 1,
        "pending": 5,
    }


def test_one_message_is_taken_by_one_lane_and_closed_once(cli, project: Path) -> None:
    root = init(cli, project)
    record = messages.send(root, sender="CEO", recipient="Developer-1", subject="do a thing")
    messages.take(root, "Developer-1", record["id"], "Developer-1")
    with pytest.raises(ValueError):
        messages.take(root, "Developer-1", record["id"], "Developer-2")
    closed = messages.finish(root, "Developer-1", record["id"], "Developer-1", "done it @abc123")
    assert closed["state"] == "done"
    assert messages.inbox(root, "Developer-1") == []
    with pytest.raises(ValueError):
        messages.take(root, "Developer-1", record["id"], "Developer-1")


def test_a_message_needs_a_subject_and_a_known_priority(cli, project: Path) -> None:
    root = init(cli, project)
    with pytest.raises(ValueError):
        messages.send(root, sender="CEO", recipient="Developer-1", subject="   ")
    with pytest.raises(ValueError):
        messages.send(root, sender="CEO", recipient="Developer-1", subject="x", priority="whenever")


def test_ids_are_per_mailbox_and_never_reused(cli, project: Path) -> None:
    root = init(cli, project)
    first = messages.send(root, sender="CEO", recipient="Developer-1", subject="a")
    second = messages.send(root, sender="CEO", recipient="Developer-1", subject="b")
    other = messages.send(root, sender="CEO", recipient="Developer-2", subject="c")
    assert (first["id"], second["id"], other["id"]) == ("M-0001", "M-0002", "M-0001")


def test_the_packet_block_names_priority_and_the_urgent_instruction(cli, project: Path) -> None:
    root = init(cli, project)
    assert messages.packet_lines(root, "Developer-1") == []
    messages.send(root, sender="CEO", recipient="Developer-1", subject="later", priority="low")
    messages.send(
        root,
        sender="Reviewer-1",
        recipient="Developer-1",
        subject="stop and fix the guard",
        priority="urgent",
        task="T-0001",
    )
    block = messages.packet_lines(root, "Developer-1")
    assert block[0].startswith("## Messages for you (2 pending")
    assert block[1].startswith("- M-0002 [urgent] from Reviewer-1: stop and fix the guard")
    assert "(task T-0001)" in block[1]
    assert block[2].startswith("- M-0001 [low]")
    assert any("Process every **urgent** message first" in line for line in block)


def test_an_urgent_message_preempts_the_lane_and_pauses_the_task(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    add_task(cli, project, "ship it", "--priority", "P0")
    launcher(monkeypatch, tmp_path, "time.sleep(30)\n")
    assert (
        cli("--project", project, "lane", "start", "--agent", "developer-1", "--task", "T-0001")
        == 0
    )
    assert task_status(root) == "doing"
    message = messages.send(
        root,
        sender="Reviewer-1",
        recipient="Developer-1",
        subject="the guard test cannot fail",
        priority="urgent",
        task="T-0001",
    )

    freed = lanes.preempt_urgent(root, "ceo")

    assert freed == ["Developer-1"]
    run = lanes.load_runs(root)[0]
    assert run["state"] == lanes.STOPPED
    assert run["preempted_by"] == message["id"]
    assert task_status(root) == "paused"
    assert not lanes.live_runs(root)


def test_lane_resume_puts_the_paused_task_back_on_the_queue(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "ship it", "--priority", "P0")
    engine.set_task_status(root, "T-0001", "paused", note="paused for M-0001", by="ceo")
    assert task_status(root) == "paused"
    assert cli("--project", project, "lane", "resume", "T-0001", "--by", "ceo") == 0
    assert task_status(root) == "doing"


def test_the_cli_round_trip_send_inbox_take_done(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "message",
            "send",
            "--from",
            "CEO",
            "--to",
            "Developer-1",
            "--priority",
            "high",
            "--subject",
            "rebase before resubmitting",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "message", "inbox", "--for", "Developer-1") == 0
    listed = capsys.readouterr().out
    assert "M-0001 [high] pending from CEO: rebase before resubmitting" in listed
    assert (
        cli(
            "--project",
            project,
            "message",
            "take",
            "M-0001",
            "--for",
            "Developer-1",
            "--by",
            "Developer-1",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "message",
            "done",
            "M-0001",
            "--for",
            "Developer-1",
            "--by",
            "Developer-1",
            "--result",
            "rebased @abc123",
        )
        == 0
    )
    assert messages.inbox(root, "Developer-1") == []
    closed = messages.inbox(root, "Developer-1", states=("done",))
    assert closed[0]["result"] == "rebased @abc123"


def test_the_cli_refuses_an_unknown_recipient(cli, project: Path, capsys) -> None:
    init(cli, project)
    code = cli(
        "--project",
        project,
        "message",
        "send",
        "--from",
        "CEO",
        "--to",
        "Ghost-1",
        "--subject",
        "hello",
    )
    assert code == 2
    assert "no instance 'Ghost-1'" in capsys.readouterr().out


def test_a_closed_message_cannot_be_reopened_by_done(cli, project: Path) -> None:
    root = init(cli, project)
    record = messages.send(root, sender="CEO", recipient="Developer-1", subject="one")
    messages.take(root, "Developer-1", record["id"], "Developer-1")
    messages.finish(root, "Developer-1", record["id"], "Developer-1", "dropped it", state="dropped")
    with pytest.raises(ValueError):
        messages.finish(root, "Developer-1", record["id"], "Developer-1", "done after all")


def test_a_paused_task_records_the_message_that_displaced_it(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "ship it", "--priority", "P0")
    engine.set_task_status(
        root,
        "T-0001",
        "paused",
        note="paused for M-0001 [urgent]: fix it",
        by="ceo",
        paused_by="M-0001",
    )
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert task["paused_by"] == "M-0001"
    assert "urgent" in task["paused_note"]
    rendered = (engine.task_file(root, "developer")).read_text(encoding="utf-8")
    assert "- paused_by: M-0001" in rendered
    assert "- paused_note: paused for M-0001 [urgent]: fix it" in rendered


def test_a_paused_task_is_in_flight_not_an_invalid_status(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    add_task(cli, project, "ship it", "--priority", "P0")
    engine.set_task_status(
        root, "T-0001", "paused", note="paused for M-0001", by="ceo", paused_by="M-0001"
    )
    capsys.readouterr()
    assert cli("--project", project, "loop") == 1
    report = capsys.readouterr().out
    assert "INVALID STATUS" not in report
    assert "unknown status" not in report
    assert "paused: 1" in report
    assert "1 task(s) not finished" in report
