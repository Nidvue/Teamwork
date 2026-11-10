"""Integration: the section 14 loop through the real CLI on a throwaway team.

Layer ``integration``, area ``skills``, owner Tester (T-0004). Each case drives
the commands a lane actually runs - ``lesson add``, ``load``, ``lesson fix``,
``skill create``, ``skill list``, ``skill candidates`` - against a ``--no-git``
workspace, and asserts what the operator sees: the exit code, the exact line,
and the record the command left on disk (``docs/Team/Architecture.md`` 14.1-14.4,
AC-M17-3/AC-M17-4).

The pytest cases drive the in-process engine (fast, one process); the
concurrency case spawns the shipped ``scripts/teamwork.py`` so it measures the
process boundary the unit lock test cannot: the unit test starts ``engine.main``
in a child, this one executes the file a lane executes.

Owner: tester. Layer: integration. Area: skills.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from tests.gitenv import child_env

from teamwork import config, engine, io

AGENTS = "ceo,developer-1,tester-1,reviewer-1"

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"

ALREADY_FIXED = "lesson L-0001 is already fixed by no skill; pass --evidence to re-prove the fix"
PREFIX_REFUSAL = (
    "skill name 'foo' must start with tw-: every team skill is recognisable by the "
    "fixed prefix (e.g. tw-<name>)"
)
MISTAKE_NEEDS_LESSON = (
    "--kind mistake requires --from-lesson L-nnnn: a mistake skill names the lesson it fixes"
)

MEASURED_STARVED_LOCK_WAIT_SECONDS = 60

CONCURRENT_LOCK_WAIT_SECONDS = 360


def team_root(project: Path) -> Path:
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def init_workspace(cli, project: Path) -> Path:
    """A no-git team: the skill branch guard has no main to refuse on."""
    code = cli("--project", project, "init", "--agents", AGENTS, "--no-git")
    assert code == 0, f"init returned {code}"
    root = team_root(project)
    assert root.is_dir()
    return root


def lessons_file(project: Path, role: str) -> Path:
    return engine.role_dir(team_root(project), role) / config.F_LESSONS


def registry(project: Path) -> Path:
    return team_root(project) / config.F_SKILLS


def skill_md(project: Path, name: str) -> Path:
    return project / ".agents" / "skills" / name / "SKILL.md"


def add_lesson(
    cli,
    project: Path,
    *,
    by: str,
    role: str,
    mistake: str,
    cause: str = "the guard was skipped",
    rule: str = "run the guard first",
    evidence: str = "pytest @abc -> 1 passed",
) -> int:
    return cli(
        "--project",
        project,
        "lesson",
        "add",
        "--by",
        by,
        "--role",
        role,
        "--mistake",
        mistake,
        "--cause",
        cause,
        "--rule",
        rule,
        "--evidence",
        evidence,
    )


def ledger_records(root: Path) -> list:
    path = root / config.F_LEDGER
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_two_role_lessons_load_list_show_and_fix(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    capsys.readouterr()

    assert (
        add_lesson(cli, project, by="Developer-1", role="developer", mistake="committed on main")
        == 0
    )
    printed = capsys.readouterr().out
    assert "# L-0001 recorded for developer: committed on main" in printed
    assert f"#   file: {lessons_file(project, 'developer')}" in printed

    assert (
        add_lesson(cli, project, by="Tester-1", role="tester", mistake="certified without CI") == 0
    )
    printed = capsys.readouterr().out
    assert "# L-0002 recorded for tester: certified without CI" in printed
    assert f"#   file: {lessons_file(project, 'tester')}" in printed

    developer = engine.parse_lessons(lessons_file(project, "developer"))
    tester = engine.parse_lessons(lessons_file(project, "tester"))
    assert [(item["id"], item["role"], item["status"]) for item in developer] == [
        ("L-0001", "developer", "open")
    ]
    assert [(item["id"], item["role"], item["status"]) for item in tester] == [
        ("L-0002", "tester", "open")
    ]

    assert cli("--project", project, "load", "Developer-1") == 0
    loaded = capsys.readouterr().out
    assert "# Lessons (developer) - open mistakes to avoid:" in loaded
    assert "- committed on main -> Roles/Developer/Lessons.md#L-0001" in loaded
    assert "certified without CI" not in loaded
    assert "# fixed: 0; full list: teamwork.py lesson list --role developer" in loaded

    assert cli("--project", project, "lesson", "list") == 0
    listed = capsys.readouterr().out
    assert (
        "- L-0001 [open] developer: committed on main -> run the guard first "
        "(skill: no skill)" in listed
    )
    assert (
        "- L-0002 [open] tester: certified without CI -> run the guard first "
        "(skill: no skill)" in listed
    )

    assert cli("--project", project, "lesson", "show", "L-0002") == 0
    shown = capsys.readouterr().out
    assert shown.startswith("# L-0002 - certified without CI")
    for field in engine.LESSON_FIELDS:
        assert f"- {field}:" in shown, f"lesson show dropped {field}"
    assert "- role: tester" in shown
    assert "- evidence: pytest @abc -> 1 passed" in shown

    assert (
        cli(
            "--project",
            project,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @def -> 2 passed",
        )
        == 0
    )
    fixed = capsys.readouterr().out
    assert "# L-0001 - committed on main" in fixed
    assert "- status: fixed" in fixed
    assert "- evidence: pytest @def -> 2 passed" in fixed

    assert cli("--project", project, "lesson", "fix", "L-0001", "--by", "Developer-1") == 1
    refusal = capsys.readouterr().err
    assert refusal.startswith("teamwork: ")
    assert refusal[len("teamwork: ") :].strip() == ALREADY_FIXED
    still = engine.parse_lessons(lessons_file(project, "developer"))[0]
    assert still["status"] == "fixed"
    assert still["evidence"] == "pytest @def -> 2 passed"

    assert (
        cli(
            "--project",
            project,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @ghi -> 3 passed",
        )
        == 0
    )
    assert "- evidence: pytest @ghi -> 3 passed" in capsys.readouterr().out
    assert engine.parse_lessons(lessons_file(project, "developer"))[0]["evidence"] == (
        "pytest @ghi -> 3 passed"
    )


def test_skill_from_lesson_links_both_ways_and_the_late_skill_order(
    cli, project: Path, capsys
) -> None:
    init_workspace(cli, project)
    assert (
        add_lesson(
            cli,
            project,
            by="Developer-1",
            role="developer",
            mistake="committed on main",
            cause="the branch guard was skipped",
            rule="run branch start before the first edit",
        )
        == 0
    )
    assert (
        add_lesson(
            cli,
            project,
            by="Tester-1",
            role="tester",
            mistake="certified without CI",
            cause="the local run was treated as the whole signal",
            rule="wait for the CI run on the pushed SHA",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-fix-x",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a lesson names a repeated mistake",
            "--from-lesson",
            "L-0002",
            "--body",
            "1. Run the CI job before the claim.",
        )
        == 0
    )
    created = capsys.readouterr().out
    assert "# S-0001 skill 'tw-fix-x' for the tester role (kind: mistake)" in created
    assert "#   fixes lesson: L-0002" in created
    assert "#   file: .agents/skills/tw-fix-x/SKILL.md" in created

    skill = skill_md(project, "tw-fix-x").read_text(encoding="utf-8")
    front = skill.split("---")[1]
    assert "kind: mistake" in front
    assert "prevents: L-0002" in front
    assert "## Prevents" in skill
    assert "the local run was treated as the whole signal" in skill
    assert "wait for the CI run on the pushed SHA" in skill

    rows = engine.parse_skills(registry(project))
    assert [(row["id"], row["name"], row["kind"], row["lesson"]) for row in rows] == [
        ("S-0001", "tw-fix-x", "mistake", "L-0002")
    ]

    closed = engine.parse_lessons(lessons_file(project, "tester"))[0]
    assert (closed["status"], closed["skill"]) == ("fixed", "tw-fix-x")
    assert closed["evidence"] == "pytest @abc -> 1 passed"

    assert cli("--project", project, "skill", "list") == 0
    skills = capsys.readouterr().out
    assert (
        "- S-0001 tw-fix-x                     [draft] kind=mistake lesson=L-0002 "
        "owner=tester           file=ok" in skills
    )
    assert cli("--project", project, "lesson", "list") == 0
    assert "(skill: tw-fix-x)" in capsys.readouterr().out

    assert (
        cli(
            "--project",
            project,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @def -> 2 passed",
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-close-a-fixed-lesson",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a fixed lesson still needs its workflow",
            "--from-lesson",
            "L-0001",
        )
        == 0
    )
    late = engine.parse_lessons(lessons_file(project, "developer"))[0]
    assert (late["status"], late["skill"]) == ("fixed", "tw-close-a-fixed-lesson")
    assert late["evidence"] == "pytest @def -> 2 passed"


def test_skill_create_refuses_the_illegal_shapes(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    assert (
        add_lesson(cli, project, by="Tester-1", role="tester", mistake="certified without CI") == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "foo",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a prefix is missing",
        )
        == 1
    )
    refusal = capsys.readouterr().err
    assert refusal[len("teamwork: ") :].strip() == PREFIX_REFUSAL
    assert not (project / ".agents" / "skills" / "foo").exists()
    assert engine.parse_skills(registry(project)) == []

    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-flow",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a flow repeats",
            "--kind",
            "workflow",
        )
        == 0
    )
    assert "# S-0001 skill 'tw-flow' for the tester role (kind: workflow)" in (
        capsys.readouterr().out
    )
    rows = engine.parse_skills(registry(project))
    assert [(row["id"], row["kind"], row["lesson"]) for row in rows] == [("S-0001", "workflow", "")]
    assert "- kind: workflow" in engine.render_skills(rows)

    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-mistake",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a mistake repeats",
            "--kind",
            "mistake",
        )
        == 1
    )
    mistake = capsys.readouterr().err
    assert mistake[len("teamwork: ") :].strip() == MISTAKE_NEEDS_LESSON
    assert not skill_md(project, "tw-mistake").exists()

    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-first-fix",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when the lesson gets its first skill",
            "--from-lesson",
            "L-0001",
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-second-fix",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a second skill claims the same lesson",
            "--from-lesson",
            "L-0001",
        )
        == 1
    )
    second = capsys.readouterr().err
    assert second[len("teamwork: ") :].strip() == ("lesson L-0001 is already fixed by tw-first-fix")
    assert not skill_md(project, "tw-second-fix").exists()


def test_candidates_names_a_review_failure_as_a_mistake(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    capsys.readouterr()
    queue = engine.task_file(team_root(project), "developer")
    queue.write_text(
        "# Tasks - developer\n\n"
        "## T-0001 · Fix the parser\n"
        "- priority: P0\n"
        "- status: done\n"
        "- area: parser\n"
        "- review_fails: 2\n"
        "- findings: the parser accepted a bare flag\n"
        "- review_evidence: pytest @abc -> 1 failed\n",
        encoding="utf-8",
    )

    assert cli("--project", project, "skill", "candidates") == 0
    out = capsys.readouterr().out
    assert "## mistake candidates (review failures)" in out
    assert "- developer: 1 task(s) with failed review(s), e.g. Fix the parser" in out
    assert "teamwork.py lesson add --by developer --mistake 'Fix the parser'" in out
    assert "--cause 'the parser accepted a bare flag'" in out
    assert "--evidence 'pytest @abc -> 1 failed'" in out
    assert (
        "teamwork.py skill create --name tw-<slug> --role developer --by <you> "
        "--kind mistake --from-lesson L-nnnn" in out
    )

    assert (
        add_lesson(cli, project, by="Developer-1", role="developer", mistake="accepted a bare flag")
        == 0
    )
    capsys.readouterr()
    assert cli("--project", project, "skill", "candidates") == 0
    assert "--from-lesson L-0001" in capsys.readouterr().out


def test_skill_share_notifies_a_peer_and_rm_unregisters(cli, project: Path, capsys) -> None:
    init_workspace(cli, project)
    assert cli("--project", project, "instance", "add", "tester", "--count", "1") == 0
    assert (
        cli(
            "--project",
            project,
            "skill",
            "create",
            "--name",
            "tw-flow",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a flow repeats",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", project, "skill", "share", "tw-flow", "--by", "Tester-1") == 0
    shared = capsys.readouterr().out
    assert "# shared 'tw-flow' with 1 instance(s): Tester-2" in shared

    row = engine.parse_skills(registry(project))[0]
    assert (row["status"], row["shared_with"]) == ("shared", "Tester-2")
    inbox = (team_root(project) / "Agents" / "Tester-2" / config.F_INBOX).read_text(
        encoding="utf-8"
    )
    assert "skill shared: tw-flow" in inbox
    assert "- when to use: when a flow repeats" in inbox

    assert cli("--project", project, "skill", "list") == 0
    listed = capsys.readouterr().out
    assert "[shared] kind=workflow" in listed
    assert "shared with: Tester-2" in listed

    assert cli("--project", project, "skill", "rm", "tw-flow", "--by", "Tester-1") == 0
    removed = capsys.readouterr().out
    assert (
        "# unregistered 'tw-flow'. The file .agents/skills/tw-flow/SKILL.md still "
        "exists: delete it on a branch through the normal review flow." in removed
    )
    assert engine.parse_skills(registry(project)) == []
    assert skill_md(project, "tw-flow").exists()


def test_eight_real_cli_adds_persist_one_record_each(project: Path, tmp_path: Path) -> None:
    """The process-boundary twin of the unit lock test (TS-0071).

    Eight ``scripts/teamwork.py lesson add`` processes are released from one
    barrier file so their read-allocate-write sequences overlap. An unlocked
    engine loses records and reuses ids; the lock makes every exit-0 add leave
    exactly one record and one ledger row that names it.

    The wait budget is the only thing ``CONCURRENT_LOCK_WAIT_SECONDS`` changes,
    and it is deliberately above ``io.LOCK_STALE_SECONDS`` (300): eight waiters
    re-poll every 50 ms with no fairness, so on a loaded Windows runner one of
    them can lose the race for the 60 s default and exit 4 even though the lock
    itself is correct (run 41916744357, job 126878425913). Waiting past the
    stale window also lets ``_lock_owner_stale`` reclaim a lock whose owner died
    instead of reporting it as a busy timeout. No assertion is relaxed: every
    process must still exit 0, every lesson must still be recorded exactly once
    with its own id, and the ledger must still carry one row per record.
    """
    code = [sys.executable, str(CLI_SHIM), "--project", str(project), "init", "--agents", AGENTS]
    code += ["--no-git"]
    assert subprocess.run(code, cwd=str(project), env=_env()).returncode == 0
    root = team_root(project)

    count = 8
    barrier = tmp_path / "lesson-race-start"
    env = _env()
    env["TEAMWORK_LOCK_TIMEOUT"] = str(CONCURRENT_LOCK_WAIT_SECONDS)
    processes = []
    for index in range(count):
        role = "developer" if index % 2 == 0 else "tester"
        by = "Developer-1" if role == "developer" else "Tester-1"
        argv = [
            "--project",
            str(project),
            "lesson",
            "add",
            "--by",
            by,
            "--role",
            role,
            "--mistake",
            f"race-{index}",
            "--cause",
            "the read-allocate-write sequence overlapped",
            "--rule",
            "hold the lessons lock for the whole sequence",
            "--evidence",
            f"pytest @race-{index} -> 1 passed",
        ]
        driver = (
            "import pathlib, runpy, sys, time\n"
            f"while not pathlib.Path({str(barrier)!r}).exists():\n"
            "    time.sleep(0.002)\n"
            f"sys.argv = [{str(CLI_SHIM)!r}, *{argv!r}]\n"
            f"runpy.run_path({str(CLI_SHIM)!r}, run_name='__main__')\n"
        )
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", driver],
                cwd=str(project),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
        )
    barrier.write_text("go", encoding="utf-8")
    results = [
        process.communicate(timeout=CONCURRENT_LOCK_WAIT_SECONDS + 120) for process in processes
    ]
    codes = [process.returncode for process in processes]
    assert codes == [0] * count, [
        (index, code, out, err)
        for index, (code, (out, err)) in enumerate(zip(codes, results, strict=True))
        if code != 0
    ]

    records = []
    for role in ("developer", "tester"):
        records.extend(engine.parse_lessons(lessons_file(project, role)))
    ids = [record["id"] for record in records]
    assert len(records) == count, records
    assert len(set(ids)) == count, ids
    assert sorted(ids) == [f"L-{index:04d}" for index in range(1, count + 1)]
    assert sorted(record["mistake"] for record in records) == sorted(
        f"race-{index}" for index in range(count)
    )

    printed = []
    for out, _err in results:
        found = re.findall(r"^# (L-\d{4}) recorded for \w+: (race-\d+)$", out, re.MULTILINE)
        assert len(found) == 1, out
        printed.append(found[0])
    assert {lesson_id for lesson_id, _mistake in printed} == set(ids)

    adds = [record for record in ledger_records(root) if record["action"] == "lesson.add"]
    assert len(adds) == count, adds
    assert {record["target"] for record in adds} == set(ids)


def _env() -> dict:
    """The child environment: hermetic, pointed at this checkout, no ambient team."""
    env = child_env(
        PYTHONPATH=str(REPO_ROOT / "src"),
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        TEAMWORK_SKILL_DIR=str(REPO_ROOT),
    )
    env.pop("TEAMWORK_ROOT", None)
    env.pop("TEAMWORK_TEAM", None)
    return env


def test_the_concurrent_wait_budget_is_derived_from_the_measured_starvation() -> None:
    """The wait is a measurement, not a round number: 2x what starved, past stale.

    Run 41916744357 job 126878425913: eight `lesson add` processes, one of them
    starved for the full 60 s default and exited 4 while the lock was correct.
    The budget must stay above that measurement with headroom, and above
    `io.LOCK_STALE_SECONDS` so a wait that long lets `_lock_owner_stale` reclaim
    a dead owner's lock instead of calling it busy. Raising the measurement
    without raising the budget fails here.
    """
    assert CONCURRENT_LOCK_WAIT_SECONDS >= 2 * MEASURED_STARVED_LOCK_WAIT_SECONDS, (
        f"CONCURRENT_LOCK_WAIT_SECONDS={CONCURRENT_LOCK_WAIT_SECONDS}s must be at least twice "
        f"the {MEASURED_STARVED_LOCK_WAIT_SECONDS}s wait a loaded runner starved, or the next "
        "loaded runner fails the concurrency test again"
    )
    assert CONCURRENT_LOCK_WAIT_SECONDS > io.LOCK_STALE_SECONDS, (
        f"CONCURRENT_LOCK_WAIT_SECONDS={CONCURRENT_LOCK_WAIT_SECONDS}s must outlast "
        f"io.LOCK_STALE_SECONDS={io.LOCK_STALE_SECONDS}s, or an abandoned lock reports as busy"
    )
