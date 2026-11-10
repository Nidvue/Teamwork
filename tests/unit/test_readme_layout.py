"""README layout: the slim front door ``docs/Team/Design.md`` section 2 requires.

The README is the product's first surface, so its hierarchy is a contract, not
an accident: one pitch, one install block, the proof blocks in a fixed order, no
repeated heading and no section that promises content it does not carry. The
order below is Design.md section 2 - the hero and the demo carry no ``##``
heading - and the depth it used to carry now lives on the linked guide pages.

Two properties are pinned besides the order: the README stays a front door
(``MAX_BYTES`` = 10 KiB), and the documentation map it carries names every guide page in
``mkdocs.yml``, so a moved section cannot become an orphan.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BLOCK_ORDER = (
    "What makes it different",
    "Install the skill",
    "30-second quickstart",
    "What you get",
    "Documentation",
    "Contributing, security and license",
)

MAX_BYTES = 10 * 1024

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
NAV_PAGE = re.compile(r"^\s*-\s+[^:\n]+:\s+(guide/[^\s]+\.md)\s*$", re.MULTILINE)


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
    see, not a section.
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


def test_the_readme_stays_a_front_door(readme):
    """Depth moved to docs/: the README must not grow back into the manual."""
    size = len(readme.encode("utf-8"))
    assert size <= MAX_BYTES, f"README.md is {size} B, over the {MAX_BYTES} B front-door cap"


def test_the_documentation_map_names_every_guide_page(root, readme):
    """A page the nav publishes must be reachable from the README too."""
    map_block = "\n".join(section(readme.splitlines(), "Documentation"))
    nav = (root / "mkdocs.yml").read_text(encoding="utf-8")
    pages = set(NAV_PAGE.findall(nav))
    assert len(pages) >= 10, f"mkdocs.yml nav lists {len(pages)} guide pages"
    missing = sorted(page for page in pages if f"(docs/{page})" not in map_block)
    assert missing == [], f"README documentation map does not link {missing}"


def test_the_differentiator_block_is_bounded_and_links_its_proof(lines):
    """5-7 rows, each naming the page that proves it - no unsourced claim."""
    body = section(lines, "What makes it different")
    rows = [line for line in body if line.startswith("| **")]
    assert 5 <= len(rows) <= 7, f"the differentiator table has {len(rows)} row(s)"
    for row in rows:
        assert re.search(r"\]\(docs/[^)\s]+\)", row), f"row has no proof link: {row}"


def test_the_top_hooks_point_at_the_evidence(readme):
    """The three hooks above the fold each carry a link, not a paragraph."""
    intro = readme.split("## What makes it different", 1)[0]
    for hook in (
        "Developed by AI agents, for AI agents",
        "One prompt in, a whole company out",
        "It improves from its own failures",
    ):
        assert hook in intro, hook
    assert "(docs/Team/Archive.md)" in intro
    assert "(docs/Team/Evolution.md)" in intro
    assert "(#30-second-quickstart)" in intro
    assert "confounded" in intro, "EV-0004 is confounded, not no-observed-effect"
    assert "no observed effect" not in intro
    assert "refuses a close" not in intro, "a routine is not a gate at this revision"
    assert "all but two commits" in intro, "the author claim must be bounded"


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
