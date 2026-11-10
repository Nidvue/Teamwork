"""Every merge revision the archive names must exist and be reachable from main.

The archive is the accepted-results record: an entry says which branch merged and
at which revision. That revision is the one thing a reader uses to check the claim
later, so a ``- branch / merge:`` line that names a revision git cannot resolve -
or one that never landed on the default branch - makes the record unverifiable in
exactly the way the whole ledger exists to prevent.

The failure that motivated this test was real: a history rewrite re-cut eleven
merged commits and two of them were dropped entirely, while the archive kept
naming the pre-rewrite shas. ``git cat-file`` answered ``fatal: Not a valid object
name`` for two entries and ``merge-base --is-ancestor`` failed for nine more, and
nothing in the suite noticed because the archive is never parsed for its shas.

Reachability is deliberately measured against the default branch rather than
against HEAD: the archive is committed on the default branch, so a revision only
counts as merged once it is on that branch.

The default branch is resolved, not assumed. A push build has a local ``main``; a
``pull_request`` build is detached at the merge ref and has only ``origin/main``,
so hard-coding ``main`` made every archived revision look unreachable on a PR -
sixty false failures, and a guard that is red on every contribution measures
nothing. What is asserted is the ref that was actually used, so an unmeasurable
checkout fails with its reason instead of passing quietly.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = REPO_ROOT / "docs" / "Team" / "Archive.md"

MERGE_FIELD = re.compile(r"^- branch / merge: (\S+) / (\S+)$", re.MULTILINE)

#: Placeholders that mean "no revision exists yet", not a revision to resolve.
PENDING = {"pending", "-"}


def filled_fields() -> list[tuple[str, str]]:
    """(branch, revision) for every archive entry that claims a merge revision."""
    text = ARCHIVE.read_text(encoding="utf-8")
    return [(branch, rev) for branch, rev in MERGE_FIELD.findall(text) if rev not in PENDING]


def git(*argv: str, root: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True)


def resolves(rev: str, root: Path = REPO_ROOT) -> bool:
    return git("cat-file", "-t", rev, root=root).returncode == 0


def shallow(root: Path = REPO_ROOT) -> bool:
    """A shallow clone cannot answer these questions, and saying so beats a red."""
    return git("rev-parse", "--is-shallow-repository", root=root).stdout.strip() == "true"


#: The default branch as a checkout can expose it, in the order it is preferred:
#: a local branch on a push build, the remote-tracking one on a pull_request build.
DEFAULT_BRANCH_REFS = ("refs/heads/main", "refs/remotes/origin/main")


def default_branch_ref(root: Path = REPO_ROOT) -> str:
    """The ref reachability is measured against: resolved, never assumed.

    Reading ``main`` alone is what made this guard report sixty unreachable
    revisions on the repository's first ``pull_request`` build - a detached
    checkout has ``origin/main`` and no local branch, so ``git merge-base
    --is-ancestor`` failed for every entry and the archive looked rewritten.
    """
    for ref in DEFAULT_BRANCH_REFS:
        if git("rev-parse", "--verify", "--quiet", ref, root=root).returncode == 0:
            return ref
    raise AssertionError(
        "cannot resolve the default branch (neither "
        + " nor ".join(DEFAULT_BRANCH_REFS)
        + f" exists in {root}), so archive reachability is UNVERIFIED"
    )


def reachable(rev: str, root: Path = REPO_ROOT) -> bool:
    if not resolves(rev, root):
        return False
    return (
        git("merge-base", "--is-ancestor", rev, default_branch_ref(root), root=root).returncode == 0
    )


def test_every_archive_merge_revision_resolves() -> None:
    """A recorded revision must be an object this repository still has."""
    if shallow():
        pytest.skip("shallow clone: the recorded revisions are truncated away, not missing")
    missing = [f"{branch} / {rev}" for branch, rev in filled_fields() if not resolves(rev)]
    assert missing == [], (
        "the archive names merge revisions git cannot resolve, so those claims "
        f"cannot be checked: {missing}"
    )


def test_every_archive_merge_revision_is_on_main() -> None:
    """A merge that landed on the default branch must be reachable from it."""
    if shallow():
        pytest.skip("shallow clone: ancestry is not walkable, fetch the full history")
    base = default_branch_ref()
    unreachable = [f"{branch} / {rev}" for branch, rev in filled_fields() if not reachable(rev)]
    assert unreachable == [], (
        "the archive records these branches as merged, but their revision is not "
        f"an ancestor of {base}: {unreachable}"
    )


def test_the_default_branch_is_resolved_in_a_pull_request_checkout(tmp_path: Path) -> None:
    """A detached ``pull_request`` checkout has ``origin/main`` and no local ``main``.

    Measured on the repository's own first ``pull_request`` build: with ``main``
    hard-coded, ``merge-base --is-ancestor`` failed for all sixty archived
    revisions and the guard reported the archive as rewritten. This pins the ref
    resolution rather than trusting the shape of whatever checkout runs it.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    # ``-b trunk`` on purpose: a checkout that has a local ``main`` would not
    # exercise the shape this test exists for.
    for argv in (
        ("init", "-q", "-b", "trunk", "."),
        # A CI runner has no configured identity: a bare ``commit`` fails there
        # with "Please tell me who you are", so the role mailbox is passed in.
        (
            "-c",
            "user.name=Tester",
            "-c",
            "user.email=tester@agents.nidvue.com",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "only commit",
        ),
    ):
        done = git(*argv, root=repo)
        assert done.returncode == 0, done.stderr
    head = git("rev-parse", "HEAD", root=repo).stdout.strip()
    # The pull_request shape: the commit is on the remote-tracking branch only.
    assert git("update-ref", "refs/remotes/origin/main", head, root=repo).returncode == 0
    assert git("rev-parse", "--verify", "--quiet", "refs/heads/main", root=repo).returncode != 0
    assert default_branch_ref(repo) == "refs/remotes/origin/main"
    assert reachable(head, repo)


def test_an_unresolvable_default_branch_fails_instead_of_passing(tmp_path: Path) -> None:
    """Silence is the failure mode this guard exists to close, so state it."""
    repo = tmp_path / "empty"
    repo.mkdir()
    assert git("init", "-q", "-b", "trunk", ".", root=repo).returncode == 0
    with pytest.raises(AssertionError, match="UNVERIFIED"):
        default_branch_ref(repo)


def test_the_archive_still_has_fields_to_check() -> None:
    """Guard the guard: an emptied or renamed field would make this suite empty."""
    fields = filled_fields()
    assert len(fields) >= 20, f"expected many recorded merges, found {len(fields)}"
    assert ARCHIVE.is_file(), f"{ARCHIVE} must exist for these checks to mean anything"


def test_a_bad_revision_would_be_caught() -> None:
    """Prove the checks discriminate, without editing the archive."""
    if shallow():
        pytest.skip("shallow clone: the discriminating probes need real objects")
    # a revision this repository does not have (all-zeros is never a commit)
    assert not resolves("0" * 40)
    assert not reachable("0" * 40)
    # a real object that is not on main: the empty tree, or failing that any blob
    empty_tree = git("hash-object", "-t", "tree", "--stdin").stdout.strip()
    if empty_tree and git("merge-base", "--is-ancestor", empty_tree, "main").returncode != 0:
        assert not reachable(empty_tree), "an object off main must not count as merged"


if __name__ == "__main__":  # pragma: no cover - manual run aid
    sys.exit(0 if all(reachable(rev) for _branch, rev in filled_fields()) else 1)
