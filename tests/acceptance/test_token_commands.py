"""Acceptance: the M18 token commands as one operator run on a throwaway team.

One scenario, driven only through the installed CLI as a subprocess (never by
importing the engine), proving the user-visible contract of the six tools that
make the token/throughput surface measurable:

* ``throughput`` runs on an empty ledger and reports a zero sample, not a crash;
* ``archive --task`` reads one entry out of a real archive and nothing else;
* ``harness budget`` keeps a long-term entry out of the startup row while
  ``--recallable`` reports it per instance;
* ``instance retire`` moves a lane's evidence and names the retired path in the
  ledger, with the source directory gone and the artifact intact.

Offline, and the whole file stays under the ten-second budget.

Owner: tester. Layer: acceptance. Area: throughput.
"""

from __future__ import annotations

import json
from pathlib import Path

from cli_harness import assert_ok, cli

ROSTER = "ceo,developer-1,reviewer-1"
TEAM = "Acceptance"

ARCHIVE = """# ARCHIVE - reviewed results

> One entry per passed review.

## T-0001 - first deliverable (developer)
- date: 2026-11-01
- self-check: [pass] short note | test: pytest -> 1 passed

## T-0002 - second deliverable (developer)
- date: 2026-11-02
- self-check: [pass] another note | test: pytest -> 2 passed
"""


def team_root(project: Path) -> Path:
    return project / ".pi" / "Teamwork" / "Teams" / TEAM


def startup_row(output: str, instance: str) -> int:
    rows = [line.split() for line in output.splitlines() if line.startswith(f"{instance} ")]
    assert rows, output
    value = int(rows[0][1])
    return value


def recallable_row(output: str, instance: str) -> int:
    rows = [line.split() for line in output.splitlines() if line.startswith(f"{instance} ")]
    assert rows, output
    return int(rows[0][1])


def test_the_token_commands_run_end_to_end(project: Path) -> None:
    init = assert_ok(cli(project, ["init", "--agents", ROSTER, "--no-git"]))
    assert "workspace ready" in init.output
    root = team_root(project)

    ledger = root / "Ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    report = json.loads(assert_ok(cli(project, ["throughput", "--json"])).stdout)
    assert report["ledger_records"] == 0
    assert report["review"]["count"] == 0
    assert report["review"]["p50_minutes"] is None
    assert "n=0" in assert_ok(cli(project, ["throughput"])).stdout

    archive = project / "docs" / "Team" / "Archive.md"
    archive.write_text(ARCHIVE, encoding="utf-8")
    selected = assert_ok(cli(project, ["archive", "--task", "T-0001"])).stdout
    assert "## T-0001 - first deliverable (developer)" in selected
    assert "T-0002" not in selected
    missing = assert_ok(cli(project, ["archive", "--task", "T-9999"])).stdout
    assert missing.strip() == "# no archive entry for T-9999"

    before = startup_row(assert_ok(cli(project, ["harness", "budget"])).stdout, "Developer-1")
    assert_ok(
        cli(
            project,
            [
                "remember",
                "developer",
                "acceptance-marker " * 200,
                "--layer",
                "long",
                "--by",
                "Developer-1",
                "--src",
                "T-0006",
                "--rev",
                "e6297bb",
            ],
        )
    )
    after = startup_row(assert_ok(cli(project, ["harness", "budget"])).stdout, "Developer-1")
    assert after == before, "the startup row must not charge a recall-only entry"

    recallable = assert_ok(cli(project, ["harness", "budget", "--recallable"])).stdout
    long_memory = root / "Roles" / "Developer" / "LongTermMemory.md"
    assert recallable_row(recallable, "Developer-1") >= long_memory.stat().st_size
    assert recallable_row(recallable, "CEO") > 0
    assert "total " in recallable

    artifact = root / "Agents" / "Developer-1" / "Artifacts" / "T-0006-proof.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("the measured evidence\n", encoding="utf-8")
    retired = assert_ok(cli(project, ["instance", "retire", "developer-1", "--reason", "idle"]))
    assert "retired Developer-1" in retired.output

    moved = root / "Runtime" / "Retired" / "Developer-1" / "Artifacts" / "T-0006-proof.txt"
    assert moved.read_text(encoding="utf-8") == "the measured evidence\n"
    assert not (root / "Agents" / "Developer-1").exists()
    assert "Runtime/Retired/Developer-1" in ledger.read_text(encoding="utf-8")
