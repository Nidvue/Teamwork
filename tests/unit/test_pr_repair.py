"""`pr set` repairs a PR record whose status no merge can update any more (T-0128).

P-0010 landed (its review note records "merged into main at 47db23d" and its
``merge_commit`` is f91bf1b) but its ``status`` stayed ``approved``, so ``audit``
reported "approved 23d ago, not merged" on every run and the close gate could
never reach zero problems. ``pr merge`` cannot fix it: the branch it would read
is already deleted. The repair is the record-only path, and it is deliberately
narrow - the review must have passed, the reason is mandatory, and the ledger
keeps the old and the new status.

Pinned here: the repair is accepted with a reason and recorded as ``pr.repair``
with both statuses; it is refused without a reason, refused when the review did
not pass, refused when ``merged`` names no revision or a revision that is not a
full 40-hex sha of a commit this clone carries; a second call is a no-op; and the
audit line it exists for disappears.
"""

from __future__ import annotations

import subprocess
from datetime import date, timedelta
from pathlib import Path

from tests.gitenv import child_env

from teamwork import engine, records

ROSTER = "ceo,developer-1,reviewer-1,reviewer-2"
STALE_DAYS = 40


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def git_repo(project: Path) -> str:
    """A one-commit repository: the audit's branch/PR section needs a git repo."""
    env = child_env(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )

    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(project), *args], capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    run("init", "-q", "-b", "main")
    (project / ".gitignore").write_text(".pi/\nAGENTS.md\ndocs/\n", encoding="utf-8")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    run("add", ".")
    run("commit", "-qm", "base")
    return run("rev-parse", "HEAD")


def seed(cli, project: Path, *, review_status: str = "passed") -> Path:
    """A workspace whose one task is done and whose one PR record is stale.

    The PR is ``approved`` and ``updated`` well past the stale window, which is
    exactly the shape ``audit`` reports forever: the work is in the base, the
    record never moved.
    """
    landed = git_repo(project)
    assert cli("--project", project, "init", "--agents", ROSTER) == 0
    root = team_root(project)
    task = engine.new_task("a landed deliverable whose PR record stalled")
    task["priority"] = "P0"
    task["status"] = "done"
    task["claimed_by"] = "Developer-1"
    task["branch"] = "developer-1/t-0001-a-landed-deliverable"
    task["base"] = "main"
    task["merge_commit"] = landed
    task["review_status"] = review_status
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
    return root


def landed(root: Path) -> str:
    """The revision the seeded task records as merged - what a repair names."""
    return engine.parse_tasks(engine.task_file(root, "developer"))[0]["merge_commit"]


def only_pr(root: Path) -> dict:
    prs = engine.parse_reviews(engine.reviews_path(root))
    assert len(prs) == 1
    return prs[0]


def repairs(root: Path) -> list:
    return [r for r in engine.ledger_read(root) if r.get("action") == "pr.repair"]


def audit_lines(cli, project: Path, capsys) -> str:
    capsys.readouterr()
    cli("--project", project, "audit")
    return capsys.readouterr().out


def test_the_audit_reports_the_stale_record_before_any_repair(cli, project, capsys) -> None:
    """The baseline the command exists for: the line is there on its own."""
    seed(cli, project)

    assert "P-0001 approved" in audit_lines(cli, project, capsys)
    assert "not merged" in audit_lines(cli, project, capsys)


def test_a_repair_with_a_reason_moves_the_record_and_is_ledgered(cli, project) -> None:
    root = seed(cli, project)

    assert (
        cli(
            "--project",
            project,
            "pr",
            "set",
            "--pr",
            "P-0001",
            "--status",
            "merged",
            "--merge-commit",
            landed(root),
            "--by",
            "Reviewer-1",
            "--force",
            "the review note records the merge at 47db23d; the branch is gone",
        )
        == 0
    )

    pr = only_pr(root)
    assert pr["status"] == "merged"
    assert pr["merge_commit"] == landed(root)
    assert pr["updated"] == date.today().isoformat()
    assert any("approved -> merged" in note for note in pr["notes"])
    events = repairs(root)
    assert len(events) == 1
    assert events[0]["actor"] == "Reviewer-1"
    assert f"approved -> merged at {landed(root)}" in events[0]["detail"]
    assert "the branch is gone" in events[0]["detail"]


def test_the_repair_clears_the_audit_line(cli, project, capsys) -> None:
    """The acceptance case: after the repair the audit no longer names P-0001."""
    root = seed(cli, project)
    assert "P-0001 approved" in audit_lines(cli, project, capsys)

    assert (
        cli(
            "--project",
            project,
            "pr",
            "set",
            "--pr",
            "P-0001",
            "--status",
            "merged",
            "--merge-commit",
            landed(root),
            "--by",
            "Reviewer-1",
            "--force",
            "the work landed and the record stalled",
        )
        == 0
    )

    assert "P-0001 approved" not in audit_lines(cli, project, capsys)


def test_a_repair_without_a_reason_is_refused(cli, project, capsys) -> None:
    root = seed(cli, project)
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        landed(root),
        "--by",
        "Reviewer-1",
    )

    assert code == 2
    assert "--force needs a reason" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_repair_is_refused_when_the_review_did_not_pass(cli, project, capsys) -> None:
    root = seed(cli, project, review_status="pending")
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        landed(root),
        "--by",
        "Reviewer-1",
        "--force",
        "looks merged to me",
    )

    assert code == 2
    assert "review_status=pending" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_merged_without_a_merge_commit_is_refused(cli, project, capsys) -> None:
    root = seed(cli, project)
    capsys.readouterr()

    code = cli(
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
        "--force",
        "the record stalled",
    )

    assert code == 2
    assert "--merge-commit" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_fabricated_merge_revision_is_refused(cli, project, capsys) -> None:
    """A well-shaped sha this clone does not carry is refused, not recorded."""
    root = seed(cli, project)
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        "deadbeef" * 5,
        "--by",
        "Reviewer-1",
        "--force",
        "it merged, trust me",
    )

    assert code == 2
    assert "does not resolve to a commit" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_short_sha_is_refused(cli, project, capsys) -> None:
    """M-0019: an abbreviated sha is ambiguous, so it is not a landing fact."""
    root = seed(cli, project)
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        landed(root)[:7],
        "--by",
        "Reviewer-1",
        "--force",
        "probe: the abbreviated sha of the landed commit",
    )

    assert code == 2
    assert "is not a full commit sha" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_ref_name_is_refused(cli, project, capsys) -> None:
    """M-0019: a ref name moves, so it cannot name the revision that landed."""
    root = seed(cli, project)

    for ref in ("main", "HEAD"):
        capsys.readouterr()
        code = cli(
            "--project",
            project,
            "pr",
            "set",
            "--pr",
            "P-0001",
            "--status",
            "merged",
            "--merge-commit",
            ref,
            "--by",
            "Reviewer-1",
            "--force",
            f"probe: {ref} is a ref name",
        )
        assert code == 2
        assert "is not a full commit sha" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_ledger_witnessed_revision_that_is_not_in_the_clone_is_refused(
    cli, project, capsys
) -> None:
    """M-0019 supersedes the ledger witness: the ledger prose is not a commit."""
    root = seed(cli, project)
    engine.ledger_append(
        root,
        "pr.merge",
        "Reviewer-1",
        "T-0001",
        "P-0001 developer-1/t-0001 -> main at 47db23d",
        "47db23d",
    )
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        "47db23d",
        "--by",
        "Reviewer-1",
        "--force",
        "probe: the ledger records the merge; the rebuilt history no longer carries it",
    )

    assert code == 2
    assert "is not a full commit sha" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_a_word_from_a_merge_note_is_not_a_revision(cli, project, capsys) -> None:
    """F1 round 1: a token inside a ``pr.merge`` detail is prose, not a commit."""
    root = seed(cli, project)
    engine.ledger_append(
        root,
        "pr.merge",
        "Reviewer-1",
        "T-0001",
        "P-0001 developer-1/t-0001-work -> main at 9c1d5e7",
        "9c1d5e7",
    )
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        "work",
        "--by",
        "Reviewer-1",
        "--force",
        "probe: a word from the detail is not a revision",
    )

    assert code == 2
    assert "'work' is not a full commit sha" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []


def test_closing_a_stale_record_needs_no_revision(cli, project) -> None:
    """``closed`` is a terminal state without a landing revision; the reason is enough."""
    root = seed(cli, project)

    assert (
        cli(
            "--project",
            project,
            "pr",
            "set",
            "--pr",
            "P-0001",
            "--status",
            "closed",
            "--by",
            "Reviewer-1",
            "--force",
            "superseded by the rework on T-0002",
        )
        == 0
    )

    pr = only_pr(root)
    assert pr["status"] == "closed"
    assert pr["merge_commit"] == landed(root), "a repair to closed keeps the recorded revision"


def test_a_second_repair_is_a_no_op(cli, project, capsys) -> None:
    """The second call must not twin the ledger event or rewrite the record."""
    root = seed(cli, project)
    argv = (
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "merged",
        "--merge-commit",
        landed(root),
        "--by",
        "Reviewer-1",
        "--force",
        "the work landed and the record stalled",
    )
    assert cli(*argv) == 0
    first = only_pr(root)
    capsys.readouterr()

    assert cli(*argv) == 0

    assert "already merged" in capsys.readouterr().out
    assert only_pr(root) == first
    assert len(repairs(root)) == 1


def test_an_unknown_pr_is_refused(cli, project, capsys) -> None:
    seed(cli, project)
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "pr",
            "set",
            "--pr",
            "P-0999",
            "--status",
            "closed",
            "--by",
            "Reviewer-1",
            "--force",
            "no such record",
        )
        == 1
    )
    assert "no PR 'P-0999'" in capsys.readouterr().err


def test_an_unknown_repairer_is_refused(cli, project, capsys) -> None:
    """The repair is accountable: a name that is not an instance is refused."""
    root = seed(cli, project)
    capsys.readouterr()

    code = cli(
        "--project",
        project,
        "pr",
        "set",
        "--pr",
        "P-0001",
        "--status",
        "closed",
        "--by",
        "Ghost-9",
        "--force",
        "no such record",
    )

    assert code == 1
    assert "unknown repairer 'Ghost-9'" in capsys.readouterr().err
    assert only_pr(root)["status"] == "approved"
    assert repairs(root) == []
