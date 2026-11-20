"""Acceptance: M10 - the operator-visible half of clean, dispatch and the widget.

Three scenarios, each driven the way an operator meets the feature: the shipped
CLI as a subprocess on a throwaway workspace, and the shipped pi extension run
through node for the widget (the same harness ``tests/unit/test_pi_status_render.py``
uses, so a payload the engine cannot emit fails here rather than in a grep).

* ``clean --team-wide`` prints its scope, removes stray temp files and keeps a
  file a team record cites (T-0140, criterion A-0002).
* a task whose review came back ``failed`` is re-dispatched by ``swarm run`` as
  adopted work instead of stranding in ``doing`` with an orphaned claim (T-0138).
* the status widget renders columns separated by a gap at widths 80/100/140/180,
  never a line wider than the terminal and never two columns touching (T-0137).

Owner: reviewer. Layer: acceptance. Area: clean, dispatch, status-widget. Task: T-0007.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from cli_harness import assert_ok, cli

ROSTER = "ceo,architect,developer-1,tester-1,reviewer-1"
EXTENSION = Path(__file__).resolve().parents[2] / "extensions" / "tw-status.ts"

NODE_SCRIPT = """
const { render } = await import(process.env.TW_EXTENSION);
const payload = JSON.parse(process.env.TW_PAYLOAD);
const width = Number(process.env.TW_WIDTH);
const lines = render(payload, width);
console.log(JSON.stringify({ lines }));
"""


def team_root(project: Path) -> Path:
    return project / ".pi" / "Teamwork" / "Teams" / "Acceptance"


def test_clean_team_wide_keeps_an_evidence_file_a_record_cites(project: Path) -> None:
    """The janitor prints its scope, removes scratch and spares cited evidence."""
    assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    root = team_root(project)
    scratch = root / "Agents" / "Developer-1" / "Scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    cited = scratch / "cited.tmp"
    stray = scratch / "stray.tmp"
    cited.write_text("evidence a record points at\n", encoding="utf-8")
    stray.write_text("nobody cites this\n", encoding="utf-8")
    record = root / "Agents" / "Developer-1" / "WorkLog.md"
    record.write_text(
        record.read_text(encoding="utf-8") + "\n- artifact: Agents/Developer-1/Scratch/cited.tmp\n",
        encoding="utf-8",
    )

    result = assert_ok(cli(project, ["clean", "--team-wide", "--no-worktrees"]))

    assert "team-wide clean" in result.stdout, result.output
    assert f"- {root.relative_to(project).as_posix()}/Agents/Developer-1" in result.stdout
    assert not stray.exists(), "an uncited scratch temp file must be removed"
    assert cited.exists(), "a cited evidence file must be spared"
    assert "kept 1 evidence file(s)" in result.stdout, result.output

    second = assert_ok(cli(project, ["clean", "--team-wide", "--no-worktrees"]))
    assert "removed 0 scratch/temp file(s)" in second.stdout, second.output
    assert "kept 1 evidence file(s)" in second.stdout, second.output


def test_a_review_failed_task_is_redispatched_instead_of_stranded(project: Path) -> None:
    """A fail round leaves new work; the swarm adopts it rather than reporting zero."""
    assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    assert_ok(
        cli(
            project,
            ["task", "add", "developer", "rework after a fail", "--claimed-by", "Developer-1"],
        )
    )
    assert_ok(
        cli(
            project,
            [
                "task",
                "set",
                "developer",
                "T-0001",
                "--status",
                "doing",
                "--claimed-by",
                "Developer-1",
                "--review-status",
                "failed",
                "--force",
                "acceptance fixture: a synthetic record in a throwaway workspace, "
                "no verdict was ever issued against it",
                "--by",
                "Reviewer-1",
            ],
        )
    )

    plan = assert_ok(cli(project, ["swarm", "run", "--dry-run"]))
    assert "- assigned: 1 unit(s) claimed with no live lane" in plan.stdout, plan.output
    assert "- assigned: 0 unit(s)" not in plan.stdout, plan.output

    second = assert_ok(cli(project, ["swarm", "run", "--dry-run"]))
    assert "- assigned: 1 unit(s) claimed with no live lane" in second.stdout, second.output


def node() -> str:
    binary = shutil.which("node")
    if not binary:
        pytest.skip("node is not installed, so the widget cannot be executed here")
    probe = subprocess.run(
        [binary, "--experimental-strip-types", "--no-warnings", "-e", "0"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        pytest.skip(f"node {binary} cannot strip TypeScript types: {probe.stderr.strip()[:120]}")
    return binary


def render(payload: dict, width: int) -> list[str]:
    env = os.environ.copy()
    env["TW_EXTENSION"] = EXTENSION.as_uri()
    env["TW_PAYLOAD"] = json.dumps(payload)
    env["TW_WIDTH"] = str(width)
    proc = subprocess.run(
        [node(), "--experimental-strip-types", "--no-warnings", "-e", NODE_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, f"widget render failed at width {width}:\n{proc.stderr}"
    return json.loads(proc.stdout)["lines"]


def payload(activity: str = "implementing the review gate") -> dict:
    return {
        "count": 3,
        "instances": [
            {
                "instance": "Developer-1",
                "role": "developer",
                "state": "busy",
                "lane": "L-0488",
                "lane_state": "running",
                "task": "T-0007",
                "last": activity,
                "last_seconds": 95,
                "elapsed_text": "12m",
                "progress_pct": 40,
                "model": "deepseek-v4",
                "provider": "deepinfra",
            },
            {
                "instance": "Reviewer",
                "role": "reviewer",
                "state": "busy",
                "lane": "L-0489",
                "lane_state": "running",
                "task": "T-0008",
                "last": "reading the diff",
                "last_seconds": 30,
                "elapsed_text": "3m",
                "progress_pct": 10,
                "model": "",
                "provider": "",
            },
            {"instance": "Tester-1", "role": "tester", "state": "idle", "task": "", "last": ""},
        ],
        "lanes": [
            {
                "id": "L-0488",
                "instance": "Developer-1",
                "task": "T-0007",
                "state": "running",
                "elapsed_text": "12m",
                "model": "",
                "provider": "",
            }
        ],
        "counts": {"activated": 3, "lanes_live": 2, "review": 1},
    }


WIDTHS = (80, 100, 140, 180)

BUSY_GLYPHS = {"●", "◐", "▲"}


@pytest.mark.parametrize("width", WIDTHS)
def test_the_widget_keeps_its_columns_apart_at_every_width(width: int) -> None:
    """No line wider than the terminal, and no two columns glued together."""
    lines = render(payload(), width)
    assert lines, "a populated payload must render something"
    assert lines[0].startswith("teamwork · "), lines[0]
    for line in lines:
        assert len(line) <= width, f"{width}: {len(line)} columns > bound: {line!r}"
        assert line == line.rstrip(), f"{width}: trailing whitespace: {line!r}"
        assert "\t" not in line, f"{width}: a tab is not a column gap: {line!r}"

    busy = [line for line in lines[1:] if line[:1] in BUSY_GLYPHS]
    assert len(busy) == 2, f"expected two busy rows at {width}: {lines!r}"
    for line in busy:
        cells = [cell for cell in re.split(r"\s{2,}", line.strip()) if cell]
        assert len(cells) >= 3, f"{width}: columns are touching: {line!r} -> {cells!r}"


def test_a_long_activity_is_clipped_instead_of_widening_the_line() -> None:
    """The bound wins: a 240-character activity still fits an 80-column terminal."""
    lines = render(payload("implementing the review gate " * 8), 80)
    for line in lines:
        assert len(line) <= 80, f"{len(line)} columns > 80: {line!r}"
