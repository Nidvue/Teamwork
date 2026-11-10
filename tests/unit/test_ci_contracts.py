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

#: The second answer the classifier publishes: the change set is prose/media only.
PROSE_GUARD = "needs.scope.outputs.prose"

#: The `scope` outputs and the step output each one reads. Both must be published:
#: "does this ship?" and "is this prose?" are different questions with different
#: gates behind them, and collapsing them into one output makes one of the two
#: gates wrong in one direction.
SCOPE_OUTPUTS = {
    "code": "steps.diff.outputs.code",
    "prose": "steps.diff.outputs.prose",
}

#: A prose edit cannot change what the matrix measures, so these jobs read `code`
#: alone - a prose-only push must not burn the 3x3 matrix.
CODE_ONLY_JOBS = ("lint", "typecheck", "test", "build")

#: A documentation leak is still a leak, and link health is about the prose itself,
#: so these two read `code || prose`.
CODE_OR_PROSE_JOBS = ("privacy", "docs")


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

    # The classifier answers two questions, so each guard must ask the right one.
    # A `privacy` or `docs` guard that reads `code` alone skips exactly the
    # prose-only push those gates exist for; a matrix job that reads `prose` too
    # burns the 3x3 matrix on a documentation edit.
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


# --------------------------------------------------------------------------- #
# R2's scope flag (11.2.2.1, D-20261029-Architect)
# --------------------------------------------------------------------------- #

#: The flag 11.2.2.1 adds to the checker. A gate that forgets it is still
#: *evaluated* (the checker's default is `yes`), so forgetting is a false red on
#: every pull request, not a green: the fail-closed default is what makes this
#: wiring a convenience rather than the contract.
SCOPE_FLAG = "--head-is-default-branch"

#: The only scope expression the workflow may use: a pull request publishes
#: nothing (`no`), every other event publishes (`yes`). Matched exactly, with both
#: arms captured, so a flipped pair is a visible edit rather than a silent one.
SCOPE_EXPRESSION = re.compile(
    r"^\$\{\{\s*github\.event_name\s*==\s*'pull_request'\s*&&\s*'(yes|no)'\s*\|\|\s*'(yes|no)'\s*\}\}$"
)

#: The flag's value must be one environment expansion, never a literal or a
#: shell `if`: both arms stay in one place a reviewer can read.
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
    # Both literals stay in the workflow, in one expression a reader can grep.
    assert workflow_text().count("github.event_name == 'pull_request' && 'no' || 'yes'") == 1


def test_the_r2_scope_wiring_holds_for_the_real_workflow(ci):
    assert scope_problems(ci) == []


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
