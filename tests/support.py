"""Shared helpers for the per-task worktree contract.

Since T-0067 a branch start gives the task its own worktree and leaves the shared
checkout on the base branch, so a test that acts as an author has to act inside
that tree: writing files into the project root and committing there is exactly the
behaviour the engine now refuses.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from teamwork import engine


def team_root(project: Path, team: str | None = None) -> Path:
    """The hidden team tree, honouring a ``--team`` name when one was used."""
    base = project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR
    if team:
        return (base / team).resolve()
    slug = engine.team_slug(project)
    if (base / slug).is_dir():
        return (base / slug).resolve()
    teams = sorted(path for path in base.iterdir() if path.is_dir()) if base.is_dir() else []
    assert len(teams) == 1, teams
    return teams[0].resolve()


def lane_tree(project: Path, task: str | None = None) -> Path:
    """The worktree recorded for ``task``, or the newest recorded one."""
    root = team_root(project)
    found: list[Path] = []
    for role in engine.list_roles(root):
        for item in engine.parse_tasks(engine.task_file(root, role)):
            resolved = engine.task_worktree(root, item)
            if resolved is None:
                continue
            if task is None or item["id"] == task:
                found.append(resolved)
    if not found:
        raise AssertionError(f"no worktree recorded in {root}")
    return found[-1]


@contextmanager
def in_lane(project: Path, task: str | None = None):
    """Act as the author acts: from inside the task's own worktree."""
    path = lane_tree(project, task)
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(previous)


def lane_cli(cli, project: Path, task: str | None = None):
    """A ``cli`` that runs inside the task's worktree: what an author's call is."""

    def run(*argv) -> int:
        with in_lane(project, task):
            return cli(*argv)

    return run
