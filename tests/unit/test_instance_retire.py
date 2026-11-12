"""Retirement is move-only: an idle lane's evidence must survive the roster cut.

`instance retire` used to call `shutil.rmtree`, which destroyed the lane's
`Artifacts/`, `Reports/` and `WorkLog.md` - records the ledger and
`docs/Team/Archive.md` may still cite. Throughput.md section 3 ranks the roster
cut as blocked on that defect, so the tests here pin the three parts of the fix:
the directory is moved under `Runtime/Retired/<Instance>/`, a second retirement
of the same name lands beside the first instead of replacing it, and a failed
move is a hard error with the source still intact - never a fallback to delete.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import engine


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    return team_root(project)


def test_retirement_moves_artifacts_under_runtime_retired(cli, project: Path) -> None:
    root = init(cli, project)
    lane = engine.agent_dir(root, "developer-1")
    artifact = lane / "Artifacts" / "T-0001-proof.txt"
    artifact.write_text("the measured evidence\n", encoding="utf-8")
    report = lane / "Reports" / "T-0001-report.md"
    report.write_text("# report\n", encoding="utf-8")

    assert cli("--project", project, "instance", "retire", "developer-1", "--reason", "idle") == 0

    retired = root / "Runtime" / "Retired" / "Developer-1"
    assert not lane.exists()
    assert (retired / "Artifacts" / "T-0001-proof.txt").read_text(encoding="utf-8") == (
        "the measured evidence\n"
    )
    assert (retired / "Reports" / "T-0001-report.md").is_file()

    records = [r for r in engine.ledger_read(root) if r["action"] == "instance.retire"]
    assert records, "the retirement must be recorded in the ledger"
    assert "Runtime/Retired/Developer-1" in records[-1]["detail"]


def test_a_second_retirement_of_the_same_name_never_replaces_the_first(cli, project: Path) -> None:
    root = init(cli, project)
    first = root / "Runtime" / "Retired" / "Developer-1"
    first.mkdir(parents=True)
    (first / "old-evidence.txt").write_text("keep me\n", encoding="utf-8")

    assert cli("--project", project, "instance", "retire", "developer-1", "--reason", "idle") == 0

    siblings = sorted(
        path for path in first.parent.iterdir() if path.name.startswith("Developer-1")
    )
    assert first.is_dir()
    assert (first / "old-evidence.txt").is_file()
    assert len(siblings) == 2
    stamped = next(path for path in siblings if path != first)
    assert stamped.name.startswith("Developer-1-")
    assert (stamped / "Artifacts").is_dir()


def test_a_failed_move_is_a_hard_error_and_never_deletes_the_lane(
    cli, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init(cli, project)
    lane = engine.agent_dir(root, "developer-1")
    (lane / "Artifacts" / "proof.txt").write_text("still mine\n", encoding="utf-8")

    def refuse(_source, _destination):
        raise OSError("read-only volume")

    monkeypatch.setattr(engine.shutil, "move", refuse)
    code = cli("--project", project, "instance", "retire", "developer-1", "--reason", "idle")

    assert code == 1
    assert (lane / "Artifacts" / "proof.txt").is_file()
    assert not (root / "Runtime" / "Retired" / "Developer-1").exists()


def _append_fixture_task(path: Path, tid: str, status: str, claimed: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(
            f"\n## {tid} - fixture\n"
            "- priority: P2\n"
            f"- status: {status}\n"
            f"- claimed_by: {claimed}\n"
            "- updated: 2026-11-01\n\n"
            "fixture body\n"
        )


def test_a_closed_task_claimed_by_a_retired_lane_is_not_a_phantom(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project)
    _append_fixture_task(engine.task_file(root, "developer"), "T-9001", "done", "Developer-1")

    assert cli("--project", project, "instance", "retire", "developer-1", "--reason", "idle") == 0
    cli("--project", project, "audit")
    out = capsys.readouterr().out

    assert "unknown agent 'Developer-1'" not in out, out
    assert "claimed by retired agent 'Developer-1'" not in out, out


def test_an_open_task_claimed_by_a_retired_lane_is_reported(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    _append_fixture_task(engine.task_file(root, "developer"), "T-9002", "doing", "Developer-1")

    assert (
        cli(
            "--project",
            project,
            "instance",
            "retire",
            "developer-1",
            "--reason",
            "test: abandoned lane",
            "--force",
        )
        == 0
    )
    cli("--project", project, "audit")
    out = capsys.readouterr().out

    assert "T-9002 is doing but claimed by retired agent 'Developer-1'" in out, out


def _roster(cli, project: Path, agents: str) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def test_prune_folds_every_idle_instance_and_keeps_the_ceo(cli, project: Path) -> None:
    """The user's rule: no idle instance holds a seat once it has nothing to do."""
    root = _roster(cli, project, "ceo,developer-1,developer-2,tester-1,reviewer-1")
    assert cli("--project", project, "instance", "prune", "--dry-run") == 0
    assert engine.agent_dir(root, "developer-2").is_dir(), "a dry run must move nothing"

    assert (
        cli("--project", project, "instance", "prune", "--reason", "idle after the queue drained")
        == 0
    )

    assert engine.agent_dir(root, "ceo").is_dir(), "the CEO is the only voice to the user"
    for name in ("developer-1", "developer-2", "tester-1", "reviewer-1"):
        assert not engine.agent_dir(root, name).is_dir(), name
        assert (root / "Runtime" / "Retired" / engine.pascal(name)).is_dir(), name
    retired = [r for r in engine.ledger_read(root) if r["action"] == "instance.retire"]
    assert len(retired) == 4, retired
    assert all("idle after the queue drained" in r["detail"] for r in retired)

    assert cli("--project", project, "instance", "prune") == 0, "a second prune is a no-op"


def test_prune_never_folds_a_busy_instance(cli, project: Path) -> None:
    root = _roster(cli, project, "ceo,developer-1,developer-2")
    assert cli("--project", project, "task", "add", "developer", "the only task") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0

    assert cli("--project", project, "instance", "prune") == 0

    assert engine.agent_dir(root, "developer-1").is_dir(), "a claimed task is work in flight"
    assert not engine.agent_dir(root, "developer-2").is_dir(), "an idle peer is still folded"


def test_prune_keep_required_leaves_one_instance_of_each_gate_role(cli, project: Path) -> None:
    root = _roster(cli, project, "ceo,developer-1,developer-2,tester-1,reviewer-1,reviewer-2")
    assert cli("--project", project, "instance", "prune", "--keep-required") == 0

    assert len(engine.instances_of(root, "developer")) == 1
    assert len(engine.instances_of(root, "tester")) == 1
    assert len(engine.instances_of(root, "reviewer")) == 1
    assert engine.agent_dir(root, "ceo").is_dir()


def test_pulse_folds_surplus_idle_instances_when_it_commits(cli, project: Path) -> None:
    """The CEO wake-up folds what it cannot feed - it never leaves a lane hanging."""
    root = _roster(cli, project, "ceo,developer-1,developer-2,tester-1,reviewer-1,reviewer-2")
    assert cli("--project", project, "pulse", "--commit") in (0, 3), "3 = nothing to dispatch"

    assert engine.agent_dir(root, "ceo").is_dir()
    assert len(engine.instances_of(root, "developer")) == 1
    assert len(engine.instances_of(root, "reviewer")) == 1
    assert not engine.agent_dir(root, "developer-2").is_dir()
    assert not engine.agent_dir(root, "reviewer-2").is_dir()
