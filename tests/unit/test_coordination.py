"""Coordination health: the multi-agent failure modes the records can show.

Why these tests exist: the article this change is built from measured that lanes
sharing a model, a context and a queue fail together, that starved lanes poll and
race, and that a review lane with no cross-check turns one blind spot into a
systemic one. The team already writes every record these checks need, so each
finding must be reproducible from the workspace alone - no new telemetry, no
network, no live provider.

Pinned here: duplicate branch/title detection, Reviewer model diversity,
verbatim-evidence echo, reviewer monoculture, merge-rate collapse, the live-lane
reclaim guard, and the pulse's refusal to plan more new lanes than free slots.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1,reviewer-2"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def codes(report: dict) -> set:
    return {finding["code"] for finding in report["findings"]}


def task_path(root: Path, role: str) -> Path:
    return engine.task_file(root, role)


def edit_task(root: Path, role: str, handle: str, **fields) -> None:
    path = task_path(root, role)
    tasks = engine.parse_tasks(path)
    task = next(t for t in tasks if t["id"] == handle)
    task.update(fields)
    engine.write_tasks(path, tasks, role)


def test_duplicate_branch_and_title_are_diversity_findings(cli, project: Path) -> None:
    root = init(cli, project)
    title = "implement the shared parser"
    assert cli("--project", project, "task", "add", "developer", title) == 0
    assert cli("--project", project, "task", "add", "tester", title) == 0
    edit_task(root, "developer", "T-0001", branch="shared/parser")
    edit_task(root, "tester", "T-0001", branch="shared/parser")

    found = codes(engine.coordination_report(root))
    assert "C-DIV-BRANCH" in found
    assert "C-DIV-TASK" in found


def test_reviewer_model_diversity_is_required_when_two_lanes_review(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli("--project", project, "model", "set", "reviewer", "--provider", "p", "--model", "one")
        == 0
    )
    report = engine.coordination_report(root)
    diversity = [f for f in report["findings"] if f["code"] == "C-DIV-MODEL"]
    assert diversity and diversity[0]["severity"] == "high"

    # A second model on the second lane clears the finding; the check reads the
    # effective model, not the fact that a setting exists.
    assert (
        cli(
            "--project",
            project,
            "model",
            "set",
            "reviewer-2",
            "--provider",
            "p",
            "--model",
            "two",
        )
        == 0
    )
    assert "C-DIV-MODEL" not in codes(engine.coordination_report(root))


def test_verbatim_review_evidence_is_an_echo(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "fix the parser") == 0
    evidence = "pytest tests/unit/test_parser.py @abc1234 -> 12 passed"
    edit_task(
        root,
        "developer",
        "T-0001",
        evidence=evidence,
        review_status="passed",
        review_evidence=evidence,
        status="done",
    )
    assert "C-TRUST-ECHO" in codes(engine.coordination_report(root))


def test_reviewer_monoculture_and_no_finding_lane_are_flagged(cli, project: Path) -> None:
    root = init(cli, project)
    for index in range(8):
        engine.ledger_append(root, "review.pass", "Reviewer-1", f"T-{index:04d}", "pytest -> ok")
    found = codes(engine.coordination_report(root))
    assert "C-TRUST-MONOCULTURE" in found
    assert "C-TRUST-NOFAIL" in found


def test_merge_rate_below_half_is_a_merge_health_finding(cli, project: Path) -> None:
    root = init(cli, project)
    prs = [
        engine.new_pr(
            f"pr {index}",
            status="merged" if index == 0 else "open",
            updated="2026-01-01",
            branch=f"dev/t-{index}",
        )
        for index in range(5)
    ]
    engine.write_reviews(engine.reviews_path(root), prs)
    report = engine.coordination_report(root)
    assert "C-MERGE-RATE" in codes(report)
    assert report["metrics"]["merge_fraction"] == 0.2


def test_reclaim_refuses_a_live_lane_and_force_is_recorded(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "live work") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "slot",
            "acquire",
            "--agent",
            "developer-1",
            "--provider",
            "ollama-cloud",
        )
        == 0
    )

    refused = cli(
        "--project",
        project,
        "task",
        "reclaim",
        "developer",
        "T-0001",
        "--as",
        "developer-2",
        "--reason",
        "silent",
    )
    assert refused == 2
    task = engine.parse_tasks(task_path(root, "developer"))[0]
    assert task["claimed_by"].lower() == "developer-1"
    assert task["status"] == "doing"

    forced = cli(
        "--project",
        project,
        "task",
        "reclaim",
        "developer",
        "T-0001",
        "--as",
        "developer-2",
        "--reason",
        "owner is dead",
        "--force",
        "confirmed dead for two hours",
    )
    assert forced == 0
    task = engine.parse_tasks(task_path(root, "developer"))[0]
    assert task["status"] == "todo" and task["claimed_by"] == ""
    assert "forced: confirmed dead" in task["findings"]

    # A released lease means the owner really is silent: no force needed.
    assert (
        cli(
            "--project",
            project,
            "slot",
            "release",
            "--agent",
            "developer-1",
            "--provider",
            "ollama-cloud",
        )
        == 0
    )
    # developer-2 now owns it; give the task to developer-1 first so the
    # reclaim crosses lanes again.
    edit_task(root, "developer", "T-0001", claimed_by="Developer-1", status="doing")
    assert (
        cli(
            "--project",
            project,
            "task",
            "reclaim",
            "developer",
            "T-0001",
            "--as",
            "developer-2",
            "--reason",
            "lease expired",
        )
        == 0
    )


def test_pulse_defers_more_new_lanes_than_free_slots(cli, project: Path) -> None:
    root = init(cli, project)
    settings = json.loads((root / engine.F_SETTINGS).read_text(encoding="utf-8"))
    for provider in ("ollama-cloud", "deepseek", "openai", "anthropic", "default"):
        settings[provider] = 0
    (root / engine.F_SETTINGS).write_text(json.dumps(settings), encoding="utf-8")

    for title in ("one", "two", "three"):
        assert cli("--project", project, "task", "add", "developer", title) == 0
    assert cli("--project", project, "pulse", "--commit") == 3
    tasks = engine.parse_tasks(task_path(root, "developer"))
    assert all(task["status"] == "todo" for task in tasks), "a starved pulse claimed work"

    settings["ollama-cloud"] = 1
    (root / engine.F_SETTINGS).write_text(json.dumps(settings), encoding="utf-8")
    assert cli("--project", project, "pulse", "--commit") == 0
    tasks = engine.parse_tasks(task_path(root, "developer"))
    # one lease covers a lane's WIP: the first lane takes both of its units on the
    # single free slot, and the second lane is the one deferred (T-0020/A5)
    doing = [task for task in tasks if task["status"] == "doing"]
    assert len(doing) == engine.LANE_WIP, [task["status"] for task in tasks]
    assert {task["claimed_by"].lower() for task in doing} == {"developer-1"}


def test_strict_exits_one_on_a_high_finding(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one piece") == 0
    assert cli("--project", project, "task", "add", "tester", "one piece") == 0
    edit_task(root, "developer", "T-0001", branch="same")
    edit_task(root, "tester", "T-0001", branch="same")

    assert cli("--project", project, "coordination") == 0
    assert cli("--project", project, "coordination", "--strict") == 1
    assert "C-DIV-BRANCH" in capsys.readouterr().out
