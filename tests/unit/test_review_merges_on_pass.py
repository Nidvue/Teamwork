"""A passing review merges the PR at once and closes its branch (T-0043).

The two-stage gate used to take two commands and two Reviewer lanes: one passed
the verdict, then a different Reviewer had to run ``pr merge``. That made the
merge a second queue - the passing lane recorded the verdict and moved on, and
the branch sat approved-but-unmerged until another lane picked it up. Measured
before the change: the review queue held approved PRs whose branches were still
open, and the roster's reviewer count was the throughput ceiling twice over.

So a pass is the merge trigger. The lane that verified the revision lands it and
deletes the branch; independence is enforced against the **author** (nobody
reviews or merges their own work), not against a second Reviewer.
"""

from __future__ import annotations

from pathlib import Path

from test_pr_merge_base_advance import (
    add_task,
    commit_self_check_and_open,
    committed_archive,
    init_workspace,
    rework_records,
    team_root,
)

from teamwork import engine


def reviews(project: Path) -> list:
    return engine.parse_reviews(team_root(project) / "Reviews.md")


def pass_review(cli, project: Path, *extra: str) -> None:
    argv = [
        "--project",
        project,
        "review",
        "developer",
        "T-0001",
        "--by",
        "reviewer-1",
        "--result",
        "pass",
        "--evidence",
        "pytest @HEAD -> 7 passed",
        *extra,
    ]
    assert cli(*argv) == 0


def ship(cli, project: Path) -> Path:
    """One task through branch, commit, self-check and an open PR."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the merge-on-pass fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    return work


def test_a_pass_merges_the_pr_in_the_same_command(cli, project, capsys) -> None:
    """The verified revision lands on main; the branch is gone afterwards."""
    ship(cli, project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    branch = reviews(project)[0]["branch"]
    assert engine.branch_exists(project, branch)

    capsys.readouterr()
    pass_review(cli, project)
    out = capsys.readouterr().out

    main_after = engine.run_git(project, "rev-parse", "main").stdout.strip()
    assert main_after != main_before, "the pass did not advance the base branch"
    assert "# merged P-0001" in out, out
    assert "# deleted branch" in out, out
    assert not engine.branch_exists(project, branch), "a merged branch must not survive"
    assert reviews(project)[0]["status"] == "merged"


def test_a_pass_records_the_real_merge_revision_on_the_task(cli, project, capsys) -> None:
    """``loop`` reads the task record, so the merge sha has to be there."""
    ship(cli, project)
    pass_review(cli, project)
    capsys.readouterr()

    tasks = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")
    task = tasks[0]
    assert task["status"] == "done"
    assert task["review_status"] == "passed"
    assert task["merge_commit"], "the task has no merge revision after a passing review"
    assert (
        engine.run_git(
            project, "merge-base", "--is-ancestor", task["merge_commit"], "main"
        ).returncode
        == 0
    ), "the recorded merge revision is not in the base branch"


def test_a_pass_records_the_merge_in_the_archive_on_the_base(cli, project, capsys) -> None:
    """The accepted-result entry names the merge revision the base actually holds."""
    ship(cli, project)
    branch = reviews(project)[0]["branch"]
    pass_review(cli, project)
    capsys.readouterr()

    sha = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")[0][
        "merge_commit"
    ]
    archive = committed_archive(project)
    assert f"- branch / merge: {branch} / {sha}" in archive, archive[-2000:]
    assert "pending" not in archive.split(f"- branch / merge: {branch} / ")[1][:10]
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_keep_branch_lands_the_work_and_leaves_the_branch(cli, project, capsys) -> None:
    """``--keep-branch`` opts out of the deletion only, not out of the merge."""
    ship(cli, project)
    branch = reviews(project)[0]["branch"]
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    pass_review(cli, project, "--keep-branch")
    out = capsys.readouterr().out

    assert engine.run_git(project, "rev-parse", "main").stdout.strip() != main_before
    assert "# deleted branch" not in out, out
    assert engine.branch_exists(project, branch)


def test_no_merge_records_the_verdict_without_landing_it(cli, project, capsys) -> None:
    """The escape hatch: the pass stands, the branch stays open, the message says so."""
    ship(cli, project)
    branch = reviews(project)[0]["branch"]
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    pass_review(cli, project, "--no-merge")
    out = capsys.readouterr().out

    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
    assert "--no-merge" in out and "pr merge --pr P-0001" in out, out
    assert engine.branch_exists(project, branch)
    assert reviews(project)[0]["status"] == "approved"
    assert reviews(project)[0]["merge_commit"] == ""


def test_a_failed_merge_keeps_the_verdict_and_names_the_retry(cli, project, capsys) -> None:
    """A pass that cannot land is reported, never lost and never silently 'done'."""
    ship(cli, project)
    # a base no local branch points at: the merge refuses before touching git
    rework_records(cli, project, base="0" * 40)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    pass_review(cli, project)
    out = capsys.readouterr().out

    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
    assert "the pass is recorded but the merge did not run" in out, out
    assert "NOT in the base branch yet" in out, out
    assert "pr merge --pr P-0001" in out, out
    assert reviews(project)[0]["status"] == "approved"
    tasks = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")
    assert tasks[0]["review_status"] == "passed", "the verdict must survive a failed merge"
    assert tasks[0]["merge_commit"] == ""


def test_the_author_still_cannot_pass_its_own_deliverable(cli, project, capsys) -> None:
    """Independence now rests on the author, so that guard must still bite."""
    ship(cli, project)
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest -> 7 passed",
        )
        == 1
    )
    assert "only the Reviewer role may review" in capsys.readouterr().err


def test_merge_after_pass_is_idempotent_on_a_merged_pr(cli, project, capsys) -> None:
    """Re-running the helper after the merge reports it and changes nothing."""
    ship(cli, project)
    pass_review(cli, project)
    capsys.readouterr()
    root = team_root(project)
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    main_after = engine.run_git(project, "rev-parse", "main").stdout.strip()

    assert engine.merge_after_pass(root, "developer", tasks[0], "reviewer-1") is True
    out = capsys.readouterr().out
    assert "already merged" in out, out
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_after


def test_a_deliverable_without_a_pr_still_passes(cli, project, capsys) -> None:
    """No PR means nothing to merge; the verdict is still recorded as done."""
    root = init_workspace(cli, project)
    assert (
        cli("--project", project, "task", "add", "developer", "docs only", "--priority", "P0") == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "links -> 0 issues",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "review") == 0
    )

    capsys.readouterr()
    pass_review(cli, project)
    out = capsys.readouterr().out

    assert "no PR to merge" in out, out
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    assert tasks[0]["status"] == "done"
    assert tasks[0]["review_status"] == "passed"
