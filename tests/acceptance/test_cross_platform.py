"""Cross-platform hygiene: spaces, non-ASCII paths, LF-only output, selftest.

Windows and macOS must be able to run the same commands. These tests use a
project directory that contains both a space and non-ASCII characters (the
combination that breaks naive shell and path handling), then check that every
generated file is written with LF newlines only, and that ``selftest`` exits 0.
"""

from __future__ import annotations

from cli_harness import DEFAULT_ROSTER, assert_ok, cli

TEAM = "Ünï Team"  # non-ASCII team name
PROJECT_NAME = "Pröject with Spacé"  # non-ASCII + space in the path


def _make_project(tmp_path):
    project = tmp_path / PROJECT_NAME
    project.mkdir()
    return project


def test_project_path_with_space_and_non_ascii(tmp_path):
    """init and a task round-trip succeed on a spaced, non-ASCII path."""
    project = _make_project(tmp_path)

    init = assert_ok(cli(project, ["init", "--agents", DEFAULT_ROSTER, "--no-git"], team=TEAM))
    assert str(project) in init.stdout

    assert_ok(
        cli(
            project,
            [
                "criteria",
                "add",
                "--id",
                "AC-1",
                "--text",
                "unicode path works",
                "--owner",
                "developer",
                "--by",
                "ceo",
            ],
            team=TEAM,
        )
    )
    assert_ok(
        cli(
            project,
            ["task", "add", "developer-1", "path with spécial charß", "--priority", "P0"],
            team=TEAM,
        )
    )

    teams = list((project / ".pi" / "Teamwork" / "Teams").glob("*"))
    assert len(teams) == 1, [str(p) for p in teams]
    assert teams[0].is_dir()

    listed = assert_ok(cli(project, ["task", "list", "developer"], team=TEAM))
    assert "path with spécial charß" in listed.output


def test_generated_files_have_no_cr_bytes(tmp_path):
    """Every generated file is written with LF only, never CRLF."""
    project = _make_project(tmp_path)
    assert_ok(cli(project, ["init", "--agents", DEFAULT_ROSTER, "--no-git"], team=TEAM))
    assert_ok(
        cli(
            project,
            [
                "criteria",
                "add",
                "--id",
                "AC-1",
                "--text",
                "no CR",
                "--owner",
                "developer",
                "--by",
                "ceo",
            ],
            team=TEAM,
        )
    )
    assert_ok(cli(project, ["task", "add", "developer-1", "no CR bytes"], team=TEAM))

    offending = []
    for path in sorted(project.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\r" in data:
            offending.append(str(path.relative_to(project)))

    assert offending == [], f"generated files contain CR bytes: {offending}"


def test_selftest_exits_zero(tmp_path):
    """`teamwork selftest` is the offline smoke check used by CI; it exits 0."""
    project = _make_project(tmp_path)
    result = cli(project, ["selftest"], team=TEAM)

    assert result.returncode == 0, result
    assert "checks passed" in result.stdout, result
    assert "FAIL" not in result.stdout, result
    assert "FAIL" not in result.stderr, result
