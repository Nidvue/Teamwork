"""Integration: the M23 memory flow certified end to end through the shipped commands.

Layer ``integration``, area ``memory``, owner Tester lane (T-0011). Each case runs
what an operator types - ``lane status``, ``load --task``, ``lane start --print``,
``pulse``, ``consolidate``, ``memory dream``, ``memory search`` - against a
throwaway ``--no-git`` team in ``tmp_path``, and asserts what the operator sees
plus what the stores look like afterwards (``docs/Team/Memory.md`` 15.1-15.6,
AC-M23-1..6).

The fixture writes only what no command creates: a lane run record with its
outcome file and log (the launcher writes those; the reconcile command is what
turns them into a short entry), and records whose age makes them stale.

Owner: tester. Layer: integration. Area: memory.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from teamwork import config, lanes, memorypack, records

AGENTS = "ceo,developer-1,developer-2,reviewer-1"
OLD = "2020-01-01"


def team_root(project: Path) -> Path:
    from teamwork import engine

    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init_workspace(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    root = team_root(project)
    assert root.is_dir()
    return root


def add_task(cli, project: Path, agent: str, title: str, capsys) -> str:
    assert cli("--project", project, "task", "add", agent, title) == 0
    out = capsys.readouterr().out
    return re.search(r"(T-\d{4})", out).group(1)


def add_lane_run(
    root: Path,
    *,
    run_id: str = "L-0001",
    agent: str = "Developer-1",
    role: str = "developer",
    task: str = "T-0001",
    note: str = "self-checked and PR open",
    verdict: str = "ok",
    last_word: bool = True,
) -> None:
    """One ended lane as the launcher leaves it: a record, a log, an outcome file."""
    log = root / "Agents" / agent / "Runs" / f"{run_id}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    body = f"# lane {run_id}\n... work ...\n"
    if last_word:
        body += f"LANE-RESULT: {verdict} {note}\n"
    log.write_text(body, encoding="utf-8")
    lanes.write_run(
        root,
        {
            "id": run_id,
            "agent": agent,
            "role": role,
            "task": task,
            "state": "running",
            "log": str(log),
            "started": "2026-11-11T10:00:00Z",
        },
    )
    lanes.run_path(root, run_id).with_suffix(".outcome.json").write_text(
        json.dumps({"state": "exited", "exit": 0, "seconds": 12}), encoding="utf-8"
    )


def store(root: Path, role: str, name: str) -> list[dict]:
    return records.parse_memory(root / "Roles" / role / name)


def write_entry(root: Path, role: str, name: str, body: str, *, key: str, **extra) -> str:
    path = root / "Roles" / role / name
    items = records.parse_memory(path)
    entry = records.new_entry(body, key, 2, by=f"{role.capitalize()}-1")
    entry.update(extra)
    items.append(entry)
    records.write_memory(path, items, name, role.capitalize())
    return records.parse_memory(path)[-1]["id"]


def add_lesson(cli, project: Path, mistake: str, rule: str, evidence: str) -> int:
    return cli(
        "--project",
        project,
        "lesson",
        "add",
        "--by",
        "Developer-1",
        "--role",
        "developer",
        "--mistake",
        mistake,
        "--cause",
        "the guard was skipped",
        "--rule",
        rule,
        "--evidence",
        evidence,
    )


def ledger_actions(root: Path, action: str) -> int:
    path = root / config.F_LEDGER
    if not path.is_file():
        return 0
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("action") == action
    )


def test_a_lane_run_leaves_one_short_entry_a_sibling_instance_sees(cli, project, capsys) -> None:
    """AC-M23-1: one store, two instances - the note the exit wrote reaches both."""
    root = init_workspace(cli, project)
    add_lane_run(root)
    assert cli("--project", project, "lane", "status") == 0
    capsys.readouterr()

    entries = store(root, "Developer", config.F_SHORT)
    assert len(entries) == 1, entries
    assert entries[0]["src"] == "T-0001"
    assert entries[0]["by"] == "Developer-1"
    assert "T-0001 ok" in entries[0]["body"]
    assert ledger_actions(root, "memory.add") == 1

    task = add_task(cli, project, "developer-2", "T-0002 sibling read", capsys)
    assert cli("--project", project, "load", "Developer-2", "--task", task) == 0
    loaded = capsys.readouterr().out
    assert "## Short-term memory for this task" in loaded
    assert "T-0001 ok" in loaded

    assert cli("--project", project, "lane", "start", "--agent", "developer-2", "--print") == 0
    printed = capsys.readouterr().out
    packet_line = next(line for line in printed.splitlines() if line.startswith("# packet:"))
    packet = Path(packet_line.split(":", 1)[1].strip()).read_text(encoding="utf-8")
    assert "## Short-term memory for this task" in packet
    assert "T-0001 ok" in packet


def test_the_harness_writes_nothing_when_the_lane_recorded_nothing(cli, project) -> None:
    """The empty case: a lane with no LANE-RESULT line invents no note."""
    root = init_workspace(cli, project)
    add_lane_run(root, run_id="L-0002", task="T-0003", last_word=False)
    assert cli("--project", project, "lane", "status") == 0
    assert store(root, "Developer", config.F_SHORT) == []
    assert ledger_actions(root, "memory.add") == 0


def test_promotion_moves_a_short_entry_to_long_and_a_long_entry_to_the_archive(
    cli, project, capsys
) -> None:
    """AC-M23-2 (move half): 15.3 applied by the shipped command, nothing deleted."""
    root = init_workspace(cli, project)
    stale = {"uses": 3, "last_used": OLD, "created": OLD, "updated": OLD}
    unused = {"uses": 0, "last_used": OLD, "created": OLD, "updated": OLD}
    write_entry(
        root,
        "Developer",
        config.F_SHORT,
        "the release gate runs the privacy scan before the build",
        key="gate",
        **stale,
    )
    write_entry(
        root,
        "Developer",
        config.F_LONG,
        "the archived note about the vendored cache",
        key="cache",
        **unused,
    )

    assert (
        cli("--project", project, "consolidate", "--agent", "developer", "--by", "Developer-1") == 0
    )
    capsys.readouterr()

    assert [entry["key"] for entry in store(root, "Developer", config.F_SHORT)] == []
    assert "gate" in [entry["key"] for entry in store(root, "Developer", config.F_LONG)]
    archive = store(root, "Developer", config.F_MEM_ARCHIVE)
    assert [entry["key"] for entry in archive] == ["cache"]
    assert "vendored cache" in archive[0]["body"]
    assert ledger_actions(root, "memory.promote") == 1
    assert ledger_actions(root, "memory.evict") == 1
    assert cli("--project", project, "context", "find", "vendored cache") == 0
    assert "memory/archive/M-0001" in capsys.readouterr().out


def test_recall_resolves_an_archived_record(cli, project, capsys) -> None:
    """AC-M23-2 (recall half): the demotion leaves a pointer recall still resolves."""
    root = init_workspace(cli, project)
    write_entry(
        root,
        "Developer",
        config.F_LONG,
        "the archived note about the vendored cache",
        key="cache",
        uses=0,
        last_used=OLD,
        created=OLD,
        updated=OLD,
    )
    assert (
        cli("--project", project, "consolidate", "--agent", "developer", "--by", "Developer-1") == 0
    )
    capsys.readouterr()
    assert [entry["key"] for entry in store(root, "Developer", config.F_MEM_ARCHIVE)] == ["cache"]
    assert cli("--project", project, "recall", "vendored cache", "--agent", "developer") == 0
    assert "vendored cache" in capsys.readouterr().out
    assert cli("--project", project, "memory", "search", "vendored cache") == 0
    assert "ArchivedMemory.md#M-0001" in capsys.readouterr().out


def test_the_dream_line_rides_lane_start_and_pulse_and_a_second_apply_is_empty(
    cli, project, capsys
) -> None:
    """AC-M23-3: both triggers print it, the pass stays in budget, apply is idempotent."""
    root = init_workspace(cli, project)
    add_task(cli, project, "developer-1", "T-0004 lane work", capsys)
    assert cli("--project", project, "lane", "start", "--agent", "developer-1", "--print") == 0
    printed = capsys.readouterr().out
    packet_line = next(line for line in printed.splitlines() if line.startswith("# packet:"))
    packet = Path(packet_line.split(":", 1)[1].strip()).read_text(encoding="utf-8")
    assert packet.splitlines()[1].startswith("# memory:")

    assert cli("--project", project, "pulse") == 0
    assert "# memory:" in capsys.readouterr().out

    started = time.monotonic()
    assert cli("--project", project, "memory", "dream", "--dry-run") == 0
    elapsed = time.monotonic() - started
    assert elapsed <= config.DREAM_BUDGET_SECONDS, elapsed
    capsys.readouterr()

    assert cli("--project", project, "memory", "dream", "--apply", "--by", "Developer-1") == 0
    first = capsys.readouterr().out
    events = ledger_actions(root, "memory.dream")
    assert cli("--project", project, "memory", "dream", "--apply", "--by", "Developer-1") == 0
    second = capsys.readouterr().out
    assert ledger_actions(root, "memory.dream") == events
    assert "applied: 0 " in first and "applied: 0 " in second


def test_memory_search_returns_a_wiki_page_pointer_inside_the_read_budget(
    cli, project, capsys
) -> None:
    """AC-M23-4: a fixture corpus the trigger fires on, and the page hit is paid for."""
    root = init_workspace(cli, project)
    (root / "Notes.md").write_text("the gate notes\n", encoding="utf-8")
    assert (
        add_lesson(
            cli,
            project,
            "gate skipped",
            "always run the privacy scan before the release build",
            "Notes.md:1",
        )
        == 0
    )
    assert (
        add_lesson(
            cli,
            project,
            "gate skipped",
            "refuse the release while a critical alert is open",
            "Notes.md:1",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "memory", "dream", "--apply", "--by", "Developer-1") == 0
    capsys.readouterr()
    pages = sorted((root / "Wiki").glob("*.md"))
    assert [page.name for page in pages] == ["gate-skipped.md"], pages
    assert pages[0].stat().st_size <= config.WIKI_BUDGET_BYTES
    assert pages[0].read_text(encoding="utf-8").count("-> L-000") >= 2

    assert cli("--project", project, "memory", "search", "privacy scan") == 0
    found = capsys.readouterr().out
    assert "-> Wiki/gate-skipped.md#L" in found
    assert len(found.encode("utf-8")) <= memorypack.SEARCH_BUDGET_BYTES


def test_the_measurement_table_has_no_unmeasured_cell(repo_root: Path) -> None:
    """AC-M23-5: 15.6 is a runnable table, not prose - no cell is left to a reader."""
    text = (repo_root / "docs" / "Team" / "Memory.md").read_text(encoding="utf-8")
    start = text.index("### 15.6")
    section = text[start : text.index("### 15.7")]
    rows = [
        line
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| surface") and "---" not in line
    ]
    assert len(rows) >= 10, rows
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) >= 4, row
        assert all(cells), row
        assert "TBD" not in row, row
    assert "AC-M23-6 role coverage" in section
