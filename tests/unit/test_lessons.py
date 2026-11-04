"""Unit: lesson records, the tw- prefix and the mistake workflow.

Layer ``unit``, area ``skills``. Every record is asserted on the file the
command wrote, so a renderer that loses a field or a parser that invents one
fails here rather than in a later integration run. The CLI is exercised
in-process, which is the boundary a Developer owns.

Owner: developer. Layer: unit. Area: skills.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from teamwork import config, engine, harness

AGENTS = "ceo,developer-1,tester-1"

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def ws(cli, project) -> Path:
    """A workspace with a developer and a tester lane."""
    assert cli("--project", project, "init", "--agents", AGENTS, "--no-git") == 0
    return project


def team_root(project: Path) -> Path:
    return project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)


def lessons_file(project: Path, role: str = "developer") -> Path:
    return engine.role_dir(team_root(project), role) / "Lessons.md"


def registry(project: Path) -> Path:
    return team_root(project) / "Skills.md"


def skill_md(project: Path, name: str) -> Path:
    return project / ".agents" / "skills" / name / "SKILL.md"


def add_lesson(
    cli,
    project: Path,
    *,
    by: str = "Developer-1",
    role: str = "",
    mistake: str = "committed on main",
    cause: str = "the branch guard was skipped",
    rule: str = "run branch start before the first edit",
    evidence: str = "git status @abc -> main",
    task: str = "",
) -> int:
    argv = [
        "--project",
        project,
        "lesson",
        "add",
        "--by",
        by,
        "--mistake",
        mistake,
        "--cause",
        cause,
        "--rule",
        rule,
        "--evidence",
        evidence,
    ]
    if role:
        argv += ["--role", role]
    if task:
        argv += ["--task", task]
    return cli(*argv)


def test_config_exposes_the_frozen_lesson_surface() -> None:
    assert config.F_LESSONS == "Lessons.md"
    assert config.SKILL_PREFIX == "tw-"
    assert engine.SKILL_KINDS == ("workflow", "mistake")


def test_lesson_add_writes_the_role_file_and_load_shows_it(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws, task="T-9999") == 0
    out = capsys.readouterr().out
    assert "# L-0001 recorded for developer: committed on main" in out
    assert str(lessons_file(ws)) in out

    text = lessons_file(ws).read_text(encoding="utf-8")
    assert text.startswith("# Lessons - mistakes this role will not repeat")
    assert "## L-0001 - committed on main" in text
    assert "- role: developer" in text
    assert "- status: open" in text
    assert "- task: T-9999" in text
    assert "- skill:" not in text  # empty optional fields are not noise

    assert cli("--project", ws, "load", "Developer-1") == 0
    load = capsys.readouterr().out
    assert "# Lessons (developer) - open mistakes to avoid:" in load
    assert "- [L-0001] committed on main -> run branch start before the first edit" in load
    assert "# fixed: 0; full list: teamwork.py lesson list --role developer" in load


def test_lesson_ids_are_global_across_roles(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    assert add_lesson(cli, ws, by="Tester-1", role="tester", mistake="tested nothing") == 0
    capsys.readouterr()

    assert "## L-0001" in lessons_file(ws).read_text(encoding="utf-8")
    assert "## L-0002" in lessons_file(ws, "tester").read_text(encoding="utf-8")

    assert cli("--project", ws, "lesson", "list", "--role", "developer") == 0
    out = capsys.readouterr().out
    assert "L-0001" in out and "L-0002" not in out
    assert cli("--project", ws, "lesson", "show", "L-0002") == 0
    assert "- role: tester" in capsys.readouterr().out


def test_lesson_list_filters_open_and_fixed(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    assert add_lesson(cli, ws, mistake="second mistake") == 0
    capsys.readouterr()
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0002",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @def -> 3 passed",
        )
        == 0
    )
    capsys.readouterr()

    assert cli("--project", ws, "lesson", "list", "--status", "open") == 0
    opened = capsys.readouterr().out
    assert "L-0001" in opened and "L-0002" not in opened
    assert "(skill: no skill)" in opened

    assert cli("--project", ws, "lesson", "list", "--status", "fixed") == 0
    fixed = capsys.readouterr().out
    assert "L-0002" in fixed and "L-0001" not in fixed

    assert cli("--project", ws, "lesson", "list", "--status", "all") == 0
    everything = capsys.readouterr().out
    assert "L-0001" in everything and "L-0002" in everything


def test_a_fixed_lesson_cannot_be_refixed_without_new_evidence(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @abc -> 1 passed",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
        )
        == 1
    )
    assert (
        "lesson L-0001 is already fixed by no skill; pass --evidence to re-prove the fix"
        in capsys.readouterr().err
    )
    text = lessons_file(ws).read_text(encoding="utf-8")
    assert "- status: fixed" in text
    assert "- evidence: pytest @abc -> 1 passed" in text


def test_a_fixed_lesson_can_be_refixed_with_new_evidence(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "pytest @abc -> 1 passed",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            ws,
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
    text = lessons_file(ws).read_text(encoding="utf-8")
    assert "- status: fixed" in text
    assert "- evidence: pytest @def -> 2 passed" in text


def test_lesson_show_prints_every_field_and_unknown_ids_die(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    capsys.readouterr()
    assert cli("--project", ws, "lesson", "show", "L-0001") == 0
    out = capsys.readouterr().out
    for field in engine.LESSON_FIELDS:
        assert f"- {field}:" in out, field
    assert "#   file:" in out

    assert cli("--project", ws, "lesson", "show", "L-9999") == 1
    err = capsys.readouterr().err
    assert "no lesson 'L-9999'" in err


def test_lesson_add_requires_every_text_field(cli, ws, capsys) -> None:
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "add",
            "--by",
            "Developer-1",
            "--mistake",
            "x",
            "--cause",
            "y",
            "--rule",
            "z",
        )
        == 2
    )
    assert "--evidence" in capsys.readouterr().err
    assert not lessons_file(ws).exists()


def test_lesson_fix_requires_a_registered_tw_mistake_skill(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-flow",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a workflow repeats",
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--skill",
            "tw-missing",
            "--evidence",
            "pytest @def -> 1 passed",
        )
        == 1
    )
    assert "no skill 'tw-missing' in Skills.md" in capsys.readouterr().err

    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--skill",
            "tw-flow",
            "--evidence",
            "pytest @def -> 1 passed",
        )
        == 1
    )
    assert "not 'mistake'" in capsys.readouterr().err

    old = engine.new_skill(
        "old-skill", "developer", "when", "Developer", ".agents/skills/old-skill/SKILL.md"
    )
    engine.write_skills(registry(ws), [old])
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--skill",
            "old-skill",
            "--evidence",
            "pytest @def -> 1 passed",
        )
        == 1
    )
    assert "must start with tw-" in capsys.readouterr().err
    assert "- status: open" in lessons_file(ws).read_text(encoding="utf-8")


def test_skill_create_refuses_an_unprefixed_name(cli, ws, capsys) -> None:
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "demo-skill",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a demo repeats",
        )
        == 1
    )
    err = capsys.readouterr().err
    assert "must start with tw-" in err
    assert not skill_md(ws, "demo-skill").exists()
    assert engine.parse_skills(registry(ws)) == []


def test_from_lesson_links_the_skill_and_the_lesson_both_ways(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws, task="T-9999") == 0
    capsys.readouterr()
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-branch-guard-first",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when an edit starts before a task branch exists",
            "--from-lesson",
            "L-0001",
            "--body",
            "1. Run branch start before the first edit.",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "kind: mistake" in out
    assert "fixes lesson: L-0001" in out

    text = skill_md(ws, "tw-branch-guard-first").read_text(encoding="utf-8")
    assert "kind: mistake" in text
    assert "prevents: L-0001" in text
    assert "## Prevents" in text
    assert "the branch guard was skipped" in text
    assert "run branch start before the first edit" in text

    entries = engine.parse_skills(registry(ws))
    assert [(entry["name"], entry["kind"], entry["lesson"]) for entry in entries] == [
        ("tw-branch-guard-first", "mistake", "L-0001")
    ]

    lesson = lessons_file(ws).read_text(encoding="utf-8")
    assert "- status: fixed" in lesson
    assert "- skill: tw-branch-guard-first" in lesson
    assert "- evidence: git status @abc -> main" in lesson

    assert cli("--project", ws, "lesson", "list", "--status", "fixed") == 0
    assert "tw-branch-guard-first" in capsys.readouterr().out


def test_from_lesson_requires_an_open_lesson_of_the_same_role(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws) == 0
    capsys.readouterr()
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-wrong-role",
            "--role",
            "tester",
            "--by",
            "Tester-1",
            "--for",
            "when a test fails",
            "--from-lesson",
            "L-0001",
        )
        == 1
    )
    assert "belongs to developer" in capsys.readouterr().err

    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-no-lesson",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a lesson does not exist",
            "--from-lesson",
            "L-0099",
        )
        == 1
    )
    assert "no lesson 'L-0099'" in capsys.readouterr().err


def test_a_lesson_fixed_without_a_skill_can_still_be_closed_by_a_skill(cli, ws, capsys) -> None:
    """14.1: lesson-first (fixed with evidence, no skill) then the skill closes it."""
    assert add_lesson(cli, ws) == 0
    assert (
        cli(
            "--project",
            ws,
            "lesson",
            "fix",
            "L-0001",
            "--by",
            "Developer-1",
            "--evidence",
            "manual proof @abc -> fixed",
        )
        == 0
    )
    capsys.readouterr()
    assert "- status: fixed" in lessons_file(ws).read_text(encoding="utf-8")
    assert "- skill:" not in lessons_file(ws).read_text(encoding="utf-8")

    assert (
        cli(
            "--project",
            ws,
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
    text = lessons_file(ws).read_text(encoding="utf-8")
    assert "- status: fixed" in text
    assert "- skill: tw-close-a-fixed-lesson" in text


def test_a_lesson_already_fixed_by_a_skill_refuses_a_second_skill(cli, ws, capsys) -> None:
    """14.1: the skill a fixed lesson names is its fix; a second skill is refused."""
    assert add_lesson(cli, ws) == 0
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-first-fix",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when the first fix lands",
            "--from-lesson",
            "L-0001",
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-second-fix",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a second fix tries to land",
            "--from-lesson",
            "L-0001",
        )
        == 1
    )
    assert "lesson L-0001 is already fixed by tw-first-fix" in capsys.readouterr().err
    assert not skill_md(ws, "tw-second-fix").exists()


def test_kind_mistake_without_from_lesson_is_refused(cli, ws, capsys) -> None:
    assert (
        cli(
            "--project",
            ws,
            "skill",
            "create",
            "--name",
            "tw-mistake",
            "--role",
            "developer",
            "--by",
            "Developer-1",
            "--for",
            "when a mistake repeats",
            "--kind",
            "mistake",
        )
        == 1
    )
    assert "requires --from-lesson" in capsys.readouterr().err
    assert not skill_md(ws, "tw-mistake").exists()


def test_an_old_registry_row_reads_as_workflow(cli, ws) -> None:
    registry(ws).write_text(
        "# Team skills\n\n"
        "## S-0001 · tw-old\n"
        "- name: tw-old\n"
        "- status: draft\n"
        "- owner_role: developer\n"
        "- path: .agents/skills/tw-old/SKILL.md\n"
        "- description: an older row\n",
        encoding="utf-8",
    )
    entries = engine.parse_skills(registry(ws))
    assert entries[0]["kind"] == "workflow"
    assert entries[0]["lesson"] == ""

    rec = engine.new_skill("tw-new", "developer", "when", "Developer", "p")
    rendered = engine.render_skills([rec])
    assert "- kind: workflow" in rendered
    assert "- lesson:" not in rendered

    rec = engine.new_skill(
        "tw-fix", "developer", "when", "Developer", "p", kind="mistake", lesson="L-0001"
    )
    rendered = engine.render_skills([rec])
    assert "- kind: mistake" in rendered
    assert "- lesson: L-0001" in rendered


def test_candidates_lists_review_failures_and_a_lesson_hint(cli, ws, capsys) -> None:
    assert cli("--project", ws, "skill", "candidates") == 0
    out = capsys.readouterr().out
    assert "## mistake candidates (review failures)" in out
    assert "- none: no task of any role carries a failed review" in out

    task = engine.new_task("Fix the parser", priority="P0")
    task["area"] = "parser"
    task["status"] = "doing"
    task["review_fails"] = 1
    task["findings"] = "the parser accepted a bare flag"
    task["review_evidence"] = "pytest @abc -> 1 failed"
    engine.write_tasks(engine.task_file(team_root(ws), "developer"), [task], "developer")

    assert cli("--project", ws, "skill", "candidates") == 0
    out = capsys.readouterr().out
    assert "- developer: 1 task(s) with failed review(s), e.g. Fix the parser" in out
    assert "teamwork.py lesson add --by developer --mistake 'Fix the parser'" in out
    assert "--cause 'the parser accepted a bare flag'" in out
    assert "teamwork.py skill create --name tw-<slug> --role developer" in out
    assert "--from-lesson L-nnnn" in out

    assert add_lesson(cli, ws) == 0
    capsys.readouterr()
    assert cli("--project", ws, "skill", "candidates") == 0
    assert "--from-lesson L-0001" in capsys.readouterr().out


def test_load_without_a_lessons_file_is_clean(cli, ws, capsys) -> None:
    assert not lessons_file(ws).exists()
    assert cli("--project", ws, "load", "Developer-1") == 0
    out = capsys.readouterr().out
    assert "# Lessons: none recorded for developer" in out
    assert "teamwork.py lesson add --by Developer-1 --mistake" in out


def test_lesson_text_cannot_forge_a_second_record(cli, ws, capsys) -> None:
    assert add_lesson(cli, ws, mistake="bad\n## L-9999 - forged") == 0
    capsys.readouterr()
    text = lessons_file(ws).read_text(encoding="utf-8")
    assert "\n## L-9999" not in text
    items = engine.parse_lessons(lessons_file(ws))
    assert len(items) == 1
    assert items[0]["id"] == "L-0001"


def test_concurrent_lesson_adds_persist_one_record_per_success(ws, tmp_path: Path) -> None:
    """Twelve real CLI adds race on one workspace: one record per exit-0 add.

    The pre-lock code reads the file, allocates an id and writes with no
    serialisation, so concurrent adds overwrite each other and reuse ids. Every
    child loads the engine first, then waits on one barrier file, so the calls
    enter the read-allocate-write sequence together. A child that times out
    waiting for the lock exits 4: that is a refusal, not a lost record, so only
    a code outside {0, 4} or a success without exactly one record fails here.
    """
    count = 12
    barrier = tmp_path / "lesson-race-start"
    src = str(REPO_ROOT / "src")
    processes = []
    for index in range(count):
        role = "developer" if index % 2 == 0 else "tester"
        by = "Developer-1" if role == "developer" else "Tester-1"
        argv = [
            "--project",
            str(ws),
            "lesson",
            "add",
            "--by",
            by,
            "--role",
            role,
            "--mistake",
            f"concurrent-{index}",
            "--cause",
            "the read-allocate-write sequence was not serialised",
            "--rule",
            "hold the lessons lock for the whole sequence",
            "--evidence",
            f"pytest @race-{index} -> 1 passed",
        ]
        code = (
            "import pathlib, sys, time\n"
            f"sys.path.insert(0, {src!r})\n"
            "from teamwork import engine\n"
            f"while not pathlib.Path({str(barrier)!r}).exists():\n"
            "    time.sleep(0.002)\n"
            f"raise SystemExit(engine.main({argv!r}))\n"
        )
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", code],
                cwd=str(ws),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    barrier.write_text("go", encoding="utf-8")
    results = [process.communicate(timeout=120) for process in processes]
    codes = [process.returncode for process in processes]
    unexpected = [
        (index, code, out, err)
        for index, (code, (out, err)) in enumerate(zip(codes, results))
        if code not in (0, 4)
    ]
    assert not unexpected, unexpected
    ok = [index for index, code in enumerate(codes) if code == 0]

    records = []
    for role in ("developer", "tester"):
        records.extend(engine.parse_lessons(lessons_file(ws, role)))
    assert len(records) == len(ok), (len(records), ok, codes)
    ids = [item["id"] for item in records]
    assert len(set(ids)) == len(ids), ids
    assert sorted(item["mistake"] for item in records) == sorted(
        f"concurrent-{index}" for index in ok
    )

    ledger = [
        json.loads(line)
        for line in (team_root(ws) / config.F_LEDGER).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    adds = [record for record in ledger if record["action"] == "lesson.add"]
    assert len(adds) == len(ok), adds
    assert {record["target"] for record in adds} == set(ids), adds


def test_harness_prefix_rule_fires_on_a_scratch_tree_and_accepts_tw(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    demo = repo / ".agents" / "skills" / "demo" / "SKILL.md"
    demo.parent.mkdir(parents=True)
    demo.write_text(
        '---\nname: demo\ndescription: "does a thing"\nkind: workflow\n---\n# demo\n',
        encoding="utf-8",
    )
    findings, _stats = harness.lint(repo, tmp_path / "no-team")
    prefix = [finding for finding in findings if finding.rule == harness.RULE_PREFIX]
    assert prefix, findings
    assert prefix[0].path == ".agents/skills/demo/SKILL.md"
    assert "skill name 'demo' does not carry the required prefix 'tw-'" in prefix[0].detail

    target = repo / ".agents" / "skills" / "tw-demo" / "SKILL.md"
    target.parent.mkdir(parents=True)
    demo.rename(target)
    target.write_text(
        '---\nname: tw-demo\ndescription: "does a thing"\nkind: workflow\n---\n# tw-demo\n',
        encoding="utf-8",
    )
    findings, _stats = harness.lint(repo, tmp_path / "no-team")
    assert not [finding for finding in findings if finding.rule == harness.RULE_PREFIX]
