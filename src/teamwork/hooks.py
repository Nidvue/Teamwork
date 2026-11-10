"""The git hooks that enforce the commit and push rules instead of instructing them.

Middleware control, not instruction: a rule an agent is only *told* about is the
first one skipped under pressure, so the two that must hold on every commit and
every push live in a hook git runs by itself. The hooks are opt-in (``hooks
install``), carry a documented bypass (``TEAMWORK_SKIP_HOOKS``) and never replace
the engine gates, the self-check or the review.

Two locations matter and they are not the same one. The hook *file* lives in the
common git directory (``git rev-parse --git-path hooks``), because inside a linked
worktree ``<toplevel>/.git`` is a 66-byte file and cannot hold a ``hooks/``
directory; the *rules* act on the work tree the commit or push happens in
(``git rev-parse --show-toplevel``). Installing from any lane worktree therefore
installs for every worktree of that repository, which is what the shim's
``root=$(git rev-parse --show-toplevel)`` line is for - do not "fix" it back to
``.git/hooks``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import (
    DEFAULT_BASE,
    HOOK_MARKER,
    HOOK_STAGES,
    IDENTITY_DOMAIN,
    LFS_MAX_BYTES,
)
from .gitutil import current_branch, is_binary_file, lfs_tracked, run_git
from .io import die, write_lf
from .layout import project_path
from .names import resolve_role, role_identity

ZERO_SHA = "0" * 40

ALLOW_MAIN = "TEAMWORK_ALLOW_MAIN"
ALLOW_FORCE = "TEAMWORK_ALLOW_FORCE"


def shim(stage: str) -> str:
    """The POSIX sh hook git runs. Resolves the engine from the work tree root."""
    return (
        "#!/bin/sh\n"
        f"# {HOOK_MARKER} (stage: {stage}) - remove with: teamwork.py hooks uninstall\n"
        "# the hook file lives in the git dir; the rules act on the work tree below\n"
        '[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0\n'
        "root=$(git rev-parse --show-toplevel) || exit 0\n"
        "# -f, not -x: scripts/teamwork.py is committed 100644, so an executable-bit\n"
        "# test would turn every hook into a silent no-op in this repository\n"
        '[ -f "$root/scripts/teamwork.py" ] || exit 0\n'
        f'exec python3 "$root/scripts/teamwork.py" hook {stage} "$@"\n'
    )


def git_root(args) -> Path:
    """The work tree to act on. Every subcommand here needs a repository."""
    here = project_path(args)
    result = run_git(here, "rev-parse", "--show-toplevel")
    if result.returncode != 0 or not result.stdout.strip():
        die(
            "not a git repository: `teamwork.py hooks` writes the hooks git runs, "
            "so it needs a work tree (run `git init` or pass --project <repo>)."
        )
    return Path(result.stdout.strip()).resolve()


def hooks_dir(project: Path) -> Path:
    """``git rev-parse --git-path hooks``, resolved against the project root."""
    result = run_git(project, "rev-parse", "--git-path", "hooks")
    if result.returncode != 0 or not result.stdout.strip():
        die(f"cannot resolve the git hooks directory for {project}: {result.stderr.strip()}")
    located = Path(result.stdout.strip())
    return located if located.is_absolute() else (project / located).resolve()


def is_managed(path: Path) -> bool:
    """True only for a hook this tool wrote: the marker line is the whole proof."""
    try:
        return HOOK_MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def hook_state(path: Path) -> str:
    if not path.exists():
        return "absent"
    return "installed" if is_managed(path) else "foreign"


def install(project: Path, force: bool) -> int:
    target_dir = hooks_dir(project)
    foreign = [
        target_dir / stage
        for stage in HOOK_STAGES
        if hook_state(target_dir / stage) == "foreign" and not force
    ]
    if foreign:
        die(
            "refusing to overwrite "
            + ", ".join(str(path) for path in foreign)
            + f": it was not installed by teamwork (no '{HOOK_MARKER}' line). "
            "Move it aside yourself, or re-run with --force to replace it."
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    for stage in HOOK_STAGES:
        path = target_dir / stage
        write_lf(path, shim(stage))
        path.chmod(0o755)
        print(f"{stage} installed")
    print(f"# hooks directory: {target_dir}")
    return 0


def status(project: Path) -> int:
    target_dir = hooks_dir(project)
    for stage in HOOK_STAGES:
        print(f"{stage} {hook_state(target_dir / stage)}")
    # The directory is part of the answer: in a linked worktree the hooks are not
    # under <toplevel>/.git, so a reader must be able to see where we looked.
    print(f"# hooks directory: {target_dir}")
    return 0


def uninstall(project: Path) -> int:
    target_dir = hooks_dir(project)
    for stage in HOOK_STAGES:
        path = target_dir / stage
        state = hook_state(path)
        if state == "installed":
            path.unlink()
            print(f"{stage} removed")
        elif state == "foreign":
            print(f"{stage} foreign (left alone)")
        else:
            print(f"{stage} absent")
    return 0


def protected_ref() -> str:
    """The one protected remote ref. ``config.DEFAULT_BASE`` is the only literal.

    A legacy ``master`` fallback was tried and dropped: it made the two stages
    disagree (R1 refused only the configured base while P1/P2 also guarded
    ``master``), and Architecture 12.7 freezes one constant for both.
    """
    return f"refs/heads/{DEFAULT_BASE}"


def author_identity(project: Path) -> tuple:
    """The identity a commit would carry: the environment wins, as git does."""
    name = os.environ.get("GIT_AUTHOR_NAME") or _config(project, "user.name")
    email = os.environ.get("GIT_AUTHOR_EMAIL") or _config(project, "user.email")
    return name, email


def _config(project: Path, key: str) -> str:
    return run_git(project, "config", key).stdout.strip()


def is_role_mailbox(project: Path) -> bool:
    """``<Role> <role@IDENTITY_DOMAIN>``: the only identity the team commits under."""
    name, email = author_identity(project)
    local = email.split("@", 1)[0]
    expected_name, expected_email = role_identity(resolve_role(local)) if local else ("", "")
    return bool(email) and email == expected_email and name in ("", expected_name)


def large_staged_files(project: Path) -> list:
    """Staged binary blobs above the LFS threshold with no .gitattributes pattern.

    A large text file is not LFS material: LFS replaces it with a pointer, and the
    diff, the merge and `git show <rev>:<path>` - the operations a record file
    exists for - stop working. Only binaries trip this.
    """
    staged = run_git(project, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    blocked = []
    for rel in staged.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        try:
            size = (project / rel).stat().st_size
        except OSError:
            continue
        if size > LFS_MAX_BYTES and is_binary_file(project / rel) and not lfs_tracked(project, rel):
            blocked.append((rel, size))
    return blocked


def head_branch(project: Path) -> str:
    """The branch name even on an unborn HEAD, where `rev-parse --abbrev-ref` is empty.

    A repository's very first commit has a HEAD pointing at an unresolved ref, so
    the root commit is the one a branch check would otherwise wave through.
    """
    branch = current_branch(project)
    if branch and branch != "HEAD":
        return branch
    symbolic = run_git(project, "symbolic-ref", "--short", "HEAD").stdout.strip()
    return symbolic or branch


def check_commit(project: Path) -> int:
    """R1 default branch, R2 large non-LFS blob, R3 identity (a warning, never a block)."""
    branch = head_branch(project)
    if branch == DEFAULT_BASE and not os.environ.get(ALLOW_MAIN):
        print(
            f"teamwork: refusing to commit on '{DEFAULT_BASE}': it only receives merges "
            "performed by the Reviewer.\n"
            "  teamwork.py branch start --agent <you> --task <T-id>\n"
            f"  (or set {ALLOW_MAIN}=1 deliberately, and say why)",
            file=sys.stderr,
        )
        return 1
    blocked = large_staged_files(project)
    if blocked:
        print(
            "teamwork: refusing to commit large file(s) that no Git LFS pattern covers:\n"
            + "\n".join(f"  {rel} ({size} bytes > {LFS_MAX_BYTES})" for rel, size in blocked)
            + "\n  add the pattern to .gitattributes (teamwork.py repo writes the "
            "standard set) so the blob goes through Git LFS.",
            file=sys.stderr,
        )
        return 1
    if not is_role_mailbox(project):
        name, email = author_identity(project)
        print(
            f"teamwork: warning: commit identity {name or '?'} <{email or '?'}> is not a "
            f"role mailbox (<Role> <role@{IDENTITY_DOMAIN}>). Commits belong to the "
            "acting role, never to a personal identity (AGENTS.md COMMIT IDENTITY); "
            "this is a warning, not a block.",
            file=sys.stderr,
        )
    return 0


def is_ancestor(project: Path, older: str, newer: str) -> bool:
    return run_git(project, "merge-base", "--is-ancestor", older, newer).returncode == 0


def pushed_refspecs() -> list:
    """git's pre-push stdin: ``<local ref> <local sha> <remote ref> <remote sha>``."""
    stream = sys.stdin
    if stream is None:
        return []
    try:
        if stream.isatty():
            return []
        data = stream.read()
    except (OSError, ValueError):  # pragma: no cover - a closed stdin reads as empty
        return []
    return [line.split() for line in data.splitlines() if line.strip()]


def check_push(project: Path, refspecs: list) -> int:
    """P1 no non-fast-forward on the default branch, P2 no deleting it."""
    protected = protected_ref()
    allow_force = bool(os.environ.get(ALLOW_FORCE))
    refusals = []
    for parts in refspecs:
        if len(parts) < 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts[:4]
        if remote_ref != protected:
            continue
        if local_sha == ZERO_SHA:
            refusals.append(
                f"refusing to delete {remote_ref}: deleting the default branch is a red "
                "line (AGENTS.md). Restore it or ask the CEO to authorize the deletion."
            )
            continue
        if (
            remote_sha != ZERO_SHA
            and not allow_force
            and not is_ancestor(project, remote_sha, local_sha)
        ):
            refusals.append(
                f"refusing a non-fast-forward update of {remote_ref}: {remote_sha[:12]} is "
                f"not an ancestor of {local_sha[:12]}. Force-pushing published history is "
                "a red line that needs the CEO's explicit authorization (AGENTS.md).\n"
                f"  (or set {ALLOW_FORCE}=1 deliberately, and say why)"
            )
    if not refusals:
        return 0
    print("\n".join(f"teamwork: {reason}" for reason in refusals), file=sys.stderr)
    return 1


def cmd_hooks(args) -> int:
    project = git_root(args)
    if args.hooks_cmd == "install":
        return install(project, args.force)
    if args.hooks_cmd == "status":
        return status(project)
    return uninstall(project)


def cmd_hook(args) -> int:
    project = git_root(args)
    if args.hook_cmd == "pre-commit":
        return check_commit(project)
    return check_push(project, pushed_refspecs())


def add_parsers(sub, common) -> None:
    """Register the ``hooks`` (operator) and ``hook`` (shim) command groups."""
    group = sub.add_parser(
        "hooks",
        parents=[common],
        help="install/inspect/remove the git hooks that enforce the commit and push rules",
    )
    hsub = group.add_subparsers(dest="hooks_cmd", required=True)

    parser = hsub.add_parser(
        "install", parents=[common], help="write the pre-commit and pre-push hooks"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace a hook this tool did not install (it has no marker line)",
    )
    parser.set_defaults(func=cmd_hooks)

    parser = hsub.add_parser(
        "status", parents=[common], help="each stage: installed, absent or foreign"
    )
    parser.set_defaults(func=cmd_hooks)

    parser = hsub.add_parser(
        "uninstall", parents=[common], help="remove only the hooks this tool installed"
    )
    parser.set_defaults(func=cmd_hooks)

    group = sub.add_parser(
        "hook",
        parents=[common],
        help="shim entry points git calls; not an operator command",
    )
    ksub = group.add_subparsers(dest="hook_cmd", required=True)

    parser = ksub.add_parser(
        "pre-commit", parents=[common], help="git pre-commit: default branch + large blob"
    )
    parser.set_defaults(func=cmd_hook)

    parser = ksub.add_parser(
        "pre-push", parents=[common], help="git pre-push: no force-update of the default branch"
    )
    parser.add_argument("remote", help="the remote name git passes")
    parser.add_argument("url", help="the remote URL git passes")
    parser.set_defaults(func=cmd_hook)
