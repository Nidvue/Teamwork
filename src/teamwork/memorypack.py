"""Task-aware memory: scoring, the injected pack, retrieval and the dream pass.

The implementation of ``docs/Team/Memory.md`` 4.1-4.4 and 6. Four surfaces, one
scorer, no model call and no second store:

* ``collect`` reads the three record stores this engine already has - role
  lessons, project knowledge and the role's short-term memory - into one uniform
  shape, so ranking cannot care which file a record came from.
* ``pack`` turns a task query into the smallest set of rendered pointer lines
  that fits a byte budget. It is the injected-context layer: one line per
  record, never a copy of the statement's home.
* ``search`` is the single retrieval path over those three stores, capped.
* ``dream`` and ``apply_dream`` are the off-hot-path maintenance pass: duplicate
  and contradiction detection, stale archiving, missing evidence reported. The
  only mutations are ``status`` and ``superseded_by``.

The score is frozen in 4.1: ``0.50 * overlap + 0.20 * importance/5 + 0.15 *
recency + 0.15 * min(uses/5, 1)``, ties broken by id ascending, so the same
records and the same clock produce the same bytes twice.

Two shape notes a reader needs to rank a lesson next to a knowledge record:
lessons and short-term memory carry no ``importance`` field of their own, so a
lesson scores at the default knowledge importance (3) and a memory entry at its
recorded importance; a lesson has no ``uses`` counter, so it scores 0 there.
``kind`` is the record type (lesson/knowledge/memory) and ``store`` is the file
name that holds it, which is what ``memory search`` prints.

Owner: developer. Related: docs/Team/Memory.md
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from . import harness
from .config import F_KNOWLEDGE, F_LESSONS, F_SHORT, F_TASKS
from .layout import knowledge_path, role_dir, roles_dir
from .names import one_line
from .records import (
    normalise_knowledge,
    parse_knowledge,
    parse_lessons,
    parse_memory,
    parse_tasks,
    write_knowledge,
    write_lessons,
)

PACK_BUDGET_BYTES = 4000
SEARCH_BUDGET_BYTES = 2000
SEARCH_LIMIT = 10
STATEMENT_CLIP = 200
HALF_LIFE_DAYS = 30.0
STALE_AFTER_DAYS = 90
SHORT_EVIDENCE = 20
DUPLICATE_OVERLAP = 0.8
CONTRADICTION_OVERLAP = 0.5
LESSON_IMPORTANCE = 3
DREAM_KINDS = ("lesson", "knowledge")
INJECTABLE_STATUSES = ("active", "open")
PARKED_STATUSES = ("superseded", "archived")
STOPWORDS = frozenset(
    """the and for with this that from into when then a an of to in on is are be it its
    as at by or not no if we you they do does did has have had can will should must may
    one two all any each more most other than so such only own same very just also now
    new use used using""".split()
)

TOKEN_RE = re.compile(r"[a-z0-9_]+")
TASK_ID_RE = re.compile(r"T-\d+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Lowercase ``[a-z0-9_]+`` terms, stopwords dropped, in the order they appear."""
    return [word for word in TOKEN_RE.findall(str(text or "").lower()) if word not in STOPWORDS]


def _tag_text(tags) -> str:
    if isinstance(tags, (list, tuple)):
        return " ".join(str(tag) for tag in tags)
    return str(tags or "")


def _number(value, default: float = 0.0) -> float:
    if value is None or value == "" or isinstance(value, bool):
        return default
    try:
        return float(str(value))
    except ValueError:
        return default


def _today(now: datetime.date | datetime.datetime) -> datetime.date:
    return now.date() if isinstance(now, datetime.datetime) else now


def _date_of(value) -> datetime.date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def age_days(entry: dict, now: datetime.date | datetime.datetime) -> float | None:
    """Whole days since the record's ``updated`` (else ``last_used``) date."""
    stamp = entry.get("updated") or entry.get("last_used")
    day = _date_of(stamp)
    if day is None:
        return None
    return float(max((_today(now) - day).days, 0))


def record_tokens(entry: dict) -> list[str]:
    """The tokens a query is matched against: statement, title and tags."""
    return tokenize(
        " ".join(
            [
                str(entry.get("statement") or ""),
                str(entry.get("title") or ""),
                _tag_text(entry.get("tags")),
            ]
        )
    )


def score(entry: dict, terms, now: datetime.date | datetime.datetime) -> float:
    """The frozen 4.1 score for one record against the query's distinct terms."""
    distinct = set(tokenize(terms)) if isinstance(terms, str) else {str(t).lower() for t in terms}
    overlap = 0.0
    if distinct:
        overlap = len(distinct & set(record_tokens(entry))) / len(distinct)
    importance = max(0.0, min(_number(entry.get("importance")), 5.0))
    age = age_days(entry, now)
    recency = 0.5 if age is None else 0.5 ** (age / HALF_LIFE_DAYS)
    uses = max(0.0, min(_number(entry.get("uses")) / 5.0, 1.0))
    return 0.50 * overlap + 0.20 * (importance / 5.0) + 0.15 * recency + 0.15 * uses


def rank(entries: list[dict], query: str, now: datetime.date | datetime.datetime) -> list[dict]:
    """Score-descending, id-ascending: a total order, so the pack is reproducible."""
    terms = tokenize(query)
    by_id = sorted(entries, key=lambda entry: str(entry.get("id") or ""))
    return sorted(by_id, key=lambda entry: score(entry, terms, now), reverse=True)


def _pointer(root: Path, path: Path, record_id: str) -> str:
    try:
        where = path.relative_to(root).as_posix()
    except ValueError:
        where = path.as_posix()
    return f"{where}#{record_id}"


def _entry(
    *,
    record_id: str,
    kind: str,
    store: str,
    pointer: str,
    title: str,
    statement: str,
    tags,
    importance,
    uses,
    updated: str,
    status: str,
    evidence: str,
) -> dict:
    return {
        "id": record_id,
        "kind": kind,
        "store": store,
        "title": one_line(title),
        "statement": one_line(statement),
        "tags": _tag_text(tags),
        "importance": int(_number(importance)),
        "uses": int(_number(uses)),
        "updated": str(updated or ""),
        "status": str(status or ""),
        "evidence": str(evidence or ""),
        "pointer": pointer,
    }


def lessons(root: Path, role: str) -> list[dict]:
    """Every lesson the role holds, parked ones included, in the uniform shape.

    ``mistake`` is the title, ``rule`` the statement, and the role's file plus the
    record id is the pointer back to the full record.
    """
    path = role_dir(root, role) / F_LESSONS
    return [
        _entry(
            record_id=item["id"],
            kind="lesson",
            store=F_LESSONS,
            pointer=_pointer(root, path, item["id"]),
            title=item.get("mistake", ""),
            statement=item.get("rule", ""),
            tags="",
            importance=LESSON_IMPORTANCE,
            uses=0,
            updated=item.get("updated") or item.get("created", ""),
            status=item.get("status", ""),
            evidence=item.get("evidence", ""),
        )
        for item in harness._load_lessons(root, role, statuses=("open", "superseded", "archived"))
    ]


def knowledge(root: Path) -> list[dict]:
    """Every knowledge record, active or parked: the pack filters, dream needs all of them."""
    path = knowledge_path(root)
    active, parked = harness._load_knowledge(root, limit=None)
    return [
        _entry(
            record_id=item["id"],
            kind="knowledge",
            store=F_KNOWLEDGE,
            pointer=_pointer(root, path, item["id"]),
            title=item.get("topic", ""),
            statement=item.get("statement", ""),
            tags=item.get("tags", ""),
            importance=item.get("importance", 0),
            uses=item.get("uses", 0),
            updated=item.get("updated") or item.get("created", ""),
            status=item.get("status", ""),
            evidence=item.get("evidence", ""),
        )
        for item in list(active) + list(parked)
    ]


def memories(root: Path, role: str) -> list[dict]:
    """The role's short-term memory: ``key`` is the title and the provenance is the evidence."""
    path = role_dir(root, role) / F_SHORT
    return [
        _entry(
            record_id=item["id"],
            kind="memory",
            store=F_SHORT,
            pointer=_pointer(root, path, item["id"]),
            title=item.get("key") or "note",
            statement=item.get("body", ""),
            tags=item.get("tags", ""),
            importance=item.get("importance", 0),
            uses=item.get("uses", 0),
            updated=item.get("last_used") or item.get("created", ""),
            status="active",
            evidence=" ".join(
                part
                for part in (item.get("by", ""), item.get("src", ""), item.get("rev", ""))
                if part
            ),
        )
        for item in parse_memory(path)
    ]


def collect(root: Path, role: str) -> list[dict]:
    """Lessons + knowledge + the role's memory in one uniform shape.

    Parked records (``superseded``/``archived``) are collected too: the pack
    drops them, the dream pass needs them to see what it already parked.
    """
    return lessons(root, role) + knowledge(root) + memories(root, role)


def _clip(statement: str) -> str:
    return one_line(statement)[:STATEMENT_CLIP]


def render_record(entry: dict) -> str:
    """One rendered line: id, kind, the statement clipped to 200 chars, where it lives."""
    return (
        f"- [{entry.get('id', '')}] {entry.get('kind', '')} | {_clip(entry.get('statement', ''))}"
        f" | {entry.get('pointer', '')}"
    )


def _footer(count: int, total_bytes: int, budget: int | None) -> str:
    cap = "n/a" if budget is None else str(budget)
    return f"# pack: {count} record(s), {total_bytes} bytes (budget {cap})"


def line_bytes(entry: dict) -> int:
    """The UTF-8 bytes one rendered record costs, newline included."""
    return len(render_record(entry).encode("utf-8")) + 1


def rendered_bytes(items: list[dict]) -> int:
    return sum(line_bytes(entry) for entry in items)


def pack(
    entries: list[dict],
    query: str,
    budget_bytes: int,
    now: datetime.date | datetime.datetime,
) -> list[dict]:
    """The best injectable records until the rendered bytes, footer included, would overspend.

    Entries are taken in rank order and the whole rendered pack - record lines
    plus the ``# pack:`` footer - is kept at or under ``budget_bytes``. The one
    exception is the first record: an entry list is never turned into an empty
    pack, so a single oversized record is still returned and its footer says so.
    Parked records are never injected.
    """
    candidates = [
        entry for entry in entries if str(entry.get("status") or "") in INJECTABLE_STATUSES
    ]
    taken: list[dict] = []
    total = 0
    for entry in rank(candidates, query, now):
        cost = line_bytes(entry)
        footer = len(_footer(len(taken) + 1, total + cost, budget_bytes).encode("utf-8")) + 1
        if total + cost + footer <= budget_bytes:
            taken.append(entry)
            total += cost
            continue
        if not taken:
            taken.append(entry)
        break
    return taken


def render_pack(items: list[dict], total_bytes: int, budget: int | None = None) -> str:
    """The pack as printed: one pointer line per record, then the byte footer."""
    lines = [render_record(entry) for entry in items]
    lines.append(_footer(len(items), total_bytes, budget))
    return "\n".join(lines) + "\n"


def render_search(
    entries: list[dict],
    query: str,
    now: datetime.date | datetime.datetime,
    limit: int = SEARCH_LIMIT,
    budget: int = SEARCH_BUDGET_BYTES,
) -> str:
    """Top ``limit`` matches over every store, clipped so the whole output fits ``budget``.

    A record that shares no term with the query is not a match, so an empty result
    is an honest empty result rather than ten weakly ranked records.
    """
    terms = set(tokenize(query))
    candidates = [
        entry
        for entry in entries
        if str(entry.get("status") or "") in INJECTABLE_STATUSES
        and terms & set(record_tokens(entry))
    ]
    ranked = rank(candidates, query, now)[:limit]
    lines: list[str] = []
    total = 0
    for position, entry in enumerate(ranked):
        cost = line_bytes(entry)
        footer = len(_search_footer(position + 1, len(ranked), total + cost).encode("utf-8")) + 1
        if total + cost + footer > budget:
            break
        lines.append(render_record(entry))
        total += cost
    return "\n".join(lines + [_search_footer(len(lines), len(ranked), total)]) + "\n"


def _search_footer(shown: int, total: int, bytes_used: int) -> str:
    return f"# search: {shown} of {total} match(es), {bytes_used} bytes"


def statement_overlap(left: dict, right: dict) -> float:
    """Shared terms as a fraction of the union: 1.0 for the same statement, 0.0 for disjoint."""
    first = set(tokenize(str(left.get("statement") or "")))
    second = set(tokenize(str(right.get("statement") or "")))
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _group_key(entry: dict) -> tuple:
    return (str(entry.get("kind") or ""), normalise_knowledge(entry.get("title", "")))


def _sort_stamp(entry: dict) -> tuple:
    return (str(entry.get("updated") or ""), str(entry.get("id") or ""))


def dream(entries: list[dict], now: datetime.date | datetime.datetime) -> dict:
    """The four maintenance reports of 4.2 over lessons and knowledge.

    ``duplicate`` pairs same-key active records whose statements overlap at 0.8 or
    more and names the newer one to keep; ``contradiction`` pairs same-key active
    records that share too little (under 0.5) to be the same claim and reports
    both without choosing; ``stale`` lists active records with no uses, older than
    90 days and not pinned; ``no_evidence`` lists records whose evidence is
    missing or under 20 characters. Nothing is mutated here.
    """
    scoped = [entry for entry in entries if str(entry.get("kind") or "") in DREAM_KINDS]
    groups: dict[tuple, list[dict]] = {}
    for entry in scoped:
        groups.setdefault(_group_key(entry), []).append(entry)

    duplicates: list[tuple] = []
    contradictions: list[tuple] = []
    claimed: set[str] = set()
    for key, members in sorted(groups.items()):
        ordered = sorted(members, key=lambda entry: str(entry.get("id") or ""))
        for position, left in enumerate(ordered):
            for right in ordered[position + 1 :]:
                if not _is_active(left) or not _is_active(right):
                    continue
                overlap = statement_overlap(left, right)
                if overlap >= DUPLICATE_OVERLAP:
                    keep, drop = (
                        (left, right) if _sort_stamp(left) > _sort_stamp(right) else (right, left)
                    )
                    if drop["id"] in claimed:
                        continue
                    claimed.add(drop["id"])
                    duplicates.append((keep["id"], drop["id"], round(overlap, 3)))
                elif overlap < CONTRADICTION_OVERLAP:
                    contradictions.append(
                        (
                            left["id"],
                            right["id"],
                            f"same {key[0]} key '{key[1]}' but statement overlap"
                            f" {overlap:.2f} < {CONTRADICTION_OVERLAP}",
                        )
                    )

    stale = sorted(
        entry["id"]
        for entry in scoped
        if _is_active(entry)
        and int(_number(entry.get("uses"))) == 0
        and not entry.get("pinned")
        and (age_days(entry, now) or 0.0) > STALE_AFTER_DAYS
    )
    no_evidence = sorted(
        entry["id"]
        for entry in scoped
        if len(str(entry.get("evidence") or "").strip()) < SHORT_EVIDENCE
    )
    return {
        "duplicate": duplicates,
        "contradiction": contradictions,
        "stale": stale,
        "no_evidence": no_evidence,
    }


def _is_active(entry: dict) -> bool:
    return str(entry.get("status") or "") in INJECTABLE_STATUSES


def proposal_scope(entries: list[dict]) -> dict:
    """``id -> file`` for the records a dream pass saw.

    Lesson ids are numbered per role, so ``L-0004`` can name one open lesson in
    every staffed role: the pass must carry the file each id came from or
    ``--apply`` could archive a peer's record.
    """
    return {
        str(entry.get("id") or ""): str(entry.get("pointer") or "").split("#")[0]
        for entry in entries
    }


def _store_file(root: Path, pointer: str) -> Path:
    return root / pointer if pointer else root


def _mutable_files(root: Path, scope: dict | None) -> dict:
    """``file -> (parser, writer)`` for the stores a dream pass may touch."""
    targets: dict[Path, tuple] = {knowledge_path(root): (parse_knowledge, write_knowledge)}
    if scope:
        for pointer in set(scope.values()):
            path = _store_file(root, pointer)
            if path.name == F_LESSONS:
                targets[path] = (parse_lessons, write_lessons)
        return targets
    for directory in roles_dir(root).iterdir() if roles_dir(root).is_dir() else []:
        path = directory / F_LESSONS
        if path.is_file():
            targets[path] = (parse_lessons, write_lessons)
    return targets


def _apply_status(items: list, record_id: str, status: str, superseded_by: str) -> bool:
    """Park one record in place: the status (and the duplicate edge) is all that changes."""
    for item in items:
        if item.get("id") != record_id:
            continue
        if not _is_active(item):
            return False
        item["status"] = status
        if superseded_by and "superseded_by" in item:
            item["superseded_by"] = superseded_by
        return True
    return False


def apply_dream(root: Path, proposals: dict, by: str, scope: dict | None = None) -> dict:
    """Apply the duplicate and stale findings; report the rest; append one ledger event per group.

    Only ``status`` (and ``superseded_by`` on a duplicate's dropped record) is
    written, so no statement is ever rewritten and no record is ever deleted.
    A record that is already parked is left alone, which is what makes a second
    run with the same proposals a no-op: nothing is written and nothing is
    appended. ``scope`` maps an id to the file that holds it (see
    ``proposal_scope``); without it every role's ``Lessons.md`` is scanned.
    """
    from .engine import ledger_append

    counts = {"duplicate": 0, "contradiction": 0, "stale": 0, "no_evidence": 0, "bytes": 0}
    targets = _mutable_files(root, scope)
    groups = (
        ("duplicate", list(proposals.get("duplicate") or [])),
        ("stale", list(proposals.get("stale") or [])),
    )
    for action, wanted in groups:
        applied: list[str] = []
        delta = 0
        for target, (reader, writer) in sorted(targets.items()):
            items = reader(target)
            if not items:
                continue
            before = target.stat().st_size if target.is_file() else 0
            changed: list[str] = []
            if action == "duplicate":
                for keep, drop, _overlap in wanted:
                    if _apply_status(items, str(drop), "superseded", str(keep)):
                        changed.append(str(drop))
            else:
                for record_id in wanted:
                    if _apply_status(items, str(record_id), "archived", ""):
                        changed.append(str(record_id))
            if not changed:
                continue
            writer(target, items)
            delta += target.stat().st_size - before
            applied.extend(changed)
        counts[action] = len(applied)
        counts["bytes"] += delta
        if applied:
            ledger_append(
                root,
                "memory.dream",
                by,
                "",
                f"{action}: {', '.join(sorted(applied))}; bytes {delta:+d}",
            )
    counts["contradiction"] = len(proposals.get("contradiction") or [])
    counts["no_evidence"] = len(proposals.get("no_evidence") or [])
    return counts


def task_query(root: Path, role: str, value: str) -> str:
    """A task id becomes the task's title; anything else is used as written."""
    text = (value or "").strip()
    if not TASK_ID_RE.fullmatch(text):
        return text
    for item in parse_tasks(role_dir(root, role) / F_TASKS):
        if item["id"].upper() == text.upper():
            return one_line(item.get("title") or "") or text
    return text
