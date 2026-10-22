"""The skill bundle as a movable set of files, and the mirror that keeps a copy fresh.

The repository root *is* the skill, but an agent host loads a **copy** from its
skills directory, and a `pi`/pip install unpacks another copy. Those copies are
what an agent actually reads, so they must be replaceable byte for byte: a stale
copy is a live defect (a renamed engine module that lingers shadows the new one,
an old ``SKILL.md`` describes a command that no longer exists).

One manifest lives here - :data:`BUNDLE_FILES` and :data:`BUNDLE_TREES` - and
everything that copies the bundle uses it: the wheel build, the pi package build,
``scripts/sync_skill.py`` and ``teamwork.py refresh``. Two copies of the list
would drift, and the drift would be invisible until a shipped file went missing.
"""

from __future__ import annotations

import filecmp
import os
import shutil
from pathlib import Path

#: Files the skill needs at runtime, at the bundle root.
BUNDLE_FILES = ("SKILL.md", "AGENTS.md")

#: Trees the skill needs at runtime. Tests, docs and build output stay out.
BUNDLE_TREES = ("references", "roles", "templates", "scripts", "src")

#: Where a host scans skills from. Only a default - any directory works.
HOST_DEFAULTS = {
    "pi": Path("~/.pi/agent/skills/teamwork"),
    "agents": Path("~/.agents/skills/teamwork"),
}

_SKIP_SUFFIXES = (".pyc", ".pyo")


def _skip(path: Path) -> bool:
    if "__pycache__" in path.parts or any(p.endswith(".egg-info") for p in path.parts):
        return True
    return path.suffix in _SKIP_SUFFIXES


def bundle_files(source: Path) -> list[Path]:
    """Every file the bundle needs, relative to ``source``."""
    found: list[Path] = [Path(name) for name in BUNDLE_FILES if (source / name).is_file()]
    for tree in BUNDLE_TREES:
        base = source / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or _skip(path.relative_to(source)):
                continue
            found.append(path.relative_to(source))
    return found


def installed_files(dest: Path) -> list[Path]:
    """Every file currently in ``dest``, relative to it."""
    if not dest.is_dir():
        return []
    return [
        path.relative_to(dest)
        for path in sorted(dest.rglob("*"))
        if path.is_file() and not _skip(path.relative_to(dest))
    ]


def managed(rel: Path) -> bool:
    """Is ``rel`` a path the mirror owns? Unmanaged files are never deleted.

    Only the bundle trees are pruned. A file the host or the operator put in the
    skills directory (a note, a README, a local override) is left alone: a sync
    that deletes what it did not write is a data-loss bug, not a convenience.
    """
    return bool(rel.parts) and rel.parts[0] in BUNDLE_TREES


def plan(source: Path, dest: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """``(added, updated, removed)`` - what mirroring ``source`` into ``dest`` does."""
    wanted = bundle_files(source)
    have = set(installed_files(dest))
    added, updated = [], []
    for rel in wanted:
        if rel not in have:
            added.append(rel)
        elif not filecmp.cmp(source / rel, dest / rel, shallow=False):
            updated.append(rel)
    removed = sorted(rel for rel in have - set(wanted) if managed(rel))
    return added, updated, removed


def sync(source: Path, dest: Path, *, dry_run: bool, quiet: bool = False) -> int:
    """Mirror ``source`` into ``dest``. Returns the number of files touched."""
    added, updated, removed = plan(source, dest)
    touched = len(added) + len(updated) + len(removed)
    if not quiet:
        for rel in added:
            print(f"  + {rel}")
        for rel in updated:
            print(f"  ~ {rel}")
        for rel in removed:
            print(f"  - {rel}")
    if dry_run:
        return touched
    dest.mkdir(parents=True, exist_ok=True)
    for rel in added + updated:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    for rel in removed:
        (dest / rel).unlink()
    # A stale __pycache__ would keep importing a module the source dropped.
    for path in sorted(dest.rglob("__pycache__"), reverse=True):
        shutil.rmtree(path, ignore_errors=True)
    for directory in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not quiet:
        print(f"# {len(added)} added, {len(updated)} updated, {len(removed)} removed -> {dest}")
    return touched


def resolve_dest(host: str = "pi", dest: str = "") -> Path:
    """The skills directory to write: ``--dest`` first, else the host default."""
    target = Path(dest).expanduser() if dest else HOST_DEFAULTS.get(host, HOST_DEFAULTS["pi"])
    target = target.expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    return target


def is_checkout(path: Path) -> bool:
    """Is ``path`` a git checkout of the skill (so it can be fetched and pulled)?"""
    return (path / ".git").exists() and (path / "src" / "teamwork").is_dir()


def default_mirror_path(dest: Path) -> Path:
    """Where a tool-managed mirror checkout of the skill lives for ``dest``.

    Next to the skills directory, hidden, so it is obvious that no operator owns
    it: ``refresh`` fetches into it and mirrors into ``dest``.
    """
    parent = dest.parent
    if parent.name == "skills":
        parent = parent.parent
    return parent / ".teamwork-source"


def env_source() -> str:
    return os.environ.get("TEAMWORK_SOURCE", "")
