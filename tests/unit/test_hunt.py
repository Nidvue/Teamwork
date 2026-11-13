"""Unit: the bounded discovery loop - dry rounds, the seen set, the page on a stall.

Layer ``unit``, area ``graph``. A discovery loop's value is the set of findings, so
the only honest stop condition is "two rounds in a row added nothing this loop had
not already seen". Three properties make that true and each is asserted here:

* a finding is its own dedup key, whitespace normalised;
* the seen set includes what the loop rejected, so a dead end is never paid for
  twice;
* a loop that spends its round limit still finding things has *not* converged - it
  opens an attention item and exits 1 instead of reporting success.

The round command is a script the test writes, invoked through the same interpreter
that runs the suite, so the loop is proved on any host without a shell.

Owner: architect. Layer: unit. Area: graph.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from teamwork import engine
from teamwork.hunt import fresh_keys, is_rejected, key_of, state_path


def round_script(project: Path, body: str) -> str:
    """A round command that prints whatever ``body`` prints, through this interpreter."""
    script = project / "round.py"
    script.write_text(body, encoding="utf-8")
    return shlex.join([sys.executable, str(script)])


def test_a_finding_is_its_own_key_with_whitespace_collapsed() -> None:
    assert key_of("  test_a   flaky \n") == "test_a flaky"
    assert key_of("") == ""


def test_a_seen_finding_is_never_fresh_again() -> None:
    seen: set = set()
    assert fresh_keys(["a", "b"], seen, []) == ["a", "b"]
    assert fresh_keys(["a", "c"], seen, []) == ["c"]
    assert seen == {"a", "b", "c"}


def test_a_rejected_finding_stays_seen_and_never_returns() -> None:
    seen: set = set()
    assert is_rejected("test_a flaky", ["test_a"]) is True
    assert fresh_keys(["test_a flaky", "test_b flaky"], seen, ["test_a"]) == ["test_b flaky"]


def test_the_loop_converges_after_two_dry_rounds(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    command = round_script(project, "print('one')\nprint('two')\n")
    capsys.readouterr()
    code = cli("--project", project, "hunt", "a hunt", "--run", command, "--by", "ceo")
    out = capsys.readouterr().out
    assert code == 0
    assert "## round 1: 2 fresh" in out
    assert "## round 2: 0 fresh" in out
    assert "STOP - converged after 3 round(s): 2 dry round(s) in a row" in out


def test_a_second_run_continues_instead_of_rediscovering(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    command = round_script(project, "print('one')\n")
    assert cli("--project", project, "hunt", "a hunt", "--run", command, "--by", "ceo") == 0
    capsys.readouterr()
    assert cli("--project", project, "hunt", "a hunt", "--run", command, "--by", "ceo") == 0
    out = capsys.readouterr().out
    assert "1 seen before this run" in out
    assert "## round 1: 0 fresh" in out


def test_a_stalled_loop_pages_a_person_and_exits_one(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    command = round_script(project, "import time\nprint(time.time_ns())\n")
    capsys.readouterr()
    code = cli(
        "--project", project, "hunt", "endless", "--run", command, "--rounds", "2", "--by", "ceo"
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "STALLED" in out
    root = engine.project_root(_args(project))
    items = (root / "Attention.md").read_text(encoding="utf-8")
    assert "discovery loop 'endless' stalled" in items


def test_the_state_file_keeps_the_dead_ends(cli, project: Path, capsys) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    command = round_script(project, "print('a flaky')\nprint('b flaky')\n")
    assert (
        cli(
            "--project",
            project,
            "hunt",
            "a hunt",
            "--run",
            command,
            "--reject",
            "a flaky",
            "--by",
            "ceo",
        )
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "hunt", "a hunt") == 0
    out = capsys.readouterr().out
    assert "1 rejected" in out
    assert "- a flaky" in out
    root = engine.project_root(_args(project))
    assert state_path(root, "a hunt").is_file()


def _args(project: Path):
    import argparse

    return argparse.Namespace(project=str(project), team="")
