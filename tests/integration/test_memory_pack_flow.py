"""Integration: the memory pack, search and dream pass through the real CLI.

Layer ``integration``, area ``memory``, owner Tester lane (T-0036). Each case runs
the commands a lane actually types - ``memory pack``, ``memory search``,
``memory dream`` and ``load --task`` - against a throwaway ``--no-git`` team in
``tmp_path``, and asserts what the operator sees plus what the stores look like
afterwards (``docs/Team/Memory.md`` 4.1-4.4, AC-M20-1..AC-M20-4).

The store is filled through the shipped commands wherever a command can write the
record; the stale and evidence-less fixtures are written directly because no
command creates them (``knowledge add`` refuses a record without evidence).

Owner: tester. Layer: integration. Area: memory.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from teamwork import config, engine, memorypack, records

AGENTS = "ceo,developer,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init_workspace(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    root = team_root(project)
    assert root.is_dir()
    return root


def add_lesson(cli, project: Path, mistake: str, rule: str) -> int:
    return cli(
        "--project",
        project,
        "lesson",
        "add",
        "--by",
        "Developer",
        "--role",
        "developer",
        "--mistake",
        mistake,
        "--cause",
        "the guard was skipped",
        "--rule",
        rule,
        "--evidence",
        "pytest tests/unit/test_io.py @abc1234 -> 12 passed",
    )


def add_knowledge(cli, project: Path, topic: str, statement: str, importance: int = 3) -> int:
    return cli(
        "--project",
        project,
        "knowledge",
        "add",
        "--by",
        "Developer",
        "--topic",
        topic,
        "--statement",
        statement,
        "--evidence",
        "pytest tests/unit/test_knowledge.py @abc1234 -> 15 passed",
        "--importance",
        str(importance),
    )


def knowledge_record(
    record_id: str,
    topic: str,
    statement: str,
    evidence: str,
    updated: str = "2026-11-07",
) -> dict:
    item = records.new_knowledge(topic, statement, evidence, "Developer", "developer")
    item["id"] = record_id
    item["created"] = updated
    item["updated"] = updated
    return item


def dream_events(root: Path) -> list:
    path = root / config.F_LEDGER
    if not path.is_file():
        return []
    return [
        record
        for record in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        if record["action"] == "memory.dream"
    ]


def seed_store(cli, project: Path, root: Path) -> None:
    assert (
        cli("--project", project, "task", "add", "developer", "Fix the lock steal race in io.py")
        == 0
    )
    assert add_lesson(cli, project, "committed a lock race on main", "run branch start first") == 0
    assert (
        add_knowledge(
            cli,
            project,
            "lock-steal-protocol",
            "io.py claims the lock before it re-reads the body, so no waiter unlinks a replaced lock",
            importance=5,
        )
        == 0
    )
    for index in range(1, 21):
        assert (
            add_knowledge(
                cli,
                project,
                f"filler-topic-{index}",
                f"filler statement {index} " + "padding " * 58,
                importance=1,
            )
            == 0
        )
    memory_store = root / "Roles" / "Developer" / config.F_SHORT
    entries = records.parse_memory(memory_store)
    entries.append(
        records.new_entry(
            "the lock pen is free after release",
            key="lock-pen",
            importance=4,
            by="Developer",
            src="T-0001",
            rev="abc1234",
        )
    )
    records.write_memory(memory_store, entries, config.F_SHORT, "Developer")


def test_memory_pack_is_task_aware_capped_and_deterministic(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project)
    seed_store(cli, project, root)
    capsys.readouterr()

    assert (
        cli("--project", project, "memory", "pack", "--role", "developer", "--task", "T-0001") == 0
    )
    first = capsys.readouterr().out
    assert (
        cli("--project", project, "memory", "pack", "--role", "developer", "--task", "T-0001") == 0
    )
    second = capsys.readouterr().out

    assert first == second
    assert first.startswith(
        "# task: T-0001 -> 'Fix the lock steal race in io.py' (budget 4000 bytes)"
    )
    assert "- [K-0001] knowledge | io.py claims the lock" in first
    assert "# pack: " in first
    assert "(budget 4000)" in first
    assert len(first.encode("utf-8")) <= 4000
    packed = [line for line in first.splitlines() if line.startswith("- [")]
    assert [line.split("]")[0] for line in packed[:3]] == ["- [K-0001", "- [L-0001", "- [M-0001"]
    assert 0 < len(packed) < 23


def test_memory_pack_honours_a_tighter_budget(cli, project: Path, capsys) -> None:
    root = init_workspace(cli, project)
    seed_store(cli, project, root)
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "memory",
            "pack",
            "--role",
            "developer",
            "--task",
            "lock",
            "--budget",
            "260",
        )
        == 0
    )
    printed = capsys.readouterr().out
    assert len(printed.encode("utf-8")) <= 260
    assert "(budget 260)" in printed


def test_memory_pack_refuses_a_missing_role(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    capsys.readouterr()

    assert cli("--project", project, "memory", "pack", "--task", "T-0001") == 2
    assert "--role is required for `memory pack`" in capsys.readouterr().err


def test_memory_search_reaches_all_three_stores_and_caps_its_output(
    cli, project: Path, capsys
) -> None:
    root = init_workspace(cli, project)
    seed_store(cli, project, root)
    capsys.readouterr()

    assert cli("--project", project, "memory", "search", "lock") == 0
    printed = capsys.readouterr().out
    assert "- [K-0001] knowledge" in printed
    assert "- [L-0001] lesson" in printed
    assert "- [M-0001] memory" in printed
    assert "Knowledge.md#K-0001" in printed
    assert "# search: 3 of 3 match(es)" in printed
    assert len(printed.encode("utf-8")) <= memorypack.SEARCH_BUDGET_BYTES


def test_load_task_prints_a_pack_smaller_than_the_static_block_and_leaves_load_unchanged(
    cli, project: Path, capsys
) -> None:
    root = init_workspace(cli, project)
    seed_store(cli, project, root)
    capsys.readouterr()

    assert cli("--project", project, "load", "developer") == 0
    static = capsys.readouterr().out
    assert cli("--project", project, "load", "developer", "--task", "T-0001") == 0
    packed = capsys.readouterr().out

    assert "# project knowledge:" in static
    assert "# project knowledge:" not in packed
    assert "(budget 4000 bytes; not the static top-10)" in packed
    assert "# pack: " in packed
    assert "io.py claims the lock" in packed
    assert len(packed.encode("utf-8")) < len(static.encode("utf-8"))
    assert static.split("\n# Lessons")[0] == packed.split("\n# Lessons")[0]


def test_memory_dream_reports_then_applies_once_and_is_idempotent(
    cli, project: Path, capsys
) -> None:
    root = init_workspace(cli, project)
    knowledge_file = root / config.F_KNOWLEDGE
    evidence = "pytest tests/unit/test_knowledge.py @abc1234 -> 15 passed"
    records.write_knowledge(
        knowledge_file,
        [
            knowledge_record(
                "K-0001", "pack-budget", "the pack budget is four thousand bytes", evidence
            ),
            knowledge_record(
                "K-0002", "pack-budget", "the pack budget is unbounded today", evidence
            ),
            knowledge_record(
                "K-0003",
                "lock-steal",
                "claim the lock then re-read the body before unlinking it",
                evidence,
                updated="2026-10-01",
            ),
            knowledge_record(
                "K-0004",
                "lock-steal",
                "claim the lock then re-read the body before unlinking",
                evidence,
                updated="2026-09-01",
            ),
            knowledge_record(
                "K-0005",
                "forgotten-topic",
                "a fact nobody has used since the spring",
                evidence,
                updated="2026-05-01",
            ),
            knowledge_record("K-0006", "unproven", "a claim with no evidence at all", "x"),
        ],
    )
    before = knowledge_file.read_text(encoding="utf-8")
    capsys.readouterr()

    assert cli("--project", project, "memory", "dream") == 0
    report = capsys.readouterr().out
    assert "# duplicate: 1" in report
    assert "- K-0004 -> superseded by K-0003" in report
    assert "# contradiction: 1" in report
    assert "- K-0001 vs K-0002: same knowledge key 'pack-budget'" in report
    assert "# stale: 1" in report
    assert "- K-0005" in report
    assert "# no evidence: 1" in report
    assert "- K-0006" in report
    assert "# dry run: nothing written" in report
    assert knowledge_file.read_text(encoding="utf-8") == before
    assert dream_events(root) == []

    assert cli("--project", project, "memory", "dream", "--apply", "--by", "Developer") == 0
    applied = capsys.readouterr().out
    assert "# applied: 1 duplicate(s) superseded, 1 stale archived" in applied
    after_first = knowledge_file.read_text(encoding="utf-8")
    events = dream_events(root)
    assert len(events) == 2
    assert "duplicate: K-0004" in events[0]["detail"]
    assert "stale: K-0005" in events[1]["detail"]

    by_id = {item["id"]: item for item in records.parse_knowledge(knowledge_file)}
    assert by_id["K-0004"]["status"] == "superseded"
    assert by_id["K-0004"]["superseded_by"] == "K-0003"
    assert by_id["K-0005"]["status"] == "archived"
    assert by_id["K-0003"]["statement"] == (
        "claim the lock then re-read the body before unlinking it"
    )
    assert by_id["K-0005"]["statement"] == "a fact nobody has used since the spring"
    assert [item["id"] for item in records.parse_knowledge(knowledge_file)] == [
        "K-0001",
        "K-0002",
        "K-0003",
        "K-0004",
        "K-0005",
        "K-0006",
    ]

    assert cli("--project", project, "memory", "dream", "--apply", "--by", "Developer") == 0
    capsys.readouterr()
    assert knowledge_file.read_text(encoding="utf-8") == after_first
    assert dream_events(root) == events


def test_memory_dream_on_a_copy_is_idempotent_and_keeps_provenance(
    cli, project: Path, capsys
) -> None:
    root = init_workspace(cli, project)
    evidence = "pytest tests/unit/test_knowledge.py @abc1234 -> 15 passed"
    records.write_knowledge(
        root / config.F_KNOWLEDGE,
        [
            knowledge_record(
                "K-0001",
                "lock-steal",
                "claim the lock then re-read the body before unlinking it",
                evidence,
            ),
            knowledge_record(
                "K-0002",
                "lock-steal",
                "claim the lock then re-read the body before unlinking",
                evidence,
                updated="2026-09-01",
            ),
            knowledge_record(
                "K-0003",
                "forgotten-topic",
                "a fact nobody has used since the spring",
                evidence,
                updated="2026-05-01",
            ),
        ],
    )
    assert add_lesson(cli, project, "unlinked a replaced lock", "claim then re-read") == 0
    capsys.readouterr()

    live = {
        path: (root / path).read_bytes()
        for path in (config.F_KNOWLEDGE, config.F_LESSONS, config.F_LEDGER)
        if (root / path).is_file()
    }
    copy_project = project.parent / f"{project.name}-copy"
    shutil.copytree(project, copy_project)
    copy_root = team_root(copy_project)
    (copy_project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / root.name).rename(copy_root)
    before = (copy_root / config.F_KNOWLEDGE).read_text(encoding="utf-8")

    assert (
        cli(
            "--project",
            copy_project,
            "memory",
            "dream",
            "--apply",
            "--by",
            "Developer",
        )
        == 0
    )
    report = capsys.readouterr().out
    assert "# applied: 1 duplicate(s) superseded, 1 stale archived" in report

    after = (copy_root / config.F_KNOWLEDGE).read_text(encoding="utf-8")
    assert after != before
    by_id = {item["id"]: item for item in records.parse_knowledge(copy_root / config.F_KNOWLEDGE)}
    assert [item["id"] for item in records.parse_knowledge(copy_root / config.F_KNOWLEDGE)] == [
        "K-0001",
        "K-0002",
        "K-0003",
    ]
    assert by_id["K-0002"]["status"] == "superseded"
    assert by_id["K-0002"]["superseded_by"] == "K-0001"
    assert by_id["K-0003"]["status"] == "archived"
    for record_id, updated in (("K-0001", "2026-11-07"), ("K-0002", "2026-09-01")):
        assert by_id[record_id]["by"] == "Developer"
        assert by_id[record_id]["evidence"] == evidence
        assert by_id[record_id]["updated"] == updated
    assert by_id["K-0003"]["evidence"] == evidence
    assert by_id["K-0003"]["statement"] == "a fact nobody has used since the spring"
    events = dream_events(copy_root)
    assert len(events) == 2

    for path, content in live.items():
        assert (root / path).read_bytes() == content, path
    assert dream_events(root) == []

    assert (
        cli(
            "--project",
            copy_project,
            "memory",
            "dream",
            "--apply",
            "--by",
            "Developer",
        )
        == 0
    )
    capsys.readouterr()
    assert (copy_root / config.F_KNOWLEDGE).read_text(encoding="utf-8") == after
    assert dream_events(copy_root) == events


def test_memory_dream_apply_requires_a_name(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "memory", "dream", "--apply") == 2
    assert "--by is required with --apply" in capsys.readouterr().err
