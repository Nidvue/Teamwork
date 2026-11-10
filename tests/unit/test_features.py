"""The feature record, its state machine and its two write verbs (Architecture.md 13).

Every shape here is frozen by `docs/Team/Architecture.md` section 13: the seven
record fields, the state each transition may leave and who may issue it, the
printed line and the exit code of `feature add|set|list|check`. The strings are
asserted verbatim, because a `feature`-layer record (13.4) has to assert them and
a paraphrase that drifts is a gate that stops meaning the same thing.

Owner: team-leader. Task: T-0042. Requirements: Architecture.md 13.1, 13.2, 13.4.
"""

from __future__ import annotations

from pathlib import Path

from teamwork import engine
from teamwork.config import (
    LAYER_CELL,
    LAYER_OWNER,
    LAYER_WHAT,
    TEST_LAYERS,
)

AGENTS = "ceo,architect-1,team-leader-1,team-leader-2,developer-1,tester-1"


def team_root(project: Path) -> Path:
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def init(cli, project: Path, agents: str = AGENTS) -> Path:
    assert cli("--project", project, "init", "--agents", agents, "--no-git") == 0
    seed_docs(project)
    return team_root(project)


def features_path(project: Path) -> Path:
    return project / "docs" / "Team" / "Features.md"


ARCHITECTURE_DOC = """# ARCHITECTURE - the frozen contract

Owner: Architect.

## 13. Feature teams

Frozen design.
"""

DECISIONS_DOC = """# DECISIONS

## D-20261029-Architect-2 - the single line

- date: 2026-10-29
"""


def seed_docs(project: Path) -> None:
    """A resolvable interface: one anchor and one decision id (13.1's two shapes)."""
    docs = project / "docs" / "Team"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "Architecture.md").write_text(ARCHITECTURE_DOC, encoding="utf-8")
    (docs / "Decisions.md").write_text(DECISIONS_DOC, encoding="utf-8")


def said(capsys) -> str:
    """Everything the command said, whichever stream the engine used."""
    captured = capsys.readouterr()
    return captured.out + captured.err


def seed(project: Path, *records: dict) -> None:
    """Write the records file by hand: the shape a merge or a peer lane leaves."""
    records = list(records)
    for n, record in enumerate(records, start=1):
        record.setdefault("id", f"F-{n:04d}")
        record.setdefault("created", engine.today_iso())
        record.setdefault("updated", engine.today_iso())
    features_path(project).parent.mkdir(parents=True, exist_ok=True)
    engine.write_features(features_path(project), records)


def feat(
    statement: str,
    owner: str = "Team-Leader-1",
    paths=(),
    interface: str = "-",
    state: str = "proposed",
    depends_on=(),
) -> dict:
    return engine.new_feature(statement, owner, list(paths), interface, list(depends_on), state)


def add(cli, project: Path, *extra: str) -> int:
    return cli(
        "--project",
        project,
        "feature",
        "add",
        *extra,
    )


# --------------------------------------------------------------------------- #
# 13.1 the record
# --------------------------------------------------------------------------- #


def test_a_feature_record_round_trips_through_the_file(tmp_path: Path) -> None:
    """The file's shape is one header row and one metadata block per record."""
    path = tmp_path / "Features.md"
    engine.write_features(
        path,
        [
            feat(
                "ship the record set",
                paths=["src/a.py", "src/b.py"],
                interface="Architecture.md#13",
            ),
            feat("ship the check", paths=["tools/"], depends_on=["F-0001"], state="ready"),
        ],
    )
    records = engine.parse_features(path)

    assert [r["id"] for r in records] == ["F-0001", "F-0002"]
    assert records[0]["statement"] == "ship the record set"
    assert records[0]["owner"] == "Team-Leader-1"
    assert records[0]["interface"] == "Architecture.md#13"
    assert records[0]["paths"] == ["src/a.py", "src/b.py"]
    assert records[0]["depends_on"] == []
    assert records[0]["state"] == "proposed"
    assert records[1]["paths"] == ["tools/"]
    assert records[1]["depends_on"] == ["F-0001"]
    assert records[1]["state"] == "ready"
    # Rendering is pure and idempotent: the second render is byte-identical.
    first = engine.render_features(records, path)
    assert engine.render_features(engine.parse_features(path), path) == first


def test_an_unknown_state_on_disk_falls_back_to_proposed(tmp_path: Path) -> None:
    """A torn or hand-edited state is not a state the machine may act on."""
    path = tmp_path / "Features.md"
    path.write_text(
        "# Features\n\n## F-0001 · a slice\n\n- owner: Team-Leader-1\n"
        "- interface: -\n- paths: src/a.py\n- depends-on: -\n- state: bogus\n",
        encoding="utf-8",
    )
    assert engine.parse_features(path)[0]["state"] == "proposed"


def test_the_next_id_is_one_more_than_the_highest_visible_number() -> None:
    """Allocation is max+1 over what the caller sees: no counter, no reservation."""
    assert engine.next_feature_id([]) == "F-0001"
    records = [{"id": "F-0007"}, {"id": "F-0003"}]
    assert engine.next_feature_id(records) == "F-0008"


def test_the_task_feature_field_renders_only_when_it_is_set(tmp_path: Path) -> None:
    """`task add --feature` adds one metadata line; without it the queue is unchanged."""
    path = tmp_path / "TaskQueue.md"
    plain = engine.new_task("unsliced repair")
    engine.write_tasks(path, [plain], "developer")
    without = path.read_text(encoding="utf-8")
    assert "- feature:" not in without

    sliced = engine.new_task("wire the field", feature="F-0001")
    engine.write_tasks(path, [sliced], "developer")
    text = path.read_text(encoding="utf-8")
    assert "- deps: \n- feature: F-0001\n- shared: " in text
    assert engine.parse_tasks(path)[0]["feature"] == "F-0001"

    engine.write_tasks(path, [engine.new_task("unsliced repair")], "developer")
    assert path.read_text(encoding="utf-8") == without


# --------------------------------------------------------------------------- #
# 13.2 add
# --------------------------------------------------------------------------- #


def test_add_files_the_callers_own_slice_in_proposed(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "ship the feature records",
        "--owner",
        "team-leader-1",
        "--paths",
        "src/a.py,src/b.py",
        "--by",
        "team-leader-1",
    )
    out = capsys.readouterr().out

    assert code == 0
    assert (
        "teamwork: features + F-0001 [proposed] ship the feature records"
        "  owner=Team-Leader-1 paths=2" in out
    )
    assert engine.parse_features(features_path(project))[0]["state"] == "proposed"


def test_add_refuses_an_owner_that_is_not_the_caller(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "a slice",
        "--owner",
        "team-leader-1",
        "--paths",
        "src/a.py",
        "--by",
        "team-leader-2",
    )
    out = said(capsys)

    assert code == 2
    assert (
        "teamwork: no feature added: the owner must be the caller: --by Team-Leader-2 "
        "cannot file a record owned by Team-Leader-1" in out
    )
    assert engine.parse_features(features_path(project)) == []


def test_add_refuses_an_owner_that_is_not_a_team_leader(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "a slice",
        "--owner",
        "developer-1",
        "--paths",
        "src/a.py",
        "--by",
        "developer-1",
    )
    assert code == 2
    assert (
        "teamwork: no feature added: the owner must be one team-leader instance: "
        "'Developer-1' is a developer" in said(capsys)
    )


def test_a_refused_add_consumes_no_id(cli, project, capsys) -> None:
    """13.1: nothing is written and nothing is reserved, so the next add is F-0001."""
    init(cli, project)
    capsys.readouterr()
    assert (
        add(
            cli,
            project,
            "a slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/*.py",
            "--by",
            "team-leader-1",
        )
        == 2
    )
    assert (
        add(
            cli,
            project,
            "the slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/a.py",
            "--by",
            "team-leader-1",
        )
        == 0
    )
    assert [r["id"] for r in engine.parse_features(features_path(project))] == ["F-0001"]


def test_add_creates_the_records_file_when_it_is_absent(cli, project, capsys) -> None:
    """A write verb's exit vocabulary is 0 and 2: an absent file is an empty set."""
    init(cli, project)
    features_path(project).unlink()
    capsys.readouterr()
    code = add(
        cli,
        project,
        "the first slice",
        "--owner",
        "team-leader-1",
        "--paths",
        "src/a.py",
        "--by",
        "team-leader-1",
    )

    assert code == 0
    assert [r["id"] for r in engine.parse_features(features_path(project))] == ["F-0001"]
    assert features_path(project).read_text(encoding="utf-8").startswith("# Features -")


def test_a_duplicate_statement_is_not_a_refusal(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert (
        add(
            cli,
            project,
            "one slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/a.py",
            "--by",
            "team-leader-1",
        )
        == 0
    )
    assert (
        add(
            cli,
            project,
            "one slice",
            "--owner",
            "team-leader-2",
            "--paths",
            "src/z.py",
            "--by",
            "team-leader-2",
        )
        == 0
    )
    assert (
        "teamwork: F-0001 already records that statement - not duplicated"
        in capsys.readouterr().out
    )
    assert len(engine.parse_features(features_path(project))) == 1


def test_a_bare_role_with_several_instances_is_ambiguous_and_exits_two(
    cli, project, capsys
) -> None:
    """13.2: `--by` resolves to an instance or refuses; a role is never an authority."""
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "a slice",
        "--owner",
        "team-leader",
        "--paths",
        "src/a.py",
        "--by",
        "team-leader",
    )
    out = said(capsys)

    assert code == 2
    assert (
        "teamwork: 'team-leader' is ambiguous: the team-leader role has several "
        "instances (Team-Leader-1, Team-Leader-2). Name the one acting." in out
    )


def test_an_unknown_caller_is_refused_by_name(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli, project, "a slice", "--owner", "ghost-1", "--paths", "src/a.py", "--by", "ghost-1"
    )
    out = said(capsys)

    assert code == 2
    assert "unknown actor 'ghost-1'. Known agents: " in out
    assert "CEO" in out and "Team-Leader-1" in out


# --------------------------------------------------------------------------- #
# 13.2 set: the state machine and its refusals
# --------------------------------------------------------------------------- #


def test_only_the_architect_opens_a_record_and_the_freeze_is_required(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    assert (
        add(
            cli,
            project,
            "the slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/a.py",
            "--by",
            "team-leader-1",
        )
        == 0
    )

    assert (
        cli(
            "--project",
            project,
            "feature",
            "set",
            "F-0001",
            "--state",
            "ready",
            "--by",
            "team-leader-1",
        )
        == 2
    )
    assert (
        "teamwork: F-0001 stays [proposed]: ready is the Architect's freeze: --by must "
        "name an architect instance (you are Team-Leader-1)" in capsys.readouterr().out
    )
    assert (
        cli(
            "--project",
            project,
            "feature",
            "set",
            "F-0001",
            "--state",
            "ready",
            "--by",
            "architect-1",
        )
        == 2
    )
    assert (
        "teamwork: F-0001 stays [proposed]: ready needs a frozen interface: "
        "--interface <anchor-or-decision>" in capsys.readouterr().out
    )


def test_the_freeze_is_the_interface_not_the_word(cli, project, capsys) -> None:
    """A reference that does not resolve is refused as a non-resolving reference."""
    init(cli, project)
    capsys.readouterr()
    assert (
        add(
            cli,
            project,
            "the slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/a.py",
            "--by",
            "team-leader-1",
        )
        == 0
    )
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "ready",
        "--interface",
        "Architecture.md#99",
        "--by",
        "architect-1",
    )
    assert code == 2
    assert "interface does not resolve" in capsys.readouterr().out


def test_a_leader_moves_its_own_record_through_active(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(
        project,
        feat("the slice", paths=["src/a.py"], interface="Architecture.md#13", state="ready"),
    )
    assert (
        cli(
            "--project",
            project,
            "feature",
            "set",
            "F-0001",
            "--state",
            "active",
            "--by",
            "team-leader-1",
        )
        == 0
    )
    assert "teamwork: features ~ F-0001 [ready] -> [active]" in capsys.readouterr().out
    assert (
        cli(
            "--project",
            project,
            "feature",
            "set",
            "F-0001",
            "--state",
            "active",
            "--by",
            "team-leader-1",
        )
        == 0
    )
    assert "teamwork: features ~ F-0001 [active] -> [active]" in capsys.readouterr().out


def test_a_squad_instance_cannot_move_the_record(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"], state="ready"))
    code = cli(
        "--project", project, "feature", "set", "F-0001", "--state", "active", "--by", "developer-1"
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [ready]: active is the record owner's transition: "
        "--by must be Team-Leader-1 (you are Developer-1)" in capsys.readouterr().out
    )


def test_a_skipped_state_is_refused_in_one_frozen_sentence(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "active",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [proposed]: a state cannot be skipped forward "
        "(proposed -> ready -> active -> done)" in capsys.readouterr().out
    )


def test_an_unknown_state_names_the_five(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "shipped",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [proposed]: unknown state 'shipped' "
        "(proposed, ready, active, done, dropped)" in capsys.readouterr().out
    )


def test_an_unknown_record_reads_as_no_record(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project", project, "feature", "set", "F-0009", "--state", "ready", "--by", "architect-1"
    )

    assert code == 2
    assert "teamwork: F-???? stays [-]: unknown feature F-0009" in capsys.readouterr().out


def test_done_waits_for_every_task_carrying_the_feature(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(
        project,
        feat("the slice", paths=["src/a.py"], interface="Architecture.md#13", state="active"),
    )
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    code = cli(
        "--project", project, "feature", "set", "F-0001", "--state", "done", "--by", "team-leader-1"
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [active]: done while 1 task(s) carrying feature: F-0001 "
        "are not done (T-0001)" in capsys.readouterr().out
    )


def test_dropping_an_active_feature_needs_its_tasks_terminal(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(
        project,
        feat("the slice", paths=["src/a.py"], interface="Architecture.md#13", state="active"),
    )
    assert (
        cli("--project", project, "task", "add", "developer", "the work", "--feature", "F-0001")
        == 0
    )
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "dropped",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [active]: dropped from [active] needs every task "
        "carrying feature: F-0001 terminal (open: T-0001)" in capsys.readouterr().out
    )


def test_a_terminal_record_never_reopens(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"], state="dropped"))
    code = cli(
        "--project", project, "feature", "set", "F-0001", "--state", "ready", "--by", "architect-1"
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [dropped]: a record in [dropped] is terminal; "
        "open a new feature" in capsys.readouterr().out
    )


def test_paths_are_final_once_the_work_starts(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(
        project,
        feat("the slice", paths=["src/a.py"], interface="Architecture.md#13", state="active"),
    )
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "active",
        "--paths",
        "src/b.py",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [active]: paths cannot change from [active]: the "
        "claim is final when the work starts" in capsys.readouterr().out
    )


def test_the_interface_is_the_architects_field_on_an_edit_too(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "proposed",
        "--interface",
        "Architecture.md#13",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert (
        "teamwork: F-0001 stays [proposed]: interface is the Architect's freeze: "
        "--by must name an architect instance (you are Team-Leader-1)" in capsys.readouterr().out
    )


def test_a_set_prints_one_field_per_changed_field_in_record_order(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "ready",
        "--interface",
        "Architecture.md#13",
        "--by",
        "architect-1",
    )

    assert code == 0
    assert (
        "teamwork: features ~ F-0001 [proposed] -> [ready] interface=Architecture.md#13"
        in capsys.readouterr().out
    )


# --------------------------------------------------------------------------- #
# 13.1 depends-on
# --------------------------------------------------------------------------- #


def test_a_dependency_must_already_be_done(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the first slice", paths=["src/a.py"], state="active"))
    code = add(
        cli,
        project,
        "the second slice",
        "--owner",
        "team-leader-2",
        "--paths",
        "src/b.py",
        "--depends-on",
        "F-0001",
        "--by",
        "team-leader-2",
    )

    assert code == 2
    assert (
        "teamwork: no feature added: F-0002 depends on in-flight F-0001 (state=active)"
        in capsys.readouterr().out
    )


def test_a_dependency_on_an_unknown_record_names_it(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "the second slice",
        "--owner",
        "team-leader-1",
        "--paths",
        "src/b.py",
        "--depends-on",
        "F-0003",
        "--by",
        "team-leader-1",
    )

    assert code == 2
    assert "teamwork: no feature added: unknown feature F-0003" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# 13.2 list / check: the read verbs and their exit codes
# --------------------------------------------------------------------------- #


def test_list_prints_the_frozen_block_and_dates_it(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(
        project,
        feat(
            "the slice",
            paths=["src/a.py", "src/b.py"],
            interface="Architecture.md#13",
            state="active",
        ),
    )
    assert cli("--project", project, "feature", "list") == 0
    out = capsys.readouterr().out

    assert out.startswith("# Features (1 open / 1 total) @ ")
    assert "- F-0001 [active] the slice" in out
    assert "    owner=Team-Leader-1 interface=Architecture.md#13" in out
    assert "    paths=src/a.py,src/b.py" in out
    assert "    depends-on=-" in out


def test_list_of_an_empty_state_filter_exits_three(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"], state="active"))
    code = cli("--project", project, "feature", "list", "--state", "dropped")
    out = capsys.readouterr().out

    assert code == 3
    assert "# Features (0 open / 0 total) @" in out


def test_list_refuses_an_unknown_state_with_exit_two(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli("--project", project, "feature", "list", "--state", "bogus")

    assert code == 2
    assert (
        "teamwork: feature list: unknown state 'bogus' "
        "(proposed, ready, active, done, dropped)" in capsys.readouterr().out
    )


def test_check_with_no_records_file_exits_one(cli, project, capsys) -> None:
    """The read path's I/O code stays `die`'s 1: there is nothing to answer from."""
    init(cli, project)
    features_path(project).unlink()
    capsys.readouterr()
    assert cli("--project", project, "feature", "check") == 1
    assert "teamwork: no feature records" in said(capsys)


def test_the_json_objects_are_frozen_key_by_key(cli, project, capsys) -> None:
    import json

    init(cli, project)
    capsys.readouterr()
    assert (
        add(
            cli,
            project,
            "the slice",
            "--owner",
            "team-leader-1",
            "--paths",
            "src/a.py",
            "--by",
            "team-leader-1",
            "--json",
        )
        == 0
    )
    added = json.loads(capsys.readouterr().out)
    assert list(added) == ["id", "state", "changed", "rev"]
    assert added["id"] == "F-0001" and added["state"] == "proposed" and added["changed"] is True

    assert cli("--project", project, "feature", "check", "--json") == 0
    checked = json.loads(capsys.readouterr().out)
    assert list(checked) == ["rev", "ok", "features", "problems"]
    assert checked["ok"] is True and checked["problems"] == []

    assert cli("--project", project, "feature", "list", "--json") == 0
    listed = json.loads(capsys.readouterr().out)
    assert list(listed) == ["rev", "open", "total", "features"]
    assert list(listed["features"][0]) == [
        "id",
        "statement",
        "owner",
        "interface",
        "paths",
        "depends_on",
        "state",
        "created",
        "updated",
    ]


def test_a_refused_add_prints_the_null_id_and_the_same_reason(cli, project, capsys) -> None:
    import json

    init(cli, project)
    capsys.readouterr()
    code = add(
        cli,
        project,
        "a slice",
        "--owner",
        "team-leader-1",
        "--paths",
        "src/*.py",
        "--by",
        "team-leader-1",
        "--json",
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert list(payload) == ["id", "state", "changed", "reason", "rev"]
    assert payload["id"] is None and payload["state"] is None
    assert payload["reason"] == ("F-0001 claims a glob (src/*.py); name the directory instead")


def test_a_refused_set_prints_the_current_state_and_reason(cli, project, capsys) -> None:
    import json

    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli(
        "--project",
        project,
        "feature",
        "set",
        "F-0001",
        "--state",
        "active",
        "--by",
        "team-leader-1",
        "--json",
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["id"] == "F-0001"
    assert payload["state"] == "proposed"
    assert payload["changed"] is False
    assert payload["reason"].startswith("a state cannot be skipped forward")


def test_a_read_misuse_prints_one_error_object(cli, project, capsys) -> None:
    import json

    init(cli, project)
    capsys.readouterr()
    seed(project, feat("the slice", paths=["src/a.py"]))
    code = cli("--project", project, "feature", "check", "F-0009", "--json")
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert list(payload) == ["rev", "error"]
    assert payload["error"] == "unknown feature F-0009"


# --------------------------------------------------------------------------- #
# 13.4 the `feature` test layer
# --------------------------------------------------------------------------- #


def test_the_feature_layer_is_registered_like_every_other_layer() -> None:
    assert "feature" in TEST_LAYERS
    assert LAYER_OWNER["feature"] == "team-leader"
    assert LAYER_WHAT["feature"] == (
        "feature isolation: the slice's diff, its standalone build and its frozen interface"
    )
    assert LAYER_CELL["feature"] == "feat"
    # Every other layer keeps its owner: the new layer is additive.
    assert set(LAYER_OWNER) == set(TEST_LAYERS)


def test_the_feature_layer_is_staffed_only_by_a_team_leader(cli, project) -> None:
    """`tests plan` never reports a gap for work nobody owns (13.4)."""
    root = init(cli, project, "ceo,developer-1")
    assert "feature" not in engine.staffed_layers(root)
    engine.scaffold_role(root, "team-leader")
    engine.scaffold_instance(root, "TeamLeader-1", "team-leader")
    assert "feature" in engine.staffed_layers(root)


def test_a_feature_layer_record_needs_the_team_leader_owner(cli, project, capsys) -> None:
    root = init(cli, project)
    assert engine.staffed_layers(root)
    capsys.readouterr()
    code = cli(
        "--project",
        project,
        "tests",
        "add",
        "--layer",
        "feature",
        "--area",
        "F-0001",
        "--command",
        "git diff --name-only main...HEAD",
        "--owner",
        "developer-1",
    )
    # A test-layer ownership refusal keeps `die`'s default code, as every other
    # role-owned write in the engine does; only the feature verbs are frozen at 2.
    assert code == 1
    assert "feature tests belong to the team-leader role" in said(capsys)


def test_a_feature_layer_record_can_be_opened_by_the_team_leader(cli, project, capsys) -> None:
    init(cli, project)
    capsys.readouterr()
    code = cli(
        "--project",
        project,
        "tests",
        "add",
        "--layer",
        "feature",
        "--area",
        "F-0001",
        "--command",
        "git diff --name-only main...HEAD",
        "--task",
        "T-0042",
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "# added TS-0001 feature/f-0001 owner=Team-Leader-1" in out
    assert "feature isolation: the slice's diff" in out
