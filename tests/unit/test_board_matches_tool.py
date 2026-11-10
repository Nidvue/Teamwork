"""`docs/Team/Board.md` must equal the shared role queues, row for row.

D-0025 and D-0026 were both the same defect: a board table that was correct when
it was written and stale by the time a reviewer read it, because the act of
submitting the board flipped the very row it reported. Five review rounds on
T-0002 failed on that one class, and neither `links` nor the release-consistency
gate can see it - a board that contradicts the tool passes both.

So the comparison is an executable invariant instead of a reviewer's diligence.
The tables are rendered from the queues by this file and compared with what is
committed: a row that disagrees on state, PR or merged revision, a task with no
row, a row naming no task, or an In-flight table that is not exactly the open set
fails with both sides printed. `python3 tests/unit/test_board_matches_tool.py`
rewrites the file in place, so the fix for a red run is to run it.

The queues live in the gitignored team tree, so the live checks skip in a fresh
clone and in CI. The synthetic tests below run everywhere and pin the comparison
logic itself, which is what keeps it honest where the tree is absent.

Every staffed role therefore needs an entry in both roster maps: a queue whose
role is unlisted used to reach this render path as `KeyError: 'technicalwriter'`,
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
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEAM_REL = Path(".pi") / "Teamwork" / "Teams" / "Teamwork"
BOARD = REPO / "docs" / "Team" / "Board.md"

TASK_RE = re.compile(r"^## (T-\d{4}) (.*)$")
FIELD_RE = re.compile(r"^- ([a-z_]+):[ \t]*([^\n]*)$")
OPEN = {"todo", "doing", "selfcheck", "review", "blocked"}
BOARD_ROW = re.compile(
    r"^\| ([a-z-]+) \| (T-\d{4}) \| ([^|]*) \| ([a-z]+) \| ([^|]*) \| ([^|]*) \|$", re.M
)
FLIGHT_ROW = re.compile(
    r"^\| ([a-z-]+) \| (T-\d{4}) (.*?) \| (P\d) \| ([a-z]+) \| ([^|]*) \|$", re.M
)
TABLE_HEAD = "| role | id | area | state | pr | merged revision |"
FLIGHT_HEAD = "| agent | task | prio | state | artifact |"

#: The board records one milestone's work, and task ids are allocated per role, so
#: the same number under two roles is two tasks. Each queue numbers from 1, so the
#: milestone needs a floor per role: ids at or above it are in this milestone and
#: everything below it is an older record that the board keeps as labelled history.
#: Listing the floor here is deliberate - a queue missing from this dict would
#: silently drop out of the comparison, which is the failure this file prevents.
#:
#: Two stale floors made that filter lie. M11 re-initialised the queues, so every
#: one of them was re-numbered from `T-0001` and the M9 ids survive only in the
#: board's own close-record table; the floors still read as M9 (`ceo: 59`, ...) and
#: hid all nine ceo tasks, P0 `developer T-0004` and P0 `reviewer T-0001`. Five keys
#: were also spelled hyphenated while `queues()` looks them up through
#: `norm_role()`, so `FLOOR.get("securityauditor")` was `0` and those floors never
#: applied at all. Every floor is now 1 - no queue carries a pre-milestone id - and
#: the keys are folded, which `test_the_floor_is_keyed_the_way_the_lookup_spells_it`
#: pins. The dict stays because it is the roster the render order shares.
FLOOR = {
    "architect": 1,
    "ceo": 1,
    "cto": 1,
    "developer": 1,
    "productmanager": 1,
    "projectmanager": 1,
    "releaseengineer": 1,
    "reviewer": 1,
    "securityauditor": 1,
    "technicalwriter": 1,
    "tester": 1,
}

#: The folded queue directory name -> the hyphenated spelling the board's rows use.
#: This is the roster: every role with a `Roles/*/TaskQueue.md` must appear here,
#: because the board cannot spell a role this dict has no name for.
DISPLAY = {
    "architect": "architect",
    "ceo": "ceo",
    "cto": "cto",
    "developer": "developer",
    "productmanager": "product-manager",
    "projectmanager": "project-manager",
    "releaseengineer": "release-engineer",
    "reviewer": "reviewer",
    "securityauditor": "security-auditor",
    "technicalwriter": "technical-writer",
    "tester": "tester",
}


def norm_role(name: str) -> str:
    """`SecurityAuditor`, `security-auditor` and `securityauditor` are one role."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class UnknownRole(ValueError):
    """A queue role that `DISPLAY` has no board spelling for.

    Not a `KeyError`: the message has to name the role and the maps to extend,
    because the reader of a failed regeneration needs the fix, not the dict lookup
    that produced it.
    """


def display_role(role: str) -> str:
    """The board's hyphenated spelling for a queue role, or an error naming it."""
    folded = norm_role(role)
    try:
        return DISPLAY[folded]
    except KeyError:
        raise UnknownRole(
            f"queue role {folded!r} has no board spelling: add {folded!r} to DISPLAY "
            f"(with its hyphenated spelling) and to FLOOR (with its milestone floor) "
            f"in {Path(__file__).name}"
        ) from None


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


def parse_queues(root: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Every record in the queues, keyed by (folded role, id), floor or no floor.

    The unfiltered view exists so a test can compare the board against the queues
    themselves rather than against `queues()`, which is the view that can hide a
    record from both sides of the comparison.
    """
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted((root / "Roles").glob("*/TaskQueue.md")):
        role = norm_role(path.parent.name)
        # A queue the board cannot spell is a defect in this file, so it fails here
        # naming the role instead of surfacing later as rows that are all absent.
        display_role(role)
        current: dict[str, str] | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            head = TASK_RE.match(line)
            if head:
                current = out.setdefault((role, head.group(1)), {})
                current["title"] = head.group(2).strip()
                continue
            if current is None:
                continue
            field = FIELD_RE.match(line)
            if field:
                current[field.group(1)] = field.group(2).strip()
    return out


def in_scope(key: tuple[str, str], fields: dict[str, str]) -> bool:
    """Whether a queue record belongs in this milestone's comparison.

    A task that is open is always in scope, whatever the floor says. That is the
    fix for the M9 floors outliving the M9 ids: a floor may decide only whether a
    *closed* record is history, never whether live work reaches the board.
    """
    if fields.get("status", "") in OPEN:
        return True
    return int(key[1][2:]) >= FLOOR.get(key[0], 1)


def queues(root: Path) -> dict[tuple[str, str], dict[str, str]]:
    """The milestone's tasks, keyed by (folded role, id), with their fields."""
    return {key: fields for key, fields in parse_queues(root).items() if in_scope(key, fields)}


def expected_row(fields: dict[str, str]) -> tuple[str, str, str]:
    """The board's cell for an empty field is `-`, never a blank or a guess."""
    return (
        fields.get("status", ""),
        fields.get("pr") or "-",
        fields.get("merge_commit") or "-",
    )


def board_rows(board: str) -> dict[tuple[str, str], tuple[str, str, str]]:
    return {
        (norm_role(role), tid): (state, pr.strip(), merged.strip())
        for role, tid, _area, state, pr, merged in BOARD_ROW.findall(board)
    }


def in_flight(board: str) -> dict[tuple[str, str], str]:
    start = board.index("## In flight")
    end = board.find("\n## ", start + 1)
    section = board[start:] if end == -1 else board[start:end]
    return {
        (norm_role(role), tid): state
        for role, tid, _title, _prio, state, _artifact in FLIGHT_ROW.findall(section)
    }


def mismatches(
    tasks: dict[tuple[str, str], dict[str, str]],
    rows: dict[tuple[str, str], tuple[str, str, str]],
) -> list[str]:
    """Both directions: a row that is wrong and a task that has no row."""
    out = []
    for key, fields in sorted(tasks.items()):
        want = expected_row(fields)
        got = rows.get(key)
        if got is None:
            out.append(f"{key[0]} {key[1]}: in the queue as {want}, absent from the board")
        elif got != want:
            out.append(f"{key[0]} {key[1]}: board says {got}, queue says {want}")
    for key in sorted(set(rows) - set(tasks)):
        out.append(f"{key[0]} {key[1]}: on the board, but no such task in the milestone")
    return out


def flight_mismatches(
    tasks: dict[tuple[str, str], dict[str, str]], flight: dict[tuple[str, str], str]
) -> list[str]:
    want = {
        key: fields.get("status", "")
        for key, fields in tasks.items()
        if fields.get("status") in OPEN
    }
    return (
        [
            f"{r} {t}: open in the queue as {want[(r, t)]!r}, missing from In flight"
            for r, t in sorted(set(want) - set(flight))
        ]
        + [
            f"{r} {t}: listed In flight as {flight[(r, t)]!r}, but its queue status is not open"
            for r, t in sorted(set(flight) - set(want))
        ]
        + [
            f"{r} {t}: In flight says {flight[(r, t)]!r}, the queue says {want[(r, t)]!r}"
            for r, t in sorted(set(flight) & set(want))
            if flight[(r, t)] != want[(r, t)]
        ]
    )


def render(tasks: dict[tuple[str, str], dict[str, str]], board: str) -> str:
    """Rewrite both tables from `tasks`, leaving every other section verbatim.

    It reuses the same accessors the assertions read through, so the generator and
    the check cannot disagree - a second implementation of the table shape is how
    this drifted in the first place. An In-flight row keeps its title, priority and
    artifact; only the agent and state cells are derived.
    """
    order = list(FLOOR)
    rows = sorted(
        tasks,
        key=lambda k: (order.index(k[0]) if k[0] in order else len(order), k[0], int(k[1][2:])),
    )
    table = [TABLE_HEAD, "|---|---|---|---|---|---|"]
    for key in rows:
        fields = tasks[key]
        table.append(
            "| "
            + " | ".join(
                [
                    display_role(key[0]),
                    key[1],
                    fields.get("area") or "-",
                    fields.get("status", ""),
                    fields.get("pr") or "-",
                    fields.get("merge_commit") or "-",
                ]
            )
            + " |"
        )
    lines = board.splitlines()
    start = lines.index(TABLE_HEAD)
    end = next(i for i, line in enumerate(lines) if line.startswith("Rows whose PR is not merged"))
    lines = lines[:start] + table + [""] + lines[end:]

    listed = {}
    for match in FLIGHT_ROW.findall(board):
        listed[(norm_role(match[0]), match[1])] = match
    flight = [FLIGHT_HEAD, "|---|---|---|---|---|"]
    for key in rows:
        fields = tasks[key]
        if fields.get("status") not in OPEN:
            continue
        old = listed.get(key)
        if old is not None:
            cells = [
                display_role(key[0]),
                f"{key[1]} {old[2]}".strip(),
                old[3],
                fields["status"],
                old[5],
            ]
        else:
            cells = [
                display_role(key[0]),
                f"{key[1]} {fields.get('title', '')}".strip(),
                fields.get("priority", "-"),
                fields["status"],
                "-",
            ]
        flight.append("| " + " | ".join(cells) + " |")
    i = lines.index(FLIGHT_HEAD)
    j = next(i for i, line in enumerate(lines) if line.startswith("The task queue (`teamwork.py"))
    return "\n".join(lines[:i] + flight + [""] + lines[j:]) + "\n"


def test_the_board_rows_equal_the_queues() -> None:
    tasks = live_tasks()
    rows = board_rows(BOARD.read_text(encoding="utf-8"))
    assert not mismatches(tasks, rows), mismatches(tasks, rows)


def test_the_in_flight_table_is_exactly_the_open_set() -> None:
    tasks = live_tasks()
    board = BOARD.read_text(encoding="utf-8")
    found = flight_mismatches(tasks, in_flight(board))
    assert not found, found
    assert render(tasks, board) == board, "the board is not what a regeneration writes"


def test_the_comparison_bites_on_a_stale_row() -> None:
    """The synthetic half: this logic runs in CI, where the team tree is absent."""
    tasks = {
        ("developer", "T-0005"): {"status": "done", "pr": "P-0001", "merge_commit": "abc1234"},
        ("tester", "T-0003"): {"status": "review", "pr": "P-0002"},
        ("ceo", "T-0059"): {"status": "doing"},
    }
    rows = {
        ("developer", "T-0005"): ("done", "P-0001", "abc1234"),
        # the row the submission itself flips: open in the queue, stale on the board
        ("tester", "T-0003"): ("doing", "-", "-"),
        # a board row for a task that does not exist
        ("reviewer", "T-0009"): ("done", "-", "-"),
    }
    found = mismatches(tasks, rows)
    assert (
        "tester T-0003: board says ('doing', '-', '-'), queue says ('review', 'P-0002', '-')"
        in found
    )
    assert "ceo T-0059: in the queue as ('doing', '-', '-'), absent from the board" in found
    assert "reviewer T-0009: on the board, but no such task in the milestone" in found

    flight = {("tester", "T-0003"): "doing", ("release-engineer", "T-0008"): "todo"}
    found = flight_mismatches(tasks, flight)
    assert "tester T-0003: In flight says 'doing', the queue says 'review'" in found
    assert "ceo T-0059: open in the queue as 'doing', missing from In flight" in found
    assert (
        "release-engineer T-0008: listed In flight as 'todo', but its queue status is not open"
        in found
    )


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
    board = "\n".join(
        [
            "# BOARD",
            "",
            TABLE_HEAD,
            "|---|---|---|---|---|---|",
            "| ceo | T-0059 | - | todo | - | - |",
            "",
            "Rows whose PR is not merged carry no merged revision.",
            "",
            FLIGHT_HEAD,
            "|---|---|---|---|---|",
            "| ceo | T-0059 stale title | P0 | todo | somewhere |",
            "",
            "The task queue (`teamwork.py task list ceo`) is authoritative.",
            "",
        ]
    )
    once = render(tasks, board)
    assert "| ceo | T-0059 | - | done | P-0069 | 3078c48 |" in once
    assert "| tester | T-0003 | - | doing | - | - |" in once
    assert "| tester | T-0003 acceptance proof | - | doing | - |" in once
    assert "| ceo | T-0059 stale title |" not in once
    assert render(tasks, once) == once


def _directory(root: Path, role: str) -> Path:
    for path in (root / "Roles").iterdir():
        if norm_role(path.name) == role:
            return path
    raise SystemExit(f"no queue directory for {role}")


def _skeleton() -> str:
    """A board carrying both tables, every other section one line."""
    return "\n".join(
        [
            "# BOARD",
            "",
            TABLE_HEAD,
            "|---|---|---|---|---|---|",
            "| ceo | T-0059 | - | todo | - | - |",
            "",
            "Rows whose PR is not merged carry no merged revision.",
            "",
            FLIGHT_HEAD,
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
    still listed only the older roles, so the repair recipe documented in this
    file's `__main__` block died on `KeyError: 'technicalwriter'` - the render path
    could not run at all, whatever the queues said. Both directions are covered:
    the whole roster renders, and a role that is not on it is named.
    """
    tasks = {
        (folded, "T-0001"): {"status": "doing", "title": "a task", "priority": "P1"}
        for folded in DISPLAY
    }
    once = render(tasks, _skeleton())
    for folded, spelled in DISPLAY.items():
        assert f"| {spelled} | T-0001 |" in once, folded
        assert f"| {spelled} | T-0001 a task | P1 | doing | - |" in once, folded
    assert "| technical-writer | T-0001 |" in once


def test_an_unknown_role_is_named_and_not_a_bare_keyerror() -> None:
    tasks = {("chiefofstaff", "T-0001"): {"status": "doing"}}
    with pytest.raises(UnknownRole) as caught:
        render(tasks, _skeleton())
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


def test_every_queued_role_has_a_board_spelling() -> None:
    """A new queue directory must not wait for a red regeneration to be noticed."""
    present = {
        norm_role(path.parent.name) for path in (live_root() / "Roles").glob("*/TaskQueue.md")
    }
    if not present:
        pytest.skip("no shared role queues in the local team tree")
    assert not present - set(DISPLAY), sorted(present - set(DISPLAY))
    assert not present - {norm_role(role) for role in FLOOR}, sorted(present)


if __name__ == "__main__":  # pragma: no cover - a maintainer's regeneration step
    root = team_root()
    if root is None:
        raise SystemExit("no local team tree in this checkout")
    tasks = queues(root)
    before = BOARD.read_text(encoding="utf-8")
    after = render(tasks, before)
    BOARD.write_text(after, encoding="utf-8")
    print(f"wrote {BOARD}: {len(tasks)} task(s) across {len(DISPLAY)} queue(s)")
    # `render` writes only what `queues()` returned, so a row that leaves the table
    # was filtered by FLOOR. Name it: a row dropped in silence is the stale-board
    # defect this file exists to catch, and the recipe must not commit it quietly.
    for role, tid in sorted(set(board_rows(before)) - set(board_rows(after))):
        print(
            f"note: {role} {tid} left the table - under FLOOR, or its key spelled unlike its queue"
        )
    problems = mismatches(tasks, board_rows(after)) + flight_mismatches(tasks, in_flight(after))
    if problems:
        print("\n".join(problems))
        raise SystemExit(1)
