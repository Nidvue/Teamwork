"""Research is evidence: every verdict row has a verdict, every source has a date.

T-0001 (product-manager), AC-H1: `docs/Team/Research.md` carries a
`## 8. Harness^2 ...` section whose verdict table a reader can audit, and a
`## 7. Sources` list that dates every external claim. Both rot silently - a row
keeps its technique but loses its verdict, a citation loses its access date, a
"concrete surface" names a `teamwork.py` subcommand that was never built or has
since been renamed.

Four properties are pinned here, all deterministic and offline:

1. section 8 exists, after the sources it cites;
2. every verdict-table row names Adopt/Adapt/Reject, H1..H10 are all present,
   every row has a surface and a falsifier, and the rejected rows stay rejected;
3. every external link in section 7 carries an access date;
4. every `teamwork.py ...` code span in section 8 is a real CLI subcommand.

(4) is the one that fails forward: a row naming a planned command fails here
until the command exists, so the section cannot claim a surface the team has not
shipped.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

RESEARCH = Path("docs/Team/Research.md")
SOURCES = "## 7. Sources"
ADOPTED = "## 8. Harness^2"
VERDICTS = ("Adopt", "Adapt", "Reject")
TECHNIQUES = [f"H{n}" for n in range(1, 11)]
# `- [title](https://url) - accessed YYYY-MM-DD`
ACCESS_DATE = re.compile(r"accessed \d{4}-\d{2}-\d{2}")
LINK = re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
SEPARATOR = re.compile(r"^[\s|:-]+$")
# the surface column must name something a reader can open: a command or a path
SURFACE = re.compile(r"`(?:teamwork\.py|python3|[\w./<>*-]+\.(?:py|md|jsonl))")


def research(repo_root: Path) -> str:
    return (repo_root / RESEARCH).read_text(encoding="utf-8")


def slice_section(text: str, heading: str) -> str:
    """One `## heading` section, up to the next level-2 heading."""
    start = text.find(heading)
    assert start >= 0, f"{RESEARCH} has no {heading!r} section"
    rest = text[start + len(heading) :]
    end = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def verdict_rows(section: str) -> list[list[str]]:
    """Body rows under the header that carries both `Verdict` and `Falsifier`."""
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        if "Verdict" in line and "Falsifier" in line:
            rows = []
            for row in lines[index + 1 :]:
                stripped = row.strip()
                if not stripped.startswith("|"):
                    break
                if SEPARATOR.match(stripped):
                    continue
                rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
            return rows
    pytest.fail("section 8 has no verdict table with a Verdict and a Falsifier column")


def code_spans(section: str) -> list[str]:
    return [span.strip() for span in CODE_SPAN.findall(section)]


def test_section_8_follows_the_sources_it_cites(repo_root: Path) -> None:
    text = research(repo_root)
    assert ADOPTED in text, f"{RESEARCH} has no {ADOPTED!r} section"
    assert text.index(SOURCES) < text.index(ADOPTED), "section 8 must follow section 7"


def test_every_verdict_row_names_a_verdict(repo_root: Path) -> None:
    rows = verdict_rows(slice_section(research(repo_root), ADOPTED))
    assert rows, "the verdict table is empty"
    for row in rows:
        assert len(row) == 5, f"row has {len(row)} cells, not 5: {row}"
        technique, _, verdict, surface, falsifier = row
        plain = verdict.strip("* ")
        assert plain.startswith(VERDICTS), f"{technique!r} has no verdict: {verdict!r}"
        assert SURFACE.search(surface), f"{technique!r} names no surface: {surface!r}"
        assert falsifier, f"{technique!r} has no falsifier"

    techniques = [row[0] for row in rows]
    for wanted in TECHNIQUES:
        assert wanted in techniques, f"verdict table is missing {wanted}"
    rejected = [row for row in rows if row[0] == "-"]
    assert len(rejected) >= 3, f"expected at least 3 rejected rows, got {len(rejected)}"
    for row in rows:
        if row[0] in TECHNIQUES:
            assert not row[2].strip("* ").startswith("Reject"), f"{row[0]} is an adopted row"


def test_every_cited_source_is_dated(repo_root: Path) -> None:
    section = slice_section(research(repo_root), SOURCES)
    cited = []
    for line in section.splitlines():
        if not line.startswith("- "):
            continue
        for url in LINK.findall(line):
            cited.append(url)
            assert ACCESS_DATE.search(line), f"{url} has no access date: {line!r}"
    assert cited, "section 7 cites nothing"
    joined = "\n".join(cited)
    for required in ("harness2", "arxiv.org/abs/2610.14224"):
        assert required in joined, f"section 7 does not cite {required}"


def test_every_named_subcommand_exists(repo_root: Path) -> None:
    """A code span beginning `teamwork.py <group> [<verb>]` must be a real command."""
    commands = []
    for span in code_spans(slice_section(research(repo_root), ADOPTED)):
        tokens = span.split()
        if not tokens or tokens[0] != "teamwork.py" or len(tokens) < 2:
            continue
        group = tokens[1]
        verb = tokens[2] if len(tokens) > 2 and not tokens[2].startswith(("-", "<")) else None
        commands.append([part for part in (group, verb) if part])
    assert commands, "section 8 names no teamwork.py command to verify"

    seen = set()
    for argv in commands:
        key = tuple(argv)
        if key in seen:
            continue
        seen.add(key)
        result = subprocess.run(
            [sys.executable, "scripts/teamwork.py", *argv, "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"section 8 names `teamwork.py {' '.join(argv)}`, which the CLI rejects: "
            f"{(result.stderr or result.stdout).strip().splitlines()[-1]}"
        )


def test_every_named_path_is_shipped(repo_root: Path) -> None:
    """A code span that looks like a repo path must resolve in the tree."""
    for span in code_spans(slice_section(research(repo_root), ADOPTED)):
        if "/" not in span or "." not in span or span.endswith("/") or " " in span:
            continue
        if any(char in span for char in "<>*"):
            continue
        assert (repo_root / span).exists(), f"section 8 names a path that is not shipped: {span}"
