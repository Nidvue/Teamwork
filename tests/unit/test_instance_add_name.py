"""`instance add --name` must never turn a CLI-supplied name into a traversal.

M26 security finding S-1: ``resolve_role`` strips ``../../ceo`` to ``ceo``, so
the role check passed, and ``pascal`` preserves ``..``, so ``agent_dir`` escaped
the team tree and scaffolded a seat outside it. ``instance retire`` already
routes the name through ``names.safe_component``; ``add`` did not.

The rule here is refuse, never silently rewrite: a user who typed ``../..`` gets
an error naming the legal shape, and a legal name is unchanged.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine, names


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", "ceo,developer-1", "--no-git") == 0
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def tree(project: Path) -> set:
    return {p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_dir()}


def test_pascal_keeps_the_traversal_that_safe_component_removes():
    """The measured pre-fix state: the role check strips, the path helper does not."""
    assert names.resolve_role("../../ceo") == "ceo"
    assert names.pascal("../../ceo") == "../../ceo"
    assert names.safe_component(names.pascal("../../ceo")) == "ceo"


def test_instance_add_refuses_a_traversing_name(cli, project: Path) -> None:
    """`instance add ceo --name '../../ceo'` passes the role check and escaped."""
    root = init(cli, project)
    before = tree(project)

    code = cli("--project", project, "instance", "add", "ceo", "--name", "../../ceo")

    assert code != 0, "a name that safe_component had to change must be refused"
    assert tree(project) == before, "no directory may be created outside the team tree"
    assert "Ceo" not in {path.name for path in (root / engine.DIR_AGENTS).iterdir()}
    assert "Ceo" not in {path.name for path in root.parent.iterdir()}


def test_instance_add_refuses_a_traversing_name_inside_its_own_role(cli, project: Path) -> None:
    """The same escape one level up: the role check still says 'developer'."""
    root = init(cli, project)
    before = tree(project)

    code = cli("--project", project, "instance", "add", "developer", "--name", "../developer-2")

    assert code != 0
    assert tree(project) == before
    assert not (root / "Developer-2").exists()


def test_instance_add_still_creates_a_legal_name(cli, project: Path) -> None:
    root = init(cli, project)

    assert cli("--project", project, "instance", "add", "developer", "--name", "developer-2") == 0

    assert (root / engine.DIR_AGENTS / "Developer-2").is_dir()
