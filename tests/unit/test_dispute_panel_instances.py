"""The dispute panel is computed at INSTANCE level (T-0009, Reviewer-1 finding F-P1).

A dispute names agents, not roles: ``raised_by`` and ``against`` hold the two
instances between it. The old panel test compared them at role level, so a
dispute between two instances of one role (Reviewer-1 vs Reviewer-2) dropped the
whole ``reviewer`` role from the panel - and with it Reviewer-3, the uninvolved
instance of the very same role and exactly the neutral seat the charter
promises. Measured on the pre-fix tree: ``required_tribunal`` -> ``['ceo']``,
``dispute sign D-0001 --by Reviewer-3`` -> "only the tribunal may sign: ceo", and
``dispute resolve D-0001 --by Reviewer-3`` -> "only the tribunal may resolve:
ceo". The ruling could not be issued through the shipped mechanism at all.

The rule these tests pin:

* an INSTANCE is a party when it is named in ``raised_by``/``against``;
* a ROLE leaves the panel only when EVERY one of its instances is a party, so an
  uninvolved instance of a party role can take the neutral seat;
* a party may never sign or resolve, and ``--force`` does not buy it that.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,developer-1,tester-1,reviewer-1,reviewer-2,reviewer-3"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path, agents: str = ROSTER) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    return team_root(project)


def open_dispute(cli, project: Path, raiser: str, against: str) -> None:
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            raiser,
            "--against",
            against,
            "--topic",
            "role-mates",
            "--position",
            "p",
            "--evidence",
            "e",
        )
        == 0
    )
    assert cli("--project", project, "dispute", "escalate", "D-0001", "--by", raiser) == 0


def dispute_of(project: Path) -> dict:
    root = team_root(project)
    return engine.parse_disputes(engine.disputes_path(root))[0]


def test_a_third_reviewer_seats_a_dispute_between_two_reviewers(cli, project: Path) -> None:
    """The defect: the neutral seat was locked out of a role-mate dispute.

    Reviewer-1 and Reviewer-2 are the parties; Reviewer-3 is not. The role-level
    test dropped the whole ``reviewer`` role from the panel, so Reviewer-3 was
    refused as "not the tribunal" - and the ruling had to be filed as a dispute
    round instead, leaving the CEO with a ruling that carries no ``signed=[...]``.
    """
    init(cli, project)
    open_dispute(cli, project, "reviewer-1", "reviewer-2")

    assert "reviewer" in engine.required_tribunal(team_root(project), dispute_of(project))
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-3") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "reviewer-3",
            "--decision",
            "neutral ruling",
        )
        == 0
    )
    resolved = dispute_of(project)
    assert resolved["status"] == "resolved"
    assert resolved["decision"] == "neutral ruling"
    assert "reviewer" in resolved["signed"]


def test_the_reviewer_role_leaves_the_panel_when_every_instance_is_a_party(
    cli, project: Path
) -> None:
    """A role is excluded only when EVERY one of its instances is a party.

    With Reviewer-1 and Reviewer-2 both in the dispute and no Reviewer-3, the
    role cannot be staffed neutrally, so it must leave the panel - otherwise the
    party rule would be defeated by its own panel.
    """
    init(cli, project, agents="ceo,developer-1,tester-1,reviewer-1,reviewer-2")
    open_dispute(cli, project, "reviewer-1", "reviewer-2")

    panel = engine.required_tribunal(team_root(project), dispute_of(project))
    assert "reviewer" not in panel
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") != 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-2") != 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0


def test_a_party_instance_can_never_sign_or_resolve(cli, project: Path) -> None:
    """The guarantee the fix must not weaken: no party rules its own dispute.

    The panel now seats the uninvolved Reviewer-3, so the party check is the
    only thing keeping Reviewer-1 and Reviewer-2 out. ``--force`` does not buy
    a party the ruling: it only bypasses the signature requirement.
    """
    init(cli, project)
    open_dispute(cli, project, "reviewer-1", "reviewer-2")
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-3") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0

    for party in ("reviewer-1", "reviewer-2"):
        assert (
            cli(
                "--project",
                project,
                "dispute",
                "sign",
                "D-0001",
                "--by",
                party,
            )
            != 0
        ), f"{party} signed a dispute it is a party to"
        assert (
            cli(
                "--project",
                project,
                "dispute",
                "resolve",
                "D-0001",
                "--by",
                party,
                "--decision",
                "I rule for my own side",
            )
            != 0
        ), f"{party} ruled a dispute it is a party to"
        assert (
            cli(
                "--project",
                project,
                "dispute",
                "resolve",
                "D-0001",
                "--by",
                party,
                "--decision",
                "I rule for my own side",
                "--force",
                "I am the only one left",
            )
            != 0
        ), f"--force let {party} rule a dispute it is a party to"


def test_a_non_party_dispute_is_unchanged(cli, project: Path) -> None:
    """The ordinary case keeps its old shape: a Reviewer who is not a party sits.

    The panel of a dispute between two other roles is still ceo + reviewer, the
    Reviewer signs and rules it, and a party - here the Developer who raised it
    - still cannot.
    """
    init(cli, project)
    open_dispute(cli, project, "developer-1", "tester-1")

    assert engine.required_tribunal(team_root(project), dispute_of(project)) == [
        "ceo",
        "reviewer",
    ]
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "reviewer-1") == 0
    assert cli("--project", project, "dispute", "sign", "D-0001", "--by", "ceo") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "reviewer-1",
            "--decision",
            "neutral ruling",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "developer-1",
            "--decision",
            "I rule for my own side",
        )
        != 0
    )


def test_the_party_test_is_per_instance_not_per_role(cli, project: Path) -> None:
    """The unit behind the rule: the party set holds the two named instances."""
    init(cli, project)
    open_dispute(cli, project, "reviewer-1", "reviewer-2")
    root = team_root(project)
    d = dispute_of(project)

    assert engine._dispute_party_instances(root, d) == {"Reviewer-1", "Reviewer-2"}
    assert engine._dispute_party_instance(root, d, "Reviewer-1")
    assert engine._dispute_party_instance(root, d, "Reviewer-2")
    assert not engine._dispute_party_instance(root, d, "Reviewer-3")
    assert not engine._dispute_party_instance(root, d, "CEO")
