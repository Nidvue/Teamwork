"""T-0094: `model auto --apply` writes only a model the operator named.

The guard used to ask "is any team model variable set?", so naming only
TEAMWORK_MODEL_ECONOMY plus a host PI_MODEL routed every strong lane to the
unpriced host premium default and applied it. The guard now reads the origin of
each value it would write.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,architect,developer-1,reviewer-1,reviewer-2"
ECONOMY = "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017"
PREMIUM = "anthropic/claude-sonnet-4-6"


def _root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def _team(cli, tmp_path: Path, monkeypatch, **env) -> tuple:
    project = tmp_path / "Project"
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    for var in engine.HOST_MODEL_VARS + (
        "TEAMWORK_MODEL_PROVIDER",
        "TEAMWORK_MODEL_ALLOW_PREMIUM",
        "PI_PROVIDER",
    ):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    root = _root(project)
    return project, root


def _settings(root: Path) -> dict:
    path = engine.providers_path(root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _applied_models(root: Path) -> dict:
    models = _settings(root).get("Models") or {}
    merged = dict(models.get("roles") or {})
    merged.update(models.get("agents") or {})
    return {role: entry.get("model") for role, entry in merged.items()}


def test_only_economy_named_refuses_the_host_default(cli, tmp_path, monkeypatch, capsys):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
        PI_MODEL=PREMIUM,
    )
    before = _settings(root)
    assert (
        cli(
            "--project",
            project,
            "model",
            "auto",
            "--apply",
            "--allow-switch",
            "--reason",
            "the operator named these models",
        )
        != 0
    )
    printed = capsys.readouterr().err
    assert "host default" in printed and "PI_MODEL" in printed and PREMIUM in printed
    assert _settings(root) == before
    assert PREMIUM not in json.dumps(_applied_models(root))


def test_every_model_named_is_applied(cli, tmp_path, monkeypatch):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=PREMIUM,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
        PI_MODEL="openai/whatever-the-host-had",
    )
    assert (
        cli(
            "--project",
            project,
            "model",
            "auto",
            "--apply",
            "--allow-switch",
            "--reason",
            "the operator named these models",
        )
        == 0
    )
    applied = _applied_models(root)
    assert applied["developer"] == ECONOMY
    assert applied["ceo"] == PREMIUM


def test_an_env_allow_does_not_take_the_host_default(cli, tmp_path, monkeypatch):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
        PI_MODEL=PREMIUM,
        TEAMWORK_MODEL_ALLOW_PREMIUM=PREMIUM,
    )
    before = _settings(root)
    assert (
        cli(
            "--project",
            project,
            "model",
            "auto",
            "--apply",
            "--allow-switch",
            "--reason",
            "the operator named these models",
        )
        != 0
    )
    assert _settings(root) == before
    assert PREMIUM not in json.dumps(_applied_models(root))


def test_the_plan_names_the_variable_each_model_came_from(cli, tmp_path, monkeypatch):
    _, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
        PI_MODEL=PREMIUM,
    )
    plan = engine.resolve_model_plan(root)
    ceo = plan["assignments"]["ceo"]
    developer = plan["assignments"]["developer"]
    assert (ceo["model"], ceo["source"], ceo["named"]) == (PREMIUM, "PI_MODEL", False)
    assert (developer["model"], developer["source"], developer["named"]) == (
        ECONOMY,
        "TEAMWORK_MODEL_ECONOMY",
        True,
    )


def test_a_named_strong_model_is_its_own_origin(cli, tmp_path, monkeypatch):
    _, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=ECONOMY,
        PI_MODEL=PREMIUM,
    )
    plan = engine.resolve_model_plan(root)
    assert plan["assignments"]["ceo"]["source"] == "TEAMWORK_MODEL_STRONG"
    assert plan["assignments"]["ceo"]["named"] is True
    assert plan["assignments"]["developer"]["source"] == "TEAMWORK_MODEL_STRONG"


def test_nothing_named_still_refuses_and_writes_nothing(cli, tmp_path, monkeypatch):
    project, root = _team(cli, tmp_path, monkeypatch, PI_MODEL=PREMIUM)
    before = _settings(root)
    assert (
        cli(
            "--project",
            project,
            "model",
            "auto",
            "--apply",
            "--allow-switch",
            "--reason",
            "the operator named these models",
        )
        != 0
    )
    assert _settings(root) == before
