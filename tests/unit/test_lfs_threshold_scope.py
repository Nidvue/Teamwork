"""The LFS threshold applies to BINARIES, not to the team's text records.

Covers [Architecture](../../../docs/Team/Architecture.md) section 11.10, layer
``system``, area ``lfs-scope``, owner Architect.

The three gates that read the threshold are the **audit**, **``commit
--check-lfs``** and the **pre-commit rule R2**. This suite calls all three
through their own product path - the audit function, the CLI commit and the CLI
hook - and not through the shared predicate alone. That is the whole point: a
defect in this area lives in the *wiring*, and a test that only calls the
predicate stays green while the product is broken. The predicate-only test the
first draft shipped is exactly the failure this file exists to prevent
(``D-20261021-Architect``).

Every test builds its own throwaway repository, so nothing here depends on this
checkout's git state.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import config, engine, gitutil, hooks

#: Ambient git/teamwork switches a developer shell may carry; every test starts
#: without them so the gates read the throwaway repository's own configuration.
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

ROLE_EMAIL = "architect@agents.nidvue.com"
BIG = config.LFS_MAX_BYTES + 1


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


def write_binary(path: Path, size: int) -> Path:
    """A real binary payload: bytes that no decoder reads as text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(range(256)) * (size // 256) + b"\x00" * (size % 256))
    return path


def write_text(path: Path, size: int) -> Path:
    """A text record: a document that is allowed to grow past the threshold."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * size, encoding="utf-8")
    return path


def stage(path: Path) -> None:
    git(path.parent, "add", path.name)


def queue_task(team_root: Path) -> None:
    """Put one task on the architect queue so `commit --task` can be attributed."""
    task = engine.new_task("the record grows", status="doing")
    task["id"] = "T-0001"
    engine.write_tasks(team_root / "Roles" / "Architect" / engine.F_TASKS, [task], "architect")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository with an LFS-aware .gitattributes and a team tree."""
    path = tmp_path / "Repo"
    path.mkdir()
    git(path, "init", "-q", "-b", config.DEFAULT_BASE)
    git(path, "config", "user.name", "Architect")
    git(path, "config", "user.email", ROLE_EMAIL)
    git(path, "config", "commit.gpgsign", "false")
    (path / ".gitattributes").write_text(
        "*.png filter=lfs diff=lfs merge=lfs -text\n*.bin filter=lfs diff=lfs merge=lfs -text\n"
    )
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
    git(path, "add", "README.md", ".gitattributes")
    git(path, "commit", "-q", "-m", "first")
    return path


@pytest.fixture
def team_root(repo: Path) -> Path:
    """The team tree the engine resolves for this repository."""
    root = repo / ".pi" / "Teamwork" / "Teams" / "Repo"
    (root / "Roles" / "Architect").mkdir(parents=True)
    (root / "Settings.json").write_text('{"TeamId": "team-a"}\n', encoding="utf-8")
    return root


# --------------------------------------------------------------------------- #
# the predicate
# --------------------------------------------------------------------------- #


def test_the_binary_test_reads_the_content_not_the_name(tmp_path: Path) -> None:
    """A binary renamed `.md` is binary; a text file named `.bin` is text.

    The name is not evidence. A rule keyed on the extension is defeated by the
    content it is supposed to police, so the test is the content.
    """
    disguised = write_binary(tmp_path / "Archive.md", 4096)
    named = write_text(tmp_path / "movie.bin", 4096)

    assert gitutil.is_binary_content(disguised) is True
    assert gitutil.is_binary_content(named) is False


def test_a_utf16_document_is_text_not_binary(tmp_path: Path) -> None:
    """A UTF-16 file contains NUL bytes and is still a document."""
    path = tmp_path / "Archive.md"
    path.write_bytes("evidence: the record grows".encode("utf-16-le"))

    assert gitutil.is_binary_content(path) is False


def test_an_empty_file_is_not_binary(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_bytes(b"")

    assert gitutil.is_binary_content(path) is False


# --------------------------------------------------------------------------- #
# gate 1: the audit
# --------------------------------------------------------------------------- #


def test_the_audit_exempts_a_large_text_record(repo: Path, team_root: Path, capsys) -> None:
    """The audit must not demand an LFS filter for a document."""
    write_text(repo / "docs" / "Team" / "Archive.md", BIG)

    hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    out = capsys.readouterr().out

    assert hits == 0
    assert "not LFS-tracked" not in out
    assert "large text record(s) exempt" in out


def test_the_audit_still_flags_a_large_binary(repo: Path, team_root: Path, capsys) -> None:
    """The gate the LFS rule exists for must keep its teeth."""
    write_binary(repo / "assets" / "weights.dat", BIG)

    hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    out = capsys.readouterr().out

    assert hits == 1
    assert "not LFS-tracked" in out
    assert "weights.dat" in out


def test_the_audit_flags_a_binary_disguised_as_a_record(
    repo: Path, team_root: Path, capsys
) -> None:
    """A binary dropped into `docs/Team/` is still a binary."""
    write_binary(repo / "docs" / "Team" / "Archive.md", BIG)

    hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)

    assert hits == 1
    assert "not LFS-tracked" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# gate 2: `commit --check-lfs`
# --------------------------------------------------------------------------- #


def commit_args(task: str, path: str) -> list:
    return [
        "commit",
        "--role",
        "architect",
        "--type",
        "chore",
        "--task",
        task,
        "--paths",
        path,
        "--goal",
        "the threshold applies to binaries",
        "--deliverable",
        "a text record stays a plain file",
        "--why",
        "a document in LFS is unreadable without a client",
        "--status",
        "implemented",
        "--result",
        "measured by the three gates",
    ]


def test_commit_check_lfs_accepts_a_large_text_record(
    cli, repo: Path, team_root: Path, capsys
) -> None:
    """`commit --check-lfs` must not refuse the archive."""
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "docs" / "Team" / "Archive.md", BIG)
    stage(record)
    queue_task(team_root)

    code = cli("--project", repo, *commit_args("T-0001", "docs/Team/Archive.md"))

    assert code == 0, capsys.readouterr().err
    assert "refusing to commit large" not in capsys.readouterr().err


def test_commit_check_lfs_still_refuses_a_large_binary(
    cli, repo: Path, team_root: Path, capsys
) -> None:
    """The enforcement gate must keep refusing a binary."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.dat", BIG)
    stage(blob)
    queue_task(team_root)

    code = cli("--project", repo, *commit_args("T-0001", "assets/weights.dat"))

    assert code == 2
    assert "refusing to commit large" in capsys.readouterr().err


def test_the_commit_threshold_default_is_the_one_constant() -> None:
    """One number: the parser default and the hook read the same constant."""
    parser = engine.build_parser()
    args = parser.parse_args(["commit", "--role", "architect"])
    assert args.lfs_threshold == config.LFS_MAX_BYTES == 1048576


# --------------------------------------------------------------------------- #
# gate 3: the pre-commit rule R2
# --------------------------------------------------------------------------- #


def test_the_hook_accepts_a_large_text_record(cli, repo: Path, capsys) -> None:
    """R2 must not refuse the archive."""
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "docs" / "Team" / "Archive.md", BIG)
    stage(record)
    capsys.readouterr()

    assert cli("--project", repo, "hook", "pre-commit") == 0
    assert "large file(s)" not in capsys.readouterr().err


def test_the_hook_still_refuses_a_large_binary(cli, repo: Path, capsys) -> None:
    """R2 must keep refusing a binary that no pattern covers."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.dat", BIG)
    stage(blob)
    capsys.readouterr()

    assert cli("--project", repo, "hook", "pre-commit") == 1
    err = capsys.readouterr().err
    assert "large file(s) that no Git LFS pattern covers" in err
    assert blob.name in err


def test_the_hook_refuses_a_binary_disguised_as_a_record(cli, repo: Path, capsys) -> None:
    """A binary named `.md` is refused: the name is not a defence."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "docs" / "Team" / "Archive.md", BIG)
    stage(blob)
    capsys.readouterr()

    assert cli("--project", repo, "hook", "pre-commit") == 1
    assert blob.name in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# the three gates agree
# --------------------------------------------------------------------------- #


def test_the_three_gates_agree_about_the_same_file(
    repo: Path, team_root: Path, cli, capsys
) -> None:
    """One predicate, three gates: the same file gets the same answer.

    The audit, `commit --check-lfs` and R2 are three readings of one rule. A
    disagreement between them is the defect this contract exists to prevent -
    the reviewer's finding was exactly that the audit blessed a file the hook
    refused.
    """
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "docs" / "Team" / "Archive.md", BIG)
    stage(record)
    queue_task(team_root)

    audit_hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    hook_code = cli("--project", repo, "hook", "pre-commit")
    commit_code = cli("--project", repo, *commit_args("T-0001", "docs/Team/Archive.md"))

    assert audit_hits == 0
    assert hook_code == 0
    assert commit_code == 0, capsys.readouterr().err


def test_the_hook_and_the_engine_refuse_the_same_binary(
    repo: Path, team_root: Path, cli, capsys
) -> None:
    """The other half of the agreement: a binary is refused everywhere."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.dat", BIG)
    stage(blob)
    queue_task(team_root)

    audit_hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    hook_code = cli("--project", repo, "hook", "pre-commit")
    commit_code = cli("--project", repo, *commit_args("T-0001", "assets/weights.dat"))

    assert audit_hits == 1
    assert hook_code == 1
    assert commit_code == 2


def test_the_hook_module_asks_the_shared_predicate(repo: Path, monkeypatch) -> None:
    """One predicate, not two copies: the hook calls the shared one.

    A second copy of the binary test in the hook module is how the gates drift
    apart again, so the wiring itself is asserted. The staged path asks the
    byte-level form (the content the commit records, T-0024/H5) and the deletion
    fallback asks the file form; both are `gitutil`'s.
    """
    sniffed: list = []
    real = gitutil.is_binary_bytes

    def spy(head: bytes) -> bool:
        sniffed.append(head)
        return real(head)

    monkeypatch.setattr(hooks, "is_binary_bytes", spy)
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.dat", BIG)
    stage(blob)

    blocked = hooks.large_staged_files(repo)

    assert [rel for rel, _ in blocked] == ["assets/weights.dat"]
    assert sniffed and sniffed[0][:8] == blob.read_bytes()[:8], (
        "the hook did not ask the shared binary predicate"
    )


def test_the_work_tree_fallback_is_the_only_path_that_reads_a_file(repo: Path, monkeypatch) -> None:
    """The work-tree read survives only where the index has no entry to read.

    A path the index does not hold (a staged deletion, or a conflicted path whose
    entry is not at stage 0) has nothing to commit: the gate falls back to the
    file, and the verdict is still the shared predicate. A path that is gone from
    both is no candidate at all rather than an error.
    """
    read: list = []
    real = gitutil.is_binary_content

    def spy(path: Path) -> bool:
        read.append(path)
        return real(path)

    monkeypatch.setattr(hooks, "is_binary_content", spy)
    blob = write_binary(repo / "assets" / "unstaged.bin", 4096)

    assert hooks.staged_verdict(repo, "assets/unstaged.bin") == (4096, True)
    assert read == [blob], "the fallback did not ask the shared file predicate"
    assert hooks.staged_verdict(repo, "gone/missing.bin") == (None, False)


# --------------------------------------------------------------------------- #
# a TEXT file a .gitattributes pattern would route into LFS
# --------------------------------------------------------------------------- #


def test_a_text_file_captured_by_an_lfs_pattern_is_a_misconfiguration(
    repo: Path, team_root: Path
) -> None:
    """.gitattributes routes a file into LFS BY NAME, so a text file can land there.

    `*.bin filter=lfs` captures `assets/movie.bin` whatever its content is, and
    a document in LFS is a pointer for every reader without an LFS client. The
    content decides whether the capture is a mistake.
    """
    record = write_text(repo / "assets" / "movie.bin", BIG)

    assert gitutil.lfs_tracked(repo, "assets/movie.bin") is True
    assert gitutil.is_binary_content(record) is False
    assert gitutil.lfs_text_mismatch(repo, "assets/movie.bin") is True


def test_a_binary_captured_by_an_lfs_pattern_is_not_a_misconfiguration(
    repo: Path,
) -> None:
    """The ordinary case: a real binary named `.bin` is exactly what LFS is for."""
    blob = write_binary(repo / "assets" / "weights.bin", BIG)

    assert gitutil.lfs_tracked(repo, "assets/weights.bin") is True
    assert gitutil.is_binary_content(blob) is True
    assert gitutil.lfs_text_mismatch(repo, "assets/weights.bin") is False


def test_the_audit_reports_a_text_file_routed_into_lfs(repo: Path, team_root: Path, capsys) -> None:
    """The audit must not call a misconfiguration 'exempt'."""
    write_text(repo / "assets" / "movie.bin", BIG)

    hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    out = capsys.readouterr().out

    assert hits == 1
    assert "text file(s) routed into Git LFS" in out
    assert "assets/movie.bin" in out


def test_the_audit_does_not_report_a_binary_captured_by_an_lfs_pattern(
    repo: Path, team_root: Path, capsys
) -> None:
    """A binary that LFS captures is the rule working, not a finding."""
    write_binary(repo / "assets" / "weights.bin", BIG)

    hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    out = capsys.readouterr().out

    assert hits == 0
    assert "routed into Git LFS" not in out


def test_the_hook_refuses_a_text_file_routed_into_lfs(cli, repo: Path, capsys) -> None:
    """R2 must refuse the file that would become a pointer."""
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "assets" / "movie.bin", BIG)
    stage(record)
    capsys.readouterr()

    assert cli("--project", repo, "hook", "pre-commit") == 1
    err = capsys.readouterr().err
    assert "text file(s) that .gitattributes routes into Git LFS" in err
    assert "assets/movie.bin" in err
    assert "LFS is for binaries" in err


def test_the_hook_accepts_a_binary_captured_by_an_lfs_pattern(cli, repo: Path, capsys) -> None:
    """The ordinary case must still pass: the gate does not block real binaries."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.bin", BIG)
    stage(blob)
    capsys.readouterr()

    assert cli("--project", repo, "hook", "pre-commit") == 0
    assert "routed into Git LFS" not in capsys.readouterr().err


def test_commit_check_lfs_refuses_a_text_file_routed_into_lfs(
    cli, repo: Path, team_root: Path, capsys
) -> None:
    """The commit path must refuse it too - the gates must agree."""
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "assets" / "movie.bin", BIG)
    stage(record)
    queue_task(team_root)

    code = cli("--project", repo, *commit_args("T-0001", "assets/movie.bin"))

    assert code == 2
    err = capsys.readouterr().err
    assert "text file(s) that .gitattributes routes into Git LFS" in err
    assert "assets/movie.bin" in err


def test_commit_check_lfs_accepts_a_binary_captured_by_an_lfs_pattern(
    cli, repo: Path, team_root: Path, capsys
) -> None:
    """A real binary covered by a pattern commits as usual."""
    git(repo, "checkout", "-q", "-b", "feature")
    blob = write_binary(repo / "assets" / "weights.bin", BIG)
    stage(blob)
    queue_task(team_root)

    code = cli("--project", repo, *commit_args("T-0001", "assets/weights.bin"))

    assert code == 0, capsys.readouterr().err


def test_the_mismatch_check_is_size_independent(repo: Path) -> None:
    """A text file in LFS is broken at ANY size, so the check ignores the threshold.

    A 126-byte text file named `.bin` is a pointer in the tree just as a
    1.1 MiB one is; a threshold would let the small one through.
    """
    write_text(repo / "assets" / "tiny.bin", 64)

    assert gitutil.lfs_text_mismatch(repo, "assets/tiny.bin") is True


def test_the_three_gates_agree_about_a_text_file_routed_into_lfs(
    repo: Path, team_root: Path, cli, capsys
) -> None:
    """The audit, the commit path and the hook must reach the same verdict."""
    git(repo, "checkout", "-q", "-b", "feature")
    record = write_text(repo / "assets" / "movie.bin", BIG)
    stage(record)
    queue_task(team_root)

    audit_hits = engine._audit_git_archival_lfs_large_files(team_root, ["architect"], None)
    hook_code = cli("--project", repo, "hook", "pre-commit")
    commit_code = cli("--project", repo, *commit_args("T-0001", "assets/movie.bin"))

    assert audit_hits == 1
    assert hook_code == 1
    assert commit_code == 2


def test_a_lfs_opt_out_is_honoured(repo: Path) -> None:
    """`.gitattributes` reads last-match-wins, so a `-filter` line cancels a pattern.

    The shipped `.gitattributes` opts the small social-preview PNG and the brand
    assets OUT of LFS. A check that ignored the opt-out would report a text
    brand asset as a misconfiguration that does not exist.
    """
    (repo / ".gitattributes").write_text(
        "*.png filter=lfs diff=lfs merge=lfs -text\nassets/preview.png -filter -diff -merge -text\n"
    )
    write_text(repo / "assets" / "preview.png", 64)

    assert gitutil.lfs_tracked(repo, "assets/preview.png") is False
    assert gitutil.lfs_text_mismatch(repo, "assets/preview.png") is False
