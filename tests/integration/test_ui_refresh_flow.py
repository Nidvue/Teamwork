"""Integration: `ui status` reports the host extension the `ui install` gate wrote.

The package install path is npm; the host-extension gate is a separate command.
This layer drives the shipped CLI as a subprocess against a throwaway agent
directory, so the assertion is about files an operator can see.

Owner: ceo. Layer: integration. Area: ui. Task: T-0031.
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


def run(*argv: str, cwd: Path, host: str = "pi") -> subprocess.CompletedProcess:
    env = child_env(TEAMWORK_AGENT_HOST=host)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
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


@pytest.mark.parametrize("host", ["opencode", "claude", "unknown"])
def test_install_outside_pi_writes_nothing(tmp_path: Path, host: str) -> None:
    root = tmp_path / "agent"
    dest = root / "skills" / "tw"
    dest.mkdir(parents=True)

    refused = run(str(SHIM), "ui", "install", "--dest", str(dest), cwd=tmp_path, host=host)

    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "pi" in refused.stderr
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()

    status = run(str(SHIM), "ui", "status", "--dest", str(dest), cwd=tmp_path, host=host)

    assert status.returncode == 1, status.stdout + status.stderr
    assert "missing" in status.stdout
    assert not (root / "extensions").exists()
    assert not (root / "settings.json").exists()
