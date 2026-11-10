"""Integration: release traceability - version.py <-> tag <-> CHANGELOG <-> exceptions.

The traceability chain is four artefacts that must agree: the version the code
declares, the tag that publishes it, the CHANGELOG section that describes it,
and the exception record that admits a version the checker cannot verify. Each
link is one rule family (R1 tag-carries-its-version, R2 head-moves-past-tags,
R5 tag-has-a-release, plus R7's section and the exception record of 11.4).

This module builds real fixture repositories under ``tmp_path`` and drives the
checker *as a command* (the same ``--offline --json`` invocation CI uses),
asserting the verdict per family. Nothing is mocked: the chain is a git
repository and a JSON file on disk.

Two links cannot be exercised from a command without a network:

* **R5 positive** (a tag whose GitHub Release exists) needs the GitHub API.
* The R3 payload-digest comparison needs the npm registry.

Both are marked NOT RUN with that reason in
``test_the_online_link_of_the_chain_is_not_run_here``; what is covered offline
is the negative contract that matters - the gate never *claims* R5 passed
without consulting the API.

Owner: tester. Task: T-0004.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
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
# Building the chain
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


def commit(root: Path, files: dict[str, str], message: str = "edit") -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def changelog(*versions: str) -> str:
    sections = "".join(f"## [{version}]\n\n- released {version}\n\n" for version in versions)
    return f"# Changelog\n\n{sections}".rstrip("\n") + "\n"


def make_chain(
    root: Path,
    *,
    version: str = "1.0.0",
    tags: tuple[str, ...] = ("v1.0.0",),
    exceptions: list[dict[str, str]] | None = None,
    changelog_versions: tuple[str, ...] | None = None,
) -> Path:
    """A repository whose four release artefacts are pinned as arguments."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    commit(
        root,
        {
            "src/teamwork/version.py": VERSION_FILE.format(version),
            "CHANGELOG.md": changelog(*(changelog_versions or (version,))),
            "release-exceptions.json": json.dumps(exceptions or [], indent=2) + "\n",
            "README.md": "# Teamwork\n",
        },
        "release",
    )
    for tag in tags:
        git(root, "tag", tag)
    return root


def trace(root: Path) -> tuple[int, dict, str]:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--offline", "--json", "--repo-root", str(root)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")},
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = {}
    return result.returncode, report, result.stderr


def verdict(report: dict, rule: str) -> str:
    return next(r["status"] for r in report.get("rules", []) if r["id"] == rule)


def detail(report: dict, rule: str) -> str:
    return next(r["detail"] for r in report.get("rules", []) if r["id"] == rule)


def problems(report: dict) -> str:
    return " | ".join(f"{p['rule']}: {p['detail']}" for p in report.get("problems", []))


# --------------------------------------------------------------------------- #
# Link 1 - version.py <-> tag (R1)
# --------------------------------------------------------------------------- #


def test_the_tag_and_version_py_agree_is_a_pass(tmp_path: Path) -> None:
    root = make_chain(tmp_path / "agreed")

    code, report, stderr = trace(root)

    assert code == 0, stderr or problems(report)
    assert verdict(report, "R1") == "ok"
    assert "1 tag(s) agree" in detail(report, "R1")


def test_head_newer_than_every_tag_is_a_pass(tmp_path: Path) -> None:
    """The chain after a release: 1.0.0 is tagged, HEAD carries 1.1.0."""
    root = make_chain(tmp_path / "ahead", version="1.0.0", tags=("v1.0.0",))
    commit(
        root,
        {
            "src/teamwork/version.py": VERSION_FILE.format("1.1.0"),
            "CHANGELOG.md": changelog("1.1.0", "1.0.0"),
        },
        "start 1.1.0",
    )

    code, report, _ = trace(root)

    assert code == 0, problems(report)
    assert verdict(report, "R2") == "ok"
    assert "HEAD 1.1.0 is newer than 1 tag(s)" in detail(report, "R2")


def test_a_tag_newer_than_the_version_is_drift(tmp_path: Path) -> None:
    """The tag publishes 2.0.0; the commit it points at declares 1.0.0."""
    root = make_chain(tmp_path / "behind", version="1.0.0", tags=("v2.0.0",))

    code, report, _ = trace(root)

    assert code == 1, problems(report)
    assert verdict(report, "R1") == "DRIFT"
    assert "v2.0.0: __version__ 1.0.0 != tag version 2.0.0" in problems(report)


def test_a_tag_without_a_changelog_section_is_drift(tmp_path: Path) -> None:
    """Link 3: the tag must have exactly one matching CHANGELOG section (R7)."""
    root = make_chain(
        tmp_path / "nosection",
        version="2.0.0",
        tags=("v2.0.0",),
        changelog_versions=("1.9.0",),
    )

    code, report, _ = trace(root)

    assert code == 1, problems(report)
    assert verdict(report, "R7") == "DRIFT"
    assert "v2.0.0 has no '## [2.0.0]' section" in problems(report)


# --------------------------------------------------------------------------- #
# Link 2 - the exception record
# --------------------------------------------------------------------------- #


def measured_exception(version: str = "0.9.0") -> dict[str, str]:
    return {
        "version": version,
        "reason": "published before the payload-digest rule existed",
        "evidence": "gh run 12345 failed the 0.9.0 digest comparison",
        "recorded": "2025-01-01",
    }


def test_an_exception_with_a_measured_reason_admits_the_version(tmp_path: Path) -> None:
    root = make_chain(tmp_path / "admitted", exceptions=[measured_exception()])

    code, report, _ = trace(root)

    assert code == 0, problems(report)
    assert "0.9.0 admitted by exception" in detail(report, "R3")
    assert verdict(report, "R3") == "SKIP"  # offline: admitted, not verified


def test_an_exception_without_a_reason_is_an_unreadable_input(tmp_path: Path) -> None:
    """Measured, not assumed: an empty reason is exit 2, not exit 1.

    The frozen contract (Architecture 11.4) makes an incomplete record an
    unreadable input *before* any rule runs - a reviewer cannot judge a record
    with no reason, so the checker refuses to pretend it evaluated the rule.
    The task brief expected "drift"; the observed verdict is exit 2, and this
    test asserts what the code does.
    """
    root = make_chain(
        tmp_path / "unmeasured",
        exceptions=[dict(measured_exception(), reason="")],
    )

    code, report, _ = trace(root)

    assert code == 2, problems(report)
    assert "reason is empty" in detail(report, "R3")
    assert verdict(report, "R3") == "SKIP"


def test_an_exception_still_measured_after_the_version_became_traceable_is_drift(
    tmp_path: Path,
) -> None:
    """A stale exception is drift: 1.0.0 *is* tagged, so it needs no excuse.

    This is the traceability guarantee that makes the record trustworthy - an
    exception outliving its reason would quietly cover a future defect.
    """
    root = make_chain(
        tmp_path / "stale",
        version="1.0.0",
        tags=("v1.0.0",),
        exceptions=[measured_exception("1.0.0")],
    )

    code, report, _ = trace(root)

    assert code == 1, problems(report)
    assert verdict(report, "R3") == "DRIFT"
    assert "exception names a traceable version, tag v1.0.0 exists" in problems(report)


# --------------------------------------------------------------------------- #
# Link 4 - R5 must never claim a release that was not checked
# --------------------------------------------------------------------------- #


def test_r5_never_claims_a_release_offline(tmp_path: Path) -> None:
    root = make_chain(tmp_path / "r5offline")

    code, report, _ = trace(root)

    assert code == 0, problems(report)
    assert verdict(report, "R5") == "SKIP"
    assert "offline" in detail(report, "R5")
    assert "cannot confirm 1 tag(s) are released" in detail(report, "R5")


def test_the_online_link_of_the_chain_is_not_run_here() -> None:
    """NOT RUN, by necessity, and recorded as such.

    R5's positive verdict (a tag *has* a GitHub Release) and R3's digest
    comparison need ``--online``, i.e. the npm registry, api.github.com and
    PyPI, plus a bearer token for the GitHub API. This suite opens no socket,
    so those verdicts are produced only by ``.github/workflows/release.yml``
    on a real tag push. Offline they are SKIP with a reason - asserted in
    ``test_r5_never_claims_a_release_offline`` - so the gate cannot become
    green by forgetting to check.
    """
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0
    assert "--online" in result.stdout


# --------------------------------------------------------------------------- #
# The chain must bite: break one link and the verdict flips
# --------------------------------------------------------------------------- #


def test_repairing_the_broken_link_turns_the_verdict_green(tmp_path: Path) -> None:
    """The same repository, mutated and then repaired: drift -> pass."""
    root = make_chain(tmp_path / "reversible", version="1.0.0", tags=("v2.0.0",))

    broken_code, broken_report, _ = trace(root)
    assert broken_code == 1
    assert verdict(broken_report, "R1") == "DRIFT"

    # Repair the chain: make the declared version match the published tag.
    commit(
        root,
        {
            "src/teamwork/version.py": VERSION_FILE.format("2.0.0"),
            "CHANGELOG.md": changelog("2.0.0"),
        },
        "align version.py with the tag",
    )
    git(root, "tag", "-f", "v2.0.0")

    fixed_code, fixed_report, _ = trace(root)

    assert fixed_code == 0, problems(fixed_report)
    assert verdict(fixed_report, "R1") == "ok"
    assert "1 tag(s) agree" in detail(fixed_report, "R1")
