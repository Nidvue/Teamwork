"""Acceptance: the CI contract is a gate a user can run locally.

The promise a user relies on is *"the command CI runs is a command I can run, and
it gives me the same verdict"*. This file accepts that promise from the outside:

1. the workflow text names the same script the user runs, with the same mode, and
   the job is blocking (no ``continue-on-error``, no ``|| true``);
2. running that script in this tree exits ``0``;
3. a drifted tree exits ``1`` - and the reported finding names the drift;
4. a tree the gate cannot read exits ``2``, not ``0`` and not ``1``.

Every subject is a real subprocess; no engine internals are imported.

Owner: reviewer. Task: T-0003. Requirement: acceptance layer, area ``ci-contracts``.
"""

from __future__ import annotations

import re

from gate_fixtures import (
    CI_WORKFLOW,
    REPO_ROOT,
    commit_all,
    git,
    make_repo,
    run_checker,
    write_release_facts,
)

AREA = "ci-contracts"


def _release_consistency_job(text: str) -> str:
    """The ``release-consistency`` job block of ``ci.yml``, as text."""
    match = re.search(
        r"^  release-consistency:\n(.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "ci.yml carries no `release-consistency` job:\n" + text[:2000]
    # Only the executable substance: a comment that *says* the job is blocking is
    # not the job being blocking, so YAML comments are dropped before asserting.
    return "\n".join(
        line for line in match.group(0).splitlines() if not line.lstrip().startswith("#")
    )


def test_ci_runs_the_same_gate_the_user_runs():
    """ACCEPT: the CI job invokes the shipped checker offline, and it blocks."""
    job = _release_consistency_job(CI_WORKFLOW.read_text(encoding="utf-8"))

    assert "scripts/check_release_consistency.py" in job, job
    assert "--offline" in job, "the blocking CI gate must run the offline mode:\n" + job
    assert "continue-on-error" not in job, "a non-blocking consistency gate is not a gate:\n" + job
    assert "|| true" not in job, "a swallowed gate exit is not a gate:\n" + job

    # The script the job names is the one this test then runs in this tree.
    assert (REPO_ROOT / "scripts" / "check_release_consistency.py").is_file()


def test_clean_tree_accepts_with_exit_0():
    """ACCEPT: `python3 scripts/check_release_consistency.py --offline` -> exit 0."""
    proc = run_checker(REPO_ROOT, "--offline")

    assert proc.returncode == 0, (
        "the gate that CI blocks on disagrees with this tree; a user running the "
        f"same command is told the release is inconsistent:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "# release consistency: 0 problem(s)" in proc.stdout, proc.stdout
    assert "DRIFT" not in proc.stdout, proc.stdout


def test_drifted_tree_is_refused_with_exit_1(tmp_path):
    """ACCEPT: a tag that disagrees with the version in the tree exits 1."""
    repo = make_repo(tmp_path / "drifted")
    write_release_facts(repo)
    commit_all(repo)
    git(repo, "tag", "v1.0.0")
    # The drift: a new tag that claims a version the tree does not carry.
    git(repo, "tag", "v1.0.1")

    proc = run_checker(repo, "--offline")

    assert proc.returncode == 1, (
        "a tag claiming 1.0.1 on a tree that says 1.0.0 must be refused with exit 1 "
        f"(drift), got {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "R1 DRIFT" in proc.stdout, proc.stdout
    assert "v1.0.1: __version__ 1.0.0 != tag version 1.0.1" in proc.stdout, proc.stdout


def test_unreadable_tree_is_an_error_with_exit_2(tmp_path):
    """ACCEPT: an input that cannot be read exits 2 - never a pass, never drift."""
    repo = make_repo(tmp_path / "unreadable")
    write_release_facts(repo)
    commit_all(repo)
    git(repo, "tag", "v1.0.0")
    # The unreadable input: the version file the gate reads is gone at HEAD.
    git(repo, "rm", "-q", "src/teamwork/version.py")
    git(repo, "commit", "-qm", "drop the version file")

    proc = run_checker(repo, "--offline")

    assert proc.returncode == 2, (
        "an unreadable input must exit 2 (never 0 = pass, never 1 = drift), got "
        f"{proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "# release consistency: 0 problem(s)" in proc.stdout, (
        "the tree has no drift finding, yet the run must still fail:\n" + proc.stdout
    )
