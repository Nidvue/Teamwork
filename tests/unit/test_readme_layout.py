"""README layout: the block order ``docs/Team/Design.md`` section 2 requires.

The README is the product's first surface, so its hierarchy is a contract, not
an accident: one pitch, one install block, the proof sections in a fixed order,
no repeated heading and no section that promises content it does not carry.
The order below is Design.md section 2 (blocks 3-13) plus the "30-second
quickstart" heading that block 5 introduces; blocks 1-2 are the hero and the
demo, which carry no ``##`` heading.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BLOCK_ORDER = (
    "Why Teamwork",
    "Features",
    "Install the skill",
    "30-second quickstart",
    "For agents",
    "Common ways to use it",
    "How it works",
    "Teamwork vs alternatives",
    "Architecture at a glance",
    "Roadmap",
    "Contributing, security and license",
    "Star history",
)

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@pytest.fixture(scope="module")
def readme(root: Path) -> str:
    return (root / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lines(readme: str) -> list[str]:
    return readme.splitlines()


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """``(line number, level, title)`` for every ATX heading outside a fence.

    A ``##`` line inside a ``console`` transcript is output the reader is meant to
    see, not a section: the README's ``## provider slots`` sample lives inside one.
    """
    found: list[tuple[int, int, str]] = []
    fence: str | None = None
    for number, line in enumerate(lines, 1):
        marker = FENCE.match(line)
        if marker:
            run = marker.group(1)
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        match = HEADING.match(line)
        if match:
            found.append((number, len(match.group(1)), match.group(2)))
    return found


def fenced_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """``(info string, body lines)`` for every fenced block, in document order."""
    blocks: list[tuple[str, list[str]]] = []
    fence: str | None = None
    info = ""
    body: list[str] = []
    for line in lines:
        marker = FENCE.match(line)
        if marker and fence is None:
            fence = marker.group(1)
            info = line.strip()[len(fence) :].strip()
            body = []
            continue
        if marker and fence is not None and line.strip().startswith(fence):
            blocks.append((info, body))
            fence = None
            continue
        if fence is not None:
            body.append(line)
    assert fence is None, "README.md has an unclosed fenced block"
    return blocks


def section(lines: list[str], title: str) -> list[str]:
    """The body lines of the ``##`` section named ``title``, headings included."""
    start = None
    for number, level, found in headings(lines):
        if start is None:
            if level == 2 and found == title:
                start = number
            continue
        if level <= 2:
            return lines[start : number - 1]
    assert start is not None, f"README.md has no '## {title}' section"
    return lines[start:]


def test_the_heading_parser_ignores_fenced_transcripts():
    """A ``##`` line inside a fence is output the reader sees, not a section."""
    sample = ["```console", "## provider slots", "```", "", "## Real section", "", "body"]
    assert headings(sample) == [(5, 2, "Real section")]


def test_the_sections_are_the_designed_blocks_in_the_designed_order(lines):
    found = [title for _, level, title in headings(lines) if level == 2]
    assert tuple(found) == BLOCK_ORDER, (
        "README.md's ## sections must follow Design.md section 2; expected "
        f"{list(BLOCK_ORDER)}, found {found}"
    )


def test_the_readme_has_one_title(lines, readme):
    markdown_h1 = [title for _, level, title in headings(lines) if level == 1]
    assert markdown_h1 == [], f"the README title is the hero <h1>, not a markdown H1: {markdown_h1}"
    html_h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", readme, re.DOTALL)
    assert [text.strip() for text in html_h1] == ["Nidvue Teamwork"]


def test_no_heading_text_is_repeated(lines):
    seen: dict[str, int] = {}
    repeated = []
    for number, _level, title in headings(lines):
        key = title.casefold()
        if key in seen:
            repeated.append((seen[key], number, title))
        seen.setdefault(key, number)
    assert repeated == [], f"duplicated heading text: {repeated}"


def test_every_section_carries_content(lines):
    """No heading may be followed straight away by the next one of its level."""
    found = headings(lines)
    empty = []
    for index, (number, level, title) in enumerate(found):
        end = len(lines)
        for later_number, later_level, _ in found[index + 1 :]:
            if later_level <= level:
                end = later_number - 1
                break
        body = [line for line in lines[number:end] if line.strip()]
        if not body:
            empty.append((number, title))
    assert empty == [], f"headings with no content: {empty}"


def test_the_quickstart_block_is_a_runnable_install(lines):
    body = section(lines, "30-second quickstart")
    blocks = fenced_blocks(body)
    assert blocks, "the quickstart section needs a fenced block"
    info, block = blocks[0]
    assert info == "bash", f"the quickstart block is bash, not {info!r}"
    commands = [line.strip() for line in block if line.strip() and not line.strip().startswith("#")]
    assert commands, "the quickstart block carries no commands"
    for line in commands:
        assert line.startswith(("$ ", "> ")), f"not a shell line the reader can run: {line!r}"
        assert len(line) > 2, f"empty command: {line!r}"
    joined = " ".join(commands)
    for required in (
        "git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork",
        "rm -rf .agents/skills/teamwork/.git",
        "use the teamwork skill:",
    ):
        assert required in joined, f"the quickstart lost a step it documents: {required}"
    placeholders = re.findall(r"<[A-Za-z][\w-]*>", " ".join(block))
    assert placeholders == [], f"unfilled placeholders in the quickstart: {placeholders}"
