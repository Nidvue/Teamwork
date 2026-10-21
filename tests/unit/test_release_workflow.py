"""The release workflow cannot publish a revision the consistency gate rejected.

Why this exists: `scripts/check_release_consistency.py` is graded, but nothing is
published by the checker itself - `.github/workflows/release.yml` decides. A job
that publishes must therefore sit *downstream* of the `consistency` job in the
graph, and the graph is the only place that ordering cannot be edited away by a
comment. This file grades the graph:

* the `consistency` job exists and is unconditional (a gate that can be skipped
  is not a gate);
* every job that publishes (creates a Release, uploads release assets, or holds
  `contents: write`) either *is* the gate or needs it, directly or transitively;
* no publisher widens its trigger with `if: always()` / `if: failure()` /
  `continue-on-error`, which would let it run after the gate failed;
* every checkout claims the complete tag set (`fetch-depth: 0`), because the
  tag rules R1/R2/R4/R5 are vacuous on a shallow clone - measured in the
  workflow's own header comment and in Architecture.md section 11.2.2;
* the post-publish re-check exists (R5 can only be judged after the Release is
  created) and it is the same checker, not a second implementation.

The publisher set is *computed* from what each job actually does, not hard-coded:
a new job that uses `softprops/action-gh-release` or asks for `contents: write`
joins the graded set automatically. A test asserts the computed set is non-empty,
so a workflow with no publishers at all cannot make the invariant vacuous.

Mutants edit the parsed workflow in memory (or a `tmp_path` copy of the YAML
text) and re-run the same analysis, so the tracked workflow is never written.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from workflow_yaml import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_PATH = ".github/workflows/release.yml"
GATE_JOB = "consistency"

#: Actions that put something in front of the world.
PUBLISH_ACTIONS = {
    "softprops/action-gh-release",
    "actions/create-release",
    "gh-release",
    "pypa/gh-action-pypi-publish",
    "actions/upload-release-asset",
    "docker/build-push-action",
}

#: Conditions that make a job run *despite* a failed dependency.
BYPASS_IF_RE = r"always\(\)|failure\(\)|cancelled\(\)"


def release_text(repo_root: Path = REPO_ROOT) -> str:
    return (repo_root / RELEASE_PATH).read_text(encoding="utf-8")


def release(repo_root: Path = REPO_ROOT) -> dict:
    return parse_workflow(release_text(repo_root))


def jobs(document: dict) -> dict:
    found = document.get("jobs")
    assert isinstance(found, dict) and found, "the release workflow declares no jobs"
    return found


def needs_of(job: dict) -> list[str]:
    needs = job.get("needs")
    if needs is None:
        return []
    if isinstance(needs, str):
        return [needs]
    assert isinstance(needs, list), f"needs: {needs!r} is neither a string nor a list"
    return [str(item) for item in needs]


def dangling_needs(document: dict) -> list[str]:
    """`needs:` entries that name a job the workflow does not declare.

    GitHub rejects such a workflow, but the local parse would still show the edge
    and a reader could believe the ordering holds. A dropped job must be reported,
    not silently satisfied by a leftover reference to it.
    """
    declared = set(jobs(document))
    return sorted(
        f"{name} -> {parent}"
        for name, job in jobs(document).items()
        for parent in needs_of(job)
        if parent not in declared
    )


def blocked_by(gate: str, job_name: str, document: dict) -> bool:
    """Is `job_name` downstream of the *existing* `gate` job (or the gate itself)?"""
    if gate not in jobs(document):
        return False
    if job_name == gate:
        return True
    seen: set[str] = set()
    frontier = [job_name]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        job = jobs(document).get(current) or {}
        for parent in needs_of(job):
            if parent == gate:
                return True
            frontier.append(parent)
    return False


def actions_of(job: dict) -> list[str]:
    out: list[str] = []
    for step in job.get("steps") or []:
        if isinstance(step, dict) and isinstance(step.get("uses"), str):
            out.append(step["uses"])
    return out


def action_name(spec: str) -> str:
    """`owner/repo@sha # v7` -> `owner/repo`."""
    return spec.split("@", 1)[0].strip()


def permissions_of(job: dict) -> dict:
    perms = job.get("permissions")
    return perms if isinstance(perms, dict) else {}


def publishes(job: dict) -> bool:
    """Computed, not declared: what does this job actually do to the world?"""
    if any(action_name(spec) in PUBLISH_ACTIONS for spec in actions_of(job)):
        return True
    if str(permissions_of(job).get("contents", "")).strip() == "write":
        return True
    # An upload of the release asset bundle is a publish step only when it goes
    # to a Release; `actions/upload-artifact` feeds the job that does that, so it
    # is not counted here (the job that consumes it is).
    return False


def publishers(document: dict) -> list[str]:
    return sorted(name for name, job in jobs(document).items() if publishes(job))


def checkouts(job: dict) -> list[dict]:
    """The `with:` mapping of every `actions/checkout` step in a job."""
    out: list[dict] = []
    for step in job.get("steps") or []:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if isinstance(uses, str) and action_name(uses) == "actions/checkout":
            with_ = step.get("with")
            out.append(with_ if isinstance(with_, dict) else {})
    return out


def bypass_problems(document: dict) -> list[str]:
    """Publishers that can run although the gate failed."""
    problems: list[str] = []
    for name in publishers(document):
        job = jobs(document)[name]
        if not blocked_by(GATE_JOB, name, document):
            problems.append(f"{name}: publishes but does not need {GATE_JOB}")
        condition = str(job.get("if") or "")
        if any(token in condition for token in ("always()", "failure()", "cancelled()")) or any(
            token in condition for token in ("!cancelled()", "!failure()")
        ):
            problems.append(f"{name}: publishes under a bypassing condition {condition!r}")
        if job.get("continue-on-error") in (True, "true"):
            problems.append(f"{name}: publishes with continue-on-error")
        for step in job.get("steps") or []:
            if isinstance(step, dict) and step.get("continue-on-error") in (True, "true"):
                problems.append(f"{name}: publish step {step.get('name')!r} ignores its failure")
    return problems


def shallow_checkouts(document: dict) -> list[str]:
    """checkout steps whose `fetch-depth` is not `0`."""
    problems: list[str] = []
    for name, job in jobs(document).items():
        for index, with_ in enumerate(checkouts(job)):
            depth = str(with_.get("fetch-depth", "")).strip()
            if depth != "0":
                problems.append(f"{name}: checkout #{index} has fetch-depth {depth or '<unset>'}")
    return problems


def gate_reachable(document: dict) -> list[str]:
    """Jobs that run the consistency checker itself."""
    return sorted(
        name
        for name, job in jobs(document).items()
        if any(
            "check_release_consistency.py" in str(step.get("run") or "")
            for step in job.get("steps") or []
            if isinstance(step, dict)
        )
    )


# --------------------------------------------------------------------------- #
# the real workflow
# --------------------------------------------------------------------------- #


def test_the_gate_job_exists_and_is_unconditional():
    document = release()
    assert GATE_JOB in jobs(document), sorted(jobs(document))
    gate = jobs(document)[GATE_JOB]
    assert needs_of(gate) == [], f"{GATE_JOB} has dependencies and can be skipped: {needs_of(gate)}"
    assert "if" not in gate, f"{GATE_JOB} is conditional: {gate.get('if')!r}"


def test_the_build_depends_on_the_gate():
    build = jobs(release()).get("build")
    assert isinstance(build, dict), sorted(jobs(release()))
    assert GATE_JOB in needs_of(build), needs_of(build)


def test_no_publisher_can_run_when_the_gate_failed():
    document = release()
    names = publishers(document)
    assert names, "no publishing job was recognised - the invariant would be vacuous"
    assert dangling_needs(document) == []
    assert bypass_problems(document) == []


def test_every_publisher_is_downstream_of_the_gate():
    document = release()
    for name in publishers(document):
        assert blocked_by(GATE_JOB, name, document), f"{name}: {needs_of(jobs(document)[name])}"


def test_every_checkout_fetches_the_complete_tag_set():
    assert shallow_checkouts(release()) == []


def test_both_gate_runs_use_the_one_checker():
    """The pre-publish gate and the post-publish re-check share the script."""
    reachable = gate_reachable(release())
    assert GATE_JOB in reachable, reachable
    assert len(reachable) >= 2, f"no post-publish re-check found: {reachable}"
    steps = [
        step["run"]
        for job in jobs(release()).values()
        for step in job.get("steps") or []
        if isinstance(step, dict) and "CHECKER" in str(step.get("run") or "")
    ]
    assert len(steps) == 2, f"expected exactly two checker invocations, found {len(steps)}"
    for snippet in steps:
        assert 'CHECKER = "scripts/check_release_consistency.py"' in snippet


def test_the_release_job_rechecks_after_it_publishes():
    document = release()
    release_job = jobs(document)["release"]
    step_names = [
        str(step.get("name") or "")
        for step in release_job.get("steps") or []
        if isinstance(step, dict)
    ]
    steps = [step for step in release_job.get("steps") or [] if isinstance(step, dict)]
    publish_index = next(
        index
        for index, step in enumerate(steps)
        if action_name(str(step.get("uses") or "")) in PUBLISH_ACTIONS
    )
    recheck_index = next(
        index
        for index, step in enumerate(steps)
        if "check_release_consistency.py" in str(step.get("run") or "")
    )
    assert recheck_index > publish_index, (
        f"the re-check runs before the publish; steps: {step_names}"
    )


def test_the_analysis_sees_the_workflow_it_claims_to_grade():
    """Guard against a parser that silently reads nothing."""
    document = release()
    assert set(jobs(document)) == {"consistency", "build", "attest", "release"}
    assert publishers(document) == ["release"], publishers(document)
    assert len(checkouts(jobs(document)["consistency"])) == 1
    assert needs_of(jobs(document)["attest"]) == ["build"]
    assert set(needs_of(jobs(document)["release"])) == {"build", "attest"}


# --------------------------------------------------------------------------- #
# mutants
# --------------------------------------------------------------------------- #


def test_mutant_a_publisher_that_does_not_need_the_gate_is_reported():
    document = release()
    document["jobs"]["release"]["needs"] = ["attest"]
    document["jobs"]["attest"]["needs"] = []
    problems = bypass_problems(document)
    assert any("does not need consistency" in problem for problem in problems), problems


def test_mutant_a_publisher_with_always_is_reported():
    document = release()
    document["jobs"]["release"]["if"] = "always()"
    problems = bypass_problems(document)
    assert any("bypassing condition" in problem for problem in problems), problems


def test_mutant_a_continue_on_error_publish_step_is_reported():
    document = release()
    for step in document["jobs"]["release"]["steps"]:
        if isinstance(step, dict) and action_name(str(step.get("uses") or "")) in PUBLISH_ACTIONS:
            step["continue-on-error"] = True
    problems = bypass_problems(document)
    assert any("ignores its failure" in problem for problem in problems), problems


def test_mutant_a_shallow_checkout_is_reported():
    document = release()
    document["jobs"]["consistency"]["steps"][0]["with"]["fetch-depth"] = "1"
    problems = shallow_checkouts(document)
    assert any("fetch-depth 1" in problem for problem in problems), problems


def test_mutant_a_dropped_fetch_depth_is_reported():
    document = release()
    del document["jobs"]["build"]["steps"][0]["with"]["fetch-depth"]
    assert any("unset" in problem for problem in shallow_checkouts(document))


def test_mutant_a_dropped_gate_job_is_reported(tmp_path):
    text = release_text()
    start = text.index("  consistency:\n")
    end = text.index("  build:\n")
    mutated = text[:start] + text[end:]
    (tmp_path / "release.yml").write_text(mutated, encoding="utf-8")
    document = parse_workflow((tmp_path / "release.yml").read_text(encoding="utf-8"))
    assert GATE_JOB not in jobs(document)
    assert not blocked_by(GATE_JOB, "release", document)
    # The leftover `needs: [consistency]` must be reported, not read as an edge.
    assert "build -> consistency" in dangling_needs(document), dangling_needs(document)
    assert bypass_problems(document), "a dangling publisher dependency must be reported"


def test_mutant_a_second_checker_implementation_is_not_accepted(tmp_path):
    """A re-check that runs something else would grade a different script."""
    text = release_text().replace(
        'CHECKER = "scripts/check_release_consistency.py"',
        'CHECKER = "scripts/other_checker.py"',
    )
    assert text != release_text()
    (tmp_path / "release.yml").write_text(text, encoding="utf-8")
    document = parse_workflow(text)
    reachable = gate_reachable(document)
    assert GATE_JOB not in reachable, reachable


@pytest.mark.parametrize(
    "condition",
    ["always()", "failure()", "!cancelled()"],
)
def test_each_bypassing_condition_is_recognised(condition):
    document = release()
    document["jobs"]["release"]["if"] = condition
    assert bypass_problems(document), condition
