"""The suite measures the checkout's engine, not an installed copy of it."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"


def test_no_path_entry_ahead_of_the_checkout_can_shadow_it() -> None:
    src = str(SRC_DIR)
    assert src in sys.path
    ahead = sys.path[: sys.path.index(src)]
    shadowing = [entry for entry in ahead if entry and (Path(entry) / "teamwork").exists()]
    assert shadowing == [], shadowing


def test_the_imported_engine_is_the_checkout_engine() -> None:
    import teamwork

    resolved = Path(teamwork.__file__).resolve()
    assert resolved.is_relative_to(SRC_DIR), resolved
