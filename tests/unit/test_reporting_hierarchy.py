"""The reporting tree is one table, and every surface renders that table.

`ROLE_PARENT` in `src/teamwork/config.py` is the single source of truth. This
module fails if a document states a different line, if a role is orphaned or
double-managed, or if the tree loses the property that makes the gates work: the
Reviewer and the Security Auditor report to nobody whose work they judge.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from teamwork.config import ROLE_PARENT, ROLE_REPORT_ORDER


def _rows(path: Path) -> dict[str, str]:
    """`role -> reports-to` from a `| Role | ... | Reports to |` markdown table."""
    found: dict[str, str] = {}
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Role |"):
            in_table = "Reports to" in line
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if found:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= {"-"}:
            continue
        role, reports = cells[0], cells[-1]
        key = re.sub(r"\s*\(.*?\)|\*|`", "", role).strip()
        # "CTO" stays "cto"; "Product Manager" becomes "product-manager"; a row
        # naming instances ("Developer (1..N)") has that suffix stripped above.
        key = key.replace(" ", "-").lower()
        found[key] = reports
    return found


def test_the_tree_has_one_parent_per_role_and_a_root() -> None:
    assert ROLE_PARENT["ceo"] is None
    assert sum(1 for p in ROLE_PARENT.values() if p is None) == 1
    for role, parent in ROLE_PARENT.items():
        if role == "ceo":
            continue
        assert parent in ROLE_PARENT, f"{role} reports to unknown role {parent!r}"
        assert parent != role, f"{role} reports to itself"
    assert set(ROLE_REPORT_ORDER) == set(ROLE_PARENT)


def test_no_role_is_orphaned_from_the_ceo() -> None:
    for role in ROLE_PARENT:
        seen = []
        cur = role
        while ROLE_PARENT.get(cur) is not None:
            assert cur not in seen, f"cycle through {role}: {seen}"
            seen.append(cur)
            cur = ROLE_PARENT[cur]
        assert cur == "ceo", f"{role} does not reach the CEO"


@pytest.mark.parametrize("role", ["reviewer", "security-auditor"])
def test_the_gate_roles_report_past_the_lanes_they_judge(role: str) -> None:
    """The Reviewer and the Security Auditor must not be managed by a lane they audit."""
    assert ROLE_PARENT[role] == "ceo", (
        f"{role} reports to {ROLE_PARENT[role]!r}; a role judged by {role} would then be "
        "its manager, which is review under the reviewed"
    )


def test_delivery_roles_report_into_the_cto() -> None:
    """Engineering lanes hang off the CTO, not off the CEO directly."""
    for role in ("architect", "developer", "tester", "release-engineer", "data-engineer"):
        assert ROLE_PARENT[role] == "cto", f"{role} -> {ROLE_PARENT[role]!r}"


def test_the_ceo_is_not_everyones_manager() -> None:
    direct = [r for r, p in ROLE_PARENT.items() if p == "ceo"]
    assert len(direct) <= 6, (
        f"{len(direct)} roles report straight to the CEO ({sorted(direct)}); the tree has "
        "collapsed back to a flat organisation"
    )


def test_agents_md_states_the_tree(repo_root: Path) -> None:
    rows = _rows(repo_root / "templates" / "AGENTS.md")
    for role, parent in ROLE_PARENT.items():
        if role == "ceo":
            continue
        assert role in rows, f"templates/AGENTS.md has no row for {role}"
        assert (
            rows[role].startswith(parent.replace("-", " ").title()) or rows[role] == parent.upper()
        ), f"templates/AGENTS.md says {role} reports to {rows[role]!r}, config says {parent!r}"


def test_roles_reference_states_the_tree(repo_root: Path) -> None:
    rows = _rows(repo_root / "references" / "Roles.md")
    for role, parent in ROLE_PARENT.items():
        if role == "ceo":
            continue
        assert role in rows, f"references/Roles.md has no row for {role}"
        assert (
            rows[role].startswith(parent.replace("-", " ").title()) or rows[role] == parent.upper()
        ), f"references/Roles.md says {role} reports to {rows[role]!r}, config says {parent!r}"


def test_map_renders_the_tree(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from teamwork import engine

    assert engine.main(["map"]) == 0
    out = capsys.readouterr().out
    assert "reporting lines" in out
    lines = out.split("reporting lines", 1)[1].split("\nroles (", 1)[0]
    for role in ROLE_PARENT:
        assert re.search(rf"\b{re.escape(role.replace('-', ' ').title())}\b", lines, re.I), role
    indent = {m.group(2): len(m.group(1)) for m in re.finditer(r"^( +)(\S.*)$", lines, re.M)}
    cto = next(k for k in indent if k.strip() == "CTO")
    dev = next(k for k in indent if k.strip() == "Developer")
    assert indent[dev] > indent[cto], "the map prints a flat list, not a tree"
