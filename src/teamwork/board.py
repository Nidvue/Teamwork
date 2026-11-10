"""Render and verify ``docs/Team/Board.md`` against the shared role queues.

The committed board is a projection of the queues at the commit that carries it,
and nothing else. The product owns both sides of that invariant:
``teamwork.py board --write`` renders the two task tables from
``Roles/*/TaskQueue.md`` and ``teamwork.py board --check`` exits 1 naming every
row that disagrees (Tester audit TA-01/TA-07). The comparison used to live only
in ``tests/unit/test_board_matches_tool.py``, which skips whenever the
gitignored team tree is absent - CI and every fresh clone - so board drift was
found late and only on a developer machine. The test module is now a thin caller
and keeps its synthetic cases.

D-0025 and D-0026 were both the same defect: a board table that was correct when
it was written and stale by the time a reviewer read it, because the act of
submitting the board flipped the very row it reported. Five review rounds on
T-0002 failed on that one class, and neither `links` nor the release-consistency
gate can see it - a board that contradicts the tool passes both.

So the comparison is an executable invariant instead of a reviewer's diligence.
A row that disagrees on state, PR or merged revision, a task with no row, a row
naming no task, or an In-flight table that is not exactly the open set fails with
both sides printed; the rendered text must also equal the committed text, so a
reordered or duplicated table row cannot survive. An In-flight title, priority and
artifact are the lane's own cells and are preserved verbatim by the renderer.

The queues live in the gitignored team tree, and this module never guesses one:
``--check`` refuses an empty queue set instead of reporting a clean board.

Every staffed role therefore needs an entry in both roster maps: a queue whose
role is unlisted used to reach this render path as ``KeyError: 'technicalwriter'``,
which named a dict key instead of the missing role, so the documented repair
recipe could not run at all. An unlisted role now raises ``UnknownRole`` naming
itself and the two maps to extend.

The floor that separates this milestone's ids from an older one is the one filter
between the queues and the board, and it hid 10 open tasks: five floors were
spelled hyphenated while ``queues()`` looked them up folded (so they never applied),
and the rest were written for M9 ids that M11's re-numbered queues no longer
carry. ``queues()`` is the renderer's only view, so a record dropped there is
dropped from both sides of the comparison and the invariant cannot see it. The
floor therefore may only decide whether a *closed* record is history: an open task
is always in scope, the keys are folded the way the lookup spells them, and
``test_no_queued_task_is_silently_hidden`` counts the raw queues instead of
trusting the view that does the hiding.

One row is exempt from both invariants, and only one kind: a task that is LANDING.
A committed board is a projection at render time, but the act of landing a PR flips
its own task from ``review``/``doing`` to ``done`` plus a merge revision, so no
commit can carry its own post-merge state - the merge that would make the row true
does not exist yet when the row is written. This is structural, not an author's
error: ``projectmanager T-0003`` read ``doing`` on the board and ``done`` +
``cfba521`` in the queue with no defect behind the difference. So a landing task is
excluded from both sides (the CEO decision: "The board cannot contain its own
post-merge state"), while every other comparison stays strict - an open
``todo``/``doing`` task must still be visible and equal, and a ``done`` task must
still match when both sides say ``done``.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

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
#: silently drop out of the comparison, which is the failure this module prevents.
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

TABLE_ANCHOR = "Rows whose PR is not merged"
FLIGHT_ANCHOR = "The task queue (`teamwork.py"


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


def parse_queues(root: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Every record in the queues, keyed by (folded role, id), floor or no floor.

    The unfiltered view exists so a test can compare the board against the queues
    themselves rather than against `queues()`, which is the view that can hide a
    record from both sides of the comparison.
    """
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted((root / "Roles").glob("*/TaskQueue.md")):
        role = norm_role(path.parent.name)
        # A queue the board cannot spell is a defect here, so it fails naming the
        # role instead of surfacing later as rows that are all absent.
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


def is_landing(fields: dict[str, str], row: tuple[str, str, str]) -> bool:
    """Whether this task's state is changing by the act of landing - see the module note.

    A landing task's state changes by the act of landing, so neither side can be
    stable until the post-merge re-render: the queue moves to `review` (the PR is up
    for review) and then to `done` + a merge revision (the PR landed), while the last
    committed board still shows the state it rendered under. Two shapes are that
    window, and nothing else is:

    * either side says `review` - the review the landing waits on; or
    * the queue already carries the merge for the *same* PR whose row is still open
      on the board with no merged revision (`projectmanager T-0003`). Both sides name
      one PR, so the board is exactly one render behind the queue for that PR, which
      a drift between two different PRs can never look like.
    """
    queue_state = fields.get("status", "")
    board_state, board_pr, board_merged = row
    if queue_state == "review" or board_state == "review":
        return True
    return (
        queue_state == "done"
        and board_state in OPEN
        and board_merged in ("", "-")
        and board_pr != "-"
        and board_pr == (fields.get("pr") or "-")
        and bool(fields.get("merge_commit"))
    )


def landing_keys(
    tasks: dict[tuple[str, str], dict[str, str]],
    rows: dict[tuple[str, str], tuple[str, str, str]],
    flight: dict[tuple[str, str], str] | None = None,
) -> set[tuple[str, str]]:
    """The tasks excluded from both invariants because they are mid-landing.

    A task with no board row is read from its In-flight entry instead: that table
    carries no PR, so only the `review` half of the predicate can match, and the
    missing row is itself already reported by `mismatches`.
    """
    out: set[tuple[str, str]] = set()
    for key, fields in tasks.items():
        row = rows.get(key)
        if row is None and flight is not None and key in flight:
            row = (flight[key], fields.get("pr") or "-", "-")
        if row is not None and is_landing(fields, row):
            out.add(key)
    return out


def mismatches(
    tasks: dict[tuple[str, str], dict[str, str]],
    rows: dict[tuple[str, str], tuple[str, str, str]],
) -> list[str]:
    """Both directions: a row that is wrong and a task that has no row."""
    out = []
    landing = landing_keys(tasks, rows)
    for key, fields in sorted(tasks.items()):
        if key in landing:
            continue
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
    tasks: dict[tuple[str, str], dict[str, str]],
    flight: dict[tuple[str, str], str],
    rows: dict[tuple[str, str], tuple[str, str, str]] | None = None,
) -> list[str]:
    """The In-flight table versus the open set, minus the tasks that are landing."""
    landing = landing_keys(tasks, rows or {}, flight)
    tasks = {key: fields for key, fields in tasks.items() if key not in landing}
    # both directions of the comparison, so a landing row is not reported as an
    # In-flight entry whose queue status is no longer open
    flight = {key: state for key, state in flight.items() if key not in landing}
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


def without_landing(board: str, keys: set[tuple[str, str]]) -> str:
    """The board with the landing rows removed from both tables.

    Only those rows are dropped: everything else is still compared and still has to
    be what a regeneration writes, so the exemption cannot spread.
    """
    kept = []
    for line in board.splitlines():
        match = BOARD_ROW.match(line) or FLIGHT_ROW.match(line)
        if match and (norm_role(match.group(1)), match.group(2)) in keys:
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


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
    end = next(i for i, line in enumerate(lines) if line.startswith(TABLE_ANCHOR))
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
    j = next(i for i, line in enumerate(lines) if line.startswith(FLIGHT_ANCHOR))
    return "\n".join(lines[:i] + flight + [""] + lines[j:]) + "\n"


def problems(tasks: dict[tuple[str, str], dict[str, str]], board: str) -> list[str]:
    """Every row that contradicts the queues, named, plus any render drift.

    The row comparators run first because they name the cells; the render equality
    is the backstop for the cells they do not look at (an In-flight title, priority
    or artifact), with the landing rows removed from both sides.
    """
    rows = board_rows(board)
    flight = in_flight(board)
    found = mismatches(tasks, rows) + flight_mismatches(tasks, flight, rows)
    if found:
        return found
    landing = landing_keys(tasks, rows, flight)
    rest = {key: fields for key, fields in tasks.items() if key not in landing}
    stable = without_landing(board, landing)
    after = render(rest, stable)
    if after == stable:
        return []
    return [
        line
        for line in difflib.unified_diff(
            stable.splitlines(), after.splitlines(), "committed", "rendered", lineterm="", n=0
        )
        if not line.startswith(("---", "+++"))
    ]
