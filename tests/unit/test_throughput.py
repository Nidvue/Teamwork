"""`teamwork throughput` is the reproducible reader for Throughput.md's baseline.

The report is only useful if its numbers come from the ledger and the tree rather
than a hand-written table, so these tests build a synthetic ledger with known
claim->verdict gaps and a workspace with known queue counts, then assert the
report's counts, percentiles, rework share and surface sizes. They also pin the
read-only contract: running the report (text or `--json`) leaves the ledger
byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine, harness


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path) -> Path:
    assert (
        cli(
            "--project",
            project,
            "init",
            "--agents",
            "ceo,developer-1,reviewer-1,tester-1",
            "--no-git",
        )
        == 0
    )
    return team_root(project)


def write_ledger(root: Path, records: list) -> None:
    path = engine.ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, record in enumerate(records, 1):
        payload = {
            "n": index,
            "actor": "Reviewer-1",
            "role": "developer",
            "rev": "",
            "hash": "",
            "prev": "",
            **record,
        }
        lines.append(json.dumps(payload, sort_keys=True))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def synthetic_ledger() -> list:
    return [
        {"ts": "2026-11-03T10:00:00", "action": "task.add", "target": "T-0001"},
        {"ts": "2026-11-03T10:00:00", "action": "review.claim", "target": "T-0001"},
        {
            "ts": "2026-11-03T10:10:00",
            "action": "review.fail",
            "target": "T-0001",
            "actor": "Reviewer-1",
        },
        {"ts": "2026-11-03T10:20:00", "action": "review.claim", "target": "T-0001"},
        {
            "ts": "2026-11-03T10:40:00",
            "action": "review.pass",
            "target": "T-0001",
            "actor": "Reviewer-1",
        },
        {"ts": "2026-11-03T11:00:00", "action": "review.claim", "target": "T-0002"},
        {
            "ts": "2026-11-03T11:40:00",
            "action": "review.pass",
            "target": "T-0002",
            "actor": "Reviewer-1",
        },
        {"ts": "2026-11-03T12:00:00", "action": "task.add", "target": "T-0003"},
    ]


def edit_task(root: Path, role: str, handle: str, **fields) -> None:
    path = engine.task_file(root, role)
    tasks = engine.parse_tasks(path)
    task = next(t for t in tasks if t["id"] == handle)
    task.update(fields)
    engine.write_tasks(path, tasks, role)


def test_the_report_counts_the_ledger_and_the_rework_share(cli, project: Path) -> None:
    root = init(cli, project)
    write_ledger(root, synthetic_ledger())

    report = engine.throughput_report(root)

    assert report["team"] == root.name
    assert report["ledger_records"] == 8
    assert {"action": "task.add", "count": 2} in report["actions"]
    review = report["review"]
    assert review["count"] == 3
    assert review["pass"] == 2
    assert review["fail"] == 1
    assert review["targets"] == 2
    assert review["multi_verdict_targets"] == 1
    assert review["max_minutes"] == 40.0
    assert review["p50_minutes"] == 20.0
    assert review["p90_minutes"] == 40.0


def test_the_queue_lines_and_instance_count_are_read_from_the_workspace(cli, project: Path) -> None:
    root = init(cli, project)
    for title in ("first", "second", "third"):
        assert cli("--project", project, "task", "add", "developer", title) == 0
    edit_task(root, "developer", "T-0001", status="review")
    edit_task(root, "developer", "T-0002", status="doing")

    report = engine.throughput_report(root)

    developer = next(row for row in report["queue"] if row["role"] == "developer")
    assert developer == {"role": "developer", "todo": 1, "doing": 1, "review": 1}
    assert report["instances"] == 4


def test_the_surface_is_the_same_bytes_the_harness_measures(cli, project: Path) -> None:
    root = init(cli, project)
    report = engine.throughput_report(root)["surface"]
    docs = project / "docs" / "Team"
    docs_total = sum(path.stat().st_size for path in docs.glob("*.md"))

    assert report["agents_bytes"] == harness.file_size(project / "AGENTS.md")
    assert report["skill_bytes"] == harness.file_size(project / "SKILL.md")
    assert report["startup_min_bytes"] <= report["startup_max_bytes"]
    assert report["docs_bytes"] == docs_total
    assert report["docs_tokens"] == docs_total // 4
    assert report["archive_tokens"] == report["archive_bytes"] // 4
    assert report["largest_task_queue"] == "developer"
    assert report["largest_task_queue_tokens"] == report["largest_task_queue_bytes"] // 4


def test_an_empty_ledger_prints_dashes_not_none(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    engine.ledger_path(root).write_text("", encoding="utf-8")

    report = engine.throughput_report(root)
    assert report["ledger_records"] == 0
    assert report["review"]["count"] == 0
    assert report["review"]["max_minutes"] is None

    capsys.readouterr()
    assert cli("--project", project, "throughput") == 0
    out = capsys.readouterr().out
    assert "review claim->verdict: n=0 p50=- p90=- max=-" in out
    assert "None" not in out


def test_text_and_json_are_deterministic_and_read_only(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    write_ledger(root, synthetic_ledger())
    ledger = engine.ledger_path(root)
    before = ledger.read_bytes()

    first = engine.throughput_report(root)
    second = engine.throughput_report(root)
    assert first == second
    assert ledger.read_bytes() == before

    capsys.readouterr()
    assert cli("--project", project, "throughput", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "throughput"
    assert payload["ledger_records"] == 8

    capsys.readouterr()
    assert cli("--project", project, "throughput") == 0
    text = capsys.readouterr().out
    assert text.startswith(f"# throughput ({root.name})")
    assert "ledger records: 8" in text
    assert "review claim->verdict: n=3" in text
    assert "targets: 1/2 with more than one verdict" in text
    assert "instances: 4" in text
    assert "largest TaskQueue developer" in text
    assert ledger.read_bytes() == before
