"""Integration coverage for the command surface that the gates depend on.

These are deliberately CLI-level: each command is exercised through
``engine.main`` against a throwaway workspace, so argument wiring, locks and
rendering are all part of the assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, *extra: str) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git", *extra) == 0
    return team_root(project)


def test_decision_list_and_trace(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "decision",
            "add",
            "--by",
            "ceo",
            "--decision",
            "use the bounded queue",
            "--evidence",
            "pytest @rev -> ok",
        )
        == 0
    )
    decision_id = next(
        line.split(" ", 2)[1]
        for line in (root.parents[3] / "docs" / "Team" / "Decisions.md")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("## D-") and "2026" in line
    )
    assert cli("--project", project, "decision", "list") == 0
    assert cli("--project", project, "trace", decision_id) == 0
    assert cli("--project", project, "trace", "nothing-references-this") == 3


def test_slot_lifecycle_and_provider_cap(cli, project: Path) -> None:
    root = init(cli, project)
    settings = json.loads((root / engine.F_SETTINGS).read_text(encoding="utf-8"))
    settings["testcap"] = 1
    (root / engine.F_SETTINGS).write_text(json.dumps(settings) + "\n", encoding="utf-8")

    assert (
        cli(
            "--project",
            project,
            "slot",
            "acquire",
            "--agent",
            "developer-1",
            "--provider",
            "testcap",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "slot",
            "acquire",
            "--agent",
            "developer-2",
            "--provider",
            "testcap",
        )
        == 3
    )
    assert cli("--project", project, "slot", "list") == 0
    assert (
        cli(
            "--project",
            project,
            "slot",
            "renew",
            "--agent",
            "developer-1",
            "--provider",
            "testcap",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "slot",
            "release",
            "--agent",
            "developer-1",
            "--provider",
            "testcap",
        )
        == 0
    )
    assert cli("--project", project, "slot", "reap") == 0


def test_board_parallel_pulse_and_map(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "ship") == 0
    assert cli("--project", project, "board") == 0
    assert cli("--project", project, "parallel") == 0
    assert cli("--project", project, "pulse", "--commit") == 0
    assert cli("--project", project, "map") == 0
    task = engine.parse_tasks(root / "Roles" / "Developer" / engine.F_TASKS)[0]
    assert task["status"] == "doing"
    assert task["claimed_by"] == "Developer-1"


def test_clean_removes_scratch_only(cli, project: Path) -> None:
    root = init(cli, project)
    scratch = root / "Agents" / "Developer-1" / "Scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "a.tmp").write_text("x", encoding="utf-8")
    (scratch / "keep.md").write_text("keep", encoding="utf-8")
    assert cli("--project", project, "clean", "--dry-run") == 0
    assert cli("--project", project, "clean") == 0
    assert not (scratch / "a.tmp").exists()
    assert (scratch / "keep.md").exists()
    assert cli("--project", project, "clean", "--all") == 0
    assert not (scratch / "keep.md").exists()


def test_links_and_model_commands(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "links") == 0
    assert (
        cli(
            "--project",
            project,
            "model",
            "set",
            "developer-1",
            "--provider",
            "p",
            "--model",
            "m",
        )
        == 0
    )
    assert cli("--project", project, "model", "get", "developer-1") == 0
    assert cli("--project", project, "model", "list") == 0
    assert cli("--project", project, "model", "auto") == 0


def test_ledger_export_dry_run_and_stats(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "ledger", "export", "--dry-run") == 0
    assert cli("--project", project, "stats", "--all") == 0
    assert cli("--project", project, "agents") == 0


def test_ledger_export_does_not_pin_the_append_only_archive(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "ledger", "export") == 0

    manifest = json.loads(
        (project / "docs" / "Team" / "AuditManifest.json").read_text(encoding="utf-8")
    )
    paths = [a["path"] for a in manifest["artifacts"]]

    # the archive gains an entry when the review passes, so pinning it would be
    # stale the moment its own manifest is merged
    assert "docs/Team/Archive.md" not in paths
    assert "docs/Team/Project.md" in paths
    assert "docs/Team/Decisions.md" in paths


def test_dispute_round_cap_sign_and_resolve(cli, project: Path) -> None:
    init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            "developer-1",
            "--against",
            "tester-1",
            "--topic",
            "round cap",
        )
        == 0
    )
    for _ in range(3):
        assert (
            cli(
                "--project",
                project,
                "dispute",
                "round",
                "D-0001",
                "--by",
                "developer-1",
                "--message",
                "evidence",
            )
            == 0
        )
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "round",
            "D-0001",
            "--by",
            "developer-1",
            "--message",
            "one too many",
        )
        == 2
    )
    # The panel is every independent member this roster staffs (ceo + reviewer), so
    # both must sign before the ruling - a one-signature panel was the old defect.
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "ceo",
            "--decision",
            "stop",
        )
        == 0
    )
    assert cli("--project", project, "dispute", "list") == 0


def test_review_queue_and_branch_list(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER) == 0
    assert cli("--project", project, "task", "add", "developer", "ship") == 0
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
    assert cli("--project", project, "branch", "list") == 0
    assert cli("--project", project, "pr", "list") == 0
    assert cli("--project", project, "review", "--queue") == 0
