"""Transcript reach: the ledger and the worklogs as a searchable store.

The implementation of ``docs/Team/Memory.md`` 10. The transcript is the one store
the engine writes on every action and never reads, so it was write-only: the
ledger and the per-instance worklogs grew on disk while ``context find`` and
``recall`` could not see a single line of them. This module makes them
retrievable without a second store, an index, or a model call.

Two append-only sources, both already on disk, one hit per unit:

* ``<team>/Ledger.jsonl`` -> ``Ledger.jsonl#<n>`` (1-based line number), one hit
  per ledger event, rendered from the event's action/actor/target/detail fields
  so the reader sees the event and not a raw JSON blob;
* ``Agents/<Instance>/WorkLog.md`` -> ``Agents/<Instance>/WorkLog.md:<line>``,
  one hit per non-blank line.

Ranking is the frozen 4.1 score of ``memorypack``: a hit is built in the same
record shape, so ``memorypack.score`` and ``memorypack.render_record`` are called
rather than re-implemented and a transcript hit ranks exactly like any other
record. The output is capped at ``SEARCH_LIMIT`` hits and ``SEARCH_BUDGET_BYTES``
with the ``# search:`` footer ``memory search`` prints, and a rendered hit clips
its text to 200 characters.

The reader streams. ``iter_hits`` opens one file at a time and yields as it goes,
so a 100k-line ledger costs one line of memory rather than the file, and
``collect`` keeps a bounded top-``limit`` heap rather than every match, so the
peak footprint is the cap and not the corpus.

Owner: developer. Related: docs/Team/Memory.md
"""

from __future__ import annotations

import datetime
import heapq
import json
from collections.abc import Iterator
from pathlib import Path

from .config import DIR_AGENTS, F_WORKLOG
from .layout import agent_dir, list_agents
from .memorypack import (
    SEARCH_BUDGET_BYTES,
    SEARCH_LIMIT,
    _search_footer,
    line_bytes,
    record_tokens,
    render_record,
    score,
    tokenize,
)
from .names import one_line

SCOPE = "transcripts"
LEDGER_FILE = "Ledger.jsonl"
EVENT_KIND = "event"
WORKLOG_KIND = "worklog"
SOURCES = f"{LEDGER_FILE}, {DIR_AGENTS}/<Instance>/{F_WORKLOG}"
EVENT_FIELDS = ("action", "actor", "target", "detail")
NO_MATCH = '# no transcript line matched "{}"'


def _now(now: datetime.date | datetime.datetime | None) -> datetime.date:
    if now is None:
        return datetime.date.today()
    return now.date() if isinstance(now, datetime.datetime) else now


def _hit(pointer: str, kind: str, text: str, stamp: str) -> dict:
    """One transcript line in the record shape the 4.1 scorer and renderer expect."""
    return {
        "id": pointer,
        "kind": kind,
        "store": SCOPE,
        "title": "",
        "statement": one_line(text),
        "tags": "",
        "importance": 0,
        "uses": 0,
        "updated": stamp,
        "status": "active",
        "evidence": "",
        "pointer": pointer,
    }


def _event_text(event: dict, raw: str) -> str:
    """The event's own fields, never the JSON blob: action, by, subject, body."""
    parts = [str(event.get(field) or "") for field in EVENT_FIELDS]
    text = " | ".join(one_line(part) for part in parts if one_line(part))
    return text or one_line(raw)


def _iter_ledger(root: Path) -> Iterator[dict]:
    path = Path(root) / LEDGER_FILE
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                event = json.loads(text)
            except ValueError:
                event = {}
            if not isinstance(event, dict):
                event = {}
            yield _hit(
                f"{LEDGER_FILE}#{number}",
                EVENT_KIND,
                _event_text(event, text),
                str(event.get("ts") or "")[:10],
            )


def _iter_worklogs(root: Path) -> Iterator[dict]:
    for instance in list_agents(root):
        path = agent_dir(root, instance) / F_WORKLOG
        if not path.is_file():
            continue
        where = f"{DIR_AGENTS}/{instance}/{F_WORKLOG}"
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                text = one_line(line)
                if not text:
                    continue
                yield _hit(f"{where}:{number}", WORKLOG_KIND, text, "")


def iter_hits(root: Path, query: str) -> Iterator[dict]:
    """Every transcript line that shares a term with ``query``, streaming, in file order.

    A line that shares no term is not a hit, so an empty result is an honest empty
    result. The generator holds one line at a time: it takes a root, not a corpus.
    """
    terms = set(tokenize(query))
    if not terms:
        return
    for entry in _iter_ledger(root):
        if terms & set(record_tokens(entry)):
            yield entry
    for entry in _iter_worklogs(root):
        if terms & set(record_tokens(entry)):
            yield entry


def collect(
    root: Path,
    query: str,
    limit: int = SEARCH_LIMIT,
    budget: int = SEARCH_BUDGET_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> tuple[list[dict], int]:
    """The top ``limit`` hits and the number ranked, both already inside ``budget``.

    The heap is capped at ``limit`` entries, so a ledger with a million matching
    events costs ten records in memory. ``total`` is the ranked count the footer
    reports and ``len(hits)`` is what survived the byte budget.
    """
    if limit <= 0:
        return [], 0
    stamp = _now(now)
    best: list[tuple[float, str, dict]] = []
    for entry in iter_hits(root, query):
        heapq.heappush(best, (score(entry, tokenize(query), stamp), entry["id"], entry))
        if len(best) > limit:
            heapq.heappop(best)
    ranked = sorted(best, key=lambda item: (-item[0], item[1]))
    hits: list[dict] = []
    used = 0
    for position, (_value, _id, entry) in enumerate(ranked):
        cost = line_bytes(entry)
        footer = len(_search_footer(position + 1, len(ranked), used + cost).encode("utf-8")) + 1
        if used + cost + footer > budget:
            break
        hits.append(entry)
        used += cost
    return hits, len(ranked)


def render(hits: list[dict], total: int, budget: int = SEARCH_BUDGET_BYTES) -> str:
    """The hits as printed: one pointer line each, then the ``# search:`` footer."""
    lines = [render_record(entry) for entry in hits]
    used = sum(line_bytes(entry) for entry in hits)
    return "\n".join(lines + [_search_footer(len(hits), total, used)]) + "\n"


def search(
    root: Path,
    query: str,
    limit: int = SEARCH_LIMIT,
    budget: int = SEARCH_BUDGET_BYTES,
    now: datetime.date | datetime.datetime | None = None,
) -> str:
    """The whole transcript answer for one query, capped and footed, or the no-match line."""
    hits, total = collect(root, query, limit, budget, now)
    if total == 0:
        return NO_MATCH.format(query) + "\n"
    return render(hits, total, budget)
