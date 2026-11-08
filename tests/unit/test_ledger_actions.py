"""The declared ledger vocabulary must match the actions the code writes.

``engine.LEDGER_ACTIONS`` is the closed set ``ledger_append`` validates against.
These tests derive the written set from the call sites with the AST, so a new
literal action cannot land undeclared and a declared action cannot go unused.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from teamwork import engine

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "teamwork"


def _action_literals(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _action_literals(node.body) + _action_literals(node.orelse)
    raise AssertionError(
        f"ledger_append action is not a literal, so it cannot be declared: {ast.unparse(node)}"
    )


def _written_actions() -> dict[str, list[str]]:
    written: dict[str, list[str]] = {}
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "ledger_append" or len(node.args) < 2:
                continue
            for action in _action_literals(node.args[1]):
                written.setdefault(action, []).append(f"{path.name}:{node.lineno}")
    return written


def test_written_actions_are_all_declared() -> None:
    written = _written_actions()
    assert written
    undeclared = sorted(set(written) - set(engine.LEDGER_ACTIONS))
    assert undeclared == [], {action: written[action] for action in undeclared}


def test_declared_actions_are_all_written() -> None:
    written = set(_written_actions())
    unused = sorted(set(engine.LEDGER_ACTIONS) - written)
    assert unused == []


def test_declared_actions_are_unique_sorted_and_lowercase() -> None:
    actions = engine.LEDGER_ACTIONS
    assert len(actions) == len(set(actions))
    assert list(actions) == sorted(actions)
    assert [a for a in actions if a != a.strip().lower() or not a] == []


def test_ledger_append_warns_once_on_an_undeclared_action(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    engine.UNDECLARED_ACTION_WARNED.discard("undeclared.probe")
    engine.ledger_append(tmp_path, "undeclared.probe", "ceo", "x", "first")
    engine.ledger_append(tmp_path, "undeclared.probe", "ceo", "x", "second")
    err = capsys.readouterr().err
    assert err.count("undeclared ledger action 'undeclared.probe'") == 1
    assert [r["action"] for r in engine.ledger_read(tmp_path)] == [
        "undeclared.probe",
        "undeclared.probe",
    ]


def test_declared_action_does_not_warn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    engine.ledger_append(tmp_path, "task.add", "ceo", "T-0001", "declared")
    assert capsys.readouterr().err == ""
