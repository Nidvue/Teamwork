"""Clarifying questions with options - the gate that stops a guess.

A prompt is a request, not a specification, and the expensive failure is a team
that guesses at an ambiguity and discovers it after the work is built. This store
is the opposite of a guess: an open question names what is unclear, offers 2-5
concrete options, says which one the team recommends and why, and - when it
``blocks`` - holds the loop at CONTINUE until a person answers it.

Two properties make it a gate rather than a note:

* **Options are mandatory.** A question with no alternatives is a request for
  permission, not a decision, and it invites the model to answer itself. Two to
  five options is the shape that forces the asker to have done the reading.
* **A blocking question stops the loop.** ``loop`` reads this store and reports
  CONTINUE while any ``blocks`` question is open, so a team cannot mark itself
  done on an assumption it never surfaced. The record is team-local
  (``Questions.md``, never committed) and every transition is a ledger action.
"""

from __future__ import annotations

import re
from pathlib import Path

from .io import atomic_write
from .names import one_line
from .records import masked_text

QUESTION_BLOCKS = ("intake", "plan", "any")

QUESTION_STATUSES = ("open", "answered", "dropped")

QUESTION_RE = re.compile(r"^##\s+(Q-\d+)\s*(?:·|:)?\s*(.*)$")

OPTION_RE = re.compile(r"^-\s+option\s+(\d+):\s*(.*)$")

META_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")

QUESTION_HEADER = (
    "# QUESTIONS - what the team must ask before it guesses\n\n"
    "> One entry per ambiguity that changes what gets built. Each carries 2-5\n"
    "> concrete options and the team's recommendation; a `blocks:` question holds\n"
    "> `teamwork.py loop` at CONTINUE until a person answers it. Manage with\n"
    "> `teamwork.py ask add|list|answer`.\n\n"
    "Related: [team map](TeamMap.md) | [attention](Attention.md) | "
    "[disputes](Disputes.md)\n"
)

QUESTION_FIELDS = (
    "status",
    "blocks",
    "recommend",
    "asked_by",
    "created",
    "answered_by",
    "answered",
    "choice",
    "note",
)

MIN_OPTIONS = 2

MAX_OPTIONS = 5


def today_iso() -> str:
    import datetime

    return datetime.date.today().isoformat()


def new_question(
    text: str,
    options: list,
    blocks: str = "intake",
    recommend: int = 1,
    by: str = "",
) -> dict:
    """One open question with its options and the team's recommendation."""
    clean = [one_line(option) for option in options if one_line(option)]
    return {
        "id": "",
        "text": one_line(text),
        "options": clean,
        "status": "open",
        "blocks": blocks if blocks in QUESTION_BLOCKS else "intake",
        "recommend": str(recommend if recommend else 1),
        "asked_by": one_line(by),
        "created": today_iso(),
        "answered_by": "",
        "answered": "",
        "choice": "",
        "note": "",
    }


def parse_questions(path: Path) -> list:
    """Every entry in the file, oldest first; an absent file has none."""
    if not path.exists():
        return []
    out: list = []
    cur = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = QUESTION_RE.match(raw)
        if match:
            if cur:
                out.append(cur)
            cur = new_question(match.group(2), [])
            cur["id"] = match.group(1)
            continue
        if cur is None:
            continue
        option = OPTION_RE.match(raw)
        if option:
            value = option.group(2).strip()
            if value.endswith(" (recommended)"):
                value = value[: -len(" (recommended)")]
            cur["options"].append(value)
            continue
        meta = META_RE.match(raw)
        if meta and meta.group(1) in QUESTION_FIELDS:
            cur[meta.group(1)] = meta.group(2).strip()
    if cur:
        out.append(cur)
    return sorted(out, key=lambda q: q["id"])


def assign_question_ids(items: list) -> None:
    """Number the entries that have no id, continuing the highest one in use."""
    highest = 0
    for item in items:
        tail = str(item.get("id") or "").split("-", 1)[-1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    for item in items:
        if not item.get("id"):
            highest += 1
            item["id"] = f"Q-{highest:04d}"


def render_questions(items: list) -> str:
    assign_question_ids(items)
    out = [QUESTION_HEADER, ""]
    for item in sorted(items, key=lambda q: q["id"]):
        out.append(f"## {item['id']} · {one_line(item['text']) or 'question'}")
        for field in QUESTION_FIELDS:
            out.append(f"- {field}: {one_line(item.get(field) or '')}")
        for index, option in enumerate(item.get("options") or [], start=1):
            mark = " (recommended)" if str(index) == str(item.get("recommend")) else ""
            out.append(f"- option {index}: {option}{mark}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_questions(path: Path, items: list) -> None:
    atomic_write(path, masked_text(render_questions(items)))


def find_question(items: list, handle: str):
    """The index of a question by id, or by a substring of its text."""
    raw = (handle or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"Q-\d+", raw.upper()):
        for index, item in enumerate(items):
            if item["id"].upper() == raw.upper():
                return index
        return None
    for index, item in enumerate(items):
        if raw.lower() in item["text"].lower():
            return index
    return None


def open_questions(items: list) -> list:
    return [item for item in items if item.get("status", "open") == "open"]


def blocking_questions(items: list) -> list:
    """The open questions that hold the loop: every ``blocks`` value is a gate."""
    return [item for item in open_questions(items) if (item.get("blocks") or "").strip()]


def question_line(item: dict) -> str:
    """One line of the panel: id, what it blocks, the text, the option count."""
    blocks = f" blocks={item['blocks']}" if item.get("blocks") else ""
    options = len(item.get("options") or [])
    return (
        f"{item['id']}{blocks} [{item['status']}] {item['created']}: "
        f"{item['text']} ({options} option(s))"
    )
