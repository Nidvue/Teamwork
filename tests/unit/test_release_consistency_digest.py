"""Digest and tokenizer fixtures for the release gate (T-0005, round 3).

The rules and the payload digest are frozen by
[Architecture](../../../docs/Team/Architecture.md) section 11. These tests
prove two things the per-rule suite does not:

* the 11.3 digest is a **function of the commit** - the working tree
  contributes no byte, so a link into ``.git`` can neither move the digest nor
  put a remote URL carrying a token into the printed output, and the two
  digest paths (``rev=None`` and ``rev=HEAD``) cannot disagree;
* the R8 tokenizer still reads a script out of an **inline-code** command,
  which is how the real documentation writes its install lines.

Every fixture is a synthetic repository built in ``tmp_path``; no test opens a
socket and no test reads this repository's own tree.

Owner: developer. Task: T-0005.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

_SCRIPTS_ADDED = str(SCRIPTS) not in sys.path
if _SCRIPTS_ADDED:
    sys.path.insert(0, str(SCRIPTS))

import check_release_consistency as crc  # noqa: E402  (import after sys.path setup)

if _SCRIPTS_ADDED:
    sys.path.remove(str(SCRIPTS))

GIT_OPTIONS = (
    "-c",
    "user.email=developer@agents.nidvue.com",
    "-c",
    "user.name=Developer",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "tag.gpgSign=false",
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(root: Path) -> Path:
    """A committed fixture with the payload of 11.3 and nothing else."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    write(root, "SKILL.md", "# skill\n")
    write(root, "AGENTS.md", "# agents\n")
    write(root, "roles/real.md", "# real\n")
    write(root, "references/keep.md", "# keep\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def digests(root: Path) -> tuple[str, str]:
    """``(rev=None, rev="HEAD")`` - the two paths that must agree."""
    return crc.payload_digest(root, None), crc.payload_digest(root, "HEAD")


def both_refuse(root: Path) -> list[str]:
    """The refusal message of each path, so both can be asserted on."""
    messages = []
    for rev in (None, "HEAD"):
        with pytest.raises(crc.InputError) as caught:
            crc.payload_digest(root, rev)
        messages.append(str(caught.value))
    return messages


# --------------------------------------------------------------------------- #
# 11.3 - the digest is a function of the commit
# --------------------------------------------------------------------------- #


def test_the_two_digest_paths_agree_on_a_clean_tree(tmp_path):
    root = make_repo(tmp_path / "repo")

    working, head = digests(root)

    assert working == head
    assert len(working) == 16


def test_an_edited_working_tree_does_not_move_the_digest(tmp_path):
    """The working tree contributes no byte: the digest is the commit's."""
    root = make_repo(tmp_path / "repo")
    before = crc.payload_digest(root, None)

    write(root, "roles/real.md", "# edited on disk\n")
    after = crc.payload_digest(root, None)

    assert before == after


def test_editing_git_config_does_not_move_the_digest(tmp_path):
    """A link into ``.git`` must not make git internals part of the digest."""
    root = make_repo(tmp_path / "repo")
    before = crc.payload_digest(root, None)

    config = root / ".git" / "config"
    config.write_text(
        config.read_text(encoding="utf-8") + '[remote "x"]\n\turl = https://token@example/y\n',
        encoding="utf-8",
    )
    after = crc.payload_digest(root, None)

    assert before == after


def test_a_link_to_a_gitignored_file_is_refused_on_both_paths(tmp_path):
    """The target is not in the commit, so neither path can resolve it."""
    root = make_repo(tmp_path / "repo")
    write(root, ".gitignore", "gen.bin\n")
    write(root, "gen.bin", "SECRET-GITIGNORED-BYTES\n")
    (root / "references" / "l").symlink_to("../gen.bin")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link to a gitignored file")

    for message in both_refuse(root):
        assert "references/l" in message
        assert "SECRET" not in message


def test_a_link_to_a_tracked_but_gitignored_file_resolves_and_is_stable(tmp_path):
    """The target is in the commit: both paths agree, and an edit moves nothing."""
    root = make_repo(tmp_path / "repo")
    write(root, ".gitignore", "references/keep.md\n")
    write(root, "references/keep.md", "# keep\n")
    # ``-f``: the path is gitignored, but it is *in the commit* - that is the
    # point of the fixture.
    git(root, "add", "-f", "references/keep.md")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "track a gitignored target")
    (root / "references" / "l").symlink_to("keep.md")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link to the gitignored target")

    working, head = digests(root)
    assert working == head

    write(root, "references/keep.md", "# GITIGNORED-BYTES-CHANGED\n")
    assert digests(root) == (working, head)


def test_a_link_into_the_git_directory_is_refused_on_both_paths(tmp_path):
    """``../.git/config`` must never be read, and never named in the output."""
    root = make_repo(tmp_path / "repo")
    (root / "references" / "l").symlink_to("../.git/config")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link to .git/config")

    for message in both_refuse(root):
        assert "references/l" in message
        assert "config" not in message
        assert "git directory" in message


def test_a_link_out_of_the_tree_is_refused_on_both_paths(tmp_path):
    """A relative target above the tree is refused, and named as such."""
    root = make_repo(tmp_path / "repo")
    # The file exists and is readable, so only the refusal can stop it.
    (tmp_path / "outside.md").write_text("# outside\n", encoding="utf-8")
    (root / "references" / "l").symlink_to("../../outside.md")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link out of the tree")

    for message in both_refuse(root):
        assert "references/l" in message
        assert "outside the tree" in message


def test_a_link_into_the_git_directory_never_reaches_the_digest(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "references" / "l").symlink_to("../.git/config")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link to .git/config")

    for rev in (None, "HEAD"):
        with pytest.raises(crc.InputError):
            crc.payload_digest(root, rev)


def test_an_in_commit_link_resolves_on_both_paths(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "references" / "l").symlink_to("keep.md")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "link to a committed file")

    working, head = digests(root)

    assert working == head
    assert len(working) == 16


def test_an_absolute_link_is_refused_on_both_paths(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "references" / "l").symlink_to("/etc/hostname")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "absolute link")

    for message in both_refuse(root):
        assert "references/l" in message
        assert "absolute path" in message


def test_a_broken_cyclic_or_self_link_is_refused_on_both_paths(tmp_path):
    root = make_repo(tmp_path / "repo")
    (root / "references" / "broken").symlink_to("nowhere.md")
    (root / "references" / "self").symlink_to("self")
    (root / "references" / "cyc1").symlink_to("cyc2")
    (root / "references" / "cyc2").symlink_to("cyc1")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "broken, cyclic and self links")

    for message in both_refuse(root):
        assert "references/broken" in message
        assert "references/self" in message


# --------------------------------------------------------------------------- #
# R8 - the script is read out of an inline-code command
# --------------------------------------------------------------------------- #


def test_an_inline_code_install_line_names_the_script():
    claims = crc._channel_claims("`uvx --from teamwork-agents wrongscript`")

    assert claims == [("teamwork-agents", "wrongscript")]


def test_an_inline_code_pipx_line_names_the_script():
    claims = crc._channel_claims("`pipx run --spec teamwork-agents wrongscript`")

    assert claims == [("teamwork-agents", "wrongscript")]


def test_a_flag_value_pair_before_the_script_does_not_hide_it():
    claims = crc._channel_claims("uvx --from teamwork-agents --python 3.12 wrongscript --version")

    assert claims == [("teamwork-agents", "wrongscript")]


def test_prose_after_the_distribution_names_no_script():
    claims = crc._channel_claims("uvx --from teamwork-agents is the fastest way to try it")

    assert claims == [("teamwork-agents", None)]


def test_r8_reports_an_inline_code_install_line(tmp_path):
    """End to end: the rule fires on a README line written in inline code."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    write(
        root,
        "pyproject.toml",
        '[project]\nname = "teamwork-agents"\n\n[project.scripts]\nteamwork = "teamwork.cli:main"\n',
    )
    write(root, "src/teamwork/version.py", '__version__ = "1.1.0"\nDIST_NAME = "teamwork-agents"\n')
    write(root, "README.md", "# Teamwork\n\nRun `uvx --from teamwork-agents wrongscript`.\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "readme with an inline-code install line")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "wrongscript" in result.detail
