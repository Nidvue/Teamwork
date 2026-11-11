"""The suite must not inherit the team environment a lane process exports.

A lane carries ``TEAMWORK_ROOT`` and ``TEAMWORK_TEAM``, and ``engine.team_slug``
reads ``TEAMWORK_TEAM``, so an in-process call made from a fixture that builds a
throwaway project resolves the *live* team instead of the fixture's own. The
function-scoped ``isolated_workspace`` fixture cleared those names too late for
any module- or session-scoped fixture, which pytest builds first: every lane's
full run reported 36 errors in ``tests/integration/test_context_cli.py``
(``KeyError: 'T-0001'``) whose only cause was the ambient team name.

Owner: developer. Layer: unit. Area: suite hygiene.
"""

from __future__ import annotations

import os

import pytest

TEAM_ENV = ("TEAMWORK_ROOT", "TEAMWORK_TEAM")


@pytest.fixture(scope="module")
def ambient_at_module_build() -> dict:
    """The team environment as a module-scoped fixture sees it, before any test body."""
    return {name: os.environ.get(name) for name in TEAM_ENV}


def test_module_scope_fixtures_see_no_ambient_team(ambient_at_module_build: dict) -> None:
    assert ambient_at_module_build == dict.fromkeys(TEAM_ENV), (
        "a module-scoped fixture was built with a lane's team environment in place, "
        "so every in-process team lookup inside it reads the live tree: "
        f"{ambient_at_module_build}"
    )


def test_no_test_body_sees_an_ambient_team() -> None:
    assert not [name for name in TEAM_ENV if name in os.environ]
