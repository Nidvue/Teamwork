"""The clarifying-question gate: an ambiguity becomes a decision, not a guess.

A prompt is a request, not a specification, and the expensive failure is a team
that guesses at an ambiguity and discovers it after the work is built. This store
is the opposite of a guess: a question names what is unclear, offers 2-5 concrete
options, says which one the team recommends, and - when it ``blocks`` - holds
``loop`` at CONTINUE until a person answers it.

These tests pin the three properties that make it a gate rather than a note:
options are mandatory (a one-answer question invites the model to answer itself),
a blocking question stops the loop, and answering it releases the loop.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine, layout, questions


def test_a_question_needs_at_least_two_options(cli, project: Path) -> None:
    """A one-option question is a request for permission, not a decision."""
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    code = cli(
        "--project",
        project,
        "ask",
        "add",
        "--question",
        "Which database?",
        "--option",
        "sqlite",
        "--by",
        "CEO",
    )
    assert code == 2


def test_a_question_with_options_is_recorded_with_its_recommendation(cli, project: Path) -> None:
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "ask",
            "add",
            "--question",
            "Which database?",
            "--option",
            "sqlite, single file",
            "--option",
            "postgres, a server",
            "--recommend",
            "1",
            "--blocks",
            "intake",
            "--by",
            "CEO",
        )
        == 0
    )
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    items = questions.parse_questions(layout.questions_path(root))
    assert len(items) == 1
    item = items[0]
    assert item["options"] == ["sqlite, single file", "postgres, a server"]
    assert item["recommend"] == "1"
    assert item["blocks"] == "intake"
    assert item["status"] == "open"


def test_a_blocking_question_holds_the_loop_until_answered(cli, project: Path, capsys) -> None:
    """The gate: loop CONTINUE while open, STOP-reason cleared once answered."""
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "ask",
            "add",
            "--question",
            "Ship a CLI or a web UI?",
            "--option",
            "CLI",
            "--option",
            "web UI",
            "--by",
            "CEO",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "ask", "gate") == 1
    assert "blocking question" in capsys.readouterr().out

    assert (
        cli(
            "--project",
            project,
            "ask",
            "answer",
            "Q-0001",
            "--choice",
            "1",
            "--by",
            "CEO",
            "--note",
            "CLI first",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "ask", "gate") == 0
    assert "no blocking question" in capsys.readouterr().out


def test_loop_reports_the_blocking_question_as_a_reason(cli, project: Path, capsys) -> None:
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "ask",
            "add",
            "--question",
            "Which licence?",
            "--option",
            "MIT",
            "--option",
            "AGPL",
            "--by",
            "CEO",
        )
        == 0
    )
    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out
    assert "blocking question Q-0001 is unanswered" in out


def test_a_choice_outside_the_option_range_is_refused(cli, project: Path) -> None:
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "ask",
            "add",
            "--question",
            "Which?",
            "--option",
            "a",
            "--option",
            "b",
            "--by",
            "CEO",
        )
        == 0
    )
    assert cli("--project", project, "ask", "answer", "Q-0001", "--choice", "7", "--by", "CEO") == 2
    assert cli("--project", project, "ask", "answer", "Q-0001", "--choice", "x", "--by", "CEO") == 2


def test_an_answered_question_cannot_be_answered_twice(cli, project: Path) -> None:
    assert (
        cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git", "--no-star")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "ask",
            "add",
            "--question",
            "Which?",
            "--option",
            "a",
            "--option",
            "b",
            "--by",
            "CEO",
        )
        == 0
    )
    assert cli("--project", project, "ask", "answer", "Q-0001", "--choice", "1", "--by", "CEO") == 0
    assert cli("--project", project, "ask", "answer", "Q-0001", "--choice", "2", "--by", "CEO") == 2


def test_the_question_store_round_trips_through_the_parser() -> None:
    """Render then parse keeps the text, the options and the recommendation."""
    items = [questions.new_question("Which?", ["a", "b", "c"], "plan", 2, "CEO")]
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "Questions.md"
        questions.write_questions(path, items)
        back = questions.parse_questions(path)
    assert len(back) == 1
    assert back[0]["options"] == ["a", "b", "c"]
    assert back[0]["recommend"] == "2"
    assert back[0]["blocks"] == "plan"
