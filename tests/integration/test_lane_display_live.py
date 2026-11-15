"""Live proof that the lane display shows running lanes: two real lanes, one poll.

The pi extension (templates/pi-package/extensions/teamwork-lanes.ts) renders only
`lane list --all --json` rows whose `live` is true. This probe starts two real
lane processes with a stub host command, then asserts the exact command the
extension runs reports both of them live, with the fields the footer draws.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from teamwork import engine

WORKTREE = Path(__file__).resolve().parents[2]
CLI = [sys.executable, str(WORKTREE / "scripts" / "teamwork.py")]
REPO = Path(
    subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=WORKTREE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
).parent
STUB = "sh -c 'sleep 30'"
AGENTS = ("Developer", "Developer-2")


def cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*CLI, "--project", str(REPO), *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )


def live_rows() -> list[dict]:
    proc = cli("lane", "list", "--all", "--json")
    assert proc.returncode == 0, proc.stderr
    rows = json.loads(proc.stdout)
    assert isinstance(rows, list)
    return [row for row in rows if row.get("live")]


def test_two_real_lanes_render_live() -> None:
    root = REPO / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(REPO)
    if not root.is_dir() or not all(engine.agent_dir(root, agent).is_dir() for agent in AGENTS):
        pytest.skip(
            "this checkout staffs no Developer/Developer-2 seat, so there is no workspace "
            "to start a real lane in (CI has no gitignored .pi/ team tree)"
        )
    env = dict(os.environ, TEAMWORK_LANE_CMD=STUB)
    started: list[str] = []
    try:
        for agent in AGENTS:
            proc = cli(
                "lane",
                "start",
                "--agent",
                agent,
                "--prompt",
                "lane-display live proof",
                "--minutes",
                "1",
                env=env,
            )
            assert proc.returncode == 0, proc.stderr
            started.append(agent)

        deadline = time.time() + 30
        rows: list[dict] = []
        while time.time() < deadline:
            rows = live_rows()
            if all(any(row["agent"] == agent for row in rows) for agent in AGENTS):
                break
            time.sleep(0.5)

        shown = {row["agent"]: row for row in rows}
        for agent in AGENTS:
            assert agent in shown, f"{agent} not live in {rows}"
            row = shown[agent]
            assert row["state"] == "running"
            assert row["id"].startswith("L-")
            assert row["minutes"] == 1
            assert isinstance(row["elapsed_seconds"], float)
            assert row["seconds_left"] is None or row["seconds_left"] > 0
            assert row["log"]
        print("LIVE ROWS:", json.dumps([shown[a] for a in AGENTS], sort_keys=True))
    finally:
        for agent in started:
            cli("lane", "stop", agent)
