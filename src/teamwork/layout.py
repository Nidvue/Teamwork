"""Workspace layout: the team tree, committed docs and their links."""

from __future__ import annotations

import os
from pathlib import Path

from .config import (
    DIR_AGENTS,
    DIR_DOCS,
    DIR_GLOBAL,
    DIR_ROLES,
    DIR_RUNTIME,
    DIR_WORKTREES,
    F_CRITERIA,
    F_DISPUTES,
    F_GLOBAL,
    F_GLOBAL_ARCHIVE,
    F_INBOX,
    F_LONG,
    F_MAP,
    F_MEM_ARCHIVE,
    F_REVIEWS,
    F_ROLE,
    F_SHORT,
    F_SKILLS,
    F_TASKS,
    F_TESTPLAN,
    F_TESTS,
    F_WORKLOG,
    SKILLS_DIR,
    TEAM_ROOT_DIR,
    TEAMS_SUBDIR,
)
from .io import die
from .names import pascal, resolve_role, safe_component, team_slug


def project_path(args) -> Path:
    if getattr(args, "project", None):
        return Path(args.project).expanduser().resolve()
    return Path.cwd()


def project_of(root: Path) -> Path:
    """<project>/.pi/Teamwork/Teams/<Team> -> <project>."""
    return root.parents[3]


def docs_dir(root: Path) -> Path:
    """Committed project output. The team's own tree stays in .pi/Teamwork."""
    return project_of(root).joinpath(*DIR_DOCS)


def work_repo(root: Path, cwd: Path | None = None) -> Path:
    """The git work tree this command should act on.

    Inside one of our per-instance worktrees that worktree is the answer;
    otherwise it is the project that owns the team tree.
    """
    cwd = (cwd or Path.cwd()).resolve()
    wt_root = root / DIR_RUNTIME / DIR_WORKTREES
    if wt_root.is_dir():
        for parent in [cwd, *cwd.parents]:
            try:
                rel = parent.relative_to(wt_root)
            except ValueError:
                continue
            if rel.parts:
                cand = wt_root / rel.parts[0]
                if (cand / ".git").exists():
                    return cand
    return project_of(root)


def work_docs_dir(root: Path, cwd: Path | None = None) -> Path:
    """Committed project output in the work tree this command acts on.

    ``docs_dir`` always points at the project that owns the team tree; a lane
    that runs inside its own worktree must land its output there instead, so
    the file can be committed on the lane's branch.
    """
    return work_repo(root, cwd).joinpath(*DIR_DOCS)


def team_root_from_cwd(cwd: Path) -> Path | None:
    """If we are inside one of our own worktrees, use the team that owns it.

    `<team>/Runtime/Worktrees/<Instance>/...` -> `<team>`; anything else -> None.
    Without this, running a command from a worktree would look for (and create)
    a second, unrelated team tree.
    """
    for parent in [cwd, *cwd.parents]:
        if parent.name == DIR_WORKTREES and parent.parent.name == DIR_RUNTIME:
            candidate = parent.parent.parent
            if (candidate / DIR_ROLES).is_dir() or (candidate / F_MAP).exists():
                return candidate
    return None


def project_root(args) -> Path:
    """The current team's hidden tree:
    <project>/.pi/Teamwork/Teams/<Team>/"""
    if os.environ.get("TEAMWORK_ROOT"):
        return Path(os.environ["TEAMWORK_ROOT"]).expanduser().resolve()
    if not getattr(args, "project", None):
        found = team_root_from_cwd(Path.cwd().resolve())
        if found is not None:
            return found
    project = project_path(args)
    slug = team_slug(project, getattr(args, "team", "") or "")
    return (project / TEAM_ROOT_DIR / TEAMS_SUBDIR / slug).resolve()


def teams_root_unused(project: Path) -> Path:
    return project / TEAM_ROOT_DIR / TEAMS_SUBDIR


def agents_dir(root: Path) -> Path:
    return root / DIR_AGENTS


def agent_dir(root: Path, agent: str) -> Path:
    """An instance directory: private scratch, artifacts, reports, worklog."""
    return agents_dir(root) / safe_component(pascal(agent))


def roles_dir(root: Path) -> Path:
    return root / DIR_ROLES


def role_dir(root: Path, role: str) -> Path:
    """A role directory: memory and the task list, SHARED by every instance of
    that role. developer-1 and developer-2 share one memory and one queue."""
    return roles_dir(root) / safe_component(pascal(resolve_role(role)))


def global_dir(root: Path) -> Path:
    return root / DIR_GLOBAL


def list_agents(root: Path) -> list:
    """Instance names (developer-1, developer-2, ...)."""
    d = agents_dir(root)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def list_roles(root: Path) -> list:
    """Canonical role slugs that own a shared memory + task queue."""
    d = roles_dir(root)
    if not d.is_dir():
        return []
    return sorted({resolve_role(p.name) for p in d.iterdir() if p.is_dir()})


def instances_of(root: Path, role: str) -> list:
    role = resolve_role(role)
    return [n for n in list_agents(root) if resolve_role(n) == role]


def known_instances(root: Path) -> list:
    return sorted(i for r in list_roles(root) for i in instances_of(root, r))


def team_root_from(path: Path) -> Path:
    """Recover the team root from any generated file inside the team tree.

    Roles/<Role>/X -> root ; Agents/<I>/X -> root ; Global/X -> root ; root/X -> root
    """
    parent = path.parent
    if parent.parent.name in (DIR_ROLES, DIR_AGENTS):
        return parent.parent.parent
    if parent.name == DIR_GLOBAL:
        return parent.parent
    return parent


def _rel(path: Path, target: Path) -> str:
    return os.path.relpath(target, start=path.parent).replace(os.sep, "/")


def link_fields(path: Path, owner: str) -> dict:
    """Relative links that stay correct at any depth in the team tree."""
    root = team_root_from(path)
    role = resolve_role(owner)
    docs = docs_dir(root) if root.parent.name == TEAMS_SUBDIR else root
    return {
        "tasks": _rel(path, role_dir(root, role) / F_TASKS),
        "short": _rel(path, role_dir(root, role) / F_SHORT),
        "long": _rel(path, role_dir(root, role) / F_LONG),
        "mem_archive": _rel(path, role_dir(root, role) / F_MEM_ARCHIVE),
        "role": _rel(path, role_dir(root, role) / F_ROLE),
        "global_mem": _rel(path, global_dir(root) / F_GLOBAL),
        "global_archive": _rel(path, global_dir(root) / F_GLOBAL_ARCHIVE),
        "disputes": _rel(path, root / F_DISPUTES),
        "map": _rel(path, root / F_MAP),
        "project": _rel(path, docs / "Project.md"),
        "plan": _rel(path, docs / "Plan.md"),
        "architecture": _rel(path, docs / "Architecture.md"),
        "decisions": _rel(path, docs / "Decisions.md"),
        "archive": _rel(path, docs / "Archive.md"),
        "board": _rel(path, docs / "Board.md"),
        "worklog": _rel(path, path.parent / F_WORKLOG),
        "inbox": _rel(path, path.parent / F_INBOX),
        "Role": pascal(role),
    }


def criteria_path(root: Path) -> Path:
    return root / F_CRITERIA


def tests_path(root: Path) -> Path:
    return root / F_TESTS


def testplan_path(root: Path) -> Path:
    return root / F_TESTPLAN


def reviews_path(root: Path) -> Path:
    return root / F_REVIEWS


def disputes_path(root: Path) -> Path:
    return root / F_DISPUTES


def skills_path(root: Path) -> Path:
    return root / F_SKILLS


def task_file(root: Path, agent: str) -> Path:
    """The role's shared queue. Any instance of the role may claim from it."""
    role = resolve_role(agent)
    d = role_dir(root, role)
    if not d.is_dir() and not agents_dir(root).is_dir():
        die("no workspace here: run `teamwork.py init` first")
    if agents_dir(root).is_dir() and not d.is_dir():
        known = list_roles(root)
        if role not in known:
            die(
                f"no '{role}' role in this team. Known roles: "
                + (", ".join(known) if known else "(none)")
            )
    d.mkdir(parents=True, exist_ok=True)
    return d / F_TASKS


def skills_dir(root: Path) -> Path:
    """Where team skills are written: the work tree this agent is actually in."""
    return work_repo(root).joinpath(*SKILLS_DIR)


def skill_file(root: Path, rel: str) -> Path:
    """Locate a registered skill file from either the work tree or the project."""
    for base in (work_repo(root), project_of(root)):
        p = base / rel
        if p.exists():
            return p
    return work_repo(root) / rel
