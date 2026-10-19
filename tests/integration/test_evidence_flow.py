"""Integration: structured evidence and the repro-first gate through the CLI.

These tests pin the behaviour a real team depends on: an evidence packet names
an artifact that must exist and is bound by digest, a defect fix has to prove the
failing run came before the passing one, and the bug task cannot pass its own
self-check without that proof.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def _tests_md(root: Path) -> Path:
    return root / "Tests.md"


def records(root: Path) -> list:
    return engine.parse_tests(_tests_md(root))


def add_evidence_artifact(project: Path) -> Path:
    path = project / "Reports" / "run.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("12 passed in 0.31s\n", encoding="utf-8")
    return path


def test_tests_run_records_the_packet_and_hashes_the_artifact(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "tests", "add", "--layer", "unit", "--area", "parser") == 0
    add_evidence_artifact(project)

    code = cli(
        "--project",
        project,
        "tests",
        "run",
        "TS-0001",
        "--by",
        "developer-1",
        "--result",
        "pass",
        "--evidence",
        "pytest tests/unit/test_parser.py @abc123 -> 12 passed",
        "--rev",
        "abc123",
        "--baseline",
        "empty cache",
        "--artifact",
        "Reports/run.log",
        "--replay",
        "pytest tests/unit/test_parser.py -q",
    )

    assert code == 0
    rec = records(root)[0]
    assert rec["status"] == "passing"
    assert rec["baseline"] == "empty cache"
    assert rec["replay"] == "pytest tests/unit/test_parser.py -q"
    path, digest, size = rec["artifacts"].split(":")
    assert path == "Reports/run.log" and len(digest) == 16 and int(size) > 0

    actions = [r["action"] for r in engine.ledger_read(root)]
    assert "tests.run" in actions


def test_tests_run_refuses_a_missing_artifact(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "tests", "add", "--layer", "unit", "--area", "parser") == 0

    code = cli(
        "--project",
        project,
        "tests",
        "run",
        "TS-0001",
        "--by",
        "developer-1",
        "--result",
        "pass",
        "--evidence",
        "pytest @abc123 -> 12 passed",
        "--artifact",
        "Reports/never-written.log",
    )

    assert code != 0
    assert records(root)[0]["status"] == "pending"


def add_bug_task(cli, project: Path, title: str = "fix the parser crash") -> None:
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            title,
            "--priority",
            "P1",
            "--status",
            "doing",
            "--claimed-by",
            "developer-1",
            "--bug",
        )
        == 0
    )


def developer_task(root: Path) -> dict:
    return engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]


def test_tests_repro_proves_fail_then_pass_on_the_task(cli, project: Path) -> None:
    root = init(cli, project)
    add_bug_task(cli, project)

    code = cli(
        "--project",
        project,
        "tests",
        "repro",
        "T-0001",
        "--by",
        "developer-1",
        "--pre-rev",
        "aaa111",
        "--pre-evidence",
        "pytest tests/unit/test_parser.py @aaa111 -> 3 failed",
        "--post-rev",
        "bbb222",
        "--post-evidence",
        "pytest tests/unit/test_parser.py @bbb222 -> 12 passed",
    )

    assert code == 0
    task = developer_task(root)
    assert task["repro_by"] == "Developer-1"
    assert "pre @aaa111" in task["repro"] and "post @bbb222" in task["repro"]
    assert [r["action"] for r in engine.ledger_read(root)].count("tests.repro") == 1
    # the proof belongs to the defect, not to a layer record
    assert engine.parse_tests(_tests_md(root)) == []


def test_tests_repro_rejects_a_single_revision(cli, project: Path) -> None:
    root = init(cli, project)
    add_bug_task(cli, project)

    code = cli(
        "--project",
        project,
        "tests",
        "repro",
        "T-0001",
        "--by",
        "developer-1",
        "--pre-rev",
        "same",
        "--pre-evidence",
        "pytest @same -> 3 failed",
        "--post-rev",
        "same",
        "--post-evidence",
        "pytest @same -> 12 passed",
    )

    assert code != 0
    assert developer_task(root)["repro"] == ""


def test_tests_repro_requires_a_failing_pre_run(cli, project: Path) -> None:
    root = init(cli, project)
    add_bug_task(cli, project)

    code = cli(
        "--project",
        project,
        "tests",
        "repro",
        "T-0001",
        "--by",
        "developer-1",
        "--pre-rev",
        "aaa111",
        "--pre-evidence",
        "pytest @aaa111 -> 12 passed",
        "--post-rev",
        "bbb222",
        "--post-evidence",
        "pytest @bbb222 -> 12 passed",
    )

    assert code != 0
    assert developer_task(root)["repro"] == ""


def test_tests_repro_refuses_an_unknown_task(cli, project: Path) -> None:
    root = init(cli, project)

    code = cli(
        "--project",
        project,
        "tests",
        "repro",
        "T-4040",
        "--by",
        "developer-1",
        "--pre-rev",
        "aaa111",
        "--pre-evidence",
        "pytest @aaa111 -> 3 failed",
        "--post-rev",
        "bbb222",
        "--post-evidence",
        "pytest @bbb222 -> 12 passed",
    )

    assert code != 0
    assert [r["action"] for r in engine.ledger_read(root)].count("tests.repro") == 0


def test_bug_task_cannot_self_check_without_a_repro_record(cli, project: Path) -> None:
    root = init(cli, project)
    add_bug_task(cli, project)
    assert developer_task(root)["kind"] == "bug"

    refused = cli(
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
        "pytest tests/unit/test_parser.py @bbb222 -> 12 passed",
    )

    assert refused != 0
    assert developer_task(root)["self_check"] == "pending"

    # The repro is recorded on the defect task itself and unlocks the self-check.
    assert (
        cli(
            "--project",
            project,
            "tests",
            "repro",
            "T-0001",
            "--by",
            "developer-1",
            "--pre-rev",
            "aaa111",
            "--pre-evidence",
            "pytest @aaa111 -> 3 failed",
            "--post-rev",
            "bbb222",
            "--post-evidence",
            "pytest @bbb222 -> 12 passed",
        )
        == 0
    )

    accepted = cli(
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
        "pytest tests/unit/test_parser.py @bbb222 -> 12 passed",
    )

    assert accepted == 0
    task = developer_task(root)
    assert task["self_check"] == "passed"
    assert task["status"] == "review"


def test_review_pass_binds_its_artifact(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "ship the parser fix",
            "--priority",
            "P1",
            "--status",
            "doing",
            "--claimed-by",
            "developer-1",
        )
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
            "pytest @bbb222 -> 12 passed",
        )
        == 0
    )
    add_evidence_artifact(project)

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
        "pytest @bbb222 -> 12 passed",
        "--artifact",
        "Reports/run.log",
    )

    assert code == 0
    task = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]
    assert task["status"] == "done"
    assert task["review_artifacts"].startswith("Reports/run.log:")
    assert "artifacts: Reports/run.log:" in task["review_evidence"]


def test_review_records_baseline_and_replay(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "ship the parser fix",
            "--priority",
            "P1",
            "--status",
            "doing",
            "--claimed-by",
            "developer-1",
        )
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
            "pytest @bbb222 -> 12 passed",
        )
        == 0
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
        "pytest @bbb222 -> 12 passed",
        "--baseline",
        "clean checkout",
        "--replay",
        "pytest -q",
    )

    assert code == 0
    task = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]
    assert "baseline: clean checkout" in task["review_evidence"]
    assert "replay: pytest -q" in task["review_evidence"]


def test_audit_reports_a_bug_task_closed_without_a_repro(cli, project: Path) -> None:
    init(cli, project)
    add_bug_task(cli, project)
    # The only way past the gate is an explicit override, and the audit still says so.
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
            "cannot reproduce locally",
            "--test",
            "pytest @bbb222 -> 12 passed",
            "--force",
            "defect is environment-specific",
        )
        == 0
    )

    class Sink:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, text: str) -> int:
            self.lines.append(text)
            return len(text)

        def flush(self) -> None:
            return None

    import contextlib

    out = Sink()
    with contextlib.redirect_stdout(out):
        code = cli("--project", project, "audit")

    text = "".join(out.lines)
    assert code != 0
    assert "defect fixes without a fail -> pass repro record" in text
    assert "T-0001" in text
