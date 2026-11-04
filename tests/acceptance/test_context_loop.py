"""Acceptance: the ``ctx://`` loop end to end through the shipped entrypoint.

One scenario, driven only through ``python -m teamwork`` as a subprocess (the
acceptance harness never imports the engine), covering the user-visible contract
of ``docs/Team/Architecture.md`` section 16: initialise a team, record a fact, an
experience and a lesson, find a node by a phrase an operator would type, read it
at L0/L1/L2, digest a task (a neutral one and an unknown one), and read the
stats. Every command succeeds offline - the child environment points every proxy
at a closed port, so an accidental network call fails instead of hanging - and
the whole file stays under the ten-second budget.

The two ``digest`` templates need a task a review already failed or a merge
already closed; only those gates may write that state, so the template half is
proven in ``tests/integration/test_context_cli.py`` and cited from the test
record. This file proves the shipped command's exit-code contract.

Owner: tester. Layer: acceptance. Area: context.
"""

from __future__ import annotations

import time
from pathlib import Path

from cli_harness import assert_ok, build_env, cli

ROSTER = "ceo,developer-1,tester-1,reviewer-1"

OFFLINE_ENV = build_env(
    {
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "",
    }
)

URI = "ctx://project/knowledge/K-0001"


def test_the_context_tree_loop_end_to_end(project: Path) -> None:
    started = time.monotonic()

    init = assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"], env=OFFLINE_ENV))
    assert "workspace ready" in init.output

    fact = assert_ok(
        cli(
            project,
            [
                "knowledge",
                "add",
                "--by",
                "Developer-1",
                "--topic",
                "Context tree",
                "--statement",
                "The tree is a read-only view over the stores.",
                "--evidence",
                "pytest @abc -> 1 passed",
                "--kind",
                "fact",
                "--tags",
                "context,tree",
            ],
            env=OFFLINE_ENV,
        )
    )
    assert "# K-0001 recorded: Context tree" in fact.stdout

    experience = assert_ok(
        cli(
            project,
            [
                "knowledge",
                "add",
                "--by",
                "Developer-1",
                "--kind",
                "experience",
                "--topic",
                "Ranking",
                "--statement",
                "Importance then uses ranks the load rows.",
                "--evidence",
                "pytest @abc -> 1 passed",
            ],
            env=OFFLINE_ENV,
        )
    )
    assert "# K-0002 recorded: Ranking" in experience.stdout

    lesson = assert_ok(
        cli(
            project,
            [
                "lesson",
                "add",
                "--by",
                "Developer-1",
                "--mistake",
                "shipped without reading the tree",
                "--cause",
                "the navigation surface was never exercised",
                "--rule",
                "read the node before changing it",
                "--evidence",
                "pytest @abc -> failed",
            ],
            env=OFFLINE_ENV,
        )
    )
    assert "# L-0001 recorded for developer: shipped without reading the tree" in lesson.stdout

    task = assert_ok(
        cli(
            project,
            ["task", "add", "developer", "Acceptance digest", "--priority", "P1"],
            env=OFFLINE_ENV,
        )
    )
    assert "T-0001" in task.output

    found = assert_ok(cli(project, ["context", "find", "read-only view"], env=OFFLINE_ENV))
    first = found.stdout.splitlines()[0]
    assert first.split(" ", 3)[1].isdigit(), first
    assert first.split(" ", 3)[2] == URI, first
    assert "[knowledge] [fact] Context tree:" in first

    level0 = assert_ok(cli(project, ["context", "read", URI, "--level", "0"], env=OFFLINE_ENV))
    assert (
        level0.stdout.strip()
        == "[fact] Context tree: The tree is a read-only view over the stores."
    )

    level1 = assert_ok(cli(project, ["context", "read", URI], env=OFFLINE_ENV))
    assert level1.stdout.splitlines()[0] == (
        "- statement: The tree is a read-only view over the stores."
    )

    level2 = assert_ok(cli(project, ["context", "read", URI, "--level", "2"], env=OFFLINE_ENV))
    assert level2.stdout.startswith("## K-0001 - Context tree")
    assert "- kind: fact" in level2.stdout

    neutral = assert_ok(cli(project, ["context", "digest", "T-0001"], env=OFFLINE_ENV))
    assert neutral.stdout.strip() == "# T-0001: nothing to digest"

    unknown_task = cli(project, ["context", "digest", "T-9999"], env=OFFLINE_ENV)
    assert unknown_task.returncode == 2, unknown_task
    assert "no task 'T-9999' in any role queue" in unknown_task.stderr

    unknown_uri = cli(project, ["context", "read", "ctx://project/nope"], env=OFFLINE_ENV)
    assert unknown_uri.returncode == 2, unknown_uri
    assert "unknown context URI 'ctx://project/nope'" in unknown_uri.stderr

    stats = assert_ok(cli(project, ["context", "stats"], env=OFFLINE_ENV))
    assert stats.stdout.splitlines()[:3] == [
        "- memory: 0 entries (roles 0, global 0)",
        "- lessons: 1 (1 open, 0 fixed)",
        "- knowledge: 2 active, 0 superseded",
    ]

    elapsed = time.monotonic() - started
    assert elapsed < 10.0, f"the context loop took {elapsed:.1f}s; the budget is 10s"
