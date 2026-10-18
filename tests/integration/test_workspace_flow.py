"""Integration tests: a full Nidvue Teamwork workspace lifecycle on ``tmp_path``.

Each test bootstraps its own workspace (the autouse ``isolated_workspace``
fixture clears ambient state and gives every test a fresh tmp dir) and drives
the real CLI entry point, asserting both the exit codes and the on-disk files.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

AGENTS = ("ceo", "developer-1", "reviewer-1")


def team_root(project: Path) -> Path:
    """The hidden tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init_team(cli, project: Path, agents=AGENTS) -> Path:
    code = cli("--project", project, "init", "--agents", ",".join(agents), "--no-git")
    assert code == 0, f"init returned {code}"
    root = team_root(project)
    assert root.is_dir()
    return root


# --------------------------------------------------------------------------- #
# bootstrap
# --------------------------------------------------------------------------- #


def test_init_creates_the_workspace_layout(cli, project: Path) -> None:
    root = init_team(cli, project)

    for rel in (
        "Roles/CEO/TaskQueue.md",
        "Roles/CEO/ShortTermMemory.md",
        "Roles/CEO/LongTermMemory.md",
        "Roles/Developer/TaskQueue.md",
        "Roles/Reviewer/TaskQueue.md",
        "Global/GlobalMemory.md",
        "Criteria.md",
        "Tests.md",
        "TestPlan.md",
        "Disputes.md",
        "Reviews.md",
        "Skills.md",
        "TeamMap.md",
        "Settings.json",
        "Ledger.jsonl",
        "Runtime/LedgerHead.json",
        "Agents/Developer-1/StartHere.md",
        "Agents/Developer-1/WorkLog.md",
        "Agents/Developer-1/Inbox.md",
        "Roles/Developer/Role.md",
    ):
        assert (root / rel).exists(), f"init did not create {rel}"

    assert (project / "docs" / "Team" / "Project.md").is_file()


def test_init_ledger_is_seeded_and_verifies(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert engine.ledger_verify(root) == []
    actions = [r["action"] for r in engine.ledger_read(root)]
    assert "decision.add" in actions and "ledger.export" in actions
    assert cli("--project", project, "ledger", "verify") == 0


# --------------------------------------------------------------------------- #
# memory
# --------------------------------------------------------------------------- #


def test_global_and_remember_write_memory(cli, project: Path) -> None:
    root = init_team(cli, project)

    assert cli("--project", project, "global", "shared fact", "--key", "fact") == 0
    assert (
        cli(
            "--project",
            project,
            "remember",
            "developer-1",
            "local fact",
            "--key",
            "local",
            "--by",
            "developer-1",
        )
        == 0
    )

    global_entries = engine.parse_memory(root / "Global" / "GlobalMemory.md")
    assert [e["key"] for e in global_entries] == ["fact"]
    assert global_entries[0]["body"] == "shared fact"

    role_entries = engine.parse_memory(root / "Roles" / "Developer" / "ShortTermMemory.md")
    assert [e["body"] for e in role_entries] == ["local fact"]


# --------------------------------------------------------------------------- #
# tasks
# --------------------------------------------------------------------------- #


def test_task_add_and_next_claims_the_task(cli, project: Path) -> None:
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build it",
            "--priority",
            "P0",
            "--body",
            "acceptance: it builds",
        )
        == 0
    )
    assert cli("--project", project, "task", "next", "developer-1") == 0

    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    assert len(tasks) == 1
    task = tasks[0]
    assert task["id"] == "T-0001"
    assert task["priority"] == "P0"
    assert task["status"] == "doing"
    assert task["claimed_by"] == "developer-1"
    assert "it builds" in task["body"]


def test_task_next_without_work_returns_3(cli, project: Path) -> None:
    init_team(cli, project)
    assert cli("--project", project, "task", "next", "developer-1") == 3


def test_task_add_does_not_duplicate_an_identical_title(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer-1", "Same") == 0
    assert cli("--project", project, "task", "add", "developer-1", "same") == 0
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")
    assert len(tasks) == 1


# --------------------------------------------------------------------------- #
# criteria + layered tests
# --------------------------------------------------------------------------- #


def test_criteria_add_and_independent_verify_via_passing_test(cli, project: Path) -> None:
    root = init_team(cli, project)

    assert (
        cli(
            "--project",
            project,
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the widget works",
            "--owner",
            "ceo",
            "--by",
            "ceo",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "api",
            "--command",
            "pytest -q",
        )
        == 0
    )
    assert (
        cli(
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
            "pytest -q @abc123 -> 4 passed",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "criteria",
            "verify",
            "AC-1",
            "--by",
            "reviewer-1",
            "--test",
            "TS-0001",
        )
        == 0
    )

    criteria = engine.parse_criteria(root / "Criteria.md")
    assert criteria[0]["status"] == "verified"
    assert criteria[0]["verified_by"] == "Reviewer-1"
    assert "TS-0001" in criteria[0]["evidence"]

    records = engine.parse_tests(root / "Tests.md")
    assert records[0]["id"] == "TS-0001"
    assert records[0]["status"] == "passing"
    assert records[0]["owner"] == "Developer-1"


def test_criteria_verify_rejects_the_owning_role(cli, project: Path) -> None:
    init_team(cli, project)
    assert (
        cli(
            "--project",
            project,
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the widget works",
            "--owner",
            "ceo",
            "--by",
            "ceo",
        )
        == 0
    )
    # The CEO owns AC-1, so the CEO may not verify it.
    assert (
        cli(
            "--project",
            project,
            "criteria",
            "verify",
            "AC-1",
            "--by",
            "ceo",
            "--evidence",
            "trust me @abc -> ok",
        )
        != 0
    )


def test_tests_add_rejects_a_duplicate_layer_area(cli, project: Path) -> None:
    init_team(cli, project)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "api",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "api",
        )
        != 0
    )


def test_tests_run_rejects_the_wrong_role(cli, project: Path) -> None:
    init_team(cli, project)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "api",
        )
        == 0
    )
    # A unit record belongs to the Developer; the Reviewer may not run it.
    assert (
        cli(
            "--project",
            project,
            "tests",
            "run",
            "TS-0001",
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest -q @abc -> 4 passed",
        )
        != 0
    )


# --------------------------------------------------------------------------- #
# end-to-end + audit trail
# --------------------------------------------------------------------------- #


def test_full_lifecycle_and_clean_ledger(cli, project: Path) -> None:
    root = init_team(cli, project)

    steps = [
        ("global", "shared fact", "--key", "fact"),
        ("remember", "developer-1", "local fact", "--key", "local"),
        ("task", "add", "developer-1", "Ship it", "--priority", "P0"),
        ("task", "next", "developer-1"),
        ("criteria", "add", "--id", "AC-1", "--text", "it ships", "--owner", "ceo", "--by", "ceo"),
        ("tests", "add", "--layer", "unit", "--area", "api"),
        (
            "tests",
            "run",
            "TS-0001",
            "--by",
            "developer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest -q @abc -> 4 passed",
        ),
        ("criteria", "verify", "AC-1", "--by", "reviewer-1", "--test", "TS-0001"),
    ]
    for step in steps:
        assert cli("--project", project, *step) == 0, f"failed step: {step}"

    # 9 + 2 bootstrap records minimum.
    records = engine.ledger_read(root)
    assert len(records) >= 10
    head = json.loads((root / "Runtime" / "LedgerHead.json").read_text(encoding="utf-8"))
    assert head == {"n": len(records), "hash": records[-1]["hash"]}

    assert cli("--project", project, "ledger", "verify") == 0
    assert engine.ledger_verify(root) == []


def test_ledger_tamper_is_detected_after_the_flow(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "global", "a fact", "--key", "k") == 0

    path = root / "Ledger.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["detail"] = "tampered"
    lines[1] = json.dumps(record, sort_keys=True, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert cli("--project", project, "ledger", "verify") == 1
    assert any("digest mismatch" in p for p in engine.ledger_verify(root))


def test_reviewed_branch_is_merged_and_deleted(cli, project: Path) -> None:
    """The full branch -> PR -> verdict -> merge path, including the two Reviewers."""
    agents = ("ceo", "developer-1", "reviewer-1", "reviewer-2")
    assert cli("--project", project, "init", "--agents", ",".join(agents)) == 0
    root = team_root(project)

    assert cli("--project", project, "task", "add", "developer", "ship it", "--priority", "P0") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "branch",
            "start",
            "--agent",
            "developer-1",
            "--task",
            "T-0001",
        )
        == 0
    )
    (project / "feature.txt").write_text("done\n", encoding="utf-8")
    assert (
        cli(
            "--project",
            project,
            "commit",
            "--role",
            "developer",
            "--type",
            "feat",
            "--task",
            "T-0001",
            "--area",
            "core",
            "--goal",
            "ship it",
            "--deliverable",
            "feature.txt",
            "--why",
            "the task asked for it",
            "--status",
            "implemented",
            "--result",
            "true @rev -> ok",
            "--all",
        )
        == 0
    )
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
            "true @rev -> ok",
        )
        == 0
    )
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "review") == 0
    )
    assert (
        cli("--project", project, "pr", "open", "--agent", "developer-1", "--task", "T-0001") == 0
    )
    prs = engine.parse_reviews(root / "Reviews.md")
    assert len(prs) == 1 and prs[0]["status"] == "open"
    pr_id = prs[0]["id"]

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
            "pytest @rev -> ok",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "pr",
            "merge",
            "--pr",
            pr_id,
            "--by",
            "reviewer-2",
        )
        == 0
    )
    task = engine.parse_tasks(root / "Roles" / "Developer" / "TaskQueue.md")[0]
    assert task["status"] == "done"
    assert task["merge_commit"]
    assert engine.branch_exists(project, task["branch"]) is False
    merge_message = engine.run_git(project, "log", "-1", "--format=%B").stdout
    assert "Acting role: Reviewer" in merge_message
