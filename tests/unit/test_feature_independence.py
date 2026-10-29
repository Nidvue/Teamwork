"""The independence rule, as an executable test (Architecture.md 13.3).

`feature check` is the executable form of "features must be independent": two open
features may not own one writable path (rule 1), may not depend on each other's
in-flight work (rule 2), may not share a leader (rule 3), may not claim a glob,
a path outside the repository, checkout state, a generated artifact or the records
file (rule 4), and no two records may carry one id (rule 5, over every record, open
or closed).

Each case below is a real two-record record set, and every finding is asserted
verbatim - the wording is frozen so a `feature`-layer record can assert it too.
The one case that must stay GREEN is the interesting one: two features that name
the same frozen interface anchor are parallel work, not a collision (13.2), and a
checker that refused them would serialise every squad behind the first.

Owner: team-leader. Task: T-0042. Requirements: Architecture.md 13.1, 13.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import engine

TEAM = ("ceo", "architect-1", "team-leader-1", "team-leader-2", "developer-1")


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def record(
    fid: str,
    owner: str = "Team-Leader-1",
    paths=(),
    state: str = "active",
    depends_on=(),
    interface: str = "Architecture.md#13",
    statement: str = "",
) -> dict:
    item = engine.new_feature(
        statement or f"{fid} ships one slice",
        owner,
        list(paths),
        interface,
        list(depends_on),
        state,
    )
    item["id"] = fid
    return item


def findings(records: list, only=()) -> list:
    return [problem.message for problem in engine.check_records(records, only)]


def rules(records: list, only=()) -> list:
    return [problem.rule for problem in engine.check_records(records, only)]


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(TEAM), "--no-git") == 0
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def check_cli(cli, project: Path, *extra: str) -> int:
    return cli("--project", project, "feature", "check", *extra)


# --------------------------------------------------------------------------- #
# rule 1 - one writable path, one open feature
# --------------------------------------------------------------------------- #


def test_a_shared_file_is_red(cli, project, capsys) -> None:
    init(cli, project)
    records = [
        record("F-0001", paths=["src/a.py"]),
        record("F-0002", "Team-Leader-2", paths=["src/b.py", "src/a.py"]),
    ]
    engine.write_features(project / "docs" / "Team" / "Features.md", records)
    capsys.readouterr()

    assert check_cli(cli, project) == 2
    out = capsys.readouterr().out
    assert "teamwork: feature check: 1 problem(s) in 2 open feature(s) @" in out
    assert "  - F-0001 F-0002 share a writable path: src/a.py" in out


def test_a_shared_directory_is_red_for_the_file_under_it(cli, project) -> None:
    """The prefix rule: `src/teamwork` covers `src/teamwork/engine.py`."""
    init(cli, project)
    records = [
        record("F-0001", paths=["src/teamwork"]),
        record("F-0002", "Team-Leader-2", paths=["src/teamwork/engine.py"]),
    ]
    assert findings(records) == ["F-0001 F-0002 share a writable path: src/teamwork"]


def test_a_trailing_slash_is_optional_noise(cli, project) -> None:
    init(cli, project)
    records = [
        record("F-0001", paths=["src/teamwork/"]),
        record("F-0002", "Team-Leader-2", paths=["src/teamwork"]),
    ]
    assert rules(records) == [1]


def test_sibling_names_are_not_a_collision() -> None:
    """`engine.py` and `engine_extra.py` share no boundary: the rule matches on `/`."""
    records = [
        record("F-0001", paths=["src/engine.py", "README.md"]),
        record("F-0002", "Team-Leader-2", paths=["src/engine_extra.py", "README.mdx"]),
    ]
    assert findings(records) == []


def test_a_closed_feature_releases_its_paths() -> None:
    """A `done` record is not compared at all, or the path map grows monotonically."""
    records = [
        record("F-0001", paths=["src/a.py"], state="done"),
        record("F-0002", "Team-Leader-2", paths=["src/a.py"]),
    ]
    assert findings(records) == []


def test_case_is_a_collision_on_every_platform() -> None:
    records = [
        record("F-0001", paths=["src/TeamWork/Widget.py"]),
        record("F-0002", "Team-Leader-2", paths=["src/teamwork/widget.py"]),
    ]
    assert findings(records) == ["F-0001 F-0002 share a writable path: src/TeamWork/Widget.py"]


def test_two_features_on_one_frozen_interface_are_parallel_work() -> None:
    """The probe's clean case: a shared interface anchor is permitted, not a clash."""
    records = [
        record("F-0001", paths=["src/a.py"], interface="Architecture.md#13"),
        record("F-0002", "Team-Leader-2", paths=["src/b.py"], interface="Architecture.md#13"),
    ]
    assert findings(records) == []


def test_the_same_feature_listing_a_path_twice_is_green() -> None:
    records = [record("F-0001", paths=["src/a.py", "src/a.py"])]
    assert findings(records) == []


# --------------------------------------------------------------------------- #
# rule 2 - a dependency is work, not an interface
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("state", ["proposed", "ready", "active", "dropped"])
def test_a_dependency_on_work_that_is_not_done_is_red(state: str) -> None:
    records = [
        record("F-0001", paths=["src/a.py"], state=state),
        record("F-0002", "Team-Leader-2", paths=["src/b.py"], depends_on=["F-0001"]),
    ]
    assert findings(records) == [f"F-0002 depends on in-flight F-0001 (state={state})"]


def test_a_dependency_on_a_done_feature_is_green() -> None:
    records = [
        record("F-0001", paths=["src/a.py"], state="done"),
        record("F-0002", "Team-Leader-2", paths=["src/b.py"], depends_on=["F-0001"]),
    ]
    assert findings(records) == []


# --------------------------------------------------------------------------- #
# rule 3 - one open feature per leader
# --------------------------------------------------------------------------- #


def test_one_leader_cannot_hold_two_open_features() -> None:
    records = [
        record("F-0001", paths=["src/a.py"]),
        record("F-0002", paths=["src/b.py"]),
    ]
    assert findings(records) == [
        "Team-Leader-1 owns 2 open features: F-0001, F-0002 (rule 2: one open feature per leader)"
    ]


# --------------------------------------------------------------------------- #
# rule 4 - the five frozen path findings
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (
            "src/*.py",
            "F-0001 claims a glob (src/*.py); name the directory instead",
        ),
        (
            "../outside.py",
            "F-0001 claims a path outside the repository (../outside.py); "
            "the claim is relative to the repository root",
        ),
        (
            "/etc/passwd",
            "F-0001 claims a path outside the repository (/etc/passwd); "
            "the claim is relative to the repository root",
        ),
        (
            "C:/temp/x.py",
            "F-0001 claims a path outside the repository (C:/temp/x.py); "
            "the claim is relative to the repository root",
        ),
        (
            ".pi/Teamwork/x",
            "F-0001 claims checkout state (.pi/Teamwork/x); it never merges",
        ),
        (
            "docs/Team/Board.md",
            "F-0001 claims a generated artifact (docs/Team/Board.md); it is written at the merge",
        ),
        (
            "docs/Team/Features.md",
            "F-0001 claims the records file (docs/Team/Features.md); "
            "it is the map every claim is judged against",
        ),
    ],
)
def test_the_five_rule_four_findings_are_verbatim(path: str, message: str) -> None:
    records = [record("F-0001", paths=[path])]
    assert findings(records) == [message]
    assert rules(records) == [4]


def test_a_path_that_does_not_exist_yet_is_still_inside_the_repository() -> None:
    """Nothing is `stat`'ed: a slice may claim a file it has not created."""
    records = [record("F-0001", paths=["src/new_module.py"])]
    assert findings(records) == []


def test_a_backslash_spelling_is_the_same_claim_as_the_slash_one() -> None:
    records = [
        record("F-0001", paths=["src\\teamwork\\engine.py"]),
        record("F-0002", "Team-Leader-2", paths=["src/teamwork/engine.py"]),
    ]
    assert rules(records) == [1]


# --------------------------------------------------------------------------- #
# rule 5 - an id names one feature, over every record
# --------------------------------------------------------------------------- #


def test_a_duplicated_id_is_red_with_nothing_open() -> None:
    """The one rule over every record: a closed id still names one feature."""
    records = [
        record("F-0003", "Team-Leader-1", paths=["src/a.py"], state="done"),
        record("F-0003", "Team-Leader-2", paths=["src/b.py"], state="proposed"),
    ]
    assert findings(records) == [
        "F-0003 is allocated twice (Team-Leader-1, Team-Leader-2); "
        "renumber the arriving record before it lands"
    ]


def test_rule_five_is_the_only_finding_a_named_closed_record_contributes() -> None:
    records = [
        record("F-0001", paths=["src/a.py"], state="done"),
        record("F-0002", "Team-Leader-2", paths=["src/a.py"], state="active"),
    ]
    # A named `done` record is outside rules 1-4, so the shared path is not a
    # finding; its duplicate id would be.
    assert findings(records, ["F-0001"]) == []
    assert findings(records + [record("F-0001", "Team-Leader-2", state="dropped")], ["F-0001"]) == [
        "F-0001 is allocated twice (Team-Leader-1, Team-Leader-2); "
        "renumber the arriving record before it lands"
    ]


# --------------------------------------------------------------------------- #
# the exit codes and the json object of the read verb
# --------------------------------------------------------------------------- #


def test_a_green_check_counts_the_open_features(cli, project, capsys) -> None:
    init(cli, project)
    engine.write_features(
        project / "docs" / "Team" / "Features.md",
        [
            record("F-0001", paths=["src/a.py"]),
            record("F-0002", "Team-Leader-2", paths=["src/b.py"], state="done"),
        ],
    )
    capsys.readouterr()

    assert check_cli(cli, project) == 0
    assert "open feature(s), 0 problem(s) @" in capsys.readouterr().out


def test_the_json_problem_carries_the_record_the_rule_and_the_message(cli, project, capsys) -> None:
    import json

    init(cli, project)
    engine.write_features(
        project / "docs" / "Team" / "Features.md",
        [record("F-0001", paths=["src/*.py"])],
    )
    capsys.readouterr()

    assert check_cli(cli, project, "--json") == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["features"] == 1
    assert payload["problems"] == [
        {
            "feature": "F-0001",
            "rule": 4,
            "message": "F-0001 claims a glob (src/*.py); name the directory instead",
        }
    ]


def test_a_candidate_is_judged_before_it_is_created() -> None:
    """`feature add` refuses instead of writing: the same rules, one record earlier."""
    existing = [record("F-0001", paths=["src/a.py"], state="ready")]
    candidate = record("F-0002", "Team-Leader-2", paths=["src/a.py"], state="proposed")
    problems = engine.candidate_problems(existing, candidate)
    assert [p.message for p in problems] == ["F-0002 F-0001 share a writable path: src/a.py"]


# --------------------------------------------------------------------------- #
# the merge path: the one place that sees both revisions
# --------------------------------------------------------------------------- #


def _repo(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(TEAM)) == 0
    return engine.work_repo(
        (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)).resolve()
    )


def _write_and_commit(project: Path, records: list, message: str) -> None:
    path = project / "docs" / "Team" / "Features.md"
    engine.write_features(path, records)
    assert engine.run_git(project, "add", "-A").returncode == 0
    done = engine.run_git(
        project,
        "-c",
        "user.name=CEO",
        "-c",
        "user.email=ceo@agents.nidvue.com",
        "commit",
        "-q",
        "-m",
        message,
    )
    assert done.returncode == 0, done.stderr


def test_the_merged_tree_sees_both_branches(cli, project: Path) -> None:
    """A per-branch check can be green while the merged tree is red (13.1, 13.3)."""
    repo = _repo(cli, project)
    base = [
        record("F-0001", "Team-Leader-1", paths=["src/a.py"], state="ready"),
    ]
    _write_and_commit(repo, base, "chore(records): F-0001")

    assert engine.run_git(repo, "checkout", "-q", "-b", "leader-2/t-0001-slice").returncode == 0
    arriving = base + [
        record("F-0002", "Team-Leader-2", paths=["src/a.py"], state="ready"),
    ]
    _write_and_commit(repo, arriving, "feat(records): F-0002")
    # The lane's own revision is red too, but the point is the merged tree.
    assert engine.run_git(repo, "checkout", "-q", "main").returncode == 0

    problems = engine._feature_gate(repo, "main", "leader-2/t-0001-slice")
    assert [p.message for p in problems] == ["F-0001 F-0002 share a writable path: src/a.py"]


def test_a_duplicate_id_cut_on_two_branches_is_caught_at_the_merge(cli, project: Path) -> None:
    """Allocation is max+1 per revision, so two lanes can both take F-0002."""
    repo = _repo(cli, project)
    base = [record("F-0001", "Team-Leader-1", paths=["src/a.py"], state="done")]
    _write_and_commit(repo, base, "chore(records): F-0001")

    assert engine.run_git(repo, "checkout", "-q", "-b", "leader-2/t-0001-slice").returncode == 0
    _write_and_commit(
        repo,
        base + [record("F-0002", "Team-Leader-2", paths=["src/b.py"], state="ready")],
        "feat(records): F-0002 on the branch",
    )
    assert engine.run_git(repo, "checkout", "-q", "main").returncode == 0
    _write_and_commit(
        repo,
        base + [record("F-0002", "Team-Leader-1", paths=["src/c.py"], state="ready")],
        "feat(records): F-0002 on the base",
    )

    problems = engine._feature_gate(repo, "main", "leader-2/t-0001-slice")
    assert [p.rule for p in problems] == [5]
    assert problems[0].message == (
        "F-0002 is allocated twice (Team-Leader-1, Team-Leader-2); "
        "renumber the arriving record before it lands"
    )


def test_a_branch_editing_a_base_row_is_not_a_duplicate(cli, project: Path) -> None:
    """An id the fork already carried is one feature edited, not two features."""
    repo = _repo(cli, project)
    base = [record("F-0001", "Team-Leader-1", paths=["src/a.py"], state="ready")]
    _write_and_commit(repo, base, "chore(records): F-0001")
    assert engine.run_git(repo, "checkout", "-q", "-b", "leader-1/t-0001-slice").returncode == 0
    _write_and_commit(
        repo,
        [record("F-0001", "Team-Leader-1", paths=["src/a.py"], state="active")],
        "feat(records): F-0001 is active",
    )

    problems = engine._feature_gate(repo, "main", "leader-1/t-0001-slice")
    assert [p.message for p in problems] == []
    merged, seen = engine.merged_feature_records(repo, "main", "leader-1/t-0001-slice")
    assert seen and [r["state"] for r in merged] == ["active"]


def test_the_preflight_check_refuses_the_tree_that_would_land(cli, project: Path) -> None:
    """`preflight` measures the merge, not just the lane: the same frozen finding."""
    repo = _repo(cli, project)
    base = [record("F-0001", "Team-Leader-1", paths=["src/a.py"], state="ready")]
    _write_and_commit(repo, base, "chore(records): F-0001")
    assert engine.run_git(repo, "checkout", "-q", "-b", "leader-2/t-0001-slice").returncode == 0
    _write_and_commit(
        repo,
        base + [record("F-0002", "Team-Leader-2", paths=["src/a.py"], state="ready")],
        "feat(records): F-0002",
    )

    root = (repo / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(repo)).resolve()
    check = engine._preflight_features(root, repo, "main", "leader-2/t-0001-slice")
    assert check.name == "features"
    assert check.status == engine.PREFLIGHT_FAIL
    assert "F-0001 F-0002 share a writable path: src/a.py" in check.detail
    assert "feature check" in check.fix


def test_a_tree_without_feature_records_is_green(cli, project: Path) -> None:
    repo = _repo(cli, project)
    assert (repo / "docs" / "Team" / "Features.md").unlink() is None
    assert engine.run_git(repo, "add", "-A").returncode == 0
    assert (
        engine.run_git(
            repo,
            "-c",
            "user.name=CEO",
            "-c",
            "user.email=ceo@agents.nidvue.com",
            "commit",
            "-q",
            "-m",
            "chore(records): no features yet",
        ).returncode
        == 0
    )
    root = (repo / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(repo)).resolve()

    check = engine._preflight_features(root, repo, "main", "main")
    assert check.status == engine.PREFLIGHT_OK
    assert "nothing to judge" in check.detail
