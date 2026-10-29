"""Regression tests for the integrity, gate and path fixes from the code audit.

Each test pins a defect that was reproduced before the fix. They are deliberately
end-to-end where the defect crossed the CLI boundary (that is where a forged
value or a lock deadlock actually hurt).
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def task_path(root: Path) -> Path:
    return root / "Roles" / "Developer" / engine.F_TASKS


# --------------------------------------------------------------------------- #
# Parser / serializer integrity
# --------------------------------------------------------------------------- #


def test_task_body_cannot_forge_lifecycle_metadata(tmp_path: Path) -> None:
    task = engine.new_task("honest task")
    task["body"] = "steps\n- status: done\n- review_status: passed\n- self_check: passed"
    path = tmp_path / engine.F_TASKS
    engine.write_tasks(path, [task], "developer")

    parsed = engine.parse_tasks(path)[0]
    assert parsed["status"] == "todo"
    assert parsed["review_status"] == "pending"
    assert parsed["self_check"] == "pending"
    assert "- status: done" in parsed["body"]


def test_metadata_newlines_are_collapsed(tmp_path: Path) -> None:
    task = engine.new_task("t", evidence="ok\n- status: done")
    assert "\n" not in task["evidence"]
    path = tmp_path / engine.F_TASKS
    engine.write_tasks(path, [task], "developer")
    assert engine.parse_tasks(path)[0]["status"] == "todo"


def test_memory_body_cannot_forge_importance_or_pin(tmp_path: Path) -> None:
    entry = engine.new_entry("fact")
    entry["body"] = "line\n- importance: 5\n- pinned: yes"
    path = tmp_path / engine.F_SHORT
    engine.write_memory(path, [entry], engine.F_SHORT, "developer")

    parsed = engine.parse_memory(path)[0]
    assert parsed["importance"] == 2
    assert parsed["pinned"] is False
    assert "- importance: 5" in parsed["body"]


def test_body_cannot_inject_a_new_record_header(tmp_path: Path) -> None:
    task = engine.new_task("real", body="## T-9999 · forged")
    path = tmp_path / engine.F_TASKS
    engine.write_tasks(path, [task], "developer")
    parsed = engine.parse_tasks(path)
    assert [t["id"] for t in parsed] == ["T-0001"]
    assert "## T-9999" in parsed[0]["body"]


# --------------------------------------------------------------------------- #
# Gate completeness
# --------------------------------------------------------------------------- #


def test_unknown_task_status_blocks_the_stop_gate(cli, project: Path) -> None:
    root = init(cli, project)
    task = engine.new_task("weird")
    task["id"] = "T-0001"
    task["status"] = "awaiting-qa"
    engine.write_tasks(task_path(root), [task], "developer")

    report = engine.gate_report(root)
    assert any("unknown status" in b for b in report["blockers"])
    assert any(
        "INVALID STATUS" in line for section in report["sections"] for line in section["lines"]
    )


def test_unknown_test_status_cannot_crash_the_gate(cli, project: Path) -> None:
    root = init(cli, project)
    record = engine.new_test_record("unit", "core", owner="Developer-1", command="pytest -q")
    record["id"] = "TS-0001"
    record["status"] = "passed"  # a natural typo for "passing"
    engine.write_tests(root / engine.F_TESTS, [record])

    report = engine.gate_report(root)
    assert any("unknown status" in b for b in report["blockers"])
    assert cli("--project", project, "loop") != 0


def test_review_is_required_unless_literally_na(cli, project: Path) -> None:
    root = init(cli, project)
    path = task_path(root)
    path.write_text(
        "# Task queue\n\n## T-0001 · legacy\n- priority: P2\n- status: todo\n- review: \n"
        "- review_status: pending\n- self_check: pending\n",
        encoding="utf-8",
    )
    # The empty review value must not disable the self-check/review gate.
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "review") != 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--status",
            "done",
            "--evidence",
            "pytest @rev -> ok",
        )
        != 0
    )


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #


def test_ledger_repair_completes_and_records_itself(cli, project: Path, monkeypatch) -> None:
    root = init(cli, project)
    monkeypatch.setattr(engine, "LOCK_TIMEOUT", 2.0)
    with (root / engine.F_LEDGER).open("a", encoding="utf-8") as fh:
        fh.write("{ torn tail\n")

    assert (
        cli("--project", project, "ledger", "repair", "--by", "ceo", "--reason", "torn tail") == 0
    )
    assert engine.ledger_verify(root) == []
    actions = [r["action"] for r in engine.ledger_read(root)]
    assert "ledger.repair" in actions


def test_ledger_append_trims_a_torn_tail_before_writing(cli, project: Path) -> None:
    root = init(cli, project)
    with (root / engine.F_LEDGER).open("a", encoding="utf-8") as fh:
        fh.write('{"torn": ')

    engine.ledger_append(root, "audit.test", "ceo", "x", "after crash")
    assert engine.ledger_verify(root) == []
    assert engine.ledger_read(root)[-1]["action"] == "audit.test"


def test_corrupt_ledger_line_does_not_crash_show(cli, project: Path) -> None:
    root = init(cli, project)
    with (root / engine.F_LEDGER).open("a", encoding="utf-8") as fh:
        fh.write("[]\n")

    assert cli("--project", project, "ledger", "show") == 0
    assert cli("--project", project, "ledger", "verify") == 1


# --------------------------------------------------------------------------- #
# Path safety and ownership
# --------------------------------------------------------------------------- #


def test_agent_name_cannot_escape_the_team_tree(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", "ceo,../../escape", "--no-git") == 0
    root = team_root(project)
    escaped = engine.agent_dir(root, "../../escape")
    assert escaped.parent == root / "Agents"
    assert not (project.parent / "escape").exists()


def test_slot_names_cannot_escape_the_slot_tree(cli, project: Path) -> None:
    root = init(cli, project)
    path = engine.slot_file(root, "../../provider", "../../agent")
    assert path.parent.parent == root / "Runtime" / "Slots"


def test_task_set_applies_claimed_by(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "build it") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--claimed-by",
            "developer-2",
        )
        == 0
    )
    assert engine.parse_tasks(task_path(root))[0]["claimed_by"] == "developer-2"


def test_task_add_rejects_a_claimant_from_another_role(cli, project: Path) -> None:
    init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "wrong owner",
            "--claimed-by",
            "tester-1",
        )
        != 0
    )


def test_selfcheck_rejects_an_actor_from_another_role(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "owned work") == 0
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "tester-1",
            "--note",
            "not mine",
            "--test",
            "true @rev -> ok",
        )
        != 0
    )
    assert engine.parse_tasks(task_path(root))[0]["claimed_by"] == ""


# --------------------------------------------------------------------------- #
# Records and routing
# --------------------------------------------------------------------------- #


def test_decision_ids_are_unique_per_day_and_actor(cli, project: Path) -> None:
    root = init(cli, project)
    for text in ("first", "second"):
        assert (
            cli(
                "--project",
                project,
                "decision",
                "add",
                "--by",
                "ceo",
                "--decision",
                text,
                "--evidence",
                "pytest @rev -> ok",
            )
            == 0
        )
    body = (root.parents[3] / "docs" / "Team" / "Decisions.md").read_text(encoding="utf-8")
    ids = [line.split(" ", 2)[1] for line in body.splitlines() if line.startswith("## D-")]
    assert len(ids) == len(set(ids))
    today = engine.today_iso().replace("-", "")
    assert len([i for i in ids if today in i]) == 2


def test_model_set_on_a_hyphenated_role_uses_the_role_map(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "model",
            "set",
            "product-manager",
            "--provider",
            "p",
            "--model",
            "m",
        )
        == 0
    )
    config = engine.load_model_config(root)
    assert "product-manager" in config["roles"]
    assert "product-manager" not in config["agents"]
    assert engine.resolved_model(root, "product-manager-1")["model"] == "m"


# --------------------------------------------------------------------------- #
# Staleness, consolidation, audit and links
# --------------------------------------------------------------------------- #


def test_a_task_claimed_today_is_not_stale(cli, project: Path) -> None:
    root = init(cli, project)
    task = engine.new_task("fresh", status="doing")
    task["id"] = "T-0001"
    task["claimed_by"] = "developer-1"
    engine.write_tasks(task_path(root), [task], "developer")
    assert engine.stale_claims(root) == []


def test_consolidate_does_not_crash_on_archive_overflow(cli, project: Path, monkeypatch) -> None:
    root = init(cli, project)
    monkeypatch.setattr(engine, "LONG_CAP", 2)
    monkeypatch.setattr(engine, "SHORT_CAP", 2)
    monkeypatch.setattr(engine, "ARCHIVE_CAP", 2)
    path = root / "Roles" / "Developer" / engine.F_LONG
    entries = [engine.new_entry(f"fact {i}", key=f"k{i}", importance=3) for i in range(6)]
    engine.write_memory(path, entries, engine.F_LONG, "developer")

    report = engine.consolidate_agent(root, "developer", quiet=True)
    assert report["evicted"] == 4
    assert (root / "Roles" / "Developer" / engine.F_MEM_ARCHIVE).exists()


def test_audit_reports_stale_in_progress_work(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    task = engine.new_task("stalled", status="doing")
    task["id"] = "T-0001"
    task["claimed_by"] = "developer-1"
    task["updated"] = "2020-01-01"
    engine.write_tasks(task_path(root), [task], "developer")

    hits = engine._audit_stale_in_progress(root, ["developer"], SimpleNamespace(stale_days=2))
    assert hits == 1
    assert "stalled" in capsys.readouterr().out


def test_links_skips_local_state_and_detects_bare_urls(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "[site](https://example.org) and https://example.org\n", encoding="utf-8"
    )
    local = tmp_path / ".pi" / "Teamwork" / "Teams" / "X"
    local.mkdir(parents=True)
    (local / "Notes.md").write_text("[broken](missing.md)\n", encoding="utf-8")

    report = engine.link_report(tmp_path, tmp_path)
    assert all(not path.startswith(".pi/") for path in report["files"])
    assert report["bare"] == [("README.md", "https://example.org")]


# --------------------------------------------------------------------------- #
# Review and PR gates
# --------------------------------------------------------------------------- #


def test_review_refuses_before_the_author_self_checks(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "deliverable") == 0
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest @rev -> ok",
        )
        != 0
    )


def test_review_refuses_an_author_as_reviewer(cli, project: Path) -> None:
    root = init(cli, project)
    task = engine.new_task("self review")
    task["id"] = "T-0001"
    task["status"] = "review"
    task["claimed_by"] = "Reviewer-1"
    task["self_check"] = "passed"
    engine.write_tasks(task_path(root), [task], "developer")
    assert (
        cli(
            "--project",
            project,
            "review",
            "developer",
            "T-0001",
            "--by",
            "reviewer-1",
            "--result",
            "pass",
            "--evidence",
            "pytest @rev -> ok",
        )
        != 0
    )


def test_pr_open_rejects_an_unknown_agent(cli, project: Path) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "deliverable") == 0
    assert (
        cli(
            "--project",
            project,
            "pr",
            "open",
            "--agent",
            "ghost-9",
            "--task",
            "T-0001",
        )
        != 0
    )


def test_a_staffed_role_without_tests_blocks_stop(cli, project: Path) -> None:
    root = init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "tests",
            "add",
            "--layer",
            "unit",
            "--area",
            "core",
        )
        == 0
    )
    report = engine.gate_report(root)
    assert any("have not designed or run any test" in b for b in report["blockers"])


def test_init_force_preserves_records_and_team_documents(cli, project: Path) -> None:
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "keep me") == 0
    assert cli("--project", project, "global", "shared fact", "--key", "fact") == 0
    project_doc = (root.parents[3] / "docs" / "Team" / "Project.md").read_text(encoding="utf-8")

    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git", "--force") == 0
    assert engine.parse_tasks(task_path(root))[0]["title"] == "keep me"
    assert engine.parse_memory(root / "Global" / engine.F_GLOBAL)[0]["key"] == "fact"
    assert (root.parents[3] / "docs" / "Team" / "Project.md").read_text(
        encoding="utf-8"
    ) == project_doc


def test_repo_bootstrap_sets_a_role_local_git_identity(tmp_path: Path) -> None:
    project = tmp_path / "repo-bootstrap"
    project.mkdir()
    engine.ensure_repo(project, commit=False, quiet=True)
    assert engine.run_git(project, "config", "--local", "user.email").stdout.strip() == (
        "ceo@agents.nidvue.com"
    )
    assert engine.run_git(project, "config", "--local", "user.name").stdout.strip() == "CEO"


def test_repo_bootstrap_never_overwrites_an_existing_local_identity(tmp_path: Path) -> None:
    project = tmp_path / "repo-existing-identity"
    project.mkdir()
    engine.run_git(project, "init", "-q", "-b", "main")
    engine.run_git(project, "config", "--local", "user.name", "Ops Person")
    engine.run_git(project, "config", "--local", "user.email", "ops@example.com")
    engine.ensure_repo(project, commit=False, quiet=True)
    assert engine.run_git(project, "config", "--local", "user.name").stdout.strip() == "Ops Person"
    assert engine.run_git(project, "config", "--local", "user.email").stdout.strip() == (
        "ops@example.com"
    )


def test_repo_bootstrap_preserves_a_name_only_local_identity(tmp_path: Path) -> None:
    project = tmp_path / "repo-name-only"
    project.mkdir()
    engine.run_git(project, "init", "-q", "-b", "main")
    engine.run_git(project, "config", "--local", "user.name", "Ops Person")
    engine.ensure_repo(project, commit=False, quiet=True)
    assert engine.run_git(project, "config", "--local", "user.name").stdout.strip() == "Ops Person"
    assert engine.run_git(project, "config", "--local", "user.email").stdout.strip() == (
        "ceo@agents.nidvue.com"
    )


def test_dispute_sign_by_a_non_tribunal_role_fails_cleanly(cli, project: Path) -> None:
    init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            "developer-1",
            "--against",
            "tester-1",
            "--topic",
            "boundary",
            "--evidence",
            "pytest @rev -> ok",
        )
        == 0
    )
    assert cli("--project", project, "dispute", "escalate", "D-0001", "--by", "developer-1") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "developer-1") != 0
    # The point of this test is that a NON-tribunal role is refused at both steps.
    # The roster staffs a reviewer, so the panel is ceo+reviewer and BOTH must sign.
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0
    assert (
        cli("--project", project, "dispute", "resolve", "D-0001", "--by", "ceo", "--decision", "d")
        == 0
    )


@pytest.mark.skipif(os.name == "nt", reason="Windows chmod only toggles the read-only bit")
def test_atomic_write_respects_the_umask(tmp_path: Path) -> None:
    old = os.umask(0o077)
    try:
        path = tmp_path / "private.md"
        engine.atomic_write(path, "x\n")
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        os.umask(old)


def test_repo_bootstrap_does_not_rewrite_a_parent_repo_identity(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    outer.mkdir()
    engine.run_git(outer, "init", "-q", "-b", "main")
    engine.run_git(outer, "config", "--local", "user.name", "Ops Person")
    engine.run_git(outer, "config", "--local", "user.email", "ops@example.com")
    nested = outer / "nested-project"
    nested.mkdir()
    engine.ensure_repo(nested, commit=False, quiet=True)
    assert engine.run_git(outer, "config", "--local", "user.email").stdout.strip() == (
        "ops@example.com"
    )


def test_a_slim_roster_never_leaves_the_tribunal_at_one_member(cli, project: Path) -> None:
    """No CTO/CFO means the CEO alone, so the Reviewer is added as the neutral seat."""
    init(cli, project)
    root = team_root(project)
    assert engine.instances_of(root, "cto") == []
    assert engine.instances_of(root, "cfo") == []
    assert engine.required_tribunal(root) == ["ceo", "reviewer"]
    assert len(engine.required_tribunal(root)) >= engine.TRIBUNAL_MIN_SIGNERS


def _open_and_escalate(cli, project: Path, raiser: str, against: str) -> None:
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            raiser,
            "--against",
            against,
            "--topic",
            "scope",
            "--position",
            "p",
            "--evidence",
            "e",
        )
        == 0
    )
    assert cli("--project", project, "dispute", "escalate", "D-0001", "--by", raiser) == 0


def test_a_party_to_a_dispute_cannot_rule_it(cli, project: Path) -> None:
    """The defect: on a slim roster the CEO was both the only party and the panel.

    The panel is completed FIRST, so the assertion cannot be satisfied by the
    pre-existing "members must sign" guard: with a full panel, the only thing
    standing between the CEO and their own ruling is the party rule itself.
    """
    init(cli, project)
    _open_and_escalate(cli, project, "ceo", "developer-1")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "ceo",
            "--decision",
            "I rule for myself",
        )
        != 0
    ), "a complete panel still let the CEO rule their own dispute"
    # The same complete panel does rule, through the neutral member.
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "reviewer-1",
            "--decision",
            "neutral ruling",
        )
        == 0
    )


def test_the_neutral_signer_can_resolve_a_dispute_between_two_panel_roles(
    cli, project: Path
) -> None:
    """A CEO-vs-CTO dispute must be resolvable by the Reviewer, not deadlocked.

    The resolve gate used the staffed-roles list (ceo, cto, cfo), which drops the
    Reviewer; signing used the disputed panel (reviewer), which drops the parties.
    So the Reviewer could sign and then be refused the ruling, and both parties
    were refused as parties: unreachable without --force.
    """
    init(cli, project, agents="ceo,cto,developer-1,tester-1,reviewer-1,reviewer-2")
    _open_and_escalate(cli, project, "ceo", "cto")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    # Both parties are refused.
    for party in ("ceo", "cto"):
        assert (
            cli(
                "--project",
                project,
                "dispute",
                "resolve",
                "D-0001",
                "--by",
                party,
                "--decision",
                "I rule for my own side",
            )
            != 0
        ), f"{party} ruled a dispute it is a party to"
    # The neutral signer that signing accepted can also rule.
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "reviewer-1",
            "--decision",
            "neutral ruling",
        )
        == 0
    )


def test_a_party_cannot_bypass_the_rule_with_a_blank_reason(cli, project: Path) -> None:
    init(cli, project)
    _open_and_escalate(cli, project, "ceo", "developer-1")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "ceo",
            "--decision",
            "own",
            "--force",
            " ",
        )
        != 0
    )


def test_a_one_member_panel_warns_instead_of_deadlocking(cli, project: Path) -> None:
    """T-0037 F1: an invented signer deadlocked every escalated dispute.

    With no reviewer, no CTO and no CFO staffed there is nothing to add, so the
    panel stays at one and the ruling is allowed - but it must say so rather than
    reporting a complete tribunal.
    """
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,tester-1", "--no-git") == 0
    )
    root = team_root(project)
    assert engine.required_tribunal(root) == ["ceo"]
    _open_and_escalate(cli, project, "developer-1", "tester-1")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0
    assert (
        cli("--project", project, "dispute", "resolve", "D-0001", "--by", "ceo", "--decision", "x")
        == 0
    ), "a one-member panel must not deadlock the dispute"


def test_a_signer_who_is_not_on_the_panel_is_refused(cli, project: Path) -> None:
    """The panel must never contain a role with no instance (the F1 phantom signer)."""
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,tester-1", "--no-git") == 0
    )
    _open_and_escalate(cli, project, "developer-1", "tester-1")
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "sign",
            "D-0001",
            "--by",
            "independent-arbiter",
        )
        != 0
    )


def test_a_neutral_signer_unblocks_the_ruling(cli, project: Path) -> None:
    init(cli, project)
    _open_and_escalate(cli, project, "ceo", "developer-1")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "reviewer-1",
            "--decision",
            "neutral ruling",
        )
        == 0
    )


def test_a_finished_task_override_does_not_hold_the_stop_gate(cli, project: Path) -> None:
    """A forced override explains how a task closed; it is not a live blocker.

    Counting overrides on finished tasks made the stop condition unreachable: the
    audit trail is append-only, so every past override would block STOP forever.
    """
    root = init(cli, project)
    stale = engine.new_task("closed with an override")
    stale["id"] = "T-0001"
    stale["status"] = "done"
    stale["forced"] = "closed past the evidence gate for a measured reason"
    engine.write_tasks(task_path(root), [stale], "developer")
    assert not any("gate override" in b for b in engine.gate_report(root)["blockers"])

    live = engine.new_task("still open with an override")
    live["id"] = "T-0002"
    live["status"] = "review"
    live["forced"] = "open past the evidence gate for a measured reason"
    engine.write_tasks(task_path(root), [stale, live], "developer")
    blockers = engine.gate_report(root)["blockers"]
    assert any("gate override" in b for b in blockers), blockers


def test_a_slot_command_refuses_a_root_that_is_not_a_workspace(
    cli, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mis-set TEAMWORK_ROOT must not create working state in the project root.

    The lock dir is created on demand by ``lock()``, so a slot command pointed at a
    bare directory writes ``Runtime/Locks`` there - committed-tree debris that
    ``git status`` cannot see because the directory starts empty.
    """
    bare = project / "not-a-workspace"
    bare.mkdir()
    monkeypatch.setenv("TEAMWORK_ROOT", str(bare))
    assert cli("--project", project, "slot", "acquire", "--agent", "ceo") != 0
    assert not (bare / engine.DIR_RUNTIME).exists(), "no working state may be written there"


def test_links_scans_a_worktree_that_lives_under_a_dot_pi_directory(
    tmp_path: Path,
) -> None:
    """A per-instance worktree sits at <.pi>/Teamwork/Teams/<T>/Runtime/Worktrees/<I>.

    ``iter_markdown`` skipped a file when *any* part of its absolute path was a
    skip directory, so every document in a worktree matched ``.pi`` and the check
    reported zero files while exiting 0 - the lane's own links were never checked.
    """
    worktree = tmp_path / ".pi" / "Teamwork" / "Teams" / "X" / "Runtime" / "Worktrees" / "Dev"
    worktree.mkdir(parents=True)
    (worktree / "README.md").write_text("[gone](missing.md)\n", encoding="utf-8")
    inner = worktree / ".pi" / "Scratch"
    inner.mkdir(parents=True)
    (inner / "Note.md").write_text("[also gone](missing2.md)\n", encoding="utf-8")

    report = engine.link_report(worktree, worktree)

    assert report["files"] == ["README.md"], "a worktree document must be scanned"
    assert [entry[0] for entry in report["broken"]] == ["README.md"]
    assert all("Scratch" not in path for path in report["files"]), (
        "the worktree's own .pi/ state is still skipped"
    )


def test_links_command_measures_the_worktree_it_runs_in(cli, project: Path, capsys) -> None:
    """`links` must answer for the tree under the caller, not the main checkout.

    It used ``project_of(root)``, the project that owns the team tree, so a lane
    running it inside its own worktree silently measured main and passed while
    its own document held a broken link.
    """
    init(cli, project)
    worktree = team_root(project) / engine.DIR_RUNTIME / engine.DIR_WORKTREES / "Dev"
    worktree.mkdir(parents=True)
    # work_repo() recognises one of our worktrees by its .git entry.
    (worktree / ".git").mkdir()
    (worktree / "README.md").write_text("[gone](missing.md)\n", encoding="utf-8")

    cwd = Path.cwd()
    os.chdir(worktree)
    try:
        code = cli("--project", project, "links")
    finally:
        os.chdir(cwd)

    out = capsys.readouterr().out
    assert f"# Link check ({worktree.resolve()})" in out
    assert "README.md: [gone](missing.md) - target does not exist" in out
    assert code == 1, "the worktree's broken link must fail the check"


def test_audit_link_health_measures_the_tree_under_the_caller(cli, project: Path, capsys) -> None:
    """`audit` had the same blind spot `links` had: it asked project_of(root).

    Run inside a worktree, the link-health section reported "- none" whatever the
    lane's own documents said, so a broken doc link could reach review unseen.
    """
    root = init(cli, project)
    worktree = team_root(project) / engine.DIR_RUNTIME / engine.DIR_WORKTREES / "Dev"
    worktree.mkdir(parents=True)
    (worktree / ".git").mkdir()
    (worktree / "README.md").write_text("[gone](missing.md)\n", encoding="utf-8")

    cwd = Path.cwd()
    os.chdir(worktree)
    try:
        engine._audit_markdown_link_health_broken_malformed_ba(root, [], None)
    finally:
        os.chdir(cwd)

    out = capsys.readouterr().out
    assert "- none" not in out, "a broken link in the worktree must be counted"
    assert "issue(s); run `teamwork.py links` for the list" in out


# --------------------------------------------------------------------------- #
# TEAMWORK_ROOT: a validated shape, never `IndexError: 3`
# --------------------------------------------------------------------------- #


def test_a_shallow_teamwork_root_dies_with_one_readable_line(
    cli, project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """`TEAMWORK_ROOT` was taken verbatim and `project_of` indexed `parents[3]`.

    A root one level too shallow therefore raised ``IndexError: 3`` and the CLI
    printed an integer where it promises one readable line - for links and map,
    and for every other subcommand that resolves the project.
    """
    shallow = Path(project.anchor) / "abc"
    assert len(shallow.parents) < 4, f"the fixture is not shallow enough: {shallow}"

    monkeypatch.setenv("TEAMWORK_ROOT", str(shallow))
    for argv in (("links",), ("map",), ("pr", "list"), ("ledger", "verify"), ("branch", "list")):
        assert cli(*argv) == 1, argv
        err = capsys.readouterr().err
        assert "TEAMWORK_ROOT must point at <project>/.pi/Teamwork/Teams/<Team>" in err, argv
        assert "IndexError" not in err and "Traceback" not in err, argv


def test_a_properly_shaped_teamwork_root_still_resolves_the_project(
    cli, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The validation must not reject the layout it documents."""
    root = init(cli, project)
    monkeypatch.setenv("TEAMWORK_ROOT", str(root))
    assert engine.project_of(root) == project.resolve()
    assert engine.docs_dir(root) == project.resolve().joinpath(*engine.DIR_DOCS)
