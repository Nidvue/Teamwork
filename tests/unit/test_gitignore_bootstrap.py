"""Regression tests for `ensure_gitignore`.

The bootstrap used to append a whole section header plus every entry that was
not literally present. A repository whose `.gitignore` already covered an entry
with a glob (`.env.*` covers `.env.local`) therefore gained a dangling header
and redundant lines. These tests pin the corrected behaviour.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def write_gitignore(project: Path, lines: list[str]) -> None:
    (project / ".gitignore").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_empty_repository_gets_the_full_block(tmp_path: Path) -> None:
    added = engine.ensure_gitignore(tmp_path)

    assert added == list(engine.GITIGNORE_LINES)
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == (
        "\n".join(engine.GITIGNORE_LINES) + "\n"
    )


def test_second_run_adds_nothing(tmp_path: Path) -> None:
    engine.ensure_gitignore(tmp_path)

    assert engine.ensure_gitignore(tmp_path) == []


def test_glob_covered_entries_are_not_repeated(tmp_path: Path) -> None:
    write_gitignore(
        tmp_path,
        [
            line
            for line in engine.GITIGNORE_LINES
            if line.strip() not in (".env.local", ".env.*.local")
        ]
        + [".env.*"],
    )

    assert engine.ensure_gitignore(tmp_path) == []


def test_partial_section_keeps_its_header_with_the_missing_entry(tmp_path: Path) -> None:
    header = "# --- teamwork: secrets ---"
    write_gitignore(
        tmp_path,
        [line for line in engine.GITIGNORE_LINES if line != header and line != ".env"],
    )

    added = engine.ensure_gitignore(tmp_path)

    assert added == [header, ".env"]


def test_no_dangling_header_is_appended(tmp_path: Path) -> None:
    write_gitignore(tmp_path, [".pi/"])

    added = engine.ensure_gitignore(tmp_path)

    assert added, "an empty repository should still receive the missing rules"
    for index, line in enumerate(added):
        if line.strip().startswith("#"):
            assert index + 1 < len(added), f"header without an entry: {line}"
            assert not added[index + 1].strip().startswith("#")
