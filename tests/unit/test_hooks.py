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


def test_install_is_per_stage_so_a_foreign_pre_push_does_not_block_pre_commit(
    cli, repo, capsys
) -> None:
    """F-6: `git lfs install` owns pre-push, and that refused BOTH stages.

    R1 - no commit on the default branch - has no other in-loop enforcement, so a
    foreign hook on the *other* stage must not be able to keep it off the machine.
    The old installer validated both stages and wrote neither.
    """
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install") == 0
    out = capsys.readouterr().out
    assert "pre-commit installed" in out
    assert "pre-push installed (chained: pre-push.teamwork-foreign)" in out
    body = (hook_dir(repo) / "pre-commit").read_text(encoding="utf-8")
    assert config.HOOK_MARKER in body, "the guard for the default branch must be installed"


def test_a_foreign_hook_is_preserved_and_chained_instead_of_dropped(cli, repo, capsys) -> None:
    """F-6: never delete someone else's hook - keep it and run it after ours."""
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install") == 0
    preserved = hook_dir(repo) / "pre-push.teamwork-foreign"
    assert preserved.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    assert os.access(preserved, os.X_OK), "a preserved hook that cannot execute is a refusal"
    body = (hook_dir(repo) / "pre-push").read_text(encoding="utf-8")
    assert config.HOOK_MARKER in body
    assert 'chained="$hook_dir/pre-push.teamwork-foreign"' in body
    assert '"$chained" "$@" < "$refspecs"' in body


def test_status_names_the_chained_hook_it_runs(cli, repo, capsys) -> None:
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    assert cli("--project", repo, "hooks", "install") == 0
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == [
        "pre-commit installed",
        "pre-push installed (chained: pre-push.teamwork-foreign)",
    ]


def test_status_does_not_claim_a_chain_that_does_not_run(cli, repo, capsys) -> None:
    """`--force` writes a plain shim; the orphaned preserved file must not be advertised."""
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    assert cli("--project", repo, "hooks", "install") == 0
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho lfs-again\n")
    assert cli("--project", repo, "hooks", "install", "--force", "--reason", "probe") == 0
    assert (hook_dir(repo) / "pre-push.teamwork-foreign").exists(), "the old preserve is left"
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "status") == 0
    assert stage_lines(capsys.readouterr().out) == ["pre-commit installed", "pre-push installed"]


def test_uninstall_restores_the_chained_foreign_hook(cli, repo, capsys) -> None:
    """Removing our shim must not switch the preserved LFS hook off for good."""
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    assert cli("--project", repo, "hooks", "install") == 0
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "uninstall") == 0
    out = capsys.readouterr().out
    assert "pre-push removed" in out
    assert "pre-push previous hook restored from pre-push.teamwork-foreign" in out
    assert (hook_dir(repo) / "pre-push").read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    assert not (hook_dir(repo) / "pre-push.teamwork-foreign").exists()


def test_install_force_replaces_a_foreign_hook(cli, repo, capsys) -> None:
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install", "--force", "--reason", "probe hook") == 0
    body = (hook_dir(repo) / "pre-push").read_text(encoding="utf-8")
    assert config.HOOK_MARKER in body
    assert "echo mine" not in body
    assert not (hook_dir(repo) / "pre-push.teamwork-foreign").exists(), (
        "--force replaces: it is not the same act as preserving and chaining"
    )


def test_install_force_without_a_reason_is_refused_and_touches_nothing(cli, repo, capsys) -> None:
    """F-6: a replacement is recorded with its reason or it does not happen."""
    foreign = write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install", "--force") == 1
    assert "--reason" in capsys.readouterr().err
    assert foreign.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    assert not (hook_dir(repo) / "pre-commit").exists()


def test_a_force_replacement_records_its_reason_in_the_team_ledger(cli, repo, capsys) -> None:
    from teamwork.engine import ledger_append, ledger_read

    team = repo / ".pi" / "Teamwork" / "Teams" / "Repo"
    ledger_append(team, "seed", actor="Developer")
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\necho mine\n")
    capsys.readouterr()

    assert cli("--project", repo, "hooks", "install", "--force", "--reason", "probe hook") == 0

    record = ledger_read(team)[-1]
    assert record["action"] == "hooks.install"
    assert record["target"] == "pre-push"
    assert "probe hook" in record["detail"]


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
# R2 measures the INDEX, not the work-tree file (T-0024, H5)
# --------------------------------------------------------------------------- #


def binary_bytes(size: int) -> bytes:
    return bytes(range(256)) * (size // 256) + b"\x00" * (size % 256)


def test_pre_commit_refuses_a_blob_staged_large_then_shrunk_in_the_work_tree(
    cli, feature, capsys
) -> None:
    """The commit records the INDEX blob, so the gate must measure the index.

    `git diff --cached --name-only` names an index path, and the gate used to
    `stat()` the work-tree file of the same name: a 1 MiB+ binary staged as a
    normal file and then truncated to one byte in the work tree committed the
    large blob with the hook green - a false negative in the one gate that exists
    to keep a binary out of a plain commit.
    """
    staged = stage_blob(feature / "movie.bin", config.LFS_MAX_BYTES + 1)
    staged.write_bytes(b"\x00")
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 1
    err = capsys.readouterr().err
    assert "large file(s) that no Git LFS pattern covers" in err
    assert "movie.bin" in err
    assert str(config.LFS_MAX_BYTES + 1) in err, "the size reported must be the staged size"


def test_pre_commit_accepts_a_small_staged_blob_behind_a_large_work_tree_file(
    cli, feature, capsys
) -> None:
    """The other direction: what is not committed cannot be refused.

    A one-byte blob is staged and the work-tree copy is then grown past the
    threshold; the commit carries one byte, so the gate must pass. Refusing here
    is a false positive on a commit that stores nothing large.
    """
    path = feature / "movie.bin"
    path.write_bytes(b"\x00")
    git(feature, "add", "movie.bin")
    path.write_bytes(binary_bytes(config.LFS_MAX_BYTES + 1))
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 0
    assert "large file(s)" not in capsys.readouterr().err


def test_pre_commit_sniffs_the_staged_bytes_not_the_work_tree(cli, feature, capsys) -> None:
    """The binary sniff reads the staged content too, not the file on disk.

    A large TEXT record staged, then overwritten with binary bytes in the work
    tree: the commit still holds the document, so no LFS filter is needed and R2
    must stay quiet. The pre-fix gate refused it with no cause the author could
    see - the working copy it described was not the one being committed.
    """
    path = feature / "docs" / "Archive.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * (config.LFS_MAX_BYTES + 1), encoding="utf-8")
    git(feature, "add", "docs/Archive.md")
    path.write_bytes(binary_bytes(config.LFS_MAX_BYTES + 1))
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 0
    assert "large file(s)" not in capsys.readouterr().err


def test_a_binary_routed_into_lfs_is_not_a_text_file_in_lfs(cli, feature, capsys) -> None:
    """The text-in-LFS check keeps reading the working copy, and must.

    With the `lfs` filter installed, staging a pattern-matched file stores a
    ~130-byte POINTER in the index, so the index holds no content to classify:
    sniffing it would call every correctly-tracked binary a text file. The
    content whose kind decides the question survives only in the working copy,
    so that is what `lfs_text_mismatch` reads - a binary there is what LFS is for.
    """
    write(feature / ".gitattributes", "*.bin filter=lfs diff=lfs merge=lfs -text\n")
    git(feature, "add", ".gitattributes")
    path = feature / "assets" / "weights.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(binary_bytes(config.LFS_MAX_BYTES + 1))
    git(feature, "add", "assets/weights.bin")
    capsys.readouterr()

    assert cli("--project", feature, "hook", "pre-commit") == 0
    assert "routed into Git LFS" not in capsys.readouterr().err


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
# the shim: fail closed, and chain a preserved foreign hook (F-6)
# --------------------------------------------------------------------------- #


def test_the_shim_never_fails_open() -> None:
    """F-6: `|| exit 0` on the toplevel and on the engine test disabled every rule.

    A guard that cannot run must refuse loudly. `hooks status` said `installed`
    while a renamed engine made both hooks a silent no-op, which is worse than no
    hook at all: the record claims enforcement the tree does not have.
    """
    for stage in config.HOOK_STAGES:
        for body in (hooks.shim(stage), hooks.shim(stage, chain=True)):
            assert "|| exit 0" not in body
            assert 'if [ -z "$root" ]; then' in body
            assert 'if [ ! -f "$root/scripts/teamwork.py" ]; then' in body
            assert body.count("  exit 1") >= 2
    assert '[ -n "${TEAMWORK_SKIP_HOOKS:-}" ] && exit 0' in hooks.shim("pre-commit")


@pytest.mark.parametrize("stage", ["pre-commit", "pre-push"])
def test_the_shim_exits_non_zero_when_the_engine_file_is_missing(
    cli, repo, capsys, stage: str
) -> None:
    require_tool("sh")
    assert cli("--project", repo, "hooks", "install") == 0
    assert not (repo / "scripts" / "teamwork.py").exists(), "the premise: no engine here"

    run = subprocess.run(
        ["sh", str(hook_dir(repo) / stage), "origin", "https://example.invalid/r.git"],
        cwd=str(repo),
        input="",
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert run.returncode != 0, "a renamed engine must not silently disable the guard"
    assert "is missing" in run.stderr
    assert "TEAMWORK_SKIP_HOOKS=1" in run.stderr, "the message must name the escape"

    bypassed = subprocess.run(
        ["sh", str(hook_dir(repo) / stage), "origin", "https://example.invalid/r.git"],
        cwd=str(repo),
        input="",
        capture_output=True,
        text=True,
        env=clean_env(TEAMWORK_SKIP_HOOKS="1"),
    )
    assert bypassed.returncode == 0, "the documented bypass still applies"


def test_a_refusal_stops_before_the_chained_hook(cli, repo, repo_root, capsys) -> None:
    """The chained hook is a second opinion, not a replacement: rules first."""
    require_tool("sh")
    write(hook_dir(repo) / "pre-commit", "#!/bin/sh\necho FOREIGN-RAN\n")
    assert cli("--project", repo, "hooks", "install") == 0
    write(repo / "scripts" / "teamwork.py", engine_shim(repo_root))

    run = subprocess.run(
        ["sh", str(hook_dir(repo) / "pre-commit")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert run.returncode == 1
    assert "refusing to commit on" in run.stderr
    assert "FOREIGN-RAN" not in run.stdout, "a refused commit must not reach the chained hook"


def test_the_chained_hook_runs_after_the_rules_pass(cli, repo, repo_root, capsys) -> None:
    require_tool("sh")
    git(repo, "checkout", "-q", "-b", "feature")
    write(hook_dir(repo) / "pre-commit", "#!/bin/sh\necho FOREIGN-RAN\n")
    assert cli("--project", repo, "hooks", "install") == 0
    write(repo / "scripts" / "teamwork.py", engine_shim(repo_root))

    run = subprocess.run(
        ["sh", str(hook_dir(repo) / "pre-commit")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert run.returncode == 0, run.stderr
    assert "FOREIGN-RAN" in run.stdout


def test_the_chained_pre_push_hands_git_refspecs_to_both_hooks(
    cli, repo, repo_root, capsys
) -> None:
    """git writes the refspec list to stdin; a stream can only be read once.

    The teamwork rules read it, so a chained ``git lfs``-style hook must still see
    it - otherwise the chain silently becomes a hook that always sees "nothing to
    push". The preserved hook prints the number of lines it received.
    """
    require_tool("sh")
    git(repo, "checkout", "-q", "-b", "feature")
    write(hook_dir(repo) / "pre-push", "#!/bin/sh\nwc -l | tr -d ' '\n")
    assert cli("--project", repo, "hooks", "install") == 0
    write(repo / "scripts" / "teamwork.py", engine_shim(repo_root))
    sha = git(repo, "rev-parse", "HEAD")

    run = subprocess.run(
        ["sh", str(hook_dir(repo) / "pre-push"), "origin", "https://example.invalid/r.git"],
        cwd=str(repo),
        input=f"refs/heads/feature {sha} refs/heads/feature {'0' * 40}\n",
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "1", f"the chained hook must still see git's refspecs: {run}"


def test_the_chained_shim_refuses_when_the_preserved_hook_is_gone(
    cli, repo, repo_root, capsys
) -> None:
    """Deleting the preserved file must not quietly cancel that hook either."""
    require_tool("sh")
    git(repo, "checkout", "-q", "-b", "feature")
    write(hook_dir(repo) / "pre-commit", "#!/bin/sh\nexit 0\n")
    assert cli("--project", repo, "hooks", "install") == 0
    write(repo / "scripts" / "teamwork.py", engine_shim(repo_root))
    (hook_dir(repo) / "pre-commit.teamwork-foreign").unlink()

    run = subprocess.run(
        ["sh", str(hook_dir(repo) / "pre-commit")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=clean_env(),
    )

    assert run.returncode == 1
    assert "pre-commit.teamwork-foreign" in run.stderr


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
