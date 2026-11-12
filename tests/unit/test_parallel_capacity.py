"""Why these tests exist: the team serialised itself. One lane took one task, sat
in review, and every other lane idled - measured on a real run where 12 tasks were
open, one agent was working and nine lanes were waiting. Two changes fix the
mechanics: a lane may hold more than one unit of work (LANE_WIP), and a dependency
can release at *submit* time instead of waiting for the whole task to be `done`.

Pinned here: `task next --capacity N` claims N tasks at once, a second call does
not double-claim, `role:T-id@review` and `@started` unblock earlier than `done`,
and one pulse fills a lane up to its WIP limit instead of handing it one task.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def add(cli, project: Path, role: str, title: str, deps: str = "") -> None:
    args = ["--project", project, "task", "add", role, title]
    if deps:
        args += ["--deps", deps]
    assert cli(*args) == 0


def test_task_next_capacity_claims_several_at_once(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    for i in range(3):
        add(cli, project, "developer", f"unit {i}")

    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "3") == 0
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert [t["status"] for t in tasks] == ["doing", "doing", "doing"]
    assert {t["claimed_by"].lower() for t in tasks} == {"developer-1"}

    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "3") == 3


def test_dependency_can_release_at_review_or_started(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    add(cli, project, "developer", "produce the contract")
    add(cli, project, "tester", "test against it", "developer:T-0001@review")
    add(cli, project, "tester", "shadow the work", "developer:T-0001@started")

    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert [t["status"] for t in tester] == ["todo", "todo"]

    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert cli("--project", project, "task", "next", "tester-1", "--capacity", "2") == 0
    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert tester[1]["status"] == "doing" and tester[0]["status"] == "todo"

    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--note",
            "re-read the contract",
            "--test",
            "true @rev -> ok",
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "tester-1") == 0
    tester = engine.parse_tasks(engine.task_file(root, "tester"))
    assert tester[0]["status"] == "doing"


def test_pulse_fills_every_lane_up_to_its_wip_limit(cli, project: Path) -> None:
    """No single lane is the bottleneck: the roster grows, then the units spread.

    The old rule filled one lane to `LANE_WIP` and queued the rest behind it. The
    contract now: three units need two lanes (ceil(3 / LANE_WIP)), the pulse adds
    the missing instance, and every unit is claimed - no instance over its WIP.
    """
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    for i in range(3):
        add(cli, project, "developer", f"unit {i}")

    assert cli("--project", project, "pulse", "--commit") == 0
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    claimed = [t for t in tasks if t["status"] == "doing"]
    assert len(claimed) == 3, [t["status"] for t in tasks]
    per_lane: dict = {}
    for task in claimed:
        per_lane[task["claimed_by"]] = per_lane.get(task["claimed_by"], 0) + 1
    assert len(per_lane) == 2, per_lane
    assert max(per_lane.values()) <= engine.LANE_WIP, per_lane
    assert len(engine.instances_of(root, "developer")) == 2

    assert cli("--project", project, "pulse", "--commit") in (0, 3)
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert len([t for t in tasks if t["status"] == "doing"]) == 3, "no double claim"
    assert len(engine.instances_of(root, "developer")) == 2, "no idle scale-up"


def test_every_claim_leaves_a_ledger_record(cli, project: Path) -> None:
    """A lane that takes three units must leave three records, not one.

    Measured defect: `task next --capacity 3` moved three tasks to `doing` but
    wrote a single `task.claim`, so `trace T-0002` showed no record of the claim
    and the audit trail disagreed with the queue.
    """
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    for i in range(3):
        add(cli, project, "developer", f"unit {i}")
    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "3") == 0

    ledger = (root / engine.F_LEDGER).read_text(encoding="utf-8")
    claims = [line for line in ledger.splitlines() if '"task.claim"' in line]
    assert len(claims) == 3, claims


def test_peek_and_zero_capacity_do_not_mutate_or_claim(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    add(cli, project, "developer", "unit 0")
    add(cli, project, "developer", "unit 1")

    assert (
        cli("--project", project, "task", "next", "developer-1", "--peek", "--capacity", "2") == 0
    )
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert [t["status"] for t in tasks] == ["todo", "todo"]
    assert all(not t["claimed_by"] for t in tasks)

    assert cli("--project", project, "task", "next", "developer-1", "--capacity", "0") == 0
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert [t["status"] for t in tasks] == ["doing", "todo"]


def test_one_lane_needs_one_slot_for_its_whole_wip(cli, project: Path, capsys) -> None:
    """A lane needs one lease for both WIP units, not one per plan entry.

    The capacity maths counted plan entries, so one lane with two units looked
    like two lanes needing two slots: the second unit was deferred to a later
    wake and the lane never reached its WIP (T-0020/A5).
    """
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = team_root(project)
    settings_path = root / engine.F_SETTINGS
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    for provider in ("ollama-cloud", "deepseek", "openai", "anthropic", "default"):
        settings[provider] = 0
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    add(cli, project, "developer", "unit 0")
    add(cli, project, "developer", "unit 1")

    capsys.readouterr()
    assert cli("--project", project, "pulse", "--commit") == 3
    out = capsys.readouterr().out
    assert "# capacity: 1 lane(s) need a new slot, 0 free" in out, out
    assert "deferring 2 assignment(s)" in out, out
    assert all(
        t["status"] == "todo" for t in engine.parse_tasks(engine.task_file(root, "developer"))
    )

    settings["ollama-cloud"] = 1
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    capsys.readouterr()
    assert cli("--project", project, "pulse", "--commit") == 0
    out = capsys.readouterr().out
    assert "# capacity" not in out, out
    assert "deferred until a lease frees" not in out, out
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    assert [t["status"] for t in tasks] == ["doing", "doing"]
    assert {t["claimed_by"].lower() for t in tasks} == {"developer-1"}
