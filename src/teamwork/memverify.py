"""Re-resolve a memory record's evidence against the ground truth it names.

``memory verify`` answers the question a note cannot answer for itself: does
what its evidence points at still exist? The evidence text is parsed into every
kind it names - a git revision, a path in this tree, an ``https`` source
carrying an access date - and each kind costs one cheap local read: ``git
cat-file -e`` for a revision, ``Path.is_file`` and a line count for a path, the
access date's age for a source. The record's status is the worst of them
(``drifted`` beats ``unverifiable`` beats ``verified``) and its reason names
each kind checked, so a valid revision cannot hide a path that drifted behind
it. No model call, no network, no second store. A record whose evidence names
nothing checkable is ``unverifiable``, never ``drifted``: silence is not a
contradiction.

``--focus <text | T-id>`` tunes the pass to a goal: a task id resolves to its
title through ``memorypack.task_query``, the records are ranked by the frozen
4.1 score for that text, and the first ``--limit`` (default 25) are verified in
score order; the rest are counted as deferred. Without ``--focus`` every record
is verified in pointer order, byte-identically to the pass before the flag.

The pass is read-only unless the caller asks for ``apply``, and even then only
two fields on knowledge records move - ``checked`` and ``verify_status`` - plus
one ``memory.verify`` ledger event with the counts. ``statement`` and
``evidence`` are never rewritten and no record is ever deleted: a wrong
evidence line is the thing the correction has to argue with, so the pass
records what it found instead of tidying it away. Lessons and short-term
memory carry no such field, so they are reported and left byte-identical.

Owner: developer. Related: docs/Team/Memory.md
"""

from __future__ import annotations

import datetime
import json
import re
from functools import lru_cache
from pathlib import Path

from . import memorypack, records
from .gitutil import run_git
from .layout import knowledge_path

REVISION = "revision"
PATH = "path"
SOURCE = "source"
NONE = "none"

VERIFIED = "verified"
DRIFTED = "drifted"
UNVERIFIABLE = "unverifiable"

SOURCE_MAX_AGE_DAYS = 400
FOCUS_LIMIT = 25

REVISION_RE = re.compile(r"(?:@|\brev\s+)([0-9a-f]{7,40})\b")
PATH_RE = re.compile(
    r"(?<![\w:/.-])("
    r"(?:\.{0,2}/)?(?:[\w.@+-]+/)+[\w.@+-]+(?:\.[A-Za-z][A-Za-z0-9]*)?"
    r"|[\w@+-][\w.@+-]*\.[A-Za-z][A-Za-z0-9]*"
    r")(?::(\d+))?"
)
SOURCE_RE = re.compile(r"https?://[^\s<>\"')]+")
ACCESS_RE = re.compile(r"accessed\s+(\d{4}-\d{2}-\d{2})|\((\d{4}-\d{2}-\d{2})\)")


def _revision(evidence: str) -> str:
    match = REVISION_RE.search(evidence)
    return match.group(1) if match else ""


def _path(evidence: str) -> tuple[str, int]:
    for match in PATH_RE.finditer(evidence):
        token, line = match.group(1), match.group(2)
        if line or "." in token.rsplit("/", 1)[-1]:
            return token, int(line) if line else 0
    return "", 0


def _source(evidence: str) -> str:
    match = SOURCE_RE.search(evidence)
    return match.group(0) if match else ""


def _access_date(evidence: str) -> datetime.date | None:
    match = ACCESS_RE.search(evidence)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return None


def kinds(evidence: str) -> list[str]:
    """Every kind of ground truth the evidence names, in revision/path/source order."""
    text = evidence or ""
    found = []
    if _revision(text):
        found.append(REVISION)
    if _path(text)[0]:
        found.append(PATH)
    if _source(text):
        found.append(SOURCE)
    return found


def classify(evidence: str) -> str:
    """The label the report prints for a record: its strongest kind, else ``none``.

    Revision beats path beats source, because a command line carries all three
    at once (``pytest -q tests/unit/test_x.py @abc1234``). The label is one word
    so the output line keeps its shape; :func:`verify_record` checks every kind
    :func:`kinds` reports, not just this one.
    """
    found = kinds(evidence)
    return found[0] if found else NONE


def _line_count(path: Path) -> int:
    data = path.read_bytes()
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


@lru_cache(maxsize=8)
def _tree_root(project: Path) -> Path:
    """The checkout the pass sits in, or ``project`` itself when it is not one.

    Evidence paths are written relative to either tree: the team root a lane is
    given (``Runtime/Lanes/x.log``) or the checkout that root lives inside
    (``src/teamwork/engine.py``). One ``rev-parse`` per project, and the team
    root itself when git cannot answer.
    """
    result = run_git(project, "rev-parse", "--show-toplevel")
    top = result.stdout.strip() if result.returncode == 0 else ""
    return Path(top) if top else project


def _resolve_path(project: Path, token: str) -> Path | None:
    """The file the token names in the team root or in the checkout, if either holds it."""
    for base in dict.fromkeys((project, _tree_root(project))):
        target = base / token
        if target.is_file():
            return target
    return None


SEVERITY = {VERIFIED: 0, UNVERIFIABLE: 1, DRIFTED: 2}


def verify_record(record: dict, project: Path, today: datetime.date) -> tuple[str, str]:
    """``(status, reason)`` for one record: verified, drifted, or unverifiable.

    Every kind the evidence names is checked and the worst status wins, so a
    revision that still resolves cannot mask a path that has drifted behind it.
    One kind keeps its reason byte-identical to the single-kind pass; several
    are joined as ``kind: reason; kind: reason`` so the report says what was
    checked.
    """
    evidence = str(record.get("evidence") or "")
    found = kinds(evidence)
    if not found:
        return UNVERIFIABLE, "evidence names no revision, path or source"
    checked = [(kind, *_check_kind(kind, evidence, project, today)) for kind in found]
    worst = max((status for _, status, _ in checked), key=lambda status: SEVERITY[status])
    if len(checked) == 1:
        return checked[0][1], checked[0][2]
    return worst, "; ".join(f"{kind}: {reason}" for kind, _, reason in checked)


def _check_kind(kind: str, evidence: str, project: Path, today: datetime.date) -> tuple[str, str]:
    """``(status, reason)`` for one already-detected kind of the same evidence."""
    if kind == REVISION:
        sha = _revision(evidence)
        result = run_git(project, "cat-file", "-e", f"{sha}^{{commit}}")
        if result.returncode == 0:
            return VERIFIED, f"{sha} is a commit here"
        return DRIFTED, f"{sha} is not a commit here"
    if kind == PATH:
        token, wanted = _path(evidence)
        target = _resolve_path(project, token)
        if target is None:
            return DRIFTED, f"{token} is missing"
        if wanted:
            have = _line_count(target)
            if have < wanted:
                return DRIFTED, f"{token} has {have} line(s), wanted {wanted}"
            return VERIFIED, f"{token} has {have} line(s)"
        return VERIFIED, f"{token} exists"
    if kind == SOURCE:
        url = _source(evidence)
        accessed = _access_date(evidence)
        if accessed is None:
            return UNVERIFIABLE, f"{url} carries no access date"
        age = (today - accessed).days
        if age <= SOURCE_MAX_AGE_DAYS:
            return VERIFIED, f"{url} accessed {accessed.isoformat()}, {age} day(s) old"
        return DRIFTED, (
            f"{url} accessed {accessed.isoformat()} is {age} day(s) old (max {SOURCE_MAX_AGE_DAYS})"
        )
    return UNVERIFIABLE, f"{kind} is not a kind this pass checks"


def _row(entry: dict, project: Path, today: datetime.date) -> dict:
    status, reason = verify_record(entry, project, today)
    return {
        "id": str(entry.get("id") or ""),
        "kind": classify(str(entry.get("evidence") or "")),
        "verify_status": status,
        "reason": reason,
        "pointer": str(entry.get("pointer") or ""),
        "store": str(entry.get("store") or ""),
    }


def verify_all(entries: list[dict], project: Path, now: datetime.date | datetime.datetime) -> list:
    """One row per record, ordered by pointer then id so two runs are byte-identical."""
    today = now.date() if isinstance(now, datetime.datetime) else now
    rows = [_row(entry, project, today) for entry in entries]
    return sorted(rows, key=lambda row: (row["pointer"], row["id"]))


def select(
    entries: list[dict],
    project: Path,
    query: str,
    now: datetime.date | datetime.datetime,
    limit: int = FOCUS_LIMIT,
) -> tuple[list, int]:
    """The focused pass: the best records for ``query``, in score order, and the rest.

    Selection and order are both the frozen 4.1 score, taken from ``memorypack``
    so the pass cannot drift from the pack: the first ``limit`` records are the
    highest-scoring ones, ties broken by id ascending, never the first records in
    pointer order. ``limit`` zero or less keeps every record, so ``--limit 0``
    still means all. The second element is the number of records left out.
    """
    today = now.date() if isinstance(now, datetime.datetime) else now
    ranked = memorypack.rank(entries, query, now)
    kept = cap(ranked, limit)
    return [_row(entry, project, today) for entry in kept], len(ranked) - len(kept)


def cap(rows: list, limit: int) -> list:
    """At most ``limit`` rows; zero or less means every row."""
    return rows[:limit] if limit and limit > 0 else list(rows)


def count(rows: list, limit: int = 0, deferred: int | None = None) -> dict:
    """The counts the footer and the ledger event carry.

    ``deferred`` is only present for a focused run: it is the number of records
    the focus left out, which is what the extra footer line reports. An
    unfocused run passes nothing, so its counts - and its bytes - do not move.
    """
    counts = {
        "records": len(rows),
        "verified": sum(1 for row in rows if row["verify_status"] == VERIFIED),
        "drifted": sum(1 for row in rows if row["verify_status"] == DRIFTED),
        "unverifiable": sum(1 for row in rows if row["verify_status"] == UNVERIFIABLE),
        "limit": int(limit or 0),
    }
    if deferred is not None:
        counts["deferred"] = int(deferred)
    return counts


def render(rows: list, counts: dict, as_json: bool = False) -> str:
    """The report: one line per record, then the footer; ``--json`` is one object per line."""
    if as_json:
        return "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    limit = counts.get("limit") or 0
    lines = [
        f"- [{row['id']}] {row['kind']} {row['verify_status']} | {row['reason']} | {row['pointer']}"
        for row in rows
    ]
    lines.append(
        f"# verify: {counts['records']} record(s), {counts['verified']} verified,"
        f" {counts['drifted']} drifted, {counts['unverifiable']} unverifiable"
        f" (limit {limit if limit > 0 else 'all'})"
    )
    if counts.get("deferred") is not None:
        lines.append(f"# verify: {counts['deferred']} deferred by --focus")
    return "\n".join(lines) + "\n"


def apply(rows: list, root: Path, by: str, today: datetime.date) -> dict:
    """Write ``checked`` and ``verify_status`` on knowledge records; append one ledger event.

    Only those two fields are assigned, and only when a value actually changes,
    so a second run on the same day writes nothing and appends nothing. Lessons
    and short-term memory have no such field and are never opened for writing.
    """
    from .engine import ledger_append

    path = knowledge_path(root)
    counts = count(rows)
    stamp = today.isoformat()
    changed: list[str] = []
    items = records.parse_knowledge(path)
    if items:
        by_id = {str(row["id"]): str(row["verify_status"]) for row in rows}
        before = path.stat().st_size
        for item in items:
            status = by_id.get(str(item.get("id") or ""))
            if status is None:
                continue
            if item.get("checked") == stamp and item.get("verify_status") == status:
                continue
            item["checked"] = stamp
            item["verify_status"] = status
            changed.append(str(item["id"]))
        delta = 0
        if changed:
            records.write_knowledge(path, items)
            delta = path.stat().st_size - before
    else:
        delta = 0
    if not changed:
        return {"changed": 0, "bytes": 0, **counts}
    ledger_append(
        root,
        "memory.verify",
        by,
        "",
        (
            f"{counts['records']} record(s), {counts['verified']} verified,"
            f" {counts['drifted']} drifted, {counts['unverifiable']} unverifiable;"
            f" {len(changed)} knowledge record(s) stamped; bytes {delta:+d}"
        ),
    )
    return {"changed": len(changed), "bytes": delta, **counts}
