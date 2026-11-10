"""Integration: the task lifecycle, the clean scope and preflight, through the CLI.

The unit layers next to this one call the engine in-process against fakes. These
tests do the opposite: every assertion below goes through a real ``python
scripts/teamwork.py`` subprocess against a real throwaway git repository whose
project path contains a space, because that is the shape a lane actually has on a
host like this one. The three surfaces were chosen where the fakes and reality had
already diverged:

* the lifecycle a lane runs (``init`` -> ``task add``/``next`` -> ``branch start``
  -> ``commit`` -> ``identity --audit`` -> ``ledger verify`` -> ``loop``);
* ``clean``, whose whole contract is *scope* - what it refuses to touch - so a
  test that only counts removed files cannot certify it (developer T-0005: a
  team-wide ``--all`` wiped every lane's Scratch from the base checkout);
* ``preflight``, which is fail-closed by design: an unreachable ``@<sha>`` or a
  gate this host cannot start must be a red check with a fix, never a pass and
  never a traceback.

Owner: tester. Task: T-0001.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE = REPO_ROOT / "scripts" / "teamwork.py"
ROSTER = "ceo,architect,developer,tester,reviewer-1"
TEAM = "Fixture"
GIT_IDENTITY = ("Fixture", "fixture@example.invalid")


def _env() -> dict:
    """A child environment that cannot inherit the caller's team tree."""
    env = dict(os.environ)
    for name in ("TEAMWORK_ROOT", "TEAMWORK_TEAM"):
        env.pop(name, None)
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def git(project: Path, *args: str, identity: tuple[str, str] = GIT_IDENTITY) -> str:
    name, email = identity
    proc = subprocess.run(
        ["git", "-c", f"user.name={name}", "-c", f"user.email={email}", *args],
        cwd=str(project),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"git {' '.join(args)} -> {proc.returncode}: {proc.stderr}"
    return proc.stdout


def engine_cli(project: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """The real CLI as a subprocess, addressing ``project`` by absolute path."""
    return subprocess.run(
        [sys.executable, str(ENGINE), "--project", str(project), "--team", TEAM, *args],
        cwd=str(cwd or project),
        env=_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def output(proc: subprocess.CompletedProcess) -> str:
    return proc.stdout + proc.stderr


@pytest.fixture
def fixture_project(tmp_path: Path) -> Path:
    """A git repository with one commit, in a directory whose name has a space."""
    project = tmp_path / "Portable Space" / "Project"
    project.mkdir(parents=True)
    git(project, "init", "-b", "main", "--quiet")
    (project / "app.txt").write_text("hello\n", encoding="utf-8")
    git(project, "add", "app.txt")
    git(project, "commit", "-qm", "init")
    return project


def init_workspace(project: Path) -> Path:
    proc = engine_cli(project, "init", "--agents", ROSTER)
    assert proc.returncode == 0, output(proc)
    return project / ".pi" / "Teamwork" / "Teams" / TEAM


def start_task(project: Path) -> subprocess.CompletedProcess:
    added = engine_cli(project, "task", "add", "developer", "Build the widget", "--priority", "P0")
    assert added.returncode == 0, output(added)
    claimed = engine_cli(project, "task", "next", "Developer")
    assert claimed.returncode == 0, output(claimed)
    started = engine_cli(project, "branch", "start", "--agent", "developer", "--task", "T-0001")
    assert started.returncode == 0, output(started)
    return started


def commit_widget(project: Path, *paths: str) -> subprocess.CompletedProcess:
    (project / "widget.py").write_text("WIDGET = 1\n", encoding="utf-8")
    staging = ("--paths", ",".join(paths)) if paths else ("--all",)
    return engine_cli(
        project,
        "commit",
        "--role",
        "developer",
        "--type",
        "feat",
        "--area",
        "widget",
        "--task",
        "T-0001",
        "--goal",
        "build the widget",
        "--deliverable",
        "widget.py",
        "--why",
        "the task asks for it",
        "--status",
        "done",
        "--result",
        "unit @HEAD -> ok",
        *staging,
    )


def test_the_lifecycle_runs_end_to_end_on_a_real_repository(fixture_project: Path) -> None:
    """Every step a lane takes, as the lane takes it: separate processes, real git."""
    team = init_workspace(fixture_project)
    for role in ("CEO", "Architect", "Developer", "Tester", "Reviewer"):
        assert (team / "Roles" / role / "TaskQueue.md").is_file(), role
    assert (team / "Global" / "GlobalMemory.md").is_file()
    assert (fixture_project / "AGENTS.md").is_file()

    # The board contract T-0007 landed: the board `init` writes renders and checks
    # clean in a fresh project, before its first task and after it.
    empty_write = engine_cli(fixture_project, "board", "--write")
    assert empty_write.returncode == 0, output(empty_write)
    empty_check = engine_cli(fixture_project, "board", "--check")
    assert empty_check.returncode == 0, output(empty_check)

    start_task(fixture_project)

    open_write = engine_cli(fixture_project, "board", "--write")
    assert open_write.returncode == 0, output(open_write)
    open_check = engine_cli(fixture_project, "board", "--check")
    assert open_check.returncode == 0, output(open_check)

    queue = (team / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert "T-0001" in queue and "P0" in queue
    assert "claimed_by: Developer" in queue and "status: doing" in queue

    board = engine_cli(fixture_project, "board")
    assert board.returncode == 0, output(board)
    assert "developer" in board.stdout and "doing=1" in board.stdout

    committed = commit_widget(fixture_project)
    assert committed.returncode == 0, output(committed)
    assert "Developer <developer@agents.nidvue.com>" in committed.stdout
    log = git(fixture_project, "log", "-1", "--format=%an <%ae>|%s")
    assert log.startswith("Developer <developer@agents.nidvue.com>|feat(widget):")
    body = git(fixture_project, "log", "-1", "--format=%B")
    assert "Task: T-0001" in body and "Acting role: Developer" in body

    audit = engine_cli(fixture_project, "identity", "--audit", "--range", "main..HEAD")
    assert audit.returncode == 0, output(audit)
    assert "problems: 0" in audit.stdout

    ledger = engine_cli(fixture_project, "ledger", "verify")
    assert ledger.returncode == 0, output(ledger)
    assert "chain intact" in ledger.stdout

    # The same ledger read from outside the project: project resolution must not
    # depend on the cwd, or a lane that runs from anywhere reports the wrong file.
    far = engine_cli(fixture_project, "ledger", "verify", cwd=fixture_project.parent)
    assert far.returncode == 0, output(far)
    assert "chain intact" in far.stdout

    loop = engine_cli(fixture_project, "loop")
    assert loop.returncode == 1, output(loop)
    assert "CONTINUE" in loop.stdout


def test_the_clean_scope_contract_holds_through_the_cli(fixture_project: Path) -> None:
    """A bare clean refuses; ``--agent`` reaches one lane's Scratch and nothing else."""
    team = init_workspace(fixture_project)
    agents = team / "Agents"
    (agents / "Developer" / "Scratch").mkdir(parents=True, exist_ok=True)
    (agents / "Tester" / "Scratch").mkdir(parents=True, exist_ok=True)
    (agents / "Developer" / "Scratch" / "junk.tmp").write_text("x", encoding="utf-8")
    (agents / "Developer" / "Scratch" / "notes.md").write_text("x", encoding="utf-8")
    (agents / "Tester" / "Scratch" / "peer.tmp").write_text("x", encoding="utf-8")
    (agents / "Developer" / "keep-me.txt").write_text("x", encoding="utf-8")

    bare = engine_cli(fixture_project, "clean")
    assert bare.returncode == 2, output(bare)
    assert "clean needs a scope" in output(bare)
    assert (agents / "Developer" / "Scratch" / "junk.tmp").is_file(), "a refusal removed a file"

    scoped = engine_cli(fixture_project, "clean", "--agent", "Developer")
    assert scoped.returncode == 0, output(scoped)
    assert not (agents / "Developer" / "Scratch" / "junk.tmp").exists()
    assert (agents / "Tester" / "Scratch" / "peer.tmp").is_file(), "--agent reached a peer lane"
    assert (agents / "Developer" / "Scratch" / "notes.md").is_file()
    assert (agents / "Developer" / "keep-me.txt").is_file()

    conflicting = engine_cli(fixture_project, "clean", "--agent", "Developer", "--team-wide")
    assert conflicting.returncode == 2, output(conflicting)
    assert "pick one" in output(conflicting)

    emptied = engine_cli(fixture_project, "clean", "--agent", "Developer", "--all")
    assert emptied.returncode == 0, output(emptied)
    assert not (agents / "Developer" / "Scratch" / "notes.md").exists()
    assert (agents / "Developer" / "Inbox.md").is_file()
    assert (agents / "Tester" / "Scratch" / "peer.tmp").is_file()


def test_team_wide_clean_reaches_the_shared_dirs_and_prints_the_scope_first(
    fixture_project: Path,
) -> None:
    """The positive half: ``--team-wide`` is the only scope that reaches Global/ and Roles/.

    The refund of developer T-0005 is asymmetric: the lane default must not touch a
    peer, and the deliberate flag must actually reach the team-shared state - and say
    so *before* the first unlink. A test that only asserts the refusal cannot tell a
    working ``--team-wide`` from a flag that does nothing.
    """
    team = init_workspace(fixture_project)
    agents = team / "Agents"
    (agents / "Developer" / "Scratch").mkdir(parents=True, exist_ok=True)
    (agents / "Tester" / "Scratch").mkdir(parents=True, exist_ok=True)
    (agents / "Developer" / "Scratch" / "lane.tmp").write_text("x", encoding="utf-8")
    (agents / "loose.tmp").write_text("x", encoding="utf-8")
    (team / "Global" / "shared.tmp").write_text("x", encoding="utf-8")
    (team / "Global" / "keep.md").write_text("x", encoding="utf-8")
    (team / "Roles" / "Developer" / "queue.tmp").write_text("x", encoding="utf-8")
    (team / "Roles" / "Developer" / "keep.md").write_text("x", encoding="utf-8")

    lane = engine_cli(fixture_project, "clean", "--agent", "Developer")
    assert lane.returncode == 0, output(lane)
    assert not (agents / "Developer" / "Scratch" / "lane.tmp").exists()
    assert (team / "Global" / "shared.tmp").is_file(), "--agent reached Global/"
    assert (team / "Roles" / "Developer" / "queue.tmp").is_file(), "--agent reached Roles/"

    (agents / "Developer" / "Scratch" / "lane.tmp").write_text("x", encoding="utf-8")
    wide = engine_cli(fixture_project, "clean", "--team-wide")
    assert wide.returncode == 0, output(wide)
    at = output(wide)
    lines = wide.stdout.splitlines()
    announced = next((i for i, line in enumerate(lines) if "team-wide clean:" in line), None)
    assert announced is not None, f"no scope announcement before the removals: {at}"
    summary = next((i for i, line in enumerate(lines) if "removed " in line), None)
    assert summary is not None, f"no removal summary: {at}"
    locations = [line.strip() for line in lines[announced + 1 : summary] if line.startswith("  - ")]
    assert announced < summary, f"the scope must be printed before the first removal: {at}"
    assert any(path.endswith("Global") for path in locations), locations
    assert any(path.endswith("Roles") for path in locations), locations
    assert not (team / "Global" / "shared.tmp").exists(), "--team-wide missed Global/"
    assert not (team / "Roles" / "Developer" / "queue.tmp").exists(), "--team-wide missed Roles/"
    assert not (agents / "Developer" / "Scratch" / "lane.tmp").exists()
    assert (agents / "loose.tmp").is_file(), "a file sitting directly in Agents/ has no lane"
    assert (team / "Global" / "GlobalMemory.md").is_file()
    assert (team / "Roles" / "Developer" / "TaskQueue.md").is_file()

    (team / "Global" / "last.tmp").write_text("x", encoding="utf-8")
    (team / "Roles" / "Developer" / "queue.tmp").write_text("x", encoding="utf-8")
    (agents / "Developer" / "Scratch" / "note.md").write_text("x", encoding="utf-8")
    emptied = engine_cli(fixture_project, "clean", "--team-wide", "--all")
    assert emptied.returncode == 0, output(emptied)
    assert not (team / "Global" / "last.tmp").exists(), "--all left a temp file in Global/"
    assert not (team / "Roles" / "Developer" / "queue.tmp").exists(), "--all left a temp in Roles/"
    assert not (agents / "Developer" / "Scratch" / "note.md").exists(), "--all left a lane Scratch"
    assert (team / "Global" / "GlobalMemory.md").is_file(), "--all emptied GlobalMemory.md"
    assert (team / "Roles" / "Developer" / "TaskQueue.md").is_file(), "--all emptied a queue"
    assert (team / "Global" / "keep.md").is_file(), "--all removed non-temp content in Global/"
    assert (team / "Roles" / "Developer" / "keep.md").is_file(), "--all removed non-temp in Roles/"
    assert (agents / "loose.tmp").is_file(), "--all reached a file with no lane"


def test_preflight_fails_closed_and_goes_green_on_a_real_branch(fixture_project: Path) -> None:
    """Green control first, then each red check, then green again on the same revision."""
    team = init_workspace(fixture_project)
    start_task(fixture_project)
    committed = commit_widget(fixture_project, "widget.py")
    assert committed.returncode == 0, output(committed)
    sha = git(fixture_project, "rev-parse", "HEAD").strip()

    settings = team / "Settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["PreflightCommand"] = f'"{sys.executable}" -c "print(1)"'
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    evidence = f"pytest @{sha[:12]} -> 1 passed"
    assert (
        engine_cli(
            fixture_project, "task", "set", "Developer", "T-0001", "--evidence", evidence
        ).returncode
        == 0
    )

    green = engine_cli(fixture_project, "preflight", "Developer", "T-0001", "--run")
    assert green.returncode == 0, output(green)
    assert "PREFLIGHT pass" in green.stdout and "0 failed" in green.stdout

    unreachable = "pytest @deadbeefdeadbeef -> 1 passed"
    assert (
        engine_cli(
            fixture_project, "task", "set", "Developer", "T-0001", "--evidence", unreachable
        ).returncode
        == 0
    )
    red = engine_cli(fixture_project, "preflight", "Developer", "T-0001", "--run")
    assert red.returncode == 1, output(red)
    assert "evidence" in red.stdout and "@deadbeefdeadbeef" in red.stdout
    assert (
        engine_cli(
            fixture_project, "task", "set", "Developer", "T-0001", "--evidence", evidence
        ).returncode
        == 0
    )

    # A gate this host cannot start is a red check naming the command - not a
    # traceback out of the engine, and not a silent pass on a platform that has
    # the POSIX tool but not the project's.
    data["PreflightCommand"] = "teamwork-no-such-gate-command --check"
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    absent = engine_cli(fixture_project, "preflight", "Developer", "T-0001", "--run")
    assert absent.returncode == 1, output(absent)
    assert "could not start" in absent.stdout and "teamwork-no-such-gate-command" in absent.stdout

    data["PreflightCommand"] = "git rev-parse --verify refs/heads/no-such-branch"
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    failing = engine_cli(fixture_project, "preflight", "Developer", "T-0001", "--run")
    assert failing.returncode == 1, output(failing)
    assert "-> exit" in failing.stdout and "gate" in failing.stdout

    data["PreflightCommand"] = f'"{sys.executable}" -c "print(1)"'
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    again = engine_cli(fixture_project, "preflight", "Developer", "T-0001", "--run")
    assert again.returncode == 0, output(again)
    assert "PREFLIGHT pass" in again.stdout


def test_preflight_refuses_a_team_domain_author_with_the_wrong_display_name(
    fixture_project: Path,
) -> None:
    """An inside contributor does not get the external-contributor skip."""
    init_workspace(fixture_project)
    start_task(fixture_project)
    (fixture_project / "widget.py").write_text("WIDGET = 2\n", encoding="utf-8")
    git(fixture_project, "add", "widget.py")
    git(
        fixture_project,
        "commit",
        "-qm",
        "feat: widget",
        identity=("Wrong Name", "developer@agents.nidvue.com"),
    )
    red = engine_cli(fixture_project, "preflight", "Developer", "T-0001")
    assert red.returncode == 1, output(red)
    assert "identity" in red.stdout
    assert "does not match role 'Developer'" in red.stdout
