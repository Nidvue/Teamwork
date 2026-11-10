"""Acceptance: the release gate is machine-readable and honest about its verdict.

A user shipping a release runs the checker on their own tree. What they rely on:

* the human report is one line per rule plus a problem count;
* ``--json`` prints a JSON object (not prose with braces in it) carrying a stable
  ``exit_code`` and a per-rule ``status`` in ``{ok, DRIFT, SKIP}``;
* the process exit code **agrees** with that verdict - ``0`` clean, ``1`` drift,
  ``2`` an input that could not be read - so a script can branch on either one.

Every subject is a throwaway release tree built in ``tmp_path`` and driven as a
subprocess. No socket is opened: the fixture and the run are ``--offline``.

Owner: reviewer. Task: T-0003. Requirement: acceptance layer, area
``release-consistency``.
"""

from __future__ import annotations

import json

import pytest
from gate_fixtures import commit_all, git, make_repo, run_checker, write_release_facts

AREA = "release-consistency"
STATUSES = {"ok", "DRIFT", "SKIP"}


def _clean_release_tree(root):
    """A tree whose release facts all agree: one tag, version.py, CHANGELOG."""
    repo = make_repo(root)
    write_release_facts(repo, version="1.0.0", changelog_sections=("1.0.0",))
    commit_all(repo)
    git(repo, "tag", "v1.0.0")
    return repo


def _drifted_release_tree(root):
    """The same tree with one published claim that disagrees: a stray tag."""
    repo = _clean_release_tree(root)
    git(repo, "tag", "v1.0.1")
    return repo


@pytest.mark.parametrize(
    ("builder", "expected_rc", "expected_problems"),
    [
        pytest.param(_clean_release_tree, 0, 0, id="clean"),
        pytest.param(_drifted_release_tree, 1, None, id="drift"),
    ],
)
def test_json_verdict_agrees_with_the_exit_code(tmp_path, builder, expected_rc, expected_problems):
    """ACCEPT: `--json` parses, carries a verdict, and matches the exit code."""
    repo = builder(tmp_path / builder.__name__)

    proc = run_checker(repo, "--offline", "--json")

    assert proc.returncode == expected_rc, (
        f"the process exit code must be the verdict ({expected_rc}), got {proc.returncode}:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - the assertion below reports it
        pytest.fail(f"--json did not print a JSON object ({exc}):\n{proc.stdout}")

    assert set(payload) == {"problems", "rules", "exit_code"}, sorted(payload)
    assert payload["exit_code"] == proc.returncode, (
        "the machine-readable verdict and the process exit code disagree: a script "
        f"branching on either would take a different path ({payload['exit_code']} vs "
        f"{proc.returncode})"
    )
    assert isinstance(payload["problems"], list)
    if expected_problems is not None:
        assert payload["problems"] == [], payload["problems"]
    else:
        assert payload["problems"], "a drifted tree reported no problem"
    rules = {rule["id"]: rule for rule in payload["rules"]}
    assert set(rules) == {f"R{n}" for n in range(1, 10)}, sorted(rules)
    assert all(rule["status"] in STATUSES for rule in payload["rules"]), payload["rules"]
    assert all(isinstance(rule["detail"], str) and rule["detail"] for rule in payload["rules"])


def test_human_report_agrees_with_the_json_verdict(tmp_path):
    """ACCEPT: the printed report and `--json` describe the same run."""
    repo = _drifted_release_tree(tmp_path / "both")

    human = run_checker(repo, "--offline")
    machine = run_checker(repo, "--offline", "--json")

    assert human.returncode == machine.returncode == 1, (human.stdout, machine.stdout)
    payload = json.loads(machine.stdout)
    drifts = [rule for rule in payload["rules"] if rule["status"] == "DRIFT"]
    assert drifts, payload
    for rule in drifts:
        assert f"{rule['id']} DRIFT" in human.stdout, (
            f"{rule['id']} is DRIFT in --json but not in the printed report:\n{human.stdout}"
        )
    assert f"# release consistency: {len(payload['problems'])} problem(s)" in human.stdout, (
        human.stdout
    )


def test_clean_tree_reports_every_rule_not_a_bare_pass(tmp_path):
    """ACCEPT: a clean run names all nine rules, so 'clean' is earned per rule."""
    repo = _clean_release_tree(tmp_path / "rules")

    proc = run_checker(repo, "--offline")

    assert proc.returncode == 0, proc.stdout
    for number in range(1, 10):
        assert f"R{number} " in proc.stdout, f"rule R{number} was not reported:\n{proc.stdout}"
    assert "SKIP offline" in proc.stdout, (
        "the offline mode must say which rules it skipped and why:\n" + proc.stdout
    )


def test_an_unreadable_tree_is_not_silently_clean(tmp_path):
    """ACCEPT: a missing exception record makes the gate exit 2, never 0."""
    repo = make_repo(tmp_path / "no-exceptions")
    write_release_facts(repo, exceptions=False)
    commit_all(repo)

    proc = run_checker(repo, "--offline", "--json")

    assert proc.returncode == 2, (
        f"a tree the gate cannot read must exit 2, got {proc.returncode}:\n{proc.stdout}"
    )
    payload = json.loads(proc.stdout)
    assert payload["exit_code"] == 2, payload["exit_code"]
    assert payload["problems"] == [], "an unreadable input is not drift: " + str(payload)
