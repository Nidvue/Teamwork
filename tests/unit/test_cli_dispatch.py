"""Unit tests for the frozen CLI dispatch contract (Architecture section 4).

Section 4 freezes three things no later change may break: the invocation forms
are equivalent, the documented exit codes keep their meaning, and no subcommand
is removed or renamed. This module pins them from the command layer's side - the
argv an operator types and the exit code a script reads - so a refactor cannot
quietly renumber a gate.

The installed console script is the packaging lane's claim (`release` layer);
what this repository's own CI runs, and what is pinned here, are the two checkout
forms plus the in-process dispatch.

Owner: developer. Layer: unit. Area: cli-contract.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from teamwork import engine
from teamwork.version import __version__ as VERSION

# ``tests/unit/test_cli_dispatch.py`` -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_SRC = REPO_ROOT / "src"
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"

#: The single line ``--version`` and ``version`` both owe the caller.
VERSION_LINE = f"teamwork {VERSION}"

#: Every top-level command the frozen contract ships. Section 4 allows additions
#: and forbids removals and renames, so this list may only ever grow.
FROZEN_COMMANDS = frozenset(
    {
        "agents",
        "agents-md",
        "archive",
        "audit",
        "board",
        "branch",
        "clean",
        "code-scanning",
        "commit",
        "consolidate",
        "criteria",
        "coordination",
        "decision",
        "dispute",
        "forget",
        "global",
        "hook",
        "hooks",
        "identity",
        "imaging",
        "init",
        "ledger",
        "links",
        "load",
        "loop",
        "map",
        "model",
        "parallel",
        "pr",
        "pulse",
        "recall",
        "redline",
        "refresh",
        "remember",
        "repo",
        "review",
        "selfcheck",
        "selftest",
        "skill",
        "slot",
        "stats",
        "task",
        "tests",
        "touch",
        "trace",
        "version",
    }
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one invocation form the way a script would: this checkout's sources."""
    env = dict(os.environ)
    parts = [str(REPO_SRC)]
    if env.get("PYTHONPATH"):
        parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, text=True)


def _top_level_commands() -> set[str]:
    """The subcommand names the parser actually registers."""
    for action in engine.build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("the parser registers no subcommands at all")


# --------------------------------------------------------------------------- #
# the invocation forms are equivalent
# --------------------------------------------------------------------------- #


def test_the_checkout_shim_prints_the_version_line_and_exits_zero(tmp_path: Path) -> None:
    """Form 3 of section 4: ``python scripts/teamwork.py --version``."""
    done = _run([sys.executable, str(CLI_SHIM), "--version"], tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == VERSION_LINE


def test_the_module_form_prints_the_version_line_and_exits_zero(tmp_path: Path) -> None:
    """Form 2 of section 4: ``python -m teamwork --version``."""
    done = _run([sys.executable, "-m", "teamwork", "--version"], tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == VERSION_LINE


def test_the_two_forms_are_byte_identical(tmp_path: Path) -> None:
    """Equivalence is the contract: a script may pick either form and read the same bytes."""
    shim = _run([sys.executable, str(CLI_SHIM), "--version"], tmp_path)
    module = _run([sys.executable, "-m", "teamwork", "--version"], tmp_path)
    assert (shim.returncode, shim.stdout) == (module.returncode, module.stdout)


def test_the_version_flag_exits_zero_and_prints_one_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--version`` is a clean exit 0, never an error path."""
    with pytest.raises(SystemExit) as exit_info:
        engine.main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == VERSION_LINE


def test_the_version_subcommand_returns_zero_and_prints_the_same_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same constant, same bytes: two surfaces must not drift apart."""
    assert engine.main(["version"]) == 0
    assert capsys.readouterr().out.strip() == VERSION_LINE


# --------------------------------------------------------------------------- #
# the documented exit codes
# --------------------------------------------------------------------------- #


def test_an_unknown_subcommand_is_the_documented_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit code 2, with argparse's message - never a traceback."""
    with pytest.raises(SystemExit) as exit_info:
        engine.main(["nosuchcommand"])
    assert exit_info.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "Traceback" not in captured.err + captured.out


def test_no_subcommand_at_all_is_the_documented_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit code 2: the parser refuses an empty argv instead of guessing a default."""
    with pytest.raises(SystemExit) as exit_info:
        engine.main([])
    assert exit_info.value.code == 2
    assert "required: cmd" in capsys.readouterr().err


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """Exit code 0: asking for help is a success, not an error."""
    with pytest.raises(SystemExit) as exit_info:
        engine.main(["--help"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("usage: teamwork")


def test_nothing_to_do_is_exit_code_three(capsys: pytest.CaptureFixture[str]) -> None:
    """Exit code 3 covers "nothing matched": an empty plan and an unknown trace id.

    The workspace is a throwaway one: a fresh team tree has no declared area, so
    ``tests plan`` has nothing to check, no record mentions the probed id, and no
    role has a claimable task.
    """
    assert engine.main(["init", "--no-git"]) == 0
    capsys.readouterr()
    assert engine.main(["tests", "plan"]) == 3, "an undeclared plan must say 'nothing', not 'green'"
    assert engine.main(["trace", "T-9999"]) == 3
    assert engine.main(["task", "next", "ceo"]) == 3, "an empty queue must not read as 'claimed'"


# --------------------------------------------------------------------------- #
# no removals, no renames
# --------------------------------------------------------------------------- #


def test_every_frozen_command_is_still_registered() -> None:
    """Section 4 allows additions only - a vanished subcommand breaks every script."""
    registered = _top_level_commands()
    missing = sorted(FROZEN_COMMANDS - registered)
    assert not missing, f"section 4 commands that disappeared from the parser: {missing}"


def test_the_version_surface_is_registered_twice() -> None:
    """Both documented spellings exist: ``--version`` on the top parser and ``version``."""
    parser = engine.build_parser()
    flags = [opt for action in parser._actions for opt in action.option_strings]
    assert "--version" in flags
    assert "version" in _top_level_commands()
