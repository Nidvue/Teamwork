"""Integration: two real team trees talking over one bus.

Layer ``integration``, area ``bus``, owner Tester (T-0016). The frozen interface
(D-20261117-CEO) puts the bus outside any one team tree: ``$TEAMWORK_BUS`` or
``<project>/.pi/Teamwork/Bus``, one file per ``<key>/M-nnnn.json`` under one
``.lock``, matched at read time by the keys a reader holds.

The unit layer proves the shapes in one interpreter. This layer proves the thing
the interface exists for: two *separate* project trees, each with its own team
tree, two real CLI processes, one bus. Every call is the shipped command run as a
subprocess with ``TEAMWORK_ROOT`` cleared, so a message that only travels because
both ends share a process or an ambient team fails here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ALPHA = "Alpha"
BETA = "Beta"


def _git(project: Path) -> None:
    run = ["git", "-C", str(project)]
    subprocess.run([*run, "init", "-q"], check=True)
    subprocess.run([*run, "config", "user.email", "team@example.invalid"], check=True)
    subprocess.run([*run, "config", "user.name", "Team"], check=True)
    (project / "README.md").write_text("# probe\n", encoding="utf-8")
    subprocess.run([*run, "add", "-A"], check=True)
    subprocess.run([*run, "commit", "-qm", "init"], check=True)


def _env(bus: Path | None, team: str) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("TEAMWORK_ROOT", None)
    env.pop("PI_SESSION_ID", None)
    env["TEAMWORK_TEAM"] = team
    if bus is None:
        env.pop("TEAMWORK_BUS", None)
    else:
        env["TEAMWORK_BUS"] = str(bus)
    return env


def tree(tmp_path: Path, name: str, bus: Path | None) -> Path:
    """A real project with a real team tree, initialised by the shipped CLI."""
    project = tmp_path / name
    project.mkdir()
    _git(project)
    run(project, name, bus, "init", "--agents", "tester,developer")
    assert (project / ".pi" / "Teamwork" / "Teams" / name).is_dir()
    return project


def run(project: Path, team: str, bus: Path | None, *args: str) -> subprocess.CompletedProcess:
    env = _env(bus, team)
    return subprocess.run(
        [sys.executable, "-m", "teamwork", *args, "--team", team],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def cli(project: Path, team: str, bus: Path | None, *args: str) -> str:
    done = run(project, team, bus, *args)
    assert done.returncode == 0, done.stderr or done.stdout
    return done.stdout


def rows(project: Path, team: str, bus: Path | None, *args: str) -> list:
    out = cli(project, team, bus, "message", "inbox", *args, "--json")
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def bus_file(bus: Path, key: str, message_id: str = "M-0001") -> Path:
    return bus / key / f"{message_id}.json"


@pytest.fixture()
def bus(tmp_path: Path) -> Path:
    return tmp_path / "shared-bus"


def test_a_team_addressed_message_reaches_the_other_tree(tmp_path: Path, bus: Path) -> None:
    alpha = tree(tmp_path, ALPHA, bus)
    beta = tree(tmp_path, BETA, bus)
    cli(
        alpha,
        ALPHA,
        bus,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        f"team:{BETA}",
        "--subject",
        "two trees, one bus",
        "--priority",
        "high",
    )
    assert bus_file(bus, f"team-{BETA}").is_file()
    seen = rows(beta, BETA, bus, "--for", "tester")
    assert [row["subject"] for row in seen] == ["two trees, one bus"]
    assert seen[0]["id"] == f"team-{BETA}:M-0001"
    assert rows(alpha, ALPHA, bus, "--for", "tester") == []


def test_an_empty_bus_leaves_the_inbox_empty_and_exits_zero(tmp_path: Path, bus: Path) -> None:
    beta = tree(tmp_path, BETA, bus)
    assert rows(beta, BETA, bus, "--for", "tester") == []
    assert rows(beta, BETA, bus, "--for", "tester", "--all") == []


def test_a_session_message_is_taken_once_and_a_second_taker_is_refused(
    tmp_path: Path, bus: Path
) -> None:
    alpha = tree(tmp_path, ALPHA, bus)
    beta = tree(tmp_path, BETA, bus)
    cli(
        alpha,
        ALPHA,
        bus,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        "session:s-beta",
        "--session",
        "s-alpha",
        "--subject",
        "point to point",
    )
    seen = rows(beta, BETA, bus, "--for", "tester", "--session", "s-beta")
    assert [row["id"] for row in seen] == ["session-s-beta:M-0001"]
    cli(
        beta,
        BETA,
        bus,
        "message",
        "take",
        "session-s-beta:M-0001",
        "--for",
        "tester",
        "--by",
        "tester",
        "--session",
        "s-beta",
    )
    again = run(
        beta,
        BETA,
        bus,
        "message",
        "take",
        "session-s-beta:M-0001",
        "--for",
        "tester",
        "--by",
        "developer",
        "--session",
        "s-beta",
    )
    assert again.returncode != 0
    assert "already taken" in (again.stderr + again.stdout)
    record = json.loads(bus_file(bus, "session-s-beta").read_text(encoding="utf-8"))
    assert record["state"] == "taken"
    assert record["taken_by"] == "Tester"
    assert record["scope"] == "session"
    assert record["sender_session"] == "s-alpha"


def test_team_and_bus_rows_share_one_priority_sort(tmp_path: Path, bus: Path) -> None:
    alpha = tree(tmp_path, ALPHA, bus)
    beta = tree(tmp_path, BETA, bus)
    cli(
        beta,
        BETA,
        bus,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        "tester",
        "--subject",
        "local",
    )
    cli(
        alpha,
        ALPHA,
        bus,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        f"team:{BETA}",
        "--subject",
        "cross tree urgent",
        "--priority",
        "urgent",
    )
    seen = rows(beta, BETA, bus, "--for", "tester", "--session", "s-beta")
    assert [row["subject"] for row in seen] == ["cross tree urgent", "local"]


def test_two_trees_writing_at_once_keep_every_record(tmp_path: Path, bus: Path) -> None:
    alpha = tree(tmp_path, ALPHA, bus)
    beta = tree(tmp_path, BETA, bus)
    procs = []
    for project, team in ((alpha, ALPHA), (beta, BETA)):
        for index in range(4):
            procs.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "teamwork",
                        "message",
                        "send",
                        "--from",
                        "tester",
                        "--to",
                        f"team:{BETA}",
                        "--subject",
                        f"{team} {index}",
                    ],
                    cwd=project,
                    env=_env(bus, team),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
    for proc in procs:
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err or out
    landed = sorted(path.name for path in (bus / "team-Beta").glob("M-*.json"))
    assert landed == [f"M-{index:04d}.json" for index in range(1, 9)]


def test_the_bus_override_moves_the_store_off_the_project(tmp_path: Path, bus: Path) -> None:
    plain = tree(tmp_path, BETA, None)
    cli(
        plain,
        BETA,
        bus,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        f"team:{BETA}",
        "--subject",
        "moved",
    )
    assert bus_file(bus, f"team-{BETA}").is_file()
    default = plain / ".pi" / "Teamwork" / "Bus"
    assert not default.is_dir() or not any(default.rglob("M-*.json"))


@pytest.mark.xfail(
    strict=True,
    reason="T-0133 defect: the CLI hands the team tree to bus_root, so the default bus is "
    "team-rooted (<team>/.pi/Teamwork/Bus); the frozen interface and "
    "test_the_default_bus_is_repo_rooted say project_of(root)/.pi/Teamwork/Bus",
)
def test_the_default_bus_is_repo_rooted(tmp_path: Path) -> None:
    plain = tree(tmp_path, BETA, None)
    cli(
        plain,
        BETA,
        None,
        "message",
        "send",
        "--from",
        "tester",
        "--to",
        f"team:{BETA}",
        "--subject",
        "rooted",
    )
    assert (plain / ".pi" / "Teamwork" / "Bus" / f"team-{BETA}" / "M-0001.json").is_file()
