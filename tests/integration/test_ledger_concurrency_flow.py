"""The ledger chain survives writers in separate processes.

Layer ``integration``, area ``ledger-concurrency``, owner Tester (T-0013). A
team runs several lanes at once and each one appends to the same
``Ledger.jsonl``; the chain is only worth anything if concurrent appends cannot
fork it. ``ledger_append`` takes ``ledger.lock`` for read-prev -> append ->
head-write, and this layer proves it where it matters: from real processes, not
from threads in one interpreter, then re-verifies the chain with the shipped
``ledger verify``.

The child is the shipped engine itself - no private helper is called - so a
regression that removes the lock from the write path is red here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from support import team_root
from teamwork import engine

REPO_ROOT = Path(__file__).resolve().parents[2]
WRITERS = 6
PER_WRITER = 3

CHILD = """
import sys
from pathlib import Path
from teamwork import engine

root = Path(sys.argv[1])
writer, count = sys.argv[2], int(sys.argv[3])
for index in range(count):
    engine.ledger_append(root, "decision.add", writer, f"concurrency probe {writer}", f"n={index}")
"""


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")) if part
    )
    env.pop("TEAMWORK_ROOT", None)
    return env


def burst(root: Path) -> None:
    """Run the writers as separate processes against one ledger."""
    children = [
        subprocess.Popen(
            [sys.executable, "-c", CHILD, str(root), f"writer-{index}", str(PER_WRITER)],
            env=_child_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(WRITERS)
    ]
    for child in children:
        out, err = child.communicate(timeout=180)
        assert child.returncode == 0, f"writer failed: {out}\n{err}"


def test_concurrent_writers_leave_one_verifiable_chain(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = team_root(project)
    seeded = len(engine.ledger_read(root))

    burst(root)

    records = engine.ledger_read(root)
    assert len(records) == seeded + WRITERS * PER_WRITER
    assert engine.ledger_verify(root) == [], "concurrent writers forked the chain"

    details = [record["detail"] for record in records if record["actor"].startswith("writer-")]
    assert sorted(details) == sorted(
        f"n={index}" for _ in range(WRITERS) for index in range(PER_WRITER)
    ), "a concurrent append was lost or duplicated"

    actors = sorted(
        {record["actor"] for record in records if record["actor"].startswith("writer-")}
    )
    assert actors == [f"writer-{index}" for index in range(WRITERS)]


def test_the_chain_still_accepts_a_sequential_append_after_the_burst(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    root = team_root(project)

    burst(root)

    engine.ledger_append(root, "decision.add", "Tester", "after the burst", "sequential")
    assert engine.ledger_verify(root) == []
    assert engine.ledger_read(root)[-1]["detail"] == "sequential"
