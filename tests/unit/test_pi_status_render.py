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
let lines;
try {
  lines = render(payload);
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


def render(payload: dict) -> list[str]:
    result = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", SCRIPT],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            **os.environ,
            "TW_EXTENSION": EXTENSION.as_uri(),
            "TW_PAYLOAD": json.dumps(payload),
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
    assert "+11" in lines[-1], "the collapsed idle line counts the names it hides"


def test_a_payload_without_title_or_progress_renders_instead_of_throwing() -> None:
    bare = {
        "count": 2,
        "instances": [
            {"instance": "Developer", "role": "developer", "state": "busy", "task": "T-0061"},
            {"instance": "Architect", "role": "architect", "state": "idle"},
        ],
    }
    lines = render(bare)
    assert lines[0].startswith("teamwork · 2 inst · 0 lanes · 1 busy · 0 review")
    assert "undefined" not in "\n".join(lines)
    assert lines[-1] == "○ idle: Architect"


def test_a_review_handle_names_the_task_not_the_role() -> None:
    lines = render(payload(4))
    assert "↳T-0071" in "\n".join(lines)
    assert "developer/" not in "\n".join(lines)


def with_lanes(count: int = 4) -> dict:
    data = payload(count)
    data["schema"] = 2
    data["counts"] = {"busy": 3, "review": 2, "lanes": 5}
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
            "model": "x",
            "provider": "",
            "attempt": "1/2",
        },
    ]
    return data


def test_the_header_counts_lanes_and_the_lane_lines_name_the_model() -> None:
    lines = render(with_lanes())
    assert lines[0] == "teamwork · 4 inst · 5 lanes · 3 busy · 2 review"
    lanes = [line for line in lines if line.startswith("⚙")]
    assert len(lanes) == 3, "at most three lanes, the rest is the instance rows' job"
    assert lanes[0].startswith("⚙ L-0412 Developer-1 T-0131 run")
    assert lanes[0].endswith("deepseek/deepseek-chat"), lanes[0]
    assert lanes[1].endswith("host"), "an empty model reads host, never blank"
    assert "done" in lanes[1], "a review lane shows its state and no task"
    clipped = lanes[2].split()[-1]
    assert len(clipped) == 22 and clipped.endswith("…"), clipped


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
