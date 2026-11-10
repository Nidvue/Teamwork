"""The per-instance team attachment, the claim scoping and the merge-path gate.

`instance add <role> --under <team-leader>` writes one private file,
`Agents/<Instance>/Team.md`, and never a reporting line: the *line* is
`ROLE_PARENT`, the attachment is not a line, so `map` does not change and the
reporting tree keeps one parent per role. It is what makes "one manager at a
time" true by construction - `instance add` refuses a name that exists, so no
command can write a second `under:`.

`task next` and `pulse` then refuse a squad instance another team's work: a task
carrying `feature: F-nnnn` is executable by an instance iff the record's owner is
that instance or its `Team.md` names that owner, **and** the feature is `active`.
A `ready` feature's tasks are queued and held.

Owner: team-leader. Task: T-0042. Requirements: Architecture.md 13.2.
"""

from __future__ import annotations

from pathlib import Path

from test_pr_merge_base_advance import (
    add_task,
    commit_self_check_and_open,
    init_workspace,
    team_root,
)

from teamwork import engine

AGENTS = "ceo,architect-1,team-leader-1,team-leader-2,developer-1,developer-2,tester-1,reviewer-1"


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def team_file(root: Path, instance: str) -> Path:
    return root / engine.DIR_AGENTS / instance / engine.F_TEAM


def team_md(cli, project: Path, *extra: str) -> int:
    return cli("--project", project, "instance", "add", *extra)


def seed_records(project: Path, *records: dict) -> None:
    records = list(records)
    for n, record in enumerate(records, start=1):
        record.setdefault("id", f"F-{n:04d}")
        record.setdefault("created", engine.today_iso())
        record.setdefault("updated", engine.today_iso())
    path = project / "docs" / "Team" / "Features.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    engine.write_features(path, records)


def slice_(
    owner: str = "Team-Leader-1",
    paths=("src/a.py",),
    state: str = "active",
    interface: str = "Architecture.md#13",
    statement: str = "",
) -> dict:
    return engine.new_feature(
        statement or f"the slice of {owner}", owner, list(paths), interface, [], state
    )


# --------------------------------------------------------------------------- #
# 13.2 the attachment
# --------------------------------------------------------------------------- #


def test_a_squad_instance_is_attached_by_one_private_file(cli, project, capsys) -> None:
    root = init(cli, project)
    capsys.readouterr()
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    body = team_file(root, "Developer-3").read_text(encoding="utf-8")

    assert body.startswith("# Team - Developer-3 (developer)\n")
    assert "- under: Team-Leader-1 (team-leader)\n" in body
    assert f"- since: {engine.today_iso()}\n" in body
    assert body.count("- under:") == 1


def test_the_attachment_is_not_a_reporting_line(cli, project) -> None:
    """`ROLE_PARENT` is the tree; the attachment is a fact about one instance."""
    before = dict(engine.ROLE_PARENT)
    root = init(cli, project)
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    assert engine.ROLE_PARENT == before
    assert engine.instance_under(root, "Developer-3") == "Team-Leader-1"


def test_instance_list_shows_the_attachment_beside_the_instance(cli, project, capsys) -> None:
    root = init(cli, project)
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "instance", "list") == 0
    out = capsys.readouterr().out

    assert "Developer-3 (under=Team-Leader-1)" in out
    assert "Developer-1," in out and "Developer-1 (under" not in out
    assert team_file(root, "Developer-1").exists() is False


def test_reattaching_is_impossible_because_the_name_exists(cli, project, capsys) -> None:
    """Moving a specialist is retire + add, which leaves the move in the ledger."""
    root = init(cli, project)
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    capsys.readouterr()
    code = team_md(cli, project, "developer", "--under", "team-leader-2", "--name", "developer-3")

    assert code == 2
    assert "instance 'Developer-3' already exists" in capsys.readouterr().err
    assert engine.instance_under(root, "Developer-3") == "Team-Leader-1"


def test_the_security_auditor_is_never_attachable(cli, project, capsys) -> None:
    """It audits the lane above and the team it would be attached to."""
    init(cli, project)
    capsys.readouterr()
    code = team_md(cli, project, "security-auditor", "--under", "team-leader-1", "--new-role")

    assert code == 2
    assert "the Security Auditor audits the lane above" in capsys.readouterr().err


def test_a_shared_service_is_never_attached(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = team_md(cli, project, "architect", "--under", "team-leader-1", "--name", "architect-2")

    assert code == 2
    assert "the Architect holds a standard that spans teams" in capsys.readouterr().err


def test_a_team_leader_is_never_attached_under_a_team_leader(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = team_md(cli, project, "team-leader", "--under", "team-leader-1")

    assert code == 2
    assert "a team-leader's only manager is the CTO" in capsys.readouterr().err


def test_under_must_name_a_team_leader_instance(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert (
        team_md(cli, project, "developer", "--under", "developer-1", "--name", "developer-3") == 2
    )
    assert (
        "--under must name a team-leader instance: 'developer-1' is a developer"
        in capsys.readouterr().err
    )

    assert (
        team_md(cli, project, "developer", "--under", "team-leader-9", "--name", "developer-3") == 2
    )
    assert (
        "--under must name an existing team-leader instance: 'team-leader-9' has no "
        "instance in this team" in capsys.readouterr().err
    )


# --------------------------------------------------------------------------- #
# 13.2 the claim scoping
# --------------------------------------------------------------------------- #


def test_a_squad_instance_takes_its_own_teams_task(cli, project, capsys) -> None:
    root = init(cli, project)
    seed_records(project, slice_("Team-Leader-1"))
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "next", "developer-3") == 0
    assert "T-0001 [P2] the work" in capsys.readouterr().out
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / engine.F_TASKS)
    assert engine.pascal(tasks[0]["claimed_by"]) == "Developer-3"


def test_another_teams_instance_is_refused_and_shown_why(cli, project, capsys) -> None:
    init(cli, project)
    seed_records(project, slice_("Team-Leader-1"))
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    capsys.readouterr()

    code = cli("--project", project, "task", "next", "developer-1")
    out = capsys.readouterr().out

    assert code == 3
    assert "teamwork: developer-1 (developer) has no executable task of its own team" in out
    assert "  (1 ready in the queue, 1 held by another team)" in out
    assert "  - T-0001 [P2] feature=F-0001 owner=Team-Leader-1" in out


def test_a_ready_features_tasks_are_queued_and_held(cli, project, capsys) -> None:
    """Execution is gated one state later than creation (13.2)."""
    init(cli, project)
    seed_records(project, slice_("Team-Leader-1", state="ready"))
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "next", "developer-3") == 3
    assert "has no executable task of its own team" in capsys.readouterr().out


def test_an_unsliced_task_belongs_to_no_team(cli, project, capsys) -> None:
    init(cli, project)
    seed_records(project, slice_("Team-Leader-1"))
    assert cli("--project", project, "task", "add", "developer", "a preflight repair") == 0
    capsys.readouterr()

    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert "a preflight repair" in capsys.readouterr().out


def test_a_task_cannot_be_sliced_to_a_feature_that_is_not_open(cli, project, capsys) -> None:
    init(cli, project)
    seed_records(project, slice_("Team-Leader-1", state="proposed"))
    capsys.readouterr()
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 2
    )
    assert "F-0001 is [proposed]: a task needs a ready or active feature" in capsys.readouterr().err

    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0009")
        == 2
    )
    assert "unknown feature F-0009" in capsys.readouterr().err


def test_pulse_prints_the_team_lines_and_the_shared_services_once(cli, project, capsys) -> None:
    init(cli, project)
    seed_records(
        project,
        slice_("Team-Leader-1", state="active", interface="-", statement="one slice"),
        slice_("Team-Leader-2", state="ready", interface="Architecture.md#13", statement="another"),
    )
    assert (
        team_md(cli, project, "developer", "--under", "team-leader-1", "--name", "developer-3") == 0
    )
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "pulse") == 0
    out = capsys.readouterr().out

    assert "## feature teams (2)" in out
    assert "- F-0001 [active] Team-Leader-1: squad=Developer-3  ready=1 doing=0" in out
    assert "- F-0002 [ready] Team-Leader-2: squad=-  ready=0 doing=0" in out
    assert (
        "# shared services: architect 1 lane(s), 1 feature(s) waiting on an interface freeze" in out
    )
    assert out.count("# shared services:") == 1


# --------------------------------------------------------------------------- #
# 13.1 the merge path: a pass and a merge both refuse the tree that would land
# --------------------------------------------------------------------------- #


def _ship(cli, project: Path) -> None:
    """One developer task through branch, commit, self-check and an open PR."""
    init_workspace(cli, project)
    work = Path(add_task(cli, project, "ship the slice", "feature.txt"))
    commit_self_check_and_open(cli, project, work=work, filename="feature.txt")


def _overlapping_features_on_the_branch(project: Path) -> None:
    seed_records(
        project,
        slice_("Team-Leader-1", statement="one slice"),
        slice_("Team-Leader-2", statement="another slice"),
    )
    assert engine.run_git(project, "add", "-A").returncode == 0
    done = engine.run_git(
        project,
        "-c",
        "user.name=Developer",
        "-c",
        "user.email=developer@agents.nidvue.com",
        "commit",
        "-q",
        "-m",
        "feat(records): two features on one path",
    )
    assert done.returncode == 0, done.stderr


def test_a_review_pass_refuses_an_independence_violation(cli, project, capsys) -> None:
    _ship(cli, project)
    _overlapping_features_on_the_branch(project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    capsys.readouterr()

    code = cli(
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
        "pytest @HEAD -> 7 passed",
    )
    said = capsys.readouterr()

    assert code == 2
    assert "the feature records at the tree that would be landed have 1 problem(s)" in said.err
    assert "F-0001 F-0002 share a writable path: src/a.py" in said.err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before


def test_a_pr_merge_refuses_an_independence_violation(cli, project, capsys) -> None:
    _ship(cli, project)
    root = team_root(project)
    # An approved-but-unmerged PR: the state a second Reviewer merges from.
    prs = engine.parse_reviews(root / engine.F_REVIEWS)
    prs[0]["status"] = "approved"
    engine.write_reviews(root / engine.F_REVIEWS, prs)
    tasks = engine.parse_tasks(root / "Roles" / "Developer" / engine.F_TASKS)
    tasks[0]["review_status"] = "passed"
    tasks[0]["self_check"] = "passed"
    tasks[0]["status"] = "review"
    engine.write_tasks(root / "Roles" / "Developer" / engine.F_TASKS, tasks, "developer")
    _overlapping_features_on_the_branch(project)
    main_before = engine.run_git(project, "rev-parse", "main").stdout.strip()
    capsys.readouterr()

    code = cli("--project", project, "pr", "merge", "--pr", "P-0001", "--by", "reviewer-1")
    said = capsys.readouterr()

    assert code == 2
    assert "the feature records at the merged tree have 1 problem(s)" in said.err
    assert "F-0001 F-0002 share a writable path: src/a.py" in said.err
    assert engine.run_git(project, "rev-parse", "main").stdout.strip() == main_before
