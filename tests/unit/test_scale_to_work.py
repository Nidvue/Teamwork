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


def test_a_full_slot_pool_means_no_adds(cli, project: Path) -> None:
    """A configured pool with zero free slots is a cap, not a licence (review F2)."""
    import json

    root = init(cli, project, "ceo,developer-1")
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    crowded = {"ollama-cloud": 1, "deepseek": 0, "openai": 0, "anthropic": 0}
    (root / engine.F_SETTINGS).write_text(json.dumps(crowded), encoding="utf-8")
    (root / "Runtime" / "Slots" / "ollama-cloud").mkdir(parents=True, exist_ok=True)
    (root / "Runtime" / "Slots" / "ollama-cloud" / "CEO.slot").write_text("x", encoding="utf-8")
    assert engine._scale_plan(root) == [], "no free slot means no new lane"


def test_swarm_observe_mode_never_touches_the_roster(cli, project: Path) -> None:
    """The swarm's own scale step must sit after its accept-mode guard (review F1)."""
    root = init(cli, project, "ceo,developer-1")
    for index in range(6):
        add_task(cli, project, "developer", f"code {index}")
    assert cli("--project", project, "swarm", "run", "--mode", "observe") == 2
    assert len(engine.instances_of(root, "developer")) == 1, "an observe wake mutates nothing"


def test_ready_units_are_spread_across_idle_instances(cli, project: Path, capsys) -> None:
    """One unit each, round-robin: a queue never piles onto one lane.

    The old plan filled Developer-1 to `LANE_WIP` before touching Developer-2, so a
    second idle lane sat unused. Distribution is now round-robin across the role's
    instances; the cap still holds, so a third unit goes back to the first lane.
    """
    root = init(cli, project, "ceo,developer-1,developer-2")
    add_task(cli, project, "developer", "alpha")
    add_task(cli, project, "developer", "beta")
    assert cli("--project", project, "pulse", "--commit") in (0, 3)
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    holders = {t["claimed_by"] for t in tasks if t["status"] == "doing"}
    assert holders == {"Developer-1", "Developer-2"}, holders

    add_task(cli, project, "developer", "gamma")
    assert cli("--project", project, "pulse", "--commit", "--no-scale") in (0, 3)
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    doing = [t for t in tasks if t["status"] == "doing"]
    assert len(doing) == 3
    per_lane: dict = {}
    for task in doing:
        per_lane[task["claimed_by"]] = per_lane.get(task["claimed_by"], 0) + 1
    assert max(per_lane.values()) <= engine.LANE_WIP, per_lane


def test_scale_returns_the_names_it_added_even_at_ten_instances(cli, project: Path) -> None:
    """The added names are a set difference, not the tail of a lexical sort (T-0047 F1).

    `layout.instances_of` sorts names as strings, so `Developer-10` sorts before
    `Developer-2` and `[-count:]` returns an instance that already existed. A
    revert to the slice must fail this test.
    """
    roster = "ceo," + ",".join(f"developer-{index}" for index in range(1, 10))
    root = init(cli, project, roster)
    assert len(engine.instances_of(root, "developer")) == 9

    added = engine._apply_scale(root, [("developer", 1)], "CEO")

    assert added == ["Developer-10"], added
    assert "Developer-10" in engine.instances_of(root, "developer")
    assert len(engine.instances_of(root, "developer")) == 10
