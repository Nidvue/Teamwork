"""The routing graph: which lane runs next, read from state, and when to stop.

A harness keeps one agent honest; a loop makes it better run over run; a graph
decides **which** agent runs next, and when the whole run is finished. A chain -
A, then B, then C, whatever B found - is what you get when that third layer is
missing, and it is invisible in a headcount: "twenty agents running" describes
seats, not routing ([distort, "Everyone Is Building Agent Teams. Nobody Is
Building The Graph"](https://x.com/distortgeekin/status/2099117449232699548),
accessed 2026-11-12).

This module makes the graph inspectable instead of implied. Every transition the
engine already performs is one :class:`Edge` here, and an edge is only a real
edge if it names the state field that fires it. ``graph`` prints the table with
the live reading of every one of those fields, so the question the article says
nobody can answer - *what changes what happens next?* - has a command. Two
consequences follow, and both are checks rather than prose:

* **Edges, not agents.** ``graph audit`` reports a role holding more than one
  lane over an empty queue, and a dependency graph that is one serial chain
  longer than the roster, because in both cases the extra instances cannot
  change what runs next - that is a dashboard, not a graph.
* **The exit is state too.** The stop edge *is* ``loop``'s gate report, called
  rather than restated, so the two can never disagree; the rework cycle is
  bounded by ``REVIEW_FAIL_LIMIT`` with a dispute as the exit, and an unbounded
  review loop and a dependency cycle are both reported as a loop with no exit.

The third mistake the article names - never pricing coordination against a
single-agent baseline - is the ``# cost:`` block: duplicated startup context and
the coordination records are measured on disk, and until ``graph baseline``
records what one agent doing this work actually cost, the extra spend is printed
as ``UNVERIFIED`` rather than assumed to be worth it.

The edge table is code, so a test pins every state source it names to a field the
record layer really parses; the baseline is state, because it is a measurement of
the world outside this tree.
"""

from __future__ import annotations

import argparse
import datetime
import json
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from .config import (
    DIR_AGENTS,
    DIR_ROLES,
    DIR_RUNTIME,
    F_INBOX,
    F_LEDGER,
    MAX_ROUNDS,
    REVIEW_FAIL_LIMIT,
)
from .harness import budget_rows, repo_root
from .io import atomic_write, die
from .layout import (
    agent_dir,
    disputes_path,
    instances_of,
    known_instances,
    lessons_path,
    list_roles,
    project_root,
    reviews_path,
    tests_path,
)
from .names import resolve_role
from .records import (
    OPEN_STATUSES,
    dep_target,
    executable,
    load_task_queues,
    local_dep_map,
    norm_role,
    parse_disputes,
    parse_lessons,
    parse_tests,
    split_dependencies,
)

BASELINE_FILE = "GraphBaseline.json"

STATE_SOURCES = {
    "TaskQueue.status": "a task's status: todo, doing, selfcheck, review, done",
    "TaskQueue.self_check": "the author's own check: pending, passed, failed",
    "TaskQueue.review_status": "the independent verdict: pending, passed, failed",
    "TaskQueue.review_fails": "how many times the review sent the task back",
    "TaskQueue.deps": "the dependency edges and their release mode",
    "Tests.md.status": "the last recorded run of one (layer, area)",
    "Criteria.md.status": "verified or pending, with its evidence",
    "Disputes.md.status": "open, escalated or resolved, with its round count",
    "Lessons.md.status": "open, fixed, or superseded",
}


class Live(NamedTuple):
    units: int
    detail: str


class Edge(NamedTuple):
    id: str
    src: str
    dst: str
    fires: str
    reads: tuple[str, ...]
    actions: tuple[str, ...]
    probe: Callable[[Path], Live]


def _ids(items: list) -> str:
    names = [str(item) for item in items]
    if not names:
        return "-"
    head = ", ".join(names[:4])
    return head if len(names) <= 4 else f"{head} +{len(names) - 4}"


def _open_tasks(root: Path) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for role, tasks in sorted(load_task_queues(root).items()):
        out.extend((role, task) for task in tasks if task.get("status") in OPEN_STATUSES)
    return out


def _where(role: str, task: dict) -> str:
    return f"{role}:{str(task.get('id') or '').upper()}"


def _disputes(root: Path) -> list[dict]:
    return parse_disputes(disputes_path(root))


def _disputed(root: Path) -> set[str]:
    return {
        str(item.get("task") or "").upper()
        for item in _disputes(root)
        if item.get("status") != "resolved" and item.get("task")
    }


def _probe_routable(root: Path) -> Live:
    cache: dict = {}
    items: list[str] = []
    for role, tasks in sorted(load_task_queues(root).items()):
        lookup = local_dep_map(tasks)
        items.extend(_where(role, task) for task in tasks if executable(task, lookup, cache, root))
    return Live(len(items), _ids(items))


def _probe_selfchecked(root: Path) -> Live:
    items = [
        _where(role, task)
        for role, task in _open_tasks(root)
        if task.get("status") == "review"
        and task.get("self_check") == "passed"
        and task.get("review_status") == "pending"
    ]
    return Live(len(items), _ids(items))


def _probe_returned(root: Path) -> Live:
    items = [
        _where(role, task)
        for role, task in _open_tasks(root)
        if task.get("review_status") == "failed" and _fails(task) < REVIEW_FAIL_LIMIT
    ]
    return Live(len(items), _ids(items))


def _probe_capped(root: Path) -> Live:
    open_disputes = _disputed(root)
    items = [
        _where(role, task)
        for role, task in _open_tasks(root)
        if _fails(task) >= REVIEW_FAIL_LIMIT
        and str(task.get("id") or "").upper() not in open_disputes
    ]
    return Live(len(items), _ids(items))


def _probe_passed(root: Path) -> Live:
    items = [
        _where(role, task)
        for role, task in _open_tasks(root)
        if task.get("review_status") == "passed"
    ]
    return Live(len(items), _ids(items))


def _probe_escalated(root: Path) -> Live:
    items = [
        f"{item.get('id')} r{item.get('round')}"
        for item in _disputes(root)
        if item.get("status") != "resolved"
        and (item.get("escalated") or int(item.get("round") or 0) >= MAX_ROUNDS)
    ]
    return Live(len(items), _ids(items))


def _probe_failed_run(root: Path) -> Live:
    items = [
        f"{record.get('id')} {record.get('layer')}/{record.get('area')}"
        for record in parse_tests(tests_path(root))
        if record.get("status") == "fail"
    ]
    return Live(len(items), _ids(items))


def _probe_open_lesson(root: Path) -> Live:
    items: list[str] = []
    for role in list_roles(root):
        for lesson in parse_lessons(lessons_path(root, role)):
            if lesson.get("status") == "open" and not lesson.get("skill"):
                items.append(f"{role}:{lesson.get('id')}")
    return Live(len(items), _ids(items))


def _probe_exit(root: Path) -> Live:
    """The exit edge is `loop`'s gate report: called, never restated."""
    from .engine import gate_report

    blockers = gate_report(root)["blockers"]
    if not blockers:
        return Live(1, "every gate is green")
    head = "; ".join(blockers[:3])
    more = f" +{len(blockers) - 3}" if len(blockers) > 3 else ""
    return Live(0, f"{len(blockers)} blocker(s): {head}{more}")


def _fails(task: dict) -> int:
    try:
        return int(task.get("review_fails") or 0)
    except (TypeError, ValueError):
        return 0


EDGES: tuple[Edge, ...] = (
    Edge(
        "E1",
        "ceo",
        "lane",
        "a ready task exists and a lane holds nothing",
        ("TaskQueue.status", "TaskQueue.deps"),
        ("task.claim",),
        _probe_routable,
    ),
    Edge(
        "E2",
        "lane",
        "reviewer",
        "the author's self-check passed",
        ("TaskQueue.self_check",),
        ("selfcheck",),
        _probe_selfchecked,
    ),
    Edge(
        "E3",
        "reviewer",
        "lane",
        "the verdict was fail and the fail count is under the cap",
        ("TaskQueue.review_status", "TaskQueue.review_fails"),
        ("review.fail",),
        _probe_returned,
    ),
    Edge(
        "E4",
        "reviewer",
        "dispute",
        "the fail count reached the cap",
        ("TaskQueue.review_fails", "Disputes.md.status"),
        ("dispute.open",),
        _probe_capped,
    ),
    Edge(
        "E5",
        "reviewer",
        "main",
        "the verdict was pass",
        ("TaskQueue.review_status",),
        ("review.pass", "pr.merge"),
        _probe_passed,
    ),
    Edge(
        "E6",
        "dispute",
        "ceo",
        "the dispute reached the round cap and is escalated",
        ("Disputes.md.status",),
        ("dispute.resolve",),
        _probe_escalated,
    ),
    Edge(
        "E7",
        "lane",
        "lane",
        "a recorded run failed",
        ("Tests.md.status",),
        ("tests.run",),
        _probe_failed_run,
    ),
    Edge(
        "E8",
        "lane",
        "lane",
        "a lesson is open with no skill behind it",
        ("Lessons.md.status",),
        ("skill.create",),
        _probe_open_lesson,
    ),
    Edge(
        "E9",
        "ceo",
        "stop",
        "nothing blocks the exit",
        ("Criteria.md.status", "TaskQueue.status", "Disputes.md.status"),
        ("ledger.export",),
        _probe_exit,
    ),
)


def ledger_counts(root: Path) -> dict[str, int]:
    """How many times each ledger action was taken: the edges that actually fired."""
    path = root / F_LEDGER
    counts: dict[str, int] = {}
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        action = str(record.get("action") or "")
        if action:
            counts[action] = counts.get(action, 0) + 1
    return counts


def baseline_path(root: Path) -> Path:
    return root / DIR_RUNTIME / BASELINE_FILE


def read_baseline(root: Path) -> dict | None:
    path = baseline_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_baseline(root: Path, record: str, by: str, tokens: int) -> Path:
    path = baseline_path(root)
    payload = {
        "record": record.strip(),
        "by": by.strip(),
        "tokens": int(tokens),
        "at": datetime.datetime.now().replace(microsecond=0).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _open_edges(root: Path) -> dict[tuple[str, str], list[tuple[str, str]]]:
    queues = load_task_queues(root)
    known = {
        (role, str(task.get("id") or "").upper())
        for role, items in queues.items()
        for task in items
        if task.get("status") in OPEN_STATUSES
    }
    edges: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for role, items in queues.items():
        for task in items:
            node = (role, str(task.get("id") or "").upper())
            if node not in known:
                continue
            targets = []
            for dep in split_dependencies(task.get("deps", "")):
                target = dep_target(role, dep)
                if target is not None and target in known and target != node:
                    targets.append(target)
            edges[node] = targets
    return edges


def longest_chain(root: Path) -> tuple[int, str]:
    """The longest dependency path among the open tasks, as (length, one path)."""
    edges = _open_edges(root)
    if not edges:
        return 0, "-"
    best: dict[tuple[str, str], tuple[int, list]] = {}

    def walk(node: tuple[str, str], stack: tuple) -> tuple[int, list]:
        if node in stack:
            return 0, []
        if node in best:
            return best[node]
        length, path = 0, []
        for nxt in edges.get(node, []):
            sub_length, sub_path = walk(nxt, (*stack, node))
            if sub_length + 1 > length:
                length, path = sub_length + 1, [node, *sub_path]
        best[node] = (length, path or [node])
        return best[node]

    top_length: int = 0
    top_path: list = []
    for node in edges:
        length, path = walk(node, ())
        if length > top_length or not top_path:
            top_length, top_path = length, path
    return top_length + 1, " -> ".join(f"{role}:{tid}" for role, tid in top_path)


def cost(root: Path, repo: Path) -> dict:
    """What the roster costs before any work: duplicated context plus coordination."""
    rows, _cap, _source = budget_rows(repo, root, None)
    startup = [row.always_on for row in rows if row.always_on >= 0]
    coordination = {
        name: path.stat().st_size if path.is_file() else 0
        for name, path in (
            ("Reviews.md", reviews_path(root)),
            ("Disputes.md", disputes_path(root)),
            ("Ledger.jsonl", root / F_LEDGER),
            ("Inbox.md", agent_dir(root, "ceo") / F_INBOX),
        )
    }
    return {
        "instances": len(rows),
        "startup_bytes": sum(startup),
        "lane_bytes": f"{min(startup)}..{max(startup)}" if startup else "-",
        "coordination_bytes": sum(coordination.values()),
        "coordination": coordination,
        "baseline": read_baseline(root),
    }


def snapshot(root: Path, repo: Path) -> dict:
    counts = ledger_counts(root)
    edges = []
    for edge in EDGES:
        live = edge.probe(root)
        edges.append(
            {
                "id": edge.id,
                "from": edge.src,
                "to": edge.dst,
                "fires_when": edge.fires,
                "reads": list(edge.reads),
                "taken": sum(counts.get(action, 0) for action in edge.actions),
                "now": live.units,
                "detail": live.detail,
            }
        )
    length, path = longest_chain(root)
    return {
        "nodes": sorted({node for edge in EDGES for node in (edge.src, edge.dst)}),
        "instances": known_instances(root),
        "edges": edges,
        "conditional_edges": len(EDGES),
        "chain": {"length": length, "path": path},
        "cut": sum(counts.values()),
        "cost": cost(root, repo),
    }


def workers(root: Path) -> list[str]:
    """The instances that do or verify the work; the CEO is the user interface."""
    return [name for name in known_instances(root) if resolve_role(name) != "ceo"]


def findings(root: Path, repo: Path) -> list[str]:
    """Every way this routing graph is a chain, a dashboard or an unpriced bill."""
    out: list[str] = []
    for edge in EDGES:
        for source in edge.reads:
            if source not in STATE_SOURCES:
                out.append(
                    f"C-GRAPH-STATE {edge.id} fires on {source}, which no record layer "
                    "parses: the edge reads nothing and can never be verified"
                )
    lanes = workers(root)
    queues = load_task_queues(root)
    for seat in list_roles(root):
        members = instances_of(root, seat)
        if len(members) > 1 and not queues.get(norm_role(seat)):
            out.append(
                f"C-GRAPH-CHAFF {seat} has {len(members)} lanes ({', '.join(members)}) and its "
                "queue holds no task: the extra seat cannot change what runs next"
            )
    length, path = longest_chain(root)
    open_count = len(_open_tasks(root))
    if len(lanes) > 1 and length >= 3 and length == open_count:
        out.append(
            f"C-GRAPH-CHAIN {open_count} open task(s) form one serial dependency path "
            f"({path}) while {len(lanes)} working lane(s) are staffed: the roster is a "
            "chain, and the extra lanes cannot run anything in parallel"
        )
    for problem in _cycles(root):
        out.append(f"C-GRAPH-EXIT {problem}: a loop with no exit")
    for role, task in _open_tasks(root):
        if _fails(task) >= REVIEW_FAIL_LIMIT:
            tid = str(task.get("id") or "").upper()
            if tid not in _disputed(root):
                out.append(
                    f"C-GRAPH-EXIT {role}:{tid} failed review {_fails(task)} times with no "
                    "open dispute: the rework cycle has no exit"
                )
    if len(lanes) > 1 and read_baseline(root) is None:
        priced = cost(root, repo)
        out.append(
            f"C-GRAPH-PRICE {len(lanes)} working lane(s) read {priced['startup_bytes']} B of "
            f"startup context plus {priced['coordination_bytes']} B of coordination records, "
            "and no single-agent baseline is recorded: the extra spend is UNVERIFIED"
        )
    return out


def _cycles(root: Path) -> list[str]:
    edges = _open_edges(root)
    found: list[str] = []
    walked: set[tuple[str, str]] = set()

    def walk(node: tuple[str, str], stack: tuple) -> None:
        if node in stack:
            loop = stack[stack.index(node) :] + (node,)
            found.append("dependency cycle: " + " -> ".join(f"{role}:{tid}" for role, tid in loop))
            return
        if node in walked:
            return
        for nxt in edges.get(node, []):
            walk(nxt, (*stack, node))
        walked.add(node)

    for node in edges:
        walk(node, ())
    return list(dict.fromkeys(found))


def render(data: dict, baseline: dict | None) -> str:
    instances = data["instances"]
    lines = [
        f"# routing graph: {data['conditional_edges']} conditional edges, "
        f"{len(data['nodes'])} nodes, {len(instances)} staffed instance(s)",
        f"# cut: {data['cut']} ledger record(s)",
        "",
        f"{'edge':4} {'from -> to':20} {'taken':>5} {'now':>4}  fires when (state it reads)",
    ]
    for edge in data["edges"]:
        lines.append(
            f"{edge['id']:4} {edge['from'] + ' -> ' + edge['to']:20} "
            f"{edge['taken']:5} {edge['now']:4}  {edge['fires_when']} "
            f"[{', '.join(edge['reads'])}]"
        )
    firing = [edge for edge in data["edges"] if edge["now"]]
    lines.append("")
    if firing:
        for edge in firing:
            lines.append(
                f"# next: {edge['id']} {edge['from']} -> {edge['to']} fires on "
                f"{edge['now']} ({edge['detail']})"
            )
    else:
        lines.append("# next: no edge fires; the state holds nothing to route")
    exit_edge = next(edge for edge in data["edges"] if edge["to"] == "stop")
    lines.append(f"# exit: {'open' if exit_edge['now'] else 'shut'} ({exit_edge['detail']})")
    cost_block = data["cost"]
    lines.extend(
        [
            "",
            f"# cost: {cost_block['instances']} instance(s) read "
            f"{cost_block['startup_bytes']} B of startup context "
            f"({cost_block['lane_bytes']} B each) + {cost_block['coordination_bytes']} B of "
            "coordination records: "
            + ", ".join(f"{name} {size} B" for name, size in cost_block["coordination"].items()),
        ]
    )
    if baseline is None:
        lines.append(
            "# baseline: UNRECORDED - the spend above is measured, the claim that it beats "
            "one agent is not: `teamwork.py graph baseline --record '<cmd -> result>'`"
        )
    else:
        lines.append(
            f"# baseline: {baseline.get('tokens', 0)} token(s), recorded "
            f"{baseline.get('at', '?')} by {baseline.get('by', '?')}: {baseline.get('record', '')}"
        )
    lines.append(
        f"# chain: longest open dependency path is {data['chain']['length']} task(s) "
        f"({data['chain']['path']})"
    )
    return "\n".join(lines)


def cmd_graph(args) -> int:
    root = project_root(args)
    repo = repo_root(args)
    if not (root / DIR_ROLES).is_dir() and not (root / DIR_AGENTS).is_dir():
        die(
            f"no team workspace at {root}: `graph` reads the routing state of a team, "
            "so it needs `teamwork.py init` first."
        )
    command = getattr(args, "graph_cmd", "") or "show"
    if command == "baseline":
        record = getattr(args, "record", "").strip()
        if "->" not in record:
            die(
                "graph baseline needs --record '<command> -> <observed result>': a baseline "
                "without the command and what it produced is not evidence, and a roster "
                "priced against a guess is unpriced."
            )
        path = write_baseline(root, args.record, args.by, args.tokens)
        from .engine import ledger_append

        ledger_append(
            root,
            "graph.baseline",
            actor=args.by or "ceo",
            target=str(path.relative_to(root)),
            detail=f"{args.tokens} token(s): {args.record}",
        )
        print(f"# baseline recorded at {path}")
        print(f"# {args.tokens} token(s) by {args.by or '-'}: {args.record}")
        return 0
    data = snapshot(root, repo)
    if command == "audit":
        problems = findings(root, repo)
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {"command": "graph.audit", "clean": not problems, "problems": problems},
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"# routing graph audit for {root}")
            if not problems:
                print(f"# clean: {len(EDGES)} edges, {len(data['instances'])} instance(s)")
            for problem in problems:
                print(f"- {problem}")
            print(f"# problems found: {len(problems)}")
        return 1 if problems else 0
    if getattr(args, "json", False):
        print(json.dumps({"command": "graph", **data}, indent=2, sort_keys=True))
        return 0
    print(render(data, data["cost"]["baseline"]))
    return 0


def add_parsers(sub, common) -> None:
    """Register the ``graph`` command group on the shared argparse tree."""
    group = sub.add_parser(
        "graph",
        parents=[common],
        help="the routing graph: every conditional edge, the state it reads and when to stop",
    )
    group.set_defaults(func=cmd_graph, graph_cmd="show")
    group.add_argument("--json", action="store_true", help="machine-readable output")
    gsub = group.add_subparsers(dest="graph_cmd")

    parser = gsub.add_parser(
        "show", parents=[common], help="print the edges with their live state reading"
    )
    parser.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output"
    )
    parser.set_defaults(func=cmd_graph)

    parser = gsub.add_parser(
        "audit",
        parents=[common],
        help="exit 1 when the roster is a chain, a dashboard, an unexited loop or unpriced",
    )
    parser.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output"
    )
    parser.set_defaults(func=cmd_graph)

    parser = gsub.add_parser(
        "baseline",
        parents=[common],
        help="record what one agent doing this work cost, so coordination can be priced",
    )
    parser.add_argument("--record", default="", help="the command and its observed result")
    parser.add_argument("--tokens", type=int, default=0, help="the baseline's token count")
    parser.add_argument("--by", default="", help="who measured it")
    parser.set_defaults(func=cmd_graph)
