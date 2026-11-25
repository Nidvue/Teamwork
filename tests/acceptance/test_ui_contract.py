"""Acceptance: the lane display's operator-visible contract.

The operator's whole signal about the live wave is the exit code of
`teamwork ui status` and the line it prints, so this layer pins exactly that:
the command is non-zero when the detected host would draw nothing, the dry run
writes nothing, the default action is the report, install is refused on hosts
outside {pi, opencode}, and opencode gets a config instruction instead of an
edited opencode.json/cli.json.

Owner: ceo. Layer: acceptance. Area: ui. Task: T-0024.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "scripts" / "teamwork.py"
PLUGIN_FILES = ("index.ts", "tui.tsx", "package.json")
UNSUPPORTED = ("claude", "unknown", "codex")


def run(
    *argv: str, cwd: Path, host: str = "pi", skill_dir: Path | None = None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "TEAMWORK_AGENT_HOST": host}
    if skill_dir is not None:
        env["TEAMWORK_SKILL_DIR"] = str(skill_dir)
    return subprocess.run(
        [sys.executable, str(SHIM), *argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def agent(tmp_path: Path) -> Path:
    return tmp_path / "agent"


def dest(root: Path) -> Path:
    return root / "skills" / "tw"


def bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    folder = root / "plugins" / "tw-status"
    folder.mkdir(parents=True)
    for name in PLUGIN_FILES:
        (folder / name).write_text("export default 1;\n", encoding="utf-8")
    ext = root / "extensions"
    ext.mkdir()
    for name in ("tw-status.ts", "teamwork-bus.ts"):
        (ext / name).write_text("export default function () {}\n", encoding="utf-8")
    return root


def opencode_dest(tmp_path: Path) -> Path:
    return tmp_path / "home" / ".config" / "opencode" / "plugins" / "tw-status"


def test_status_is_non_zero_before_anything_is_installed(tmp_path: Path) -> None:
    result = run("ui", "status", "--dest", str(dest(agent(tmp_path))), cwd=tmp_path)

    assert result.returncode == 1
    assert "lane display missing" in result.stdout


def test_the_dry_run_writes_nothing(tmp_path: Path) -> None:
    root = agent(tmp_path)

    result = run("ui", "install", "--dry-run", "--dest", str(dest(root)), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()


def test_the_default_action_is_the_report(tmp_path: Path) -> None:
    root = agent(tmp_path)
    assert run("ui", "status", "--dest", str(dest(root)), cwd=tmp_path).returncode == 1

    implicit = run("ui", "--dest", str(dest(root)), cwd=tmp_path)

    assert implicit.returncode == 1
    assert "missing" in implicit.stdout or "not registered" in implicit.stdout


@pytest.mark.parametrize("host", UNSUPPORTED)
def test_install_on_unsupported_hosts_is_refused_and_writes_nothing(
    tmp_path: Path, host: str
) -> None:
    root = agent(tmp_path)

    result = run("ui", "install", "--dest", str(dest(root)), cwd=tmp_path, host=host)

    assert result.returncode == 1
    assert "pi and opencode" in result.stderr
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()


@pytest.mark.parametrize("host", ("pi", "opencode", *UNSUPPORTED))
def test_status_stays_read_only_on_every_host(tmp_path: Path, host: str) -> None:
    source = bundle(tmp_path)
    target = opencode_dest(tmp_path) if host == "opencode" else dest(agent(tmp_path))

    result = run("ui", "status", "--dest", str(target), cwd=tmp_path, host=host, skill_dir=source)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "missing" in result.stdout
    assert not target.exists()
    assert not (tmp_path / "home" / ".config" / "opencode" / "opencode.json").exists()
    assert not (tmp_path / "home" / ".config" / "opencode" / "cli.json").exists()


def test_opencode_install_reports_the_config_step_without_editing_config(tmp_path: Path) -> None:
    source = bundle(tmp_path)
    target = opencode_dest(tmp_path)

    installed = run(
        "ui",
        "install",
        "--dest",
        str(target),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
    )

    assert installed.returncode == 0, installed.stderr
    assert "opencode.jsonc" in installed.stdout
    assert "cli.json" in installed.stdout
    assert all((target / name).is_file() for name in PLUGIN_FILES)
    config = target.parent.parent
    assert not (config / "opencode.json").exists()
    assert not (config / "cli.json").exists()
    assert not (config / "extensions").exists()

    status = run(
        "ui",
        "status",
        "--dest",
        str(target),
        cwd=tmp_path,
        host="opencode",
        skill_dir=source,
    )

    assert status.returncode == 0
    assert "lane display installed" in status.stdout


def test_the_agent_host_override_selects_pi_despite_an_opencode_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENCODE_MODEL", "a-model")
    root = agent(tmp_path)

    result = run("ui", "install", "--dest", str(dest(root)), cwd=tmp_path, host="pi")

    assert result.returncode == 0, result.stderr
    assert (root / "extensions" / "tw-status.ts").is_file()
    assert not (tmp_path / "home").exists()
