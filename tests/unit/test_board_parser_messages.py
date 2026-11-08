"""The board parsers name the document they need instead of raising bare (T-0021).

Finding 15: `board.in_flight` used `str.index` and `board.render` used a bare
`next(...)`, so a caller that reached them with a non-board document got
`ValueError: substring not found` or `StopIteration` - a crash, not the
module's own "this is not a board" message.
"""

from __future__ import annotations

import pytest

from teamwork import board


def test_in_flight_names_the_missing_section() -> None:
    with pytest.raises(ValueError) as refused:
        board.in_flight("# board\n")
    assert "## In flight" in str(refused.value)
    assert "templates/Docs/Board.md" in str(refused.value)


def test_render_names_the_missing_table() -> None:
    with pytest.raises(ValueError) as refused:
        board.render({}, "# board\n\n## In flight\n")
    assert "table" in str(refused.value).lower()
