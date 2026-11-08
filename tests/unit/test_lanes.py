"""The engine's own lane runtime: spawn, supervise, wave, retry, review, stop.

Why these tests exist: the six host operations used to be borrowed from whichever
plugin the host shipped, so a host without that plugin had no parallelism. They are
now the engine's own: a detached child process, a JSON record under
``Runtime/Lanes/``, a packet under ``Agents/<Instance>/Runs/``, a provider lease,
and a supervisor that computes every wave from the board.

A fake launcher keeps the tests offline and deterministic: ``TEAMWORK_LANE_CMD``
is a template split without a shell, so the tests exercise the real spawn, the real
records, the real budgets and the real wave planner while the "agent" is three
lines of Python. What must never regress: a lane outlives the CLI call, its state
is read from an outcome file rather than guessed, a dead lane is reconciled and its
slot released, a lane that makes no progress is retried inside the budget and then
left to the CEO, and a review ready on the board becomes a Reviewer lane in the
next wave.
"""

from __future__ import annotations

import json
import shlex
import sys
import time
from pathlib import Path

import pytest

from teamwork import engine, lanes

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1,reviewer-2"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def fake_lane(tmp_path: Path, name: str = "fake_lane.py", body: str = "") -> Path:
    script = tmp_path / name
    script.write_text(
        "import sys, time\n" + (body or "print('LANE-RESULT: ok fake lane finished')\n"),
        encoding="utf-8",
    )
    return script


def launcher(monkeypatch: pytest.MonkeyPatch, script: Path, *args: str) -> None:
    template = " ".join([shlex.quote(sys.executable), shlex.quote(str(script)), *args])
    monkeypatch.setenv("TEAMWORK_LANE_CMD", template)
    monkeypatch.setenv("TEAMWORK_LANE_POLL", "0.05")


def add_task(cli, project: Path, role: str, title: str, *flags: str) -> None:
    assert cli("--project", project, "task", "add", role, title, *flags) == 0


def runs(root: Path) -> list:
    return lanes.load_runs(root)


def review_ready(root: Path) -> None:
    task_file = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(task_file)
    tasks[0]["status"] = "review"
    tasks[0]["self_check"] = "passed"
    tasks[0]["claimed_by"] = "Developer-1"
    engine.write_tasks(task_file, tasks, "developer")


def test_a_lane_outlives_the_cli_call_and_records_its_result(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "produce the contract")
    launcher(
        monkeypatch,
        fake_lane(
            tmp_path,
            body=(
                "import os\nprint('cwd', os.getcwd())\nprint('LANE-RESULT: ok landed at abc123')\n"
            ),
        ),
        "{packet}",
    )
    assert (
        cli("--project", project, "lane", "start", "--agent", "developer-1", "--task", "T-0001")
        == 0
    )
    assert cli("--project", project, "lane", "wait", "L-0001", "--timeout", "30") == 0

    run = runs(root)[0]
    assert run["id"] == "L-0001"
    assert run["state"] == lanes.EXITED
    assert run["result"] == {"verdict": "ok", "note": "landed at abc123"}
    assert run["task"] == "T-0001"
    log = Path(run["log"]).read_text(encoding="utf-8")
    assert str(project) in log, "the lane runs in the project, not in the team tree"
    assert "T-0001" in Path(run["packet"]).read_text(encoding="utf-8")


def test_the_packet_names_the_work_the_charter_the_budget_and_the_result_contract(
    cli, project: Path
) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "produce the contract")
    assert (
        cli(
            "--project",
            project,
            "lane",
            "start",
            "--agent",
            "developer-1",
            "--task",
            "T-0001",
            "--print",
        )
        == 0
    )
    packet = Path(lanes.packet_path(root, "Developer-1", "L-0001")).read_text(encoding="utf-8")
    assert "T-0001" in packet
    assert "Roles/Developer/Role.md" in packet
    assert "LANE-RESULT:" in packet
    assert "tw selfcheck developer T-0001" in packet
    assert "Never merge your own work" in packet
    assert "16 tool calls and 25 minutes" in packet
    assert "tw branch start --agent Developer-1 --task T-0001 --worktree" in packet
    assert "tw load Developer-1 --task T-0001" in packet
    assert "tw load Developer-1`" not in packet
    assert "## Memory pack for this assignment (injected)" in packet
    assert "# pack:" in packet


def test_a_reviewer_packet_carries_the_review_flow_not_the_produce_flow(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "produce the contract")
    review_ready(root)
    assert (
        cli(
            "--project",
            project,
            "lane",
            "start",
            "--agent",
            "reviewer-1",
            "--task",
            "T-0001",
            "--review-owner",
            "developer",
            "--print",
        )
        == 0
    )
    packet = Path(lanes.packet_path(root, "Reviewer-1", "L-0001")).read_text(encoding="utf-8")
    assert "tw review developer T-0001 --claim --by Reviewer-1" in packet
    assert "tw branch start" not in packet


def test_an_unknown_task_is_refused_before_anything_starts(cli, project: Path) -> None:
    init(cli, project)
    assert (
        cli("--project", project, "lane", "start", "--agent", "developer-1", "--task", "T-0404")
        == 2
    )


def test_an_unknown_agent_is_refused(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "lane", "start", "--agent", "developer-9", "--print") == 1


def test_no_launcher_for_the_host_names_the_escape_hatch(
    cli, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init(cli, project)
    monkeypatch.delenv("TEAMWORK_LANE_CMD", raising=False)
    monkeypatch.setenv("TEAMWORK_AGENT_HOST", "some-host-nobody-supports")
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 2


def test_the_launcher_template_is_split_without_a_shell_and_the_packet_is_an_argument(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    launcher(
        monkeypatch,
        fake_lane(tmp_path, body="import sys\nprint('ARGV', sys.argv[1:])\n"),
        "one {agent}",
        "{packet}",
        "{provider}",
    )
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 0
    assert cli("--project", project, "lane", "wait", "L-0001", "--timeout", "30") == 0
    log = Path(runs(root)[0]["log"]).read_text(encoding="utf-8")
    assert "'one', 'Developer-1'" in log, log
    assert "ollama-cloud" in log


def test_the_provider_cap_refuses_a_second_lane_and_leaves_it_queued(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    (root / engine.F_SETTINGS).write_text(json.dumps({"ollama-cloud": 1}), encoding="utf-8")
    launcher(monkeypatch, fake_lane(tmp_path, body="import time\ntime.sleep(30)\n"), "{packet}")
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 0
    assert cli("--project", project, "lane", "start", "--agent", "developer-2") == 3
    assert [run["agent"] for run in runs(root)] == ["Developer-1"]
    assert cli("--project", project, "lane", "stop", "L-0001") == 0
    assert runs(root)[0]["state"] == lanes.STOPPED


def test_a_lane_past_its_deadline_is_killed_by_the_supervisor(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    launcher(monkeypatch, fake_lane(tmp_path, body="import time\ntime.sleep(30)\n"), "{packet}")
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 0
    record = runs(root)[0]
    record["deadline"] = time.time() - 1
    lanes.write_run(root, record)
    assert cli("--project", project, "lane", "status", "L-0001") == 0
    time.sleep(0.2)
    assert runs(root)[0]["state"] == lanes.TIMEOUT
    assert not lanes.live_runs(root)


def test_a_lane_that_died_without_an_outcome_is_reconciled_and_its_slot_released(
    cli, project: Path
) -> None:
    root = init(cli, project)
    record = {
        "id": "L-0001",
        "agent": "Developer-1",
        "role": "developer",
        "task": "T-0001",
        "state": lanes.RUNNING,
        "pid": 999999,
        "provider": "ollama-cloud",
        "log": str(lanes.log_path(root, "Developer-1", "L-0001")),
    }
    lanes.write_run(root, record)
    lanes.acquire_slot(root, "Developer-1", "ollama-cloud", "T-0001")
    assert lanes.slot_holders(root, "ollama-cloud") == ["Developer-1"]

    assert cli("--project", project, "lane", "reap") == 0
    reaped = runs(root)[0]
    assert reaped["state"] == lanes.LOST
    assert lanes.slot_holders(root, "ollama-cloud") == []


def test_swarm_dry_run_names_the_next_wave_and_starts_nothing(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "first")
    add_task(cli, project, "developer", "second")
    assert cli("--project", project, "swarm", "run", "--dry-run") == 0
    assert runs(root) == []


def test_swarm_refuses_to_dispatch_when_the_accept_mode_is_not_auto(cli, project: Path) -> None:
    root = init(cli, project)
    (root / engine.F_SETTINGS).write_text(json.dumps({"PulseMode": "observe"}), encoding="utf-8")
    add_task(cli, project, "developer", "first")
    assert cli("--project", project, "swarm", "run") == 2
    assert runs(root) == []


def test_swarm_fans_two_ready_tasks_out_to_two_lanes_in_one_wave(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "first")
    add_task(cli, project, "developer", "second")
    launcher(monkeypatch, fake_lane(tmp_path), "{packet}")
    assert cli("--project", project, "swarm", "run", "--waves", "1", "--minutes", "2") == 0
    started = {run["agent"] for run in runs(root)}
    assert started == {"Developer-1", "Developer-2"}
    assert len({run["task"] for run in runs(root)}) == 2


def test_swarm_retries_unfinished_work_once_and_then_leaves_it_to_the_ceo(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "unfinished work")
    launcher(monkeypatch, fake_lane(tmp_path), "{packet}")
    assert cli("--project", project, "swarm", "run", "--waves", "4", "--minutes", "2") == 0
    attempts = [(run["attempt"], run["state"]) for run in lanes.load_runs(root)]
    assert attempts == [(1, lanes.EXITED), (2, lanes.EXITED)], attempts
    assert lanes.load_runs(root)[0]["retried"] is True
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert task["status"] == "doing", "an exhausted lane leaves the claim for the CEO"


def test_swarm_hands_a_ready_review_to_a_reviewer_lane(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "produce the contract")
    review_ready(root)
    launcher(
        monkeypatch, fake_lane(tmp_path, body="print('LANE-RESULT: ok reviewed')\n"), "{packet}"
    )
    assert cli("--project", project, "swarm", "run", "--waves", "1", "--minutes", "2") == 0
    run = lanes.load_runs(root)[0]
    assert (run["agent"], run["role"], run["review_owner"]) == (
        "Reviewer-1",
        "reviewer",
        "developer",
    )
    claimed = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert claimed.get("review_claim") == "Reviewer-1"


def test_a_held_review_claim_is_adopted_without_crashing_the_wave(
    cli, project: Path, capsys
) -> None:
    """A claim the engine records as a 4-tuple must not be unpacked as a pair.

    Regression for the reviewer's F-1 at 5475b8e: adopted_plan read
    engine.held_review_items as (owner, task) while it returns
    (owner_role, task, lane, age), so `swarm run --dry-run` raised
    "too many values to unpack (expected 2, got 4)" on any board holding a claim.
    """
    root = init(cli, project)
    add_task(cli, project, "developer", "produce the contract")
    review_ready(root)
    task_file = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(task_file)
    tasks[0]["review_claim"] = "Reviewer-2"
    tasks[0]["review_claim_ts"] = engine.claim_stamp()
    engine.write_tasks(task_file, tasks, "developer")
    held = engine.held_review_items(root)
    assert [(owner, task["id"], lane) for owner, task, lane, _age in held] == [
        ("developer", "T-0001", "Reviewer-2")
    ]
    adopted = lanes.adopted_plan(root)
    assert [(item.instance, item.task, item.review_owner) for item in adopted] == [
        ("Reviewer-2", "T-0001", "developer")
    ]
    assert lanes.measure(root, 8).adopted >= 1
    capsys.readouterr()
    assert cli("--project", project, "swarm", "run", "--dry-run") in (0, 3)
    assert "too many values" not in capsys.readouterr().out


def test_the_runner_records_a_timeout_instead_of_hanging(tmp_path: Path) -> None:
    from teamwork import lanerun

    run_path = tmp_path / "L-0001.json"
    run_path.write_text("{}", encoding="utf-8")
    code = lanerun.run(run_path, 0.2, [sys.executable, "-c", "import time; time.sleep(30)"])
    outcome = json.loads(lanerun.outcome_path(run_path).read_text(encoding="utf-8"))
    assert code == lanerun.TIMEOUT_EXIT
    assert outcome["state"] == "timeout"


def test_an_unwritable_launcher_records_its_failure(tmp_path: Path) -> None:
    from teamwork import lanerun

    run_path = tmp_path / "L-0001.json"
    run_path.write_text("{}", encoding="utf-8")
    code = lanerun.run(run_path, 5, [str(tmp_path / "not-a-binary")])
    outcome = json.loads(lanerun.outcome_path(run_path).read_text(encoding="utf-8"))
    assert code == lanerun.MISSING_BINARY_EXIT
    assert outcome["state"] == "failed"


def test_a_lane_that_cannot_start_releases_the_claim_it_took(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A claim with no process behind it looks like a busy lane forever."""
    root = init(cli, project)
    (root / engine.F_SETTINGS).write_text(json.dumps({"ollama-cloud": 1}), encoding="utf-8")
    launcher(monkeypatch, fake_lane(tmp_path, body="import time\ntime.sleep(30)\n"), "{packet}")
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 0
    add_task(cli, project, "developer", "queued behind the cap")
    assert (
        cli("--project", project, "lane", "start", "--agent", "developer-2", "--task", "T-0001")
        == 3
    )
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert (task["status"], task.get("claimed_by")) == ("todo", "")
    assert cli("--project", project, "lane", "stop", "L-0001") == 0


def test_one_lane_per_instance_is_refused_not_shared(
    cli, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    launcher(monkeypatch, fake_lane(tmp_path, body="import time\ntime.sleep(30)\n"), "{packet}")
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 0
    assert cli("--project", project, "lane", "start", "--agent", "developer-1") == 3
    assert len(runs(root)) == 1
    assert cli("--project", project, "lane", "stop", "L-0001") == 0


def test_the_lane_count_follows_the_measured_weight(cli, project: Path) -> None:
    """One prose task is one lane; six code tasks are four, because weight is 2 each."""
    root = init(cli, project)
    add_task(cli, project, "developer", "prose", "--review-profile", "fast")
    assert lanes.measure(root).lanes == 1
    assert lanes.measure(root).band == "trivial"
    for index in range(5):
        add_task(cli, project, "developer", f"code {index}")
    measurement = lanes.measure(root)
    assert measurement.score == 1 + 5 * 2
    assert measurement.lanes == 4
    assert measurement.band == "complex"


def test_a_bug_and_a_deep_unit_weigh_more_than_their_profile(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "security fix", "--tags", "security")
    add_task(cli, project, "developer", "broken thing", "--bug")
    measurement = lanes.measure(root)
    assert measurement.profiles == {"fast": 0, "standard": 1, "deep": 1}
    assert measurement.score == 3 + 2 + 1, "the bug costs one more cycle"


def test_free_slots_and_lane_max_cap_the_policy(cli, project: Path) -> None:
    root = init(cli, project)
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    crowded = {"ollama-cloud": 2, "deepseek": 0, "openai": 0, "anthropic": 0}
    (root / engine.F_SETTINGS).write_text(json.dumps(crowded), encoding="utf-8")
    capped = lanes.measure(root)
    assert capped.lanes == 2
    assert capped.capped_by == "free provider slots"
    (root / engine.F_SETTINGS).write_text(json.dumps({**crowded, "LaneMax": 1}), encoding="utf-8")
    assert lanes.measure(root).lanes == 1


def test_the_packet_budget_follows_the_unit_profile(cli, project: Path) -> None:
    root = init(cli, project)
    add_task(cli, project, "developer", "prose", "--review-profile", "fast")
    add_task(cli, project, "developer", "security fix", "--tags", "security")
    assert (
        cli(
            "--project",
            project,
            "lane",
            "start",
            "--agent",
            "developer-1",
            "--task",
            "T-0001",
            "--print",
        )
        == 0
    )
    fast_packet = Path(lanes.packet_path(root, "Developer-1", "L-0001")).read_text(encoding="utf-8")
    assert "at most 10 tool calls and 10 minutes" in fast_packet
    assert (
        cli(
            "--project",
            project,
            "lane",
            "start",
            "--agent",
            "developer-1",
            "--task",
            "T-0002",
            "--print",
        )
        == 0
    )
    deep_packet = Path(lanes.packet_path(root, "Developer-1", "L-0001")).read_text(encoding="utf-8")
    assert "at most 24 tool calls and 40 minutes" in deep_packet


def test_dry_run_reports_the_complexity_policy(cli, project: Path, capsys) -> None:
    init(cli, project)
    add_task(cli, project, "developer", "one code task")
    assert cli("--project", project, "swarm", "run", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "## complexity (score 2 -> simple)" in out
    assert "policy: up to 1 lane(s)" in out
    assert "profile standard" in out


def test_fixed_mode_turns_the_policy_off(cli, project: Path, tmp_path: Path, monkeypatch) -> None:
    root = init(cli, project)
    for index in range(3):
        add_task(cli, project, "developer", f"code {index}")
    launcher(monkeypatch, fake_lane(tmp_path), "{packet}")
    assert cli("--project", project, "swarm", "run", "--fixed", "--lanes", "1", "--waves", "1") == 0
    assert len([run for run in lanes.load_runs(root) if run["state"] != lanes.STOPPED]) == 1


def test_pulse_spawn_adopts_the_assignments_it_just_committed(
    cli, project: Path, tmp_path: Path, monkeypatch
) -> None:
    """`pulse --commit` claims work no process owns; the swarm must adopt it, not idle."""
    root = init(cli, project)
    add_task(cli, project, "developer", "alpha")
    add_task(cli, project, "developer", "beta")
    launcher(monkeypatch, fake_lane(tmp_path), "{packet}")
    assert cli("--project", project, "pulse", "--commit", "--spawn") == 0
    runs = lanes.load_runs(root)
    assert runs, "the swarm adopted the claims and started lanes"
    assert all(run["profile"] == "standard" for run in runs)
    assert {run["task"] for run in runs} == {"T-0001", "T-0002"}


def test_an_exhausted_assignment_is_not_adopted_again(
    cli, project: Path, tmp_path: Path, monkeypatch
) -> None:
    """The measured defect: unlimited adoption re-planned one task for 783 waves."""
    root = init(cli, project)
    add_task(cli, project, "developer", "stuck")
    launcher(monkeypatch, fake_lane(tmp_path), "{packet}")
    assert cli("--project", project, "swarm", "run", "--minutes", "2") == 0
    attempts = sorted(run["attempt"] for run in lanes.load_runs(root))
    assert attempts == [1, 2], attempts


def test_group_launches_keeps_one_lane_per_instance_and_prefers_the_retry() -> None:
    retry = lanes.Assignment(
        "Developer-1", "developer", "T-0001", "one", attempt=2, source_run="L-0001"
    )
    adopted = lanes.Assignment("Developer-1", "developer", "T-0001", "one", attempt=1, adopted=True)
    second = lanes.Assignment("Developer-1", "developer", "T-0002", "two")
    third = lanes.Assignment("Developer-1", "developer", "T-0003", "three")
    groups = lanes.group_launches([retry, adopted, second, third])
    assert len(groups) == 1
    assert [item.task for item in groups[0]] == ["T-0001", "T-0002"]
    assert groups[0][0].source_run == "L-0001"
