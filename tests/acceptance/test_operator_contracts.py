"""Acceptance: the operator-visible contract of eight engine areas.

One probe per area, each driven through the installed CLI as a subprocess - never
by importing the engine - because these are the promises a person relies on when
they run the tool: what `audit` says about a fresh workspace, what `throughput`
reports before there is history, how `ci_scope` classifies a file, how `criteria`
refuses an unknown id, how `identity` treats a personal author, that a ledger
survives a write and exports, that `archive`/`decision` answer by id, and that the
privacy gate refuses a planted credential.

Owner: reviewer. Layer: acceptance. Area: one case per area (audit, baseline,
ci-scope, criteria, identity, ledger, m19-records, security).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from cli_harness import REPO_ROOT, assert_ok, cli

ROSTER = "ceo,developer-1,reviewer-1"
ARCHIVE = """# ARCHIVE - reviewed results

## T-0001 - first deliverable (developer)

- status: done
- result: merged

## T-0002 - second deliverable (developer)

- status: done
- result: merged
"""


def workspace(tmp_path: Path) -> Path:
    project = tmp_path / "SampleProject"
    project.mkdir()
    assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    return project


def git_project(tmp_path: Path) -> Path:
    project = tmp_path / "GitProject"
    project.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "Developer",
        "GIT_AUTHOR_EMAIL": "developer@agents.nidvue.com",
        "GIT_COMMITTER_NAME": "Developer",
        "GIT_COMMITTER_EMAIL": "developer@agents.nidvue.com",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    assert_ok(cli(project, ["init", "--agents", ROSTER], env=env))
    return project


def test_audit_reports_every_section_on_a_fresh_workspace(tmp_path: Path) -> None:
    """The audit is the operator's health view: every section is present, named."""
    project = workspace(tmp_path)
    result = cli(project, ["audit"])
    assert result.returncode in (0, 1), result.output
    for section in ("## done without evidence", "## memory caps", "## blocked tasks"):
        assert section in result.output, (section, result.output[:400])


def test_throughput_reports_a_zero_sample_before_there_is_history(tmp_path: Path) -> None:
    """No history is a measured zero, not a crash and not an invented number."""
    project = workspace(tmp_path)
    report = json.loads(assert_ok(cli(project, ["throughput", "--json"])).stdout)
    assert report["ledger_records"] >= 0
    assert report["review"]["count"] == 0
    assert report["review"]["p50_minutes"] is None
    assert "n=" in assert_ok(cli(project, ["throughput"])).stdout


def test_ci_scope_classifies_a_prose_and_a_code_path() -> None:
    """The classifier answers the one question CI asks: does this change ship code?"""

    def classify(path: str) -> str:
        done = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "ci_scope.py"), "--file", path],
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()

    assert "prose" in classify("docs/guide/install.md")
    assert "code" in classify("src/teamwork/engine.py")


def test_criteria_refuse_an_unknown_id_with_a_named_error(tmp_path: Path) -> None:
    """A wrong id is a refusal a reader can act on, not a traceback."""
    project = workspace(tmp_path)
    assert_ok(
        cli(
            project,
            ["criteria", "add", "--id", "AC-1", "--text", "one", "--owner", "ceo", "--by", "CEO"],
        )
    )
    listed = cli(project, ["criteria", "list"])
    assert "AC-1" in listed.output
    refused = cli(project, ["criteria", "verify", "AC-99", "--by", "Reviewer-1"])
    assert refused.returncode == 1
    assert "no criterion 'AC-99'" in refused.output


def test_identity_audit_refuses_a_personal_author(tmp_path: Path) -> None:
    """The commit-identity rule has a gate: a personal author fails, a role passes."""
    project = git_project(tmp_path)
    (project / "feature.txt").write_text("done\n", encoding="utf-8")
    personal = {
        "GIT_AUTHOR_NAME": "Ping Operator",
        "GIT_AUTHOR_EMAIL": "ping@operator.example",
        "GIT_COMMITTER_NAME": "Ping Operator",
        "GIT_COMMITTER_EMAIL": "ping@operator.example",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    subprocess.run(["git", "-C", str(project), "add", "feature.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(project), "commit", "-q", "-m", "chore: hand edit"],
        check=True,
        env=personal,
    )
    refused = cli(project, ["identity", "--audit", "--range", "HEAD"])
    assert refused.returncode == 1, refused.output
    assert "ping@operator.example" in refused.output, refused.output
    assert "problems: 0" not in refused.output


def test_a_ledger_write_verifies_and_exports(tmp_path: Path) -> None:
    """The audit trail survives its own write and can be exported for a reader."""
    project = workspace(tmp_path)
    assert_ok(
        cli(
            project,
            ["criteria", "add", "--id", "AC-1", "--text", "one", "--owner", "ceo", "--by", "CEO"],
        )
    )
    assert_ok(cli(project, ["ledger", "verify"]))
    exported = assert_ok(cli(project, ["ledger", "export"]))
    assert "manifest" in exported.output
    manifest = project / "docs" / "Team" / "AuditManifest.json"
    assert manifest.is_file()
    assert json.loads(manifest.read_text(encoding="utf-8"))["team_id"]


def test_archive_and_decision_answer_by_id(tmp_path: Path) -> None:
    """The records are read by id, so a reader never has to open the whole file."""
    project = workspace(tmp_path)
    (project / "docs" / "Team" / "Archive.md").write_text(ARCHIVE, encoding="utf-8")
    one = assert_ok(cli(project, ["archive", "--task", "T-0001"])).output
    assert "T-0001" in one and "T-0002" not in one
    assert_ok(
        cli(
            project,
            [
                "decision",
                "add",
                "--by",
                "CEO",
                "--title",
                "a ruling",
                "--decision",
                "do the thing",
                "--why",
                "because",
                "--evidence",
                "true @HEAD -> ok",
                "--falsify",
                "a counter-example",
            ],
        )
    )
    listed = assert_ok(cli(project, ["decision", "list"])).output
    assert "D-" in listed and "a ruling" in listed


def test_the_privacy_gate_refuses_a_planted_credential(tmp_path: Path) -> None:
    """A credential in the tree is a refusal, and the value is never printed."""
    project = tmp_path / "ScanProject"
    project.mkdir()
    subprocess.run(["git", "-C", str(project), "init", "-q", "-b", "main"], check=True)
    (project / "notes.md").write_text("key: " + "ghp_" + "a" * 36 + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", "notes.md"], check=True)
    done = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "privacy_scan.py"),
            "--staged",
            "--root",
            str(project),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1, done.stdout
    assert "api-token" in done.stdout
    assert "ghp_" + "a" * 36 not in done.stdout, "the matched value must never be printed"
