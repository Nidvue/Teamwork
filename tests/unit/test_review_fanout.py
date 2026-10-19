"""Why these tests exist: the docs promise several Reviewer lanes reviewing at
once, but the pulse handed every deliverable to the first idle lane and nothing
recorded which lane had taken which deliverable, so reviews serialised and lanes
collided on the same work (reproduced at 479742d before the fix).

Pinned here: the pulse fans unclaimed deliverables out one per lane, a claim
pins its deliverable to that lane until the lease expires, the lane count is the
real concurrency limit, and neither a verdict nor a release leaves a phantom
holder on the board.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from teamwork import engine

# Two Reviewer lanes minimum: with a single lane the fan-out this file pins is inert.
ROSTER = "ceo,developer-1,reviewer-1,reviewer-2,reviewer-3"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def submit(cli, project: Path, root: Path, title: str, author: str = "Developer-1") -> str:
    """Hand the Reviewers a deliverable its author has already self-checked."""
    assert cli("--project", project, "task", "add", "developer", title) == 0
    path = engine.task_file(root, "developer")
    handle = [t for t in engine.parse_tasks(path) if t["title"] == title][-1]["id"]
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            handle,
            "--by",
            author,
            "--note",
            "re-read the diff",
            "--test",
            "pytest -q @abc123 -> 9 passed",
        )
        == 0
    )
    tasks = engine.parse_tasks(path)
    [t for t in tasks if t["id"] == handle][0]["status"] = "review"
    engine.write_tasks(path, tasks, "developer")
    return handle


def age_claim(root: Path, handle: str, minutes: int, role: str = "developer") -> None:
    """Push a claim's stamp back past the lease, as if its lane died mid-review."""
    path = engine.task_file(root, role)
    tasks = engine.parse_tasks(path)
    t = [x for x in tasks if x["id"] == handle][0]
    stale = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    t["review_claim_ts"] = stale.isoformat(timespec="minutes")
    engine.write_tasks(path, tasks, role)


def claim_of(root: Path, handle: str, role: str = "developer") -> tuple:
    """What the queue really records about a deliverable's review claim."""
    tasks = engine.parse_tasks(engine.task_file(root, role))
    t = [x for x in tasks if x["id"] == handle][0]
    return t.get("review_claim", ""), t.get("review_claim_ts", "")


def review_rows(out: str) -> list:
    """Dispatch-plan rows that aim a Reviewer lane at a deliverable."""
    return [line for line in out.splitlines() if " <- " in line and "[reviewer]" in line]


def section(out: str, name: str) -> str:
    """One ``## name`` section of a pulse report."""
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {name}"))
    body = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def task_text(root: Path, role: str = "developer") -> str:
    return engine.task_file(root, role).read_text(encoding="utf-8")


def ledger_text(root: Path) -> str:
    return engine.ledger_path(root).read_text(encoding="utf-8")


@pytest.fixture
def lanes(cli, project: Path) -> tuple:
    """A team with three Reviewer lanes and one developer who ships work."""
    return cli, project, init(cli, project)


def test_the_pulse_fans_unclaimed_deliverables_out_one_per_lane(lanes, capsys) -> None:
    """The defect: three deliverables and three lanes, and one lane took them all."""
    cli, project, root = lanes
    for title in ("build the exporter", "build the importer", "build the summariser"):
        submit(cli, project, root, title)

    assert cli("--project", project, "pulse", "--commit") == 0
    rows = review_rows(capsys.readouterr().out)
    assert len(rows) == 3, rows
    assert "Reviewer-1" in rows[0] and "developer/T-0001" in rows[0], rows
    assert "Reviewer-2" in rows[1] and "developer/T-0002" in rows[1], rows
    assert "Reviewer-3" in rows[2] and "developer/T-0003" in rows[2], rows
    assert claim_of(root, "T-0001")[0] == "Reviewer-1"
    assert claim_of(root, "T-0002")[0] == "Reviewer-2"
    assert claim_of(root, "T-0003")[0] == "Reviewer-3"
    assert "review.claim" in ledger_text(root)
    busy = engine.busy_instances(root)
    assert {"Reviewer-1", "Reviewer-2", "Reviewer-3"} <= busy, busy


def test_a_held_deliverable_is_left_alone_while_a_free_lane_takes_the_next(lanes, capsys) -> None:
    cli, project, root = lanes
    submit(cli, project, root, "build the exporter")
    submit(cli, project, root, "build the importer")
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-1")
        == 0
    )

    assert cli("--project", project, "pulse") == 0
    out = capsys.readouterr().out
    rows = review_rows(out)
    assert len(rows) == 1, out
    assert "Reviewer-2" in rows[0] and "developer/T-0002" in rows[0], rows
    assert "Reviewer-1" not in section(out, "idle lanes"), out
    assert "held by Reviewer-1" in section(out, "deliverables awaiting review"), out
    assert "no Reviewer lane" not in out, out


def test_the_pulse_stops_dispatching_reviews_when_every_lane_is_holding_one(lanes, capsys) -> None:
    """The lane count, not the queue depth, is the review concurrency."""
    cli, project, root = lanes
    for title in ("build the exporter", "build the importer", "build the summariser"):
        submit(cli, project, root, title)
    assert cli("--project", project, "pulse", "--commit") == 0
    capsys.readouterr()

    handle = submit(cli, project, root, "build the dashboard")
    assert cli("--project", project, "pulse") == 3
    out = capsys.readouterr().out
    assert review_rows(out) == [], out
    assert f"{handle} [P2/review] build the dashboard  unclaimed" in out, out
    assert "no Reviewer lane is idle" in out, out
    assert "developer/T-0001=Reviewer-1" in out, out

    # a stalled lane stops pinning its deliverable once the lease runs out
    age_claim(root, "T-0001", engine.SLOT_TTL_MINUTES + 1)
    assert cli("--project", project, "pulse") == 0
    out = capsys.readouterr().out
    assert "claim by Reviewer-1 expired" in out and "take it over" in out, out


def test_the_queue_names_every_lane_and_the_holder_of_each_deliverable(lanes, capsys) -> None:
    cli, project, root = lanes
    handle = submit(cli, project, root, "build the exporter")

    assert cli("--project", project, "review", "--queue") == 0
    idle = capsys.readouterr().out
    for lane in ("Reviewer-1", "Reviewer-2", "Reviewer-3"):
        assert lane in idle, idle
    assert "--claim" in idle and "--release" in idle, idle
    assert "claim: unclaimed" in idle, idle

    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "Reviewer-2")
        == 0
    )
    assert cli("--project", project, "review", "--queue") == 0
    held = capsys.readouterr().out
    row = [line for line in held.splitlines() if f" {handle} [" in line]
    assert row and "held by Reviewer-2" in row[0], held
    assert "Reviewer-2 (holds T-0001)" in held, held


def test_a_claim_blocks_another_lane_until_the_lease_expires(lanes, capsys) -> None:
    cli, project, root = lanes
    submit(cli, project, root, "build the exporter")

    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-1")
        == 0
    )
    assert claim_of(root, "T-0001")[0] == "Reviewer-1"
    assert "review.claim" in ledger_text(root)

    capsys.readouterr()
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-2")
        == 2
    )
    err = capsys.readouterr().err
    assert "held by Reviewer-1" in err and "lease" in err, err

    age_claim(root, "T-0001", engine.SLOT_TTL_MINUTES + 1)
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-3")
        == 0
    )
    assert claim_of(root, "T-0001")[0] == "Reviewer-3"
    assert "took over Reviewer-1" in ledger_text(root)


def test_only_a_reviewer_lane_may_claim_and_it_must_name_the_deliverable(lanes, capsys) -> None:
    cli, project, root = lanes
    submit(cli, project, root, "build the exporter")

    capsys.readouterr()
    assert cli("--project", project, "review", "developer", "--claim", "--by", "Reviewer-1") == 2
    assert "usage" in capsys.readouterr().err.lower()

    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--claim",
            "--release",
            "--by",
            "Reviewer-1",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "mutually exclusive" in err, err

    capsys.readouterr()
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Developer-1")
        == 2
    )
    assert "only the reviewer role" in capsys.readouterr().err.lower()

    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-1")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "Reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest -q @abc123 -> 9 passed",
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-2")
        == 2
    )
    assert "already passed" in capsys.readouterr().err


def test_release_returns_the_work_and_only_the_holder_may_hand_it_back(lanes, capsys) -> None:
    cli, project, root = lanes
    submit(cli, project, root, "build the exporter")
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-1")
        == 0
    )

    capsys.readouterr()
    assert (
        cli(
            "--project", project, "review", "developer", "T-0001", "--release", "--by", "Reviewer-2"
        )
        == 2
    )
    assert "held by Reviewer-1" in capsys.readouterr().err

    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--release",
            "--by",
            "Reviewer-2",
            "--force",
            "",
        )
        == 2
    )
    err = capsys.readouterr().err
    # an empty --force is not an override: same refusal, and it names the remedy
    assert "only that lane releases it" in err and "--force <reason>" in err, err

    assert (
        cli(
            "--project", project, "review", "developer", "T-0001", "--release", "--by", "Reviewer-1"
        )
        == 0
    )
    assert claim_of(root, "T-0001")[0] == ""
    assert "review.release" in ledger_text(root)

    assert cli("--project", project, "pulse") == 0
    out = capsys.readouterr().out
    assert "developer/T-0001 [P2/review] build the exporter  unclaimed" in out, out

    # a live lane may pull a deliverable off a lane that stopped answering
    assert (
        cli("--project", project, "review", "developer", "T-0001", "--claim", "--by", "Reviewer-1")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--release",
            "--by",
            "Reviewer-2",
            "--force",
            "Reviewer-1 stopped answering mid-review",
        )
        == 0
    )
    assert "Reviewer-1 stopped answering mid-review" in ledger_text(root)


def test_a_verdict_clears_the_claim_so_the_lane_is_free_for_the_next(lanes, capsys) -> None:
    cli, project, root = lanes
    handle = submit(cli, project, root, "build the exporter")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "Reviewer-1")
        == 0
    )

    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            handle,
            "--by",
            "Reviewer-2",
            "--result",
            "fail",
            "--findings",
            "second opinion: the parser drops the tail",
        )
        == 0
    )
    note = capsys.readouterr().out
    assert "held by Reviewer-1" in note, note
    assert claim_of(root, handle) == ("", ""), task_text(root)

    handle2 = submit(cli, project, root, "build the importer")
    assert (
        cli("--project", project, "review", "developer", handle2, "--claim", "--by", "Reviewer-1")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            handle2,
            "--by",
            "Reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest -q @abc123 -> 9 passed",
        )
        == 0
    )
    assert "- status: done" in task_text(root)
    assert claim_of(root, handle2) == ("", ""), task_text(root)
    assert "claim by Reviewer-1 released" in ledger_text(root)
    assert "Reviewer-1" not in engine.busy_instances(root)


def test_init_warns_when_only_one_reviewer_lane_exists(cli, project: Path, capsys) -> None:
    capsys.readouterr()
    assert (
        cli("--project", project, "init", "--agents", "ceo,architect,reviewer-1", "--no-git") == 0
    )
    out = capsys.readouterr().out
    assert "WARNING one Reviewer instance" in out, out
    assert "reviewer-2" in out, out


def test_two_reviewer_lanes_start_without_the_single_lane_warning(
    cli, project: Path, capsys
) -> None:
    """The warning is about having one lane, not about Reviewers existing."""
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "init",
            "--agents",
            "ceo,architect,reviewer-1,reviewer-2",
            "--no-git",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Reviewer instance" not in out, out
