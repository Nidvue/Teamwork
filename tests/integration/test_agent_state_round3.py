"""Design.md 10.9 executed: less ink, and the roster counts live seats (ui layer, T-0074).

The spec is prose until something runs it. Four checks execute the extension
through node type stripping, one drives the CLI on a temp team tree:

1. NO-BAR - no line carries a bar glyph, a filled/empty cell run or a `%`, even
   when the payload still sends `progress_pct: 42` (D-16, D-17);
2. ACTIVITY-CAP - the activity cell is at most 28 columns at width 100 and a
   long state string is clipped at a word boundary with `…`, never mid-word;
3. NO-FILL - no emitted line keeps trailing whitespace and a short fixture does
   not reach the right edge (D-18);
4. LEFT-IS-REAL - the two clocks are re-derived from elapsed/budget/remaining,
   `-` when absent and clamped at 0;
5. ROSTER-TRACKS - a finished, workless seat is folded once at reconcile into
   Runtime/Retired/, the role memory and queue survive, a seat with ready work
   is kept, the printed staffed count is the current roster while
   counts.activated stays historical and is never printed as a roster count,
   and two reconciles fold once and ledger once (D-19, D-20).

The renderer helpers live in test_agent_state_width_matrix.py; this file loads
them rather than restating a second harness. Node is a host tool: without it the
renderer checks skip with the reason, exactly as the width matrix does.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "scripts" / "teamwork.py"
BARS = "█░▁▂▃▄▅▆▇▮▯▓▒"


def _matrix():
    path = Path(__file__).with_name("test_agent_state_width_matrix.py")
    spec = importlib.util.spec_from_file_location("tw_agent_state_width_matrix", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MATRIX = _matrix()
clock = MATRIX.clock
draw = MATRIX.draw

LONG_ACTIVITY = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"


def payload(activity: str = LONG_ACTIVITY) -> dict:
    return {
        "schema": 5,
        "count": 4,
        "counts": {"busy": 2, "stalled": 1, "lanes_live": 1},
        "instances": [
            {
                "instance": "Developer",
                "role": "Developer",
                "state": "busy",
                "task": "T-0074",
                "elapsed_seconds": 754,
                "budget_seconds": 3600,
                "remaining_seconds": 2846,
                "progress_pct": 42,
                "model": "qwen3-coder-480b",
                "activity": activity,
            },
            {
                "instance": "ReleaseEngineer",
                "role": "Release Engineer",
                "state": "busy",
                "task": "T-0091",
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
                "task": "T-0074",
                "elapsed_seconds": 4000,
                "activity": "lane.finish L-0123 - lost",
            },
            {"instance": "Architect", "role": "Architect", "state": "idle"},
        ],
        "lanes": [],
    }


def line_of(lines: list[str], name: str) -> str:
    hit = [line for line in lines if re.search(rf"(^|\s){re.escape(name)}(\s|$)", line)]
    assert len(hit) == 1, f"{name} is not drawn exactly once: {lines}"
    return hit[0]


def test_no_bar_and_no_percentage_are_emitted() -> None:
    for width in (40, 60, 80, 100):
        for line in draw(payload(), width):
            bad = [glyph for glyph in BARS if glyph in line]
            assert not bad, f"width {width}: bar glyph {bad} in {line!r}"
            assert "%" not in line, f"width {width}: a percentage survived in {line!r}"
    lines = draw(payload(), 100)
    assert not any("42" in line and "%" in line for line in lines)
    assert any("Developer" in line for line in lines)


def test_the_activity_cell_is_capped_and_clipped_at_a_word_boundary() -> None:
    def prefix_of(activity: str) -> str:
        line = line_of(draw(payload(activity), 79), "Developer")
        assert line.endswith(activity), line
        return line[: -len(activity)]

    prefix = prefix_of("alpha")
    cell = line_of(draw(payload(LONG_ACTIVITY), 79), "Developer")[len(prefix) :]
    assert len(cell) <= 28, f"activity cell is {len(cell)} columns: {cell!r}"
    assert cell.endswith("…"), f"a clipped activity must end with the ellipsis: {cell!r}"
    kept = cell[:-1].rstrip()
    assert LONG_ACTIVITY.startswith(kept), f"the clip invented text: {cell!r}"
    assert LONG_ACTIVITY[len(kept)] == " ", f"the clip cut mid-word: {cell!r}"
    wide = line_of(draw(payload(), 100), "Developer")
    assert len(wide) <= 100, f"width 100 overflowed: {len(wide)}"
    assert "…" in wide, f"the wide row does not clip the long activity: {wide!r}"


def test_no_line_is_filled_to_the_edge() -> None:
    for width in (40, 60, 80, 100):
        for line in draw(payload(), width):
            assert line == line.rstrip(), f"width {width}: trailing whitespace in {line!r}"
    short = {
        "schema": 5,
        "count": 2,
        "counts": {"busy": 1, "stalled": 0, "lanes_live": 1},
        "instances": [
            {
                "instance": "Tester",
                "role": "Tester",
                "state": "busy",
                "task": "T-0007",
                "elapsed_seconds": 12,
                "activity": "tests.run",
            },
            {"instance": "Architect", "role": "Architect", "state": "idle"},
        ],
        "lanes": [],
    }
    widest = max(len(line) for line in draw(short, 100))
    assert widest < 100, f"short content is padded to the edge: {widest} columns"


def test_the_clocks_are_derived_not_invented() -> None:
    lines = draw(payload(), 100)
    for name, elapsed, left in (
        ("Developer", 754, 3600 - 754),
        ("ReleaseEngineer", 120, 600 - 120),
    ):
        line = line_of(lines, name)
        assert clock(elapsed) in line, f"{name} used clock {clock(elapsed)} missing: {line!r}"
        assert clock(left) in line, f"{name} left clock {clock(left)} missing: {line!r}"
    stalled = line_of(lines, "Reviewer-1")
    assert clock(4000) in stalled
    assert "-" in stalled, f"no budget must render '-', not a number: {stalled!r}"
    over = payload("npm publish")
    over["instances"][1]["elapsed_seconds"] = 900
    over["instances"][1]["remaining_seconds"] = 0
    assert "0s" in line_of(draw(over, 100), "ReleaseEngineer"), "left clock is not clamped at 0"


def cli(project: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "TEAMWORK_ROOT"}
    return subprocess.run(
        [sys.executable, str(ENGINE), "--project", str(project), *argv],
        cwd=project,
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
    )


def ok(project: Path, *argv: str) -> str:
    run = cli(project, *argv)
    assert run.returncode == 0, (
        f"{argv} -> {run.returncode}: {run.stdout[-400:]} {run.stderr[-400:]}"
    )
    return run.stdout


def counts(project: Path) -> dict:
    return json.loads(ok(project, "status", "--json"))["counts"]


def staffed_of(panel: str) -> int:
    match = re.search(r"(\d+) staffed", panel)
    assert match, f"the panel prints no staffed count: {panel}"
    return int(match.group(1))


def test_a_finished_seat_is_folded_once_and_the_roster_counts_current_seats(tmp_path: Path) -> None:
    project = tmp_path / "team"
    project.mkdir()
    ok(project, "init", "--agents", "ceo,developer,architect,reviewer-1", "--no-git")
    ok(project, "task", "add", "developer", "ship the deliverable", "--priority", "P0")
    before = counts(project)
    assert staffed_of(ok(project, "status")) == 4, "the printed roster is not the 4 seats"
    assert before["activated"] == 4, before

    dry = ok(project, "instance", "prune", "--keep-required", "--dry-run", "--by", "Tester")
    assert "fold architect" in dry.lower(), dry
    assert "ready task(s) for developer" in dry, dry
    assert "one reviewer stays for the gate" in dry, dry

    ok(project, "instance", "prune", "--keep-required", "--by", "Tester")
    retired = [path for path in project.rglob("Runtime/Retired/*") if path.is_dir()]
    assert any("Architect" in path.name for path in retired), retired
    assert not any(
        path.name == "Architect" and "Agents" in path.parts for path in project.rglob("Architect")
    )

    roles = [path for path in project.rglob("Roles/Architect") if path.is_dir()]
    assert roles, "the role directory was deleted by the fold"
    assert (roles[0] / "TaskQueue.md").is_file(), "the role queue did not survive the fold"
    assert (roles[0] / "Role.md").is_file(), "the role charter did not survive the fold"

    after = counts(project)
    panel = ok(project, "status")
    assert staffed_of(panel) == 3, f"the printed staffed count is not the current roster: {panel}"
    assert after["activated"] >= 3, after
    assert "activated" not in panel, f"a surface still prints the activated total: {panel}"
    assert "staffed" not in after, (
        f"the frozen schema-5 envelope grew a staffed key: {sorted(after)}"
    )

    again = ok(project, "instance", "prune", "--keep-required", "--by", "Tester")
    assert "nothing to fold" in again, again
    ledger = [path for path in project.rglob("Ledger.jsonl") if path.is_file()]
    assert ledger, "no ledger to read"
    events = [line for line in ledger[0].read_text().splitlines() if '"instance.retire"' in line]
    assert len(events) == 1, f"two reconciles recorded {len(events)} fold event(s)"
