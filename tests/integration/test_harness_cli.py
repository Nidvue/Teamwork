"""Integration: the harness surface and the git hooks at the process boundary.

Layer ``integration``, area ``harness``, owner Tester (T-0001). Every assertion
is made by *running* ``scripts/teamwork.py`` as a subprocess against a scaffolded
temp workspace - never by importing the engine - so the tests prove what an
operator gets, and each one quotes the clause of the frozen interface it holds
(``docs/Team/Architecture.md`` section 11, AC-H2..AC-H5).

The scaffold is a real git repository with the team tree, a managed ``AGENTS.md``
block and a minimal skill bundle, so every byte ``harness list`` prints can be
compared with a size the test put on disk itself.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"
AGENTS = "ceo,developer-1"

#: 11.2: the closed set of activation classes, and the one row that is not a file.
CLASSES = {"always-on", "on-demand", "in-loop", "n/a"}
#: 11.3: C5 is an inference context, so its class cell is ``-`` like its bytes.
NO_VALUE = "-"
#: 11.2, in component order (C1..C8): the ``path`` spec each row must print,
#: frozen so a row explains its own byte count. C2 is the managed *block* (the
#: file holds text outside it), C3 is every role plus the global memory the run
#: sums, C7 is the scripts *and* the engine package, and C8 is both hook stages
#: found through the resolver the hooks are installed through - spelled as the
#: resolver call, because ``<toplevel>/.git`` is a file in a linked worktree.
SPECS = [
    "SKILL.md",
    "managed block in AGENTS.md",
    "Roles/<Role>/*.md + Global/GlobalMemory.md",
    "references/*.md",
    "n/a - lane packet, no file",
    ".agents/skills/*/SKILL.md",
    "scripts/*.py + src/teamwork/*.py",
    "hook_dir(root)/{pre-commit,pre-push}",
]

#: 11.2 freezes four columns, and two of its frozen path specs contain a single
#: space, so the cells are separated by a run of two or more spaces. ``split()``
#: tears ``managed block in AGENTS.md`` into three cells and loses the shape.
CELL_SEPARATOR = re.compile(r"\s{2,}")


def run(
    project: Path,
    *args: str,
    env: dict | None = None,
    stdin: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """``python3 scripts/teamwork.py --project <project> <args>`` as a process."""
    child = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(project),  # no developer git config reaches the scaffold
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "LC_ALL": "C.UTF-8",
    }
    child.update(env or {})
    return subprocess.run(
        [sys.executable, str(CLI_SHIM), "--project", str(project), *args],
        cwd=str(cwd or project),
        env=child,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def ok(project: Path, *args: str, **kwargs) -> str:
    done = run(project, *args, **kwargs)
    assert done.returncode == 0, f"{args} -> {done.returncode}\n{done.stdout}\n{done.stderr}"
    return done.stdout


def git(project: Path, *args: str, stdin: str | None = None, env: dict | None = None):
    """Run git in the scaffold with an explicit, hermetic environment."""
    child = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(project),
        "GIT_AUTHOR_NAME": "Tester",
        "GIT_AUTHOR_EMAIL": "tester@agents.nidvue.com",
        "GIT_COMMITTER_NAME": "Tester",
        "GIT_COMMITTER_EMAIL": "tester@agents.nidvue.com",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    child.update(env or {})
    return subprocess.run(
        ["git", "-C", str(project), *args],
        env=child,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def git_ok(project: Path, *args: str, **kwargs) -> str:
    done = git(project, *args, **kwargs)
    assert done.returncode == 0, f"git {args} -> {done.returncode}\n{done.stderr}"
    return done.stdout


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def scaffold(tmp_path: Path, *, agents: str = AGENTS, git_repo: bool = True) -> Path:
    """A temp workspace: git repo, team tree, managed AGENTS.md, minimal bundle."""
    project = tmp_path / "ws"
    project.mkdir()
    if git_repo:
        git_ok(project, "init", "-q", "-b", "main")
    ok(project, "init", "--agents", agents, "--no-git")
    ok(project, "agents-md")
    write(project / "SKILL.md", "# skill\n")
    write(project / "references" / "one.md", "# one\n")
    write(project / "roles" / "ceo.md", "# charter\n")
    return project


def skill(root: Path, name: str, body: str) -> Path:
    """One ``.agents/skills/<name>/SKILL.md`` with frontmatter and a body."""
    return write(
        root / ".agents" / "skills" / name / "SKILL.md",
        f"---\nname: {name}\ndescription: does one thing\n---\n{body}",
    )


def managed_block(path: Path) -> str:
    """The CEO-owned teamwork block inside AGENTS.md, markers included."""
    text = path.read_text(encoding="utf-8")
    start = text.find("<!-- BEGIN teamwork -->")
    end = text.find("<!-- END teamwork -->")
    assert start >= 0 and end > start, "agents-md wrote no managed block"
    return text[start : end + len("<!-- END teamwork -->")]


def rows(output: str) -> list[list[str]]:
    """The printed table as cells, on the frozen cell separator (11.2)."""
    return [CELL_SEPARATOR.split(line.strip()) for line in output.splitlines() if line.strip()]


def said(done: subprocess.CompletedProcess) -> str:
    """Everything the process printed, for one readable assertion message."""
    return done.stdout + done.stderr


# --------------------------------------------------------------------------- #
# AC-H2: harness list
# --------------------------------------------------------------------------- #


def test_harness_list_is_the_eight_row_registry_measured_on_disk(tmp_path: Path) -> None:
    """11.2: eight rows, one per component, four columns, no header, exit 0."""
    project = scaffold(tmp_path)
    skill_md = project / "SKILL.md"
    skill_md.write_text("# skill\n" + "x" * 100, encoding="utf-8")
    block = managed_block(project / "AGENTS.md")

    out = ok(project, "harness", "list")
    table = rows(out)

    assert len(table) == 8, f"11.2 says exactly eight rows, got {len(table)}:\n{out}"
    for row in table:
        assert len(row) == 4, f"11.2 says four columns, got {row!r}"
        assert row[0] in CLASSES | {NO_VALUE}, f"unknown activation class {row[0]!r}"
        assert row[1].isdigit() or row[1] == NO_VALUE, (
            f"bytes must be a count or '-', got {row[1]!r}"
        )

    # C1..C8 order, pinned by the frozen spec of each component: the registry
    # prints no component id, so the path column is what carries the order.
    assert [row[2] for row in table] == SPECS, out
    assert table[0][1] == str(skill_md.stat().st_size), table[0]
    assert table[1][1] == str(len(block.encode("utf-8"))), table[1]
    assert table[2][3] == NO_VALUE, f"11.2: C3 is owned by no single role: {table[2]}"
    assert table[3][2] == "references/*.md", table[3]
    assert table[4][1] == NO_VALUE, f"11.2: only C5 has no bytes, and it prints '-': {table[4]}"
    assert table[4][0] == NO_VALUE, f"11.2: C5 is not a file, so its class is '-': {table[4]}"
    assert table[5][2] == ".agents/skills/*/SKILL.md", table[5]
    assert table[6][3] == "developer", table[6]
    assert table[7][3] == NO_VALUE, f"11.2: C8 has no section-2 owner: {table[7]}"


def test_harness_list_measures_the_tree_at_run_time(tmp_path: Path) -> None:
    """11.2: C4 is the size of ``references/*.md`` *now*, not a stored manifest."""
    project = scaffold(tmp_path)

    def references_row() -> list[str]:
        found = [
            row
            for row in rows(ok(project, "harness", "list"))
            if len(row) > 2 and row[2] == "references/*.md"
        ]
        assert len(found) == 1, found
        return found[0]

    before = references_row()
    added = write(project / "references" / "second.md", "y" * 512)
    after = references_row()
    assert int(after[1]) == int(before[1]) + added.stat().st_size, (before, after)


# --------------------------------------------------------------------------- #
# AC-H3: harness lint, one purpose-built tree per rule
# --------------------------------------------------------------------------- #


def test_harness_lint_passes_a_clean_tree(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    write(project / "AGENTS.md", (project / "AGENTS.md").read_text() + "\ndemo-skill\n")
    skill(project, "demo-skill", "# demo\n")
    out = ok(project, "harness", "lint")
    assert "# problems found: 0" in out, out


def test_harness_lint_fails_a_skill_whose_name_differs_from_its_directory(
    tmp_path: Path,
) -> None:
    project = scaffold(tmp_path)
    write(project / "AGENTS.md", (project / "AGENTS.md").read_text() + "\ndemo\n")
    write(
        project / ".agents" / "skills" / "demo" / "SKILL.md",
        "---\nname: other\ndescription: does one thing\n---\n# demo\n",
    )
    done = run(project, "harness", "lint")
    assert done.returncode == 1, done.stdout
    assert "- PROBLEM IDENTITY .agents/skills/demo/SKILL.md:" in done.stdout, done.stdout


def test_harness_lint_fails_a_skill_no_always_on_surface_names(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    skill(project, "orphan-skill", "# orphan\n")
    done = run(project, "harness", "lint")
    assert done.returncode == 1, done.stdout
    assert "- PROBLEM TRIGGER .agents/skills/orphan-skill/SKILL.md:" in done.stdout, done.stdout


def test_harness_lint_fails_a_teamwork_subcommand_the_parser_does_not_register(
    tmp_path: Path,
) -> None:
    project = scaffold(tmp_path)
    write(project / "AGENTS.md", (project / "AGENTS.md").read_text() + "\ndemo\n")
    skill(project, "demo", "# demo\n\nRun `teamwork.py nosuchcommand` first.\n")
    done = run(project, "harness", "lint")
    assert done.returncode == 1, done.stdout
    assert "- PROBLEM SUBCOMMAND .agents/skills/demo/SKILL.md:" in done.stdout, done.stdout


def test_harness_lint_fails_a_helper_path_that_does_not_exist(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    write(project / "AGENTS.md", (project / "AGENTS.md").read_text() + "\ndemo\n")
    skill(project, "demo", "# demo\n\nSee `references/never-shipped.md`.\n")
    done = run(project, "harness", "lint")
    assert done.returncode == 1, done.stdout
    assert "- PROBLEM HELPER .agents/skills/demo/SKILL.md:" in done.stdout, done.stdout


def test_harness_lint_fails_a_shared_skill_with_no_evidence_row(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    write(project / "AGENTS.md", (project / "AGENTS.md").read_text() + "\ndemo\n")
    skill(project, "demo", "# demo\n")
    skills_md = next(project.glob(".pi/Teamwork/Teams/*/Skills.md"))
    write(
        skills_md,
        skills_md.read_text(encoding="utf-8")
        + "\n## S-0001 · demo\n- name: demo\n- path: .agents/skills/demo/SKILL.md\n"
        "- status: shared\n",
    )
    done = run(project, "harness", "lint")
    assert done.returncode == 1, done.stdout
    assert "- PROBLEM EVIDENCE .agents/skills/demo/SKILL.md:" in done.stdout, done.stdout

    # the same tree with the verdict the rule asks for is clean
    skill(project, "demo", "# demo\n\nverdict: helped\n")
    assert "# problems found: 0" in ok(project, "harness", "lint")


def test_harness_lint_verbose_names_what_it_checked(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    out = ok(project, "harness", "lint", "--verbose")
    assert "# skill files: 0" in out, out
    assert "# cli subcommands:" in out, out
    assert "# EVIDENCE:" in out, out


#: 11.4: one ``# checked: <file> -> <RULE verdict, ...>`` line per skill file read.
CHECKED_SKILL_RE = re.compile(
    r"^# checked: \S.* -> IDENTITY (?:ok|fail), TRIGGER (?:ok|fail), "
    r"SUBCOMMAND (?:ok|fail), HELPER (?:ok|fail), EVIDENCE (?:ok|fail|n/a|skipped)$"
)


def test_the_shipped_tree_lints_clean_and_accounts_for_every_file_it_read() -> None:
    """11.4 on the repository itself: `harness lint` exits 0 at this revision.

    The one skill in this tree is ``on-demand``, so it only exists while an
    always-on surface names it (``SKILL.md`` section 6 names ``ceo-audit-close``).
    Deleting that trigger line turns this test red - which is the point: an
    unnamed skill is dead text, and the rule that says so must stay enforced on
    the tree the team actually ships.
    """
    done = run(REPO_ROOT, "harness", "lint")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "# problems found: 0" in done.stdout, done.stdout

    verbose = ok(REPO_ROOT, "harness", "lint", "--verbose")
    checked = [line for line in verbose.splitlines() if line.startswith("# checked: ")]
    assert checked, verbose
    for line in checked:
        assert (
            line.endswith("TRIGGER corpus")
            or line.endswith("EVIDENCE corpus")
            or (CHECKED_SKILL_RE.match(line))
        ), f"11.4: not a '# checked: <file> -> RULE verdict' line: {line!r}"

    assert any(
        line.startswith(
            "# checked: .agents/skills/ceo-audit-close/SKILL.md -> IDENTITY ok, TRIGGER ok"
        )
        for line in checked
    ), f"the shipped skill is not named by an always-on surface:\n{verbose}"

    surfaces = len(list((REPO_ROOT / "roles").glob("*.md"))) + 2  # AGENTS.md + SKILL.md
    skills = len(list((REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")))
    registry = 1 if any("Skills.md" in line for line in checked) else 0
    assert len(checked) == surfaces + skills + registry, (
        f"{len(checked)} checked lines for {surfaces} surfaces + {skills} skills "
        f"+ {registry} registry:\n{verbose}"
    )


# --------------------------------------------------------------------------- #
# AC-H4: harness budget
# --------------------------------------------------------------------------- #


def test_harness_budget_reports_every_instance_against_the_cap(tmp_path: Path) -> None:
    project = scaffold(tmp_path)
    out = ok(project, "harness", "budget")
    lines = [line.split() for line in out.splitlines() if line[:1] not in ("#", " ") and line]
    instances = [line[0].lower() for line in lines[:-1]]
    assert instances == ["ceo", "developer-1"], lines
    for line in lines[:-1]:
        assert len(line) == 4, line
        assert line[1].isdigit() and line[2].isdigit(), line
        assert line[3] == "ok", line
    assert lines[-1][0] == "total", lines[-1]
    assert lines[-1][3] == "ok", lines[-1]


def test_harness_budget_goes_over_and_exits_non_zero(tmp_path: Path) -> None:
    """11.5: ``--limit`` overrides the workspace value; any OVER row exits 1."""
    project = scaffold(tmp_path)
    done = run(project, "harness", "budget", "--limit", "1")
    assert done.returncode == 1, done.stdout
    body = [line.split() for line in done.stdout.splitlines() if line.split()[-1:] in (["OVER"],)]
    assert len(body) == 3, done.stdout  # two instances plus the total line
    assert all(line[3] == "OVER" for line in body), done.stdout
    per_instance = [line for line in body if line[0] != "total"]
    assert all(line[2] == str(1 * 1024) for line in per_instance), f"11.5: KiB: {body}"


def test_harness_budget_without_a_workspace_says_to_init(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    done = run(empty, "harness", "budget")
    assert done.returncode == 1, done.stdout
    assert "init" in said(done), said(done)


# --------------------------------------------------------------------------- #
# AC-H5: the hooks, against a real git repository
# --------------------------------------------------------------------------- #


def installable(tmp_path: Path) -> Path:
    """A scaffold that can run its own hooks: a real engine shim in the tree."""
    project = scaffold(tmp_path)
    shutil.copytree(REPO_ROOT / "scripts", project / "scripts")
    shutil.copytree(REPO_ROOT / "src", project / "src")
    return project


def hook_path(project: Path, stage: str) -> Path:
    where = Path(git_ok(project, "rev-parse", "--git-path", "hooks").strip())
    return (where if where.is_absolute() else project / where) / stage


def test_hooks_install_status_uninstall_round_trip(tmp_path: Path) -> None:
    """11.6: written into git's own hooks dir, marked, 0755, LF, reversible."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")

    for stage in ("pre-commit", "pre-push"):
        path = hook_path(project, stage)
        assert path.is_file(), f"{stage} not written to git's hooks dir"
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o755, f"11.6 says mode 0755, got {oct(mode)}"
        assert path.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
        assert b"\r" not in path.read_bytes(), "11.6: LF endings"

    status = ok(project, "hooks", "status")
    assert "pre-commit installed" in status and "pre-push installed" in status, status

    ok(project, "hooks", "uninstall")
    assert not hook_path(project, "pre-commit").exists()
    assert "pre-commit absent" in ok(project, "hooks", "status")


def test_the_installed_hook_carries_the_marker_literal(tmp_path: Path) -> None:
    """11.6: status, uninstall and the overwrite refusal all key on one literal."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    for stage in ("pre-commit", "pre-push"):
        line = hook_path(project, stage).read_text(encoding="utf-8").splitlines()[1]
        assert "teamwork-managed hook" in line, f"11.6 marker missing on line 2: {line!r}"


def test_the_shim_body_is_the_contract_body(tmp_path: Path) -> None:
    """11.6 freezes three constructs in the shim, each for a measured reason."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    text = hook_path(project, "pre-commit").read_text(encoding="utf-8")
    # -f, not -x: scripts/teamwork.py is committed 100644, so an executable-bit
    # test would make every hook a silent no-op.
    assert '[ -f "$root/scripts/teamwork.py" ]' in text, text
    assert "[ -x" not in text, text
    # :-, so an inherited `set -u` cannot turn the bypass into a refusal.
    assert '[ -n "${TEAMWORK_SKIP_HOOKS:-}" ]' in text, text
    # the || exit 0 is the whole failure path: no silent 2>/dev/null on it.
    assert "root=$(git rev-parse --show-toplevel) || exit 0" in text, text
    assert "2>/dev/null" not in text, text


def test_hooks_install_from_a_linked_worktree_reaches_the_common_git_dir(
    tmp_path: Path,
) -> None:
    """11.6: a lane worktree has no hooks dir of its own - its ``.git`` is a file."""
    project = installable(tmp_path)
    allowed = {"TEAMWORK_ALLOW_MAIN": "1"}
    write(project / "notes.txt", "one\n")
    git_ok(project, "add", "notes.txt")
    git_ok(project, "commit", "-m", "one", env=allowed)
    lane = tmp_path / "lane"
    git_ok(project, "worktree", "add", "-q", "-b", "lane", str(lane))
    assert (lane / ".git").is_file(), "the premise: a linked worktree's .git is a file"

    ok(lane, "hooks", "install")

    for stage in ("pre-commit", "pre-push"):
        assert hook_path(project, stage).is_file(), f"{stage} is not in the common git dir"
    assert "pre-commit installed" in ok(lane, "hooks", "status")
    assert "pre-commit installed" in ok(project, "hooks", "status")

    # C8 is measured through the same resolver, so it counts both stages from
    # inside the worktree instead of reporting 0 for a hook that is executing.
    hooks_size = sum(
        hook_path(project, stage).stat().st_size for stage in ("pre-commit", "pre-push")
    )
    assert rows(ok(lane, "harness", "list"))[7][1] == str(hooks_size)

    ok(lane, "hooks", "uninstall")
    assert not hook_path(project, "pre-commit").exists()


def test_hooks_are_written_where_core_hooks_path_points(tmp_path: Path) -> None:
    """11.6: the directory is git's answer, so a configured ``core.hooksPath`` wins."""
    project = installable(tmp_path)
    custom = tmp_path / "custom-hooks"
    git_ok(project, "config", "core.hooksPath", str(custom))

    ok(project, "hooks", "install")

    for stage in ("pre-commit", "pre-push"):
        assert (custom / stage).is_file(), f"{stage} was not written to core.hooksPath"
        assert not (project / ".git" / "hooks" / stage).exists(), f"{stage} ignored the config"
    assert str(custom) in ok(project, "hooks", "status")

    # git must actually run the hook from the configured directory.
    write(project / "notes.txt", "hello\n")
    git_ok(project, "add", "notes.txt")
    refused = git(project, "commit", "-m", "on main")
    assert refused.returncode != 0, refused.stdout + refused.stderr

    ok(project, "hooks", "uninstall")
    assert not (custom / "pre-commit").exists()


def test_hooks_install_refuses_a_foreign_hook_without_force(tmp_path: Path) -> None:
    """11.6: overwrite needs ``--force``; a foreign hook is never silently replaced."""
    project = installable(tmp_path)
    hook_path(project, "pre-commit").parent.mkdir(parents=True, exist_ok=True)
    write(hook_path(project, "pre-commit"), "#!/bin/sh\nexit 0\n")

    refused = run(project, "hooks", "install")
    assert refused.returncode != 0, refused.stdout
    assert hook_path(project, "pre-commit").read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"
    assert "pre-commit foreign" in ok(project, "hooks", "status")

    ok(project, "hooks", "install", "--force")
    assert "hook pre-commit" in hook_path(project, "pre-commit").read_text(encoding="utf-8")
    ok(project, "hooks", "uninstall")
    assert not hook_path(project, "pre-push").exists()


def test_the_root_commit_on_the_default_branch_is_refused(tmp_path: Path) -> None:
    """R1 also covers the first commit: an unborn ``main`` is still ``main``."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    write(project / "notes.txt", "hello\n")
    git_ok(project, "add", "notes.txt")

    refused = git(project, "commit", "-m", "on main")
    assert refused.returncode != 0, refused.stdout + refused.stderr
    assert "main" in said(refused), said(refused)
    assert git(project, "rev-list", "-n", "1", "--all").stdout.strip() == "", "it committed"


def test_a_later_commit_on_the_default_branch_is_refused(tmp_path: Path) -> None:
    """R1: git itself must abort the commit, not a printed instruction."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    allowed = {"TEAMWORK_ALLOW_MAIN": "1"}
    write(project / "notes.txt", "hello\n")
    git_ok(project, "add", "notes.txt")
    git_ok(project, "commit", "-m", "seeded", env=allowed)

    write(project / "notes.txt", "again\n")
    refused = git(project, "commit", "-am", "on main")
    assert refused.returncode != 0, refused.stdout + refused.stderr
    assert "main" in said(refused), said(refused)
    assert git_ok(project, "log", "-1", "--format=%s").strip() == "seeded"

    allowed_run = git(project, "commit", "-am", "on main", env=allowed)
    assert allowed_run.returncode == 0, allowed_run.stderr
    assert git_ok(project, "log", "-1", "--format=%s").strip() == "on main"


def test_skip_hooks_bypasses_both_hooks(tmp_path: Path) -> None:
    """11.6: the bypass is documented and exits 0 before anything else fires."""
    project = installable(tmp_path)
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git_ok(remote, "init", "--bare", "-q", "-b", "main")
    ok(project, "hooks", "install")
    allowed = {"TEAMWORK_ALLOW_MAIN": "1"}
    write(project / "notes.txt", "hello\n")
    git_ok(project, "add", "notes.txt")
    git_ok(project, "commit", "-m", "seeded", env=allowed)
    write(project / "notes.txt", "hello again\n")
    done = git(project, "commit", "-am", "bypassed", env={"TEAMWORK_SKIP_HOOKS": "1"})
    assert done.returncode == 0, done.stderr
    assert git_ok(project, "log", "-1", "--format=%s").strip() == "bypassed"

    # the push side: a rewrite R1..P2 would refuse goes through under the bypass
    git_ok(project, "remote", "add", "origin", str(remote))
    git_ok(project, "push", "-q", "origin", "main", env={"TEAMWORK_SKIP_HOOKS": "1"})
    pushed = git_ok(remote, "rev-parse", "main").strip()
    git_ok(project, "reset", "--hard", "HEAD~1")
    write(project / "notes.txt", "rewritten\n")
    git_ok(project, "commit", "--amend", "-am", "rewritten", env=allowed)
    assert git(project, "merge-base", "--is-ancestor", pushed, "HEAD").returncode != 0
    forced = git(project, "push", "--force", "origin", "main", env={"TEAMWORK_SKIP_HOOKS": "1"})
    assert forced.returncode == 0, forced.stdout + forced.stderr
    assert git_ok(remote, "rev-parse", "main").strip() != pushed


def test_a_non_role_commit_identity_warns_and_still_commits(tmp_path: Path) -> None:
    """R3: a provenance warning by contract, never a refusal (exit 0)."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    write(project / "notes.txt", "hello\n")
    git_ok(project, "add", "notes.txt")
    done = git(
        project,
        "commit",
        "-m",
        "operator identity",
        env={
            "TEAMWORK_ALLOW_MAIN": "1",
            "GIT_AUTHOR_EMAIL": "operator@example.com",
            "GIT_COMMITTER_EMAIL": "operator@example.com",
        },
    )
    assert done.returncode == 0, done.stderr
    assert done.stderr.strip(), "R3 must say something on stderr"
    assert git_ok(project, "log", "-1", "--format=%s").strip() == "operator identity"


def test_a_force_push_to_the_default_branch_is_refused(tmp_path: Path) -> None:
    """P1: a non-fast-forward update of ``refs/heads/main`` never reaches the remote."""
    project = installable(tmp_path)
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git_ok(remote, "init", "--bare", "-q", "-b", "main")
    ok(project, "hooks", "install")
    allowed = {"TEAMWORK_ALLOW_MAIN": "1"}
    write(project / "notes.txt", "one\n")
    git_ok(project, "add", "notes.txt")
    git_ok(project, "commit", "-m", "one", env=allowed)
    write(project / "notes.txt", "two\n")
    git_ok(project, "commit", "-am", "two", env=allowed)
    git_ok(project, "remote", "add", "origin", str(remote))
    git_ok(project, "push", "-q", "origin", "main")
    pushed = git_ok(remote, "rev-parse", "main").strip()

    git_ok(project, "reset", "--hard", "HEAD~1")  # drop the pushed tip locally
    write(project / "notes.txt", "three\n")
    git_ok(project, "commit", "-am", "three", env=allowed)
    assert git(project, "merge-base", "--is-ancestor", pushed, "HEAD").returncode != 0

    refused = git(project, "push", "--force", "origin", "main")
    assert refused.returncode != 0, refused.stdout
    assert git_ok(remote, "rev-parse", "main").strip() == pushed, "the remote moved"

    allowed = git(project, "push", "--force", "origin", "main", env={"TEAMWORK_ALLOW_FORCE": "1"})
    assert allowed.returncode == 0, allowed.stderr


def test_a_delete_of_the_default_branch_is_refused(tmp_path: Path) -> None:
    """P2: deleting ``refs/heads/main`` has no override, not even the push one."""
    project = installable(tmp_path)
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git_ok(remote, "init", "--bare", "-q", "-b", "main")
    # git's own protection is switched OFF on purpose. A default bare remote
    # refuses the delete by itself ("deletion of the current branch
    # prohibited"), and then the refusal under test would be git's, not the
    # hook's - the assertion would hold for the wrong reason.
    git_ok(remote, "config", "receive.denyDeleteCurrent", "ignore")
    ok(project, "hooks", "install")
    allowed = {"TEAMWORK_ALLOW_MAIN": "1"}
    write(project / "notes.txt", "one\n")
    git_ok(project, "add", "notes.txt")
    git_ok(project, "commit", "-m", "one", env=allowed)
    git_ok(project, "remote", "add", "origin", str(remote))
    git_ok(project, "push", "-q", "origin", "main")
    pushed = git_ok(remote, "rev-parse", "main").strip()

    refused = git(project, "push", "origin", "--delete", "main")
    assert refused.returncode != 0, refused.stdout + refused.stderr
    # the ENGINE's own words. Asserting the word "delete" alone would be
    # vacuous: the pytest tmp path carries it too, so the assertion would hold
    # even with the refusal message deleted.
    assert "refusing to delete refs/heads/main" in said(refused), said(refused)
    assert "deleting the default branch is a red line" in said(refused), said(refused)
    assert git_ok(remote, "rev-parse", "main").strip() == pushed, "the remote lost main"

    still = git(project, "push", "origin", "--delete", "main", env={"TEAMWORK_ALLOW_FORCE": "1"})
    assert still.returncode != 0, "11.7: P2 has no override"
    assert "refusing to delete refs/heads/main" in said(still), said(still)
    assert git_ok(remote, "rev-parse", "main").strip() == pushed

    # CONTROL: the same push with the hook bypassed goes through, because the
    # remote no longer refuses it. So the two refusals above are the hook's.
    control = git(project, "push", "origin", "--delete", "main", env={"TEAMWORK_SKIP_HOOKS": "1"})
    assert control.returncode == 0, control.stdout + control.stderr
    assert git(remote, "rev-parse", "--verify", "main").returncode != 0, "the delete went through"


def test_hook_and_hooks_coexist_and_a_typo_is_a_usage_error() -> None:
    """11.1: ``hook`` and ``hooks`` both resolve; an unknown word exits 2."""
    bare = REPO_ROOT
    assert run(bare, "hooks", "status", cwd=REPO_ROOT).returncode in (0, 1)
    assert run(bare, "hook", "--help", cwd=REPO_ROOT).returncode == 0
    typo = run(bare, "hookk", cwd=REPO_ROOT)
    assert typo.returncode == 2, typo.stdout + typo.stderr


def test_hooks_outside_a_git_repository_say_so(tmp_path: Path) -> None:
    """11.6: every ``hooks`` subcommand dies with 1 and names the missing repository."""
    plain = tmp_path / "plain"
    plain.mkdir()
    for verb in ("install", "status", "uninstall"):
        done = run(plain, "hooks", verb)
        assert done.returncode == 1, (verb, done.stdout, done.stderr)
        assert "git" in said(done).lower(), said(done)


@pytest.mark.parametrize("stage", ["pre-commit", "pre-push"])
def test_the_installed_hook_is_a_shim_not_a_copy_of_the_rules(tmp_path: Path, stage: str) -> None:
    """11.6: the file execs the engine, so one engine serves every worktree."""
    project = installable(tmp_path)
    ok(project, "hooks", "install")
    text = hook_path(project, stage).read_text(encoding="utf-8")
    assert f"hook {stage}" in text, text
    assert "scripts/teamwork.py" in text, text
