"""The wiki: capped pages whose fact lines point at the records they came from (Memory.md 15.5).

A page is derived state, never a second store: every fact line carries the pointer
of the record it came from, at least two source records back the page, and one page
holds one subject. ``memory search`` and ``context find`` rank a page's fact lines
with the same 4.1 score as the records and pay for them out of the same read
budget, so the wiki competes for bytes instead of adding them.

Only the dream pass writes: ``dream`` proposes, ``apply`` writes, and a page whose
facts all point at parked or drifted records is stubbed or removed with one
``wiki.prune`` ledger event. Nothing here is ever invented - a fact the pass cannot
resolve is reported and left alone.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from .config import WIKI_BUDGET_BYTES, WIKI_MAX_PAGES
from .memorypack import (
    DREAM_KINDS,
    PARKED_STATUSES,
    _group_key,
    _is_active,
    rank,
    record_tokens,
    tokenize,
)
from .names import one_line

DIR_WIKI = "Wiki"
MIN_SOURCES = 2
WIKI_KIND = "wiki"
HEADING_RE = re.compile(r"^# (W-\d{4}) - (.+)$")
SOURCES_RE = re.compile(r"^- sources: (.+)$")
UPDATED_RE = re.compile(r"^- updated: (.+)$")
FACT_RE = re.compile(r"^- (.+?) -> (.+)$")
RECORD_ID_RE = re.compile(r"^(?:K|L|M)-\d{4}$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def pages_dir(root: Path) -> Path:
    return root / DIR_WIKI


def slugify(subject: str) -> str:
    """Lowercase kebab, stable across runs, never empty."""
    slug = SLUG_RE.sub("-", subject.strip().casefold()).strip("-")
    return slug or "page"


def page_path(root: Path, slug: str) -> Path:
    return pages_dir(root) / f"{slug}.md"


def parse_page(path: Path) -> dict | None:
    """One page as ``{id, slug, subject, sources, updated, facts, bytes}``, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    page_id = ""
    subject = ""
    sources: list[str] = []
    updated = ""
    facts: list[dict] = []
    in_facts = False
    for number, line in enumerate(text.splitlines(), start=1):
        if not page_id:
            heading = HEADING_RE.match(line)
            if heading:
                page_id, subject = heading.group(1), heading.group(2).strip()
                continue
        if line.startswith("## "):
            in_facts = line.strip() == "## Facts"
            continue
        found = SOURCES_RE.match(line)
        if found:
            sources = [part.strip() for part in found.group(1).split(",") if part.strip()]
            continue
        found = UPDATED_RE.match(line)
        if found:
            updated = found.group(1).strip()
            continue
        if in_facts:
            fact = FACT_RE.match(line)
            if fact:
                facts.append(
                    {
                        "statement": fact.group(1).strip(),
                        "pointer": fact.group(2).strip(),
                        "line": number,
                    }
                )
    if not page_id:
        return None
    return {
        "id": page_id,
        "slug": path.stem,
        "subject": subject,
        "sources": sources,
        "updated": updated,
        "facts": facts,
        "bytes": len(text.encode("utf-8")),
        "path": path,
    }


def pages(root: Path) -> list[dict]:
    """Every page, id-ascending, so two runs are byte-identical."""
    folder = pages_dir(root)
    if not folder.is_dir():
        return []
    found = [parse_page(path) for path in sorted(folder.glob("*.md"))]
    return sorted((page for page in found if page), key=lambda page: page["id"])


def allocate_id(existing: list[dict]) -> str:
    """Next ``W-0001`` id: never reused, even after a page is pruned."""
    used = [int(page["id"].split("-")[1]) for page in existing]
    return f"W-{max(used, default=0) + 1:04d}"


def render_page(
    page_id: str, subject: str, sources: list[str], facts: list[tuple[str, str]], updated: str
) -> str:
    """The frozen 15.5 page format."""
    lines = [
        f"# {page_id} - {one_line(subject)}",
        "",
        f"- sources: {', '.join(sources)}",
        f"- updated: {updated}",
        "",
        "## Facts",
        *[f"- {one_line(statement)} -> {pointer}" for statement, pointer in facts],
        "",
    ]
    return "\n".join(lines)


def write_page(
    root: Path,
    subject: str,
    sources: list[str],
    facts: list[tuple[str, str]],
    updated: str,
) -> dict:
    """Write one page, or raise ``ValueError`` when it breaks a 15.5 cap."""
    existing = pages(root)
    slug = slugify(subject)
    page_id = ""
    for page in existing:
        if page["slug"] == slug:
            page_id = page["id"]
    if not page_id:
        if len(existing) >= WIKI_MAX_PAGES:
            raise ValueError(f"the wiki is at WIKI_MAX_PAGES ({WIKI_MAX_PAGES})")
        page_id = allocate_id(existing)
    if len(set(sources)) < MIN_SOURCES:
        raise ValueError(f"a page needs {MIN_SOURCES} source records, got {len(set(sources))}")
    text = render_page(page_id, subject, sorted(set(sources)), facts, updated)
    size = len(text.encode("utf-8"))
    if size > WIKI_BUDGET_BYTES:
        raise ValueError(
            f"page {page_id} is {size} bytes, over WIKI_BUDGET_BYTES ({WIKI_BUDGET_BYTES})"
        )
    target = page_path(root, slug)
    if target.is_file() and target.read_text(encoding="utf-8") == text:
        return {"id": page_id, "slug": slug, "bytes": size, "action": "unchanged"}
    folder = pages_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return {"id": page_id, "slug": slug, "bytes": size, "action": "write"}


def fact_entries(page: dict) -> list[dict]:
    """A page's fact lines as record-shaped entries, so one scorer ranks both."""
    return [
        {
            "id": page["id"],
            "kind": WIKI_KIND,
            "statement": fact["statement"],
            "pointer": f"{DIR_WIKI}/{page['slug']}.md#L{fact['line']}",
            "status": "active",
            "importance": 3,
            "uses": 0,
            "updated": page["updated"],
        }
        for fact in page["facts"]
    ]


def find(
    root: Path,
    query: str,
    now: datetime.date | datetime.datetime,
    limit: int,
) -> list[dict]:
    """Page fact lines matching ``query``, ranked with the 4.1 score."""
    terms = set(tokenize(query))
    if not terms:
        return []
    facts = [fact for page in pages(root) for fact in fact_entries(page)]
    return rank([fact for fact in facts if terms & set(record_tokens(fact))], query, now)[:limit]


def _dead(fact: dict, statuses: dict, drifted_ids: set[str]) -> bool:
    pointer = fact["pointer"]
    if not RECORD_ID_RE.match(pointer):
        return False
    return pointer in drifted_ids or str(statuses.get(pointer) or "") in PARKED_STATUSES


def dream(root: Path, entries: list[dict], now: datetime.date | datetime.datetime) -> dict:
    """The wiki half of the dream pass: what to add, edit and prune. Writes nothing."""
    from .memverify import DRIFTED, verify_all

    statuses = {str(entry.get("id") or ""): str(entry.get("status") or "") for entry in entries}
    drifted_ids = {
        str(row["id"]) for row in verify_all(entries, root, now) if row["verify_status"] == DRIFTED
    }
    existing = pages(root)
    by_slug = {page["slug"]: page for page in existing}
    groups: dict[tuple, list[dict]] = {}
    for entry in entries:
        if str(entry.get("kind") or "") not in DREAM_KINDS or not _is_active(entry):
            continue
        groups.setdefault(_group_key(entry), []).append(entry)
    proposals: list[dict] = []
    today = (now.date() if isinstance(now, datetime.datetime) else now).isoformat()
    for (_kind, title), members in sorted(groups.items()):
        active = [entry for entry in members if str(entry.get("id") or "") not in drifted_ids]
        if len(active) < MIN_SOURCES or not title:
            continue
        subject = title.replace("_", " ").strip()
        sources = sorted({str(entry["id"]) for entry in active})
        facts = [(str(entry.get("statement") or ""), str(entry["id"])) for entry in active]
        page = by_slug.get(slugify(subject))
        if page and [(fact["statement"], fact["pointer"]) for fact in page["facts"]] == facts:
            continue
        proposals.append(
            {
                "subject": subject,
                "sources": sources,
                "facts": facts,
                "updated": today,
                "action": "edit" if page else "add",
            }
        )
    prunes = []
    for page in existing:
        if not page["facts"]:
            continue
        if all(_dead(fact, statuses, drifted_ids) for fact in page["facts"]):
            prunes.append({"id": page["id"], "slug": page["slug"]})
    return {"pages": proposals, "prune": prunes}


def apply(root: Path, proposals: dict, by: str) -> dict:
    """Write the proposed pages and prune the dead ones; a second call is a no-op."""
    from .engine import ledger_append

    counts = {"written": 0, "pruned": 0, "bytes": 0}
    for proposal in proposals.get("pages") or []:
        try:
            written = write_page(
                root,
                proposal["subject"],
                proposal["sources"],
                proposal["facts"],
                proposal["updated"],
            )
        except ValueError:
            continue
        if written["action"] == "write":
            counts["written"] += 1
            counts["bytes"] += written["bytes"]
    for target in proposals.get("prune") or []:
        path = page_path(root, target["slug"])
        if not path.is_file():
            continue
        before = path.stat().st_size
        stub = (
            f"# {target['id']} - stub\n\n"
            f"- sources: {', '.join(parse_page(path)['sources']) or '-'}\n"
            "- updated: pruned\n\n"
            "## Facts\n"
            "- every source record is superseded, archived or drifted -> wiki.prune\n"
        )
        path.write_text(stub, encoding="utf-8", newline="\n")
        counts["pruned"] += 1
        counts["bytes"] += path.stat().st_size - before
        ledger_append(
            root, "wiki.prune", by, target["id"], f"stubbed {DIR_WIKI}/{target['slug']}.md"
        )
    return counts
