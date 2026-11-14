"""The routing graph: every edge reads state, and the checks can fail.

Why these tests exist: a team that runs one step after another because the script
says so looks identical, from the outside, to one that routes on what it just
learned - until you ask which field decided the next move. `graph` answers that
for every transition the engine performs, so the two properties that make the
answer worth anything are pinned here:

* every edge names a state source the record layer really parses, and every
  source in the table is used by an edge - a dead source is drift, a missing one
  is an edge that reads nothing;
* each audit code fires on the workspace that breaks it and stays silent on the
  one that does not: a serial dependency chain under a multi-instance roster, a
  dependency cycle, a rework loop past the fail cap with no dispute, and a roster
  whose coordination cost was never priced against a single-agent baseline.

The live readings are pinned too, because a probe that always returns zero would
make the table look clean while saying nothing.

Owner: developer. Layer: unit. Area: graph.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine, graph
from teamwork.config import REVIEW_FAIL_LIMIT

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def edit_task(root: Path, role: str, handle: str, **fields) -> None:
    path = engine.task_file(root, role)
    tasks = engine.parse_tasks(path)
    task = next(item for item in tasks if item["id"] == handle)
    task.update(fields)
    engine.write_tasks(path, tasks, role)


def problems(cli, project: Path) -> list[str]:
    report = graph.findings(team_root(project), project)
    assert isinstance(report, list)
    return report


def codes(items: list[str]) -> set[str]:
    return {item.split(" ", 1)[0] for item in items}


def test_every_edge_names_a_state_source_the_record_layer_parses() -> None:
    """An edge whose field nothing parses reads nothing: it cannot be verified."""
    used: set[str] = set()
    for edge in graph.EDGES:
        assert edge.reads, f"{edge.id} fires on no state at all"
        for source in edge.reads:
            assert source in graph.STATE_SOURCES, f"{edge.id} reads unknown source {source}"
            used.add(source)
    assert used == set(graph.STATE_SOURCES), "a declared state source no edge reads is drift"


def test_every_edge_that_fires_has_a_ledger_action_or_is_the_exit() -> None:
    """`taken` is counted from the ledger, so a firing edge must be recorded there."""
    for edge in graph.EDGES:
        assert edge.actions, f"{edge.id} cannot be counted: no ledger action fires it"


def test_the_exit_edge_reads_the_records_loop_reads() -> None:
    """The stop condition lives in state, not in a timeout (the article's exit rule)."""
    exit_edge = next(edge for edge in graph.EDGES if edge.dst == "stop")
    assert set(exit_edge.reads) == {
        "Criteria.md.status",
        "TaskQueue.status",
        "Disputes.md.status",
    }


def test_the_exit_edge_agrees_with_loop_on_every_workspace(cli, project: Path) -> None:
    """One gate, one place: the edge delegates to the gate report instead of restating it."""
    root = init(cli, project)
    exit_edge = next(edge for edge in graph.EDGES if edge.dst == "stop")
    blocked = engine.gate_report(root)["blockers"]
    assert exit_edge.probe(root).units == (0 if blocked else 1)
    assert blocked, "a fresh workspace cannot be finished: the exit must be shut"
    assert cli("--project", project, "task", "add", "developer", "work") == 0
    assert exit_edge.probe(root).units == 0
    assert engine.gate_report(root)["blockers"], "an open task blocks the exit"


def test_show_prints_every_edge_with_its_state_and_exits_zero(cli, project: Path, capsys) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "the first task") == 0
    capsys.readouterr()
    assert cli("--project", project, "graph") == 0
    out = capsys.readouterr().out
    for edge in graph.EDGES:
        assert edge.id in out
    assert "TaskQueue.status" in out
    assert "# next: E1" in out, "a todo task must make the dispatch edge fire"
    assert "UNRECORDED" in out, "an unpriced roster must not read as priced"


def test_json_snapshot_reports_the_live_reading(cli, project: Path, capsys) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "work") == 0
    capsys.readouterr()
    assert cli("--project", project, "graph", "show", "--json") == 0
    data = json.loads(capsys.readouterr().out)
    dispatch = next(edge for edge in data["edges"] if edge["id"] == "E1")
    assert dispatch["now"] == 1 and "developer:T-0001" in dispatch["detail"]
    assert data["conditional_edges"] == len(graph.EDGES)
    assert data["instances"], "the roster is read from the tree, not from the edges"


def test_the_group_flag_works_with_and_without_the_subcommand(cli, project: Path, capsys) -> None:
    """`graph --json` is the same command as `graph show --json`, in either order."""
    init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "graph", "--json") == 0
    first = json.loads(capsys.readouterr().out)
    assert cli("--project", project, "graph", "show", "--json") == 0
    assert json.loads(capsys.readouterr().out) == first
    assert first["command"] == "graph"


def test_graph_refuses_a_directory_that_is_not_a_workspace(cli, project: Path, capsys) -> None:
    """An empty tree would print a plausible graph of nothing: say so instead."""
    capsys.readouterr()
    assert cli("--project", project, "graph") == 1
    assert "no team workspace" in capsys.readouterr().err
    assert cli("--project", project, "graph", "audit") == 1


def test_a_serial_chain_under_a_multi_instance_roster_is_a_finding(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one") == 0
    assert cli("--project", project, "task", "add", "developer", "two", "--deps", "T-0001") == 0
    assert cli("--project", project, "task", "add", "developer", "three", "--deps", "T-0002") == 0
    assert "C-GRAPH-CHAIN" in codes(problems(cli, project))
    edit_task(root, "developer", "T-0003", deps="")
    assert "C-GRAPH-CHAIN" not in codes(problems(cli, project))


def test_a_dependency_cycle_is_a_loop_with_no_exit(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one") == 0
    assert cli("--project", project, "task", "add", "developer", "two", "--deps", "T-0001") == 0
    edit_task(root, "developer", "T-0001", deps="T-0002")
    found = problems(cli, project)
    assert "C-GRAPH-EXIT" in codes(found)
    assert any("dependency cycle" in item for item in found)


def test_a_capped_rework_loop_needs_an_open_dispute_as_its_exit(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "reworked") == 0
    edit_task(
        root,
        "developer",
        "T-0001",
        status="doing",
        review_status="failed",
        review_fails=REVIEW_FAIL_LIMIT,
    )
    assert "C-GRAPH-EXIT" in codes(problems(cli, project))
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            "developer-1",
            "--against",
            "reviewer-1",
            "--topic",
            "the third fail is contested",
            "--task",
            "T-0001",
        )
        == 0
    )
    assert "C-GRAPH-EXIT" not in codes(problems(cli, project))


def test_a_second_lane_is_unpriced_until_a_baseline_is_recorded(cli, project: Path, capsys) -> None:
    init(cli, project, "ceo,developer-1")
    assert "C-GRAPH-PRICE" not in codes(problems(cli, project)), "one lane needs no baseline"
    assert cli("--project", project, "instance", "add", "developer", "--count", "2") == 0
    assert "C-GRAPH-PRICE" in codes(problems(cli, project))
    capsys.readouterr()
    assert cli("--project", project, "graph", "baseline", "--record", "x", "--tokens", "0") == 1, (
        "a baseline with no evidence is refused"
    )
    assert (
        cli(
            "--project",
            project,
            "graph",
            "baseline",
            "--record",
            "one agent on the same brief -> 41 tool calls, 210000 tokens",
            "--tokens",
            "210000",
            "--by",
            "ceo",
        )
        == 0
    )
    assert "C-GRAPH-PRICE" not in codes(problems(cli, project))


def test_audit_exits_one_on_a_finding_and_zero_when_clean(cli, project: Path, capsys) -> None:
    init(cli, project, "ceo,developer-1")
    assert (
        cli(
            "--project",
            project,
            "graph",
            "baseline",
            "--record",
            "one agent on the same brief -> 210000 tokens",
            "--by",
            "ceo",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "graph", "audit") == 0
    assert "clean" in capsys.readouterr().out
    assert cli("--project", project, "task", "add", "developer", "one") == 0
    assert cli("--project", project, "task", "add", "developer", "two", "--deps", "T-0001") == 0
    assert cli("--project", project, "task", "add", "developer", "three", "--deps", "T-0002") == 0
    assert cli("--project", project, "instance", "add", "developer", "--count", "2") == 0
    capsys.readouterr()
    assert cli("--project", project, "graph", "audit") == 1
    out = capsys.readouterr().out
    assert "C-GRAPH-CHAIN" in out


def test_the_live_probes_read_the_records_they_claim(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one") == 0
    live = {edge.id: edge.probe(root) for edge in graph.EDGES}
    assert live["E1"].units == 1, "a todo task is what the dispatch edge acts on"
    assert live["E9"].units == 0, "an open task blocks the exit"
    edit_task(root, "developer", "T-0001", status="review", self_check="passed")
    live = {edge.id: edge.probe(root) for edge in graph.EDGES}
    assert live["E2"].units == 1
    assert live["E9"].units == 0
    edit_task(root, "developer", "T-0001", status="done", review_status="passed")
    live = {edge.id: edge.probe(root) for edge in graph.EDGES}
    assert live["E1"].units == 0
    assert live["E5"].units == 0, "a pass that already landed is not awaiting a merge"


def test_a_recorded_baseline_is_a_ledger_record_too(cli, project: Path) -> None:
    """A mutation of team state that leaves no trail is invisible to `audit`."""
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "graph",
            "baseline",
            "--record",
            "one agent -> 210000 tokens",
            "--tokens",
            "210000",
            "--by",
            "ceo",
        )
        == 0
    )
    actions = [
        json.loads(line)["action"]
        for line in (root / "Ledger.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert "graph.baseline" in actions


def test_baseline_round_trips_and_survives_a_corrupt_file(cli, project: Path) -> None:
    root = init(cli, project)
    assert graph.read_baseline(root) is None
    graph.write_baseline(root, "one agent, 210000 tokens", "ceo", 210000)
    stored = graph.read_baseline(root)
    assert stored is not None and stored["tokens"] == 210000 and stored["by"] == "ceo"
    graph.baseline_path(root).write_text("{not json", encoding="utf-8")
    assert graph.read_baseline(root) is None
