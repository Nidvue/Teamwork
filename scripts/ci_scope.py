"""Classify a CI change set as code, prose-only, or undetermined.

The `scope` job of `.github/workflows/ci.yml` runs this module, and
:func:`prose_paths` is the single source that `.github/workflows/docs.yml`
triggers on - that workflow's `paths:` list is a literal copy, because a GitHub
path filter cannot call a script, and it is pinned to this tuple by
tests/unit/test_ci_scope.py. A push is the only cost-optimised event: a pull
request and a manual run report `code=true`, a tag push reports neither, and a
change set that cannot be established reports `code=true` so an unknown change
set never skips the matrix.

Every change set is measured with `git diff --no-renames`, so a rename is a
delete plus an add and a shipping path can never hide behind a move into prose.
The CLI prints `code=` and `prose=` on stdout and appends them to the file named
by `--output` (GitHub's `$GITHUB_OUTPUT`); with no flags it reads `EVENT_NAME`,
`REF_NAME`, `BEFORE_SHA`, `HEAD_SHA`, `DEFAULT_BRANCH` and `GITHUB_OUTPUT` from
the environment, which is what the `scope` step exports. `--file` classifies an
explicit path list instead of asking git, so the same answers can be checked
without a repository.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PROSE_PATHS = (
    "docs/**",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CITATION.cff",
    "LICENSE",
    "AGENTS.md",
    "assets/**",
    "mkdocs.yml",
)
PROSE_DIRECTORIES = tuple(path[: -len("**")] for path in PROSE_PATHS if path.endswith("/**"))
PROSE_FILES = tuple(path for path in PROSE_PATHS if not path.endswith("/**"))
DEFAULT_BRANCH = "main"


@dataclass(frozen=True)
class Scope:
    """One classification: the two gate answers, the files seen and the reason."""

    code: bool
    prose: bool
    files: tuple[str, ...] | None = None
    reason: str = ""
    undetermined: bool = False


def prose_paths() -> tuple[str, ...]:
    """The prose/media set, as the globs `docs.yml` must trigger on."""
    return PROSE_PATHS


def is_prose(path: str) -> bool:
    """True when `path` belongs to the prose/media set."""
    return path.startswith(PROSE_DIRECTORIES) or path in PROSE_FILES


def classify_files(files: Sequence[str]) -> Scope:
    """Classify one measured change set, path by path."""
    paths = tuple(path for path in files if path)
    if not paths:
        return Scope(code=False, prose=False, files=paths, reason="empty change set")
    if all(is_prose(path) for path in paths):
        return Scope(code=False, prose=True, files=paths, reason="prose-only change set")
    return Scope(code=True, prose=False, files=paths, reason="shipping change set")


def _git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _resolves(repo: Path, revision: str) -> bool:
    if not revision:
        return False
    return _git(repo, "rev-parse", "--verify", "-q", f"{revision}^{{commit}}") is not None


def _diff_paths(repo: Path, before: str, head: str) -> tuple[str, ...] | None:
    output = _git(repo, "diff", "--no-renames", "--name-only", before, head)
    if output is None:
        return None
    return tuple(line for line in output.splitlines() if line)


def _root_paths(repo: Path, head: str) -> tuple[str, ...] | None:
    output = _git(
        repo, "diff-tree", "--root", "--no-renames", "--no-commit-id", "--name-only", "-r", head
    )
    if output is None:
        return None
    return tuple(line for line in output.splitlines() if line)


def _change_set(
    repo: Path, before: str, head: str, default_branch: str
) -> tuple[tuple[str, ...] | None, str]:
    if _resolves(repo, before):
        paths = _diff_paths(repo, before, head)
        if paths is not None:
            return paths, "before..head"

    base = ""
    candidates = (f"origin/{default_branch}" if default_branch else "", "origin/HEAD")
    for candidate in candidates:
        if not candidate or not _resolves(repo, candidate):
            continue
        merge_base = _git(repo, "merge-base", head, candidate)
        if merge_base:
            base = merge_base
            break

    if base and base != head:
        paths = _diff_paths(repo, base, head)
        if paths:
            return paths, "merge-base..head"
        return None, "empty change set from the merge base"

    if not _resolves(repo, f"{head}^"):
        paths = _root_paths(repo, head)
        if paths:
            return paths, "root commit"
        return None, "empty root commit"

    return None, "pre-push state unavailable"


def classify(
    *,
    event: str = "push",
    ref: str = "",
    before: str = "",
    head: str = "",
    default_branch: str = DEFAULT_BRANCH,
    files: Sequence[str] | None = None,
    repo: Path = Path("."),
) -> Scope:
    """Classify one CI event, from an explicit file list or from git."""
    if event != "push":
        return Scope(code=True, prose=False, reason=f"{event} runs every job")
    if ref.startswith("refs/tags/"):
        return Scope(code=False, prose=False, reason="tag push runs the tag-sensitive jobs only")
    if files is not None:
        return classify_files(files)

    resolved_head = head or (_git(repo, "rev-parse", "HEAD") or "")
    if not resolved_head:
        return Scope(code=True, prose=False, reason="no head revision", undetermined=True)

    paths, reason = _change_set(repo, before, resolved_head, default_branch)
    if paths is None:
        return Scope(code=True, prose=False, reason=reason, undetermined=True)

    scope = classify_files(paths)
    return Scope(
        code=scope.code,
        prose=scope.prose,
        files=scope.files,
        reason=f"{reason}: {scope.reason}",
    )


def _boolean(value: bool) -> str:
    return "true" if value else "false"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify a CI change set and print code=/prose= for the job guards."
    )
    parser.add_argument("--event", default=os.environ.get("EVENT_NAME", "push"))
    parser.add_argument("--ref", default=os.environ.get("REF_NAME", ""))
    parser.add_argument("--before", default=os.environ.get("BEFORE_SHA", ""))
    parser.add_argument("--head", default=os.environ.get("HEAD_SHA", ""))
    parser.add_argument(
        "--default-branch", default=os.environ.get("DEFAULT_BRANCH", DEFAULT_BRANCH)
    )
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        metavar="PATH",
        help="classify this explicit path (repeatable); git is not consulted",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("GITHUB_OUTPUT", ""),
        metavar="PATH",
        help="append code= and prose= to this step output file",
    )
    parser.add_argument("--repo", default=".", metavar="PATH")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    scope = classify(
        event=args.event,
        ref=args.ref,
        before=args.before,
        head=args.head,
        default_branch=args.default_branch,
        files=args.files,
        repo=Path(args.repo),
    )
    if scope.files:
        print(f"scope: changed -> {' '.join(scope.files)}")
    print(f"scope: {scope.reason}")
    lines = f"code={_boolean(scope.code)}\nprose={_boolean(scope.prose)}\n"
    sys.stdout.write(lines)
    if args.output:
        with Path(args.output).open("a", encoding="utf-8", newline="\n") as sink:
            sink.write(lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
