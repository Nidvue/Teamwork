"""The feature-team flow over the CLI: record, freeze, squad, slice, claim, independence.

Drives the commands the team actually uses: a Team Leader files the slice
(proposed), the Architect freezes it ready with an interface, a squad instance is
attached, a task is sliced, and the claim gate follows the feature state. A
second feature on the same path must fail the independence check.

Owner: team-leader. Task: T-0042. Requirements: Architecture.md 13.2.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

AGENTS = "ceo,architect-1,team-leader-1,team-leader-2,developer-1,developer-2,reviewer-1"


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def file_feature(cli, project: Path, owner: str, path: str, statement: str) -> int:
    return cli(
        "--project",
        project,
        "feature",
        "add",
        statement,
        "--owner",
        owner,
        "--paths",
        path,
        "--by",
        owner,
    )


def freeze(cli, project: Path, handle: str) -> int:
    """The Architect's freeze: an interface anchor and the move to ready."""
    return cli(
        "--project",
        project,
        "feature",
        "set",
        handle,
        "--state",
        "ready",
        "--interface",
        "Architecture.md#3",
        "--by",
        "architect-1",
    )


def activate(cli, project: Path, handle: str, owner: str) -> int:
    return cli("--project", project, "feature", "set", handle, "--state", "active", "--by", owner)


def attach(cli, project: Path, under: str, name: str) -> int:
    return cli(
        "--project", project, "instance", "add", "developer", "--under", under, "--name", name
    )


def test_a_sliced_task_is_held_until_the_feature_is_active(cli, project, capsys) -> None:
    init(cli, project)
    assert file_feature(cli, project, "team-leader-1", "src/feature_view.py", "ships the view") == 0
    assert "F-0001" in capsys.readouterr().out
    assert freeze(cli, project, "F-0001") == 0
    assert attach(cli, project, "team-leader-1", "developer-3") == 0
    assert (
        cli(
            "--project", project, "task", "add", "developer", "the view work", "--feature", "F-0001"
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "next", "developer-3") == 3

    assert activate(cli, project, "F-0001", "team-leader-1") == 0
    capsys.readouterr()
    assert cli("--project", project, "task", "next", "developer-3") == 0
    assert "the view work" in capsys.readouterr().out


def test_another_teams_instance_cannot_take_the_slice(cli, project, capsys) -> None:
    init(cli, project)
    assert file_feature(cli, project, "team-leader-1", "src/feature_view.py", "ships the view") == 0
    assert freeze(cli, project, "F-0001") == 0
    assert activate(cli, project, "F-0001", "team-leader-1") == 0
    assert attach(cli, project, "team-leader-1", "developer-3") == 0
    assert (
        cli(
            "--project", project, "task", "add", "developer", "the view work", "--feature", "F-0001"
        )
        == 0
    )
    assert attach(cli, project, "team-leader-2", "developer-4") == 0
    capsys.readouterr()

    assert cli("--project", project, "task", "next", "developer-4") == 3
    assert "has no executable task of its own team" in capsys.readouterr().out


def test_an_overlapping_slice_is_refused_and_an_independent_one_is_not(
    cli, project, capsys
) -> None:
    init(cli, project)
    assert file_feature(cli, project, "team-leader-1", "src/feature_view.py", "ships the view") == 0
    assert freeze(cli, project, "F-0001") == 0
    capsys.readouterr()

    assert file_feature(cli, project, "team-leader-2", "src/feature_view.py", "ships it again") == 2
    refused = capsys.readouterr().out
    assert "share a writable path" in refused and "src/feature_view.py" in refused

    assert (
        file_feature(cli, project, "team-leader-2", "src/other_view.py", "ships another view") == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "feature", "check") == 0
