"""T-0100: no staffed role may sit over AlwaysOnBudgetKb unnoticed.

The Reviewers sat 2624 B over the cap on every instance while nothing read the
row, so a one-off trim grew back with the next memory entry. These pin the cap:
the live tree must report no over row, and a fixture row over the cap must be
reported by instance.
"""

from pathlib import Path

import pytest

from teamwork import harness

REPO = Path(__file__).resolve().parents[2]


def team_roots(base: Path) -> list[Path]:
    return [p for p in sorted(base.glob(".pi/*/*/*")) if (p / "Settings.json").is_file()]


def test_no_live_row_is_over_the_cap() -> None:
    roots = team_roots(REPO)
    if not roots:
        pytest.skip("no team tree in this checkout")
    rows = harness.over_budget_rows(REPO, roots[0])
    assert not rows, f"rows over AlwaysOnBudgetKb: {[tuple(row) for row in rows]}"


def test_a_row_over_the_cap_is_reported(cli, tmp_path) -> None:
    project = tmp_path / "Project"
    assert cli("--project", project, "init", "--agents", "reviewer-1", "--no-git") == 0
    roots = team_roots(project)
    assert len(roots) == 1, roots
    role_dir = [p for p in (roots[0] / "Roles").glob("*") if p.name.lower() == "reviewer"][0]
    (role_dir / "ShortTermMemory.md").write_text("x" * 400_000, encoding="utf-8")
    rows = harness.over_budget_rows(REPO, roots[0])
    assert rows, "a 400 KB short-term memory did not put the row over the cap"
    assert any(str(row[0]).lower().startswith("reviewer") for row in rows), [
        tuple(row) for row in rows
    ]
