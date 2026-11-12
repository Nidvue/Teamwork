"""``teamwork refresh`` moves the installed skill copy to the source it is given.

Layer ``integration``, area ``refresh``, owner Tester (T-0013). A lane runs the
*installed* copy of the skill, so the only thing that makes a merged engine
change reach it is this command writing the bundle into the skills directory.
This layer drives the real CLI against a real checkout: the first refresh adds
the bundle, the second carries an edit and a deletion, ``--check`` reports drift
without writing, and a source that is not a checkout is refused with the
installed copy left alone.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import bundle


def seed_checkout(path: Path) -> Path:
    """A minimal skill checkout: ``.git`` plus the bundle's two required parts."""
    (path / ".git").mkdir(parents=True)
    (path / "src" / "teamwork").mkdir(parents=True)
    (path / "SKILL.md").write_text("# skill v1\n", encoding="utf-8")
    (path / "src" / "teamwork" / "__init__.py").write_text("VERSION = '1'\n", encoding="utf-8")
    return path


def test_refresh_adds_then_updates_then_removes_to_match_the_source(
    cli, project: Path, tmp_path: Path
) -> None:
    source = seed_checkout(tmp_path / "checkout")
    dest = project / "skills"

    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch") == 0
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# skill v1\n"
    assert (dest / "src" / "teamwork" / "__init__.py").is_file()

    (source / "SKILL.md").write_text("# skill v2\n", encoding="utf-8")
    (source / "references").mkdir()
    (source / "references" / "extra.md").write_text("new\n", encoding="utf-8")
    (source / "src" / "teamwork" / "__init__.py").unlink()

    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch") == 0
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# skill v2\n"
    assert (dest / "references" / "extra.md").is_file()
    assert not (dest / "src" / "teamwork" / "__init__.py").exists()


def test_check_reports_drift_without_writing(cli, project: Path, tmp_path: Path) -> None:
    source = seed_checkout(tmp_path / "checkout")
    dest = project / "skills"
    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch") == 0
    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch", "--check") == 0

    (source / "SKILL.md").write_text("# skill v2\n", encoding="utf-8")
    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch", "--check") == 1
    assert (dest / "SKILL.md").read_text(encoding="utf-8") == "# skill v1\n"


def test_a_source_that_is_not_a_checkout_is_refused_and_writes_nothing(
    cli, project: Path, tmp_path: Path, capsys
) -> None:
    plain = tmp_path / "plain"
    (plain / "src" / "teamwork").mkdir(parents=True)
    (plain / "SKILL.md").write_text("# not a checkout\n", encoding="utf-8")
    dest = project / "skills"

    assert cli("refresh", "--source", str(plain), "--dest", dest, "--no-fetch") != 0
    assert "not a git checkout" in capsys.readouterr().err
    assert not (dest / "SKILL.md").exists()
    assert bundle.installed_files(dest) == []


def test_refresh_does_not_touch_the_team_records(cli, project: Path, tmp_path: Path) -> None:
    from support import team_root

    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = team_root(project)
    ledger_before = (root / "Ledger.jsonl").read_bytes()

    source = seed_checkout(tmp_path / "checkout")
    dest = project / "skills"
    assert cli("refresh", "--source", str(source), "--dest", dest, "--no-fetch") == 0
    assert (root / "Ledger.jsonl").read_bytes() == ledger_before, (
        "mirroring the bundle wrote into the team's append-only ledger"
    )
