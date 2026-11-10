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
is the shape a CI job or a pre-release gate needs. ``teamwork.py refresh`` uses
the same mirror and additionally fetches the remote first, so an installed skill
can follow ``main`` without a manual checkout.

Usage::

    python3 scripts/sync_skill.py                      # sync into the pi user dir
    python3 scripts/sync_skill.py --dest DIR           # any host's skills dir
    python3 scripts/sync_skill.py --check              # verify only, non-zero on drift
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One source of truth for what a skill bundle contains: the engine module that
# also serves ``teamwork.py refresh`` and the pi package build.
sys.path.insert(0, str(ROOT / "src"))
from teamwork import bundle  # noqa: E402

BUNDLE_FILES = bundle.BUNDLE_FILES
BUNDLE_TREES = bundle.BUNDLE_TREES
HOST_DEFAULTS = bundle.HOST_DEFAULTS
bundle_files = bundle.bundle_files
installed_files = bundle.installed_files
managed = bundle.managed
plan = bundle.plan


def sync(source: Path, dest: Path, *, dry_run: bool, quiet: bool = False) -> int:
    """Mirror ``source`` into ``dest``; ``0`` when the copy is in sync afterwards."""
    bundle.sync(source, dest, dry_run=dry_run, quiet=quiet)
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
    dest = bundle.resolve_dest(args.host, args.dest)
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
        print(f"# {dest} is in sync with {source}")
        return 0
    bundle.sync(source, dest, dry_run=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
