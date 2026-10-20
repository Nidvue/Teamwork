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


# --------------------------------------------------------------------------- #
# 11.2.2 - the frozen contract: R2's tag set, R9's pattern, the shallow guard
# --------------------------------------------------------------------------- #

#: The contract's frozen pattern (Architecture.md 11.2.4), byte for byte.
CONTRACT_TAGGED_TOKEN = (
    r"(?:(?<![\w./-])v"
    r"|(?<![\w./-])(?:--(?:branch|tag|ref)[\s=]+|git\s+(?:checkout|switch)\s+"
    r"|releases/tag/|compare/)v?)"
    r"(\d+\.\d+\.\d+)(?![-/\w])(?!\.\w)"
)


def cgit(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def cwrite(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def cversion(root: Path, version: str) -> None:
    cwrite(
        root,
        "src/teamwork/version.py",
        f'__version__ = "{version}"\nDIST_NAME = "teamwork-agents"\n',
    )


def ccommit(root: Path, message: str) -> None:
    cgit(root, "add", "-A")
    cgit(root, "commit", "-q", "-m", message)


def ctag(root: Path, name: str) -> None:
    cgit(root, "tag", name)


def crepo(root: Path, version: str = "1.0.0") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    cgit(root, "init", "-q")
    cversion(root, version)
    ccommit(root, "base")
    return root


def test_r2_counts_the_reachable_version_tags_and_never_a_negative(tmp_path):
    """``S = A - O``: the two doc tags at HEAD are not version tags."""
    root = crepo(tmp_path / "repo", "1.0.0")
    ctag(root, "v1.0.0")
    ctag(root, "docs-a")
    ctag(root, "docs-b")
    cwrite(root, "README.md", "# readme\n")
    ccommit(root, "doc commit")
    cversion(root, "1.0.1")
    ccommit(root, "bump")

    result = crc.rule_r2_head_is_newer(root)

    reachable = crc._reachable_version_tags(root)
    at_head = crc._tags_at_head(root)
    assert reachable == ["v1.0.0"]
    assert at_head == set()
    assert len(reachable) - len(at_head) >= 0
    assert result.status == "ok"
    assert result.detail == "HEAD 1.0.1 is newer than 1 tag(s)"


def test_r2_a_maintenance_branch_is_not_permanently_red(tmp_path):
    """A ``1.0.x`` line branched off ``v1.0.0`` is ``ok``."""
    root = crepo(tmp_path / "repo", "1.0.0")
    ctag(root, "v1.0.0")
    cgit(root, "checkout", "-q", "-b", "main-line")
    cversion(root, "1.1.0")
    ccommit(root, "main bump")
    ctag(root, "v1.1.0")
    cversion(root, "1.1.2")
    ccommit(root, "main bump again")
    ctag(root, "v1.1.2")
    cgit(root, "checkout", "-q", "-b", "maintenance", "v1.0.0")
    cversion(root, "1.0.1")
    ccommit(root, "maintenance release")
    ctag(root, "v1.0.1")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert result.detail == "HEAD 1.0.1 is newer than 1 tag(s)"


def test_r2_a_stale_main_names_only_the_reachable_tags_ahead(tmp_path):
    """HEAD between two reachable tags: DRIFT names the reachable one only."""
    root = crepo(tmp_path / "repo", "1.0.0")
    ctag(root, "v1.0.0")
    cversion(root, "1.1.0")
    ccommit(root, "bump")
    ctag(root, "v1.1.0")
    cversion(root, "1.0.5")
    ccommit(root, "stale bump")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "DRIFT"
    assert "v1.1.0" in result.detail
    assert "v1.0.0" not in result.detail


def test_r2_a_tag_push_is_ok_because_the_tag_at_head_is_excluded(tmp_path):
    """HEAD is exactly ``vX.Y.Z``: the tag at HEAD is in ``O``, so R2 is ok."""
    root = crepo(tmp_path / "repo", "1.1.0")
    ctag(root, "v1.1.0")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert result.detail == "HEAD 1.1.0 is newer than 0 tag(s)"


def test_the_implemented_r9_pattern_is_the_contract_pattern_byte_for_byte():
    assert crc.TAGGED_TOKEN.pattern == CONTRACT_TAGGED_TOKEN
    assert crc.TAGGED_TOKEN.groups == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("we shipped v1.0.0 today", "1.0.0"),
        ("roll back to v0.9.0 now", "0.9.0"),
        ("checkout --branch 1.2.3", "1.2.3"),
        ("checkout --branch=v1.2.3", "1.2.3"),
        ("checkout --tag 1.2.3", "1.2.3"),
        ("checkout --ref v1.2.3", "1.2.3"),
        ("git checkout 1.2.3", "1.2.3"),
        ("git switch v1.2.3", "1.2.3"),
        ("see releases/tag/1.2.3", "1.2.3"),
        ("see releases/tag/v1.2.3", "1.2.3"),
        ("compare/1.2.3...HEAD", "1.2.3"),
        ("compare/v1.2.3...HEAD", "1.2.3"),
        ("released at v9.9.9.", "9.9.9"),
        ("https://github.com/Nidvue/Teamwork/compare/v1.1.2...HEAD", None),
        ("https://github.com/Nidvue/Teamwork/releases/tag/v1.1.2", None),
        ("semver.org/spec/v2.0.0.html", None),
        ("xcompare/9.9.9", None),
        ("my--branch 9.9.9", None),
        ("python: 3.12.13", None),
    ],
)
def test_the_r9_pattern_matches_exactly_the_contract_table(text, expected):
    versions = [match.group(1) for match in crc.TAGGED_TOKEN.finditer(text)]
    if expected is None:
        assert versions == []
    else:
        assert expected in versions


def test_the_reported_tag_is_never_vnone():
    """Every branch of the alternation carries the version in group 1."""
    for text in (
        "we shipped v1.0.0 today",
        "checkout --branch 1.2.3",
        "git switch v1.2.3",
        "see releases/tag/1.2.3",
        "compare/v1.2.3...HEAD",
    ):
        match = crc.TAGGED_TOKEN.search(text)
        assert match is not None, text
        assert match.re.groups == 1
        assert f"v{match.group(1)}" != "vNone"


def test_r9_reports_the_group_1_version_as_a_tag(tmp_path):
    """End to end: a bare semver in a pin context names a tag that is missing."""
    root = tmp_path / "repo"
    root.mkdir()
    cgit(root, "init", "-q")
    cwrite(root, "src/teamwork/version.py", '__version__ = "1.1.0"\n')
    cwrite(root, "README.md", "# Teamwork\n\nInstall with --branch 9.9.9 today.\n")
    ccommit(root, "readme with a pin")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "DRIFT"
    assert "v9.9.9" in result.detail
    assert "vNone" not in result.detail


def test_a_real_shallow_clone_is_an_input_error_not_a_pass(tmp_path):
    """A **real** ``git clone --depth 1`` is exit 2, never a green run.

    The clone is real, not simulated: the guard exists precisely because the
    clone cannot see the tags, so the clone itself has to be shallow for the
    test to mean anything.
    """
    origin = crepo(tmp_path / "origin", "1.1.0")
    ctag(origin, "v1.1.0")
    cversion(origin, "1.1.2")
    ccommit(origin, "bump")
    ctag(origin, "v1.1.2")

    clone = tmp_path / "clone"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", "v1.1.2", f"file://{origin}", str(clone)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert cgit(clone, "rev-parse", "--is-shallow-repository").strip() == "true"

    # The clone sees only the tag it was branched on - the blind build the guard exists for.
    assert crc._version_tags(clone) == ["v1.1.2"]
    assert "v1.1.0" not in crc._version_tags(clone)

    for rule in (crc.rule_r1_tagged_version, crc.rule_r2_head_is_newer):
        with pytest.raises(crc.InputError) as caught:
            rule(clone)
        assert "shallow" in str(caught.value)

    assert crc.main(["--offline", "--repo-root", str(clone)]) == 2


def test_a_full_clone_is_the_normal_result(tmp_path):
    """The same origin, cloned with the complete tag set, evaluates normally."""
    origin = crepo(tmp_path / "origin", "1.1.0")
    ctag(origin, "v1.1.0")
    cversion(origin, "1.1.2")
    ccommit(origin, "bump")
    ctag(origin, "v1.1.2")

    clone = tmp_path / "clone"
    result = subprocess.run(
        ["git", "clone", "--no-local", str(origin), str(clone)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    assert crc._version_tags(clone) == ["v1.1.0", "v1.1.2"]
    assert crc.rule_r1_tagged_version(clone).status == "ok"
    assert crc.rule_r2_head_is_newer(clone).status == "ok"


def test_a_tarball_without_git_is_an_input_error(tmp_path):
    """A tree with no ``.git`` has no tag list: exit 2, never a clean run."""
    root = tmp_path / "tarball"
    root.mkdir()
    cwrite(root, "src/teamwork/version.py", '__version__ = "1.1.0"\n')

    assert crc.main(["--offline", "--repo-root", str(root)]) == 2
