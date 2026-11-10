"""The merge path's own commits carry the default-branch override.

The R1 pre-commit hook refuses a commit on the default branch so no lane can land
work there directly. A merge's records, board render and archive rewrite are the
one exception the rule names, and the engine sets the marker itself: a Reviewer
lane has no human to export `TEAMWORK_ALLOW_MAIN` before its pass lands.
"""

from __future__ import annotations

import os

import pytest

from teamwork import engine


def test_the_merge_environment_marks_the_default_branch_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEAMWORK_ALLOW_MAIN", raising=False)
    env = engine._merge_commit_env()
    assert env["TEAMWORK_ALLOW_MAIN"] == "1"


def test_the_merge_environment_keeps_the_ambient_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEAMWORK_MARKER", "kept")
    env = engine._merge_commit_env()
    assert env["TEAMWORK_MARKER"] == "kept"
    assert os.environ["TEAMWORK_MARKER"] == "kept"


def test_the_merge_environment_never_leaks_into_the_calling_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TEAMWORK_ALLOW_MAIN", raising=False)
    engine._merge_commit_env()
    assert "TEAMWORK_ALLOW_MAIN" not in os.environ
