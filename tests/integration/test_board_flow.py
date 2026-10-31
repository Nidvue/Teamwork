"""Integration tests: `teamwork.py board --check` / `--write` on a real CLI run.

The committed board is a projection of the shared role queues, and the product
must be able to prove it without a developer's gitignored team tree: `--check`
exits 1 naming a stale cell, `--write` renders the tables and exits 0, and a
second render equals what was written. `--check` never writes (Tester audit
TA-01/TA-07).
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import board as boardlib
from teamwork import engine

AGENTS = ("ceo", "developer-1", "tester-1", "reviewer-1")
STALE_ROW = "| developer | T-0001 | - | doing | - | - |"
FRESH_ROW = "| developer | T-0001 | - | todo | - | - |"


def team_root(project: Path) -> Path:
    """The hidden tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def write_board(project: Path, row: str) -> Path:
    """A committed board carrying both tables under their headings, one row."""
    path = project / "docs" / "Team" / "Board.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# BOARD",
                "",
                "| role | id | area | state | pr | merged revision |",
                "|---|---|---|---|---|---|",
                row,
                "",
                "Rows whose PR is not merged carry no merged revision.",
                "",
                "## In flight",
                "",
                "| agent | task | prio | state | artifact |",
                "|---|---|---|---|---|",
                "| developer | T-0001 Build the API | P0 | doing | - |",
                "",
                "The task queue (`teamwork.py task list <role>`) is authoritative.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def one_open_task(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS), "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer-1",
            "Build the API",
            "--priority",
            "P0",
            "--no-review",
        )
        == 0
    )
    return team_root(project)


def test_check_exits_one_on_a_stale_cell_and_check_does_not_write(
    cli, project: Path, capsys
) -> None:
    one_open_task(cli, project)
    path = write_board(project, STALE_ROW)
    before = path.read_bytes()
    capsys.readouterr()

    assert cli("--project", project, "board", "--check") == 1
    out = capsys.readouterr().out
    assert "developer T-0001" in out, out
    assert "board says ('doing', '-', '-'), queue says ('todo', '-', '-')" in out, out
    assert path.read_bytes() == before, "--check rewrote the board"

    # The same tree in JSON: a machine-readable diff and the same exit code.
    assert cli("--project", project, "board", "--check", "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["board"] == str(path)
    assert any("developer T-0001" in line for line in payload["problems"]), payload
    assert path.read_bytes() == before, "--check --json rewrote the board"


def test_write_renders_the_tables_and_a_second_render_is_equal(cli, project: Path, capsys) -> None:
    root = one_open_task(cli, project)
    path = write_board(project, STALE_ROW)
    capsys.readouterr()

    assert cli("--project", project, "board", "--write") == 0
    written = path.read_text(encoding="utf-8")
    assert FRESH_ROW in written, written
    assert STALE_ROW not in written, written
    assert "| developer | T-0001 Build the API | P0 | todo | - |" in written, written

    # A second render is a no-op, and the product agrees the board is current.
    assert boardlib.render(boardlib.queues(root), written) == written
    assert boardlib.problems(boardlib.queues(root), written) == []
    assert cli("--project", project, "board", "--check") == 0

    # --write is idempotent: the second run reports unchanged, not a new rendering.
    capsys.readouterr()
    assert cli("--project", project, "board", "--write", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["written"] is False, payload
    assert path.read_text(encoding="utf-8") == written


def test_the_board_commands_refuse_a_board_without_the_tables(cli, project: Path) -> None:
    """A prose board is named (exit 2), never crashed and never rewritten.

    `init` now writes the conforming skeleton (T-0007), so the prose board is built
    here explicitly: the gate must still refuse an older or hand-written one, and a
    refused `--write` must leave it untouched.
    """
    one_open_task(cli, project)
    path = project / "docs" / "Team" / "Board.md"
    prose = "# BOARD\n\nOwner: Project Manager.\n"
    path.write_text(prose, encoding="utf-8")

    assert cli("--project", project, "board", "--check") == 2
    assert cli("--project", project, "board", "--write") == 2
    assert path.read_text(encoding="utf-8") == prose, "a refused board was rewritten"


def test_write_reports_every_row_it_drops(cli, project: Path, capsys) -> None:
    """A row that leaves the table must be named, in both the human and JSON paths.

    The projection silently dropping a row is the stale-board defect this PR
    exists to prevent, so the drop report is a contract, not a log line. In
    --json the list travels in the payload so stdout stays parseable.
    """
    one_open_task(cli, project)
    gone = "| release-engineer | T-0099 | - | done | - | - |"
    capsys.readouterr()
    write_board(project, STALE_ROW + "\n" + gone)
    assert cli("--project", project, "board", "--write", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert "releaseengineer T-0099" in payload["dropped"], payload
    assert payload["queues"] == 1, payload

    write_board(project, STALE_ROW + "\n" + gone)
    assert cli("--project", project, "board", "--write") == 0
    out = capsys.readouterr().out
    assert "note: releaseengineer T-0099 left the table" in out, out


def test_json_is_only_meaningful_with_a_mode(cli, project: Path) -> None:
    one_open_task(cli, project)
    assert cli("--project", project, "board", "--json") == 2
