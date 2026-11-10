"""System-layer conformance test for the frozen harness/hook CLI contract.

Covers [Architecture](../../../docs/Team/Architecture.md) section 11, which is the
contract the `harness`, `hooks` and `hook` lanes build against:

1. the documented command and flag list is exactly the frozen list;
2. the harness surface registry names exactly the eight Harness^2 components,
   each with an activation class from the closed set, and every component that
   names a repository file names one that exists;
3. the clauses a downstream lane cannot re-derive are stated in the contract -
   the skip escape, the hook marker, the budget key and its unit, the one
   threshold, and the hook directory git is asked for;
4. the hook directory is ONE resolver used by install, status and uninstall,
   correct only as an atomic pair with the `-C <root>` pin (ruling D-0001
   R1-R6), and the git facts under that ruling hold on this machine;
5. the CLI registers what the document freezes, group by group: a group that
   has landed must be complete, and a group this revision has not landed is
   reported as NOT LANDED instead of failing the whole test (11.9).

Owner: architect. Task: T-0001. Layer: system (area cli-contract).
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import pytest

# ``tests/unit/test_cli_contract.py`` -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO_ROOT / "docs" / "Team" / "Architecture.md"

#: The hook directory is one resolver, spelled as an atomic pair (D-0001 R2).
RESOLVER = "git -C <root> rev-parse --path-format=absolute --git-path hooks"

#: The relative form, correct only WITH the `-C <root>` pin beside it.
RESOLVER_RELATIVE = "git -C <root> rev-parse --git-path hooks"

#: The CEO's withdrawn amendment (D-0001 R2): unsafe alone, never a contract.
WITHDRAWN = "resolved against the project root"

SECTION = "## 11. Harness surface and hook contract (frozen)"

#: The frozen surface, verb by verb, flag and positional included.
FROZEN_COMMANDS = (
    ("harness", "list", (), ()),
    ("harness", "lint", ("--verbose",), ()),
    ("harness", "budget", ("--limit",), ()),
    ("hooks", "install", ("--force",), ()),
    ("hooks", "status", (), ()),
    ("hooks", "uninstall", (), ()),
    ("hook", "pre-commit", (), ()),
    ("hook", "pre-push", (), ("remote", "url")),
)

#: The closed set in 11.3, plus ``-`` for the component with no file (C5).
ACTIVATION_CLASSES = ("always-on", "on-demand", "in-loop", "-")

#: C1..C8 in registry order -> the class each one is frozen to.
FROZEN_CLASSES = (
    ("C1", "always-on"),
    ("C2", "always-on"),
    ("C3", "always-on"),
    ("C4", "on-demand"),
    ("C5", "-"),
    ("C6", "on-demand"),
    ("C7", "in-loop"),
    ("C8", "in-loop"),
)

#: Clauses a lane would otherwise have to invent: each must be in the contract.
REQUIRED_CLAUSES = (
    "TEAMWORK_SKIP_HOOKS",
    "TEAMWORK_ALLOW_MAIN=1",
    "TEAMWORK_ALLOW_FORCE=1",
    "teamwork-managed hook",
    "AlwaysOnBudgetKb",
    "SETTINGS_NON_PROVIDER",
    "1048576",
    "config.DEFAULT_BASE",
    "gitutil.lfs_tracked",
    "rev-parse --git-path hooks",
    "git rev-parse --show-toplevel",
    "# problems found: N",
    "- PROBLEM <RULE> <path>: <detail>",
)

GROUP = ("harness", "hooks", "hook")


def _section_text() -> str:
    """The text of Architecture.md section 11, up to the next level-2 heading."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert SECTION in text, f"Architecture.md lost its section heading: {SECTION!r}"
    body = text.split(SECTION, 1)[1]
    return body.split("\n## ", 1)[0]


def _documented_commands() -> list:
    """Parse the fenced command block of 11.1 into (group, verb, flags, positionals)."""
    block = re.search(r"```text\n(.*?)```", _section_text(), re.S)
    assert block, "section 11.1 must keep its fenced command block"
    parsed = []
    for line in block.group(1).splitlines():
        line = line.strip()
        if not line.startswith("teamwork.py "):
            continue
        words = line[len("teamwork.py ") :].split()
        group, verb = words[0], words[1]
        rest = " ".join(words[2:])
        optional = " ".join(re.findall(r"\[([^\]]*)\]", rest))
        flags = tuple(word for word in optional.split() if word.startswith("--"))
        required = re.sub(r"\[[^\]]*\]", " ", rest)
        positionals = tuple(word.strip("<>") for word in required.split() if word)
        parsed.append((group, verb, flags, positionals))
    return parsed


def _flowed() -> str:
    """Section 11 with its line wrapping collapsed, so phrases match across lines."""
    return re.sub(r"\s+", " ", _section_text())


def _frozen_body() -> str:
    """The one fenced `sh` block of 11.6: the hook body, verbatim."""
    section = _section_text()
    marker = "and exactly this body:"
    assert marker in section, "11.6 must keep its 'and exactly this body' fence"
    tail = section.split(marker, 1)[1]
    assert "```sh\n" in tail, "11.6's body fence is gone"
    return tail.split("```sh\n", 1)[1].split("```", 1)[0]


def _registry_rows() -> list:
    """Parse the C1..C8 markdown table of 11.2 into (component, path cell, class, role)."""
    rows = []
    for line in _section_text().splitlines():
        if not re.match(r"\| C\d ", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == 5, f"registry row must have 5 columns: {line!r}"
        component, _name, path_cell, activation, role = cells
        rows.append((component, path_cell, activation, role))
    return rows


def _top_level_choices() -> dict:
    from teamwork.engine import build_parser

    parser = build_parser()
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(actions) == 1, "the engine must expose exactly one top-level subparser"
    return actions[0].choices


def _group_gaps(group: str) -> list:
    """Every frozen verb/flag/positional this group's parser is missing.

    Empty means the group landed whole; anything else on a registered group is
    the half-landing 11.9 forbids. An unregistered group is not asked.
    """
    parser = _top_level_choices()[group]
    subparsers = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    verbs = subparsers[0].choices if subparsers else {}
    gaps = []
    for name, verb, flags, positionals in FROZEN_COMMANDS:
        if name != group:
            continue
        if verb not in verbs:
            gaps.append(f"{group} {verb}")
            continue
        leaf = verbs[verb]
        options = {opt for action in leaf._actions for opt in action.option_strings}
        gaps += [f"{group} {verb} {flag}" for flag in flags if flag not in options]
        dests = {action.dest for action in leaf._actions if not action.option_strings}
        gaps += [f"{group} {verb} <{pos}>" for pos in positionals if pos not in dests]
    return gaps


# --------------------------------------------------------------------------- #
# 11.1 the frozen command list
# --------------------------------------------------------------------------- #


def test_the_contract_freezes_exactly_the_eight_commands() -> None:
    assert _documented_commands() == list(FROZEN_COMMANDS)


def test_the_documented_flags_are_the_frozen_flags() -> None:
    documented = {f"{g} {v}": (flags, pos) for g, v, flags, pos in _documented_commands()}
    frozen = {f"{g} {v}": (flags, pos) for g, v, flags, pos in FROZEN_COMMANDS}
    assert documented == frozen


# --------------------------------------------------------------------------- #
# 11.2 / 11.3 the surface registry
# --------------------------------------------------------------------------- #


def test_the_registry_names_exactly_the_eight_components() -> None:
    rows = _registry_rows()
    assert [row[0] for row in rows] == [component for component, _ in FROZEN_CLASSES]


def test_every_component_carries_the_activation_class_it_is_frozen_to() -> None:
    rows = _registry_rows()
    assert [(row[0], row[2]) for row in rows] == list(FROZEN_CLASSES)
    for component, _path, activation, _role in rows:
        assert activation in ACTIVATION_CLASSES, f"{component} has class {activation!r}"


def test_every_role_cell_names_a_real_role_or_none() -> None:
    from teamwork.config import ROLE_PARENT

    for component, _path, _activation, role in _registry_rows():
        assert role == "-" or role in ROLE_PARENT, f"{component} names role {role!r}"


def test_every_registry_path_that_is_a_repository_file_exists() -> None:
    """The registry describes the tree; a path it names must be in the tree.

    Workspace state (`Roles/<Role>/`, `Global/`) and C8 - which is measured
    through the hook-directory resolver, not as a repository path (11.6) - are
    asserted by their spelling instead, one section each.
    """
    checked = 0
    for component, path_cell, _activation, _role in _registry_rows():
        for token in re.findall(r"`([^`]+)`", path_cell):
            if "<" in token or token.startswith(("Roles/", "Global/", "n/a", "hook_dir(")):
                continue
            matches = sorted(REPO_ROOT.glob(token))
            assert matches, f"{component} names {token!r}, which matches nothing in the tree"
            checked += 1
        if component == "C5":
            assert path_cell.startswith("`n/a`"), "C5 must stay marked as having no file"
    assert checked >= 5, f"only {checked} registry paths were actually checked"


def test_the_activation_classes_are_defined_as_a_closed_set() -> None:
    section = _section_text()
    for name in ("always-on", "on-demand", "in-loop", "`n/a`"):
        assert name in section, f"section 11 does not define the class {name!r}"


# --------------------------------------------------------------------------- #
# 11.5 / 11.6 clauses a lane must not invent
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("clause", REQUIRED_CLAUSES)
def test_the_contract_states_each_clause_a_lane_could_invent(clause: str) -> None:
    assert clause in _section_text(), f"the contract no longer states {clause!r}"


def test_the_budget_unit_is_frozen_as_kib_and_the_single_threshold_is_named() -> None:
    section = _section_text()
    assert "**one instance**" in section, "the budget unit is one instance"
    assert "never the roster" in section
    assert "120 KiB = 122880 B" in section
    assert "**1024**" in section, "the KiB multiplier is frozen"


def test_the_contract_records_the_hook_directory_git_is_asked_for() -> None:
    section = _section_text()
    assert "per **common git dir**" in section
    assert "prints the literal directory it probed" in section


# --------------------------------------------------------------------------- #
# 11.2 C8 / 11.6 / 11.9 one hook-directory resolver (ruling D-0001 R1-R6)
# --------------------------------------------------------------------------- #


def _rule_rows() -> list:
    """The hook-rule table of 11.7: (id, stage, rule, override)."""
    rows = []
    for block in _section_text().split("### 11.7", 1)[1].split("\n### ", 1)[0].splitlines():
        if not re.match(r"\| [RP]\d ", block):
            continue
        cells = [c.strip() for c in block.strip().strip("|").split("|")]
        assert len(cells) == 4, f"rule row must have 4 columns: {block!r}"
        rows.append(tuple(cells))
    return rows


def _row(component: str) -> tuple:
    for row in _registry_rows():
        if row[0] == component:
            return row
    raise AssertionError(f"component {component} is missing from the registry")


def test_c8_is_measured_through_the_resolver_not_a_repository_relative_path() -> None:
    """A repository-relative `.git/hooks` spec selects nothing inside a worktree.

    There `<toplevel>/.git` is a gitfile, so `os.path.getsize` raises
    `NotADirectoryError` and `glob` returns `[]`: the row would print 0 bytes for
    a hook that is installed and executing (review finding F1, D-0001 R6).
    """
    path_cell = _row("C8")[1]
    assert "hook_dir(root)" in path_cell, path_cell
    assert "pre-commit" in path_cell and "pre-push" in path_cell
    assert ".git/hooks" not in path_cell, path_cell


def test_the_contract_forbids_a_hook_path_built_from_dot_git() -> None:
    """R1/R5: no `.git` + suffix, no `.git/hooks` constant, no hardcoded default."""
    flowed = _flowed()
    assert "build a path from `.git` plus a suffix" in flowed
    assert "spell `.git/hooks` as a constant" in flowed
    assert "No default is hardcoded" in flowed
    assert "`<toplevel>/.git/hooks`" not in flowed


def test_a_surface_that_selects_nothing_by_spelling_may_not_report_zero() -> None:
    section = _flowed()
    assert "genuinely do not exist" in section
    assert "by its spelling" in section


def test_the_resolver_is_frozen_as_an_atomic_pair_with_the_c_pin() -> None:
    """R2: the resolver and the `-C <root>` pin stand or fall together."""
    flowed = _flowed()
    assert RESOLVER in flowed
    assert RESOLVER_RELATIVE in flowed
    assert "The `-C <root>` pin is mandatory" in flowed
    assert WITHDRAWN not in flowed, "the withdrawn amendment reappeared as contract text"


def test_one_resolver_serves_install_status_and_uninstall() -> None:
    """R1: the read side must be the same call as the write side."""
    section = _section_text()
    flowed = _flowed()
    for subcommand in ("`hooks install`", "`hooks status`", "`hooks uninstall`"):
        assert subcommand in section, subcommand
    assert "One resolver, three subcommands" in flowed
    assert "same helper" in flowed and "hook_dir(root)" in flowed
    assert "prints the literal directory it probed" in flowed


def test_the_shim_keeps_the_toplevel_and_the_hook_dir_is_git_s_answer() -> None:
    """R3: two different questions, two different answers, no common prefix."""
    flowed = _flowed()
    body = _frozen_body()
    assert "root=$(git rev-parse --show-toplevel) || exit 0" in body
    assert "2>/dev/null" not in body, "the merged shim leaves git's error on stderr"
    assert "must not assert a common prefix" in flowed
    assert "which work tree the rules act on" in flowed
    assert "where git reads hooks" in flowed


def test_the_frozen_shim_body_tests_the_engine_file_for_existence_not_mode() -> None:
    """A1: `scripts/teamwork.py` is committed 100644, so `-x` is a silent no-op."""
    section = _section_text()
    body = _frozen_body()
    assert '[ -f "$root/scripts/teamwork.py" ]' in body
    assert "[ -x " not in body, "an executable-bit test turns every hook into a no-op"
    assert "committed mode" in section and "100644" in section
    assert 'config.HOOK_MARKER = "teamwork-managed hook"' in section


def test_the_frozen_shim_body_writes_the_merged_marker_line_verbatim() -> None:
    """A1/A3: the body is `hooks.py shim()`, line for line and flag for flag."""
    from teamwork.hooks import shim

    body = _frozen_body()
    assert body.strip("\n") == shim("pre-commit").strip("\n"), (
        "11.6 has drifted from the shim the code writes"
    )
    assert shim("pre-push").replace("pre-push", "pre-commit") == shim("pre-commit")


def test_r1_resolves_an_unborn_head_so_the_root_commit_is_refused() -> None:
    """A3: `rev-parse --abbrev-ref HEAD` cannot answer on an unborn branch.

    Both halves are frozen: the RULE row names the resolver, and the prose says
    why - the first commit on the default branch is exactly the one that an
    unborn HEAD would wave through.
    """
    flowed = _flowed()
    assert "must also refuse the **root commit**" in flowed
    assert "falls back to `git symbolic-ref --short HEAD`" in flowed
    assert "unborn branch" in flowed
    r1 = [row for row in _rule_rows() if row[0] == "R1"]
    assert len(r1) == 1, "the R1 rule row is missing"
    assert "git symbolic-ref --short HEAD" in r1[0][2], r1[0]


def test_the_layer_test_must_cover_the_linked_worktree_and_a_subdirectory() -> None:
    """F3 / R4: a primary-checkout-only suite has not tested this contract."""
    section = _section_text()
    flowed = _flowed()
    assert "git worktree add -q ../wt -b probe" in section
    assert "still a **file**" in section
    assert "**executes** the hook" in flowed
    assert "never in `<parent-of-repo>/.git/hooks`" in section
    assert "worktree test is a review failure" in flowed


def test_the_ruling_is_recorded_as_a_decision() -> None:
    decisions = (REPO_ROOT / "docs" / "Team" / "Decisions.md").read_text(encoding="utf-8")
    entry = decisions.split("## D-20261020-Architect-8", 1)
    assert len(entry) == 2, "the D-0001 ruling has no Decisions.md entry"
    body = entry[1].split("\n## ", 1)[0]
    for clause in ("R1", "R2", "R3", "R4", "R5", "R6", "falsified by", "evidence"):
        assert clause in body, f"the ruling entry does not carry {clause}"


# --- the git facts the frozen resolver and the mandatory tests rest on ------- #


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(("git", *args), cwd=cwd, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _hermetic_repo(tmp_path: Path) -> tuple:
    """A disposable repository plus one linked worktree, no network, no config."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "probe@example.invalid")
    _git(repo, "config", "user.name", "Probe")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "one")
    _git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "-b", "probe")
    return repo, tmp_path / "wt"


def test_the_documented_resolver_answers_from_a_linked_worktree(tmp_path: Path) -> None:
    """R2/R3 measured on git itself: the answer is the PRIMARY repository's hooks."""
    repo, wt = _hermetic_repo(tmp_path)
    assert (wt / ".git").is_file(), "a linked worktree's .git must be a gitfile"
    assert (wt / ".git" / "hooks").exists() is False
    assert _git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks") == (
        _git(wt, "-C", ".", "rev-parse", "--path-format=absolute", "--git-path", "hooks")
    )
    assert _git(wt, "rev-parse", "--path-format=absolute", "--git-path", "hooks") == str(
        repo / ".git" / "hooks"
    )
    assert _git(wt, "rev-parse", "--show-toplevel") == str(wt)


def test_the_pin_is_what_keeps_a_relative_answer_inside_this_repository(
    tmp_path: Path,
) -> None:
    """R2: without `-C <root>` the relative answer resolves into the PARENT repo."""
    repo, _wt = _hermetic_repo(tmp_path)
    subdir = repo / "scripts"
    subdir.mkdir()
    unpinned = _git(subdir, "rev-parse", "--git-path", "hooks")
    assert unpinned == "../.git/hooks", unpinned
    joined = Path(_git(repo, "rev-parse", "--show-toplevel"), unpinned).resolve()
    assert joined != (repo / ".git" / "hooks").resolve(), "the pin is not observable here"
    assert joined == (tmp_path / ".git" / "hooks").resolve(), joined


def test_core_hooks_path_is_honoured_by_the_resolver_and_not_special_cased(
    tmp_path: Path,
) -> None:
    """R5: git computes the answer, so a configured hooksPath needs no branch."""
    repo, _wt = _hermetic_repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    assert _git(
        repo, "-c", f"core.hooksPath={elsewhere}", "rev-parse", "--git-path", "hooks"
    ) == str(elsewhere)


def test_a_hook_in_the_resolved_directory_executes_from_the_linked_worktree(
    tmp_path: Path,
) -> None:
    """R4(c): the ruling's core fact - one directory, written once, executed there."""
    repo, wt = _hermetic_repo(tmp_path)
    hooks = repo / ".git" / "hooks"
    probe = hooks / "pre-commit"
    probe.write_text("#!/bin/sh\necho HOOK-RAN\n", encoding="utf-8")
    probe.chmod(0o755)
    (wt / "b.txt").write_text("two\n", encoding="utf-8")
    _git(wt, "add", "b.txt")
    result = subprocess.run(
        ("git", "commit", "-m", "two"), cwd=wt, capture_output=True, text=True, check=False
    )
    assert "HOOK-RAN" in result.stdout + result.stderr


def test_an_unborn_branch_is_readable_only_through_symbolic_ref(tmp_path: Path) -> None:
    """A3: the root commit is the case `rev-parse --abbrev-ref HEAD` cannot answer."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    _git(fresh, "init", "-q", ".")
    assert _git(fresh, "symbolic-ref", "--short", "HEAD") == "main"
    abbrev = subprocess.run(
        ("git", "rev-parse", "--abbrev-ref", "HEAD"),
        cwd=fresh,
        capture_output=True,
        text=True,
        check=False,
    )
    assert abbrev.returncode != 0, "an unborn HEAD must not look like a resolvable branch"
    assert abbrev.stdout.strip() == "HEAD"


# --------------------------------------------------------------------------- #
# 11.4 / 11.8 the lint output and exit-code contract
# --------------------------------------------------------------------------- #


def test_the_lint_rules_and_their_order_are_frozen() -> None:
    section = _section_text()
    order = ["IDENTITY", "TRIGGER", "SUBCOMMAND", "HELPER", "EVIDENCE"]
    positions = [section.index(rule) for rule in order]
    assert positions == sorted(positions), "the lint rules must stay in their frozen order"


def test_the_exit_codes_are_frozen_for_the_new_surface() -> None:
    section = _section_text()
    assert "argparse usage error only" in section, "code 2 must stay argparse-only"
    assert "a hook refusal (R1, R2, P1, P2)" in section, "hook refusals are code 1"


# --------------------------------------------------------------------------- #
# 11.9 the CLI must register what the contract freezes
# --------------------------------------------------------------------------- #


def test_the_three_groups_land_atomically() -> None:
    """Atomicity is PER GROUP: a landed group is whole, an absent one is reported.

    Architecture 11.9 freezes the landing per group, not across the three, so a
    revision that ships `hooks` + `hook` while `harness` is still pending is
    legal - which lane lands first is not this contract's business. What is
    forbidden is half of one group: a `hooks` group without `uninstall`, or
    `harness list` without `harness budget`.
    """
    choices = _top_level_choices()
    landed = [group for group in GROUP if group in choices]
    absent = [group for group in GROUP if group not in choices]
    for group in landed:
        gaps = _group_gaps(group)
        assert gaps == [], (
            f"the `{group}` group is registered but half-landed; frozen and missing: {gaps}"
        )
    print(f"groups landed: {landed or 'none'} | NOT LANDED: {absent or 'none'}")


def test_the_parser_registers_what_the_contract_freezes() -> None:
    """Every documented verb, flag, positional - for each group that has landed.

    A group this revision has not shipped is reported as NOT LANDED and skipped,
    not failed: 11.9's atomicity is per group. `hook` and `hooks` are two
    subcommands, not one aliased over the other: an agent-facing group and git's
    entry point must never share a parser.
    """
    choices = _top_level_choices()
    landed = [group for group in GROUP if group in choices]
    absent = [group for group in GROUP if group not in choices]
    if "hook" in landed and "hooks" in landed:
        assert choices["hook"] is not choices["hooks"], "`hook` and `hooks` must not share a parser"
    for group in landed:
        gaps = _group_gaps(group)
        assert gaps == [], f"the `{group}` group is documented but not fully registered: {gaps}"
    print(f"walked: {landed or 'none'} | NOT LANDED: {absent or 'none'}")
