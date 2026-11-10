"""`clean` unlinks only inside the scope it was given.

T-0005: `clean --all` swept *every* agent's Scratch and a workspace-wide temp pass
that no flag filtered, so one lane's janitor run unlinked a peer lane's in-flight
files - the "no lane wars" failure mode in tool form, and irreversible because
scratch files bypass any recycle bin.

The scope is one lane: the caller's worktree or `--agent <name>`. Every unlink -
the `--all` emptying *and* the `*.tmp`/`*.temp` pass - goes through that scope.
`--team-wide` is the only way to reach another lane or the shared `Global/` and
`Roles/` state, and it prints every location before the first unlink.

Most cases here assert **effects** (which files exist afterwards); the exit-code
cases at the end are contract checks, not the guard.

Owner: developer. Layer: unit. Area: clean-scope.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

#: Three files per lane: one ordinary scratch file (removed only by `--all`) and
#: two that match `SCRATCH_PATTERNS` (removed by every clean).
SCRATCH_FILES = ("render/in-flight.png", "in-flight.tmp", "notes.temp")


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def seed(cli, project: Path) -> tuple[Path, list[Path], list[Path], list[Path]]:
    """A team where Developer-1 (a peer) and Developer-2 (the caller) both have scratch.

    Returns the team root, the peer's files, the caller's files and the
    team-shared temp files that belong to no lane.
    """
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,developer-2", "--no-git")
        == 0
    )
    root = team_root(project)

    def lane(name: str) -> list[Path]:
        base = root / "Agents" / name
        out = []
        for rel in SCRATCH_FILES:
            path = base / "Scratch" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"lane work in flight")
            out.append(path)
        artifact = base / "Artifacts" / "draft.tmp"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("lane artifact temp\n", encoding="utf-8")
        out.append(artifact)
        return out

    peer = lane("Developer-1")
    mine = lane("Developer-2")
    shared = [root / "Roles" / "Developer" / "queue.tmp", root / "Global" / "board.tmp"]
    for path in shared:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("shared temp\n", encoding="utf-8")
    return root, peer, mine, shared


def clean(cli, project: Path, *extra: str) -> int:
    return cli("--project", project, "clean", "--no-worktrees", *extra)


def caller_worktree(root: Path, monkeypatch, name: str = "Developer-2") -> Path:
    """Run the caller from its lane worktree, which is how `clean` resolves its scope."""
    lane = root / engine.DIR_RUNTIME / engine.DIR_WORKTREES / name
    lane.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(lane)
    return lane


def test_a_peer_scratch_file_survives_an_agent_scoped_clean(cli, project: Path) -> None:
    """The regression: `--agent developer-2 --all` must not reach Developer-1 at all."""
    _, peer, mine, _ = seed(cli, project)
    clean(cli, project, "--agent", "developer-2", "--all")
    for path in peer:
        assert path.exists(), f"an agent-scoped clean removed a peer lane's file: {path}"
    for path in mine:
        assert not path.exists(), f"--all left the caller's own scratch file behind: {path}"


def test_the_calling_lane_is_the_default_scope(cli, project: Path, monkeypatch) -> None:
    root, peer, mine, _ = seed(cli, project)
    caller_worktree(root, monkeypatch)
    clean(cli, project, "--all")
    for path in peer:
        assert path.exists(), f"the caller's clean reached a peer lane: {path}"
    for path in mine:
        assert not path.exists(), f"the caller's own scratch file survived: {path}"


def test_the_temp_pattern_pass_never_reaches_a_peer_lane(cli, project: Path, monkeypatch) -> None:
    """`clean` without `--all` removes temp patterns - in the caller's lane only."""
    root, peer, mine, shared = seed(cli, project)
    caller_worktree(root, monkeypatch)
    clean(cli, project)
    for path in peer:
        assert path.exists(), f"the temp-pattern pass unlinked a peer lane's file: {path}"
    for path in shared:
        assert path.exists(), f"the temp-pattern pass unlinked shared state: {path}"
    assert not (root / "Agents" / "Developer-2" / "Scratch" / "in-flight.tmp").exists()
    assert not (root / "Agents" / "Developer-2" / "Scratch" / "notes.temp").exists()
    assert not (root / "Agents" / "Developer-2" / "Artifacts" / "draft.tmp").exists()
    assert (root / "Agents" / "Developer-2" / "Scratch" / "render" / "in-flight.png").exists()


def test_roles_and_global_temp_files_survive_an_agent_scoped_clean(
    cli, project: Path, monkeypatch
) -> None:
    """The shared tree is nobody's lane: only --team-wide may touch it."""
    root, peer, mine, shared = seed(cli, project)
    caller_worktree(root, monkeypatch)
    clean(cli, project, "--all")
    for path in shared:
        assert path.exists(), f"an agent-scoped clean unlinked shared team state: {path}"
    for path in mine:
        assert not path.exists()


def test_dry_run_removes_nothing(cli, project: Path, monkeypatch) -> None:
    root, peer, mine, shared = seed(cli, project)
    caller_worktree(root, monkeypatch)
    assert clean(cli, project, "--all", "--dry-run") == 0
    for path in [*peer, *mine, *shared]:
        assert path.exists(), f"--dry-run unlinked {path}"


def test_team_wide_removes_the_peer_and_announces_each_location_first(
    cli, project: Path, capsys
) -> None:
    _, peer, mine, shared = seed(cli, project)
    code = clean(cli, project, "--team-wide", "--all")
    out = capsys.readouterr().out
    for path in peer:
        assert not path.exists(), f"--team-wide left a peer file behind: {path}"
    for path in mine:
        assert not path.exists(), f"--all left the caller's own scratch file behind: {path}"
    for path in shared:
        assert not path.exists(), f"--team-wide left a temp file in shared state: {path}"
    removal_line = out.index("removed")
    for location in ("Agents/Developer-1", "Agents/Developer-2", "Global", "Roles"):
        assert location in out, f"{location} was never announced: {out}"
        assert out.index(location) < removal_line, (
            f"{location} was announced after the first unlink: {out}"
        )
    assert code == 0


def test_an_unresolved_caller_is_refused_and_removes_nothing(cli, project: Path) -> None:
    """From the main checkout no lane owns the tree: stop instead of guessing."""
    _, peer, mine, shared = seed(cli, project)
    code = clean(cli, project, "--all")
    for path in [*peer, *mine, *shared]:
        assert path.exists(), f"a refused clean still unlinked {path}"
    assert code == 2


def test_an_unknown_agent_is_refused_before_anything_is_removed(cli, project: Path) -> None:
    """Exit-code case: an unknown lane name must not fall back to a wider scope."""
    _, peer, mine, shared = seed(cli, project)
    code = clean(cli, project, "--agent", "nobody-9", "--all")
    for path in [*peer, *mine, *shared]:
        assert path.exists(), f"a refused clean still unlinked {path}"
    assert code == 2


def test_team_wide_and_agent_are_mutually_exclusive(cli, project: Path) -> None:
    """Exit-code case: the two scopes are opposites, so the pair is refused."""
    _, peer, mine, shared = seed(cli, project)
    code = clean(cli, project, "--team-wide", "--agent", "developer-2", "--all")
    for path in [*peer, *mine, *shared]:
        assert path.exists(), f"a refused clean still unlinked {path}"
    assert code == 2
