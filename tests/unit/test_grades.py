"""Unit: the two classifications the gates read - evidence grade and undo class.

Layer ``system``, area ``gates``. The ladder and the lanes are data, so they are
asserted as a table here; the wiring (self-check refuses noise, a closed lane
refuses a verdict, the CEO's authorization opens it) is asserted against the real
CLI in ``tests/unit/test_preflight.py``.

The point of both: a check a program can fail. "Looks good to me" and "no errors
were thrown" are the two lines a failing tree produces exactly as often as a
passing one, and a confidence score is the one number the model produces about
itself. Neither is allowed to open a gate.

Owner: architect. Layer: system. Area: gates.
"""

from __future__ import annotations

import pytest

from teamwork.grades import EVIDENCE_RANK, evidence_grade, undo_class

LADDER = [
    ("", "none"),
    ("   ", "none"),
    ("pytest -q tests/unit/test_x.py @a1b2c3d -> 12 passed", "strong"),
    ("ruff check . -> exit 0", "strong"),
    ("teamwork.py links -> # issues: 0", "strong"),
    ("privacy_scan --tree -> PASS 0 findings", "strong"),
    ("harness lint -> 0 problems", "strong"),
    ("3/3 checks passed", "strong"),
    ("docs/Team/Board.md:42 names the retired lane", "medium"),
    ("TS-0006 unit/skills @a1b2c3d4e5f6", "medium"),
    ("PF-0f1e2d3c4b5a @a1b2c3d", "medium"),
    ("see commit 9e2955a", "medium"),
    ("https://example.org/spec - accessed 2026-11-13", "medium"),
    ("pytest -q tests/unit/test_x.py", "weak"),
    ("git rev-parse HEAD", "weak"),
    ("looks good to me", "noise"),
    ("LGTM", "noise"),
    ("verified", "noise"),
    ("no errors were thrown", "noise"),
    ("nothing to report", "noise"),
    ("see the run", "noise"),
    ("I am confident this is correct", "noise"),
]


@pytest.mark.parametrize(("text", "grade"), LADDER)
def test_evidence_ladder(text: str, grade: str) -> None:
    assert evidence_grade(text) == grade


def test_a_result_beats_a_pointer_and_a_pointer_beats_a_command() -> None:
    assert EVIDENCE_RANK["strong"] > EVIDENCE_RANK["medium"] > EVIDENCE_RANK["weak"]
    assert EVIDENCE_RANK["weak"] > EVIDENCE_RANK["noise"] > EVIDENCE_RANK["none"]


def test_a_bare_revision_is_medium_not_strong() -> None:
    """A revision says where to look; it is not proof that anything ran."""
    assert evidence_grade("@9e2955a") == "medium"


def test_an_ordinary_diff_is_one_revert_away() -> None:
    assert undo_class([("src/teamwork/board.py", 4, 1)]) == ("revert", "one revert undoes it")


@pytest.mark.parametrize(
    "path",
    [
        "migrations/0002_drop_users.sql",
        "src/payments/charge.py",
        "deploy/certs/site.pem",
        ".github/workflows/release.yml",
        "release-exceptions.json",
        "app/auth/session.py",
    ],
)
def test_an_irreversible_path_is_a_closed_lane(path: str) -> None:
    cls, why = undo_class([(path, 3, 0)])
    assert cls == "closed"
    assert path in why


def test_a_deletion_is_a_closed_lane_whatever_the_path() -> None:
    """A deletion is the one edit a revert cannot always undo."""
    cls, why = undo_class([("docs/Team/Risks.md", 0, 12)])
    assert cls == "closed"
    assert "1 deleted file(s)" in why


def test_a_frozen_or_shared_surface_needs_hard_evidence() -> None:
    for path in ("AGENTS.md", "docs/Team/Architecture.md", "pyproject.toml"):
        cls, why = undo_class([(path, 9, 0)])
        assert cls == "evidence", path
        assert "shared or frozen surface" in why


def test_the_constitution_outranks_the_shared_surface() -> None:
    """A diff that both edits AGENTS.md and deletes a file is closed, not evidence."""
    assert undo_class([("AGENTS.md", 2, 0), ("docs/Team/Risks.md", 0, 4)])[0] == "closed"
