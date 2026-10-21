"""The audit must ask "was this verified?", not "was the evidence field used?".

Two defects are pinned here, both reproduced on the real team tree before the fix:

1. ``audit`` listed every review-passed task as a fabricated completion. A review
   pass writes ``review_evidence`` and a self-check writes ``self_note``; neither
   writes ``evidence``. So the five properly reviewed tasks (developer T-0015 with
   ``review_status: passed`` and ``merge_commit: cc2f50f`` among them) were
   reported as unverified while their proof sat one field away.
2. ``audit`` reported a forced review pass as "submitted for review without a
   self-check" forever. The force records *why* the self-check was skipped, which
   is the audit trail; re-reporting it on every run is noise that hides new ones.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine
from teamwork.records import new_task, parse_tasks, write_tasks

ROSTER = "ceo,developer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def make_root(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def developer_queue(root: Path) -> Path:
    return root / "Roles" / "Developer" / engine.F_TASKS


def write_task(root: Path, **fields) -> str:
    path = developer_queue(root)
    tasks = parse_tasks(path)
    task = new_task(
        fields.pop("title", "a task"),
        fields.pop("priority", "P1"),
        deps="",
        tags="",
    )
    task.update(fields)
    tasks.append(task)
    write_tasks(path, tasks, "Developer")
    return task["id"]


def audit_output(cli, project: Path) -> tuple[int, str]:
    """Run audit, capturing stdout (the engine prints its sections)."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli("--project", project, "audit")
    return code, buf.getvalue()


def section(text: str, header: str) -> list[str]:
    """Return the bullet lines under one audit section header."""
    lines, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(header)
            continue
        if inside and line.startswith("- "):
            lines.append(line)
    return lines


def test_a_review_passed_task_is_not_a_fabricated_completion(cli, project: Path):
    root = make_root(cli, project)
    task_id = write_task(
        root,
        title="proved by a review pass only",
        status="done",
        review="required",
        review_status="passed",
        self_check="passed",
        review_evidence="pytest -q @abc1234 -> 42 passed",
        evidence="",
    )

    _, text = audit_output(cli, project)

    flagged = section(text, "## done without evidence")
    assert not [line for line in flagged if task_id in line], (
        "a review pass records its proof in review_evidence; the audit must accept it"
    )


def test_a_self_checked_task_is_not_a_fabricated_completion(cli, project: Path):
    root = make_root(cli, project)
    task_id = write_task(
        root,
        title="proved by the author's own run",
        status="done",
        self_check="passed",
        self_note="[pass] re-read the diff | test: pytest -q @def5678 -> 12 passed",
        evidence="",
    )

    _, text = audit_output(cli, project)

    assert not [line for line in section(text, "## done without evidence") if task_id in line]


def test_a_done_task_with_no_proof_at_all_is_still_flagged(cli, project: Path):
    """The gate must not become vacuous: real fabrication is still caught."""
    root = make_root(cli, project)
    task_id = write_task(
        root,
        title="closed by hand with nothing behind it",
        status="done",
        review="na",
        evidence="",
    )

    _, text = audit_output(cli, project)

    assert [line for line in section(text, "## done without evidence") if task_id in line], (
        "a done task with no evidence, no review evidence and no self note is the exact "
        "fabricated completion this audit exists to find"
    )


def test_a_forced_review_pass_is_not_reported_as_a_skipped_self_check(cli, project: Path):
    root = make_root(cli, project)
    task_id = write_task(
        root,
        title="closed on a recorded force",
        status="done",
        review="required",
        review_status="passed",
        self_check="pending",
        forced="review pass forced by Reviewer-1: the preconditions were measured on main",
        review_evidence="pytest -q @abc1234 -> 42 passed",
    )

    _, text = audit_output(cli, project)

    flagged = section(text, "## submitted for review without a self-check")
    assert not [line for line in flagged if task_id in line], (
        "the forced field is the recorded reason the self-check was skipped"
    )


def test_an_unforced_skipped_self_check_is_still_flagged(cli, project: Path):
    """The gate must not become vacuous here either."""
    root = make_root(cli, project)
    task_id = write_task(
        root,
        title="submitted without checking itself",
        status="review",
        review="required",
        review_status="pending",
        self_check="pending",
        forced="",
    )

    _, text = audit_output(cli, project)

    flagged = section(text, "## submitted for review without a self-check")
    assert [line for line in flagged if task_id in line], (
        "a self-check that was skipped with no recorded force is a real defect"
    )
