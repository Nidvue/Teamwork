"""`pr set` repairs a stalled PR record through the real CLI (T-0015).

Layer ``integration``, area ``pr-repair``. The unit layer pins the decision table
in-process; this layer runs the command as a *process* against a real git
repository and a real ledger, because the facts it writes are the ones the close
gate reads:

1. ``audit`` reports the stale record - the reason the repair exists.
2. ``pr set --status merged --merge-commit <40-hex> --force <reason>`` moves the
   record to ``merged``, keeps the old status in the notes and appends one
   ``pr.repair`` ledger line carrying the revision.
3. ``audit`` no longer reports it, and ``ledger verify`` still passes: the
   repair line is chained like every other record.
4. A second call is a no-op - exit 0, no second ledger line, record unchanged.
5. A ref name passed as ``--merge-commit`` is refused at the argv boundary
   (exit 2) with the record and the ledger untouched.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from tests.gitenv import child_env

from teamwork import engine, records

REPO_ROOT = Path(__file__).resolve().parents[2]
ROSTER = "ceo,developer-1,reviewer-1,reviewer-2"
STALE_DAYS = 40
REASON = "the branch is gone and the work is in main; the record never moved"


def env() -> dict:
    return child_env(
        PYTHONPATH=str(REPO_ROOT / "src"),
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )


def git(project: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(project), *argv],
        capture_output=True,
        text=True,
        env=env(),
        check=False,
    )
    assert done.returncode == 0, f"git {' '.join(argv)}: {done.stderr}"
    return done.stdout.strip()


def tw(project: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "teamwork", *argv],
        cwd=project,
        capture_output=True,
        text=True,
        env=env(),
        timeout=180,
        check=False,
    )


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def landed_revision(project: Path) -> str:
    (project / ".gitignore").write_text(".pi/\nAGENTS.md\ndocs/\n", encoding="utf-8")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    git(project, "init", "-q", "-b", "main")
    git(project, "add", ".")
    git(project, "commit", "-qm", "base")
    return git(project, "rev-parse", "HEAD")


def seed(project: Path) -> str:
    """A team whose one PR landed but whose record is still ``approved``.

    ``pr merge`` cannot produce this shape - it is what a branch deleted before
    the record moved leaves behind - so the records are written directly and
    every *repair* step below goes through the CLI.
    """
    project.mkdir()
    landed = landed_revision(project)
    assert tw(project, "--project", project, "init", "--agents", ROSTER).returncode == 0
    root = team_root(project)

    task = engine.new_task("a landed deliverable whose PR record stalled")
    task["priority"] = "P0"
    task["status"] = "done"
    task["claimed_by"] = "Developer-1"
    task["branch"] = "developer-1/t-0001-a-landed-deliverable"
    task["base"] = "main"
    task["merge_commit"] = landed
    task["review_status"] = "passed"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")

    pr = records.new_pr(
        "a landed deliverable",
        id="P-0001",
        task="T-0001",
        role="developer",
        author="Developer-1",
        branch="developer-1/t-0001-a-landed-deliverable",
        base="main",
        reviewer="Reviewer-1",
        merge_commit=landed,
    )
    pr["status"] = "approved"
    pr["updated"] = (date.today() - timedelta(days=STALE_DAYS)).isoformat()
    records.write_reviews(engine.reviews_path(root), [pr])
    return landed


def only_pr(project: Path) -> dict:
    prs = engine.parse_reviews(engine.reviews_path(team_root(project)))
    assert len(prs) == 1
    return prs[0]


def repairs(project: Path) -> list:
    return [
        record
        for record in engine.ledger_read(team_root(project))
        if record.get("action") == "pr.repair"
    ]


def repair(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return tw(
        project,
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--by",
        "Reviewer-1",
        *extra,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "SampleProject"
    seed(path)
    return path


def test_the_stale_record_is_reported_before_the_repair(project: Path) -> None:
    done = tw(project, "--project", project, "audit")

    assert f"- P-0001 approved {STALE_DAYS}d ago, not merged" in done.stdout, done.stdout
    assert only_pr(project)["status"] == "approved"
    assert repairs(project) == []


def test_the_repair_moves_the_record_and_is_ledgered(project: Path) -> None:
    landed = git(project, "rev-parse", "HEAD")
    done = repair(project, "--merge-commit", landed, "--force", REASON)

    assert done.returncode == 0, done.stderr
    assert f"# repaired P-0001: approved -> merged at {landed}" in done.stdout, done.stdout
    record = only_pr(project)
    assert record["status"] == "merged"
    assert record["merge_commit"] == landed
    assert any("status repaired approved -> merged" in note for note in record["notes"])

    entries = repairs(project)
    assert len(entries) == 1
    assert landed in str(entries[0]), entries[0]


def test_the_audit_line_disappears_and_the_ledger_still_verifies(project: Path) -> None:
    landed = git(project, "rev-parse", "HEAD")
    assert repair(project, "--merge-commit", landed, "--force", REASON).returncode == 0

    audit = tw(project, "--project", project, "audit")
    assert "P-0001 approved" not in audit.stdout, audit.stdout

    verify = tw(project, "--project", project, "ledger", "verify")
    assert verify.returncode == 0, verify.stdout + verify.stderr


def test_a_second_repair_is_a_no_op(project: Path) -> None:
    landed = git(project, "rev-parse", "HEAD")
    assert repair(project, "--merge-commit", landed, "--force", REASON).returncode == 0
    before = only_pr(project)

    again = repair(project, "--merge-commit", landed, "--force", REASON)

    assert again.returncode == 0, again.stderr
    assert "# P-0001 is already merged; nothing to repair" in again.stdout, again.stdout
    assert only_pr(project) == before
    assert len(repairs(project)) == 1


def test_a_ref_name_as_the_landed_revision_is_refused(project: Path) -> None:
    done = repair(project, "--merge-commit", "main", "--force", REASON)

    assert done.returncode == 2, done.stdout + done.stderr
    assert "is not a full commit sha" in done.stderr, done.stderr
    assert only_pr(project)["status"] == "approved"
    assert repairs(project) == []
