"""``teamwork refresh`` must accept a tag pin, not only a branch pin (T-0019).

Why: `docs/guide/install.md` promised "Pin a tag (`--branch v1.1.2`)" and the
update path could not honour it. ``_fetch_source`` fetched the name and then
resolved ``<remote>/<branch>``, a ref that only exists for a *branch*: measured
on a bare clone of this repository, ``git fetch --quiet origin v1.1.2`` returns 0
while ``git rev-parse origin/v1.1.2`` says ``fatal: Needed a single revision``.
A first ``git clone --branch <tag>`` works (git accepts a tag there), so the
promise held exactly once and every later refresh died with
``no origin/v1.1.2 after fetch``.

These tests are the contract: a branch pin still fast-forwards, a tag pin
resolves to the tag commit and survives a second refresh, an unknown name fails
with a message instead of a traceback, and a dirty checkout is still never
clobbered. They use real git in ``tmp_path`` - no network, no mocks - because
the defect is in how git stores a fetched tag, which a mock would hide.

Owner: developer. Task: T-0019.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import engine

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Developer",
    "GIT_AUTHOR_EMAIL": "developer@agents.nidvue.com",
    "GIT_COMMITTER_NAME": "Developer",
    "GIT_COMMITTER_EMAIL": "developer@agents.nidvue.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(path: Path, *argv: str) -> str:
    """Run git with a hermetic environment; fail loudly when it refuses."""
    done = subprocess.run(
        ["git", "-C", str(path), *argv],
        capture_output=True,
        text=True,
        env={**GIT_ENV, "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    assert done.returncode == 0, (argv, done.stderr)
    return done.stdout.strip()


def commit(path: Path, message: str) -> str:
    (path / "SKILL.md").write_text(f"# {message}\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", message)
    return git(path, "rev-parse", "HEAD")


@pytest.fixture()
def remote(tmp_path: Path) -> Path:
    """A bare ``origin`` carrying ``main``, a tag v1.1.2 and a newer tag v1.2.0."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    git(bare, "init", "--bare", "-q", "-b", "main")
    author = tmp_path / "author"
    author.mkdir()
    git(author, "init", "-q", "-b", "main")
    commit(author, "one")
    git(author, "tag", "v1.1.2")
    commit(author, "two")
    git(author, "tag", "-a", "v1.2.0", "-m", "release 1.2.0")
    git(author, "remote", "add", "origin", str(bare))
    git(author, "push", "-q", "--tags", "origin", "main")
    return bare


@pytest.fixture()
def checkout(tmp_path: Path, remote: Path) -> Path:
    """A clone of ``remote`` on ``main``, the state ``refresh`` normally meets."""
    path = tmp_path / "checkout"
    git(tmp_path, "clone", "-q", str(remote), str(path))
    return path


def test_a_branch_pin_still_resolves_and_fast_forwards(remote: Path, checkout: Path) -> None:
    """The pre-existing behaviour, pinned: ``--branch main`` moves with ``origin``."""
    ok, detail, kind, commit_sha = engine._fetch_source(checkout, "origin", "main")
    assert ok, detail
    assert kind == "branch"
    assert commit_sha == git(checkout, "rev-parse", "refs/remotes/origin/main")
    assert detail == git(checkout, "rev-parse", "--short", "refs/remotes/origin/main")

    peer = checkout.parent / "peer"
    git(checkout.parent, "clone", "-q", str(remote), str(peer))
    newer = commit(peer, "three")
    git(peer, "push", "-q", "origin", "main")

    ok, detail = engine._update_source(checkout, "origin", "main")
    assert ok, detail
    assert "->" in detail
    assert git(checkout, "rev-parse", "HEAD") == newer


def test_a_tag_pin_resolves_to_the_tag_commit_and_survives_a_second_refresh(
    remote: Path, checkout: Path
) -> None:
    """The defect: a tag fetch fills FETCH_HEAD, never ``origin/<tag>``.

    Reproduced on this repository: ``git fetch origin v1.1.2`` returns 0 and
    ``git rev-parse --short origin/v1.1.2`` fails, so ``refresh`` printed
    ``no origin/v1.1.2 after fetch`` and exited 1 - the second refresh always
    died. Now the pin resolves to the tag commit and says it is a tag.
    """
    ok, detail, kind, commit_sha = engine._fetch_source(checkout, "origin", "v1.1.2")
    assert ok, detail
    assert kind == "tag"
    assert commit_sha == git(checkout, "rev-parse", "refs/tags/v1.1.2^{commit}")
    assert "tag v1.1.2" in detail, detail

    # The update path, twice: a refresh that only works once is the old defect.
    ok, first = engine._update_source(checkout, "origin", "v1.1.2")
    assert ok, first
    assert "pinned to tag v1.1.2" in first, first
    assert git(checkout, "rev-parse", "HEAD") == commit_sha
    ok, second = engine._update_source(checkout, "origin", "v1.1.2")
    assert ok, second
    assert "tag v1.1.2" in second, second
    assert git(checkout, "rev-parse", "HEAD") == commit_sha
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD", "a tag pin is detached"


def test_a_tag_pin_moves_a_detached_mirror_onto_a_newer_tag(remote: Path, checkout: Path) -> None:
    """A tag pin is detached and read-only; naming a newer tag must still work."""
    assert engine._update_source(checkout, "origin", "v1.1.2")[0]
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD", "a pin detaches"
    ok, detail = engine._update_source(checkout, "origin", "v1.2.0")
    assert ok, detail
    assert "tag v1.2.0" in detail, detail
    assert git(checkout, "rev-parse", "HEAD") == git(
        checkout, "rev-parse", "refs/tags/v1.2.0^{commit}"
    )


def test_a_branch_pin_after_a_tag_pin_re_attaches_to_the_branch(
    remote: Path, checkout: Path
) -> None:
    """Leaving a tag pin must land on the branch, not move a detached HEAD.

    ``--branch v1.1.2`` detaches the checkout. A later ``--branch main`` that only
    ran ``merge --ff-only`` would advance the detached HEAD while ``refs/heads/main``
    stayed behind, so the next refresh would move the same commits again and the
    checkout would be on no branch at all. Re-attaching first is the fix.
    """
    assert engine._update_source(checkout, "origin", "v1.1.2")[0]
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"

    ok, detail = engine._update_source(checkout, "origin", "main")

    assert ok, detail
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "main", detail
    assert git(checkout, "rev-parse", "HEAD") == git(
        checkout, "rev-parse", "refs/remotes/origin/main"
    )
    assert engine._update_source(checkout, "origin", "main")[0]
    assert git(checkout, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_a_tag_that_does_not_exist_fails_with_a_message_not_a_traceback(
    remote: Path, checkout: Path
) -> None:
    ok, detail, kind, commit_sha = engine._fetch_source(checkout, "origin", "v9.9.9")
    assert not ok
    assert kind == "" and commit_sha == ""
    assert "v9.9.9" in detail and "no branch or tag" in detail, detail
    assert engine._update_source(checkout, "origin", "v9.9.9") == (False, detail)


def test_a_dirty_checkout_is_never_clobbered_by_a_tag_pin(remote: Path, checkout: Path) -> None:
    """Uncommitted work belongs to the operator: mirror it, never move HEAD."""
    (checkout / "SKILL.md").write_text("# uncommitted\n", encoding="utf-8")
    head = git(checkout, "rev-parse", "HEAD")

    ok, detail = engine._update_source(checkout, "origin", "v1.2.0")

    assert ok, detail
    assert "mirroring this checkout as it stands" in detail, detail
    assert (checkout / "SKILL.md").read_text(encoding="utf-8") == "# uncommitted\n"
    assert git(checkout, "rev-parse", "HEAD") == head, "a dirty tree is never reset or detached"
    assert git(checkout, "status", "--porcelain").strip() == "M SKILL.md"
