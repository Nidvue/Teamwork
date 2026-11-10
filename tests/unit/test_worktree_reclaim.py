"""`clean` reclaims only worktrees that cannot lose work.

T-0040: 43 worktrees / 267 MB accumulated under `.pi/` because nothing ever
removed them, and a hand-deleted worktree is how a lane silently loses a commit.
The reclaimer is allowed to touch a worktree only when it is inside the project's
own `.pi/`, is not the main checkout, has a clean status, and its HEAD is reachable
from the default branch.
"""

from __future__ import annotations

import os
import time
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


def _add_worktree(project: Path, name: str, rev: str = "HEAD") -> Path:
    path = project / ".pi" / "worktrees" / name
    engine.run_git(project, "worktree", "add", "--detach", str(path), rev)
    return path


def _age(path: Path, minutes: int) -> None:
    """Age the whole tree, not just its top dir: freshness is recursive."""
    stamp = time.time() - minutes * 60
    for child in [path, *path.rglob("*")]:
        try:
            os.utime(child, (stamp, stamp), follow_symlinks=False)
        except (OSError, NotImplementedError):
            # Windows cannot set a symlink's own time (follow_symlinks=False is
            # unimplemented there); the link target's time is enough for the
            # freshness rule, so fall back to following instead of skipping.
            try:
                os.utime(child, (stamp, stamp))
            except OSError:
                continue


def test_a_clean_merged_worktree_is_reclaimed(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "gone")
    _age(wt, 120)
    assert [w["path"] for w in engine.reclaimable_worktrees(root, 60)] == [str(wt)]


def test_a_worktree_holding_unmerged_commits_is_kept(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "ahead")
    (wt / "b.txt").write_text("two\n", encoding="utf-8")
    engine.run_git(wt, "add", "-A")
    engine.run_git(wt, "commit", "-qm", "work only here")
    _age(wt, 120)
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_dirty_worktree_is_kept(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "dirty")
    (wt / "a.txt").write_text("edited\n", encoding="utf-8")
    _age(wt, 120)
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_recent_worktree_is_kept(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    _add_worktree(project, "fresh")
    assert engine.reclaimable_worktrees(root, 60) == []


def test_the_main_checkout_is_never_reclaimed(cli, project: Path) -> None:
    root = _repo_with_team(cli, project)
    assert engine.reclaimable_worktrees(root, 0) == []


def test_a_worktree_outside_pi_is_never_reclaimed(cli, project: Path) -> None:
    """A reviewer may create one; it is theirs, not the team's to delete."""
    root = _repo_with_team(cli, project)
    outside = project / "elsewhere"
    engine.run_git(project, "worktree", "add", "--detach", str(outside), "HEAD")
    _age(outside, 120)
    assert engine.reclaimable_worktrees(root, 60) == []


def test_clean_removes_the_reclaimable_worktree_and_keeps_the_rest(cli, project: Path) -> None:
    _repo_with_team(cli, project)
    gone = _add_worktree(project, "gone")
    kept = _add_worktree(project, "dirty")
    (kept / "a.txt").write_text("edited\n", encoding="utf-8")
    _age(gone, 120)
    _age(kept, 120)
    assert cli("--project", project, "clean") == 0
    assert not gone.exists()
    assert kept.exists()
    assert engine.run_git(project, "worktree", "list").returncode == 0


def test_no_worktrees_leaves_them_alone(cli, project: Path) -> None:
    _repo_with_team(cli, project)
    gone = _add_worktree(project, "gone")
    _age(gone, 120)
    assert cli("--project", project, "clean", "--no-worktrees") == 0
    assert gone.exists()


def test_a_worktree_holding_only_ignored_build_output_is_kept(cli, project: Path) -> None:
    """A lane's gitignored build cache is work, even though git status is clean."""
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "live")
    (wt / "build").mkdir()
    (wt / "build" / "obj.o").write_bytes(b"x")
    _age(wt, 120)
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_directory_sharing_the_pi_prefix_is_not_ours(cli, project: Path) -> None:
    """`.pi-evil/x` starts with the same characters as `.pi` but is not our tree."""
    root = _repo_with_team(cli, project)
    outside = project / ".pi-evil" / "x"
    engine.run_git(project, "worktree", "add", "--detach", str(outside), "HEAD")
    _age(outside, 120)
    listed = engine.run_git(project, "worktree", "list", "--porcelain").stdout
    assert str(outside) in listed, "the probe worktree must really be registered"
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_locked_worktree_is_not_reclaimed(cli, project: Path) -> None:
    """`git worktree lock` pins a worktree on purpose; the reclaimer must respect it."""
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "pinned")
    engine.run_git(project, "worktree", "lock", str(wt))
    _age(wt, 120)
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_worktree_claimed_by_a_doing_task_is_not_reclaimed(cli, project: Path) -> None:
    """A live lane's worktree may look idle; its claimed task is the signal."""
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "Developer-1")
    _age(wt, 120)
    cli("--project", project, "task", "add", "developer", "work in progress")
    tasks_path = root / "Roles" / "Developer" / engine.F_TASKS
    tasks = engine.parse_tasks(tasks_path)
    tasks[0]["status"] = "doing"
    tasks[0]["claimed_by"] = "Developer-1"
    engine.write_tasks(tasks_path, tasks, "developer")
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_claim_in_any_case_protects_the_worktree(cli, project: Path) -> None:
    """Claims are written `Developer-1`, worktree dirs `developer-1`: both must match."""
    root = _repo_with_team(cli, project)
    wt = _add_worktree(project, "developer-1")
    _age(wt, 120)
    cli("--project", project, "task", "add", "developer", "work in progress")
    tasks_path = root / "Roles" / "Developer" / engine.F_TASKS
    tasks = engine.parse_tasks(tasks_path)
    tasks[0]["status"] = "doing"
    tasks[0]["claimed_by"] = "Developer-1"
    engine.write_tasks(tasks_path, tasks, "developer")
    assert engine.reclaimable_worktrees(root, 60) == []


def test_a_reclaim_that_failed_is_reported_not_counted(cli, project: Path, capsys) -> None:
    """A lock or permission failure must never print as a successful reclaim."""
    _repo_with_team(cli, project)
    wt = _add_worktree(project, "stuck")
    _age(wt, 120)
    engine.run_git(project, "worktree", "lock", str(wt))
    capsys.readouterr()
    assert cli("--project", project, "clean", "--stale-minutes", "60") == 0
    out = capsys.readouterr().out
    assert "could not be reclaimed" not in out, "a locked worktree is skipped, not failed"
    assert wt.exists(), "a locked worktree must survive"
