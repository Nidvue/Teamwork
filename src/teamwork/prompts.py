"""The prompt record: the original, each research round, and the enhanced prompt.

The intake has three artifacts and they answer different questions:

* **Original** - what the user actually wrote, verbatim. The only ground truth
  when an intent dispute arrives, so it is never edited.
* **Research rounds** - what each pass found, with its evidence. One round is
  often enough; a second is required when the first leaves a fact unresolved or
  a term contested, because "I read it once" is not an understanding.
* **Enhanced** - the prompt rewritten from that understanding: the same intent,
  stated precisely enough to build from, with every addition marked `added:` so
  the user can reject it. This is the artifact the plan decomposes; the original
  stays the authority.

The gate is the point: a fresh project cannot record acceptance criteria until an
enhanced prompt exists, because criteria are what "done" means and freezing them
before the prompt is understood is how a team builds the wrong thing quickly.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from .io import atomic_write
from .names import one_line
from .records import masked_text

PROMPT_HEADER = (
    "# PROMPT - the request, what research found, and the enhanced prompt\n\n"
    "> Three artifacts: the original prompt verbatim (never edited), one entry per\n"
    "> research round with its evidence, and the enhanced prompt the plan\n"
    "> decomposes. Manage with `teamwork.py prompt record|show`.\n\n"
    "Related: [team map](TeamMap.md) | [questions](Questions.md) | "
    "[criteria](Criteria.md)\n"
)

PROMPT_RE = re.compile(r"^##\s+(P-\d+)\s*(?:·|:)?\s*(.*)$")

FIELD_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")

PROMPT_FIELDS = (
    "recorded_by",
    "created",
    "rounds",
    "enhanced_by",
    "evidence",
)

MIN_ROUNDS = 1


def today_iso() -> str:
    return datetime.date.today().isoformat()


def new_prompt(
    original: str,
    enhanced: str,
    rounds: list,
    by: str = "",
    evidence: str = "",
) -> dict:
    """One record: the verbatim original, the enhanced prompt and the rounds."""
    return {
        "id": "",
        "title": one_line(original)[:80] or "prompt",
        "original": original.strip(),
        "enhanced": enhanced.strip(),
        "rounds": [one_line(item) for item in rounds if one_line(item)],
        "recorded_by": one_line(by),
        "created": today_iso(),
        "enhanced_by": one_line(by),
        "evidence": one_line(evidence),
    }


def render_prompt(items: list) -> str:
    """A record whose original and enhanced text are kept as fenced blocks."""
    highest = 0
    for item in items:
        tail = str(item.get("id") or "").split("-", 1)[-1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    for item in items:
        if not item.get("id"):
            highest += 1
            item["id"] = f"P-{highest:04d}"
    out = [PROMPT_HEADER, ""]
    for item in sorted(items, key=lambda p: p["id"]):
        out.append(f"## {item['id']} · {item.get('title') or 'prompt'}")
        for field in PROMPT_FIELDS:
            value = item.get(field)
            if field == "rounds":
                value = str(len(item.get("rounds") or []))
            out.append(f"- {field}: {one_line(str(value or ''))}")
        out.append("")
        out.append("### Original prompt (verbatim)")
        out.append("")
        out.append("```text")
        out.extend((item.get("original") or "").splitlines() or [""])
        out.append("```")
        out.append("")
        out.append("### Research rounds")
        out.append("")
        for index, round_text in enumerate(item.get("rounds") or [], start=1):
            out.append(f"{index}. {round_text}")
        if not item.get("rounds"):
            out.append("- none recorded")
        out.append("")
        out.append("### Enhanced prompt")
        out.append("")
        out.append("```text")
        out.extend((item.get("enhanced") or "").splitlines() or [""])
        out.append("```")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def parse_prompt(path: Path) -> list:
    """Read the records back: the fields, the original and the enhanced text."""
    if not path.exists():
        return []
    out: list = []
    cur = None
    section = ""
    fence: list = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PROMPT_RE.match(raw)
        if match:
            if cur:
                out.append(cur)
            cur = new_prompt("", "", [])
            cur["id"] = match.group(1)
            cur["title"] = match.group(2).strip()
            section = ""
            continue
        if cur is None:
            continue
        if raw.startswith("### "):
            section = raw[4:].strip().lower()
            continue
        if raw.strip() == "```text":
            section = section + ":fence"
            fence = []
            continue
        if raw.strip() == "```" and section.endswith(":fence"):
            key = "original" if section.startswith("original") else "enhanced"
            cur[key] = "\n".join(fence).strip("\n")
            section = section.replace(":fence", "")
            fence = []
            continue
        if section.endswith(":fence"):
            fence.append(raw)
            continue
        field = FIELD_RE.match(raw)
        if field and field.group(1) in PROMPT_FIELDS:
            if field.group(1) == "rounds":
                continue
            cur[field.group(1)] = field.group(2).strip()
            continue
        if section.startswith("research rounds") and re.match(r"^\d+\.\s", raw):
            cur["rounds"].append(raw.split(".", 1)[1].strip())
    if cur:
        out.append(cur)
    return sorted(out, key=lambda p: p["id"])


def write_prompt(path: Path, items: list) -> None:
    atomic_write(path, masked_text(render_prompt(items)))


def latest_prompt(items: list):
    """The most recent record, or ``None`` on a fresh team."""
    return items[-1] if items else None


def has_enhanced(items: list) -> bool:
    item = latest_prompt(items)
    return bool(item and (item.get("enhanced") or "").strip())
