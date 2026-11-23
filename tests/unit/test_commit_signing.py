"""Commit signing: one resolver, threaded into every engine-made commit."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from teamwork import engine, gitutil


def _git(repo: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True, text=True, check=False
    )


def _repo(tmp_path: Path, gpgsign: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test Lane")
    _git(repo, "config", "user.email", "lane@agents.example")
    _git(repo, "config", "commit.gpgsign", "false")
    if gpgsign is not None:
        _git(repo, "config", "commit.gpgsign", gpgsign)
    return repo


def _commit(repo: Path, name: str) -> str:
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", "--", name)
    made = _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", name)
    assert made.returncode == 0, made.stderr
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def test_sign_args_follow_the_repository_when_the_team_says_nothing(tmp_path):
    assert gitutil.sign_args(_repo(tmp_path / "plain")) == []
    assert gitutil.sign_args(_repo(tmp_path / "signed", "true")) == ["-S"]
    assert gitutil.sign_args(_repo(tmp_path / "off", "false")) == []
    assert gitutil.sign_args(_repo(tmp_path / "unset", "off")) == []


def test_the_team_setting_overrides_the_repository_both_ways(tmp_path):
    plain = _repo(tmp_path / "plain")
    assert gitutil.sign_args(plain, "true") == ["-S"]
    assert gitutil.sign_args(plain, "yes") == ["-S"]
    assert gitutil.sign_args(plain, "false") == []
    signed = _repo(tmp_path / "signed", "true")
    assert gitutil.sign_args(signed, "false") == []
    assert gitutil.sign_args(signed, "true") == ["-S"]
    assert gitutil.sign_args(signed, "maybe") == ["-S"]


def test_an_unreadable_team_setting_falls_back_to_the_repository(tmp_path):
    assert engine._sign_args(_repo(tmp_path / "plain")) == []
    assert engine._sign_args(_repo(tmp_path / "signed", "true")) == ["-S"]


def test_every_engine_record_commit_carries_the_signature_args():
    lines = Path(engine.__file__).read_text(encoding="utf-8").splitlines()
    commits = [index for index, line in enumerate(lines) if '"commit", "-q"' in line]
    assert len(commits) >= 6, commits
    for index in commits:
        window = lines[max(0, index - 3) : index]
        assert any("_sign_args(" in line for line in window), (
            f"engine.py:{index + 1} commits without _sign_args"
        )


def test_audit_reports_an_unsigned_commit_when_signing_is_required(tmp_path, capsys):
    repo = _repo(tmp_path, "true")
    _commit(repo, "one")
    _git(repo, "checkout", "-q", "-b", "lane")
    _commit(repo, "two")
    assert engine._audit_unsigned_commits_on_the_reviewed_range(repo, [], None) == 1
    assert "HIGH signing" in capsys.readouterr().out


def test_audit_stays_quiet_when_signing_is_not_configured(tmp_path, capsys):
    repo = _repo(tmp_path)
    _commit(repo, "one")
    _git(repo, "checkout", "-q", "-b", "lane")
    _commit(repo, "two")
    assert engine._audit_unsigned_commits_on_the_reviewed_range(repo, [], None) == 0
    assert "HIGH signing" not in capsys.readouterr().out


@pytest.mark.skipif(
    os.name == "nt",
    reason="the git shim is a POSIX script; argv threading is covered on every POSIX cell",
)
def test_ensure_repo_threads_the_signature_args_into_its_initial_commit(tmp_path, monkeypatch):
    """The init call site itself, not the source text: a fake git records the argv.

    ``ensure_repo`` is what a fresh project runs first, so a broken argument list
    there breaks ``init`` for every project. The shim logs the argv the engine
    built and then drops ``-S`` before exec'ing the real git, so the commit lands
    on a host with no signing key while the assertion still sees the ``-S``.
    """
    import os
    import shutil

    project = tmp_path / "project"
    project.mkdir()
    (project / "Settings.json").write_text('{"SignCommits": "true"}', encoding="utf-8")
    log = tmp_path / "git-argv.log"
    shim = tmp_path / "shim"
    shim.mkdir()
    real_git = shutil.which("git")
    assert real_git, "git must be on PATH for this test"
    script = shim / "git"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        f"open({str(log)!r}, 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + '\\n')\n"
        f"os.execv({real_git!r}, [{real_git!r}] + [a for a in sys.argv[1:] if a != '-S'])\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(shim) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("TEAMWORK_STAR_ONCE", "off")

    assert engine.ensure_repo(project, commit=True, quiet=True) == 0
    invocations = log.read_text(encoding="utf-8").splitlines()
    commits = [line.split() for line in invocations if "commit" in line.split()]
    assert commits, invocations
    assert all("-S" in argv for argv in commits), commits


def test_an_unreadable_team_setting_never_refuses_a_commit(tmp_path):
    repo = _repo(tmp_path / "repo", "false")
    (repo / "Settings.json").write_text("{not json", encoding="utf-8")
    assert engine._sign_args(repo) == []
    (repo / "Settings.json").write_text('{"SignCommits": "true"}', encoding="utf-8")
    assert engine._sign_args(repo) == ["-S"]
