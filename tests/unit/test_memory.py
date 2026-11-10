"""Unit tests for memory entry records: new_entry, parse_memory, render."""

from __future__ import annotations

from pathlib import Path

from teamwork import config, engine


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


def test_load_refuses_a_name_the_team_does_not_know(cli, project: Path, capsys) -> None:
    """A typo must not invent a role: `load nope` exits 1 and writes no directory.

    The old guard only fired when `Agents/` was missing, and `init` always creates
    it, so `load nope` wrote `Roles/Nope/` with two memory files and made the typo
    look like a staffed role (T-0003). An unstaffed role is refused the same way,
    and so is a stray directory the old bug left behind: a directory may not keep
    itself alive, while a registered instance and its role name still load.
    """
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    roles = root / "Roles"
    before = sorted(path.name for path in roles.iterdir())

    assert cli("--project", project, "load", "nope") == 1
    refusal = capsys.readouterr().err
    assert "unknown role 'nope': no nope instance is registered" in refusal
    assert "nothing was created" in refusal
    assert "Known roles: ceo, developer" in refusal
    assert cli("--project", project, "load", "Architect") == 1
    capsys.readouterr()
    assert sorted(path.name for path in roles.iterdir()) == before
    assert not (roles / "Nope").exists()
    assert not (roles / "Architect").exists()

    stray = roles / "Nope"
    stray.mkdir()
    (stray / engine.F_SHORT).write_text("# Short-term memory - nope\n", encoding="utf-8")
    assert cli("--project", project, "load", "nope") == 1
    stray_refusal = capsys.readouterr().err
    assert "unknown role 'nope'" in stray_refusal
    listed = stray_refusal.split("Known roles: ", 1)[1].strip()
    assert "nope" not in listed
    assert listed == "ceo, developer"
    assert (stray / engine.F_SHORT).read_text(encoding="utf-8") == "# Short-term memory - nope\n"

    assert cli("--project", project, "load", "Developer-1") == 0
    assert cli("--project", project, "load", "Developer") == 0


def test_remember_refuses_a_name_the_team_does_not_know(cli, project: Path, capsys) -> None:
    """A typo must not invent a role on the write side either (T-0027).

    `_memory_path` carried the same dead guard `cmd_load` did and then created
    `Roles/<Name>/` for any spelling, so `remember QaEnginere note --by
    QaEnginere` exited 0 and left a directory the rest of the tool then reported
    as a role. A name this team cannot resolve is refused before the directory is
    created, and a refusal for a foreign `--by` no longer leaves an empty one.
    """
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    roles = root / "Roles"
    before = sorted(path.name for path in roles.iterdir())

    assert cli("--project", project, "remember", "QaEnginere", "note", "--by", "QaEnginere") == 1
    refusal = capsys.readouterr().err
    assert "unknown role 'QaEnginere'" in refusal
    assert sorted(path.name for path in roles.iterdir()) == before
    assert not (roles / "Qaenginere").exists()

    assert cli("--project", project, "remember", "Nope", "note", "--by", "nope") == 1
    capsys.readouterr()
    assert sorted(path.name for path in roles.iterdir()) == before
    assert not (roles / "Nope").exists()

    assert (
        cli("--project", project, "remember", "Developer", "a real note", "--by", "Developer") == 0
    )
    assert (roles / "Developer" / engine.F_SHORT).is_file()
    assert cli("--project", project, "load", "Developer") == 0
    assert "a real note" in capsys.readouterr().out
