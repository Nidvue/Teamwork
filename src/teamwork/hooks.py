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

Three properties are contract, because a guard nobody can install - or one that
quietly stops running - is worse than no guard at all (security audit F-6):

* **Per stage.** ``pre-commit`` (R1, the rule that keeps commits off the default
  branch) is installed even when ``pre-push`` already belongs to someone else.
  ``git lfs install`` owns ``pre-push`` in a fresh clone, and an all-or-nothing
  installer refused BOTH stages because of it.
* **A foreign hook is chained, not dropped.** A hook this tool did not write is
  preserved as ``<stage>.teamwork-foreign`` and run by the teamwork shim after the
  rules pass, so the LFS hook keeps working and so does the branch guard.
* **Fail closed.** The shim exits 1 with a message when it cannot resolve the work
  tree or when the engine file is missing. It used to exit 0 in both cases, which
  silently disabled every rule while ``hooks status`` still reported ``installed``.

The guard is **local only**: ``git commit --no-verify``, ``git push --no-verify``
and a ``core.hooksPath`` pointing elsewhere all skip these files, and a clone that
never ran ``hooks install`` has none of them. The forge-side rule (branch
protection / ruleset) is what covers those paths; the hook is the cheap in-loop
half of the same rule, never the whole control.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import (
    DEFAULT_BASE,
    F_LEDGER,
    HOOK_MARKER,
    HOOK_STAGES,
    IDENTITY_DOMAIN,
    LFS_MAX_BYTES,
    TEAM_ROOT_DIR,
    TEAMS_SUBDIR,
)
from .gitutil import (
    HooksDirUnresolved,
    current_branch,
    is_binary_bytes,
    is_binary_content,
    lfs_text_mismatch,
    lfs_tracked,
    run_git,
    staged_blob_meta,
)
from .gitutil import hooks_dir as resolved_hooks_dir
from .io import die, write_lf
from .layout import project_path
from .names import resolve_role, role_identity

ZERO_SHA = "0" * 40

ALLOW_MAIN = "TEAMWORK_ALLOW_MAIN"
ALLOW_FORCE = "TEAMWORK_ALLOW_FORCE"

#: Where a foreign hook is preserved before the teamwork shim takes its place:
#: ``pre-push`` -> ``pre-push.teamwork-foreign``. One suffix derived from the stage
#: name, so ``install``, ``status`` and ``uninstall`` cannot disagree about it.
CHAIN_SUFFIX = ".teamwork-foreign"

#: The interpreter the shim runs the engine with. A hook is a machine-local file
#: (nothing is committed), so an absolute path would be safe; ``python3`` stays the
#: documented spelling here and T-0030 owns the interpreter-resolution question.
SHIM_INTERPRETER = "python3"


def chained_hook(path: Path) -> Path:
    """The preserved foreign hook that the stage at ``path`` chains, or would chain."""
    return path.parent / f"{path.name}{CHAIN_SUFFIX}"


#: The head of every shim: the marker line, the bypass, and the two fail-closed
#: guards. Literal shell with ``@MARKER@``/``@STAGE@`` as the only substitutions, so
#: the frozen body in ``docs/Team/Architecture.md`` section 12.6 can be read beside
#: this text. Two constructs here are contract, not style:
#:
#: * ``[ -n "${TEAMWORK_SKIP_HOOKS:-}" ]`` - the ``:-`` keeps the expansion total,
#:   so an inherited ``set -u`` cannot turn the bypass into a blocker;
#: * the two ``exit 1`` blocks - a guard that cannot run must refuse loudly. The
#:   previous ``|| exit 0`` disabled every rule when the engine file was renamed
#:   or the checkout was broken, while ``hooks status`` still said ``installed``.
SHIM_HEAD = """\
#!/bin/sh
# @MARKER@ (stage: @STAGE@) - remove with: teamwork.py hooks uninstall
# the hook file lives in the git dir; the rules act on the work tree below
# local only: `--no-verify` and a core.hooksPath pointing elsewhere skip this
# file, and a clone that never ran `hooks install` has none of it - the
# forge-side rule covers those, so this hook is never the whole control.
[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0
root=$(git rev-parse --show-toplevel)
if [ -z "$root" ]; then
  echo "teamwork: @STAGE@ hook: cannot resolve the work tree root (git rev-parse --show-toplevel failed); refusing rather than skipping the guard. Bypass deliberately with TEAMWORK_SKIP_HOOKS=1." >&2
  exit 1
fi
# -f, not -x: scripts/teamwork.py is committed 100644, so an executable-bit
# test would turn every hook into a silent no-op in this repository
if [ ! -f "$root/scripts/teamwork.py" ]; then
  echo "teamwork: @STAGE@ hook: $root/scripts/teamwork.py is missing, so the rules cannot run; refusing rather than failing open. Restore the file, run 'teamwork.py hooks uninstall', or bypass deliberately with TEAMWORK_SKIP_HOOKS=1." >&2
  exit 1
fi
"""

#: The tail of a normal shim: the engine replaces the shell, so git reads its exit
#: code directly.
SHIM_EXEC = 'exec @INTERP@ "$root/scripts/teamwork.py" hook @STAGE@ "$@"\n'

#: The ``pre-push`` preamble for a chained stage. git hands the refspec list to the
#: hook on stdin and BOTH hooks need it, so it is copied once and each hook is fed
#: from the copy; a pipe would give the list to whichever hook read first.
SHIM_REFSPECS = """\
# git hands pre-push the refspec list on stdin and BOTH hooks need it: copy it
# once, then feed each hook from the copy
refspecs=$(mktemp "${TMPDIR:-/tmp}/teamwork-@STAGE@.XXXXXX") || {
  echo "teamwork: @STAGE@ hook: cannot create a temporary file for git's refspec list; refusing rather than starving the chained hook." >&2
  exit 1
}
trap 'rm -f "$refspecs"' 0
cat > "$refspecs"
@INTERP@ "$root/scripts/teamwork.py" hook @STAGE@ "$@" < "$refspecs"
"""

#: The tail of a chained shim: the rules first, then the preserved foreign hook.
#: The preserved file is named beside this one and found through this file's own
#: directory, which is the hooks directory whatever path git used to reach it.
SHIM_CHAIN = """\
# this stage had a foreign hook when teamwork installed over it: it is kept
# beside this file as @STAGE@@SUFFIX@ and runs after the rules pass
hook_dir=$(cd "$(dirname "$0")" && pwd) || exit 1
chained="$hook_dir/@STAGE@@SUFFIX@"
if [ ! -f "$chained" ]; then
  echo "teamwork: @STAGE@ hook: the preserved @STAGE@@SUFFIX@ it was installed to chain is gone; refusing rather than silently dropping that hook. Re-run 'teamwork.py hooks install', or remove this hook with 'teamwork.py hooks uninstall'." >&2
  exit 1
fi
@BEFORE@# a refusal from the rules stops here: the chained hook must not run for a
# commit or push that already failed
status=$?
if [ "$status" -ne 0 ]; then exit "$status"; fi
@AFTER@status=$?
exit "$status"
"""


def shim(stage: str, chain: bool = False) -> str:
    """The POSIX sh hook git runs. Resolves the engine from the work tree root.

    Both guards exit **non-zero** on purpose. ``git rev-parse --show-toplevel``
    failing and ``scripts/teamwork.py`` being absent both mean the rules cannot
    run; exiting 0 there made a renamed engine or a broken checkout disable every
    rule silently while ``hooks status`` still reported ``installed`` (security
    audit F-6). A guard that cannot run must say so and refuse, and
    ``TEAMWORK_SKIP_HOOKS`` stays the one documented escape.

    ``chain=True`` writes the variant for a stage whose foreign hook was preserved
    as ``<stage>.teamwork-foreign``: the rules run first and the preserved hook
    runs after them with the same arguments - and, on ``pre-push``, with the same
    stdin, which is why git's refspec list is copied through a temporary file
    rather than piped to a hook that would starve the other one.
    """
    head = SHIM_HEAD.replace("@MARKER@", HOOK_MARKER).replace("@STAGE@", stage)
    if not chain:
        tail = SHIM_EXEC
        return head + tail.replace("@INTERP@", SHIM_INTERPRETER).replace("@STAGE@", stage)
    if stage == "pre-push":
        before = SHIM_REFSPECS.replace("@INTERP@", SHIM_INTERPRETER).replace("@STAGE@", stage)
        after = '"$chained" "$@" < "$refspecs"\n'
    else:
        before = f'{SHIM_INTERPRETER} "$root/scripts/teamwork.py" hook {stage} "$@"\n'
        after = '"$chained" "$@"\n'
    tail = SHIM_CHAIN.replace("@SUFFIX@", CHAIN_SUFFIX).replace("@STAGE@", stage)
    return head + tail.replace("@BEFORE@", before).replace("@AFTER@", after)


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
    """The installer's hooks directory: resolved, and loud when git cannot answer.

    Delegates to :func:`teamwork.gitutil.hooks_dir`, the single implementation of
    this contract; the harness reads the same function and turns its failure into
    a reported absence. The installer writes into the directory, so a failure here
    must stop the run - with the message it has always printed.
    """
    try:
        return resolved_hooks_dir(project)
    except HooksDirUnresolved as exc:
        die(str(exc))


def is_managed(path: Path) -> bool:
    """True only for a hook this tool wrote: the marker line is the whole proof."""
    try:
        return HOOK_MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def hook_state(path: Path) -> str:
    """``installed`` (a hook this tool wrote), ``foreign`` (anyone else's), ``absent``."""
    if not path.exists():
        return "absent"
    return "installed" if is_managed(path) else "foreign"


def shim_chains(path: Path) -> bool:
    """True only when the installed shim actually runs a preserved foreign hook.

    The preserved file's existence is not the answer: ``--force`` writes a plain
    shim on purpose, and ``hooks status`` must not claim a chain that does not run.
    The body is the proof, exactly as it is for ``is_managed``.
    """
    if hook_state(path) != "installed":
        return False
    try:
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return f"{path.name}{CHAIN_SUFFIX}" in body


def write_shim(path: Path, stage: str, chain: bool) -> None:
    """One stage's shim, mode 0755 and LF endings; the only place a hook is written."""
    write_lf(path, shim(stage, chain))
    path.chmod(0o755)


def keep_executable(path: Path) -> None:
    """A preserved hook git could not execute would turn the chain into a refusal."""
    if not os.access(path, os.X_OK):
        path.chmod(path.stat().st_mode | 0o111)


def record_force(project: Path, stages: list, reason: str) -> None:
    """Record *why* a foreign hook was replaced, when this project has a team ledger.

    ``hooks install`` runs in any repository git can answer for, so it may not
    create a team tree of its own: the line is appended only where the project
    already carries one, and a missing or unwritable ledger never costs the
    operator the install.
    """
    teams = project / TEAM_ROOT_DIR / TEAMS_SUBDIR
    if not teams.is_dir():
        return
    candidates = sorted(teams.glob(f"*/{F_LEDGER}"))
    if len(candidates) != 1:
        return
    from .engine import ledger_append

    try:
        ledger_append(
            candidates[0].parent,
            "hooks.install",
            actor=_config(project, "user.name"),
            target=", ".join(stages),
            detail=f"replaced a foreign hook with --force; reason: {reason}",
        )
    except (OSError, SystemExit):  # pragma: no cover - the install must not die here
        return


def install(project: Path, force: bool, reason: str = "") -> int:
    """Install **each** stage on its own; a foreign hook is chained, never dropped.

    All-or-nothing was the defect (security audit F-6): one foreign ``pre-push``
    (``git lfs install`` writes one in every fresh clone) made ``install`` refuse
    ``pre-commit`` as well, so R1 - the rule that keeps commits off the default
    branch - could not be installed without ``--force`` deleting the LFS hook.
    Now every stage lands unless that specific stage is blocked, a foreign hook is
    moved aside to ``<stage>.teamwork-foreign`` and run after the rules pass, and a
    stage that could not be installed makes the run exit 1 while the others stay.
    """
    target_dir = hooks_dir(project)
    foreign = [stage for stage in HOOK_STAGES if hook_state(target_dir / stage) == "foreign"]
    if force and foreign and not reason.strip():
        die(
            "--force replaces a hook this tool did not install ("
            + ", ".join(foreign)
            + "), so say why: --force --reason '<why>'. The reason is recorded, and a "
            "replacement without one is the kind of quiet overwrite this refusal exists "
            "to prevent."
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    replaced: list = []
    chained: list = []
    blocked: list = []
    for stage in HOOK_STAGES:
        path = target_dir / stage
        preserved = chained_hook(path)
        state = hook_state(path)
        if state == "foreign":
            if force:
                write_shim(path, stage, chain=False)
                replaced.append(stage)
                print(f"{stage} replaced (--force); the hook that was there is gone")
                continue
            if preserved.exists():
                blocked.append(stage)
                print(
                    f"teamwork: {stage}: a foreign hook and a preserved "
                    f"{preserved.name} are both in the way; resolve one of them, or "
                    "re-run with --force --reason '<why>'",
                    file=sys.stderr,
                )
                continue
            path.replace(preserved)
            keep_executable(preserved)
            chained.append(stage)
        write_shim(path, stage, chain=preserved.exists())
        if preserved.exists():
            print(f"{stage} installed (chained: {preserved.name})")
        else:
            print(f"{stage} installed")
    if replaced:
        record_force(project, replaced, reason.strip())
    print(f"# hooks directory: {target_dir}")
    if chained:
        print(
            "# chained: "
            + ", ".join(f"{stage}{CHAIN_SUFFIX}" for stage in chained)
            + " runs after the rules pass"
        )
    return 1 if blocked else 0


def status(project: Path) -> int:
    target_dir = hooks_dir(project)
    for stage in HOOK_STAGES:
        path = target_dir / stage
        line = f"{stage} {hook_state(path)}"
        if shim_chains(path):
            line += f" (chained: {chained_hook(path).name})"
        print(line)
    # The directory is part of the answer: in a linked worktree the hooks are not
    # under <toplevel>/.git, so a reader must be able to see where we looked.
    print(f"# hooks directory: {target_dir}")
    return 0


def uninstall(project: Path) -> int:
    """Remove only marked hooks, and hand a chained foreign hook back its stage.

    Deleting the teamwork hook while leaving ``<stage>.teamwork-foreign`` behind
    would silently switch the LFS hook off for good, so the preserved hook is
    restored to its own name. A foreign hook this tool never touched is left alone
    and said so.
    """
    target_dir = hooks_dir(project)
    for stage in HOOK_STAGES:
        path = target_dir / stage
        preserved = chained_hook(path)
        state = hook_state(path)
        if state == "installed":
            path.unlink()
            print(f"{stage} removed")
        elif state == "foreign":
            print(f"{stage} foreign (left alone)")
            continue
        else:
            print(f"{stage} absent")
        if preserved.exists():
            preserved.replace(path)
            print(f"{stage} previous hook restored from {preserved.name}")
    return 0


def protected_ref() -> str:
    """The one protected remote ref. ``config.DEFAULT_BASE`` is the only literal.

    A legacy ``master`` fallback was tried and dropped: it made the two stages
    disagree (R1 refused only the configured base while P1/P2 also guarded
    ``master``), and Architecture 11.7 freezes one constant for both.
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


def staged_verdict(project: Path, rel: str) -> tuple:
    """``(size, is_binary)`` for what the commit would record, or ``(None, False)``.

    ``git diff --cached`` names an INDEX path, so R2 must measure the index: a
    blob staged large and then shrunk in the work tree still commits the large
    blob, and text staged then overwritten with binary bytes still commits text.
    The work-tree file is read only when the index has no entry for the path - the
    deletion case, where there is nothing to commit and nothing to refuse.
    """
    staged = staged_blob_meta(project, rel)
    if staged is not None:
        size, head = staged
        return size, is_binary_bytes(head)
    path = project / rel
    try:
        return path.stat().st_size, is_binary_content(path)
    except OSError:
        return None, False


def large_staged_files(project: Path) -> list:
    """Staged BINARY blobs above the LFS threshold that no pattern covers.

    The threshold is a binary threshold (Architecture 11.10): a text record is a
    document, so it is never refused however large it grows. The binary test is
    the shared `gitutil.is_binary_bytes`, the same one `commit --check-lfs` and
    the audit ask, so the three gates cannot disagree about a file.
    """
    staged = run_git(project, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    blocked = []
    for rel in staged.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        size, binary = staged_verdict(project, rel)
        if size is None:
            continue
        if size > LFS_MAX_BYTES and binary and not lfs_tracked(project, rel):
            blocked.append((rel, size))
    return blocked


def text_files_routed_into_lfs(project: Path) -> list:
    """Staged TEXT files that a .gitattributes pattern would push into LFS.

    `.gitattributes` routes a file into LFS BY NAME, so a text file can be
    routed there by accident - and a document in LFS is a pointer for every
    reader without an LFS client. The check is size-independent, because a text
    file in LFS is broken at any size (Architecture 11.10).

    This is the one check that reads the WORKING copy rather than the index, and
    deliberately: with the `lfs` filter installed, staging a pattern-matched file
    stores a POINTER in the index, so the index cannot say whether the content the
    pointer replaced was text. The content decides, and only the work tree still
    has it.
    """
    staged = run_git(project, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    mismatched = []
    for rel in staged.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        if lfs_text_mismatch(project, rel):
            mismatched.append(rel)
    return mismatched


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
    mismatched = text_files_routed_into_lfs(project)
    if mismatched:
        print(
            "teamwork: refusing to commit text file(s) that .gitattributes routes "
            "into Git LFS:\n"
            + "\n".join(f"  {rel}" for rel in mismatched)
            + "\n  this file is text but a LFS pattern captures its name; LFS is for "
            "binaries, and a document in LFS is unreadable without a client.\n"
            "  drop the pattern from .gitattributes, or make the content binary.",
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
        return install(project, args.force, args.reason)
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
        help="replace a hook this tool did not install (it has no marker line) instead of "
        "preserving and chaining it",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="why a foreign hook is replaced; required with --force when one is present, "
        "and recorded in the team ledger when this project has one",
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
