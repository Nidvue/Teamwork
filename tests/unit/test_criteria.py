"""Unit tests for acceptance-criteria records: new_criterion, parse_criteria."""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def test_new_criterion_normalises_fields() -> None:
    criterion = engine.new_criterion(" ac-1 ", "  does the thing  ", owner=" ceo ")
    assert criterion["id"] == "AC-1"
    assert criterion["text"] == "does the thing"
    assert criterion["owner"] == "ceo"
    assert criterion["status"] == "open"
    assert criterion["evidence"] == ""
    assert criterion["verified_by"] == ""
    assert criterion["rev"] == ""


def test_parse_criteria_missing_file_is_empty(tmp_path: Path) -> None:
    assert engine.parse_criteria(tmp_path / "missing.md") == []


def test_criteria_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "Criteria.md"
    items = [engine.new_criterion("AC-1", "widget works", owner="ceo")]
    engine.write_criteria(path, items)

    out = engine.parse_criteria(path)
    assert len(out) == 1
    assert out[0]["id"] == "AC-1"
    assert out[0]["text"] == "widget works"
    assert out[0]["owner"] == "ceo"
    assert out[0]["status"] == "open"


def test_parse_criteria_reads_metadata(tmp_path: Path) -> None:
    path = tmp_path / "Criteria.md"
    path.write_text(
        "# Criteria\n\n"
        "## AC-7 · login works\n"
        "- status: verified\n"
        "- owner: ceo\n"
        "- verified_by: reviewer-1\n"
        "- verified: 2026-01-01\n"
        "- evidence: pytest @abc -> 4 passed\n"
        "- rev: abc123\n",
        encoding="utf-8",
    )
    out = engine.parse_criteria(path)
    assert out[0]["id"] == "AC-7"
    assert out[0]["status"] == "verified"
    assert out[0]["verified_by"] == "reviewer-1"
    assert out[0]["evidence"] == "pytest @abc -> 4 passed"
    assert out[0]["rev"] == "abc123"


def test_parse_criteria_ignores_preamble(tmp_path: Path) -> None:
    path = tmp_path / "Criteria.md"
    path.write_text(
        "# Criteria\n\n> prose before any criterion\n- status: bogus\n", encoding="utf-8"
    )
    assert engine.parse_criteria(path) == []


def test_render_criteria_is_parseable(tmp_path: Path) -> None:
    path = tmp_path / "Criteria.md"
    items = [
        engine.new_criterion("AC-1", "one", owner="ceo"),
        engine.new_criterion("AC-2", "two", owner="developer"),
    ]
    text = engine.render_criteria(items, path)
    assert "## AC-1 · one" in text
    assert "## AC-2 · two" in text
    assert text.endswith("\n")


def test_find_criterion_by_id_then_text() -> None:
    items = [
        engine.new_criterion("AC-1", "login works", owner="ceo"),
        engine.new_criterion("AC-2", "logout works", owner="ceo"),
    ]
    assert engine.find_criterion(items, "AC-2") == 1
    assert engine.find_criterion(items, "login") == 0
    assert engine.find_criterion(items, "missing") is None


def test_criteria_list_exit_codes_include_the_empty_store(cli, project: Path, capsys) -> None:
    """`criteria list` is 3 on an empty store, 1 while open, 0 when all verified.

    The empty store is a state, not an error: exit 3 keeps "nothing recorded yet"
    apart from exit 0's "everything verified", so a store with no acceptance
    criteria can never read as green. Documented in `docs/guide/cli-records.md`.
    """
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    assert cli("--project", project, "criteria", "list") == 3
    empty = capsys.readouterr().out
    assert "# no criteria yet (" in empty
    assert "criteria add --id" in empty

    assert (
        cli(
            "--project",
            project,
            "criteria",
            "add",
            "--id",
            "AC-1",
            "--text",
            "the store exists",
            "--owner",
            "developer",
            "--by",
            "ceo",
        )
        == 0
    )
    assert cli("--project", project, "criteria", "list") == 1

    assert (
        cli(
            "--project",
            project,
            "criteria",
            "verify",
            "AC-1",
            "--by",
            "ceo",
            "--evidence",
            "python -m pytest -q tests/unit/test_criteria.py @HEAD -> 1 passed",
        )
        == 0
    )
    assert cli("--project", project, "criteria", "list") == 0
