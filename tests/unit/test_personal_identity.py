"""No personal identity may exist in this repository, in a display or in the bytes.

The operator's own name and address were published on 21 commits before the
role-mailbox rule took effect, and an allowlist entry accepted them instead of
removing them. A `.mailmap` hid the display, but a map that names the pair is itself
a copy of it, so the requirement is stronger than a map: the raw author and
committer fields, the commit bodies and every tracked file must carry only a role
mailbox. The rewrite is what makes that true; this module is what keeps it true.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_RE_ROLE_MAILBOX = re.compile(r"^[^<>]+ <[a-z][a-z0-9-]*@agents\.nidvue\.com>$")
_RE_PERSONAL = re.compile(r"@(?!agents\.nidvue\.com)[a-z0-9.-]+\.[a-z]{2,}$")
_PERSONAL_WORDS = ("<redacted-personal-name>", "ping.zhao", "operatorhao")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _raw(field: str) -> set[str]:
    """``%an``/``%ae`` and friends: the bytes, with no mailmap applied."""
    return {line.strip() for line in _git("log", "--all", f"--format=%{field}").splitlines()}


def test_no_raw_author_or_committer_is_a_personal_identity() -> None:
    for field in ("an", "ae", "cn", "ce"):
        for identity in _raw(field):
            assert not _RE_PERSONAL.search(identity), (
                f"%{field} still stores a personal address: {identity}"
            )
            assert not any(word in identity.lower() for word in _PERSONAL_WORDS), (
                f"%{field} still stores a personal name: {identity}"
            )


def test_every_author_and_committer_is_a_role_mailbox() -> None:
    for field in ("an <%ae>", "cn <%ce>"):
        for identity in _raw(field):
            assert _RE_ROLE_MAILBOX.match(identity), (
                f"identity is not a role mailbox: {identity}. `teamwork.py commit` "
                "builds the role identity; a commit made by hand inherits the ambient one."
            )


def test_no_commit_message_names_a_person() -> None:
    bodies = _git("log", "--all", "--format=%B").lower()
    for word in _PERSONAL_WORDS:
        assert word not in bodies, f"a commit message still names a person: {word}"


def test_no_tracked_file_names_a_person() -> None:
    tracked = _git("ls-files").split()
    offenders = []
    for rel in tracked:
        try:
            text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(word in text for word in _PERSONAL_WORDS):
            offenders.append(rel)
    assert offenders == [], f"tracked files name a person: {offenders}"
