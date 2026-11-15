"""Integration: the routing graph, driven through the shipped CLI on a real tree.

The unit layer pins the edge table and the audit codes against a synthetic
workspace. This layer asks the question an operator asks - what does the command
do on a team tree that `init` just created, with real queues, a real ledger and a
real baseline file - because a graph that is right in memory and wrong through
`teamwork.py` is wrong.

Owner: ceo. Layer: integration. Area: graph. Task: T-0031.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine, graph

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def init(cli, project: Path, capsys, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    capsys.readouterr()
    return team_root(project)


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def test_the_cli_renders_every_edge_with_its_state_source(cli, project: Path, capsys) -> None:
    init(cli, project, capsys)

    assert cli("--project", project, "graph") == 0
    out = capsys.readouterr().out

    for edge in graph.EDGES:
        assert f"{edge.id:4} {edge.src} -> {edge.dst}" in out, edge.id
    assert f"# routing graph: {len(graph.EDGES)} conditional edges" in out


def test_json_is_the_same_snapshot_whichever_spelling_asks_for_it(
    cli, project: Path, capsys
) -> None:
    init(cli, project, capsys)

    assert cli("--project", project, "graph", "--json") == 0
    bare = json.loads(capsys.readouterr().out)
    assert cli("--project", project, "graph", "show", "--json") == 0
    spelled = json.loads(capsys.readouterr().out)

    assert bare["edges"] == spelled["edges"]
    assert len(bare["edges"]) == len(graph.EDGES)
    assert [edge["id"] for edge in bare["edges"]] == [edge.id for edge in graph.EDGES]


def test_a_serial_chain_under_a_fanned_out_roster_is_a_finding(cli, project: Path, capsys) -> None:
    root = init(cli, project, capsys)
    for index in (1, 2, 3):
        assert cli("--project", project, "task", "add", "developer", f"step {index}") == 0
    capsys.readouterr()
    path = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(path)
    for index, task in enumerate(tasks, start=1):
        task["deps"] = f"developer:T-{index - 1:04d}" if index > 1 else ""
        task["status"] = "todo"
        task["claimed_by"] = ""
    engine.write_tasks(path, tasks, "developer")

    assert cli("--project", project, "graph", "audit") == 1
    out = capsys.readouterr().out
    assert "C-GRAPH-CHAIN" in out


def test_a_recorded_baseline_is_a_file_and_a_ledger_line(cli, project: Path, capsys) -> None:
    root = init(cli, project, capsys)
    before = graph.ledger_counts(root).get("graph.baseline", 0)

    assert (
        cli(
            "--project",
            project,
            "graph",
            "baseline",
            "--record",
            "pytest -q -> 1 passed",
            "--tokens",
            "1200",
            "--by",
            "ceo",
        )
        == 0
    )
    capsys.readouterr()

    baseline = graph.read_baseline(root)
    assert baseline is not None
    assert baseline["record"] == "pytest -q -> 1 passed"
    assert baseline["tokens"] == 1200
    assert graph.ledger_counts(root).get("graph.baseline", 0) == before + 1


def test_a_second_baseline_supersedes_the_first_instead_of_stacking(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project, capsys)
    for record, tokens in (("first -> 1", 10), ("second -> 2", 20)):
        assert (
            cli(
                "--project",
                project,
                "graph",
                "baseline",
                "--record",
                record,
                "--tokens",
                str(tokens),
                "--by",
                "ceo",
            )
            == 0
        )
        capsys.readouterr()

    baseline = graph.read_baseline(root)
    assert baseline is not None
    assert baseline["record"] == "second -> 2"
    assert baseline["tokens"] == 20
    assert len(list(root.glob("Runtime/GraphBaseline.json"))) == 1


def test_the_exit_edge_reports_the_blockers_it_read(cli, project: Path, capsys) -> None:
    init(cli, project, capsys)

    assert cli("--project", project, "graph") == 0
    graph_out = capsys.readouterr().out

    assert "# exit: shut" in graph_out
    assert "no acceptance criteria recorded" in graph_out
