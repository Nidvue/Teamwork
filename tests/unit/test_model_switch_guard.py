"""The model the user configured is kept unless a switch is explicitly demanded.

D-20261123-CEO-4: switching is an opt-in act, never a background behaviour.
Every test here runs the real CLI so the guard, the dry run and the ledger are
proved together.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ROSTER = "ceo,reviewer-1,reviewer-2,developer-1"
STRONG = "deepinfra/strong-model"
ECONOMY = "deepinfra/economy-model"
ALT = "deepinfra/alt-model"


def _root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def _team(cli, tmp_path: Path, monkeypatch, **env) -> tuple:
    project = tmp_path / "Project"
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    for var in engine.HOST_MODEL_VARS + (
        "TEAMWORK_MODEL_PROVIDER",
        "TEAMWORK_MODEL_ALT",
        "PI_PROVIDER",
    ):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    return project, _root(project)


def _settings(root: Path) -> dict:
    path = engine.providers_path(root)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _models(root: Path) -> dict:
    models = _settings(root).get("Models") or {}
    merged = dict(models.get("roles") or {})
    merged.update(models.get("agents") or {})
    return {lane: entry.get("model") for lane, entry in merged.items()}


def test_apply_without_a_demand_refuses_and_writes_nothing(
    cli, tmp_path: Path, monkeypatch, capsys
):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
    )
    assert cli("--project", project, "model", "set", "reviewer-1", "--model", "user-default") == 0
    before = _settings(root)
    assert cli("--project", project, "model", "auto", "--apply") != 0
    assert "refusing to switch models" in capsys.readouterr().err
    assert _settings(root) == before
    assert _models(root)["Reviewer-1"] == "user-default"


def test_allow_switch_without_a_reason_is_not_a_demand(cli, tmp_path: Path, monkeypatch, capsys):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
    )
    before = _settings(root)
    assert cli("--project", project, "model", "auto", "--apply", "--allow-switch") != 0
    assert "--reason" in capsys.readouterr().err
    assert _settings(root) == before


def test_a_blank_reason_is_not_a_demand(cli, tmp_path: Path, monkeypatch, capsys):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
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
            "   ",
        )
        != 0
    )
    assert "--reason" in capsys.readouterr().err
    assert _settings(root) == before


def test_dry_run_needs_no_demand_and_writes_nothing(cli, tmp_path: Path, monkeypatch, capsys):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
    )
    assert cli("--project", project, "model", "set", "reviewer-1", "--model", "user-default") == 0
    before = _settings(root)
    assert cli("--project", project, "model", "auto") == 0
    out = capsys.readouterr().out
    assert "dry run" in out and "model switching is off" in out
    assert _settings(root) == before


def test_an_authorized_apply_writes_the_plan_and_records_why(cli, tmp_path: Path, monkeypatch):
    project, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ECONOMY=ECONOMY,
    )
    reason = "the user asked for economy lanes"
    assert (
        cli(
            "--project",
            project,
            "model",
            "auto",
            "--apply",
            "--allow-switch",
            "--reason",
            reason,
        )
        == 0
    )
    models = _models(root)
    assert models["ceo"] == STRONG
    assert models["developer"] == ECONOMY
    assert reason in engine.ledger_path(root).read_text(encoding="utf-8")


def test_alt_is_inert_without_an_authorization(cli, tmp_path: Path, monkeypatch):
    _, root = _team(
        cli,
        tmp_path,
        monkeypatch,
        TEAMWORK_MODEL_STRONG=STRONG,
        TEAMWORK_MODEL_ALT=ALT,
    )
    default_plan = engine.resolve_model_plan(root)
    assert default_plan["allow_switch"] is False
    assert default_plan["assignments"]["reviewer"]["model"] == STRONG
    assert not any(lane.startswith("Reviewer-") for lane in default_plan["assignments"])
    assert any("switching is off" in note for note in default_plan["notes"])

    authorized = engine.resolve_model_plan(root, allow_switch=True)
    assert authorized["allow_switch"] is True
    assert (
        len({authorized["assignments"][lane]["model"] for lane in ("Reviewer-1", "Reviewer-2")})
        == 2
    )
