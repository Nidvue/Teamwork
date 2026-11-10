"""Re-resolve a memory record's evidence against the ground truth it names.

``memory verify`` answers the question a note cannot answer for itself: does
what its evidence points at still exist? The evidence text is parsed into
exactly one kind, first match wins - a git revision, a path in this tree, or an
``https`` source carrying an access date - and each kind costs one cheap local
read: ``git cat-file -e`` for a revision, ``Path.is_file`` and a line count for
a path, the access date's age for a source. No model call, no network, no
second store. A record whose evidence names nothing checkable is
``unverifiable``, never ``drifted``: silence is not a contradiction.

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
from pathlib import Path

from . import records
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


def classify(evidence: str) -> str:
    """The one kind of ground truth the evidence names, first match wins.

    Revision beats path beats source, because a command line carries all three
    at once (``pytest -q tests/unit/test_x.py @abc1234``): the revision is the
    strongest claim the evidence makes, so that is the one checked.
    """
    text = evidence or ""
    if _revision(text):
        return REVISION
    if _path(text)[0]:
        return PATH
    if _source(text):
        return SOURCE
    return NONE


def _line_count(path: Path) -> int:
    data = path.read_bytes()
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


def verify_record(record: dict, project: Path, today: datetime.date) -> tuple[str, str]:
    """``(status, reason)`` for one record: verified, drifted, or unverifiable."""
    evidence = str(record.get("evidence") or "")
    kind = classify(evidence)
    if kind == REVISION:
        sha = _revision(evidence)
        result = run_git(project, "cat-file", "-e", f"{sha}^{{commit}}")
        if result.returncode == 0:
            return VERIFIED, f"{sha} is a commit here"
        return DRIFTED, f"{sha} is not a commit here"
    if kind == PATH:
        token, wanted = _path(evidence)
        target = project / token
        if not target.is_file():
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
    return UNVERIFIABLE, "evidence names no revision, path or source"


def verify_all(entries: list[dict], project: Path, now: datetime.date | datetime.datetime) -> list:
    """One row per record, ordered by pointer then id so two runs are byte-identical."""
    today = now.date() if isinstance(now, datetime.datetime) else now
    rows = []
    for entry in entries:
        status, reason = verify_record(entry, project, today)
        rows.append(
            {
                "id": str(entry.get("id") or ""),
                "kind": classify(str(entry.get("evidence") or "")),
                "verify_status": status,
                "reason": reason,
                "pointer": str(entry.get("pointer") or ""),
                "store": str(entry.get("store") or ""),
            }
        )
    return sorted(rows, key=lambda row: (row["pointer"], row["id"]))


def cap(rows: list, limit: int) -> list:
    """At most ``limit`` rows; zero or less means every row."""
    return rows[:limit] if limit and limit > 0 else list(rows)


def count(rows: list, limit: int = 0) -> dict:
    """The counts the footer and the ledger event carry."""
    return {
        "records": len(rows),
        "verified": sum(1 for row in rows if row["verify_status"] == VERIFIED),
        "drifted": sum(1 for row in rows if row["verify_status"] == DRIFTED),
        "unverifiable": sum(1 for row in rows if row["verify_status"] == UNVERIFIABLE),
        "limit": int(limit or 0),
    }


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
