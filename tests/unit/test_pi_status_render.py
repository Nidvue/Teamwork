"""The status widget is a real renderer, not a string the test greps for.

Why this test exists: review round 1 found the first extension read `title` and
`progress_pct` off `status --json`, threw `TypeError` on its first refresh, and
passed its own test because that test searched the source text instead of running
the code. This one imports the extension through node's type stripping and calls
`render()` on a payload, so a missing field or a broken template fails here.

The assertions are Design.md 10.5/10.6 at d93efc3d: the 12-line budget, the
frozen row arithmetic, CONSERVATION, AGREEMENT, OVERFLOW and the width rules.

Node is a host tool, not a test dependency: without it the test skips with the
reason, exactly as the package's own smoke tests do.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "extensions" / "tw-status.ts"

ANSI = re.compile(r"\x1b\[[0-9;]*m")

SCRIPT = """
const mod = await import(process.env.TW_EXTENSION);
const { render } = mod;
const payload = JSON.parse(process.env.TW_PAYLOAD);
const width = Number(process.env.TW_WIDTH || 0);
const paint = process.env.TW_PAINT
  ? { fg: (token, text) => `\\u001b[3${token === "success" ? 2 : token === "warning" ? 3 : 1}m${text}\\u001b[0m` }
  : undefined;
let lines;
try {
  lines = width ? render(payload, width, paint) : render(payload, undefined, paint);
} catch (error) {
  console.log(JSON.stringify({ error: String(error && error.message) }));
  process.exit(0);
}
console.log(JSON.stringify({ lines, footer: typeof mod.footer }));
"""


def node() -> str:
    binary = shutil.which("node")
    if not binary:
        pytest.skip("node is not installed, so the extension cannot be executed here")
    probe = subprocess.run(
        [binary, "--experimental-strip-types", "--no-warnings", "-e", "0"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip(f"node {binary} cannot strip TypeScript types: {probe.stderr.strip()[:120]}")
    return binary


def run(payload: dict, width: int | None = None, paint: bool = False) -> dict:
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", SCRIPT],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TW_EXTENSION": EXTENSION.as_uri(),
            "TW_PAYLOAD": json.dumps(payload),
            "TW_WIDTH": str(width or ""),
            "TW_PAINT": "1" if paint else "",
        },
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "error" not in body, body["error"]
    return body


def render(payload: dict, width: int | None = None, paint: bool = False) -> list[str]:
    return run(payload, width, paint)["lines"]


def footer_surface(payload: dict) -> str:
    return run(payload)["footer"]


def feed(busy: int = 3, idle: int = 0, lanes: list[dict] | None = None, review: int = 0) -> dict:
    rows = [
        {
            "instance": f"Developer-{index + 1}",
            "role": "developer",
            "state": "busy",
            "task": f"T-00{70 + index}",
            "title": "pi extension tw-status",
            "elapsed_text": f"{index + 1}m",
            "progress_pct": (index + 1) * 20,
            "last": "tests.run TS-0001 - 76 passed in 35s",
            "last_seconds": 12 + index,
            "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
            "provider": "deepinfra",
        }
        for index in range(busy)
    ]
    rows += [
        {"instance": f"Idle-{index + 1}", "role": "tester", "state": "idle"}
        for index in range(idle)
    ]
    return {
        "schema": 4,
        "count": busy + idle,
        "counts": {
            "busy": busy,
            "idle": idle,
            "review": review,
            "lanes_live": len(
                [lane for lane in (lanes or []) if lane["state"] in ("starting", "running")]
            ),
            "activated": busy + idle + 8,
            "retired": 13,
            "lanes_ended": 124,
        },
        "instances": rows,
        "lanes": lanes or [],
    }


LANE_ONLY = [
    {
        "id": f"L-04{20 + index}",
        "instance": f"Ghost-{index + 1}",
        "role": "tester",
        "task": f"T-01{30 + index}",
        "state": "running",
        "elapsed_text": "12m",
        "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
        "provider": "deepinfra",
        "attempt": "1/2",
    }
    for index in range(3)
]


def shown_and_hidden(lines: list[str]) -> tuple[int, int]:
    shown = sum(1 for line in lines if line.startswith("●"))
    hidden = 0
    for line in lines:
        match = re.match(r"^\+(\d+) more busy$", line)
        if match:
            hidden = int(match.group(1))
    return shown, hidden


def test_the_frozen_budget_holds_for_every_fixture() -> None:
    matrix = [
        feed(1, 1),
        feed(3, 2, LANE_ONLY, review=1),
        feed(5, 0, LANE_ONLY),
        feed(21, 0, LANE_ONLY),
        feed(21, 4, LANE_ONLY),
        feed(0, 6),
    ]
    for payload in matrix:
        for width in (24, 40, 60, 80, 100):
            lines = render(payload, width)
            assert len(lines) <= 12, (payload["count"], width, lines)
            assert max(len(line) for line in lines) <= width, (width, lines)


def test_a_dropped_seat_is_always_counted_and_the_count_is_exact() -> None:
    payload = feed(21, 0, LANE_ONLY)
    lines = render(payload, 100)
    shown, hidden = shown_and_hidden(lines)
    assert len(lines) == 12, lines
    assert (shown, hidden) == (10, 11), lines
    assert lines[-1] == "+11 more busy", "the overflow line is the last line when rows are hidden"
    assert not [line for line in lines if line.startswith("◇")], "lanes yield to the hidden count"
    for candidate in (feed(5, 0, LANE_ONLY), feed(3, 2), feed(1, 1), feed(0, 6)):
        lines = render(candidate, 100)
        shown, hidden = shown_and_hidden(lines)
        assert shown + hidden == candidate["counts"]["busy"], lines
        assert (hidden > 0) == any(line.endswith("more busy") for line in lines), lines


def test_the_header_prints_live_and_review_only_and_the_widget_is_the_only_surface() -> None:
    payload = schema5(
        [busy_row(), stalled_row()], {"busy": 1, "stalled": 1, "lanes_live": 2, "review": 3}
    )
    result = run(payload, 100)
    assert result["lines"][0] == "teamwork · 2 live · 3 review", result["lines"]
    assert "busy" not in result["lines"][0], "the busy count is not a header count"
    assert "stalled" not in result["lines"][0], "the stalled count is not a header count"
    assert result["footer"] == "undefined", "the footer status surface was deleted, not renamed"
    zero = run(schema5([busy_row()], {"busy": 1, "stalled": 0, "lanes_live": 0, "review": 0}), 100)
    assert zero["lines"][0] == "teamwork", "a zero count is omitted, separator included"


def test_the_lanes_are_drawn_last_from_the_room_the_rows_leave() -> None:
    payload = feed(5, 0, LANE_ONLY)
    lines = render(payload, 100)
    assert len(lines) == 9, lines
    lanes = [line for line in lines if line.startswith("◇")]
    assert len(lanes) == 3, lines
    assert lanes[0].startswith("◇ L-0420 Ghost-1 T-0130 ▸ run"), lanes[0]
    assert lines.index(lanes[0]) > max(
        index for index, line in enumerate(lines) if line.startswith("●")
    ), "a lane line never takes a line from a busy row"
    assert "deepinfra/" not in "\n".join(lines), "the model name is the signal, not the provider"


def test_a_narrow_terminal_drops_columns_and_never_a_headless_row() -> None:
    payload = feed(3, 1)
    for width in (24, 40, 60, 80, 100):
        lines = render(payload, width)
        for line in lines[1:]:
            assert line[0] in "●◇○+", (width, line)
        rows = [line for line in lines if line.startswith("●")]
        assert len(rows) == 3, (width, lines)
        for row in rows:
            instance = row.split()[1]
            assert len(instance) >= 6, (width, row)
            assert instance.startswith("Developer"), (width, row)
    narrow = render(payload, 40)
    wide = render(payload, 100)
    assert "tests.run" not in "\n".join(narrow), "below 56 columns the activity column is gone"
    assert "tests.run" in "\n".join(wide)
    assert "░" not in "\n".join(wide), "no bar on any line, at any width"
    assert "█" not in "\n".join(wide), "the bar is deleted, not shrunk"


def test_a_null_progress_keeps_the_tail_columns_aligned() -> None:
    rows = [
        busy_row("Developer", progress_pct=None),
        busy_row(
            "Tester",
            progress_pct=None,
            elapsed_seconds=720,
            budget_seconds=None,
            remaining_seconds=None,
            remaining_text="-",
        ),
    ]
    body = [line for line in run(schema5(rows, {"busy": 2}), 100)["lines"] if line.startswith("●")]
    assert len(body) == 2, body
    assert body[0].index("▸") == body[1].index("▸"), body
    assert "█" not in "\n".join(body) and "░" not in "\n".join(body), "the bar is deleted"
    assert not any(line.endswith(" ") for line in body), "no row is padded to the edge"


def test_a_review_lane_is_named_by_its_task_and_never_by_its_owner() -> None:
    payload = feed(2, 1, review=1)
    payload["instances"][0].update(
        {"instance": "Reviewer-1", "role": "reviewer", "task": "developer/T-0071"}
    )
    payload["instances"][1].update({"instance": "Developer", "task": "designer/T-0001"})
    body = "\n".join(render(payload, 100))
    assert "↳T-0071" in body, body
    assert "T-0001" in body
    assert "developer/" not in body and "designer/" not in body


def test_a_row_whose_task_is_not_an_identity_is_clipped_to_the_column() -> None:
    row = busy_row("Developer", task="unassigned-work")
    body = [line for line in run(schema5([row], {"busy": 1}), 100)["lines"] if line.startswith("●")]
    assert body, "the row must still be drawn"
    cell = body[0].split()[2]
    assert cell.endswith("…"), body[0]
    assert len(cell) <= 7, body[0]


def test_a_payload_without_title_or_progress_renders_instead_of_throwing() -> None:
    bare = {
        "schema": 4,
        "count": 1,
        "counts": {"busy": 1},
        "instances": [
            {"instance": "Developer", "role": "developer", "state": "busy", "task": "T-0070"}
        ],
        "lanes": [],
    }
    lines = run(bare, 100)["lines"]
    assert lines[0] == "teamwork", lines
    assert "undefined" not in "\n".join(lines), lines
    assert "NaN" not in "\n".join(lines), lines


def test_an_empty_feed_stays_silent_and_draws_no_footer() -> None:
    assert render({}) == []
    empty = {"schema": 4, "count": 0, "counts": {"busy": 0}, "instances": [], "lanes": []}
    assert render(empty) == []
    assert footer_surface(empty) == "undefined"


def test_two_calls_on_one_payload_return_the_same_lines() -> None:
    payload = feed(6, 2, LANE_ONLY, review=2)
    assert render(payload, 100) == render(payload, 100)


def test_colour_is_redundant_with_the_glyph_and_the_word() -> None:
    payload = feed(3, 1, LANE_ONLY, review=1)
    plain = render(payload, 100)
    painted = render(payload, 100, paint=True)
    assert any("\x1b[" in line for line in painted), "the renderer must colour the glyphs"
    assert [ANSI.sub("", line) for line in painted] == plain
    words = " ".join(plain)
    for word in ("run", "T-0070", "●"):
        assert word in words, words


def schema5(rows: list[dict], counts: dict | None = None, lanes: list[dict] | None = None) -> dict:
    return {
        "schema": 5,
        "count": len(rows),
        "counts": counts if counts is not None else {},
        "instances": rows,
        "lanes": lanes or [],
    }


def busy_row(instance: str = "Developer", **extra) -> dict:
    row = {
        "instance": instance,
        "role": "developer",
        "state": "busy",
        "task": "T-0070",
        "title": "payload schema 5",
        "elapsed": 300,
        "elapsed_text": "5m00s",
        "elapsed_seconds": 300,
        "budget_seconds": 1200,
        "remaining_seconds": 900,
        "remaining_text": "15m00s",
        "progress": "attempt 1/2, 25% of 20m",
        "progress_pct": 25,
        "activity": "lane started L-0141",
        "stalled": False,
        "last": "lane.start L-0141 - developer/T-0070 attempt 1/2",
        "last_seconds": 12,
        "model": "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        "provider": "deepinfra",
    }
    row.update(extra)
    return row


def stalled_row(instance: str = "ReleaseEngineer") -> dict:
    return {
        "instance": instance,
        "role": "release-engineer",
        "state": "stalled",
        "stalled": True,
        "task": "T-0002",
        "title": "release",
        "elapsed": None,
        "elapsed_text": "-",
        "elapsed_seconds": None,
        "budget_seconds": None,
        "remaining_seconds": None,
        "remaining_text": "-",
        "progress": "claimed, no live lane",
        "progress_pct": None,
        "activity": "lane lost L-0123",
        "last": "lane.finish L-0123 - lost exit=- result=- task=T-0002",
        "last_seconds": 120,
        "model": "",
        "provider": "",
    }


def left_cell(line: str) -> str:
    found = re.search(r"▸\s+(\S+)", line)
    assert found, line
    return found.group(1)


def test_left_is_real_and_clamped_at_zero() -> None:
    rows = [
        busy_row("Developer"),
        busy_row(
            "Tester",
            progress_pct=100,
            elapsed_seconds=1500,
            budget_seconds=1200,
            remaining_seconds=0,
            remaining_text="0s",
        ),
        busy_row(
            "Reviewer",
            progress_pct=None,
            elapsed_seconds=None,
            budget_seconds=None,
            remaining_seconds=None,
            remaining_text="-",
        ),
    ]
    lines = run(schema5(rows, {"busy": 3}))["lines"]
    cells = {line.split()[1]: left_cell(line) for line in lines if line.startswith("●")}
    assert cells == {"Developer": "15m", "Tester": "0s", "Reviewer": "-"}, cells


def test_release_engineer_is_never_clipped() -> None:
    row = busy_row("ReleaseEngineer", role="release-engineer", task="T-0002")
    for width in (120, 100, 80, 72, 60, 48):
        lines = run(schema5([row], {"busy": 1}), width)["lines"]
        body = [line for line in lines if line.startswith("●")]
        assert body, (width, lines)
        assert "ReleaseEngineer" in body[0], (width, body[0])
        assert "ReleaseE…" not in body[0], (width, body[0])
        assert max(len(line) for line in lines) <= width, (width, lines)


def test_a_stalled_seat_is_drawn_as_stalled_and_never_as_busy() -> None:
    lines = run(schema5([busy_row(), stalled_row()], {"busy": 1, "stalled": 1}))["lines"]
    assert lines[0] == "teamwork", "neither the busy nor the stalled count is a header count"
    stalled = [line for line in lines if line.startswith("▲")]
    assert len(stalled) == 1, lines
    assert "stalled" in stalled[0], stalled[0]
    assert "▸" not in stalled[0], "a stalled row carries no left clock"
    assert "█" not in stalled[0] and "░" not in stalled[0], "a stalled row carries no bar"
    assert "lane lost" in stalled[0], stalled[0]
    busy = [line for line in lines if line.startswith("●")]
    assert len(busy) == 1, lines
    assert "stalled" not in busy[0], busy[0]


def test_one_line_per_agent_and_no_idle_line() -> None:
    rows = [busy_row(f"Developer-{n}") for n in range(1, 5)]
    rows.append(stalled_row("Tester"))
    rows.append(
        busy_row(
            "IdleSeat",
            state="idle",
            task="",
            elapsed_seconds=None,
            budget_seconds=None,
            remaining_seconds=None,
            remaining_text="-",
            activity="",
            last="",
            stalled=False,
        )
    )
    lines = run(schema5(rows, {"busy": 4, "stalled": 1}))["lines"]
    body = [line for line in lines if line[:1] in "●▲"]
    assert len(body) == 5, lines
    names = [line.split()[1] for line in body]
    assert len(set(names)) == 5, names
    assert not [line for line in body if "IdleSeat" in line], "an idle seat is a count, not a row"
    assert not [line for line in lines if "idle" in line], lines
    assert len(lines) == 6, lines


def test_the_line_budget_and_the_hidden_count_stay_exact() -> None:
    rows = [busy_row(f"Developer-{n}") for n in range(1, 16)]
    lines = run(schema5(rows, {"busy": 15}), 100)["lines"]
    assert len(lines) == 12, lines
    assert lines[-1] == "+5 more busy", lines


def test_a_schema_four_payload_still_renders_with_dashes() -> None:
    legacy = {
        "schema": 4,
        "count": 1,
        "counts": {"busy": 1, "lanes_live": 0, "review": 0},
        "instances": [
            {
                "instance": "Developer",
                "role": "developer",
                "state": "busy",
                "task": "T-0070",
                "elapsed_text": "3m01s",
                "progress_pct": None,
                "last": "tests.run - 12 passed",
            }
        ],
        "lanes": [],
    }
    lines = run(legacy, 100)["lines"]
    body = [line for line in lines if line.startswith("●")]
    assert body, lines
    assert "3m01s" in body[0], "the schema-4 elapsed_text still fills the used clock"
    assert left_cell(body[0]) == "-", body[0]
    assert "undefined" not in "\n".join(lines) and "NaN" not in "\n".join(lines)
    assert "%" not in "\n".join(lines), "the bar carries no percentage text"


def test_an_unknown_state_renders_its_own_word() -> None:
    row = busy_row("Developer", state="paused", activity="lane paused L-9")
    lines = run(schema5([row], {"busy": 0}), 100)["lines"]
    assert any("paused" in line for line in lines), lines


def test_every_width_keeps_every_line_inside_the_bound() -> None:
    rows = [busy_row("ReleaseEngineer"), busy_row("Developer"), stalled_row("Tester")]
    for width in (120, 100, 80, 72, 60, 56, 48, 40, 32):
        lines = run(schema5(rows, {"busy": 2, "stalled": 1}), width)["lines"]
        assert lines, width
        assert max(len(line) for line in lines) <= width, (width, lines)
        assert len(lines) <= 12, (width, lines)


def test_the_activity_is_capped_at_28_columns_and_never_padded() -> None:
    row = busy_row("Developer", activity="a long activity string that runs well past the cap")
    body = [line for line in run(schema5([row], {"busy": 1}), 100)["lines"] if line.startswith("●")]
    assert body, "the busy row is drawn"
    assert "…" in body[0], body[0]
    assert not body[0].endswith(" "), "the line ends at its last visible character"
    assert len(body[0]) < 100, "the row is never filled to the terminal edge"


def test_the_activity_is_clipped_at_a_word_boundary_not_mid_token() -> None:
    row = busy_row("Developer", activity="alpha beta gamma delta epsilon zeta")
    body = [line for line in run(schema5([row], {"busy": 1}), 100)["lines"] if line.startswith("●")]
    assert body, "the busy row is drawn"
    assert "delta…" in body[0], body[0]
    assert "epsil…" not in body[0], "a partial token is never emitted"


def test_a_short_activity_leaves_a_short_line() -> None:
    short = [
        line
        for line in run(schema5([busy_row("Developer", activity="lane done")], {"busy": 1}), 100)[
            "lines"
        ]
        if line.startswith("●")
    ]
    long = [
        line
        for line in run(
            schema5(
                [busy_row("Developer", activity="a long activity that fills the whole cell")],
                {"busy": 1},
            ),
            100,
        )["lines"]
        if line.startswith("●")
    ]
    assert short and long
    assert len(short[0]) < len(long[0]), (short, long)
    assert not short[0].endswith(" ")


EMOJI_CAPABLE = {
    0x23F8,
    0x25B6,
    0x25C0,
    0x25FB,
    0x25FC,
    0x25FD,
    0x25FE,
    0x2699,
    0x26A0,
}


def test_every_glyph_the_renderer_draws_is_one_cell_wide() -> None:
    """Design.md 10.10: a glyph the terminal can widen breaks every column after it.

    `⏸` (U+23F8) and `▶` (U+25B6) carry Emoji_Presentation=Yes, so they are two
    cells by default; `⚠` (U+26A0) and `⚙` (U+2699) are emoji-capable, so a font
    that prefers colour emoji widens them. `EMOJI_CAPABLE` is the set this widget
    can reach - the four it drew plus the geometric shapes that share the class -
    because no stdlib call answers the question (East Asian width reports `N` or
    `A` for all of them). The row is a fixed-width table, so the class is a defect
    whatever this font decides today.
    """
    text = (ROOT / "extensions" / "tw-status.ts").read_text(encoding="utf-8")
    table = re.search(r"const GLYPH = \{([^}]*)\}", text)
    assert table, "the renderer has no glyph table"
    glyphs = re.findall(r':\s*"([^"]+)"', table.group(1))
    assert len(glyphs) >= 8, glyphs

    for glyph in glyphs:
        for char in glyph:
            point = ord(char)
            assert point not in EMOJI_CAPABLE, (
                f"glyph {glyph!r} (U+{point:04X}) is emoji-capable, so a terminal "
                "may draw it two cells wide"
            )
