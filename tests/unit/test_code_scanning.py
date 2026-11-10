"""The forge's code-scanning alerts must reach the role that owns the file (T-0045).

Why this exists: a red code-scanning alert on the default branch is a known defect
in the revision that ships, and nothing in the team ever looked at the forge's
security tab. Measured on this repository's own remote: two `error`-severity
alerts (`py/clear-text-logging-sensitive-data`) open on `scripts/privacy_scan.py`,
both on `main`, with no task, no owner and no gate aware of them.

Pinned here: the alert list is read from the forge (never invented), each alert is
routed by file ownership, a blocking severity makes the command fail, and
``--commit`` files exactly one task per (owner, rule, file) without duplicating an
existing one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from teamwork import engine  # noqa: E402
from teamwork.config import SCAN_BLOCKING, SCAN_OWNER_ROLE, SCAN_ROUTE  # noqa: E402


@pytest.fixture
def workspace(tmp_path: Path, cli) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    roster = "ceo,developer,security-auditor,release-engineer,reviewer"
    assert cli("--project", project, "init", "--agents", roster, "--no-git") == 0
    return project


def run(monkeypatch, project: Path, alerts: list, *argv: str) -> int:
    """Drive ``cmd_code_scanning`` with a fake forge and a captured task queue."""
    monkeypatch.setattr(engine, "_scan_remote", lambda p: ("acme", "shop"))
    monkeypatch.setattr(
        engine, "_scan_alerts", lambda p, limit, full: (alerts, f"gh api fake -> {len(alerts)}")
    )
    args = engine.build_parser().parse_args(["--project", str(project), "code-scanning", *argv])
    return engine.cmd_code_scanning(args)


def alert(number: int, path: str, severity: str = "error", rule: str = "py/log") -> dict:
    return {
        "number": number,
        "rule": rule,
        "severity": severity,
        "description": "d",
        "path": path,
        "line": 12,
        "ref": "refs/heads/main",
        "state": "open",
    }


def team_root(project: Path) -> Path:
    return (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def tasks_of(project: Path, role: str) -> list:
    return engine.parse_tasks(engine.task_file(team_root(project), role))


def test_each_alert_is_routed_to_the_role_that_owns_the_file(monkeypatch, workspace, capsys):
    alerts = [
        alert(1, "scripts/privacy_scan.py"),
        alert(2, "src/teamwork/engine.py"),
        alert(3, ".github/workflows/ci.yml"),
        alert(4, "docs/guide/cli.md"),
    ]
    assert run(monkeypatch, workspace, alerts) == 1  # blocking severities
    out = capsys.readouterr().out
    assert "scripts/privacy_scan.py:12 -> security-auditor" in out
    assert "src/teamwork/engine.py:12 -> developer" in out
    assert ".github/workflows/ci.yml:12 -> release-engineer" in out
    assert "docs/guide/cli.md:12 -> technical-writer" in out
    assert "2 blocking alert(s)" not in out  # four, all blocking
    assert "4 blocking alert(s)" in out


def test_a_low_severity_alert_is_printed_but_does_not_fail_the_gate(monkeypatch, workspace, capsys):
    assert run(monkeypatch, workspace, [alert(9, "src/x.py", severity="note")]) == 0
    out = capsys.readouterr().out
    assert "none blocking" in out


def test_an_unreadable_scanner_is_reported_not_treated_as_zero_alerts(
    monkeypatch, workspace, capsys
):
    """A host with no scanner must say so AND must not pass the gate.

    Measured defect this closes: the command printed "no open alert" and exited 0
    for an unauthenticated gh, a 404 and a repo with no origin - so an unread
    security tab read as a green release gate.
    """
    monkeypatch.setattr(engine, "_scan_remote", lambda p: ("", ""))
    args = engine.build_parser().parse_args(["--project", str(workspace), "code-scanning"])
    assert engine.cmd_code_scanning(args) == 2
    out = capsys.readouterr().out
    assert "no origin remote here" in out
    assert "no open alert" not in out
    assert "UNVERIFIED" in out


def test_an_unauthenticated_forge_does_not_report_zero_alerts(monkeypatch, tmp_path, capsys):
    """The real failure: gh exists but cannot read the security tab."""
    monkeypatch.setattr(engine, "_scan_remote", lambda p: ("acme", "shop"))
    monkeypatch.setattr(
        engine.subprocess,
        "run",
        lambda *a, **k: type(
            "D", (), {"returncode": 1, "stdout": "", "stderr": "gh: not logged in"}
        )(),
    )
    args = engine.build_parser().parse_args(["--project", str(tmp_path), "code-scanning"])
    assert engine.cmd_code_scanning(args) == 2
    out = capsys.readouterr().out
    assert "not readable for acme/shop" in out
    assert "no open alert" not in out


def test_a_dot_directory_route_actually_fires(monkeypatch) -> None:
    """``.github/**`` must route; ``lstrip("./")`` used to strip the leading dot.

    The fallback owner is the release-engineer, which ``.github/**`` also names, so
    a plain equality check stays green when the dot is eaten - the mutant that
    restored ``lstrip("./")`` survived the first version of this test. Poisoning
    the fallback makes the route the only way to get the answer.
    """
    monkeypatch.setattr(engine, "SCAN_OWNER_ROLE", "nobody-owns-this")
    assert engine.scan_owner(".github/workflows/ci.yml") == "release-engineer"
    assert engine.scan_owner(".github/dependabot.yml") == "release-engineer"
    assert engine.scan_owner(".gitignore") == "nobody-owns-this"
    assert engine.scan_owner("./src/teamwork/engine.py") == "developer"
    assert engine.scan_owner("/scripts/privacy_scan.py") == "security-auditor"


def test_routing_is_asked_of_the_real_resolver_not_the_pattern_string() -> None:
    """The old route test grepped the pattern list and passed with a route deleted."""
    from teamwork.config import SCAN_ROUTE as routes

    for pattern, role in routes:
        sample = pattern.replace("**", "probe.txt").replace("*", "probe")
        assert engine.scan_owner(sample) == role, (pattern, role)


def test_commit_stays_red_while_a_blocking_alert_is_open(monkeypatch, workspace, capsys):
    """Filing the fix does not close the gate: the alert is open until the forge says so."""
    assert run(monkeypatch, workspace, [alert(1, "src/a.py")], "--commit") == 1
    assert run(monkeypatch, workspace, [alert(2, "src/b.py", severity="note")], "--commit") == 0


def test_commit_files_one_task_per_owner_rule_and_file(monkeypatch, workspace, capsys):
    alerts = [
        alert(1, "scripts/privacy_scan.py"),
        alert(2, "scripts/privacy_scan.py"),  # same rule and file -> one task
        alert(3, "src/teamwork/engine.py"),
    ]
    assert run(monkeypatch, workspace, alerts, "--commit") == 1
    security = tasks_of(workspace, "security-auditor")
    assert len(security) == 1
    body = security[0]
    assert body["priority"] == "P0", "a blocking alert is not a P2"
    assert "#1,#2" in body["title"] or "#1,#2" in body["shared"]
    assert body["kind"] in ("", "bug")
    assert "security,code-scanning" in body["tags"]
    assert "gh api fake -> 3" in body["evidence"]
    developer = tasks_of(workspace, "developer")
    assert len(developer) == 1
    assert "src/teamwork/engine.py" in developer[0]["title"]


def test_commit_is_idempotent(monkeypatch, workspace, capsys):
    alerts = [alert(1, "src/a.py")]
    run(monkeypatch, workspace, alerts, "--commit")
    before = len(tasks_of(workspace, "developer"))
    run(monkeypatch, workspace, alerts, "--commit")
    assert len(tasks_of(workspace, "developer")) == before
    assert "filed 0 code-scanning task(s)" in capsys.readouterr().out


def test_a_fix_task_without_a_known_file_goes_to_the_release_engineer(monkeypatch, workspace):
    assert run(monkeypatch, workspace, [alert(5, "")], "--commit") == 1
    assert len(tasks_of(workspace, "release-engineer")) == 1
    assert SCAN_OWNER_ROLE == "release-engineer"


def test_the_route_covers_every_shipped_tree() -> None:
    """The ownership map must not leave a shipped directory unowned."""
    patterns = " ".join(pattern for pattern, _role in SCAN_ROUTE)
    for tree in ("src/", "scripts/", "tests/", "docs/", ".github/", "roles/", "references/"):
        assert tree in patterns, tree
    assert set(SCAN_BLOCKING) >= {"error", "critical"}


def test_the_route_never_assigns_a_file_to_a_role_that_cannot_exist() -> None:
    from teamwork.config import ROLE_PARENT

    for pattern, role in SCAN_ROUTE:
        assert role in ROLE_PARENT, (pattern, role)


def test_json_payload_from_the_forge_is_parsed_into_alerts(monkeypatch, tmp_path):
    """The reading path itself: gh JSON -> alert dicts, with a provenance line."""
    raw = json.dumps([alert(7, "src/q.py")])
    calls = {}

    def fake_run(cmd, capture_output=True, text=True, timeout=0):
        calls["cmd"] = cmd

        class Done:
            returncode = 0
            stdout = raw
            stderr = ""

        return Done()

    monkeypatch.setattr(engine, "_scan_remote", lambda p: ("acme", "shop"))
    monkeypatch.setattr(engine.subprocess, "run", fake_run)
    alerts, provenance = engine._scan_alerts(tmp_path, 50, False)
    assert alerts[0]["number"] == 7
    assert "repos/acme/shop/code-scanning/alerts" in provenance
    assert "code-scanning" in calls["cmd"][2]
