"""Two pure classifications the gates read: what an evidence line proves, and how
hard a diff is to undo.

Why this exists: the protocol already refuses an empty evidence line, and an empty
line was never the problem. The problem is a line that *looks* like evidence and
cannot fail - "looks good to me", "no errors were thrown", "verified". A model
grading its own work is a model grading its own homework with a friend. So the
grade is a property of the text and a program can compute it, which is the only
kind of check worth having.

The ladder, strongest first, is the one the gates accept:

* ``strong`` - a result a program produced: an exit code, a count with a unit
  (``-> 12 passed``, ``# issues: 0``), a verdict token after an arrow, or a
  content digest. This is the only grade that proves the check ran.
* ``medium`` - a pointer a reader can follow: ``path:line``, a record id
  (``TS-0004``, ``PF-0f1e2d3c4b5a``), a revision (``@a1b2c3d``). Reproducible by
  someone else, not proof the author ran anything.
* ``weak`` - a named command or artifact with no observed result.
* ``noise`` - a self-assessment. It is refused on a pass, because it is the one
  grade that a failing tree produces just as easily as a passing one.

The second classification sorts a diff by how hard it is to undo, which is the
question a gate should ask. A confidence score is a number the model produces
about itself and a threshold is a number someone can lower on a busy Friday; a
closed lane has no number to lower.

Owner: architect. Layer: system. Area: gates.
"""

from __future__ import annotations

import re

EVIDENCE_GRADES = ("strong", "medium", "weak", "noise", "none")

_STRONG = (
    re.compile(r"\bexit\s*(code\s*)?[0-9]+\b", re.IGNORECASE),
    re.compile(r"->\s*(PASS|FAIL|ok|OK|green|red)\b"),
    re.compile(r"->\s*[0-9]+\b"),
    re.compile(r"\b[0-9]+\s*(passed|failed|errors?|issues?|problems?|findings?|warnings?)\b"),
    re.compile(r"#\s*(issues|problems|findings|checks)\b[^0-9]{0,20}[0-9]+"),
    re.compile(r"\b[0-9]+/[0-9]+\b"),
    re.compile(r"\b[0-9a-f]{16}\b"),
    re.compile(r"\b(checks|tests)\b[^0-9]{0,12}[0-9]+\b", re.IGNORECASE),
)

_MEDIUM = (
    re.compile(r"\b[\w./-]+\.(py|md|json|toml|yml|yaml|txt|cfg|ini|sh|ts|tsx|js|rs|go):[0-9]+"),
    re.compile(r"\b(TS|PF|K|L|D|T|AC)-[0-9A-Za-z-]{3,}\b"),
    re.compile(r"@[0-9a-f]{7,40}\b"),
    re.compile(r"\bcommit\s+[0-9a-f]{7,40}\b"),
    re.compile(r"https?://\S+"),
)

_NOISE = (
    re.compile(
        r"^(looks?\s+good|looks?\s+fine|lgtm|verified|confirmed|done|ok|okay|pass|passed|"
        r"good|fine|correct|all\s+good|no\s+errors?(\s+were\s+thrown)?|no\s+problems?|"
        r"no\s+issues?|nothing\s+to\s+report|as\s+above|see\s+(the\s+)?run|"
        r"seems?\s+(fine|correct|good)|checked|reviewed|tested)\b",
        re.IGNORECASE,
    ),
)

_WEAK = (
    re.compile(r"\b(teamwork\.py|pytest|ruff|mypy|make|git|rg|grep|npm|go|cargo|node)\b"),
    re.compile(r"\b[\w./-]+\.(py|md|json|toml|yml|yaml|txt|log)\b"),
    re.compile(r"\bArtifacts/|\bReports/|\bScratch/"),
)


def evidence_grade(text: str) -> str:
    """Classify one evidence line. ``none`` for empty, never a silent ``strong``."""
    value = " ".join(str(text or "").split())
    if not value:
        return "none"
    if any(pattern.search(value) for pattern in _STRONG):
        return "strong"
    if any(pattern.search(value) for pattern in _MEDIUM):
        return "medium"
    if any(pattern.match(value) for pattern in _NOISE):
        return "noise"
    if any(pattern.search(value) for pattern in _WEAK):
        return "weak"
    return "noise"


EVIDENCE_RANK = {"strong": 4, "medium": 3, "weak": 2, "noise": 1, "none": 0}

UNDO_CLASSES = ("revert", "evidence", "closed")

_CLOSED_MARKERS = (
    "migrations/",
    "alembic/",
    ".sql",
    "schema",
    "payment",
    "billing",
    "invoice",
    ".env",
    "secret",
    "credential",
    "auth",
    "crypto",
    "tls",
    "cert",
    ".github/workflows/",
    ".github/actions/",
    "release-exceptions.json",
)

_EVIDENCE_MARKERS = (
    "agents.md",
    "architecture.md",
    "pyproject.toml",
    "makefile",
    "src/teamwork/config.py",
    "src/teamwork/records.py",
    "settings.json",
    ".github/",
)


def undo_class(entries) -> tuple:
    """``(class, reason)`` for a diff given as ``(path, added, deleted)`` rows.

    ``closed`` is the lane no score opens: data and schema changes, secrets and
    auth, a workflow that fires on merge, a release exception, and any deletion of
    a tracked file (a deletion is the one edit a revert cannot always undo).
    ``evidence`` is a wide blast radius that a revert does undo - the constitution,
    the frozen contract, the shared record layer, the build and gate config.
    """
    deleted = [path for path, added, gone in entries if added == 0 and gone > 0]
    if deleted:
        return "closed", f"{len(deleted)} deleted file(s): " + ", ".join(sorted(deleted)[:3])
    for path, _added, _gone in entries:
        low = path.lower()
        marker = next((m for m in _CLOSED_MARKERS if m in low), "")
        if marker:
            return "closed", f"{path} matches {marker!r}"
    for path, _added, _gone in entries:
        low = path.lower()
        marker = next((m for m in _EVIDENCE_MARKERS if m in low), "")
        if marker:
            return "evidence", f"{path} is a shared or frozen surface ({marker})"
    return "revert", "one revert undoes it"
