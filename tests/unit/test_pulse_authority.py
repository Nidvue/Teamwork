"""Proactive work is recorded before it is acted on (AC-9).

Why these tests exist: the pulse hands out ready work by itself, so a team that
has not yet accepted proactive work has no way to see what it *would* have done
without also having done it. The accept mode - ``off`` / ``observe`` / ``auto``,
from the team ``Settings.json`` or one ``--mode`` run - is that gate, and
``task next`` honours it for a task whose mandate is ``inferred``.

Pinned here: an absent ``PulseMode`` reads as ``auto`` (every tree written before
the key keeps dispatching); ``observe`` prints the would-accept plan, records
``pulse.observe`` and claims nothing even with ``--commit`` (exit 0); ``off``
reports only; ``auto`` claims; ``--mode`` overrides one run and names its source;
an unrecognised value is read as ``observe``, never ``auto``; ``task next``
refuses an inferred task in observe and off, naming its basis and the mode, takes
it in auto, and is unaffected for an explicit task.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teamwork import engine

# One developer lane is all the pulse needs to plan a dispatch.
ROSTER = "ceo,developer-1"


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ROSTER, "--no-git") == 0
    return team_root(project)


def set_mode(root: Path, mode: object) -> None:
    """Write (or remove, for None) the accept mode in the team Settings.json.

    Any JSON value may be written: the numeric case is the one that decides
    whether the key is registered as a non-provider, so the helper must not
    quietly coerce it to a string.
    """
    path = engine.providers_path(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    if mode is None:
        data.pop(engine.PULSE_MODE_KEY, None)
    else:
        data[engine.PULSE_MODE_KEY] = mode
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def add_task(
    cli,
    project: Path,
    title: str,
    priority: str = "P2",
    mandate: str = "explicit",
    basis: str = "",
) -> str:
    argv = ["--project", project, "task", "add", "developer", title, "--priority", priority]
    if mandate != "explicit":
        argv += ["--mandate", mandate, "--basis", basis]
    assert cli(*argv) == 0
    path = engine.task_file(team_root(project), "developer")
    return [t for t in engine.parse_tasks(path) if t["title"] == title][-1]["id"]


def task_in(root: Path, handle: str) -> dict:
    tasks = engine.parse_tasks(engine.task_file(root, "developer"))
    return [t for t in tasks if t["id"] == handle][0]


def records(root: Path, action: str) -> list:
    return [r for r in engine.ledger_read(root) if r["action"] == action]


@pytest.fixture
def team(cli, project: Path) -> tuple:
    return cli, project, init(cli, project)


def test_a_settings_file_without_a_pulse_mode_reads_as_auto(team, capsys) -> None:
    """Backward compatibility: every existing tree keeps dispatching."""
    cli, project, root = team
    set_mode(root, None)
    add_task(cli, project, "ship the exporter")

    assert cli("--project", project, "pulse", "--commit") == 0
    out = capsys.readouterr().out
    assert engine.load_pulse_mode(root)[0] == "auto"
    assert "# accept mode: auto (from default" in out, out
    assert task_in(root, "T-0001")["status"] == "doing"
    assert task_in(root, "T-0001")["claimed_by"].lower() == "developer-1"


def test_observe_records_the_would_accept_plan_and_claims_nothing(team, capsys) -> None:
    cli, project, root = team
    set_mode(root, "observe")
    add_task(cli, project, "ship the importer")

    assert cli("--project", project, "pulse", "--commit") == 0
    out = capsys.readouterr().out
    assert "# accept mode: observe (from Settings.json PulseMode)" in out, out
    assert "## would accept (observe - nothing is claimed)" in out, out
    assert "Developer-1" in out and "<- T-0001" in out, out
    assert "--commit downgraded" in out and "claimed 0" in out, out

    task = task_in(root, "T-0001")
    assert task["status"] == "todo", "observe claimed work it only assessed"
    assert not task["claimed_by"]

    observed = records(root, "pulse.observe")
    assert len(observed) == 1, observed
    assert observed[0]["target"] == "T-0001"
    assert "Developer-1" in observed[0]["detail"] and "observe" in observed[0]["detail"]
    # An unattributed ledger line cannot be audited: the record names its actor.
    assert observed[0]["actor"] == "ceo"

    assert cli("--project", project, "pulse", "--agent", "ceo-2") == 0
    capsys.readouterr()
    assert records(root, "pulse.observe")[-1]["actor"] == "ceo-2"


def test_auto_claims_the_ready_task(team, capsys) -> None:
    cli, project, root = team
    set_mode(root, "auto")
    add_task(cli, project, "ship the summariser")

    assert cli("--project", project, "pulse", "--commit") == 0
    assert "# accept mode: auto (from Settings.json PulseMode)" in capsys.readouterr().out
    task = task_in(root, "T-0001")
    assert task["status"] == "doing"
    assert task["claimed_by"].lower() == "developer-1"
    assert records(root, "pulse.observe") == []


def test_off_reports_the_plan_and_claims_nothing(team, capsys) -> None:
    cli, project, root = team
    set_mode(root, "off")
    add_task(cli, project, "ship the reconciler")

    assert cli("--project", project, "pulse", "--commit") == 0
    out = capsys.readouterr().out
    assert "# accept mode: off (from Settings.json PulseMode)" in out, out
    assert "## dispatch plan (off - report only, nothing is claimed)" in out, out
    assert "Developer-1" in out and "<- T-0001" in out, out
    assert "--commit downgraded" in out and "claimed 0" in out, out

    task = task_in(root, "T-0001")
    assert task["status"] == "todo"
    assert not task["claimed_by"]
    assert records(root, "pulse.observe") == [], "off is a report, not an assessment record"


def test_observe_records_even_without_commit_and_claims_nothing(team, capsys) -> None:
    """The assessment is recorded by the report itself, not by a refused commit."""
    cli, project, root = team
    set_mode(root, "observe")
    add_task(cli, project, "ship the dashboard")

    assert cli("--project", project, "pulse") == 0
    out = capsys.readouterr().out
    assert "# observe: 1 assignment(s) recorded as pulse.observe" in out, out
    assert "report only - --commit would not claim here" in out, out
    assert "no lane has been given work" in out, out

    assert task_in(root, "T-0001")["status"] == "todo"
    assert len(records(root, "pulse.observe")) == 1


@pytest.mark.parametrize(
    ("stored", "override"),
    [("auto", "observe"), ("auto", "off"), ("observe", "auto")],
)
def test_pulse_mode_overrides_one_run_and_names_its_source(
    cli, project: Path, capsys, stored: str, override: str
) -> None:
    """The flag wins in both directions, and never rewrites the setting."""
    root = init(cli, project)
    set_mode(root, stored)
    first = add_task(cli, project, "ship the migrator", "P1")

    assert cli("--project", project, "pulse", "--mode", override, "--commit") == 0
    out = capsys.readouterr().out
    assert f"# accept mode: {override} (from --mode)" in out, out
    claimed = task_in(root, first)["status"] == "doing"
    assert claimed is (override == "auto"), "--mode must win over Settings.json"
    # Only the record-taking mode writes an assessment.
    assert bool(records(root, "pulse.observe")) is (override == "observe")

    # The override is one run only: the stored setting decides the next pulse.
    kept = json.loads(engine.providers_path(root).read_text(encoding="utf-8"))
    assert kept[engine.PULSE_MODE_KEY] == stored
    third = add_task(cli, project, "ship the reconciler")
    assert cli("--project", project, "pulse", "--commit") in (0, 3)
    capsys.readouterr()
    assert task_in(root, third)["status"] == ("doing" if stored == "auto" else "todo")


def test_an_unrecognised_mode_is_read_as_observe_not_auto(team, capsys) -> None:
    """A typo must not silently authorise proactive work."""
    cli, project, root = team
    set_mode(root, "sometimes")
    add_task(cli, project, "ship the probe")

    assert cli("--project", project, "pulse", "--commit") == 0
    out = capsys.readouterr().out
    assert "# accept mode: observe" in out and "read as observe" in out, out
    assert task_in(root, "T-0001")["status"] == "todo"


@pytest.mark.parametrize("mode", ["observe", "off"])
def test_task_next_refuses_an_inferred_task_when_the_mode_is_not_auto(
    cli, project: Path, capsys, mode: str
) -> None:
    root = init(cli, project)
    set_mode(root, mode)
    handle = add_task(
        cli,
        project,
        "reconcile the incident log",
        "P0",
        "inferred",
        "the incident log shows unowned rework",
    )

    assert cli("--project", project, "task", "next", "developer-1") == 3
    out = capsys.readouterr().out
    assert f"refused {handle} [inferred]" in out, out
    assert f"accept mode is {mode}" in out, out
    assert "taking inferred work needs auto" in out, out
    assert "1 refused: the accept mode is not auto" in out, out
    assert "the incident log shows unowned rework" in out, out

    task = task_in(root, handle)
    assert task["mandate"] == "inferred"
    assert task["status"] == "todo", "a refused inferred task was claimed anyway"
    assert not task["claimed_by"]


def test_auto_takes_an_inferred_task(cli, project: Path) -> None:
    root = init(cli, project)
    set_mode(root, "auto")
    handle = add_task(
        cli,
        project,
        "reconcile the incident log",
        "P0",
        "inferred",
        "the incident log shows unowned rework",
    )

    assert cli("--project", project, "task", "next", "developer-1") == 0
    task = task_in(root, handle)
    assert task["status"] == "doing"
    assert task["claimed_by"].lower() == "developer-1"


@pytest.mark.parametrize("mode", ["observe", "off"])
def test_an_explicit_task_is_unaffected_by_the_mode(cli, project: Path, mode: str) -> None:
    root = init(cli, project)
    set_mode(root, mode)
    handle = add_task(cli, project, "fix the parser", "P0")

    assert cli("--project", project, "task", "next", "developer-1") == 0
    task = task_in(root, handle)
    assert task["status"] == "doing"
    assert task["claimed_by"].lower() == "developer-1"


def test_a_refusal_does_not_block_an_explicit_task_in_the_same_queue(
    cli, project: Path, capsys
) -> None:
    root = init(cli, project)
    set_mode(root, "observe")
    inferred = add_task(
        cli,
        project,
        "reconcile the incident log",
        "P0",
        "inferred",
        "the incident log shows unowned rework",
    )
    explicit = add_task(cli, project, "fix the parser", "P2")

    assert cli("--project", project, "task", "next", "developer-1") == 0
    out = capsys.readouterr().out
    assert f"refused {inferred} [inferred]" in out, out
    assert task_in(root, inferred)["status"] == "todo"
    assert task_in(root, explicit)["status"] == "doing"


def test_pulse_mode_is_registered_as_a_non_provider_settings_key(team) -> None:
    """The key must be listed, or `slot`/`parallel` read it as a provider cap."""
    _cli, _project, root = team
    set_mode(root, "observe")
    assert engine.PULSE_MODE_KEY not in engine.load_providers(root)
    assert engine.PULSE_MODE_KEY in engine.SETTINGS_NON_PROVIDER


@pytest.mark.parametrize("value", ["observe", 0])
def test_parallel_prints_no_pulse_mode_provider(cli, project: Path, capsys, value: object) -> None:
    """A phantom provider here corrupts every free-slot count the pulse plans from.

    The numeric case is the one that bites: `"PulseMode": 0` is a natural mistake
    for `off`, and `load_providers` reads any numeric Settings value as a cap, so
    only the registration in ``SETTINGS_NON_PROVIDER`` keeps it out. Both forms
    are also still read as accept modes - a typo must not authorise proactive work.
    """
    root = init(cli, project)
    set_mode(root, value)
    assert cli("--project", project, "parallel") == 0
    out = capsys.readouterr().out
    assert "PulseMode" not in out, out
    assert engine.load_pulse_mode(root)[0] == "observe"
