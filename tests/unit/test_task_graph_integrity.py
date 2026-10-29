"""The task graph the Plan promises: deps resolve, no cycles, no duplicate open ids.

`docs/Team/Plan.md` states these invariants in its "Task-graph integrity" section
rather than a task census, because a census moves with every status change. This
test is the executable half of that claim: it calls the product's checker
(`teamwork.records.task_graph_problems`) over synthetic queues, over the live
ones when this checkout has a team tree, and over the write gates the CLI uses -
so the invariant lives in the product, not in test-only code.

Each invariant is exercised twice: the checker reports it on a queue, and
`task add` / `task set --deps` refuses to write it, because a queue that cannot
run is indistinguishable from a lane with nothing to do.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from teamwork import config, engine, records

REPO = Path(__file__).resolve().parents[2]
TEAM_REL = Path(".pi") / "Teamwork" / "Teams" / "Teamwork"
ROSTER = "ceo,developer-1,tester-1,reviewer-1"


def team_root() -> Path | None:
    """The local team tree, which `.gitignore` keeps out of a fresh clone."""
    override = os.environ.get("TEAMWORK_ROOT")
    for candidate in ([Path(override)] if override else []) + [REPO / TEAM_REL]:
        if (candidate / "Roles").is_dir():
            return candidate
    return None


def queues_of(root: Path) -> list[Path]:
    return sorted((root / "Roles").glob("*/TaskQueue.md"))


def write_queue(root: Path, role: str, body: str) -> Path:
    path = root / "Roles" / role / "TaskQueue.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


CLEAN = """# Queue
## T-0001 · produce the contract
- priority: P1
- status: done
- deps: -
## T-0002 · build against it
- priority: P2
- status: todo
- deps: T-0001
"""

# A second role, so the fixture never plants the duplicate this suite looks for.
CLEAN_TESTER = """# Queue
## T-0011 · test the contract
- priority: P1
- status: done
- deps: -
## T-0012 · test the build
- priority: P2
- status: todo
- deps: T-0011
"""


@pytest.fixture
def synthetic(tmp_path) -> Path:
    write_queue(tmp_path, "Developer", CLEAN)
    write_queue(tmp_path, "Tester", CLEAN_TESTER)
    return tmp_path


def problems(root: Path) -> list[str]:
    """The product's verdict on every queue under ``root``."""
    return records.task_graph_problems(root)


def named(root: Path, *fragments: str) -> list[str]:
    """The problems that mention every fragment, so a message can be pinned exactly."""
    return [p for p in problems(root) if all(fragment in p for fragment in fragments)]


def test_a_clean_graph_passes_every_invariant(synthetic):
    assert len(queues_of(synthetic)) == 2
    assert problems(synthetic) == []


def test_a_dangling_role_qualified_dep_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0013 · wait on a role that never wrote it\n"
        + "- priority: P1\n- status: todo\n- deps: security-auditor:T-0001\n",
    )
    assert named(synthetic, "tester:T-0013", "security-auditor:T-0001", "names no task")


def test_a_dep_on_a_missing_bare_id_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0014 · wait on an id that never existed\n"
        + "- priority: P1\n- status: todo\n- deps: T-0099\n",
    )
    assert named(synthetic, "tester:T-0014", "'T-0099'", "names no task")


def test_a_qualified_dep_resolves_inside_its_own_role(synthetic):
    """`tester:T-0012` must resolve against the Tester queue, not the Developer one."""
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0015 · two roles at once\n"
        + "- priority: P1\n- status: todo\n- deps: developer:T-0002, tester:T-0012\n",
    )
    assert problems(synthetic) == []


def test_a_two_node_cycle_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        "## T-0001 · one\n- priority: P1\n- status: todo\n- deps: tester:T-0002\n"
        "## T-0002 · two\n- priority: P1\n- status: todo\n- deps: tester:T-0001\n",
    )
    found = named(synthetic, "dependency cycle")
    assert len(found) == 1, found
    assert "tester:T-0001" in found[0] and "tester:T-0002" in found[0]
    # The path starts and ends on the same task: it is a loop, not a chain.
    path = found[0].split(": ", 1)[1].split(" -> ")
    assert path[0] == path[-1], path


def test_a_self_dependency_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        "## T-0001 · itself\n- priority: P1\n- status: todo\n- deps: T-0001\n",
    )
    assert named(synthetic, "tester:T-0001", "depends on itself")


def test_a_resolved_chain_is_not_a_cycle(synthetic):
    write_queue(
        synthetic,
        "Tester",
        "## T-0001 · one\n- priority: P1\n- status: done\n- deps: -\n"
        "## T-0002 · two\n- priority: P1\n- status: todo\n- deps: T-0001\n"
        "## T-0003 · three\n- priority: P1\n- status: todo\n- deps: T-0002\n",
    )
    assert problems(synthetic) == []


def test_two_roles_each_owning_an_open_t_0001_is_not_a_duplicate(synthetic):
    """Ids are per role queue by design, so a shared id across lanes is normal."""
    write_queue(
        synthetic,
        "SecurityAuditor",
        "## T-0001 · audit\n- priority: P1\n- status: doing\n- deps: -\n",
    )
    assert problems(synthetic) == []


def test_one_queue_holding_the_same_id_twice_is_reported(synthetic):
    """One queue with a repeated block makes `task set` act on whichever comes first."""
    write_queue(
        synthetic,
        "Developer",
        CLEAN + "## T-0002 · a second block with the same id\n"
        "- priority: P3\n- status: todo\n- deps: -\n",
    )
    assert named(synthetic, "developer:T-0002", "appears 2 times in one queue")


def test_a_capitalised_dep_qualifier_resolves(synthetic):
    """A dependency may spell the role the way it is displayed, not the way it is filed."""
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0016 · display casing\n"
        + "- priority: P1\n- status: todo\n- deps: SecurityAuditor:T-0001\n",
    )
    write_queue(
        synthetic,
        "SecurityAuditor",
        "## T-0001 · audit\n- priority: P1\n- status: doing\n- deps: -\n",
    )
    assert problems(synthetic) == []


def test_a_dep_qualified_with_an_instance_name_resolves(synthetic):
    """`developer-1:T-0001` is the same queue as `developer:T-0001` (dep_satisfied agrees)."""
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0017 · instance spelling\n"
        + "- priority: P1\n- status: todo\n- deps: developer-1:T-0002\n",
    )
    assert problems(synthetic) == []


def test_a_queue_directory_that_is_not_a_role_is_reported(synthetic):
    write_queue(
        synthetic, "Auditor", "## T-0001 · rogue\n- priority: P1\n- status: todo\n- deps: -\n"
    )
    staffed = {records.norm_role(role) for role in config.ROLE_PARENT}
    assert set(records.load_task_queues(synthetic)) - staffed == {"auditor"}


def test_a_task_without_a_priority_is_reported(synthetic):
    write_queue(
        synthetic, "Tester", "## T-0001 · unprioritised\n- priority: -\n- status: todo\n- deps: -\n"
    )
    assert named(synthetic, "tester:T-0001", "has no priority")


# --------------------------------------------------------------------------- #
# the write gates: a broken graph must be refused before it exists
# --------------------------------------------------------------------------- #


def init_team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    assert root.is_dir()
    return root


def queue(root: Path, role: str) -> list[dict]:
    return engine.parse_tasks(root / "Roles" / role / "TaskQueue.md")


def test_task_add_refuses_a_self_dependency(cli, project: Path, capsys) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "first", "--no-review") == 0
    capsys.readouterr()

    # The new task gets T-0002, so depending on T-0002 is depending on itself.
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "second",
            "--deps",
            "T-0002",
            "--no-review",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "developer:T-0002 depends on itself" in err, err
    assert [t["id"] for t in queue(root, "Developer")] == ["T-0001"]


@pytest.mark.parametrize("dep", ["T-0099", "nosuchrole:T-0001", "no-task-id"])
def test_task_add_refuses_an_unknown_dependency(cli, project: Path, capsys, dep: str) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "first", "--no-review") == 0
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "downstream",
            "--deps",
            dep,
            "--no-review",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert dep in err, err
    assert [t["id"] for t in queue(root, "Developer")] == ["T-0001"]


def test_task_set_refuses_a_two_node_cycle(cli, project: Path, capsys) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "api", "--no-review") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester",
            "test the api",
            "--deps",
            "developer:T-0001",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--deps", "tester:T-0001")
        == 2
    )
    err = capsys.readouterr().err
    assert "dependency cycle: developer:T-0001 -> tester:T-0001 -> developer:T-0001" in err, err
    # The refused write changed nothing: the queue on disk still has no deps.
    assert queue(root, "Developer")[0]["deps"] == ""


def test_task_set_refuses_a_cross_role_cycle(cli, project: Path, capsys) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "ceo", "decide", "--no-review") == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "build",
            "--deps",
            "ceo:T-0001",
            "--no-review",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "tester",
            "verify",
            "--deps",
            "developer:T-0001",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "set", "ceo", "T-0001", "--deps", "tester:T-0001") == 2
    err = capsys.readouterr().err
    assert "ceo:T-0001 -> tester:T-0001 -> developer:T-0001 -> ceo:T-0001" in err, err
    assert queue(root, "CEO")[0]["deps"] == ""


def test_task_add_refuses_a_duplicate_open_id(cli, project: Path, capsys) -> None:
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "tester", "only", "--no-review") == 0
    path = root / "Roles" / "Tester" / "TaskQueue.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n## T-0001 · a repeated block\n- priority: P1\n- status: todo\n- deps: -\n",
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "add", "tester", "another", "--no-review") == 2
    err = capsys.readouterr().err
    assert "tester:T-0001 appears 2 times in one queue" in err, err


def test_task_check_is_clean_on_a_valid_graph(cli, project: Path, capsys) -> None:
    init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "api", "--no-review") == 0
    assert (
        cli("--project", project, "task", "add", "tester", "test", "--deps", "developer:T-0001")
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "check") == 0
    out = capsys.readouterr().out
    assert "0 problems in 4 role queue(s)" in out, out


def test_task_check_reports_a_cycle_that_arrived_on_disk(cli, project: Path, capsys) -> None:
    """A merge can bring a queue the gate never wrote, so the read side must see it."""
    root = init_team(cli, project)
    write_queue(
        root,
        "Tester",
        "## T-0001 · one\n- priority: P1\n- status: todo\n- deps: tester:T-0002\n"
        "## T-0002 · two\n- priority: P1\n- status: todo\n- deps: tester:T-0001\n",
    )
    capsys.readouterr()

    assert cli("--project", project, "task", "check") == 2
    out = capsys.readouterr().out
    assert "dependency cycle: tester:T-0001 -> tester:T-0002 -> tester:T-0001" in out, out


# --------------------------------------------------------------------------- #
# the committed claim
# --------------------------------------------------------------------------- #


def test_the_plan_states_the_same_invariants():
    """The document and these checks must not drift apart."""
    plan = (REPO / "docs" / "Team" / "Plan.md").read_text(encoding="utf-8")
    split = plan.split("## Task-graph integrity", 1)
    assert len(split) == 2, "docs/Team/Plan.md has no '## Task-graph integrity' section"
    body = split[1].split("\n## ", 1)[0]
    for phrase in (
        "dangling dependencies",
        "dependency cycles",
        "holding the same task id twice",
        "missing a priority",
        "not a role",
    ):
        assert phrase in body, f"the Plan section no longer states {phrase!r}"


def test_the_plan_section_pins_no_census():
    """A task count is stale the moment any task changes status, so it must not ship.

    The previous deliverable pinned "44 tasks (done 31, review 5, doing 6, todo 1,
    dropped 1)" and the repo had already outgrown it: a committed table, its own
    artifact and a fresh parse gave three different numbers.
    """
    plan = (REPO / "docs" / "Team" / "Plan.md").read_text(encoding="utf-8")
    body = plan.split("## Task-graph integrity", 1)[1].split("\n## ", 1)[0]
    # Any count of graph objects, in either order ("44 tasks", "61 rows", "done 31")
    # and any phrasing - a fixed word list only catches the words it was written for.
    census = [
        line
        for line in body.splitlines()
        if re.search(
            r"\b\d+\s*(?:tasks?|rows?|blocks?|headings?|queues?|items?|entries|nodes?|edges?"
            r"|deps?|dependencies|done|review|doing|todo|dropped|open|closed)\b"
            r"|\b(?:done|review|doing|todo|dropped|open|closed|total)\s*[:=]?\s*\d+",
            line,
            re.IGNORECASE,
        )
        and "`" not in line.split("|")[0]
    ]
    assert not census, f"the section pins a census, which goes stale: {census}"


def test_the_plan_lists_each_milestone_once():
    """A duplicated closed-milestone table is the defect this task set out to fix."""
    pattern = r"^## (?:M\d+|Closed milestones)"
    headings = re.findall(
        pattern, (REPO / "docs" / "Team" / "Plan.md").read_text(encoding="utf-8"), re.M
    )
    assert len(headings) == len(set(headings)), f"duplicated sections: {headings}"


def test_the_live_queues_are_clean():
    """The real team tree, when this checkout has one (it is gitignored)."""
    root = team_root()
    if root is None:
        pytest.skip("no local team tree in this checkout (gitignored working state)")
    paths = queues_of(root)
    if not paths:
        pytest.skip("no shared role queues in the local team tree")
    found = records.task_graph_problems(root)
    assert not found, found
    staffed = {records.norm_role(role) for role in config.ROLE_PARENT}
    assert not set(records.load_task_queues(root)) - staffed
