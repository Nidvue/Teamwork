"""One contract per defect from the M12 engine batch (T-0017).

Four independent defects, each with the behaviour that fails on the old code:

* (a) ``portable.py`` carried a ``type: ignore`` on ``ctypes.windll`` that mypy
  reports as *unused* on every non-Windows run, so the typing gate was permanently
  red. Its proof is the gate itself - ``python -m mypy src/teamwork`` -> Success, no
  source-file assertion can stand in for it.
* (b) ``ensure_lfs`` swallowed a failed ``git lfs install``: ``.gitattributes``
  named LFS filters git was never told about, with no warning and no status.
* (c) ``harness.hooks_dir`` and ``hooks.hooks_dir`` were two implementations of one
  ``rev-parse`` with two contracts (``Path | None`` unresolved vs ``Path`` resolved
  or die). Now one implementation, two policies, and they must agree on the path.
* (d) ``identity --audit`` resolved its range against the *primary* checkout, so a
  lane worktree audited main's history and printed a vacuous "0 problems".
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pytest

from teamwork import engine, gitutil, harness, hooks


def _git(repo: Path, *args: str, ident: tuple[str, str] | None = None):
    command = ["git", "-C", str(repo)]
    if ident:
        command += ["-c", f"user.name={ident[0]}", "-c", f"user.email={ident[1]}"]
    return subprocess.run(
        command + list(args),
        env={
            **os.environ,
            "HOME": str(repo.parent),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main", ".")
    _commit(path, "Developer", "developer@agents.nidvue.com", "feat(x): base")
    return path


def _commit(repo: Path, name: str, email: str, subject: str) -> None:
    _git(
        repo,
        "commit",
        "--allow-empty",
        "-m",
        f"{subject}\n\nActing role: {name}",
        ident=(name, email),
    )


# --- (b) a failed `git lfs install` is surfaced ------------------------------


def _fake_probe_ok(**kwargs):
    return subprocess.CompletedProcess(
        args=kwargs.get("args", []), returncode=0, stdout="lfs/3.4.0", stderr=""
    )


def test_ensure_lfs_warns_and_records_a_failed_install(repo, monkeypatch, capsys):
    """A failing install must warn in the probe's own style and set a status field."""
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if "install" in args:
            return subprocess.CompletedProcess(
                args=args,
                returncode=128,
                stdout="",
                stderr="error: could not lock config file .git/config: Permission denied",
            )
        return _fake_probe_ok(**kwargs)

    monkeypatch.setattr(gitutil.subprocess, "run", fake_run)
    result = gitutil.ensure_lfs(repo, quiet=False)
    out = capsys.readouterr().out

    assert any("install" in call for call in calls), "the install command must still be attempted"
    assert result["available"] is True
    assert result["installed"] is False
    assert "Permission denied" in result["install_error"]
    assert "WARNING" in out and "git lfs install --local" in out
    # The probe's wording is the style this warning copies: both name the cost.
    assert "large binaries will be committed as plain blobs" in out


def test_ensure_lfs_reports_success_with_no_error(repo, monkeypatch):
    """The status field must be empty on success, so a caller can trust it."""

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gitutil.subprocess, "run", fake_run)
    result = gitutil.ensure_lfs(repo, quiet=True)
    assert result["installed"] is True
    assert result["install_error"] == ""


def test_ensure_lfs_probe_failure_still_warns_once(repo, monkeypatch, capsys):
    """Absent git-lfs keeps its original warning and never claims an install."""

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="git: 'lfs' is not a git command"
        )

    monkeypatch.setattr(gitutil.subprocess, "run", fake_run)
    result = gitutil.ensure_lfs(repo, quiet=False)
    out = capsys.readouterr().out
    assert result["available"] is False
    assert result["installed"] is False
    assert out.count("WARNING") == 1
    assert "git-lfs is not installed" in out


# --- (c) one hooks-directory contract, two policies --------------------------


def test_both_hooks_dir_callers_agree_on_the_same_resolved_path(repo):
    """The installer and the report must name the identical directory."""
    installer = hooks.hooks_dir(repo)
    report = harness.hooks_dir(repo)
    assert report is not None
    assert installer == report
    assert installer.is_absolute()
    assert installer.name == "hooks"


def test_hooks_dir_policies_differ_only_on_failure(tmp_path):
    """A repo git cannot resolve: the report returns None, the installer dies loudly."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    assert harness.hooks_dir(not_a_repo) is None

    with pytest.raises(SystemExit) as caught:
        hooks.hooks_dir(not_a_repo)
    assert caught.value.code == 1


def test_installer_message_is_unchanged(tmp_path, capsys):
    """The operator-visible text stays exactly what it always was."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(SystemExit):
        hooks.hooks_dir(not_a_repo)
    err = capsys.readouterr().err
    assert err.startswith(f"teamwork: cannot resolve the git hooks directory for {not_a_repo}: ")
    assert err.count("cannot resolve the git hooks directory") == 1


def test_harness_report_survives_a_git_that_cannot_answer(repo, monkeypatch):
    """A failing ``rev-parse`` is a reported absence, never an aborted listing."""

    def fake_run(project, *argv):
        return subprocess.CompletedProcess(
            args=list(argv), returncode=128, stdout="", stderr="fatal: not a git repository"
        )

    monkeypatch.setattr(gitutil, "run_git", fake_run)
    assert harness.hooks_dir(repo) is None
    with pytest.raises(SystemExit):
        hooks.hooks_dir(repo)


# --- (d) identity --audit reads the repository that contains cwd -------------


def _identity_args(**overrides) -> argparse.Namespace:
    values = {
        "audit": True,
        "rev_range": "",
        "role": "",
        "project": None,
        "team": "",
        "strict_authors": False,
        "guard_committer": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.fixture()
def two_checkouts(repo, tmp_path, monkeypatch):
    """main holds only clean commits; a linked worktree's branch adds one bad one.

    ``TEAMWORK_ROOT`` points at the *primary* checkout's team tree, which is what a
    real lane inherits - that is precisely the state in which the old resolution
    (``project_of(root)``) read main and printed a vacuous clean audit.
    """
    team_root = repo / ".pi" / "Teamwork" / "Teams" / "Teamwork"
    team_root.mkdir(parents=True)
    lane = tmp_path / "lane"
    _git(repo, "worktree", "add", "-q", "-b", "lane", str(lane))
    _commit(lane, "Teamwork", "teamwork@agents.nidvue.com", "chore: import without a role")
    bad = _git(lane, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setenv("TEAMWORK_ROOT", str(team_root))
    return repo, lane, bad


def test_audit_in_a_worktree_reports_the_worktrees_own_bad_commit(
    two_checkouts, monkeypatch, capsys
):
    """The old code audited the primary checkout here and printed 0 problems."""
    main, lane, bad = two_checkouts
    monkeypatch.chdir(lane)

    assert engine.cmd_identity(_identity_args()) == 1
    out = capsys.readouterr().out
    assert f"# Repository read: {lane.resolve()}" in out
    assert bad[:12] in out
    assert "problems: 1" in out


def test_audit_in_the_primary_checkout_still_reads_the_primary(two_checkouts, monkeypatch, capsys):
    """The control: main's own history is clean, so the same command passes there."""
    main, lane, bad = two_checkouts
    monkeypatch.chdir(main)

    assert engine.cmd_identity(_identity_args()) == 0
    out = capsys.readouterr().out
    assert f"# Repository read: {main.resolve()}" in out
    assert bad[:12] not in out


def test_audit_honours_an_explicit_project(two_checkouts, tmp_path, monkeypatch, capsys):
    """``--project`` still wins over cwd, so an operator can name the repository."""
    main, lane, bad = two_checkouts
    monkeypatch.chdir(tmp_path)

    assert engine.cmd_identity(_identity_args(project=str(main))) == 0
    out = capsys.readouterr().out
    assert f"# Repository read: {main.resolve()}" in out
