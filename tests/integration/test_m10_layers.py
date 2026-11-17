"""Integration: the M10 surfaces a lane meets at the process boundary.

The unit layers next to this one call the engine in-process against fakes. Every
assertion below runs a real ``python scripts/teamwork.py`` subprocess against a
real throwaway git repository, because the eight test-plan gaps this module
closes (claims, clean, dispatch, git, signing, status-widget, worktree) are all
*scope* contracts: what a second caller may not take, what clean may not delete,
which tree a commit lands in. A fake cannot fail those.

Owner: tester. Task: T-0017.
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
    env = dict(os.environ)
    for name in ("TEAMWORK_ROOT", "TEAMWORK_TEAM", "TEAMWORK_BUS"):
        env.pop(name, None)
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def git(project: Path, *args: str) -> str:
    name, email = GIT_IDENTITY
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


def cli(project: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
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


def text(proc: subprocess.CompletedProcess) -> str:
    return proc.stdout + proc.stderr


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "Portable Space" / "Project"
    path.mkdir(parents=True)
    git(path, "init", "-b", "main", "--quiet")
    (path / "app.txt").write_text("hello\n", encoding="utf-8")
    git(path, "add", "app.txt")
    git(path, "commit", "-qm", "init")
    done = cli(path, "init", "--agents", ROSTER)
    assert done.returncode == 0, text(done)
    return path


def team_root(project: Path) -> Path:
    return project / ".pi" / "Teamwork" / "Teams" / TEAM


def add_task(project: Path, role: str, title: str, priority: str = "P0") -> str:
    added = cli(project, "task", "add", role, title, "--priority", priority)
    assert added.returncode == 0, text(added)
    listed = cli(project, "task", "list", role)
    assert listed.returncode == 0, text(listed)
    return ""


def test_a_second_claim_on_a_live_value_is_refused_and_release_frees_it(project: Path) -> None:
    first = cli(project, "claim", "add", "--by", "Dev-1", "--path", "src/widget.py", "--ttl", "60")
    assert first.returncode == 0, text(first)
    claim_id = next(word for word in first.stdout.split() if word.startswith("C-"))

    second = cli(project, "claim", "add", "--by", "Dev-2", "--path", "src/widget.py", "--ttl", "60")
    assert second.returncode != 0
    assert "Dev-1" in text(second)

    held = cli(project, "claim", "check", "src/widget.py")
    assert held.returncode == 0, text(held)
    assert "Dev-1" in held.stdout

    released = cli(project, "claim", "release", claim_id)
    assert released.returncode == 0, text(released)
    assert cli(project, "claim", "check", "src/widget.py").returncode != 0

    again = cli(project, "claim", "add", "--by", "Dev-2", "--path", "src/widget.py", "--ttl", "60")
    assert again.returncode == 0, text(again)


def test_clean_removes_only_scratch_and_a_dry_run_removes_nothing(project: Path) -> None:
    scratch = team_root(project) / "Agents" / "Developer" / "Scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    junk = scratch / "draft.py.orig"
    junk.write_text("junk\n", encoding="utf-8")
    kept = team_root(project) / "Agents" / "Developer" / "WorkLog.md"
    kept.write_text("# WorkLog\n", encoding="utf-8")

    dry = cli(project, "clean", "--agent", "Developer", "--all", "--dry-run")
    assert dry.returncode == 0, text(dry)
    assert junk.exists(), "a dry run removed a file"

    real = cli(project, "clean", "--agent", "Developer", "--all")
    assert real.returncode == 0, text(real)
    assert not junk.exists(), "clean left the scratch file"
    assert kept.exists(), "clean deleted a record outside Scratch"
    assert (project / "app.txt").is_file(), "clean deleted a tracked file"


def test_dispatch_hands_two_instances_two_different_tasks(project: Path) -> None:
    add_task(project, "developer", "Build the widget")
    add_task(project, "developer", "Build the gadget", "P1")

    one = cli(project, "task", "next", "Developer")
    assert one.returncode == 0, text(one)
    two = cli(project, "task", "next", "Developer")
    assert two.returncode == 0, text(two)
    claimed = [
        next(word for word in proc.stdout.split() if word.startswith("T-")) for proc in (one, two)
    ]
    assert sorted(claimed) == ["T-0001", "T-0002"], claimed
    assert claimed[0] != claimed[1], claimed

    third = cli(project, "task", "next", "Developer")
    assert third.returncode != 0, text(third)


def test_a_commit_lands_on_the_lane_branch_and_leaves_the_checkout_alone(project: Path) -> None:
    add_task(project, "developer", "Build the widget")
    assert cli(project, "task", "next", "Developer").returncode == 0
    started = cli(project, "branch", "start", "--agent", "developer", "--task", "T-0001")
    assert started.returncode == 0, text(started)
    tree = Path(
        next(
            line.split("worktree:", 1)[1].strip()
            for line in started.stdout.splitlines()
            if "worktree:" in line
        )
    )

    (tree / "widget.py").write_text("WIDGET = 1\n", encoding="utf-8")
    made = cli(
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
        "--paths",
        "widget.py",
        cwd=tree,
    )
    assert made.returncode == 0, text(made)
    assert (
        git(tree, "rev-parse", "--abbrev-ref", "HEAD").strip()
        == "developer/t-0001-build-the-widget"
    )
    assert not (project / "widget.py").exists(), "the commit landed in the main checkout"
    tracked = git(project, "ls-tree", "-r", "--name-only", "HEAD")
    assert "widget.py" not in tracked, tracked


def test_a_signed_repository_without_a_key_fails_closed_without_a_commit(project: Path) -> None:
    """The gate adds no requirement, but it never swallows one either: a repo that
    requires signing and a host with no key is a red commit, not a silent unsigned
    one, and nothing is recorded."""
    git(project, "config", "commit.gpgsign", "true")
    add_task(project, "developer", "Build the widget")
    assert cli(project, "task", "next", "Developer").returncode == 0
    started = cli(project, "branch", "start", "--agent", "developer", "--task", "T-0001")
    assert started.returncode == 0, text(started)
    tree = Path(
        next(
            line.split("worktree:", 1)[1].strip()
            for line in started.stdout.splitlines()
            if "worktree:" in line
        )
    )
    before = git(tree, "rev-list", "--count", "HEAD").strip()

    (tree / "widget.py").write_text("WIDGET = 1\n", encoding="utf-8")
    made = cli(
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
        "--paths",
        "widget.py",
        cwd=tree,
    )
    assert made.returncode != 0, text(made)
    assert "sign" in text(made).lower(), text(made)
    assert git(tree, "rev-list", "--count", "HEAD").strip() == before


def test_status_json_names_the_instance_and_the_task_it_holds(project: Path) -> None:
    add_task(project, "developer", "Build the widget")
    assert cli(project, "task", "next", "Developer").returncode == 0

    done = cli(project, "status", "--json")
    assert done.returncode == 0, text(done)
    payload = json.loads(done.stdout)
    rows = payload if isinstance(payload, list) else payload.get("instances", payload)
    assert rows, payload
    blob = json.dumps(rows)
    assert "T-0001" in blob
    assert "Developer" in blob


def test_two_tasks_get_two_worktrees_and_neither_is_the_checkout(project: Path) -> None:
    add_task(project, "developer", "Build the widget")
    add_task(project, "developer", "Build the gadget", "P1")
    trees = []
    for task in ("T-0001", "T-0002"):
        assert cli(project, "task", "next", "Developer").returncode == 0
        started = cli(project, "branch", "start", "--agent", "developer", "--task", task)
        assert started.returncode == 0, text(started)
        trees.append(
            Path(
                next(
                    line.split("worktree:", 1)[1].strip()
                    for line in started.stdout.splitlines()
                    if "worktree:" in line
                )
            )
        )

    assert trees[0] != trees[1], trees
    assert project not in trees
    assert trees[0].is_dir() and trees[1].is_dir()
    assert (trees[0] / "app.txt").is_file(), "the worktree is not a checkout of the project"
