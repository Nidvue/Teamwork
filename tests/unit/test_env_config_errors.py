"""Regression: a malformed ``TEAMWORK_*`` number is a usage error, not a traceback.

Before this, ``config`` and ``io`` parsed their environment at import with a bare
``int()``/``float()``, so ``TEAMWORK_SHORT_CAP=abc teamwork.py version`` died with
a ``ValueError`` traceback from ``config.py:223`` for *every* command, and the
message named neither the variable nor a fix (M19 engine audit, finding 5).

The contract now: a blank value is unset, a valid value is parsed, and a
malformed one prints one line naming the variable and exits 2 (usage) with no
traceback and no file written. The parse stays inside ``config.py`` because
Architecture section 3 freezes the level-1 import direction (``config`` ->
``resources`` only), so the helper is not shared with ``io.py``

Owner: developer. Task: T-0011. Layer: unit (area config-env).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "teamwork.py"
SRC = REPO_ROOT / "src"

INT_DEFAULTS = {
    "TEAMWORK_SLOT_TTL_MINUTES": 90,
    "TEAMWORK_REVIEW_FAIL_LIMIT": 3,
    "TEAMWORK_REVIEW_LEASE_MINUTES": 20,
    "TEAMWORK_MEMORY_LEASE_MINUTES": 30,
    "TEAMWORK_MEMORY_STALL_MINUTES": 15,
    "TEAMWORK_SHORT_CAP": 24,
    "TEAMWORK_LONG_CAP": 64,
    "TEAMWORK_ARCHIVE_CAP": 256,
    "TEAMWORK_STALE_DAYS": 3,
    "TEAMWORK_MIN_USES": 2,
    "TEAMWORK_PROMOTE_MIN_IMPORTANCE": 2,
    "TEAMWORK_MAX_DISPUTE_ROUNDS": 3,
}

CONSTANTS = {
    "TEAMWORK_SLOT_TTL_MINUTES": "SLOT_TTL_MINUTES",
    "TEAMWORK_REVIEW_FAIL_LIMIT": "REVIEW_FAIL_LIMIT",
    "TEAMWORK_REVIEW_LEASE_MINUTES": "REVIEW_LEASE_MINUTES",
    "TEAMWORK_MEMORY_LEASE_MINUTES": "MEMORY_LEASE_MINUTES",
    "TEAMWORK_MEMORY_STALL_MINUTES": "MEMORY_STALL_MINUTES",
    "TEAMWORK_SHORT_CAP": "SHORT_CAP",
    "TEAMWORK_LONG_CAP": "LONG_CAP",
    "TEAMWORK_ARCHIVE_CAP": "ARCHIVE_CAP",
    "TEAMWORK_STALE_DAYS": "STALE_DAYS",
    "TEAMWORK_MIN_USES": "MIN_USES",
    "TEAMWORK_PROMOTE_MIN_IMPORTANCE": "PROMOTE_MIN_IMPORTANCE",
    "TEAMWORK_MAX_DISPUTE_ROUNDS": "MAX_ROUNDS",
}


def _env(overrides: dict[str, str], cwd: Path) -> dict[str, str]:
    env = dict(os.environ)
    for name in INT_DEFAULTS:
        env.pop(name, None)
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONPYCACHEPREFIX"] = str(cwd / "__pycache__")
    env.update(overrides)
    return env


def _cli(overrides: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "version"],
        capture_output=True,
        text=True,
        env=_env(overrides, cwd),
        cwd=cwd,
        timeout=120,
    )


def _value(name: str, cwd: Path, overrides: dict[str, str] | None = None) -> str:
    constant = CONSTANTS[name]
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from teamwork import config; print(config.{constant})",
        ],
        capture_output=True,
        text=True,
        env=_env(overrides or {}, cwd),
        cwd=cwd,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@pytest.mark.parametrize("name", sorted(INT_DEFAULTS))
def test_a_malformed_integer_exits_two_naming_the_variable(name: str, tmp_path: Path) -> None:
    done = _cli({name: "abc"}, tmp_path)
    assert done.returncode == 2, (done.returncode, done.stderr)
    assert name in done.stderr
    assert "must be an integer" in done.stderr
    assert "Traceback" not in done.stderr
    assert "ValueError" not in done.stderr
    assert list(tmp_path.glob("*.md")) == []


@pytest.mark.parametrize("name", sorted(INT_DEFAULTS))
def test_a_blank_value_is_unset_and_keeps_the_default(name: str, tmp_path: Path) -> None:
    done = _cli({name: "   "}, tmp_path)
    assert done.returncode == 0, done.stderr
    assert _value(name, tmp_path, {name: "   "}) == str(INT_DEFAULTS[name])


def test_a_valid_integer_is_parsed(tmp_path: Path) -> None:
    assert _value("TEAMWORK_SHORT_CAP", tmp_path) == "24"
    done = _cli({"TEAMWORK_SHORT_CAP": "7"}, tmp_path)
    assert done.returncode == 0, done.stderr
    assert _value("TEAMWORK_SHORT_CAP", tmp_path, {"TEAMWORK_SHORT_CAP": "7"}) == "7"


def test_the_error_is_the_same_on_a_second_call(tmp_path: Path) -> None:
    first = _cli({"TEAMWORK_LONG_CAP": "64x"}, tmp_path)
    second = _cli({"TEAMWORK_LONG_CAP": "64x"}, tmp_path)
    assert (first.returncode, first.stderr) == (second.returncode, second.stderr)
    assert first.returncode == 2
