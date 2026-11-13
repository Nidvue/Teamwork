"""The graph between the nodes: what can run in parallel and what the serial cost is.

Why this exists: a loop makes one unit of work correct without a person, and the
team already had one (self-check, independent review, a graded evidence ladder, a
closed lane for an irreversible diff). A loop cannot tell you that two units had
no reason to wait for each other, or that the arrow between them carries nothing.
That question lives on the edge, not inside the node, and the only record the team
kept was ``deps`` as free text that one wave counter summed.

So this module reads the dependency edges the queues already carry and answers
three questions with numbers instead of prose:

* **what runs in parallel** - every open task's wave number, where a wave is the
  set of tasks with no open dependency left;
* **what gates the finish** - the longest chain, i.e. the path whose shortening
  would shorten the run;
* **what an arrow costs** - for every edge, how many waves disappear if the edge
  is cut. An edge whose cost is zero is an arrow carrying nothing: the dependent
  task does not wait for it in any measurable way, and the article's test applies
  (name the payload or delete the arrow). An edge with no shared feature, area or
  tag between its two ends is listed as *unproved* for the same reason.

A dependency on a task that is already ``done`` is satisfied, so it is not an
edge: counting it would report a wait that no lane performs.

Owner: architect. Layer: system. Area: graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .io import die
from .layout import list_roles, project_root, task_file
from .records import (
    OPEN_STATUSES,
    dep_target,
    norm_role,
    parse_tasks,
    split_dependencies,
    task_graph_problems,
)


@dataclass(frozen=True)
class Node:
    """One open task: the unit of work a lane takes, with what it is about."""

    key: str
    role: str
    id: str
    title: str
    status: str
    priority: str
    feature: str
    area: str
    tags: str

    def label(self) -> str:
        return f"{self.key} {self.title}".strip()

    def about(self) -> set:
        tokens = {self.feature.strip(), self.area.strip()}
        tokens.update(part.strip() for part in str(self.tags or "").split(","))
        return {token.lower() for token in tokens if token and token != "-"}


@dataclass
class Graph:
    """The open tasks, the edges between them and what each edge costs."""

    nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)
    level: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)

    @property
    def waves(self) -> list:
        grouped: dict = {}
        for key, wave in self.level.items():
            grouped.setdefault(wave, []).append(key)
        return [sorted(grouped[wave]) for wave in sorted(grouped)]

    @property
    def makespan(self) -> int:
        return max(self.level.values(), default=0)

    def critical_path(self) -> list:
        """The longest chain, walked back from the latest node to a source."""
        if not self.level:
            return []
        current = max(self.level, key=lambda key: (self.level[key], key))
        path = [current]
        while True:
            deps = [dep for dep, node in self.edges if node == current and dep in self.level]
            earlier = [dep for dep in deps if self.level[dep] < self.level[current]]
            if not earlier:
                return list(reversed(path))
            current = max(earlier, key=lambda key: (self.level[key], key))
            path.append(current)


def open_nodes(root: Path) -> dict:
    """Every open task, keyed ``role:T-0001`` on the normalised role name."""
    nodes: dict = {}
    for role in list_roles(root):
        for task in parse_tasks(task_file(root, role)):
            if task.get("status") not in OPEN_STATUSES:
                continue
            key = f"{norm_role(role)}:{task['id']}"
            nodes[key] = Node(
                key=key,
                role=norm_role(role),
                id=task["id"],
                title=str(task.get("title") or ""),
                status=str(task.get("status") or ""),
                priority=str(task.get("priority") or ""),
                feature=str(task.get("feature") or ""),
                area=str(task.get("area") or ""),
                tags=str(task.get("tags") or ""),
            )
    return nodes


def _queues(root: Path) -> dict:
    """Open tasks by normalised role, so a dependency resolves in its own queue."""
    return {
        norm_role(role): [
            task
            for task in parse_tasks(task_file(root, role))
            if task.get("status") in OPEN_STATUSES
        ]
        for role in list_roles(root)
    }


def edges(root: Path, nodes: dict) -> list:
    """``(dep, node)`` for every open dependency edge, sorted for stable output."""
    found = set()
    for role, tasks in _queues(root).items():
        for task in tasks:
            node = f"{role}:{task['id']}"
            if node not in nodes:
                continue
            for raw in split_dependencies(task.get("deps", "")):
                target = dep_target(role, raw)
                if target is None:
                    continue
                dep = f"{target[0]}:{target[1]}"
                if dep in nodes and dep != node:
                    found.add((dep, node))
    return sorted(found)


def levels(nodes: dict, edges: list, cut: tuple | None = None) -> dict:
    """Wave number per node: a source is wave 1, a dependent is one past its deps.

    ``cut`` drops one edge, which is the what-if the report is built on: the same
    graph without an arrow, so the number of waves an arrow costs is measured
    rather than argued. A cycle returns a bounded result instead of recursing
    forever; ``graph --check`` is what refuses it.
    """
    deps: dict = {key: set() for key in nodes}
    for dep, node in edges:
        if dep in nodes and node in nodes and (dep, node) != cut:
            deps[node].add(dep)
    placed: dict = {}

    def walk(key: str, stack: frozenset) -> int:
        if key in placed:
            return placed[key]
        if key in stack:
            return 0
        value = 0
        for dep in deps.get(key, ()):
            value = max(value, walk(dep, stack | {key}))
        placed[key] = value + 1
        return placed[key]

    for key in sorted(nodes):
        walk(key, frozenset())
    return placed


def cut_cost(graph: Graph, dep: str, node: str) -> tuple:
    """``(waves saved overall, waves the dependent moves)`` if this edge is cut."""
    without = levels(graph.nodes, graph.edges, cut=(dep, node))
    return (
        graph.makespan - max(without.values(), default=0),
        graph.level.get(node, 0) - without.get(node, 0),
    )


def build(root: Path) -> Graph:
    nodes = open_nodes(root)
    found = edges(root, nodes)
    return Graph(
        nodes=nodes,
        edges=found,
        level=levels(nodes, found),
        problems=task_graph_problems(root),
    )


def unproved(graph: Graph) -> list:
    """Edges whose two ends share no feature, area or tag: name the payload, or cut."""
    return [
        (dep, node)
        for dep, node in graph.edges
        if not (graph.nodes[dep].about() & graph.nodes[node].about())
    ]


def as_json(graph: Graph) -> dict:
    return {
        "nodes": [
            {
                "key": node.key,
                "role": node.role,
                "id": node.id,
                "title": node.title,
                "status": node.status,
                "priority": node.priority,
                "wave": graph.level.get(node.key, 0),
            }
            for node in sorted(graph.nodes.values(), key=lambda item: item.key)
        ],
        "edges": [
            {"from": dep, "to": node, "waves_saved": cut_cost(graph, dep, node)[0]}
            for dep, node in graph.edges
        ],
        "waves": graph.waves,
        "critical_path": graph.critical_path(),
        "unproved_edges": [{"from": dep, "to": node} for dep, node in unproved(graph)],
        "problems": graph.problems,
    }


def report(graph: Graph) -> list:
    """The human view: waves, critical path, the dearest edges, then the problems."""
    lines = [
        f"# Task graph ({len(graph.nodes)} open node(s), {len(graph.edges)} edge(s), "
        f"{graph.makespan} wave(s))"
    ]
    lines += ["", "## waves (one wave runs in parallel)"]
    if not graph.waves:
        lines.append("- none: no open task carries a dependency")
    for index, wave in enumerate(graph.waves, start=1):
        lines.append(f"{index}. " + ", ".join(graph.nodes[key].label() for key in wave))
    path = graph.critical_path()
    lines += ["", "## critical path (shortening anything else shortens nothing)"]
    lines.append(" -> ".join(path) if path else "- none")
    lines += ["", "## edges, dearest first (waves saved if the arrow is cut)"]
    if not graph.edges:
        lines.append("- none: every open task is independent")
    ranked = sorted(graph.edges, key=lambda edge: (-cut_cost(graph, *edge)[0], edge))
    for dep, node in ranked:
        saved, moved = cut_cost(graph, dep, node)
        lines.append(f"- {node} <- {dep}: {saved} wave(s) saved, {node} moves {moved} earlier")
    loose = unproved(graph)
    lines += ["", "## unproved edges (no shared feature, area or tag: name the payload or cut)"]
    if not loose:
        lines.append("- none")
    for dep, node in loose:
        lines.append(f"- {node} <- {dep}")
    lines += ["", "## problems"]
    if not graph.problems:
        lines.append("- none")
    for problem in graph.problems:
        lines.append(f"- {problem}")
    return lines


def cmd_graph(args) -> int:
    root = project_root(args)
    graph = build(root)
    if getattr(args, "check", False):
        for problem in graph.problems:
            print(f"- {problem}")
        print(f"# graph check: {len(graph.problems)} problem(s)")
        return 1 if graph.problems else 0
    cut = None
    raw = str(getattr(args, "cut", "") or "").strip()
    if raw:
        parts = raw.split("<-") if "<-" in raw else raw.split()
        if len(parts) != 2:
            die("--cut takes one edge as '<dep> <- <task>', e.g. developer:T-0001 <- ceo:T-0002", 2)
        cut = (parts[0].strip(), parts[1].strip())
        missing = [key for key in cut if key not in graph.nodes]
        if missing:
            die(
                f"--cut names no open task: {', '.join(missing)}; "
                "run `teamwork graph` for the node keys",
                2,
            )
        if cut not in graph.edges:
            die(
                f"--cut names no edge: {cut[0]} <- {cut[1]}; the graph has "
                + (", ".join(f"{dep} <- {node}" for dep, node in graph.edges) or "none")
                + ".",
                2,
            )
    if getattr(args, "json", False):
        payload = as_json(graph)
        if cut:
            payload["cut"] = {"edge": list(cut), "waves_saved": cut_cost(graph, *cut)[0]}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if cut:
        trimmed = Graph(
            nodes=graph.nodes,
            edges=[edge for edge in graph.edges if edge != cut],
            level=levels(graph.nodes, graph.edges, cut=cut),
            problems=graph.problems,
        )
        lines = report(trimmed)
        lines.insert(
            1,
            f"# cut {cut[0]} <- {cut[1]}: {graph.makespan} -> {trimmed.makespan} wave(s)",
        )
        print("\n".join(lines))
        return 0
    print("\n".join(report(graph)))
    return 0


def add_parsers(sub, common) -> None:
    s = sub.add_parser(
        "graph",
        parents=[common],
        help="the dependency graph between tasks: waves, critical path, what an arrow costs",
    )
    s.add_argument(
        "--cut",
        default="",
        metavar="EDGE",
        help="what-if: print the waves without one edge, as '<dep> <- <task>'",
    )
    s.add_argument(
        "--check",
        action="store_true",
        help="exit 1 on a cycle, a dangling dependency or a duplicate open id",
    )
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.set_defaults(func=cmd_graph)
