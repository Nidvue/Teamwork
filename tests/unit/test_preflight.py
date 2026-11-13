"""`preflight` is the author's mechanical gate, and `selfcheck` refuses while it is red.

Measured from the ledger at one cut (n=1615): 44 review failures over 66 review
targets (one role + task), of which 26 needed more than one verdict and 11 needed
three or more; two independent readings put the locally-decidable share at 16-24
of 44, and they disagree. Every extra round cost a Reviewer lease (p50 12.2 / p90
25.8 min) and serialised the author, so the point of this command is that a defect
class a shell can decide reaches the author before a human reviewer sees it; the
`mechanical:` field on every fail keeps the share measured prospectively.

These tests are behavioural, one per class the command claims to remove:

* a branch behind the base or conflicting with it, and green after the rebase the
  command prints - the 11-in-43 class;
* evidence that names a revision the repository does not have - 4-in-43;
* a commit whose author is not the acting role mailbox - the identity gate;
* a branch that edits the generated board into a drift - 6-in-43, charged only
  when the branch itself carries the file;
* the feature-independence rule at the tree the branch would LAND (`features`):
  a lane's own `feature check` can be green while the merged tree is red, because
  the record it collides with may live on another branch;
* the project gate, which is reported UNVERIFIED unless the author asks for it;
* and the three integration points: `selfcheck` refuses a red preflight (with
  `--force <reason>` as the honest exception), the note it is about to store - its
  `--test` line included - is scanned before it is written, and the digest it
  records moves when a check flips and reproduces at its own revision.

And one thing the verdict path has to keep: a `review --result fail` records
whether the AUTHOR's preflight was green at the revision that failed
(`mechanical: no | unknown | n/a`), on the task and in the ledger, so the
mechanical-fail rate this command exists to cut can be re-counted afterwards.

The tree is built through the CLI (init, task add, branch start, commit) instead of
by hand, so a test fails when the commands stop agreeing with each other and not
only when `preflight` is wrong.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from teamwork import board as boardlib
from teamwork import engine
from teamwork.names import role_identity

AGENTS = ("ceo", "developer-1", "reviewer-1", "reviewer-2")
BOARD = "docs/Team/Board.md"
DIGEST = re.compile(r"PREFLIGHT digest: (PF-[0-9a-f]+) @([0-9a-f]+)")

BOARD_SKELETON = """# BOARD - live status

Owner: Project Manager.

## Snapshot

- Milestone: -

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| developer | T-0001 | - | doing | - | - |

Rows whose PR is not merged carry no merged revision.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| developer | T-0001 | P0 | doing | - |

The task queue (`teamwork.py task list <role>`) is authoritative.

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| | | | |
"""


def team_root(project: Path) -> Path:
    """The hidden team tree ``<project>/.pi/Teamwork/Teams/<Team>/``."""
    slug = engine.team_slug(project)
    return (project / engine.TEAM_ROOT_DIR / engine.TEAMS_SUBDIR / slug).resolve()


def git(project: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(project), *argv], capture_output=True, text=True, check=False
    )


def git_as(project: Path, role: str, *argv: str) -> subprocess.CompletedProcess:
    """Run git with a role mailbox identity, the way a lane applies it per command."""
    name, email = role_identity(role)
    return git(project, "-c", f"user.name={name}", "-c", f"user.email={email}", *argv)


def init_team(cli, project: Path) -> Path:
    assert cli("--project", project, "init", "--agents", ",".join(AGENTS)) == 0
    root = team_root(project)
    assert root.is_dir()
    return root


def lane_tree(project: Path, task: str = "T-0001") -> Path:
    """The worktree the task's author works in; `branch start` creates one by default."""
    root = team_root(project)
    for role in engine.list_roles(root):
        for item in engine.parse_tasks(engine.task_file(root, role)):
            if item["id"] == task and item.get("worktree"):
                return engine.task_worktree(root, item)
    raise AssertionError(f"no worktree recorded for {task}: {task} would share the checkout")


def tree_of(project: Path, task: str = "T-0001") -> Path:
    """The task's worktree, or the shared checkout when the task has no branch yet."""
    try:
        return lane_tree(project, task)
    except AssertionError:
        return project


@contextmanager
def in_tree(path: Path):
    """Act as the author acts: from inside its own worktree."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def start_branch(cli, project: Path, *, evidence: str = "") -> str:
    """Add + claim a developer task and start its branch on the initial base.

    Since M23 a branch start gives the task its own worktree and leaves the main
    checkout alone, so this asserts both: the branch exists and the shared checkout
    did not move. `commit_as_author`, `preflight` and `selfcheck` then run inside
    that tree, which is what the author does.
    """
    add = ["--project", project, "task", "add", "developer", "a clean deliverable"]
    add += ["--priority", "P0"]
    if evidence:
        add += ["--evidence", evidence]
    assert cli(*add) == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "branch", "start", "--agent", "developer-1", "--task", "T-0001")
        == 0
    )
    tree = lane_tree(project)
    assert tree.is_dir()
    assert git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "main"
    branch = git(tree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert branch.startswith("developer-1/t-0001")
    return branch


def commit_as_author(cli, project: Path, filename: str = "feat.txt") -> str:
    """One role commit in the task's own worktree; returns its sha."""
    tree = lane_tree(project)
    (tree / filename).write_text("done\n", encoding="utf-8")
    with in_tree(tree):
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "land a clean deliverable",
                "--deliverable",
                "one file and its test",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "pytest -q -> 1 passed",
                "--paths",
                filename,
            )
            == 0
        )
    return git(tree, "rev-parse", "HEAD").stdout.strip()


def advance_main(project: Path, filename: str, text: str) -> str:
    """A commit on main the branch does not have: the base has moved."""
    assert git(project, "checkout", "-q", "main").returncode == 0
    (project / filename).write_text(text, encoding="utf-8")
    assert git(project, "add", "-A").returncode == 0
    done = git_as(project, "ceo", "commit", "-q", "-m", "chore(plan): the base moves on")
    assert done.returncode == 0, done.stderr
    return git(project, "rev-parse", "HEAD").stdout.strip()


def preflight(cli, capsys, project: Path, *extra: str) -> tuple:
    """Run preflight from the task's worktree, return (exit code, stdout)."""
    capsys.readouterr()
    with in_tree(tree_of(project)):
        code = cli("--project", project, "preflight", "developer", "T-0001", *extra)
    return code, capsys.readouterr().out


def selfcheck(cli, project: Path, *extra: str) -> int:
    """The author's self-check on T-0001, run in-process from its worktree."""
    with in_tree(tree_of(project)):
        return cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            *extra,
        )


RECORDED_PREFLIGHT = re.compile(
    r"\s*\|\s*preflight: PF-[0-9a-f]+ @[0-9a-f]+ \(\d+ checks, \d+ failed\)"
)


def test_a_clean_single_commit_branch_is_green(cli, project, capsys):
    """One commit over the current base, role identity, reachable evidence: pass.

    The gate line is UNVERIFIED here and that is not a failure: the skill names no
    toolchain, so an unconfigured project gate must not read as a red preflight.
    """
    init_team(cli, project)
    start_branch(cli, project)
    sha = commit_as_author(cli, project)

    code, out = preflight(cli, capsys, project)

    assert code == 0, out
    assert f"PREFLIGHT pass @{sha[:12]} :: 8 checks, 0 failed" in out
    assert "1 commit over main" in out
    assert "UNVERIFIED: no PreflightCommand configured" in out
    assert "does not carry docs/Team/Board.md" in out
    assert DIGEST.search(out), out


def test_a_branch_behind_the_base_is_a_reminder_until_it_is_rebased(cli, project, capsys):
    """D-0017: a clean merge tree makes staleness a reminder, not a blocker.

    The report still names the count and prints the rebase that clears it, and
    running exactly that rebase must leave the same task green - otherwise the
    command reports a problem it does not actually decide. A conflicting merge
    tree or a red project gate keeps the failure (test_preflight_behind_branch).
    """
    init_team(cli, project)
    branch = start_branch(cli, project)
    commit_as_author(cli, project)
    advance_main(project, "main-only.txt", "main\n")

    code, out = preflight(cli, capsys, project)
    assert code == 0, out
    assert "1 commit(s) behind main" in out
    assert "rebase main" in out

    tree = lane_tree(project)
    assert git(tree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == branch
    rebased = git_as(tree, "developer", "rebase", "main")
    assert rebased.returncode == 0, rebased.stderr

    code, out = preflight(cli, capsys, project)
    assert code == 0, out
    assert "PREFLIGHT pass @" in out


def test_a_conflicting_branch_is_red_and_names_the_paths(cli, project, capsys):
    """A conflict is decided locally, so no Reviewer has to discover it in a merge."""
    init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project, "shared.txt")
    advance_main(project, "shared.txt", "the other side\n")

    code, out = preflight(cli, capsys, project)

    assert code == 1, out
    assert "CONFLICT in shared.txt" in out
    assert "mergeable" in out
    assert "git merge-tree --write-tree main developer-1/t-0001-a-clean-deliverable" in out


def test_evidence_naming_an_unknown_revision_is_red(cli, project, capsys):
    """4-in-43: a claim bound to a revision nobody can check out is not evidence."""
    init_team(cli, project)
    start_branch(cli, project, evidence="pytest -q @deadbeef -> 3 failed")
    commit_as_author(cli, project)

    code, out = preflight(cli, capsys, project)

    assert code == 1, out
    assert "@deadbeef" in out
    assert "not a commit in this repository" in out


def test_a_commit_by_the_wrong_identity_is_red(cli, project, capsys):
    """The identity gate runs the same audit CI runs, so the author sees it first."""
    init_team(cli, project)
    start_branch(cli, project)
    tree = lane_tree(project)
    (tree / "feat.txt").write_text("done\n", encoding="utf-8")
    assert git(tree, "add", "-A").returncode == 0
    wrong = git(
        tree,
        "-c",
        "user.name=Developer-1",
        "-c",
        "user.email=developer-1@agents.nidvue.com",
        "commit",
        "-q",
        "-m",
        "feat(engine): a commit with an instance-numbered identity",
        "-m",
        "Task: T-0001\n\nActing role: Developer-1",
    )
    assert wrong.returncode == 0, wrong.stderr

    code, out = preflight(cli, capsys, project)

    assert code == 1, out
    assert "not a role mailbox: developer-1@agents.nidvue.com" in out
    assert "teamwork.py commit --role developer" in out


def test_a_branch_that_edits_the_board_into_a_drift_is_red(cli, project, capsys):
    """6-in-43: the board is generated, so a hand-edited row is drift by definition.

    The board is only charged when the branch carries it - the sibling-drift case is
    covered by the green test, where the branch leaves it alone.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    rendered = boardlib.render(boardlib.queues(root), BOARD_SKELETON)
    drifted = rendered.replace(
        "| developer | T-0001 | - | doing |", "| developer | T-0001 | - | done |", 1
    )
    assert drifted != rendered, rendered
    tree = lane_tree(project)
    (tree / BOARD).write_text(drifted, encoding="utf-8")
    with in_tree(tree):
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "docs",
                "--goal",
                "record the milestone",
                "--deliverable",
                "a board render",
                "--why",
                "the board is the projection of the queues",
                "--status",
                "implemented",
                "--result",
                "teamwork.py board --check -> 1 stale cell",
                "--paths",
                BOARD,
            )
            == 0
        )

    code, out = preflight(cli, capsys, project)

    assert code == 1, out
    assert "disagrees with the queues" in out
    assert "developer T-0001" in out
    assert "teamwork.py board --write" in out


def test_a_task_with_no_branch_is_a_warning_so_the_shipped_flow_still_runs(cli, project, capsys):
    """A task may carry no code, so a missing branch must not block the self-check.

    A verdict, a records pass or a research note has no diff, and the review flow in
    this repository records a verdict on such a task. Failing here would refuse that
    flow and teach every lane to `--force` on its first day, so the missing branch is
    reported with its fix and the other revision checks say `not measured`.
    """
    init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "a verdict only") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )

    code, out = preflight(cli, capsys, project)

    assert code == 0, out
    assert "warn" in out
    assert "names no branch" in out
    assert "PREFLIGHT pass @- :: 8 checks, 0 failed" in out
    assert "teamwork.py branch start --agent developer" in out
    assert (
        cli(
            "--project",
            project,
            "selfcheck",
            "developer",
            "T-0001",
            "--by",
            "developer-1",
            "--note",
            "re-read the verdict",
            "--test",
            "links -> 0 issues",
        )
        == 0
    )


def portable_failing_gate() -> str:
    """A `PreflightCommand` that exits 1 on every host, quoted as `shlex` reads it.

    `sh -c false` is the POSIX spelling of "a gate that fails"; a win32 host ships
    no `sh`, so the portable spelling is this interpreter refusing on purpose. The
    quotes matter: `shlex.split` keeps a backslash inside them, so a Windows
    interpreter path survives (T-0003).
    """
    return f'"{sys.executable}" -c "raise SystemExit(1)"'


def test_the_project_gate_is_unverified_until_run_asks_for_it(cli, project, capsys):
    """The skill names no toolchain: the command is the project's, and it is opt-in.

    Without `--run` a configured gate is not executed (the report says so), and with
    it a failing command is a real failure carrying its own exit status - the 5-in-43
    red-gate class, decided before the Reviewer is asked.

    The command is written portably on purpose: this test asserts the same contract
    on a POSIX and on a win32 host (T-0003), so the exact POSIX spelling
    (`sh -c false`) lives in the two tests below - one that runs it where the host
    has a `sh`, and one that pins what an unlaunchable gate must report.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    gate = portable_failing_gate()
    settings = root / engine.F_SETTINGS
    settings.write_text(json.dumps({"PreflightCommand": gate}) + "\n", encoding="utf-8")

    code, out = preflight(cli, capsys, project)
    assert code == 0, out
    assert f"UNVERIFIED: PreflightCommand not run (pass --run): {gate}" in out

    code, out = preflight(cli, capsys, project, "--run")
    assert code == 1, out
    assert f"{gate} -> exit 1" in out
    assert "(gate)" in out


def test_the_posix_false_gate_reports_its_exit_where_the_host_has_a_sh(cli, project, capsys):
    """The original red-gate command, kept everywhere it can actually run.

    The engine contract is host-independent - a gate that exits non-zero is red and
    the report names its exit status - but `sh -c false` is not: a win32 host ships
    no `sh`, so there is no exit status to read and demanding one would assert a
    shell this host does not have. That host is covered by the next test instead,
    which pins what an unlaunchable gate must report; here the host is asked
    whether it can run the exact command before the command is used (T-0003).
    """
    if shutil.which("sh") is None:
        pytest.skip(
            "this host has no `sh` on PATH, so `sh -c false` has no exit status to "
            "assert here; the portable failing gate above carries the exit-status "
            "contract and the unlaunchable gate below carries this host's case"
        )
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    settings = root / engine.F_SETTINGS
    settings.write_text('{"PreflightCommand": "sh -c false"}\n', encoding="utf-8")

    code, out = preflight(cli, capsys, project, "--run")

    assert code == 1, out
    assert "sh -c false -> exit 1" in out
    assert "(gate)" in out


def test_a_compound_gate_reaches_the_host_shell(cli, project, capsys):
    """`a && b` is the spelling the docs invite, so `&&` must reach a shell (T-0005).

    `shlex` alone hands `&&` to the first program as an argument, so the gate ran
    only `a`: a green `a` masked a red `b` and a configured gate reported PASS for
    a command that fails - the same exit-2-on-a-typo class the author reads as a
    broken gate. Both sides are pinned here: a red second command is a red gate and
    a green compound is still OK, so the shell is not bought with a false red.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    settings = root / engine.F_SETTINGS
    green = f'"{sys.executable}" -c "print(1)"'
    red = f'"{sys.executable}" -c "raise SystemExit(1)"'

    settings.write_text(
        json.dumps({"PreflightCommand": f"{green} && {red}"}) + "\n", encoding="utf-8"
    )
    code, out = preflight(cli, capsys, project, "--run")
    assert code == 1, out
    assert f"{green} && {red} -> exit 1" in out
    assert "(gate)" in out

    settings.write_text(
        json.dumps({"PreflightCommand": f"{green} && {green}"}) + "\n", encoding="utf-8"
    )
    code, out = preflight(cli, capsys, project, "--run")
    assert code == 0, out
    assert f"{green} && {green} -> exit 0" in out


def test_a_single_command_keeps_the_no_shell_argv():
    """Only a compound command takes the shell; a plain one stays `shlex` argv.

    The unlaunchable-gate contract (a missing program reports "could not start",
    not a shell's exit 127) rests on this split, and an unquotable single command
    still reports itself as unquotable rather than being handed to the shell. On
    Windows a compound line is one string for `shell=True`, because a list is
    re-quoted and `cmd.exe` then reads those quotes literally (T-0094).
    """
    assert engine._gate_argv("make check") == ["make", "check"]
    assert engine._gate_argv('"a b/py" -c "print(1)"')[0] == "a b/py"
    assert engine._gate_argv('"a b/py" -m ruff check .')[0] == "a b/py"
    compound = engine._gate_argv("a && b")
    if os.name == "nt":
        assert compound == "a && b"
    else:
        assert compound == ["/bin/sh", "-c", "a && b"]
    with pytest.raises(ValueError):
        engine._gate_argv('make "check')


def test_an_unlaunchable_gate_command_is_red_with_its_reason(cli, project, capsys):
    """An unlaunchable gate must never escape the engine and never pass silently.

    The defect this pins (T-0003): a POSIX-only `PreflightCommand` on win32 either
    raised out of `preflight` or reported nothing the author could act on, so the
    gate was lost exactly where it was needed. The contract is host-independent -
    exit 1, a `(gate)` failure, and a detail naming the command AND why it could
    not start - and the program is one no host ships, so the assertion is the same
    everywhere.
    """
    missing = "teamwork-preflight-no-such-program-9c1f"
    assert shutil.which(missing) is None, f"this host unexpectedly ships {missing!r}"
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    gate = f"{missing} --check"
    settings = root / engine.F_SETTINGS
    settings.write_text(json.dumps({"PreflightCommand": gate}) + "\n", encoding="utf-8")

    code, out = preflight(cli, capsys, project, "--run")

    assert code == 1, out
    assert "(gate)" in out
    assert f"{gate} -> could not start" in out
    assert "install it, or point PreflightCommand at a command this host has" in out


def test_a_hanging_gate_is_red_with_its_budget_named(cli, project, capsys, monkeypatch):
    """A gate that never exits is a failure, not a stall and not an exception.

    The reviewer's F1 on T-0003: the timeout branch of `_preflight_gate` shipped
    with no test, so deleting it left every check green. This pins the whole
    branch - status `fail`, the exact `no exit` line naming the budget, the advice
    that a hang is not a pass - and calls the check directly so a raise out of the
    engine fails here rather than escaping as a traceback. The budget is patched
    to one second, so the case is proved in about two rather than in an hour.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    gate = f'"{sys.executable}" -c "import time; time.sleep(30)"'
    settings = root / engine.F_SETTINGS
    settings.write_text(json.dumps({"PreflightCommand": gate}) + "\n", encoding="utf-8")
    monkeypatch.setattr(engine, "PREFLIGHT_GATE_TIMEOUT", 1)

    check = engine._preflight_gate(root, project, run=True)

    assert check.status == engine.PREFLIGHT_FAIL, check.detail
    assert check.detail == f"{gate} -> no exit in the project checkout: still running after 1s", (
        check.detail
    )
    assert "a gate that hangs is not a pass" in check.fix, check.fix

    code, out = preflight(cli, capsys, project, "--run")

    assert code == 1, out
    assert re.search(r"^- fail\s+gate\s+", out, re.MULTILINE), out
    assert f"{gate} -> no exit in the project checkout: still running after 1s" in out
    assert "(gate)" in out


def test_selfcheck_refuses_a_red_preflight_and_records_a_forced_exception(cli, project, capsys):
    """An author cannot submit work the mechanical half already rejects.

    `--force <reason>` is the honest exception, and it must be visible where an
    auditor looks: the task's `forced` field, naming the preflight that was
    overridden rather than a bare reason.
    """
    root = init_team(cli, project)
    start_branch(cli, project, evidence="pytest -q @deadbeef -> 3 failed")
    commit_as_author(cli, project)
    assert (
        cli("--project", project, "task", "set", "developer", "T-0001", "--status", "selfcheck")
        == 0
    )
    base = ["--project", project, "selfcheck", "developer", "T-0001", "--by", "developer-1"]
    note = ["--note", "re-read the diff and the queue", "--test", "pytest -q -> 1 passed"]

    capsys.readouterr()
    with in_tree(tree_of(project)):
        assert cli(*base, *note) == 2
    refused = capsys.readouterr().err
    assert "preflight is red" in refused
    assert "evidence: the task evidence names @deadbeef" in refused
    queue = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert "self_check: pending" in queue

    with in_tree(tree_of(project)):
        assert cli(*base, *note, "--force", "the sha is a doc link, tracked as T-0009") == 0
    queue = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert "self_check: passed" in queue
    assert "preflight red (" in queue and "the sha is a doc link, tracked as T-0009" in queue
    assert re.search(r"preflight: PF-[0-9a-f]+ @[0-9a-f]+ \(8 checks, 1 failed\)", queue)


def test_the_digest_is_stable_and_moves_when_a_check_flips(cli, project, capsys):
    """The digest is what the Reviewer trusts, so it must identify the measurement.

    Same tree, same verdict -> the same digest; one check flipped -> a different
    one. A digest that survives a change would let a stale preflight ride a fixed
    branch into the self-check evidence.
    """
    init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)

    _, first = preflight(cli, capsys, project)
    _, again = preflight(cli, capsys, project)
    before = DIGEST.search(first)
    assert before and DIGEST.search(again)
    assert before.group(1) == DIGEST.search(again).group(1)

    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer",
            "T-0001",
            "--evidence",
            "pytest -q @deadbeef -> 3 failed",
        )
        == 0
    )
    code, after = preflight(cli, capsys, project)
    assert code == 1
    flipped = DIGEST.search(after)
    assert flipped and flipped.group(1) != before.group(1)


def test_a_selfcheck_test_line_naming_an_unknown_revision_is_refused(cli, project, capsys):
    """The `--test` text is evidence, so the gate has to read it before it is stored.

    The stored `self_note` is written after `preflight` runs, so scanning only what
    was already stored let `--test "pytest -q @deadbeef -> 1 passed"` through with a
    green digest - a self-check certifying a revision this repository does not have,
    which is the four-in-43 class this command exists to remove.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)

    capsys.readouterr()
    code = selfcheck(
        cli,
        project,
        "--note",
        "re-read the diff",
        "--test",
        "pytest -q @deadbeef -> 1 passed",
    )
    refused = capsys.readouterr().err

    assert code == 2, refused
    assert "preflight is red" in refused
    assert "@deadbeef" in refused
    assert "not a commit in this repository" in refused
    queue = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    assert "self_check: pending" in queue
    assert "preflight: PF-" not in queue


def test_a_green_selfcheck_digest_reproduces_at_its_own_revision(cli, project, capsys):
    """The digest a passing self-check records must be reproducible by `preflight`.

    Scanning the `--test` text is what makes that true: a digest recorded green can
    only mean every revision the note names was checked, including the one the test
    ran against. A `preflight` at the same revision therefore prints the same digest
    - if it did not, the Reviewer would be citing a measurement nobody can repeat.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    sha = commit_as_author(cli, project)

    capsys.readouterr()
    code = selfcheck(
        cli,
        project,
        "--note",
        "re-read the diff against the brief",
        "--test",
        f"pytest -q @{sha[:12]} -> 1 passed",
    )
    out = capsys.readouterr().out
    assert code == 0, out

    queue = (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")
    recorded = re.search(r"preflight: (PF-[0-9a-f]+) @([0-9a-f]+) ", queue)
    assert recorded, queue
    assert recorded.group(2) == sha[:12]
    assert "(8 checks, 0 failed)" in queue

    code, live = preflight(cli, capsys, project)
    assert code == 0, live
    measured = DIGEST.search(live)
    assert measured and measured.group(1) == recorded.group(1)


def review_fail(cli, project: Path, handle: str = "T-0001") -> int:
    """A Reviewer fails the deliverable, in-process."""
    return cli(
        "--project",
        project,
        "review",
        "developer",
        handle,
        "--by",
        "reviewer-1",
        "--result",
        "fail",
        "--findings",
        "the guide still describes the old flag",
        "--detects",
        "a reader who copies the documented flag gets 'unrecognized arguments'",
    )


def queue_text(root: Path) -> str:
    return (root / "Roles" / "Developer" / "TaskQueue.md").read_text(encoding="utf-8")


def last_fail_detail(root: Path) -> str:
    """The detail of the newest `review.fail` ledger record."""
    records = [r for r in engine.ledger_read(root) if r.get("action") == "review.fail"]
    assert records, "no review.fail record was appended"
    return records[-1].get("detail") or ""


def test_a_fail_after_a_green_preflight_is_recorded_as_judgement(cli, project, capsys):
    """`mechanical: no` - the author ran the gate at this revision, so this is judgement.

    At one ledger cut (n=1615) there were 44 review failures over 66 targets, and
    the locally-decidable share is contested at 16-24 of 44. The verdict path keeps
    it measurable prospectively: a green preflight digest for the SAME revision
    means the finding is about the work, not about a miss a shell could have caught.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    sha = commit_as_author(cli, project)
    assert (
        selfcheck(
            cli,
            project,
            "--note",
            "re-read the diff",
            "--test",
            f"pytest -q @{sha[:12]} -> 1 passed",
        )
        == 0
    )

    capsys.readouterr()
    assert review_fail(cli, project) == 0
    out = capsys.readouterr().out

    assert "mechanical: no" in out
    queue = queue_text(root)
    assert "review_mechanical: no" in queue
    assert "review_fail_rev: " in queue
    assert last_fail_detail(root).startswith("mechanical: no | ")


def test_the_recorded_value_flips_when_the_preflight_line_leaves_the_evidence(cli, project, capsys):
    """`unknown` - the same fail, same revision, once the green preflight is gone.

    This is the difference the classification exists to draw: with the preflight
    line the finding is judgement, without it the author skipped the gate and the
    finding may well be mechanical. Removing only that fragment must flip the value,
    so nothing else in the note can be doing the work.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    sha = commit_as_author(cli, project)
    assert (
        selfcheck(
            cli,
            project,
            "--note",
            "re-read the diff",
            "--test",
            f"pytest -q @{sha[:12]} -> 1 passed",
        )
        == 0
    )
    queue = queue_text(root)
    assert re.search(r"preflight: PF-[0-9a-f]+ @[0-9a-f]+ \(8 checks, 0 failed\)", queue)

    assert review_fail(cli, project) == 0
    assert "review_mechanical: no" in queue_text(root)

    path = root / "Roles" / "Developer" / "TaskQueue.md"
    stripped, count = RECORDED_PREFLIGHT.subn("", path.read_text(encoding="utf-8"))
    assert count == 1, stripped
    path.write_text(stripped, encoding="utf-8")

    capsys.readouterr()
    assert review_fail(cli, project) == 0
    out = capsys.readouterr().out

    assert "mechanical: unknown" in out
    assert "no green preflight is recorded" in out
    assert "review_mechanical: unknown" in queue_text(root)
    assert last_fail_detail(root).startswith("mechanical: unknown | ")


def test_a_fail_on_a_task_with_no_revision_is_recorded_as_not_applicable(cli, project, capsys):
    """`n/a` - a verdict or a records pass has no branch, so it has nothing to gate.

    Reporting it as `unknown` would count a records task among the authors who
    skipped the gate, which is the kind of mis-measurement this flag removes.
    """
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "a verdict only") == 0

    capsys.readouterr()
    assert review_fail(cli, project) == 0
    out = capsys.readouterr().out

    assert "mechanical: n/a" in out
    assert "nothing to preflight" in out
    assert "review_mechanical: n/a" in queue_text(root)
    assert last_fail_detail(root).startswith("mechanical: n/a | ")


def test_the_slice_warning_uses_the_profiles_file_budget(tmp_path: Path) -> None:
    """A diff past the profile's slice warns; the same diff under it is silent."""
    repo = tmp_path / "slice-repo"
    repo.mkdir()
    assert git(repo, "init", "-q").returncode == 0
    assert git(repo, "config", "user.name", "Developer").returncode == 0
    assert git(repo, "config", "user.email", "developer@agents.nidvue.com").returncode == 0
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", "base").returncode == 0
    base = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert git(repo, "checkout", "-q", "-b", "slice").returncode == 0
    for index in range(7):
        (repo / f"file-{index}.txt").write_text("one line\n", encoding="utf-8")
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", "seven files").returncode == 0

    fast = engine._preflight_slice(
        repo, base, "slice", tmp_path, "developer", {"review_profile": "fast"}
    )
    assert fast is not None
    assert fast.status == engine.PREFLIGHT_WARN
    assert "7 files / 7 changed lines vs fast budget" in fast.detail
    assert "split the task or record why it cannot be split" in fast.detail

    standard = engine._preflight_slice(
        repo, base, "slice", tmp_path, "developer", {"review_profile": "standard"}
    )
    assert standard is None


def test_a_slice_over_the_profile_warns_but_does_not_fail_preflight(cli, project, capsys) -> None:
    """13 files is past the standard 12-file slice: warn, exit 0, other checks intact."""
    init_team(cli, project)
    start_branch(cli, project)
    tree = lane_tree(project)
    names = [f"slice-{index}.txt" for index in range(13)]
    for name in names:
        (tree / name).write_text("one line\n", encoding="utf-8")
    with in_tree(tree):
        assert (
            cli(
                "--project",
                project,
                "commit",
                "--role",
                "developer",
                "--task",
                "T-0001",
                "--type",
                "feat",
                "--goal",
                "land a slice",
                "--deliverable",
                "thirteen files",
                "--why",
                "the task asks for it",
                "--status",
                "implemented",
                "--result",
                "pytest -q -> 1 passed",
                "--all",
            )
            == 0
        )

    code, out = preflight(cli, capsys, project)

    assert code == 0, out
    assert re.search(r"- warn\s+slice\s+13 files / 13 changed lines vs standard budget", out), out
    assert "PREFLIGHT pass" in out
    assert "9 checks, 0 failed" in out


def test_evidence_naming_a_rebased_away_commit_is_red(cli, project, capsys):
    """Existing is not reachable: a rebase leaves the object, no ref contains it."""
    init_team(cli, project)
    start_branch(cli, project)
    first = commit_as_author(cli, project, "gone.txt")
    assert git(lane_tree(project), "reset", "--hard", "HEAD~1").returncode == 0
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer-1",
            "T-0001",
            "--evidence",
            f"pytest -q @{first[:7]} -> 3 passed",
        )
        == 0
    )
    commit_as_author(cli, project, "feat.txt")

    code, out = preflight(cli, capsys, project)

    assert code == 1, out
    assert "no ref contains" in out, out


def test_the_tool_digest_survives_a_rewrite(cli, project, capsys):
    """selfcheck's own digest names the measured revision; a rewrite must not block it.

    `preflight` appends `| preflight: PF-... @<rev>` to the note, and a rebase or
    amend rewrites that revision. The tool's own record cannot be the reason its
    next run is refused, or a rebase leaves the lane with no way out but --force.
    """
    root = init_team(cli, project)
    start_branch(cli, project)
    commit_as_author(cli, project)
    tree = lane_tree(project)
    sha = git(tree, "rev-parse", "--short", "HEAD").stdout.strip()
    assert (
        selfcheck(
            cli, project, "--note", "re-read the diff", "--test", f"pytest -q @{sha} -> 3 passed"
        )
        == 0
    )

    queue = engine.role_dir(root, "developer") / "TaskQueue.md"
    assert "preflight: PF-" in queue.read_text(encoding="utf-8")

    (tree / "extra.txt").write_text("more\n", encoding="utf-8")
    assert git(tree, "add", "extra.txt").returncode == 0
    assert git_as(tree, "developer", "commit", "--amend", "--no-edit").returncode == 0
    new_sha = git(tree, "rev-parse", "--short", "HEAD").stdout.strip()
    assert (
        cli(
            "--project",
            project,
            "task",
            "set",
            "developer-1",
            "T-0001",
            "--evidence",
            f"commit {new_sha}",
        )
        == 0
    )
    code, out = preflight(cli, capsys, project)
    assert code == 1, out
    assert "stored self-check" in out and "refresh the note" in out

    capsys.readouterr()
    assert (
        selfcheck(
            cli, project, "--note", "re-read again", "--test", f"pytest -q @{new_sha} -> 3 passed"
        )
        == 0
    )


def test_a_recorded_digest_is_not_a_claim() -> None:
    """The digest `selfcheck` writes is the tool's record, not the author's claim."""
    task = {
        "evidence": "",
        "self_note": "re-read | preflight: PF-abc123 @deadbeef (7 checks, 0 failed)",
    }
    check = engine._preflight_evidence(Path("/nonexistent"), task)
    assert check.status == engine.PREFLIGHT_OK


def test_the_gate_runs_in_the_lane_worktree_and_names_its_tree(cli, project, capsys):
    """The gate measures the tree that holds the branch, not the invoking checkout.

    A lane that runs `preflight --run` from the main checkout while its work lives
    in `Runtime/Worktrees/<Instance>/<T-id>` measured the wrong tree, so a syntax
    error in the lane passed its own gate (T-0058). `gate.py` exists only in the
    worktree: run from the checkout the interpreter cannot open it (exit 2), run
    from the worktree it exits 0, so the reported exit status proves the cwd.
    """
    root = init_team(cli, project)
    assert cli("--project", project, "task", "add", "developer", "a lane deliverable") == 0
    assert cli("--project", project, "task", "next", "developer-1") == 0
    started = cli(
        "--project",
        project,
        "branch",
        "start",
        "--agent",
        "developer-1",
        "--task",
        "T-0001",
        "--worktree",
    )
    assert started == 0
    worktree = engine.lane_worktree(root, "developer-1", "T-0001")
    assert worktree.is_dir()
    (worktree / "gate.py").write_text("", encoding="utf-8")
    assert not (project / "gate.py").exists()
    gate = f'"{sys.executable}" gate.py'
    settings = root / engine.F_SETTINGS
    settings.write_text(json.dumps({"PreflightCommand": gate}) + "\n", encoding="utf-8")

    _code, out = preflight(cli, capsys, project, "--run")
    assert "-> exit 0 in " in out, out
    assert f"the task's own worktree: {worktree}" in out, out


def test_a_recorded_worktree_that_is_gone_is_not_a_tree_to_run_in(project):
    """The gate falls back to the checkout, never to a path this host does not have."""
    assert engine._gate_tree(project, project, {}) == project
    assert engine._gate_tree(project, project, {"worktree": ""}) == project
    assert engine._gate_tree(project, project, {"worktree": str(project / "gone")}) == project
    assert engine._gate_tree(project, project, {"worktree": str(project)}) == project


def test_a_recorded_worktree_resolves_from_a_foreign_cwd(project, tmp_path, monkeypatch):
    """A stored worktree path is not read against whatever cwd the lane happened to have."""
    root = project / ".pi" / "Teamwork" / "Teams" / "SampleProject"
    tree = root / "Runtime" / "Worktrees" / "developer-1" / "T-0001"
    tree.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    stored = "Runtime/Worktrees/developer-1/T-0001"
    assert engine._gate_tree(root, project, {"worktree": stored}) == tree
    assert engine._gate_tree(root, project, {"worktree": str(tree)}) == tree
    assert engine._gate_tree(root, project, {"worktree": "Runtime/gone/T-0001"}) == project


def test_a_self_check_that_measured_an_older_revision_is_refused(cli, project, capsys):
    """Evidence is bound to the revision it names, and that must be the branch head.

    Measured review class (30 of 158 fails): the self-check suite line does not
    reproduce at the revision it names, because the tree moved after the run. The
    gate now compares the note's revisions with the branch head, so the author
    re-runs instead of the Reviewer discovering it.
    """
    init_team(cli, project)
    start_branch(cli, project)
    first = commit_as_author(cli, project, "first.txt")
    tree = lane_tree(project)
    (tree / "second.txt").write_text("done\n", encoding="utf-8")
    second = commit_as_author(cli, project, "second.txt")
    assert first != second

    code = selfcheck(
        cli,
        project,
        "--note",
        "re-read the diff",
        "--test",
        f"pytest -q @{first[:7]} -> 3 passed",
    )

    assert code == 2, "a self-check bound to an older revision must be refused"
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "tree moved after the run" in out, out
    assert f"@{second[:7]}" in out, out

    code = selfcheck(
        cli,
        project,
        "--note",
        "re-read the diff",
        "--test",
        f"pytest -q @{second[:7]} -> 3 passed",
    )
    assert code == 0
