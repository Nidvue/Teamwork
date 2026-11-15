"""A non-escalated dispute belongs to the CEO, and that rule speaks first (T-0075).

Measured defect on D-0016 (``Reviewer-2 -> CEO``, not escalated): ``dispute
resolve D-0016 --by ceo`` answered "only the tribunal may resolve: cto,
reviewer". The panel gate ran before the non-escalated owner rule, so the role
that owns arbitration was pointed at a mechanism that may not act on that
dispute at all - and the tribunal was pointed at a case it had not been given.

The rule these tests pin:

* a NON-escalated dispute is the CEO's: the panel gate does not apply to it;
* a CEO who is a party is told to escalate, because no party rules its own case
  and the escalation is the only exit;
* an ESCALATED dispute still needs the panel and every signature.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine

ROSTER = "ceo,cto,developer-1,tester-1,reviewer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0


def open_dispute(cli, project: Path, against: str) -> None:
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "open",
            "--by",
            "developer-1",
            "--against",
            against,
            "--topic",
            "scope",
            "--position",
            "p",
            "--evidence",
            "e",
        )
        == 0
    )


def dispute_of(project: Path) -> dict:
    return engine.parse_disputes(engine.disputes_path(team_root(project)))[0]


def test_the_ceo_resolves_a_non_escalated_dispute(cli, project: Path) -> None:
    """The owner of arbitration rules its own case without the panel gate."""
    init(cli, project)
    open_dispute(cli, project, "tester-1")
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "ceo",
            "--decision",
            "the CEO's ruling",
        )
        == 0
    )
    d = dispute_of(project)
    assert d["status"] == "resolved"
    assert d["decision"] == "the CEO's ruling"


def test_only_the_ceo_resolves_a_non_escalated_dispute(cli, project: Path, capsys) -> None:
    """A non-CEO is told the owner rule, not the panel rule."""
    init(cli, project)
    open_dispute(cli, project, "tester-1")
    capsys.readouterr()
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
            "x",
        )
        == 1
    )
    err = capsys.readouterr().err
    assert "not escalated: only the CEO resolves it" in err
    assert "Escalate it first" in err
    assert dispute_of(project)["status"] != "resolved"


def test_a_ceo_who_is_a_party_is_told_to_escalate(cli, project: Path, capsys) -> None:
    """The measured defect: the CEO got the panel message on its own case."""
    init(cli, project)
    open_dispute(cli, project, "ceo")
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "ceo",
            "--decision",
            "x",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "is a party to this dispute and cannot rule it" in err
    assert "Escalate it" in err
    assert "only the tribunal may resolve" not in err
    assert dispute_of(project)["status"] != "resolved"


def test_the_escalation_is_the_exit_for_a_ceo_party_dispute(cli, project: Path) -> None:
    """After escalation the neutral panel signs and rules - no deadlock."""
    init(cli, project)
    open_dispute(cli, project, "ceo")
    assert cli("--project", project, "dispute", "escalate", "D-0001", "--by", "developer-1") == 0
    panel = engine.required_tribunal(team_root(project), dispute_of(project))
    assert panel == ["cto", "reviewer"]
    for signer in panel:
        assert cli("--project", project, "dispute", "sign", "D-0001", "--by", signer) == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "cto",
            "--decision",
            "panel ruling",
        )
        == 0
    )
    assert dispute_of(project)["decision"] == "panel ruling"


def test_an_escalated_dispute_still_needs_the_signatures(cli, project: Path) -> None:
    """The panel gate and the signature gate stay in force for an escalated case."""
    init(cli, project)
    open_dispute(cli, project, "tester-1")
    assert cli("--project", project, "dispute", "escalate", "D-0001", "--by", "developer-1") == 0
    assert (
        cli(
            "--project",
            project,
            "dispute",
            "resolve",
            "D-0001",
            "--by",
            "tester-1",
            "--decision",
            "x",
        )
        != 0
    )
    assert (
        cli("--project", project, "dispute", "resolve", "D-0001", "--by", "ceo", "--decision", "x")
        != 0
    )
    assert dispute_of(project)["status"] != "resolved"
