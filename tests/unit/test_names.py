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
    # ``slugify`` guards against None via ``(text or "")``.
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
    # The last token being a digit keeps the instance suffix separated.
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


def test_git_identity_args_shape() -> None:
    args = engine.git_identity_args("developer")
    assert args == [
        "-c",
        "user.name=Developer",
        "-c",
        f"user.email=developer@{engine.IDENTITY_DOMAIN}",
    ]
