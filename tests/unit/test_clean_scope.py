"""`clean` touches only the Scratch it was scoped to.

T-0005: `clean --all` swept *every* agent's Scratch, so one lane's documented
janitor run unlinked a peer lane's in-flight renders - the "no lane wars" failure
mode in tool form, and irreversible because scratch files bypass any recycle bin.
The scope is now one agent: the caller's, or the one `--agent` names. Reaching the
whole team takes `--team-wide` and that flag prints each directory before the
first unlink.

Owner: developer. Layer: unit. Area: clean-scope.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def two_lanes(cli, project: Path) -> tuple[Path, Path, Path]:
    """A team where Developer-1 (a peer) and Developer-2 (the caller) both have scratch."""
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,developer-2", "--no-git")
        == 0
    )
    root = team_root(project)
    peer = root / "Agents" / "Developer-1" / "Scratch" / "render" / "in-flight.png"
    peer.parent.mkdir(parents=True, exist_ok=True)
    peer.write_bytes(b"\x89PNG not a real render, only a peer's file")
    mine = root / "Agents" / "Developer-2" / "Scratch" / "notes.md"
    mine.parent.mkdir(parents=True, exist_ok=True)
    mine.write_text("my draft\n", encoding="utf-8")
    return root, peer, mine


def clean(cli, project: Path, *extra: str) -> int:
    return cli("--project", project, "clean", "--no-worktrees", *extra)


def test_an_agent_scoped_clean_keeps_a_peer_scratch_file(cli, project: Path) -> None:
    """The regression: a peer's Scratch file must survive another lane's clean."""
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--agent", "developer-2", "--all") == 0
    assert not mine.exists()
    assert peer.exists(), (
        "clean --agent developer-2 removed a file in Developer-1's Scratch: "
        "an agent-scoped clean must never reach a peer lane"
    )


def test_the_calling_lane_is_the_default_scope(cli, project: Path, monkeypatch) -> None:
    root, peer, mine = two_lanes(cli, project)
    lane = root / engine.DIR_RUNTIME / engine.DIR_WORKTREES / "Developer-2"
    lane.mkdir(parents=True)
    monkeypatch.chdir(lane)
    assert clean(cli, project, "--all") == 0
    assert not mine.exists()
    assert peer.exists()


def test_an_unresolved_caller_is_refused_and_removes_nothing(cli, project: Path) -> None:
    """No scope is guessed: from the main checkout clean stops and says how to scope it."""
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--all") == 2
    assert peer.exists()
    assert mine.exists()


def test_team_wide_announces_every_directory_before_it_removes_anything(
    cli, project: Path, capsys
) -> None:
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--team-wide", "--all") == 0
    out = capsys.readouterr().out
    touched = out.index("team-wide clean")
    removed = out.index("removed")
    assert touched < removed
    for shown in ("Agents/Developer-1", "Agents/Developer-2"):
        assert out.index(shown) < removed, f"{shown} was not announced before removal: {out}"
    assert not peer.exists()
    assert not mine.exists()


def test_team_wide_and_agent_are_mutually_exclusive(cli, project: Path) -> None:
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--team-wide", "--agent", "developer-2", "--all") == 2
    assert peer.exists()
    assert mine.exists()


def test_an_unknown_agent_is_refused_before_anything_is_removed(cli, project: Path) -> None:
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--agent", "nobody-9", "--all") == 2
    assert peer.exists()
    assert mine.exists()


def test_dry_run_still_removes_nothing(cli, project: Path) -> None:
    _, peer, mine = two_lanes(cli, project)
    assert clean(cli, project, "--agent", "developer-2", "--all", "--dry-run") == 0
    assert mine.exists()
    assert peer.exists()
