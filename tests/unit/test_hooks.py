"""The git hooks: install/status/uninstall, and the rules that refuse to pass.

Every test runs against a throwaway repository created with ``git init`` and a
real commit, so nothing here depends on this checkout's own git state. The
negative cases are the point: a pre-commit hook that cannot block a commit on the
default branch and a pre-push hook that cannot refuse a force-update are
decoration, and the linked-worktree case is the one the first draft got wrong
(``<toplevel>/.git`` is a file there, so the hook lives in the common git dir).
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.tooling import require_tool

from teamwork import config, engine, hooks

#: Ambient git/teamwork switches a developer shell may carry; every test starts
#: without them so the hook reads the throwaway repository's own configuration.
CLEARED = (
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_DATE",
    "TEAMWORK_SKIP_HOOKS",
    "TEAMWORK_ALLOW_MAIN",
    "TEAMWORK_ALLOW_FORCE",
)

ROLE_EMAIL = "developer@agents.nidvue.com"


def clean_env(**extra: str) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in CLEARED}
    env.update(extra)
    return env


def git(path: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(path), *argv], capture_output=True, text=True, env=clean_env()
    )
    assert done.returncode == 0, (argv, done.stderr)
    return done.stdout.strip()


def write(path: Path, text: str, mode: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return path


def stage_lines(out: str) -> list:
    """The two stage rows of `hooks status`, with the directory comment removed."""
    return [line for line in out.splitlines() if line and not line.startswith("#")]


def hook_dir(repo: Path) -> Path:
    """Asked of git directly, so the test does not trust the code under test."""
    located = Path(git(repo, "rev-parse", "--git-path", "hooks"))
    return located if located.is_absolute() else (repo / located).resolve()


@pytest.fixture(autouse=True)
def no_ambient_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in CLEARED:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "Repo"
    path.mkdir()
    git(path, "init", "-q", "-b", config.DEFAULT_BASE)
    git(path, "config", "user.name", "Developer")
    git(path, "config", "user.email", ROLE_EMAIL)
    git(path, "config", "commit.gpgsign", "false")
    write(path / "README.md", "# repo\n")
    git(path, "add", "README.md")
    git(path, "commit", "-q", "-m", "first")
    return path


@pytest.fixture
def unborn(tmp_path: Path) -> Path:
    """A repository whose HEAD names the default branch before any commit exists."""
    path = tmp_path / "Unborn"
    path.mkdir()
    git(path, "init", "-q", "-b", config.DEFAULT_BASE)
    git(path, "config", "user.name", "Developer")
    git(path, "config", "user.email", ROLE_EMAIL)
    return path


@pytest.fixture
def feature(repo: Path) -> Path:
    git(repo, "checkout", "-q", "-b", "feature")
    return repo


# --------------------------------------------------------------------------- #
# install / status / uninstall
# --------------------------------------------------------------------------- #


def test_install_writes_both_stages_with_the_marker_and_mode(cli, repo, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "install") == 0
    out = capsys.readouterr().out
    assert "pre-commit installed" in out

    for stage in ("pre-commit", "pre-push"):
        path = hook_dir(repo) / stage
        body = path.read_text(encoding="utf-8")
        if os.name != "nt":
            # Windows has no executable bit and git for Windows ignores the file
            # mode, so the 0755 contract only holds where POSIX modes exist.
            assert path.stat().st_mode & 0o777 == 0o755
        lines = body.splitlines()
        assert lines[0] == "#!/bin/sh"
        assert config.HOOK_MARKER == "teamwork-managed hook"
        expected = (
            f"# {config.HOOK_MARKER} (stage: {stage}) - remove with: teamwork.py hooks uninstall"
        )
        assert lines[1] == expected
        assert "\r" not in body
        assert body.rstrip().endswith(f'hook {stage} "$@"')
        assert "root=$(git rev-parse --show-toplevel)" in body
        assert '[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0' in body


def test_install_is_idempotent(cli, repo, capsys) -> None:
    assert cli("--project", repo, "hooks", "install") == 0
    first = (hook_dir(repo) / "pre-commit").read_text(encoding="utf-8")
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "install") == 0
    assert (hook_dir(repo) / "pre-commit").read_text(encoding="utf-8") == first


def test_install_refuses_a_foreign_hook_and_touches_nothing(cli, repo, capsys) -> None:
    foreign = write(hook_dir(repo) / "pre-commit", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install") == 1
    assert "refusing to overwrite" in capsys.readouterr().err
    assert foreign.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    # All-or-nothing: the second stage must not be written either.
    assert not (hook_dir(repo) / "pre-push").exists()


def test_install_force_replaces_a_foreign_hook(cli, repo, capsys) -> None:
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install", "--force") == 0
    body = (hook_dir(repo) / "pre-push").read_text(encoding="utf-8")
    assert config.HOOK_MARKER in body
    assert "echo mine" not in body


def test_status_reports_the_directory_it_probed(cli, repo, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "status") == 0
    out = capsys.readouterr().out
    assert f"# hooks directory: {hook_dir(repo)}" in out


def test_status_reports_absent_then_installed_then_foreign(cli, repo, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == ["pre-commit absent", "pre-push absent"]

    assert cli("--project", repo, "hooks", "install") == 0
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == ["pre-commit installed", "pre-push installed"]

    write(hook_dir(repo) / "pre-commit", "#!/bin/sh\necho mine\n")
    capsys.readouterr()
    assert cli("--project", repo, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == ["pre-commit foreign", "pre-push installed"]


def test_uninstall_removes_only_its_own_hook(cli, repo, capsys) -> None:
    assert cli("--project", repo, "hooks", "install") == 0
    foreign = write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "uninstall") == 0
    out = capsys.readouterr().out
    assert "pre-commit removed" in out
    assert "pre-push foreign" in out
    assert not (hook_dir(repo) / "pre-commit").exists()
    assert foreign.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"


@pytest.mark.parametrize(
    "argv",
    [
        ("hooks", "install"),
        ("hooks", "status"),
        ("hooks", "uninstall"),
        ("hook", "pre-commit"),
        ("hook", "pre-push", "origin", "https://example.invalid/repo.git"),
    ],
)
def test_every_command_dies_outside_a_git_repository(cli, tmp_path, capsys, argv) -> None:
    plain = tmp_path / "Plain"
    plain.mkdir()
    capsys.readouterr()

    assert cli("--project", plain, *argv) == 1
    assert "not a git repository" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# R1 / R2 / R3 - pre-commit
# --------------------------------------------------------------------------- #


def test_pre_commit_refuses_on_the_default_branch(cli, repo, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", repo, "hook", "pre-commit") == 1
    err = capsys.readouterr().err
    assert "refusing to commit on" in err
    assert "teamwork.py branch start --agent <you> --task <T-id>" in err


def test_pre_commit_refuses_the_root_commit_on_the_default_branch(cli, unborn, capsys) -> None:
    """The first commit has an unborn HEAD: `rev-parse --abbrev-ref` prints nothing."""
    probe = subprocess.run(
        ["git", "-C", str(unborn), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert probe.stdout.strip() != config.DEFAULT_BASE, (
        "an unborn HEAD does not name the branch, which is why the guard asks git symbolic-ref"
    )
    capsys.readouterr()

    assert cli("--project", unborn, "hook", "pre-commit") == 1
    assert "refusing to commit on" in capsys.readouterr().err


def test_the_root_commit_is_refused_end_to_end(cli, unborn, repo_root, capsys) -> None:
    write(unborn / "scripts" / "teamwork.py", engine_shim(repo_root))
    write(unborn / "README.md", "# first\n")
    git(unborn, "add", "README.md")
    capsys.readouterr()
    assert cli("--project", unborn, "hooks", "install") == 0

    done = subprocess.run(
        ["git", "-C", str(unborn), "commit", "-q", "-m", "first"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert done.returncode != 0, "the root commit on the default branch must be refused"
    assert "refusing to commit on" in done.stderr or "refusing to commit on" in done.stdout
    assert git(unborn, "rev-list", "--all") == "", "nothing may have been committed"


def test_pre_commit_allows_the_default_branch_with_the_override(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEAMWORK_ALLOW_MAIN", "1")
    capsys.readouterr()
    assert cli("--project", repo, "hook", "pre-commit") == 0


def test_pre_commit_allows_a_feature_branch(cli, feature, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", feature, "hook", "pre-commit") == 0
    assert capsys.readouterr().err == ""


def stage_blob(path: Path, size: int) -> Path:
    """Stage a BINARY blob of `size` bytes.

    The payload is real binary, not a run of ``x``: the LFS threshold is a
    binary threshold (Architecture 11.10) and the content decides, so a text
    payload named `.bin` is a text record and must not be refused.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(range(256)) * (size // 256) + b"\x00" * (size % 256))
    git(path.parent, "add", path.name)
    return path


def test_pre_commit_refuses_a_large_staged_blob_without_an_lfs_pattern(
    cli, feature, capsys
) -> None:
    big = stage_blob(feature / "movie.bin", config.LFS_MAX_BYTES + 1)
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 1
    err = capsys.readouterr().err
    assert "large file(s) that no Git LFS pattern covers" in err
    assert big.name in err


def test_pre_commit_allows_a_large_blob_covered_by_an_lfs_pattern(cli, feature, capsys) -> None:
    stage_blob(feature / "movie.bin", config.LFS_MAX_BYTES + 1)
    write(
        feature / ".gitattributes",
        "*.bin filter=lfs diff=lfs merge=lfs -text\n",
    )
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 0


def test_pre_commit_threshold_is_exactly_one_mib(cli, feature, capsys) -> None:
    stage_blob(feature / "exactly-at-the-line.bin", config.LFS_MAX_BYTES)
    capsys.readouterr()
    assert config.LFS_MAX_BYTES == 1048576
    assert cli("--project", feature, "hook", "pre-commit") == 0

    stage_blob(feature / "one-byte-over.bin", config.LFS_MAX_BYTES + 1)
    capsys.readouterr()
    assert cli("--project", feature, "hook", "pre-commit") == 1
    assert "one-byte-over.bin" in capsys.readouterr().err


def test_pre_commit_warns_on_a_non_role_identity_but_passes(cli, feature, capsys) -> None:
    git(feature, "config", "user.name", "Ping Zhao")
    git(feature, "config", "user.email", "ping@example.com")
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 0
    err = capsys.readouterr().err
    assert "warning" in err
    assert "is not a role mailbox" in err


def test_pre_commit_is_silent_for_a_role_mailbox(cli, feature, capsys) -> None:
    capsys.readouterr()
    assert cli("--project", feature, "hook", "pre-commit") == 0
    assert capsys.readouterr().err == ""


# --------------------------------------------------------------------------- #
# P1 / P2 - pre-push
# --------------------------------------------------------------------------- #


def diverged(repo: Path) -> tuple:
    """(base, side sha, main sha): ``side`` is not a descendant of ``main``."""
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "side")
    write(repo / "side.txt", "side\n")
    git(repo, "add", "side.txt")
    git(repo, "commit", "-q", "-m", "side")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", config.DEFAULT_BASE)
    write(repo / "main.txt", "main\n")
    git(repo, "add", "main.txt")
    git(repo, "commit", "-q", "-m", "main")
    return base, side, git(repo, "rev-parse", "HEAD")


def prepush(cli, monkeypatch: pytest.MonkeyPatch, repo: Path, lines: str) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(lines))
    return cli("--project", repo, "hook", "pre-push", "origin", "https://example.invalid/r.git")


def test_pre_push_refuses_a_non_fast_forward_update_of_the_default_branch(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, side, main_sha = diverged(repo)
    capsys.readouterr()

    code = prepush(cli, monkeypatch, repo, f"refs/heads/side {side} refs/heads/main {main_sha}\n")

    assert code == 1
    err = capsys.readouterr().err
    assert "non-fast-forward" in err
    assert "CEO's explicit authorization" in err


def test_pre_push_allows_a_fast_forward_new_branch_and_other_refs(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, side, main_sha = diverged(repo)
    capsys.readouterr()
    zero = "0" * 40

    for line in (
        f"refs/heads/main {main_sha} refs/heads/main {base}",  # fast-forward
        f"refs/heads/main {main_sha} refs/heads/main {zero}",  # new remote branch
        f"refs/heads/side {side} refs/heads/topic {main_sha}",  # not the default branch
    ):
        assert prepush(cli, monkeypatch, repo, line + "\n") == 0, line


def test_pre_push_allows_the_force_with_the_override(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    _base, side, main_sha = diverged(repo)
    monkeypatch.setenv("TEAMWORK_ALLOW_FORCE", "1")
    capsys.readouterr()

    assert (
        prepush(cli, monkeypatch, repo, f"refs/heads/side {side} refs/heads/main {main_sha}\n") == 0
    )


def test_pre_push_refuses_deleting_the_default_branch(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    _base, _side, main_sha = diverged(repo)
    capsys.readouterr()

    code = prepush(cli, monkeypatch, repo, f"(delete) {'0' * 40} refs/heads/main {main_sha}\n")

    assert code == 1
    err = capsys.readouterr().err
    assert "refusing to delete" in err
    assert "red line" in err


def test_pre_push_with_no_refspecs_passes(
    cli, repo, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    capsys.readouterr()
    assert prepush(cli, monkeypatch, repo, "") == 0


def test_hook_and_hooks_are_separate_subcommands() -> None:
    parser = engine.build_parser()
    assert parser.parse_args(["hook", "pre-commit"]).hook_cmd == "pre-commit"
    assert parser.parse_args(["hooks", "status"]).hooks_cmd == "status"
    with pytest.raises(SystemExit):
        parser.parse_args(["hookk", "status"])


# --------------------------------------------------------------------------- #
# the case the first draft got wrong: a linked worktree
# --------------------------------------------------------------------------- #


def engine_shim(repo_root: Path) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"sys.path.insert(0, {str(repo_root / 'src')!r})\n"
        "from teamwork.cli import main\n"
        "sys.exit(main())\n"
    )


def test_install_from_a_linked_worktree_lands_in_the_common_git_dir_and_fires(
    cli, repo, repo_root, tmp_path, capsys
) -> None:
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-q", str(linked), "-b", "feature")
    assert (linked / ".git").is_file(), "a linked worktree has a .git FILE, not a directory"
    assert not (linked / ".git" / "hooks").exists()

    capsys.readouterr()
    assert cli("--project", linked, "hooks", "install") == 0
    capsys.readouterr()

    common = hook_dir(repo)
    assert (common / "pre-commit").is_file()
    assert (common / "pre-push").is_file()
    assert cli("--project", linked, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == ["pre-commit installed", "pre-push installed"]

    # The hooks themselves are POSIX shell scripts, so running one needs `sh`:
    # an absent shell is a skip that names it, not a FileNotFoundError.
    require_tool("sh")

    body = engine_shim(repo_root)
    write(linked / "scripts" / "teamwork.py", body)
    write(repo / "scripts" / "teamwork.py", body)

    # The shim resolves the engine from the work tree it runs in, so it fires from
    # the linked worktree and from the main one, on that tree's own branch.
    allowed = subprocess.run(
        ["sh", str(common / "pre-commit")],
        cwd=str(linked),
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert allowed.returncode == 0, allowed.stderr

    blocked = subprocess.run(
        ["sh", str(common / "pre-commit")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert blocked.returncode == 1
    assert "refusing to commit on" in blocked.stderr

    bypassed = subprocess.run(
        ["sh", str(common / "pre-commit")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=clean_env(TEAMWORK_SKIP_HOOKS="1"),
    )
    assert bypassed.returncode == 0


def test_install_from_a_linked_worktree_is_visible_to_every_worktree(cli, repo, tmp_path) -> None:
    other = tmp_path / "other"
    git(repo, "worktree", "add", "-q", str(other), "-b", "other")
    assert cli("--project", repo, "hooks", "install") == 0
    assert cli("--project", other, "hooks", "status") == 0
    assert (hook_dir(repo) / "pre-commit").is_file()
    assert hooks.is_managed(hook_dir(repo) / "pre-commit")
