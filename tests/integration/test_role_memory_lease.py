"""Integration tests: every role scales, and its shared memory has ONE reviser.

Two rules, exercised through the real CLI on a throwaway workspace:

1. any role can run several instances (`instance add`), and those instances share
   exactly one ``Roles/<Role>/`` memory set and one ``TaskQueue.md`` - adding a
   third architect must not create a second memory file;
2. only one instance of a role may revise that shared memory at a time. The lease
   is explicit (`memory claim` ... several writes ... `memory release`) so a
   coherent update lands whole, and implicit (one `remember`) so two peers still
   serialise instead of interleaving. A peer is read-only meanwhile; reads and
   `recall` always work; an expired lease frees the role.

Owner: tester. Layer: integration. Area: role-memory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from teamwork import engine

AGENTS = ("ceo", "architect-1", "developer-1", "tester-1", "reviewer-1")


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init_team(cli, project: Path) -> Path:
    code = cli("--project", project, "init", "--agents", ",".join(AGENTS), "--no-git")
    assert code == 0, f"init returned {code}"
    root = team_root(project)
    assert root.is_dir()
    return root


def short_memory(root: Path, role: str) -> list:
    """The role's short-term entry bodies, in file order (whitespace-normalised)."""
    entries = engine.parse_memory(root / "Roles" / engine.pascal(role) / "ShortTermMemory.md")
    return [e["body"].strip() for e in entries]


def claim_file(root: Path, role: str) -> Path:
    return engine.memory_claim_path(root, role)


# --------------------------------------------------------------------------- #
# any role scales, and the role's state stays shared
# --------------------------------------------------------------------------- #


def test_any_role_can_add_instances_and_they_share_one_memory(cli, project: Path) -> None:
    root = init_team(cli, project)

    assert cli("--project", project, "instance", "add", "architect", "--count", "2") == 0
    assert engine.instances_of(root, "architect") == [
        "Architect-1",
        "Architect-2",
        "Architect-3",
    ]

    # One memory set and one queue for the role, however many lanes serve it.
    assert (
        cli("--project", project, "remember", "architect", "one fact", "--by", "Architect-3") == 0
    )
    assert cli("--project", project, "remember", "Architect-2", "another fact") == 0
    assert short_memory(root, "architect") == ["one fact", "another fact"]
    assert not (root / "Agents" / "Architect-2" / "ShortTermMemory.md").exists()

    tasks = engine.parse_tasks(root / "Roles" / "Architect" / "TaskQueue.md")
    assert (
        cli("--project", project, "task", "add", "architect", "freeze the API", "--priority", "P0")
        == 0
    )
    tasks = engine.parse_tasks(root / "Roles" / "Architect" / "TaskQueue.md")
    assert len(tasks) == 1
    # Either instance may take the role's next task; the claim names the lane.
    assert cli("--project", project, "task", "next", "Architect-3") == 0
    assert (
        engine.parse_tasks(root / "Roles" / "Architect" / "TaskQueue.md")[0]["claimed_by"]
        == "Architect-3"
    )


def test_a_role_outside_the_roster_needs_an_explicit_opt_in(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "designer") != 0
    assert cli("--project", project, "instance", "add", "designer", "--new-role") == 0
    assert engine.instances_of(root, "designer") == ["Designer"]
    assert (root / "Roles" / "Designer" / "ShortTermMemory.md").is_file()


def test_a_retired_instance_leaves_the_role_memory_in_place(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect", "--count", "2") == 0
    assert (
        cli("--project", project, "remember", "architect", "kept fact", "--by", "Architect-2") == 0
    )

    assert (
        cli("--project", project, "instance", "retire", "Architect-3", "--reason", "trimmed") == 0
    )
    assert not (root / "Agents" / "Architect-3").exists()
    assert short_memory(root, "architect") == ["kept fact"]


def test_an_instance_holding_work_is_not_retired_silently(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0
    assert (
        cli("--project", project, "task", "add", "architect", "in flight", "--priority", "P0") == 0
    )
    assert cli("--project", project, "task", "next", "Architect-2") == 0

    assert cli("--project", project, "instance", "retire", "Architect-2") != 0
    assert (
        cli("--project", project, "instance", "retire", "Architect-2", "--reason", "lane replaced")
        != 0
    )
    assert (
        cli(
            "--project",
            project,
            "instance",
            "retire",
            "Architect-2",
            "--reason",
            "lane replaced",
            "--force",
        )
        == 0
    )
    assert (root / "Agents" / "Architect-2").exists() is False


# --------------------------------------------------------------------------- #
# one reviser per role
# --------------------------------------------------------------------------- #


def test_the_explicit_lease_makes_a_peer_read_only_until_release(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0

    assert (
        cli(
            "--project",
            project,
            "memory",
            "claim",
            "architect",
            "--by",
            "Architect-1",
            "--reason",
            "rewrite the contract",
        )
        == 0
    )
    live = engine.read_memory_claim(root, "architect")
    assert live["instance"] == "Architect-1" and live["explicit"] is True

    # A peer may not revise the shared memory while the pen is out...
    assert cli("--project", project, "remember", "architect", "peer", "--by", "Architect-2") == 2
    assert cli("--project", project, "forget", "architect", "M-0001", "--by", "Architect-2") == 2
    assert (
        cli("--project", project, "consolidate", "--agent", "architect", "--by", "Architect-2") == 2
    )
    assert short_memory(root, "architect") == []

    # ...but it may read, and the holder may write.
    assert cli("--project", project, "load", "Architect-2") == 0
    assert (
        cli("--project", project, "remember", "architect", "owner fact", "--by", "Architect-1") == 0
    )
    assert short_memory(root, "architect") == ["owner fact"]

    assert cli("--project", project, "memory", "release", "architect", "--by", "Architect-2") == 2
    assert cli("--project", project, "memory", "release", "architect", "--by", "Architect-1") == 0
    assert engine.read_memory_claim(root, "architect") == {}
    assert (
        cli("--project", project, "remember", "architect", "peer fact", "--by", "Architect-2") == 0
    )


def test_a_single_write_takes_the_pen_for_its_own_duration_only(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0
    assert cli("--project", project, "remember", "architect", "a", "--by", "Architect-1") == 0
    # The implicit lease dies with the command: no state file left behind.
    assert not claim_file(root, "architect").exists()
    assert cli("--project", project, "remember", "architect", "b", "--by", "Architect-2") == 0
    assert short_memory(root, "architect") == ["a", "b"]


def test_an_expired_lease_frees_the_pen_without_a_release(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0
    assert cli("--project", project, "remember", "architect", "blocked", "--by", "Architect-2") == 2

    path = claim_file(root, "architect")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expires_ts"] = time.time() - 1
    path.write_text(json.dumps(data), encoding="utf-8")

    assert (
        cli("--project", project, "remember", "architect", "took over", "--by", "Architect-2") == 0
    )
    assert short_memory(root, "architect") == ["took over"]


def test_a_stalled_holder_can_be_taken_over_on_the_record(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0

    assert (
        cli(
            "--project",
            project,
            "memory",
            "claim",
            "architect",
            "--by",
            "Architect-2",
            "--force",
            "Architect-1 went silent",
        )
        == 0
    )
    assert engine.read_memory_claim(root, "architect")["instance"] == "Architect-2"
    actions = [r["action"] for r in engine.ledger_read(root)]
    assert "memory.claim.force" in actions and "memory.claim" in actions


def test_the_lease_is_named_per_role_and_cannot_cross_roles(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Developer-1") != 0
    # Different roles never contend: each takes its own pen in parallel.
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0
    assert cli("--project", project, "memory", "claim", "developer", "--by", "Developer-1") == 0
    assert engine.read_memory_claim(root, "architect")["instance"] == "Architect-1"
    assert engine.read_memory_claim(root, "developer")["instance"] == "Developer-1"


def test_memory_status_reports_the_holder_and_the_free_roles(cli, project: Path, capsys) -> None:
    init_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0
    capsys.readouterr()
    assert cli("--project", project, "memory", "status", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    rows = {row["role"]: row for row in payload["roles"]}
    assert rows["architect"]["holder"] == "Architect-1"
    assert rows["developer"]["holder"] == ""
    assert rows["architect"]["minutes_left"] >= 1


def test_the_audit_trail_records_the_scaling_and_the_lease(cli, project: Path) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "instance", "add", "architect") == 0
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-2") == 0
    assert cli("--project", project, "memory", "release", "architect", "--by", "Architect-2") == 0
    assert engine.ledger_verify(root) == []
    actions = [r["action"] for r in engine.ledger_read(root)]
    assert "instance.add" in actions
    assert "memory.claim" in actions and "memory.release" in actions


# --------------------------------------------------------------------------- #
# a long update: a peer contests, the CTO rules
# --------------------------------------------------------------------------- #

ESCALATION_AGENTS = ("ceo", "cto", "architect-1", "architect-2", "developer-1", "reviewer-1")


def init_escalation_team(cli, project: Path) -> Path:
    code = cli("--project", project, "init", "--agents", ",".join(ESCALATION_AGENTS), "--no-git")
    assert code == 0, f"init returned {code}"
    return team_root(project)


def test_a_peer_contests_a_long_lease_and_the_cto_gets_the_case(cli, project: Path) -> None:
    root = init_escalation_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0

    assert (
        cli(
            "--project",
            project,
            "memory",
            "contest",
            "architect",
            "--by",
            "Architect-2",
            "--reason",
            "three tasks are blocked on this update",
        )
        == 0
    )
    # The contest is on the lease the arbiter will read, and on the CTO's queue.
    claim = engine.read_memory_claim(root, "architect")
    assert claim["contests"][-1]["by"] == "Architect-2"
    tasks = engine.parse_tasks(root / "Roles" / "CTO" / "TaskQueue.md")
    assert len(tasks) == 1
    assert tasks[0]["priority"] == "P0" and "architect memory lease" in tasks[0]["title"]
    assert "memory.contest" in [r["action"] for r in engine.ledger_read(root)]

    # Contesting twice does not file a second copy of the same case.
    assert (
        cli(
            "--project",
            project,
            "memory",
            "contest",
            "architect",
            "--by",
            "Architect-2",
            "--reason",
            "still blocked",
        )
        == 0
    )
    assert len(engine.parse_tasks(root / "Roles" / "CTO" / "TaskQueue.md")) == 1


def test_only_the_arbiter_may_extend_or_revoke(cli, project: Path) -> None:
    root = init_escalation_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0

    assert (
        cli(
            "--project",
            project,
            "memory",
            "extend",
            "architect",
            "--by",
            "Architect-2",
            "--ttl",
            "10",
            "--reason",
            "more time",
        )
        == 2
    )
    assert (
        cli(
            "--project",
            project,
            "memory",
            "revoke",
            "architect",
            "--by",
            "Developer-1",
            "--reason",
            "free it",
        )
        == 2
    )
    assert cli("--project", project, "memory", "extend", "architect", "--by", "CTO") == 2
    claim = engine.read_memory_claim(root, "architect")
    assert claim["instance"] == "Architect-1" and engine.memory_claim_remaining(claim) <= 30


def test_the_cto_extends_a_lease_that_needs_more_time(cli, project: Path) -> None:
    root = init_escalation_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0
    assert (
        cli(
            "--project",
            project,
            "memory",
            "contest",
            "architect",
            "--by",
            "Architect-2",
            "--reason",
            "looks stuck",
        )
        == 0
    )

    assert (
        cli(
            "--project",
            project,
            "memory",
            "extend",
            "architect",
            "--by",
            "CTO",
            "--ttl",
            "45",
            "--reason",
            "the contract rewrite is genuinely large",
        )
        == 0
    )
    claim = engine.read_memory_claim(root, "architect")
    assert claim["instance"] == "Architect-1"
    assert engine.memory_claim_remaining(claim) >= 44
    assert claim["contests"] == []
    assert claim["arbitrated_by"] == "CTO"
    assert "memory.grant" in [r["action"] for r in engine.ledger_read(root)]


def test_the_cto_revokes_the_lock_and_the_role_is_free(cli, project: Path) -> None:
    root = init_escalation_team(cli, project)
    assert cli("--project", project, "memory", "claim", "architect", "--by", "Architect-1") == 0
    assert (
        cli(
            "--project",
            project,
            "memory",
            "contest",
            "architect",
            "--by",
            "Architect-2",
            "--reason",
            "looks stuck",
        )
        == 0
    )

    assert (
        cli(
            "--project",
            project,
            "memory",
            "revoke",
            "architect",
            "--by",
            "CTO",
            "--reason",
            "that lane is wedged; free the role",
        )
        == 0
    )
    assert engine.read_memory_claim(root, "architect") == {}
    assert (
        cli("--project", project, "remember", "architect", "peer fact", "--by", "Architect-2") == 0
    )
    assert short_memory(root, "architect") == ["peer fact"]
    assert "memory.revoke" in [r["action"] for r in engine.ledger_read(root)]


def test_the_arbiter_folds_to_the_ceo_when_the_cto_holds_the_lease(cli, project: Path) -> None:
    root = init_escalation_team(cli, project)
    assert cli("--project", project, "instance", "add", "cto") == 0
    assert cli("--project", project, "memory", "claim", "cto", "--by", "CTO") == 0
    assert (
        cli(
            "--project",
            project,
            "memory",
            "contest",
            "cto",
            "--by",
            "CTO-2",
            "--reason",
            "the policy rewrite is wedged",
        )
        == 0
    )

    # No party rules its own lease: the CTO's case goes to the CEO.
    assert (
        cli(
            "--project",
            project,
            "memory",
            "extend",
            "cto",
            "--by",
            "CTO",
            "--ttl",
            "10",
            "--reason",
            "self",
        )
        == 2
    )
    assert (
        cli(
            "--project",
            project,
            "memory",
            "extend",
            "cto",
            "--by",
            "CEO",
            "--ttl",
            "40",
            "--reason",
            "a large policy rewrite",
        )
        == 0
    )
    assert engine.read_memory_claim(root, "cto")["arbitrated_by"] == "CEO"


def test_a_role_with_no_arbiter_is_told_to_open_a_dispute(cli, project: Path) -> None:
    """A CEO lease contested on a roster with no CTO: nobody above may rule it."""
    root = team_root(project)
    assert cli("--project", project, "init", "--agents", "ceo,ceo-2,architect-1", "--no-git") == 0
    root = team_root(project)
    assert cli("--project", project, "memory", "claim", "ceo", "--by", "CEO") == 0
    assert (
        cli("--project", project, "memory", "contest", "ceo", "--by", "CEO-2", "--reason", "wedged")
        == 2
    )
    assert engine.read_memory_claim(root, "ceo")["instance"] == "CEO"
