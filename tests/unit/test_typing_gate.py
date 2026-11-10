"""The type gate covers the whole runtime: no module carries a standing exemption."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_no_mypy_override_exempts_a_runtime_module() -> None:
    mypy = _pyproject()["tool"]["mypy"]
    exempt = [
        module
        for override in mypy.get("overrides", [])
        if override.get("ignore_errors")
        for module in override.get("module", [])
    ]
    assert exempt == [], f"mypy still exempts {exempt}: the gate must cover every module"
    assert not mypy.get("ignore_errors"), "[tool.mypy] must not exempt the whole file set"


def test_the_command_layer_is_inside_the_checked_file_set() -> None:
    assert _pyproject()["tool"]["mypy"]["files"] == ["src/teamwork"]
    assert (ROOT / "src/teamwork/engine.py").is_file()
    assert (ROOT / "src/teamwork/engine.py").stat().st_size > 0


def test_the_second_checker_excludes_no_module() -> None:
    pyright = _pyproject()["tool"]["pyright"]
    assert pyright.get("exclude", []) == []
    assert pyright.get("ignore", []) == []
    assert pyright["include"] == ["src/teamwork"]
