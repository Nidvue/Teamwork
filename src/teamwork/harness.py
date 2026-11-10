"""The harness surface: its registry, its always-on budget and its lint.

Harness^2 names the *harness* around a frozen model as eight file-level
components, each with an activation class that says what it costs on every run.
This module does the same for this repository: the registry maps C1..C8 onto real
paths, and every byte count is measured on disk at run time, so a row cannot
drift from the tree it claims to describe.

``harness list`` is deliberately a table, not a diagram: one row per component -
never one per file, so the table can be read against the source taxonomy row by
row - with an activation class, a measured cost and the role that pays it. C5
(subagents) is the one component that is not a file - a lane packet is assembled
per task - so its class, byte and role cells are ``-`` and its path cell says so.

The path column is the specification the bytes were measured through, not a
short name for the component: ``AGENTS.md`` would not let a reader recompute the
managed block's size from a file that also holds text outside the block, and
``scripts/*.py`` alone would not explain a count that also sums
``src/teamwork/*.py``. Every cell is therefore the frozen spec of Architecture
12.2, so ``wc -c`` over what the row names reproduces the number printed beside
it.

``harness lint`` is the whole-proposal invalidator. A skill that no always-on
file names is silently dead, a ``teamwork.py <word>`` the CLI does not implement
is a broken instruction, and a referenced path that was never shipped sends the
reader to nowhere. Each of those is a fact about the tree, so each is checked
mechanically instead of being trusted to review.

The always-on budget is the cost doctrine made measurable: SKILL.md, the managed
teamwork block of AGENTS.md, the role charter and the role's memory files are in
context on every run, so they are the expensive option and the only one capped.
``AlwaysOnBudgetKb`` in the team ``Settings.json`` sets the cap; missing,
unreadable or non-numeric settings fall back to
:data:`teamwork.config.DEFAULT_ALWAYS_ON_BUDGET_KB`.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import NamedTuple

from .config import (
    DEFAULT_ALWAYS_ON_BUDGET_KB,
    DIR_AGENTS,
    DIR_ROLES,
    F_GLOBAL,
    F_LONG,
    F_ROLE,
    F_SETTINGS,
    F_SHORT,
)
from .gitutil import run_git
from .io import die
from .layout import (
    global_dir,
    known_instances,
    list_roles,
    project_of,
    project_path,
    project_root,
    role_dir,
    skills_path,
)
from .names import resolve_role
from .records import parse_skills

#: The three activation classes (12.3), cheapest to reason about first: always-on
#: text is in context on every call, on-demand text is opened when a skill or a
#: reference is needed, and in-loop code runs inside the tool loop.
ALWAYS_ON = "always-on"
ON_DEMAND = "on-demand"
IN_LOOP = "in-loop"
CLASSES = (ALWAYS_ON, ON_DEMAND, IN_LOOP)

NO_VALUE = "-"

#: C5 is an inference context, not an artifact: it has no file, so its class, byte
#: and role cells are ``-`` (12.2: ``-`` is the value for the component with no
#: file) and its path cell says what it is instead of naming a path.
LANE_PACKET = "n/a - lane packet, no file"

#: The closed set of values the class column may print: the three activation
#: classes plus `-`, the one component that is an inference context, not a file.
CLASS_CELLS = CLASSES + (NO_VALUE,)

#: The path column, verbatim from the frozen registry table of Architecture 12.2.
#: Each string is the spec the row's bytes are measured through, so the number can
#: be recomputed from the cell alone: the managed block (not the file that holds
#: it), the union of both globs (not one member of it), both hook stages
#: through the resolver (not one file under a path that does not exist in a
#: worktree). A prettier spelling would describe the component and hide the
#: measurement, which is the defect this column exists to prevent.
SPEC_SYSTEM_PROMPT = "SKILL.md"
SPEC_GUARDRAILS = "managed block in AGENTS.md"
SPEC_MEMORY = "Roles/<Role>/*.md + Global/GlobalMemory.md"
SPEC_TOOL_GUIDANCE = "references/*.md"
SPEC_SKILLS = ".agents/skills/*/SKILL.md"
SPEC_SCRIPTS = "scripts/*.py + src/teamwork/*.py"
SPEC_HOOKS = "hook_dir(root)/{pre-commit,pre-push}"

#: The two stages the `hooks` command group writes; C8 measures both.
HOOK_STAGES = ("pre-commit", "pre-push")

RULE_IDENTITY = "IDENTITY"
RULE_TRIGGER = "TRIGGER"
RULE_SUBCOMMAND = "SUBCOMMAND"
RULE_HELPER = "HELPER"
RULE_EVIDENCE = "EVIDENCE"
RULES = (RULE_IDENTITY, RULE_TRIGGER, RULE_SUBCOMMAND, RULE_HELPER, RULE_EVIDENCE)

SKILLS_DIRNAME = Path(".agents") / "skills"

#: The four verdicts an evidence row may carry. ``NO_ENTRY`` - no row at all - is a
#: valid answer for a draft skill and only becomes a failure once it is shared.
VERDICT_RE = re.compile(
    r"verdict:\s*(?:helped|hurt|no\s+observed\s+effect|confounded)\b",
    re.IGNORECASE,
)

_COMMAND_RE = re.compile(r"teamwork\.py\s+([a-z][a-z0-9_-]*)")

#: A token that looks like a repository-relative path: at least two segments and a
#: file extension. The lookbehind keeps URL host names (``https://host/a/b.md``)
#: and shell-variable roots (``$SKILL/scripts/x.py``) out: their existence cannot
#: be decided from the repository, so the match may not start mid-token.
_PATH_RE = re.compile(
    r"(?<![\w/.$-])([A-Za-z0-9_][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*\.[A-Za-z][A-Za-z0-9]{0,7})"
)

#: Characters that make a path token a template, a glob or a shell variable rather
#: than a file the skill promises to ship.
_PLACEHOLDER_CHARS = ("<", ">", "{", "}", "$", "*", "?", "~")


class Surface(NamedTuple):
    """One registry row. ``size`` is ``None`` when the surface is not a file."""

    component: str
    klass: str
    path: str
    role: str
    size: int | None


class Finding(NamedTuple):
    """One lint failure, rendered as ``- PROBLEM <rule> <path>: <detail>``."""

    rule: str
    path: str
    detail: str


#: What one rule said about one file, for ``lint --verbose``. ``ok``/``fail`` are
#: verdicts; ``corpus`` marks a file read as evidence for a rule that reasons over
#: several files at once (TRIGGER reads every always-on surface, EVIDENCE reads the
#: team registry); ``n/a`` marks a rule that does not apply to that file; ``skipped``
#: marks a rule that could not run at all.
OK = "ok"
FAIL = "fail"
CORPUS = "corpus"
NOT_APPLICABLE = "n/a"
SKIPPED = "skipped"


class CheckedFile(NamedTuple):
    """One file ``lint`` opened, with the rules evaluated against it and the verdicts."""

    path: str
    outcomes: tuple


class LintStats(NamedTuple):
    """What the last lint actually looked at, for ``--verbose`` and for tests."""

    repo: str
    skills: int
    always_on: list[str]
    commands: int
    shared_checked: int
    registry: str
    checked: list[CheckedFile]


class BudgetRow(NamedTuple):
    """One instance's always-on cost against the cap."""

    instance: str
    always_on: int
    budget: int

    @property
    def over(self) -> bool:
        return self.always_on > self.budget


# --------------------------------------------------------------------------- #
# Measuring the tree
# --------------------------------------------------------------------------- #


def repo_root(args) -> Path:
    """The work tree the command acts on: the git toplevel, else the project dir."""
    here = project_path(args)
    result = run_git(here, "rev-parse", "--show-toplevel")
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return here


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def glob_size(base: Path, pattern: str) -> int:
    """Bytes of every file ``base/pattern`` matches right now; no match is 0."""
    try:
        matches = sorted(base.glob(pattern))
    except OSError:  # pragma: no cover - only an unreadable directory gets here
        return 0
    return sum(file_size(path) for path in matches if path.is_file())


def managed_block_size(path: Path) -> int:
    """Bytes of the CEO-owned teamwork block inside AGENTS.md, markers included.

    The markers are the engine's own pair (`agents-md` writes them): a second copy
    of a marker literal is a second source of truth.
    """
    from . import engine  # local: the command layer registers this module

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    start = text.find(engine.BEGIN)
    end = text.find(engine.END)
    if start < 0 or end < start:
        return 0
    return len(text[start : end + len(engine.END)].encode("utf-8"))


def hooks_dir(repo: Path) -> Path | None:
    """``<git-dir>/hooks``, resolved through git so a worktree finds the shared one."""
    result = run_git(repo, "rev-parse", "--git-path", "hooks")
    if result.returncode != 0 or not result.stdout.strip():
        return None
    located = Path(result.stdout.strip())
    return located if located.is_absolute() else repo / located


def display(path: Path, base: Path) -> str:
    """A repo-relative path when it is inside the base, else the absolute one."""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def collect(repo: Path, root: Path) -> list[Surface]:
    """The eight components, in C1..C8 order, measured on disk now.

    One row per Harness^2 component, never one per file: an inventory that splits a
    component across rows cannot be checked against the taxonomy it claims to
    describe. Each row's ``path`` is the frozen spec (Architecture 12.2) and
    ``size`` is what that spec selects at run time: C2 is the managed block inside
    AGENTS.md, C3 is every role's markdown plus the global memory, C7 is the
    scripts plus the engine package, C8 is both hook stages found through the git
    hook directory. Measuring something other than what the cell names would make
    the printed number unreproducible from the row, which is what the registry is
    for.
    """
    hooks = hooks_dir(repo)
    return [
        Surface("C1", ALWAYS_ON, SPEC_SYSTEM_PROMPT, "ceo", file_size(repo / "SKILL.md")),
        Surface(
            "C2",
            ALWAYS_ON,
            SPEC_GUARDRAILS,
            "ceo",
            managed_block_size(repo / "AGENTS.md"),
        ),
        Surface("C3", ALWAYS_ON, SPEC_MEMORY, NO_VALUE, memory_bytes(root)),
        Surface("C4", ON_DEMAND, SPEC_TOOL_GUIDANCE, "ceo", glob_size(repo, "references/*.md")),
        Surface("C5", NO_VALUE, LANE_PACKET, NO_VALUE, None),
        Surface(
            "C6",
            ON_DEMAND,
            SPEC_SKILLS,
            "ceo",
            glob_size(repo, ".agents/skills/*/SKILL.md"),
        ),
        Surface(
            "C7",
            IN_LOOP,
            SPEC_SCRIPTS,
            "developer",
            glob_size(repo, "scripts/*.py") + glob_size(repo, "src/teamwork/*.py"),
        ),
        Surface(
            "C8",
            IN_LOOP,
            SPEC_HOOKS,
            NO_VALUE,
            sum(file_size(hooks / stage) for stage in HOOK_STAGES) if hooks is not None else 0,
        ),
    ]


def memory_bytes(root: Path) -> int:
    """C3: every role's markdown plus the shared global memory of the team."""
    total = file_size(global_dir(root) / F_GLOBAL)
    for role in list_roles(root):
        total += glob_size(role_dir(root, role), "*.md")
    return total


#: A row's third cell is a spec, and the frozen specs contain single spaces
#: (``managed block in AGENTS.md``), so the cells are separated by two or more
#: spaces and split on that: ``split()`` would tear a spec in half.
_CELL_SEPARATOR_RE = re.compile(r"\s{2,}")


def render_surfaces(rows: list[Surface]) -> str:
    """Exactly eight rows, four columns, no header: the frozen registry format."""
    path_width = max([len(row.path) for row in rows] + [len("path")])
    class_width = max(len(row.klass) for row in rows)
    lines = []
    for row in rows:
        size = NO_VALUE if row.size is None else str(row.size)
        lines.append(f"{row.klass:<{class_width}}  {size:>9}  {row.path:<{path_width}}  {row.role}")
    return "\n".join(lines)


def parse_surface_row(line: str) -> tuple:
    """``(class, bytes, path, role)`` from one printed row - the inverse of render.

    The bytes cell stays a string (``-`` for C5): a caller that wants a number has
    to decide what ``-`` means, and pretending it is ``0`` would turn "not
    measured" into a measurement.
    """
    cells = _CELL_SEPARATOR_RE.split(line.strip())
    if len(cells) != 4:
        raise ValueError(f"not a four-column registry row: {line!r} -> {cells!r}")
    klass, size, path, role = cells
    return klass, size, path, role


def class_totals(rows: list[Surface]) -> dict:
    """Bytes per activation class, summed over the eight rows.

    The registry prints its eight rows and nothing else, so the cost roll-up a
    reader wants ("what does always-on cost me") is computed here rather than
    appended to the table the frozen format fixes.
    """
    return {klass: sum(row.size or 0 for row in rows if row.klass == klass) for klass in CLASSES}


# --------------------------------------------------------------------------- #
# lint: the whole-proposal invalidators
# --------------------------------------------------------------------------- #


def parse_frontmatter(text: str) -> dict:
    """The scalar fields of a leading ``---`` block; a repeated key wins last."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict = {}
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", raw)
        if match is None:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].strip()
        out[match.group(1).lower()] = value
    return out


def skill_files(repo: Path) -> list[Path]:
    """``.agents/skills/<dir>/SKILL.md`` - one skill per directory, none nested."""
    try:
        found = sorted((repo / SKILLS_DIRNAME).glob("*/SKILL.md"))
    except OSError:  # pragma: no cover
        return []
    return [path for path in found if path.is_file()]


def always_on_surfaces(repo: Path) -> list[Path]:
    """The files a skill name must appear in for the skill to be reachable."""
    names = [repo / "AGENTS.md", repo / "SKILL.md"]
    roles = repo / "roles"
    if roles.is_dir():
        names.extend(sorted(roles.glob("*.md")))
    return [path for path in names if path.is_file()]


def cli_subcommands() -> set:
    """Every ``teamwork.py <word>`` the parser actually accepts.

    Read off the parser, never copied: the scripts *are* the engine, so a
    hardcoded list would drift the first time a command is renamed.
    """
    from . import engine  # local: the command layer is what registers this module

    parser = engine.build_parser()
    names: set = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            names.update(action.choices)
    return names


def helper_paths(text: str) -> list[str]:
    """Repository-relative paths a skill file claims to ship, placeholders dropped."""
    out = set()
    for raw in _PATH_RE.findall(text):
        token = raw.strip("\"'`()[].,;:")
        if not token or any(char in token for char in _PLACEHOLDER_CHARS):
            continue
        if token.startswith(("/", "http", "www")) or "://" in token:
            continue
        if ".." in token.split("/"):
            continue
        out.add(token)
    return sorted(out)


def lint(repo: Path, root: Path) -> tuple[list[Finding], LintStats]:
    """Run every rule over the tree; return the findings and what was checked."""
    findings: list[Finding] = []
    surfaces = always_on_surfaces(repo)
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in surfaces)
    commands = cli_subcommands()
    files = skill_files(repo)
    registry = skills_path(root)
    has_registry = registry.is_file()

    # Files read for a rule that reasons across files rather than per file: the
    # always-on corpus TRIGGER searches, and the team registry EVIDENCE reads.
    checked: list[CheckedFile] = [
        CheckedFile(display(path, repo), ((RULE_TRIGGER, CORPUS),)) for path in surfaces
    ]

    evidence: list[Finding] = []
    evaluated: list[str] = []
    shared_checked = 0
    if has_registry:
        evidence, evaluated, shared_checked = evidence_findings(repo, registry)

    for path in files:
        rel = display(path, repo)
        text = path.read_text(encoding="utf-8")
        fields = parse_frontmatter(text)
        name = (fields.get("name") or "").strip()
        directory = path.parent.name
        mine: list[Finding] = []

        if not name:
            mine.append(Finding(RULE_IDENTITY, rel, "frontmatter has no `name:` line"))
        elif name != directory:
            mine.append(
                Finding(
                    RULE_IDENTITY,
                    rel,
                    f"frontmatter name '{name}' does not match the directory '{directory}'",
                )
            )
        if not (fields.get("description") or "").strip():
            mine.append(
                Finding(RULE_IDENTITY, rel, "frontmatter `description:` is missing or empty")
            )

        if directory and directory not in corpus:
            mine.append(
                Finding(
                    RULE_TRIGGER,
                    rel,
                    f"'{directory}' appears in no always-on surface "
                    "(AGENTS.md, SKILL.md, roles/*.md), so the skill is silently dead",
                )
            )

        for word in sorted(set(_COMMAND_RE.findall(text))):
            if word not in commands:
                mine.append(
                    Finding(RULE_SUBCOMMAND, rel, f"`teamwork.py {word}` is not a CLI subcommand")
                )

        for token in helper_paths(text):
            if not (repo / token).exists():
                mine.append(
                    Finding(RULE_HELPER, rel, f"references '{token}', which does not exist")
                )

        findings.extend(mine)
        checked.append(CheckedFile(rel, _outcomes(mine, rel, evidence, evaluated, has_registry)))

    findings.extend(evidence)
    if has_registry:
        checked.append(CheckedFile(display(registry, project_of(root)), ((RULE_EVIDENCE, CORPUS),)))

    findings = ordered(findings)
    stats = LintStats(
        repo=str(repo),
        skills=len(files),
        always_on=[display(path, repo) for path in surfaces],
        commands=len(commands),
        shared_checked=shared_checked,
        registry=display(registry, project_of(root)) if has_registry else "",
        checked=checked,
    )
    return findings, stats


def _outcomes(
    mine: list[Finding], rel: str, evidence: list[Finding], evaluated: list[str], has_registry: bool
) -> tuple:
    """The verdict of each rule on one skill file, in frozen rule order."""
    failed = {finding.rule for finding in mine}
    out = [(rule, FAIL if rule in failed else OK) for rule in RULES[:4]]
    if not has_registry:
        out.append((RULE_EVIDENCE, SKIPPED))
    elif rel not in evaluated:
        out.append((RULE_EVIDENCE, NOT_APPLICABLE))
    elif any(finding.path == rel for finding in evidence):
        out.append((RULE_EVIDENCE, FAIL))
    else:
        out.append((RULE_EVIDENCE, OK))
    return tuple(out)


def render_checked(checked: list[CheckedFile]) -> list[str]:
    """One ``# checked: <file> -> <RULE verdict, ...>`` line per file, rule order."""
    return [
        f"# checked: {item.path} -> "
        + ", ".join(f"{rule} {outcome}" for rule, outcome in item.outcomes)
        for item in checked
    ]


def ordered(findings: list[Finding]) -> list[Finding]:
    """Rule order first (IDENTITY..EVIDENCE), path order inside a rule."""
    rank = {rule: index for index, rule in enumerate(RULES)}
    return sorted(findings, key=lambda finding: (rank.get(finding.rule, len(rank)), finding.path))


def evidence_findings(repo: Path, registry: Path) -> tuple[list[Finding], list[str], int]:
    """EVIDENCE: a shared skill must carry an evidence row; a draft skill need not.

    Returns the findings, the paths the rule evaluated (shared entries, so
    ``--verbose`` can say which file was checked for what), and how many of them
    were readable skill files.
    """
    findings: list[Finding] = []
    evaluated: list[str] = []
    checked = 0
    for entry in parse_skills(registry):
        if (entry.get("status") or "").strip().lower() != "shared":
            continue
        rel = (entry.get("path") or "").strip()
        evaluated.append(rel or entry.get("name") or "?")
        skill = repo / rel if rel else None
        if skill is None or not skill.is_file():
            findings.append(
                Finding(
                    RULE_HELPER,
                    rel or entry.get("name") or "?",
                    "registered in Skills.md as shared, but the file does not exist",
                )
            )
            continue
        checked += 1
        if not VERDICT_RE.search(skill.read_text(encoding="utf-8")):
            findings.append(
                Finding(
                    RULE_EVIDENCE,
                    rel,
                    "shared skill has no evidence row "
                    "(`verdict: helped|hurt|no observed effect|confounded`)",
                )
            )
    return findings, evaluated, checked


# --------------------------------------------------------------------------- #
# budget: the always-on cap, per instance
# --------------------------------------------------------------------------- #


def settings_budget_kb(root: Path) -> int | None:
    """``AlwaysOnBudgetKb`` from the team settings, or ``None`` when unusable."""
    try:
        data = json.loads((root / F_SETTINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("AlwaysOnBudgetKb")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def charter_path(repo: Path, root: Path, role: str) -> Path:
    """The charter an instance actually reads: the team copy, else the bundle copy."""
    team_copy = role_dir(root, role) / F_ROLE
    return team_copy if team_copy.is_file() else repo / "roles" / f"{role}.md"


def instance_always_on(repo: Path, root: Path, role: str) -> int:
    """What is in context on every run for one instance, in bytes."""
    return (
        managed_block_size(repo / "AGENTS.md")
        + file_size(repo / "SKILL.md")
        + file_size(charter_path(repo, root, role))
        + file_size(role_dir(root, role) / F_SHORT)
        + file_size(role_dir(root, role) / F_LONG)
    )


def budget_rows(repo: Path, root: Path, limit_kb: int | None) -> tuple[list[BudgetRow], int, str]:
    """One row per agent instance, the cap in bytes, and where the cap came from."""
    configured = settings_budget_kb(root)
    if limit_kb is not None:
        kb, source = limit_kb, "--limit"
    elif configured is not None:
        kb, source = configured, "Settings.json AlwaysOnBudgetKb"
    else:
        kb, source = DEFAULT_ALWAYS_ON_BUDGET_KB, "default"
    cap = max(kb, 0) * 1024
    rows = [
        BudgetRow(instance, instance_always_on(repo, root, resolve_role(instance)), cap)
        for instance in known_instances(root)
    ]
    return rows, cap, source


def render_budget(rows: list[BudgetRow]) -> str:
    """``<instance> <always_on> <budget> <ok|OVER>`` per row, then the total line."""
    lines = [
        f"{row.instance} {row.always_on} {row.budget} {'OVER' if row.over else 'ok'}"
        for row in rows
    ]
    state = "OVER" if any(row.over for row in rows) else "ok"
    lines.append(
        f"total {sum(row.always_on for row in rows)} {sum(row.budget for row in rows)} {state}"
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def cmd_list(args) -> int:
    repo = repo_root(args)
    root = project_root(args)
    print(render_surfaces(collect(repo, root)))
    return 0


def cmd_lint(args) -> int:
    repo = repo_root(args)
    root = project_root(args)
    findings, stats = lint(repo, root)
    if args.verbose:
        print(f"# repo: {stats.repo}")
        print(f"# skill files: {stats.skills}")
        print(f"# cli subcommands: {stats.commands}")
        print(f"# always-on surfaces: {', '.join(stats.always_on) or '(none)'}")
        if stats.registry:
            print(f"# EVIDENCE: {stats.shared_checked} shared skill(s) checked")
        else:
            print("# EVIDENCE: skipped (no team workspace / no Skills.md)")
        # 12.4: --verbose also lists every file checked, so a clean run is
        # auditable file by file instead of being a count the reader must trust.
        for line in render_checked(stats.checked):
            print(line)
    for finding in findings:
        print(f"- PROBLEM {finding.rule} {finding.path}: {finding.detail}")
    print(f"# problems found: {len(findings)}")
    return 1 if findings else 0


def cmd_budget(args) -> int:
    repo = repo_root(args)
    root = project_root(args)
    if not (root / DIR_ROLES).is_dir() and not (root / DIR_AGENTS).is_dir():
        die(
            f"no team workspace at {root}: `harness budget` measures the always-on "
            "context every instance loads, so it needs `teamwork.py init` first."
        )
    rows, cap, source = budget_rows(repo, root, args.limit)
    print(f"# always-on budget for {root}")
    print(f"# cap: {cap} bytes per instance ({source})")
    if not rows:
        print("# no agent instances in this team yet")
    print(render_budget(rows))
    return 1 if any(row.over for row in rows) else 0


def add_parsers(sub, common) -> None:
    """Register the ``harness`` command group on the shared argparse tree."""
    surface = sub.add_parser(
        "harness",
        parents=[common],
        help="name, measure and lint the harness surface (Harness^2 C1..C8)",
    )
    hsub = surface.add_subparsers(dest="harness_cmd", required=True)

    parser = hsub.add_parser(
        "list", parents=[common], help="every surface with its class, bytes and role"
    )
    parser.set_defaults(func=cmd_list)

    parser = hsub.add_parser(
        "lint",
        parents=[common],
        help="whole-proposal checks: identity, trigger, subcommand, helper, evidence",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="print what was checked and what was skipped"
    )
    parser.set_defaults(func=cmd_lint)

    parser = hsub.add_parser(
        "budget", parents=[common], help="always-on bytes per instance against AlwaysOnBudgetKb"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="KB",
        help="override AlwaysOnBudgetKb for this run only",
    )
    parser.set_defaults(func=cmd_budget)
