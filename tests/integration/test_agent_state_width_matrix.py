"""The status renderer executed at 40/80/120 columns (ui layer, T-0070 output).

Three questions, each answered by running the extension rather than reading it:

1. width bound - no rendered line is wider than the column it was given;
2. overflow count - a row that does not fit, or that the 12-line budget cannot
   hold, is counted in `+N more busy` and never silently lost: drawn + hidden is
   the number of drawable rows, and no instance is drawn twice or invented;
3. no invented metric - the used and left clocks are re-derived here from
   `elapsed_seconds` / `remaining_seconds` / `budget_seconds` and must match the
   rendered cell, and a payload carrying no numbers renders no clock, no percent
   and no bar fill.

Node is a host tool, not a test dependency: without it the test skips with the
reason, exactly as tests/unit/test_pi_status_render.py does.
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
EXTENSION = ROOT / "extensions" / "teamwork-status.ts"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
WIDTHS = (40, 80, 120)

SCRIPT = """
const { render } = await import(process.env.TW_EXTENSION);
const payload = JSON.parse(process.env.TW_PAYLOAD);
const lines = render(payload, Number(process.env.TW_WIDTH));
console.log(JSON.stringify({ lines }));
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


def draw(payload: dict, width: int) -> list[str]:
    env = {
        **os.environ,
        "TW_EXTENSION": EXTENSION.as_uri(),
        "TW_PAYLOAD": json.dumps(payload),
        "TW_WIDTH": str(width),
    }
    run = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", SCRIPT],
        capture_output=True,
        text=True,
        env=env,
    )
    assert run.returncode == 0, run.stderr.strip()[:400]
    result = json.loads(run.stdout)
    assert "error" not in result, result.get("error")
    return [ANSI.sub("", line) for line in result["lines"]]


def clock(seconds: float) -> str:
    whole = max(0, round(seconds))
    if whole < 60:
        return f"{whole}s"
    if whole < 3600:
        minutes = whole // 60
        return f"{minutes}m" if minutes >= 10 else f"{minutes}m{whole % 60:02d}s"
    return f"{whole // 3600}h{(whole % 3600) // 60:02d}m"


def fixture() -> dict:
    return {
        "schema": 5,
        "count": 6,
        "counts": {"busy": 2, "stalled": 1, "lanes_live": 0},
        "instances": [
            {
                "instance": "Developer",
                "role": "Developer",
                "state": "busy",
                "task": "T-0070",
                "title": "renderer v3 width matrix",
                "elapsed_seconds": 754,
                "budget_seconds": 3600,
                "remaining_seconds": 2846,
                "progress_pct": 21,
                "model": "qwen3-coder-480b",
                "activity": "tests.run width matrix",
            },
            {
                "instance": "ReleaseEngineer",
                "role": "Release Engineer",
                "state": "busy",
                "task": "T-0091",
                "title": "publish the stage",
                "elapsed_seconds": 120,
                "budget_seconds": 600,
                "remaining_seconds": 480,
                "progress_pct": 20,
                "activity": "npm publish",
            },
            {
                "instance": "Reviewer-1",
                "role": "Reviewer",
                "state": "stalled",
                "task": "T-0070",
                "elapsed_seconds": 4000,
                "activity": "lane.finish L-0123 - lost",
            },
            {"instance": "Architect", "role": "Architect", "state": "idle"},
        ],
        "lanes": [],
    }


def drawable(payload: dict) -> list[str]:
    return [row["instance"] for row in payload["instances"] if row.get("state") != "idle"]


def hidden_of(lines: list[str]) -> int:
    for line in lines:
        found = re.fullmatch(r"\+(\d+) more busy", line.strip())
        if found:
            return int(found.group(1))
    return 0


def drawn_of(lines: list[str], names: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        hit = [name for name in names if re.search(rf"(^|\s){re.escape(name)}(\s|$)", line)]
        assert len(hit) <= 1, f"one line names two agents: {line!r}"
        out.extend(hit)
    return out


def test_every_line_fits_the_column_it_was_given() -> None:
    payload = fixture()
    names = drawable(payload)
    for width in WIDTHS:
        lines = draw(payload, width)
        drawn = drawn_of(lines, names)
        assert len(drawn) == len(names), (
            f"{width} columns drew {len(drawn)} of {len(names)} rows: {lines}"
        )
        over = [line for line in lines if len(line) > width]
        assert not over, f"{width} columns: {len(over)} line(s) wider than the bound: {over[:2]}"


def test_the_overflow_count_is_exact_at_every_width() -> None:
    payload = fixture()
    names = drawable(payload)
    for width in WIDTHS:
        lines = draw(payload, width)
        drawn = drawn_of(lines, names)
        hidden = hidden_of(lines)
        assert len(drawn) == len(set(drawn)), f"{width}: an agent is drawn twice: {drawn}"
        assert set(drawn) <= set(names), f"{width}: a line names an agent not in the payload"
        assert len(drawn) + hidden == len(names), (
            f"{width} columns: {len(drawn)} drawn + {hidden} hidden != {len(names)} drawable"
        )
        assert len(lines) <= 12, f"{width} columns: {len(lines)} lines breaks the 12-line budget"


def test_the_line_budget_overflow_is_counted_not_dropped() -> None:
    payload = fixture()
    payload["instances"] = [
        {
            "instance": f"Developer-{n}",
            "role": "Developer",
            "state": "busy",
            "task": f"T-{n:04d}",
            "elapsed_seconds": 60 * n,
            "progress_pct": n,
            "activity": f"work item {n}",
        }
        for n in range(1, 15)
    ]
    payload["counts"] = {"busy": 14, "stalled": 0, "lanes_live": 0}
    names = drawable(payload)
    for width in WIDTHS:
        lines = draw(payload, width)
        drawn = drawn_of(lines, names)
        hidden = hidden_of(lines)
        assert len(lines) <= 12, f"{width}: {len(lines)} lines"
        assert len(drawn) + hidden == len(names), (
            f"{width}: {len(drawn)} drawn + {hidden} hidden != {len(names)} drawable"
        )
        assert hidden > 0, f"{width}: 14 busy rows must overflow the 12-line budget"
        assert lines[0].startswith("teamwork"), "the header is the first line"


def test_the_clocks_are_derived_and_not_invented() -> None:
    payload = fixture()
    lines = "\n".join(draw(payload, 120))
    assert clock(754) in lines, f"used clock for 754s is not {clock(754)}"
    assert clock(2846) in lines, f"left clock for 2846s remaining is not {clock(2846)}"

    derived = fixture()
    for row in derived["instances"]:
        row.pop("remaining_seconds", None)
        row.pop("progress_pct", None)
    derived["instances"][0]["budget_seconds"] = 3600
    derived["instances"][0]["elapsed_seconds"] = 3300
    line = next(row for row in draw(derived, 120) if "Developer " in row)
    assert clock(300) in line, (
        f"left must be re-derived as {clock(300)} from budget - elapsed: {line!r}"
    )


def test_a_payload_without_numbers_renders_no_metric() -> None:
    payload = {
        "schema": 5,
        "count": 2,
        "counts": {"busy": 2, "stalled": 0, "lanes_live": 0},
        "instances": [
            {"instance": "Developer", "role": "Developer", "state": "busy", "task": "T-0070"},
            {"instance": "Tester", "role": "Tester", "state": "busy", "task": "T-0006"},
        ],
        "lanes": [],
    }
    lines = draw(payload, 120)
    rows = [line for line in lines if line.startswith(("●", "◐", "▲"))]
    assert len(rows) == 2, f"expected one line per busy agent, got {lines}"
    for line in rows:
        assert not re.search(r"\d+[smh]\b", line), f"a clock was invented: {line!r}"
        assert "█" not in line, f"a progress bar was invented: {line!r}"
        assert "%" not in line, f"a percent was invented: {line!r}"
