#!/usr/bin/env python3
"""Render the GitHub social preview card (assets/social-preview.png).

Inputs, all committed:
  - docs/assets/nidvue-icon.svg - the Nidvue mark, rasterised with cairosvg
  - README.md - the canonical pitch, read from its <p><strong>...</strong></p> line

The card is composed at 4x and downsampled so the text is crisp. The mark is
rendered separately at 600 px and resized to its 168 px placement: it is already
a raster of a vector, and resampling it with the card would blur its 1 px frame.

Text uses Pillow's BASIC layout, not the Raqm/HarfBuzz default: BASIC is what
produced the review-approved card, and Raqm kerns the title about 5 px tighter,
which would move every letter off the approved position.

Output: 1280x640, 8-bit RGB (colour type 2), no alpha and no metadata chunk.

Requires Pillow and cairosvg. The repository's Windows venv has neither; the
repository's WSL .venv has both. Run it from the repository root:

    .venv/bin/python scripts/render_social_preview.py

Options:
  --output PATH   write the card elsewhere (default assets/social-preview.png)
"""

from __future__ import annotations

import argparse
import html
import io
import re
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
ICON = REPO / "docs" / "assets" / "nidvue-icon.svg"
README = REPO / "README.md"
OUTPUT = REPO / "assets" / "social-preview.png"

WIDTH, HEIGHT = 1280, 640
SUPERSAMPLE = 4

MARK_SOURCE = 600
MARK_SIZE = 168
MARK_TOP_LEFT = (556, 118)

NAME = "Nidvue Teamwork"
NAME_SIZE = 72
NAME_FILL = (17, 17, 38)
NAME_CENTER = (639.5, 362)

RULE = (276, 400, 1004, 407)
RULE_FILL = (88, 87, 232)

BODY_SIZE = 32
BODY_FILL = (76, 76, 102)
PITCH_CENTER = (639.5, 456.5)
DESC = "An evidence-gated, auditable multi-agent team for any repository."
DESC_CENTER = (639.5, 501.5)

FONT_DIRS = (
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
)


def font_path(name: str) -> str:
    for directory in FONT_DIRS:
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    raise SystemExit(
        f"missing {name}: install the DejaVu fonts or run this where they exist "
        "(the repository's WSL .venv has them)"
    )


def read_pitch(readme: Path) -> str:
    match = re.search(r"<p><strong>([^<]+)</strong></p>", readme.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"no <p><strong>pitch</strong></p> line in {readme}")
    return html.unescape(match.group(1)).strip()


def render_mark() -> Image.Image:
    png = cairosvg.svg2png(
        url=str(ICON),
        output_width=MARK_SOURCE,
        output_height=MARK_SOURCE,
    )
    mark = Image.open(io.BytesIO(png)).convert("RGBA")
    if mark.size != (MARK_SIZE, MARK_SIZE):
        mark = mark.resize((MARK_SIZE, MARK_SIZE), Image.Resampling.LANCZOS)
    return mark


def render(pitch: str) -> Image.Image:
    scale = SUPERSAMPLE
    canvas = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    layout = ImageFont.Layout.BASIC
    name_font = ImageFont.truetype(
        font_path("DejaVuSans-Bold.ttf"), NAME_SIZE * scale, layout_engine=layout
    )
    body_font = ImageFont.truetype(
        font_path("DejaVuSans.ttf"), BODY_SIZE * scale, layout_engine=layout
    )

    draw.text(
        (NAME_CENTER[0] * scale, NAME_CENTER[1] * scale),
        NAME,
        font=name_font,
        fill=NAME_FILL,
        anchor="mm",
    )
    draw.rectangle(tuple(value * scale for value in RULE), fill=RULE_FILL)
    draw.text(
        (PITCH_CENTER[0] * scale, PITCH_CENTER[1] * scale),
        pitch,
        font=body_font,
        fill=BODY_FILL,
        anchor="mm",
    )
    draw.text(
        (DESC_CENTER[0] * scale, DESC_CENTER[1] * scale),
        DESC,
        font=body_font,
        fill=BODY_FILL,
        anchor="mm",
    )

    card = canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    mark = render_mark()
    card.paste(mark, MARK_TOP_LEFT, mark)
    return card


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    card = render(read_pitch(README))
    card.save(args.output, format="PNG", optimize=True)
    print(f"wrote {args.output} ({card.width}x{card.height}, {card.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
