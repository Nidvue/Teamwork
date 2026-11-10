"""Unit tests for skill-bundle resolution (teamwork.resources)."""

from __future__ import annotations

from pathlib import Path

import pytest

from teamwork import resources


def test_skill_root_honours_the_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text("x", encoding="utf-8")
    monkeypatch.setenv(resources.ENV_VAR, str(bundle))
    assert resources.skill_root() == bundle.resolve()


def test_skill_root_rejects_a_missing_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(resources.ENV_VAR, str(tmp_path / "does-not-exist"))
    with pytest.raises(FileNotFoundError):
        resources.skill_root()


def test_asset_joins_under_the_skill_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / "roles").mkdir(parents=True)
    monkeypatch.setenv(resources.ENV_VAR, str(bundle))
    assert resources.asset("roles", "developer.md") == (bundle.resolve() / "roles" / "developer.md")


def test_repo_bundle_has_the_expected_assets(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(resources.ENV_VAR, str(repo_root))
    assert resources.asset("SKILL.md").is_file()
    assert resources.has_asset("roles")
    assert resources.has_asset("templates")
    assert not resources.has_asset("no-such-asset")


def test_self_invocation_is_a_command(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(resources.ENV_VAR, str(repo_root))
    invocation = resources.self_invocation()
    assert isinstance(invocation, str)
    assert invocation.strip()
    assert "teamwork" in invocation


def test_looks_like_skill_detects_markers(tmp_path: Path) -> None:
    assert resources._looks_like_skill(None) is False
    assert resources._looks_like_skill(tmp_path / "missing") is False

    empty = tmp_path / "empty"
    empty.mkdir()
    assert resources._looks_like_skill(empty) is False

    marked = tmp_path / "marked"
    (marked / "references").mkdir(parents=True)
    assert resources._looks_like_skill(marked) is True
