"""Acceptance: a citation that predates a compaction of its own session dies.

Layer ``acceptance``, area ``evidence-staleness``, owner Reviewer (T-0001,
D-20261120-CEO-5). Driven only through the shipped CLI as a subprocess.

One contrast, twice the same command: the record is at the revision under
review, it is passing, and revision binding and the author-role rule both accept
it as a credit. The only difference is the session that cites it. Cited by the
lane that ran it before its context was compacted, the credit is taken; cited by
that same lane after two compactions - the model no longer holds the output it
saw, only the summary of a run - the verdict is refused and told to re-run. That
is the whole adopted mechanism: compaction invalidates the claim, it does not
soften it.

Owner: reviewer. Related: references/Evidence.md
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cli_harness import assert_ok, build_env, cli

ROSTER = "ceo,developer-1,tester-1,reviewer-1"


def git(project: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *map(str, args)],
        cwd=str(project),
        capture_output=True,
        text=True,
        env=build_env(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_AUTHOR_NAME": "Reviewer",
                "GIT_AUTHOR_EMAIL": "reviewer@agents.nidvue.com",
                "GIT_COMMITTER_NAME": "Reviewer",
                "GIT_COMMITTER_EMAIL": "reviewer@agents.nidvue.com",
            }
        ),
        check=False,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr}"
    return proc.stdout.strip()


def session_file(tmp_path: Path, compactions: int) -> str:
    path = tmp_path / f"session-{compactions}.jsonl"
    lines = [json.dumps({"type": "user", "id": "a1", "message": "run the gate"})]
    lines += [
        json.dumps(
            {
                "type": "compaction",
                "id": f"c{n}",
                "summary": "## Goal",
                "firstKeptEntryId": "a1",
                "tokensBefore": 100000 + n,
            }
        )
        for n in range(compactions)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def lane_env(tmp_path: Path, compactions: int) -> dict:
    return build_env(
        {"PI_SESSION_ID": "lane-9", "PI_SESSION_FILE": session_file(tmp_path, compactions)}
    )


def test_the_same_credit_is_accepted_before_and_refused_after_a_compaction(
    tmp_path: Path,
) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    git(project, "init", "-q", "-b", "main")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    (project / ".gitignore").write_text(".pi/\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-qm", "base")
    git(project, "checkout", "-q", "-b", "work")
    (project / "README.md").write_text("base\nfixed\n", encoding="utf-8")
    git(project, "add", "README.md")
    git(project, "commit", "-qm", "fix: the thing")
    head = git(project, "rev-parse", "HEAD")

    fresh = lane_env(tmp_path, 0)
    assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"], env=fresh))
    scaffold = git(project, "status", "--porcelain")
    assert scaffold, "teamwork init must scaffold an uncommitted AGENTS.md/docs tree"
    git(project, "add", "-A")
    git(project, "commit", "-qm", "teamwork scaffold")
    head = git(project, "rev-parse", "HEAD")
    assert_ok(
        cli(
            project,
            [
                "task",
                "add",
                "developer",
                "Fix the README boundary",
                "--claimed-by",
                "Developer-1",
                "--priority",
                "P1",
            ],
            env=fresh,
        )
    )
    assert_ok(
        cli(
            project,
            [
                "task",
                "set",
                "developer",
                "T-0001",
                "--branch",
                "work",
                "--area",
                "engine",
                "--by",
                "Developer-1",
                "--force",
                "acceptance fixture: the branch is created with plain git, not branch start",
            ],
            env=fresh,
        )
    )
    assert_ok(
        cli(
            project,
            [
                "selfcheck",
                "developer",
                "T-0001",
                "--by",
                "Developer-1",
                "--result",
                "pass",
                "--note",
                "scope: the README boundary; second call changes nothing; concurrency: "
                "one branch, one lane",
                "--test",
                f"git show {head[:7]} -> README carries the fix",
                "--force",
                "acceptance fixture: the branch shape is written by hand, not by branch start",
            ],
            env=fresh,
        )
    )
    assert_ok(cli(project, ["pr", "open", "--agent", "Developer-1", "--task", "T-0001"], env=fresh))
    assert_ok(
        cli(
            project,
            [
                "tests",
                "add",
                "--layer",
                "acceptance",
                "--area",
                "engine",
                "--owner",
                "Reviewer-1",
                "--command",
                "pytest -q tests/acceptance",
            ],
            env=fresh,
        )
    )
    assert_ok(
        cli(
            project,
            [
                "tests",
                "run",
                "TS-0001",
                "--by",
                "Reviewer-1",
                "--result",
                "pass",
                "--rev",
                head,
                "--evidence",
                f"pytest -q tests/acceptance @{head[:7]} -> 12 passed",
                "--baseline",
                "no acceptance record for area engine",
            ],
            env=fresh,
        )
    )

    compacted = lane_env(tmp_path, 2)
    refused = cli(
        project,
        [
            "review",
            "developer",
            "T-0001",
            "--by",
            "Reviewer-1",
            "--result",
            "pass",
            "--credit",
            "TS-0001",
            "--evidence",
            "python3 -m pytest -q tests/acceptance in this session -> 12 passed",
        ],
        env=compacted,
    )
    assert refused.returncode != 0, refused
    assert "compact" in refused.output, refused.output
    assert "TS-0001" in refused.output

    accepted = cli(
        project,
        [
            "review",
            "developer",
            "T-0001",
            "--by",
            "Reviewer-1",
            "--result",
            "pass",
            "--credit",
            "TS-0001",
            "--evidence",
            "pytest -q tests/acceptance in this context -> 12 passed",
        ],
        env=fresh,
    )
    assert "compact" not in accepted.output, accepted.output


def test_the_record_names_the_context_that_produced_it(tmp_path: Path) -> None:
    project = tmp_path / "proj2"
    project.mkdir()
    assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    assert_ok(
        cli(
            project,
            [
                "tests",
                "add",
                "--layer",
                "unit",
                "--area",
                "engine",
                "--command",
                "pytest -q tests/unit",
            ],
        )
    )
    assert_ok(
        cli(
            project,
            [
                "tests",
                "run",
                "TS-0001",
                "--by",
                "Developer-1",
                "--result",
                "pass",
                "--evidence",
                "pytest -q tests/unit -> 9 passed",
                "--baseline",
                "no unit record for area engine",
            ],
            env=lane_env(tmp_path, 1),
        )
    )
    listed = assert_ok(cli(project, ["tests", "list"]))
    tests_md = project / ".pi" / "Teamwork" / "Teams" / "Acceptance" / "Tests.md"
    assert "epoch: lane-9@1" in tests_md.read_text(encoding="utf-8"), (
        f"no context epoch on the record:\n{listed.output}\n{tests_md.read_text(encoding='utf-8')}"
    )
