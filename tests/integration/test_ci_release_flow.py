"""Integration: the ci-release surface, executed instead of read.

`tests/unit/test_ci_contracts.py` asserts the *shape* of `ci.yml` from its text,
and `tests/integration/test_ci_scope_classifier.py` runs the classifier on single
change sets. Two claims are still unproved there, and both are the kind that only
bites after a push:

1. **The prose set and the `docs.yml` trigger list are the same set.** A path that
   leaves one list without joining the other is a hole in one of the two gates:
   prose classified as code burns the 3x3 matrix, code classified as prose skips
   it. The unit side of this claim is a *paper* comparison: `test_skill_contracts`
   expands the `PROSE` alternation into globs and compares that pattern set with the
   globs in `docs.yml`'s `paths:` list - two lists that agree on paper can still
   disagree about a real path, and no unit test says what the shipped classifier
   prints. This module compares their *behaviour*: it materialises one real file per
   entry of the `docs.yml` list and per alternative of the `PROSE` regex the `scope`
   job carries, one real file per near-miss boundary, runs the shipped classifier on
   each single-path git change set, and requires the verdict to equal `docs.yml`'s
   answer in both directions. The probe set is built from the shipped files, never
   only from the pair under test, so an entry deleted from *either* side is still
   probed and reported. The comparison is then shown to bite: dropping one entry
   from either side must produce a named mismatch.
2. **Every command a workflow runs exists in the tree and is the real one.** A
   workflow that names a script or a flag the tree does not have fails only on
   the forge, on the revision that needed the gate. Here every repository path in
   every workflow `run:` block must resolve, every script must answer `--help`,
   every long flag a workflow passes to a repository script must be documented by
   that script, and the tool set the Makefile/CI gates invoke must resolve on this
   host (a skip naming the absent tool when it does not).

Owner: tester. Task: T-0001.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Same-directory import: `tests/integration` is a pytest rootdir entry (no
# `__init__.py`), so the sibling module is importable by name. Reusing it keeps
# one extractor for the shipped classifier instead of a second copy that drifts.
from test_ci_scope_classifier import (
    CI_WORKFLOW,
    REPO_ROOT,
    SCOPE_STEP,
    classify,
    commit,
    extract_run_block,
    new_repo,
    write_script,
)

DOCS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
WORKFLOWS = (CI_WORKFLOW, DOCS_WORKFLOW, RELEASE_WORKFLOW)
MAKEFILE = REPO_ROOT / "Makefile"


# --------------------------------------------------------------------------- #
# The docs.yml trigger list
# --------------------------------------------------------------------------- #


def docs_trigger_markers(text: str) -> list[str]:
    """The `paths:` entries under `push:` in a `docs.yml` text.

    Line-based on purpose: the file is YAML, but the only thing needed here is the
    literal list, and a YAML reader is not in the `dev` extra.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "paths:"), None)
    assert start is not None, "docs.yml: no `paths:` trigger list"
    key_indent = len(lines[start]) - len(lines[start].lstrip())
    markers: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if len(line) - len(line.lstrip()) <= key_indent:
            break
        if not stripped.startswith("- "):
            break
        markers.append(stripped[2:].strip().strip('"').strip("'"))
    assert markers, "docs.yml: the `paths:` trigger list is empty"
    return markers


def marker_matches(rel: str, marker: str) -> bool:
    """True when the changed path ``rel`` is covered by a `docs.yml` marker."""
    if marker.endswith("/**"):
        return rel.startswith(marker[: -len("/**")] + "/")
    return rel == marker


def sample_for_marker(marker: str) -> str:
    """A concrete changed path that the marker covers."""
    if marker.endswith("/**"):
        return marker[: -len("/**")] + "/probe/page.md"
    return marker


#: Paths that ship, or that the site does not read, so the matrix must run for
#: them. The near-misses (`docs-notes/`, `assets2/`, `LICENSE.md`) are the point:
#: they prove the two lists agree on the *boundary* of `docs/` and `assets/`, not
#: only on their members.
CODE_PROBES = (
    "src/teamwork/engine.py",
    "scripts/teamwork.py",
    "scripts/check_release_consistency.py",
    "tests/integration/probe.py",
    "tests/unit/probe.py",
    "tests/acceptance/probe.py",
    "tests/conftest.py",
    "Makefile",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "skills/probe",
    ".agents/skills/probe/SKILL.md",
    "roles/developer.md",
    "references/Evidence.md",
    "templates/project/AGENTS.md",
    "AGENTS.template.md",
    "LICENSE.md",
    "docs-notes/page.md",
    "assets2/logo.svg",
    "docsite/index.html",
)


#: The classifier states its prose set as one alternation in the `scope` job:
#: `PROSE='^(docs/|assets/|README\.md$|...|mkdocs\.yml$)'`. Reading the alternatives
#: back out of the shipped run block is what gives the comparison its prose side: an
#: entry deleted from `docs.yml` is *still* probed, as a path the classifier calls
#: prose and `docs.yml` no longer covers. A fixed tuple of probes cannot do this - it
#: would have to be edited by hand exactly when the list moved, which is the edit that
#: opens the hole.
PROSE_REGEX_RE = re.compile(r"PROSE='(?P<regex>[^']*)'")


def prose_alternatives(ci_text: str) -> list[str]:
    """The alternatives of the `PROSE` regex the shipped `scope` job carries."""
    match = PROSE_REGEX_RE.search(ci_text)
    assert match is not None, "ci.yml: the scope job no longer states a `PROSE` regex"
    body = match.group("regex").strip()
    # A whole-path alternation is written `^(a|b|c)$`; peel the anchors before
    # splitting, without assuming the parens are there.
    if body.startswith("^(") and body.endswith(")$"):
        body = body[2:-2]
    elif body.startswith("^") and body.endswith("$"):
        body = body[1:-1]
    alternatives = [alt for alt in body.split("|") if alt]
    assert alternatives, "ci.yml: the `PROSE` regex has no alternatives"
    return alternatives


def sample_for_prose(alternative: str) -> str:
    """A concrete changed path that one `PROSE` alternative matches."""
    if alternative.endswith("/"):
        return alternative + "probe/page.md"
    return alternative.rstrip("$").replace("\\.", ".")


def verdict(tmp_path: Path, repo: Path, script: Path, before: str, head: str) -> str:
    """Run the classifier for one change set and return ``code``'s value.

    ``$GITHUB_OUTPUT`` is written *outside* the repository on purpose: the fixture
    commit stages every path with ``git add -A``, so a sink inside the work tree
    would be committed and would turn the next change set into a two-path diff - a
    defect in the harness that reads exactly like a defect in the classifier.
    """
    sink = tmp_path / "github-output.txt"
    return classify(repo, script, before=before, head=head, output_name=str(sink))["code"]


def mismatch_report(
    tmp_path: Path,
    *,
    ci_text: str | None = None,
    docs_text: str | None = None,
    only: tuple[str, ...] | None = None,
) -> list[str]:
    """Compare the classifier's verdict with `docs.yml`'s answer for every probe.

    The trigger side comes from the `docs.yml` text under test; the prose side is
    read out of the *shipped* `ci.yml` run block. Probing both sources is the point:
    the shipped prose list still names an entry that a real edit removed from
    `docs.yml`, so the removed path is probed and the disagreement is named.
    Deriving the probe set from the file under test alone, or from a fixed tuple of
    code paths, lets a deletion pass silently - exactly the hole this module exists
    to close.

    ``ci_text`` / ``docs_text`` default to the shipped files and exist so a mutant
    can be fed in. ``only`` narrows the probe set to the given paths; the mutant
    tests use it so that the full sweep stays in the one test that needs it and the
    module stays in the seconds, not the minutes. Returns one line per disagreement;
    an empty list means the two lists agree on every probed path.
    """
    workflow = CI_WORKFLOW
    if ci_text is not None:
        workflow = tmp_path / "ci-mutant.yml"
        workflow.write_text(ci_text, encoding="utf-8")
    docs = DOCS_WORKFLOW.read_text(encoding="utf-8") if docs_text is None else docs_text
    markers = docs_trigger_markers(docs)
    script = write_script(tmp_path, extract_run_block(workflow, SCOPE_STEP))
    repo, previous = new_repo(tmp_path, {"README.md": "# root\n"}, name="agreement-repo")

    # Sample the *shipped* trigger list as well as the given one, and the *shipped*
    # prose set as well: a path that a mutant has removed from either file must still
    # be probed, or the comparison falls silent exactly on the hole it exists to find.
    shipped = docs_trigger_markers(DOCS_WORKFLOW.read_text(encoding="utf-8"))
    prose = [
        sample_for_prose(alternative)
        for alternative in prose_alternatives(CI_WORKFLOW.read_text(encoding="utf-8"))
    ]
    if only is None:
        selected = (*shipped, *markers, *prose)
    else:
        # Narrow, but never blind: the paths asked for, plus any prose alternative
        # that names the same path - which is what a one-entry mutant needs.
        selected = (*only, *(probe for probe in prose if probe in only))
    probes = [sample_for_marker(marker) for marker in selected]
    if only is None:
        probes += list(CODE_PROBES)
    problems: list[str] = []
    for rel in dict.fromkeys(probes):
        head = commit(repo, {rel: "probe\n"}, message=f"touch {rel}")
        code = verdict(tmp_path, repo, script, previous, head) == "true"
        expected = not any(marker_matches(rel, marker) for marker in markers)
        if code != expected:
            problems.append(
                f"{rel}: classifier says code={str(code).lower()}, "
                f"docs.yml {'triggers' if not expected else 'does not trigger'} "
                f"-> {'a prose path burns the matrix' if code else 'a shipping path skips it'}"
            )
        previous = head
    return problems


def test_the_docs_trigger_list_and_the_scope_prose_set_are_the_same_set(
    tmp_path: Path,
) -> None:
    """Real change sets, both directions: the two lists must answer identically."""
    problems = mismatch_report(tmp_path)
    assert problems == [], (
        "the scope prose set and the docs.yml `paths:` list disagree:\n" + "\n".join(problems)
    )


def test_the_agreement_bites_when_the_docs_list_drops_an_entry(tmp_path: Path) -> None:
    """Delete a `docs.yml` trigger entry: the comparison must name the hole."""
    docs_text = DOCS_WORKFLOW.read_text(encoding="utf-8")
    mutated = re.sub(r"(?m)^\s*- \"AGENTS\.md\"\n", "", docs_text)
    assert mutated != docs_text, "docs.yml no longer lists AGENTS.md as a trigger path"

    problems = mismatch_report(tmp_path, docs_text=mutated, only=("AGENTS.md",))

    assert any("AGENTS.md" in problem for problem in problems), (
        "dropping AGENTS.md from the docs.yml trigger list produced no mismatch, so the "
        f"comparison does not actually compare: {problems}"
    )


def test_the_agreement_bites_when_the_prose_regex_drops_an_entry(tmp_path: Path) -> None:
    """Delete an entry from the classifier's PROSE regex: same hole, other side."""
    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    mutated = ci_text.replace(r"AGENTS\.md$|", "", 1)
    assert mutated != ci_text, "the classifier's PROSE regex no longer carries AGENTS\\.md$"

    problems = mismatch_report(tmp_path, ci_text=mutated, only=("AGENTS.md",))

    assert any("AGENTS.md" in problem for problem in problems), (
        "dropping AGENTS.md from the classifier's PROSE regex produced no mismatch, so the "
        f"comparison does not actually compare: {problems}"
    )


# --------------------------------------------------------------------------- #
# Every command a workflow runs exists in the tree
# --------------------------------------------------------------------------- #

#: A repository-relative path mentioned by a workflow command. Shell comments are
#: stripped first (the classifier's own comment illustrates a moved
#: `src/teamwork/foo.py`, which is prose, not a command).
WORKFLOW_PATH_RE = re.compile(r"(?<![\w/.-])((?:scripts|docs|\.github|src|tests|roles)/[\w./@-]+)")
INVOKED_SCRIPT_RE = re.compile(r"python3?\s+((?:scripts|\.github)/[\w./@-]+\.py)")
#: The Makefile spells its interpreter `$(PYTHON)`, which is the same process.
MAKE_SCRIPT_RE = re.compile(r"\$\(PYTHON\)\s+((?:scripts|\.github)/[\w./@-]+\.py)")
LONG_FLAG_RE = re.compile(r"(?<![\w-])(--[a-z][a-z0-9-]+)")
PYTHON_MODULE_RE = re.compile(r"python3?\s+-m\s+([A-Za-z_][\w.]*)")


def run_blocks(path: Path) -> list[str]:
    """Every `run:` body in a workflow, with shell comments removed."""
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped in {"run: |", "run: >", "run: |-"}:
            key_indent = len(line) - len(line.lstrip())
            body_indent = key_indent + 2
            body: list[str] = []
            index += 1
            while index < len(lines):
                inner = lines[index]
                if inner.strip() and len(inner) - len(inner.lstrip()) < body_indent:
                    break
                text = inner[body_indent:] if inner.strip() else ""
                if not text.lstrip().startswith("#"):
                    body.append(text)
                index += 1
            blocks.append("\n".join(body))
            continue
        match = re.match(r"\s*run:\s*(?!\||>)(.+)$", line)
        if match:
            blocks.append(match.group(1))
        index += 1
    assert blocks, f"{path}: no run blocks found"
    return blocks


def workflow_paths(path: Path) -> set[str]:
    found: set[str] = set()
    for block in run_blocks(path):
        for match in WORKFLOW_PATH_RE.finditer(block):
            candidate = match.group(1).rstrip(".,'\"")
            found.add(candidate)
    return found


def invoked_scripts(path: Path) -> dict[str, set[str]]:
    """Repository scripts a workflow invokes, with the long flags it passes them."""
    found: dict[str, set[str]] = {}
    for block in run_blocks(path):
        for line in block.splitlines():
            matches = list(INVOKED_SCRIPT_RE.finditer(line))
            if not matches:
                continue
            match = matches[0]
            script = match.group(1)
            tail = line[match.end() :]
            found.setdefault(script, set()).update(LONG_FLAG_RE.findall(tail))
    return found


def test_every_repository_path_a_workflow_runs_exists() -> None:
    """A workflow that names a file the tree does not have fails only on the forge."""
    seen: set[str] = set()
    missing: list[str] = []
    for workflow in WORKFLOWS:
        for candidate in workflow_paths(workflow):
            seen.add(candidate)
            if (REPO_ROOT / candidate).exists():
                continue
            missing.append(f"{workflow.relative_to(REPO_ROOT).as_posix()}: {candidate}")

    assert len(seen) >= 5, (
        f"the path scan found only {sorted(seen)} - it is not reading the run blocks"
    )
    assert "scripts/check_release_consistency.py" in seen, (
        f"the scan did not see the consistency checker in any workflow: {sorted(seen)}"
    )
    assert missing == [], "workflow commands name paths that are not in the tree:\n" + "\n".join(
        missing
    )


def test_every_script_a_workflow_invokes_answers_help() -> None:
    """The shipped script is runnable, not merely present."""
    scripts: dict[str, set[str]] = {}
    for workflow in WORKFLOWS:
        for script, flags in invoked_scripts(workflow).items():
            scripts.setdefault(script, set()).update(flags)

    assert scripts, "no repository script is invoked by any workflow - the scan is blind"

    problems: list[str] = []
    for script in sorted(scripts):
        path = REPO_ROOT / script
        if not path.is_file():
            problems.append(f"{script}: invoked by a workflow but not in the tree")
            continue
        result = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            problems.append(
                f"{script} --help: exit {result.returncode}: {result.stderr.strip()[:400]}"
            )
    assert problems == [], "a workflow invokes a script that does not run:\n" + "\n".join(problems)


def _help_text(script: Path, subcommand: str | None) -> str:
    argv = [sys.executable, str(script)]
    if subcommand:
        argv.append(subcommand)
    argv.append("--help")
    result = subprocess.run(
        argv, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False
    )
    assert result.returncode == 0, (
        f"{' '.join(argv[1:])}: exit {result.returncode}: {result.stderr[:400]}"
    )
    return result.stdout + result.stderr


def test_every_flag_a_workflow_passes_a_script_is_documented() -> None:
    """A renamed flag in a workflow is invisible until the job runs; prove it exists."""
    problems: list[str] = []
    checked = 0
    for workflow in WORKFLOWS:
        for block in run_blocks(workflow):
            for line in block.splitlines():
                match = INVOKED_SCRIPT_RE.search(line)
                if not match:
                    continue
                script = repr(match.group(1))
                tail = line[match.end() :].split()
                subcommand = tail[0] if tail and not tail[0].startswith("-") else None
                flags = sorted({flag.split("=")[0] for flag in LONG_FLAG_RE.findall(line)})
                if not flags:
                    continue
                help_text = _help_text(REPO_ROOT / match.group(1), subcommand)
                for flag in flags:
                    checked += 1
                    if flag not in help_text:
                        problems.append(
                            f"{script}: a workflow passes {flag} but "
                            f"`{' '.join([match.group(1), *([subcommand] if subcommand else []), '--help'])}` "
                            f"does not document it"
                        )
    assert checked >= 4, f"only {checked} workflow flags were checked - the scan is blind"
    assert problems == [], "a workflow passes a flag its script does not accept:\n" + "\n".join(
        problems
    )


# --------------------------------------------------------------------------- #
# The gates Makefile and CI run are the real ones
# --------------------------------------------------------------------------- #

#: Tool -> the argv that reports its presence. Each entry is a gate the Makefile
#: or CI executes; a missing tool is a skipped test naming it, never a pass.
#: The probe is per-tool and parametrized: a single probe that skipped when *any*
#: tool was absent would never bite on a host without GNU make, which is most
#: Windows contributors and is how the absent-tool hole went unnoticed.
GATE_TOOLS = {
    "ruff": ("ruff", "--version"),
    "mypy": ("mypy", "--version"),
    "build": ("build", "--version"),
    "pytest": ("pytest", "--version"),
    "mkdocs": ("mkdocs", "--version"),
    "make": ("make", "--version"),
}

#: `make` is a binary the project drives but never imports; the rest are
#: `python -m <tool>` gates CI installs from the dev extra.
BINARY_GATES = frozenset({"make"})


def _module_available(module: str) -> bool:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import importlib.util as u; print(u.find_spec({module!r}) is not None)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "True"


def gate_argv(name: str) -> list[str] | None:
    """The argv that runs a gate tool, or ``None`` when this host does not have it."""
    argv = GATE_TOOLS[name]
    if name in BINARY_GATES:
        return list(argv) if shutil.which(name) else None
    return [sys.executable, "-m", *argv] if _module_available(name) else None


@pytest.mark.parametrize("name", sorted(GATE_TOOLS))
def test_every_gate_tool_the_makefile_and_ci_invoke_is_real_on_this_host(name: str) -> None:
    """The gates are executable here, or the skip names the one tool that is absent."""
    argv = gate_argv(name)
    if argv is None:
        pytest.skip(
            f"{name} is not installed on this host, so its gate cannot be executed here; "
            "CI installs it from the dev extra and the docs requirements"
        )
    else:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
        assert result.returncode == 0, (
            f"{' '.join(argv)}: exit {result.returncode}: {result.stderr.strip()[:300]}"
        )


def test_every_script_the_makefile_runs_exists() -> None:
    """`make release-check` must invoke scripts that are in the tree."""
    text = MAKEFILE.read_text(encoding="utf-8")
    scripts = {match.group(1) for match in MAKE_SCRIPT_RE.finditer(text)}
    assert len(scripts) >= 4, f"the Makefile scan found only {sorted(scripts)}"
    missing = sorted(script for script in scripts if not (REPO_ROOT / script).is_file())
    assert missing == [], f"the Makefile invokes scripts that are not in the tree: {missing}"


def test_the_ci_test_invocation_is_a_real_pytest_invocation() -> None:
    """Collect the suite with the flags CI uses, minus the report flags."""
    blocks = run_blocks(CI_WORKFLOW)
    run_block = next(
        (block for block in blocks if "--cov-fail-under" in block),
        None,
    )
    assert run_block is not None, "ci.yml no longer runs pytest with a coverage floor"
    assert "--cov-fail-under=55" in run_block, "the documented coverage floor (55) is gone"

    # `run: |` keeps the shell's line continuations, so the pytest command spans
    # several lines and ends each one with a backslash. Joining them first is what
    # stops that backslash from being read as a path argument - which made pytest
    # collect the whole filesystem instead of this repository.
    joined = re.sub(r"\\\n\s*", " ", run_block)
    command = next((line for line in joined.splitlines() if "pytest" in line), None)
    assert command is not None, "could not find the pytest command in the CI run block"
    words = command.split()
    start = next(i for i, word in enumerate(words) if word == "pytest")
    args = words[start + 1 :]
    assert args, "could not read the pytest arguments out of the CI run block"

    kept = [
        arg
        for arg in args
        if not arg.startswith(("--junitxml", "--cov-report", "--cov=", "--cov-fail-under"))
    ]
    # Do not pass `-q` twice: two of them (`-qq`) suppress the summary line this
    # test counts, so a real collection would read as zero collected tests.
    collected_args = [*kept, "--collect-only"] if "-q" in kept else [*kept, "--collect-only", "-q"]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *collected_args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, (
        f"`pytest {' '.join(collected_args)}` failed with exit {result.returncode}:\n"
        f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
    )
    collected = sum(
        int(match.group(1)) for match in re.finditer(r"(?m)^(\d+) tests? collected", result.stdout)
    )
    assert collected >= 200, (
        f"the CI test invocation collected only {collected} tests:\n{result.stdout[-800:]}"
    )


def test_the_python_modules_the_makefile_runs_are_importable() -> None:
    """`python -m <tool>` in a Makefile recipe is a gate only if the module is real."""
    modules: dict[str, str] = {}
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        match = re.search(r"\$\(PYTHON\)\s+-m\s+([A-Za-z_][\w.]*)", line)
        if match:
            modules.setdefault(match.group(1), line.strip())
    assert modules, "the Makefile runs no `$(PYTHON) -m <module>` gate"

    absent = [module for module in modules if not _module_available(module)]
    if absent:
        pytest.skip(
            "modules the Makefile runs are not installed on this host: "
            + ", ".join(f"{module} ({modules[module]})" for module in absent)
            + " - CI installs the dev extra"
        )


def test_the_makefile_exists_and_documents_every_target_it_ships() -> None:
    """The documented local entry point is present and non-trivial."""
    assert MAKEFILE.is_file(), "the Makefile documented in README/AGENTS is missing"
    text = MAKEFILE.read_text(encoding="utf-8")
    targets = set(re.findall(r"(?m)^([a-zA-Z][\w-]*):.*?## ", text))
    assert {"test", "lint", "release-check"} <= targets, (
        f"the Makefile lost a documented gate target: {sorted(targets)}"
    )
