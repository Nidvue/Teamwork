"""Unit tests for pure name/identity helpers: slugify, pascal, team_slug,
role_identity and identity_string."""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import engine


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Hello, World!", "hello-world"),
        ("Already-slug", "already-slug"),
        ("snake_case_name", "snake-case-name"),
        ("UPPER CASE", "upper-case"),
        ("  spaces   and   dashes -- ", "spaces-and-dashes"),
        ("", "work"),
        ("!!!", "work"),
        ("---", "work"),
    ],
)
def test_slugify_normalises_text(text: str, expected: str) -> None:
    assert engine.slugify(text) == expected


def test_slugify_none_is_work() -> None:
    assert engine.slugify(None) == "work"


def test_slugify_respects_limit() -> None:
    assert engine.slugify("hello world", limit=5) == "hello"


def test_slugify_never_ends_with_dash_after_truncation() -> None:
    out = engine.slugify("ab cd ef gh", limit=3)
    assert out == "ab"
    long = engine.slugify("a" * 50 + " tail", limit=10)
    assert len(long) <= 10
    assert not long.endswith("-")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("developer-2", "Developer-2"),
        ("product-manager", "ProductManager"),
        ("project-manager", "ProjectManager"),
        ("ceo", "CEO"),
        ("api-gateway", "APIGateway"),
        ("ui-designer", "UIDesigner"),
        ("my_team name", "MyTeamName"),
        ("", "Team"),
    ],
)
def test_pascal(name: str, expected: str) -> None:
    assert engine.pascal(name) == expected


def test_pascal_keeps_trailing_instance_number() -> None:
    assert engine.pascal("tester-10") == "Tester-10"


def test_team_slug_from_directory_name() -> None:
    assert engine.team_slug(Path("/work/My Cool Project")) == "MyCoolProject"


def test_team_slug_explicit_wins() -> None:
    assert engine.team_slug(Path("/work/x"), "Friendly Team") == "FriendlyTeam"


def test_team_slug_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMWORK_TEAM", "Env Team")
    assert engine.team_slug(Path("/work/x")) == "EnvTeam"


def test_team_slug_explicit_beats_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMWORK_TEAM", "Env Team")
    assert engine.team_slug(Path("/work/x"), "Explicit") == "Explicit"


def test_team_slug_unusable_name_falls_back_to_team() -> None:
    assert engine.team_slug(Path("/work/x"), "!!!") == "Team"


@pytest.mark.parametrize(
    "role,name,local",
    [
        ("developer", "Developer", "developer"),
        ("developer-2", "Developer", "developer"),
        ("product-manager", "Product Manager", "productmanager"),
        ("security-auditor", "Security Auditor", "securityauditor"),
        ("ceo", "CEO", "ceo"),
        ("reviewer-1", "Reviewer", "reviewer"),
    ],
)
def test_role_identity_is_role_based(role: str, name: str, local: str) -> None:
    who = engine.role_identity(role)
    assert who[0] == name
    assert who[1] == f"{local}@{engine.IDENTITY_DOMAIN}"


def test_role_identity_never_uses_instance_number() -> None:
    assert engine.role_identity("developer-2") == engine.role_identity("developer-7")


def test_identity_string_format() -> None:
    assert engine.identity_string("reviewer-1") == (f"Reviewer <reviewer@{engine.IDENTITY_DOMAIN}>")


def test_git_identity_args_shape(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    project = tmp_path / "no-identity"
    project.mkdir()
    engine.run_git(project, "init", "-q")
    args = engine.git_identity_args("developer", project)
    assert args == [
        "-c",
        "user.name=Developer",
        "-c",
        f"user.email=developer@{engine.IDENTITY_DOMAIN}",
    ]


def test_the_declared_preset_wins_over_the_role_mailbox(tmp_path: Path) -> None:
    project = tmp_path / "preset"
    project.mkdir()
    engine.run_git(project, "init", "-q")
    engine.run_git(project, "config", "--local", "teamwork.identity.name", "Ops Person")
    engine.run_git(project, "config", "--local", "teamwork.identity.email", "ops@example.com")
    assert engine.commit_identity("developer", project) == ("Ops Person", "ops@example.com")
    assert engine.git_identity_args("developer", project) == [
        "-c",
        "user.name=Ops Person",
        "-c",
        "user.email=ops@example.com",
    ]


def test_the_configured_pair_authors_the_commit(tmp_path: Path) -> None:
    """The repository's own ``user.name``/``user.email`` authors its commits.

    Decision 2026-11-11: published history names the project, not the agent, so the
    configured pair is the default and the role mailbox is an opt-in.
    """
    project = tmp_path / "ambient"
    project.mkdir()
    engine.run_git(project, "init", "-q")
    engine.run_git(project, "config", "--local", "user.name", "Ops Person")
    engine.run_git(project, "config", "--local", "user.email", "ops@example.com")
    assert engine.declared_identity(project) is None
    assert engine.commit_identity("developer", project) == ("Ops Person", "ops@example.com")


def test_the_role_mailbox_is_an_opt_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "opt-in"
    project.mkdir()
    engine.run_git(project, "init", "-q")
    engine.run_git(project, "config", "--local", "user.name", "Ops Person")
    engine.run_git(project, "config", "--local", "user.email", "ops@example.com")
    monkeypatch.setenv("TEAMWORK_COMMIT_IDENTITY", "role")
    assert engine.commit_identity("developer", project) == (
        "Developer",
        f"developer@{engine.IDENTITY_DOMAIN}",
    )


def test_a_half_declared_preset_is_no_preset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "half-preset"
    project.mkdir()
    engine.run_git(project, "init", "-q")
    engine.run_git(project, "config", "--local", "teamwork.identity.name", "Ops Person")
    assert engine.declared_identity(project) is None
    monkeypatch.setenv("TEAMWORK_COMMIT_IDENTITY", "role")
    assert engine.commit_identity("ceo", project) == ("CEO", f"ceo@{engine.IDENTITY_DOMAIN}")


def test_the_identity_environment_pins_both_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMWORK_COMMIT_IDENTITY", "role")
    env = engine.git_identity_env("developer")
    assert env == {
        "GIT_AUTHOR_NAME": "Developer",
        "GIT_AUTHOR_EMAIL": f"developer@{engine.IDENTITY_DOMAIN}",
        "GIT_COMMITTER_NAME": "Developer",
        "GIT_COMMITTER_EMAIL": f"developer@{engine.IDENTITY_DOMAIN}",
    }
