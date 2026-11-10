"""Acceptance: a release cannot be published without the consistency gate.

The promise of ``.github/workflows/release.yml`` is structural *and* behavioural:

* **structural** - the publishing job's ``needs:`` reaches the ``consistency`` job
  transitively, so GitHub's dependency graph refuses to even start a publish on a
  tree the gate has not judged;
* **behavioural** - the gate step's own script (the inline ``python3 - <<'PY'``
  block, extracted verbatim from the workflow) refuses a missing checker, refuses
  a tag that does not point at HEAD, refuses drift, and accepts a clean report.

The rehearsal runs that extracted block offline against a throwaway repository
with a stub checker, so the accepted behaviour is the workflow's, not a
re-implementation of it. Nothing here needs the network.

Owner: reviewer. Task: T-0003. Requirement: acceptance layer, area
``release-workflow``.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

from cli_harness import REPO_ROOT, build_env
from gate_fixtures import RELEASE_WORKFLOW, commit_all, git, make_repo, write_release_facts

AREA = "release-workflow"
TAG = "v1.0.0"


def _jobs() -> dict[str, dict]:
    """Parse the workflow's jobs (2-space map keys) without a YAML dependency."""
    jobs: dict[str, dict] = {}
    current = None
    in_jobs = False
    for line in RELEASE_WORKFLOW.read_text(encoding="utf-8").splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            current = jobs.setdefault(match.group(1), {"needs": []})
            continue
        if current is None:
            continue
        needs = re.match(r"^    needs:\s*(.+)$", line)
        if needs:
            raw = needs.group(1).strip()
            raw = raw.strip("[]")
            current["needs"] = [
                part.strip().strip("'\"") for part in raw.split(",") if part.strip()
            ]
    return jobs


def _gate_block() -> str:
    """The pre-publish gate step: the first inline ``python3 - <<'PY'`` block."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    blocks = re.findall(r"python3 - <<'PY'\n(.*?)\n\s*PY\n", text, re.DOTALL)
    assert blocks, "release.yml carries no inline gate block"
    return textwrap.dedent(blocks[0])


def _rehearse(repo: Path, *, tag: str = TAG) -> subprocess.CompletedProcess:
    """Run the workflow's gate block in ``repo``, offline."""
    script = repo / "gate-step.py"
    script.write_text(_gate_block(), encoding="utf-8")
    env = build_env({"RELEASE_TAG": tag, "RELEASE_GATE_RETRY_SECONDS": "0"})
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    return subprocess.run(
        [sys.executable, "gate-step.py"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _fixture(tmp_path: Path, verdict: str | None = None) -> Path:
    """A tagged fixture release tree, optionally with a stub checker in place.

    The tag is created *after* every file is committed: the gate refuses a tag
    that does not point at HEAD, so committing the stub last would rehearse the
    wrong refusal.
    """
    repo = make_repo(tmp_path / "release")
    write_release_facts(repo, version="1.0.0", changelog_sections=("1.0.0",))
    if verdict is not None:
        _write_stub_checker(repo, verdict)
    commit_all(repo)
    git(repo, "tag", TAG)
    return repo


def _write_stub_checker(repo: Path, verdict: str) -> None:
    """Install a checker that prints the JSON verdict ``_emit`` prints."""
    payloads = {
        "clean": '{"problems": [], "rules": [{"id": "R1", "status": "ok", "detail": "ok"}], '
        '"exit_code": 0}',
        "drift": '{"problems": [{"rule": "R1", "detail": "v1.0.0: drifted"}], '
        '"rules": [{"id": "R1", "status": "DRIFT", "detail": "v1.0.0: drifted"}], "exit_code": 1}',
    }
    code = 0 if verdict == "clean" else 1
    scripts = repo / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "check_release_consistency.py").write_text(
        f"import json, sys\nprint({payloads[verdict]!r})\nraise SystemExit({code})\n",
        encoding="utf-8",
    )


def test_publish_job_needs_the_gate_transitively():
    """ACCEPT: `release` cannot run unless `consistency` succeeded."""
    jobs = _jobs()

    assert "consistency" in jobs, sorted(jobs)
    assert {"build", "attest", "release"} <= set(jobs), sorted(jobs)

    def ancestors(job: str) -> set[str]:
        seen: set[str] = set()
        stack = list(jobs[job]["needs"])
        while stack:
            name = stack.pop()
            if name in seen:
                continue
            assert name in jobs, f"{job} needs unknown job {name!r}"
            seen.add(name)
            stack.extend(jobs[name]["needs"])
        return seen

    for job in ("build", "attest", "release"):
        assert "consistency" in ancestors(job), (
            f"the {job!r} job does not depend on 'consistency'; a release could be "
            f"published from a tree the gate never judged (needs={jobs[job]['needs']})"
        )


def test_gate_is_not_optional_in_the_workflow_text():
    """ACCEPT: the gate is fail-closed - no swallow, no continue-on-error."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "check_release_consistency.py" in code
    assert "continue-on-error" not in code, "a non-blocking release gate is not a gate"
    # No step may discard the checker's exit code. (`|| true` is legitimate on
    # the unrelated `grep -c` that counts tags, so the assertion is scoped to the
    # lines that invoke the gate.)
    gate_lines = [line for line in code.splitlines() if "check_release_consistency" in line]
    assert gate_lines, code
    for line in gate_lines:
        assert "|| true" not in line and "|| :" not in line, (
            f"the gate's exit code is discarded here: {line.strip()}"
        )


def test_rehearsal_refuses_a_missing_checker(tmp_path):
    """ACCEPT: no checker in the tree -> exit 2, never a green release."""
    repo = _fixture(tmp_path)

    proc = _rehearse(repo)

    assert proc.returncode == 2, (
        f"a release tree without the checker must be refused (exit 2), got {proc.returncode}:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    assert "is missing: the release gate cannot be skipped" in proc.stderr, proc.stderr


def test_rehearsal_refuses_a_tag_that_is_not_at_head(tmp_path):
    """ACCEPT: the gate judges the revision being tagged, or it refuses."""
    repo = _fixture(tmp_path, "clean")
    # A tag that does not point at HEAD: tag the first commit, then move HEAD on.
    first = git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.strip()
    git(repo, "tag", "v1.0.1", first)
    commit_all(repo, "a later commit the tag does not cover", allow_empty=True)

    proc = _rehearse(repo, tag="v1.0.1")

    assert proc.returncode == 2, f"{proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    assert "does not point at HEAD" in proc.stderr, proc.stderr


def test_rehearsal_refuses_drift_and_accepts_a_clean_report(tmp_path):
    """ACCEPT: drift -> exit 1; a clean JSON verdict -> exit 0. Same block."""
    drifted = _fixture(tmp_path / "drifted", "drift")
    refused = _rehearse(drifted)

    assert refused.returncode == 1, (
        f"drift must fail the release gate with exit 1, got {refused.returncode}:\n"
        f"{refused.stdout}\n{refused.stderr}"
    )
    assert "R1 DRIFT: v1.0.0: drifted" in refused.stderr, refused.stderr

    clean = _fixture(tmp_path / "clean", "clean")
    accepted = _rehearse(clean)

    assert accepted.returncode == 0, (
        f"a clean report must let the release through, got {accepted.returncode}:\n"
        f"{accepted.stdout}\n{accepted.stderr}"
    )
    assert "R1 ok ok" in accepted.stdout, accepted.stdout


def test_the_rehearsal_uses_the_shipped_workflow_file():
    """ACCEPT: the block under test is this repository's, not a copy of it."""
    assert RELEASE_WORKFLOW == REPO_ROOT / ".github" / "workflows" / "release.yml"
    assert os.access(RELEASE_WORKFLOW, os.R_OK)
    block = _gate_block()
    assert 'CHECKER = "scripts/check_release_consistency.py"' in block, block[:400]
