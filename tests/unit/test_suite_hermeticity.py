"""The suite must not inherit the team environment a lane process exports.

A lane carries ``TEAMWORK_ROOT`` and ``TEAMWORK_TEAM``, and ``engine.team_slug``
reads ``TEAMWORK_TEAM``, so an in-process call made from a fixture that builds a
throwaway project resolves the *live* team instead of the fixture's own. The
function-scoped ``isolated_workspace`` fixture cleared those names too late for
any module- or session-scoped fixture, which pytest builds first: every lane's
full run reported 36 errors in ``tests/integration/test_context_cli.py``
(``KeyError: 'T-0001'``) whose only cause was the ambient team name.

Owner: developer. Layer: unit. Area: suite hygiene.

The launcher is pinned for the same reason: ``pulse --commit`` and ``swarm run``
dispatch by default, and a test that dispatched without installing a fake launcher
resolved the host's own agent CLI (``pi`` on this host) and started a real lane that
ran a whole team run and left the checkout detached at ``main``.
"""

from __future__ import annotations

import os

import pytest

TEAM_ENV = ("TEAMWORK_ROOT", "TEAMWORK_TEAM")
LAUNCHER_ENV = "TEAMWORK_LANE_CMD"
SAFE_LAUNCHER = "/bin/true"


@pytest.fixture(scope="module")
def ambient_at_module_build() -> dict:
    """The team environment as a module-scoped fixture sees it, before any test body."""
    return {name: os.environ.get(name) for name in TEAM_ENV}


@pytest.fixture(scope="module")
def launcher_at_module_build() -> str | None:
    """The lane command as a module-scoped fixture sees it, before any test body."""
    return os.environ.get(LAUNCHER_ENV)


def test_module_scope_fixtures_see_no_ambient_team(ambient_at_module_build: dict) -> None:
    assert ambient_at_module_build == dict.fromkeys(TEAM_ENV), (
        "a module-scoped fixture was built with a lane's team environment in place, "
        "so every in-process team lookup inside it reads the live tree: "
        f"{ambient_at_module_build}"
    )


def test_no_test_body_sees_an_ambient_team() -> None:
    assert not [name for name in TEAM_ENV if name in os.environ]


def test_module_scope_fixtures_see_the_safe_launcher(launcher_at_module_build: str | None) -> None:
    assert launcher_at_module_build == SAFE_LAUNCHER, (
        "a module-scoped fixture was built with a real lane launcher in place, so a "
        f"dispatch inside it would start this host's agent CLI: {launcher_at_module_build!r}"
    )


def test_a_dispatching_test_starts_no_real_lane(project) -> None:
    from teamwork import lanes

    assert lanes.lane_command(project) == SAFE_LAUNCHER
    assert lanes.launcher_ready(project) == (True, ""), (
        "a pinned launcher must still read as ready, or the suite stops exercising "
        "the dispatch path instead of the real CLI"
    )


def test_a_test_that_installs_its_own_launcher_still_wins(project, monkeypatch) -> None:
    from teamwork import lanes

    monkeypatch.setenv(LAUNCHER_ENV, "/bin/false {prompt}")
    assert lanes.lane_command(project) == "/bin/false {prompt}"
