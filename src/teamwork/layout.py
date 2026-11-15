"""Workspace layout: the team tree, committed docs and their links."""

from __future__ import annotations

import os
from pathlib import Path

from .config import (
    CONTEXT_MEMORY_FILES,
    DIR_AGENTS,
    DIR_DOCS,
    DIR_GLOBAL,
    DIR_RETIRED,
    DIR_ROLES,
    DIR_RUNTIME,
    DIR_WORKTREES,
    F_CRITERIA,
    F_DISPUTES,
    F_GLOBAL,
    F_GLOBAL_ARCHIVE,
    F_INBOX,
    F_KNOWLEDGE,
    F_LESSONS,
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


def team_root_or_die(root: Path) -> Path:
    """Validate that ``root`` is deep enough to name a project, once, in one message.

    ``TEAMWORK_ROOT`` is a documented override and is taken verbatim, so a value
    one level too shallow reached ``root.parents[3]`` and raised ``IndexError: 3``
    - the engine's one-line ``die()`` replaced by a traceback whose message was an
    integer. Only the depth ``project_of`` needs is asserted: callers other than
    the CLI (the engine's own tests, the archive path) hand in bare team
    directories that are not laid out under ``.pi/Teamwork``.
    """
    if len(root.parents) < 4:
        die(
            "TEAMWORK_ROOT must point at <project>/.pi/Teamwork/Teams/<Team> "
            f"(got {root}, which is {len(root.parents) + 1} level(s) deep)"
        )
    return root


def project_of(root: Path) -> Path:
    """<project>/.pi/Teamwork/Teams/<Team> -> <project>."""
    return team_root_or_die(root).parents[3]


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
            if parent == wt_root:
                break
            try:
                parent.relative_to(wt_root)
            except ValueError:
                continue
            if (parent / ".git").exists():
                return parent
    return project_of(root)


def work_docs_dir(root: Path, cwd: Path | None = None) -> Path:
    """Committed project output in the work tree this command acts on.

    ``docs_dir`` always points at the project that owns the team tree; a lane
    that runs inside its own worktree must land its output there instead, so
    the file can be committed on the lane's branch.
    """
    return work_repo(root, cwd).joinpath(*DIR_DOCS)


def _inside(base: Path, path: Path) -> bool:
    """A computed node never escapes the directory it was enumerated from."""
    try:
        path.resolve().relative_to(base.resolve())
    except (OSError, ValueError):
        return False
    return True


def context_docs_dir(root: Path, cwd: Path | None = None) -> Path:
    """The committed documentation root: every ``docs/**/*.md``, not only Team."""
    return work_repo(root, cwd) / "docs"


def context_doc_files(root: Path, cwd: Path | None = None) -> list:
    """Every committed ``docs/**/*.md`` in the work tree, path-sorted."""
    base = context_docs_dir(root, cwd)
    if not base.is_dir():
        return []
    return sorted(path for path in base.rglob("*.md") if path.is_file() and _inside(base, path))


def context_skill_files(root: Path, cwd: Path | None = None) -> list:
    """Every ``.agents/skills/<name>/SKILL.md`` in the work tree, name-sorted.

    Enumerated from disk, not from the ``Skills.md`` registry: a prefix lint
    finding must stay visible in the view instead of being hidden by the
    registry (Architecture.md 16.1).
    """
    base = work_repo(root, cwd).joinpath(*SKILLS_DIR)
    if not base.is_dir():
        return []
    return sorted(
        path for path in base.glob("*/SKILL.md") if path.is_file() and _inside(base, path)
    )


def memory_layer_path(root: Path, agent: str, layer: str) -> Path:
    """``Roles/<Role>/{ShortTermMemory,LongTermMemory,ArchivedMemory}.md``."""
    filename = CONTEXT_MEMORY_FILES.get(layer)
    if filename is None:
        raise ValueError(f"unknown memory layer '{layer}'")
    return role_dir(root, agent) / filename


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
    """The current team's hidden tree: <project>/.pi/Teamwork/Teams/<Team>/.

    **Explicit beats ambient.** ``--project`` names the tree to act on and wins over
    ``TEAMWORK_ROOT``; the environment variable is the lane's own binding, so it
    applies only when the caller named no project. A lane exports
    ``TEAMWORK_ROOT``, and before this rule a repro that passed ``--project`` at a
    scratch tree still wrote into the live queue - six tasks landed in the team's
    developer queue twice (L-0047/L-0048). The project flag is the isolation
    boundary, so it is the one that decides.
    """
    if getattr(args, "project", None):
        project = project_path(args)
        slug = team_slug(project, getattr(args, "team", "") or "")
        return (project / TEAM_ROOT_DIR / TEAMS_SUBDIR / slug).resolve()
    if os.environ.get("TEAMWORK_ROOT"):
        return Path(os.environ["TEAMWORK_ROOT"]).expanduser().resolve()
    found = team_root_from_cwd(Path.cwd().resolve())
    if found is not None:
        return found
    project = project_path(args)
    slug = team_slug(project, getattr(args, "team", "") or "")
    return (project / TEAM_ROOT_DIR / TEAMS_SUBDIR / slug).resolve()


def agents_dir(root: Path) -> Path:
    return root / DIR_AGENTS


def agent_dir(root: Path, agent: str) -> Path:
    """An instance directory: private scratch, artifacts, reports, worklog."""
    return agents_dir(root) / safe_component(pascal(agent))


def shown_path(path: Path | str) -> str:
    """A path as the packet and the memory pointer print it: forward slashes.

    The packet is read by an agent that types the path into a POSIX shell even on
    Windows, and a pointer is compared as text, so one form on every host (T-0120).
    """
    return os.fspath(path).replace("\\", "/")


def roles_dir(root: Path) -> Path:
    return root / DIR_ROLES


def role_dir(root: Path, role: str) -> Path:
    """A role directory: memory and the task list, SHARED by every instance of
    that role. developer-1 and developer-2 share one memory and one queue."""
    return roles_dir(root) / safe_component(pascal(resolve_role(role)))


def global_dir(root: Path) -> Path:
    return root / DIR_GLOBAL


def retired_dir(root: Path) -> Path:
    """Where a retired instance directory is moved, never deleted.

    The lane's ``Artifacts/``, ``Reports/`` and ``WorkLog.md`` are evidence the
    ledger and Archive may still cite, so retirement preserves the whole
    directory under ``Runtime/Retired/<Instance>/``.
    """
    return root / DIR_RUNTIME / DIR_RETIRED


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


F_ATTENTION = "Attention.md"


def attention_path(root: Path) -> Path:
    return root / F_ATTENTION


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


def lessons_path(root: Path, agent: str) -> Path:
    """The role's shared lesson record. A missing file reads as no lessons."""
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
    return d / F_LESSONS


def knowledge_path(root: Path) -> Path:
    """The project-wide knowledge store at the team root.

    Team-local working state, shared by every role: it sits next to
    ``Criteria.md`` and ``Tests.md`` under ``.pi/`` and is never committed. A
    missing file reads as an empty store (Architecture.md 15).
    """
    return root / F_KNOWLEDGE


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
