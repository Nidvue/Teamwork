"""The self-evolution books, checked by code instead of trusted to prose.

``docs/Team/Evolution.md`` names four books - metrics, known issues, the evolution
ledger and the promotion backlog - and the close-out rule in its section 11 says
every one of them must be consistent before a milestone is called done. A rule
with no command behind it is a wish, so this module parses the four tables and
turns each close condition into a mechanical finding:

* a metrics row without a command cell cannot be recomputed at the next cut,
  and a tracked metric whose row was deleted is not a fix either;
* an open known issue whose ``re-measure by`` date has passed is freshness debt;
  open means any status short of the lifecycle's terminal ``closed``/``waived``/
  ``escalated``, so an unlisted label cannot hide an overdue row;
* an evolution row whose verdict is not one of the four closed labels is an
  unfalsifiable claim;
* a promotion row without an ``L1``..``L4`` level has no destination.

A missing or empty table is a violation, never a skip: the failure mode this
guards against is a clean report over a page that was never written.

``evolution snapshot`` reads the same tree the ledger sees and prints the current
cut with its id (the ledger record count), so a number is never free-floating.
``teamwork audit`` calls :func:`check` so a close cannot pass with overdue debt.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import NamedTuple

from .layout import project_root, work_docs_dir

DOC_NAME = "Evolution.md"

METRICS = "metrics"
KNOWN = "known"
EVOLUTION = "evolution"
PROMOTION = "promotion"

VERDICTS = ("helped", "hurt", "no observed effect", "confounded")

TRACKED_METRICS = (
    "RFR",
    "Rework",
    "SFR",
    "TTV",
    "Verification waste",
    "Record density",
    "Freshness debt",
    "Promotion lag",
    "Guardrails",
)

MISSING = "MISSING"
EMPTY = "EMPTY"
MALFORMED = "MALFORMED"
OVERDUE = "OVERDUE"
VERDICT = "VERDICT"
LEVEL = "LEVEL"
COMMAND = "COMMAND"
METRIC = "METRIC"

TERMINAL_STATUSES = ("closed", "waived", "escalated")

VERDICT_RE = re.compile(
    r"^(helped|hurt|no\s+observed\s+effect|confounded)(?:\s*\(.*\))?$", re.IGNORECASE
)
LEVEL_RE = re.compile(r"^L([1-4])\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class TableSpec(NamedTuple):
    key: str
    title: str
    match: re.Pattern
    columns: tuple


SPECS = (
    TableSpec(METRICS, "Metrics", re.compile(r"\bmetrics\b", re.IGNORECASE), ("metric", "command")),
    TableSpec(
        KNOWN,
        "Known issues",
        re.compile(r"\bknown issues\b", re.IGNORECASE),
        ("id", "re-measure by", "status"),
    ),
    TableSpec(
        EVOLUTION,
        "Evolution ledger",
        re.compile(r"\bevolution ledger\b", re.IGNORECASE),
        ("id", "verdict"),
    ),
    TableSpec(
        PROMOTION,
        "Promotion backlog",
        re.compile(r"\bpromotion backlog\b", re.IGNORECASE),
        ("record", "level now"),
    ),
)


class Row(NamedTuple):
    line: int
    cells: dict


class Table(NamedTuple):
    key: str
    title: str
    headers: tuple
    rows: list


class Violation(NamedTuple):
    code: str
    where: str
    detail: str


class CheckResult(NamedTuple):
    path: Path
    violations: list

    @property
    def problems(self) -> int:
        return len(self.violations)


def normalise(text: str) -> str:
    """``cell`` with runs of whitespace collapsed and edges trimmed."""
    return " ".join((text or "").split())


def split_cells(line: str) -> list:
    """The cells of one markdown table row, without the outer pipes."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def find_section(lines: list, spec: TableSpec):
    """``(heading index, level)`` of the first heading the spec names."""
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match and spec.match.search(match.group(2)):
            return index, len(match.group(1))
    return None


def section_body(lines: list, heading: int, level: int) -> list:
    """The lines under one heading, up to the next heading at the same or a higher level."""
    body = []
    for line in lines[heading + 1 :]:
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) <= level:
            break
        body.append(line)
    return body


def table_block(body: list) -> list:
    """The first run of table lines in a section; the page has one table per book."""
    block = []
    for line in body:
        if line.strip().startswith("|"):
            block.append(line)
        elif block:
            break
    return block


def parse_table(key: str, title: str, block: list, spec: TableSpec, violations: list):
    """The table, or ``None`` after recording why it could not be read."""
    if not block:
        violations.append(Violation(MISSING, title, "no table found under this heading"))
        return None
    headers = tuple(normalise(cell) for cell in split_cells(block[0]))
    duplicates = sorted({name for name in headers if headers.count(name) > 1})
    if duplicates:
        violations.append(
            Violation(MALFORMED, title, f"duplicate header column(s): {', '.join(duplicates)}")
        )
        return None
    width = len(headers)
    if len(block) < 2 or not all(
        SEPARATOR_RE.match(normalise(cell)) for cell in split_cells(block[1])
    ):
        violations.append(
            Violation(MALFORMED, title, "the header is not followed by a separator row")
        )
        return None
    missing = [column for column in spec.columns if column not in headers]
    if missing:
        violations.append(
            Violation(MALFORMED, title, f"missing required column(s): {', '.join(missing)}")
        )
        return None
    rows = []
    for offset, raw in enumerate(block[2:], start=3):
        cells = split_cells(raw)
        if len(cells) != width:
            violations.append(
                Violation(
                    MALFORMED,
                    f"{title} row {offset}",
                    f"{len(cells)} cell(s) where the header has {width}",
                )
            )
            continue
        rows.append(Row(offset, dict(zip(headers, cells, strict=True))))
    if not rows:
        violations.append(Violation(EMPTY, title, "the table has a header and no data row"))
        return None
    return Table(key, title, headers, rows)


def parse_document(text: str, violations: list) -> dict:
    """The four tables a section names, recording every table it could not read."""
    lines = text.splitlines()
    tables = {}
    for spec in SPECS:
        found = find_section(lines, spec)
        if found is None:
            violations.append(Violation(MISSING, spec.title, "no heading for this book was found"))
            continue
        heading, level = found
        block = table_block(section_body(lines, heading, level))
        table = parse_table(spec.key, spec.title, block, spec, violations)
        if table is not None:
            tables[spec.key] = table
    return tables


def parse_date(text: str):
    """The first ISO date in a cell, or ``None`` when it names a relative trigger."""
    match = ISO_DATE_RE.search(text or "")
    if match is None:
        return None
    try:
        return datetime.date.fromisoformat(match.group(1))
    except ValueError:
        return None


def check_metrics(table: Table, violations: list) -> None:
    names = [normalise(row.cells.get("metric", "")) for row in table.rows]
    for required in TRACKED_METRICS:
        pattern = re.compile(rf"\b{re.escape(required)}\b", re.IGNORECASE)
        if not any(pattern.search(name) for name in names):
            violations.append(
                Violation(
                    METRIC,
                    "Metrics",
                    f"tracked metric '{required}' has no row; deleting the row is not a fix",
                )
            )
    for row in table.rows:
        command = normalise(row.cells.get("command", ""))
        if not command or command in ("-", "\u2014"):
            label = normalise(row.cells.get("metric", f"row {row.line}"))
            violations.append(Violation(COMMAND, f"Metrics {label}", "the command cell is empty"))


def debt_status(status: str) -> bool:
    """True unless the row reached a terminal lifecycle state.

    The lifecycle is ``open -> re-measured -> {closed | waived | escalated}``.
    Everything else - ``open``, ``in flight``, ``filed``, an unlisted word, an
    empty cell - is still debt: an unknown status must not be able to hide an
    overdue row. ``dropped`` is not a known-issue lifecycle state and is treated
    as debt for the same reason.
    """
    return normalise(status).lower() not in TERMINAL_STATUSES


def check_known(table: Table, violations: list, today: datetime.date) -> None:
    for row in table.rows:
        status = normalise(row.cells.get("status", ""))
        due = parse_date(row.cells.get("re-measure by", ""))
        if not debt_status(status) or due is None or due >= today:
            continue
        label = normalise(row.cells.get("id", f"row {row.line}"))
        violations.append(
            Violation(
                OVERDUE,
                f"Known issues {label}",
                f"re-measure by {due.isoformat()} is past and the status is {status or '(empty)'}",
            )
        )


def check_evolution(table: Table, violations: list) -> None:
    for row in table.rows:
        verdict = normalise(row.cells.get("verdict", ""))
        if VERDICT_RE.match(verdict):
            continue
        label = normalise(row.cells.get("id", f"row {row.line}"))
        allowed = ", ".join(VERDICTS)
        violations.append(
            Violation(
                VERDICT,
                f"Evolution ledger {label}",
                f"'{verdict}' is not one of {allowed}",
            )
        )


def check_promotion(table: Table, violations: list) -> None:
    for row in table.rows:
        level = normalise(row.cells.get("level now", ""))
        if LEVEL_RE.match(level):
            continue
        label = normalise(row.cells.get("record", f"row {row.line}"))
        violations.append(Violation(LEVEL, f"Promotion backlog {label}", f"'{level}' is not L1-L4"))


def check_text(text: str, today: datetime.date | None = None) -> list:
    """Every violation in one Evolution page, table errors first, then rows."""
    day = today or datetime.date.today()
    violations: list = []
    tables = parse_document(text, violations)
    if METRICS in tables:
        check_metrics(tables[METRICS], violations)
    if KNOWN in tables:
        check_known(tables[KNOWN], violations, day)
    if EVOLUTION in tables:
        check_evolution(tables[EVOLUTION], violations)
    if PROMOTION in tables:
        check_promotion(tables[PROMOTION], violations)
    return violations


def evolution_path(root: Path) -> Path:
    return work_docs_dir(root) / DOC_NAME


def check(root: Path, today: datetime.date | None = None) -> CheckResult:
    """Read the committed page and return every close-condition violation."""
    path = evolution_path(root)
    if not path.is_file():
        return CheckResult(
            path,
            [Violation(MISSING, "document", f"{path.name} was not found at {path}")],
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return CheckResult(path, [Violation(MISSING, "document", f"unreadable: {exc}")])
    return CheckResult(path, check_text(text, today))


def ledger_count(root: Path) -> int:
    from . import engine

    return len(engine.ledger_read(root))


def test_gap_rows(root: Path):
    """The tests planner's gaps, or ``None`` when the planner cannot be imported."""
    try:
        from . import engine

        gaps = engine.test_gaps(root)
    except (ImportError, AttributeError):
        return None
    return [{"area": area, "layer": layer, "reason": reason} for area, layer, reason in gaps]


def snapshot(root: Path) -> dict:
    """The current cut, read from the ledger and the tree at call time."""
    from . import engine, harness
    from .layout import docs_dir, project_of

    report = engine.throughput_report(root)
    review = report["review"]
    verdicts = review["pass"] + review["fail"]
    fail_share = None if verdicts == 0 else round(review["fail"] * 100.0 / verdicts, 1)
    targets = review["targets"]
    rework = None if targets == 0 else round(review["multi_verdict_targets"] * 100.0 / targets, 1)
    project = project_of(root)
    budget_rows, cap, source = harness.budget_rows(project, root, None)
    startup = [row.always_on for row in budget_rows]
    docs = docs_dir(root)
    archive = docs / "Archive.md"
    result = check(root)
    gaps = test_gap_rows(root)
    surface = report["surface"]
    return {
        "cut": len(engine.ledger_read(root)),
        "review": {
            "verdicts": verdicts,
            "pass": review["pass"],
            "fail": review["fail"],
            "fail_share_pct": fail_share,
            "targets": targets,
            "rework_targets": review["multi_verdict_targets"],
            "rework_pct": rework,
        },
        "ttv": {
            "count": report["review"]["count"],
            "p50_minutes": report["review"]["p50_minutes"],
            "p90_minutes": report["review"]["p90_minutes"],
        },
        "budget": {
            "instances": len(budget_rows),
            "min_bytes": min(startup) if startup else 0,
            "max_bytes": max(startup) if startup else 0,
            "cap_bytes": cap,
            "over": sum(1 for row in budget_rows if row.over),
            "source": source,
        },
        "test_gaps": {
            "available": gaps is not None,
            "count": None if gaps is None else len(gaps),
            "gaps": gaps,
        },
        "archive_bytes": archive.stat().st_size if archive.is_file() else 0,
        "largest_task_queue": {
            "role": surface["largest_task_queue"],
            "bytes": surface["largest_task_queue_bytes"],
        },
        "freshness": {
            "debt": sum(1 for violation in result.violations if violation.code == OVERDUE),
            "check_problems": result.problems,
        },
    }


def render_check(result: CheckResult, cut: int) -> str:
    lines = [f"# evolution check ({result.path})", f"# cut: {cut} ledger records"]
    for violation in result.violations:
        lines.append(f"- {violation.code} {violation.where}: {violation.detail}")
    lines.append(f"# problems found: {result.problems}")
    return "\n".join(lines)


def _minutes(value) -> str:
    return "-" if value is None else f"{value:g}m"


def _share(value) -> str:
    return "-" if value is None else f"{value:g}%"


def render_snapshot(data: dict) -> str:
    review = data["review"]
    ttv = data["ttv"]
    budget = data["budget"]
    gaps = data["test_gaps"]
    queue = data["largest_task_queue"]
    lines = [
        "# evolution snapshot",
        f"cut: {data['cut']} ledger records",
        f"review fail share: {review['fail']}/{review['verdicts']} = "
        f"{_share(review['fail_share_pct'])}",
        f"rework: {review['rework_targets']}/{review['targets']} targets = "
        f"{_share(review['rework_pct'])}",
        f"claim->verdict: p50={_minutes(ttv['p50_minutes'])} "
        f"p90={_minutes(ttv['p90_minutes'])} (n={ttv['count']})",
        f"always-on: {budget['min_bytes']}..{budget['max_bytes']} B "
        f"cap={budget['cap_bytes']} over={budget['over']}/{budget['instances']}",
        f"test gaps: {'unavailable' if gaps['count'] is None else gaps['count']}",
        f"Archive: {data['archive_bytes']} B",
        f"largest task queue: {queue['role'] or '-'} {queue['bytes']} B",
        f"freshness debt: {data['freshness']['debt']} overdue known issue(s), "
        f"{data['freshness']['check_problems']} check problem(s)",
    ]
    return "\n".join(lines)


def cmd_check(args) -> int:
    root = project_root(args)
    cut = ledger_count(root)
    result = check(root)
    if getattr(args, "json", False):
        payload = {
            "command": "evolution.check",
            "path": str(result.path),
            "cut": cut,
            "clean": result.problems == 0,
            "problems": result.problems,
            "violations": [
                {"code": item.code, "where": item.where, "detail": item.detail}
                for item in result.violations
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_check(result, cut))
    return 1 if result.problems else 0


def cmd_snapshot(args) -> int:
    root = project_root(args)
    data = snapshot(root)
    if getattr(args, "json", False):
        print(json.dumps({"command": "evolution.snapshot", **data}, indent=2, sort_keys=True))
    else:
        print(render_snapshot(data))
    return 0


def add_parsers(sub, common) -> None:
    """Register the ``evolution`` command group on the shared argparse tree."""
    group = sub.add_parser(
        "evolution",
        parents=[common],
        help="check and snapshot the self-evolution books in docs/Team/Evolution.md",
    )
    esub = group.add_subparsers(dest="evolution_cmd", required=True)

    parser = esub.add_parser(
        "check", parents=[common], help="exit 1 naming every table or row that breaks a close rule"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.set_defaults(func=cmd_check)

    parser = esub.add_parser(
        "snapshot", parents=[common], help="print the current cut with its ledger id"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.set_defaults(func=cmd_snapshot)
