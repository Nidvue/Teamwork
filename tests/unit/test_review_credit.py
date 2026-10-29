"""Review economy: verify once, credit the rest.

Why these tests exist: every review re-ran the gates another role had already
run at the same revision (the ledger at the start of this task: 36 fails in 95
verdicts, 21 of 61 deliverables re-reviewed, claim -> verdict p50 12.2 min), and
a re-submitted fix was specified as "reviewed from scratch" with the previous
findings not even in the packet. The reviewer is the lane every other lane waits
on, so a duplicated run is the most expensive run in the team.

Pinned here: the packet lists creditable records at the revision under review
(another role's passing run) and never the author's own run, reports stale
records, and carries the round, the previous findings and the delta after a
fail; `--credit` refuses an unknown, failing, author-role or stale record and
records the citation on a pass; a fail stores the revision that failed; and
`coordination` reports the credit ratio, the delta re-reviews, `C-REVIEW-DUP`
(a gate re-run that was already green at the same revision) and
`C-REVIEW-NOCREDIT` (a recent window of passes that cited nothing).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.gitenv import child_env

from teamwork import engine, records

ROSTER = "ceo,developer-1,tester-1,reviewer-1,reviewer-2"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def git(project: Path, *args: str) -> str:
    env = child_env(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    result = subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def seed(cli, project: Path, area: str = "engine") -> tuple:
    """A git repo with a base and a work branch, plus a team and a submitted task.

    Returns (root, head short sha). The task is claimed by developer-1, sits on
    ``work`` and is submitted, which is the state a review starts from.
    """
    git(project, "init", "-q", "-b", "main")
    (project / ".gitignore").write_text(".pi/\nAGENTS.md\ndocs/\n", encoding="utf-8")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-qm", "base")
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = team_root(project)
    git(project, "checkout", "-q", "-b", "work")
    (project / "README.md").write_text("base\nfixed\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-qm", "fix the thing")
    head = git(project, "rev-parse", "--short", "HEAD")

    path = engine.task_file(root, "developer")
    task = engine.new_task("fix the README boundary")
    task["priority"] = "P1"
    task["area"] = area
    task["claimed_by"] = "Developer-1"
    task["branch"] = "work"
    task["base"] = "main"
    task["status"] = "review"
    task["self_check"] = "passed"
    engine.write_tasks(path, [task], "developer")
    assert engine.parse_tasks(path)[0]["status"] == "review"
    return root, head


def add_record(
    cli, project: Path, layer: str, by: str, rev: str, command: str, area: str = "engine"
) -> str:
    """A passing layer record at ``rev``, run by ``by``."""
    root = team_root(project)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            layer,
            "--area",
            area,
            "--command",
            command,
        )
        == 0
    )
    record = [
        r
        for r in engine.parse_tests(engine.tests_path(root))
        if r["layer"] == layer and r["area"] == area
    ][0]
    handle = record["id"]
    code = cli(
        "--project",
        project,
        "tests",
        "run",
        handle,
        "--by",
        by,
        "--result",
        "pass",
        "--rev",
        rev,
        "--command",
        command,
        "--evidence",
        f"{command} @{rev} -> 12 passed",
    )
    assert code == 0
    return handle


def test_packet_lists_credits_and_never_the_author_own_run(cli, project: Path) -> None:
    root, head = seed(cli, project)
    tester = add_record(
        cli, project, "integration", "Tester-1", head, "pytest -q tests/integration"
    )
    add_record(cli, project, "unit", "Developer-1", head, "pytest -q tests/unit")
    # A record at another revision is stale: the tree moved, so the run must too.
    add_record(cli, project, "acceptance", "Reviewer-1", "0" * 7, "pytest -q tests/acceptance")

    packet = engine.review_packet(
        root, "developer", engine.parse_tasks(engine.task_file(root, "developer"))[0]
    )
    assert f"credits at {head}" in packet
    assert f"{tester} integration/engine by Tester-1" in packet
    assert "pytest -q tests/unit" not in packet, "the author's own run is never a credit"
    assert "stale: 1 passing record(s)" in packet
    assert "--credit" in packet


def test_credit_is_refused_for_the_author_a_stale_rev_or_an_unknown_id(cli, project: Path) -> None:
    root, head = seed(cli, project)
    tester = add_record(
        cli, project, "integration", "Tester-1", head, "pytest -q tests/integration"
    )
    own = add_record(cli, project, "unit", "Developer-1", head, "pytest -q tests/unit")
    assert (
        cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", "T-0001") == 0
    )

    base = ["--project", project, "review", "developer", "T-0001", "--by", "reviewer-1"]
    evidence = f"pytest -q tests/acceptance @{head} -> 3 passed"
    assert cli(*base, "--result", "pass", "--evidence", evidence, "--credit", own) != 0
    assert cli(*base, "--result", "pass", "--evidence", evidence, "--credit", "TS-9999") != 0

    tests = engine.parse_tests(engine.tests_path(root))
    record = [r for r in tests if r["id"] == tester][0]
    record["rev"] = "0" * 7
    engine.write_tests(engine.tests_path(root), tests)
    assert cli(*base, "--result", "pass", "--evidence", evidence, "--credit", tester) != 0

    record["rev"] = head
    engine.write_tests(engine.tests_path(root), tests)
    assert cli(*base, "--result", "pass", "--evidence", evidence, "--credit", tester) == 0
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert task["review_status"] == "passed"
    assert f"credited: {tester} integration/engine by Tester-1 @{head}" in task["review_evidence"]

    # --credit belongs to a pass: a fail names findings, not a citation.
    task["status"] = "review"
    task["review_status"] = "pending"
    task["self_check"] = "passed"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")
    assert cli(*base, "--result", "fail", "--findings", "no", "--credit", tester) != 0


def test_a_fail_stores_the_revision_and_the_next_packet_is_a_delta(cli, project: Path) -> None:
    root, head = seed(cli, project)
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "reviewer-1",
            "--result",
            "fail",
            "--findings",
            "the boundary is untested",
        )
        == 0
    )
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    assert task["review_fails"] == 1
    assert task["review_fail_rev"] == head

    task["status"] = "review"
    task["self_check"] = "passed"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")
    unchanged = engine.review_packet(root, "developer", task)
    assert "review round: 2 (1 previous fail)" in unchanged
    assert "previous findings: the boundary is untested" in unchanged
    assert f"delta since {head}: none" in unchanged

    (project / "README.md").write_text("base\nfixed\nplus a boundary test\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-qm", "test the boundary")
    moved = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    packet = engine.review_packet(root, "developer", moved)
    assert f"delta since {head} (1 file(s)): README.md" in packet
    assert "re-review the delta" in packet

    # A failed revision that is not in this repository cannot be diffed: say so
    # instead of claiming nothing changed, which would send the reviewer home.
    unreadable = dict(moved)
    unreadable["review_fail_rev"] = "deadbeef"
    assert "not diffable" in engine.review_packet(root, "developer", unreadable)


def test_credit_is_refused_for_a_failing_record(cli, project: Path) -> None:
    """Only a passing result is a fact: a failing record is a defect to fix, not a credit."""
    root, head = seed(cli, project)
    tester = add_record(
        cli, project, "integration", "Tester-1", head, "pytest -q tests/integration"
    )
    tests = engine.parse_tests(engine.tests_path(root))
    [r for r in tests if r["id"] == tester][0]["status"] = "failing"
    engine.write_tests(engine.tests_path(root), tests)
    assert (
        cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", "T-0001") == 0
    )
    code = cli(
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
        f"pytest -q @{head} -> 12 passed",
        "--credit",
        tester,
    )
    assert code != 0
    assert (
        engine.credit_refusal(
            root, "developer", engine.parse_tasks(engine.task_file(root, "developer"))[0], tester
        )
        == f"{tester} is failing, not passing"
    )


def test_coordination_reports_a_duplicated_gate_and_a_zero_credit_window(
    cli, project: Path
) -> None:
    root, head = seed(cli, project)
    command = "pytest -q tests/integration"
    add_record(cli, project, "integration", "Tester-1", head, command)
    task = engine.parse_tasks(engine.task_file(root, "developer"))[0]
    task["review_status"] = "passed"
    task["status"] = "done"
    task["review_evidence"] = f"{command} @{head} -> 12 passed"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")

    report = engine.coordination_report(root)
    codes = {finding["code"] for finding in report["findings"]}
    assert "C-REVIEW-DUP" in codes
    assert report["metrics"]["review_duplicated_gates"] == 1

    # A fresh pass per ledger record: five recent passes with no credit cited is
    # no longer a one-off, it is the team re-running everything.
    for _ in range(engine.COORD_CREDIT_FLOOR):
        engine.ledger_append(root, "review.pass", "Reviewer-1", "T-0001", "pass", "", "developer")
    report = engine.coordination_report(root)
    assert "C-REVIEW-NOCREDIT" in {finding["code"] for finding in report["findings"]}
    assert report["metrics"]["review_recent_passes"] >= engine.COORD_CREDIT_FLOOR
    assert report["metrics"]["review_credited_passes"] == 0

    task["review_evidence"] = f"{command} @{head} -> 12 passed | credited: TS-0001"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")
    report = engine.coordination_report(root)
    assert "C-REVIEW-NOCREDIT" not in {finding["code"] for finding in report["findings"]}
    assert report["metrics"]["review_credited_passes"] >= 1


def test_a_stale_record_is_not_offered_and_a_prefix_still_matches(tmp_path: Path) -> None:
    """The revision comparison is prefix-based on both sides, and empty is never a match."""
    assert engine._same_revision("abc1234", "abc1234def5678") is True
    assert engine._same_revision("", "abc1234") is False
    assert engine._same_revision("abc1234", "def5678") is False
    # A record without `rev` falls back to the ``@sha`` its evidence quotes.
    assert (
        engine.record_revision({"rev": "", "evidence": "pytest -q @abc1234 -> 9 passed"})
        == "abc1234"
    )
    assert records.new_task("x").get("review_fail_rev") == ""
