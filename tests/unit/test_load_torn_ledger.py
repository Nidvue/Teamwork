"""`load` settles a torn ledger tail before it renders, not after (T-0065).

The defect: `load` renders the packet and only then appends (consolidation,
`memory.pack`). A crash-torn ledger tail made that late append refuse, so the
reader got the packet and exit 1 from the same command. These tests pin the order:
the trail is healed or the command refuses before the first byte of the packet.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def setup(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    engine.ledger_append(root, "audit.test", "ceo", "seed", "a first record")
    engine.ledger_append(root, "audit.test", "ceo", "seed", "a second record")
    return root


def torn_tail(root: Path) -> None:
    with (root / engine.F_LEDGER).open("a", encoding="utf-8") as fh:
        fh.write('{"torn": ')


def head_ahead_of_the_file(root: Path) -> None:
    """The crash shape: the head cache names a record the torn write never landed."""
    records = engine._ledger_valid(engine.ledger_read(root))
    engine.atomic_write(
        engine.ledger_head_path(root),
        json.dumps({"n": len(records) + 1, "hash": "0" * 64}) + "\n",
    )


def load(cli, project: Path) -> int:
    return cli("--project", project, "load", "developer-1", "--task", "T-0001")


def test_a_torn_tail_is_dropped_before_the_packet_is_rendered(cli, project: Path, capsys) -> None:
    root = setup(cli, project)
    torn_tail(root)

    assert load(cli, project) == 0

    out = capsys.readouterr()
    assert "# memory pack for T-0001" in out.out
    assert "torn trailing ledger line" in out.err
    assert engine.ledger_verify(root) == []
    assert not [r for r in engine.ledger_read(root) if r.get("action") == "corrupt"]


def test_a_torn_tail_the_head_cache_already_counted_exits_zero(cli, project: Path, capsys) -> None:
    root = setup(cli, project)
    torn_tail(root)
    head_ahead_of_the_file(root)

    assert load(cli, project) == 0

    out = capsys.readouterr()
    assert "# memory pack for T-0001" in out.out
    head = json.loads(engine.ledger_head_path(root).read_text(encoding="utf-8"))
    valid = engine._ledger_valid(engine.ledger_read(root))
    assert head == {"n": len(valid), "hash": valid[-1]["hash"]}
    assert engine.ledger_verify(root) == []


def test_a_second_load_on_the_healed_trail_is_quiet_and_stable(cli, project: Path, capsys) -> None:
    root = setup(cli, project)
    torn_tail(root)
    head_ahead_of_the_file(root)

    assert load(cli, project) == 0
    capsys.readouterr()
    assert load(cli, project) == 0

    out = capsys.readouterr()
    assert "torn trailing ledger line" not in out.err
    assert engine.ledger_verify(root) == []


def test_a_chain_broken_before_the_tail_refuses_before_rendering(
    cli, project: Path, capsys
) -> None:
    root = setup(cli, project)
    path = root / engine.F_LEDGER
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.insert(1, "[]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert load(cli, project) == 1

    out = capsys.readouterr()
    assert "# memory pack" not in out.out
    assert "nothing was rendered" in out.err
