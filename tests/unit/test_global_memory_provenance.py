"""The global memory writer must record provenance like every other writer.

`audit` reports a memory entry without `by` as a blocker, but `teamwork.py
global` had no way to set one, so a global entry could never satisfy the rule
it was audited against. This pins the fix, at the process boundary and in the
merge that carries the provenance forward.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from teamwork import config, engine
from teamwork.records import merge_entries, new_entry, write_memory


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_the_global_command_accepts_provenance_flags(root):
    text = (root / "src" / "teamwork" / "engine.py").read_text(encoding="utf-8")
    block = text[text.index('sub.add_parser(\n        "global"') :]
    block = block[: block.index("s.set_defaults(func=cmd_global)")]
    for flag in ("--by", "--src", "--rev"):
        assert f's.add_argument("{flag}"' in block, f"global has no {flag} flag"


def test_the_global_writer_stores_the_author(root):
    text = (root / "src" / "teamwork" / "engine.py").read_text(encoding="utf-8")
    body = text[text.index("def cmd_global(") :]
    body = body[: body.index("def cmd_recall(")]
    assert re.search(r"new_entry\([^)]*by=author", body, re.S), (
        "cmd_global must pass the derived author into the memory entry"
    )
    assert 'author = args.by or "ceo"' in body, (
        "cmd_global must derive one author, defaulting to the CEO the ledger already names"
    )
    assert '"memory.global",\n        author,' in body, (
        "the ledger record for a global memory entry must name its author"
    )
    assert 'by=args.by or ""' not in body, "no write may store an empty author"


def test_a_merge_never_drops_the_author():
    """Re-recording an entry must not erase the provenance it already had.

    A memory file is written once and merged afterwards, so a later writer who
    adds context to an entry that was recorded without an author is the only
    chance to complete the record - and the merge must keep the author it
    already had.
    """
    first = new_entry("first", "k", 2, "", False)
    second = new_entry("second", "k", 2, "", False, by="CEO", src="T-1", rev="abc")
    entries, merged, added = merge_entries([], [first])
    entries, merged, added = merge_entries(entries, [second])
    assert merged == 1 and added == 0
    assert entries[0]["by"] == "CEO"
    assert entries[0]["src"] == "T-1"
    assert entries[0]["rev"] == "abc"


def test_a_merge_never_overwrites_the_author():
    """A later writer must not REPLACE an existing author with themselves.

    The merge completes a missing author; it never overwrites one. An entry
    that already carries provenance keeps all three fields, so the second
    writer cannot take the credit for a record they did not author - and
    cannot graft their own src/rev onto it either.
    """
    first = new_entry("first", "k", 2, "", False, by="CEO", src="T-1", rev="abc")
    entries, _, _ = merge_entries([], [first])

    second = new_entry("second", "k", 2, "", False, by="Reviewer-1", src="T-9", rev="fff")
    entries, merged, added = merge_entries(entries, [second])
    assert merged == 1 and added == 0
    assert entries[0]["by"] == "CEO"
    assert entries[0]["src"] == "T-1"
    assert entries[0]["rev"] == "abc"


def test_a_merge_completes_a_missing_author_from_one_writer():
    """The three provenance fields travel together.

    A record written without an author can be completed by a later writer, and
    the whole triple moves with it: an entry that names an author but no
    revision is not a half-record the next writer should patch field by field.
    """
    first = new_entry("first", "k", 2, "", False)
    second = new_entry("second", "k", 2, "", False, by="Developer", src="T-0005", rev="0f5f883")
    entries, _, _ = merge_entries([], [first])
    entries, _, _ = merge_entries(entries, [second])
    assert entries[0]["by"] == "Developer"
    assert entries[0]["src"] == "T-0005"
    assert entries[0]["rev"] == "0f5f883"


def test_a_merge_does_not_graft_a_source_onto_another_author():
    """src and rev belong to the author, so they travel with the author.

    A record that names an author but no source is not three independent
    fields to patch one at a time: `src` and `rev` describe the SAME recording
    act as `by`. A later writer who is not the author must not graft their
    own source and revision onto it, or the record ends up crediting the
    first author with a revision the second writer verified.
    """
    first = new_entry("first", "k", 2, "", False, by="CEO")
    second = new_entry("second", "k", 2, "", False, by="Reviewer-1", src="T-9", rev="fff")
    entries, _, _ = merge_entries([], [first])
    entries, _, _ = merge_entries(entries, [second])
    assert entries[0]["by"] == "CEO"
    assert entries[0]["src"] == ""
    assert entries[0]["rev"] == ""


def test_the_same_author_completes_their_own_record():
    """The author re-recording their own entry may fill the gaps they left."""
    first = new_entry("first", "k", 2, "", False, by="Developer")
    second = new_entry("second", "k", 2, "", False, by="Developer", src="T-0005", rev="0f5f883")
    entries, _, _ = merge_entries([], [first])
    entries, _, _ = merge_entries(entries, [second])
    assert entries[0]["by"] == "Developer"
    assert entries[0]["src"] == "T-0005"
    assert entries[0]["rev"] == "0f5f883"


def test_a_writer_without_provenance_never_erases_an_author():
    """An entry written with no --by at all must not blank an existing author."""
    first = new_entry("first", "k", 2, "", False, by="CEO", src="T-1", rev="abc")
    second = new_entry("second", "k", 2, "", False)
    entries, _, _ = merge_entries([], [first])
    entries, _, _ = merge_entries(entries, [second])
    assert entries[0]["by"] == "CEO"
    assert entries[0]["src"] == "T-1"
    assert entries[0]["rev"] == "abc"


def _global_file(project: Path) -> Path:
    return project / ".pi" / "Teamwork" / "Teams" / project.name / "Global" / "GlobalMemory.md"


def test_the_global_command_writes_the_author_into_the_file(cli, project: Path):
    """`teamwork global --by X` must land `by: X` in the memory file."""
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Developer",
            "--src",
            "T-0005",
            "--rev",
            "0f5f883",
        )
        == 0
    )
    text = _global_file(project).read_text(encoding="utf-8")
    assert "- by: Developer" in text
    assert "- src: T-0005" in text
    assert "- rev: 0f5f883" in text


def _seed_a_legacy_unprovenanced_entry(project: Path) -> None:
    """Write an entry with no author the way the pre-fix writer left it.

    A store can still hold records written before the writer filled the author
    in, so the completion and audit paths are proved against such a record
    rather than against a writer that no longer produces one.
    """
    entries, _, _ = merge_entries([], [new_entry("a shared fact", "fact", 3, "", False)])
    write_memory(_global_file(project), entries, engine.F_GLOBAL, "all agents")


def test_a_later_writer_completes_a_provenance_free_entry(cli, project: Path):
    """The merge completes a missing author at the file level, and keeps it."""
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    _seed_a_legacy_unprovenanced_entry(project)
    text = _global_file(project).read_text(encoding="utf-8")
    assert "- by: \n" in text, "the legacy entry has no author"

    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Reviewer-1",
            "--src",
            "T-0005",
            "--rev",
            "0f5f883",
        )
        == 0
    )
    text = _global_file(project).read_text(encoding="utf-8")
    assert "- by: Reviewer-1" in text
    assert "- src: T-0005" in text
    assert "- rev: 0f5f883" in text


def test_a_later_writer_cannot_take_over_the_author(cli, project: Path):
    """A second writer must not replace the author that is already recorded."""
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    for argv in (
        ["global", "a shared fact", "--key", "fact", "--by", "CEO", "--src", "T-1", "--rev", "abc"],
        [
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Impostor",
            "--src",
            "T-9",
            "--rev",
            "f",
        ],
    ):
        assert cli("--project", project, *argv) == 0
    text = _global_file(project).read_text(encoding="utf-8")
    assert "- by: CEO" in text
    assert "Impostor" not in text
    assert "- src: T-1" in text
    assert "- rev: abc" in text


def test_a_later_writer_cannot_graft_its_own_source_onto_another_author(cli, project: Path):
    """The file level of the same rule: a second writer leaves the record alone.

    The first writer named an author but no source; the second writer must not
    patch their own src/rev into that record, or the file credits the first
    author with a revision the second writer verified.
    """
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "CEO",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Reviewer-1",
            "--src",
            "T-9",
            "--rev",
            "fff",
        )
        == 0
    )
    text = _global_file(project).read_text(encoding="utf-8")
    assert "- by: CEO" in text
    assert "- src: \n" in text
    assert "- rev: \n" in text
    assert "T-9" not in text
    assert "fff" not in text


def test_the_audit_gate_is_satisfiable_by_a_global_entry(cli, project: Path, capsys):
    """The gate the writer is audited against must be reachable by the writer.

    `audit` reports a memory entry without `by` as a blocker. A global entry
    recorded with `--by` must therefore not trip it - the writer can now
    satisfy the rule it is audited against.
    """
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Developer",
            "--src",
            "T-0005",
            "--rev",
            "0f5f883",
        )
        == 0
    )
    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out
    assert "memory entr(y/ies) without `by` provenance" not in out
    assert "lack provenance" not in out

    _seed_a_legacy_unprovenanced_entry(project)
    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out
    assert "memory entr(y/ies) without `by` provenance" in out
    assert "lack provenance" in out


def test_the_ledger_record_names_the_author(cli, project: Path):
    """The ledger record for a global entry names who wrote it."""
    assert cli("--project", project, "init", "--agents", "ceo,reviewer-1", "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "global",
            "a shared fact",
            "--key",
            "fact",
            "--by",
            "Developer",
            "--rev",
            "0f5f883",
        )
        == 0
    )
    root = project / ".pi" / "Teamwork" / "Teams" / project.name
    records = engine.ledger_read(root)
    globals_ = [r for r in records if r["action"] == "memory.global"]
    assert globals_, "the global write was not recorded in the ledger"
    assert globals_[-1]["actor"] == "Developer"
    assert globals_[-1]["rev"] == "0f5f883"


def test_global_without_a_by_flag_still_records_the_author(cli, project: Path, capsys) -> None:
    """The sibling of `remember`: `global` must not store an empty author either.

    `audit` blocks on a memory entry whose `by` is empty and scans the global
    store, so a `global` write with no `--by` re-blocked the integrity gate that
    the `remember` fix had just cleared (Reviewer M-0009, CEO M-0010).
    """
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    assert cli("--project", project, "global", "a fact with no author") == 0
    store = (
        project
        / config.TEAM_ROOT_DIR
        / config.TEAMS_SUBDIR
        / engine.team_slug(project)
        / "Global"
        / engine.F_GLOBAL
    )
    assert [entry["by"] for entry in engine.parse_memory(store) if entry["body"]] == ["ceo"]
    capsys.readouterr()
    cli("--project", project, "loop")
    out = capsys.readouterr().out
    assert "memory entr(y/ies) without `by` provenance" not in out
    assert "lack provenance" not in out
