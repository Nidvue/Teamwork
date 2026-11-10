"""README images: reserved boxes, resolving badges, and a truthful demo block.

The README's first screen is its conversion surface, and every defect here is one
a reader sees before the first line of prose:

* an image with no intrinsic height makes the page jump while it loads (Design.md
  section 5, "Intrinsic size"), so each in-tree image must declare both dimensions
  in the asset's own aspect ratio;
* a badge whose link or source does not resolve is a broken credential, and badge
  wallpaper is a design regression (Design.md section 4 fixes the set);
* the animated terminal is the README's proof that the install works, so the
  transcript it renders must carry the very commands the quickstart tells the
  reader to run. ``test_skill_contracts`` pins the demo's literal content; this
  guard pins the coupling instead - change the command in the README and the demo
  must change with it, which a literal assertion cannot catch.
"""

from __future__ import annotations

import html
import re
import struct
from pathlib import Path

import pytest

ATTRIBUTE = re.compile(r"([\w-]+)\s*=\s*\"([^\"]*)\"")
IMAGE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
BADGE_LINK = re.compile(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>\s*<img\b([^>]*)>", re.IGNORECASE)
SVG_ROOT = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)
SVG_TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.IGNORECASE | re.DOTALL)
TAG = re.compile(r"<[^>]+>")
BADGE_TABLE_ROW = re.compile(r"^\|\s*(?!Badge|---).+?\|\s*\"([^\"]+)\"\s*\|")
BADGE_HOST = "https://img.shields.io/"
STAR_CHART = "https://api.star-history.com/"


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def readme(root: Path) -> str:
    return (root / "README.md").read_text(encoding="utf-8")


def attributes(tag: str) -> dict[str, str]:
    return {name.lower(): value for name, value in ATTRIBUTE.findall(tag)}


def images(readme: str) -> list[dict[str, str]]:
    return [attributes(tag) for tag in IMAGE.findall(readme)]


@pytest.fixture(scope="module")
def readme_images(readme: str) -> list[dict[str, str]]:
    return images(readme)


def intrinsic_size(path: Path) -> tuple[float, float]:
    """The pixel size the asset itself declares (SVG attributes or PNG IHDR)."""
    if path.suffix.lower() == ".svg":
        match = SVG_ROOT.search(path.read_text(encoding="utf-8"))
        assert match, f"{path} has no <svg> root"
        declared = attributes(match.group(1))
        return _number(declared.get("width", "")), _number(declared.get("height", ""))
    if path.suffix.lower() == ".png":
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
        width, height = struct.unpack(">II", data[16:24])
        return float(width), float(height)
    raise AssertionError(f"{path} is neither an SVG nor a PNG")


def _number(value: str) -> float:
    match = re.match(r"\s*([0-9.]+)", value)
    assert match, f"not a pixel length: {value!r}"
    return float(match.group(1))


def is_local(src: str) -> bool:
    return not re.match(r"^[a-zA-Z][\w+.-]*:", src)


def test_the_image_parser_reads_every_attribute():
    tag = ' src="a.svg" alt="A" width="10" height="20" style="max-width:100%"'
    assert attributes(tag) == {
        "src": "a.svg",
        "alt": "A",
        "width": "10",
        "height": "20",
        "style": "max-width:100%",
    }


def test_every_image_has_a_text_alternative(readme_images):
    missing = [image.get("src", "?") for image in readme_images if not image.get("alt", "").strip()]
    assert missing == [], f"README images without alt text: {missing}"


def test_every_in_tree_image_reserves_a_box_in_its_own_aspect_ratio(root, readme_images):
    defects = []
    checked = 0
    for image in readme_images:
        src = image.get("src", "")
        if not is_local(src):
            continue
        path = root / src
        assert path.exists(), f"README image src does not resolve: {src}"
        checked += 1
        expected_w, expected_h = intrinsic_size(path)
        width, height = image.get("width", ""), image.get("height", "")
        if not width or not height:
            defects.append(f"{src}: declares width={width or 'none'!r} height={height or 'none'!r}")
            continue
        if width.endswith("%") or height.endswith("%"):
            defects.append(f"{src}: a percentage dimension reserves no box ({width} x {height})")
            continue
        ratio = _number(width) / _number(height)
        expected = expected_w / expected_h
        if abs(ratio - expected) > 0.01 * expected:
            defects.append(
                f"{src}: declared {width} x {height} is {ratio:.4f}:1, "
                f"the asset is {expected_w:g} x {expected_h:g} = {expected:.4f}:1"
            )
    assert checked >= 3, f"expected the README's in-tree images, found {checked}"
    assert defects == [], "README images must reserve their intrinsic box: " + "; ".join(defects)


def designed_badges(path: Path) -> set[str]:
    """The Alt text column of the badge table, read by header rather than by shape.

    The table gained a `Declared box` column in M15, so a row-shaped regex either
    missed every row or matched rows of the neighbouring comparison table.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Badge |"))
    header = [cell.strip() for cell in lines[start].strip("|").split("|")]
    column = header.index("Alt text")
    names: set[str] = set()
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) > column:
            names.add(cells[column].strip('"'))
    return names


def test_every_badge_is_the_designed_one_and_resolves(root, readme):
    designed = designed_badges(root / "docs" / "Team" / "Design.md")
    assert len(designed) == 6, (
        f"Design.md section 4 should name 6 badges, parsed {sorted(designed)}"
    )

    found = set()
    charts = 0
    defects = []
    for href, tag in BADGE_LINK.findall(readme):
        linked = attributes(tag)
        src = linked.get("src", "")
        alt = linked.get("alt", "").strip()
        if src.startswith(STAR_CHART):
            charts += 1
            continue
        if not src.startswith(BADGE_HOST):
            defects.append(f"{src or '?'}: linked image is neither a badge nor the star chart")
            continue
        found.add(alt)
        if not alt:
            defects.append(f"{src}: badge without alt text")
        if is_local(href):
            if not (root / href).exists():
                defects.append(f"{alt or href}: link target does not resolve ({href})")
        elif not href.startswith("https://") or " " in href:
            defects.append(f"{alt or '?'}: badge link is not a clean https URL ({href})")
    assert charts == 1, f"expected the one documented star-history chart, found {charts}"
    assert found == designed, (
        "the README badges must be the designed set: "
        f"missing {sorted(designed - found)}, undocumented {sorted(found - designed)}"
    )
    assert defects == [], "badges that do not resolve: " + "; ".join(defects)


def test_the_demo_transcript_shows_the_commands_the_quickstart_documents(root, readme):
    quickstart = re.search(
        r"^## 30-second quickstart[ \t]*\r?\n(.*?)(?=^## )",
        readme,
        re.MULTILINE | re.DOTALL,
    )
    assert quickstart, "the README has no '## 30-second quickstart' section"
    block = quickstart.group(1)
    clone = re.search(r"git clone --depth 1 \S+ \S+", block)
    assert clone, "the quickstart no longer shows a clone command"
    request = re.search(r"^> (use the teamwork skill: .+)$", block, re.MULTILINE)
    assert request, "the quickstart no longer shows the request that starts the team"
    wanted_request = f"> {request.group(1).strip()}"

    demo = (root / "assets" / "demo.svg").read_text(encoding="utf-8")
    transcript = [html.unescape(TAG.sub("", chunk)).strip() for chunk in SVG_TEXT.findall(demo)]
    assert len(transcript) >= 6, f"the demo transcript has {len(transcript)} lines"
    rendered = "\n".join(transcript)
    assert clone.group(0) in rendered, (
        "the demo does not show the clone command the quickstart documents: "
        f"{clone.group(0)!r} not in {transcript}"
    )
    assert wanted_request in rendered, (
        "the demo does not show the request the quickstart documents: "
        f"{wanted_request!r} not in {transcript}"
    )
