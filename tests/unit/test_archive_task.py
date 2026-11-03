"""`archive --task` reads one deliverable instead of the whole evidence ledger.

`docs/Team/Archive.md` is the team's largest document (~622k tokens at the
Throughput.md baseline), so a close-out must never read it whole. The filter keeps
the existing view contract - clipped evidence by default, `--full` unclipped,
`--limit` over the matches - and an unknown id is an empty answer, not an error.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ARCHIVE = """# ARCHIVE - reviewed results

> One entry per passed review.

## T-0001 - first deliverable (architect)
- date: 2026-11-01
- priority: P1
- self-check: [pass] short note | test: pytest -> 1 passed

## T-0002 - second deliverable (developer)
- date: 2026-11-02
- priority: P0
- self-check: [pass] another note | test: pytest -> 2 passed

## T-0001 - the developer's T-0001 (developer)
- date: 2026-11-03
- priority: P1
- self-check: [pass] {long_note} | test: pytest -> 3 passed
"""


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = team_root(project)
    archive = engine.docs_dir(root) / "Archive.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(ARCHIVE.format(long_note="x" * 900), encoding="utf-8")
    return root


def test_task_filter_prints_every_entry_with_that_heading(cli, project: Path, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "archive", "--task", "T-0001") == 0
    out = capsys.readouterr().out

    assert "## T-0001 - first deliverable (architect)" in out
    assert "## T-0001 - the developer's T-0001 (developer)" in out
    assert "T-0002" not in out
    assert out.count("## T-0001") == 2


def test_no_match_is_an_empty_answer_and_exit_zero(cli, project: Path, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "archive", "--task", "T-9999") == 0
    assert capsys.readouterr().out.strip() == "# no archive entry for T-9999"


def test_the_existing_clip_and_limit_still_apply(cli, project: Path, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "archive", "--task", "T-0001", "--limit", "1") == 0
    clipped = capsys.readouterr().out
    assert "the developer's T-0001" in clipped
    assert "first deliverable" not in clipped
    assert "x" * 700 not in clipped

    capsys.readouterr()
    assert cli("--project", project, "archive", "--task", "T-0001", "--limit", "1", "--full") == 0
    whole = capsys.readouterr().out
    assert "x" * 900 in whole


def test_a_missing_archive_is_the_same_empty_answer(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    (engine.docs_dir(root) / "Archive.md").unlink()
    capsys.readouterr()
    assert cli("--project", project, "archive", "--task", "T-0001") == 0
    assert capsys.readouterr().out.strip() == "# no archive entry for T-0001"


def test_repeating_task_filters_selects_both(cli, project: Path, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "archive",
            "--task",
            "T-0001",
            "--task",
            "T-0002",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "first deliverable" in out
    assert "second deliverable" in out
