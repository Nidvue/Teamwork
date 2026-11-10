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

Reachability is deliberately measured against ``main`` rather than against HEAD:
the archive is committed on the default branch, so a revision only counts as
merged once it is on that branch.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = REPO_ROOT / "docs" / "Team" / "Archive.md"

MERGE_FIELD = re.compile(r"^- branch / merge: (\S+) / (\S+)$", re.MULTILINE)

#: Placeholders that mean "no revision exists yet", not a revision to resolve.
PENDING = {"pending", "-"}


def filled_fields() -> list[tuple[str, str]]:
    """(branch, revision) for every archive entry that claims a merge revision."""
    text = ARCHIVE.read_text(encoding="utf-8")
    return [(branch, rev) for branch, rev in MERGE_FIELD.findall(text) if rev not in PENDING]


def git(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO_ROOT), *argv], capture_output=True, text=True)


def resolves(rev: str) -> bool:
    return git("cat-file", "-t", rev).returncode == 0


def reachable(rev: str) -> bool:
    return resolves(rev) and git("merge-base", "--is-ancestor", rev, "main").returncode == 0


def test_every_archive_merge_revision_resolves() -> None:
    """A recorded revision must be an object this repository still has."""
    missing = [f"{branch} / {rev}" for branch, rev in filled_fields() if not resolves(rev)]
    assert missing == [], (
        "the archive names merge revisions git cannot resolve, so those claims "
        f"cannot be checked: {missing}"
    )


def test_every_archive_merge_revision_is_on_main() -> None:
    """A merge that landed on the default branch must be reachable from it."""
    unreachable = [f"{branch} / {rev}" for branch, rev in filled_fields() if not reachable(rev)]
    assert unreachable == [], (
        "the archive records these branches as merged, but their revision is not "
        f"an ancestor of main: {unreachable}"
    )


def test_the_archive_still_has_fields_to_check() -> None:
    """Guard the guard: an emptied or renamed field would make this suite empty."""
    fields = filled_fields()
    assert len(fields) >= 20, f"expected many recorded merges, found {len(fields)}"
    assert ARCHIVE.is_file(), f"{ARCHIVE} must exist for these checks to mean anything"


def test_a_bad_revision_would_be_caught() -> None:
    """Prove the checks discriminate, without editing the archive."""
    # a revision this repository does not have (all-zeros is never a commit)
    assert not resolves("0" * 40)
    assert not reachable("0" * 40)
    # a real object that is not on main: the empty tree, or failing that any blob
    empty_tree = git("hash-object", "-t", "tree", "--stdin").stdout.strip()
    if empty_tree and git("merge-base", "--is-ancestor", empty_tree, "main").returncode != 0:
        assert not reachable(empty_tree), "an object off main must not count as merged"


if __name__ == "__main__":  # pragma: no cover - manual run aid
    sys.exit(0 if all(reachable(rev) for _branch, rev in filled_fields()) else 1)
