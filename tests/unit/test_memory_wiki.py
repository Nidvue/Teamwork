"""Unit tests for the capped wiki: page format, caps, prune and the search hit (Memory.md 15.5).

A page is derived state: one subject, at least two source records, every fact line
carrying the pointer of the record it came from, one page under ``WIKI_BUDGET_BYTES``
and at most ``WIKI_MAX_PAGES`` pages. The dream pass adds, edits and prunes pages;
``memory search`` ranks a page's fact lines with the same 4.1 score and pays for
them out of the same read budget as the records.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from teamwork import config, memorypack, records, wiki

NOW = datetime.datetime(2026, 11, 11, 12, 0, 0)


def wiki_facts(root: Path) -> list[dict]:
    return [fact for stored in wiki.pages(root) for fact in wiki.fact_entries(stored)]


def team(tmp_path: Path) -> Path:
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    return root


def add_knowledge(root: Path, topic: str, statement: str, *, status: str = "active") -> str:
    path = root / config.F_KNOWLEDGE
    items = records.parse_knowledge(path)
    item = records.new_knowledge(
        topic,
        statement,
        "https://example.com/lock-steal - accessed 2026-11-11",
        "Dev",
        "developer",
        importance=3,
    )
    item["id"] = records.next_id(items, "K-")
    item["status"] = status
    item["created"] = "2026-11-07"
    item["updated"] = "2026-11-07"
    items.append(item)
    records.write_knowledge(path, items)
    return records.parse_knowledge(path)[-1]["id"]


def page(root: Path, subject: str, sources: list[str], facts: list[tuple[str, str]]) -> dict:
    return wiki.write_page(root, subject, sources, facts, "2026-11-11")


def test_a_page_is_written_at_its_path_in_the_frozen_format(tmp_path: Path) -> None:
    root = team(tmp_path)

    written = page(
        root,
        "Lock Steal",
        ["K-0001", "K-0002"],
        [("claim the lock before re-reading", "K-0001")],
    )

    path = root / "Wiki" / "lock-steal.md"
    assert written["id"] == "W-0001"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# W-0001 - Lock Steal\n")
    assert "- sources: K-0001, K-0002" in text
    assert "## Facts" in text
    assert "- claim the lock before re-reading -> K-0001" in text
    assert len(text.encode("utf-8")) <= config.WIKI_BUDGET_BYTES


def test_a_second_page_gets_the_next_id_and_an_edit_keeps_it(tmp_path: Path) -> None:
    root = team(tmp_path)
    page(root, "first subject", ["K-0001", "K-0002"], [("a fact", "K-0001")])
    second = page(root, "second subject", ["K-0003", "K-0004"], [("another fact", "K-0003")])
    edited = page(root, "second subject", ["K-0003", "K-0005"], [("changed fact", "K-0005")])

    assert second["id"] == "W-0002"
    assert edited["id"] == "W-0002"
    assert "changed fact" in (root / "Wiki" / "second-subject.md").read_text(encoding="utf-8")


def test_a_page_needs_two_source_records(tmp_path: Path) -> None:
    root = team(tmp_path)

    with pytest.raises(ValueError, match="source records"):
        page(root, "one record", ["K-0001"], [("a fact", "K-0001")])


def test_a_page_over_the_byte_budget_is_refused(tmp_path: Path) -> None:
    root = team(tmp_path)
    facts = [(f"fact {index} " + "x" * 200, f"K-{index:04d}") for index in range(1, 10)]

    with pytest.raises(ValueError, match="WIKI_BUDGET_BYTES"):
        page(root, "too long", ["K-0001", "K-0002"], facts)


def test_a_new_page_is_refused_at_the_page_cap(tmp_path: Path, monkeypatch) -> None:
    root = team(tmp_path)
    monkeypatch.setattr(wiki, "WIKI_MAX_PAGES", 1)
    page(root, "first subject", ["K-0001", "K-0002"], [("a fact", "K-0001")])

    with pytest.raises(ValueError, match="WIKI_MAX_PAGES"):
        page(root, "second subject", ["K-0003", "K-0004"], [("another fact", "K-0003")])


def test_dream_adds_a_page_from_two_records_and_prunes_it_when_both_are_archived(
    tmp_path: Path,
) -> None:
    root = team(tmp_path)
    first = add_knowledge(root, "lock-steal", "claim the lock then re-read the body")
    second = add_knowledge(root, "lock-steal", "claim the lock, then re-read the body twice")
    entries = memorypack.collect(root, "Developer")

    proposals = wiki.dream(root, entries, NOW)
    written = wiki.apply(root, proposals, "Developer")

    assert written["written"] == 1
    stored = wiki.pages(root)
    assert len(stored) == 1
    assert stored[0]["sources"] == sorted([first, second])
    assert len(stored[0]["facts"]) == 2

    archived = root / config.F_KNOWLEDGE
    items = records.parse_knowledge(archived)
    for item in items:
        item["status"] = "archived"
    records.write_knowledge(archived, items)
    dead = memorypack.collect(root, "Developer")

    pruning = wiki.dream(root, dead, NOW)
    assert [item["id"] for item in pruning["prune"]] == [stored[0]["id"]]
    counts = wiki.apply(root, pruning, "Developer")

    assert counts["pruned"] == 1
    stubbed = (root / "Wiki" / f"{stored[0]['slug']}.md").read_text(encoding="utf-8")
    assert "every source record is superseded, archived or drifted -> wiki.prune" in stubbed
    events = (root / config.F_LEDGER).read_text(encoding="utf-8")
    assert "wiki.prune" in events


def test_memory_search_prints_a_page_hit_inside_the_shared_budget(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body")
    page(
        root,
        "lock-steal",
        ["K-0001", "K-0002"],
        [("claim the lock then re-read the body before unlinking", "K-0001")],
    )
    entries = memorypack.collect(root, "Developer")

    text = memorypack.render_search(entries, "lock", NOW, page_facts=wiki_facts(root))

    assert "W-0001 -> Wiki/lock-steal.md#L" in text
    assert len(text.encode("utf-8")) <= memorypack.SEARCH_BUDGET_BYTES

    squeezed = memorypack.render_search(entries, "lock", NOW, budget=1, page_facts=wiki_facts(root))
    assert "W-0001" not in squeezed


def test_a_page_hit_competes_for_the_same_limit_as_a_record(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body")
    page(
        root,
        "lock-steal",
        ["K-0001", "K-0002"],
        [("claim the lock then re-read the body before unlinking", "K-0001")],
    )
    entries = memorypack.collect(root, "Developer")

    text = memorypack.render_search(entries, "lock", NOW, limit=1, page_facts=wiki_facts(root))

    assert text.count("- ") == 1
