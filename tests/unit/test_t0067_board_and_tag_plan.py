"""T-0067: a release task must not block its own release, and a board edit must not
be charged for a parallel lane's status drift.

Two measured defects, one class: a generated document and the gate that reads it
could not both be satisfied by the person who had to change it.

1. ``docs/Team/Board.md`` keeps an In-flight row's title verbatim, so a release
   task titled "cut the v1.5.9 release" put a ``vX.Y.Z`` token in committed
   markdown that R9 failed until the tag existed - and the tag could not be created
   because the SHA was not CI-green (CI 43747243572: "R9 DRIFT:
   docs/Team/Board.md:219: names v1.5.9, which is not a tag").
2. preflight compared the WHOLE board against the live queues, so any task whose
   diff touched the board was charged for every sibling that moved a status cell
   after the render, and could never be green (measured twice on T-0038:
   "releaseengineer T-0002 board blocked vs queue doing").
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from teamwork import board as boardlib  # noqa: E402


def _load_checker():
    """The release-consistency script, by path: ``scripts/`` also holds a
    ``teamwork.py`` that would shadow the package on ``sys.path``."""
    spec = importlib.util.spec_from_file_location(
        "check_release_consistency", ROOT / "scripts" / "check_release_consistency.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crc = _load_checker()

SKELETON = (ROOT / "templates" / "Docs" / "Board.md").read_text(encoding="utf-8")

PLANNED_BOARD = """# BOARD - live status

## Task table

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| developer | T-0009 cut the v1.5.9 release | P1 | doing | - |

## Blockers

none
"""

CLAIMED_BOARD = """# BOARD - live status

## Task table

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| developer | T-0009 | ship v1.5.9 | doing | - | - |

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| developer | T-0009 cut the release | P1 | doing | - |

## Blockers

none
"""


def _task(status, title="work", area="x"):
    return {
        "status": status,
        "area": area,
        "pr": "",
        "merge_commit": "",
        "priority": "P1",
        "title": title,
    }


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "Team").mkdir(parents=True)
    for args in (
        ("init", "-q"),
        ("config", "user.email", "team@example.com"),
        ("config", "user.name", "team"),
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return repo


def _commit(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", rel], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", rel], check=True, capture_output=True
    )


def test_a_release_task_title_is_a_plan_and_r9_admits_it(tmp_path):
    repo = _repo(tmp_path)
    _commit(repo, "docs/Team/Board.md", PLANNED_BOARD)
    result = crc.rule_r9_markdown_tags(repo)
    assert not result.findings, result.findings


def test_the_same_token_outside_the_in_flight_table_is_still_a_claim(tmp_path):
    repo = _repo(tmp_path)
    _commit(repo, "docs/Team/Board.md", CLAIMED_BOARD)
    result = crc.rule_r9_markdown_tags(repo)
    assert result.findings, "a vX.Y.Z token in the task table must still name a tag"
    assert "v1.5.9" in result.findings[0]


def test_a_parallel_lanes_status_drift_is_not_charged_to_a_title_only_board_edit():
    base = {("developer", "T-0001"): _task("doing"), ("tester", "T-0002"): _task("doing")}
    base_board = boardlib.render(base, SKELETON)
    branch_board = boardlib.render(
        {**base, ("developer", "T-0001"): _task("doing", title="cut the v1.5.9 release")}, SKELETON
    )
    live = {("developer", "T-0001"): _task("doing"), ("tester", "T-0002"): _task("blocked")}
    assert boardlib.problems(live, branch_board), "the sibling drift must still be visible"
    assert boardlib.problems(live, branch_board, baseline=base_board) == []


def test_a_row_the_edit_changed_is_still_compared_with_the_queue():
    base = {("developer", "T-0001"): _task("doing")}
    base_board = boardlib.render(base, SKELETON)
    branch_board = base_board.replace(
        "| developer | T-0001 | x | doing |", "| developer | T-0001 | x | blocked |"
    )
    assert branch_board != base_board
    # `review` on either side is the documented landing window, so this row is a
    # plain contradiction instead: the board says blocked, the queue says doing.
    found = boardlib.problems(
        {("developer", "T-0001"): _task("doing")}, branch_board, baseline=base_board
    )
    assert found, "a touched row that contradicts the queue must still fail"
    assert "T-0001" in " ".join(found)
