"""Sparse reading: a bounded, source-anchored evidence pack for one file.

Adopted from SparseRead (https://github.com/Liuzedooong/SparseReading, MIT,
accessed 2026-11-13). The idea that survives the port is the shape, not the
machinery: a **read gate** decides whether a file is worth a sparse read at all,
a typed **hint** says what the reader wants, and the returned **evidence pack**
carries `path:line` provenance so the reader can refine or verify instead of
trusting a summary. A file that is small, binary or explicitly requested whole is
returned by the native path, unchanged - the layer must never make a read worse.

The gate is calibrated on this repository's own surfaces: `SKILL.md` is ~47 kB,
`Archive.md` 4 MB, `Decisions.md` 410 kB and a task queue up to 700 kB, while a
role charter is 7-24 kB. Under 4 kB the whole file is cheaper than the protocol.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SPARSE_MIN_BYTES = 4096
DEFAULT_BUDGET = 4096
CONTEXT_LINES = 3
SCOUT_LINES = 40

MODES = ("native", "scout", "focus", "verify", "full")

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".toml",
    ".cfg",
    ".ini",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".cff",
}


@dataclass(frozen=True)
class Hint:
    """What the reader wants from the file, in the SparseRead sense."""

    query: tuple[str, ...] = ()
    budget: int = DEFAULT_BUDGET
    lines: str = ""
    full: bool = False


@dataclass(frozen=True)
class Snippet:
    start: int
    end: int
    matches: int

    @property
    def provenance(self) -> str:
        return f"{self.start}-{self.end}"


@dataclass
class Pack:
    path: str
    total_bytes: int
    total_lines: int
    mode: str
    reason: str
    snippets: list = field(default_factory=list)
    body: str = ""
    returned_bytes: int = 0
    omitted: int = 0

    @property
    def saved_bytes(self) -> int:
        return max(self.total_bytes - self.returned_bytes, 0)

    @property
    def saved_percent(self) -> float:
        if not self.total_bytes:
            return 0.0
        return round(100.0 * self.saved_bytes / self.total_bytes, 1)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "mode": self.mode,
            "reason": self.reason,
            "total_bytes": self.total_bytes,
            "total_lines": self.total_lines,
            "returned_bytes": self.returned_bytes,
            "saved_bytes": self.saved_bytes,
            "saved_percent": self.saved_percent,
            "snippets": [
                {"start": s.start, "end": s.end, "matches": s.matches} for s in self.snippets
            ],
            "omitted": self.omitted,
        }


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES and path.suffix:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    return data.decode("utf-8", "replace")


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _ranges_for(lines: list, needles: list) -> list:
    """Matching line ranges, merged with a small context, in file order."""
    hits: list[tuple] = []
    for index, line in enumerate(lines, 1):
        low = line.lower()
        matched = sum(1 for needle in needles if needle in low)
        if matched:
            hits.append((index, matched))
    if not hits:
        return []
    ranges: list[tuple] = []
    for number, matched in hits:
        start = max(number - CONTEXT_LINES, 1)
        end = min(number + CONTEXT_LINES, len(lines))
        if ranges and start <= ranges[-1][1] + 1:
            previous = ranges[-1]
            ranges[-1] = (previous[0], max(previous[1], end), previous[2] + matched)
        else:
            ranges.append((start, end, matched))
    return ranges


def _render(lines: list, snippets: list, budget: int) -> tuple[str, list, int, int]:
    """Render snippets until the budget, returning body, kept, bytes, omitted."""
    out: list[str] = []
    kept: list[Snippet] = []
    used = 0
    omitted = 0
    for start, end, matched in snippets:
        block = [f"## {start}-{end} ({matched} match(es))"]
        for number in range(start, end + 1):
            block.append(f"{number}: {lines[number - 1]}")
        text = "\n".join(block) + "\n"
        size = len(text.encode())
        if kept and used + size > budget:
            omitted += 1
            continue
        kept.append(Snippet(start, end, matched))
        out.append(text)
        used += size
    return "".join(out), kept, used, omitted


def read_pack(project: Path, target: str, hint: Hint) -> Pack:
    """Decide the mode for one file and return the pack (never the whole file by accident)."""
    path = Path(target)
    if not path.is_absolute():
        path = (project / target).resolve()
    rel = _relative(path, project)
    if not path.is_file():
        raise FileNotFoundError(f"no file at {rel}")
    text = _read_text(path)
    if text is None:
        size = path.stat().st_size
        return Pack(rel, size, 0, "native", "binary or unsupported type: read it natively", body="")
    raw = path.read_bytes()
    total = len(raw)
    lines = text.splitlines()

    if hint.full:
        return Pack(
            rel,
            total,
            len(lines),
            "full",
            "asked for the native read",
            body=text,
            returned_bytes=total,
        )
    if hint.lines:
        start, end = _parse_lines(hint.lines, len(lines))
        body = "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1)) + "\n"
        return Pack(
            rel,
            total,
            len(lines),
            "verify",
            f"lines {start}-{end}",
            snippets=[Snippet(start, end, 0)],
            body=body,
            returned_bytes=len(body.encode()),
        )
    if total <= SPARSE_MIN_BYTES:
        return Pack(
            rel,
            total,
            len(lines),
            "native",
            f"{total} B is under the {SPARSE_MIN_BYTES} B gate",
            body=text,
            returned_bytes=total,
        )

    needles = [needle.lower() for needle in hint.query if needle.strip()]
    if needles:
        ranges = _ranges_for(lines, needles)
        if not ranges:
            return Pack(
                rel,
                total,
                len(lines),
                "focus",
                "no line matches the query",
                body=f"# no match for {', '.join(hint.query)} in {rel} ({len(lines)} lines)\n",
            )
        body, kept, used, omitted = _render(lines, ranges, hint.budget)
        reason = f"{len(kept)} snippet(s) for {', '.join(hint.query)}"
        if omitted:
            reason += f"; {omitted} more match(es): raise --budget, --lines A-B, or --full"
        return Pack(
            rel,
            total,
            len(lines),
            "focus",
            reason,
            snippets=kept,
            body=body,
            returned_bytes=used,
            omitted=omitted,
        )

    head = lines[:SCOUT_LINES]
    body = "\n".join(f"{n}: {line}" for n, line in enumerate(head, 1)) + "\n"
    body += (
        f"# {len(lines)} lines, {total} B: add --query '<text>' (or --lines A-B) to read a slice\n"
    )
    return Pack(
        rel,
        total,
        len(lines),
        "scout",
        f"no query: first {len(head)} line(s)",
        body=body,
        returned_bytes=len(body.encode()),
    )


def _parse_lines(spec: str, total: int) -> tuple:
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", spec or "")
    if not match:
        raise ValueError(f"--lines '{spec}' is not A-B")
    start = max(int(match.group(1)), 1)
    end = min(int(match.group(2) or start), total)
    if start > end or start > total:
        raise ValueError(f"--lines {spec} is outside the file ({total} lines)")
    return start, end


def _relative(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render(pack: Pack) -> str:
    head = (
        f"# read {pack.path} ({pack.total_bytes} B, {pack.total_lines} line(s)) -> "
        f"{pack.mode}: {pack.reason}\n"
    )
    if pack.mode in ("native", "full"):
        return head + pack.body
    footer = (
        f"# returned {pack.returned_bytes} B, saved {pack.saved_bytes} B "
        f"({pack.saved_percent}% of the file); refine with --query, raise --budget, verify "
        "with --lines A-B, or --full for the native read\n"
    )
    return head + pack.body + footer


def cmd_read(args) -> int:
    from . import engine

    root = engine.project_root(args)
    project = engine.project_of(root)
    hint = Hint(
        query=tuple(args.query or ()),
        budget=max(int(args.budget or DEFAULT_BUDGET), 256),
        lines=args.lines or "",
        full=bool(args.full),
    )
    try:
        pack = read_pack(project, args.path, hint)
    except (FileNotFoundError, ValueError) as exc:
        print(f"# {exc}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps({"command": "read", **pack.as_dict()}, indent=2, sort_keys=True))
    else:
        print(render(pack), end="")
    engine.ledger_append(
        root,
        "read.sparse",
        getattr(args, "by", "") or "ceo",
        pack.path,
        f"mode={pack.mode} bytes={pack.returned_bytes} full={pack.total_bytes} "
        f"saved={pack.saved_percent}",
    )
    return 0


def add_parsers(sub, common) -> None:
    """`read` - the sparse read gate for one file."""
    p = sub.add_parser(
        "read",
        parents=[common],
        help="sparse, source-anchored read of one file (bounded, with provenance)",
    )
    p.add_argument("path", help="the file to read, relative to the project")
    p.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="TEXT",
        help="a needle to match; repeatable, case-insensitive",
    )
    p.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="max returned bytes")
    p.add_argument("--lines", default="", metavar="A-B", help="verify: return exactly these lines")
    p.add_argument("--full", action="store_true", help="native read: the whole file")
    p.add_argument("--by", default="", help="the reader (provenance)")
    p.add_argument("--json", action="store_true", help="machine-readable pack")
    p.set_defaults(func=cmd_read)
