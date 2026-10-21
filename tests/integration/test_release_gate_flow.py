"""Integration: ``scripts/check_release_consistency.py`` as a real subprocess.

The unit layer (``tests/unit/test_release_consistency.py``) imports the checker
and calls its rules. This module instead drives the *command* the CI gate runs -
the same ``--offline``/``--json`` invocation as `.github/workflows/ci.yml` and
the same exit-code mapping the workflow implements - against real git
repositories under ``tmp_path``, and reads the verdict from its exit code and
its JSON report.

Exit codes are the frozen contract (Architecture 11.1.1): 0 clean, 1 drift,
2 an input that could not be read. A test that only asserted "non-zero" would
not distinguish drift from an unreadable input, so every case asserts the exact
code.

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

VERSION_FILE = '__version__ = "{version}"\nDIST_NAME = "teamwork-agents"\n'
PYPROJECT = (
    '[project]\nname = "teamwork-agents"\n\n[project.scripts]\nteamwork = "teamwork.cli:main"\n'
)


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


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def commit(root: Path, files: dict[str, str], message: str = "edit") -> None:
    write(root, files)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def baseline(version: str = "1.0.0") -> dict[str, str]:
    return {
        "src/teamwork/version.py": VERSION_FILE.format(version=version),
        "pyproject.toml": PYPROJECT,
        "CHANGELOG.md": f"# Changelog\n\n## [{version}]\n\n- initial\n",
        "README.md": "# Teamwork\n",
        "release-exceptions.json": "[]\n",
    }


def make_repo(root: Path, version: str = "1.0.0", tag: str | None = "v1.0.0") -> Path:
    write(root, baseline(version))
    git(root, "init", "-q", "-b", "main")
    commit(root, {}, message="fixture")
    if tag is not None:
        git(root, "tag", tag)
    return root


def gate(root: Path, *args: str) -> tuple[int, dict | None, str]:
    """Run the checker exactly as CI does and return ``(exit code, report, stderr)``."""
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--offline", "--json", "--repo-root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        env={k: v for k, v in os.environ.items() if not k.startswith("TEAMWORK_")},
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = None
    return result.returncode, report, result.stderr


def statuses(report: dict) -> dict[str, str]:
    return {rule["id"]: rule["status"] for rule in report["rules"]}


# --------------------------------------------------------------------------- #
# 0 - a consistent repository
# --------------------------------------------------------------------------- #


def test_a_consistent_repository_exits_zero(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "clean")

    code, report, stderr = gate(root)

    assert code == 0, stderr
    assert report is not None, "the checker printed no JSON report"
    assert report["problems"] == []
    assert report["exit_code"] == 0
    seen = statuses(report)
    assert seen["R1"] == "ok"
    assert seen["R2"] == "ok"
    assert seen["R6"] == "ok"
    assert seen["R7"] == "ok"
    assert seen["R9"] == "ok"


# --------------------------------------------------------------------------- #
# 1 - drift
# --------------------------------------------------------------------------- #


def test_a_version_older_than_its_tag_is_drift_exit_1(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "regressed")
    # The tag says 2.0.0 but version.py at that commit says 1.0.0.
    git(root, "tag", "v2.0.0")

    code, report, stderr = gate(root)

    assert code == 1, stderr
    assert report is not None
    details = " ".join(problem["detail"] for problem in report["problems"])
    assert "v2.0.0" in details
    assert statuses(report)["R1"] == "DRIFT"


def test_head_that_does_not_move_past_a_tag_is_drift_exit_1(tmp_path: Path) -> None:
    """R2: a commit after a tag must raise the version, not repeat it."""
    root = make_repo(tmp_path / "stale")
    commit(root, {"README.md": "# Teamwork\n\nmore prose\n"}, "prose only, same version")

    code, report, stderr = gate(root)

    assert code == 1, stderr
    assert report is not None
    assert statuses(report)["R1"] == "ok"
    assert statuses(report)["R2"] == "DRIFT"
    details = " ".join(problem["detail"] for problem in report["problems"])
    assert "not greater than tag v1.0.0" in details


def test_a_missing_changelog_section_is_drift_exit_1(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "nochangelog")
    write(root, {"CHANGELOG.md": "# Changelog\n\n- no sections\n"})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "drop the section")

    code, report, _ = gate(root)

    assert code == 1
    assert report is not None
    assert statuses(report)["R7"] == "DRIFT"


# --------------------------------------------------------------------------- #
# 2 - an input that could not be read
# --------------------------------------------------------------------------- #


def test_a_directory_that_is_not_a_git_work_tree_exits_2(tmp_path: Path) -> None:
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    write(plain, baseline())

    code, report, _ = gate(plain)

    assert code == 2
    assert report is not None
    assert report["exit_code"] == 2
    assert all(rule["status"] in {"SKIP", "ok"} for rule in report["rules"])


def test_a_malformed_exception_record_exits_2(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "badexceptions")
    # ``reason`` is empty: a reviewer cannot judge it, so the record is unreadable.
    commit(
        root,
        {
            "release-exceptions.json": json.dumps(
                [
                    {
                        "version": "0.9.0",
                        "reason": "",
                        "evidence": "docs/Team/Release.md",
                        "recorded": "2025-01-01",
                    }
                ]
            )
        },
        "bad exception",
    )

    code, report, _ = gate(root)

    assert code == 2
    assert report is not None
    assert report["exit_code"] == 2
    assert statuses(report)["R3"] == "SKIP"


def test_offline_and_online_are_mutually_exclusive_exit_2(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "bothflags")

    result = subprocess.run(
        [sys.executable, str(CHECKER), "--offline", "--online", "--repo-root", str(root)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 2
    assert "--offline and --online are mutually exclusive" in result.stderr


# --------------------------------------------------------------------------- #
# --offline behaviour: local rules evaluate, network rules SKIP with a reason
# --------------------------------------------------------------------------- #


def test_offline_skips_the_network_rules_and_still_evaluates_the_local_ones(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path / "offline")

    code, report, _ = gate(root)

    assert code == 0
    assert report is not None
    seen = statuses(report)
    for rule in ("R3", "R4", "R5", "R8"):
        assert seen[rule] == "SKIP", f"{rule} must not be claimed offline"
    for rule in ("R1", "R2", "R6", "R7", "R9"):
        assert seen[rule] in {"ok", "DRIFT"}, f"{rule} is local and must evaluate offline"
    details = " ".join(rule["detail"] for rule in report["rules"] if rule["status"] == "SKIP")
    assert "offline" in details


def test_offline_drift_is_still_drift_not_a_skip(tmp_path: Path) -> None:
    """Going offline must not soften the local rules into a green gate."""
    root = make_repo(tmp_path / "offline-drift")
    commit(root, {"src/teamwork/version.py": VERSION_FILE.format(version="0.9.0")}, "downgrade")
    git(root, "tag", "-f", "v1.0.0", "HEAD")

    code, report, _ = gate(root)

    assert code == 1
    assert report is not None
    assert report["problems"]


# --------------------------------------------------------------------------- #
# The gate must bite: the clean fixture, mutated, becomes drift
# --------------------------------------------------------------------------- #


def test_the_clean_fixture_turns_red_when_its_version_is_mutated(tmp_path: Path) -> None:
    root = make_repo(tmp_path / "mutable")
    assert gate(root)[0] == 0

    # Mutation: the tag still says 1.0.0, the commit now says 9.9.9.
    commit(root, {"src/teamwork/version.py": VERSION_FILE.format(version="9.9.9")}, "mutate")
    git(root, "tag", "-f", "v1.0.0", "HEAD")

    code, report, _ = gate(root)

    assert code == 1
    assert report is not None
    assert any(problem["rule"] == "R1" for problem in report["problems"])


ADMITTED_RECORD = [
    {
        "version": "0.9.0",
        "reason": "published before the payload-digest rule existed",
        "evidence": "gh run 12345 failed on the 0.9.0 digest",
        "recorded": "2025-01-01",
    }
]


def test_an_admitted_version_via_a_measured_exception_is_not_drift(tmp_path: Path) -> None:
    """An exception with a reason and evidence admits a version R3 cannot match.

    The tag is re-pointed at HEAD after the exception commit so R2 keeps its
    ``S = A - O`` exemption: this test is about the record, not about tags.
    """
    root = make_repo(tmp_path / "admitted")
    commit(
        root,
        {
            "release-exceptions.json": json.dumps(ADMITTED_RECORD),
            "CHANGELOG.md": "# Changelog\n\n## [1.0.0]\n\n- initial\n",
        },
        "record the exception",
    )
    git(root, "tag", "-f", "v1.0.0")

    code, report, stderr = gate(root)

    assert code == 0, stderr
    assert report is not None
    assert report["problems"] == []
    r3 = next(rule for rule in report["rules"] if rule["id"] == "R3")
    assert "0.9.0 admitted by exception" in r3["detail"]


def test_the_admitted_version_bites_when_the_exception_loses_its_reason(tmp_path: Path) -> None:
    """Remove the reason and the same record becomes an unreadable input (exit 2)."""
    root = make_repo(tmp_path / "unmeasured")
    broken = [dict(entry, reason="") for entry in ADMITTED_RECORD]
    commit(
        root,
        {
            "release-exceptions.json": json.dumps(broken),
            "CHANGELOG.md": "# Changelog\n\n## [1.0.0]\n\n- initial\n",
        },
        "drop the reason",
    )
    git(root, "tag", "-f", "v1.0.0")

    code, report, _ = gate(root)

    assert code == 2
    assert report is not None
    r3 = next(rule for rule in report["rules"] if rule["id"] == "R3")
    assert "reason is empty" in r3["detail"]
