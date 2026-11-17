"""The one exit code an unknown record id returns, across the four record commands.

docs/guide/cli-records.md: an id the CLI cannot see exits `2` for `criteria verify`,
`criteria reopen`, `knowledge show`, `attention take`, `tests run` and `tests rm`.
Exit `2` is argparse's "bad input", so a script branches on one code.
"""

from __future__ import annotations


def test_unknown_test_id_exits_2(cli, project) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    assert (
        cli(
            "--project",
            project,
            "tests",
            "run",
            "TS-9999",
            "--by",
            "Developer-1",
            "--result",
            "pass",
            "--evidence",
            "x",
        )
        == 2
    )
    assert cli("--project", project, "tests", "rm", "TS-9999", "--by", "Developer-1") == 2


def test_the_four_record_commands_agree_on_an_unknown_id(cli, project) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    assert cli("--project", project, "criteria", "verify", "AC-9999", "--by", "Developer-1") == 2
    assert cli("--project", project, "knowledge", "show", "K-9999") == 2
    assert cli("--project", project, "attention", "take", "A-9999", "--by", "Developer-1") == 2
