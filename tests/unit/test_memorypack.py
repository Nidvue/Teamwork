"""Unit tests for the agent-memory lifecycle: score, collect, pack, search, dream.

The contract under test is ``docs/Team/Memory.md`` 4.1-4.4 and 6 (AC-M20-1..
AC-M20-4). Every case here is a pure call on a hand-built store or on a hand-built
record list: no CLI, no git, no clock. The scoring cases pin the exact formula
term by term, the pack cases pin the byte accounting, and the dream cases pin
that a maintenance pass only ever parks a record - it never deletes one and never
rewrites a statement.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from teamwork import config, engine, memorypack, records

NOW = datetime.datetime(2026, 11, 7, 12, 0, 0)

SHAPE = (
    "id",
    "kind",
    "store",
    "title",
    "statement",
    "tags",
    "importance",
    "uses",
    "updated",
    "status",
    "evidence",
    "pointer",
)


def entry(**overrides) -> dict:
    base = {
        "id": "K-0001",
        "kind": "knowledge",
        "store": "Knowledge.md",
        "title": "lock-steal-protocol",
        "statement": "a waiter claims the lock before it re-reads the body",
        "tags": "",
        "importance": 3,
        "uses": 0,
        "updated": "2026-11-07",
        "status": "active",
        "evidence": "pytest tests/unit/test_io.py @abc1234 -> 12 passed",
        "pointer": "Knowledge.md#K-0001",
    }
    base.update(overrides)
    return base


def team(tmp_path: Path) -> Path:
    """A bare team tree: Roles/ exists, so role_dir and lessons_path resolve."""
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    (root / "Roles" / "Tester").mkdir(parents=True)
    return root


def add_lesson(
    root: Path,
    role: str,
    mistake: str,
    rule: str,
    *,
    status: str = "open",
    updated: str = "2026-11-07",
    evidence: str = "pytest tests/unit/test_memory.py @abc1234 -> 9 passed",
) -> str:
    path = root / "Roles" / role.capitalize() / config.F_LESSONS
    items = records.parse_lessons(path)
    item = records.new_lesson(role.lower(), mistake, "the guard was skipped", rule, evidence, "Dev")
    item["id"] = records.next_id(items, "L-")
    item["status"] = status
    item["created"] = updated
    item["updated"] = updated
    items.append(item)
    records.write_lessons(path, items)
    return records.parse_lessons(path)[-1]["id"]


def add_knowledge(
    root: Path,
    topic: str,
    statement: str,
    *,
    importance: int = 3,
    uses: int = 0,
    status: str = "active",
    updated: str = "2026-11-07",
    evidence: str = "pytest tests/unit/test_knowledge.py @abc1234 -> 15 passed",
) -> str:
    path = root / config.F_KNOWLEDGE
    items = records.parse_knowledge(path)
    item = records.new_knowledge(
        topic, statement, evidence, "Dev", "developer", importance=importance
    )
    item["id"] = records.next_id(items, "K-")
    item["status"] = status
    item["uses"] = uses
    item["created"] = updated
    item["updated"] = updated
    items.append(item)
    records.write_knowledge(path, items)
    return records.parse_knowledge(path)[-1]["id"]


def add_memory(root: Path, role: str, key: str, body: str) -> str:
    path = root / "Roles" / role.capitalize() / config.F_SHORT
    items = records.parse_memory(path)
    items.append(
        records.new_entry(body, key=key, importance=2, by="Dev", src="T-0001", rev="abc1234")
    )
    records.write_memory(path, items, config.F_SHORT, role.capitalize())
    return records.parse_memory(path)[-1]["id"]


def test_tokenize_lowercases_strips_punctuation_and_drops_stopwords() -> None:
    assert memorypack.tokenize("The LOCK is in the io.py path") == ["lock", "io", "py", "path"]


def test_tokenize_keeps_code_identifiers_and_underscores() -> None:
    assert memorypack.tokenize("_load_knowledge lock_steal v1.2") == [
        "_load_knowledge",
        "lock_steal",
        "v1",
        "2",
    ]


def test_tokenize_of_empty_text_is_empty() -> None:
    assert memorypack.tokenize("") == []
    assert memorypack.tokenize("the and for") == []


def test_score_is_the_frozen_formula() -> None:
    item = entry(statement="lock steal", importance=5, uses=5, updated="2026-11-07")
    assert memorypack.score(item, ["lock", "absent"], NOW) == pytest.approx(0.75)
    assert memorypack.score(item, ["lock", "absent"], NOW) == pytest.approx(
        0.50 * 0.5 + 0.20 * (5 / 5) + 0.15 * 1.0 + 0.15 * 1.0
    )


def test_score_with_no_matching_term_keeps_the_other_three_axes() -> None:
    item = entry(statement="lock steal", importance=5, uses=5)
    assert memorypack.score(item, ["unrelated"], NOW) == pytest.approx(0.5)


def test_score_of_an_empty_query_has_no_overlap_term() -> None:
    item = entry(importance=0, uses=0, updated="")
    assert memorypack.score(item, [], NOW) == pytest.approx(0.15 * 0.5)


def test_score_missing_date_uses_the_half_recency_and_missing_uses_are_zero() -> None:
    missing = entry(importance=0, uses=0, updated="")
    assert memorypack.score(missing, [], NOW) == pytest.approx(0.075)
    dated = entry(importance=0, uses=0, updated="", last_used="2026-11-07")
    assert memorypack.score(dated, [], NOW) == pytest.approx(0.15)
    assert memorypack.score(dated, ["absent"], NOW) == pytest.approx(0.15)


def test_score_recency_halves_every_thirty_days() -> None:
    fresh = entry(importance=0, uses=0, updated="2026-11-07")
    thirty = entry(importance=0, uses=0, updated="2026-10-08")
    ninety = entry(importance=0, uses=0, updated="2026-08-09")
    assert memorypack.score(fresh, [], NOW) == pytest.approx(0.15)
    assert memorypack.score(thirty, [], NOW) == pytest.approx(0.075)
    assert memorypack.score(ninety, [], NOW) == pytest.approx(0.15 * 0.125)


def test_score_caps_uses_at_five() -> None:
    five = memorypack.score(entry(importance=0, uses=5, updated=""), [], NOW)
    fifty = memorypack.score(entry(importance=0, uses=50, updated=""), [], NOW)
    assert five == pytest.approx(fifty)


def test_score_reads_tags_and_title_as_well_as_the_statement() -> None:
    tagged = entry(statement="nothing relevant", title="other", tags="lock,io")
    assert memorypack.score(tagged, ["lock"], NOW) > memorypack.score(
        entry(statement="nothing relevant", title="other", tags=""), ["lock"], NOW
    )


def test_rank_breaks_a_tie_by_ascending_id() -> None:
    first = entry(id="K-0002")
    second = entry(id="K-0010")
    assert [item["id"] for item in memorypack.rank([second, first], "lock", NOW)] == [
        "K-0002",
        "K-0010",
    ]


def test_pack_is_deterministic_over_two_calls() -> None:
    items = [entry(id="K-0002", statement="lock steal protocol"), entry(id="K-0001")]
    first = memorypack.pack(items, "lock", 4000, NOW)
    second = memorypack.pack(items, "lock", 4000, NOW)
    assert memorypack.rendered_bytes(first) == memorypack.rendered_bytes(second)
    assert memorypack.render_pack(first, memorypack.rendered_bytes(first), 4000) == (
        memorypack.render_pack(second, memorypack.rendered_bytes(second), 4000)
    )


def test_pack_with_an_empty_query_falls_back_to_importance_and_recency() -> None:
    old = entry(id="K-0001", statement="", importance=5, updated="2026-08-09")
    new = entry(id="K-0002", statement="", importance=1, updated="2026-11-07")
    assert [item["id"] for item in memorypack.pack([new, old], "", 4000, NOW)] == [
        "K-0001",
        "K-0002",
    ]
    assert [item["id"] for item in memorypack.pack([new, old], "", 4000, NOW)][0] == "K-0001"


def test_relevant_record_outranks_an_irrelevant_high_importance_one() -> None:
    relevant = entry(id="K-0001", title="lock steal", statement="the lock steal race", importance=1)
    irrelevant = entry(id="K-0002", title="ci note", statement="unrelated ci note", importance=5)
    assert [item["id"] for item in memorypack.pack([irrelevant, relevant], "lock", 4000, NOW)] == [
        "K-0001",
        "K-0002",
    ]


def test_pack_honours_the_exact_byte_budget() -> None:
    items = [
        entry(id=f"K-{index:04d}", statement=f"lock steal rule number {index} " + "x" * 120)
        for index in range(1, 11)
    ]
    budget = 400
    taken = memorypack.pack(items, "lock", budget, NOW)
    rendered = memorypack.render_pack(taken, memorypack.rendered_bytes(taken), budget)
    assert len(rendered.encode("utf-8")) <= budget
    ranked = memorypack.rank(items, "lock", NOW)
    next_item = ranked[len(taken)]
    over = taken + [next_item]
    assert (
        len(memorypack.render_pack(over, memorypack.rendered_bytes(over), budget).encode()) > budget
    )


def test_pack_returns_the_first_record_even_when_it_alone_exceeds_the_budget() -> None:
    huge = entry(id="K-0001", statement="lock " + "y" * 5000)
    taken = memorypack.pack([huge], "lock", 100, NOW)
    assert [item["id"] for item in taken] == ["K-0001"]
    assert memorypack.rendered_bytes(taken) > 100


def test_pack_never_spends_the_budget_on_a_parked_record() -> None:
    dropped = entry(id="K-0001", statement="lock steal rule", status="superseded")
    stale = entry(id="K-0002", statement="lock steal rule two", status="archived")
    live = entry(id="K-0003", statement="nothing about it")

    assert [item["id"] for item in memorypack.pack([dropped, stale], "lock", 4000, NOW)] == []
    assert [item["id"] for item in memorypack.pack([dropped, stale, live], "lock", 4000, NOW)] == [
        "K-0003"
    ]


def test_pack_of_an_empty_store_is_empty() -> None:
    assert memorypack.pack([], "lock", 4000, NOW) == []


def test_render_pack_is_one_pointer_line_per_record_and_a_byte_footer() -> None:
    items = [entry(id="K-0001", statement="lock steal rule", pointer="Knowledge.md#K-0001")]
    text = memorypack.render_pack(items, memorypack.rendered_bytes(items), 4000)
    assert text == (
        "- [K-0001] knowledge | lock steal rule | Knowledge.md#K-0001\n"
        "# pack: 1 record(s), 61 bytes (budget 4000)\n"
    )


def test_render_pack_clips_a_long_statement_to_two_hundred_characters() -> None:
    items = [entry(statement="z" * 500)]
    line = memorypack.render_record(items[0])
    assert line.split(" | ")[1] == "z" * 200


def test_render_pack_without_a_budget_says_so() -> None:
    assert "(budget n/a)" in memorypack.render_pack([], 0)


def test_collect_returns_one_uniform_shape_from_every_store(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_lesson(root, "developer", "committed on main", "branch start first")
    add_knowledge(root, "lock-steal", "claim then re-read")
    add_memory(root, "developer", "handoff", "the pen is free")

    items = memorypack.collect(root, "developer")
    assert [item["kind"] for item in items] == ["lesson", "knowledge", "memory"]
    for item in items:
        assert tuple(item.keys()) == SHAPE
    assert items[0]["title"] == "committed on main"
    assert items[0]["statement"] == "branch start first"
    assert items[1]["store"] == config.F_KNOWLEDGE
    assert items[2]["store"] == config.F_SHORT


def test_collect_keeps_a_parked_record_so_dream_can_see_it(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "old-note", "a fact", status="archived")
    add_lesson(root, "developer", "old mistake", "old rule", status="archived")

    by_kind = {item["kind"]: item for item in memorypack.collect(root, "developer")}
    assert by_kind["knowledge"]["status"] == "archived"
    assert by_kind["lesson"]["status"] == "archived"


def test_collect_pointer_locates_the_full_record(tmp_path: Path) -> None:
    root = team(tmp_path)
    lesson_id = add_lesson(root, "developer", "committed on main", "branch start first")
    pointer = memorypack.collect(root, "developer")[0]["pointer"]
    assert pointer == f"Roles/Developer/{config.F_LESSONS}#{lesson_id}"
    path, _, record_id = pointer.partition("#")
    assert (root / path).is_file()
    assert record_id in (root / path).read_text(encoding="utf-8")


def test_search_reaches_lessons_knowledge_and_memory(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_lesson(root, "developer", "the lock race", "hold the lock across the swap")
    add_knowledge(root, "lock-steal", "claim then re-read the body")
    add_memory(root, "developer", "lock note", "the lock is free after release")

    text = memorypack.render_search(memorypack.collect(root, "developer"), "lock", NOW)
    assert "L-0001" in text
    assert "K-0001" in text
    assert "M-0001" in text
    assert "# search: 3 of 3 match(es)" in text


def test_search_output_is_capped_at_its_budget(tmp_path: Path) -> None:
    root = team(tmp_path)
    for index in range(1, 13):
        add_knowledge(
            root, f"lock-topic-{index}", "lock steal rule " + "q" * 300, updated="2026-11-07"
        )
    text = memorypack.render_search(memorypack.collect(root, "developer"), "lock", NOW)
    assert len(text.encode("utf-8")) <= memorypack.SEARCH_BUDGET_BYTES
    assert " of 10 match(es)" in text


def test_search_reports_zero_matches(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim then re-read")
    text = memorypack.render_search(memorypack.collect(root, "developer"), "quantum", NOW)
    assert text == "# search: 0 of 0 match(es), 0 bytes\n"


def test_dream_finds_a_duplicate_and_keeps_the_newer_record() -> None:
    older = entry(
        id="K-0001",
        title="lock-steal",
        statement="claim the lock then re-read the body before unlinking",
        updated="2026-01-01",
    )
    newer = entry(
        id="K-0002",
        title="lock-steal",
        statement="claim the lock then re-read the body before unlinking it",
        updated="2026-06-01",
    )
    proposals = memorypack.dream([older, newer], NOW)
    keep, drop, overlap = proposals["duplicate"][0]
    assert (keep, drop) == ("K-0002", "K-0001")
    assert overlap >= memorypack.DUPLICATE_OVERLAP


def test_dream_finds_a_contradiction_and_names_both() -> None:
    left = entry(
        id="K-0001", title="pack-budget", statement="the pack budget is four thousand bytes"
    )
    right = entry(
        id="K-0002",
        title="pack-budget",
        statement="the pack budget is unbounded and grows with the store size",
    )
    proposals = memorypack.dream([left, right], NOW)
    assert proposals["contradiction"][0][:2] == ("K-0001", "K-0002")
    assert "pack-budget" in proposals["contradiction"][0][2]
    assert proposals["duplicate"] == []


def test_dream_ignores_a_parked_record_in_both_checks() -> None:
    left = entry(
        id="K-0001", title="pack-budget", statement="the pack budget is four thousand bytes"
    )
    right = entry(
        id="K-0002",
        title="pack-budget",
        statement="the pack budget is unbounded",
        status="superseded",
    )
    proposals = memorypack.dream([left, right], NOW)
    assert proposals["duplicate"] == []
    assert proposals["contradiction"] == []


def test_dream_finds_a_stale_record_and_respects_pinned() -> None:
    old = entry(id="K-0001", statement="unused fact", uses=0, updated="2026-05-01")
    used = entry(id="K-0002", statement="used fact", uses=3, updated="2026-05-01")
    recent = entry(id="K-0003", statement="new fact", uses=0, updated="2026-11-01")
    pinned = entry(id="K-0004", statement="pinned fact", uses=0, updated="2026-05-01", pinned=True)
    proposals = memorypack.dream([old, used, recent, pinned], NOW)
    assert proposals["stale"] == ["K-0001"]


def test_dream_reports_records_without_evidence() -> None:
    thin = entry(id="K-0001", evidence="see above")
    missing = entry(id="K-0002", evidence="")
    good = entry(id="K-0003", evidence="pytest @abc1234 -> 12 passed")
    assert memorypack.dream([thin, missing, good], NOW)["no_evidence"] == ["K-0001", "K-0002"]


def test_dream_is_independent_of_record_order() -> None:
    older = entry(
        id="K-0001",
        title="t",
        statement="claim the lock then re-read the body",
        updated="2026-01-01",
    )
    newer = entry(
        id="K-0002",
        title="t",
        statement="claim the lock then re-read the body",
        updated="2026-06-01",
    )
    assert memorypack.dream([older, newer], NOW) == memorypack.dream([newer, older], NOW)


def test_dream_covers_lessons_and_knowledge_but_not_memory() -> None:
    memory = entry(id="M-0001", kind="memory", title="t", statement="claim the lock then re-read")
    assert memorypack.dream([memory], NOW) == {
        "duplicate": [],
        "contradiction": [],
        "stale": [],
        "no_evidence": [],
    }


def test_proposal_scope_maps_each_id_to_its_file() -> None:
    items = [
        entry(id="K-0001", pointer="Knowledge.md#K-0001"),
        entry(id="L-0001", kind="lesson", pointer="Roles/Developer/Lessons.md#L-0001"),
    ]
    assert memorypack.proposal_scope(items) == {
        "K-0001": "Knowledge.md",
        "L-0001": "Roles/Developer/Lessons.md",
    }


def test_task_query_resolves_a_task_id_to_its_title(tmp_path: Path) -> None:
    root = team(tmp_path)
    queue = root / "Roles" / "Developer" / config.F_TASKS
    task = records.new_task("Fix the lock steal race in io.py", priority="P1")
    records.write_tasks(queue, [task], "developer")
    task_id = records.parse_tasks(queue)[0]["id"]

    assert memorypack.task_query(root, "developer", task_id) == "Fix the lock steal race in io.py"
    assert memorypack.task_query(root, "developer", "T-9999") == "T-9999"
    assert memorypack.task_query(root, "developer", "the lock race") == "the lock race"


def managed_status_lines(path: Path) -> list[str]:
    """The lines an `apply` pass is allowed to touch: `- status:` and `- superseded_by:`."""
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("- status:") or line.startswith("- superseded_by:")
    ]


def frozen_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line not in managed_status_lines(path)
    ]


def ledger_lines(root: Path) -> int:
    path = root / config.F_LEDGER
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0


def test_apply_dream_parks_duplicates_and_stale_without_deleting_or_rewriting(
    tmp_path: Path,
) -> None:
    root = team(tmp_path)
    older = add_knowledge(
        root,
        "lock-steal",
        "claim the lock then re-read the body before unlinking",
        updated="2026-09-01",
    )
    newer = add_knowledge(
        root,
        "lock-steal",
        "claim the lock then re-read the body before unlinking it",
        updated="2026-10-01",
    )
    stale = add_knowledge(root, "unused", "a fact nobody used", updated="2026-05-01")
    knowledge_file = root / config.F_KNOWLEDGE
    before_lines = frozen_lines(knowledge_file)
    before_records = records.parse_knowledge(knowledge_file)

    entries = memorypack.collect(root, "developer")
    proposals = memorypack.dream(entries, NOW)
    counts = memorypack.apply_dream(
        root, proposals, "Developer", scope=memorypack.proposal_scope(entries)
    )

    assert counts["duplicate"] == 1
    assert counts["stale"] == 1
    after = records.parse_knowledge(knowledge_file)
    assert [item["id"] for item in after] == [item["id"] for item in before_records]
    assert [item["statement"] for item in after] == [item["statement"] for item in before_records]
    assert frozen_lines(knowledge_file) == before_lines
    by_id = {item["id"]: item for item in after}
    assert by_id[older]["status"] == "superseded"
    assert by_id[older]["superseded_by"] == newer
    assert by_id[stale]["status"] == "archived"


def test_apply_dream_is_idempotent_and_appends_nothing_the_second_time(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", updated="2026-09-01")
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", updated="2026-10-01")
    add_knowledge(root, "unused", "a fact nobody used", updated="2026-05-01")
    knowledge_file = root / config.F_KNOWLEDGE

    entries = memorypack.collect(root, "developer")
    proposals = memorypack.dream(entries, NOW)
    scope = memorypack.proposal_scope(entries)
    memorypack.apply_dream(root, proposals, "Developer", scope=scope)
    after_first = knowledge_file.read_text(encoding="utf-8")
    ledger_after_first = ledger_lines(root)

    counts = memorypack.apply_dream(root, proposals, "Developer", scope=scope)
    assert counts["duplicate"] == 0
    assert counts["stale"] == 0
    assert knowledge_file.read_text(encoding="utf-8") == after_first
    assert ledger_lines(root) == ledger_after_first

    fresh = memorypack.dream(memorypack.collect(root, "developer"), NOW)
    memorypack.apply_dream(root, fresh, "Developer", scope=scope)
    assert knowledge_file.read_text(encoding="utf-8") == after_first
    assert ledger_lines(root) == ledger_after_first


def test_apply_dream_appends_one_ledger_event_per_action_group(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", updated="2026-09-01")
    add_knowledge(root, "lock-steal", "claim the lock then re-read the body", updated="2026-10-01")
    add_knowledge(root, "unused", "a fact nobody used", updated="2026-05-01")

    entries = memorypack.collect(root, "developer")
    proposals = memorypack.dream(entries, NOW)
    memorypack.apply_dream(root, proposals, "Developer", scope=memorypack.proposal_scope(entries))

    events = [line for line in (root / config.F_LEDGER).read_text(encoding="utf-8").splitlines()]
    assert len(events) == 2
    assert events[0].count("memory.dream") == 1
    assert "duplicate:" in events[0]
    assert "stale:" in events[1]
    assert "bytes" in events[1]


def test_apply_dream_scopes_a_lesson_id_to_the_file_it_came_from(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_lesson(root, "developer", "same mistake", "same rule", status="open")
    add_lesson(root, "tester", "same mistake", "same rule", status="open")
    developer_lessons = root / "Roles" / "Developer" / config.F_LESSONS
    tester_lessons = root / "Roles" / "Tester" / config.F_LESSONS
    tester_before = tester_lessons.read_text(encoding="utf-8")

    entries = memorypack.collect(root, "developer")
    proposals = {"duplicate": [], "contradiction": [], "stale": ["L-0001"], "no_evidence": []}
    counts = memorypack.apply_dream(
        root, proposals, "Developer", scope=memorypack.proposal_scope(entries)
    )

    assert counts["stale"] == 1
    assert "status: archived" in developer_lessons.read_text(encoding="utf-8")
    assert tester_lessons.read_text(encoding="utf-8") == tester_before


def test_apply_dream_without_scope_scans_every_roles_lessons(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_lesson(root, "developer", "old mistake", "old rule", status="open", updated="2026-01-01")
    proposals = {"duplicate": [], "contradiction": [], "stale": ["L-0001"], "no_evidence": []}
    counts = memorypack.apply_dream(root, proposals, "Developer")
    assert counts["stale"] == 1
    assert "status: archived" in (root / "Roles" / "Developer" / config.F_LESSONS).read_text(
        encoding="utf-8"
    )


def test_apply_dream_writes_nothing_when_the_proposals_are_empty(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "lock-steal", "claim then re-read")
    knowledge_file = root / config.F_KNOWLEDGE
    before = knowledge_file.read_text(encoding="utf-8")

    counts = memorypack.apply_dream(
        root, {"duplicate": [], "contradiction": [], "stale": [], "no_evidence": []}, "Developer"
    )
    assert counts == {"duplicate": 0, "contradiction": 0, "stale": 0, "no_evidence": 0, "bytes": 0}
    assert knowledge_file.read_text(encoding="utf-8") == before
    assert ledger_lines(root) == 0


def test_engine_reports_the_same_score_as_the_module() -> None:
    assert engine.memorypack is memorypack
