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
from teamwork.names import ROLE_DISPLAY


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


def reporting_children_of(role: str) -> list[str]:
    return [r for r in ROLE_REPORT_ORDER if ROLE_PARENT.get(r) == role]


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


def test_every_charter_states_its_own_line(repo_root: Path) -> None:
    """`ROLE_PARENT` is what an agent reads at startup, in its own charter.

    The charter is the file the startup routine tells every instance to read first,
    so a charter that names a different parent than `ROLE_PARENT` is the worst kind
    of drift: the doc the agent obeys contradicts the doc the map renders.
    """
    for role, parent in ROLE_PARENT.items():
        path = repo_root / "roles" / f"{role}.md"
        assert path.is_file(), f"missing charter {path}"
        text = path.read_text(encoding="utf-8")
        assert "## Reports to" in text, f"roles/{role}.md has no ## Reports to section"
        section = text.split("## Reports to", 1)[1].split("\n## ", 1)[0]
        if parent is None:
            assert "**The user" in section or "**user" in section.lower(), (
                f"roles/{role}.md must name the user as its line"
            )
            continue
        want = ROLE_DISPLAY.get(parent, parent)
        assert f"**{want}.**" in section, (
            f"roles/{role}.md does not name **{want}.** in its Reports-to section; "
            f"config.py says {role} -> {parent}"
        )


def test_every_manages_line_matches_the_tree(repo_root: Path) -> None:
    """A `Manages:` line lists exactly the roles whose parent is this role."""
    for role in ROLE_PARENT:
        path = repo_root / "roles" / f"{role}.md"
        text = path.read_text(encoding="utf-8")
        section = text.split("## Reports to", 1)[1].split("\n## ", 1)[0]
        expected = reporting_children_of(role)
        line = next((ln for ln in section.splitlines() if ln.startswith("Manages:")), None)
        if line is None:
            assert not expected, f"roles/{role}.md omits Manages: {expected}"
            continue
        names = {ROLE_DISPLAY.get(k, k) for k in expected}
        body = line[len("Manages:") :].split(".")[0]
        if not names:
            assert body.strip().lower().startswith("nobody"), (
                f"roles/{role}.md claims to manage {body.strip()!r} but no role reports to it"
            )
            continue
        listed = {n.strip() for n in body.split(",")}
        assert listed == names, (
            f"roles/{role}.md Manages: {sorted(listed)} but the tree gives {sorted(names)}"
        )


def test_reports_to_boilerplate_is_not_self_contradictory(repo_root: Path) -> None:
    """A role whose parent IS the CEO must not say 'not to the CEO'."""
    for role, parent in ROLE_PARENT.items():
        if parent != "ceo":
            continue
        text = (repo_root / "roles" / f"{role}.md").read_text(encoding="utf-8")
        assert "not to the CEO" not in text, (
            f"roles/{role}.md reports to the CEO and still says 'not to the CEO'"
        )


def _parent_cell(value: str) -> str:
    """Normalise a `Reports to` cell to exactly one role name.

    A row naming two managers ("CEO, CTO", "Product Manager, CEO") is the defect
    this tree removes - a role with two managers answers to neither - so the cell
    must hold exactly one name to pass. Comparing with ``startswith`` let
    "Product Manager, CEO" satisfy a `product-manager` parent, which is the very
    shape being forbidden.
    """
    cell = re.sub(r"\*\*|`", "", value).strip().rstrip(".")
    return cell


def _assert_states(rows: dict[str, str], where: str) -> None:
    for role, parent in ROLE_PARENT.items():
        if role == "ceo":
            continue
        assert role in rows, f"{where} has no row for {role}"
        cell = _parent_cell(rows[role])
        want = {ROLE_DISPLAY.get(parent, parent)}
        assert cell in want, (
            f"{where} says {role} reports to {cell!r}; config says "
            f"{ROLE_DISPLAY.get(parent, parent)!r} (exactly one manager per role)"
        )


def test_agents_md_states_the_tree(repo_root: Path) -> None:
    _assert_states(_rows(repo_root / "templates" / "AGENTS.md"), "templates/AGENTS.md")


def test_the_live_agents_md_matches_the_template(repo_root: Path) -> None:
    """The committed AGENTS.md is what every agent actually obeys.

    Regenerating the managed block (``teamwork agents-md``) or a hand edit could
    otherwise drift the live table while the template stays correct - the same
    decorative-surface defect as an unguarded charter.
    """
    path = repo_root / "AGENTS.md"
    live = _rows(path)
    if not live:
        # Skipping here would let a table header rename silently disable the pin,
        # so an existing file that parses to no rows is a failure, not a skip.
        assert not path.is_file(), (
            "AGENTS.md exists but its reporting table parsed to zero rows; the header "
            "must stay `| Role | Owns | Reports to |` or the tree goes unchecked"
        )
        pytest.skip("this checkout has no committed AGENTS.md")
    template = _rows(repo_root / "templates" / "AGENTS.md")
    assert live == template, (
        "AGENTS.md and templates/AGENTS.md disagree on the reporting tree; the live "
        "block is written by `teamwork.py agents-md`, so regenerate it rather than "
        "editing one side"
    )
    _assert_states(live, "AGENTS.md")


def test_roles_reference_states_the_tree(repo_root: Path) -> None:
    _assert_states(_rows(repo_root / "references" / "Roles.md"), "references/Roles.md")


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


def test_the_generated_brief_states_the_same_line_as_the_charter(
    repo_root: Path, tmp_path: Path
) -> None:
    """`StartHere.md` is read at step 1, before the charter, and is generated.

    A hard-coded "report to the CEO" here told every developer and tester to
    escalate past their own manager while their charter said the opposite - two
    files an agent obeys, contradicting each other. The brief has to be rendered
    from `ROLE_PARENT` like every other surface.
    """
    from teamwork import engine

    root = tmp_path / "Team"
    root.mkdir(parents=True, exist_ok=True)
    # A fully staffed team: every role has somewhere to report.
    staffed = set(ROLE_PARENT)
    for role, parent in ROLE_PARENT.items():
        brief = engine.start_here(f"{role}-1", role, root, tmp_path / "docs", staffed)
        body = " ".join(brief.split())
        assert "Report to the CEO:" not in body or parent == "ceo", (
            f"the generated brief for {role} tells it to report to the CEO, but "
            f"config.py says it reports to {parent}"
        )
        if parent is None:
            assert "only lane that" in body or "the user" in body
            continue
        want = ROLE_DISPLAY.get(parent, parent)
        assert f"You report to the **{want}**" in body, (
            f"the generated brief for {role} does not name {want} as its manager"
        )
        if parent == "ceo":
            # A CEO parent is the one case where "not to the CEO" would contradict
            # the same sentence, and the assertion above already forbids it.
            continue
        assert f"Report to the {want}:" in body, (
            f"the brief for {role} still says 'Report to the CEO' in the closing step"
        )


def test_a_vacant_manager_folds_to_the_nearest_staffed_ancestor(
    tmp_path: Path,
) -> None:
    """A slim roster has no CTO, so "report to the CTO" would be a dead address.

    The brief names a manager; naming one the team does not staff sends an agent
    to a mailbox nobody reads. It must fold upward and say which line is vacant.
    """
    from teamwork import engine

    root = tmp_path / "Team"
    root.mkdir(parents=True, exist_ok=True)
    slim = {"ceo", "developer", "architect", "tester", "reviewer"}
    brief = engine.start_here("developer-1", "developer", root, tmp_path / "docs", slim)
    body = " ".join(brief.split())
    assert "CTO, which this team does not staff" in body
    assert "Report to the CEO (CTO not staffed here)" in body
    assert "You report to the **CTO**" not in body

    # With the CTO staffed the same role reports to it again.
    full = engine.start_here("developer-1", "developer", root, tmp_path / "docs", set(ROLE_PARENT))
    assert "You report to the **CTO**" in " ".join(full.split())


def test_an_unbundled_role_does_not_get_the_users_ear(tmp_path: Path) -> None:
    """A role outside the tree falls back to the CEO, never to the user.

    The fallback charter already says "report to the CEO"; handing such a lane the
    CEO branch would tell a non-CEO agent it is the only lane that reaches the user.
    """
    from teamwork import engine

    root = tmp_path / "Team"
    root.mkdir(parents=True, exist_ok=True)
    brief = engine.start_here("auditor-1", "auditor", root, tmp_path / "docs", {"ceo"})
    body = " ".join(brief.split())
    assert "only lane that" not in body
    assert "Report to the user" not in body
    assert "report to the **CEO**" in body
