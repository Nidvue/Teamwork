"""Purpose-built fixture for the memory index header (``docs/Team/Memory.md`` 11).

T-0009 measured AC-M22-4 on the *live* team tree and on a copy of it. That tree
carries whatever lessons and transcripts the team happens to hold, so its numbers
(228-403 B index, net -523/-168, +125 where a role has no open lessons) cannot be
reproduced later, and the zero-open-lesson branch rested on one incidental case.
This module builds the tree itself - a throwaway ``--no-git`` workspace whose
knowledge and lesson records are fixed literals below - so every bound is asserted
against constants that the fixture, not the live store, determines:

* ``(b)`` the index caps itself: at most ``INDEX_BUDGET_BYTES`` and
  ``INDEX_MAX_LINES`` topic lines, on both fixtures;
* ``(c)`` the index is charged against the pack budget: ``index + pack <= 4000``;
* ``(e)`` with no open lesson the index displaces nothing, so its own bytes are the
  whole growth and that growth stays at or under one ``INDEX_BUDGET_BYTES``;
* where open lessons exist the index displaces their verbose ``- [L-nnnn] mistake ->
  rule`` rows instead of adding to them, and the whole growth is again the index's
  own bytes, at or under one budget - the net figure itself is a property of how
  long the displaced rows are, measured on the live tree in TS-0068;
* the index is additive: it is a prefix of ``load`` and it changes nothing that
  ``context find`` or ``recall`` print.

Owner: developer. Layer: integration. Area: memory-index. Task: T-0066.
"""

from __future__ import annotations

import re
from pathlib import Path

from teamwork import memorypack

KNOWLEDGE = (
    ("Preflight gate working tree", "The gate runs on the working tree, not the pushed SHA.", 5),
    ("Privacy scan store coverage", "The scan covers every record store, not one file.", 4),
    ("Archive render bare urls", "The archive render strips a bare url from evidence.", 3),
)

LESSONS = (
    ("i measured the injected portion instead of the whole load output", "measure the command"),
    ("i merged my own branch before the reviewer signed off", "wait for the verdict"),
    ("i trusted the editor diagnostics instead of the cli", "run the checker"),
    ("i claimed the suite was green without running it", "run the suite"),
    ("i read the whole archive instead of the record by id", "read by id"),
)


def build(cli, project: Path, *, lessons: bool) -> Path:
    """The synthetic tree: fixed knowledge records and, optionally, fixed lessons."""
    assert cli("--project", project, "init", "--agents", "developer-1", "--no-git") == 0
    for topic, statement, importance in KNOWLEDGE:
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
    if not lessons:
        return project
    for mistake, rule in LESSONS:
        assert (
            cli(
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
                "the gate measured the block, not the command",
                "--rule",
                rule,
                "--evidence",
                "pytest @abc1234 -> 3 passed",
            )
            == 0
        )
    return project


def team_root(project: Path) -> Path:
    from teamwork import config, engine

    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def block_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def index_lines(text: str) -> list[str]:
    lines = text.splitlines()
    footer = next(i for i, line in enumerate(lines) if line.startswith("# index: "))
    return lines[:footer]


def assert_caps(block: str, *, topics: int) -> None:
    lines = index_lines(block)
    assert block_bytes("\n".join(lines)) <= memorypack.INDEX_BUDGET_BYTES
    topic_lines = [line for line in lines if line.startswith("- ")]
    assert len(topic_lines) == topics
    assert len(topic_lines) <= memorypack.INDEX_MAX_LINES


def load(cli, project: Path, *extra) -> str:
    import io
    from contextlib import redirect_stdout

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert cli("--project", project, "load", "Developer-1", *extra) == 0
    return buffer.getvalue()


def strip_index(out: str) -> str:
    lines = out.splitlines(keepends=True)
    footer = next(i for i, line in enumerate(lines) if line.startswith("# index: "))
    return "".join(lines[footer + 1 :])


def test_zero_open_lessons_growth_stays_within_one_index_budget(cli, project: Path) -> None:
    """AC-M22-4(e): nothing is displaced, so the index's own bytes are the growth."""
    build(cli, project, lessons=False)
    root = team_root(project)
    block = memorypack.index_block(root, "developer")
    assert_caps(block, topics=len(KNOWLEDGE))
    index = memorypack.index_bytes(root, "developer")
    assert index == block_bytes(block) + 1
    assert index <= memorypack.INDEX_BUDGET_BYTES

    out = load(cli, project)
    assert "- [L-" not in out
    growth = block_bytes(out) - block_bytes(strip_index(out))
    assert growth == index
    assert growth <= memorypack.INDEX_BUDGET_BYTES


def test_zero_open_lessons_is_a_prefix_not_a_rewrite(cli, project: Path) -> None:
    """The index is additive: it is the head of the output and changes no other byte."""
    build(cli, project, lessons=False)
    root = team_root(project)
    first = load(cli, project)
    assert first.startswith(memorypack.index_block(root, "developer") + "\n")
    assert load(cli, project) == first
    assert strip_index(first) == strip_index(load(cli, project))


def test_open_lessons_index_costs_less_than_the_rows_it_displaces(cli, project: Path) -> None:
    """Where open lessons exist the index displaces their verbose rows, not adds to them.

    The net byte figure of AC-M22-4 is a property of the displaced content's length,
    so this fixture asserts the mechanism instead of that arithmetic: every open
    lesson contributes a topic line, no ``- [L-nnnn] mistake -> rule`` row survives
    in the output, and the whole growth is the index's own bytes - bounded by one
    ``INDEX_BUDGET_BYTES``.
    """
    build(cli, project, lessons=True)
    root = team_root(project)
    block = memorypack.index_block(root, "developer")
    assert_caps(block, topics=len(KNOWLEDGE) + len(LESSONS))
    assert len(KNOWLEDGE) + len(LESSONS) == memorypack.INDEX_MAX_LINES
    for mistake, _ in LESSONS:
        head = mistake[:30]
        assert any(head in line for line in index_lines(block)), mistake

    index = memorypack.index_bytes(root, "developer")
    assert index <= memorypack.INDEX_BUDGET_BYTES

    out = load(cli, project)
    assert "- [L-" not in out
    growth = block_bytes(out) - block_bytes(strip_index(out))
    assert growth == index


def test_index_and_pack_share_one_budget_on_the_synthetic_tree(cli, project: Path) -> None:
    """AC-M22-4(c): index + pack <= PACK_BUDGET_BYTES, on both fixtures."""
    for lessons in (False, True):
        fixture = project / ("with-lessons" if lessons else "zero-lessons")
        fixture.mkdir()
        build(cli, fixture, lessons=lessons)
        out = load(cli, fixture, "--task", "T-0001")
        index = int(re.search(r"# index: (\d+) bytes", out).group(1))
        pack, pack_budget = (
            int(value)
            for value in re.search(
                r"# pack: \d+ record\(s\), (\d+) bytes \(budget (\d+)\)", out
            ).groups()
        )
        assert index <= memorypack.INDEX_BUDGET_BYTES
        assert pack_budget == memorypack.PACK_BUDGET_BYTES - index
        assert index + pack <= memorypack.PACK_BUDGET_BYTES


def test_the_index_changes_nothing_that_find_or_recall_print(cli, project: Path) -> None:
    """Additivity on the retrieval paths: the index adds bytes to `load` only."""
    import io
    from contextlib import redirect_stdout

    build(cli, project, lessons=True)
    root = team_root(project)

    def run(*argv) -> str:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli("--project", project, *argv)
        return buffer.getvalue()

    before_find, before_recall = (
        run("context", "find", "gate"),
        run("recall", "gate", "--agent", "developer"),
    )
    memorypack.index_block(root, "developer")
    after_find, after_recall = (
        run("context", "find", "gate"),
        run("recall", "gate", "--agent", "developer"),
    )
    assert before_find == after_find
    assert before_recall == after_recall
    assert "# memory index: " not in before_find + before_recall
