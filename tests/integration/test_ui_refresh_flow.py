"""Integration: `ui status` reports the host adapter the `ui install` gate wrote.

The package install path is npm; the host-adapter gate is a separate command.
This layer drives the shipped CLI as a subprocess against a throwaway agent
directory, so the assertion is about files an operator can see. Every host in
the matrix gets an explicit TEAMWORK_AGENT_HOST in the child environment only.

Owner: ceo. Layer: integration. Area: ui. Task: T-0024.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from tests.gitenv import child_env

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "scripts" / "teamwork.py"
RENDERER = "tw-status.ts"
BUS = "teamwork-bus.ts"
PLUGIN_FILES = ("index.ts", "tui.tsx", "package.json")
UNSUPPORTED = ("claude", "unknown", "codex")


def bundle(tmp_path: Path) -> Path:
    """A bundle that carries the opencode plugin for the child to install."""
    root = tmp_path / "bundle"
    folder = root / "plugins" / "tw-status"
    folder.mkdir(parents=True)
    for name in PLUGIN_FILES:
        (folder / name).write_text("export default 1;\n", encoding="utf-8")
    return root


def run(
    *argv: str,
    cwd: Path,
    host: str = "pi",
    skill_dir: Path | None = None,
    markers: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = child_env(TEAMWORK_AGENT_HOST=host, **(markers or {}))
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if skill_dir is not None:
        env["TEAMWORK_SKILL_DIR"] = str(skill_dir)
    return subprocess.run(
        [sys.executable, *argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_ui_command_reports_what_it_installed(tmp_path: Path) -> None:
    root = tmp_path / "agent"
    dest = root / "skills" / "tw"

    installed = run(str(SHIM), "ui", "install", "--dest", str(dest), cwd=tmp_path)

    assert installed.returncode == 0, installed.stdout + installed.stderr
    status = run(str(SHIM), "ui", "status", "--dest", str(dest), cwd=tmp_path)

    assert status.returncode == 0, status.stdout + status.stderr
    assert "installed" in status.stdout
    assert "registered" in status.stdout
    assert (root / "extensions" / RENDERER).is_file()
    assert (root / "extensions" / BUS).is_file()


@pytest.mark.parametrize("host", UNSUPPORTED)
def test_install_on_unsupported_hosts_writes_nothing(tmp_path: Path, host: str) -> None:
    root = tmp_path / "agent"
    dest = root / "skills" / "tw"
    dest.mkdir(parents=True)

    refused = run(str(SHIM), "ui", "install", "--dest", str(dest), cwd=tmp_path, host=host)

    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "pi and opencode" in refused.stderr
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()

    status = run(str(SHIM), "ui", "status", "--dest", str(dest), cwd=tmp_path, host=host)

    assert status.returncode == 1, status.stdout + status.stderr
    assert "missing" in status.stdout
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()


def test_opencode_install_writes_only_the_plugin_discovery_dir(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    config = tmp_path / "home" / ".config" / "opencode"
    dest = config / "plugins" / "tw-status"

    installed = run(
        str(SHIM),
        "ui",
        "install",
        "--dest",
        str(dest),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
    )

    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert "opencode.jsonc" in installed.stdout, installed.stdout
    assert all((dest / name).is_file() for name in PLUGIN_FILES)
    assert not (config / "extensions").exists()
    assert not (config / "settings.json").exists()
    assert not (config / "opencode.json").exists()
    assert not (config / "cli.json").exists()

    status = run(
        str(SHIM),
        "ui",
        "status",
        "--dest",
        str(dest),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
    )

    assert status.returncode == 0, status.stdout + status.stderr
    assert "lane display installed" in status.stdout


def test_opencode_status_is_read_only_before_install(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    dest = tmp_path / "home" / ".config" / "opencode" / "plugins" / "tw-status"

    status = run(
        str(SHIM),
        "ui",
        "status",
        "--dest",
        str(dest),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
    )

    assert status.returncode == 1, status.stdout + status.stderr
    assert "missing" in status.stdout
    assert not dest.exists()


def test_agent_host_override_wins_over_existing_markers(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    dest = tmp_path / "home" / ".config" / "opencode" / "plugins" / "tw-status"

    installed = run(
        str(SHIM),
        "ui",
        "install",
        "--dest",
        str(dest),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
        markers={"PI_SESSION_ID": "a-session", "OPENCODE_MODEL": "a-model"},
    )

    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert all((dest / name).is_file() for name in PLUGIN_FILES)
    assert not (tmp_path / "agent" / "extensions").exists()
