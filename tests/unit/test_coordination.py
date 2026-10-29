"""Coordination health: the multi-agent failure modes the records can show.

Why these tests exist: the article this change is built from measured that lanes
sharing a model, a context and a queue fail together, that starved lanes poll and
race, and that a review lane with no cross-check turns one blind spot into a
systemic one. The team already writes every record these checks need, so each
finding must be reproducible from the workspace alone - no new telemetry, no
network, no live provider.

Pinned here: duplicate branch/title detection, Reviewer model diversity,
verbatim-evidence echo, reviewer monoculture, merge-rate collapse, the abandoned
PR rule (a live PR record on a dead branch, never a finished record whose branch
was retired), the live-lane reclaim guard, and the pulse's refusal to plan more
new lanes than free slots.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from tests.gitenv import child_env

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1,reviewer-2"

#: The identity every throwaway git repository in this file commits with. A git
#: child also gets ``tests.gitenv.child_env`` so the developer's own git
#: configuration cannot decide what these fixtures do.
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Developer",
    "GIT_AUTHOR_EMAIL": "developer@agents.nidvue.com",
    "GIT_COMMITTER_NAME": "Developer",
    "GIT_COMMITTER_EMAIL": "developer@agents.nidvue.com",
}


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def codes(report: dict) -> set:
    return {finding["code"] for finding in report["findings"]}


def task_path(root: Path, role: str) -> Path:
    return engine.task_file(root, role)


def edit_task(root: Path, role: str, handle: str, **fields) -> None:
    path = task_path(root, role)
    tasks = engine.parse_tasks(path)
    task = next(t for t in tasks if t["id"] == handle)
    task.update(fields)
    engine.write_tasks(path, tasks, role)


def test_duplicate_branch_and_title_are_diversity_findings(cli, project: Path) -> None:
    root = init(cli, project)
    title = "implement the shared parser"
    assert cli("--project", project, "task", "add", "developer", title) == 0
    assert cli("--project", project, "task", "add", "tester", title) == 0
    edit_task(root, "developer", "T-0001", branch="shared/parser")
    edit_task(root, "tester", "T-0001", branch="shared/parser")

    found = codes(engine.coordination_report(root))
    assert "C-DIV-BRANCH" in found
    assert "C-DIV-TASK" in found


def test_reviewer_model_diversity_is_required_when_two_lanes_review(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli("--project", project, "model", "set", "reviewer", "--provider", "p", "--model", "one")
        == 0
    )
    report = engine.coordination_report(root)
    diversity = [f for f in report["findings"] if f["code"] == "C-DIV-MODEL"]
    assert diversity and diversity[0]["severity"] == "high"

    # A second model on the second lane clears the finding; the check reads the
    # effective model, not the fact that a setting exists.
    assert (
        cli(
            "--project",
            project,
            "model",
            "set",
            "reviewer-2",
            "--provider",
            "p",
            "--model",
            "two",
        )
        == 0
    )
    assert "C-DIV-MODEL" not in codes(engine.coordination_report(root))


def test_verbatim_review_evidence_is_an_echo(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "fix the parser") == 0
    evidence = "pytest tests/unit/test_parser.py @abc1234 -> 12 passed"
    edit_task(
        root,
        "developer",
        "T-0001",
        evidence=evidence,
        review_status="passed",
        review_evidence=evidence,
        status="done",
    )
    assert "C-TRUST-ECHO" in codes(engine.coordination_report(root))


def test_reviewer_monoculture_and_no_finding_lane_are_flagged(cli, project: Path) -> None:
    root = init(cli, project)
    for index in range(8):
        engine.ledger_append(root, "review.pass", "Reviewer-1", f"T-{index:04d}", "pytest -> ok")
    found = codes(engine.coordination_report(root))
    assert "C-TRUST-MONOCULTURE" in found
    assert "C-TRUST-NOFAIL" in found


def test_merge_rate_below_half_is_a_merge_health_finding(cli, project: Path) -> None:
    root = init(cli, project)
    prs = [
        engine.new_pr(
            f"pr {index}",
            status="merged" if index == 0 else "open",
            updated="2026-01-01",
            branch=f"dev/t-{index}",
        )
        for index in range(5)
    ]
    engine.write_reviews(engine.reviews_path(root), prs)
    report = engine.coordination_report(root)
    assert "C-MERGE-RATE" in codes(report)
    assert report["metrics"]["merge_fraction"] == 0.2


def test_reclaim_refuses_a_live_lane_and_force_is_recorded(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "live work") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "slot",
            "acquire",
            "--agent",
            "developer-1",
            "--provider",
            "ollama-cloud",
        )
        == 0
    )

    refused = cli(
        "--project",
        project,
        "task",
        "reclaim",
        "developer",
        "T-0001",
        "--as",
        "developer-2",
        "--reason",
        "silent",
    )
    assert refused == 2
    task = engine.parse_tasks(task_path(root, "developer"))[0]
    assert task["claimed_by"].lower() == "developer-1"
    assert task["status"] == "doing"

    forced = cli(
        "--project",
        project,
        "task",
        "reclaim",
        "developer",
        "T-0001",
        "--as",
        "developer-2",
        "--reason",
        "owner is dead",
        "--force",
        "confirmed dead for two hours",
    )
    assert forced == 0
    task = engine.parse_tasks(task_path(root, "developer"))[0]
    assert task["status"] == "todo" and task["claimed_by"] == ""
    assert "forced: confirmed dead" in task["findings"]

    # A released lease means the owner really is silent: no force needed.
    assert (
        cli(
            "--project",
            project,
            "slot",
            "release",
            "--agent",
            "developer-1",
            "--provider",
            "ollama-cloud",
        )
        == 0
    )
    # developer-2 now owns it; give the task to developer-1 first so the
    # reclaim crosses lanes again.
    edit_task(root, "developer", "T-0001", claimed_by="Developer-1", status="doing")
    assert (
        cli(
            "--project",
            project,
            "task",
            "reclaim",
            "developer",
            "T-0001",
            "--as",
            "developer-2",
            "--reason",
            "lease expired",
        )
        == 0
    )


def test_pulse_defers_more_new_lanes_than_free_slots(cli, project: Path) -> None:
    root = init(cli, project)
    settings = json.loads((root / engine.F_SETTINGS).read_text(encoding="utf-8"))
    for provider in ("ollama-cloud", "deepseek", "openai", "anthropic", "default"):
        settings[provider] = 0
    (root / engine.F_SETTINGS).write_text(json.dumps(settings), encoding="utf-8")

    for title in ("one", "two", "three"):
        assert cli("--project", project, "task", "add", "developer", title) == 0
    assert cli("--project", project, "pulse", "--commit") == 3
    tasks = engine.parse_tasks(task_path(root, "developer"))
    assert all(task["status"] == "todo" for task in tasks), "a starved pulse claimed work"

    settings["ollama-cloud"] = 1
    (root / engine.F_SETTINGS).write_text(json.dumps(settings), encoding="utf-8")
    assert cli("--project", project, "pulse", "--commit") == 0
    tasks = engine.parse_tasks(task_path(root, "developer"))
    # one lease covers a lane's WIP: the first lane takes both of its units on the
    # single free slot, and the second lane is the one deferred (T-0020/A5)
    doing = [task for task in tasks if task["status"] == "doing"]
    assert len(doing) == engine.LANE_WIP, [task["status"] for task in tasks]
    assert {task["claimed_by"].lower() for task in doing} == {"developer-1"}


def test_strict_exits_one_on_a_high_finding(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "one piece") == 0
    assert cli("--project", project, "task", "add", "tester", "one piece") == 0
    edit_task(root, "developer", "T-0001", branch="same")
    edit_task(root, "tester", "T-0001", branch="same")

    assert cli("--project", project, "coordination") == 0
    assert cli("--project", project, "coordination", "--strict") == 1
    assert "C-DIV-BRANCH" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Merge health: an abandoned PR is one the forge still has open
#
# The check used to mean "not merged and the branch is gone", which is the wrong
# question: every finished PR retires its branch. P-0035 was `superseded` with its
# work landed under P-0036, P-0022/P-0023 were `changes-requested` whose tasks were
# dropped, and P-0010 was `approved` with a merge_commit - four terminal records
# reported as high-severity abandonment. The rule below is stated from the record
# states, not from those four cases, and each state is pinned separately so a
# regression to "not merged" fails here.
# --------------------------------------------------------------------------- #


def pr_record(**fields) -> dict:
    """A PR record carrying only the fields the abandoned rule reads."""
    return engine.new_pr(fields.pop("title", "a change"), **fields)


#: status, merge_commit, and whether the forge still owes that record an action.
PR_STATES = (
    ("open", "", True),
    ("in-review", "", True),
    ("changes-requested", "", True),
    # An approval is a decision, not a landing: without the merge commit the
    # merge is still owed, so the record is live.
    ("approved", "", True),
    ("approved", "abc1234", False),
    ("merged", "abc1234", False),
    ("closed", "", False),
    ("superseded", "", False),
    # A status this engine does not know fails closed: an unreadable record is
    # not evidence that the work finished.
    ("on-hold", "", True),
)


@pytest.mark.parametrize("status,merge_commit,owes_action", PR_STATES)
def test_the_pr_status_decides_whether_an_action_is_still_owed(
    status: str, merge_commit: str, owes_action: bool
) -> None:
    record = pr_record(
        status=status,
        merge_commit=merge_commit,
        task="T-0001",
        role="developer",
        branch="developer/gone",
    )
    live_task = {"id": "T-0001", "status": "doing"}
    assert engine.pr_owes_action(record) == owes_action
    # The same status, with a live task and a dead branch: only the live states
    # are abandonment.
    assert engine.pr_is_abandoned(record, live_task, True) == owes_action


#: task status, and whether that task still owes the team an outcome.
TASK_STATES = (
    ("todo", True),
    ("doing", True),
    ("selfcheck", True),
    ("review", True),
    ("blocked", True),
    ("done", False),
    ("dropped", False),
    ("superseded", False),
)


@pytest.mark.parametrize("task_status,owes_action", TASK_STATES)
def test_the_task_state_decides_whether_an_open_pr_is_abandoned(
    task_status: str, owes_action: bool
) -> None:
    record = pr_record(status="open", task="T-0001", role="developer", branch="developer/gone")
    task = {"id": "T-0001", "status": task_status}
    assert engine.task_owes_action(task) == owes_action
    assert engine.pr_is_abandoned(record, task, True) == owes_action


def test_a_pr_whose_branch_still_exists_is_never_abandoned() -> None:
    """The branch is a condition, not a symptom: a live branch is live work."""
    record = pr_record(status="open", task="T-0001", role="developer", branch="developer/live")
    assert engine.pr_is_abandoned(record, {"id": "T-0001", "status": "doing"}, False) is False


def test_a_pr_with_no_resolvable_task_fails_closed() -> None:
    """A missing task record is not evidence that the work landed."""
    record = pr_record(status="open", task="T-9999", role="developer", branch="dev/gone")
    assert engine.task_owes_action(None) is True
    assert engine.pr_is_abandoned(record, None, True) is True


#: The four records the old rule reported, with the values each record really
#: carries on the team tree: id, status, task, role, the task's status in its
#: queue, the record's merge_commit, and the verdict the rule must reach.
RECORDED_PRS = (
    ("P-0010", "approved", "T-0005", "ceo", "done", "f91bf1b"),
    ("P-0022", "changes-requested", "T-0001", "security-auditor", "dropped", ""),
    ("P-0023", "changes-requested", "T-0001", "reviewer", "dropped", ""),
    ("P-0035", "superseded", "T-0013", "developer", "done", "90eb61c"),
)


@pytest.mark.parametrize("handle,status,task,role,task_status,merge_commit", RECORDED_PRS)
def test_each_record_the_old_rule_reported_is_terminal(
    handle: str, status: str, task: str, role: str, task_status: str, merge_commit: str
) -> None:
    """The four measured records, classified from their own fields.

    The values are copied from the team's Reviews.md and each record's own queue,
    so this test fails if a record is relabelled in the product (a state that only
    exists to silence the gate) or if the rule regresses to "not merged": every
    one of these four has a dead branch. The live tree is the real proof and
    ``test_coordination_flags_only_a_live_pr_on_a_dead_branch`` runs the product
    over a real repository; this table is the per-record part of it.
    """
    record = pr_record(
        status=status,
        task=task,
        role=role,
        merge_commit=merge_commit,
        branch=f"{role}/gone-{handle.lower()}",
    )
    task_record = {"id": task, "status": task_status}
    assert engine.pr_is_abandoned(record, task_record, True) is False, (
        f"{handle} is {status} with a {task_status} task, so its branch is gone "
        "because the work ended"
    )


def git(project: Path, *argv: str) -> str:
    """Run git in a throwaway repository, hermetically, and fail loudly."""
    done = subprocess.run(
        ("git", "-C", str(project), *argv),
        capture_output=True,
        text=True,
        env=child_env(**GIT_IDENTITY),
        check=True,
    )
    return done.stdout


def make_git_project(project: Path) -> None:
    """A real repository with one commit: the abandoned check resolves branches."""
    git(project, "init", "-q", "-b", "main")
    (project / "README.md").write_text("a project\n", encoding="utf-8")
    git(project, "add", "--", "README.md")
    git(project, "commit", "-qm", "init")


def test_coordination_flags_only_a_live_pr_on_a_dead_branch(cli, project: Path) -> None:
    """The whole check, over a real repository, against realistic records.

    Three finished records and one live one, all with a branch the repository does
    not have - which is the exact shape that produced four false high findings.
    The pre-fix rule (status != merged) reports two of the three terminal records
    here, so restoring it turns this test red.
    """
    root = init(cli, project)
    make_git_project(project)
    assert cli("--project", project, "task", "add", "developer", "live work") == 0
    assert cli("--project", project, "task", "add", "developer", "landed work") == 0
    assert cli("--project", project, "task", "add", "ceo", "landed records") == 0
    assert cli("--project", project, "task", "add", "reviewer", "withdrawn review") == 0
    edit_task(root, "developer", "T-0001", status="doing")
    edit_task(root, "developer", "T-0002", status="done")
    edit_task(root, "ceo", "T-0001", status="done")
    edit_task(root, "reviewer", "T-0001", status="dropped")

    finished = [
        pr_record(
            title="the work moved to another PR",
            status="superseded",
            task="T-0002",
            role="developer",
            branch="developer/gone-superseded",
        ),
        pr_record(
            title="approved and merged",
            status="approved",
            task="T-0001",
            role="ceo",
            branch="ceo/gone-approved",
            merge_commit="abc1234",
        ),
        pr_record(
            title="the review was withdrawn",
            status="changes-requested",
            task="T-0001",
            role="reviewer",
            branch="reviewer/gone-dropped",
        ),
    ]
    engine.write_reviews(engine.reviews_path(root), finished)
    assert "C-MERGE-ABANDONED" not in codes(engine.coordination_report(root))

    # One genuinely live PR on a branch the repository does not have: the check
    # must still fire, and name only that record.
    live = pr_record(
        title="nobody is coming back for this",
        status="open",
        task="T-0001",
        role="developer",
        branch="developer/gone-live",
    )
    engine.write_reviews(engine.reviews_path(root), [*finished, live])
    found = [
        finding
        for finding in engine.coordination_report(root)["findings"]
        if finding["code"] == "C-MERGE-ABANDONED"
    ]
    assert found, "a live PR on a dead branch is still abandonment"
    assert found[0]["severity"] == "high"
    assert "P-0004" in found[0]["detail"]
    for terminal in ("P-0001", "P-0002", "P-0003"):
        assert terminal not in found[0]["detail"]


def test_a_bare_task_id_resolves_through_the_record_role(cli, project: Path) -> None:
    """Task ids are unique per queue, so the PR record's role decides.

    Two queues carry a T-0001 with different states. Reporting the wrong one
    would make the rule depend on queue iteration order, so the role is used
    first and an ambiguous bare id degrades to ``None`` (which fails closed).
    """
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "live work") == 0
    assert cli("--project", project, "task", "add", "reviewer", "withdrawn review") == 0
    edit_task(root, "developer", "T-0001", status="doing")
    edit_task(root, "reviewer", "T-0001", status="dropped")
    tasks = engine.all_tasks(root)
    index = {(role, task["id"].upper()): task for role, task in tasks}

    resolved = engine._pr_task({"task": "T-0001", "role": "reviewer"}, index)
    assert resolved is not None and resolved["status"] == "dropped"
    assert (
        engine.pr_is_abandoned(
            pr_record(status="open", task="T-0001", role="reviewer", branch="x/gone"),
            resolved,
            True,
        )
        is False
    )

    still_live = engine._pr_task({"task": "T-0001", "role": "developer"}, index)
    assert still_live is not None and still_live["status"] == "doing"
    assert (
        engine.pr_is_abandoned(
            pr_record(status="open", task="T-0001", role="developer", branch="x/gone"),
            still_live,
            True,
        )
        is True
    )

    # No role: the id is ambiguous across the queues, so it does not resolve and
    # the caller fails closed rather than guessing.
    assert engine._pr_task({"task": "T-0001"}, index) is None
