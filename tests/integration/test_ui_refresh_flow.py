"""Integration: the install script puts the lane renderer where the host looks.

`teamwork.py refresh` and `scripts/sync_skill.py` are the two shipped install
paths, and both used to mirror the bundle and stop - which left the renderer
inside a skills directory no host reads as an extension directory. This layer
drives the script as a subprocess against a throwaway agent directory, so the
assertion is about files an operator can see rather than about a helper.

Owner: ceo. Layer: integration. Area: ui. Task: T-0031.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.gitenv import child_env

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC = REPO_ROOT / "scripts" / "sync_skill.py"
SHIM = REPO_ROOT / "scripts" / "teamwork.py"
RENDERER = "teamwork-status.ts"


def agent(tmp_path: Path) -> Path:
    return tmp_path / "agent"


def dest(root: Path) -> Path:
    return root / "skills" / "teamwork"


def run(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    env = child_env()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, *argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_script_installs_the_renderer_and_registers_it(tmp_path: Path) -> None:
    root = agent(tmp_path)

    result = run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "extensions" / RENDERER).is_file()
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings["extensions"] == [f"extensions/{RENDERER}"]
    assert "lane display" in result.stdout


def test_a_second_run_changes_nothing_and_says_so(tmp_path: Path) -> None:
    root = agent(tmp_path)
    assert run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path).returncode == 0
    before = (root / "settings.json").read_text(encoding="utf-8")

    second = run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path)

    assert second.returncode == 0, second.stderr
    assert (root / "settings.json").read_text(encoding="utf-8") == before


def test_check_reports_a_display_the_host_would_not_load(tmp_path: Path) -> None:
    root = agent(tmp_path)
    assert run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path).returncode == 0
    (root / "extensions" / RENDERER).unlink()

    checked = run(str(SYNC), "--check", "--dest", str(dest(root)), cwd=tmp_path)

    assert checked.returncode == 1
    assert "lane display" in checked.stderr


def test_the_ui_command_reports_what_the_script_installed(tmp_path: Path) -> None:
    root = agent(tmp_path)
    assert run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path).returncode == 0

    status = run(str(SHIM), "ui", "status", "--dest", str(dest(root)), cwd=tmp_path)

    assert status.returncode == 0, status.stdout + status.stderr
    assert "installed" in status.stdout
    assert "registered" in status.stdout


def test_a_host_with_no_settings_file_is_created_not_refused(tmp_path: Path) -> None:
    root = agent(tmp_path)
    assert not (root / "settings.json").exists()

    assert run(str(SYNC), "--dest", str(dest(root)), cwd=tmp_path).returncode == 0

    assert os.access(root / "settings.json", os.R_OK)
    assert json.loads((root / "settings.json").read_text(encoding="utf-8"))["extensions"]
