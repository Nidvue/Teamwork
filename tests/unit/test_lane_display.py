"""The lane display must be loaded, not merely shipped (T-0065).

Why: the renderer that draws the live wave ships inside the bundle, and a
skill-only install therefore *carries* it while the host never loads it - a host
reads extensions from its own ``extensions/`` directory and its ``settings.json``,
never from a skills directory. The gap is silent: 60 lane runs on record, no
widget, and ``refresh --check`` reporting the bundle as in sync.

Pinned here: the install copies the shipped file and registers it once, the
settings file keeps every other key, a second run changes nothing, a broken
settings file is left untouched rather than rewritten, and a destination outside
the host's ``<agent>/skills/<name>`` shape is reported as having no display
instead of writing into a stranger's directory.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import lanedisplay

RENDERER = Path("templates") / "pi-package" / "extensions" / "teamwork-lanes.ts"


def skill(tmp_path: Path) -> Path:
    """A bundle that carries the renderer and nothing else."""
    root = tmp_path / "bundle"
    target = root / RENDERER
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export default function () {}\n", encoding="utf-8")
    return root


def host(tmp_path: Path) -> Path:
    """The host shape the agent directory is derived from."""
    return tmp_path / "agent" / "skills" / "teamwork"


def test_the_repository_ships_the_renderer() -> None:
    shipped = Path(__file__).resolve().parents[2] / RENDERER
    text = shipped.read_text(encoding="utf-8")
    assert "lane" in text and "list" in text, "the renderer polls the lane records"
    assert "setWidget" in text, "a renderer that draws nothing is not a renderer"


def test_install_copies_the_renderer_and_registers_it_once(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text(
        json.dumps({"theme": "dark", "extensions": ["extensions/other.ts"]}, indent=2) + "\n",
        encoding="utf-8",
    )

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert state.ok and state.live, state.detail
    assert state.target is not None and state.target.is_file()
    assert state.target.read_text(encoding="utf-8") == "export default function () {}\n"
    written = json.loads(settings.read_text(encoding="utf-8"))
    assert written["theme"] == "dark", "an unrelated setting is never dropped"
    assert written["extensions"] == ["extensions/other.ts", "extensions/teamwork-lanes.ts"]

    again = lanedisplay.install(skill(tmp_path), skills=str(dest))
    assert again.live
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == [
        "extensions/other.ts",
        "extensions/teamwork-lanes.ts",
    ], "a second install must not append the entry twice"


def test_a_settings_entry_in_another_spelling_is_already_registered(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text(
        json.dumps({"extensions": ["/abs/path/extensions/teamwork-lanes.ts"]}),
        encoding="utf-8",
    )

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert state.registered
    assert json.loads(settings.read_text(encoding="utf-8"))["extensions"] == [
        "/abs/path/extensions/teamwork-lanes.ts"
    ]


def test_status_reports_missing_before_the_install(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    state = lanedisplay.status(skill(tmp_path), skills=str(dest))

    assert state.ok, state.detail
    assert not state.installed and not state.registered and not state.live


def test_a_broken_settings_file_is_left_untouched(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)
    settings = dest.parent.parent / "settings.json"
    settings.write_text("{ not json", encoding="utf-8")

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert not state.ok
    assert "not valid JSON" in state.detail
    assert settings.read_text(encoding="utf-8") == "{ not json"
    assert state.target is not None and not state.target.exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    state = lanedisplay.install(skill(tmp_path), skills=str(dest), dry_run=True)

    assert state.ok and not state.live
    assert state.target is not None and not state.target.exists()
    assert not (dest.parent.parent / "settings.json").exists()


def test_a_destination_outside_the_host_shape_has_no_display(tmp_path: Path) -> None:
    dest = tmp_path / "installed"
    dest.mkdir()

    state = lanedisplay.install(skill(tmp_path), skills=str(dest))

    assert not state.ok
    assert "no extensions directory" in state.detail
    assert not (tmp_path / "extensions").exists()


def test_the_cli_installs_and_then_reports_a_live_display(tmp_path: Path, cli) -> None:
    dest = host(tmp_path)
    dest.mkdir(parents=True)

    assert cli("ui", "status", "--dest", dest) == 1, "not installed yet"
    assert cli("ui", "install", "--dest", dest) == 0
    assert cli("ui", "status", "--dest", dest) == 0


def test_a_built_host_package_declares_its_own_extension(tmp_path: Path) -> None:
    """A package that ships ``extensions/`` beside ``skills/`` needs no install."""
    package = tmp_path / "package"
    skill_dir = package / "skills" / "teamwork"
    skill_dir.mkdir(parents=True)
    (package / "extensions").mkdir()
    (package / "extensions" / "teamwork-lanes.ts").write_text("x\n", encoding="utf-8")

    state = lanedisplay.status(skill_dir, skills=str(skill_dir))

    assert not state.ok
    assert "declares that file itself" in state.detail
