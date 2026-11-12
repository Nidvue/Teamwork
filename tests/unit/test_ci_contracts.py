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
matrix clause contributes six mutants (a shard with no path, a test file in two
shards, a cell without xdist, a boundary interpreter moved onto the subset, a
macOS subset without the portability flow, and a header that drops it); its
remaining checks - `fail-fast`, the full-history checkout and the junit step - are
direct assertions on the real workflow and have no mutant twin.
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
    "privacy": 30,
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


SHARDED_CELLS = {("windows-latest", "3.13")}

SUBSET_PATHS = "tests/unit tests/acceptance"

PORTABILITY_FLOW = "tests/integration/test_portability_flow.py"

SUBSET_CELLS = {
    ("ubuntu-latest", "3.12"): SUBSET_PATHS,
    ("macos-latest", "3.13"): f"{SUBSET_PATHS} {PORTABILITY_FLOW}",
}

FULL_SUITE_CELLS = (("ubuntu-latest", "3.11"), ("ubuntu-latest", "3.13"))

PLATFORM_TEST = "tests/unit/test_portability.py"

XDIST = "--numprocesses=auto"


def matrix_entries(document: dict) -> list[dict]:
    """The raw `include:` entries, so a clause can read a row's own fields."""
    matrix = ((jobs(document).get("test") or {}).get("strategy") or {}).get("matrix") or {}
    return list(matrix.get("include") or [])


def subset_problems(document: dict, repo_root: Path = REPO_ROOT) -> list[str]:
    """Each subset cell names its contracted subset, and the boundaries run everything.

    A subset is only safe while some lane still runs the whole suite: the matrix
    is sized to the portability question, and the question is answered by the two
    boundary interpreters. macOS is one of the hosts the portability contract
    exists for, so its subset keeps `tests/integration/test_portability_flow.py`
    (the spaced-path, symlink and GNU-make guards) beside the unit tree's
    `tests/unit/test_portability.py`.
    """
    problems: list[str] = []
    rows = {
        (str(entry.get("os")), str(entry.get("python-version"))): str(entry.get("paths") or "")
        for entry in matrix_entries(document)
    }
    required = {
        ("macos-latest", "3.13"): (PLATFORM_TEST, PORTABILITY_FLOW),
    }
    for cell, expected in sorted(SUBSET_CELLS.items()):
        paths = rows.get(cell)
        if paths is None:
            problems.append(f"the subset cell {cell} is missing from the matrix")
            continue
        if paths != expected:
            problems.append(f"{cell} runs {paths!r}, contract says the subset {expected!r}")
            continue
        for token in paths.split():
            if not list(repo_root.glob(token)):
                problems.append(f"{cell} names {token!r}, which matches no path")
        covered = {
            path.relative_to(repo_root).as_posix()
            for token in paths.split()
            for match in repo_root.glob(token)
            for path in (sorted(match.rglob("*.py")) if match.is_dir() else [match])
        }
        for subject in required.get(cell, (PLATFORM_TEST,)):
            if subject not in covered:
                problems.append(f"{cell} drops {subject}, a portability contract")
    for cell in FULL_SUITE_CELLS:
        if rows.get(cell):
            problems.append(f"{cell} is a boundary interpreter and must run the whole suite")
    return problems


def header_text(source: str) -> str:
    """The workflow's leading comment block, with its `#` markers and wraps removed."""
    lines: list[str] = []
    for line in source.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            break
        lines.append(line.lstrip("#").strip())
    return " ".join(part for part in lines if part)


def header_problems(source: str | None = None) -> list[str]:
    """The header names each subset cell's paths exactly as its matrix row does.

    The header is the contract document a lane reads to decide whether a cell may
    drop a path, so a header that restates a row differently is a defect even when
    the row is right: T-0105 was failed for leaving a refuted premise in the
    header while the row it declares itself the contract for had been fixed.
    """
    text = header_text(workflow_text() if source is None else source)
    return [
        f"the header does not state {cell}'s subset {expected!r}"
        for cell, expected in sorted(SUBSET_CELLS.items())
        if expected not in text
    ]


def parallel_problems(document: dict) -> list[str]:
    """Every non-Windows cell runs under xdist; the Windows shards stay serial.

    The suite spawns hundreds of processes and a hosted runner gives 3-4 vCPUs, so
    a cell is wall-clock bound. Measured on the 4-worker emulation of a runner:
    242s serial against 94s with `-n 4`, same results. The Windows rows are
    already split into six path shards and gain nothing from a second split.
    """
    problems: list[str] = []
    for entry in matrix_entries(document):
        cell = (str(entry.get("os")), str(entry.get("python-version")))
        flag = str(entry.get("xdist") or "")
        if cell[0] == "windows-latest":
            if flag:
                problems.append(f"the sharded Windows cell {cell} also sets xdist {flag!r}")
        elif flag != XDIST:
            problems.append(f"{cell} does not run under pytest-xdist: {flag!r}")
    steps = (jobs(document).get("test") or {}).get("steps") or []
    plain = [step for step in steps if "--junitxml" in str(step.get("run") or "")]
    if len(plain) != 2:
        problems.append(f"{len(plain)} junit steps, want the coverage and plain pair")
        return problems
    plain_run = str(plain[1].get("run") or "")
    if "matrix.xdist" not in plain_run:
        problems.append("the plain test step ignores matrix.xdist")
    coverage_run = str(plain[0].get("run") or "")
    if XDIST not in coverage_run:
        problems.append(f"the coverage step does not run under {XDIST!r}")
    return problems


def naming_problems(document: dict) -> list[str]:
    """A sharded job names its shard, and its pytest run names the tests it runs.

    The job name is the only label a reader has while a run is in flight, and a
    shard that hangs at the cap is otherwise indistinguishable from a slow one.
    `-v` writes each test as it starts and `--durations=25` names the slowest
    tests when the run ends, so a cancelled shard leaves the last test it began
    in the log instead of an empty tail (T-0111, run 43035306476).
    """
    problems: list[str] = []
    job = jobs(document).get("test") or {}
    name = str(job.get("name") or "")
    if "matrix.shard" not in name:
        problems.append(f"the test job name does not name its shard: {name!r}")
    steps = job.get("steps") or []
    plain = [step for step in steps if "--junitxml" in str(step.get("run") or "")]
    if len(plain) != 2:
        problems.append(f"{len(plain)} junit steps, want the coverage and plain pair")
        return problems
    run = str(plain[1].get("run") or "")
    for flag in ("--durations", "-v"):
        if flag not in run:
            problems.append(f"the plain test step does not pass {flag!r}")
    if "matrix.shard" not in run:
        problems.append("the plain test step passes those flags to every cell, not the shards")
    return problems


def shard_problems(document: dict) -> list[str]:
    """A cell may be sharded, but the shards must partition the suite by path.

    Windows spawns processes several times slower than the POSIX runners, so one
    job per cell exceeded the 90-minute cap even after the traceability guard
    stopped re-running the privacy scan (T-0090). A shard is one matrix row with a
    `paths` field; the rule is that a sharded cell has at least two rows, every
    shard names a path, and no two shards name the same path.
    """
    matrix = ((jobs(document).get("test") or {}).get("strategy") or {}).get("matrix") or {}
    rows = matrix.get("include") or []
    problems: list[str] = []
    seen: dict = {}
    for entry in rows:
        cell = (str(entry.get("os")), str(entry.get("python-version")))
        seen.setdefault(cell, []).append(str(entry.get("paths") or ""))
    for cell, paths in sorted(seen.items()):
        if len(paths) == 1:
            if not paths[0]:
                continue
            if cell not in SUBSET_CELLS:
                problems.append(f"{cell} names shard paths but is one job: {paths[0]!r}")
            continue
        if cell not in SHARDED_CELLS:
            problems.append(f"{cell} is sharded into {len(paths)} jobs; only {SHARDED_CELLS}")
        if any(not path for path in paths):
            problems.append(f"{cell} has a shard with no paths: {paths}")
        if len(set(paths)) != len(paths):
            problems.append(f"{cell} has two shards with the same paths: {paths}")
    for cell in SHARDED_CELLS:
        if cell not in seen:
            problems.append(f"the sharded cell {cell} is missing from the matrix")
    return problems


def shard_rows(document: dict) -> list[tuple[str, str]]:
    """``(shard name, paths)`` for every row of a sharded cell."""
    matrix = ((jobs(document).get("test") or {}).get("strategy") or {}).get("matrix") or {}
    rows = []
    for entry in matrix.get("include") or []:
        cell = (str(entry.get("os")), str(entry.get("python-version")))
        if cell in SHARDED_CELLS:
            rows.append((str(entry.get("shard") or ""), str(entry.get("paths") or "")))
    return rows


def shard_file_problems(document: dict, repo_root: Path = REPO_ROOT) -> list[str]:
    """The shards must *partition* the suite, not merely avoid naming one path twice.

    `shard_problems` catches two shards naming the same paths. It cannot see a test
    file that no shard names, and the sharded cell is the only lane that runs the
    suite through `paths`, so such a gap is a test that never runs there. Both
    halves are computed from the tree: every path token is expanded by the same
    glob semantics the shell uses, and the union is compared with every
    `test_*.py` under `tests/`.
    """
    problems: list[str] = []
    named: dict[str, list[str]] = {}
    for shard, paths in shard_rows(document):
        if not paths:
            problems.append(f"shard {shard!r} names no paths")
            continue
        for token in paths.split():
            matches = list(repo_root.glob(token))
            files = [
                path
                for match in matches
                for path in (sorted(match.rglob("test_*.py")) if match.is_dir() else [match])
                if path.is_file() and path.name.startswith("test_")
            ]
            if not files:
                problems.append(f"shard {shard!r} names {token!r}, which matches no test file")
            for path in files:
                named.setdefault(path.relative_to(repo_root).as_posix(), []).append(shard)
    every = sorted(
        path.relative_to(repo_root).as_posix() for path in (repo_root / "tests").rglob("test_*.py")
    )
    unnamed = sorted(set(every) - set(named))
    if unnamed:
        problems.append(f"no shard runs {len(unnamed)} test file(s): {unnamed}")
    unknown = sorted(set(named) - set(every))
    if unknown:
        problems.append(f"the shards name {len(unknown)} file(s) outside tests/: {unknown}")
    doubled = {path: shards for path, shards in named.items() if len(shards) > 1}
    if doubled:
        problems.append(f"test files in two shards: {doubled}")
    return problems


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
    cells = sorted({(os_name, version) for os_name, version, _coverage in rows})
    if cells != sorted(MATRIX_CELLS):
        problems.append(f"test matrix is {cells}, contract says {sorted(MATRIX_CELLS)}")
    problems.extend(shard_problems(document))
    problems.extend(subset_problems(document))
    problems.extend(parallel_problems(document))
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
    assert sorted({(os_name, version) for os_name, version, _ in matrix_rows(ci)}) == sorted(
        MATRIX_CELLS
    )


def test_the_matrix_keeps_fail_fast_false(ci):
    assert (jobs(ci)["test"].get("strategy") or {}).get("fail-fast") == "false"


def test_the_shards_partition_the_suite_and_stay_small(ci):
    """Every test file runs in exactly one shard, and no shard carries the a-f bulk.

    The a-f row of the first split ran unit a-f plus the whole integration and
    acceptance trees and was cancelled at the 90-minute cap (run 43000716956), so
    the tree with the most subprocesses is no longer bundled with a unit range.
    """
    assert shard_problems(ci) == []
    assert shard_file_problems(ci) == []
    rows = shard_rows(ci)
    assert len(rows) >= 6, rows
    assert len({shard for shard, _paths in rows}) == len(rows), rows
    for shard, paths in rows:
        assert not ("test_[a-f]" in paths and "tests/integration" in paths), shard
    integration = [shard for shard, paths in rows if "tests/integration/" in paths]
    assert len(integration) >= 2, rows


def test_every_sharded_job_names_itself_and_its_slowest_tests(ci):
    """The Windows integration shard ran 55 minutes with nothing in the log to name."""
    assert naming_problems(ci) == []


def test_mutant_a_job_name_without_its_shard_is_reported():
    mutant = workflow_text().replace(
        "${{ matrix.shard && format(' / {0}', matrix.shard) || '' }}", "", 1
    )
    assert mutant != workflow_text(), "the job name no longer names the shard"
    problems = naming_problems(parse_workflow(mutant))
    assert any("does not name its shard" in problem for problem in problems), problems


def test_mutant_a_plain_run_without_durations_is_reported():
    mutant = workflow_text().replace("'-v --durations=25'", "'-v'", 1)
    assert mutant != workflow_text(), "the plain run no longer asks for durations"
    problems = naming_problems(parse_workflow(mutant))
    assert any("--durations" in problem for problem in problems), problems


def test_mutant_a_dropped_shard_path_is_reported():
    """A test file no shard names never runs on the sharded lane."""
    mutant = workflow_text().replace('            paths: "tests/acceptance"\n', "", 1)
    assert mutant != workflow_text(), "the acceptance shard is gone"
    problems = shard_file_problems(parse_workflow(mutant))
    assert any("names no paths" in problem for problem in problems), problems


def test_mutant_a_test_file_in_two_shards_is_reported():
    """The same file in two shards is the cost the split exists to avoid."""
    mutant = workflow_text().replace(
        '            paths: "tests/acceptance"\n',
        '            paths: "tests/acceptance tests/unit/test_[a-f]*.py"\n',
        1,
    )
    assert mutant != workflow_text(), "the acceptance shard is gone"
    problems = shard_file_problems(parse_workflow(mutant))
    assert any("two shards" in problem for problem in problems), problems


def test_the_matrix_is_sized_to_the_portability_question(ci):
    """The interior interpreter and macOS run a subset; the boundaries run it all."""
    assert subset_problems(ci) == []
    assert parallel_problems(ci) == []
    full = [
        (str(entry.get("os")), str(entry.get("python-version")))
        for entry in matrix_entries(ci)
        if not entry.get("paths") and not entry.get("shard")
    ]
    assert full == list(FULL_SUITE_CELLS), full


def test_mutant_a_cell_without_xdist_is_reported():
    """A cell that still runs serially is exactly the wall clock T-0105 removes."""
    old = (
        '            python-version: "3.13"\n'
        "            coverage: false\n"
        '            xdist: "--numprocesses=auto"\n'
        "          # macOS runs"
    )
    assert workflow_text().count(old) == 1, "the ubuntu 3.13 row moved"
    mutant = workflow_text().replace(
        old, old.replace('            xdist: "--numprocesses=auto"\n', ""), 1
    )
    problems = parallel_problems(parse_workflow(mutant))
    assert any("pytest-xdist" in problem for problem in problems), problems


def test_mutant_a_macos_subset_without_the_portability_flow_is_reported():
    """macOS is a host the spaced-path/symlink/GNU-make guards exist for."""
    old = f'            paths: "{SUBSET_CELLS[("macos-latest", "3.13")]}"\n'
    assert workflow_text().count(old) == 1, "the macOS row moved"
    mutant = workflow_text().replace(old, f'            paths: "{SUBSET_PATHS}"\n', 1)
    problems = subset_problems(parse_workflow(mutant))
    assert any(PORTABILITY_FLOW in problem for problem in problems), problems


def test_the_header_states_each_subset_cell_as_its_row_does():
    """The header is the contract document; it may not restate a row differently."""
    problems = header_problems()
    assert problems == [], problems


def test_mutant_a_header_that_drops_the_portability_flow_is_reported():
    """A header naming the subset without the portability module is the refuted premise."""
    text = workflow_text()
    mutant = text.replace(
        "tests/integration/test_portability_flow.py` in full",
        "tests/acceptance` in full",
        1,
    )
    assert mutant != text, "the header's macOS subset sentence moved"
    problems = header_problems(mutant)
    assert any(PORTABILITY_FLOW in problem for problem in problems), problems


def test_mutant_a_boundary_interpreter_on_the_subset_is_reported():
    """A subset is only safe while another lane still runs the whole suite."""
    old = (
        '            python-version: "3.11"\n'
        "            coverage: true\n"
        '            xdist: "--numprocesses=auto"\n'
    )
    assert workflow_text().count(old) == 1, "the coverage row moved"
    mutant = workflow_text().replace(old, old + f'            paths: "{SUBSET_PATHS}"\n', 1)
    problems = subset_problems(parse_workflow(mutant))
    assert any("must run the whole suite" in problem for problem in problems), problems


CENSUS_DOCS = ("docs/Team/Architecture.md", "pyproject.toml")

CENSUS_WORDS = frozenset(
    {
        "test",
        "tests",
        "case",
        "cases",
        "run",
        "runs",
        "passed",
        "failed",
        "collected",
        "deselected",
        "skipped",
    }
)

CENSUS_EXEMPT_SPANS = (
    re.compile(r"\b\d+(?:\.\d+)?[\s-]?(?:ms|s|m|min|h|minutes?|hours?|seconds?)\b"),
    re.compile(r"\b[0-9a-f]{7,40}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\bpy\d+\.\d+\b"),
    re.compile(r"\b\d+\.\d+(?:\.\d+)?\b"),
    re.compile(r"\b\d{1,2}:\d{2}\b"),
    re.compile(r"\b\d+(?:\.\d+)?%"),
)

CENSUS_CLAUSE = re.compile(r"[|;()\[\].:?!]")

CENSUS_EDGE = "`'\"*_<>#-\u2014\u2013,;:.!?"

CENSUS_NUMERAL = re.compile(r"\d[\d,]*")


def _census_words(text: str) -> list[str]:
    return [token.strip(CENSUS_EDGE).lower() for token in text.split()]


def _bare_numeral(token: str) -> bool:
    stripped = token.strip(CENSUS_EDGE)
    return bool(CENSUS_NUMERAL.fullmatch(stripped))


CENSUS_DETERMINERS = frozenset(
    {
        "the",
        "this",
        "that",
        "these",
        "those",
        "its",
        "their",
        "our",
        "your",
        "his",
        "her",
        "any",
        "each",
        "every",
        "some",
        "all",
        "both",
        "no",
        "which",
        "whose",
    }
)


def _clause_states_a_census(clause: str) -> bool:
    tokens = _census_words(clause)
    for index, token in enumerate(tokens):
        if not _bare_numeral(token):
            continue
        for following in tokens[index + 1 :]:
            if following in CENSUS_DETERMINERS:
                break
            if following in CENSUS_WORDS:
                return True
    return False


def states_a_census(line: str) -> bool:
    """Default-deny: a census word after a bare numeral that is not an exempt form.

    The guard inverts the question (ruling D-0022(2)) instead of enumerating word
    orders: a line that carries a census word and a numeral fails unless every
    numeral on it belongs to a measurement form - a duration, a revision, a date,
    a version, a clock time or a percentage. No word order is enumerated, so no
    modifier count can leak: `2763 unit and integration tests` and `2763 a b c d e
    f g h i tests` both fail. The structure that remains is the word boundary and
    the phrase: a numeral is a whole token, so `developer-2`, `T-0042`, `argv[0]`
    and `--durations=25` carry none; a census word is a whole token, so
    `tests/unit/**` is a path and not a count; a numeral counts only forward, so
    `exit 0 when both land` and `-> 0 matches` are not a census; and a determiner
    ends the phrase, so `code 1 and the message that says to run` is not one.
    A count of tests is stale the moment a test lands, so a doc carries the
    comparison and the command instead (the CEO ruling on T-0105); a measurement
    with a unit stays, pinned to a revision and a date: `36s at f4cd508, 2026-11-11`.
    """
    if not any(character.isdigit() for character in line):
        return False
    if not CENSUS_WORDS.intersection(_census_words(line)):
        return False
    rest = line
    for exempt in CENSUS_EXEMPT_SPANS:
        rest = exempt.sub("", rest)
    return any(_clause_states_a_census(clause) for clause in CENSUS_CLAUSE.split(rest))


def census_problems(repo_root: Path = REPO_ROOT) -> list[str]:
    """A doc states no test census; it points at the command that re-reads it."""
    problems: list[str] = []
    for relative in CENSUS_DOCS:
        path = repo_root / relative
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if states_a_census(line):
                problems.append(f"{relative}:{number} states a test census: {line.strip()}")
    return problems


def test_no_doc_states_a_test_census():
    """The matrix section and the dev extra quote the comparison, not a count."""
    problems = census_problems()
    assert problems == [], problems


def test_mutant_a_census_number_in_a_doc_is_reported(tmp_path):
    """The shape that goes stale: a number followed by passed/collected/skipped."""
    for relative in CENSUS_DOCS:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text("the run gave 2751 passed\n", encoding="utf-8")
    problems = census_problems(tmp_path)
    assert len(problems) == len(CENSUS_DOCS), problems
    assert all("states a test census" in problem for problem in problems), problems
    (tmp_path / CENSUS_DOCS[0]).write_text(
        "the run gave 36s at `f4cd508`, 2026-11-11\n", encoding="utf-8"
    )
    assert [p for p in census_problems(tmp_path) if CENSUS_DOCS[0] in p] == []


CENSUS_SENTENCES = (
    "the tree collects 2763 tests",
    "the tree has 2763 tests",
    "the tree gives 2763 tests",
    "the tree reports 2763 tests",
    "the suite ran 2763 test cases",
    "2763 tests pass on every cell",
    "there are 2,763 passing tests",
    "the run recorded 12 failed",
    "2763 subprocess tests",
    "2763 cross-host tests",
    "2763 macOS tests",
    "2763 Windows tests",
    "2763 unit and integration tests",
    "the tree collects 2763 unit and integration tests",
    "the tree holds 2763 fast, offline end to end tests",
    "2763 a b c d e f g h i tests",
    "2763 alpha bravo charlie delta echo foxtrot golf hotel india tests",
    "3 shards run tests/integration",
    "the roster has 15 roles and 15 test layers",
)

CENSUS_FREE_SENTENCES = (
    "the run took 36s at `f4cd508`, 2026-11-11",
    "the parallel run gave 36s at f4cd508, 2026-11-11",
    "the tests run on py3.13 and 3.11",
    "the tests cover 81.68% of the source",
    "the tests pass at 0821fd42b95afba2adfcc221a54d695c21ea0ea4",
    "the tests finished at 12:41",
    "a hosted runner gives 3-4 vCPUs",
    "the `test` job is bounded at 90 minutes",
    "the integration tree (30% of the serial wall clock) runs on both boundaries",
    "the bound only stops a hung run",
    "tests/unit/test_ci_contracts.py asserts the matrix",
    "python 3.11, 3.12 and 3.13 test the same tree",
    "so the doc states no count and the two runs below are the check",
)


@pytest.mark.parametrize("sentence", CENSUS_SENTENCES)
def test_mutant_a_numeral_that_heads_the_test_noun_is_reported(tmp_path, sentence):
    """The verb and the modifiers are irrelevant: the numeral heads the noun."""
    for relative in CENSUS_DOCS:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(sentence + "\n", encoding="utf-8")
    problems = census_problems(tmp_path)
    assert len(problems) == len(CENSUS_DOCS), problems
    assert all("states a test census" in problem for problem in problems), problems
    (tmp_path / CENSUS_DOCS[0]).write_text(
        "so the doc states no count and the two runs below are the check\n", encoding="utf-8"
    )
    assert [p for p in census_problems(tmp_path) if CENSUS_DOCS[0] in p] == []


@pytest.mark.parametrize("sentence", CENSUS_FREE_SENTENCES)
def test_a_measurement_with_a_unit_is_not_a_census(tmp_path, sentence):
    """The inversion must not eat the numbers the doc is allowed to carry."""
    for relative in CENSUS_DOCS:
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(sentence + "\n", encoding="utf-8")
    assert census_problems(tmp_path) == [], sentence


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


def test_no_lane_opts_out_of_a_history_proof(ci):
    """The history gate is its own job, so the matrix has no history clause to drop.

    It used to: every test lane re-ran the traceability guard, which re-ran the
    privacy history scan, and the lanes that were not the coverage lane exported
    `TEAMWORK_CI_SKIP_HISTORY_PROOF=1` to drop it. That is the duplicate gate the
    throughput contract forbids and it is what pushed the Windows cell past its
    90-minute budget, so the guard exempts the row and the switch is gone.
    """
    for step in jobs(ci)["test"].get("steps") or []:
        env = step.get("env") or {}
        assert HISTORY_OPT_OUT not in env, (
            f"the test step {step.get('name')!r} still exports {HISTORY_OPT_OUT}: the history "
            "proof is the privacy job's, not the matrix's"
        )


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
        '            shard: "unit-a-f"\n'
        '            paths: "tests/unit/test_[a-f]*.py"\n'
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
