"""The budget must count what `teamwork load` prints, not the whole memory store.

Throughput.md section 3 item 4: the budget charged `LongTermMemory.md`, which
`load` never prints, and did not charge the open lessons and ranked knowledge that
`load` does print. The developer lane was reported OVER while its real startup
read was under the cap. These tests pin both directions:

* long-term and archived memory never move the startup row;
* an open lesson and a top-ten active knowledge record do;
* fixed/superseded records are recallable, and `--recallable` reports them;
* the default four-column report keeps its frozen shape.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine, harness, records

REPO_ROOT = Path(__file__).resolve().parents[2]


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path) -> Path:
    assert (
        cli("--project", project, "init", "--agents", "ceo,developer-1,reviewer-1", "--no-git") == 0
    )
    return team_root(project)


def startup(root: Path) -> int:
    return harness.instance_always_on(REPO_ROOT, root, "developer")


def write_long_memory(root: Path, body: str) -> None:
    path = engine.role_dir(root, "developer") / engine.F_LONG
    entry = records.new_entry(body, by="Developer-1", src="T-0034", rev="1fe03b7")
    records.write_memory(path, [entry], engine.F_LONG, "developer")


def write_archive_memory(root: Path, body: str) -> None:
    path = engine.role_dir(root, "developer") / engine.F_MEM_ARCHIVE
    entry = records.new_entry(body, by="Developer-1", src="T-0034", rev="1fe03b7")
    records.write_memory(path, [entry], engine.F_MEM_ARCHIVE, "developer")


def add_lesson(path: Path, lesson_id: str, status: str, mistake: str, rule: str) -> dict:
    existing = records.parse_lessons(path) if path.exists() else []
    item = records.new_lesson(
        "developer", mistake, "the cause", rule, "evidence", "Developer-1", "T-0034"
    )
    item["id"] = lesson_id
    item["status"] = status
    existing.append(item)
    records.write_lessons(path, existing)
    return item


def add_knowledge(
    path: Path, knowledge_id: str, status: str, topic: str, statement: str, importance: int = 3
) -> dict:
    existing = records.parse_knowledge(path) if path.exists() else []
    item = records.new_knowledge(
        topic, statement, "evidence", "Developer-1", "developer", importance=importance
    )
    item["id"] = knowledge_id
    item["status"] = status
    existing.append(item)
    records.write_knowledge(path, existing)
    return item


def test_long_term_memory_does_not_move_the_startup_row(cli, project: Path) -> None:
    root = init(cli, project)
    before = startup(root)
    write_long_memory(root, "long-term " * 2000)
    write_archive_memory(root, "archived " * 2000)

    assert startup(root) == before


def test_an_open_lesson_is_charged_and_a_fixed_one_is_recallable(cli, project: Path) -> None:
    root = init(cli, project)
    lessons = engine.lessons_path(root, "developer")
    before = startup(root)

    open_item = add_lesson(lessons, "L-0001", "open", "mistake one", "rule one")
    after_open = startup(root)
    line = f"- [{open_item['id']}] {open_item['mistake']} -> {open_item['rule']}\n"
    assert after_open - before == len(line.encode("utf-8"))

    fixed = add_lesson(lessons, "L-0002", "fixed", "mistake two", "rule two")
    assert startup(root) == after_open
    recallable = harness.instance_recallable(root, "developer")
    fixed_line = f"- [{fixed['id']}] {fixed['mistake']} -> {fixed['rule']}\n"
    assert recallable >= len(fixed_line.encode("utf-8"))


def test_a_knowledge_record_is_charged_as_load_prints_it(cli, project: Path) -> None:
    root = init(cli, project)
    before = startup(root)
    add_knowledge(engine.knowledge_path(root), "K-0001", "active", "topic one", "statement one")

    line = "- [K-0001] [fact] topic one: statement one (uses=0, tags=-)\n"
    assert startup(root) - before == len(line.encode("utf-8"))


def test_only_the_top_ten_active_knowledge_records_are_charged(cli, project: Path) -> None:
    root = init(cli, project)
    path = engine.knowledge_path(root)
    for index in range(1, 11):
        add_knowledge(path, f"K-{index:04d}", "active", f"topic {index}", f"statement {index}")
    charged = startup(root)

    add_knowledge(path, "K-0011", "active", "low", "outside the top ten", importance=1)
    assert startup(root) == charged

    items = records.parse_knowledge(path)
    for item in items:
        if item["id"] == "K-0011":
            item["importance"] = 9
    records.write_knowledge(path, items)
    assert startup(root) > charged


def test_superseded_knowledge_is_recallable_not_startup(cli, project: Path) -> None:
    root = init(cli, project)
    path = engine.knowledge_path(root)
    before = startup(root)
    before_recallable = harness.instance_recallable(root, "developer")

    add_knowledge(path, "K-0001", "superseded", "old", "a superseded fact")

    assert startup(root) == before
    assert harness.instance_recallable(root, "developer") > before_recallable


def test_the_recallable_flag_reports_the_long_and_archive_store(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    long_body = "long-term " * 1000
    archive_body = "archived " * 1000
    write_long_memory(root, long_body)
    write_archive_memory(root, archive_body)

    capsys.readouterr()
    assert cli("--project", project, "harness", "budget", "--recallable") == 0
    out = capsys.readouterr().out

    assert "# recallable budget for" in out
    rows = [line for line in out.splitlines() if line.startswith("Developer-1 ")]
    assert rows, out
    value = int(rows[0].split()[1])
    long_size = (engine.role_dir(root, "developer") / engine.F_LONG).stat().st_size
    archive_size = (engine.role_dir(root, "developer") / engine.F_MEM_ARCHIVE).stat().st_size
    assert value >= long_size + archive_size
    total = [line for line in out.splitlines() if line.startswith("total ")]
    assert total and int(total[0].split()[1]) >= value


def test_the_default_budget_output_keeps_the_frozen_four_columns(
    cli, project: Path, capsys
) -> None:
    init(cli, project)
    capsys.readouterr()
    cli("--project", project, "harness", "budget")
    out = capsys.readouterr().out

    data_rows = [line for line in out.splitlines() if line and not line.startswith("#")]
    assert data_rows[-1].startswith("total ")
    for line in data_rows:
        cells = line.split()
        assert len(cells) == 4, line
        assert cells[2].isdigit()
        assert cells[3] in ("ok", "OVER")
