"""A finished seat is folded at reconcile, so nothing idle is left to print.

AC-M25-6 asks for two things and T-0074 delivered one: the counts name current
seats, and a seat whose lane ended and that holds nothing is folded at the next
reconcile. This pins the fold: move-only (the directory lands under
Runtime/Retired, the role's queue stays), the CEO is never folded, one ledger
event per fold batch, a second reconcile is silent, and `status --json` folds
nothing because it is read-only.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path) -> Path:
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,tester-1", "--no-git") == 0
    )
    return team_root(project)


def test_a_finished_seat_is_folded_once_and_the_ceo_never_is(cli, project, capsys) -> None:
    root = init(cli, project)
    queue = engine.task_file(root, "developer")
    before = queue.read_text(encoding="utf-8")
    seat = engine.agent_dir(root, "developer-1")
    assert seat.is_dir()

    folded = engine.fold_finished_seats(root)

    assert [entry.split()[0] for entry in folded] == ["Developer-1", "Tester-1"], folded
    retired = root / "Runtime" / "Retired" / "Developer-1"
    assert not seat.exists()
    assert retired.is_dir()
    assert engine.agent_dir(root, "ceo").is_dir(), "the CEO is the only voice to the user"
    assert queue.read_text(encoding="utf-8") == before, "role memory and queue stay"
    assert "folded 2 finished seat(s)" in capsys.readouterr().out

    capsys.readouterr()
    assert engine.fold_finished_seats(root) == []
    assert capsys.readouterr().out == "", "a second reconcile with nothing to fold is silent"
    assert sorted(path.name for path in (root / "Runtime" / "Retired").iterdir()) == [
        "Developer-1",
        "Tester-1",
    ]


def test_status_is_read_only_and_folds_no_seat(cli, project) -> None:
    root = init(cli, project)
    assert cli("--project", project, "status", "--json") == 0
    assert engine.agent_dir(root, "developer-1").is_dir()
    assert engine.agent_dir(root, "tester-1").is_dir()
