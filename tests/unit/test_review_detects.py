"""A review finding must name the failure it detects (M16 A1).

Why these tests exist: a review finding is a claim, and until now the claim only
had to say what looked wrong. HERO's reachability test asks the two questions that
make it falsifiable - which specific failure would this catch, and what would I do
differently if it occurred - and requires the failure to be *reachable* in the
project's supported use: its documented inputs, published interface or real data.
"Constructible in principle" is not enough, so a detector like "edge case" answers
nothing and is refused at the verdict.

Pinned here: `review --result fail` refuses a missing or canned `--detects` and
states the reachability rule in one line; a real detector is recorded on the task
(`review_detects`), rendered as `detects: <x>` before the defect in the findings
history, and carried in the `review.fail` ledger detail; `audit` counts the fails
that have no detector or a restatement without blocking on them; and a record
written before the field existed still reads (empty, not an error).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_review_credit import seed, team_root

from teamwork import engine, records

DEFECT = "the limit check uses > where it must use >="
#: A detector that answers HERO's two questions: the failure, and the input that
#: reaches it through a documented interface.
DETECTOR = "a request exactly at the limit is rejected instead of accepted"


def fail(cli, project: Path, *extra: str, findings: str = DEFECT) -> int:
    """A Reviewer fails T-0001 with whatever extra flags the caller adds."""
    return cli(
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
        findings,
        *extra,
    )


def task_record(project: Path) -> dict:
    return engine.parse_tasks(engine.task_file(team_root(project), "developer"))[0]


def queue_text(project: Path) -> str:
    return engine.task_file(team_root(project), "developer").read_text(encoding="utf-8")


def fail_records(project: Path) -> list:
    return [r for r in engine.ledger_read(team_root(project)) if r.get("action") == "review.fail"]


# --------------------------------------------------------------------------- #
# The gate: a fail without a detector (or with a canned one) is refused
# --------------------------------------------------------------------------- #


def test_a_fail_with_no_detector_is_refused_and_records_nothing(cli, project, capsys) -> None:
    """The field is required, and a refused verdict leaves the task untouched."""
    seed(cli, project)
    capsys.readouterr()

    assert fail(cli, project) != 0
    err = capsys.readouterr().err

    assert "a fail needs --detects '<the specific failure this would catch>'" in err, err
    assert "the --detects is missing" in err, err
    task = task_record(project)
    assert task["status"] == "review", "a refused fail must not move the task"
    assert task["review_fails"] == 0
    assert task["review_detects"] == ""
    assert task["findings"] == ""
    assert fail_records(project) == []


def test_the_refusal_states_the_reachability_rule_in_one_line(cli, project, capsys) -> None:
    """The rule is the point of the field, so the reviewer reads it with the refusal."""
    seed(cli, project)
    capsys.readouterr()
    assert fail(cli, project) != 0
    err = capsys.readouterr().err

    line = next(ln for ln in err.splitlines() if "reachable in this project" in ln)
    assert "documented inputs, published interface or real data" in line, line
    assert "constructible in principle is not enough" in line, line
    assert line.startswith("teamwork: a fail needs --detects"), line
    assert line.endswith(engine.REVIEW_REACHABILITY_RULE + "."), line


@pytest.mark.parametrize(
    "detects",
    [
        "",
        "   ",
        "edge case",
        "Edge case!",
        "it could break",
        "might fail",
        "not tested",
        "no tests",
        "a typical edge case",
    ],
)
def test_a_detector_that_only_names_a_worry_is_refused(cli, project, capsys, detects) -> None:
    """The control's negative half: '' and 'edge case' are refused, as is their family."""
    seed(cli, project)
    capsys.readouterr()

    assert fail(cli, project, "--detects", detects) != 0
    err = capsys.readouterr().err

    assert engine.REVIEW_REACHABILITY_RULE in err, err
    assert "a restatement" in err or "missing" in err, err
    assert task_record(project)["review_fails"] == 0
    assert fail_records(project) == []


def test_a_detector_that_repeats_the_defect_is_refused(cli, project, capsys) -> None:
    """Saying the work is wrong is not saying what would have caught it."""
    seed(cli, project)
    capsys.readouterr()

    assert fail(cli, project, "--detects", DEFECT) != 0
    err = capsys.readouterr().err
    assert "restatement of the defect" in err, err
    assert task_record(project)["review_fails"] == 0


# --------------------------------------------------------------------------- #
# The control: a real, reachable detection passes and is recorded
# --------------------------------------------------------------------------- #


def test_a_reachable_detector_is_recorded_on_the_task_and_in_the_ledger(
    cli, project, capsys
) -> None:
    """The control's positive half: a detectable failure is accepted and stored."""
    seed(cli, project)
    capsys.readouterr()

    assert fail(cli, project, "--detects", DETECTOR) == 0
    out = capsys.readouterr().out

    assert f"detects: {DETECTOR}" in out, out
    task = task_record(project)
    assert task["review_fails"] == 1
    assert task["review_status"] == "failed"
    assert task["review_detects"] == DETECTOR
    assert task["findings"].startswith(f"detects: {DETECTOR} | {DEFECT}"), task["findings"]
    assert f"review_detects: {DETECTOR}" in queue_text(project)

    records_ = fail_records(project)
    assert len(records_) == 1
    detail = records_[0]["detail"]
    assert detail.startswith("mechanical: "), detail
    assert engine.ledger_detects(detail) == DETECTOR, detail
    # The mechanical classification still leads, so the existing rate is countable.
    assert " | detects: " in detail


def test_the_detector_renders_before_the_defect_in_the_packet(cli, project) -> None:
    """A reader judges proportionality without reading the whole report."""
    root, _head = seed(cli, project)
    assert fail(cli, project, "--detects", DETECTOR) == 0

    task = task_record(project)
    assert task["findings"].index("detects: ") < task["findings"].index(DEFECT)
    packet = engine.review_packet(root, "developer", task)
    assert f"previous findings: detects: {DETECTOR} | {DEFECT}" in packet, packet


def test_a_second_fail_records_its_own_round_and_findings(cli, project) -> None:
    """The ledger detail carries THIS round: the round number and its finding.

    Measured on P-0063 (ceo T-0021): ledger n=1616 and n=1622 both opened with the
    same round-2 preamble, so the round-3 finding could not be read from the ledger
    at all.
    """
    root, _head = seed(cli, project)
    first = "the first defect: a missing header"
    second = "the second defect: a wrong column order"
    assert fail(cli, project, "--detects", DETECTOR, findings=first) == 0
    path = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(path)
    tasks[0]["status"] = "review"
    tasks[0]["self_check"] = "passed"
    engine.write_tasks(path, tasks, "developer")
    assert fail(cli, project, "--detects", DETECTOR, findings=second) == 0

    records_ = fail_records(project)
    assert len(records_) == 2
    assert "round: 1 |" in records_[0]["detail"], records_[0]["detail"]
    assert "round: 2 |" in records_[1]["detail"], records_[1]["detail"]
    assert engine.ledger_detects(records_[1]["detail"]) == DETECTOR
    assert second in records_[1]["detail"], records_[1]["detail"]
    assert first not in records_[1]["detail"], records_[1]["detail"]


def test_a_pass_still_needs_no_detector(cli, project, capsys) -> None:
    """The gate is scoped to a finding: a clean pass has nothing to detect."""
    seed(cli, project)
    task = task_record(project)
    # No branch and no PR: the verdict is what is under test here, not the merge.
    task["branch"] = ""
    task["base"] = ""
    engine.write_tasks(engine.task_file(team_root(project), "developer"), [task], "developer")
    capsys.readouterr()

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
            "pass",
            "--evidence",
            "pytest -q -> 7 passed",
        )
        == 0
    )
    assert task_record(project)["review_status"] == "passed"


def test_a_pipe_in_the_detector_does_not_break_the_ledger_boundary(cli, project) -> None:
    """The ledger detail is one line; a pipe inside the text is written as a slash."""
    seed(cli, project)
    assert (
        fail(
            cli,
            project,
            "--detects",
            "a path with a | in it is read as two paths and the second is dropped",
        )
        == 0
    )
    detail = fail_records(project)[0]["detail"]
    assert (
        engine.ledger_detects(detail)
        == "a path with a / in it is read as two paths and the second is dropped"
    ), detail


# --------------------------------------------------------------------------- #
# audit: count the fails with no reachable detector, never block on them
# --------------------------------------------------------------------------- #


def test_audit_counts_missing_and_restated_detectors_without_blocking(cli, project, capsys) -> None:
    """Three fails, three verdicts: reachable, legacy (no field), restatement."""
    root, _head = seed(cli, project)
    assert fail(cli, project, "--detects", DETECTOR) == 0
    # Legacy: every fail recorded before the field existed looks exactly like this.
    engine.ledger_append(
        root,
        "review.fail",
        "Reviewer-1",
        "T-0001",
        "mechanical: no | the limit check is wrong",
        "",
        "developer",
    )
    # A canned detector can only reach the trail by a rewritten/older record now;
    # the count is what makes that visible instead of silently acceptable.
    engine.ledger_append(
        root,
        "review.fail",
        "Reviewer-1",
        "T-0001",
        "mechanical: no | detects: edge case | the limit check is wrong",
        "",
        "developer",
    )

    capsys.readouterr()
    assert engine._audit_review_fails_without_a_reachable_detect(root, [], None) == 0
    out = capsys.readouterr().out
    assert "3 review fail(s): 1 reachable, 1 no detector recorded, 1 a restatement" in out, out
    assert "legacy fail" in out
    assert "non-blocking" in out

    capsys.readouterr()
    cli("--project", project, "audit")
    audited = capsys.readouterr().out
    assert "## review fails without a reachable --detects (proportionality)" in audited
    assert "3 review fail(s):" in audited


def test_audit_with_no_review_fails_reports_none(cli, project, capsys) -> None:
    """A young workspace has nothing to count; that is not a problem either."""
    root, _head = seed(cli, project)
    capsys.readouterr()
    assert engine._audit_review_fails_without_a_reachable_detect(root, [], None) == 0
    assert "no review fails recorded" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Compatibility: a record written before the field still reads
# --------------------------------------------------------------------------- #


def test_a_legacy_task_record_reads_with_an_empty_detector(cli, project) -> None:
    """Reading old queues must not break, and must not invent a detector."""
    root, _head = seed(cli, project)
    task = task_record(project)
    task["review_fails"] = 2
    task["findings"] = "a | b"
    engine.write_tasks(engine.task_file(root, "developer"), [task], "developer")
    path = engine.task_file(root, "developer")
    path.write_text(
        "\n".join(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("- review_detects:")
        )
        + "\n",
        encoding="utf-8",
    )

    reloaded = engine.parse_tasks(path)[0]
    assert reloaded["review_detects"] == ""
    assert reloaded["review_fails"] == 2
    assert reloaded["findings"] == "a | b"


def test_a_tampered_or_absent_detects_field_is_counted_not_fatal() -> None:
    """The audit counter reads a hand-written detail as missing, never as a crash."""
    assert engine.ledger_detects("") is None
    assert engine.ledger_detects("mechanical: no | no field here") is None
    assert engine.ledger_detects("mechanical: unknown | detects:  | defect") == ""


def test_the_predicate_is_narrow_enough_not_to_refuse_a_real_sentence() -> None:
    """A vague phrase inside a specific failure is still a specific failure."""
    assert engine.detects_problem("") == "missing"
    assert engine.detects_problem("edge case").startswith("a restatement")
    assert engine.detects_problem("not tested").startswith("a restatement")
    assert (
        engine.detects_problem(
            "an edge case in --detects is still refused when the answer names no failure"
        )
        == ""
    )
    assert engine.detects_problem("the parser drops the last path element") == ""


def test_new_task_seeds_the_field_empty() -> None:
    """The record default is the legacy value, so every older queue stays readable."""
    assert records.new_task("x")["review_detects"] == ""
