"""The swarm file-ownership rule: a lane touches only the files it declared.

Two lanes editing one file is the collision that costs a merge. The cheapest place
to stop it is the author's own gate, so a task declares the paths it owns and
`preflight` warns when the branch touches any other. The rule is borrowed from
Google Antigravity's `/swarm` mode, whose first iron law is to slice write
permission physically in the initial brief.

These tests are behavioural: they build a real git repo, commit a diff, and read
the `files` check `_preflight_files` returns. A warning never fails the gate - a
genuine cross-file fix names the extra path in the self-check note and the Reviewer
judges it - so the tests assert the warning and the clean case, not an exit code.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from teamwork import engine, records


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True, text=True, check=False
    )


def build_repo(tmp_path: Path, paths: list) -> tuple:
    """A one-commit repo plus a branch that touches exactly `paths`."""
    repo = tmp_path / "ownership-repo"
    repo.mkdir()
    assert git(repo, "init", "-q").returncode == 0
    assert git(repo, "config", "user.name", "Developer").returncode == 0
    assert git(repo, "config", "user.email", "developer@agents.nidvue.com").returncode == 0
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", "base").returncode == 0
    base = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert git(repo, "checkout", "-q", "-b", "owned").returncode == 0
    for path in paths:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("one line\n", encoding="utf-8")
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", "touch the declared paths").returncode == 0
    return repo, base


def test_a_new_task_carries_the_files_it_owns_and_the_parser_round_trips_them(
    tmp_path: Path,
) -> None:
    task = records.new_task("owned slice", files="src/teamwork/engine.py,docs/Team/Plan.md")
    assert task["files"] == "src/teamwork/engine.py,docs/Team/Plan.md"

    queue = tmp_path / "TaskQueue.md"
    records.write_tasks(queue, [task], "developer")
    parsed = records.parse_tasks(queue)
    assert parsed[0]["files"] == "src/teamwork/engine.py,docs/Team/Plan.md"


def test_owned_by_matches_an_exact_file_a_directory_prefix_and_a_glob() -> None:
    declared = ["src/teamwork/engine.py", "docs/Team/", "tests/unit/test_*.py"]
    assert engine._owned_by("src/teamwork/engine.py", declared)
    assert engine._owned_by("docs/Team/Plan.md", declared)
    assert engine._owned_by("tests/unit/test_file_ownership.py", declared)
    assert not engine._owned_by("src/teamwork/records.py", declared)
    assert not engine._owned_by("docs/guide/cli.md", declared)


def test_a_diff_inside_the_declared_ownership_is_ok(tmp_path: Path) -> None:
    repo, base = build_repo(tmp_path, ["src/teamwork/engine.py", "tests/unit/test_owned.py"])
    check = engine._preflight_files(
        repo,
        base,
        "owned",
        {"files": "src/teamwork/engine.py,tests/unit/test_owned.py"},
    )
    assert check is not None
    assert check.status == engine.PREFLIGHT_OK
    assert "all within the 2 declared" in check.detail


def test_a_diff_outside_the_declared_ownership_warns_with_the_path(tmp_path: Path) -> None:
    repo, base = build_repo(tmp_path, ["src/teamwork/engine.py", "src/teamwork/records.py"])
    check = engine._preflight_files(repo, base, "owned", {"files": "src/teamwork/engine.py"})
    assert check is not None
    assert check.status == engine.PREFLIGHT_WARN
    assert "1 path(s) outside the declared ownership: src/teamwork/records.py" in check.detail
    assert "declare the extra path" in check.fix


def test_an_undeclared_task_is_not_forced_into_a_budget(tmp_path: Path) -> None:
    repo, base = build_repo(tmp_path, ["anything.py"])
    assert engine._preflight_files(repo, base, "owned", {"files": ""}) is None
    assert engine._preflight_files(repo, base, "owned", {}) is None


def test_the_lane_packet_prints_the_files_the_task_owns(cli, project: Path) -> None:
    """The brief carries the slice of write permission the article puts first."""
    from teamwork import lanes

    assert cli("--project", project, "init", "--agents", "ceo", "--no-git") == 0
    root = (
        project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()
    assert (
        cli(
            "--project",
            project,
            "task",
            "add",
            "ceo",
            "owned work",
            "--files",
            "src/teamwork/engine.py,docs/Team/Plan.md",
        )
        == 0
    )
    tasks = engine.parse_tasks(engine.task_file(root, "ceo"))
    assert tasks[0]["files"] == "src/teamwork/engine.py,docs/Team/Plan.md"
    packet = lanes.build_packet(
        root,
        [lanes.Assignment("CEO", "ceo", tasks[0]["id"], tasks[0]["title"])],
        "L-0001",
        1,
        1,
        50,
        40,
        "pi",
        "",
        "default",
    )
    assert "## Files you own (do not touch any other)" in packet
    assert "- src/teamwork/engine.py" in packet
    assert "- docs/Team/Plan.md" in packet
    assert "Two lanes editing one file is the collision" in packet
