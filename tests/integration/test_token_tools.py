"""Integration: the six M18 token/throughput tools on throwaway teams.

Layer ``integration``, area ``throughput``, owner Tester (T-0006). Every case
builds its own workspace under ``tmp_path`` and drives the shipped command, then
asserts what an operator sees - the exit code, the exact row or line, and the
record the command left on disk:

* ``archive --task`` selects one deliverable and leaves the default view intact;
* ``harness budget`` charges the startup read, not the recall-only store;
* ``coordination`` separates reviewer oversupply from a review backlog;
* ``preflight`` warns - never fails - when a standard diff overruns its slice;
* ``throughput`` reports exact claim->verdict percentiles from the ledger;
* ``instance retire`` moves a lane's evidence and a failed move never deletes it.

The budget case runs ``scripts/teamwork.py`` as a subprocess on purpose: the
unit layer already calls ``harness.instance_always_on`` directly, and the claim
under test is what the shipped command prints for a real workspace.

Owner: tester. Layer: integration. Area: throughput.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from teamwork import config, engine

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"

#: One fixed team name for every command, so ``--team`` can never drift between
#: the in-process CLI and the shipped subprocess.
TEAM = "TokenTools"

ROSTER = "ceo,developer-1,tester-1,reviewer-1"

ARCHIVE = """# ARCHIVE - reviewed results

> One entry per passed review.

## T-0001 - first deliverable (developer)
- date: 2026-11-01
- priority: P1
- self-check: [pass] short note | test: pytest -> 1 passed

## T-0002 - second deliverable (developer)
- date: 2026-11-02
- priority: P0
- self-check: [pass] {long_note} | test: pytest -> 2 passed
"""

#: claim -> verdict gaps of 10, 15, 40 and 5 minutes. Sorted, the 0-based
#: percentile index ``int(n * share)`` gives p50 = index 2 -> 15.0 and
#: p90 = index 3 -> 40.0; the test asserts those numbers, not the runner.
SYNTHETIC_LEDGER = (
    ("2026-11-03T10:00:00", "review.claim", "T-0001"),
    ("2026-11-03T10:10:00", "review.fail", "T-0001"),
    ("2026-11-03T10:20:00", "review.claim", "T-0001"),
    ("2026-11-03T10:35:00", "review.pass", "T-0001"),
    ("2026-11-03T11:00:00", "review.claim", "T-0002"),
    ("2026-11-03T11:40:00", "review.pass", "T-0002"),
    ("2026-11-03T12:00:00", "review.claim", "T-0003"),
    ("2026-11-03T12:05:00", "review.pass", "T-0003"),
)


def team_root(project: Path) -> Path:
    return project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / TEAM


def cli_run(cli, project: Path, *argv: str) -> int:
    return cli("--project", project, "--team", TEAM, *argv)


def shipped(project: Path, *argv: str) -> subprocess.CompletedProcess:
    """Run the checkout's ``scripts/teamwork.py`` against the temp workspace."""
    env = os.environ.copy()
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.pop("TEAMWORK_ROOT", None)
    env.pop("TEAMWORK_TEAM", None)
    return subprocess.run(
        [sys.executable, str(CLI_SHIM), "--project", str(project), "--team", TEAM, *argv],
        cwd=str(project),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def init_workspace(cli, project: Path, agents: str = ROSTER, git: bool = False) -> Path:
    argv = ["init", "--agents", agents] + ([] if git else ["--no-git"])
    assert cli_run(cli, project, *argv) == 0
    return team_root(project)


def budget_rows(output: str) -> dict:
    rows = {}
    for line in output.splitlines():
        if not line or line.startswith("#") or line.startswith("total "):
            continue
        cells = line.split()
        assert len(cells) == 4, line
        rows[cells[0]] = int(cells[1])
    return rows


def recallable_rows(output: str) -> dict:
    rows = {}
    for line in output.splitlines():
        if not line or line.startswith("#") or line.startswith("total "):
            continue
        cells = line.split()
        assert len(cells) == 2, line
        rows[cells[0]] = int(cells[1])
    return rows


def edit_tasks(root: Path, role: str, statuses: list) -> None:
    """Fixture setup: put the first ``len(statuses)`` tasks in review order."""
    path = engine.task_file(root, role)
    tasks = engine.parse_tasks(path)
    for index, status in enumerate(statuses):
        tasks[index]["status"] = status
        if status == "review":
            tasks[index]["self_check"] = "passed"
    engine.write_tasks(path, tasks, role)


def add_tasks(cli, project: Path, titles: list) -> None:
    for title in titles:
        assert cli_run(cli, project, "task", "add", "developer", title) == 0


def coordination_report(cli, project: Path, capsys) -> dict:
    capsys.readouterr()
    assert cli_run(cli, project, "coordination", "--json") == 0
    return json.loads(capsys.readouterr().out)


def findings(report: dict) -> dict:
    return {finding["code"]: finding for finding in report["findings"]}


def commit_all(cli, project: Path, task: str) -> None:
    assert (
        cli_run(
            cli,
            project,
            "commit",
            "--role",
            "developer",
            "--task",
            task,
            "--type",
            "feat",
            "--goal",
            "land a slice",
            "--deliverable",
            "the task's files",
            "--why",
            "the task asks for it",
            "--status",
            "implemented",
            "--result",
            "pytest -q -> 1 passed",
            "--all",
        )
        == 0
    )


# --------------------------------------------------------------------------- #
# 1. archive --task
# --------------------------------------------------------------------------- #


def test_archive_task_selects_one_deliverable_and_keeps_the_view(cli, project, capsys):
    init_workspace(cli, project, "ceo,developer-1")
    archive = project / "docs" / "Team" / "Archive.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(ARCHIVE.format(long_note="x" * 900), encoding="utf-8")

    capsys.readouterr()
    assert cli_run(cli, project, "archive", "--task", "T-0001") == 0
    selected = capsys.readouterr().out
    assert selected.startswith("## T-0001 - first deliverable (developer)")
    assert "T-0002" not in selected
    assert selected.count("## ") == 1

    capsys.readouterr()
    assert cli_run(cli, project, "archive", "--task", "T-9999") == 0
    assert capsys.readouterr().out.strip() == "# no archive entry for T-9999"

    capsys.readouterr()
    assert cli_run(cli, project, "archive") == 0
    default = capsys.readouterr().out
    assert "## T-0001" in default and "## T-0002" in default
    assert "x" * 700 not in default, "the default view must still clip quoted evidence"

    capsys.readouterr()
    assert cli_run(cli, project, "archive", "--limit", "1") == 0
    limited = capsys.readouterr().out
    assert "## T-0002" in limited and "## T-0001" not in limited
    assert "1 of 2 entries (most recent first)" in limited

    capsys.readouterr()
    assert cli_run(cli, project, "archive", "--task", "T-0002", "--full") == 0
    assert "x" * 900 in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# 2. harness budget: startup vs recallable
# --------------------------------------------------------------------------- #


def test_harness_budget_charges_startup_not_the_recall_only_store(cli, project):
    init_workspace(cli, project, "ceo,developer-1,reviewer-1")
    before = shipped(project, "harness", "budget")
    assert before.returncode == 0, before.stderr
    startup_before = budget_rows(before.stdout)
    assert set(startup_before) == {"CEO", "Developer-1", "Reviewer-1"}
    assert "cap: 122880 bytes per instance (default)" in before.stdout

    remembered = shipped(
        project,
        "remember",
        "developer",
        "long-term-marker " * 300,
        "--layer",
        "long",
        "--by",
        "Developer-1",
        "--src",
        "T-0034",
        "--rev",
        "e6297bb",
    )
    assert remembered.returncode == 0, remembered.stderr

    after = shipped(project, "harness", "budget")
    assert after.returncode == 0, after.stderr
    assert budget_rows(after.stdout) == startup_before, (
        "a long-term entry is read with recall, so it must not move the startup row"
    )

    recallable = shipped(project, "harness", "budget", "--recallable")
    assert recallable.returncode == 0, recallable.stderr
    recallable_before = recallable_rows(recallable.stdout)
    assert set(recallable_before) == set(startup_before)
    long_bytes = (
        (team_root(project) / config.DIR_ROLES / "Developer" / config.F_LONG).stat().st_size
    )
    assert recallable_before["Developer-1"] >= long_bytes
    assert "total " in recallable.stdout

    lesson = shipped(
        project,
        "lesson",
        "add",
        "--by",
        "Developer-1",
        "--mistake",
        "left the gate red",
        "--cause",
        "skipped it",
        "--rule",
        "run it first",
        "--evidence",
        "pytest @abc -> 1 failed",
    )
    assert lesson.returncode == 0, lesson.stderr
    knowledge = shipped(
        project,
        "knowledge",
        "add",
        "--by",
        "Developer-1",
        "--topic",
        "slice budget",
        "--statement",
        "the standard profile warns past 12 files",
        "--evidence",
        "pytest @abc -> 1 passed",
    )
    assert knowledge.returncode == 0, knowledge.stderr

    grown = shipped(project, "harness", "budget")
    assert grown.returncode == 0, grown.stderr
    startup_grown = budget_rows(grown.stdout)
    lesson_line = "- [L-0001] left the gate red -> run it first\n"
    knowledge_line = (
        "- [K-0001] [fact] slice budget: the standard profile warns past 12 files "
        "(uses=0, tags=-)\n"
    )
    assert startup_grown["Developer-1"] - startup_before["Developer-1"] == len(
        (lesson_line + knowledge_line).encode("utf-8")
    )
    assert startup_grown["CEO"] - startup_before["CEO"] == len(knowledge_line.encode("utf-8"))


# --------------------------------------------------------------------------- #
# 3-4. coordination: oversupply vs backlog
# --------------------------------------------------------------------------- #


def test_nine_reviewer_lanes_with_two_unclaimed_is_oversupply_not_backlog(cli, project, capsys):
    init_workspace(cli, project, "ceo,developer-1,tester-1,reviewer-1")
    assert cli_run(cli, project, "instance", "add", "reviewer", "--count", "8", "--by", "ceo") == 0
    add_tasks(cli, project, ["alpha review", "bravo review"])
    edit_tasks(team_root(project), "developer", ["review", "review"])

    report = coordination_report(cli, project, capsys)
    found = findings(report)

    assert "C-REVIEW-OVERSUPPLY" in found
    assert "C-REVIEW-BACKLOG" not in found
    oversupply = found["C-REVIEW-OVERSUPPLY"]
    assert oversupply["severity"] == "low"
    assert oversupply["subject"] == "9 lane(s) / 2 unclaimed"
    assert "retire or reuse an idle Reviewer lane" in oversupply["fix"]
    assert report["metrics"]["reviewer_lanes"] == 9
    assert report["metrics"]["review_queue"] == 2


def test_five_unclaimed_with_two_lanes_is_backlog_not_oversupply(cli, project, capsys):
    init_workspace(cli, project, "ceo,developer-1,tester-1,reviewer-1,reviewer-2")
    titles = ["alpha review", "bravo review", "charlie review", "delta review", "echo review"]
    add_tasks(cli, project, titles)
    edit_tasks(team_root(project), "developer", ["review"] * 5)

    report = coordination_report(cli, project, capsys)
    found = findings(report)

    assert "C-REVIEW-BACKLOG" in found
    assert "C-REVIEW-OVERSUPPLY" not in found
    assert found["C-REVIEW-BACKLOG"]["severity"] == "medium"
    assert found["C-REVIEW-BACKLOG"]["subject"].startswith("5 unclaimed / 2 lane(s)")
    assert report["metrics"]["reviewer_lanes"] == 2
    assert report["metrics"]["review_queue"] == 5


# --------------------------------------------------------------------------- #
# 5. preflight slice warning
# --------------------------------------------------------------------------- #


def test_preflight_warns_on_an_oversized_slice_and_stays_green(cli, project, capsys):
    """13 files is past the standard 12-file slice; 2 files is inside it."""
    init_workspace(cli, project, "ceo,developer-1", git=True)
    add_tasks(cli, project, ["a standard slice", "a small slice"])

    assert (
        cli_run(cli, project, "branch", "start", "--agent", "developer-1", "--task", "T-0001") == 0
    )
    for index in range(13):
        (project / f"slice-{index}.txt").write_text("one line\n", encoding="utf-8")
    commit_all(cli, project, "T-0001")

    capsys.readouterr()
    code = cli_run(cli, project, "preflight", "developer", "T-0001")
    oversized = capsys.readouterr().out
    assert code == 0, oversized
    assert re.search(
        r"^- warn\s+slice\s+13 files / 13 changed lines vs standard budget", oversized, re.M
    )
    assert "split the task or record why it cannot be split" in oversized
    assert "PREFLIGHT pass" in oversized
    assert "8 checks, 0 failed" in oversized

    assert (
        cli_run(cli, project, "branch", "start", "--agent", "developer-1", "--task", "T-0002") == 0
    )
    for name in ("small-a.txt", "small-b.txt"):
        (project / name).write_text("one line\n", encoding="utf-8")
    commit_all(cli, project, "T-0002")

    capsys.readouterr()
    code = cli_run(cli, project, "preflight", "developer", "T-0002")
    small = capsys.readouterr().out
    assert code == 0, small
    assert not re.search(r"^- \w+\s+slice\b", small, re.M), small
    assert "PREFLIGHT pass" in small
    assert "7 checks, 0 failed" in small


# --------------------------------------------------------------------------- #
# 6. throughput: exact arithmetic over a synthetic ledger
# --------------------------------------------------------------------------- #


def test_throughput_reports_exact_percentiles_and_surface_bytes(cli, project, capsys):
    root = init_workspace(cli, project, "ceo,developer-1,tester-1,reviewer-1")
    add_tasks(cli, project, ["alpha item", "bravo item", "charlie item"])

    ledger = engine.ledger_path(root)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "n": index,
                "actor": "Reviewer-1",
                "role": "developer",
                "rev": "",
                "hash": "",
                "prev": "",
                "ts": stamp,
                "action": action,
                "target": target,
            },
            sort_keys=True,
        )
        for index, (stamp, action, target) in enumerate(SYNTHETIC_LEDGER, 1)
    ]
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    edit_tasks(root, "developer", ["review", "doing", "todo"])

    report = json.loads(shipped(project, "throughput", "--json").stdout)
    review = report["review"]
    assert review == {
        "count": 4,
        "p50_minutes": 15.0,
        "p90_minutes": 40.0,
        "max_minutes": 40.0,
        "pass": 3,
        "fail": 1,
        "targets": 3,
        "multi_verdict_targets": 1,
    }
    assert report["ledger_records"] == 8
    assert report["instances"] == 4
    developer = next(row for row in report["queue"] if row["role"] == "developer")
    assert developer == {"role": "developer", "todo": 1, "doing": 1, "review": 1}

    surface = report["surface"]
    docs = project / "docs" / "Team"
    docs_total = sum(path.stat().st_size for path in docs.glob("*.md"))
    assert surface["agents_bytes"] == (project / "AGENTS.md").stat().st_size
    assert surface["docs_bytes"] == docs_total
    assert surface["docs_tokens"] == docs_total // 4
    assert surface["archive_tokens"] == surface["archive_bytes"] // 4
    assert surface["decisions_tokens"] == surface["decisions_bytes"] // 4
    assert surface["plan_tokens"] == surface["plan_bytes"] // 4
    assert surface["largest_task_queue"] == "developer"
    assert surface["largest_task_queue_bytes"] == engine.task_file(root, "developer").stat().st_size
    assert surface["startup_min_bytes"] <= surface["startup_max_bytes"]

    before = ledger.read_bytes()
    text = shipped(project, "throughput")
    assert text.returncode == 0, text.stderr
    assert "review claim->verdict: n=4 p50=15.0m p90=40.0m max=40.0m" in text.stdout
    assert "verdicts: 3 pass / 1 fail" in text.stdout
    assert "targets: 1/3 with more than one verdict" in text.stdout
    assert "instances: 4" in text.stdout
    assert ledger.read_bytes() == before, "the report is read-only"


# --------------------------------------------------------------------------- #
# 7-8. retirement: move-only, and a failed move never deletes
# --------------------------------------------------------------------------- #


def test_retirement_moves_the_lane_and_its_artifacts(cli, project):
    root = init_workspace(cli, project, "ceo,developer-1")
    lane = engine.agent_dir(root, "Developer-1")
    artifact = lane / "Artifacts" / "T-0001-proof.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("the measured evidence\n", encoding="utf-8")

    assert cli_run(cli, project, "instance", "retire", "developer-1", "--reason", "idle") == 0

    retired = root / "Runtime" / "Retired" / "Developer-1"
    assert not lane.exists()
    assert (retired / "Artifacts" / "T-0001-proof.txt").read_text(encoding="utf-8") == (
        "the measured evidence\n"
    )
    records = [row for row in engine.ledger_read(root) if row["action"] == "instance.retire"]
    assert records, "the retirement must be recorded in the ledger"
    assert "Runtime/Retired/Developer-1" in records[-1]["detail"]


def test_a_failed_retirement_move_never_deletes_the_lane(cli, project, monkeypatch):
    root = init_workspace(cli, project, "ceo,developer-1")
    lane = engine.agent_dir(root, "Developer-1")
    artifact = lane / "Artifacts" / "proof.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("still mine\n", encoding="utf-8")

    def refuse(_source, _destination):
        raise OSError("read-only volume")

    monkeypatch.setattr(engine.shutil, "move", refuse)
    code = cli_run(cli, project, "instance", "retire", "developer-1", "--reason", "idle")

    assert code == 1
    assert artifact.read_text(encoding="utf-8") == "still mine\n"
    assert not (root / "Runtime" / "Retired" / "Developer-1").exists()
    assert not [row for row in engine.ledger_read(root) if row["action"] == "instance.retire"]
