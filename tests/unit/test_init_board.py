"""A fresh project's own board must render; `init` wrote one the tool refused.

Measured (T-0007): in a throwaway repository,

    teamwork.py --project <fixture> --team Fixture init --agents ceo,architect,developer,tester,reviewer-1
    teamwork.py --project <fixture> --team Fixture task add developer "a first task"
    teamwork.py --project <fixture> --team Fixture board --write
    -> exit 2: docs/Team/Board.md is not a rendered board:
       missing '| role | id | area | state | pr | merged revision |'
       ... the skeleton `init` copies is templates/Docs/Board.md

`init` copied `templates/Docs/Board.md`, which carried only the human sections,
while `teamwork.board` renders between anchors the template did not have. So the
tool refused the file the tool itself created, and its repair line pointed back at
that same file. The fix chosen here is the template, not a repair inside
`board --write`:

* `init` is the only producer of a board the tool did not itself render, so making
  its one skeleton conforming closes the source; a repair in `--write` would have
  to guess where the missing tables belong in an arbitrary hand-edited file, and
  would also turn "this committed board lost its anchors" into a silent rewrite
  instead of the finding the drift gate exists to raise.
* The template and the renderer are two spellings of one shape, so they are
  compared here: `test_the_init_template_is_a_renderable_board` renders the
  template itself. A change to `board.py`'s anchors that the template does not
  follow is then a red test, not a broken `init` discovered in the field.

The second half of the measured defect is the empty start: a fresh `init` writes
one empty queue per role, and `board --write` refused that with "no task records:
run `teamwork.py init` first" - after `init` had just run. An empty queue is not a
missing one, so the new project now renders an empty table and checks clean.
"""

from __future__ import annotations

import re
from pathlib import Path

from teamwork import board as boardlib
from teamwork import engine
from teamwork.config import TEMPLATES_DIR

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = TEMPLATES_DIR / "Docs" / "Board.md"
COMMITTED = REPO / "docs" / "Team" / "Board.md"
AGENTS = ("ceo", "architect", "developer-1", "tester-1", "reviewer-1")
BOARD = Path("docs") / "Team" / "Board.md"

#: Every anchor the renderer and both gates need, not only the three `--check`
#: names: `render` locates each table by its head and stops at its anchor sentence.
ANCHORS = engine.BOARD_ANCHORS + (boardlib.TABLE_ANCHOR, boardlib.FLIGHT_ANCHOR)


def read_board(project: Path) -> str:
    return (project / BOARD).read_text(encoding="utf-8")


def init(cli, project: Path) -> None:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0


def test_the_init_template_is_a_renderable_board() -> None:
    """The template is a board, by the renderer's own definition of one."""
    text = TEMPLATE.read_text(encoding="utf-8")

    missing = [anchor for anchor in ANCHORS if anchor not in text]
    assert not missing, f"{TEMPLATE} is not a rendered board: missing {missing}"
    assert boardlib.render({}, text) == text, "rendering the template would change it"
    assert boardlib.problems({}, text) == []


def test_a_fresh_project_renders_and_checks_its_own_board(cli, project: Path) -> None:
    """The measured exit 2: init then board --write on nothing but a fresh project."""
    init(cli, project)
    assert read_board(project) == TEMPLATE.read_text(encoding="utf-8")

    assert cli("--project", project, "board", "--write") == 0
    assert cli("--project", project, "board", "--check") == 0
    assert all(anchor in read_board(project) for anchor in ANCHORS)


def test_the_first_task_reaches_the_fresh_board(cli, project: Path) -> None:
    """A project is usable at its first task, not only at zero."""
    init(cli, project)
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "developer",
            "the first task",
            "--priority",
            "P1",
        )
        == 0
    )

    assert cli("--project", project, "board", "--write") == 0
    text = read_board(project)
    assert "| developer | T-0001 | - | todo | - | - |" in text
    assert "| developer | T-0001 · the first task | P1 | todo | - |" in text
    assert cli("--project", project, "board", "--check") == 0


def test_a_board_that_lost_its_table_is_refused_not_repaired(cli, project, capsys) -> None:
    """The repair boundary: the skeleton comes from init, `--write` never rebuilds."""
    init(cli, project)
    board = project / BOARD
    stripped = [line for line in read_board(project).splitlines() if line != boardlib.TABLE_HEAD]
    board.write_text("\n".join(stripped) + "\n", encoding="utf-8")

    capsys.readouterr()
    assert cli("--project", project, "board", "--write") == 2
    captured = capsys.readouterr()
    out = captured.err + captured.out
    assert boardlib.TABLE_HEAD in out
    assert "templates/Docs/Board.md" in out
    assert boardlib.TABLE_HEAD not in read_board(project), "a refused board was rewritten"


def test_the_committed_board_is_still_what_a_render_writes() -> None:
    """The regression half: this template change must not strand the real board.

    The committed board is a projection of one milestone's queues, and those queues
    are gitignored state that CI does not have. Its own rows are the queue side
    here: a rendered board must reproduce them exactly, table cells and In-flight
    title, priority and artifact included. That is the shape `--write` accepts, so
    it stays checkable where the queues are absent.
    """
    text = COMMITTED.read_text(encoding="utf-8")
    missing = [anchor for anchor in ANCHORS if anchor not in text]
    assert not missing, f"{COMMITTED} lost anchors: {missing}"

    tasks: dict[tuple[str, str], dict[str, str]] = {}
    for match in re.finditer(
        r"^\| ([a-z-]+) \| (T-\d{4}) \| ([^|]*) \| ([a-z]+) \| ([^|]*) \| ([^|]*) \|$",
        text,
        re.M,
    ):
        tasks[(boardlib.norm_role(match[1]), match[2])] = {
            "area": match[3].strip(),
            "status": match[4],
            "pr": match[5].strip(),
            "merge_commit": match[6].strip(),
        }
    assert tasks, "the committed board carries no task rows"
    for role, tid, title, priority, state, _artifact in boardlib.FLIGHT_ROW.findall(text):
        fields = tasks.setdefault((boardlib.norm_role(role), tid), {})
        fields.update({"title": title.strip(), "priority": priority, "status": state})

    assert boardlib.render(tasks, text) == text, "the committed board is not its own render"
