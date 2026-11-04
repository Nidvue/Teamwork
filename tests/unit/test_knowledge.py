"""Unit: the project knowledge store (Architecture.md 15 + the kind field in 16.5).

Layer ``unit``, area ``knowledge``. Every assertion is made on the file the
command wrote or on the command's own stdout, so a renderer that loses a field, a
parser that invents one, or a duplicate rule that collapses the wrong pair fails
here rather than in a later acceptance run. The CLI is exercised in-process: that
is the boundary a Developer owns.

The load section, the ranking, the active-only duplicate key, the claim slot and
the supersession edges are the load-bearing parts of section 15, so each has its
own test; the concurrency case is a real multi-process race on one workspace,
because a read-modify-write that is only sequentially correct loses records the
moment two lanes write.

Owner: developer. Layer: unit. Area: knowledge.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from teamwork import config, engine

AGENTS = "ceo,developer-1,developer-2,tester-1"

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(cli, project: Path, capsys) -> Path:
    """A workspace with two developer lanes and a tester."""
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    capsys.readouterr()  # the init banner is not part of a command under test
    return project


def team_root(project: Path) -> Path:
    return project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)


def knowledge_file(project: Path) -> Path:
    return team_root(project) / config.F_KNOWLEDGE


def records(project: Path) -> list:
    return engine.parse_knowledge(knowledge_file(project))


def ledger(project: Path) -> list:
    path = team_root(project) / config.F_LEDGER
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def add(
    cli,
    project: Path,
    *,
    by: str = "Developer-1",
    topic: str = "Use the venv python",
    statement: str = "Run tests with venv\\Scripts\\python.exe.",
    evidence: str = "pytest @abc -> 1 passed",
    tags: str = "",
    kind: str = "",
    importance: int | None = None,
    supersedes: str = "",
    task: str = "",
) -> int:
    argv = [
        "--project",
        project,
        "knowledge",
        "add",
        "--by",
        by,
        "--topic",
        topic,
        "--statement",
        statement,
        "--evidence",
        evidence,
    ]
    if tags:
        argv += ["--tags", tags]
    if kind:
        argv += ["--kind", kind]
    if importance is not None:
        argv += ["--importance", str(importance)]
    if supersedes:
        argv += ["--supersedes", supersedes]
    if task:
        argv += ["--task", task]
    return cli(*argv)


def seed(project: Path, specs: list) -> list:
    """Write records directly through the records layer, for ordering fixtures."""
    items = []
    for index, spec in enumerate(specs, start=1):
        item = engine.new_knowledge(
            spec["topic"],
            spec["statement"],
            spec.get("evidence", "pytest @seed -> ok"),
            spec.get("by", "Developer-1"),
            spec.get("owner", "developer"),
            kind=spec.get("kind", "fact"),
            tags=spec.get("tags", ""),
            importance=spec.get("importance", 3),
            task=spec.get("task", ""),
        )
        item["id"] = spec.get("id", f"K-{index:04d}")
        item["uses"] = spec.get("uses", 0)
        item["status"] = spec.get("status", "active")
        item["supersedes"] = spec.get("supersedes", "")
        item["superseded_by"] = spec.get("superseded_by", "")
        item["created"] = spec.get("created", "2026-01-01")
        item["updated"] = spec.get("updated", "2026-01-01")
        items.append(item)
    engine.write_knowledge(knowledge_file(project), items)
    return items


def row(kid: str, status: str, importance, uses, tags: str, topic: str, statement: str) -> str:
    return (
        f"- {kid} [{status}] importance={importance} uses={uses} tags={tags}: {topic} - {statement}"
    )


def knowledge_events(project: Path) -> list:
    return [event for event in ledger(project) if event["action"].startswith("knowledge.")]


def test_config_exposes_the_frozen_knowledge_surface(ws: Path) -> None:
    assert config.F_KNOWLEDGE == "Knowledge.md"
    assert config.KNOWLEDGE_KINDS == ("fact", "experience", "preference", "gotcha", "rule")
    assert engine.knowledge_path(team_root(ws)) == knowledge_file(ws)
    assert knowledge_file(ws).parent == team_root(ws)


def test_owner_is_the_role_and_by_is_the_instance(cli, ws, capsys) -> None:
    assert add(cli, ws, by="Tester-1", topic="a tester fact") == 0
    capsys.readouterr()
    item = records(ws)[0]
    assert (item["owner"], item["by"]) == ("tester", "Tester-1")


def test_a_record_without_a_kind_line_reads_as_fact(cli, ws, capsys) -> None:
    """16.5: section 15's records need no migration, so a missing kind is fact."""
    knowledge_file(ws).write_text(
        "# Knowledge - what this project has learned\n\n"
        "## K-0001 - an older record\n"
        "- statement: written before the kind field existed\n"
        "- evidence: pytest @old -> 1 passed\n"
        "- tags: -\n"
        "- owner: developer\n"
        "- by: Developer-1\n"
        "- importance: 3\n"
        "- uses: 0\n"
        "- status: active\n"
        "- created: 2026-01-01\n"
        "- updated: 2026-01-01\n",
        encoding="utf-8",
    )
    assert records(ws)[0]["kind"] == "fact"

    assert cli("--project", ws, "knowledge", "list") == 0
    assert "K-0001 [active]" in capsys.readouterr().out
    assert cli("--project", ws, "knowledge", "show", "K-0001") == 0
    assert "- kind: fact" in capsys.readouterr().out


def test_blank_evidence_is_refused_before_anything_is_written(cli, ws, capsys) -> None:
    assert add(cli, ws, evidence="   ") == 2
    assert "--evidence is required" in capsys.readouterr().err
    assert not knowledge_file(ws).exists()


def test_add_writes_the_store_and_prints_the_frozen_lines(cli, ws, capsys) -> None:
    assert (
        add(
            cli,
            ws,
            topic="Use the venv python",
            statement="Run tests with venv\\Scripts\\python.exe.",
            evidence="pytest @abc -> 1 passed",
            tags="Build, CI",
            kind="experience",
            importance=4,
            task="T-9999",
        )
        == 0
    )
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "# K-0001 recorded: Use the venv python",
        f"- path: {knowledge_file(ws)}",
    ]

    text = knowledge_file(ws).read_text(encoding="utf-8")
    assert text.startswith("# Knowledge - what this project has learned")
    assert "## K-0001 - Use the venv python" in text
    assert "- statement: Run tests with venv\\Scripts\\python.exe." in text
    assert "- kind: experience" in text
    assert "- evidence: pytest @abc -> 1 passed" in text
    assert "- tags: build,ci" in text
    assert "- owner: developer" in text
    assert "- by: Developer-1" in text
    assert "- task: T-9999" in text
    assert "- importance: 4" in text
    assert "- uses: 0" in text
    assert "- status: active" in text
    assert "- created: " in text
    assert "- updated: " in text
    assert "- supersedes:" not in text
    assert "- superseded_by:" not in text

    item = records(ws)[0]
    assert item["id"] == "K-0001"
    assert item["topic"] == "Use the venv python"
    assert item["statement"] == "Run tests with venv\\Scripts\\python.exe."
    assert item["kind"] == "experience"
    assert item["tags"] == ["build", "ci"]
    assert item["importance"] == 4
    assert item["uses"] == 0
    assert item["status"] == "active"


def test_tags_are_lower_case_kebab_and_an_empty_list_renders_dash(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="tagged", tags="Build, CI ,build") == 0
    assert add(cli, ws, topic="untagged", statement="A fact with no tags.") == 0
    capsys.readouterr()

    assert records(ws)[0]["tags"] == ["build", "ci"]
    assert records(ws)[1]["tags"] == []

    assert cli("--project", ws, "knowledge", "list") == 0
    out = capsys.readouterr().out
    assert "tags=build,ci:" in out
    assert "tags=-:" in out


def test_list_orders_by_importance_uses_updated_then_id(cli, ws, capsys) -> None:
    seed(
        ws,
        [
            {"topic": "one", "statement": "s1", "importance": 1, "updated": "2026-11-01"},
            {"topic": "two", "statement": "s2", "importance": 5, "updated": "2026-10-01"},
            {
                "topic": "three",
                "statement": "s3",
                "importance": 5,
                "uses": 3,
                "updated": "2026-09-01",
            },
            {
                "topic": "four",
                "statement": "s4",
                "importance": 5,
                "uses": 3,
                "updated": "2026-11-02",
            },
            {
                "topic": "five",
                "statement": "s5",
                "importance": 5,
                "uses": 3,
                "updated": "2026-11-02",
            },
        ],
    )
    assert cli("--project", ws, "knowledge", "list") == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split(" ", 3)[1] for line in out if line.startswith("- K-")] == [
        "K-0004",
        "K-0005",
        "K-0003",
        "K-0002",
        "K-0001",
    ]
    assert out[-1] == "# knowledge: 5 active, 0 superseded, 9 use(s)"


def test_list_defaults_to_active_and_twenty_rows(cli, ws, capsys) -> None:
    active = [{"topic": f"topic-{index}", "statement": f"statement-{index}"} for index in range(25)]
    superseded = [
        {
            "id": f"K-{index:04d}",
            "topic": f"retired-{index}",
            "statement": f"retired statement {index}",
            "status": "superseded",
            "superseded_by": "K-0001",
        }
        for index in range(26, 28)
    ]
    seed(ws, active + superseded)

    assert cli("--project", ws, "knowledge", "list") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if line.startswith("- K-")]
    assert len(rows) == 20
    assert all("[active]" in line for line in rows)

    assert cli("--project", ws, "knowledge", "list", "--limit", "0", "--status", "all") == 0
    out = capsys.readouterr().out
    assert len([line for line in out.splitlines() if line.startswith("- K-")]) == 27
    assert out.splitlines()[-1] == "# knowledge: 25 active, 2 superseded, 0 use(s)"

    assert cli("--project", ws, "knowledge", "list", "--status", "superseded") == 0
    out = capsys.readouterr().out
    assert len([line for line in out.splitlines() if line.startswith("- K-")]) == 2
    assert "[superseded]" in out


def test_list_filters_tag_role_and_kind(cli, ws, capsys) -> None:
    seed(
        ws,
        [
            {
                "topic": "build fact",
                "statement": "a fact",
                "tags": "build",
                "owner": "developer",
                "kind": "fact",
            },
            {
                "topic": "build experience",
                "statement": "an experience",
                "tags": "build,ci",
                "owner": "tester",
                "kind": "experience",
            },
            {
                "topic": "docs preference",
                "statement": "a preference",
                "tags": "docs",
                "owner": "developer",
                "kind": "preference",
            },
        ],
    )

    def listed(*args) -> list:
        assert cli("--project", ws, "knowledge", "list", *args) == 0
        return [
            line.split(" ", 3)[1]
            for line in capsys.readouterr().out.splitlines()
            if line.startswith("- K-")
        ]

    assert listed("--tag", "build") == ["K-0001", "K-0002"]
    assert listed("--role", "tester") == ["K-0002"]
    assert listed("--kind", "experience") == ["K-0002"]
    assert listed("--tag", "build", "--role", "developer", "--kind", "fact") == ["K-0001"]


def test_show_prints_the_header_every_field_and_the_path(cli, ws, capsys) -> None:
    assert (
        add(
            cli,
            ws,
            topic="Use the venv python",
            statement="Run tests with the venv.",
            tags="build,ci",
            task="T-9999",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", ws, "knowledge", "show", "k-0001") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "## K-0001 - Use the venv python"
    for field in engine.KNOWLEDGE_FIELDS:
        assert any(line.startswith(f"- {field}: ") for line in out), field
    assert "- tags: build,ci" in out
    assert "- task: T-9999" in out
    assert "- supersedes: -" in out
    assert "- superseded_by: -" in out
    assert out[-1] == f"- path: {knowledge_file(ws)}"

    assert cli("--project", ws, "knowledge", "show", "K-9999") == 2
    assert "no knowledge 'K-9999'" in capsys.readouterr().err


def test_show_keeps_a_superseded_record_readable(cli, ws, capsys) -> None:
    assert add(cli, ws) == 0
    capsys.readouterr()
    assert (
        add(
            cli,
            ws,
            statement="Run tests with the repo venv.",
            evidence="pytest @def -> 2 passed",
            supersedes="K-0001",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", ws, "knowledge", "show", "K-0001") == 0
    out = capsys.readouterr().out
    assert "- status: superseded" in out
    assert "- superseded_by: K-0002" in out


def test_touch_increments_uses_and_records_the_event(cli, ws, capsys) -> None:
    assert add(cli, ws) == 0
    capsys.readouterr()

    assert cli("--project", ws, "knowledge", "touch", "K-0001", "--by", "Developer-2") == 0
    assert capsys.readouterr().out == "# K-0001 uses=1\n"
    assert cli("--project", ws, "knowledge", "touch", "K-0001", "--by", "Developer-1") == 0
    assert capsys.readouterr().out == "# K-0001 uses=2\n"

    item = records(ws)[0]
    assert item["uses"] == 2
    touches = [event for event in knowledge_events(ws) if event["action"] == "knowledge.touch"]
    assert [(event["actor"], event["target"], event["detail"]) for event in touches] == [
        ("Developer-2", "K-0001", "uses=1"),
        ("Developer-1", "K-0001", "uses=2"),
    ]

    assert cli("--project", ws, "knowledge", "touch", "K-9999", "--by", "Developer-1") == 2
    assert "no knowledge 'K-9999'" in capsys.readouterr().err
    assert len(records(ws)) == 1


def test_duplicate_add_returns_the_existing_id_and_adds_nothing(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="Use the venv python", statement="Run tests with the venv.") == 0
    capsys.readouterr()
    before_events = len(knowledge_events(ws))

    assert (
        add(
            cli,
            ws,
            topic="  use   the VENV python ",
            statement=" run  tests with the VENV. ",
        )
        == 0
    )
    assert capsys.readouterr().out == "# K-0001 already records this: Use the venv python\n"

    assert len(records(ws)) == 1
    assert len(knowledge_events(ws)) == before_events
    assert len([event for event in knowledge_events(ws) if event["action"] == "knowledge.add"]) == 1


def test_same_topic_different_statement_is_refused_with_the_claim_message(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="Use the venv python", statement="Run tests with the venv.") == 0
    capsys.readouterr()

    assert (
        add(
            cli,
            ws,
            topic="use the venv PYTHON",
            statement="A different statement.",
            evidence="pytest @def -> 2 passed",
        )
        == 2
    )
    err = capsys.readouterr().err
    assert (
        "topic 'use the venv PYTHON' is already claimed by K-0001; "
        "pass --supersedes K-0001 to replace it" in err
    )
    assert [item["topic"] for item in records(ws)] == ["Use the venv python"]


def test_supersede_marks_the_old_record_and_hides_it_from_list_and_load(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="Use the venv python", statement="Run tests with the venv.") == 0
    capsys.readouterr()
    assert (
        add(
            cli,
            ws,
            topic="Use the venv python",
            statement="Run tests with the repo venv.",
            evidence="pytest @def -> 2 passed",
            supersedes="K-0001",
        )
        == 0
    )
    assert capsys.readouterr().out.startswith("# K-0002 recorded: Use the venv python\n")

    old, new = records(ws)
    assert (old["status"], old["superseded_by"]) == ("superseded", "K-0002")
    assert (new["status"], new["supersedes"]) == ("active", "K-0001")

    assert cli("--project", ws, "knowledge", "list") == 0
    out = capsys.readouterr().out
    assert "K-0001" not in out
    assert "K-0002 [active]" in out
    assert out.splitlines()[-1] == "# knowledge: 1 active, 1 superseded, 0 use(s)"

    assert (
        add(
            cli,
            ws,
            topic="Use the venv python",
            statement="A third statement under the same topic.",
            evidence="pytest @def -> 2 passed",
        )
        == 2
    )
    assert "is already claimed by K-0002" in capsys.readouterr().err

    assert cli("--project", ws, "load", "Developer-1") == 0
    load = capsys.readouterr().out
    assert (
        "- [K-0002] [fact] Use the venv python: Run tests with the repo venv. (uses=0, tags=-)"
        in load
    )
    assert "- [K-0001]" not in load
    assert (
        '# project knowledge: 1 active, 1 superseded; search: teamwork.py knowledge search "<topic>"'
        in load
    )

    actions = [(event["action"], event["target"]) for event in knowledge_events(ws)]
    assert ("knowledge.add", "K-0002") in actions
    assert ("knowledge.supersede", "K-0001") in actions


def test_duplicate_with_supersedes_retires_the_named_active_record(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    assert add(cli, ws, topic="topic b", statement="statement two") == 0
    capsys.readouterr()

    assert (
        add(
            cli,
            ws,
            topic="TOPIC A",
            statement="STATEMENT ONE",
            supersedes="K-0002",
        )
        == 0
    )
    assert capsys.readouterr().out == "# K-0001 already records this: topic a\n"

    first, second = records(ws)
    assert (first["id"], first["status"]) == ("K-0001", "active")
    assert (second["id"], second["status"], second["superseded_by"]) == (
        "K-0002",
        "superseded",
        "K-0001",
    )
    assert len(records(ws)) == 2

    assert (
        add(
            cli,
            ws,
            topic="TOPIC A",
            statement="STATEMENT ONE",
            supersedes="K-0001",
        )
        == 2
    )
    assert "K-0001 cannot supersede itself" in capsys.readouterr().err

    assert (
        add(
            cli,
            ws,
            topic="TOPIC A",
            statement="STATEMENT ONE",
            supersedes="K-0002",
        )
        == 2
    )
    assert "K-0002 is already superseded by K-0001" in capsys.readouterr().err


def test_a_retired_fact_is_reinstated_as_a_new_active_record(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    assert (
        add(
            cli,
            ws,
            topic="topic b",
            statement="statement two",
            evidence="pytest @def -> 2 passed",
            supersedes="K-0001",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        add(
            cli,
            ws,
            topic="Topic A",
            statement="Statement One",
            evidence="pytest @ghi -> 3 passed",
            supersedes="K-0001",
        )
        == 0
    )
    assert capsys.readouterr().out.startswith("# K-0003 recorded: Topic A\n")

    old, replacement, reinstated = records(ws)
    assert (old["status"], old["superseded_by"]) == ("superseded", "K-0002")
    assert (replacement["status"], replacement["supersedes"]) == ("active", "K-0001")
    assert (reinstated["status"], reinstated["supersedes"]) == ("active", "K-0001")

    assert cli("--project", ws, "knowledge", "list") == 0
    out = capsys.readouterr().out
    assert "K-0003" in out and "K-0002" in out and "K-0001" not in out

    assert (
        add(
            cli,
            ws,
            topic="topic c",
            statement="A different fact under an unrelated topic.",
            supersedes="K-0001",
        )
        == 2
    )
    assert "K-0001 is already superseded by K-0002" in capsys.readouterr().err


def test_reinstating_without_supersedes_also_creates_a_new_active_record(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    assert add(cli, ws, topic="topic b", statement="statement two", supersedes="K-0001") == 0
    capsys.readouterr()

    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    capsys.readouterr()
    reinstated = records(ws)[2]
    assert reinstated["id"] == "K-0003"
    assert reinstated["status"] == "active"
    assert reinstated["supersedes"] == ""


def test_unknown_self_and_already_superseded_targets_are_refused(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    capsys.readouterr()

    assert add(cli, ws, topic="topic b", statement="statement two", supersedes="K-9999") == 2
    assert "no knowledge 'K-9999'" in capsys.readouterr().err

    assert add(cli, ws, topic="topic b", statement="statement two", supersedes="K-0002") == 2
    assert "K-0002 cannot supersede itself" in capsys.readouterr().err

    assert (
        add(
            cli,
            ws,
            topic="topic a",
            statement="statement two",
            supersedes="K-0001",
        )
        == 0
    )
    capsys.readouterr()
    assert add(cli, ws, topic="topic c", statement="statement three", supersedes="K-0001") == 2
    assert "K-0001 is already superseded by K-0002" in capsys.readouterr().err


def test_kind_defaults_to_fact_and_filters_list_and_search(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="plain fact", statement="the default kind") == 0
    assert add(cli, ws, topic="a reusable approach", statement="it worked", kind="experience") == 0
    assert add(cli, ws, topic="a preference", statement="we prefer it", kind="preference") == 0
    capsys.readouterr()

    assert records(ws)[0]["kind"] == "fact"
    assert cli("--project", ws, "knowledge", "show", "K-0001") == 0
    assert "- kind: fact" in capsys.readouterr().out

    assert cli("--project", ws, "knowledge", "list", "--kind", "experience") == 0
    out = capsys.readouterr().out
    assert "K-0002" in out and "K-0001" not in out

    assert cli("--project", ws, "knowledge", "search", "reusable", "--kind", "experience") == 0
    assert "K-0002" in capsys.readouterr().out
    assert cli("--project", ws, "knowledge", "search", "reusable", "--kind", "gotcha") == 0
    assert '# no knowledge matched "reusable"' in capsys.readouterr().out

    assert add(cli, ws, topic="bad", statement="bad", kind="opinion") == 2
    err = capsys.readouterr().err
    assert "unknown knowledge kind 'opinion'" in err
    for kind in config.KNOWLEDGE_KINDS:
        assert kind in err
    assert cli("--project", ws, "knowledge", "list", "--kind", "opinion") == 2
    assert "unknown knowledge kind 'opinion'" in capsys.readouterr().err


def test_search_matches_topic_statement_and_tags_across_status(cli, ws, capsys) -> None:
    seed(
        ws,
        [
            {
                "topic": "Use the venv python",
                "statement": "Run pytest with the repo interpreter.",
                "tags": "build,ci",
            },
            {
                "topic": "Old venv rule",
                "statement": "This one was replaced.",
                "tags": "build",
                "status": "superseded",
                "superseded_by": "K-0001",
            },
            {
                "topic": "Release tag",
                "statement": "Tags are immutable.",
                "tags": "release",
            },
        ],
    )
    before = knowledge_file(ws).read_bytes()
    before_events = len(ledger(ws))

    assert cli("--project", ws, "knowledge", "search", "VENV") == 0
    out = capsys.readouterr().out
    assert "K-0001" in out and "K-0002" not in out
    assert out.splitlines()[-1] == "# knowledge: 2 active, 1 superseded, 0 use(s)"

    assert cli("--project", ws, "knowledge", "search", "pytest") == 0
    assert "K-0001" in capsys.readouterr().out
    assert cli("--project", ws, "knowledge", "search", "BUILD") == 0
    assert "K-0001" in capsys.readouterr().out
    assert cli("--project", ws, "knowledge", "search", "venv", "--status", "superseded") == 0
    assert "K-0002" in capsys.readouterr().out
    assert cli("--project", ws, "knowledge", "search", "venv", "--status", "all") == 0
    out = capsys.readouterr().out
    assert "K-0001" in out and "K-0002" in out

    assert cli("--project", ws, "knowledge", "search", "no-such-fact") == 0
    assert capsys.readouterr().out == '# no knowledge matched "no-such-fact"\n'

    assert knowledge_file(ws).read_bytes() == before
    assert len(ledger(ws)) == before_events


def test_search_defaults_to_twenty_rows(cli, ws, capsys) -> None:
    seed(
        ws,
        [
            {"topic": f"match {index}", "statement": "the same needle in every statement"}
            for index in range(25)
        ],
    )
    assert cli("--project", ws, "knowledge", "search", "needle") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if line.startswith("- K-")]
    assert len(rows) == 20
    assert cli("--project", ws, "knowledge", "search", "needle", "--limit", "0") == 0
    rows = [line for line in capsys.readouterr().out.splitlines() if line.startswith("- K-")]
    assert len(rows) == 25


def test_load_shows_the_top_ten_active_and_a_footer(cli, ws, capsys) -> None:
    specs = [
        {
            "topic": f"fact {index}",
            "statement": f"statement {index}",
            "importance": 1 if index == 1 else 5,
            "uses": 0 if index == 1 else 1,
            "tags": "build,ci" if index == 2 else "",
            "kind": "experience" if index == 2 else "fact",
        }
        for index in range(1, 13)
    ]
    specs.append(
        {
            "id": "K-0013",
            "topic": "retired",
            "statement": "retired statement",
            "status": "superseded",
            "superseded_by": "K-0002",
        }
    )
    seed(ws, specs)

    assert cli("--project", ws, "load", "Developer-1") == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("- [K-"))
    rows = lines[start:]
    knowledge_rows = [line for line in rows if line.startswith("- [K-")]
    assert len(knowledge_rows) == 10
    assert knowledge_rows[0] == (
        "- [K-0002] [experience] fact 2: statement 2 (uses=1, tags=build,ci)"
    )
    assert all("retired" not in line for line in knowledge_rows)
    assert rows[len(knowledge_rows)] == (
        "# project knowledge: 12 active, 1 superseded; "
        'search: teamwork.py knowledge search "<topic>"'
    )


def test_load_without_a_knowledge_file_is_clean(cli, ws, capsys) -> None:
    assert not knowledge_file(ws).exists()
    assert cli("--project", ws, "load", "Developer-1") == 0
    out = capsys.readouterr().out
    assert "# project knowledge:" not in out
    assert not knowledge_file(ws).exists()


def test_a_missing_store_reads_as_empty_and_show_still_errors(cli, ws, capsys) -> None:
    assert cli("--project", ws, "knowledge", "list") == 0
    assert capsys.readouterr().out == "# knowledge: 0 active, 0 superseded, 0 use(s)\n"
    assert cli("--project", ws, "knowledge", "search", "anything") == 0
    assert capsys.readouterr().out == '# no knowledge matched "anything"\n'
    assert cli("--project", ws, "knowledge", "show", "K-0001") == 2
    assert "no knowledge 'K-0001'" in capsys.readouterr().err
    assert not knowledge_file(ws).exists()


def test_text_fields_are_one_line_and_the_caps_are_enforced(cli, ws, capsys) -> None:
    assert (
        add(
            cli,
            ws,
            topic="forged\ntopic",
            statement="line one\n## K-9999 - forged\nline two",
        )
        == 0
    )
    capsys.readouterr()
    text = knowledge_file(ws).read_text(encoding="utf-8")
    assert "\n## K-9999" not in text
    assert len(records(ws)) == 1
    assert records(ws)[0]["statement"] == "line one ## K-9999 - forged line two"

    assert add(cli, ws, topic="x" * 121, statement="ok") == 2
    assert "the cap is 120" in capsys.readouterr().err
    assert add(cli, ws, topic="ok", statement="y" * 501) == 2
    assert "the cap is 500" in capsys.readouterr().err
    assert len(records(ws)) == 1


def test_importance_must_be_one_to_five(cli, ws) -> None:
    assert add(cli, ws, importance=6) == 2
    assert add(cli, ws, importance=0) == 2
    assert not knowledge_file(ws).exists()


def test_ledger_records_add_supersede_and_touch(cli, ws, capsys) -> None:
    assert add(cli, ws, topic="topic a", statement="statement one") == 0
    assert add(cli, ws, topic="topic a", statement="statement two", supersedes="K-0001") == 0
    assert cli("--project", ws, "knowledge", "touch", "K-0002", "--by", "Developer-1") == 0
    assert add(cli, ws, topic="topic a", statement="statement two") == 0
    capsys.readouterr()

    events = [(event["action"], event["target"], event["actor"]) for event in knowledge_events(ws)]
    assert events == [
        ("knowledge.add", "K-0001", "Developer-1"),
        ("knowledge.add", "K-0002", "Developer-1"),
        ("knowledge.supersede", "K-0001", "Developer-1"),
        ("knowledge.touch", "K-0002", "Developer-1"),
    ]


def test_concurrent_adds_and_touches_serialise_under_one_lock(ws, tmp_path: Path) -> None:
    """Real CLI writers race on one store: every add persists and every touch counts.

    Pre-lock code reads the file, changes it and writes with no serialisation, so
    two adds can overwrite each other (a lost record) and two touches can both
    write uses=1 over uses=0 (a lost increment). Every child imports the engine
    first, then waits on one barrier file, so the calls enter the
    read-modify-write sequence together. A child that times out waiting for the
    lock exits 4: that is a refusal, not a lost write, so the counts are the
    successful adds and touches and any other code still fails.
    """
    assert add_for_race(ws) == 0
    assert engine.parse_knowledge(knowledge_file(ws))[0]["uses"] == 0

    adds = 10
    touches = 10
    barrier = tmp_path / "knowledge-race-start"
    src = str(REPO_ROOT / "src")
    processes = []
    for index in range(adds):
        argv = [
            "--project",
            str(ws),
            "knowledge",
            "add",
            "--by",
            "Developer-1",
            "--topic",
            f"race topic {index}",
            "--statement",
            f"race statement {index}",
            "--evidence",
            f"pytest @race-{index} -> 1 passed",
        ]
        processes.append(_race_process(argv, ws, barrier, src))
    for _index in range(touches):
        argv = [
            "--project",
            str(ws),
            "knowledge",
            "touch",
            "K-0001",
            "--by",
            "Developer-1",
        ]
        processes.append(_race_process(argv, ws, barrier, src))
    barrier.write_text("go", encoding="utf-8")
    results = [process.communicate(timeout=180) for process in processes]
    codes = [process.returncode for process in processes]
    unexpected = [
        (index, code, out, err)
        for index, (code, (out, err)) in enumerate(zip(codes, results))
        if code not in (0, 4)
    ]
    assert not unexpected, unexpected
    ok_adds = [index for index, code in enumerate(codes[:adds]) if code == 0]
    ok_touches = sum(1 for code in codes[adds:] if code == 0)

    items = engine.parse_knowledge(knowledge_file(ws))
    assert len(items) == 1 + len(ok_adds), [(item["id"], item["topic"]) for item in items]
    assert len({item["id"] for item in items}) == len(items)
    assert {item["topic"] for item in items if item["topic"].startswith("race ")} == {
        f"race topic {index}" for index in ok_adds
    }
    first = next(item for item in items if item["id"] == "K-0001")
    assert first["uses"] == ok_touches

    events = [event for event in ledger(ws) if event["action"].startswith("knowledge.")]
    add_events = [event for event in events if event["action"] == "knowledge.add"]
    touch_events = [event for event in events if event["action"] == "knowledge.touch"]
    assert len([event for event in add_events if event["target"] != "K-0001"]) == len(ok_adds)
    assert len(touch_events) == ok_touches
    assert {event["target"] for event in touch_events} <= {"K-0001"}
    assert [event["detail"] for event in touch_events] == [
        f"uses={number}" for number in range(1, ok_touches + 1)
    ]


def add_for_race(project: Path) -> int:
    """The one record the race touches, written through the same CLI path."""
    return engine.main(
        [
            "--project",
            str(project),
            "knowledge",
            "add",
            "--by",
            "Developer-1",
            "--topic",
            "shared record",
            "--statement",
            "every touch counts this one",
            "--evidence",
            "pytest @seed -> 1 passed",
        ]
    )


def _race_process(argv: list, project: Path, barrier: Path, src: str) -> subprocess.Popen:
    code = (
        "import pathlib, sys, time\n"
        f"sys.path.insert(0, {src!r})\n"
        "from teamwork import engine\n"
        f"while not pathlib.Path({str(barrier)!r}).exists():\n"
        "    time.sleep(0.002)\n"
        f"raise SystemExit(engine.main({argv!r}))\n"
    )
    return subprocess.Popen(
        [sys.executable, "-c", code],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
