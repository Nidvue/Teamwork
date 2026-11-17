"""A pass lands the merge, and an unlandable tree names its blocker (T-0139).

A verdict is only worth recording if the revision it verified can reach the base
branch. The merge runs in the work tree that holds the base, and git refuses to
check out that branch over uncommitted work, so a dirty work tree is the one
condition that turns a recorded pass into approved-but-unmerged work: the task
reads ``done``, the PR reads ``approved``, the archive says ``pending``, and
nothing re-runs the merge.

So the check moves in front of the verdict: a pass whose merge would be refused
records nothing and names the paths that block it. The helper that lands an
already-recorded pass names them too, instead of the generic "fix the cause".
"""

from __future__ import annotations

from pathlib import Path

from test_pr_merge_base_advance import (
    add_task,
    commit_self_check_and_open,
    init_workspace,
    team_root,
)

from teamwork import engine


def reviews(project: Path) -> list:
    return engine.parse_reviews(team_root(project) / "Reviews.md")


def ship(cli, project: Path) -> Path:
    """One task through branch, commit, self-check and an open PR."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the dirty-tree blocker fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")
    return work


def dirty(project: Path, name: str) -> Path:
    """Uncommitted work in the base work tree, outside the merge's own records."""
    path = project / name
    path.write_text("a lane's work in progress\n", encoding="utf-8")
    return path


def pass_review(cli, project: Path, *extra: str) -> int:
    return cli(
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
    )


def test_a_dirty_work_tree_records_no_verdict_and_names_the_blocker(cli, project, capsys) -> None:
    """The pass is refused before the verdict: nothing is approved, nothing says pending."""
    ship(cli, project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    dirty(project, "blocker.txt")

    capsys.readouterr()
    code = pass_review(cli, project)
    err = capsys.readouterr().err

    assert code != 0, "a pass that cannot land must not be recorded"
    assert "blocker.txt" in err, err
    assert "no verdict was recorded" in err, err
    assert reviews(project)[0]["status"] == "open", "the PR must stay unapproved"
    tasks = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")
    assert tasks[0]["review_status"] != "passed", "a refused pass must record no verdict"
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before


def test_the_merge_own_records_are_not_a_blocker(cli, project, capsys) -> None:
    """A dirty ``docs/`` record belongs to the merge, so it is committed, not refused."""
    ship(cli, project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    (project / "docs" / "Team" / "Board.md").write_text("# board\n", encoding="utf-8")

    capsys.readouterr()
    assert pass_review(cli, project) == 0
    capsys.readouterr()

    assert engine.run_git(project, "rev-parse", "main").stdout.strip() != main_before
    assert reviews(project)[0]["status"] == "merged"


def test_merge_after_pass_names_the_blocker_instead_of_a_generic_retry(
    cli, project, capsys
) -> None:
    """The already-recorded pass path names the paths and keeps the verdict."""
    ship(cli, project)
    assert pass_review(cli, project, "--no-merge") == 0
    root = team_root(project)
    dirty(project, "blocker.txt")
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    assert engine.merge_after_pass(root, "developer", tasks[0], "reviewer-1") is False
    out = capsys.readouterr().out

    assert "blocker.txt" in out, out
    assert "fix the cause" not in out, out
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    assert tasks[0]["review_status"] == "passed", "the verdict must survive a refused merge"
    assert tasks[0]["merge_commit"] == ""


def test_the_blocker_list_is_empty_on_a_clean_tree_and_stable_on_a_second_call(
    cli, project
) -> None:
    """No dirt means no blocker, and asking twice answers the same list."""
    ship(cli, project)
    root = team_root(project)

    assert engine.merge_tree_blockers(root, project, "main") == []
    dirty(project, "blocker.txt")
    assert engine.merge_tree_blockers(root, project, "main") == ["blocker.txt"]
    assert engine.merge_tree_blockers(root, project, "main") == ["blocker.txt"]
