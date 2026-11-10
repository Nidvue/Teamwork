"""Attention items and the task stage table.

Two things a team needs and must keep apart:

* **Attention** - one item per thing that cannot continue without a person: an
  authorization, a decision, a blocker or a review hand-off. It is team-local
  state in ``Attention.md`` next to ``Reviews.md``/``Disputes.md``, never
  committed, and ``attention list`` prints only the open items. A healthy team
  prints nothing at all: a panel that always shows something is noise a person
  learns to skip ([000-philosophy](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/000-philosophy.md),
  accessed 2026-11-01).
* **Stage** - what one task is waiting for, read from a first-match table over
  stored records ([003-execution](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/003-execution.md),
  accessed 2026-11-01). The table is read top to bottom and the first matching
  row wins; a ``person`` stage means the task cannot continue without human
  input.

``stage_of`` is a pure function of the task record, the open attention items and
an injected ``now``. It reads no clock and no queue: the caller resolves
dependencies (``deps_ready``) and passes the time, so the same records always
give the same stage and a test can pin the 24h idle rule without sleeping. The
two facts the table needs from the clock at all - how long a task has been idle
and whether a review claim outlived its lease - are computed from the record's
own stamps against that injected ``now``.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from .config import REVIEW_FAIL_LIMIT, REVIEW_LEASE_MINUTES
from .io import atomic_write
from .names import one_line

ATTENTION_KINDS = ("authorization", "decision", "blocker", "review")

STAGE_ROWS = (
    "person/answer",
    "person/review",
    "person/blocked-failed",
    "working/queued",
    "person/review-lane",
    "idle",
    "working",
)

STAGE_ORDER = {
    "person/answer": 0,
    "person/review": 1,
    "person/blocked-failed": 2,
    "person/review-lane": 3,
    "working/queued": 4,
    "working": 5,
    "idle": 6,
}

IDLE_HOURS = 24

ATTENTION_RE = re.compile(r"^##\s+(A-\d+)\s*(?:·|:)?\s*(.*)$")

META_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")

ATTENTION_HEADER = (
    "# ATTENTION - what needs a person\n\n"
    "> One entry per item that cannot continue without a person: an\n"
    "> authorization, a decision, a blocker or a review hand-off. `attention\n"
    "> list` prints the open ones, oldest first, and a healthy team prints\n"
    "> nothing at all. Manage with `teamwork.py attention add|list|resolve`.\n\n"
    "Related: [team map](TeamMap.md) | [reviews](Reviews.md) | "
    "[disputes](Disputes.md)\n"
)

ATTENTION_FIELDS = (
    "kind",
    "status",
    "task",
    "by",
    "created",
    "resolved_by",
    "resolved",
    "resolution",
)


def today_iso() -> str:
    return datetime.date.today().isoformat()


def new_attention(text: str, kind: str = "blocker", by: str = "", task: str = "") -> dict:
    """One open item, with an empty id the writer allocates."""
    return {
        "id": "",
        "text": one_line(text),
        "kind": kind if kind in ATTENTION_KINDS else "blocker",
        "status": "open",
        "task": one_line(task).upper(),
        "by": one_line(by),
        "created": today_iso(),
        "resolved_by": "",
        "resolved": "",
        "resolution": "",
    }


def parse_attention(path: Path) -> list:
    """Every entry in the file, oldest first; an absent file has none."""
    if not path.exists():
        return []
    out: list = []
    cur = None
    in_meta = True
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = ATTENTION_RE.match(raw)
        if match:
            if cur:
                out.append(cur)
            cur = new_attention(match.group(2))
            cur["id"] = match.group(1)
            in_meta = True
            continue
        if cur is None:
            continue
        if not raw.strip():
            in_meta = False
            continue
        if in_meta:
            meta = META_RE.match(raw)
            if meta and meta.group(1) in ATTENTION_FIELDS:
                cur[meta.group(1)] = meta.group(2).strip()
                continue
            in_meta = False
    if cur:
        out.append(cur)
    return sorted(out, key=lambda a: a["id"])


def assign_attention_ids(items: list) -> None:
    """Number the entries that have no id, continuing the highest one in use."""
    highest = 0
    for item in items:
        tail = str(item.get("id") or "").split("-", 1)[-1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    for item in items:
        if not item.get("id"):
            highest += 1
            item["id"] = f"A-{highest:04d}"


def render_attention(items: list) -> str:
    assign_attention_ids(items)
    out = [ATTENTION_HEADER, ""]
    for item in sorted(items, key=lambda a: a["id"]):
        out.append(f"## {item['id']} · {one_line(item['text']) or 'attention item'}")
        for field in ATTENTION_FIELDS:
            out.append(f"- {field}: {one_line(item.get(field) or '')}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_attention(path: Path, items: list) -> None:
    atomic_write(path, render_attention(items))


def find_attention(items: list, handle: str):
    """The index of an entry by id, or by a substring of its text."""
    raw = (handle or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"A-\d+", raw.upper()):
        for index, item in enumerate(items):
            if item["id"].upper() == raw.upper():
                return index
        return None
    for index, item in enumerate(items):
        if raw.lower() in (item["text"] + " " + item["task"]).lower():
            return index
    return None


def open_attention(items: list) -> list:
    """The entries still waiting on a person, oldest first."""
    return [item for item in items if item.get("status", "open") == "open"]


def attention_line(item: dict) -> str:
    """One line of the panel: id, kind, the task it names, who asked, the text."""
    task = f" {item['task']}" if item.get("task") else ""
    by = f" by {item['by']}" if item.get("by") else ""
    return f"{item['id']} [{item['kind']}]{task}{by} {item['created']}: {item['text']}"


def authorization_count(items: list) -> int:
    return sum(1 for item in items if item.get("kind") == "authorization")


def _parse_stamp(value: str) -> datetime.datetime | None:
    """An ISO date or datetime stamp; ``None`` when it is unusable."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None


def claim_state(task: dict, now: datetime.datetime | None = None) -> tuple:
    """Return ``(lane, age_minutes|None, live)`` for a task's review claim.

    A claim is a lease, not a lock: an undated or unreadable stamp counts as
    expired, so a lane that died holding a deliverable cannot freeze it forever.
    The lease length is the one stored on the claim (the profile it was granted
    for); an older claim without one gets the base lease. This mirrors
    ``engine.review_claim_state`` with the clock injected - the two are compared
    in ``tests/unit/test_stage.py`` so they cannot drift apart unnoticed.
    """
    lane = (task.get("review_claim") or "").strip()
    if not lane:
        return "", None, False
    now = now or datetime.datetime.now()
    stamp = _parse_stamp(task.get("review_claim_ts") or "")
    if stamp is None:
        return lane, None, False
    age = max(int((now - stamp).total_seconds() // 60), 0)
    raw_lease = str(task.get("review_claim_lease") or "").strip()
    lease = int(raw_lease) if raw_lease.isdigit() and int(raw_lease) > 0 else REVIEW_LEASE_MINUTES
    return lane, age, age <= lease


def idle_hours(task: dict, now: datetime.datetime | None = None) -> float | None:
    """Hours since the record's ``updated`` stamp; ``None`` when unusable.

    ``updated`` is written as a date, so it is read at midnight: a task updated
    today is under 24h old and one updated yesterday or earlier is parked.
    """
    stamp = _parse_stamp(task.get("updated") or "")
    if stamp is None:
        return None
    now = now or datetime.datetime.now()
    return max((now - stamp).total_seconds() / 3600.0, 0.0)


def stage_of(
    task: dict,
    open_items=(),
    deps_ready: bool = False,
    now: datetime.datetime | None = None,
) -> tuple:
    """``(stage, fact)`` for one task record - first matching row wins.

    ``open_items`` are the open attention entries (already filtered), ``deps_ready``
    is the caller's answer to "is every dependency of this task satisfied yet"
    (``records.executable``), and ``now`` is injected so the 24h idle rule and the
    review-claim lease are testable without a clock.
    """
    now = now or datetime.datetime.now()
    task_id = (task.get("id") or "").upper()
    status = (task.get("status") or "").strip()

    for item in open_items:
        if task_id and (item.get("task") or "").upper() == task_id:
            return (
                "person/answer",
                f"open attention {item['id']} ({item.get('kind') or 'item'}) names it",
            )

    if task.get("self_check") == "passed" and task.get("review_status") == "pending":
        return "person/review", "self-check passed, review pending"

    if status == "blocked":
        return "person/blocked-failed", "status=blocked"
    fails = int(task.get("review_fails") or 0)
    if fails >= REVIEW_FAIL_LIMIT:
        return "person/blocked-failed", f"failed review {fails}x"
    lane, age, live = claim_state(task, now)
    if lane and not live:
        where = "undated" if age is None else f"{age}m old"
        return "person/blocked-failed", f"review claim by {lane} expired ({where})"

    if status == "todo" and deps_ready:
        return "working/queued", "todo, every dependency done"

    if status == "review" and task.get("review_status") == "pending" and not live:
        return "person/review-lane", "in review, no reviewer lane holds it"

    hours = idle_hours(task, now)
    if status == "doing" and hours is not None and hours >= IDLE_HOURS:
        return "idle", f"doing, updated {task.get('updated')} (over {IDLE_HOURS}h ago)"

    if status == "todo":
        return "working", f"todo, dependencies not done: {task.get('deps') or '-'}"
    if live:
        return "working", f"review claim held by {lane}"
    return "working", f"status={status or '-'}"
