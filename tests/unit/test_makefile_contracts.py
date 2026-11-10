"""The Makefile runs the same gates CI runs, and `make help` sees every target.

Why this exists: `Makefile` is the documented local entry point ("Run `make help`
for the target list") and `.github/workflows/ci.yml` is the gate that blocks a
merge. When the two drift, a developer who runs `make release-check` before
pushing is told the tree is green while CI runs a *different* command and fails,
and nothing reports the drift because each file is individually correct.

The comparison is programmatic and precise about identity. `$(PYTHON)`,
`python3` and `.venv/bin/python` are the same interpreter, so a gate is identified
by the script or module it invokes (`python -m ruff check .` -> `ruff check`,
`python scripts/privacy_scan.py ...` -> `privacy_scan.py`), not by the flags or
the interpreter spelling. Only Python invocations count as gates - that is what
this repository's gates are - and a separate test asserts that *every* gating CI
job contributes at least one recognised gate, so a new job that used another
tool would fail loudly instead of being skipped silently.

Shell snippets are read with `shlex` (quote-aware), so a `|` inside a quoted regex
is not mistaken for a pipeline, and heredoc bodies (`<<'PY'`) are skipped whole.
`scope` is a path classifier, not a gate, and is excluded by name - the exclusion
is asserted to be the only one.

Most of this file is static: it reads the two files and compares parsed
invocations. Only `make help` needs GNU make installed, so only that test guards
on the tool (`require_tool("make")`) and the rest keeps running on a host
without it - a guard is a skip that names the tool, never a weakened assertion.

Mutations edit the *text* of the Makefile / workflow in a `tmp_path` tree or in
memory and re-run the same comparison, so no tracked file is ever written.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

from tests.tooling import require_tool
from workflow_yaml import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = "Makefile"
CI_PATH = ".github/workflows/ci.yml"

#: Jobs that run no gate. `scope` only classifies the changed paths.
NON_GATE_JOBS = {"scope"}

#: Shell words that begin a line which is not a gate invocation.
SHELL_WORDS = {
    "set",
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "for",
    "do",
    "done",
    "case",
    "esac",
    "while",
    "until",
    "export",
    "local",
    "read",
    "return",
    "break",
    "continue",
    "echo",
    "printf",
    "cat",
    "mkdir",
    "mktemp",
    "cd",
    "test",
    "[",
    "[[",
    "exit",
    "wait",
    "true",
    "false",
    "touch",
    "chmod",
    "git",
    "grep",
    "sed",
    "awk",
    "sort",
    "head",
    "tail",
    "cut",
    "tr",
    "wc",
    "xargs",
    "rm",
    "cp",
    "mv",
    "ls",
    "diff",
    "tee",
    "basename",
    "dirname",
    "readlink",
    "command",
    "which",
}

#: Module-style tools whose subcommand is part of the identity.
SUBTYPED_MODULES = {"ruff", "mypy", "pytest", "mkdocs", "build", "unittest", "sphinx"}

#: Modules that install things rather than check them.
SETUP_MODULES = {"pip", "wheel", "setuptools", "ensurepip", "venv", "virtualenv"}

#: Tools CI and the Makefile invoke directly (`ruff check .`, not `python -m ruff`).
DIRECT_TOOLS = {"ruff", "mypy", "pytest", "mkdocs", "coverage", "shellcheck", "actionlint"}

TARGET_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+):(?!=)\s*(?P<rest>.*)$")


def normalise(word: str) -> str:
    return word.replace("$(PYTHON)", "python3").replace("${PYTHON}", "python3")


def is_interpreter(word: str) -> bool:
    stem = Path(normalise(word)).name
    return stem in {"python", "python3", "py"} or bool(re.fullmatch(r"python3\.\d+", stem))


def signature(argv: list[str]) -> tuple[str, ...] | None:
    """The identity of a gate invocation, or None when the command is not a gate.

    Identity = the script or module invoked (+ its subcommand for tools where the
    subcommand is a separate gate, e.g. `ruff check` vs `ruff format`).
    """
    argv = [normalise(word) for word in argv if word]
    while argv and "=" in argv[0] and not argv[0].startswith("-"):
        argv.pop(0)  # leading VAR=value assignment
    while argv and argv[0] in {"sudo", "env"}:
        argv.pop(0)
    if not argv or Path(argv[0]).name in SHELL_WORDS:
        return None
    if not is_interpreter(argv[0]):
        tool = Path(argv[0]).name
        if tool not in DIRECT_TOOLS:
            return None
        rest = [word for word in argv[1:] if not word.startswith("-")]
        return (tool, rest[0]) if tool in SUBTYPED_MODULES and rest else (tool,)
    if len(argv) < 2:
        return None
    if argv[1] == "-m":
        if len(argv) < 3:
            return None
        module = argv[2]
        if module in SETUP_MODULES:
            return None
        rest = [word for word in argv[3:] if not word.startswith("-")]
        if module in SUBTYPED_MODULES and rest:
            return (module, rest[0])
        return (module,)
    if argv[1].startswith("-"):
        return None  # `python -` is a stdin heredoc body, not a gate
    script = Path(argv[1]).name
    return (script,) if script.endswith(".py") else None


ASSIGNMENT_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")


def split_commands(snippet: str) -> list[list[str]]:
    """Split a shell snippet into argv lists, honouring quotes, heredocs and `X=y`."""
    out: list[list[str]] = []
    variables: dict[str, str] = {}
    heredoc: str | None = None
    for raw in snippet.splitlines():
        line = raw.strip()
        if heredoc is not None:
            if line == heredoc:
                heredoc = None
            continue
        marker = re.search(r"<<-?\s*'?([A-Za-z_]+)'?", line)
        if marker:
            heredoc = marker.group(1)
            line = line[: marker.start()]
        line = re.sub(r"\s+#\s.*$", "", line).rstrip("\\").strip()
        if not line or line.startswith("#"):
            continue
        assignment = ASSIGNMENT_RE.match(line)
        if assignment:
            value = assignment.group("value").strip().strip("'\"")
            if value and not value.startswith("$(") and " " not in value:
                variables[assignment.group("name")] = value
            continue
        for name, value in variables.items():
            line = line.replace("${" + name + "}", value).replace("$" + name, value)
        lexer = shlex.shlex(line, posix=True, punctuation_chars="|&;")
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError:
            continue
        current: list[str] = []
        for token in tokens:
            if token and set(token) <= set("|&;"):
                if current:
                    out.append(current)
                current = []
            else:
                current.append(token)
        if current:
            out.append(current)
    return out


def makefile_text(repo_root: Path = REPO_ROOT) -> str:
    return (repo_root / MAKEFILE).read_text(encoding="utf-8")


def make_targets(text: str) -> dict[str, list[str]]:
    """target -> its recipe lines."""
    targets: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        if raw.startswith("\t"):
            if current is not None:
                targets[current].append(raw.strip())
            continue
        match = TARGET_RE.match(raw)
        if match and not raw.startswith("."):
            name = match.group("name")
            current = name
            prerequisites = match.group("rest").split("##", 1)[0].split()
            targets.setdefault(name, []).extend(prerequisites)
        elif not raw.strip():
            current = None
    return targets


def phony_targets(text: str) -> set[str]:
    joined = re.sub(r"\\\n\s*", " ", text)
    names: set[str] = set()
    for line in joined.splitlines():
        if line.startswith(".PHONY:"):
            names.update(line.split(":", 1)[1].split())
    return names


def documented_targets(text: str) -> set[str]:
    return set(re.findall(r"(?m)^([A-Za-z0-9_.-]+):.*?## ", text))


def make_signatures(text: str) -> dict[tuple, set]:
    """gate signature -> the Makefile targets whose recipe invokes it."""
    found: dict[tuple, set] = {}
    for name, recipe in make_targets(text).items():
        for line in recipe:
            if line.startswith("@"):
                line = line[1:].strip()
            for argv in split_commands(line):
                sig = signature(argv)
                if sig:
                    found.setdefault(sig, set()).add(name)
    return found


def job_run_snippets(workflow: dict, skip: set[str] = NON_GATE_JOBS) -> dict[str, list[str]]:
    """job name -> every `run:` shell snippet in that job's steps."""
    out: dict[str, list[str]] = {}
    for name, job in (workflow.get("jobs") or {}).items():
        if name in skip:
            continue
        snippets: list[str] = []
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                snippets.append(step["run"])
        out[name] = snippets
    return out


def ci_gates(repo_root: Path = REPO_ROOT) -> dict[str, set[tuple]]:
    """job name -> the gate signatures that job runs."""
    workflow = parse_workflow((repo_root / CI_PATH).read_text(encoding="utf-8"))
    gates: dict[str, set[tuple]] = {}
    for job, snippets in job_run_snippets(workflow).items():
        found: set[tuple] = set()
        for snippet in snippets:
            for argv in split_commands(snippet):
                sig = signature(argv)
                if sig:
                    found.add(sig)
        gates[job] = found
    return gates


def all_ci_gates(repo_root: Path = REPO_ROOT) -> set[tuple]:
    return {sig for sigs in ci_gates(repo_root).values() for sig in sigs}


def uncovered_gates(repo_root: Path = REPO_ROOT) -> list[tuple]:
    """Gate signatures CI runs that no Makefile target invokes."""
    covered = set(make_signatures(makefile_text(repo_root)))
    return sorted(sig for sig in all_ci_gates(repo_root) if sig not in covered)


# --------------------------------------------------------------------------- #
# the real tree
# --------------------------------------------------------------------------- #


def test_every_gate_command_ci_runs_has_a_makefile_target():
    assert uncovered_gates() == []


def test_no_gating_job_runs_a_command_this_comparison_cannot_see():
    """Anti-vacuity: a job whose gate is invisible would pass the parity check free."""
    gates = ci_gates()
    assert set(gates) == {
        "lint",
        "committer-guard",
        "typecheck",
        "test",
        "build",
        "privacy",
        "release-consistency",
        "docs",
    }, f"unexpected gating job set: {sorted(gates)}"
    for job, sigs in gates.items():
        assert sigs, f"{job} runs no recognised gate, so its parity is never checked"


def test_the_comparison_sees_the_gates_the_tree_actually_has():
    gates = all_ci_gates()
    for expected in (
        ("ruff", "check"),
        ("ruff", "format"),
        ("mypy", "src/teamwork"),
        ("pytest",),
        ("verify_release.py",),
        ("privacy_scan.py",),
        ("teamwork.py",),
        ("mkdocs", "build"),
    ):
        assert expected in gates, f"{expected} not recognised in {sorted(gates)}"
    covered = set(make_signatures(makefile_text()))
    assert len(covered) >= 10, f"the Makefile half of the comparison found only {sorted(covered)}"


def test_interpreter_spellings_are_one_identity():
    """`$(PYTHON)`, `python3` and `.venv/bin/python` must not look like two gates."""
    spellings = [
        ["$(PYTHON)", "-m", "ruff", "check", "."],
        ["python3", "-m", "ruff", "check", "."],
        [".venv/bin/python", "-m", "ruff", "check", "."],
    ]
    assert {signature(argv) for argv in spellings} == {("ruff", "check")}


def test_the_subcommand_is_part_of_the_identity():
    """`ruff check` and `ruff format --check` are different gates."""
    assert signature(["python", "-m", "ruff", "check", "."]) != signature(
        ["python", "-m", "ruff", "format", "--check", "."]
    )
    assert signature(["python", "-m", "ruff", "format", "--check", "."]) == ("ruff", "format")


def test_every_phony_target_exists():
    text = makefile_text()
    declared = phony_targets(text)
    assert declared, ".PHONY declares nothing"
    assert sorted(declared - set(make_targets(text))) == []


def test_every_gate_target_is_declared_phony():
    """A gate target shadowed by a file of the same name would silently do nothing."""
    text = makefile_text()
    targets = set(make_targets(text))
    covered = {target for names in make_signatures(text).values() for target in names}
    gate_targets = {
        "lint",
        "typecheck",
        "test",
        "build",
        "verify",
        "privacy",
        "links",
        "identity",
        "release-consistency",
        "docs",
    }
    assert gate_targets <= targets, f"a gate target disappeared: {gate_targets - targets}"
    assert gate_targets <= covered, f"a gate target no longer runs a gate: {gate_targets - covered}"
    assert gate_targets <= phony_targets(text), (
        f"gate target not phony: {gate_targets - phony_targets(text)}"
    )


def test_the_makefile_documents_enough_targets():
    """The static half of the `help` contract: no tool needed, so no guard.

    Kept separate from the executing half below, or a host without GNU make
    would skip this assertion for a reason that has nothing to do with it.
    """
    documented = documented_targets(makefile_text())
    assert len(documented) >= 20, f"only {len(documented)} documented target(s)"


def test_make_help_lists_every_documented_target():
    """`make help` lists exactly the documented targets - needs GNU make."""
    require_tool("make")
    text = makefile_text()
    documented = documented_targets(text)
    result = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    listed = {
        line.split()[0] for line in plain.splitlines() if line.startswith("  ") and line.split()
    }
    assert documented - listed == set(), f"documented but not listed: {sorted(documented - listed)}"
    assert listed - documented == set(), f"listed but not documented: {sorted(listed - documented)}"


def test_release_check_chains_the_gates_it_claims():
    """`release-check` is what a developer trusts before pushing; list it truthfully."""
    recipe = make_targets(makefile_text())["release-check"]
    for gate in (
        "lint",
        "test",
        "selftest",
        "sync-check",
        "verify",
        "release-consistency",
        "privacy",
        "docs",
        "links",
        "identity",
    ):
        assert gate in recipe, f"release-check no longer runs {gate}: {recipe}"


# --------------------------------------------------------------------------- #
# The advertised release gate must be runnable after a plain `make dev`
# --------------------------------------------------------------------------- #

#: Module -> the distribution that provides it. A module the gate runs but this
#: map does not name fails the test below, so a new gate cannot slip past the
#: installability claim by being unknown.
MODULE_DISTRIBUTIONS = {
    "pytest": "pytest",
    "ruff": "ruff",
    "mypy": "mypy",
    "build": "build",
    "mkdocs": "mkdocs-material",
}

#: Modules that install things rather than check them; never a gate.
INSTALL_MODULES = {"pip", "wheel", "setuptools", "ensurepip", "venv", "virtualenv"}

REQUIREMENT_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<spec>.*)$")


def distribution(name: str) -> str:
    """PEP 503 normalisation: `MkDocs_Material` and `mkdocs-material` are one name."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def requirement_specs(entries: list[str]) -> dict[str, str]:
    """distribution -> its version specifier, from requirement strings or file lines."""
    specs: dict[str, str] = {}
    for entry in entries:
        entry = entry.split("#", 1)[0].strip()
        if not entry:
            continue
        match = REQUIREMENT_RE.match(entry)
        if match:
            specs[distribution(match.group("name"))] = match.group("spec").strip()
    return specs


def dev_extra_requirements(repo_root: Path = REPO_ROOT) -> list[str]:
    """The `dev` extra's requirement strings, read without a TOML dependency."""
    text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    table = re.search(r"(?ms)^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[)", text)
    assert table, "pyproject.toml no longer declares [project.optional-dependencies]"
    extra = re.search(r"(?ms)^dev\s*=\s*\[(.*?)^\]", table.group(1))
    assert extra, "pyproject.toml no longer declares a dev extra"
    return re.findall(r'"([^"]+)"', extra.group(1))


def prerequisite_closure(text: str, target: str = "release-check") -> set[str]:
    """`target` plus every target it depends on, transitively."""
    targets = make_targets(text)
    seen: set[str] = set()
    stack = [target]
    while stack:
        name = stack.pop()
        if name in seen or name not in targets:
            continue
        seen.add(name)
        stack.extend(prereq for prereq in targets[name] if prereq in targets)
    return seen


def modules_run_by(text: str, target: str = "release-check") -> set[str]:
    """Every `python -m <module>` a prerequisite of `target` invokes."""
    recipes = make_targets(text)
    modules: set[str] = set()
    for name in prerequisite_closure(text, target):
        for line in recipes[name]:
            for argv in split_commands(line.lstrip("@")):
                argv = [normalise(word) for word in argv]
                if len(argv) >= 3 and is_interpreter(argv[0]) and argv[1] == "-m":
                    if argv[2] not in INSTALL_MODULES:
                        modules.add(argv[2])
    return modules


def test_every_makefile_target_is_declared_phony():
    """A target shadowed by a file of the same name silently does nothing.

    `.PHONY` listed 20 of the 23 targets: `package`, `sync-skill` and `sync-check`
    were missing, so a directory called `package` (which `make package` creates)
    would have turned the target into a no-op.
    """
    text = makefile_text()
    undeclared = sorted(set(make_targets(text)) - phony_targets(text))
    assert undeclared == [], f"targets missing from .PHONY: {undeclared}"


def test_every_module_the_release_gate_runs_is_in_the_dev_extra():
    """`make dev` must install everything `make release-check` executes.

    `docs` is part of the gate but `mkdocs` was not in the `dev` extra, so the
    advertised one-shot local gate failed on a clean `make dev` checkout.
    """
    modules = modules_run_by(makefile_text())
    assert {"pytest", "ruff", "mkdocs"} <= modules, (
        f"the scan missed a gate module, so the claim is vacuous: {sorted(modules)}"
    )
    unknown = sorted(modules - set(MODULE_DISTRIBUTIONS))
    assert unknown == [], f"gate modules with no known distribution: {unknown}"
    dev = set(requirement_specs(dev_extra_requirements()))
    missing = sorted(MODULE_DISTRIBUTIONS[m] for m in modules if MODULE_DISTRIBUTIONS[m] not in dev)
    assert missing == [], f"`make release-check` runs modules `.[dev]` does not install: {missing}"


def test_the_docs_builder_range_is_the_one_docs_requirements_pins():
    """Two homes for one requirement is fine only while they cannot drift."""
    docs = requirement_specs((REPO_ROOT / "docs" / "requirements.txt").read_text().splitlines())
    dev = requirement_specs(dev_extra_requirements())
    assert "mkdocs-material" in docs, "docs/requirements.txt no longer pins the docs builder"
    assert dev.get("mkdocs-material") == docs["mkdocs-material"], (
        f"the dev extra pins {dev.get('mkdocs-material')!r} but docs/requirements.txt "
        f"pins {docs['mkdocs-material']!r}"
    )


# --------------------------------------------------------------------------- #
# mutants: break the parity and assert the comparison reports it
# --------------------------------------------------------------------------- #


def _tree(tmp_path: Path, makefile: str | None = None) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (tmp_path / CI_PATH).write_text(
        (REPO_ROOT / CI_PATH).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / MAKEFILE).write_text(makefile if makefile is not None else makefile_text(), "utf-8")
    return tmp_path


def test_mutant_a_dropped_gate_recipe_line_is_reported(tmp_path):
    line = (
        "\t$(PYTHON) scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt\n"
    )
    text = makefile_text()
    assert line in text, "the privacy gate recipe line was not found"
    problems = uncovered_gates(_tree(tmp_path, text.replace(line, "")))
    assert ("privacy_scan.py",) in problems, problems


def test_mutant_a_gate_pointed_at_another_script_is_reported(tmp_path):
    line = "\t$(PYTHON) scripts/verify_release.py\n"
    text = makefile_text()
    assert line in text, "the verify gate recipe line was not found"
    problems = uncovered_gates(
        _tree(tmp_path, text.replace(line, "\t$(PYTHON) scripts/sync_skill.py\n"))
    )
    assert ("verify_release.py",) in problems, problems


def test_mutant_a_phony_entry_without_a_target_is_reported():
    text = makefile_text().replace(".PHONY: help install", ".PHONY: help ghost-target install")
    assert sorted(phony_targets(text) - set(make_targets(text))) == ["ghost-target"]


def test_mutant_a_target_hidden_from_help_is_reported():
    """`make help` greps `##` markers; without one the target is invisible."""
    text = makefile_text().replace(
        "links: ## Check markdown links", "links: # Check markdown links"
    )
    assert text != makefile_text()
    assert "links" not in documented_targets(text)
    assert "links" in documented_targets(makefile_text())


def test_mutant_a_ci_gate_with_no_makefile_equivalent_is_reported(tmp_path):
    """The other direction: CI grows a gate the Makefile does not have."""
    anchor = "      - name: Link health (broken links, back-links)\n        run: python scripts/teamwork.py links\n"
    original = (REPO_ROOT / CI_PATH).read_text(encoding="utf-8")
    assert anchor in original, "the docs job anchor was not found"
    mutated = original.replace(
        anchor, anchor + "      - name: Extra gate\n        run: python scripts/ghost_gate.py\n"
    )
    tree = _tree(tmp_path)
    (tree / CI_PATH).write_text(mutated, encoding="utf-8")
    problems = uncovered_gates(tree)
    assert ("ghost_gate.py",) in problems, problems


def test_the_prose_regex_is_read_as_quoted_text_not_as_a_pipeline():
    """A `|` inside a quoted regex is not a command separator; splitting naively
    would invent gates (`assets`, `LICENSE$`) that no Makefile target could cover."""
    workflow = parse_workflow((REPO_ROOT / CI_PATH).read_text(encoding="utf-8"))
    assert "scope" not in job_run_snippets(workflow), "scope is a classifier, not a gate"
    scope_snippet = next(
        step["run"]
        for step in workflow["jobs"]["scope"]["steps"]
        if isinstance(step.get("run"), str) and "PROSE=" in step["run"]
    )
    prose_line = next(line for line in scope_snippet.splitlines() if "PROSE=" in line)
    assert "|" in prose_line
    naive = {token.strip("'\" ") for token in prose_line.split("|")}
    assert "assets" in {Path(token).name for token in naive}, "the fixture lost its pipe"
    assert all(signature(argv) is None for argv in split_commands(prose_line))
