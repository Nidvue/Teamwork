"""Regression tests for the integrity, gate and path fixes from the code audit.

Each test pins a defect that was reproduced before the fix. They are deliberately
end-to-end where the defect crossed the CLI boundary (that is where a forged
value or a lock deadlock actually hurt).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from teamwork import engine

ROSTER = "ceo,developer-1,developer-2,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
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
