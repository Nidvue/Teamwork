"""The roster follows the work: the wave is bounded by the job, never by one lane.

Why these tests exist: a team staffed with one Developer serialises six ready
tasks behind one instance, and a review queue fans onto a single Reviewer - the
two bottlenecks the CEO is told to break. `pulse --commit` (and `swarm run`) now
add instances for the ready work (one lane carries LANE_WIP units) and for the
unclaimed reviews (one Reviewer takes one deliverable), bounded by the per-role
cap, the per-wake cap and the free provider slots. Folding is the other half, and
it obeys the accept mode: an `observe` wake reports and retires nothing.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def add_task(cli, project: Path, role: str, title: str) -> None:
    assert cli("--project", project, "task", "add", role, title) == 0


def review_ready(root: Path) -> None:
    path = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(path)
    tasks[0]["status"] = "review"
    tasks[0]["self_check"] = "passed"
    tasks[0]["claimed_by"] = "Developer-1"
    engine.write_tasks(path, tasks, "developer")


def test_the_plan_sizes_workers_from_the_ready_work(cli, project: Path) -> None:
    root = init(cli, project, "ceo,developer-1")
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    plan = dict(engine._scale_plan(root))
    assert plan["developer"] == 2, "6 units / LANE_WIP 2 = 3 lanes, 1 already staffed"


def test_the_plan_sizes_reviewers_one_per_deliverable(cli, project: Path) -> None:
    root = init(cli, project, "ceo,developer-1,reviewer-1")
    for index in range(3):
        add_task(cli, project, "developer", f"deliverable {index}")
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    for task in tasks:
        task["status"] = "review"
        task["self_check"] = "passed"
        task["claimed_by"] = "Developer-1"
    engine.write_tasks(engine.task_file(root, "developer"), tasks, "developer")
    plan = dict(engine._scale_plan(root))
    assert plan["reviewer"] == 2, "one Reviewer takes one deliverable, so 3 need 3 lanes"


def test_pulse_commit_adds_the_instances_and_dispatches_to_them(cli, project: Path, capsys) -> None:
    root = init(cli, project, "ceo,developer-1")
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    capsys.readouterr()
    assert cli("--project", project, "pulse", "--commit") in (0, 3)
    out = capsys.readouterr().out
    assert "scaled to the work" in out, out
    assert len(engine.instances_of(root, "developer")) == 3
    assert "ready task(s) have no free lane" not in out


def test_no_scale_dispatches_to_the_current_roster_only(cli, project: Path, capsys) -> None:
    root = init(cli, project, "ceo,developer-1")
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    capsys.readouterr()
    assert cli("--project", project, "pulse", "--commit", "--no-scale") in (0, 3)
    out = capsys.readouterr().out
    assert "scale plan" not in out and "scaled to the work" not in out, out
    assert len(engine.instances_of(root, "developer")) == 1


def test_folding_obeys_the_accept_mode(cli, project: Path, capsys) -> None:
    root = init(cli, project, "ceo,developer-1,developer-2")
    capsys.readouterr()
    assert cli("--project", project, "pulse", "--commit", "--mode", "observe") in (0, 3)
    out = capsys.readouterr().out
    assert "folding skipped" in out, out
    assert engine.agent_dir(root, "developer-2").is_dir(), "an observe wake dispatches nothing"
