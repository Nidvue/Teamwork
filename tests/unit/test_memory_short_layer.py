"""Unit tests for the short layer: lane-exit capture and injection (Memory.md 15.1-15.2).

The short layer is the role's own working notes. Two writers, one file: the agent
through ``remember`` and the harness at lane exit. These cases pin the harness
entry's shape and provenance, the three cases that must write nothing (no
``LANE-RESULT`` line, a note the agent already wrote for that task, a second
reconcile of the same run), the empty store printing no heading, the 5-entry and
600-byte sub-caps with bodies clipped to 160 characters, determinism, that the
short block is paid for by the pack rather than added to it, and that ``load
--task`` and a lane packet both carry the block between the index and the pack.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from teamwork import config, engine, lanes, memorypack, records

NOW = datetime.datetime(2026, 11, 11, 12, 0, 0)


def team(tmp_path: Path) -> Path:
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    return root


def run(task: str = "T-0001", verdict: str = "ok", note: str = "self-checked and PR open") -> dict:
    return {
        "task": task,
        "role": "Developer",
        "agent": "Developer-1",
        "result": {"verdict": verdict, "note": note},
    }


def add_note(root: Path, body: str, *, src: str = "", uses: int = 0, key: str = "note") -> str:
    path = root / "Roles" / "Developer" / config.F_SHORT
    items = records.parse_memory(path)
    entry = records.new_entry(body, key, 2, by="Developer-1", src=src)
    entry["uses"] = uses
    items.append(entry)
    records.write_memory(path, items, config.F_SHORT, "Developer")
    return records.parse_memory(path)[-1]["id"]


def store(root: Path) -> list[dict]:
    return records.parse_memory(root / "Roles" / "Developer" / config.F_SHORT)


def test_capture_writes_one_note_with_its_provenance(tmp_path: Path) -> None:
    root = team(tmp_path)
    entry = lanes.capture_short_layer(root, run())
    written = store(root)
    assert len(written) == 1
    assert entry["id"] == written[0]["id"]
    assert written[0]["key"] == "lane:T-0001"
    assert written[0]["src"] == "T-0001"
    assert written[0]["by"] == "Developer-1"
    assert written[0]["importance"] == 2
    assert written[0]["body"] == "T-0001 ok: self-checked and PR open"
    assert written[0]["rev"] == ""


def test_capture_is_idempotent_for_one_run(tmp_path: Path) -> None:
    root = team(tmp_path)
    lanes.capture_short_layer(root, run())
    assert lanes.capture_short_layer(root, run()) == {}
    assert len(store(root)) == 1


def test_capture_skips_a_lane_without_a_lane_result(tmp_path: Path) -> None:
    root = team(tmp_path)
    assert lanes.capture_short_layer(root, run(verdict="")) == {}
    assert store(root) == []


def test_capture_does_not_echo_the_agents_own_note(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_note(root, "I proved the boundary myself", src="T-0001")
    assert lanes.capture_short_layer(root, run()) == {}
    assert len(store(root)) == 1


def test_short_block_is_empty_and_headingless_on_an_empty_store(tmp_path: Path) -> None:
    root = team(tmp_path)
    assert memorypack.short_block(root, "Developer", "T-0001", now=NOW) == ""
    assert memorypack.short_bytes(root, "Developer", "T-0001", now=NOW) == 0


def test_short_block_clips_every_body_to_160_chars(tmp_path: Path) -> None:
    root = team(tmp_path)
    for index in range(7):
        add_note(root, f"note {index} " + "x" * 300)
    block = memorypack.short_block(root, "Developer", "note", now=NOW)
    lines = block.splitlines()
    assert lines[0] == memorypack.SHORT_HEADING
    assert 1 <= len(lines) - 1 <= memorypack.SHORT_INJECT_ENTRIES
    for line in lines[1:]:
        body = line.split("] ", 1)[1].rsplit(" (uses ", 1)[0]
        assert len(body) == memorypack.SHORT_CLIP
        assert line.endswith("(uses 0)")
    assert len(block.encode("utf-8")) + 1 <= memorypack.SHORT_INJECT_BYTES


def test_short_block_caps_at_five_entries(tmp_path: Path) -> None:
    root = team(tmp_path)
    for index in range(7):
        add_note(root, f"note {index}")
    lines = memorypack.short_block(root, "Developer", "note", now=NOW).splitlines()
    assert len(lines) - 1 == memorypack.SHORT_INJECT_ENTRIES


def test_short_block_is_deterministic(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_note(root, "the gate runs in the lane worktree")
    add_note(root, "a second note about the ledger")
    first = memorypack.short_block(root, "Developer", "gate", now=NOW)
    assert memorypack.short_block(root, "Developer", "gate", now=NOW) == first
    assert len(store(root)) == 2


def test_injected_budget_pays_for_the_short_block(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_note(root, "the gate runs in the lane worktree")
    short = memorypack.short_bytes(root, "Developer", "T-0001", now=NOW)
    spent = memorypack.index_bytes(root, "Developer", "T-0001", now=NOW)
    assert short > 0
    assert memorypack.injected_budget(root, "Developer", "T-0001", now=NOW) == (
        memorypack.PACK_BUDGET_BYTES - spent - short
    )
    empty = team(tmp_path / "empty")
    assert memorypack.injected_budget(empty, "Developer", "T-0001", now=NOW) == (
        memorypack.PACK_BUDGET_BYTES - memorypack.index_bytes(empty, "Developer", "T-0001", now=NOW)
    )


def test_load_prints_index_then_short_then_pack(cli, project, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    capsys.readouterr()
    assert (
        cli("--project", project, "remember", "Developer-1", "the gate runs in the lane tree") == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1", "--task", "T-0001") == 0
    out = capsys.readouterr().out
    assert out.count(memorypack.SHORT_HEADING) == 1
    assert out.index("# memory index: ") < out.index(memorypack.SHORT_HEADING)
    assert out.index(memorypack.SHORT_HEADING) < out.index("# memory pack for")


def test_lane_packet_carries_the_short_block(cli, project) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    add_note(root, "the gate runs in the lane worktree")
    packet = lanes.build_packet(
        root,
        [lanes.Assignment("Developer-1", "Developer", "T-0001", "a task")],
        "L-0001",
        1,
        2,
        50,
        40,
        "pi",
        "",
        "default",
    )
    assert packet.count(memorypack.SHORT_HEADING) == 1
    assert packet.index("# memory index: ") < packet.index(memorypack.SHORT_HEADING)
    assert packet.index(memorypack.SHORT_HEADING) < packet.index("# pack: ")
