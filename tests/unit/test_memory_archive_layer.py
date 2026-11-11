"""The archive layer of the memory read side: a demotion leaves a pointer (Memory.md 15.3).

A demoted record keeps its statement in ``Roles/<Role>/ArchivedMemory.md``, so
``recall`` and ``memory search`` must still find it there, by its archive pointer.
The other half of the contract is the negative: a parked record never spends an
injection budget, so the pack and the short block never carry it.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from teamwork import config, engine, memorypack, records

NOW = datetime.datetime(2026, 11, 11, 12, 0, 0)
BODY = "claim the lock then re-read the body"


def team(tmp_path: Path) -> Path:
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    return root


def add_archived(root: Path, body: str = BODY, key: str = "lock-steal") -> dict:
    path = root / "Roles" / "Developer" / config.F_MEM_ARCHIVE
    items = records.parse_memory(path)
    entry = records.new_entry(body, key, 2, by="Developer-1")
    entry["created"] = entry["last_used"] = "2026-01-01"
    items.append(entry)
    records.write_memory(path, items, config.F_MEM_ARCHIVE, "Developer")
    return records.parse_memory(path)[-1]


def test_an_archived_record_is_searchable_under_its_archive_pointer(tmp_path: Path) -> None:
    root = team(tmp_path)
    record = add_archived(root)

    entries = memorypack.archived_memories(root, "Developer")

    assert [entry["id"] for entry in entries] == [record["id"]]
    assert entries[0]["status"] == "archived"
    assert entries[0]["pointer"] == f"Roles/Developer/{config.F_MEM_ARCHIVE}#{record['id']}"
    assert entries[0]["statement"] == BODY


def test_an_empty_archive_is_an_empty_list_not_an_error(tmp_path: Path) -> None:
    assert memorypack.archived_memories(team(tmp_path), "Developer") == []


def test_memory_search_ranks_an_archived_record_with_its_pointer(
    cli, tmp_path: Path, monkeypatch, capsys
) -> None:
    root = team(tmp_path)
    record = add_archived(root)
    monkeypatch.setenv("TEAMWORK_ROOT", str(root))

    assert cli("memory", "search", "lock", "--role", "developer") == 0
    out = capsys.readouterr().out

    assert f"Roles/Developer/{config.F_MEM_ARCHIVE}#{record['id']}" in out
    assert BODY in out
    assert len(out.encode("utf-8")) <= memorypack.SEARCH_BUDGET_BYTES


def test_recall_resolves_an_archived_record_with_the_archive_layer(
    cli, tmp_path: Path, monkeypatch, capsys
) -> None:
    root = team(tmp_path)
    add_archived(root)
    monkeypatch.setenv("TEAMWORK_ROOT", str(root))

    assert cli("recall", "lock", "--agent", "developer", "--layer", "archive") == 0
    out = capsys.readouterr().out

    assert f"## developer / {config.F_MEM_ARCHIVE}" in out
    assert BODY in out


def test_the_default_and_all_layers_include_the_archive(
    cli, tmp_path: Path, monkeypatch, capsys
) -> None:
    root = team(tmp_path)
    add_archived(root)
    monkeypatch.setenv("TEAMWORK_ROOT", str(root))

    for argv in (("recall", "lock", "--agent", "developer"), ("recall", "lock", "--all")):
        assert cli(*argv) == 0
        assert BODY in capsys.readouterr().out, argv


def test_recall_over_an_empty_archive_says_no_memory_matched(
    cli, tmp_path: Path, monkeypatch, capsys
) -> None:
    root = team(tmp_path)
    monkeypatch.setenv("TEAMWORK_ROOT", str(root))

    assert cli("recall", "lock", "--agent", "developer", "--layer", "archive") == 0

    assert "no memory matched" in capsys.readouterr().out


def test_the_archive_layer_is_one_of_the_recall_layers() -> None:
    assert engine.RECALL_LAYERS["archive"] == config.F_MEM_ARCHIVE
    assert set(engine.RECALL_LAYERS) == {"short", "long", "archive"}


def test_a_parked_record_never_spends_an_injection_budget(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_archived(root)
    entries = memorypack.collect(root, "Developer") + memorypack.archived_memories(
        root, "Developer"
    )

    assert memorypack.pack(entries, "lock", memorypack.PACK_BUDGET_BYTES, NOW) == []
    assert (
        memorypack.short_entries(root, "Developer", "lock", memorypack.SHORT_INJECT_BYTES, NOW)
        == []
    )


def test_search_still_keeps_a_parked_knowledge_record_out() -> None:
    parked = memorypack._entry(
        record_id="K-0001",
        kind="knowledge",
        store=config.F_KNOWLEDGE,
        pointer="Knowledge.md#K-0001",
        title="lock",
        statement=BODY,
        tags="",
        importance=2,
        uses=0,
        updated="2026-01-01",
        status="archived",
        evidence="",
    )

    assert memorypack.searchable(parked) is False
