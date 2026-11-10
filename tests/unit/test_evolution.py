"""The Evolution page's close conditions, enforced by code.

``docs/Team/Evolution.md`` section 11 says a close checks four books: no known
issue past its re-measure date, a verdict on every evolution row, a level on every
promotion row, and a command on every metric row. These tests pin each rule twice -
on a page it must accept and on a page that breaks exactly that rule - because a
check that cannot fail is decoration. The table shape is the committed one; a page
that is missing a table is a violation, never a silent pass.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from teamwork import evolution

TODAY = date(2026, 11, 4)

CLEAN = """# EVOLUTION

## 5. Metrics

| metric | formula | cut #1 | cut #2 | target | command |
|---|---|---|---|---|---|
| RFR | fail verdicts / verdicts | 41% | 0% | <= 30% | `teamwork throughput` |
| Rework | targets with >1 verdict | 47.7% | 0% | falling | `teamwork throughput` |
| SFR / MFR | substantive / mechanical fail share | 25 of 29 | none | SFR falling | `teamwork throughput` |
| TTV p50 / p90 | claim -> verdict | 5.8 / 22.1 min | 2.3 / 69.2 min | p90 falling | `teamwork throughput` |
| Verification waste | repeated full-suite runs | structural | 0 | 0 | review evidence |
| Record density | Archive bytes; largest queue bytes | 2.5 MB | 2.7 MB | bounded | `wc -c` |
| Freshness debt | KI rows past re-measure by | not tracked | 0 | 0 | `teamwork evolution check` |
| Promotion lag | days from a repeated L- to a tw- skill | 3 skills | see 9.3 | <= 7 days | `teamwork skill candidates` |
| Guardrails | required layers, security, budget, independence | all green | budget red | any regression is hurt | `tests plan` |

## 9. Current ledgers

### 9.1 Known issues

| id | issue | class | owner | first seen | re-measure by | status |
|---|---|---|---|---|---|---|
| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |
| KI-0002 | a closed issue | D | ceo | 2026-10-01 | 2026-10-15 | closed |

### 9.2 Evolution ledger

| id | change | class | baseline -> result | verdict | evidence |
|---|---|---|---|---|---|
| EV-0001 | a real change | T | old -> new | helped (defect fixed) | `pytest -q` |
| EV-0002 | a record only | D | none -> recorded | no observed effect (a record) | `gh run view 1` |

### 9.3 Promotion backlog

| record | level now | blocker | next step |
|---|---|---|---|
| `L-0001` a lesson | L1 (lesson) | one occurrence | promote at the second |
| a contract | L2 (a section) | unmeasured | measure the next cut |
"""


def document(text: str = CLEAN, old: str = "", new: str = "") -> str:
    if old:
        assert old in text, old
        text = text.replace(old, new)
    return text


def violations(text: str, today: date = TODAY) -> list:
    return evolution.check_text(text, today)


def drop_rows(text: str, predicate) -> str:
    kept = []
    for line in text.splitlines():
        if line.strip().startswith("|") and predicate(evolution.split_cells(line)):
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


def test_a_clean_page_has_no_violation() -> None:
    assert violations(CLEAN) == []


def test_parse_reads_all_four_tables() -> None:
    found: list = []
    tables = evolution.parse_document(CLEAN, found)
    assert found == []
    assert set(tables) == {
        evolution.METRICS,
        evolution.KNOWN,
        evolution.EVOLUTION,
        evolution.PROMOTION,
    }
    assert len(tables[evolution.METRICS].rows) == len(evolution.TRACKED_METRICS)
    assert len(tables[evolution.KNOWN].rows) == 2
    assert len(tables[evolution.EVOLUTION].rows) == 2
    assert len(tables[evolution.PROMOTION].rows) == 2
    assert tables[evolution.EVOLUTION].rows[0].cells["verdict"] == "helped (defect fixed)"


def test_an_open_known_issue_past_its_date_is_overdue() -> None:
    text = document(
        old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
        new="| KI-0007 | an old issue | T | developer | 2026-10-01 | 2026-10-20 | open |",
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.OVERDUE]
    assert "KI-0007" in found[0].where
    assert "2026-10-20" in found[0].detail


def test_a_closed_issue_past_its_date_is_not_overdue() -> None:
    text = document(
        old="| KI-0002 | a closed issue | D | ceo | 2026-10-01 | 2026-10-15 | closed |",
        new="| KI-0002 | a closed issue | D | ceo | 2026-09-01 | 2026-09-15 | closed |",
    )
    assert violations(text) == []


def test_a_relative_re_measure_trigger_is_not_a_date() -> None:
    assert violations(CLEAN) == []


def test_a_future_re_measure_date_is_not_overdue() -> None:
    text = document(
        old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
        new="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | 2026-12-01 | open |",
    )
    assert violations(text) == []


def past_with_status(status: str) -> str:
    return document(
        old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
        new=f"| KI-0007 | a stale issue | T | developer | 2026-10-01 | 2026-10-20 | {status} |",
    )


@pytest.mark.parametrize("status", ["open", "in flight", "filed", "watching", ""])
def test_every_non_terminal_status_is_debt(status: str) -> None:
    found = violations(past_with_status(status))
    assert [item.code for item in found] == [evolution.OVERDUE]
    assert "KI-0007" in found[0].where


def test_dropped_is_not_a_terminal_lifecycle_state_and_stays_debt() -> None:
    """The page's lifecycle is open -> re-measured -> closed|waived|escalated.

    ``dropped`` is a task status, not a known-issue terminator, so it is treated
    as debt rather than silently hiding an overdue row.
    """
    found = violations(past_with_status("dropped"))
    assert [item.code for item in found] == [evolution.OVERDUE]


@pytest.mark.parametrize("status", ["closed", "waived", "escalated", "Closed"])
def test_each_terminal_status_does_not_fire(status: str) -> None:
    assert violations(past_with_status(status)) == []


@pytest.mark.parametrize(
    "verdict",
    ["helped", "hurt", "no observed effect", "confounded", "helped (with evidence)"],
)
def test_each_closed_verdict_label_is_accepted(verdict: str) -> None:
    text = document(old="helped (defect fixed)", new=verdict)
    assert violations(text) == []


@pytest.mark.parametrize("verdict", ["helped a bit", "improved", "unknown", "-"])
def test_an_unclosed_verdict_is_a_violation(verdict: str) -> None:
    text = document(old="helped (defect fixed)", new=verdict)
    found = violations(text)
    assert [item.code for item in found] == [evolution.VERDICT]
    assert "EV-0001" in found[0].where


@pytest.mark.parametrize("level", ["L1 (lesson)", "L2 (skill)", "L3 (core)", "L4 (adapter)"])
def test_each_promotion_level_is_accepted(level: str) -> None:
    text = document(old="L1 (lesson)", new=level)
    assert violations(text) == []


@pytest.mark.parametrize("level", ["L5", "level one", "", "-"])
def test_an_invalid_promotion_level_is_a_violation(level: str) -> None:
    text = document(old="L1 (lesson)", new=level)
    found = violations(text)
    assert [item.code for item in found] == [evolution.LEVEL]


def test_an_empty_metric_command_is_a_violation() -> None:
    text = document(
        old="| Rework | targets with >1 verdict | 47.7% | 0% | falling | `teamwork throughput` |",
        new="| Rework | targets with >1 verdict | 47.7% | 0% | falling |  |",
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.COMMAND]
    assert "Rework" in found[0].where


@pytest.mark.parametrize("command", ["-", "\u2014"])
def test_a_placeholder_metric_command_is_a_violation(command: str) -> None:
    text = document(
        old="| RFR | fail verdicts / verdicts | 41% | 0% | <= 30% | `teamwork throughput` |",
        new=f"| RFR | fail verdicts / verdicts | 41% | 0% | <= 30% | {command} |",
    )
    assert [item.code for item in violations(text)] == [evolution.COMMAND]


@pytest.mark.parametrize("name", evolution.TRACKED_METRICS)
def test_deleting_a_tracked_metric_row_is_a_violation(name: str) -> None:
    text = drop_rows(
        CLEAN,
        lambda cells: bool(cells) and cells[0].lower().startswith(name.lower()),
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.METRIC]
    assert name in found[0].detail


def test_an_empty_metrics_table_is_a_violation_not_a_pass() -> None:
    head, tail = CLEAN.split("### 9.1 Known issues", 1)
    kept = []
    for line in head.splitlines():
        cells = evolution.split_cells(line) if line.strip().startswith("|") else []
        if cells and cells[0] not in ("metric", "---"):
            continue
        kept.append(line)
    text = "\n".join(kept) + "\n### 9.1 Known issues" + tail
    found = violations(text)
    assert [item.code for item in found] == [evolution.EMPTY]
    assert found[0].where == "Metrics"


def test_deleting_the_only_overdue_known_issue_leaves_an_empty_table() -> None:
    single = document(
        old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
        new="| KI-0009 | a stale issue | T | developer | 2026-01-01 | 2026-01-02 | open |",
    )
    single = drop_rows(single, lambda cells: bool(cells) and cells[0] == "KI-0002")
    assert [item.code for item in violations(single)] == [evolution.OVERDUE]

    emptied = drop_rows(single, lambda cells: bool(cells) and cells[0].startswith("KI-"))
    found = violations(emptied)
    assert [item.code for item in found] == [evolution.EMPTY]
    assert found[0].where == "Known issues"


def test_a_missing_table_is_a_violation_not_a_skip() -> None:
    head = CLEAN.split("### 9.2 Evolution ledger", 1)[0]
    tail = CLEAN.split("### 9.3 Promotion backlog", 1)[1]
    text = head + "### 9.3 Promotion backlog" + tail
    found = violations(text)
    assert evolution.MISSING in [item.code for item in found]
    assert any("Evolution ledger" in item.where for item in found)


def test_a_missing_heading_is_a_violation() -> None:
    text = CLEAN.replace("### 9.3 Promotion backlog", "### 9.3 Another book")
    found = violations(text)
    assert [item.code for item in found] == [evolution.MISSING]
    assert "Promotion backlog" in found[0].where


def test_an_empty_table_is_a_violation() -> None:
    text = CLEAN.replace(
        "| EV-0001 | a real change | T | old -> new | helped (defect fixed) | `pytest -q` |\n"
        "| EV-0002 | a record only | D | none -> recorded | no observed effect (a record) | `gh run view 1` |",
        "",
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.EMPTY]
    assert "Evolution ledger" in found[0].where


def test_a_row_with_the_wrong_cell_count_is_malformed() -> None:
    text = document(
        old="| EV-0001 | a real change | T | old -> new | helped (defect fixed) | `pytest -q` |",
        new="| EV-0001 | a real change | T | old -> new | helped |",
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.MALFORMED]


def test_a_table_missing_a_required_column_is_malformed() -> None:
    text = (
        CLEAN.replace(
            "| id | change | class | baseline -> result | verdict | evidence |",
            "| id | change | class | baseline -> result | evidence |",
        )
        .replace(
            "| EV-0001 | a real change | T | old -> new | helped (defect fixed) | `pytest -q` |",
            "| EV-0001 | a real change | T | old -> new | `pytest -q` |",
        )
        .replace(
            "| EV-0002 | a record only | D | none -> recorded | no observed effect (a record) | `gh run view 1` |",
            "| EV-0002 | a record only | D | none -> recorded | `gh run view 1` |",
        )
    )
    found = violations(text)
    assert [item.code for item in found] == [evolution.MALFORMED]
    assert "verdict" in found[0].detail


def test_a_missing_document_is_a_violation(tmp_path: Path) -> None:
    root = tmp_path / "SampleProject" / ".pi" / "Teamwork" / "Teams" / "SampleProject"
    root.mkdir(parents=True)
    result = evolution.check(root)
    assert result.problems == 1
    assert result.violations[0].code == evolution.MISSING


def write_page(project: Path, text: str = CLEAN) -> Path:
    path = project / "docs" / "Team" / "Evolution.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_check_cli_exits_zero_on_a_clean_page(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(project, CLEAN)
    capsys.readouterr()

    assert cli("--project", project, "evolution", "check") == 0
    out = capsys.readouterr().out
    assert "# problems found: 0" in out
    assert "cut:" in out


def test_check_cli_exits_one_and_names_the_overdue_issue(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(
        project,
        document(
            old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
            new="| KI-0009 | a stale issue | T | developer | 2026-01-01 | 2026-01-02 | open |",
        ),
    )
    capsys.readouterr()

    assert cli("--project", project, "evolution", "check") == 1
    out = capsys.readouterr().out
    assert "OVERDUE" in out and "KI-0009" in out
    assert "# problems found: 1" in out


def test_check_json_has_the_stable_shape(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(
        project,
        document(
            old="helped (defect fixed)",
            new="improved",
        ),
    )
    capsys.readouterr()

    assert cli("--project", project, "evolution", "check", "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "evolution.check"
    assert payload["clean"] is False
    assert payload["problems"] == len(payload["violations"]) == 1
    assert payload["violations"][0]["code"] == evolution.VERDICT
    assert isinstance(payload["cut"], int)


def test_snapshot_names_the_cut_in_text(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(project, CLEAN)
    capsys.readouterr()

    assert cli("--project", project, "evolution", "snapshot") == 0
    out = capsys.readouterr().out
    assert "ledger records" in out and "cut: " in out
    assert "review fail share:" in out
    assert "test gaps:" in out


def test_snapshot_json_reads_the_tree_and_the_ledger(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(project, CLEAN)
    capsys.readouterr()

    assert cli("--project", project, "evolution", "snapshot", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "evolution.snapshot"
    assert payload["cut"] >= 1
    assert payload["review"]["verdicts"] == 0
    assert payload["review"]["fail_share_pct"] is None
    assert payload["budget"]["instances"] >= 1
    assert payload["budget"]["over"] == 0
    assert payload["test_gaps"]["available"] is True
    assert payload["test_gaps"]["count"] == 0
    assert payload["freshness"]["debt"] == 0
    assert isinstance(payload["archive_bytes"], int)


def test_snapshot_freshness_debt_uses_the_lifecycle_status_set(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(project, past_with_status("in flight"))
    capsys.readouterr()

    assert cli("--project", project, "evolution", "snapshot", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["freshness"]["debt"] == 1
    assert payload["freshness"]["check_problems"] == 1

    write_page(project, past_with_status("waived"))
    capsys.readouterr()
    assert cli("--project", project, "evolution", "snapshot", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["freshness"]["debt"] == 0


def audit(cli, capsys, project: Path) -> tuple:
    capsys.readouterr()
    code = cli("--project", project, "audit")
    return code, capsys.readouterr().out


def problems(text: str) -> int:
    for line in reversed(text.splitlines()):
        if line.startswith("# problems found: "):
            return int(line.split(": ", 1)[1])
    raise AssertionError("the audit did not print its problem count")


def test_audit_counts_a_clean_page_as_no_problem(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    write_page(project)
    clean_code, clean_out = audit(cli, capsys, project)
    section = clean_out.split("## self-evolution ledger", 1)[1].split("\n## ", 1)[0]
    assert "- none" in section
    clean_problems = problems(clean_out)

    write_page(
        project,
        document(
            old="| KI-0001 | a fresh issue | T | developer | 2026-11-01 | next milestone | open |",
            new="| KI-0009 | a stale issue | T | developer | 2026-01-01 | 2026-01-02 | open |",
        ),
    )
    dirty_code, dirty_out = audit(cli, capsys, project)
    dirty_section = dirty_out.split("## self-evolution ledger", 1)[1].split("\n## ", 1)[0]
    assert "- OVERDUE" in dirty_section and "KI-0009" in dirty_section
    assert dirty_code == 1
    assert problems(dirty_out) == clean_problems + 1
    assert clean_code in (0, 1)


def test_audit_fails_when_the_page_is_missing(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--no-git") == 0
    code, out = audit(cli, capsys, project)
    section = out.split("## self-evolution ledger", 1)[1].split("\n## ", 1)[0]
    assert evolution.MISSING in section
    assert code == 1
