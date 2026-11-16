"""The prompt record: original verbatim, research rounds, enhanced prompt.

The intake has three artifacts and they answer different questions. The original
is what the user wrote and is never edited; the rounds are what research found;
the enhanced prompt is the improved request the plan decomposes. The gate is the
point: a fresh project cannot freeze acceptance criteria before an enhanced
prompt exists, because criteria are what "done" means and freezing them on an
unread prompt is how a team builds the wrong thing quickly.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine, layout, prompts


def _init(cli, project: Path) -> None:
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )


def test_criteria_without_a_prompt_warn_and_block_the_loop(cli, project: Path, capsys) -> None:
    """Recording criteria is allowed; finishing without an enhanced prompt is not.

    The gate lives at the completion boundary, not the record boundary: a team may
    iterate on criteria, but `loop` cannot report STOP while the prompt was never
    researched and enhanced.
    """
    _init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the CLI exits 0",
            "--owner",
            "developer",
            "--by",
            "CEO",
        )
        == 0
    )
    assert "no enhanced prompt is recorded yet" in capsys.readouterr().out
    capsys.readouterr()
    cli("--project", project, "loop")
    assert "criteria are recorded but no prompt was researched" in capsys.readouterr().out


def test_recording_the_enhanced_prompt_releases_the_loop_blocker(
    cli, project: Path, capsys
) -> None:
    _init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the CLI exits 0",
            "--owner",
            "developer",
            "--by",
            "CEO",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--original",
            "build a url shortener",
            "--round",
            "ask: CLI, tests and docs map to three deliverables",
            "--enhanced",
            "Build a URL shortener: a CLI with create/resolve, unit tests and docs.",
            "--by",
            "CEO",
        )
        == 0
    )
    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out
    assert "no prompt was researched and enhanced" not in out
    assert "enhanced prompt recorded" in out


def test_the_original_is_kept_verbatim_and_the_enhanced_differs(cli, project: Path) -> None:
    _init(cli, project)
    original = "make it fast and good"
    enhanced = "p95 < 200 ms over 10k rows, proved by `pytest tests/perf -q`"
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--original",
            original,
            "--round",
            "why: 'fast' is unmeasured; the job is a report under 200 ms",
            "--enhanced",
            enhanced,
            "--by",
            "CEO",
        )
        == 0
    )
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    items = prompts.parse_prompt(layout.prompt_path(root))
    assert items[-1]["original"] == original
    assert items[-1]["enhanced"] == enhanced
    assert items[-1]["rounds"] == ["why: 'fast' is unmeasured; the job is a report under 200 ms"]


def test_an_empty_enhanced_prompt_is_refused(cli, project: Path) -> None:
    """A restatement with no improvement is not an enhanced prompt."""
    _init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--original",
            "build a CLI",
            "--round",
            "ask: one deliverable",
            "--by",
            "CEO",
        )
        == 2
    )


def test_no_research_round_is_refused(cli, project: Path) -> None:
    """An unread prompt is the failure the gate exists to stop."""
    _init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--original",
            "build a CLI",
            "--enhanced",
            "Build a CLI that prints the version.",
            "--by",
            "CEO",
        )
        == 2
    )


def test_an_empty_original_is_refused(cli, project: Path) -> None:
    _init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--round",
            "ask: one deliverable",
            "--enhanced",
            "Build a CLI.",
            "--by",
            "CEO",
        )
        == 2
    )


def test_the_prompt_store_round_trips_multiline_text() -> None:
    """Fenced blocks survive a render/parse cycle, including blank lines."""
    original = "line one\n\nline three with ``` inside"
    enhanced = "enhanced line one\n\nenhanced line three"
    items = [prompts.new_prompt(original, enhanced, ["round one", "round two"], "CEO")]
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "Prompt.md"
        prompts.write_prompt(path, items)
        back = prompts.parse_prompt(path)
    assert len(back) == 1
    assert back[0]["original"] == original
    assert back[0]["enhanced"] == enhanced
    assert back[0]["rounds"] == ["round one", "round two"]


def test_the_gate_command_reports_state(cli, project: Path, capsys) -> None:
    _init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "prompt", "gate") == 1
    assert "no enhanced prompt yet" in capsys.readouterr().out
    assert (
        cli(
            "--project",
            project,
            "prompt",
            "record",
            "--original",
            "x",
            "--round",
            "ask: x is one deliverable",
            "--enhanced",
            "Deliverable X: a CLI that prints x.",
            "--by",
            "CEO",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "prompt", "gate") == 0
    assert "an enhanced prompt is recorded" in capsys.readouterr().out
