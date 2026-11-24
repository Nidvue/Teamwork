"""Acceptance: the lane display's operator-visible contract.

The operator's whole signal about the live wave is the exit code of
`teamwork ui status` and the line it prints, so this layer pins exactly that:
the command is non-zero when the host would draw nothing, the dry run writes
nothing, the default action is the report, and the guide documents the command
an operator is told to run.

Owner: ceo. Layer: acceptance. Area: ui. Task: T-0031.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "scripts" / "teamwork.py"
GUIDE = REPO_ROOT / "docs" / "guide" / "cli.md"


def run(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SHIM), *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def agent(tmp_path: Path) -> Path:
    return tmp_path / "agent"


def dest(root: Path) -> Path:
    return root / "skills" / "tw"


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


def test_the_guide_documents_the_command() -> None:
    text = GUIDE.read_text(encoding="utf-8")

    assert "teamwork ui" in text
    assert "ui install" in text
    assert "ui status" in text
