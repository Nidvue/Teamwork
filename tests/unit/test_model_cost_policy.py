"""D-20261117-CEO-4: no lane on a premium model without its own explicit allow."""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import engine

ECONOMY = {"provider": "deepinfra", "model": "deepseek-ai/DeepSeek-V4.1-Flash-1017"}


def _team(tmp_path: Path, roles=None, agents=None) -> Path:
    root = tmp_path / "Project"
    root.mkdir(parents=True, exist_ok=True)
    (root / "Settings.json").write_text(
        json.dumps({"Models": {"roles": roles or {}, "agents": agents or {}}}),
        encoding="utf-8",
    )
    return root


def test_an_economy_lane_is_not_a_violation(tmp_path: Path):
    root = _team(tmp_path, roles={"developer": ECONOMY, "reviewer": dict(ECONOMY)})
    assert engine.premium_lane_violations(root) == []


def test_a_premium_provider_is_a_violation(tmp_path: Path):
    root = _team(
        tmp_path,
        roles={
            "reviewer": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "developer": ECONOMY,
        },
    )
    violations = engine.premium_lane_violations(root)
    assert [(v["lane"], v["reason"]) for v in violations] == [("reviewer", "premium-provider")]


def test_a_premium_vendor_model_on_an_economy_provider_is_a_violation(tmp_path: Path):
    root = _team(
        tmp_path,
        roles={"reviewer": {"provider": "deepinfra", "model": "anthropic/claude-sonnet-4-6"}},
    )
    assert [v["reason"] for v in engine.premium_lane_violations(root)] == ["premium-model"]


def test_the_provider_match_ignores_case_and_padding(tmp_path: Path):
    root = _team(
        tmp_path, roles={"reviewer": {"provider": "  Anthropic ", "model": "claude-sonnet-4-6"}}
    )
    assert [v["reason"] for v in engine.premium_lane_violations(root)] == ["premium-provider"]


def test_an_allow_on_the_lane_clears_only_that_lane(tmp_path: Path):
    root = _team(
        tmp_path,
        agents={
            "Reviewer-2": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "allow_premium": True,
            }
        },
        roles={
            "reviewer": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "developer": ECONOMY,
        },
    )
    assert [v["lane"] for v in engine.premium_lane_violations(root)] == ["reviewer"]


def test_an_entry_with_no_model_is_a_violation(tmp_path: Path):
    root = _team(tmp_path, agents={"TechnicalWriter": {"provider": "", "model": ""}})
    assert [(v["lane"], v["reason"]) for v in engine.premium_lane_violations(root)] == [
        ("TechnicalWriter", "unset")
    ]


def test_no_settings_file_and_no_models_yield_no_violation(tmp_path: Path):
    empty = tmp_path / "Empty"
    empty.mkdir()
    assert engine.premium_lane_violations(empty) == []
    assert engine.premium_lane_violations(_team(tmp_path)) == []


def test_the_check_writes_nothing_and_repeats_its_answer(tmp_path: Path):
    root = _team(tmp_path, roles={"reviewer": {"provider": "anthropic", "model": "x"}})
    before = (root / "Settings.json").read_text(encoding="utf-8")
    first = engine.premium_lane_violations(root)
    second = engine.premium_lane_violations(root)
    assert first == second and len(first) == 1
    assert (root / "Settings.json").read_text(encoding="utf-8") == before


def test_the_audit_section_counts_what_it_prints(tmp_path: Path, capsys):
    root = _team(tmp_path, roles={"reviewer": {"provider": "anthropic", "model": "x"}})
    assert engine._audit_premium_lane_without_explicit_allow(root, [], None) == 1
    out = capsys.readouterr().out
    assert "## cost policy" in out and "reviewer" in out and "premium-provider" in out
    assert "D-20261117-CEO-4" in out


def test_the_audit_section_is_clean_on_an_economy_team(tmp_path: Path, capsys):
    root = _team(tmp_path, roles={"developer": ECONOMY})
    assert engine._audit_premium_lane_without_explicit_allow(root, [], None) == 0
    assert "- none" in capsys.readouterr().out
