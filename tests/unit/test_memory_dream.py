"""Unit tests for the M23 maintenance pass: the 15.3 promotion table and the 15.4 cadence.

The table under test is frozen in ``docs/Team/Memory.md`` 15.3: staleness is age
only, use alone decides promotion, importance only splits the overflow, a pinned
note never leaves, a drifted note is never promoted, and a promotion deletes
nothing. The cadence cases pin that the pass stops at its budget and names what it
deferred, and that a second ``--apply`` is 0 actions with no new ledger event.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from teamwork import config, engine, memorypack, records

NOW = datetime.datetime(2026, 11, 11, 12, 0, 0)
ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def team(tmp_path: Path) -> Path:
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    return root


def add_short(
    root: Path,
    body: str,
    *,
    days_old: int = 10,
    uses: int = 0,
    importance: int = 2,
    pinned: bool = False,
    evidence: str = "",
) -> dict:
    path = root / "Roles" / "Developer" / config.F_SHORT
    items = records.parse_memory(path)
    entry = records.new_entry(body, body.split()[0], importance, pinned=pinned, by="Developer-1")
    stamp = (datetime.date.today() - datetime.timedelta(days=days_old)).isoformat()
    entry["created"] = entry["last_used"] = stamp
    entry["uses"] = uses
    if evidence:
        entry["evidence"] = evidence
    items.append(entry)
    records.write_memory(path, items, config.F_SHORT, "Developer")
    return records.parse_memory(path)[-1]


def add_long(root: Path, body: str, *, days_old: int = 200, uses: int = 0) -> dict:
    path = root / "Roles" / "Developer" / config.F_LONG
    items = records.parse_memory(path)
    entry = records.new_entry(body, body.split()[0], 2, by="Developer-1")
    stamp = (datetime.date.today() - datetime.timedelta(days=days_old)).isoformat()
    entry["created"] = entry["last_used"] = stamp
    entry["uses"] = uses
    items.append(entry)
    records.write_memory(path, items, config.F_LONG, "Developer")
    return records.parse_memory(path)[-1]


def store(root: Path, name: str) -> list[dict]:
    return records.parse_memory(root / "Roles" / "Developer" / name)


def consolidate(root: Path) -> dict:
    return engine.consolidate_agent(root, "Developer", quiet=True)


def test_a_stale_used_note_is_promoted_and_a_stale_unused_note_is_archived(
    tmp_path: Path,
) -> None:
    root = team(tmp_path)
    used = add_short(root, "the pen is free after release", uses=2)
    unused = add_short(root, "nobody recalled this", uses=1)

    report = consolidate(root)

    assert report["promoted"] == 1
    assert report["dropped"] == 1
    assert [entry["id"] for entry in store(root, config.F_LONG)] == [used["id"]]
    assert [entry["body"] for entry in store(root, config.F_MEM_ARCHIVE)] == [unused["body"]]
    assert store(root, config.F_SHORT) == []


def test_importance_decides_nothing_about_survival(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_short(root, "an author liked this note a lot", uses=0, importance=5)

    report = consolidate(root)

    assert report["promoted"] == 0
    assert report["dropped"] == 1
    assert store(root, config.F_LONG) == []


def test_a_fresh_note_stays_short_however_often_it_was_used(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_short(root, "recalled today and yesterday", days_old=1, uses=9)

    report = consolidate(root)

    assert report["promoted"] == 0
    assert report["dropped"] == 0
    assert len(store(root, config.F_SHORT)) == 1


def test_a_pinned_note_never_leaves_the_short_layer(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_short(root, "the rule this role must never re-learn", days_old=400, pinned=True)

    report = consolidate(root)

    assert report["promoted"] == 0
    assert report["dropped"] == 0
    assert len(store(root, config.F_SHORT)) == 1


def test_an_unused_long_note_is_demoted_to_the_archive_with_its_statement_intact(
    tmp_path: Path,
) -> None:
    root = team(tmp_path)
    add_long(root, "long-term note nobody used for a season", uses=0)

    report = consolidate(root)

    assert report["demoted"] == 1
    assert store(root, config.F_LONG) == []
    archived = store(root, config.F_MEM_ARCHIVE)
    assert [entry["body"] for entry in archived] == ["long-term note nobody used for a season"]


def test_a_used_long_note_is_not_demoted(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_long(root, "long-term note the role keeps recalling", uses=4)

    assert consolidate(root)["demoted"] == 0
    assert len(store(root, config.F_LONG)) == 1


def test_a_drifted_note_is_never_promoted_and_the_pass_reports_it(
    tmp_path: Path, monkeypatch
) -> None:
    root = team(tmp_path)
    note = add_short(
        root,
        "a note whose evidence no longer resolves",
        uses=5,
        evidence="docs/Team/Gone.md:12 @abc1234 -> 3 passed",
    )
    drifting = [dict(entry) for entry in store(root, config.F_SHORT)]
    drifting[0]["evidence"] = "docs/Team/Gone.md:12 @abc1234 -> 3 passed"
    monkeypatch.setattr(
        engine,
        "parse_memory",
        lambda path: (
            [dict(entry) for entry in drifting]
            if path.name == config.F_SHORT
            else records.parse_memory(path)
        ),
    )

    report = engine.consolidate_agent(root, "Developer", quiet=True, dry_run=True)

    assert report["drifted"] == 1
    assert report["promoted"] == 0
    assert note["id"] == drifting[0]["id"]


def test_the_dream_pass_stops_at_its_budget_and_names_what_it_deferred() -> None:
    entries = [
        memorypack_entry(f"K-000{index}", f"record {index} about the lock") for index in range(1, 5)
    ]

    proposals = memorypack.dream(entries, NOW, None, budget_seconds=1e-9)

    assert proposals["deferred"] == len(entries)
    assert proposals["duplicate"] == []
    assert proposals["stale"] == []
    assert proposals["drifted"] == []


def test_a_second_dream_apply_is_zero_actions_and_no_new_event(tmp_path: Path) -> None:
    root = team(tmp_path)
    knowledge = root / config.F_KNOWLEDGE
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", "2026-09-01")
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", "2026-10-01")

    entries = memorypack.collect(root, "Developer")
    proposals = memorypack.dream(entries, NOW)
    scope = memorypack.proposal_scope(entries)
    first = memorypack.apply_dream(root, proposals, "Developer", scope=scope)
    after_first = knowledge.read_text(encoding="utf-8")
    events = ledger_lines(root)

    second = memorypack.apply_dream(root, proposals, "Developer", scope=scope)

    assert first["duplicate"] == 1
    assert second["duplicate"] == 0
    assert second["stale"] == 0
    assert knowledge.read_text(encoding="utf-8") == after_first
    assert ledger_lines(root) == events


def memorypack_entry(record_id: str, statement: str) -> dict:
    return {
        "id": record_id,
        "kind": "knowledge",
        "store": "Knowledge.md",
        "title": "lock-steal",
        "statement": statement,
        "tags": "",
        "importance": 3,
        "uses": 0,
        "updated": "2026-11-07",
        "status": "active",
        "evidence": "pytest tests/unit/test_memory_dream.py @abc1234 -> 9 passed",
        "pointer": f"Knowledge.md#{record_id}",
    }


def add_knowledge(root: Path, topic: str, statement: str, updated: str) -> str:
    path = root / config.F_KNOWLEDGE
    items = records.parse_knowledge(path)
    item = records.new_knowledge(
        topic,
        statement,
        "pytest tests/unit/test_memory_dream.py @abc1234 -> 9 passed",
        "Dev",
        "developer",
        importance=3,
    )
    item["id"] = records.next_id(items, "K-")
    item["status"] = "active"
    item["created"] = updated
    item["updated"] = updated
    items.append(item)
    records.write_knowledge(path, items)
    return records.parse_knowledge(path)[-1]["id"]


def ledger_lines(root: Path) -> int:
    path = root / config.F_LEDGER
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0
