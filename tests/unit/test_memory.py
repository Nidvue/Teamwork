"""Unit tests for memory entry records: new_entry, parse_memory, render."""

from __future__ import annotations

from pathlib import Path

from teamwork import engine


def test_new_entry_defaults() -> None:
    entry = engine.new_entry("  remember this  ")
    assert entry["body"] == "remember this"
    assert entry["importance"] == 2
    assert entry["uses"] == 0
    assert entry["pinned"] is False
    assert entry["id"] == ""


def test_new_entry_clamps_importance() -> None:
    assert engine.new_entry("x", importance=99)["importance"] == 5
    assert engine.new_entry("x", importance=-3)["importance"] == 0


def test_new_entry_carries_provenance() -> None:
    entry = engine.new_entry("x", key=" k ", tags=" a,b ", by=" dev ", src=" run ", rev=" abc ")
    assert entry["key"] == "k"
    assert entry["tags"] == "a,b"
    assert entry["by"] == "dev"
    assert entry["src"] == "run"
    assert entry["rev"] == "abc"


def test_parse_memory_missing_file_is_empty(tmp_path: Path) -> None:
    assert engine.parse_memory(tmp_path / "missing.md") == []


def test_memory_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "ShortTermMemory.md"
    entry = engine.new_entry(
        "a useful fact",
        key="fact",
        importance=3,
        tags="core",
        pinned=True,
        by="developer-1",
        src="T-0002",
        rev="deadbeef",
    )
    engine.write_memory(path, [entry], engine.F_SHORT, "developer")

    out = engine.parse_memory(path)
    assert len(out) == 1
    assert out[0]["id"] == "M-0001"
    assert out[0]["key"] == "fact"
    assert out[0]["body"] == "a useful fact"
    assert out[0]["importance"] == 3
    assert out[0]["tags"] == "core"
    assert out[0]["pinned"] is True
    assert out[0]["by"] == "developer-1"
    assert out[0]["rev"] == "deadbeef"


def test_parse_memory_reads_pinned_variants(tmp_path: Path) -> None:
    path = tmp_path / "m.md"
    path.write_text(
        "# Memory\n\n## M-0001 · one\n- pinned: yes\n\nbody one\n\n"
        "## M-0002 · two\n- pinned: no\n\nbody two\n",
        encoding="utf-8",
    )
    entries = engine.parse_memory(path)
    assert entries[0]["pinned"] is True
    assert entries[1]["pinned"] is False


def test_parse_memory_reads_importance_and_uses(tmp_path: Path) -> None:
    path = tmp_path / "m.md"
    path.write_text(
        "# Memory\n\n## M-0001 · one\n- importance: 4\n- uses: 7\n\nbody\n",
        encoding="utf-8",
    )
    entry = engine.parse_memory(path)[0]
    assert entry["importance"] == 4
    assert entry["uses"] == 7


def test_parse_memory_ignores_header_only_file(tmp_path: Path) -> None:
    path = tmp_path / "m.md"
    path.write_text("# Memory - developer\n\n> nothing here\n", encoding="utf-8")
    assert engine.parse_memory(path) == []
