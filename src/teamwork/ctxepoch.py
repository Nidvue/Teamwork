"""Context epoch: the compaction count of the session that produced a claim.

Revision binding says a result belongs to one tree. That half of the rule is
worthless inside one long lane: the tree never moved, yet the model that ran
the command no longer holds its output - a context compaction replaced the
transcript with a summary. So a run also records *which context* produced it,
and a citation from an earlier epoch of the same session is refused rather
than trusted.

The signal is the host session transcript, whose path the host exports as
``PI_SESSION_FILE``: every compaction appends one entry with ``"type":
"compaction"``. The epoch is therefore ``<PI_SESSION_ID>@<compactions>``. A
session that never set the variables has no epoch, and every comparison on an
empty or unknown epoch answers "not stale" - the rule binds a context it can
see, and says nothing about one it cannot. Only the same session id is
comparable: two lanes have no order between their contexts, and the revision
axis already governs a cross-lane claim.

Owner: developer. Related: references/Evidence.md
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _compactions(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"compaction"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") == "compaction":
                count += 1
    return count


def epoch() -> str:
    """``<session>@<compactions>``, ``<session>@?`` when the transcript is absent."""
    session = (os.environ.get("PI_SESSION_ID") or "").strip()
    if not session:
        return ""
    raw = (os.environ.get("PI_SESSION_FILE") or "").strip()
    if not raw or not Path(raw).is_file():
        return f"{session}@?"
    return f"{session}@{_compactions(Path(raw))}"


def stale(record: str, live: str) -> bool:
    """True when ``record`` was written in an earlier compaction of ``live``'s session."""
    if not record or not live or record.endswith("@?") or live.endswith("@?"):
        return False
    record_session, _, record_count = record.rpartition("@")
    live_session, _, live_count = live.rpartition("@")
    if record_session != live_session or not (record_count.isdigit() and live_count.isdigit()):
        return False
    return int(record_count) < int(live_count)
