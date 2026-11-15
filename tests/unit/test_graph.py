"""Unit: the task graph - waves, critical path, and what one dependency costs.

Layer ``unit``, area ``graph``. The claim under test is the one a loop cannot
answer: a task's correctness is a property of the node, and the *order* of the
nodes is a property of the edge. Two facts have to hold for the report to be worth
reading - a dependency that is already ``done`` is not a wait, and an edge's cost
is measured by rebuilding the graph without it, not by an opinion about it.

The pure cases pin the arithmetic on a hand-built graph, so they run everywhere;
the CLI case pins the wiring on a real workspace.

Owner: architect. Layer: unit. Area: graph.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from teamwork import engine
from teamwork.graph import Graph, cut_cost, levels, open_nodes, unproved


def graph_of(spec: dict) -> Graph:
    from teamwork.graph import Node

    nodes = {}
    edges = []
    for key, deps in spec.items():
        role, tid = key.split(":")
        nodes[key] = Node(
            key=key,
            role=role,
            id=tid,
            title=f"task {tid}",
            status="todo",
            priority="P1",
            feature="",
            area="",
            tags="",
        )
        edges.extend((dep, key) for dep in deps)
    return Graph(nodes=nodes, edges=sorted(edges), level=levels(nodes, sorted(edges)))


CHAIN = graph_of({"ceo:T-0001": (), "ceo:T-0002": ("ceo:T-0001",), "dev:T-0001": ("ceo:T-0002",)})


def test_a_source_is_wave_one_and_a_dependent_is_one_past_its_dependencies() -> None:
    assert CHAIN.level == {"ceo:T-0001": 1, "ceo:T-0002": 2, "dev:T-0001": 3}
    assert CHAIN.waves == [["ceo:T-0001"], ["ceo:T-0002"], ["dev:T-0001"]]
    assert CHAIN.makespan == 3


def test_independent_tasks_share_a_wave() -> None:
    graph = graph_of({"ceo:T-0001": (), "ceo:T-0002": (), "dev:T-0001": ("ceo:T-0001",)})
    assert graph.waves == [["ceo:T-0001", "ceo:T-0002"], ["dev:T-0001"]]
    assert graph.makespan == 2


def test_the_critical_path_is_the_longest_chain_not_the_longest_list() -> None:
    graph = graph_of(
        {
            "ceo:T-0001": (),
            "ceo:T-0002": ("ceo:T-0001",),
            "dev:T-0001": ("ceo:T-0002",),
            "dev:T-0002": (),
        }
    )
    assert graph.critical_path() == ["ceo:T-0001", "ceo:T-0002", "dev:T-0001"]


def test_an_edge_costs_the_waves_that_disappear_without_it() -> None:
    assert cut_cost(CHAIN, "ceo:T-0001", "ceo:T-0002") == (1, 1)
    assert cut_cost(CHAIN, "ceo:T-0002", "dev:T-0001") == (1, 2)


def test_a_redundant_edge_costs_nothing() -> None:
    """The article's arrow that carries nothing: cutting it shortens no run."""
    graph = graph_of(
        {"ceo:T-0001": (), "ceo:T-0002": (), "dev:T-0001": ("ceo:T-0001", "ceo:T-0002")}
    )
    assert graph.level["dev:T-0001"] == 2
    assert cut_cost(graph, "ceo:T-0002", "dev:T-0001") == (0, 0)


def test_an_edge_with_no_shared_feature_area_or_tag_is_unproved() -> None:
    graph = graph_of({"ceo:T-0001": (), "ceo:T-0002": ("ceo:T-0001",)})
    assert unproved(graph) == [("ceo:T-0001", "ceo:T-0002")]
    graph.nodes["ceo:T-0001"] = replace(graph.nodes["ceo:T-0001"], feature="F-0001")
    graph.nodes["ceo:T-0002"] = replace(graph.nodes["ceo:T-0002"], feature="F-0001")
    assert unproved(graph) == []
    graph.nodes["ceo:T-0002"] = replace(graph.nodes["ceo:T-0002"], feature="F-0002")
    assert unproved(graph) == [("ceo:T-0001", "ceo:T-0002")]


def test_a_done_dependency_is_not_an_edge(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    capsys.readouterr()
    assert (
        cli("--project", project, "task", "add", "ceo", "first", "--priority", "P1", "--no-review")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "ceo",
            "second",
            "--priority",
            "P1",
            "--deps",
            "ceo:T-0001",
        )
        == 0
    )
    capsys.readouterr()
    root = engine.project_root(_args(project))
    before = open_nodes(root)
    assert sorted(before) == ["ceo:T-0001", "ceo:T-0002"]
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "ceo",
            "T-0001",
            "--status",
            "done",
            "--evidence",
            "teamwork graph @a1b2c3d -> 1 passed",
        )
        == 0
    )
    after = open_nodes(root)
    assert sorted(after) == ["ceo:T-0002"]


def _args(project: Path):
    import argparse

    return argparse.Namespace(project=str(project), team="")


def test_the_report_names_the_waves_and_the_critical_path(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    assert cli("--project", project, "task", "add", "ceo", "research", "--priority", "P1") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "build",
            "--priority",
            "P0",
            "--deps",
            "ceo:T-0001",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "graph") == 0
    out = capsys.readouterr().out
    assert "# Task graph (2 open node(s), 1 edge(s), 2 wave(s))" in out
    assert "1. ceo:T-0001 research" in out
    assert "ceo:T-0001 -> developer:T-0001" in out
    assert cli("--project", project, "graph", "--check") == 0
    assert cli("--project", project, "graph", "--cut", "ceo:T-0001 <- developer:T-0001") == 0
    assert "2 -> 1 wave(s)" in capsys.readouterr().out
