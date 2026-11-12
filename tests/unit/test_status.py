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
            "title",
            "elapsed",
            "elapsed_text",
            "progress",
            "progress_pct",
            "lane",
            "lane_state",
            "model",
            "provider",
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


def test_the_payload_names_its_schema_and_counts(cli, project: Path, capsys) -> None:
    build(cli, project)
    assert cli("--project", project, "task", "add", "developer", "a second ready job") == 0
    data = payload(cli, project, capsys)
    assert data["schema"] == 2
    assert data["counts"] == {"busy": 1, "idle": 3, "ready": 1, "review": 0, "lanes": 1}


def test_each_row_names_the_work_its_task_is(cli, project: Path, capsys) -> None:
    build(cli, project)
    rows = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}
    assert rows["Developer-1"]["title"] == "produce the contract"
    assert rows["Developer-2"]["title"] == ""
    assert cli("--project", project, "status") == 0
    line = next(
        line
        for line in capsys.readouterr().out.splitlines()
        if "Developer-1" in line and not line.startswith("- L-")
    )
    assert "produce the contract" in line


def test_progress_pct_is_an_int_with_a_lane_and_null_without_one(
    cli, project: Path, capsys
) -> None:
    build(cli, project)
    rows = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}
    assert rows["Developer-1"]["progress_pct"] == 25
    assert rows["Developer-2"]["progress_pct"] is None
    root = build(cli, project)
    for path in lanes.lanes_dir(root).glob("*.json"):
        path.unlink()
    row = {row["instance"]: row for row in payload(cli, project, capsys)["instances"]}[
        "Developer-1"
    ]
    assert row["progress_pct"] is None


def test_a_lane_row_names_its_state_model_and_attempt(cli, project: Path, capsys) -> None:
    root = build(cli, project)
    engine.save_model_config(
        root,
        {
            "roles": {"developer": {"model": "dev-model", "provider": "dev-provider"}},
            "agents": {"Tester-1": {"model": "tester-model", "provider": "tester-provider"}},
        },
    )
    data = payload(cli, project, capsys)
    assert [lane["id"] for lane in data["lanes"]] == ["L-0001"]
    lane = data["lanes"][0]
    assert set(lane) == {
        "id",
        "instance",
        "role",
        "task",
        "state",
        "elapsed_text",
        "model",
        "provider",
        "attempt",
    }
    assert lane["instance"] == "Developer-1"
    assert lane["role"] == "developer"
    assert lane["state"] == lanes.RUNNING
    assert lane["attempt"] == "1/2"
    assert lane["task"].startswith("T-")
    assert (lane["model"], lane["provider"]) == ("dev-model", "dev-provider")
    assert lane["elapsed_text"].endswith("s")
    rows = {row["instance"]: row for row in data["instances"]}
    assert rows["Developer-1"]["model"] == "dev-model"
    assert rows["Tester-1"]["model"] == "tester-model", "the agent entry wins over the role"
    assert (rows["CEO"]["model"], rows["CEO"]["provider"]) == ("", ""), "unset reads empty"


def test_a_review_lane_names_no_task_and_a_newer_lane_leads(cli, project: Path, capsys) -> None:
    root = build(cli, project)
    now = time.time()
    lanes.write_run(
        root,
        {
            "id": "L-0002",
            "agent": "Tester-1",
            "role": "tester",
            "state": lanes.EXITED,
            "review_owner": "Reviewer-1",
            "task": "T-0099",
            "attempt": 1,
            "attempts": 2,
            "minutes": 20,
            "created": now - 60,
        },
    )
    data = payload(cli, project, capsys)
    assert [lane["id"] for lane in data["lanes"]] == ["L-0001", "L-0002"], "live lane first"
    assert data["lanes"][1]["task"] == "", "a review lane is not a task lane"
    assert data["counts"]["lanes"] == 2


def test_lanes_are_newest_first_and_bounded_to_six(cli, project: Path, capsys) -> None:
    root = build(cli, project)
    now = time.time()
    for index in range(7):
        lanes.write_run(
            root,
            {
                "id": f"L-01{index:02d}",
                "agent": "Developer-2",
                "role": "developer",
                "state": lanes.EXITED,
                "task": f"T-02{index:02d}",
                "attempt": 1,
                "attempts": 2,
                "minutes": 20,
                "created": now - 600 - index,
            },
        )
    data = payload(cli, project, capsys)
    ids = [lane["id"] for lane in data["lanes"]]
    assert ids[0] == "L-0001", "the live lane leads even though it is the oldest"
    assert ids[1:4] == ["L-0100", "L-0101", "L-0102"], "then the newest by created"
    assert len(ids) == 6 and data["counts"]["lanes"] == 6
    assert ids == [lane["id"] for lane in payload(cli, project, capsys)["lanes"]], "stable"


def test_the_panel_prints_the_lane_block_before_the_instance_rows(
    cli, project: Path, capsys
) -> None:
    root = build(cli, project)
    engine.save_model_config(
        root, {"roles": {"developer": {"model": "m", "provider": "p"}}, "agents": {}}
    )
    capsys.readouterr()
    assert cli("--project", project, "status") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("# Status (4 instance(s), 1 busy)")
    assert lines[1] == "# Lanes (1)"
    assert lines[2].startswith("- L-0001  Developer-1      running   T-"), lines[2]
    assert lines[2].endswith(" p/m"), lines[2]
    assert lines[3].startswith("- CEO"), "the instance rows follow the lane block"


def test_a_team_with_no_lane_prints_no_lane_block(cli, project: Path, capsys) -> None:
    build(cli, project, lane=False)
    data = payload(cli, project, capsys)
    assert data["lanes"] == [] and data["counts"]["lanes"] == 0
    assert cli("--project", project, "status") == 0
    assert "# Lanes" not in capsys.readouterr().out


def test_a_long_title_is_truncated_and_every_line_stays_within_110_columns(
    cli, project: Path, capsys
) -> None:
    root = build(cli, project)
    task_file = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(task_file)
    tasks[0]["title"] = "x" * 60
    engine.write_tasks(task_file, tasks, "developer")
    assert cli("--project", project, "status") == 0
    lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("- ") and not line.startswith("- L-")
    ]
    assert all(len(line) <= 110 for line in lines)
    assert any("x" * 40 in line and "x" * 41 not in line for line in lines)


def test_the_text_form_prints_one_line_per_instance(cli, project: Path, capsys) -> None:
    build(cli, project)
    assert cli("--project", project, "status") == 0
    lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("- ") and not line.startswith("- L-")
    ]
    assert len(lines) == 4
    assert any("Developer-1" in line and "busy" in line for line in lines)
    assert any("Developer-2" in line and "idle" in line for line in lines)
