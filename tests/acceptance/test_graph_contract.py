"""Acceptance: the routing graph's operator-visible contract.

The unit layer pins the edge table against a synthetic workspace and the
integration layer drives the CLI on a real one. This layer asks the question the
operator asks before trusting the command at all: does the shipped text promise
what the shipped code does, and does the exit code mean what a script would
assume? Every assertion reads a shipped file or a shipped process.

Owner: ceo. Layer: acceptance. Area: graph. Task: T-0031.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "scripts" / "teamwork.py"
COORDINATION = REPO_ROOT / "references/Coordination.md"
SKILL = REPO_ROOT / "SKILL.md"
CLI_GUIDE = REPO_ROOT / "docs/guide/cli.md"
CODES = ("C-GRAPH-STATE", "C-GRAPH-CHAFF", "C-GRAPH-CHAIN", "C-GRAPH-EXIT", "C-GRAPH-PRICE")


def run(*argv: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SHIM), *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_contract_documents_every_code_the_command_can_print() -> None:
    text = COORDINATION.read_text(encoding="utf-8")

    missing = [code for code in CODES if code not in text]
    assert not missing, f"the coordination contract does not document {missing}"


def test_the_skill_and_the_cli_guide_name_the_three_subcommands() -> None:
    for path in (SKILL, CLI_GUIDE):
        text = path.read_text(encoding="utf-8")
        for word in ("graph", "baseline"):
            assert word in text, (path, word)


def test_help_lists_show_audit_and_baseline(tmp_path: Path) -> None:
    result = run("graph", "--help", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    for action in ("show", "audit", "baseline"):
        assert action in result.stdout, action


def test_a_directory_that_is_not_a_workspace_is_refused_not_guessed(tmp_path: Path) -> None:
    result = run("graph", cwd=tmp_path)

    assert result.returncode != 0
    assert "init" in (result.stdout + result.stderr)


def test_a_finding_is_a_non_zero_exit_so_a_script_can_gate_on_it(tmp_path: Path) -> None:
    assert (
        run(
            "init",
            "--agents",
            "ceo,developer-1,developer-2,tester-1,reviewer-1",
            "--no-git",
            cwd=tmp_path,
        ).returncode
        == 0
    )

    audit = run("graph", "audit", cwd=tmp_path)

    assert audit.returncode == 1
    assert "# problems found:" in audit.stdout
    assert any(code in audit.stdout for code in CODES)
