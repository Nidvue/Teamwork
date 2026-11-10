"""The board's feature section: open features only, grouped by owner and squad.

The board is a render, so the feature table must be produced from
`docs/Team/Features.md` and the `Agents/<Instance>/Team.md` attachments, never
hand-edited. Closed features are history, not board rows.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import board, engine

AGENTS = "ceo,architect-1,team-leader-1,developer-1,reviewer-1"


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def test_the_feature_section_lists_open_features_with_their_squad(cli, project) -> None:
    root = init(cli, project)
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
            "developer-3",
        )
        == 0
    )
    assert cli("--project", project, "task", "add", "developer", "the work") == 0
    engine.write_features(
        project / "docs" / "Team" / "Features.md",
        [
            engine.new_feature(
                "ships the view", "team-leader-1", ["src/view.py"], "-", [], "active"
            ),
            engine.new_feature("ships history", "team-leader-1", ["src/old.py"], "-", [], "done"),
        ],
    )

    text = (project / "docs" / "Team" / "Board.md").read_text(encoding="utf-8")
    after = board.render(board.queues(root), text, root)

    assert "| F-0001 | active | team-leader-1 | Developer-3 | src/view.py |" in after
    assert "F-0002" not in after, "a closed feature is history, not a board row"
    assert after.count("Shared services serve every feature") == 1
    assert (
        "Shared services serve every feature and are attached to none: Architect, CEO, CFO, COO, "
        "CTO, Project Manager, Release Engineer, Reviewer, Security Auditor." in after
    )


def test_the_section_is_inserted_once_at_render_time(cli, project) -> None:
    """A board without the section gains it at the merge render, exactly once."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "the work") == 0
    tasks = board.queues(root)
    text = (project / "docs" / "Team" / "Board.md").read_text(encoding="utf-8")
    start = text.index("## Feature teams (rendered)")
    end = text.index("## In flight")
    stripped = text[:start] + text[end:]

    without_root = board.render(tasks, stripped)
    assert without_root == board.render(tasks, stripped, None)
    assert board.FEATURE_HEAD not in without_root, "no root, no feature section"

    after = board.render(tasks, stripped, root)
    assert after.count("## Feature teams (rendered)") == 1
    assert after.count("| feature |") == 1
    assert board.render(tasks, after, root) == after, "a second render is a no-op"


def test_a_stale_shared_services_sentence_is_rewritten(cli, project) -> None:
    """The sentence is rendered too: a board written before the list grew is fixed."""
    root = init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "the work") == 0
    text = (project / "docs" / "Team" / "Board.md").read_text(encoding="utf-8")
    stale = text.replace(
        "Architect, CEO, CFO, COO, CTO, Project Manager, Release Engineer, Reviewer, Security Auditor.",
        "Architect, Project Manager.",
    )
    assert "Architect, Project Manager." in stale

    after = board.render(board.queues(root), stale, root)

    assert "Architect, CEO, CFO, COO, CTO" in after
    assert "Architect, Project Manager." not in after


def test_a_project_without_feature_records_still_renders(cli, project) -> None:
    """A team that has filed no feature has no records; every gate over [] is green."""
    root = init(cli, project)
    (project / "docs" / "Team" / "Features.md").unlink()
    assert cli("--project", project, "task", "add", "developer", "the work") == 0
    text = (project / "docs" / "Team" / "Board.md").read_text(encoding="utf-8")

    after = board.render(board.queues(root), text, root)

    assert "## Feature teams (rendered)" in after
    assert board.FEATURE_HEAD in after
