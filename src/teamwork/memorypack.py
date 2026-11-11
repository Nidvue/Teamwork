"""Task-aware memory: scoring, the injected pack, retrieval and the dream pass.

The implementation of ``docs/Team/Memory.md`` 4.1-4.4 and 6. Four surfaces, one
scorer, no model call and no second store:

* ``collect`` reads the three record stores this engine already has - role
  lessons, project knowledge and the role's short-term memory - into one uniform
  shape, so ranking cannot care which file a record came from.
* ``pack`` turns a task query into the smallest set of rendered pointer lines
  that fits a byte budget. It is the injected-context layer: one line per
  record, never a copy of the statement's home.
* ``index_block`` is the header above that pack: the distinct topics of the
  active knowledge records and open lessons as ``- <topic> -> <pointer>`` lines,
  capped at 8 lines and ``INDEX_BUDGET_BYTES`` (Memory.md 11), so the injected
  layer opens with an index instead of a dump. A topic is a label, not a
  sentence: it is clipped to ``TOPIC_CLIP`` characters at a word boundary, and
  ``load`` prints this index *instead of* the verbose lesson rows, so the whole
  command output does not grow by the index's bytes (AC-M22-4).
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
    write_memory,
)

PACK_BUDGET_BYTES = 4000
INDEX_BUDGET_BYTES = 800
SHORT_INJECT_BYTES = 600
SHORT_INJECT_ENTRIES = 5
SHORT_CLIP = 160
SHORT_HEADING = "## Short-term memory for this task"
INDEX_MAX_LINES = 8
INDEX_KINDS = ("knowledge", "lesson")
SEARCH_BUDGET_BYTES = 2000
SEARCH_LIMIT = 10
STATEMENT_CLIP = 200
TOPIC_CLIP = 60
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


def _clip(statement: str, limit: int = STATEMENT_CLIP) -> str:
    return one_line(statement)[:limit]


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


def clip_topic(topic: str, limit: int = TOPIC_CLIP) -> str:
    """A topic as the index may print it: at most ``limit`` chars, cut at a word boundary.

    The index points at a record, so its line carries the record's *label*, not the
    record's sentence: a 168-character lesson mistake is clipped to a phrase and the
    statement (and the rule) stay in their home, which the pointer names. The cut
    lands on the last whole word inside ``limit`` and drops any trailing
    punctuation, so a clipped topic never ends in a dangling ``...`` or comma.
    """
    text = " ".join(str(topic or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut.rstrip():
        cut = cut[: cut.rstrip().rfind(" ")]
    return cut.strip().rstrip(" .,;:-\u2026").strip() or text[:limit].strip()


def index_topics(
    entries: list[dict], query: str, now: datetime.date | datetime.datetime
) -> list[tuple[str, dict]]:
    """The index's topics in rank order: one ``(normalised topic, record)`` per distinct topic.

    A topic is the distinct normalised ``topic`` of an active knowledge record plus
    an open lesson's title (4.1 order, so the same task and the same clock give the
    same list). The first record of a topic is the one its pointer names; a record
    with an empty topic contributes no line, because a bare pointer is not an index.
    """
    seen: dict[str, dict] = {}
    for entry in rank([item for item in entries if _is_index_record(item)], query, now):
        topic = clip_topic(normalise_knowledge(entry.get("title", "")))
        if topic and topic not in seen:
            seen[topic] = entry
    return list(seen.items())


def _is_index_record(entry: dict) -> bool:
    return str(entry.get("kind") or "") in INDEX_KINDS and _is_active(entry)


def _index_footer(body_bytes: int, budget: int) -> str:
    """The ``# index:`` footer, its own byte count solved so the number is exact."""
    guess = body_bytes + 1
    text = ""
    for _ in range(4):
        text = f"# index: {guess} bytes (budget {budget})"
        size = len(text.encode("utf-8")) + 1
        if body_bytes + size == guess:
            return text
        guess = body_bytes + size
    return text


def _index_text(topics: int, records: int, lines: list[str], budget: int) -> str:
    header = f"# memory index: {topics} topic(s), {records} record(s)"
    body = len(header.encode("utf-8")) + 1 + sum(len(line.encode("utf-8")) + 1 for line in lines)
    return "\n".join([header, *lines, _index_footer(body, budget)])


def index_block(
    root: Path,
    role: str,
    task: str = "",
    budget: int = INDEX_BUDGET_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> str:
    """The memory index: a capped pointer list of the topics a task will need.

    The small top layer of the hierarchy (docs/Team/Memory.md 11): at most
    ``INDEX_MAX_LINES`` topic lines, in the 4.1 order for the task's query, and the
    whole block - header, lines and footer - kept at or under ``budget`` bytes by
    dropping any line that would overspend. It points at a record, never at its
    statement, so the header costs bytes once and the statement is still read from
    its home. An empty store prints ``0 topic(s), 0 record(s)`` and no line.

    ``records`` counts the active knowledge records and open lessons the index
    ranks; ``topics`` counts the distinct lines actually printed.
    """
    moment = now or datetime.date.today()
    entries = collect(root, role)
    records = sum(1 for entry in entries if _is_index_record(entry))
    lines: list[str] = []
    for topic, entry in index_topics(entries, task_query(root, role, task), moment)[
        :INDEX_MAX_LINES
    ]:
        line = f"- {topic} -> {entry.get('pointer', '')}"
        trial = _index_text(len(lines) + 1, records, [*lines, line], budget)
        if len(trial.encode("utf-8")) + 1 > budget:
            continue
        lines.append(line)
    return _index_text(len(lines), records, lines, budget)


def index_bytes(
    root: Path,
    role: str,
    task: str = "",
    budget: int = INDEX_BUDGET_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> int:
    """The UTF-8 bytes the index costs when injected, its own newline included."""
    return len(index_block(root, role, task, budget, now).encode("utf-8")) + 1


def injected_budget(
    root: Path,
    role: str,
    task: str = "",
    now: datetime.date | datetime.datetime | None = None,
) -> int:
    """The pack budget left after the index: ``PACK_BUDGET_BYTES - index bytes``.

    The index and the pack are one injected layer, so they share one budget: the
    second guard on AC-M22-4 is that ``index + pack <= PACK_BUDGET_BYTES`` even on
    a store whose pack would otherwise fill the whole 4000 bytes. Never negative -
    an index at or over the budget leaves the pack its one-record minimum.
    """
    spent = index_bytes(root, role, task, now=now) + short_bytes(root, role, task, now=now)
    return max(PACK_BUDGET_BYTES - spent, 1)


def _short_line(entry: dict) -> str:
    """One short-layer pointer line: id, the body clipped to 160 chars, its use count."""
    return (
        f"- [{entry.get('id', '')}] {_clip(entry.get('statement', ''), SHORT_CLIP)}"
        f" (uses {entry.get('uses', 0)})"
    )


def short_entries(
    root: Path,
    role: str,
    task: str = "",
    budget: int = SHORT_INJECT_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> list[dict]:
    """The working notes the short block injects: ranked, at most 5, inside ``budget``.

    The short layer is the role's own file (Memory.md 15.1), so it is ranked by the
    same 4.1 score over the same task query as the pack, and every body is clipped to
    ``SHORT_CLIP`` characters - it is a pointer list, never a copy of the store. A
    line that would overspend the block is dropped, and an empty result means the
    caller prints no heading at all.
    """
    moment = now or datetime.date.today()
    candidates = [
        entry for entry in memories(root, role) if str(entry.get("status")) in INJECTABLE_STATUSES
    ]
    taken: list[dict] = []
    size = len(SHORT_HEADING.encode("utf-8")) + 1
    for entry in rank(candidates, task_query(root, role, task), moment)[:SHORT_INJECT_ENTRIES]:
        cost = len(_short_line(entry).encode("utf-8")) + 1
        if size + cost > budget:
            continue
        taken.append(entry)
        size += cost
    return taken


def short_block(
    root: Path,
    role: str,
    task: str = "",
    budget: int = SHORT_INJECT_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> str:
    """The short block as injected: one heading and one pointer line per entry.

    Empty when the role's short store holds nothing to inject, so the block and its
    heading are omitted entirely and the pack keeps the full remainder of the
    budget.
    """
    entries = short_entries(root, role, task, budget, now)
    if not entries:
        return ""
    return "\n".join([SHORT_HEADING, *(_short_line(entry) for entry in entries)])


def short_bytes(
    root: Path,
    role: str,
    task: str = "",
    budget: int = SHORT_INJECT_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> int:
    """The UTF-8 bytes the short block costs when injected, its own newline included."""
    block = short_block(root, role, task, budget, now)
    return len(block.encode("utf-8")) + 1 if block else 0


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


def dream(
    entries: list[dict],
    now: datetime.date | datetime.datetime,
    project: Path | None = None,
) -> dict:
    """The four maintenance reports of 4.2 over lessons and knowledge.

    ``duplicate`` pairs same-key active records whose statements overlap at 0.8 or
    more and names the newer one to keep; ``contradiction`` pairs same-key active
    records that share too little (under 0.5) to be the same claim and reports
    both without choosing; ``stale`` lists active records with no uses, older than
    90 days and not pinned; ``no_evidence`` lists records whose evidence is
    missing or under 20 characters. ``drifted`` names the records whose evidence
    no longer resolves against the tree, computed by :func:`memverify.verify_all`
    - the same function ``memory verify`` reports - and empty when the caller
    passes no ``project`` to resolve against. Nothing is mutated here.
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
        "drifted": drifted(scoped, project, now),
    }


def drifted(
    entries: list[dict], project: Path | None, now: datetime.date | datetime.datetime
) -> list[tuple[str, str, str]]:
    """``(id, evidence kind, reason)`` for every record whose evidence no longer resolves.

    The computation lives in :mod:`teamwork.memverify` so ``memory verify`` and
    the dream pass can never disagree about what drifted.
    """
    if project is None:
        return []
    from .memverify import DRIFTED, verify_all

    return [
        (str(row["id"]), str(row["kind"]), str(row["reason"]))
        for row in verify_all(entries, project, now)
        if row["verify_status"] == DRIFTED
    ]


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


def _saver(path: Path):
    """The writer for one store file, bound to that file and its owner."""
    if path.name == F_KNOWLEDGE:
        return lambda items: write_knowledge(path, items)
    owner = path.parent.name
    return lambda items: write_memory(path, items, path.name, owner)


def touch_used(root: Path, items: list, by: str) -> int:
    """Count the records a pack injected, so ranking by usefulness stops being inert.

    Injection is the strongest signal that a record was worth its bytes: the pack
    spends budget on it and the agent reads it. Knowledge and memory carry a
    ``uses`` counter and a ``last_used`` date; a lesson has neither, so a lesson is
    left byte-identical rather than given a field its store does not define.

    One write per store file and one ``memory.pack`` ledger event per call, so the
    read path stays cheap: ``n`` records cost two writes, not ``n``.
    """
    import datetime as _datetime

    from .engine import ledger_append

    wanted: dict[str, set] = {}
    for entry in items:
        if str(entry.get("kind") or "") not in ("knowledge", "memory"):
            continue
        pointer = str(entry.get("pointer") or "")
        store, _, record_id = pointer.partition("#")
        if not store or not record_id:
            continue
        wanted.setdefault(store, set()).add(record_id)
    if not wanted:
        return 0
    today = _datetime.date.today().isoformat()
    touched = 0
    for store, ids in sorted(wanted.items()):
        path = _store_file(root, store)
        if not path.is_file():
            continue
        if path.name == F_KNOWLEDGE:
            records = parse_knowledge(path)
        else:
            records = parse_memory(path)
        save = _saver(path)
        changed = 0
        for record in records:
            if str(record.get("id") or "") not in ids:
                continue
            record["uses"] = int(_number(record.get("uses"))) + 1
            record["last_used"] = today
            changed += 1
        if changed:
            save(records)
            touched += changed
    if touched:
        ledger_append(
            root,
            "memory.pack",
            by,
            "",
            f"injected {touched} record(s) from {len(wanted)} store(s)",
        )
    return touched


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
