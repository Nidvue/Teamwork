"""Unit: transcript reach over the ledger and the worklogs (Memory.md 10).

Layer ``unit``, area ``memory``. The transcript is the one store the engine writes
and never reads, so the load-bearing assertions are that both append-only sources
are reachable, that a pointer names the exact line a reader can open, that the
cap and the footer are the ones ``memory search`` prints, that a query with no
match is an honest empty result, and that the ledger is streamed rather than
materialised - a 100k-line ledger must cost a line of memory, not the file.

Owner: developer. Layer: unit. Area: memory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from teamwork import config, transcripts

EVENT_MATCH = {
    "action": "task.claim",
    "actor": "Developer",
    "target": "T-0056",
    "detail": "claimed the transcript reach lane and started the branch",
    "ts": "2026-10-20T12:14:58",
}
EVENT_OTHER = {
    "action": "task.done",
    "actor": "Reviewer",
    "target": "T-0055",
    "detail": "merged the memory focus lane",
    "ts": "2026-10-19T09:00:00",
}
WORKLOG_LINES = [
    "# WorkLog - developer (developer)",
    "",
    "Claimed the transcript reach lane and started the branch.",
    "Ran the gate on the worktree.",
]


def ledger_line(event: dict) -> str:
    return json.dumps(event, sort_keys=True)


def team_tree(tmp_path: Path) -> Path:
    """A bare team tree: one ledger with three events and one instance worklog."""
    root = tmp_path / "Team"
    root.mkdir()
    (root / transcripts.LEDGER_FILE).write_text(
        "\n".join([ledger_line(EVENT_MATCH), ledger_line(EVENT_OTHER), ledger_line(EVENT_OTHER)])
        + "\n",
        encoding="utf-8",
    )
    worklog = root / config.DIR_AGENTS / "Developer" / config.F_WORKLOG
    worklog.parent.mkdir(parents=True)
    worklog.write_text("\n".join(WORKLOG_LINES) + "\n", encoding="utf-8")
    return root


def test_iter_hits_reaches_both_sources_with_line_pointers(tmp_path: Path) -> None:
    root = team_tree(tmp_path)
    hits = list(transcripts.iter_hits(root, "transcript reach lane"))
    pointers = [hit["pointer"] for hit in hits]
    assert "Ledger.jsonl#1" in pointers
    assert "Agents/Developer/WorkLog.md:3" in pointers
    assert pointers.count("Ledger.jsonl#1") == 1
    assert all(hit["pointer"] == hit["id"] for hit in hits)
    kinds = {hit["pointer"]: hit["kind"] for hit in hits}
    assert kinds["Ledger.jsonl#1"] == transcripts.EVENT_KIND
    assert kinds["Agents/Developer/WorkLog.md:3"] == transcripts.WORKLOG_KIND


def test_a_ledger_hit_renders_the_event_fields_not_the_json_blob(tmp_path: Path) -> None:
    root = team_tree(tmp_path)
    text = transcripts.search(root, "T-0056")
    assert "task.claim | Developer | T-0056 | claimed the transcript reach lane" in text
    assert '{"action"' not in text
    assert "Ledger.jsonl#1" in text


def test_no_match_is_an_honest_empty_result(tmp_path: Path) -> None:
    root = team_tree(tmp_path)
    hits, total = transcripts.collect(root, "zebra unicorn")
    assert hits == []
    assert total == 0
    assert (
        transcripts.search(root, "zebra unicorn")
        == '# no transcript line matched "zebra unicorn"\n'
    )


def test_the_cap_is_ten_hits_and_two_thousand_bytes(tmp_path: Path) -> None:
    root = tmp_path / "Team"
    root.mkdir()
    events = [
        dict(EVENT_MATCH, detail=f"planted transcript event {index}", target=f"T-{index:04d}")
        for index in range(30)
    ]
    (root / transcripts.LEDGER_FILE).write_text(
        "\n".join(ledger_line(event) for event in events) + "\n", encoding="utf-8"
    )
    hits, total = transcripts.collect(root, "planted transcript event")
    assert len(hits) == transcripts.SEARCH_LIMIT == 10
    assert total == 10
    rendered = transcripts.render(hits, total)
    lines = rendered.splitlines()
    assert len(lines) == 11
    assert len(rendered.encode("utf-8")) <= transcripts.SEARCH_BUDGET_BYTES
    used = sum(len(line.encode("utf-8")) + 1 for line in lines[:-1])
    assert lines[-1] == f"# search: 10 of 10 match(es), {used} bytes"


def test_a_rendered_hit_clips_its_text_to_two_hundred_characters(tmp_path: Path) -> None:
    root = tmp_path / "Team"
    root.mkdir()
    event = {"action": " ".join(["needle"] * 80), "actor": "", "target": "", "detail": "", "ts": ""}
    (root / transcripts.LEDGER_FILE).write_text(ledger_line(event) + "\n", encoding="utf-8")
    line = transcripts.search(root, "needle").splitlines()[0]
    assert len(line.split(" | ")[1]) == 200


def test_the_ledger_is_streamed_not_materialised(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "Team"
    root.mkdir()
    ledger = root / transcripts.LEDGER_FILE
    with ledger.open("w", encoding="utf-8") as handle:
        for number in range(100_000):
            handle.write(ledger_line(dict(EVENT_OTHER, detail=f"filler line {number}")) + "\n")
        handle.write(ledger_line(EVENT_MATCH) + "\n")

    def refuse(*_args, **_kwargs):
        raise AssertionError("the transcript reader must not materialise the ledger")

    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)

    stream = transcripts.iter_hits(root, "transcript reach")
    assert hasattr(stream, "__next__")
    assert next(stream)["pointer"] == "Ledger.jsonl#100001"
    started = time.monotonic()
    hits, total = transcripts.collect(root, "transcript reach")
    elapsed = time.monotonic() - started
    assert [hit["pointer"] for hit in hits] == ["Ledger.jsonl#100001"]
    assert total == 1
    assert elapsed < 60.0, (
        f"collecting a 100k-line ledger took {elapsed:.1f}s: the structural proof above "
        "(read_text/read_bytes refuse) is the contract; this bound only catches a reader "
        "that re-scans the file per line on a loaded CI runner"
    )


def test_context_find_scope_transcripts_is_additive(tmp_path: Path, cli, capsys) -> None:
    root = team_tree(tmp_path)
    monkeypatch_env = pytest.MonkeyPatch()
    monkeypatch_env.setenv("TEAMWORK_ROOT", str(root))
    try:
        assert cli("context", "find", "transcript reach lane") == 0
        default_out = capsys.readouterr().out
        assert cli("context", "find", "transcript reach lane", "--scope", "transcripts") == 0
        scope_out = capsys.readouterr().out
    finally:
        monkeypatch_env.undo()
    assert "Ledger.jsonl#1" in scope_out
    assert "Agents/Developer/WorkLog.md:3" in scope_out
    assert "# search:" in scope_out
    assert "Ledger.jsonl#1" not in default_out
    assert default_out.startswith("# no context node matched")


def test_recall_transcripts_is_additive(tmp_path: Path, cli, capsys) -> None:
    root = team_tree(tmp_path)
    (root / config.DIR_ROLES / "Developer").mkdir(parents=True)
    (root / config.DIR_ROLES / "Developer" / config.F_SHORT).write_text(
        "# Short-term memory - developer\n\n"
        "## M-0001 \u00b7 transcript lane\n- importance: 3\n\n"
        "The transcript reach lane is open.\n",
        encoding="utf-8",
    )
    monkeypatch_env = pytest.MonkeyPatch()
    monkeypatch_env.setenv("TEAMWORK_ROOT", str(root))
    try:
        assert cli("recall", "transcript reach lane", "--agent", "developer") == 0
        default_out = capsys.readouterr().out
        assert cli("recall", "transcript reach lane", "--agent", "developer", "--transcripts") == 0
        with_flag = capsys.readouterr().out
    finally:
        monkeypatch_env.undo()
    assert f"## developer / {config.F_SHORT}" in default_out
    assert with_flag.startswith(default_out)
    assert f"## {transcripts.SCOPE} / {transcripts.SOURCES}" in with_flag
    assert "Ledger.jsonl#1" in with_flag
    assert "Ledger.jsonl#1" not in default_out
