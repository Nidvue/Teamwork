"""`--pr` accepts a PR id, a task id or a title, and they can collide.

A task reworked after a merge keeps the PR record of the branch already in the
base and gains a second one for the follow-up work. Every PR lookup on the merge
path therefore narrows on the branch the task is on now, so `pr merge --pr
T-0001` reaches the live record instead of the integrated one.
"""

from __future__ import annotations

from pathlib import Path

from test_context_economy import (
    committed_archive,
    init_workspace,
    pass_review,
    root_reviews,
    ship_and_open_pr,
    ship_task,
)
from test_context_economy import merge_pr as merge_first_pr

from teamwork import engine, records


def test_find_pr_exact_prefers_the_record_on_the_given_branch() -> None:
    """The same task id on two branches: only the named branch matches."""
    merged = records.new_pr(
        "first deliverable", id="P-0001", task="T-0001", branch="developer-1/t-0001-a"
    )
    merged["status"] = "merged"
    live = records.new_pr(
        "first deliverable", id="P-0002", task="T-0001", branch="developer-1/t-0001-b"
    )
    live["status"] = "approved"
    prs = [merged, live]

    assert records.find_pr_exact(prs, "T-0001") == 0, "without a branch the oldest record wins"
    assert records.find_pr_exact(prs, "T-0001", "developer-1/t-0001-b") == 1
    assert records.find_pr_exact(prs, "T-0001", "developer-1/t-0001-gone") is None


def test_pr_merge_by_task_id_reaches_the_live_record_after_a_rework(
    cli, project: Path, capsys
) -> None:
    """`pr merge --pr T-0001` merges the record the task is on now.

    A rework reuses the branch name, so the review pass reopens the same PR
    record rather than opening a second one; the merge then has to reach that
    reopened record on the task's current branch, not the copy that already
    names the first merge revision. The archive must gain the second revision
    while keeping the first.
    """
    root = init_workspace(cli, project, git=True)
    ship_and_open_pr(cli, project, root)
    pass_review(cli, project, capsys)
    first_sha = merge_first_pr(cli, project, capsys)
    first_prs = engine.parse_reviews(root_reviews(project))
    assert [pr["id"] for pr in first_prs] == ["P-0001"]

    assert (
        cli(
            "--project",
            project,
            "task",
            "reclaim",
            "developer",
            "T-0001",
            "--as",
            "developer-1",
            "--reason",
            "the reviewer asked for a follow-up",
        )
        == 0
    )
    assert cli("--project", project, "task", "set", "developer", "T-0001", "--status", "doing") == 0
    ship_task(cli, project, "T-0001", "first deliverable", "second_pass.txt")
    pass_review(cli, project, capsys)

    reopened = engine.parse_reviews(root_reviews(project))
    assert [pr["id"] for pr in reopened] == ["P-0001"], "the rework reuses the PR record"
    assert reopened[0]["status"] == "approved"
    live_branch = reopened[0]["branch"]

    # the task id also matches the record that already names the first merge;
    # the lookup narrows on the live branch, so the merge takes the reopened one
    assert cli("--project", project, "pr", "merge", "--pr", "T-0001", "--by", "reviewer-2") == 0
    assert f"# merged P-0001 {live_branch}" in capsys.readouterr().out

    merged = engine.parse_reviews(root_reviews(project))[0]
    assert merged["status"] == "merged"
    assert merged["merge_commit"] != first_sha
    archive = committed_archive(project)
    assert f"- branch / merge: {live_branch} / {first_sha}" in archive
    assert f"- branch / merge: {live_branch} / {merged['merge_commit']}" in archive
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_merge_by_an_ambiguous_task_id_is_refused_not_guessed() -> None:
    """Two lanes can each own a T-0001, so a bare task id is ambiguous.

    Reviewer-1 proved at 6c8d818 that `pr merge --pr T-0001` silently consumed
    the developer's record and answered "already merged" for the security lane,
    which could then never merge its own PR by task id. The hint lookup took the
    first role's branch, so the wrong record matched by construction.
    """
    prs = [
        {
            "id": "P-0001",
            "task": "T-0001",
            "title": "developer ship",
            "branch": "developer/t-0001-ship-it",
            "status": "open",
        },
        {
            "id": "P-0002",
            "task": "T-0001",
            "title": "security rescan",
            "branch": "securityauditor/t-0001-rescan",
            "status": "open",
        },
    ]
    assert engine._handle_is_ambiguous(prs, "T-0001") is True
    assert engine._handle_is_ambiguous(prs, "P-0002") is False
    # A merged record no longer competes: the live one is unambiguous.
    prs[1]["status"] = "merged"
    assert engine._handle_is_ambiguous(prs, "T-0001") is False
    # With a branch hint the right record is reached without any guessing.
    assert records.find_pr_exact(prs, "T-0001", "developer/t-0001-ship-it") == 0


def test_a_bare_task_id_skips_a_merged_sibling_instead_of_reporting_success(
    cli, project: Path, capsys
) -> None:
    """A merged record must not shadow its lane's live PR (round-3 MAJOR).

    Reviewer-3 measured at e82a6fe: developer-1's T-0001 was already merged, the
    security lane's T-0001 was approved, and `pr merge --pr T-0001` printed
    "# P-0001 already merged at <sha>" rc 0 while leaving the approved PR
    unmerged - so that lane could never land its work by task id. The lookup now
    prefers the single live record and only reports "already merged" when every
    candidate is dead.
    """
    dead = {
        "id": "P-0001",
        "task": "T-0001",
        "title": "developer ship",
        "branch": "developer-1/t-0001-ship-it",
        "status": "merged",
    }
    live = {
        "id": "P-0002",
        "task": "T-0001",
        "title": "security rescan",
        "branch": "securityauditor/t-0001-rescan",
        "status": "approved",
    }
    prs = [dead, live]
    assert engine._merge_pr_index(prs, "T-0001") == 1, "the live record wins, not the dead one"
    assert engine._merge_pr_index(prs, "P-0001") == 0, "an explicit PR id still resolves exactly"
    # Every candidate dead: the caller may report the merge it already has.
    live["status"] = "closed"
    assert engine._merge_pr_index(prs, "T-0001") == 0


def test_an_ambiguous_task_id_is_refused_through_the_cli(cli, project: Path, capsys) -> None:
    """The refusal itself must be measured, not only the predicate (MAJOR-2).

    Reviewer-3 showed at e82a6fe that disabling the CALLER (`if False and
    _handle_is_ambiguous(...)`) left the suite fully green, so nothing proved a
    merge is refused rather than guessed. This drives the CLI and asserts the
    non-zero exit, both PR ids in stderr and both records untouched.
    """
    init_workspace(cli, project, git=True)
    reviews = root_reviews(project)
    reviews.parent.mkdir(parents=True, exist_ok=True)
    reviews.write_text(
        "\n\n".join(
            [
                "## P-0001 · developer ship\n- status: approved\n- task: T-0001\n"
                "- role: developer\n- author: Developer\n"
                "- branch: developer-1/t-0001-ship-it\n- base: main",
                "## P-0002 · security rescan\n- status: approved\n- task: T-0001\n"
                "- role: security-auditor\n- author: SecurityAuditor\n"
                "- branch: securityauditor/t-0001-rescan\n- base: main",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli("--project", project, "pr", "merge", "--pr", "T-0001", "--by", "reviewer-2") != 0
    err = capsys.readouterr().err
    assert "names more than one open PR" in err, err
    assert "P-0001" in err and "P-0002" in err, err
    after = engine.parse_reviews(reviews)
    assert [pr["status"] for pr in after] == ["approved", "approved"], "nothing was merged"
