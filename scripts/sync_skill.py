#!/usr/bin/env python3
"""Mirror this checkout's skill bundle into an installed skill directory.

Why: the repository root *is* the skill, but an agent host loads a **copy** from
its skills directory (``~/.pi/agent/skills/teamwork`` on pi, or whatever the host
names). That copy is what every agent actually reads, so the moment the source
tree changes the installed copy is stale: the host reads an old ``SKILL.md``, and
an engine file the tree needs (``config.py``, ``gitutil.py``) is simply absent,
so a shipped behaviour appears broken on the machine that ships it.

``sync`` copies the bundle, deletes files the source no longer has (a renamed
module must not linger and shadow the new one), and reports every change.
``--check`` writes nothing and exits ``1`` when the installed copy differs, which
is the shape a CI job or a pre-release gate needs.

Usage::

    python3 scripts/sync_skill.py                      # sync into the pi user dir
    python3 scripts/sync_skill.py --dest DIR           # any host's skills dir
    python3 scripts/sync_skill.py --check              # verify only, non-zero on drift
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One source of truth for what a skill bundle contains: the pi package build
# imports the same names, so the tarball and an installed copy can never drift.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pi_package import SKILL_FILES, SKILL_TREES  # noqa: E402

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.egg-info")

#: Where each host scans skills from. Only a default - any directory works.
HOST_DEFAULTS = {
    "pi": Path("~/.pi/agent/skills/teamwork"),
    "agents": Path("~/.agents/skills/teamwork"),
}


def bundle_files(source: Path) -> list[Path]:
    """Every file the skill bundle needs, relative to ``source``."""
    found: list[Path] = [Path(name) for name in SKILL_FILES if (source / name).is_file()]
    for tree in SKILL_TREES:
        base = source / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.suffix in (".pyc", ".pyo"):
                continue
            if "__pycache__" in path.parts or any(p.endswith(".egg-info") for p in path.parts):
                continue
            found.append(path.relative_to(source))
    return found


def installed_files(dest: Path) -> list[Path]:
    """Every file currently in the destination, relative to it."""
    if not dest.is_dir():
        return []
    return [
        path.relative_to(dest)
        for path in sorted(dest.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in (".pyc", ".pyo")
    ]


def managed(rel: Path) -> bool:
    """Is ``rel`` a path this script owns? Unmanaged files are never deleted.

    Only the bundle trees are pruned. A file the host or the operator put in the
    skills directory (a note, a README, a local override) is left alone: a sync
    that deletes what it did not write is a data-loss bug, not a convenience.
    """
    return bool(rel.parts) and rel.parts[0] in SKILL_TREES


def plan(source: Path, dest: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """``(added, updated, removed)`` - what syncing ``source`` into ``dest`` does."""
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
    added, updated, removed = plan(source, dest)
    if not quiet:
        for rel in added:
            print(f"  + {rel}")
        for rel in updated:
            print(f"  ~ {rel}")
        for rel in removed:
            print(f"  - {rel}")
    if dry_run:
        return 0 if not (added or updated or removed) else 1
    dest.mkdir(parents=True, exist_ok=True)
    for rel in added + updated:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    for rel in removed:
        (dest / rel).unlink()
    for path in sorted(dest.rglob("__pycache__"), reverse=True):
        shutil.rmtree(path, ignore_errors=True)
    for directory in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not quiet:
        print(f"# {len(added)} added, {len(updated)} updated, {len(removed)} removed -> {dest}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sync_skill.py",
        description="mirror this checkout's skill bundle into an installed skills directory",
    )
    parser.add_argument(
        "--dest",
        default="",
        help=f"skills directory to write ({', '.join(str(p) for p in HOST_DEFAULTS.values())})",
    )
    parser.add_argument(
        "--host",
        default="pi",
        choices=sorted(HOST_DEFAULTS),
        help="which host's default skills directory to use when --dest is omitted",
    )
    parser.add_argument(
        "--source",
        default="",
        help="checkout to mirror (default: this script's repository root)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 when the installed copy differs from the checkout",
    )
    args = parser.parse_args(argv)

    source = Path(args.source).resolve() if args.source else ROOT
    dest = Path(args.dest or HOST_DEFAULTS[args.host]).expanduser()
    if not dest.is_absolute():
        dest = (Path.cwd() / dest).resolve()
    added, updated, removed = plan(source, dest)
    if args.check:
        if not dest.is_dir():
            print(f"sync_skill: {dest} does not exist (nothing installed there)", file=sys.stderr)
            return 1
        if added or updated or removed:
            print(
                f"sync_skill: {dest} is out of sync with {source}: "
                f"{len(added)} missing, {len(updated)} stale, {len(removed)} to delete",
                file=sys.stderr,
            )
            for rel in added:
                print(f"  missing: {rel}", file=sys.stderr)
            for rel in updated:
                print(f"  stale:   {rel}", file=sys.stderr)
            for rel in removed:
                print(f"  extra:   {rel}", file=sys.stderr)
            return 1
        if os.environ.get("SYNC_SKILL_QUIET") != "1":
            print(f"# {dest} is in sync with {source}")
        return 0
    return sync(source, dest, dry_run=False)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
