"""Why this file exists: ``status --json`` is a machine contract, not a panel.

The pi status widget (`extensions/teamwork-status.ts`) shells out to
``teamwork.py status --json`` and renders the fields by name, so a renamed key or a
non-zero exit on an empty team silently blanks the operator's only live view - the
widget swallows any failure into "no data". Nothing else in the suite executes the
command against a real tree: the unit render tests feed it dicts.

Pinned here, end to end: the JSON envelope and row keys on this team's own tree,
exit 0 with an empty instance list on a tree that has no team yet, the deliberate
difference between the panel (3) and the feed (0), and the built tarball actually
shipping the extension its manifest declares.

A lane carries ``TEAMWORK_ROOT``, which makes the CLI ignore ``--project`` and read
the live team (K-0011), so every run below strips it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "scripts" / "teamwork.py"
BUILD = ROOT / "scripts" / "build_pi_package.py"
EXTENSION = "teamwork-status.ts"

ENVELOPE = {"schema", "generated", "count", "counts", "instances", "lanes"}
ROW = {
    "instance",
    "role",
    "state",
    "task",
    "title",
    "elapsed",
    "elapsed_text",
    "progress",
    "progress_pct",
    "lane",
    "lane_state",
    "model",
    "provider",
}
LANE = {
    "id",
    "instance",
    "role",
    "task",
    "state",
    "elapsed_text",
    "model",
    "provider",
    "attempt",
}
COUNTS = {"busy", "idle", "ready", "review", "lanes"}


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "TEAMWORK_ROOT"}
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env, timeout=180)


def populated(tmp_path: Path) -> tuple[Path, str]:
    """A synthetic tree that has a team: `init` writes the workspace, `instance add`
    staffs it, so the row contract is measured even where no live team exists (CI)."""
    project = tmp_path / "synthetic"
    project.mkdir()
    team = "Synthetic"
    argv = ["--project", str(project), "--team", team]
    for command in (["init", *argv], ["instance", "add", "ceo", *argv]):
        done = run([sys.executable, str(ENGINE), *command], project)
        assert done.returncode == 0, (command, done.stderr or done.stdout)
    return project, team


def live_team() -> tuple[Path, str]:
    """The project root that holds the team tree, and the team directory name."""
    candidates = [ROOT, *ROOT.parents[:8]]
    env_root = os.environ.get("TEAMWORK_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    for candidate in candidates:
        teams = candidate / ".pi" / "Teamwork" / "Teams"
        if teams.is_dir() and any(teams.iterdir()):
            names = sorted(p.name for p in teams.iterdir() if p.is_dir())
            return candidate, ("Teamwork" if "Teamwork" in names else names[0])
    raise AssertionError(
        "no team tree found: neither the checkout nor TEAMWORK_ROOT holds .pi/Teamwork/Teams"
    )


def status_json(project: Path, team: str) -> tuple[int, dict]:
    done = run(
        [
            sys.executable,
            str(ENGINE),
            "status",
            "--json",
            "--project",
            str(project),
            "--team",
            team,
        ],
        project,
    )
    assert done.returncode == 0, done.stderr or done.stdout
    return done.returncode, json.loads(done.stdout)


def test_status_json_envelope_and_rows(tmp_path: Path) -> None:
    project, team = populated(tmp_path)
    _code, payload = status_json(project, team)

    assert set(payload) == ENVELOPE, sorted(payload)
    assert payload["schema"] == 2, "the widget reads schema 2: lanes and models are additive"
    assert isinstance(payload["generated"], str) and payload["generated"][:4].isdigit()
    assert set(payload["counts"]) == COUNTS, sorted(payload["counts"])
    assert isinstance(payload["instances"], list)
    assert payload["count"] == len(payload["instances"]), "count must describe instances"
    assert payload["instances"], "a staffed team must produce rows"
    assert payload["counts"]["busy"] + payload["counts"]["idle"] == payload["count"], (
        "every instance is busy or idle; the panel header sums the two"
    )

    for row in payload["instances"]:
        assert set(row) == ROW, (row.get("instance"), sorted(row))
        assert row["state"] in {"busy", "idle"}, row
        assert row["instance"], row
        assert row["role"], row
        assert isinstance(row["progress"], str), "the widget prints progress as text"
        assert isinstance(row["elapsed_text"], str)
        if row["state"] == "idle":
            assert row["progress_pct"] is None and row["task"] == "", row


def test_status_json_exits_zero_with_no_instances(tmp_path: Path) -> None:
    project = tmp_path / "synthetic"
    project.mkdir()
    assert run(["git", "init", "-q", str(project)], project).returncode == 0

    done = run(
        [
            sys.executable,
            str(ENGINE),
            "status",
            "--json",
            "--project",
            str(project),
            "--team",
            "Synthetic",
        ],
        project,
    )
    assert done.returncode == 0, f"the feed must not fail on a fresh tree: {done.stderr}"
    payload = json.loads(done.stdout)
    assert set(payload) == ENVELOPE, sorted(payload)
    assert payload["count"] == 0
    assert payload["instances"] == []
    assert payload["counts"] == {"busy": 0, "idle": 0, "ready": 0, "review": 0, "lanes": 0}
    assert payload["lanes"] == [], "an empty tree has no lane rows"

    panel = run(
        [sys.executable, str(ENGINE), "status", "--project", str(project), "--team", "Synthetic"],
        project,
    )
    assert panel.returncode == 3, "the human panel reports 'nothing staffed' as 3, the feed as 0"
    assert "no instance" in panel.stdout


def test_this_teams_feed_matches_the_same_contract() -> None:
    """The live tree, when the run has one: `.pi` is local state, so a CI checkout
    has no team at all - a skip that names that, never a silent pass."""
    try:
        project, team = live_team()
    except AssertionError as reason:
        import pytest

        pytest.skip(str(reason))
    _code, payload = status_json(project, team)
    assert set(payload) == ENVELOPE, sorted(payload)
    assert payload["count"] == len(payload["instances"])
    for row in payload["instances"]:
        assert set(row) == ROW, (row.get("instance"), sorted(row))
        assert isinstance(row["model"], str) and isinstance(row["provider"], str)
    for lane in payload["lanes"]:
        assert set(lane) == LANE, (lane.get("id"), sorted(lane))
        assert lane["id"].startswith("L-"), lane
        assert lane["state"], lane
        assert "/" in lane["attempt"], lane
    assert payload["counts"]["lanes"] == len(payload["lanes"]), "the count describes the rows"


def test_second_call_is_stable(tmp_path: Path) -> None:
    project, team = populated(tmp_path)
    _code, first = status_json(project, team)
    _code, second = status_json(project, team)

    assert set(first) == set(second)
    assert [row["instance"] for row in first["instances"]] == [
        row["instance"] for row in second["instances"]
    ], "the feed must not reorder rows between calls"
    assert first["counts"]["review"] == second["counts"]["review"]
    assert [lane["id"] for lane in first["lanes"]] == [lane["id"] for lane in second["lanes"]], (
        "the lane order must not change between two calls with no state change"
    )


def test_agent_filter_keeps_the_lane_count_equal_to_the_rows() -> None:
    """`--agent` narrows the rows; `counts.lanes` must describe what it narrowed to,
    or the widget header prints six lanes over two lines (review finding F3)."""
    try:
        project, team = live_team()
    except AssertionError as reason:
        import pytest

        pytest.skip(str(reason))
    _code, payload = status_json(project, team)
    if not payload["lanes"]:
        import pytest

        pytest.skip("no live lane row in this tree, so no filter to measure")
    wanted = payload["lanes"][0]["instance"]
    done = run(
        [
            sys.executable,
            str(ENGINE),
            "status",
            "--json",
            "--agent",
            wanted,
            "--project",
            str(project),
            "--team",
            team,
        ],
        project,
    )
    assert done.returncode == 0, done.stderr or done.stdout
    narrowed = json.loads(done.stdout)
    assert narrowed["counts"]["lanes"] == len(narrowed["lanes"]), (
        "the count must describe the narrowed rows"
    )
    assert {lane["instance"] for lane in narrowed["lanes"]} <= {wanted}


def test_built_package_ships_the_status_extension(tmp_path: Path) -> None:
    out = tmp_path / "dist"
    done = run([sys.executable, str(BUILD), "--out", str(out)], ROOT)
    assert done.returncode == 0, done.stderr
    pkg = out / "@nidvue" / "teamwork"
    manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))

    assert "./extensions" in manifest["pi"]["extensions"], manifest["pi"]["extensions"]
    assert "extensions" in manifest["files"], "npm ships only what `files` names"
    shipped = pkg / "extensions" / EXTENSION
    assert shipped.is_file(), f"the manifest declares extensions/, {EXTENSION} is not in it"
    assert shipped.read_bytes() == (ROOT / "extensions" / EXTENSION).read_bytes(), (
        "the tarball must ship the repository's extension, not a stale copy"
    )
    text = shipped.read_text(encoding="utf-8")
    assert '"status"' in text and '"--json"' in text, "the widget drives the status feed"
    assert "scripts" in text and "teamwork.py" in text
