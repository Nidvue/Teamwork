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
