"""The GitHub social preview: one committed card, built from the README pitch.

``assets/social-preview.png`` is the only raster on a Teamwork surface and the one
asset no reader can check by scrolling, so its contract has to be measured:

* it is an open-graph container - 1280 x 640, 8-bit RGB, no alpha and no metadata
  chunk (``docs/Team/Design.md`` section 3, IMG-1);
* the bytes on disk are the committed bytes, and the card is the file the release
  publishes, so a working-tree-only preview cannot ship;
* no second, unreferenced preview raster exists;
* its pitch is the README's pitch, not a text typed once into a raster: the card
  is reproducible only if a committed generator derives that pitch from
  ``README.md``. The glyphs themselves are not read back here - a raster has no
  text layer - so the guard is the generator's input, which is what can regress.
"""

from __future__ import annotations

import html
import re
import struct
import subprocess
from pathlib import Path

import pytest

CARD = "assets/social-preview.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PITCH = re.compile(r"<p><strong>([^<]+)</strong></p>")
PREVIEW_NAME = re.compile(r"(social|preview|open-?graph|og[-_]?image|card)", re.IGNORECASE)
RASTER = (".png", ".jpg", ".jpeg", ".webp", ".gif")
GENERATOR_HINT = "social-preview.png"


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def card(root: Path) -> Path:
    return root / CARD


@pytest.fixture(scope="module")
def tracked(root: Path) -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def chunks(data: bytes) -> list[tuple[str, bytes]]:
    """``(type, payload)`` for every chunk in a PNG, in file order."""
    assert data[:8] == PNG_SIGNATURE, "not a PNG"
    found: list[tuple[str, bytes]] = []
    offset = 8
    while offset < len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8].decode("ascii")
        payload = data[offset + 8 : offset + 8 + length]
        found.append((kind, payload))
        offset += 12 + length
    return found


def header(data: bytes) -> tuple[int, int, int, int]:
    """``(width, height, bit depth, colour type)`` from the IHDR chunk."""
    first, payload = chunks(data)[0]
    assert first == "IHDR", f"first chunk is {first}, not IHDR"
    width, height, depth, colour = struct.unpack(">IIBB", payload[:10])
    return width, height, depth, colour


def readme_pitch(root: Path) -> str:
    found = PITCH.findall((root / "README.md").read_text(encoding="utf-8"))
    assert found, "README.md has no <p><strong>pitch</strong></p> line"
    assert len(found) == 1, f"the README pitch must be one sentence, found {found}"
    return found[0].strip()


def test_the_chunk_parser_reads_a_header():
    ihdr = struct.pack(">IIBBBBB", 1280, 640, 8, 2, 0, 0, 0)
    sample = b"".join(
        [
            PNG_SIGNATURE,
            struct.pack(">I", 13),
            b"IHDR",
            ihdr,
            b"\x00\x00\x00\x00",
            struct.pack(">I", 0),
            b"IEND",
            b"\x00\x00\x00\x00",
        ]
    )
    assert [kind for kind, _ in chunks(sample)] == ["IHDR", "IEND"]
    assert header(sample) == (1280, 640, 8, 2)


def test_the_card_is_the_open_graph_container(card):
    data = card.read_bytes()
    width, height, depth, colour = header(data)
    assert (width, height) == (1280, 640), (
        f"the open-graph card is 1280 x 640, not {width} x {height}"
    )
    assert depth == 8, f"colour depth {depth}, expected 8"
    assert colour == 2, f"colour type {colour}, expected 2 (RGB, no alpha)"
    kinds = [kind for kind, _ in chunks(data)]
    assert kinds[0] == "IHDR" and kinds[-1] == "IEND", kinds
    assert kinds.count("IDAT") >= 1, "the card carries no image data"
    ancillary = [kind for kind in kinds if kind[0].islower()]
    assert ancillary == [], f"the card must carry no metadata chunk (alpha or text): {ancillary}"


def test_the_card_bytes_are_the_committed_bytes(root, card):
    listed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", CARD], cwd=root, capture_output=True, text=True
    )
    assert listed.returncode == 0, f"{CARD} is not tracked: {listed.stderr.strip()}"
    committed = subprocess.run(
        ["git", "rev-parse", f"HEAD:{CARD}"], cwd=root, capture_output=True, text=True
    )
    assert committed.returncode == 0, committed.stderr
    on_disk = subprocess.run(["git", "hash-object", CARD], cwd=root, capture_output=True, text=True)
    assert on_disk.returncode == 0, on_disk.stderr
    assert on_disk.stdout.strip() == committed.stdout.strip(), (
        "the preview on disk is not the committed card: "
        f"HEAD:{CARD} is {committed.stdout.strip()}, the file hashes to {on_disk.stdout.strip()}"
    )


def test_the_card_is_the_preview_the_release_publishes(root, card):
    build = (root / "scripts" / "build_pi_package.py").read_text(encoding="utf-8")
    preview = re.search(r"^PREVIEW\s*=\s*(.+)$", build, re.MULTILINE)
    assert preview, "scripts/build_pi_package.py no longer declares PREVIEW"
    assert CARD in preview.group(1), (
        f"the published preview must name the committed card, it points at {preview.group(1).strip()}"
    )
    attributes = (root / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(rf"^{re.escape(CARD)}\s+.*-filter", attributes, re.MULTILINE), (
        f"{CARD} must stay opted out of Git LFS, or the shipped bytes are a pointer"
    )
    assert card.stat().st_size < 1024 * 1024, "the card must stay below the LFS threshold"


def test_no_unreferenced_preview_raster_is_committed(root, tracked):
    previews = [
        rel
        for rel in tracked
        if rel.lower().endswith(RASTER) and PREVIEW_NAME.search(Path(rel).stem)
    ]
    assert CARD in previews, f"the tracked preview raster set changed: {previews}"
    references = {}
    for rel in tracked:
        if rel.startswith("tests/"):
            continue
        if not rel.lower().endswith((".md", ".py", ".yml", ".yaml", ".toml", ".json", ".cff")):
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        references[rel] = text
    unreferenced = []
    for rel in previews:
        name = Path(rel).name
        citing = [other for other, text in references.items() if other != rel and name in text]
        if not citing:
            unreferenced.append(rel)
    assert unreferenced == [], f"preview rasters nothing references: {unreferenced}"


def generators(root: Path, tracked: list[str]) -> list[tuple[str, str]]:
    """Tracked, non-test scripts that write the card (the pitch's only source)."""
    found = []
    for rel in tracked:
        if not rel.endswith(".py") or rel.startswith("tests/"):
            continue
        source = (root / rel).read_text(encoding="utf-8", errors="replace")
        if GENERATOR_HINT in source and "save(" in source:
            found.append((rel, source))
    return found


def test_the_card_pitch_is_the_readme_pitch(root, tracked):
    pitch = readme_pitch(root)
    found = generators(root, tracked)
    assert len(found) == 1, (
        "the card must be reproducible from one committed generator that writes it "
        f"(found {[rel for rel, _ in found]}); without it the pitch is baked "
        "into a raster and cannot be checked"
    )
    rel, source = found[0]
    assert pitch not in source, (
        f"{rel} hardcodes the pitch; a README change would no longer reach the card"
    )
    patterns = re.findall(r"r\"([^\"]+)\"", source) + re.findall(r"r'([^']+)'", source)
    readme = (root / "README.md").read_text(encoding="utf-8")
    extracted = []
    for pattern in patterns:
        try:
            match = re.search(pattern, readme)
        except re.error:
            continue
        if not match:
            continue
        value = match.group(1) if match.groups() else match.group(0)
        extracted.append(html.unescape(value).strip())
    assert pitch in extracted, (
        f"{rel} no longer derives the card's pitch from README.md: no pattern it carries "
        f"extracts {pitch!r} from the README (patterns tried: {len(patterns)})"
    )
