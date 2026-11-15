"""`branch start --worktree` compares the whole path, never a substring.

T-0037 / A-0012: the existence check was `str(wt) in <porcelain listing>`, so an
instance whose name is a prefix of a sibling's (`Developer-1` inside
`Developer-10`) matched the sibling's record, `git worktree add` never ran, and
the task recorded a worktree path that did not exist.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,developer-10"


def _team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def _repo(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    engine.ensure_repo(project, commit=False, quiet=True)
    (project / "a.txt").write_text("one\n", encoding="utf-8")
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "seed")
    return _team_root(project)


def _record(root: Path, task_id: str) -> dict:
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    return tasks[engine.find_task(tasks, task_id)]


def _task(cli, project: Path, title: str) -> dict:
    assert cli("--project", project, "task", "add", "developer", title) == 0
    return engine.parse_tasks(engine.task_file(_team_root(project), "developer"))[-1]


def test_a_prefix_named_sibling_does_not_count_as_our_worktree(cli, project: Path) -> None:
    root = _repo(cli, project)
    sibling = _task(cli, project, "sibling lane")
    ours = _task(cli, project, "our lane")
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "Developer-10",
            "--task",
            sibling["id"],
            "--worktree",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "Developer-1",
            "--task",
            ours["id"],
            "--worktree",
        )
        == 0
    )
    recorded = _record(root, ours["id"])
    here = engine.task_worktree(root, recorded)
    assert here.is_dir()
    assert (here / ".git").exists()
    assert here.resolve() == Path(engine.branch_worktree(project, recorded["branch"])).resolve()


def test_a_second_start_reuses_the_registered_worktree(cli, project: Path) -> None:
    root = _repo(cli, project)
    task = _task(cli, project, "our lane")
    args = (
        "--project",
        project,
        "branch",
        "start",
        "--agent",
        "Developer-1",
        "--task",
        task["id"],
        "--worktree",
    )
    assert cli(*args) == 0
    first = _record(root, task["id"])["worktree"]
    assert cli(*args) == 0
    second = _record(root, task["id"])["worktree"]
    assert first == second
    assert engine.task_worktree(root, {"worktree": second}).is_dir()


def test_the_check_matches_whole_paths_only(cli, project: Path) -> None:
    _repo(cli, project)
    ten = project / ".pi" / "worktrees" / "Developer-10"
    engine.run_git(project, "worktree", "add", "--detach", str(ten), "HEAD")
    assert engine._worktree_registered(project, ten)
    assert not engine._worktree_registered(project, project / ".pi" / "worktrees" / "Developer-1")
