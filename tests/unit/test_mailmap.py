"""No personal identity may be *displayed* by a git surface.

Twenty-one commits were published before the role-mailbox rule took effect, and one
of them carries the operator's own name and address. Published history is protected
and rewriting it is a red line, so the bytes stay in the objects - but nothing a
reader, a forge or `git shortlog` shows may carry them. `.mailmap` is the standard,
non-destructive map for exactly that, and this module is what keeps it complete: a
new commit that is neither a role mailbox nor mapped here fails the suite.

`git log` honours the map only with `log.mailmap` set (or `--use-mailmap`), so the
test asks git for the mapped form explicitly rather than trusting the local config.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAILMAP = ROOT / ".mailmap"

_RE_ROLE_MAILBOX = re.compile(r"^[^<>]+ <[a-z][a-z0-9-]*@agents\.nidvue\.com>$")
_RE_PERSONAL = re.compile(r"@(?!agents\.nidvue\.com)[a-z0-9.-]+\.[a-z]{2,}$")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _identities(field: str) -> set[str]:
    """Every ``Name <email>`` git reports for ``field``, mapped through .mailmap."""
    out = _git("log", "--all", "--use-mailmap", f"--format=%{field}")
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_the_map_exists_and_is_read_by_git() -> None:
    assert MAILMAP.is_file(), "a .mailmap is how a published commit is displayed as a role"
    assert "CEO" in MAILMAP.read_text(encoding="utf-8")


def test_no_author_or_committer_displays_a_personal_address() -> None:
    """The mapped view is what a reader, a forge and a release note show."""
    for field in ("aN", "aE", "cN", "cE"):
        for identity in _identities(field):
            assert not _RE_PERSONAL.search(identity), (
                f"{field} still displays a personal address: {identity}. Either author "
                "the commit as the role mailbox, or map it in .mailmap."
            )


def test_every_author_is_a_role_mailbox() -> None:
    for identity in _identities("aN <%aE>"):
        assert _RE_ROLE_MAILBOX.match(identity), (
            f"author is not a role mailbox: {identity}. `teamwork.py commit` builds the "
            "role identity; a commit made by hand inherits the ambient one."
        )
