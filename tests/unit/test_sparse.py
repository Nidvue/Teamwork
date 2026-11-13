"""The sparse read gate: bounded, source-anchored, never worse than a full read.

Adopted from SparseRead (https://github.com/Liuzedooong/SparseReading, MIT,
accessed 2026-11-13). What the tests pin is the shape the team relies on: a small
file is returned whole, a large file with a query returns only matching ranges
with `path:line` provenance inside a byte budget, and the reader can always fall
back to the native read. A read that silently dropped evidence would be worse
than no gate at all, so the budget, the provenance and the fallback are asserted.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine, sparse


def big(tmp_path: Path, needle: str = "read gate", hits: int = 40) -> Path:
    body = ["# a large document", ""]
    for index in range(1, 600):
        if index % 10 == 0 and hits > 0:
            body.append(f"line {index}: the {needle} decides what enters context")
            hits -= 1
        else:
            body.append(f"line {index}: filler text that the query should not match")
    path = tmp_path / "big.md"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def test_a_small_file_is_returned_whole(tmp_path: Path) -> None:
    path = tmp_path / "small.md"
    path.write_text("# small\none line\n", encoding="utf-8")
    pack = sparse.read_pack(tmp_path, "small.md", sparse.Hint(query=("small",)))
    assert pack.mode == "native", pack.reason
    assert "one line" in pack.body
    assert pack.saved_bytes == 0, "a native read must not claim a saving"


def test_a_large_file_with_a_query_returns_matching_ranges_with_provenance(tmp_path: Path) -> None:
    big(tmp_path)
    pack = sparse.read_pack(tmp_path, "big.md", sparse.Hint(query=("read gate",)))
    assert pack.mode == "focus", pack.reason
    assert pack.snippets, "a query that matches must return snippets"
    for snippet in pack.snippets:
        assert f"{snippet.start}-{snippet.end}" in pack.body, "every snippet carries its range"
    assert pack.returned_bytes < pack.total_bytes
    assert pack.saved_percent > 50.0
    assert "line 501: filler" not in pack.body, "a distant non-matching line must not leak"
    assert pack.body.count("\n") < 200, "the pack is a slice, not the file"


def test_the_budget_is_respected_and_the_overflow_is_named(tmp_path: Path) -> None:
    big(tmp_path)
    pack = sparse.read_pack(tmp_path, "big.md", sparse.Hint(query=("read gate",), budget=600))
    assert pack.returned_bytes <= 900, "the budget bounds the pack (one snippet may overshoot)"
    assert pack.omitted > 0, "a bounded read must say how many matches it left out"
    assert "more match(es)" in pack.reason, pack.reason


def test_the_hinted_remedy_returns_the_omitted_match(tmp_path: Path) -> None:
    """The remedy the pack prints must work: raising --budget returns the rest.

    The review of the first version found `--scope expand` advertised and inert -
    a lane that follows the tool's own instruction and gets a byte-identical pack
    falls back to grep, which is the cost the gate exists to remove.
    """
    big(tmp_path)
    small = sparse.read_pack(tmp_path, "big.md", sparse.Hint(query=("read gate",), budget=600))
    assert small.omitted > 0
    assert "raise --budget" in small.reason, small.reason
    omitted_line = "line 400: the read gate decides what enters context"
    assert omitted_line not in small.body, "the bounded pack leaves this match out"
    raised = sparse.read_pack(
        tmp_path, "big.md", sparse.Hint(query=("read gate",), budget=1_000_000)
    )
    assert omitted_line in raised.body, "raising --budget returns the omitted match"
    assert raised.omitted == 0, "the budget is the only cap, so a large one drops nothing"


def test_full_returns_everything_and_saves_nothing(tmp_path: Path) -> None:
    big(tmp_path)
    pack = sparse.read_pack(tmp_path, "big.md", sparse.Hint(query=("read gate",), full=True))
    assert pack.mode == "full"
    assert pack.returned_bytes == pack.total_bytes
    assert "filler text" in pack.body


def test_lines_returns_exactly_that_range(tmp_path: Path) -> None:
    big(tmp_path)
    pack = sparse.read_pack(tmp_path, "big.md", sparse.Hint(lines="3-5"))
    assert pack.mode == "verify"
    assert pack.snippets == [sparse.Snippet(3, 5, 0)]
    body = [line for line in pack.body.splitlines() if line]
    assert len(body) == 3
    assert body[0].startswith("3: ")


def test_no_query_on_a_large_file_is_a_scout_not_a_dump(tmp_path: Path) -> None:
    big(tmp_path)
    pack = sparse.read_pack(tmp_path, "big.md", sparse.Hint())
    assert pack.mode == "scout", pack.reason
    assert "add --query" in pack.body
    assert pack.returned_bytes < pack.total_bytes


def test_a_binary_file_takes_the_native_path(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\x00\x01\x02binary")
    pack = sparse.read_pack(tmp_path, "blob.bin", sparse.Hint(query=("binary",)))
    assert pack.mode == "native"
    assert "binary or unsupported" in pack.reason


def test_a_missing_file_is_refused(tmp_path: Path) -> None:
    try:
        sparse.read_pack(tmp_path, "nope.md", sparse.Hint())
    except FileNotFoundError as exc:
        assert "nope.md" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("a missing file must be refused, not silently empty")


def test_the_cli_records_the_read_with_its_saving(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    big(project)
    capsys.readouterr()
    assert cli("--project", project, "read", "big.md", "--query", "read gate", "--by", "CEO") == 0
    out = capsys.readouterr().out
    assert "saved" in out
    records = [r for r in engine.ledger_read(root) if r.get("action") == "read.sparse"]
    assert records, "every sparse read is a ledger record"
    assert "mode=focus" in records[-1]["detail"]
    assert "saved=" in records[-1]["detail"]


def test_the_cli_json_reports_the_pack(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    big(project)
    capsys.readouterr()
    assert cli("--project", project, "read", "big.md", "--query", "read gate", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "focus"
    assert payload["saved_bytes"] > 0
    assert payload["snippets"] and "start" in payload["snippets"][0]
