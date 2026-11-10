"""Unit tests for the memory index header (``docs/Team/Memory.md`` 11).

The index is the small top layer of the memory hierarchy: a capped pointer list
printed before the pack, never a copy of a statement. These cases pin the frozen
shape line for line, the 8-line and 800-byte caps, determinism, the empty store,
which records may contribute a topic, that a topic is clipped to a phrase, and that
``load`` opens with the index before the pack. The last two cases pin AC-M22-4 on
the *whole* command output: ``load`` prints the index instead of the verbose
lesson rows, so the total bytes stay at or under a literal baseline captured from
the pre-index renderer (90502bb) on the same fixture store, and the index is
charged against the pack budget so ``index + pack <= PACK_BUDGET_BYTES``. The
zero-open-lesson case pins the bounded half of AC-M22-4 the D-0009 ruling
requires: there the index displaces nothing, so it may add at most
``INDEX_BUDGET_BYTES`` and no more. Every case is a pure call on a hand-built
store except the AC-M22-4 cases, which drive the CLI in-process.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from teamwork import config, engine, memorypack, records

NOW = datetime.datetime(2026, 11, 7, 12, 0, 0)
EVIDENCE = "pytest tests/unit/test_memory_index.py @abc1234 -> 6 passed"


def team(tmp_path: Path) -> Path:
    """A bare team tree with one role directory, so the two stores resolve."""
    root = tmp_path / "team"
    (root / "Roles" / "Developer").mkdir(parents=True)
    return root


def add_knowledge(
    root: Path,
    topic: str,
    statement: str = "a durable fact about the tree",
    *,
    status: str = "active",
    importance: int = 3,
    uses: int = 0,
    updated: str = "2026-11-07",
) -> str:
    path = root / config.F_KNOWLEDGE
    items = records.parse_knowledge(path)
    item = records.new_knowledge(
        topic, statement, EVIDENCE, "Dev", "developer", importance=importance
    )
    item["id"] = records.next_id(items, "K-")
    item["status"] = status
    item["uses"] = uses
    item["created"] = updated
    item["updated"] = updated
    items.append(item)
    records.write_knowledge(path, items)
    return records.parse_knowledge(path)[-1]["id"]


def add_lesson(
    root: Path,
    role: str,
    mistake: str,
    rule: str,
    *,
    status: str = "open",
    updated: str = "2026-11-07",
) -> str:
    path = root / "Roles" / role.capitalize() / config.F_LESSONS
    items = records.parse_lessons(path)
    item = records.new_lesson(role.lower(), mistake, "the guard was skipped", rule, EVIDENCE, "Dev")
    item["id"] = records.next_id(items, "L-")
    item["status"] = status
    item["created"] = updated
    item["updated"] = updated
    items.append(item)
    records.write_lessons(path, items)
    return records.parse_lessons(path)[-1]["id"]


def block_bytes(text: str) -> int:
    """The bytes the block costs when injected: every line, newline included."""
    return len(text.encode("utf-8")) + 1


def test_index_is_the_frozen_shape_line_for_line(tmp_path: Path) -> None:
    root = team(tmp_path)
    kid = add_knowledge(root, "Lock Steal Protocol", importance=5, uses=5)
    text = memorypack.index_block(root, "Developer", "lock steal", now=NOW)
    lines = text.splitlines()
    assert lines[0] == "# memory index: 1 topic(s), 1 record(s)"
    assert lines[1] == f"- lock steal protocol -> Knowledge.md#{kid}"
    assert lines[2] == f"# index: {block_bytes(text)} bytes (budget 800)"
    assert len(lines) == 3


def test_index_of_an_empty_store_is_zero_and_still_fits(tmp_path: Path) -> None:
    root = team(tmp_path)
    text = memorypack.index_block(root, "Developer", "", now=NOW)
    lines = text.splitlines()
    assert lines[0] == "# memory index: 0 topic(s), 0 record(s)"
    assert len(lines) == 2
    assert lines[1] == f"# index: {block_bytes(text)} bytes (budget 800)"
    assert block_bytes(text) <= memorypack.INDEX_BUDGET_BYTES


def test_index_caps_at_eight_topic_lines(tmp_path: Path) -> None:
    root = team(tmp_path)
    for number in range(12):
        add_knowledge(root, f"topic {number}", importance=1)
    text = memorypack.index_block(root, "Developer", "", now=NOW)
    lines = text.splitlines()
    assert lines[0] == "# memory index: 8 topic(s), 12 record(s)"
    assert len(lines) == 2 + memorypack.INDEX_MAX_LINES


def test_index_stays_inside_its_budget_without_splitting_a_line(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "short topic", importance=5, uses=5)
    for number in range(9):
        topic = f"aaaaaaaaa bbbbbbbbb ccccccccc ddddddddd eeeeeeeee fffffff{number}"
        add_lesson(root, "Developer", topic, "a rule")
    text = memorypack.index_block(root, "Developer", "", now=NOW)
    assert block_bytes(text) <= memorypack.INDEX_BUDGET_BYTES
    assert "short topic" in text
    lines = text.splitlines()
    assert len(lines) - 2 <= memorypack.INDEX_MAX_LINES
    assert text.splitlines()[0] == f"# memory index: {len(lines) - 2} topic(s), 10 record(s)"
    assert all(line.startswith("- ") and " -> " in line for line in lines[1:-1])


def test_a_lesson_topic_is_a_phrase_not_a_sentence(tmp_path: Path) -> None:
    """A topic is a label: clipped to TOPIC_CLIP at a word boundary, no dangling ellipsis."""
    root = team(tmp_path)
    mistake = (
        "i classified a source with no access date as drifted, and shipped a --focus flag"
        " that belongs to t-0055's frozen 9.1 surface"
    )
    add_lesson(root, "Developer", mistake, "a rule")
    text = memorypack.index_block(root, "Developer", "", now=NOW)
    line = next(item for item in text.splitlines() if item.startswith("- "))
    topic = line[2:].split(" -> ")[0]
    assert len(topic) <= memorypack.TOPIC_CLIP
    assert topic == mistake[: len(topic)]
    assert mistake[len(topic)] == " "
    assert not topic.endswith(("...", "\u2026", ",", " "))
    assert mistake not in text


def test_index_is_deterministic(tmp_path: Path) -> None:
    root = team(tmp_path)
    for number in range(5):
        add_knowledge(root, f"topic {number}", importance=number)
    add_lesson(root, "Developer", "a mistake", "a rule")
    first = memorypack.index_block(root, "Developer", "topic", now=NOW)
    assert memorypack.index_block(root, "Developer", "topic", now=NOW) == first
    assert memorypack.index_block(root, "Developer", "topic") == memorypack.index_block(
        root, "Developer", "topic"
    )


def test_index_lists_active_knowledge_and_open_lessons_only(tmp_path: Path) -> None:
    root = team(tmp_path)
    add_knowledge(root, "live fact")
    add_knowledge(root, "parked fact", status="superseded")
    add_lesson(root, "Developer", "open mistake", "a rule")
    add_lesson(root, "Developer", "fixed mistake", "a rule", status="fixed")
    text = memorypack.index_block(root, "Developer", "", now=NOW)
    assert "live fact" in text
    assert "open mistake" in text
    assert "parked fact" not in text
    assert "fixed mistake" not in text
    assert text.splitlines()[0] == "# memory index: 2 topic(s), 2 record(s)"


def test_load_opens_with_the_index_before_the_pack(cli, project, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1", "--task", "T-0001") == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0].startswith("# memory index: ")
    assert lines[0].endswith(" topic(s), 0 record(s)")
    assert any(line.startswith("# memory pack for") for line in lines)
    assert out.index("# memory index: ") < out.index("# memory pack for")


FIXTURE_KNOWLEDGE = (
    (
        "Preflight gate working tree",
        "The preflight gate runs on the working tree, not the pushed SHA.",
        5,
    ),
    (
        "Privacy scan store coverage",
        "The privacy scan covers every record store, not only Knowledge.md.",
        4,
    ),
    ("Archive render bare urls", "The archive render strips bare urls from the evidence cell.", 3),
)
FIXTURE_LESSONS = (
    "i measured the injected portion instead of the whole load output, so the index bytes looked free",
    "i merged my own branch before the reviewer signed off, and the finding arrived after the merge",
    "i trusted the editor diagnostics instead of the cli, and the type error reached the gate run",
    "i rewrote a shared history to fix an author name instead of recording the exception",
    "i claimed the suite was green without running it, and the reviewer found the red case",
)
LOAD_BASELINE_BYTES = 1827
"""Literal bytes of `load Developer-1` on the store fixture_team() builds, rendered
by the pre-index engine at 90502bb: build the fixture, then run
`python3 .pi/Scratch/ceo/baseline/scripts/teamwork.py --project <fixture> load
Developer-1 | wc -c` -> 1827. The assertion below has zero slack, so a single
added line fails it."""


def fixture_team(cli, project: Path) -> None:
    """The store the byte baseline was captured on, built through the same CLI calls."""
    assert cli("--project", project, "init", "--agents", "developer-1", "--no-git") == 0
    for topic, statement, importance in FIXTURE_KNOWLEDGE:
        assert (
            cli(
                "--project",
                project,
                "knowledge",
                "add",
                "--by",
                "Developer-1",
                "--topic",
                topic,
                "--statement",
                statement,
                "--evidence",
                "pytest @abc1234 -> 3 passed",
                "--importance",
                str(importance),
            )
            == 0
        )
    for mistake in FIXTURE_LESSONS:
        assert (
            cli(
                "--project",
                project,
                "lesson",
                "add",
                "--by",
                "Developer-1",
                "--mistake",
                mistake,
                "--cause",
                "the gate measured the block, not the command",
                "--rule",
                "measure the whole command output",
                "--evidence",
                "pytest @abc1234 -> 3 passed",
            )
            == 0
        )


def test_whole_load_output_does_not_exceed_the_pre_index_baseline(cli, project, capsys) -> None:
    """AC-M22-4: the index is net-negative in the whole `load` output.

    LOAD_BASELINE_BYTES = 1827 is the literal byte count of `load Developer-1` on
    exactly the store ``fixture_team()`` builds, rendered by the pre-index engine at
    90502bb: build the fixture, then run
    ``python3 .pi/Scratch/ceo/baseline/scripts/teamwork.py --project <fixture> load
    Developer-1 | wc -c`` -> 1827. There is no slack, so the guard bites on any
    growth; the earlier 2804 pin left 883 bytes of room and would have passed an
    output that grew by the index's own size. The index replaces the verbose
    ``- [L-0001] mistake -> rule`` rows *and* the five-line preamble, which is now
    two lines of counts and commands, so the whole command stays under that number.
    """
    fixture_team(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1") == 0
    out = capsys.readouterr().out
    assert "# memory index: " in out
    assert "- [L-0001]" not in out
    assert len(out.encode("utf-8")) <= LOAD_BASELINE_BYTES
    # The second half of the same finding: the preamble the index displaces is two
    # lines (counts, commands), not five, so a role with nothing to displace still
    # comes out ahead. Counted between the index footer and the first blank line.
    lines = out.splitlines()
    footer = next(i for i, line in enumerate(lines) if line.startswith("# index: "))
    preamble = []
    for line in lines[footer + 1 :]:
        if not line.strip():
            break
        preamble.append(line)
    assert len(preamble) <= 2, preamble


LOAD_BASELINE_NO_LESSON_BYTES = 1137
"""Literal bytes of `load Developer-1` on the zero-open-lesson store
``fixture_team_without_lessons()`` builds, rendered by the pre-index engine at
90502bb: build the fixture, then run
`python3 .pi/Scratch/ceo/baseline/scripts/teamwork.py --project <fixture> load
Developer-1 | wc -c` -> 1137. The bound below is this literal plus one index
budget and nothing else, so growth past a single index fails it."""


def fixture_team_without_lessons(cli, project: Path) -> None:
    """``fixture_team()``'s store with every lesson left out.

    This is the case the D-0009 ruling carves out: the role has knowledge records
    to index but zero open lessons, so the index has no verbose ``- [L-...]`` rows
    to displace and is pure growth against the preamble it saves.
    """
    assert cli("--project", project, "init", "--agents", "developer-1", "--no-git") == 0
    for topic, statement, importance in FIXTURE_KNOWLEDGE:
        assert (
            cli(
                "--project",
                project,
                "knowledge",
                "add",
                "--by",
                "Developer-1",
                "--topic",
                topic,
                "--statement",
                statement,
                "--evidence",
                "pytest @abc1234 -> 3 passed",
                "--importance",
                str(importance),
            )
            == 0
        )


def test_a_role_with_no_open_lessons_stays_within_the_index_budget(cli, project, capsys) -> None:
    """AC-M22-4(e): with no open lessons the index adds at most INDEX_BUDGET_BYTES.

    LOAD_BASELINE_NO_LESSON_BYTES = 1137 is the literal byte count of `load
    Developer-1` on exactly the store ``fixture_team_without_lessons()`` builds,
    rendered by the pre-index engine at 90502bb: build the fixture, then run
    ``python3 .pi/Scratch/ceo/baseline/scripts/teamwork.py --project <fixture> load
    Developer-1 | wc -c`` -> 1137. Nothing is displaced here, so the ruling's bound
    is that literal plus one index budget - no slack beyond it - and the same run
    still charges the index against ``PACK_BUDGET_BYTES`` with a task given.
    """
    fixture_team_without_lessons(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1") == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    footer = next(i for i, line in enumerate(lines) if line.startswith("# index: "))
    index_lines = lines[:footer]
    # (b) the index's own caps, measured on the block itself rather than trusted
    # from the footer number it prints.
    assert block_bytes("\n".join(index_lines)) <= memorypack.INDEX_BUDGET_BYTES
    assert len([line for line in index_lines if line.startswith("- ")]) <= (
        memorypack.INDEX_MAX_LINES
    )
    assert "- [L-" not in out  # the fixture really has no open lesson rows
    # (e) the whole command output: baseline + one index budget, no slack.
    assert len(out.encode("utf-8")) <= LOAD_BASELINE_NO_LESSON_BYTES + memorypack.INDEX_BUDGET_BYTES
    # (c) the index is still charged against the pack budget on a task run.
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1", "--task", "T-0001") == 0
    tasked = capsys.readouterr().out
    index = int(re.search(r"# index: (\d+) bytes", tasked).group(1))
    pack = int(re.search(r"# pack: \d+ record\(s\), (\d+) bytes", tasked).group(1))
    assert index + pack <= memorypack.PACK_BUDGET_BYTES


def test_record_writes_do_not_depend_on_another_test_importing_the_engine() -> None:
    """The store mask is installed by this module's own import, not by test order.

    ``records.write_knowledge`` refuses to write an unmasked record until
    ``teamwork.engine`` has installed the mask, so this file has to import the
    engine itself: run alone it must not rely on another module having done it.
    """
    assert records._MASK is engine.mask_secret_shapes


def test_index_and_pack_share_one_budget(cli, project, capsys) -> None:
    """The second guard on AC-M22-4: index + pack <= PACK_BUDGET_BYTES."""
    fixture_team(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "load", "Developer-1", "--task", "T-0001") == 0
    out = capsys.readouterr().out
    index = int(re.search(r"# index: (\d+) bytes", out).group(1))
    pack, pack_budget = (
        int(value)
        for value in re.search(
            r"# pack: \d+ record\(s\), (\d+) bytes \(budget (\d+)\)", out
        ).groups()
    )
    assert pack_budget == memorypack.PACK_BUDGET_BYTES - index
    assert index + pack <= memorypack.PACK_BUDGET_BYTES
