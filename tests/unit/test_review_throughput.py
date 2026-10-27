"""Review throughput: a short lease, a packet, a profile and a priority queue.

Why these tests exist: a Reviewer claim used the 90-minute provider-slot lease,
the default was two lanes with one claim each, and the Reviewer had to rediscover
the diff and run the full matrix even for a prose-only change. Measured on the
previous revision: a dead lane froze a deliverable for 90 minutes, and a
docs-only review paid the full code suite.

Pinned here: the 20-minute renewable review lease, expiry/take-over, the packet
(profile, gates, self-check, checklist), profile inference, priority/age queue
order, capacity guidance, and claim->verdict latency in `coordination`.
"""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path

from tests.gitenv import child_env

from teamwork import engine

ROSTER = "ceo,developer-1,tester-1,reviewer-1,reviewer-2"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def submit(cli, project: Path, root: Path, title: str, *extra: str) -> str:
    args = ["--project", project, "task", "add", "developer", title, *extra]
    assert cli(*args) == 0
    path = engine.task_file(root, "developer")
    handle = [t for t in engine.parse_tasks(path) if t["title"] == title][-1]["id"]
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            handle,
            "--by",
            "developer-1",
            "--note",
            "re-read the diff",
            "--test",
            "pytest -q @abc123 -> 9 passed",
        )
        == 0
    )
    return handle


def age_claim(root: Path, handle: str, minutes: int, role: str = "developer") -> None:
    path = engine.task_file(root, role)
    tasks = engine.parse_tasks(path)
    task = [t for t in tasks if t["id"] == handle][0]
    stamp = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    task["review_claim_ts"] = stamp.isoformat(timespec="minutes")
    engine.write_tasks(path, tasks, role)


def git(project: Path, *args: str) -> str:
    env = child_env(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    result = subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_review_lease_is_short_expires_and_renews(cli, project: Path) -> None:
    root = init(cli, project)
    assert engine.REVIEW_LEASE_MINUTES == 20
    assert engine.REVIEW_LEASE_MINUTES != engine.SLOT_TTL_MINUTES
    handle = submit(cli, project, root, "review lease")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-1")
        == 0
    )
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert engine.review_claim_state(task, engine.REVIEW_LEASE_MINUTES)[2] is True

    # A lane that died 21 minutes ago no longer blocks the deliverable.
    age_claim(root, handle, 21)
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert engine.review_claim_state(task, engine.REVIEW_LEASE_MINUTES)[2] is False
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-2")
        == 0
    )

    # Only the holder renews, and renewal resets the clock.
    age_claim(root, handle, 15)
    assert (
        cli("--project", project, "review", "developer", handle, "--renew", "--by", "reviewer-1")
        == 2
    )
    assert (
        cli("--project", project, "review", "developer", handle, "--renew", "--by", "reviewer-2")
        == 0
    )
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    lane, age, held = engine.review_claim_state(task, engine.REVIEW_LEASE_MINUTES)
    assert lane == "Reviewer-2" and held and age is not None and age < engine.REVIEW_LEASE_MINUTES


def test_packet_gives_the_reviewer_everything_needed_to_start(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    handle = submit(cli, project, root, "document the parser", "--review-profile", "fast")
    capsys.readouterr()
    assert cli("--project", project, "review", "developer", handle, "--packet") == 0
    out = capsys.readouterr().out
    assert "profile: fast" in out
    assert "gates:" in out and "checklist:" in out
    assert "claim:" in out and "--renew" in out
    assert "self-check note" in out and "self-check artifacts" not in out


def test_profile_is_inferred_from_tags_and_can_be_overridden(cli, project: Path) -> None:
    root = init(cli, project)
    deep = submit(cli, project, root, "rotate the signing key", "--tags", "security")
    fast = submit(cli, project, root, "fix the docs", "--review-profile", "fast")
    profile_deep, _ = engine.review_profile_for(
        root, "developer", engine.parse_tasks(engine.task_file(root, "developer"))[0]
    )
    profile_fast, _ = engine.review_profile_for(
        root, "developer", engine.parse_tasks(engine.task_file(root, "developer"))[1]
    )
    assert profile_deep == "deep"
    assert profile_fast == "fast"
    assert deep != fast


def test_review_queue_is_priority_then_age_and_reports_capacity(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    low = submit(cli, project, root, "low priority prose", "--priority", "P2")
    high = submit(cli, project, root, "high priority prose", "--priority", "P0")
    mid = submit(cli, project, root, "middle priority prose", "--priority", "P1")
    capsys.readouterr()
    assert cli("--project", project, "review", "--queue") == 0
    out = capsys.readouterr().out
    assert out.index(high) < out.index(mid) < out.index(low)
    assert "review capacity:" in out or "capacity:" in out
    assert "oldest" in out


def test_claim_to_verdict_latency_is_measured(cli, project: Path) -> None:
    root = init(cli, project)
    handle = submit(cli, project, root, "measure the review", "--review-profile", "fast")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-1")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            handle,
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest tests/unit/test_docs_contracts.py @abc -> 17 passed",
        )
        == 0
    )
    report = engine.coordination_report(root)
    assert report["metrics"]["review_p50_minutes"] is not None
    assert report["metrics"]["review_p90_minutes"] is not None
    assert report["metrics"]["review_queue"] == 0


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def test_coordination_flags_a_review_backlog(cli, project: Path) -> None:
    root = init(cli, project)
    path = engine.task_file(root, "developer")
    tasks = []
    for index in range(5):
        task = engine.new_task(f"queued item {index}")
        task["status"] = "review"
        task["self_check"] = "passed"
        task["claimed_by"] = "Developer-1"
        task["created"] = "2026-01-01"
        tasks.append(task)
    engine.write_tasks(path, tasks, "developer")
    report = engine.coordination_report(root)
    assert "C-REVIEW-BACKLOG" in {finding["code"] for finding in report["findings"]}


def test_profile_is_inferred_from_the_branch_diff_and_renames(cli, project: Path) -> None:
    git(project, "init", "-q", "-b", "main")
    (project / "src" / "pkg").mkdir(parents=True)
    (project / "src" / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-qm", "base")
    root = init(cli, project)

    git(project, "checkout", "-q", "-b", "docs")
    (project / "docs").mkdir(exist_ok=True)
    (project / "docs" / "x.md").write_text("doc\n", encoding="utf-8")
    git(project, "add", "docs/x.md")
    git(project, "commit", "-qm", "docs")
    docs_task = {"branch": "docs", "base": "main", "tags": "", "area": "", "review_profile": ""}
    assert engine.review_profile_for(root, "developer", docs_task)[0] == "fast"

    git(project, "checkout", "-q", "main")
    git(project, "checkout", "-q", "-b", "code")
    (project / "src" / "pkg" / "mod.py").write_text("x = 2\n", encoding="utf-8")
    git(project, "add", "src/pkg/mod.py")
    git(project, "commit", "-qm", "code")
    code_task = {"branch": "code", "base": "main", "tags": "", "area": "", "review_profile": ""}
    assert engine.review_profile_for(root, "developer", code_task)[0] == "standard"

    git(project, "checkout", "-q", "main")
    git(project, "checkout", "-q", "-b", "workflow")
    (project / ".github" / "workflows").mkdir(parents=True)
    (project / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    git(project, "add", ".github/workflows/ci.yml")
    git(project, "commit", "-qm", "workflow")
    workflow_task = {
        "branch": "workflow",
        "base": "main",
        "tags": "",
        "area": "",
        "review_profile": "",
    }
    assert engine.review_profile_for(root, "developer", workflow_task)[0] == "deep"

    git(project, "checkout", "-q", "main")
    git(project, "checkout", "-q", "-b", "rename")
    (project / "docs").mkdir(exist_ok=True)
    git(project, "mv", "src/pkg/mod.py", "docs/mod.md")
    git(project, "commit", "-qm", "move")
    rename_task = {"branch": "rename", "base": "main", "tags": "", "area": "", "review_profile": ""}
    profile, reason = engine.review_profile_for(root, "developer", rename_task)
    assert profile == "standard", reason
    packet = engine.review_packet(
        root,
        "developer",
        {
            **rename_task,
            "id": "T-0001",
            "title": "move the module",
            "priority": "P2",
            "status": "review",
            "self_check": "passed",
            "review_status": "pending",
        },
    )
    assert "docs/mod.md" in packet and "src/pkg/mod.py" in packet


def test_queue_ties_break_by_age(cli, project: Path) -> None:
    root = init(cli, project)
    path = engine.task_file(root, "developer")
    tasks = []
    for created, title in (("2026-01-03", "newer"), ("2026-01-01", "older")):
        task = engine.new_task(title)
        task["status"] = "review"
        task["self_check"] = "passed"
        task["claimed_by"] = "Developer-1"
        task["created"] = created
        tasks.append(task)
    engine.write_tasks(path, tasks, "developer")
    items = engine.open_review_items(root)
    assert [task["title"] for _name, task in items] == ["older", "newer"]


def test_review_latency_does_not_mix_task_ids_across_roles(cli, project: Path) -> None:
    root = init(cli, project)
    engine.ledger_append(root, "review.claim", "Reviewer-1", "T-0001", "", "", "developer")
    engine.ledger_append(root, "review.claim", "Reviewer-2", "T-0001", "", "", "tester")
    engine.ledger_append(root, "review.pass", "Reviewer-1", "T-0001", "ok", "", "developer")
    engine.ledger_append(root, "review.pass", "Reviewer-2", "T-0001", "ok", "", "tester")
    assert engine.review_latency(root)["count"] == 2


def test_packet_is_read_only(cli, project: Path) -> None:
    root = init(cli, project)
    handle = submit(cli, project, root, "packet guard")
    assert (
        cli("--project", project, "review", "developer", handle, "--packet", "--result", "pass")
        == 2
    )
