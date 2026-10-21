"""Integration coverage for the release gate as a *process*.

The unit layer (``tests/unit/test_release_consistency.py``) calls the checker's
functions in-process. This layer runs the merged checker **end to end**, the way
CI and the release pipeline run it: as ``python scripts/check_release_consistency.py``
in a subprocess, against a synthetic git repository with tags, a CHANGELOG and a
README, and asserts the two things the contract freezes:

1. the exit codes - ``0`` clean, ``1`` drift, ``2`` an unreadable input;
2. the per-rule output line format ``<RULE-ID> <ok|DRIFT|SKIP> <detail>``.

The CLI half is **offline** (``--offline``), so no socket is opened and the run
is deterministic. The published half (R3/R4/R5) needs npm and the GitHub API;
the checker exposes that seam as the ``fetch``/``fetch_bytes`` parameters of
``rule_r3_npm_payloads``, so it is exercised with an injected fake fetcher
instead of the network.

Owner: tester. Task: T-0003.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from collections.abc import Mapping
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
#: ``TEAMWORK_RELEASE_CHECKER`` is the same explicit override the unit layer
#: honours: it points a run at one file, which is how a mutant - a copy of the
#: checker with one rule removed - is measured.
CHECKER = Path(
    os.environ.get("TEAMWORK_RELEASE_CHECKER")
    or (REPO_ROOT / "scripts" / "check_release_consistency.py")
)

#: The contract's line format: a rule id, one of three statuses, a detail.
LINE = re.compile(r"^R(?P<rule>[1-9]) (?P<status>ok|DRIFT|SKIP) (?P<detail>.+)$")
SUMMARY = re.compile(r"^# release consistency: (?P<count>\d+) problem\(s\)$")

VERSION_FILE = '__version__ = "{version}"\nDIST_NAME = "teamwork-agents"\n'
PYPROJECT = (
    '[project]\nname = "teamwork-agents"\n\n[project.scripts]\nteamwork = "teamwork.cli:main"\n'
)

#: Identity and signing are pinned per call so the fixture never depends on the
#: operator's git configuration.
GIT_OPTIONS = (
    "-c",
    "user.email=developer@agents.nidvue.com",
    "-c",
    "user.name=Developer",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "tag.gpgSign=false",
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def write(root: Path, files: Mapping[str, str]) -> None:
    # LF on every platform, for the same reason the unit fixture pins it: the
    # tagged payload's digest is computed over committed bytes and the recipe
    # pins core.autocrlf=false, so a CRLF fixture would make R3 disagree with
    # itself on windows-latest only. Opened directly because
    # ``Path.write_text(newline=...)`` is Python 3.10+ and CI runs this on 3.9.
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        assert b"\r\n" not in path.read_bytes(), f"fixture {rel} must be LF on every platform"


def commit(root: Path, files: Mapping[str, str] | None = None, message: str = "edit") -> None:
    write(root, files or {})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def make_repo(root: Path, version: str = "1.1.0", files: Mapping[str, str] | None = None) -> Path:
    """A committed fixture: one version, one CHANGELOG section, a README."""
    baseline = {
        "src/teamwork/version.py": VERSION_FILE.format(version=version),
        "pyproject.toml": PYPROJECT,
        "CHANGELOG.md": f"# Changelog\n\n## [{version}]\n\n- initial\n",
        "README.md": "# Teamwork\n",
        "release-exceptions.json": "[]\n",
    }
    baseline.update(files or {})
    write(root, baseline)
    git(root, "init", "-q")
    commit(root, message="fixture")
    return root


def bump(root: Path, version: str) -> None:
    """Raise HEAD's version above the tag, which R2 requires of every release."""
    files = {
        "src/teamwork/version.py": VERSION_FILE.format(version=version),
        "CHANGELOG.md": (
            f"# Changelog\n\n## [{version}]\n\n- next\n\n"
            + (root / "CHANGELOG.md").read_text(encoding="utf-8").split("\n", 2)[2]
        ),
    }
    commit(root, files, message=f"bump to {version}")


def run_gate(root: Path, *flags: str) -> tuple[int, str, str]:
    """Run the merged checker in a subprocess and return (code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(CHECKER), *flags, "--repo-root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(root),
    )
    return proc.returncode, proc.stdout, proc.stderr


def parse_report(stdout: str) -> tuple[list[tuple[str, str, str]], int]:
    """The rule lines and the problem count, both parsed from the real output."""
    lines = stdout.splitlines()
    assert SUMMARY.match(lines[-1]), f"the report has no summary line: {lines[-1]!r}"
    problems = int(SUMMARY.match(lines[-1]).group("count"))  # type: ignore[union-attr]
    rules: list[tuple[str, str, str]] = []
    for line in lines[:-1]:
        match = LINE.match(line)
        assert match, f"the line does not match the contract format: {line!r}"
        rules.append((f"R{match.group('rule')}", match.group("status"), match.group("detail")))
    return rules, problems


@pytest.fixture(scope="module")
def checker():
    """The merged checker, loaded by path (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("checker_under_integration_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Exit code 0 - a clean tree
# --------------------------------------------------------------------------- #


def test_a_clean_tree_exits_zero_with_nine_rule_lines(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")

    code, stdout, stderr = run_gate(root, "--offline")

    assert (code, stderr) == (0, "")
    rules, problems = parse_report(stdout)
    assert [rule for rule, _, _ in rules] == [f"R{index}" for index in range(1, 10)]
    assert problems == 0
    assert all(status in ("ok", "SKIP") for _, status, _ in rules)
    assert all(detail.strip() for _, _, detail in rules)


def test_every_rule_line_carries_a_status_and_a_detail(tmp_path):
    """The contract format is ``<RULE-ID> <ok|DRIFT|SKIP> <detail>`` - no exceptions."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")

    _, stdout, _ = run_gate(root, "--offline")

    rules, _ = parse_report(stdout)
    assert {status for _, status, _ in rules} <= {"ok", "DRIFT", "SKIP"}
    assert all(detail for _, _, detail in rules)


# --------------------------------------------------------------------------- #
# Exit code 1 - drift
# --------------------------------------------------------------------------- #


def test_a_tagged_version_above_head_exits_one_with_drift(tmp_path):
    """A reachable tag ahead of HEAD is the R2 drift the gate must report."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.0.0")

    code, stdout, _ = run_gate(root, "--offline")

    rules, problems = parse_report(stdout)
    assert code == 1
    assert problems >= 1
    drift = [rule for rule, status, _ in rules if status == "DRIFT"]
    assert drift == ["R2"]
    assert any("R2" in rule and status == "DRIFT" for rule, status, _ in rules)


def test_a_stale_version_in_the_readme_exits_one(tmp_path):
    """R6: prose that prints a version older than HEAD is drift."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")
    commit(root, {"README.md": "# Teamwork\n\nInstall Teamwork 1.0.0 to match the release.\n"})

    code, stdout, _ = run_gate(root, "--offline")

    rules, problems = parse_report(stdout)
    assert code == 1
    assert problems >= 1
    assert ("R6", "DRIFT") in [(rule, status) for rule, status, _ in rules]


# --------------------------------------------------------------------------- #
# Exit code 2 - an unreadable input
# --------------------------------------------------------------------------- #


def test_a_root_that_is_not_a_work_tree_exits_two(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    code, stdout, _ = run_gate(plain, "--offline")

    rules, _ = parse_report(stdout)
    assert code == 2
    assert all(status == "SKIP" for _, status, _ in rules)
    assert any("not a git work tree" in detail for _, _, detail in rules)


def test_an_unreadable_exception_record_exits_two(tmp_path):
    """A malformed ``release-exceptions.json`` is an unreadable input, not a pass."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")
    (root / "release-exceptions.json").write_text("{not json\n", encoding="utf-8")

    code, stdout, _ = run_gate(root, "--offline")

    rules, _ = parse_report(stdout)
    assert code == 2
    assert ("R3", "SKIP") in [(rule, status) for rule, status, _ in rules]


def test_offline_and_online_together_exit_two(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")

    code, _, stderr = run_gate(root, "--offline", "--online")

    assert code == 2
    assert "mutually exclusive" in stderr


# --------------------------------------------------------------------------- #
# The published half, with an injected fetcher instead of the network
# --------------------------------------------------------------------------- #

PAYLOAD = {
    "SKILL.md": "# Skill\n",
    "AGENTS.md": "# Agents\n",
    "src/teamwork/version.py": VERSION_FILE.format(version="1.1.0"),
}


def tarball(payload: Mapping[str, str], prefix: str = "package/skills/teamwork") -> bytes:
    """An npm-shaped ``.tgz`` whose shipped subtree is ``payload``."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for rel, text in payload.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{prefix}/{rel}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def fake_fetch(responses: Mapping[str, object]):
    """A ``fetch`` callable that answers from memory and records the URLs asked."""
    asked: list[str] = []

    def fetch(url: str) -> object:
        asked.append(url)
        if url not in responses:
            raise AssertionError(f"unexpected network request: {url}")
        return responses[url]

    fetch.asked = asked  # type: ignore[attr-defined]
    return fetch


def npm_registry(*versions: str) -> dict[str, object]:
    return {
        "versions": {
            version: {"dist": {"tarball": f"https://registry.npmjs.org/-/{version}.tgz"}}
            for version in versions
        }
    }


def tagged_payload_repo(tmp_path: Path) -> Path:
    """A fixture whose tag carries a known payload, so a digest can be compared."""
    root = make_repo(tmp_path / "repo", version="1.1.0", files=PAYLOAD)
    git(root, "tag", "v1.1.0")
    return root


def test_a_published_version_matching_a_tagged_payload_is_ok(checker, tmp_path):
    """R3: the npm tarball's payload digest equals the tagged payload's digest."""
    root = tagged_payload_repo(tmp_path)
    fetch = fake_fetch({checker.NPM_REGISTRY: npm_registry("1.1.0")})

    result = checker.rule_r3_npm_payloads(root, [], fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "ok"
    assert "1 npm version(s) match" in result.detail
    assert fetch.asked == [checker.NPM_REGISTRY]


def test_a_published_version_whose_payload_differs_is_drift(checker, tmp_path):
    root = tagged_payload_repo(tmp_path)
    fetch = fake_fetch({checker.NPM_REGISTRY: npm_registry("1.1.0")})

    result = checker.rule_r3_npm_payloads(
        root, [], fetch, lambda url: tarball({**PAYLOAD, "SKILL.md": "# different\n"})
    )

    assert result.status == "DRIFT"
    assert "payload digest" in result.detail


def test_a_version_with_no_tag_is_drift(checker, tmp_path):
    """A published version that no tag can explain is drift, never a pass."""
    root = tagged_payload_repo(tmp_path)
    fetch = fake_fetch({checker.NPM_REGISTRY: npm_registry("1.9.9")})

    result = checker.rule_r3_npm_payloads(root, [], fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "DRIFT"
    assert "no tag v1.9.9" in result.detail


def test_a_recorded_exception_admits_an_untraceable_version(checker, tmp_path):
    """AC-REL-1: an untraceable version is admitted by ``release-exceptions.json``."""
    root = tagged_payload_repo(tmp_path)
    fetch = fake_fetch({checker.NPM_REGISTRY: npm_registry("1.1.0", "1.1.1")})
    exceptions = [
        {
            "version": "1.1.1",
            "reason": "published from a workspace whose commit was never pushed",
            "evidence": "no commit in git rev-list --all carries this payload",
            "recorded": "2026-10-20",
        }
    ]

    result = checker.rule_r3_npm_payloads(root, exceptions, fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "ok"
    assert "1.1.1 admitted by exception" in result.detail


def test_the_json_report_carries_the_three_contract_keys(checker, tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")

    code, stdout, _ = run_gate(root, "--offline", "--json")
    payload = json.loads(stdout)

    assert code == 0
    assert sorted(payload) == ["exit_code", "problems", "rules"]
    assert payload["exit_code"] == 0
    assert [rule["id"] for rule in payload["rules"]] == [f"R{index}" for index in range(1, 10)]
    assert all(rule["status"] in ("ok", "DRIFT", "SKIP") for rule in payload["rules"])
    assert all(rule["detail"] for rule in payload["rules"])


# --------------------------------------------------------------------------- #
# AC-REL-2: every rule has a test that fails before the rule exists
# --------------------------------------------------------------------------- #

#: A mutant replaces one rule with a constant ``ok`` - that rule is absent.
#: The stub is appended to a copy of the checker, so the later definition wins.
MUTANTS = {
    "R1": "def rule_r1_tagged_version(repo_root):\n    return RuleResult('R1', 'ok', 'mutant: the rule does not exist')\n",
    "R2": "def rule_r2_head_is_newer(repo_root):\n    return RuleResult('R2', 'ok', 'mutant: the rule does not exist')\n",
    "R3": "def rule_r3_npm_payloads(repo_root, exceptions=(), fetch=None, fetch_bytes=None):\n    return RuleResult('R3', 'ok', 'mutant: the rule does not exist')\n",
    "R4": "def rule_r4_releases_have_tags(repo_root, fetch=None):\n    return RuleResult('R4', 'ok', 'mutant: the rule does not exist')\n",
    "R5": "def rule_r5_tags_have_releases(repo_root, fetch=None):\n    return RuleResult('R5', 'ok', 'mutant: the rule does not exist')\n",
    "R6": "def rule_r6_markdown_versions(repo_root):\n    return RuleResult('R6', 'ok', 'mutant: the rule does not exist')\n",
    "R7": "def rule_r7_changelog(repo_root):\n    return RuleResult('R7', 'ok', 'mutant: the rule does not exist')\n",
    "R8": "def rule_r8_install_channels(repo_root, fetch=None):\n    return RuleResult('R8', 'ok', 'mutant: the rule does not exist')\n",
    "R9": "def rule_r9_markdown_tags(repo_root):\n    return RuleResult('R9', 'ok', 'mutant: the rule does not exist')\n",
}

#: The layer that owns the per-rule tests. The mutant is measured against the
#: unit layer only, so the inner pytest run never re-enters this file.
RULE_TESTS = (
    "tests/unit/test_release_consistency.py",
    "tests/unit/test_release_consistency_digest.py",
    "tests/unit/test_release_consistency_r8.py",
)


def test_every_rule_has_a_test_that_fails_before_the_rule_exists(tmp_path):
    """AC-REL-2: removing a rule must make the suite go red.

    The mutant is a copy of the merged checker with one rule replaced by a
    constant ``ok``; the suite is run against it through the checker's own
    ``TEAMWORK_RELEASE_CHECKER`` override. A rule with no test of its own
    leaves the suite green, and that is the defect this test closes.
    """
    source = CHECKER.read_text(encoding="utf-8")

    def run_rule_tests(checker_path: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if checker_path is None:
            env.pop("TEAMWORK_RELEASE_CHECKER", None)
        else:
            env["TEAMWORK_RELEASE_CHECKER"] = str(checker_path)
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly", *RULE_TESTS],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
            env=env,
        )

    # The baseline must be green: otherwise a mutant would be "killed" by a
    # failure that has nothing to do with the rule that was removed.
    baseline = run_rule_tests()
    assert baseline.returncode == 0, f"the rule tests are not green: {baseline.stdout[-2000:]}"

    survivors = []
    for rule, stub in MUTANTS.items():
        mutant = tmp_path / f"checker_without_{rule}.py"
        mutant.write_text(source + "\n\n" + stub, encoding="utf-8")
        if run_rule_tests(mutant).returncode == 0:
            survivors.append(rule)
    assert survivors == [], f"a rule with no failing test: {survivors}"
