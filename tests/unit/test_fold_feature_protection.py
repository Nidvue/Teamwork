"""An open feature protects its leader and that leader's squad from being folded.

Why these tests exist: the fold policy (`engine._foldable_instances`, shared by
`instance prune`, `lane reap` and every reconcile) tested only in-flight work -
slot, claim, doing task, ready unit, review claim. A Team Leader owning an open
feature, and the squad attached under it, held none of those while between units,
so a wave folded both minutes after the team was built and the chain the user
requires (user -> CEO -> leader -> workers) collapsed (T-0099).

What must not regress: a seat is not foldable while it owns a feature in
`FEATURE_OPEN_STATES` (`ready`, `active` - the same set `records.open_records`
compares), or while the leader it is attached to under `Team.md` does; a feature
only `proposed` protects nobody; a leader whose feature is closed still folds; a
squad member is folded only after its leader; nothing else about the policy moves.

Owner: developer. Task: T-0099. Requirements: AGENTS.md (reporting lines), 13.2.
"""

from __future__ import annotations

from pathlib import Path

from test_pr_merge_base_advance import team_root

from teamwork import engine, lanes

AGENTS = "ceo,team-leader-1,developer-1,tester-1,reviewer-1"


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    root = team_root(project)
    assert (
        cli(
            "--project",
            project,
            "instance",
            "add",
            "developer",
            "--under",
            "team-leader-1",
            "--name",
            "developer-2",
        )
        == 0
    )
    return root


def seed_feature(project: Path, state: str = "ready", owner: str = "Team-Leader-1") -> None:
    path = project / "docs" / "Team" / "Features.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = engine.new_feature("the slice", owner, ["src/a.py"], "Architecture.md#13", [], state)
    record["id"] = "F-0001"
    record["created"] = engine.today_iso()
    record["updated"] = engine.today_iso()
    engine.write_features(path, [record])


def finished_run(root: Path, agent: str, index: int) -> None:
    lanes.write_run(
        root,
        {
            "id": f"L-{index:04d}",
            "agent": agent,
            "role": engine.resolve_role(agent),
            "task": "",
            "attempt": 1,
            "state": "done",
            "profile": "standard",
        },
    )


def kept_reason(root: Path, name: str) -> str:
    _fold, keep = engine._foldable_instances(root, keep_required=False, mutate=False)
    return next((why for who, _role, why in keep if who == name), "")


def test_an_open_feature_protects_its_leader_and_the_squad_under_it(cli, project) -> None:
    root = init(cli, project)
    seed_feature(project, state="ready")
    fold, _keep = engine._foldable_instances(root, keep_required=False, mutate=False)
    folded = {name for name, _role in fold}
    assert "Team-Leader-1" not in folded
    assert "Developer-2" not in folded
    assert "F-0001" in kept_reason(root, "Team-Leader-1")
    assert "F-0001" in kept_reason(root, "Developer-2")


def test_instance_prune_keeps_a_leader_that_owns_an_open_feature(cli, project, capsys) -> None:
    root = init(cli, project)
    seed_feature(project, state="active")
    capsys.readouterr()
    assert cli("--project", project, "instance", "prune", "--by", "ceo") == 0
    out = capsys.readouterr().out
    assert (root / engine.DIR_AGENTS / "Team-Leader-1").is_dir()
    assert (root / engine.DIR_AGENTS / "Developer-2").is_dir()
    assert "keep Team-Leader-1" in out and "F-0001" in out
    assert "keep Developer-2" in out and "F-0001" in out


def test_lane_reap_keeps_an_attached_squad_while_the_feature_is_open(cli, project) -> None:
    root = init(cli, project)
    seed_feature(project, state="ready")
    finished_run(root, "Team-Leader-1", 1)
    finished_run(root, "Developer-2", 2)
    assert lanes._recycle_finished(root, "ceo") == []
    assert (root / engine.DIR_AGENTS / "Team-Leader-1").is_dir()
    assert (root / engine.DIR_AGENTS / "Developer-2").is_dir()


def test_a_closed_feature_folds_the_leader_first_and_then_its_squad(cli, project) -> None:
    root = init(cli, project)
    seed_feature(project, state="done")
    fold, _keep = engine._foldable_instances(root, keep_required=False, mutate=False)
    names = [name for name, _role in fold]
    assert "Team-Leader-1" in names and "Developer-2" in names
    assert names.index("Team-Leader-1") < names.index("Developer-2")
    assert cli("--project", project, "instance", "prune", "--by", "ceo") == 0
    assert not (root / engine.DIR_AGENTS / "Team-Leader-1").is_dir()
    assert not (root / engine.DIR_AGENTS / "Developer-2").is_dir()


def test_a_proposed_feature_protects_nobody(cli, project) -> None:
    root = init(cli, project)
    seed_feature(project, state="proposed")
    assert engine.open_records(engine.parse_features(root / "docs" / "Team" / "Features.md")) == []
    fold, _keep = engine._foldable_instances(root, keep_required=False, mutate=False)
    names = [name for name, _role in fold]
    assert "Team-Leader-1" in names
    assert "Developer-2" in names
    assert kept_reason(root, "Team-Leader-1") == ""


def test_a_seat_with_no_feature_still_folds(cli, project) -> None:
    root = init(cli, project)
    fold, _keep = engine._foldable_instances(root, keep_required=False, mutate=False)
    names = [name for name, _role in fold]
    assert "Team-Leader-1" in names
    assert "Developer-2" in names
