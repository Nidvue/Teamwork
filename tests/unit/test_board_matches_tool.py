"""`docs/Team/Board.md` must equal the shared role queues, row for row.

The comparison and the renderer live in the product - `teamwork.board`, driven by
`teamwork.py board --write` and `teamwork.py board --check` - because this file
skipped whenever the gitignored team tree was absent, which is CI and every fresh
clone (Tester audit TA-01/TA-07). This module keeps the synthetic cases that pin
the comparison logic where no tree is needed, and runs the live checks against the
checkout's own queues when they exist.

D-0025 and D-0026 were both the same defect: a board table that was correct when
it was written and stale by the time a reviewer read it, because the act of
submitting the board flipped the very row it reported. Five review rounds on
T-0002 failed on that one class, and neither `links` nor the release-consistency
gate can see it - a board that contradicts the tool passes both.

So the comparison is an executable invariant instead of a reviewer's diligence.
The tables are rendered from the queues and compared with what is committed: a row
that disagrees on state, PR or merged revision, a task with no row, a row naming no
task, or an In-flight table that is not exactly the open set fails with both sides
printed. `teamwork.py board --write` rewrites the committed file in place, so the
fix for a red `board --check` is that command, not a hand edit.

The synthetic tests below run everywhere and pin the comparison logic itself,
which is what keeps it honest where the tree is absent.

Every staffed role therefore needs an entry in both roster maps: a queue whose
role is unlisted used to reach the render path as `KeyError: 'technicalwriter'`,
which named a dict key instead of the missing role, so the documented repair
recipe could not run at all. An unlisted role now raises `UnknownRole` naming
itself and the two maps to extend.

The floor that separates this milestone's ids from an older one is the one filter
between the queues and the board, and it hid 10 open tasks: five floors were
spelled hyphenated while `queues()` looked them up folded (so they never applied),
and the rest were written for M9 ids that M11's re-numbered queues no longer
carry. `queues()` is the renderer's only view, so a record dropped there is
dropped from both sides of the comparison and the invariant cannot see it. The
floor therefore may only decide whether a *closed* record is history: an open task
is always in scope, the keys are folded the way the lookup spells them, and
`test_no_queued_task_is_silently_hidden` counts the raw queues instead of trusting
the view that does the hiding.

One row is exempt from both invariants, and only one kind: a task that is LANDING.
A committed board is a projection at render time, but the act of landing a PR flips
its own task from `review`/`doing` to `done` plus a merge revision, so no commit can
carry its own post-merge state - the merge that would make the row true does not
exist yet when the row is written. This is structural, not an author's error:
`projectmanager T-0003` read `doing` on the board and `done` + `cfba521` in the queue
with no defect behind the difference. So a landing task is excluded from both sides
(the CEO decision: "The board cannot contain its own post-merge state"), while every
other comparison stays strict - an open `todo`/`doing` task must still be visible and
equal, and a `done` task must still match when both sides say `done`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from teamwork.board import (
    DISPLAY,
    FLOOR,
    UnknownRole,
    board_rows,
    display_role,
    expected_row,
    flight_mismatches,
    in_flight,
    landing_keys,
    mismatches,
    norm_role,
    parse_queues,
    problems,
    queues,
    render,
    without_landing,
)
from teamwork.config import ROLE_PARENT

REPO = Path(__file__).resolve().parents[2]
TEAM_REL = Path(".pi") / "Teamwork" / "Teams" / "Teamwork"
BOARD = REPO / "docs" / "Team" / "Board.md"
OPEN = {"todo", "doing", "selfcheck", "review", "blocked"}
ROLE_CELL = re.compile(r"[a-z][a-z-]*")


def team_root() -> Path | None:
    override = os.environ.get("TEAMWORK_ROOT")
    for candidate in ([Path(override)] if override else []) + [REPO / TEAM_REL]:
        if (candidate / "Roles").is_dir():
            return candidate
    return None


def live_root() -> Path:
    """This checkout's team tree, or a skip - the queues are gitignored state.

    The `assert` narrows `team_root()` for a checker that cannot see that
    `pytest.skip` does not return; it is unreachable at runtime.
    """
    root = team_root()
    if root is None:
        pytest.skip("no local team tree in this checkout (gitignored working state)")
    assert root is not None
    return root


def live_tasks() -> dict[tuple[str, str], dict[str, str]]:
    """The milestone's tasks from this checkout's queues, or a skip when empty."""
    tasks = queues(live_root())
    if not tasks:
        pytest.skip("no shared role queues in the local team tree")
    return tasks


def test_the_board_rows_equal_the_queues() -> None:
    tasks = live_tasks()
    text = BOARD.read_text(encoding="utf-8")
    assert not mismatches(tasks, board_rows(text)), mismatches(tasks, board_rows(text))


def test_the_in_flight_table_is_exactly_the_open_set() -> None:
    tasks = live_tasks()
    board = BOARD.read_text(encoding="utf-8")
    landing = landing_keys(tasks, board_rows(board), in_flight(board))
    found = flight_mismatches(tasks, in_flight(board), board_rows(board))
    assert not found, found
    rest = {key: fields for key, fields in tasks.items() if key not in landing}
    stable = without_landing(board, landing)
    assert not flight_mismatches(rest, in_flight(stable), board_rows(stable)), "In flight drifted"
    assert render(rest, stable) == stable, "the board is not what a regeneration writes"


def test_the_product_check_accepts_a_rendered_board() -> None:
    tasks = {
        ("ceo", "T-0059"): {"status": "done", "pr": "P-0069", "merge_commit": "3078c48"},
        ("tester", "T-0003"): {"status": "doing", "title": "acceptance proof", "priority": "P1"},
    }
    board = render(tasks, _board())
    assert problems(tasks, board) == []


def test_the_product_check_names_a_stale_cell() -> None:
    tasks = {
        ("ceo", "T-0059"): {"status": "done", "pr": "P-0069", "merge_commit": "3078c48"},
        ("tester", "T-0003"): {"status": "doing", "title": "acceptance proof", "priority": "P1"},
    }
    board = render(tasks, _board()).replace(
        "| ceo | T-0059 | - | done | P-0069 | 3078c48 |", "| ceo | T-0059 | - | todo | - | - |"
    )
    found = problems(tasks, board)
    assert (
        "ceo T-0059: board says ('todo', '-', '-'), queue says ('done', 'P-0069', '3078c48')"
        in (found)
    )


def test_the_product_check_sees_a_duplicated_in_flight_row() -> None:
    """The row comparators dedupe; only the render equality sees a doubled line."""
    tasks = {
        ("tester", "T-0003"): {"status": "doing", "title": "acceptance proof", "priority": "P1"}
    }
    row = "| tester | T-0003 acceptance proof | P1 | doing | - |"
    board = render(tasks, _board()).replace(row + "\n", row + "\n" + row + "\n")
    found = problems(tasks, board)
    assert found, "a duplicated In-flight row slipped through the check"
    assert any("T-0003" in line for line in found), found


def test_the_comparison_bites_on_a_stale_row() -> None:
    """The synthetic half: this logic runs in CI, where the team tree is absent."""
    tasks = {
        ("developer", "T-0005"): {"status": "done", "pr": "P-0001", "merge_commit": "abc1234"},
        # a task mid-work, not landing: open on both sides, one side stale
        ("tester", "T-0003"): {"status": "doing", "pr": "P-0002"},
        ("ceo", "T-0059"): {"status": "doing"},
    }
    rows = {
        ("developer", "T-0005"): ("done", "P-0001", "abc1234"),
        # a stale row that no landing can explain: still todo after the claim
        ("tester", "T-0003"): ("todo", "-", "-"),
        # a board row for a task that does not exist
        ("reviewer", "T-0009"): ("done", "-", "-"),
    }
    found = mismatches(tasks, rows)
    assert (
        "tester T-0003: board says ('todo', '-', '-'), queue says ('doing', 'P-0002', '-')" in found
    )
    assert "ceo T-0059: in the queue as ('doing', '-', '-'), absent from the board" in found
    assert "reviewer T-0009: on the board, but no such task in the milestone" in found

    flight = {("tester", "T-0003"): "todo", ("release-engineer", "T-0008"): "todo"}
    found = flight_mismatches(tasks, flight, rows)
    assert "tester T-0003: In flight says 'todo', the queue says 'doing'" in found
    assert "ceo T-0059: open in the queue as 'doing', missing from In flight" in found
    assert (
        "release-engineer T-0008: listed In flight as 'todo', but its queue status is not open"
        in found
    )


def test_a_landing_task_is_excluded_and_a_drift_is_not() -> None:
    """The structural exemption, pinned in the three directions that could go wrong.

    (a) a landing task does not fail either invariant; (b) a genuinely drifted task
    that is not landing still fails; (c) a done-vs-doing drift on a task with no
    landing evidence - the same two states as `projectmanager T-0003` - still fails,
    so the exemption cannot be used to wave through a stale board.
    """
    # (a) the measured shape: the row rendered while P-0016 was open, queue merged
    landed = {
        ("projectmanager", "T-0003"): {"status": "done", "pr": "P-0016", "merge_commit": "cfba521"}
    }
    stale_row = {("projectmanager", "T-0003"): ("doing", "P-0016", "-")}
    assert mismatches(landed, stale_row) == []
    assert flight_mismatches(landed, {("projectmanager", "T-0003"): "doing"}, stale_row) == []
    # (a) the earlier window: the queue is at review, the board still says doing
    assert (
        mismatches(
            {("tester", "T-0004"): {"status": "review", "pr": "P-0003"}},
            {("tester", "T-0004"): ("doing", "P-0003", "-")},
        )
        == []
    )
    # (b) a non-landing task that really drifted: open on both sides, states differ
    assert mismatches(
        {("tester", "T-0006"): {"status": "doing"}}, {("tester", "T-0006"): ("todo", "-", "-")}
    ) == ["tester T-0006: board says ('todo', '-', '-'), queue says ('doing', '-', '-')"]
    # (c) done in the queue, doing on the board, and no merge record either side
    assert mismatches(
        {("ceo", "T-0002"): {"status": "done"}}, {("ceo", "T-0002"): ("doing", "-", "-")}
    ) == ["ceo T-0002: board says ('doing', '-', '-'), queue says ('done', '-', '-')"]
    # (c) the same two states, but the two sides name different PRs: two PRs is not
    # one PR observed twice, so this is a drift and not a landing
    assert mismatches(
        {("ceo", "T-0004"): {"status": "done", "pr": "P-0001", "merge_commit": "abc1234"}},
        {("ceo", "T-0004"): ("doing", "P-0009", "-")},
    ) == [
        "ceo T-0004: board says ('doing', 'P-0009', '-'), queue says ('done', 'P-0001', 'abc1234')"
    ]


def test_an_empty_field_is_a_dash_not_a_value() -> None:
    tasks = {("developer", "T-0005"): {"status": "done"}}
    assert expected_row(tasks[("developer", "T-0005")]) == ("done", "-", "-")
    found = mismatches(tasks, {("developer", "T-0005"): ("done", "P-0001", "-")})
    assert found == [
        "developer T-0005: board says ('done', 'P-0001', '-'), queue says ('done', '-', '-')"
    ]


def test_the_floor_is_keyed_the_way_the_lookup_spells_it() -> None:
    """Five floors were spelled hyphenated, so `FLOOR.get('securityauditor')` was 0."""
    assert set(FLOOR) == {norm_role(role) for role in FLOOR}, sorted(FLOOR)
    for role in FLOOR:
        assert FLOOR[role] > 0, role
        assert FLOOR.get(norm_role(role), 0) == FLOOR[role], role


def test_a_stale_floor_cannot_hide_an_open_task(tmp_path: Path, monkeypatch) -> None:
    """The regression: an M9 floor must not be able to hide an M11 task."""
    queue = tmp_path / "Roles" / "CEO" / "TaskQueue.md"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        "## T-0001 the P0 intake, open under a stale floor\n- status: doing\n"
        "## T-0058 a closed M9-era record\n- status: done\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(FLOOR, "ceo", 59)
    found = queues(tmp_path)
    assert ("ceo", "T-0001") in found, "an open task was hidden by a stale floor"
    assert ("ceo", "T-0058") not in found, "a closed record below the floor is history"
    assert parse_queues(tmp_path)[("ceo", "T-0058")]["status"] == "done"


def test_no_queued_task_is_silently_hidden() -> None:
    """Every task in every queue reaches the board, or this fails naming it.

    The floor is the one filter between the queues and the board, and `queues()` is
    the renderer's only view of them, so a record dropped there is dropped from both
    sides of the comparison and no assertion in this file can see it - which is how
    the board went on claiming to be the queues' state while hiding 10 open tasks.
    So this counts the raw queues and the open set independently of that view.
    """
    raw = parse_queues(live_root())
    hidden = sorted(set(raw) - set(queues(live_root())))
    assert not hidden, hidden
    board = BOARD.read_text(encoding="utf-8")
    rows, flight = board_rows(board), in_flight(board)
    open_ids = {key for key, fields in raw.items() if fields.get("status") in OPEN}
    assert not open_ids - set(rows), sorted(open_ids - set(rows))
    assert not open_ids - set(flight), sorted(open_ids - set(flight))


def test_the_regeneration_round_trips() -> None:
    """`render` must be idempotent on its own output, or the fix would churn."""
    tasks = {
        ("ceo", "T-0059"): {"status": "done", "pr": "P-0069", "merge_commit": "3078c48"},
        ("tester", "T-0003"): {"status": "doing", "title": "acceptance proof"},
    }
    board = _board()
    once = render(tasks, board)
    assert "| ceo | T-0059 | - | done | P-0069 | 3078c48 |" in once
    assert "| tester | T-0003 | - | doing | - | - |" in once
    assert "| tester | T-0003 acceptance proof | - | doing | - |" in once
    assert "| ceo | T-0059 stale title |" not in once
    assert render(tasks, once) == once


def _board() -> str:
    """A board carrying both tables under their headings, every other section one line."""
    return "\n".join(
        [
            "# BOARD",
            "",
            "| role | id | area | state | pr | merged revision |",
            "|---|---|---|---|---|---|",
            "| ceo | T-0059 | - | todo | - | - |",
            "",
            "Rows whose PR is not merged carry no merged revision.",
            "",
            "## In flight",
            "",
            "| agent | task | prio | state | artifact |",
            "|---|---|---|---|---|",
            "| ceo | T-0059 stale title | P0 | todo | somewhere |",
            "",
            "The task queue (`teamwork.py task list ceo`) is authoritative.",
            "",
        ]
    )


def test_the_full_roster_renders() -> None:
    """Every staffed role has a board spelling, so the recipe cannot KeyError.

    The defect this pins: `technical-writer` was queued while DISPLAY and FLOOR
    still listed only the older roles, so the repair recipe documented for this
    module died on `KeyError: 'technicalwriter'` - the render path could not run at
    all, whatever the queues said. Both directions are covered: the whole roster
    renders, and a role that is not on it is named.
    """
    tasks = {
        (folded, "T-0001"): {"status": "doing", "title": "a task", "priority": "P1"}
        for folded in DISPLAY
    }
    once = render(tasks, _board())
    for folded, spelled in DISPLAY.items():
        assert f"| {spelled} | T-0001 |" in once, folded
        assert f"| {spelled} | T-0001 a task | P1 | doing | - |" in once, folded
    assert "| technical-writer | T-0001 |" in once


def test_an_unknown_role_is_named_and_not_a_bare_keyerror() -> None:
    tasks = {("chiefofstaff", "T-0001"): {"status": "doing"}}
    with pytest.raises(UnknownRole) as caught:
        render(tasks, _board())
    message = str(caught.value)
    assert "chiefofstaff" in message
    assert "DISPLAY" in message and "FLOOR" in message
    assert not isinstance(caught.value, KeyError)
    with pytest.raises(UnknownRole, match="chiefofstaff"):
        display_role("ChiefOfStaff")


def test_display_and_floor_list_the_same_roster() -> None:
    """One map without the other is how a queued role becomes unrenderable."""
    assert {norm_role(role) for role in DISPLAY} == {norm_role(role) for role in FLOOR}
    assert display_role("TechnicalWriter") == display_role("technical-writer")


def test_every_staffable_role_has_a_board_spelling() -> None:
    """`config.ROLE_PARENT` is the roster; both maps must name every role on it.

    No team tree is needed, because the comparison is between the two constants and
    the engine's own role list - so the check runs in CI and on a fresh clone. A
    roster that gained a role without a board spelling used to fail only when a
    team tree happened to staff it: `designer` was staffed and queued while DISPLAY
    listed the older roles, and `board --check`/`--write` then exited 2 for the
    whole team on `UnknownRole`. A misspelt value is the same defect in a quieter
    form - `board_rows()` folds the committed cell back with `norm_role()`, so a row
    whose fold does not reproduce its role is unfindable even though it renders.
    """
    roster = {norm_role(role) for role in ROLE_PARENT}
    unspelled = sorted(roster - set(DISPLAY))
    unfloored = sorted(roster - set(FLOOR))
    assert not unspelled, f"staffable role(s) with no board spelling in DISPLAY: {unspelled}"
    assert not unfloored, f"staffable role(s) with no milestone floor in FLOOR: {unfloored}"
    assert set(DISPLAY) == roster, sorted(set(DISPLAY) ^ roster)
    assert set(FLOOR) == roster, sorted(set(FLOOR) ^ roster)
    for folded in sorted(roster):
        spelled = DISPLAY[folded]
        assert ROLE_CELL.fullmatch(spelled), (
            f"{folded!r} renders as {spelled!r}, which is not a role cell a board row can carry"
        )
        assert norm_role(spelled) == folded, (
            f"{folded!r} renders as {spelled!r}, which folds back to {norm_role(spelled)!r}"
        )


def test_every_queued_role_has_a_board_spelling() -> None:
    """A new queue directory must not wait for a red regeneration to be noticed."""
    present = {
        norm_role(path.parent.name) for path in (live_root() / "Roles").glob("*/TaskQueue.md")
    }
    if not present:
        pytest.skip("no shared role queues in the local team tree")
    assert not present - set(DISPLAY), sorted(present - set(DISPLAY))
    assert not present - {norm_role(role) for role in FLOOR}, sorted(present)
