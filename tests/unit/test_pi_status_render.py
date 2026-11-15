"""The status widget is a real renderer, not a string the test greps for.

Why this test exists: review round 1 found the first extension read `title` and
`progress_pct` off `status --json`, threw `TypeError` on its first refresh, and
passed its own test because that test searched the source text instead of running
the code. This one imports the extension through node's type stripping and calls
`render()` on a payload, so a missing field or a broken template fails here.

Node is a host tool, not a test dependency: without it the test skips with the
reason, exactly as the package's own smoke tests do.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTENSION = ROOT / "extensions" / "teamwork-status.ts"

SCRIPT = """
const { render } = await import(process.env.TW_EXTENSION);
const payload = JSON.parse(process.env.TW_PAYLOAD);
const width = Number(process.env.TW_WIDTH || 0);
let lines;
try {
  lines = width ? render(payload, width) : render(payload);
} catch (error) {
  console.log(JSON.stringify({ error: String(error && error.message) }));
  process.exit(0);
}
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


def render(payload: dict, width: int | None = None) -> list[str]:
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
        },
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "error" not in body, body["error"]
    return body["lines"]


def payload(count: int = 20) -> dict:
    rows = [
        {
            "instance": "Developer-2",
            "state": "busy",
            "task": "T-0070",
            "title": "pi extension teamwork-status",
            "elapsed_text": "12m",
            "progress_pct": 60,
        },
        {
            "instance": "Reviewer-2",
            "state": "busy",
            "task": "developer/T-0071",
            "title": "status: name the work",
            "elapsed_text": "8m",
            "progress_pct": 35,
        },
        {"instance": "Tester", "state": "busy", "task": "T-0010", "elapsed_text": "1m"},
    ]
    rows += [{"instance": f"Idle-{i}", "state": "idle"} for i in range(count - len(rows))]
    return {"schema": 1, "count": count, "counts": {"busy": 3, "review": 2}, "instances": rows}


def test_the_widget_stays_compact_and_puts_the_working_agents_first() -> None:
    lines = render(payload())
    assert len(lines) <= 12
    assert max(len(line) for line in lines) <= 100
    busy = [line for line in lines if line.startswith("●")]
    assert busy, lines
    assert busy[0].startswith("● Developer-2"), "the most advanced lane leads"
    assert lines.index(busy[-1]) < next(
        index for index, line in enumerate(lines) if line.startswith("○ idle:")
    ), "busy rows precede the idle line"
    assert sum(1 for line in lines if line.startswith("○ idle:")) == 1
    assert lines[-1] == "○ idle: 17 (activated 20)", "idle is a count, never a name list"


def test_a_payload_without_title_or_progress_renders_instead_of_throwing() -> None:
    bare = {
        "count": 2,
        "instances": [
            {"instance": "Developer", "role": "developer", "state": "busy", "task": "T-0061"},
            {"instance": "Architect", "role": "architect", "state": "idle"},
        ],
    }
    lines = render(bare)
    assert lines[0].startswith("teamwork · 2 act · 0 live · 1 busy · 0 review")
    assert "undefined" not in "\n".join(lines)
    assert lines[-1] == "○ idle: 1 (activated 2)"


def test_a_review_handle_names_the_task_not_the_role() -> None:
    lines = render(payload(4))
    assert "↳T-0071" in "\n".join(lines)
    assert "developer/" not in "\n".join(lines)


def with_lanes(count: int = 4) -> dict:
    data = payload(count)
    data["schema"] = 2
    data["counts"] = {"busy": 3, "review": 2, "lanes": 4, "activated": 4, "lanes_live": 2}
    data["instances"][0]["model"] = "deepseek-chat"
    data["instances"][0]["provider"] = "deepseek"
    data["lanes"] = [
        {
            "id": "L-0412",
            "instance": "Developer-1",
            "role": "developer",
            "task": "T-0131",
            "state": "running",
            "elapsed_text": "12m",
            "model": "deepseek-chat",
            "provider": "deepseek",
            "attempt": "1/2",
        },
        {
            "id": "L-0413",
            "instance": "Reviewer-1",
            "role": "reviewer",
            "task": "",
            "state": "exited",
            "elapsed_text": "3m",
            "model": "",
            "provider": "",
            "attempt": "1/2",
        },
        {
            "id": "L-0414",
            "instance": "Tester-1",
            "role": "tester",
            "task": "T-0140",
            "state": "timeout",
            "elapsed_text": "45m",
            "model": "m" * 40,
            "provider": "p",
            "attempt": "2/2",
        },
        {
            "id": "L-0415",
            "instance": "Architect",
            "role": "architect",
            "task": "T-0141",
            "state": "running",
            "elapsed_text": "1m",
            "model": "m" * 40,
            "provider": "p",
            "attempt": "1/2",
        },
    ]
    return data


def test_the_header_counts_lanes_and_the_lane_lines_name_the_model() -> None:
    lines = render(with_lanes())
    assert lines[0] == "teamwork · 4 act · 2 live · 3 busy · 2 review"
    lanes = [line for line in lines if line.startswith("⚙")]
    assert len(lanes) == 2, "only live lanes: an ended record is history, not a row"
    assert lanes[0].startswith("⚙ L-0412 Developer-1 T-0131 run")
    assert lanes[0].endswith("deepseek/deepseek-chat"), lanes[0]
    assert lanes[1].startswith("⚙ L-0415 Architect T-0141 run")
    clipped = lanes[1].split()[-1]
    assert len(clipped) == 22 and clipped.endswith("…"), clipped
    body = "\n".join(lines)
    assert "exited" not in body and "timeout" not in body, "an ended lane is not displayed"


def test_the_busy_rows_carry_the_model_and_stay_inside_the_bound() -> None:
    lines = render(with_lanes())
    assert len(lines) <= 12
    assert max(len(line) for line in lines) <= 100
    busy = [line for line in lines if line.startswith("●")]
    assert busy, lines
    assert "deepseek/deepseek-chat" in busy[0], busy[0]
    assert "host" in busy[1], "a row without a model still names the host"
    assert any(line.startswith("○ idle:") for line in lines), "the idle collapse survives"


def test_an_empty_payload_stays_silent() -> None:
    assert render({}) == []
    assert (
        render({"schema": 2, "count": 0, "counts": {"lanes": 0}, "instances": [], "lanes": []})
        == []
    )


def with_activity(width_payload: dict | None = None) -> dict:
    data = width_payload or payload(6)
    data["schema"] = 4
    data["instances"][0]["last"] = "tests.run TS-0001 - 76 passed in 35s"
    data["instances"][0]["last_seconds"] = 12
    data["instances"][1]["last"] = (
        "review.pass T-0062 - Re-derived the mechanism, then mutated it. "
        "CHANGE-SET: git diff --stat main...7c2ab2b -> two files, +110/-13"
    )
    data["instances"][1]["last_seconds"] = 240
    return data


def test_one_line_per_active_agent_carries_its_latest_command() -> None:
    lines = render(with_activity())
    busy = [line for line in lines if line.startswith("●")]
    assert len(busy) == 3, f"three busy agents, one line each: {lines}"
    assert "tests.run TS-0001" in busy[0]
    assert "12s · tests.run" in busy[0], "the age says how live the line is"
    assert "review.pass T-0062" in busy[1]
    assert "4m · review.pass" in busy[1]


def test_a_wide_terminal_shows_more_of_the_command_without_wrapping() -> None:
    data = with_activity()
    data["counts"] = {"busy": 3, "review": 2, "lanes_live": 1, "activated": 6}
    data["lanes"] = [
        {
            "id": "L-0433",
            "instance": "Developer-2",
            "task": "T-0070",
            "state": "running",
            "elapsed_text": "12m",
            "model": "deepseek-chat",
            "provider": "deepseek",
        }
    ]
    narrow = render(data, 60)
    wide = render(data, 160)
    assert max(len(line) for line in narrow) <= 60, narrow
    assert max(len(line) for line in wide) <= 160, wide
    narrow_row = next(line for line in narrow if "Reviewer-2" in line)
    wide_row = next(line for line in wide if "Reviewer-2" in line)
    assert len(wide_row) > len(narrow_row), "the wider bound is used, not a fixed cap"
    assert "CHANGE-SET" in wide_row, "the long command survives at the wider bound"
    assert "CHANGE-SET" not in narrow_row
    assert "\n" not in wide_row


def test_a_row_with_no_activity_falls_back_to_the_task_title() -> None:
    data = payload(4)
    data["instances"][0]["title"] = "pi extension teamwork-status"
    lines = render(data)
    row = next(line for line in lines if line.startswith("● Developer-2"))
    assert "pi extension teamwork-status" in row
