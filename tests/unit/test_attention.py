"""Unit tests for the attention record: the file, the commands and the loop gate.

Attention is team-local state (``Attention.md``), one item per thing that cannot
continue without a person. The two properties that matter are that the panel only
shows what a person must act on - a healthy team prints nothing at all - and that
only an ``authorization`` may hold the team's STOP, because the other kinds are
recorded but can be worked around.

Owner: developer. Layer: unit. Area: attention.
"""

from __future__ import annotations

import json
from pathlib import Path

from teamwork import attention, engine

ROSTER = "ceo,developer-1,reviewer-1"


def team_root(project: Path) -> Path:
    """The ``.pi/Teamwork/Teams/<Team>`` directory the engine will act on."""
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def ledger_actions(root: Path) -> list:
    """The ``action`` of every ledger record, in order."""
    path = root / engine.F_LEDGER
    if not path.exists():
        return []
    return [json.loads(line)["action"] for line in path.read_text(encoding="utf-8").splitlines()]


# --------------------------------------------------------------------------- #
# the record
# --------------------------------------------------------------------------- #


def test_new_attention_defaults_to_an_open_blocker() -> None:
    item = engine.new_attention("  approve the release  ", by="CEO", task=" t-0007 ")

    assert item["text"] == "approve the release"
    assert item["kind"] == "blocker"
    assert item["status"] == "open"
    assert item["task"] == "T-0007"
    assert item["by"] == "CEO"
    assert item["id"] == ""
    assert item["resolution"] == ""


def test_new_attention_keeps_a_known_kind_and_falls_back_on_an_unknown_one() -> None:
    assert engine.new_attention("x", kind="authorization")["kind"] == "authorization"
    assert engine.new_attention("x", kind="curiosity")["kind"] == "blocker"


def test_parse_attention_of_a_missing_file_is_empty(tmp_path: Path) -> None:
    assert engine.parse_attention(tmp_path / "Attention.md") == []


def test_attention_roundtrip_allocates_ids_in_order(tmp_path: Path) -> None:
    path = tmp_path / "Attention.md"
    items = [
        engine.new_attention("first", kind="decision", by="CEO", task="T-0001"),
        engine.new_attention("second", kind="authorization", by="Developer-1"),
    ]
    engine.write_attention(path, items)

    out = engine.parse_attention(path)

    assert [item["id"] for item in out] == ["A-0001", "A-0002"]
    assert [item["text"] for item in out] == ["first", "second"]
    assert [item["kind"] for item in out] == ["decision", "authorization"]
    assert out[0]["task"] == "T-0001"
    assert out[1]["task"] == ""


def test_assign_attention_ids_continues_after_the_highest(tmp_path: Path) -> None:
    path = tmp_path / "Attention.md"
    engine.write_attention(path, [engine.new_attention("one"), engine.new_attention("two")])

    items = engine.parse_attention(path)
    items.append(engine.new_attention("three"))
    engine.write_attention(path, items)

    assert [item["id"] for item in engine.parse_attention(path)] == ["A-0001", "A-0002", "A-0003"]


def test_parse_attention_does_not_let_prose_forge_a_field(tmp_path: Path) -> None:
    """A body line that looks like metadata must never rewrite the stored state."""
    path = tmp_path / "Attention.md"
    path.write_text(
        "# ATTENTION\n\n"
        "## A-0003 · needs a decision\n"
        "- kind: decision\n"
        "- status: open\n\n"
        "the person wrote:\n"
        "- status: resolved\n"
        "- kind: authorization\n",
        encoding="utf-8",
    )

    item = engine.parse_attention(path)[0]

    assert item["status"] == "open"
    assert item["kind"] == "decision"


def test_find_attention_by_id_and_by_text() -> None:
    items = [
        engine.new_attention("grant the release", kind="authorization"),
        engine.new_attention("pick a licence", kind="decision"),
    ]
    attention.assign_attention_ids(items)

    assert engine.find_attention(items, "a-0002") == 1
    assert engine.find_attention(items, "licence") == 1
    assert engine.find_attention(items, "A-9999") is None
    assert engine.find_attention(items, "") is None


# --------------------------------------------------------------------------- #
# the commands
# --------------------------------------------------------------------------- #


def test_a_healthy_team_prints_nothing_from_attention_list(cli, project: Path, capsys) -> None:
    """The panel is paid for by the items on it: no items, no output, not even a banner."""
    root = init(cli, project)
    capsys.readouterr()

    assert engine.main(["--project", str(project), "attention", "list"]) == 0
    assert capsys.readouterr().out == ""
    assert engine.parse_attention(engine.attention_path(root)) == []


def test_attention_add_then_list_shows_one_line_per_open_item_oldest_first(
    cli, project: Path, capsys
) -> None:
    init(cli, project)
    assert cli("--project", project, "task", "add", "developer", "push the release") == 0
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "attention",
            "add",
            "--text",
            "grant the push",
            "--kind",
            "authorization",
            "--task",
            "T-0001",
            "--by",
            "Developer-1",
        )
        == 0
    )
    assert (
        cli(
            "--project",
            project,
            "attention",
            "add",
            "--text",
            "pick a licence",
            "--kind",
            "decision",
            "--by",
            "CEO",
        )
        == 0
    )
    capsys.readouterr()

    engine.main(["--project", str(project), "attention", "list"])
    lines = capsys.readouterr().out.strip().splitlines()

    assert len(lines) == 2
    assert lines[0].startswith("A-0001 [authorization] T-0001 by Developer-1 ")
    assert lines[0].endswith("grant the push")
    assert lines[1].startswith("A-0002 [decision] by CEO ")
    assert lines[1].endswith("pick a licence")


def test_attention_resolve_closes_the_item_and_leaves_the_panel(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    cli(
        "--project",
        project,
        "attention",
        "add",
        "--text",
        "grant the push",
        "--kind",
        "authorization",
        "--by",
        "CEO",
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "attention",
            "resolve",
            "A-0001",
            "--by",
            "CEO",
            "--resolution",
            "the user authorized it",
        )
        == 0
    )
    capsys.readouterr()

    engine.main(["--project", str(project), "attention", "list"])
    assert capsys.readouterr().out == ""
    stored = engine.parse_attention(engine.attention_path(root))[0]
    assert stored["status"] == "resolved"
    assert stored["resolution"] == "the user authorized it"
    assert stored["resolved_by"] == "CEO"
    assert stored["resolved"]


def test_resolving_an_item_twice_is_refused(cli, project: Path, capsys) -> None:
    init(cli, project)
    cli(
        "--project",
        project,
        "attention",
        "add",
        "--text",
        "pick a licence",
        "--kind",
        "decision",
        "--by",
        "CEO",
    )
    assert (
        cli(
            "--project",
            project,
            "attention",
            "resolve",
            "A-0001",
            "--by",
            "CEO",
            "--resolution",
            "MIT",
        )
        == 0
    )

    assert (
        cli(
            "--project",
            project,
            "attention",
            "resolve",
            "A-0001",
            "--by",
            "CEO",
            "--resolution",
            "again",
        )
        != 0
    )


def test_attention_add_and_resolve_are_recorded_in_the_ledger(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    cli(
        "--project",
        project,
        "attention",
        "add",
        "--text",
        "grant the push",
        "--kind",
        "authorization",
        "--by",
        "CEO",
    )
    cli(
        "--project",
        project,
        "attention",
        "resolve",
        "A-0001",
        "--by",
        "CEO",
        "--resolution",
        "authorized",
    )

    actions = ledger_actions(root)

    assert "attention.add" in actions
    assert "attention.resolve" in actions
    assert actions.index("attention.add") < actions.index("attention.resolve")


def test_attention_add_refuses_an_unknown_author(cli, project: Path) -> None:
    init(cli, project)

    assert (
        cli(
            "--project",
            project,
            "attention",
            "add",
            "--text",
            "who asked?",
            "--kind",
            "blocker",
            "--by",
            "ghost-9",
        )
        != 0
    )


def test_attention_add_refuses_a_task_id_no_queue_holds(cli, project: Path, capsys) -> None:
    """An item that names a task is what releases it in `stage`: a phantom id must not be stored."""
    root = init(cli, project)
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "attention",
            "add",
            "--text",
            "grant the push",
            "--kind",
            "authorization",
            "--task",
            "T-9999",
            "--by",
            "CEO",
        )
        != 0
    )
    assert engine.parse_attention(engine.attention_path(root)) == []
    assert "T-9999" in capsys.readouterr().err


def test_attention_resolve_refuses_an_unknown_item(cli, project: Path) -> None:
    init(cli, project)

    assert (
        cli(
            "--project",
            project,
            "attention",
            "resolve",
            "A-9999",
            "--by",
            "CEO",
            "--resolution",
            "nothing",
        )
        != 0
    )


# --------------------------------------------------------------------------- #
# the stop gate
# --------------------------------------------------------------------------- #


def _attention_section(root: Path) -> dict:
    return next(sec for sec in engine.gate_report(root)["sections"] if sec["key"] == "attention")


def test_an_open_authorization_blocks_the_stop_gate(cli, project: Path) -> None:
    root = init(cli, project)
    engine.write_attention(
        engine.attention_path(root),
        [engine.new_attention("grant the push", kind="authorization", by="CEO")],
    )

    report = engine.gate_report(root)

    assert any("need authorization" in blocker for blocker in report["blockers"])
    assert any("A-0001" in line for line in _attention_section(root)["lines"])


def test_an_open_blocker_is_informational_and_only_counts(cli, project: Path) -> None:
    """A blocker is recorded and shown, but it must not hold the team's STOP."""
    root = init(cli, project)
    engine.write_attention(
        engine.attention_path(root),
        [
            engine.new_attention("waiting on CI", kind="blocker", by="Developer-1"),
            engine.new_attention("waiting on a vendor", kind="blocker", by="CEO"),
        ],
    )

    report = engine.gate_report(root)

    assert not any("authorization" in blocker for blocker in report["blockers"])
    lines = _attention_section(root)["lines"]
    assert any(line.startswith("2 open attention item(s): 0 authorization") for line in lines)


def test_a_resolved_authorization_no_longer_blocks_the_stop_gate(cli, project: Path) -> None:
    root = init(cli, project)
    items = [engine.new_attention("grant the push", kind="authorization", by="CEO")]
    engine.write_attention(engine.attention_path(root), items)
    stored = engine.parse_attention(engine.attention_path(root))
    stored[0]["status"] = "resolved"
    stored[0]["resolved_by"] = "CEO"
    stored[0]["resolution"] = "authorized"
    engine.write_attention(engine.attention_path(root), stored)

    report = engine.gate_report(root)

    assert not any("authorization" in blocker for blocker in report["blockers"])
    assert _attention_section(root)["lines"] == ["none"]


def test_loop_prints_the_open_items_and_their_count(cli, project: Path, capsys) -> None:
    root = init(cli, project)
    engine.write_attention(
        engine.attention_path(root),
        [
            engine.new_attention("grant the push", kind="authorization", by="CEO", task="T-0007"),
            engine.new_attention("pick a licence", kind="decision", by="CEO"),
        ],
    )
    capsys.readouterr()

    assert cli("--project", project, "loop") == 1
    out = capsys.readouterr().out

    assert "A-0001 [authorization] T-0007 grant the push" in out
    assert "A-0002 [decision] pick a licence" in out
    assert "2 open attention item(s): 1 authorization, 1 informational" in out
    assert "1 open attention item(s) need authorization: A-0001" in out
