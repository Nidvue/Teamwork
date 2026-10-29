"""Review throughput: a short lease, a packet, a profile and a priority queue.

Why these tests exist: a Reviewer claim used the 90-minute provider-slot lease,
the default was two lanes with one claim each, and the Reviewer had to rediscover
the diff and run the full matrix even for a prose-only change. Measured on the
previous revision: a dead lane froze a deliverable for 90 minutes, and a
docs-only review paid the full code suite.

Pinned here: the profile-aware review lease (a fast claim keeps the 20-minute
base, a standard claim twice it, a deep claim four times, capped), expiry and
take-over, the packet (profile, gates, self-check, checklist), profile inference,
priority/age queue order, `review --next` (claim + packet in one atomic step), the
queue listing only submitted work, capacity guidance, expired-claim reporting, and
claim->verdict latency in `coordination`.
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
    assert task["review_claim_profile"] == "standard"
    assert task["review_claim_lease"] == str(2 * engine.REVIEW_LEASE_MINUTES)
    assert engine.review_claim_state(task)[2] is True

    # The stored lease is the one the claim was granted: a standard claim is still
    # held at 21 minutes, where the flat 20-minute rule used to free it (and let
    # the other lane take the same deliverable over).
    age_claim(root, handle, 21)
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert engine.review_claim_state(task)[2] is True
    assert engine.review_claim_state(task, engine.REVIEW_LEASE_MINUTES)[2] is False

    # A lane that died past its own lease no longer blocks the deliverable.
    age_claim(root, handle, 41)
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert engine.review_claim_state(task)[2] is False
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


def test_a_deep_review_claims_a_longer_lease_than_a_prose_review(cli, project: Path) -> None:
    """The lease follows the work: prose is cheap to restart, a deep review is not."""
    root = init(cli, project)
    fast = engine.review_lease_for_profile(root, "fast")
    standard = engine.review_lease_for_profile(root, "standard")
    deep = engine.review_lease_for_profile(root, "deep")
    assert fast == engine.REVIEW_LEASE_MINUTES
    assert fast < standard < deep
    assert engine.review_lease_for_profile(root, "fast") == engine.REVIEW_LEASE_MINUTES
    # The cap wins over the multiplier, so a misconfigured base cannot freeze work.
    # Written through the real Settings file: the base lease is what the cap caps.
    import json

    settings = engine.providers_path(root)
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["ReviewLeaseMinutes"] = 100
    data["ReviewLeaseMaxMinutes"] = 240
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert engine.review_lease_for_profile(root, "deep") == 240
    data["ReviewLeaseMaxMinutes"] = 30
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert engine.review_lease_for_profile(root, "deep") == 30
    assert engine.review_lease_for_profile(root, "standard") == 30
    assert engine.review_lease_for_profile(root, "fast") == 30


def test_the_queue_lists_only_work_the_author_submitted(cli, project: Path, capsys) -> None:
    """A todo task has no frozen diff; counting it inflated the queue and the advice."""
    root = init(cli, project)
    submitted = submit(cli, project, root, "ready to review")
    assert cli("--project", project, "task", "add", "developer", "not submitted yet") == 0
    capsys.readouterr()
    assert cli("--project", project, "review", "--queue") == 0
    out = capsys.readouterr().out
    assert submitted in out
    assert "not submitted yet" not in out, "a todo task is not awaiting review"
    assert "1 deliverable(s) to review" in out


def test_review_next_claims_and_prints_the_top_packet_in_one_step(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project)
    low = submit(cli, project, root, "low priority", "--priority", "P2")
    high = submit(cli, project, root, "high priority", "--priority", "P0")
    capsys.readouterr()
    assert cli("--project", project, "review", "--next", "--by", "reviewer-1") == 0
    out = capsys.readouterr().out
    assert high in out and "# Review packet:" in out, "the claimed packet is printed"
    assert low not in out
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    claimed = [t for t in tasks if t["id"] == high][0]
    assert claimed["review_claim"] == "Reviewer-1"
    assert engine.review_is_held(claimed)

    # One lane, one deliverable: a deep review is not divisible.
    assert cli("--project", project, "review", "--next", "--by", "reviewer-1") == 2
    capsys.readouterr()
    # The other lane takes the next item.
    assert cli("--project", project, "review", "--next", "--by", "reviewer-2") == 0
    out = capsys.readouterr().out
    assert low in out


def test_review_next_reports_an_empty_queue_with_its_own_exit_code(
    cli, project: Path, capsys
) -> None:
    init(cli, project)
    capsys.readouterr()
    assert cli("--project", project, "review", "--next", "--by", "reviewer-1") == 3
    assert "nothing awaiting review" in capsys.readouterr().out


def test_coordination_reports_a_claim_that_outlived_its_lease(cli, project: Path) -> None:
    root = init(cli, project)
    handle = submit(cli, project, root, "stale claim")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-1")
        == 0
    )
    age_claim(root, handle, 2 * engine.REVIEW_LEASE_MINUTES + 1)
    report = engine.coordination_report(root)
    assert report["metrics"]["review_expired_claims"] == 1
    assert "C-REVIEW-LEASE" in {finding["code"] for finding in report["findings"]}


def test_release_clears_every_claim_field(cli, project: Path) -> None:
    """A released claim must not lend its profile or lease to the next claimant."""
    root = init(cli, project)
    handle = submit(cli, project, root, "released claim")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-1")
        == 0
    )
    assert (
        cli("--project", project, "review", "developer", handle, "--release", "--by", "reviewer-1")
        == 0
    )
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert task["review_claim"] == ""
    assert task["review_claim_ts"] == ""
    assert task["review_claim_profile"] == ""
    assert task["review_claim_lease"] == ""


def test_a_claim_after_a_release_gets_the_current_profiles_lease(cli, project: Path) -> None:
    """The next lane's lease follows the diff it reviews, not the released claim."""
    root = init(cli, project)
    deep = submit(cli, project, root, "deep review after a release", "--review-profile", "deep")
    assert (
        cli("--project", project, "review", "developer", deep, "--claim", "--by", "reviewer-1") == 0
    )
    # The claim was explicitly deep: 4x the base, and the stored lease says so.
    task = [t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == deep][
        0
    ]
    assert task["review_claim_profile"] == "deep"
    assert task["review_claim_lease"] == str(4 * engine.REVIEW_LEASE_MINUTES)
    assert (
        cli("--project", project, "review", "developer", deep, "--release", "--by", "reviewer-1")
        == 0
    )
    assert (
        cli("--project", project, "review", "developer", deep, "--claim", "--by", "reviewer-2") == 0
    )
    task = [t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == deep][
        0
    ]
    assert task["review_claim"] == "Reviewer-2"
    assert task["review_claim_profile"] == "deep"
    assert task["review_claim_lease"] == str(4 * engine.REVIEW_LEASE_MINUTES)


def test_a_take_over_gets_the_current_profiles_lease(cli, project: Path) -> None:
    """The case that distinguishes the stored lease from the profile lease.

    A release clears the stored lease, so a release-then-claim test recomputes
    either way. The stored lease is observable only on a take-over: a live
    standard claim (40m) whose profile is widened to deep, aged past 40m, then
    taken over by the other lane must be granted the CURRENT profile's 80m, not
    the 40m the expired claim was granted.
    """
    root = init(cli, project)
    handle = submit(cli, project, root, "take over a widened claim", "--review-profile", "standard")
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-1")
        == 0
    )
    path = engine.task_file(root, "developer")
    tasks = engine.parse_tasks(path)
    task = [t for t in tasks if t["id"] == handle][0]
    assert task["review_claim_lease"] == str(2 * engine.REVIEW_LEASE_MINUTES)
    task["review_profile"] = "deep"
    engine.write_tasks(path, tasks, "developer")
    age_claim(root, handle, 2 * engine.REVIEW_LEASE_MINUTES + 1)
    assert (
        cli("--project", project, "review", "developer", handle, "--claim", "--by", "reviewer-2")
        == 0
    )
    task = [
        t for t in engine.parse_tasks(engine.task_file(root, "developer")) if t["id"] == handle
    ][0]
    assert task["review_claim"] == "Reviewer-2"
    assert task["review_claim_profile"] == "deep"
    assert task["review_claim_lease"] == str(4 * engine.REVIEW_LEASE_MINUTES)
