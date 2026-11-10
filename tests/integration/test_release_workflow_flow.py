"""Integration: the release pipeline's local contract, driven as a subprocess.

``.github/workflows/release.yml`` does not run the checker and trust its exit
code: the ``consistency`` job wraps it in a Python block that asserts the tag
being published points at HEAD, maps the checker's exit codes (0/1/2) and
applies exactly one narrow exemption (the R5 finding for the tag being
published). That glue is the thing that decides whether a release is published,
and no layer exercised it.

This module extracts that block from the real workflow and runs it with
``python3 -`` against fixture repositories under ``tmp_path``, so the code under
test is the shipped text, not a copy of it.

Two halves:

* with the *real* checker, offline (``--online`` is replaced by ``--offline``
  in the extracted copy, because the online rules need the npm registry, the
  GitHub API and PyPI - those are marked NOT RUN, see
  ``test_the_online_gate_is_not_run_here``): the refusal and acceptance paths
  are exercised on their exit codes;
* with a *stand-in* checker that prints a chosen report, the exemption logic is
  exercised - the real checker cannot produce an R5 finding offline.

Owner: tester. Task: T-0004.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
CHECKER = REPO_ROOT / "scripts" / "check_release_consistency.py"

GIT_OPTIONS = (
    "-c",
    "user.email=tester@agents.nidvue.com",
    "-c",
    "user.name=Tester",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "tag.gpgSign=false",
)

VERSION_FILE = '__version__ = "{}"\nDIST_NAME = "teamwork-agents"\n'


# --------------------------------------------------------------------------- #
# Extracting the shipped gate block
# --------------------------------------------------------------------------- #


def extract_gate_block(workflow: Path = RELEASE_WORKFLOW) -> str:
    """The Python body of the release workflow's ``consistency`` gate step.

    The block is a ``python3 - <<'PY'`` heredoc; it ends at the matching
    ``PY``. It is dedented to column 0 and returned verbatim otherwise.
    """
    lines = workflow.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "python3 - <<'PY'"),
        None,
    )
    assert start is not None, f"{workflow}: no 'python3 - <<PY' heredoc"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "PY"), None)
    assert end is not None, f"{workflow}: the heredoc is not closed"
    body = lines[start + 1 : end]
    indent = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    code = "\n".join(line[indent:] if line.strip() else "" for line in body) + "\n"
    for marker in ("RELEASE_TAG", "CHECKER", "git", "tag", "points-at"):
        assert marker in code, f"extracted block is not the release gate: no {marker!r}"
    return code


def offline_gate_block() -> str:
    """The same block with the network half switched off, and why.

    NOT a silent weakening: ``--offline`` makes R3/R4/R5/R8 SKIP with a reason
    (the checker's own documented behaviour), so the exit-code mapping, the
    tag-at-HEAD assertion and the missing-checker refusal are all still
    exercised - nothing here touches a socket.
    """
    code = extract_gate_block()
    assert '"--online"' in code, "the gate no longer passes --online"
    return code.replace('"--online"', '"--offline"')


# --------------------------------------------------------------------------- #
# Fixture repositories
# --------------------------------------------------------------------------- #


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout.strip()


def make_release_tree(
    root: Path,
    *,
    version: str = "1.0.0",
    tag: str = "v1.0.0",
    with_checker: bool = True,
) -> Path:
    """A tagged checkout that looks like the release workflow's ``actions/checkout``."""
    (root / "src" / "teamwork").mkdir(parents=True)
    (root / "src" / "teamwork" / "version.py").write_text(
        VERSION_FILE.format(version), encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}]\n\n- initial\n", encoding="utf-8"
    )
    (root / "release-exceptions.json").write_text("[]\n", encoding="utf-8")
    (root / "README.md").write_text("# Teamwork\n", encoding="utf-8")
    if with_checker:
        (root / "scripts").mkdir()
        shutil.copy2(CHECKER, root / "scripts" / CHECKER.name)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "release")
    git(root, "tag", tag)
    return root


def install_stand_in_checker(root: Path, report: dict, exit_code: int) -> None:
    """Replace the checker with a script that prints ``report`` and exits ``exit_code``.

    The subject of these tests is the workflow's own logic (tag assertion,
    exit-code mapping, exemption narrowness), not the checker - that one is
    proven for real in ``tests/integration/test_release_gate_flow.py``. A
    stand-in is the only way to drive the R5 exemption offline.
    """
    path = root / "scripts" / CHECKER.name
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report)
    path.write_text(
        "import json\n"
        "import sys\n"
        f"sys.stdout.write({payload!r} + '\\n')\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )


def run_gate(root: Path, code: str, tag: str = "v1.0.0") -> tuple[int, str]:
    """Run the extracted gate block inside ``root`` with ``RELEASE_TAG=tag``."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env["RELEASE_TAG"] = tag
    # The gate retries an unreadable input three times, sleeping 20s between
    # attempts; the retry policy is not what these tests measure.
    env["RELEASE_GATE_RETRY_SECONDS"] = "0"
    result = subprocess.run(
        [sys.executable, "-"],
        cwd=str(root),
        env=env,
        input=code,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


# --------------------------------------------------------------------------- #
# The real checker, offline: refuse and accept
# --------------------------------------------------------------------------- #


def test_the_gate_accepts_a_consistent_tagged_checkout(tmp_path: Path) -> None:
    root = make_release_tree(tmp_path / "consistent")

    code, output = run_gate(root, offline_gate_block())

    assert code == 0, output
    assert "R1 ok" in output
    assert "R2 ok" in output


def test_the_gate_refuses_a_checkout_whose_version_disagrees_with_its_tag(
    tmp_path: Path,
) -> None:
    """The consistency gate is not recorded: R1 drift must block the release."""
    root = make_release_tree(tmp_path / "drifted", version="1.0.0", tag="v1.0.0")
    # The tag points at HEAD, so R2 is silent (`S = A - O`); version.py no
    # longer carries the released version, which is exactly R1's subject.
    (root / "src" / "teamwork" / "version.py").write_text(
        VERSION_FILE.format("0.9.0"), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "wrong version")
    git(root, "tag", "-f", "v1.0.0")

    code, output = run_gate(root, offline_gate_block())

    assert code == 1, output
    assert "R1 DRIFT" in output
    assert "!= tag version 1.0.0" in output


def test_the_gate_refuses_when_the_published_tag_does_not_point_at_head(
    tmp_path: Path,
) -> None:
    """Otherwise the gate would judge a revision that is not being released."""
    root = make_release_tree(tmp_path / "wrongtag")
    git(root, "tag", "v1.0.1")  # RELEASE_TAG below names v1.0.0

    code, output = run_gate(root, offline_gate_block(), tag="v9.9.9")

    assert code == 2, output
    assert "does not point at HEAD" in output


def test_the_gate_refuses_when_the_checker_is_absent(tmp_path: Path) -> None:
    """A gate that is silently absent is a gate that is silently green."""
    root = make_release_tree(tmp_path / "nochecker", with_checker=False)

    code, output = run_gate(root, offline_gate_block())

    assert code == 2, output
    assert "is missing: the release gate cannot be skipped" in output


def test_the_gate_refuses_an_unreadable_input_exit_2(tmp_path: Path) -> None:
    root = make_release_tree(tmp_path / "unreadable")
    install_stand_in_checker(root, {"problems": [], "rules": [], "exit_code": 2}, 2)

    code, output = run_gate(root, offline_gate_block())

    assert code == 2, output
    assert "could not be read" in output


def test_an_unexpected_exit_code_is_refused_not_treated_as_pass(tmp_path: Path) -> None:
    root = make_release_tree(tmp_path / "weird")
    install_stand_in_checker(root, {"problems": [], "rules": [], "exit_code": 7}, 7)

    code, output = run_gate(root, offline_gate_block())

    assert code == 2, output
    assert "unexpected exit code" in output


# --------------------------------------------------------------------------- #
# The exemption: exactly the R5 finding of the tag being published
# --------------------------------------------------------------------------- #


def r5_report(tag: str) -> dict:
    return {
        "problems": [{"rule": "R5", "detail": f"tag {tag} has no GitHub Release"}],
        "rules": [{"id": "R5", "status": "DRIFT", "detail": f"tag {tag} has no GitHub Release"}],
        "exit_code": 1,
    }


def test_the_tag_being_published_is_exempt_from_its_own_r5_finding(tmp_path: Path) -> None:
    """The Release is created *after* this gate, so it cannot exist yet."""
    root = make_release_tree(tmp_path / "exempt")
    install_stand_in_checker(root, r5_report("v1.0.0"), 1)

    code, output = run_gate(root, offline_gate_block())

    assert code == 0, output
    assert "expected on a tag push, checked again later" in output


def test_the_exemption_does_not_cover_another_tag(tmp_path: Path) -> None:
    """Widen the exemption and this test fails: only the published tag is excused."""
    root = make_release_tree(tmp_path / "othertag")
    install_stand_in_checker(root, r5_report("v0.9.0"), 1)

    code, output = run_gate(root, offline_gate_block())

    assert code == 1, output
    assert "R5 DRIFT" in output


def test_the_exemption_does_not_cover_another_rule(tmp_path: Path) -> None:
    root = make_release_tree(tmp_path / "otherrule")
    report = {
        "problems": [{"rule": "R2", "detail": "HEAD version 1.0.0 is not greater than tag v1.0.0"}],
        "rules": [{"id": "R2", "status": "DRIFT", "detail": "drift"}],
        "exit_code": 1,
    }
    install_stand_in_checker(root, report, 1)

    code, output = run_gate(root, offline_gate_block())

    assert code == 1, output
    assert "R2 DRIFT" in output


# --------------------------------------------------------------------------- #
# The gate must bite: mutate the shipped block and watch it accept drift
# --------------------------------------------------------------------------- #


def test_the_gate_bites_when_its_drift_branch_is_removed(tmp_path: Path) -> None:
    """Without ``if others: ... SystemExit(1)`` a drifted release is published."""
    original = offline_gate_block()
    assert "if others:" in original
    mutated = original.replace("if others:", "if False:")
    root = make_release_tree(tmp_path / "mutated")
    (root / "src" / "teamwork" / "version.py").write_text(
        VERSION_FILE.format("0.9.0"), encoding="utf-8"
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "wrong version")
    git(root, "tag", "-f", "v1.0.0")

    assert run_gate(root, original)[0] == 1
    code, output = run_gate(root, mutated)

    assert code != 1, output
    assert "R1 DRIFT" in output


def test_the_gate_bites_when_the_tag_assertion_is_removed(tmp_path: Path) -> None:
    original = offline_gate_block()
    assert "if tag not in at_head:" in original
    mutated = original.replace("if tag not in at_head:", "if False:")
    root = make_release_tree(tmp_path / "mutated-tag")

    assert run_gate(root, original, tag="v9.9.9")[0] == 2
    code, output = run_gate(root, mutated, tag="v9.9.9")

    assert code != 2, output


def test_the_online_gate_is_not_run_here() -> None:
    """NOT RUN, by necessity - recorded rather than silently skipped.

    The ``--online`` half needs the npm registry, the GitHub releases API and
    PyPI (and a bearer token for the GitHub API). This suite opens no socket,
    so that path is exercised only in ``.github/workflows/release.yml`` on a
    real tag push. What *is* covered here is every local decision the same
    block makes: the tag-at-HEAD assertion, the 0/1/2 exit mapping, the
    unexpected-exit refusal and the exemption's exact scope.
    """
    code = extract_gate_block()
    assert '"--online"' in code, "the shipped gate no longer runs the online half"
    assert "--offline" not in code


# --------------------------------------------------------------------------- #
# The ordering contract: nothing is published before the gate is recorded
# --------------------------------------------------------------------------- #


def job_blocks(workflow: Path = RELEASE_WORKFLOW) -> dict[str, list[str]]:
    """Split the workflow's ``jobs:`` section into ``{job name: its lines}``."""
    lines = workflow.read_text(encoding="utf-8").splitlines()
    jobs_at = lines.index("jobs:")
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[jobs_at + 1 :]:
        match = re.match(r"^  ([a-z][a-z0-9_-]*):\s*$", line)
        if match:
            current = match.group(1)
            blocks[current] = []
            continue
        if current is None:
            continue
        if line.strip() and not line.startswith("    "):
            break
        blocks[current].append(line)
    assert blocks, "no jobs parsed"
    return blocks


def test_nothing_is_built_or_published_before_the_gate_has_run() -> None:
    """The ordering is in the dependency graph, not only in step order."""
    jobs = job_blocks()

    assert "needs: [consistency]" in "\n".join(jobs["build"])
    assert "needs: [build, attest]" in "\n".join(jobs["release"])
    for name in ("build", "attest", "release"):
        assert "needs:" in "\n".join(jobs[name]), f"{name} has no dependency"


def test_the_gate_job_cannot_soft_fail() -> None:
    """``continue-on-error`` / ``|| true`` in the gate would make it advisory."""
    # Comment lines explain the absence of these; the executable keys are the
    # subject, so the YAML comments are stripped first.
    gate = "\n".join(
        line for line in job_blocks()["consistency"] if not line.lstrip().startswith("#")
    )

    assert "continue-on-error:" not in gate
    # The checker invocation itself is not softened. (An unrelated `|| true`
    # does exist in the tag-count step, where it guards `grep -c`; that is a
    # count, not a verdict, so only the invocation line is asserted here.)
    invocation = [line for line in gate.splitlines() if 'CHECKER, "--online"' in line]
    assert invocation, "the checker invocation was not found in the gate job"
    for line in invocation:
        assert "|| true" not in line
        assert "check=False" not in line or "returncode" in gate


def test_the_ordering_contract_bites_when_the_dependency_is_dropped(tmp_path: Path) -> None:
    """Same assertion, on a workflow copy with ``needs: [consistency]`` removed."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "needs: [consistency]" in text
    mutated = tmp_path / "release.yml"
    mutated.write_text(text.replace("needs: [consistency]", "needs: []"), encoding="utf-8")

    build = "\n".join(job_blocks(mutated)["build"])

    assert "needs: [consistency]" not in build
    assert "needs: []" in build


# --------------------------------------------------------------------------- #
# ``scripts/verify_release.py`` - the local pre-flight
# --------------------------------------------------------------------------- #


def test_verify_release_refuses_when_its_builder_is_unavailable(tmp_path: Path) -> None:
    """``verify_release.py`` fails closed rather than building nothing.

    Read first, then measured: the script's subject is the built artefact, and
    its first step imports ``build`` and raises ``VerificationError`` when it
    is missing ("'build' is not installed; ... has not been run
    `python -m pip install build`"). Running it under ``-S`` (no site
    packages) reproduces exactly that path, offline and in well under a second.
    """
    result = subprocess.run(
        [sys.executable, "-S", str(REPO_ROOT / "scripts" / "verify_release.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "'build' is not installed" in result.stdout


def test_verify_release_does_not_read_the_consistency_gate_record() -> None:
    """Recorded mismatch with the task brief, asserted rather than assumed.

    The brief expected ``verify_release.py`` to refuse a release whose
    consistency gate has not been recorded. The script does not read that
    record at all: it builds, inspects the wheel/sdist, smoke-tests an
    installed wheel and writes ``SHA256SUMS``. The gate-is-recorded contract
    lives in the workflow's dependency graph instead, and is asserted above
    (``test_nothing_is_built_or_published_before_the_gate_has_run``). If a
    consistency step is ever added to the script, this test fails and the
    contract test above must be revisited.
    """
    source = (REPO_ROOT / "scripts" / "verify_release.py").read_text(encoding="utf-8")

    assert "check_release_consistency" not in source

    # The full local pre-flight was executed once by hand on this revision:
    # `python scripts/verify_release.py` -> exit 0, "OK - release verified"
    # (wheel payload 43/43 bundle files, sdist 167 entries, installed-wheel
    # loop -> STOP). It is NOT part of this suite: it runs `python -m build`,
    # creates a virtualenv and installs the wheel (minutes, plus an isolated
    # build environment that fetches hatchling), which is beyond the runtime
    # and no-network budget of the integration layer. Marked NOT RUN here.
