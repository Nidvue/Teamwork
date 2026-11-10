"""`teamwork.py status`: the compact live state of every instance.

Why these tests exist: the operator panel and the pi extension render whatever
this command prints, so an instance missing from the panel is an instance the
operator cannot see. What must hold: every instance appears exactly once; an
instance with a live lane record reads busy with its task, its elapsed seconds
and the fraction of its time budget it has used; an instance with neither a lane
nor a claim reads idle with no task and no invented elapsed time; a claim with no
lane record is busy but says so; `--agent` narrows to one instance and an unknown
name is a usage error; `--json` carries the same data as the text form; an
instance-free team reports zero rows instead of failing.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from teamwork import engine, lanes

ROSTER = "ceo,developer-1,developer-2,tester-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def build(cli, project: Path, *, lane: bool = True) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    assert cli("--project", project, "task", "add", "developer", "produce the contract") == 0
    task_file = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(task_file)
    tasks[0]["status"] = "doing"
    tasks[0]["claimed_by"] = "Developer-1"
    engine.write_tasks(task_file, tasks, "developer")
    if lane:
        lanes.lanes_dir(root).mkdir(parents=True, exist_ok=True)
        lanes.write_run(
            root,
            {
                "id": "L-0001",
                "agent": "Developer-1",
                "state": lanes.RUNNING,
                "role": "developer",
                "task": tasks[0]["id"],
                "attempt": 1,
                "attempts": 2,
                "minutes": 20,
                "pid": os.getpid(),
                "created": time.time() - 300,
                "deadline": time.time() + 900,
                "log": str(lanes.log_path(root, "Developer-1", "L-0001")),
                "provider": "default",
            },
        )
    return root


def payload(cli, project: Path, capsys, *flags) -> dict:
    capsys.readouterr()
    assert cli("--project", project, "status", "--json", *flags) == 0
    return json.loads(capsys.readouterr().out)


def test_every_instance_appears_exactly_once(cli, project: Path, capsys) -> None:
    build(cli, project)
    data = payload(cli, project, capsys)
    names = [row["instance"] for row in data["instances"]]
    assert names == ["CEO", "Developer-1", "Developer-2", "Tester-1"]
    assert data["count"] == len(names) == 4
    for row in data["instances"]:
        assert set(row) == {
            "instance",
            "role",
            "state",
            "task",
            "elapsed",
            "elapsed_text",
            "progress",
            "lane",
            "lane_state",
        }


def test_a_live_lane_reads_busy_with_task_elapsed_and_budget_progress(
    cli, project: Path, capsys
) -> None:
    root = build(cli, project)
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]["id"]
    rows = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}
    row = rows["Developer-1"]
    assert row["state"] == "busy"
    assert row["role"] == "developer"
    assert row["task"] == task
    assert row["lane"] == "L-0001"
    assert row["lane_state"] == lanes.RUNNING
    assert 300 <= row["elapsed"] < 3600
    assert row["progress"] == "attempt 1/2, 25% of 20m"
    assert row["elapsed_text"].endswith("s")


def test_an_instance_with_no_lane_and_no_claim_reads_idle(cli, project: Path, capsys) -> None:
    build(cli, project)
    rows = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}
    for name in ("Developer-2", "Tester-1", "CEO"):
        row = rows[name]
        assert row["state"] == "idle"
        assert row["task"] == ""
        assert row["elapsed"] is None
        assert row["elapsed_text"] == "-"
        assert row["progress"] == "idle"


def test_a_claim_with_no_lane_record_is_busy_and_says_so(cli, project: Path, capsys) -> None:
    build(cli, project, lane=False)
    row = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}[
        "Developer-1"
    ]
    assert row["state"] == "busy"
    assert row["task"].startswith("T-")
    assert row["elapsed"] is None
    assert row["progress"] == "claimed, no lane record"


def test_agent_narrows_to_one_row_and_an_unknown_name_is_a_usage_error(
    cli, project: Path, capsys
) -> None:
    build(cli, project)
    data = payload(cli, project, capsys, "--agent", "developer-2")
    assert [row["instance"] for row in data["instances"]] == ["Developer-2"]
    assert cli("--project", project, "status", "--agent", "reviewer-9") == 2


def test_an_instance_free_team_reports_zero_rows(cli, project: Path, capsys) -> None:
    root = build(cli, project)
    for instance in (root / "Agents").iterdir():
        shutil.rmtree(instance)
    assert engine.status_rows(root) == []
    data = payload(cli, project, capsys)
    assert data["count"] == 0 and data["instances"] == []
    assert cli("--project", project, "status") == 3
    assert "no instance" in capsys.readouterr().out


def test_the_text_form_prints_one_line_per_instance(cli, project: Path, capsys) -> None:
    build(cli, project)
    assert cli("--project", project, "status") == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("- ")]
    assert len(lines) == 4
    assert any("Developer-1" in line and "busy" in line for line in lines)
    assert any("Developer-2" in line and "idle" in line for line in lines)
