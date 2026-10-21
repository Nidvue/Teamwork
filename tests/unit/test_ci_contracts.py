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
below reads the workflow and asserts one clause of the header's contract, and
each has a mutant twin that proves it bites (`test_..._mutant`): the mutant
applies one targeted edit to the workflow *text*, parses the result and asserts
the contract function reports a violation. Mutants are built in memory, so no
tracked file is ever written.

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

#: The job set the workflow header promises. Kept as an explicit tuple: a job that
#: appears or disappears without the contract changing is a reviewable event, not
#: a silent one.
#: Workflow- and trigger-level filters that decide whether the workflow runs at
#: all. Both are forbidden here; the `scope` job does the classifying.
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
)

#: Jobs that are cheap and unconditional by design: `scope` only classifies paths,
#: `committer-guard` is one git call that must fire on every push, and
#: `release-consistency` is the gate that must never be skipped.
UNCONDITIONAL_JOBS = ("scope", "committer-guard", "release-consistency")

#: The `if:` guard that ties an expensive job to the `scope` job's output.
SCOPE_GUARD = "needs.scope.outputs.code"


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


def contract_problems(document: dict) -> list[str]:
    """Every clause of the header's contract that the given document violates."""
    problems: list[str] = []
    found = jobs(document)

    if tuple(found) != EXPECTED_JOBS:
        problems.append(f"job set is {tuple(found)}, contract says {EXPECTED_JOBS}")

    # A workflow-level path filter is the defect this file exists to keep out: a
    # prose-only push would skip the release-consistency gate.
    triggers = document.get("on") or document.get(True) or {}
    for filter_key in PATH_FILTERS:
        # A filter written at the `on:` level applies to every trigger - the shape
        # `paths-ignore` had when it silently skipped the gate on a prose push.
        if filter_key in triggers:
            problems.append(f"on carries {filter_key}, so a push can skip every job")
    for trigger, spec in triggers.items():
        if not isinstance(spec, dict):
            continue
        for filter_key in PATH_FILTERS:
            if filter_key in spec:
                problems.append(f"on.{trigger} carries {filter_key}, so a push can skip every job")

    # The gate must be unconditional: no `needs:` it could be skipped with, no `if:`.
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

    # Every other job is expensive and must (a) wait for `scope` and (b) read its
    # output, so a prose-only push skips the matrix instead of the gate.
    for name, job in found.items():
        if name in UNCONDITIONAL_JOBS:
            continue
        if "scope" not in needs_of(job):
            problems.append(f"{name} does not declare `needs: scope`")
        guard = str(job.get("if") or "")
        if SCOPE_GUARD not in guard:
            problems.append(f"{name} has no `if:` guard on {SCOPE_GUARD}: {guard!r}")
    return problems


@pytest.fixture(scope="module")
def ci() -> dict:
    return workflow()


def test_the_workflow_declares_the_contracted_job_set(ci):
    assert tuple(jobs(ci)) == EXPECTED_JOBS


def test_the_release_consistency_gate_is_unconditional(ci):
    """No `needs:` and no `if:`: the gate cannot be skipped by a sibling job."""
    gate = jobs(ci)["release-consistency"]
    assert "needs" not in gate, f"release-consistency declares needs={gate.get('needs')!r}"
    assert "if" not in gate, f"release-consistency declares if={gate.get('if')!r}"


def test_every_expensive_job_is_gated_on_the_scope_output(ci):
    """The 3x3 matrix and the packaging jobs must be skippable; nothing else must."""
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


def test_every_job_contract_clause_holds_for_the_real_workflow(ci):
    assert contract_problems(ci) == []


# --------------------------------------------------------------------------- #
# Mutants: each one breaks exactly one clause and must be reported
# --------------------------------------------------------------------------- #


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
            break  # the next top-level job begins
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
