"""The task graph the Plan promises: deps resolve, no cycles, no duplicate open ids.

`docs/Team/Plan.md` states these invariants in its "Task-graph integrity" section
rather than a task census, because a census moves with every status change. This
test is the executable half of that claim: it parses shared role queues and fails
when one of the four invariants breaks.

The invariant checks run against synthetic queues as well as the live ones, so the
logic is exercised in CI where the local team tree (gitignored) is absent.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from teamwork import config

REPO = Path(__file__).resolve().parents[2]
TEAM_REL = Path(".pi") / "Teamwork" / "Teams" / "Teamwork"

TASK_RE = re.compile(r"^## (T-\d{4})\b")
FIELD_RE = re.compile(r"^- ([a-z_]+):\s*(.*)$")
DEP_RE = re.compile(r"^(?:(?P<role>[A-Za-z][A-Za-z-]*):)?(?P<id>T-\d{4})$")
OPEN = {"todo", "doing", "review", "selfcheck"}
PRIORITIES = {"P0", "P1", "P2", "P3"}


def team_root() -> Path | None:
    """The local team tree, which `.gitignore` keeps out of a fresh clone."""
    override = os.environ.get("TEAMWORK_ROOT")
    for candidate in ([Path(override)] if override else []) + [REPO / TEAM_REL]:
        if (candidate / "Roles").is_dir():
            return candidate
    return None


def queues_of(root: Path) -> list[Path]:
    return sorted((root / "Roles").glob("*/TaskQueue.md"))


def norm_role(name: str) -> str:
    """`security-auditor`, `SecurityAuditor` and `securityauditor` are one role.

    The queues are directories (`Roles/SecurityAuditor/`) while a dependency may
    write the qualifier however the role is displayed, so both sides of the
    comparison go through this - otherwise `security-auditor:T-0001` looks dangling
    while the task exists.
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def role_of(path: Path) -> str:
    return norm_role(path.parent.name)


def ids_in(path: Path) -> list[str]:
    """Every `## T-xxxx` heading in a queue, in file order, including repeats."""
    return re.findall(r"^## (T-\d{4})\b", path.read_text(encoding="utf-8"), re.M)


def parse(path: Path) -> dict[str, dict[str, str]]:
    """One dict per `## T-xxxx` block, keyed by id, holding its `- field: value` lines."""
    tasks: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        head = TASK_RE.match(line)
        if head:
            current = tasks.setdefault(head.group(1), {})
            continue
        if current is None:
            continue
        field = FIELD_RE.match(line)
        if field:
            current[field.group(1)] = field.group(2).strip()
    return tasks


def graph(paths: list[Path]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        for tid, fields in parse(path).items():
            out[(role_of(path), tid)] = fields
    return out


def deps(fields: dict[str, str]) -> list[str]:
    raw = fields.get("deps", "")
    if raw in ("", "-"):
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def dangling(g: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    """Deps naming a task that does not exist would silently never release."""
    out = []
    for (role, tid), fields in g.items():
        for dep in deps(fields):
            match = DEP_RE.match(dep)
            if not match:
                out.append(f"{role}:{tid} -> unparsable {dep!r}")
            elif (
                (norm_role(match.group("role")) if match.group("role") else role),
                match.group("id"),
            ) not in g:
                out.append(f"{role}:{tid} -> {dep}")
    return out


def cycles(g: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    """A cycle makes every task in it unexecutable, so it must fail loudly."""
    edges = {}
    for node, fields in g.items():
        edges[node] = [
            ((norm_role(m.group("role")) if m.group("role") else node[0]), m.group("id"))
            for m in (DEP_RE.match(d) for d in deps(fields))
            if m
            and ((norm_role(m.group("role")) if m.group("role") else node[0]), m.group("id")) in g
        ]
    found: list[str] = []
    done: set[tuple[str, str]] = set()

    def walk(node, stack):
        if node in stack:
            loop = stack[stack.index(node) :] + [node]
            found.append(" -> ".join(f"{r}:{t}" for r, t in loop))
            return
        if node in done:
            return
        for nxt in edges.get(node, []):
            walk(nxt, [*stack, node])
        done.add(node)

    for node in g:
        walk(node, [])
    return found


def duplicate_open_ids(paths: list[Path]) -> dict[str, int]:
    """One queue holding the same id twice is a defect; the same id across queues is not.

    Ids are allocated per role queue (`records.assign_ids`), so every role legitimately
    owns a `T-0001`. What must not happen is one queue carrying the id twice: `task set`
    and `pr merge` would then act on whichever block they read first. Counting has to
    happen on the parsed blocks, not on the flattened graph, which keys by `(role, id)`.
    """
    out: dict[str, int] = {}
    for path in paths:
        role = role_of(path)
        seen: dict[str, int] = {}
        for tid in ids_in(path):
            seen[tid] = seen.get(tid, 0) + 1
        for tid, n in seen.items():
            if n > 1:
                out[f"{role}:{tid}"] = n
    return out


def unprioritised(g: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    """A task with no priority is never pickable by `task next`."""
    return [
        f"{role}:{tid}"
        for (role, tid), fields in g.items()
        if fields.get("priority", "").strip() not in PRIORITIES
    ]


def unknown_role(g: dict[tuple[str, str], dict[str, str]], staffed: set[str]) -> list[str]:
    """A queue directory that is not a role has no charter, budget or place in the tree."""
    return sorted({role for role, _ in g if role not in staffed})


def write_queue(root: Path, role: str, body: str) -> Path:
    path = root / "Roles" / role / "TaskQueue.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


CLEAN = """# Queue
## T-0001
- priority: P1
- status: done
- deps: -
## T-0002
- priority: P2
- status: todo
- deps: T-0001
"""

# A second role, so the fixture never plants the duplicate this suite looks for.
CLEAN_TESTER = """# Queue
## T-0011
- priority: P1
- status: done
- deps: -
## T-0012
- priority: P2
- status: todo
- deps: T-0011
"""


@pytest.fixture
def synthetic(tmp_path) -> Path:
    write_queue(tmp_path, "Developer", CLEAN)
    write_queue(tmp_path, "Tester", CLEAN_TESTER)
    return tmp_path


def test_a_clean_graph_passes_every_invariant(synthetic):
    g = graph(queues_of(synthetic))
    assert len(g) == 4
    assert not dangling(g)
    assert not cycles(g)
    assert not duplicate_open_ids(queues_of(synthetic))
    assert not unprioritised(g)


def test_a_dangling_role_qualified_dep_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0013\n- priority: P1\n- status: todo\n- deps: security-auditor:T-0001\n",
    )
    g = graph(queues_of(synthetic))
    assert dangling(g) == ["tester:T-0013 -> security-auditor:T-0001"]


def test_a_dep_on_a_missing_bare_id_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER + "## T-0014\n- priority: P1\n- status: todo\n- deps: T-0099\n",
    )
    assert dangling(graph(queues_of(synthetic))) == ["tester:T-0014 -> T-0099"]


def test_a_qualified_dep_resolves_inside_its_own_role(synthetic):
    """`tester:T-0012` must resolve against the Tester queue, not the Developer one."""
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0015\n- priority: P1\n- status: todo\n- deps: developer:T-0002, tester:T-0012\n",
    )
    assert not dangling(graph(queues_of(synthetic)))


def test_a_two_node_cycle_is_reported(synthetic):
    write_queue(
        synthetic,
        "Tester",
        "## T-0001\n- priority: P1\n- status: todo\n- deps: tester:T-0002\n"
        "## T-0002\n- priority: P1\n- status: todo\n- deps: tester:T-0001\n",
    )
    found = cycles(graph(queues_of(synthetic)))
    assert found and "tester:T-0001" in found[0] and "tester:T-0002" in found[0]


def test_a_self_dependency_is_a_cycle(synthetic):
    write_queue(synthetic, "Tester", "## T-0001\n- priority: P1\n- status: todo\n- deps: T-0001\n")
    assert cycles(graph(queues_of(synthetic)))


def test_a_resolved_chain_is_not_a_cycle(synthetic):
    write_queue(
        synthetic,
        "Tester",
        "## T-0001\n- priority: P1\n- status: done\n- deps: -\n"
        "## T-0002\n- priority: P1\n- status: todo\n- deps: T-0001\n"
        "## T-0003\n- priority: P1\n- status: todo\n- deps: T-0002\n",
    )
    assert not cycles(graph(queues_of(synthetic)))


def test_two_roles_each_owning_an_open_t_0001_is_not_a_duplicate(synthetic):
    """Ids are per role queue by design, so a shared id across lanes is normal."""
    write_queue(
        synthetic, "SecurityAuditor", "## T-0001\n- priority: P1\n- status: doing\n- deps: -\n"
    )
    assert not duplicate_open_ids(queues_of(synthetic))


def test_one_queue_holding_the_same_id_twice_is_reported(synthetic):
    """One queue with a repeated block makes `task set` act on whichever comes first."""
    write_queue(
        synthetic,
        "Developer",
        CLEAN + "## T-0002\n- priority: P3\n- status: todo\n- deps: -\n",
    )
    found = duplicate_open_ids(queues_of(synthetic))
    assert found == {"developer:T-0002": 2}


def test_a_capitalised_dep_qualifier_resolves(synthetic):
    """A dependency may spell the role the way it is displayed, not the way it is filed."""
    write_queue(
        synthetic,
        "Tester",
        CLEAN_TESTER
        + "## T-0016\n- priority: P1\n- status: todo\n- deps: SecurityAuditor:T-0001\n",
    )
    write_queue(
        synthetic, "SecurityAuditor", "## T-0001\n- priority: P1\n- status: doing\n- deps: -\n"
    )
    assert not dangling(graph(queues_of(synthetic)))


def test_a_queue_directory_that_is_not_a_role_is_reported(synthetic):
    write_queue(synthetic, "Auditor", "## T-0001\n- priority: P1\n- status: todo\n- deps: -\n")
    staffed = {"developer", "tester"}
    assert unknown_role(graph(queues_of(synthetic)), staffed) == ["auditor"]


def test_a_task_without_a_priority_is_reported(synthetic):
    write_queue(synthetic, "Tester", "## T-0001\n- priority: -\n- status: todo\n- deps: -\n")
    assert unprioritised(graph(queues_of(synthetic))) == ["tester:T-0001"]


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
    headings = re.findall(
        r"^## (?:M\d+|Closed milestones)",
        (REPO / "docs" / "Team" / "Plan.md").read_text(encoding="utf-8"),
        re.M,
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
    g = graph(paths)
    assert not dangling(g), dangling(g)
    assert not cycles(g), cycles(g)
    assert not duplicate_open_ids(paths)
    assert not unprioritised(g)
    staffed = {norm_role(role) for role in config.ROLE_PARENT}
    assert not unknown_role(g, staffed), unknown_role(g, staffed)
