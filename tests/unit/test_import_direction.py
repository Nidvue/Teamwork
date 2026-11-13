"""Unit: the module-scope import graph stays acyclic.

Layer ``system``, area ``imports``. ``docs/Team/Architecture.md`` 3 states the
dependency direction ``config <- io/names <- layout <- records`` with ``engine``
on top. The direction is only real if the *import-time* graph is acyclic: a
module-scope import of a module that already imports you back is an
``ImportError`` for whoever imports first, which is the failure an agent copying
the neighbouring module reproduces.

The check reads the AST, not the source text, and it is proved on a synthetic
cycle before it is trusted on the tree - a rule that cannot fail proves nothing.

Owner: architect. Layer: system. Area: imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "teamwork"


def module_scope_imports(tree: ast.Module, own: str) -> set:
    """The package-local modules this file imports at import time, not in a function."""
    found = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = own.split(".")[: -node.level] if own else []
                base = ".".join([*parts, base]) if base else ".".join(parts)
            for alias in node.names:
                found.add(f"{base}.{alias.name}" if base else alias.name)
            if base:
                found.add(base)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
    return {name for name in found if name.startswith("teamwork.") or "." not in name}


def module_graph(files: dict) -> dict:
    graph = {}
    for name, source in files.items():
        edges = module_scope_imports(ast.parse(source), f"teamwork.{name}")
        graph[name] = {edge.split(".")[1] for edge in edges if edge.startswith("teamwork.")}
        graph[name].discard(name)
    return graph


def cycles(graph: dict) -> list:
    """Every cycle reachable in the import graph, as sorted module paths."""
    found, state, stack = [], {}, []

    def walk(node: str) -> None:
        state[node] = "open"
        stack.append(node)
        for peer in sorted(graph.get(node, ())):
            if state.get(peer) == "open":
                found.append(tuple(stack[stack.index(peer) :] + [peer]))
            elif peer not in state:
                walk(peer)
        stack.pop()
        state[node] = "done"

    for node in sorted(graph):
        if node not in state:
            walk(node)
    return found


def package_sources() -> dict:
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(PACKAGE.glob("*.py"))}


def test_the_rule_catches_a_cycle_it_was_given() -> None:
    graph = module_graph(
        {
            "engine": "from . import lanes\n",
            "lanes": "from . import engine\n",
            "records": "from . import io\n",
            "io": "import os\n",
        }
    )
    assert graph["engine"] == {"lanes"}
    assert cycles(graph) == [("engine", "lanes", "engine")]


def test_the_rule_ignores_a_lazy_import() -> None:
    graph = module_graph({"engine": "def run():\n    from . import lanes\n    return lanes\n"})
    assert graph["engine"] == set()


def test_the_package_import_graph_is_acyclic() -> None:
    graph = module_graph(package_sources())
    assert cycles(graph) == []


def test_the_command_layer_imports_the_lane_runtime_lazily() -> None:
    """Architecture.md 3: ``lanes`` sits above ``engine``, so ``engine`` is the lazy side."""
    graph = module_graph(package_sources())
    assert "lanes" not in graph["engine"]
    assert "engine" in graph["lanes"]


def test_only_the_entry_points_import_the_command_layer_at_import_time() -> None:
    graph = module_graph(package_sources())
    importers = {name for name, edges in graph.items() if "engine" in edges}
    assert importers == {"cli", "lanes"}
