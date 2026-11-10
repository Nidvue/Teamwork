"""Acceptance: the lessons -> ``tw-`` skill loop, black-box on a throwaway team.

One scenario, driven only through the installed CLI as a subprocess (never by
importing the engine), covering the user-visible contract of
``docs/Team/Architecture.md`` 14.1-14.3: record two lessons for two roles, load
them, close one through a ``tw-`` mistake skill created with ``--from-lesson``,
list both surfaces, and prove an unprefixed name is refused at the documented
line. Offline, and the whole file stays well under the ten-second budget.

Owner: tester. Layer: acceptance. Area: lessons.
"""

from __future__ import annotations

from pathlib import Path

from cli_harness import assert_ok, cli

ROSTER = "ceo,developer-1,tester-1,reviewer-1"

PREFIX_REFUSAL = (
    "skill name 'fix-x' must start with tw-: every team skill is recognisable by "
    "the fixed prefix (e.g. tw-<name>)"
)


def test_the_lessons_to_skill_loop_end_to_end(project: Path) -> None:
    init = assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    assert "workspace ready" in init.output

    developer = assert_ok(
        cli(
            project,
            [
                "lesson",
                "add",
                "--by",
                "Developer-1",
                "--mistake",
                "committed on main",
                "--cause",
                "the branch guard was skipped",
                "--rule",
                "run branch start before the first edit",
                "--evidence",
                "git status @abc -> main",
            ],
        )
    )
    assert "# L-0001 recorded for developer: committed on main" in developer.stdout

    tester = assert_ok(
        cli(
            project,
            [
                "lesson",
                "add",
                "--by",
                "Tester-1",
                "--role",
                "tester",
                "--mistake",
                "certified without CI",
                "--cause",
                "the local run was treated as the whole signal",
                "--rule",
                "wait for the CI run on the pushed SHA",
                "--evidence",
                "gh run list @abc -> no runs",
            ],
        )
    )
    assert "# L-0002 recorded for tester: certified without CI" in tester.stdout

    loaded = assert_ok(cli(project, ["load", "Developer-1"]))
    assert "# Lessons (developer) - open mistakes to avoid:" in loaded.stdout
    assert "- committed on main -> Roles/Developer/Lessons.md#L-0001" in loaded.stdout

    created = assert_ok(
        cli(
            project,
            [
                "skill",
                "create",
                "--name",
                "tw-fix-x",
                "--role",
                "tester",
                "--by",
                "Tester-1",
                "--for",
                "when a lesson names a repeated mistake",
                "--from-lesson",
                "L-0002",
                "--body",
                "1. Read the run for the pushed SHA before claiming a pass.",
            ],
        )
    )
    assert "# S-0001 skill 'tw-fix-x' for the tester role (kind: mistake)" in (created.stdout)
    assert "#   fixes lesson: L-0002" in created.stdout
    assert "#   file: .agents/skills/tw-fix-x/SKILL.md" in created.stdout

    skill = (project / ".agents" / "skills" / "tw-fix-x" / "SKILL.md").read_text(encoding="utf-8")
    assert "kind: mistake" in skill.split("---")[1]
    assert "prevents: L-0002" in skill.split("---")[1]

    lessons = assert_ok(cli(project, ["lesson", "list"]))
    assert (
        "- L-0001 [open] developer: committed on main -> run branch start before the first edit"
        in (lessons.stdout)
    )
    assert (
        "- L-0002 [fixed] tester: certified without CI -> wait for the CI run on the pushed SHA (skill: tw-fix-x)"
        in (lessons.stdout)
    )

    skills = assert_ok(cli(project, ["skill", "list"]))
    assert (
        "- S-0001 tw-fix-x                     [draft] kind=mistake lesson=L-0002 owner=tester           file=ok"
        in (skills.stdout)
    )

    refused = cli(
        project,
        [
            "skill",
            "create",
            "--name",
            "fix-x",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when the prefix is missing",
        ],
    )
    assert refused.returncode == 1, refused
    assert f"teamwork: {PREFIX_REFUSAL}" in refused.stderr
    assert not (project / ".agents" / "skills" / "fix-x").exists()
