"""The harness surface: registry, whole-proposal lint and the always-on budget.

Each rule is pinned twice: once on a wired tree it must accept, and once on a tree
that breaks exactly that rule - a lint that cannot fail is decoration, and a
budget that cannot go over is not a cap. Every tree here is a throwaway directory,
so no test depends on this repository's own state or on a team workspace existing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from teamwork import config, engine, harness

SKILL_NAME = "demo-skill"

AGENTS_MD = """# Agents

<!-- BEGIN teamwork -->
## Guardrails

demo-skill is the extracted flow. Never commit on main.
<!-- END teamwork -->

Outside the managed block.
"""


def team_root(project: Path) -> Path:
    return (
        project / config.TEAM_ROOT_DIR / config.TEAMS_SUBDIR / engine.team_slug(project)
    ).resolve()


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def skill_text(
    name: str = SKILL_NAME,
    *,
    name_field: str | None = None,
    description: str = "when the demo flow is needed",
    body: str = "Run `teamwork.py ledger verify` first.",
) -> str:
    front = [
        "---",
        f"name: {name_field if name_field is not None else name}",
    ]
    if description:
        front.append(f'description: "{description}"')
    front.append("---")
    front.append(f"# {name}")
    front.append(body)
    return "\n".join(front) + "\n"


def build_tree(project: Path, *, name: str = SKILL_NAME, **overrides: str) -> Path:
    """A repository that satisfies every lint rule, with a hook to break one."""
    write(project / "AGENTS.md", AGENTS_MD)
    write(project / "SKILL.md", "# Skill\n\nAlways-on procedure.\n")
    write(project / "roles" / "developer.md", "# Developer\n")
    write(project / "references" / "Engineering.md", "# Engineering\n")
    write(project / "scripts" / "teamwork.py", "# shim\n")
    write(project / "src" / "teamwork" / "engine.py", "# engine\n")
    text = overrides.get("skill", skill_text(name))
    write(project / ".agents" / "skills" / name / "SKILL.md", text)
    return project


def rows(out: str) -> list[tuple]:
    """Data rows of ``harness list``, parsed with the product's own row parser.

    The frozen path spec of C2 is ``managed block in AGENTS.md``, spaces included,
    so a row is not ``line.split()``: the four columns are separated by runs of two
    or more spaces and ``harness.parse_surface_row`` is the one reader of that.
    """
    return [
        harness.parse_surface_row(line)
        for line in out.splitlines()
        if line.strip() and not line.startswith("#")
    ]


def row_by_path(out: str, spec: str) -> tuple:
    """The row whose path cell is exactly ``spec`` - the frozen registry spec."""
    for row in rows(out):
        if row[2] == spec:
            return row
    raise AssertionError(f"no row names the spec {spec!r} in:\n{out}")


def git(path: Path, *argv: str) -> str:
    done = subprocess.run(["git", "-C", str(path), *argv], capture_output=True, text=True)
    assert done.returncode == 0, (argv, done.stderr)
    return done.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", config.DEFAULT_BASE)
    git(path, "config", "user.name", "Developer")
    git(path, "config", "user.email", "developer@agents.nidvue.com")
    write(path / "README.md", "# repo\n")
    git(path, "add", "README.md")
    git(path, "commit", "-q", "-m", "first")
    return path


# --------------------------------------------------------------------------- #
# harness list
# --------------------------------------------------------------------------- #


def test_list_names_every_component_with_class_bytes_and_role(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    capsys.readouterr()

    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    components = [surface.component for surface in harness.collect(project, team_root(project))]
    assert components == [f"C{index}" for index in range(1, 9)]

    skill_line = row_by_path(out, "SKILL.md")
    assert skill_line[0] == harness.ALWAYS_ON
    assert int(skill_line[1]) == (project / "SKILL.md").stat().st_size
    assert skill_line[3] == "ceo"


def test_list_prints_exactly_eight_rows_in_component_order(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    capsys.readouterr()
    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    table = [line for line in out.splitlines() if not line.startswith("#")]
    assert len(table) == 8, f"one row per Harness^2 component, got:\n{out}"
    # parse_surface_row raises unless the line is four columns, so this also pins
    # "four whitespace-separated columns" - the spec cells may contain one space.
    for line in table:
        cells = harness.parse_surface_row(line)
        assert cells[0] in harness.CLASS_CELLS, f"unknown activation class: {line!r}"
        assert cells[1] == harness.NO_VALUE or cells[1].isdigit(), f"bytes: {line!r}"

    # The frozen path column of Architecture 12.2, spelled out and not read from
    # the product's own constants: `AGENTS.md` alone would not let a reader
    # recompute the 27 kB managed block, and `scripts/*.py` alone would not explain
    # a count that also sums `src/teamwork/*.py`.
    specs = [harness.parse_surface_row(line)[2] for line in table]
    assert specs == [
        "SKILL.md",
        "managed block in AGENTS.md",
        "Roles/<Role>/*.md + Global/GlobalMemory.md",
        "references/*.md",
        "n/a - lane packet, no file",
        ".agents/skills/*/SKILL.md",
        "scripts/*.py + src/teamwork/*.py",
        "hook_dir(root)/{pre-commit,pre-push}",
    ]
    roles = [harness.parse_surface_row(line)[3] for line in table]
    assert roles == ["ceo", "ceo", "-", "ceo", "-", "ceo", "developer", "-"]


def test_every_row_bytes_recompute_from_its_own_path_cell(cli, project, capsys) -> None:
    """A reader with only the row can reproduce the number: measure the spec."""
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    write(root / config.DIR_GLOBAL / config.F_GLOBAL, "# global memory\n")
    write(root / config.DIR_ROLES / "Developer" / config.F_SHORT, "# short\n")
    capsys.readouterr()

    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    for klass, size, spec, _role in rows(out):
        if spec == "n/a - lane packet, no file":
            assert size == harness.NO_VALUE, f"C5 has no file and no bytes: {klass} {size}"
            continue
        if spec == "hook_dir(root)/{pre-commit,pre-push}":
            # The hook directory is git's answer, not a repository path; the
            # linked-worktree test recomputes this row instead.
            assert size.isdigit(), f"C8 must still be a measurement: {size}"
            continue
        assert int(size) == recompute(spec, project, root), f"{klass} {spec} -> {size}"


def recompute(spec: str, repo: Path, root: Path) -> int:
    """Sum the files the cell names - the check a reader does with ``wc -c``."""
    total = 0
    for part in spec.split(" + "):
        if part == "managed block in AGENTS.md":
            text = (repo / "AGENTS.md").read_text(encoding="utf-8")
            start = text.find(engine.BEGIN)
            end = text.find(engine.END)
            total += len(text[start : end + len(engine.END)].encode("utf-8"))
        elif part == "Global/GlobalMemory.md":
            total += (root / part).stat().st_size
        elif part == "Roles/<Role>/*.md":
            for role in sorted((root / config.DIR_ROLES).iterdir()):
                if role.is_dir():
                    total += sum(path.stat().st_size for path in role.glob("*.md"))
        else:
            total += sum(path.stat().st_size for path in repo.glob(part) if path.is_file())
    return total


def test_list_marks_the_lane_packet_as_a_non_file(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    # 12.2: C5 has no file, so its class, byte and role cells are `-`; the path
    # cell says what it is, so nobody reads `n/a` as a path named n/a.
    assert row_by_path(out, "n/a - lane packet, no file") == ("-", "-", harness.LANE_PACKET, "-")
    assert [row[0] for row in rows(out) if row[0] == harness.NO_VALUE] == [harness.NO_VALUE]


def test_list_measures_the_managed_block_not_the_whole_agents_file(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    measured = int(row_by_path(out, "managed block in AGENTS.md")[1])
    block = AGENTS_MD.split(engine.BEGIN)[1].split(engine.END)[0]
    assert measured < (project / "AGENTS.md").stat().st_size
    assert measured == len((engine.BEGIN + block + engine.END).encode("utf-8"))


def test_list_bytes_are_measured_at_run_time(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert cli("--project", project, "harness", "list") == 0
    before = int(row_by_path(capsys.readouterr().out, "references/*.md")[1])

    write(project / "references" / "Extra.md", "x" * 1000)

    assert cli("--project", project, "harness", "list") == 0
    after = int(row_by_path(capsys.readouterr().out, "references/*.md")[1])
    assert after - before == (project / "references" / "Extra.md").stat().st_size


def test_list_resolves_the_hooks_through_git_not_through_toplevel_dot_git(
    cli, repo_root, tmp_path, capsys
) -> None:
    """C8 must ask git where the hooks live: in a linked worktree `.git` is a file.

    The pre-ruling resolver (``<toplevel>/.git/hooks``) reports 0 here because that
    path cannot even exist, which is the defect D-0001 was opened for. Both stages
    are written and both are counted: the cell names the pair, so a row that
    measured one stage would print half the number the cell promises.
    """
    primary = init_repo(tmp_path / "Primary")
    linked = tmp_path / "linked"
    git(primary, "worktree", "add", "-q", str(linked), "-b", "feature")
    assert (linked / ".git").is_file()

    common = Path(git(primary, "rev-parse", "--git-path", "hooks"))
    common = common if common.is_absolute() else (primary / common).resolve()
    write(common / "pre-commit", "#!/bin/sh\nexit 0\n")
    write(common / "pre-push", "#!/bin/sh\nexit 0\n# stage: pre-push\n")
    size = sum((common / stage).stat().st_size for stage in harness.HOOK_STAGES)

    capsys.readouterr()
    assert cli("--project", linked, "harness", "list") == 0
    measured = row_by_path(capsys.readouterr().out, "hook_dir(root)/{pre-commit,pre-push}")
    assert int(measured[1]) == size


def test_class_totals_sum_the_eight_rows(cli, project, capsys) -> None:
    """The printed table is fixed at eight rows; the cost roll-up is computed from it."""
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    capsys.readouterr()
    assert cli("--project", project, "harness", "list") == 0
    out = capsys.readouterr().out

    measured = {klass: 0 for klass in harness.CLASSES}
    for row in rows(out):
        if row[0] in measured and row[1].isdigit():
            measured[row[0]] += int(row[1])
    assert measured["always-on"] > 0 and measured["in-loop"] > 0
    assert harness.class_totals(harness.collect(project, team_root(project))) == measured


# --------------------------------------------------------------------------- #
# harness lint - the clean tree
# --------------------------------------------------------------------------- #


def test_lint_is_clean_on_a_wired_tree(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 0
    out = capsys.readouterr().out
    assert out.strip().endswith("# problems found: 0")
    assert "PROBLEM" not in out


def test_lint_skips_evidence_when_there_is_no_team_workspace(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert not team_root(project).exists()
    assert cli("--project", project, "harness", "lint", "--verbose") == 0
    out = capsys.readouterr().out
    assert "EVIDENCE: skipped" in out
    assert "# problems found: 0" in out


def test_lint_verbose_lists_every_file_checked_with_its_rule_outcomes(cli, project, capsys) -> None:
    """12.4: ``--verbose`` lists every file checked - not a count the reader trusts."""
    assert cli("--project", project, "init", "--no-git") == 0
    build_tree(project)  # after init: init regenerates AGENTS.md from the template
    write(
        project / ".agents" / "skills" / "other-skill" / "SKILL.md",
        skill_text("other-skill", body="Run `teamwork.py nosuchcommand` now."),
    )
    capsys.readouterr()

    assert cli("--project", project, "harness", "lint", "--verbose") == 1
    out = capsys.readouterr().out
    checked = [line for line in out.splitlines() if line.startswith("# checked: ")]

    # One line per file the run read: every always-on surface (TRIGGER's corpus),
    # every skill file, and the team registry when there is one.
    surfaces = harness.always_on_surfaces(project)
    skills = harness.skill_files(project)
    registry = harness.skills_path(team_root(project))
    expected = len(surfaces) + len(skills) + (1 if registry.is_file() else 0)
    assert len(checked) == expected, f"every file checked gets a line:\n{out}"

    for surface in surfaces:
        rel = harness.display(surface, project)
        assert [line for line in checked if line.startswith(f"# checked: {rel} ")], rel
        assert any(line == f"# checked: {rel} -> TRIGGER corpus" for line in checked), rel
    assert any(
        line.startswith("# checked: .agents/skills/demo-skill/SKILL.md -> IDENTITY ok, TRIGGER ok,")
        for line in checked
    ), out
    # The rule that did fire says so on the file's own line, not only in the
    # PROBLEM block: the verdict and the detail stay one grep apart.
    fired = [line for line in checked if "SUBCOMMAND fail" in line]
    assert fired == [
        "# checked: .agents/skills/other-skill/SKILL.md -> IDENTITY ok, TRIGGER fail, "
        "SUBCOMMAND fail, HELPER ok, EVIDENCE n/a"
    ], fired


# --------------------------------------------------------------------------- #
# harness lint - one failing tree per rule
# --------------------------------------------------------------------------- #


def lint_out(cli, capsys, project: Path) -> str:
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 1
    return capsys.readouterr().out


def test_identity_fails_when_the_frontmatter_name_disagrees_with_the_directory(
    cli, project, capsys
) -> None:
    build_tree(project, skill=skill_text(SKILL_NAME, name_field="other-skill"))
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_IDENTITY} .agents/skills/{SKILL_NAME}/SKILL.md" in out
    assert "does not match the directory" in out
    assert "# problems found: 1" in out


def test_identity_fails_without_a_description(cli, project, capsys) -> None:
    build_tree(project, skill=skill_text(SKILL_NAME, description=""))
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_IDENTITY}" in out
    assert "description" in out


def test_identity_fails_without_a_name_field(cli, project, capsys) -> None:
    build_tree(project, skill='---\ndescription: "x"\n---\n# demo-skill\n')
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_IDENTITY}" in out
    assert "no `name:`" in out


def test_trigger_fails_when_no_always_on_surface_names_the_skill(cli, project, capsys) -> None:
    build_tree(project, name="dead-skill", skill=skill_text("dead-skill"))
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_TRIGGER} .agents/skills/dead-skill/SKILL.md" in out
    assert "silently dead" in out

    write(project / "roles" / "developer.md", "# Developer\n\nRun `dead-skill` here.\n")
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 0


def test_subcommand_fails_on_a_command_the_parser_does_not_implement(cli, project, capsys) -> None:
    build_tree(project, skill=skill_text(SKILL_NAME, body="Run `teamwork.py nosuchcommand` now."))
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_SUBCOMMAND} .agents/skills/{SKILL_NAME}/SKILL.md" in out
    assert "nosuchcommand" in out


def test_subcommand_list_is_derived_from_the_parser() -> None:
    commands = harness.cli_subcommands()
    assert {"harness", "ledger", "tests", "skill"} <= commands
    assert "nosuchcommand" not in commands
    # `harness` is accepted only because this module registered itself there, so a
    # subcommand the parser does not know and this set does are the same question.
    assert engine.build_parser().parse_args(["harness", "list"]).cmd == "harness"


def test_helper_fails_on_a_path_the_skill_never_ships(cli, project, capsys) -> None:
    build_tree(project, skill=skill_text(SKILL_NAME, body="Read `references/Ghost.md` first."))
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_HELPER} .agents/skills/{SKILL_NAME}/SKILL.md" in out
    assert "references/Ghost.md" in out

    write(project / "references" / "Ghost.md", "# Ghost\n")
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 0


def test_helper_ignores_placeholders_globs_and_urls(cli, project, capsys) -> None:
    body = (
        "Use `scripts/<name>.py`, `docs/Team/*.md`, `$SKILL/scripts/teamwork.py` "
        "and see https://example.com/docs/guide.md for context."
    )
    build_tree(project, skill=skill_text(SKILL_NAME, body=body))
    capsys.readouterr()
    assert harness.helper_paths(body) == []
    assert cli("--project", project, "harness", "lint") == 0


def registered_skill(project: Path, status: str, verdict_line: str) -> None:
    """A team registry that lists the demo skill exactly the way `skill create` does.

    ``verdict_line`` goes into the skill file, which is where the evidence row
    lives; the registry only says which skills are shared.
    """
    root = team_root(project)
    write(
        project / ".agents" / "skills" / SKILL_NAME / "SKILL.md",
        skill_text(SKILL_NAME, body=f"## Evidence\n\n{verdict_line}"),
    )
    write(
        root / config.F_SKILLS,
        "\n".join(
            [
                "# Team skills",
                "",
                f"## S-0001 · {SKILL_NAME}",
                f"- name: {SKILL_NAME}",
                f"- status: {status}",
                "- owner_role: developer",
                "- created_by: Developer",
                f"- path: .agents/skills/{SKILL_NAME}/SKILL.md",
                verdict_line,
                "",
            ]
        )
        + "\n",
    )


def test_evidence_fails_for_a_shared_skill_without_a_verdict(cli, project, capsys) -> None:
    build_tree(project)
    registered_skill(project, "shared", "- note: extracted")
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_EVIDENCE} .agents/skills/{SKILL_NAME}/SKILL.md" in out
    assert "verdict" in out


@pytest.mark.parametrize("verdict", ["helped", "hurt", "no observed effect", "confounded"])
def test_evidence_accepts_every_documented_verdict(cli, project, capsys, verdict: str) -> None:
    build_tree(project)
    registered_skill(project, "shared", f"- verdict: {verdict}")
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 0


def test_evidence_is_not_required_for_a_draft_skill(cli, project, capsys) -> None:
    build_tree(project)
    registered_skill(project, "draft", "- note: NO_ENTRY - no rollout yet")
    capsys.readouterr()
    assert cli("--project", project, "harness", "lint") == 0


def test_evidence_fails_when_a_shared_skill_file_is_missing(cli, project, capsys) -> None:
    build_tree(project)
    registered_skill(project, "shared", "- verdict: helped")
    (project / ".agents" / "skills" / SKILL_NAME / "SKILL.md").unlink()
    out = lint_out(cli, capsys, project)
    assert f"- PROBLEM {harness.RULE_HELPER}" in out
    assert "does not exist" in out


def test_lint_reports_rule_major_and_path_sorted(cli, project, capsys) -> None:
    """Findings are ordered by rule first, path second: a reader reads a rule at a time."""
    build_tree(project)
    write(
        project / ".agents" / "skills" / "zeta-skill" / "SKILL.md",
        skill_text("zeta-skill", body="Run `teamwork.py nosuchcommand` on `scripts/Ghost.py`."),
    )
    write(
        project / ".agents" / "skills" / "alpha-skill" / "SKILL.md",
        skill_text("alpha-skill", body="Run `teamwork.py nosuchcommand` too."),
    )

    out = lint_out(cli, capsys, project)
    problems = [line for line in out.splitlines() if line.startswith("- PROBLEM ")]
    order = [line.split()[2] for line in problems]
    assert order == [
        harness.RULE_TRIGGER,
        harness.RULE_TRIGGER,
        harness.RULE_SUBCOMMAND,
        harness.RULE_SUBCOMMAND,
        harness.RULE_HELPER,
    ]
    paths = [line.split()[3].rstrip(":") for line in problems]
    assert paths[:2] == [
        ".agents/skills/alpha-skill/SKILL.md",
        ".agents/skills/zeta-skill/SKILL.md",
    ]
    assert paths[2:] == [
        ".agents/skills/alpha-skill/SKILL.md",
        ".agents/skills/zeta-skill/SKILL.md",
        ".agents/skills/zeta-skill/SKILL.md",
    ]


# --------------------------------------------------------------------------- #
# harness budget
# --------------------------------------------------------------------------- #


def budget_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line and not line.startswith("#")]


def test_budget_reports_every_instance_and_the_total(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    capsys.readouterr()

    assert cli("--project", project, "harness", "budget") == 0
    out = capsys.readouterr().out
    lines = budget_lines(out)
    instances = engine.known_instances(team_root(project))
    assert [line.split()[0] for line in lines[:-1]] == instances
    assert lines[-1].split()[0] == "total"
    cap = config.DEFAULT_ALWAYS_ON_BUDGET_KB * 1024
    for line in lines[:-1]:
        instance, always_on, budget, state = line.split()
        assert int(budget) == cap
        assert state == "ok"
        assert int(always_on) == harness.instance_always_on(
            project, team_root(project), engine.resolve_role(instance)
        )
    per_instance = [int(line.split()[1]) for line in lines[:-1]]
    assert lines[-1].split()[1:] == [str(sum(per_instance)), str(cap * len(instances)), "ok"]


def test_budget_goes_over_and_exits_non_zero(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    capsys.readouterr()

    assert cli("--project", project, "harness", "budget", "--limit", "1") == 1
    out = capsys.readouterr().out
    assert any(line.endswith("OVER") for line in budget_lines(out))
    assert budget_lines(out)[-1].endswith("OVER")


def test_budget_reads_the_cap_from_settings(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    settings = team_root(project) / config.F_SETTINGS
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["AlwaysOnBudgetKb"] = 200
    settings.write_text(json.dumps(data), encoding="utf-8")
    capsys.readouterr()

    assert cli("--project", project, "harness", "budget") == 0
    out = capsys.readouterr().out
    assert "Settings.json AlwaysOnBudgetKb" in out
    assert all(line.split()[2] == str(200 * 1024) for line in budget_lines(out)[:-1])

    data["AlwaysOnBudgetKb"] = 1
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert cli("--project", project, "harness", "budget") == 1
    assert all(line.endswith("OVER") for line in budget_lines(capsys.readouterr().out)[:-1])

    assert cli("--project", project, "harness", "budget", "--limit", "200") == 0


def test_budget_dies_without_a_team_workspace(cli, project, capsys) -> None:
    build_tree(project)
    capsys.readouterr()
    assert cli("--project", project, "harness", "budget") == 1
    err = capsys.readouterr().err
    assert "no team workspace" in err
    assert "init" in err


def test_budget_ignores_an_unusable_setting(cli, project, capsys) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    settings = team_root(project) / config.F_SETTINGS
    settings.write_text('{"AlwaysOnBudgetKb": "lots"}', encoding="utf-8")
    capsys.readouterr()

    assert cli("--project", project, "harness", "budget") == 0
    assert "(default)" in capsys.readouterr().out


def test_budget_settings_key_is_not_read_as_a_provider_cap(cli, project) -> None:
    build_tree(project)
    assert cli("--project", project, "init", "--no-git") == 0
    root = team_root(project)
    settings = root / config.F_SETTINGS
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["AlwaysOnBudgetKb"] = 90
    settings.write_text(json.dumps(data), encoding="utf-8")

    limits = engine.load_providers(root)
    assert "AlwaysOnBudgetKb" not in limits
    assert limits["ollama-cloud"] == config.DEFAULT_PROVIDER_LIMITS["ollama-cloud"]


def test_lint_on_this_repository_reports_only_the_routed_dead_skill(repo_root: Path) -> None:
    """Our own tree is the first real customer of the TRIGGER rule.

    `ceo-audit-close` is shipped but named in no always-on surface, so the rule
    must fire here - it has been silently dead since it was created. The one-line
    trigger fix belongs to the docs lane, so this test pins the exact routed
    finding instead of hiding it, and keeps working (asserting silence) once that
    line lands. Any *other* problem on our own tree is a regression.
    """
    findings, _stats = harness.lint(repo_root, repo_root / ".pi" / "no-team-workspace")
    others = [
        finding
        for finding in findings
        if finding.rule != harness.RULE_TRIGGER or "ceo-audit-close" not in finding.detail
    ]
    assert others == [], f"unexpected lint problems in this repository: {others}"

    if not (repo_root / ".agents" / "skills" / "ceo-audit-close" / "SKILL.md").is_file():
        return
    named = "ceo-audit-close" in "\n".join(
        path.read_text(encoding="utf-8") for path in harness.always_on_surfaces(repo_root)
    )
    dead = [finding for finding in findings if finding.rule == harness.RULE_TRIGGER]
    if named:
        assert dead == [], "the skill is named in an always-on surface: TRIGGER must be silent"
    else:
        assert [finding.path for finding in dead] == [".agents/skills/ceo-audit-close/SKILL.md"], (
            "the unnamed ceo-audit-close skill is the only TRIGGER finding this tree allows"
        )
