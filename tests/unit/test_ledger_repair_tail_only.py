"""`ledger repair` drops only a torn tail, never a record in the middle (T-0015).

Finding 9 of the M19 audit: the command is documented as a torn-tail repair but
dropped any unreadable line anywhere in the chain. A line that does not parse in
the middle of the chain is not a torn write - it is an altered or spliced file -
so the repair refuses and `ledger verify` keeps reporting it.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine


def _seeded(tmp_path: Path) -> Path:
    root = tmp_path / "team"
    root.mkdir(parents=True)
    for text in ("one", "two", "three"):
        engine.ledger_append(root, "task.add", "ceo", "T-0001", text)
    return root


def test_a_corrupted_middle_line_is_not_a_trailing_run(tmp_path: Path) -> None:
    root = _seeded(tmp_path)
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = "{broken"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert engine._trailing_run([2], total=3) == set()


def test_a_torn_last_line_is_a_trailing_run(tmp_path: Path) -> None:
    root = _seeded(tmp_path)
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[-1] = '{"partial":'
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert engine._trailing_run([3], total=3) == {3}


def test_repair_refuses_a_middle_corruption_and_leaves_the_file_alone(tmp_path: Path) -> None:
    root = _seeded(tmp_path)
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = "{broken"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    try:
        engine._ledger_repair_locked(
            type("A", (), {"reason": "probe", "force": "", "by": "ceo"})(), root, "CEO"
        )
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover
        raise AssertionError("repair accepted a middle corruption")
    assert path.read_text(encoding="utf-8") == before


def test_repair_drops_a_torn_tail(tmp_path: Path) -> None:
    root = _seeded(tmp_path)
    path = engine.ledger_path(root)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[-1] = '{"partial":'
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    engine._ledger_repair_locked(
        type("A", (), {"reason": "probe", "force": "", "by": "ceo"})(), root, "CEO"
    )
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 3
    assert records[-1]["action"] == "ledger.repair"
