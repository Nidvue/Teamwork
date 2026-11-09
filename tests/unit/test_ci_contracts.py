"""The CI workflow's job contract, asserted instead of trusted.

Why this exists: `.github/workflows/ci.yml` is the only gate that every pushed
revision must pass, and its header states the contract it is built on - the job
set, a `release-consistency` gate that is *unconditional*, expensive jobs that a
prose-only push may skip through the `scope` job's output, and no workflow-level
`paths-ignore` (which used to skip the consistency gate exactly when the
documentation drifted, see the header of that file).

A comment cannot hold a contract: `paths-ignore` was deleted from `on:` once and
nothing failed; a `needs:` on `release-consistency` would let the gate skip with
the job it depends on, and the failure would look like a green run. Each test
below reads the workflow and asserts one clause of the header's contract. The
core clauses - the job set, the scope guards, the unconditional release gate and
the R2 flag - each have a mutant twin that proves the clause bites
(`test_..._mutant`): the mutant applies one targeted edit to the workflow *text*,
parses the result and asserts the contract function reports a violation. The
matrix clause contributes two mutants (a sixth lane, the coverage lane switched
off); its remaining checks - `fail-fast`, the full-history checkout and the junit
step - are direct assertions on the real workflow and have no mutant twin.
Mutants are built in memory, so no tracked file is ever written.

The workflow is parsed by `workflow_yaml.parse_workflow`, a standard-library
reader for the YAML subset these files use. PyYAML is not in the `dev` extra, so
`import yaml` would fail collection in the CI `test` job; the reader is asserted
against the real files, not assumed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from workflow_yaml import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ".github/workflows/ci.yml"

PATH_FILTERS = ("paths", "paths-ignore")

EXPECTED_JOBS = (
    "scope",
    "lint",
    "committer-guard",
    "typecheck",
    "test",
    "build",
    "privacy",
    "release-consistency",
    "docs",
    "docs-contract",
)

TIMEOUT_MINUTES = {
    "scope": 5,
    "lint": 10,
    "committer-guard": 5,
    "typecheck": 10,
    "test": 90,
    "build": 15,
    "privacy": 15,
    "release-consistency": 10,
    "docs": 10,
    "docs-contract": 10,
}

DOCS_READING_TESTS = (
    "tests/acceptance/test_acceptance_docs.py",
    "tests/unit/test_readme_layout.py",
    "tests/unit/test_provider_caps.py",
    "tests/unit/test_docs_contracts.py",
    "tests/unit/test_skill_contracts.py",
)

HISTORY_OPT_OUT = "TEAMWORK_CI_SKIP_HISTORY_PROOF"

UNCONDITIONAL_JOBS = ("scope", "committer-guard", "release-consistency")

SCOPE_GUARD = "needs.scope.outputs.code"

PROSE_GUARD = "needs.scope.outputs.prose"

SCOPE_OUTPUTS = {
    "code": "steps.diff.outputs.code",
    "prose": "steps.diff.outputs.prose",
}

CODE_ONLY_JOBS = ("lint", "typecheck", "test", "build")

MATRIX_CELLS = (
    ("ubuntu-latest", "3.11"),
    ("ubuntu-latest", "3.12"),
    ("ubuntu-latest", "3.13"),
    ("macos-latest", "3.13"),
    ("windows-latest", "3.13"),
)

COVERAGE_CELL = ("ubuntu-latest", "3.11")

COVERAGE_FLOOR = "--cov-fail-under=55"

CODE_OR_PROSE_JOBS = ("privacy", "docs", "docs-contract")


def workflow_text(repo_root: Path = REPO_ROOT) -> str:
    return (repo_root / CI_PATH).read_text(encoding="utf-8")


def workflow(repo_root: Path = REPO_ROOT) -> dict:
    return parse_workflow(workflow_text(repo_root))


def jobs(document: dict) -> dict:
    found = document.get("jobs")
    assert isinstance(found, dict), f"{CI_PATH} has no `jobs:` mapping"
    return found


def needs_of(job: dict) -> list[str]:
    """`needs:` is a scalar or a flow sequence; normalise both to a list."""
    needs = job.get("needs")
    if needs is None:
        return []
    if isinstance(needs, list):
        return [str(item) for item in needs]
    return [str(needs)]


def matrix_rows(document: dict) -> list[tuple[str, str, str]]:
    """``(os, python-version, coverage)`` for every expanded test-matrix cell."""
    matrix = ((jobs(document).get("test") or {}).get("strategy") or {}).get("matrix") or {}
    rows = []
    for entry in matrix.get("include") or []:
        rows.append(
            (str(entry.get("os")), str(entry.get("python-version")), str(entry.get("coverage")))
        )
    return rows


def matrix_problems(document: dict) -> list[str]:
    """The five-cell matrix, its fail-fast policy and the single coverage lane."""
    problems: list[str] = []
    test_job = jobs(document).get("test") or {}
    strategy = test_job.get("strategy") or {}
    matrix = strategy.get("matrix") or {}
    if strategy.get("fail-fast") != "false":
        problems.append(f"test fail-fast is {strategy.get('fail-fast')!r}, want the string 'false'")
    if "os" in matrix or "python-version" in matrix:
        problems.append(
            f"the test matrix still expands a cartesian product beside `include:`: {sorted(matrix)}"
        )
    rows = matrix_rows(document)
    cells = [(os_name, version) for os_name, version, _coverage in rows]
    if sorted(cells) != sorted(MATRIX_CELLS):
        problems.append(f"test matrix is {sorted(cells)}, contract says {sorted(MATRIX_CELLS)}")
    covered = [(os_name, version) for os_name, version, coverage in rows if coverage == "true"]
    if covered != [COVERAGE_CELL]:
        problems.append(f"coverage lanes are {covered}, want only {COVERAGE_CELL}")
    for os_name, version, _coverage in rows:
        if version in {"3.9", "3.10"}:
            problems.append(f"the matrix still schedules {os_name} / py{version}")
    steps = test_job.get("steps") or []
    with_cov = [step for step in steps if "--cov" in str(step.get("run") or "")]
    if len(with_cov) != 1:
        problems.append(f"{len(with_cov)} step(s) run coverage, want exactly 1")
    elif str(with_cov[0].get("if") or "") != "matrix.coverage":
        problems.append(
            f"the coverage step is gated on {with_cov[0].get('if')!r}, want matrix.coverage"
        )
    if workflow_text().count(COVERAGE_FLOOR) != 1:
        problems.append(f"{COVERAGE_FLOOR} appears {workflow_text().count(COVERAGE_FLOOR)}x")
    names = " ".join(str(step.get("name") or "") for step in steps)
    if "Checkout (full history)" not in names:
        problems.append("the test job lost its full-history checkout step")
    if not any(
        "fetch-depth" in str(step.get("with") or {})
        for step in steps
        if "Checkout" in str(step.get("name") or "")
    ):
        problems.append("the checkout step no longer asserts fetch-depth")
    if not any("junit" in str(step.get("name") or "").lower() for step in steps):
        problems.append("the test job lost its junit artifact step")
    return problems


def docs_reading_problems(document: dict) -> list[str]:
    """The cheap docs job: it must run on a prose push and run all five files.

    A prose-only push skips the matrix, which is right for the expensive lanes and
    wrong for the tests that read the prose: the README rewrite that dropped the
    install command and the provider-cap statement both landed as "prose" and were
    only found later. This job is the cheap half that runs anyway, so its guard and
    its file list are the contract.
    """
    problems: list[str] = []
    job = jobs(document).get("docs-contract")
    if job is None:
        return ["the docs-contract job is missing, so a prose push runs none of the prose tests"]
    if "scope" not in needs_of(job):
        problems.append("docs-contract does not declare `needs: scope`")
    guard = str(job.get("if") or "")
    if SCOPE_GUARD not in guard or PROSE_GUARD not in guard:
        problems.append(f"docs-contract does not gate on `code || prose`: {guard!r}")
    if "strategy" in job:
        problems.append("docs-contract expands a matrix; it is one cheap ubuntu job by design")
    runs = "\n".join(str(step.get("run") or "") for step in job.get("steps") or [])
    missing = [path for path in DOCS_READING_TESTS if path not in runs]
    if missing:
        problems.append(f"docs-contract does not run the prose tests {missing}")
    if "--cov" in runs:
        problems.append("docs-contract runs coverage, which the matrix's coverage lane owns")
    return problems


def timeout_problems(document: dict) -> list[str]:
    """Every job is bounded, with the budget the contract names.

    Without `timeout-minutes` GitHub holds a hung job for six hours of runner
    time; the red run this task started from burned 51 minutes on one lane
    because a proof waited out its own budget. The per-job numbers are the
    contract: the matrix gets an hour, the static gates minutes.
    """
    problems: list[str] = []
    for name, job in jobs(document).items():
        value = job.get("timeout-minutes")
        if value is None:
            problems.append(f"{name} has no timeout-minutes, so a hang runs to the runner limit")
            continue
        if str(value) != str(TIMEOUT_MINUTES.get(name)):
            problems.append(
                f"{name} timeout-minutes is {value!r}, contract says {TIMEOUT_MINUTES.get(name)}"
            )
    return problems


def contract_problems(document: dict) -> list[str]:
    """Every clause of the header's contract that the given document violates."""
    problems: list[str] = []
    found = jobs(document)

    if tuple(found) != EXPECTED_JOBS:
        problems.append(f"job set is {tuple(found)}, contract says {EXPECTED_JOBS}")

    triggers = document.get("on") or document.get(True) or {}
    for filter_key in PATH_FILTERS:
        if filter_key in triggers:
            problems.append(f"on carries {filter_key}, so a push can skip every job")
    for trigger, spec in triggers.items():
        if not isinstance(spec, dict):
            continue
        for filter_key in PATH_FILTERS:
            if filter_key in spec:
                problems.append(f"on.{trigger} carries {filter_key}, so a push can skip every job")

    gate = found.get("release-consistency")
    if gate is None:
        problems.append("release-consistency job is missing")
    else:
        if needs_of(gate):
            problems.append(
                f"release-consistency has needs={needs_of(gate)}, it must be unconditional"
            )
        if gate.get("if"):
            problems.append(
                f"release-consistency has if={gate.get('if')!r}, it must be unconditional"
            )

    for name in UNCONDITIONAL_JOBS:
        job = found.get(name)
        if job is None:
            continue
        if job.get("if"):
            problems.append(f"{name} carries if={job.get('if')!r} but must always run")

    for name, job in found.items():
        if name in UNCONDITIONAL_JOBS:
            continue
        if "scope" not in needs_of(job):
            problems.append(f"{name} does not declare `needs: scope`")
        guard = str(job.get("if") or "")
        if SCOPE_GUARD not in guard:
            problems.append(f"{name} has no `if:` guard on {SCOPE_GUARD}: {guard!r}")

    outputs = (found.get("scope") or {}).get("outputs") or {}
    for name, expression in SCOPE_OUTPUTS.items():
        if expression not in str(outputs.get(name) or ""):
            problems.append(f"scope does not publish the `{name}` output: outputs={outputs!r}")
    for name in CODE_OR_PROSE_JOBS:
        guard = str((found.get(name) or {}).get("if") or "")
        if SCOPE_GUARD not in guard or PROSE_GUARD not in guard:
            problems.append(f"{name} does not gate on `code || prose`: {guard!r}")
    for name in CODE_ONLY_JOBS:
        guard = str((found.get(name) or {}).get("if") or "")
        if PROSE_GUARD in guard:
            problems.append(f"{name} gates on the prose output, so a prose push runs it: {guard!r}")
    problems.extend(matrix_problems(document))
    problems.extend(docs_reading_problems(document))
    problems.extend(timeout_problems(document))
    return problems


@pytest.fixture(scope="module")
def ci() -> dict:
    return workflow()


def test_the_matrix_is_the_five_designed_cells(ci):
    """3.11/3.12/3.13 on ubuntu, newest on macOS and Windows: five lanes, no more."""
    assert sorted((os_name, version) for os_name, version, _ in matrix_rows(ci)) == sorted(
        MATRIX_CELLS
    )


def test_the_matrix_keeps_fail_fast_false(ci):
    assert (jobs(ci)["test"].get("strategy") or {}).get("fail-fast") == "false"


def test_the_coverage_gate_runs_on_one_lane_only(ci):
    """The 55% floor must exist exactly once, on ubuntu 3.11."""
    assert workflow_text().count(COVERAGE_FLOOR) == 1
    covered = [
        (os_name, version) for os_name, version, coverage in matrix_rows(ci) if coverage == "true"
    ]
    assert covered == [COVERAGE_CELL]
    with_cov = [
        step
        for step in jobs(ci)["test"].get("steps") or []
        if "--cov" in str(step.get("run") or "")
    ]
    assert len(with_cov) == 1, "coverage flags must live in one step"
    assert str(with_cov[0].get("if") or "") == "matrix.coverage"


def test_every_test_lane_keeps_full_history_and_the_junit_artifact(ci):
    steps = jobs(ci)["test"].get("steps") or []
    names = [str(step.get("name") or "") for step in steps]
    assert "Checkout (full history)" in names
    assert any("junit" in name.lower() for name in names)


def test_the_workflow_declares_the_contracted_job_set(ci):
    assert tuple(jobs(ci)) == EXPECTED_JOBS


def test_the_release_consistency_gate_is_unconditional(ci):
    """No `needs:` and no `if:`: the gate cannot be skipped by a sibling job."""
    gate = jobs(ci)["release-consistency"]
    assert "needs" not in gate, f"release-consistency declares needs={gate.get('needs')!r}"
    assert "if" not in gate, f"release-consistency declares if={gate.get('if')!r}"


def test_every_expensive_job_is_gated_on_the_scope_output(ci):
    """The test matrix and the packaging jobs must be skippable; nothing else must."""
    expensive = [name for name in EXPECTED_JOBS if name not in UNCONDITIONAL_JOBS]
    assert expensive, "every job is unconditional, so the guard clause is untested"
    for name in expensive:
        job = jobs(ci)[name]
        assert needs_of(job) == ["scope"], f"{name} needs={needs_of(job)}"
        assert SCOPE_GUARD in str(job.get("if") or ""), f"{name} has no scope guard"


def test_no_workflow_level_path_filter_remains(ci):
    """The prose filter lives in the `scope` job, not in `on:`."""
    triggers = ci.get("on") or ci.get(True) or {}
    assert isinstance(triggers, dict) and triggers, "the workflow declares no triggers"
    for filter_key in PATH_FILTERS:
        assert filter_key not in triggers, f"on carries {filter_key}"
        for trigger, spec in triggers.items():
            if isinstance(spec, dict):
                assert filter_key not in spec, f"on.{trigger} carries {filter_key}"


def test_the_scope_job_publishes_the_output_the_guard_reads(ci):
    """A guard on an output nobody writes evaluates to the empty string forever."""
    scope = jobs(ci)["scope"]
    assert "code" in (scope.get("outputs") or {}), "scope declares no `code` output"
    assert "${{ steps.diff.outputs.code }}" in str((scope.get("outputs") or {})["code"])


def test_the_scope_job_publishes_the_prose_output_too(ci):
    """`code` alone cannot express "prose-only", which is what `privacy` reads."""
    outputs = jobs(ci)["scope"].get("outputs") or {}
    assert "prose" in outputs, f"scope publishes {sorted(outputs)}, want code and prose"
    assert "${{ steps.diff.outputs.prose }}" in str(outputs["prose"])


def test_privacy_and_docs_gate_on_code_or_prose(ci):
    """A prose-only push skips the matrix but must not skip these two gates."""
    for name in CODE_OR_PROSE_JOBS:
        guard = str(jobs(ci)[name].get("if") or "")
        assert SCOPE_GUARD in guard, f"{name} does not read `code`: {guard!r}"
        assert PROSE_GUARD in guard, f"{name} does not read `prose`: {guard!r}"


def test_the_matrix_jobs_gate_on_code_alone(ci):
    """A prose edit cannot change what lint/typecheck/test/build measure."""
    for name in CODE_ONLY_JOBS:
        guard = str(jobs(ci)[name].get("if") or "")
        assert SCOPE_GUARD in guard, f"{name} does not read `code`: {guard!r}"
        assert PROSE_GUARD not in guard, f"{name} reads `prose` too: {guard!r}"


def test_the_docs_contract_job_runs_the_prose_tests_on_a_prose_push(ci):
    """The false economy: a prose push skips the matrix, so this job must run."""
    assert docs_reading_problems(ci) == []


def test_the_proof_once_lane_declares_the_history_choice(ci):
    """One lane proves the history; the others say so, rather than inheriting it."""
    steps = jobs(ci)["test"].get("steps") or []
    coverage = [step for step in steps if "--cov" in str(step.get("run") or "")]
    plain = [step for step in steps if str(step.get("name") or "") == "Run tests (plain)"]
    assert len(coverage) == 1, "coverage and its history proof must be one step"
    assert len(plain) == 1, "the non-coverage lanes need one explicit step"
    assert (coverage[0].get("env") or {}).get(HISTORY_OPT_OUT) == "0"
    assert (plain[0].get("env") or {}).get(HISTORY_OPT_OUT) == "1"


def test_every_job_is_bounded_by_a_timeout(ci):
    assert timeout_problems(ci) == []


def test_mutant_a_dropped_docs_reading_file_is_reported():
    document = _mutate("            tests/unit/test_readme_layout.py \\\n", "")
    problems = docs_reading_problems(document)
    assert any("test_readme_layout.py" in problem for problem in problems), problems


def test_mutant_a_prose_blind_docs_contract_job_is_reported():
    document = _mutate(
        "    # seconds of work, so they run on `code || prose` and on every event.\n"
        "    if: github.event_name != 'push' || needs.scope.outputs.code == 'true' || needs.scope.outputs.prose == 'true'",
        "    # seconds of work, so they run on `code || prose` and on every event.\n"
        "    if: github.event_name != 'push' || needs.scope.outputs.code == 'true'",
    )
    problems = docs_reading_problems(document)
    assert any("code || prose" in problem for problem in problems), problems


def test_mutant_a_job_without_a_timeout_is_reported():
    document = _mutate("    timeout-minutes: 90\n", "")
    problems = timeout_problems(document)
    assert any("test has no timeout-minutes" in problem for problem in problems), problems


def test_every_job_contract_clause_holds_for_the_real_workflow(ci):
    assert contract_problems(ci) == []


def _mutate(old: str, new: str, count: int = 1) -> dict:
    text = workflow_text()
    assert text.count(old) == count, (
        f"mutant anchor {old!r} appears {text.count(old)}x, want {count}"
    )
    return parse_workflow(text.replace(old, new))


def _drop_line_of_job(job: str, prefix: str) -> dict:
    """Remove the first line starting with `prefix` inside the block of `job`."""
    lines = workflow_text().splitlines(keepends=True)
    start = lines.index(f"  {job}:\n")
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped and not lines[index].startswith("    "):
            break
        if lines[index].startswith(prefix):
            del lines[index]
            return parse_workflow("".join(lines))
    raise AssertionError(f"{job} has no line starting with {prefix!r}")


def test_mutant_a_paths_ignore_under_on_is_reported():
    document = _mutate(
        "on:\n  push:\n    branches: [main]",
        "on:\n  push:\n    branches: [main]\n    paths-ignore: ['docs/**']",
    )
    problems = contract_problems(document)
    assert any("paths-ignore" in problem for problem in problems), problems


def test_mutant_a_path_filter_at_the_on_level_is_reported():
    """`on: {paths-ignore: ...}` applies to every trigger and skips the gate too."""
    document = _mutate("on:\n  push:\n", "on:\n  paths-ignore: ['docs/**']\n  push:\n")
    problems = contract_problems(document)
    assert "on carries paths-ignore, so a push can skip every job" in problems, problems


def test_mutant_a_needs_on_the_gate_is_reported():
    document = _mutate(
        "  release-consistency:\n    name:", "  release-consistency:\n    needs: scope\n    name:"
    )
    problems = contract_problems(document)
    assert any("release-consistency has needs" in problem for problem in problems), problems


def test_mutant_a_missing_scope_guard_is_reported():
    document = _drop_line_of_job("build", "    if: ")
    problems = contract_problems(document)
    assert any(problem.startswith("build has no `if:` guard") for problem in problems), problems


def test_mutant_a_dropped_job_is_reported():
    lines = workflow_text().splitlines(keepends=True)
    start = lines.index("  docs:\n")
    document = parse_workflow("".join(lines[:start]))
    problems = contract_problems(document)
    assert any(problem.startswith("job set is") for problem in problems), problems
    assert any("docs" in problem for problem in problems), problems


def test_the_guard_regex_names_an_output_only_the_scope_job_writes(ci):
    """Guards elsewhere (`docs.yml`) may use a different job name, never `scope`."""
    guard = re.compile(r"needs\.(\w+)\.outputs")
    names = set()
    for job in jobs(ci).values():
        names.update(guard.findall(str(job.get("if") or "")))
    assert names <= {"scope"}, f"a guard reads an output of {sorted(names - {'scope'})}"


def test_mutant_the_one_output_workflow_is_reported():
    """The pre-change workflow: `scope` published `code` only, and `privacy` and
    `docs` gated on it alone, so a prose-only push skipped the privacy and docs
    gates. That text must be reported, not merely different."""
    text = workflow_text()
    mutant = text.replace("      prose: ${{ steps.diff.outputs.prose }}\n", "")
    mutant = mutant.replace(" || needs.scope.outputs.prose == 'true'", "")
    assert mutant != text, "mutant anchors are gone: the workflow no longer publishes `prose`"

    problems = contract_problems(parse_workflow(mutant))
    assert any("does not publish the `prose` output" in problem for problem in problems), problems
    for name in CODE_OR_PROSE_JOBS:
        assert any(
            problem.startswith(f"{name} does not gate on `code || prose`") for problem in problems
        ), problems


SCOPE_FLAG = "--head-is-default-branch"

SCOPE_EXPRESSION = re.compile(
    r"^\$\{\{\s*github\.event_name\s*==\s*'pull_request'\s*&&\s*'(yes|no)'\s*\|\|\s*'(yes|no)'\s*\}\}$"
)

SCOPE_ENV_REFERENCE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def checker_steps(document: dict) -> list[tuple[str, dict]]:
    """Every ``(job, step)`` whose ``run:`` invokes the release checker."""
    found: list[tuple[str, dict]] = []
    for job_name, job in jobs(document).items():
        for step in job.get("steps") or []:
            if "check_release_consistency.py" in str(step.get("run") or ""):
                found.append((job_name, step))
    return found


def scope_arms(step: dict) -> tuple[str, str] | None:
    """The ``(pull_request, other)`` values the step's flag resolves to, or ``None``.

    ``None`` is every shape the contract forbids: no flag, two flags, a literal
    value, or an expression that is not the two-armed ternary above.
    """
    run = str(step.get("run") or "")
    values = re.findall(SCOPE_FLAG + r"=(\S+)", run)
    if len(values) != 1:
        return None
    reference = SCOPE_ENV_REFERENCE.match(values[0].strip("'\""))
    if reference is None:
        return None
    env = step.get("env")
    if not isinstance(env, dict):
        return None
    expression = SCOPE_EXPRESSION.match(str(env.get(reference.group(1)) or ""))
    if expression is None:
        return None
    pull_request, other = expression.groups()
    return (pull_request, other)


def scope_problems(document: dict) -> list[str]:
    """Every clause of the 11.2.2.1 wiring the workflow violates."""
    problems: list[str] = []
    steps = checker_steps(document)
    if not steps:
        problems.append("no step invokes check_release_consistency.py")
    for job_name, step in steps:
        run = str(step.get("run") or "")
        count = run.count(SCOPE_FLAG)
        if count != 1:
            problems.append(f"{job_name} passes {SCOPE_FLAG} {count}x, want exactly 1")
            continue
        arms = scope_arms(step)
        if arms is None:
            problems.append(
                f"{job_name} does not carry the {SCOPE_FLAG} scope in one env expression"
            )
            continue
        pull_request, other = arms
        if pull_request != "no":
            problems.append(
                f"{job_name} passes {SCOPE_FLAG}={pull_request} on a pull request, want no"
            )
        if other != "yes":
            problems.append(f"{job_name} passes {SCOPE_FLAG}={other} on the other arm, want yes")
    return problems


def test_every_checker_invocation_passes_head_is_default_branch_no_on_a_pull_request(ci):
    """11.2.2.1: a pull-request merge ref publishes nothing, so R2 must SKIP."""
    steps = checker_steps(ci)
    assert steps, "no step invokes the release checker, so the scope is untested"
    for job_name, step in steps:
        arms = scope_arms(step)
        assert arms is not None, f"{job_name} passes no {SCOPE_FLAG} scope"
        assert arms[0] == "no", (job_name, arms)


def test_the_non_pull_request_arm_keeps_r2_evaluated_with_head_is_default_branch_yes(ci):
    """Both arms are greppable, and the non-pull-request arm is the evaluating one.

    A push to `main` and a `v*` tag push both publish, so the flag must say `yes`
    there: the amendment's catch for a tag placed on an older commit depends on
    R2 still being evaluated.
    """
    for job_name, step in checker_steps(ci):
        arms = scope_arms(step)
        assert arms is not None, f"{job_name} passes no {SCOPE_FLAG} scope"
        assert arms[1] == "yes", (job_name, arms)
    assert workflow_text().count("github.event_name == 'pull_request' && 'no' || 'yes'") == 1


def test_the_r2_scope_wiring_holds_for_the_real_workflow(ci):
    assert scope_problems(ci) == []


def test_mutant_a_sixth_matrix_cell_is_reported():
    """An added lane is a cost the contract did not agree to."""
    anchor = (
        "          - os: windows-latest\n"
        '            python-version: "3.13"\n'
        "            coverage: false\n"
    )
    mutant = workflow_text().replace(
        anchor,
        anchor + '          - os: ubuntu-latest\n            python-version: "3.10"\n'
        "            coverage: false\n",
        1,
    )
    assert mutant != workflow_text(), "matrix anchor is gone"
    problems = matrix_problems(parse_workflow(mutant))
    assert any("test matrix is" in problem for problem in problems), problems
    assert any("still schedules" in problem for problem in problems), problems


def test_mutant_a_dropped_coverage_lane_is_reported():
    """Turning the one coverage cell off would make the gate unreachable."""
    mutant = workflow_text().replace(
        "            coverage: true\n", "            coverage: false\n", 1
    )
    assert mutant != workflow_text(), "coverage anchor is gone"
    problems = matrix_problems(parse_workflow(mutant))
    assert any("coverage lanes are" in problem for problem in problems), problems


def test_mutant_the_swapped_scope_arms_are_reported():
    """Flip the two literals: the pull request would evaluate, main would not."""
    text = workflow_text()
    mutant = text.replace("&& 'no' || 'yes'", "&& 'yes' || 'no'")
    assert mutant != text, "mutant anchor is gone: the workflow no longer spells both arms"

    problems = scope_problems(parse_workflow(mutant))
    assert any("on a pull request, want no" in problem for problem in problems), problems
    assert any("on the other arm, want yes" in problem for problem in problems), problems


def test_mutant_a_dropped_scope_flag_is_reported():
    """A gate that forgets the flag pays R2's false red on every pull request."""
    text = workflow_text()
    mutant = text.replace(' --head-is-default-branch="${HEAD_IS_DEFAULT_BRANCH}"', "")
    assert mutant != text, "mutant anchor is gone: the flag is written differently now"

    problems = scope_problems(parse_workflow(mutant))
    assert any("passes --head-is-default-branch 0x" in problem for problem in problems), problems
