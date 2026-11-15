"""Every instance works in its own worktree; the shared checkout is the exception.

The contract, in the order a lane meets it:

* `branch start` creates the task's worktree and leaves the shared checkout on the
  default branch, so two lanes of one repository never share a writable tree;
* the recorded path is relative to the team root - an absolute host path in a queue
  is disclosure to every lane that reads it, and the record mask can rewrite a
  directory path that looks high-entropy, which silently points the record at a
  tree that does not exist;
* the worktree carries the project's toolchain link, so the project gate command
  runs there unchanged;
* `commit --task` refuses from the shared checkout when the task owns a worktree;
* `preflight` fails its `tree` check when the command ran in a different tree than
  the task records, and its gate runs in the task's tree;
* `--shared` is the documented exception and records no worktree.
"""

from __future__ import annotations

from pathlib import Path

from support import in_lane, lane_tree, team_root
from teamwork import engine

AGENTS = ("ceo", "developer-1", "reviewer-1")


def init_team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    return team_root(project)


def start_task(cli, project: Path, *, shared: bool = False) -> None:
    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    argv = ["--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001"]
    if shared:
        argv.append("--shared")
    assert cli(*argv) == 0


def record(project: Path) -> dict:
    root = team_root(project)
    for item in engine.parse_tasks(engine.task_file(root, "developer")):
        if item["id"] == "T-0001":
            return item
    raise AssertionError("T-0001 not on the developer queue")


def test_branch_start_gives_the_task_its_own_worktree(cli, project: Path) -> None:
    """The default: a worktree exists, the shared checkout did not move."""
    root = init_team(cli, project)
    start_task(cli, project)

    task = record(project)
    recorded = task["worktree"]
    assert recorded, "the task must record the worktree it works in"
    assert not Path(recorded).is_absolute(), "a recorded host path is disclosure to every lane"
    tree = engine.task_worktree(root, task)
    assert tree.is_dir()
    assert (tree / ".git").exists()
    assert engine.current_branch(project) == "main"
    assert engine.current_branch(tree) == task["branch"]


def test_the_toolchain_link_lets_the_gate_command_run_in_the_worktree(cli, project: Path) -> None:
    """A worktree carries tracked files only; the venv is linked, not copied."""
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / ".venv" / "bin" / "ruff").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    init_team(cli, project)
    start_task(cli, project)

    tree = lane_tree(project, "T-0001")
    link = tree / ".venv"
    assert link.is_symlink() or link.is_dir()
    assert (link / "bin" / "ruff").is_file()


def test_commit_from_the_shared_checkout_is_refused(cli, project: Path, capsys) -> None:
    """Two guards, two messages: the branch guard first, then the worktree guard."""
    init_team(cli, project)
    start_task(cli, project)
    tree = lane_tree(project, "T-0001")
    (project / "feature.txt").write_text("done\n", encoding="utf-8")
    capsys.readouterr()

    argv = (
        "--project",
        project,
        "commit",
        "--role",
        "developer",
        "--task",
        "T-0001",
        "--type",
        "feat",
        "--goal",
        "ship it",
        "--deliverable",
        "feature.txt",
        "--why",
        "the task asks for it",
        "--status",
        "implemented",
        "--result",
        "true @rev -> ok",
        "--all",
    )
    assert cli(*argv) == 2
    first = capsys.readouterr().err
    assert "belongs to" in first, "on the default branch the branch guard refuses first"

    assert cli(*argv, "--allow-main") == 2
    second = capsys.readouterr().err
    assert "owns the worktree" in second, (
        "with the branch guard bypassed the worktree guard refuses"
    )
    assert str(tree) in second, "the refusal must name the worktree to cd into"
    assert engine.current_branch(project) == "main"

    with in_lane(project, "T-0001") as work:
        (work / "feature.txt").write_text("done\n", encoding="utf-8")
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "ship it",
                "--deliverable",
                "feature.txt",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "true @rev -> ok",
                "--all",
            )
            == 0
        )


def commit_feature(cli, project: Path) -> None:
    """One committed change in the task's tree, so the branch check is not the reason."""
    with in_lane(project, "T-0001") as work:
        (work / "feature.txt").write_text("done\n", encoding="utf-8")
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "ship it",
                "--deliverable",
                "feature.txt",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "true @rev -> ok",
                "--all",
            )
            == 0
        )


def test_preflight_refuses_a_command_that_ran_in_another_tree(cli, project: Path, capsys) -> None:
    """A green gate that measured the shared checkout says nothing about the branch."""
    init_team(cli, project)
    start_task(cli, project)
    commit_feature(cli, project)

    capsys.readouterr()
    assert cli("--project", project, "preflight", "developer", "T-0001") == 1
    assert "- fail       tree" in capsys.readouterr().out

    with in_lane(project, "T-0001"):
        capsys.readouterr()
        assert cli("--project", project, "preflight", "developer", "T-0001") == 0
        assert "- ok         tree" in capsys.readouterr().out


def test_the_gate_runs_in_the_task_tree(cli, project: Path) -> None:
    """`PreflightCommand` runs in the task's tree: the branch's file is visible."""
    import json

    root = init_team(cli, project)
    start_task(cli, project)
    commit_feature(cli, project)
    settings = root / "Settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["PreflightCommand"] = "test -f feature.txt"
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    with in_lane(project, "T-0001"):
        assert cli("--project", project, "preflight", "developer", "T-0001", "--run") == 0


def test_shared_is_the_exception_and_records_no_worktree(cli, project: Path) -> None:
    """`--shared` switches the shared checkout and records nothing to resolve."""
    init_team(cli, project)
    start_task(cli, project, shared=True)

    task = record(project)
    assert not task.get("worktree")
    assert engine.current_branch(project) == task["branch"]
    assert not (team_root(project) / "Runtime" / "Worktrees").exists() or not any(
        (team_root(project) / "Runtime" / "Worktrees").rglob("T-0001")
    )
