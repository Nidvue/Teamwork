"""`memory verify`: one kind per evidence, one status per kind, two fields written."""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from teamwork import config, engine, memorypack, memverify, records
from teamwork.layout import knowledge_path, role_dir

TODAY = datetime.date(2026, 3, 1)
NOW = datetime.datetime(2026, 3, 1, 12, 0, 0)

KNOWLEDGE_FILE = """# Knowledge - what this project has learned

## K-0001 - the readme is the entry point
- statement: the readme is the entry point
- kind: fact
- evidence: README.md
- tags: docs
- owner: developer
- by: Developer
- importance: 3
- uses: 0
- status: active
- created: 2026-01-01
- updated: 2026-01-01

## K-0002 - a file that is gone
- statement: a file that is gone
- kind: gotcha
- evidence: docs/missing.md
- tags: docs
- owner: developer
- by: Developer
- importance: 3
- uses: 0
- status: active
- created: 2026-01-01
- updated: 2026-01-01
"""

LESSONS_FILE = """# Lessons

## L-0001 - a lesson
- role: developer
- status: open
- mistake: a lesson
- cause: a lesson
- rule: a lesson
- evidence: src/teamwork/memverify.py:1
- by: Developer
- created: 2026-01-01
- updated: 2026-01-01
"""


def _repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    env = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("one\ntwo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), *env, "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), *env, "commit", "-q", "-m", "seed"], check=True)
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tree(path: Path) -> Path:
    (path / "docs").mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("one\ntwo\n", encoding="utf-8")
    (path / "docs" / "short.md").write_text("only one line\n", encoding="utf-8")
    (path / "Knowledge.md").write_text(KNOWLEDGE_FILE, encoding="utf-8")
    (path / "Lessons.md").write_text(LESSONS_FILE, encoding="utf-8")
    return path


def _knowledge(project: Path) -> list[dict]:
    return [
        dict(item, store="Knowledge.md", pointer=f"Knowledge.md#{item['id']}")
        for item in records.parse_knowledge(knowledge_path(project))
    ]


def _entry(**overrides) -> dict:
    base = {
        "id": "K-0001",
        "kind": "knowledge",
        "store": "Knowledge.md",
        "pointer": "Knowledge.md#K-0001",
        "title": "a fact",
        "statement": "a fact",
        "tags": "",
        "importance": 3,
        "uses": 0,
        "updated": "2020-01-01",
        "status": "active",
        "evidence": "",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("evidence", "kind"),
    [
        ("pytest -q tests/unit/test_x.py @0123456 -> 4 passed", memverify.REVISION),
        ("rev 0123456 -> the commit that introduced it", memverify.REVISION),
        ("src/teamwork/memverify.py:45 -> the constant", memverify.PATH),
        ("docs/Team/Memory.md", memverify.PATH),
        ("README.md", memverify.PATH),
        ("https://example.invalid/article (2026-01-02)", memverify.SOURCE),
        ("no idea", memverify.NONE),
        ("", memverify.NONE),
    ],
)
def test_classify_names_exactly_one_kind_first_match_wins(evidence: str, kind: str) -> None:
    assert memverify.classify(evidence) == kind


def test_a_revision_verifies_against_git_and_a_stranger_does_not(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    sha = _repo(project)
    assert memverify.verify_record({"evidence": f"@{sha}"}, project, TODAY) == (
        memverify.VERIFIED,
        f"{sha} is a commit here",
    )
    status, reason = memverify.verify_record({"evidence": "rev deadbeef0 -> gone"}, project, TODAY)
    assert status == memverify.DRIFTED
    assert "deadbeef0 is not a commit here" == reason


def test_a_path_verifies_only_when_the_file_and_the_line_are_there(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    assert memverify.verify_record({"evidence": "README.md"}, project, TODAY) == (
        memverify.VERIFIED,
        "README.md exists",
    )
    assert memverify.verify_record({"evidence": "README.md:2"}, project, TODAY) == (
        memverify.VERIFIED,
        "README.md has 2 line(s)",
    )
    status, reason = memverify.verify_record({"evidence": "docs/short.md:9"}, project, TODAY)
    assert (status, reason) == (memverify.DRIFTED, "docs/short.md has 1 line(s), wanted 9")
    status, reason = memverify.verify_record({"evidence": "docs/gone.md"}, project, TODAY)
    assert (status, reason) == (memverify.DRIFTED, "docs/gone.md is missing")


def test_a_source_verifies_until_the_access_date_is_older_than_400_days() -> None:
    fresh = {"evidence": "https://example.invalid/a accessed 2025-01-25"}
    assert memverify.verify_record(fresh, Path("."), TODAY) == (
        memverify.VERIFIED,
        "https://example.invalid/a accessed 2025-01-25, 400 day(s) old",
    )
    stale = {"evidence": "https://example.invalid/a (2025-01-24)"}
    status, reason = memverify.verify_record(stale, Path("."), TODAY)
    assert status == memverify.DRIFTED
    assert "401 day(s) old (max 400)" in reason
    undated = {"evidence": "https://example.invalid/a"}
    assert memverify.verify_record(undated, Path("."), TODAY) == (
        memverify.UNVERIFIABLE,
        "https://example.invalid/a carries no access date",
    )


def test_the_400_day_boundary_is_inclusive_and_a_silent_source_never_drifts() -> None:
    at_the_edge = {"evidence": "https://example.invalid/a accessed 2025-01-25"}
    assert memverify.verify_record(at_the_edge, Path("."), TODAY)[0] == memverify.VERIFIED
    one_day_over = {"evidence": "https://example.invalid/a accessed 2025-01-24"}
    status, reason = memverify.verify_record(one_day_over, Path("."), TODAY)
    assert (status, reason) == (
        memverify.DRIFTED,
        "https://example.invalid/a accessed 2025-01-24 is 401 day(s) old (max 400)",
    )
    silent = {"evidence": "https://example.invalid/a"}
    status, reason = memverify.verify_record(silent, Path("."), TODAY)
    assert status == memverify.UNVERIFIABLE
    assert reason == "https://example.invalid/a carries no access date"


def test_evidence_that_names_nothing_is_unverifiable_never_drifted(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    for evidence in ("", "it is obvious", "see the discussion"):
        assert memverify.verify_record({"evidence": evidence}, project, TODAY) == (
            memverify.UNVERIFIABLE,
            "evidence names no revision, path or source",
        )


def test_verify_all_orders_by_pointer_then_id_and_repeats_byte_identically(
    tmp_path: Path,
) -> None:
    project = _tree(tmp_path)
    rows = _knowledge(project) + [
        _entry(id="L-0001", store="Lessons.md", pointer="Lessons.md#L-0001")
    ]
    first = memverify.verify_all(rows, project, NOW)
    second = memverify.verify_all(rows, project, NOW)
    assert [row["id"] for row in first] == ["K-0001", "K-0002", "L-0001"]
    counts = memverify.count(first, 0)
    assert memverify.render(first, counts) == memverify.render(second, counts)
    assert memverify.render(first, counts, as_json=True) == memverify.render(
        second, counts, as_json=True
    )


def test_render_prints_one_line_per_record_then_the_footer(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    rows = memverify.verify_all(_knowledge(project), project, NOW)
    counts = memverify.count(memverify.cap(rows, 1), 1)
    text = memverify.render(memverify.cap(rows, 1), counts)
    assert text.splitlines() == [
        "- [K-0001] path verified | README.md exists | Knowledge.md#K-0001",
        "# verify: 1 record(s), 1 verified, 0 drifted, 0 unverifiable (limit 1)",
    ]
    whole = memverify.render(rows, memverify.count(rows, 0))
    assert whole.splitlines()[-1] == (
        "# verify: 2 record(s), 1 verified, 1 drifted, 0 unverifiable (limit all)"
    )


def test_render_json_is_one_object_per_record_with_the_same_fields(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    rows = memverify.verify_all(_knowledge(project), project, NOW)
    lines = memverify.render(rows, memverify.count(rows, 0), as_json=True).splitlines()
    assert [json.loads(line) for line in lines] == rows
    assert set(json.loads(lines[0])) == {
        "id",
        "kind",
        "verify_status",
        "reason",
        "pointer",
        "store",
    }


def test_apply_writes_only_the_two_fields_and_leaves_lessons_byte_identical(
    tmp_path: Path,
) -> None:
    project = _tree(tmp_path)
    path = knowledge_path(project)
    lessons = project / "Lessons.md"
    lessons_before = lessons.read_bytes()
    before = {item["id"]: dict(item) for item in records.parse_knowledge(path)}
    entries = _knowledge(project) + [
        _entry(id="L-0001", store="Lessons.md", pointer="Lessons.md#L-0001")
    ]
    rows = memverify.verify_all(entries, project, NOW)
    applied = memverify.apply(rows, project, "Developer", TODAY)
    assert applied["changed"] == 2
    after = {item["id"]: dict(item) for item in records.parse_knowledge(path)}
    for record_id, item in after.items():
        for field in (
            "statement",
            "kind",
            "evidence",
            "tags",
            "owner",
            "by",
            "importance",
            "uses",
            "status",
            "created",
            "updated",
        ):
            assert item[field] == before[record_id][field], field
        assert item["checked"] == "2026-03-01"
        assert item["verify_status"] in (memverify.VERIFIED, memverify.DRIFTED)
    assert after["K-0001"]["verify_status"] == memverify.VERIFIED
    assert after["K-0002"]["verify_status"] == memverify.DRIFTED
    assert lessons.read_bytes() == lessons_before
    ledger = engine.ledger_path(project).read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in ledger if '"memory.verify"' in line]
    assert len(events) == 1
    assert "1 verified" in events[0]["detail"] and "1 drifted" in events[0]["detail"]


def test_a_second_apply_writes_nothing_and_appends_nothing(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    path = knowledge_path(project)
    rows = memverify.verify_all(_knowledge(project), project, NOW)
    memverify.apply(rows, project, "Developer", TODAY)
    stamped = path.read_bytes()
    ledger_before = engine.ledger_path(project).read_text(encoding="utf-8").splitlines()
    again = memverify.verify_all(_knowledge(project), project, NOW)
    applied = memverify.apply(again, project, "Developer", TODAY)
    assert applied["changed"] == 0
    assert path.read_bytes() == stamped
    assert engine.ledger_path(project).read_text(encoding="utf-8").splitlines() == ledger_before


def test_dream_keeps_its_four_groups_and_adds_drifted(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    entries = [
        _entry(id="K-0001", title="same key", statement="one claim about the tree"),
        _entry(
            id="K-0002",
            title="same key",
            statement="one claim about the tree",
            evidence="docs/missing.md",
        ),
    ]
    proposals = memorypack.dream(entries, NOW, project)
    assert set(proposals) == {
        "duplicate",
        "contradiction",
        "stale",
        "no_evidence",
        "drifted",
    }
    assert proposals["duplicate"] == [("K-0002", "K-0001", 1.0)]
    assert proposals["stale"] == ["K-0001", "K-0002"]
    assert [row[0] for row in proposals["drifted"]] == ["K-0002"]
    assert proposals["drifted"][0][1] == memverify.PATH
    assert "docs/missing.md is missing" == proposals["drifted"][0][2]


def test_dream_without_a_project_reports_no_drift() -> None:
    entries = [_entry(id="K-0001", evidence="docs/missing.md")]
    assert memorypack.dream(entries, NOW)["drifted"] == []


def _team(tmp_path: Path) -> Path:
    project = _tree(tmp_path)
    role_dir(project, "developer").mkdir(parents=True, exist_ok=True)
    knowledge_path(project).write_text(KNOWLEDGE_FILE, encoding="utf-8")
    return project


def _verify_args(**overrides) -> SimpleNamespace:
    base = {
        "role": "developer",
        "focus": "",
        "limit": None,
        "json": False,
        "apply": False,
        "by": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


BASELINE = """- [K-0001] path verified | README.md exists | Knowledge.md#K-0001
- [K-0002] path drifted | docs/missing.md is missing | Knowledge.md#K-0002
# verify: 2 record(s), 1 verified, 1 drifted, 0 unverifiable (limit all)
"""


def test_without_focus_the_report_is_byte_identical_to_the_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _team(tmp_path)
    assert engine._memory_verify(project, "developer", _verify_args()) == 0
    assert capsys.readouterr().out == BASELINE


def test_focus_ranks_by_the_frozen_score_not_pointer_order(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    entries = [
        _entry(id="K-0001", statement="an unrelated note", importance=1, updated="2020-01-01"),
        _entry(
            id="K-0002",
            statement="the parser budget",
            importance=5,
            uses=5,
            updated="2026-02-25",
        ),
        _entry(id="K-0003", statement="the parser", importance=3, updated="2020-01-01"),
    ]
    rows, deferred = memverify.select(entries, project, "parser", NOW, 2)
    assert [row["id"] for row in rows] == ["K-0002", "K-0003"]
    assert deferred == 1
    whole, none_deferred = memverify.select(entries, project, "parser", NOW, 0)
    assert [row["id"] for row in whole] == ["K-0002", "K-0003", "K-0001"]
    assert none_deferred == 0
    assert [row["id"] for row in memverify.verify_all(entries, project, NOW)] == [
        "K-0001",
        "K-0002",
        "K-0003",
    ]


def test_focus_resolves_a_task_id_to_its_title(tmp_path: Path) -> None:
    project = _tree(tmp_path)
    queue = role_dir(project, "developer") / config.F_TASKS
    task = records.new_task("Repair the parser budget leak", priority="P1")
    records.write_tasks(queue, [task], "developer")
    task_id = records.parse_tasks(queue)[0]["id"]
    entries = [
        _entry(id="K-0001", statement="an unrelated note", importance=1, updated="2020-01-01"),
        _entry(id="K-0002", statement="the parser budget", importance=3, updated="2020-01-01"),
    ]
    query = memorypack.task_query(project, "developer", task_id)
    assert query == "Repair the parser budget leak"
    rows, deferred = memverify.select(entries, project, query, NOW, 1)
    assert [row["id"] for row in rows] == ["K-0002"]
    assert deferred == 1


def test_the_focused_footer_reports_the_deferred_records(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _team(tmp_path)
    assert (
        engine._memory_verify(
            project, "developer", _verify_args(focus="readme entry point", limit=1)
        )
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "- [K-0001] path verified | README.md exists | Knowledge.md#K-0001"
    assert lines[-2] == "# verify: 1 record(s), 1 verified, 0 drifted, 0 unverifiable (limit 1)"
    assert lines[-1] == "# verify: 1 deferred by --focus"


def test_focus_with_limit_zero_keeps_every_record(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _team(tmp_path)
    assert (
        engine._memory_verify(
            project, "developer", _verify_args(focus="readme entry point", limit=0)
        )
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert [line.split("]")[0] for line in lines[:2]] == ["- [K-0001", "- [K-0002"]
    assert lines[-2] == "# verify: 2 record(s), 1 verified, 1 drifted, 0 unverifiable (limit all)"
    assert lines[-1] == "# verify: 0 deferred by --focus"


def test_the_focused_default_keeps_the_highest_scoring_records(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _team(tmp_path)
    assert memverify.FOCUS_LIMIT == 25
    assert (
        engine._memory_verify(project, "developer", _verify_args(focus="readme entry point")) == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("- [K-0001]")
    assert lines[-1] == "# verify: 0 deferred by --focus"
