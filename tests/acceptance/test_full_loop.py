"""AC-10: the full gate loop reaches STOP on a fresh workspace.

Driven end to end through the CLI as a subprocess, in an isolated temp project:

    init --agents ceo,architect,developer-1,tester-1,reviewer-1 --no-git
    criteria add
    tests require + tests add + tests run      (every staffed layer passes)
    criteria verify                            (independent verifier)
    task add -> task set selfcheck -> selfcheck
              -> task set review -> review --result pass
    loop                                       -> STOP, exit code 0

The last test proves the opposite direction too: a freshly initialised workspace
must *not* STOP, so the STOP in the main test is earned and not hardcoded.
"""

from __future__ import annotations

import re

from cli_harness import (
    DEFAULT_LAYERS,
    DEFAULT_ROSTER,
    assert_ok,
    cli,
)

TEAM = "Acceptance"
AREA = "core"

#: layer -> the instance that owns and runs it (one instance per role here).
LAYER_OWNER = {
    "goal": "ceo",
    "system": "architect",
    "unit": "developer-1",
    "integration": "tester-1",
    "acceptance": "reviewer-1",
}


def _id_from(output: str, prefix: str) -> str:
    match = re.search(rf"({prefix}-\d+)", output)
    assert match, f"no {prefix}- id in output:\n{output}"
    return match.group(1)


def _drive_gate_loop(project) -> None:
    """Run every step that clears the STOP gate, asserting each one succeeds."""
    assert_ok(cli(project, ["init", "--agents", DEFAULT_ROSTER, "--no-git"]))

    assert_ok(
        cli(
            project,
            [
                "criteria",
                "add",
                "--id",
                "AC-1",
                "--text",
                "the core deliverable works",
                "--owner",
                "developer",
                "--by",
                "ceo",
            ],
        )
    )

    assert_ok(
        cli(
            project,
            [
                "tests",
                "require",
                "--area",
                AREA,
                "--layers",
                DEFAULT_LAYERS,
                "--by",
                "ceo",
                "--reason",
                "acceptance layer exercises the full gate",
            ],
        )
    )

    test_ids = {}
    for layer, owner in LAYER_OWNER.items():
        added = assert_ok(
            cli(
                project,
                [
                    "tests",
                    "add",
                    "--layer",
                    layer,
                    "--area",
                    AREA,
                    "--owner",
                    owner,
                    "--command",
                    f"echo {layer}-layer-ok",
                ],
            )
        )
        test_ids[layer] = _id_from(added.output, "TS")

    # Each layer is run and evidenced by its own owning role.
    for layer, owner in LAYER_OWNER.items():
        assert_ok(
            cli(
                project,
                [
                    "tests",
                    "run",
                    test_ids[layer],
                    "--by",
                    owner,
                    "--result",
                    "pass",
                    "--evidence",
                    f"echo {layer}-layer-ok @rev1 -> ok",
                ],
            )
        )

    # Independent verification: owner is developer, verifier is the reviewer.
    assert_ok(
        cli(
            project,
            [
                "criteria",
                "verify",
                "AC-1",
                "--by",
                "reviewer-1",
                "--evidence",
                "pytest tests/acceptance @rev1 -> passed",
            ],
        )
    )

    added = assert_ok(
        cli(
            project,
            [
                "task",
                "add",
                "developer-1",
                "Implement the core deliverable",
                "--priority",
                "P0",
                "--body",
                "deliverable for the acceptance flow",
            ],
        )
    )
    task_id = _id_from(added.output, "T")

    assert_ok(
        cli(
            project,
            [
                "task",
                "set",
                "developer",
                task_id,
                "--claimed-by",
                "developer-1",
                "--status",
                "selfcheck",
            ],
        )
    )
    assert_ok(
        cli(
            project,
            [
                "selfcheck",
                "developer",
                task_id,
                "--by",
                "developer-1",
                "--note",
                "re-read the diff, boundary and error paths",
                "--test",
                "pytest tests/acceptance @rev1 -> 5 passed",
            ],
        )
    )
    assert_ok(
        cli(
            project,
            [
                "task",
                "set",
                "developer",
                task_id,
                "--status",
                "review",
            ],
        )
    )
    assert_ok(
        cli(
            project,
            [
                "review",
                "developer",
                task_id,
                "--by",
                "reviewer-1",
                "--result",
                "pass",
                "--evidence",
                "ran pytest tests/acceptance @rev1 -> 5 passed",
            ],
        )
    )


def test_full_gate_loop_reports_stop(tmp_path):
    """AC-10: once selfcheck + review pass, `loop` reports STOP with exit 0."""
    project = tmp_path / "loop-project"
    project.mkdir()

    _drive_gate_loop(project)

    loop = cli(project, ["loop"], env=None)
    assert loop.returncode == 0, (
        "loop did not STOP after the gate was cleared. If a required layer is "
        "genuinely missing, this is a real defect (not a test bug):\n" + loop.output
    )
    assert "> STOP" in loop.stdout, loop.output
    assert "> CONTINUE" not in loop.stdout, loop.output
    # A STOP with blockers must never happen.
    assert "  ! " not in loop.stdout, loop.output


def test_loop_blocks_before_the_gate_is_cleared(tmp_path):
    """A bare workspace must not STOP: the gate is genuine, not a hardcoded STOP."""
    project = tmp_path / "empty-project"
    project.mkdir()
    assert_ok(cli(project, ["init", "--agents", DEFAULT_ROSTER, "--no-git"]))

    loop = cli(project, ["loop"])
    assert loop.returncode != 0, (
        "a freshly initialised workspace must NOT report STOP:\n" + loop.output
    )
    assert "> CONTINUE" in loop.stdout, loop.output
    assert "no acceptance criteria recorded" in loop.output, loop.output
