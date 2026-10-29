"""A pass is the merge, so the merge is proved before the verdict and the board is
written at the merge (T-0043).

P-0057 is the measurement. Its branch conflicted with ``docs/Team/Board.md`` in three
regions - each branch carried its own render of a generated file - and
``review --result pass`` recorded ``review_status=passed`` and then died inside
``_pr_merge`` on that conflict. The work stayed unlanded behind a green verdict,
which is the exact state rule 8 of the throughput contract forbids: "a pass must
never precede a merge that cannot happen" and "generated artifacts render at the
merge".

So this module locks the two halves of the fix:

* the mergeability probe. A pass (and ``pr merge``) runs
  ``git merge-tree --write-tree <base> <branch>`` first and, when it is non-zero,
  refuses with the conflicting paths and the rebase instruction - no verdict, no
  approved PR, no partial state. ``--force <reason>`` records a deliberate override
  instead of silently skipping the probe.
* the render at the merge. After a pass merges the branch and the records commit,
  the merging Reviewer re-renders ``docs/Team/Board.md`` from the role queues with
  the product's own renderer and commits it as ``chore(records): ...``. The branch's
  own board copy (if it carries one) is irrelevant: the merge overwrites it. A
  render that ``cannot`` be committed is reported loudly and never un-records the
  merge.

The tree is built through the CLI (``init``, ``task add``, ``branch start``,
``commit``, ``selfcheck``, ``pr open``) so a test fails when the commands stop
agreeing with each other and not only when one function is wrong. The anchored
board is written before ``init`` because ``init`` leaves an existing
``docs/Team/Board.md`` alone, and the queue movement is made *after* the branch was
cut - the drift that used to be the author's problem.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from test_pr_merge_base_advance import (
    add_task,
    commit_self_check_and_open,
    init_workspace,
    team_root,
)

from teamwork import engine
from teamwork.names import git_identity_args

BOARD = "docs/Team/Board.md"

#: A board that carries the five anchors the renderer and the checker share, so a
#: landing can re-render it. A fresh `init` writes a skeleton without the task
#: tables; the render at the merge needs the tables to exist.
BOARD_SKELETON = """# BOARD - live status

Owner: Project Manager.

## Snapshot

- Milestone: -

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| developer | T-0001 | - | doing | - | - |

Rows whose PR is not merged carry no merged revision.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| developer | T-0001 | P0 | doing | - |

The task queue (`teamwork.py task list <role>`) is authoritative.

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| | | | |
"""


def seed_board(project: Path) -> None:
    """Put an anchored board in place before `init` commits the tree."""
    board = project.joinpath(*BOARD.split("/"))
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text(BOARD_SKELETON, encoding="utf-8")


def git_as_ceo(project: Path, *argv: str) -> subprocess.CompletedProcess:
    """A commit made the way the CEO commits records: the role mailbox identity."""
    return subprocess.run(
        ["git", "-C", str(project), *git_identity_args("ceo"), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


def diverge_main(project: Path, filename: str = "feature.txt") -> None:
    """Move main onto a commit that conflicts with the branch's file."""
    assert engine.run_git(project, "checkout", "main").returncode == 0
    (project / filename).write_text("main's version\n", encoding="utf-8")
    assert git_as_ceo(project, "add", "--", filename).returncode == 0
    committed = git_as_ceo(project, "commit", "-q", "-m", "chore: main moves on")
    assert committed.returncode == 0, committed.stderr


def review_pass(cli, project: Path, *extra: str) -> int:
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
    return cli(*argv)


def developer_task(project: Path) -> dict:
    tasks = engine.parse_tasks(team_root(project) / "Roles" / "Developer" / "TaskQueue.md")
    found = next((t for t in tasks if t["id"] == "T-0001"), None)
    assert found is not None, [t["id"] for t in tasks]
    return found


def pass_records(project: Path) -> list:
    return engine.parse_reviews(team_root(project) / "Reviews.md")


def ship(cli, project: Path) -> None:
    """One task through branch, commit, self-check and an open PR."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the merge-board fix", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")


def test_a_pass_whose_branch_does_not_merge_is_refused_before_the_verdict(
    cli, project, capsys
) -> None:
    """P-0057: a verdict must never precede a merge that cannot happen.

    The branch's ``feature.txt`` and main's are both changed, so git reports a
    content conflict on that path. The pass has to name it and stop BEFORE it
    writes ``review_status``, flips the PR to approved, or touches the task.
    """
    seed_board(project)
    ship(cli, project)
    branch = developer_task(project)["branch"]
    diverge_main(project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    assert review_pass(cli, project) == 2
    err = capsys.readouterr().err

    assert "does not merge into main" in err, err
    assert "CONFLICT in feature.txt" in err, err
    assert "git rebase main" in err, err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
    assert engine.branch_exists(project, branch)
    task = developer_task(project)
    assert task["review_status"] == "pending", "a refused pass must not record a verdict"
    assert task["status"] == "review", "a refused pass must leave the task awaiting review"
    assert task["merge_commit"] == ""
    assert pass_records(project)[0]["status"] == "open", "the PR must not be approved"


def test_pr_merge_refuses_a_branch_that_no_longer_merges_and_changes_nothing(
    cli, project, capsys
) -> None:
    """The merge path re-probes the base it will advance, not the base the pass saw."""
    seed_board(project)
    ship(cli, project)
    branch = developer_task(project)["branch"]
    # a verdict recorded against a base that was clean at pass time
    assert review_pass(cli, project, "--no-merge") == 0
    diverge_main(project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()

    capsys.readouterr()
    assert cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-2") == 2
    err = capsys.readouterr().err

    assert "does not merge into main" in err, err
    assert "CONFLICT in feature.txt" in err, err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
    assert engine.branch_exists(project, branch)
    task = developer_task(project)
    assert task["review_status"] == "passed", "the verdict recorded earlier stands"
    assert task["merge_commit"] == "", "a refused merge must not record a merge revision"
    assert pass_records(project)[0]["status"] == "approved"


def test_force_overrides_the_mergeability_probe_and_records_the_reason(
    cli, project, capsys
) -> None:
    """``--force`` may override the probe, but the override is a recorded fact."""
    seed_board(project)
    ship(cli, project)
    diverge_main(project)
    reason = "the sibling branch must land before its rebase window closes"

    capsys.readouterr()
    # --no-merge: the override is about the verdict; git still cannot merge a
    # conflict, and that failure is reported rather than counted as landed.
    assert review_pass(cli, project, "--force", reason, "--no-merge") == 0

    task = developer_task(project)
    assert task["review_status"] == "passed"
    assert "mergeability overridden" in task["forced"], task["forced"]
    assert "CONFLICT in feature.txt" in task["forced"], task["forced"]
    assert reason in task["forced"], task["forced"]
    assert pass_records(project)[0]["status"] == "approved"
    ledger = (team_root(project) / engine.F_LEDGER).read_text(encoding="utf-8")
    assert "review.pass" in ledger, "the verdict must be on the ledger"
    assert f"FORCED: {reason}" in ledger, "the recorded override reason must be on the ledger"
    assert "mergeability overridden" in ledger, "the ledger must say what was overridden"


def test_a_merge_renders_the_board_from_queues_that_moved_after_the_branch_was_cut(
    cli, project, capsys
) -> None:
    """The landing leaves a board equal to the queues, whoever moved them."""
    seed_board(project)
    ship(cli, project)
    # the queues move after the branch was cut: a second task nobody rendered
    assert cli("--project", project, "task", "add", "developer", "a later task") == 0

    capsys.readouterr()
    assert review_pass(cli, project) == 0
    out = capsys.readouterr().out

    assert "# board: rendered docs/Team/Board.md from the queues at the merge" in out, out
    task = developer_task(project)
    assert task["status"] == "done"
    assert task["merge_commit"], "the board render must not replace the merge revision"
    assert (
        engine.run_git(
            project, "merge-base", "--is-ancestor", task["merge_commit"], "main"
        ).returncode
        == 0
    )
    board = engine.run_git(project, "show", f"main:{BOARD}").stdout
    assert "| developer | T-0002 |" in board, board
    assert "| developer | T-0001 |" in board and "| done | P-0001 |" in board, board
    # the rendered board is the product's own view of the queues, so --check is green
    capsys.readouterr()
    assert cli("--project", project, "board", "--check") == 0
    assert "matches the role queues" in capsys.readouterr().out
    subjects = engine.run_git(project, "log", "-3", "--format=%s", "main").stdout
    assert "chore(records): re-render docs/Team/Board.md at the merge" in subjects, subjects
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""


def test_a_board_render_that_cannot_land_is_reported_without_un_recording_the_merge(
    cli, project, capsys, monkeypatch
) -> None:
    """Landed-but-board-stale is said loudly; the merge record stands."""
    seed_board(project)
    ship(cli, project)
    main_before_board = engine.run_git(project, "show", f"main:{BOARD}").stdout

    def explode(tasks, board):
        raise ValueError("queues are unreadable in this test")

    monkeypatch.setattr(engine.boardlib, "render", explode)

    capsys.readouterr()
    assert review_pass(cli, project) == 0
    out = capsys.readouterr().out

    assert "WARNING: the merge of P-0001 is LANDED" in out, out
    assert "STALE" in out and "teamwork.py board --write" in out, out
    task = developer_task(project)
    assert task["status"] == "done", "the merge record must survive a failed render"
    assert task["merge_commit"], "the merge revision must survive a failed render"
    assert pass_records(project)[0]["status"] == "merged"
    assert engine.run_git(project, "show", f"main:{BOARD}").stdout == main_before_board
    assert engine.run_git(project, "status", "--porcelain").stdout.strip() == ""
