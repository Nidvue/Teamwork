"""Decision ids are project-wide identifiers, so they must be unique team-wide.

T-0038: `cmd_decision` allocated the next id by scanning only the checked-out
branch's `Decisions.md`, so two lanes working on two branches both picked
D-20261019-CEO-14 and the later archive cited a number that existed twice.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def _decide(cli, project: Path, text: str) -> int:
    return cli(
        "--project",
        project,
        "decision",
        "add",
        "--by",
        "ceo",
        "--kind",
        "technical",
        "--decision",
        text,
        "--evidence",
        "pytest @rev -> ok",
    )


def _ids(project: Path, rev: str = "") -> list:
    text = engine.run_git(project, "show", f"{rev}:docs/Team/Decisions.md").stdout
    return engine._decision_ids_in(text)


def test_a_decision_recorded_on_another_branch_takes_a_fresh_id(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    engine.ensure_repo(project, commit=False, quiet=True)
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "Decisions.md").write_text("# DECISIONS\n", encoding="utf-8")
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "seed")
    base = engine.run_git(project, "rev-parse", "HEAD").stdout.strip()

    assert _decide(cli, project, "first on main") == 0
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "first")
    main_ids = _ids(project)

    engine.run_git(project, "checkout", "-q", "-b", "other", base)
    assert _decide(cli, project, "recorded on another branch") == 0
    engine.run_git(project, "add", "-A")
    engine.run_git(project, "commit", "-qm", "second")
    other_ids = _ids(project, "other")

    assert main_ids and other_ids
    assert not set(main_ids) & set(other_ids), (main_ids, other_ids)


def test_the_id_helper_only_reads_heading_lines(cli, project: Path) -> None:
    """A quoted id in prose must not consume a number."""
    text = "# DECISIONS\n\n## D-20261019-CEO-1 - one\n\n- context: see D-20261019-CEO-9\n"
    assert engine._decision_ids_in(text) == ["D-20261019-CEO-1"]
