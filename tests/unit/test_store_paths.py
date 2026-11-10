"""A store records a lane path relative to the team root (T-0060).

An absolute host path in `Roles/<Role>/TaskQueue.md` names a machine the reader
may not be on, and its high-entropy segment is what the record mask redacts
(K-0008). The store keeps `Runtime/Worktrees/<Instance>/<T-id>` and a reader
joins it back onto the team root.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def _team_root(project: Path) -> Path:
    return project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)


def _repo_with_team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    engine.ensure_repo(project, commit=False, quiet=True)
    (project / "a.txt").write_text("one\n", encoding="utf-8")
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "seed")
    return _team_root(project).resolve()


def test_branch_start_records_a_worktree_relative_to_the_team_root(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    assert cli("--project", project, "task", "add", "developer-1", "lane") == 0
    queue = engine.task_file(root, engine.resolve_role("developer-1"))
    task_id = engine.parse_tasks(queue)[0]["id"]
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "developer-1",
            "--task",
            task_id,
            "--worktree",
        )
        == 0
    )

    stored = engine.parse_tasks(queue)[0]["worktree"]
    assert stored == f"Runtime/Worktrees/Developer-1/{task_id}"
    assert engine.resolve_team_relative(root, stored) == engine.lane_worktree(
        root, "Developer-1", task_id
    )
    assert str(root) not in queue.read_text(encoding="utf-8")


def test_the_scaffolded_charter_names_its_references_portably(tmp_path: Path) -> None:
    role_dir = engine.scaffold_role(tmp_path / "Team", "developer")
    text = (role_dir / engine.F_ROLE).read_text(encoding="utf-8")
    assert "references/Roles.md" in text
    assert "/home/" not in text
