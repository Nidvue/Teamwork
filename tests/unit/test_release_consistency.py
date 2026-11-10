"""Unit tests for the release gate (``scripts/check_release_consistency.py``).

Every rule R1..R9 is proved on a *synthetic fixture repository* built in
``tmp_path``, never on this repository: a rule is only trustworthy if it fires on
a deliberately drifted tree and stays quiet on a clean one, while a test that
reads the real repository would fail the moment the repository changes for a
legitimate reason.

The rules, their exit codes and the exception record are frozen by
[Architecture](../../../docs/Team/Architecture.md) section 11. No test opens a
socket: the offline switch is ``fetch=None`` and the online half is exercised
with a fake callable.

Owner: developer. Task: T-0006.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest

# ``tests/unit/test_release_consistency.py`` -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The checker is a script, not a package module, and it lands in its own lane
#: (T-0005). A plain ``import check_release_consistency`` therefore fails to
#: collect on every revision that does not carry the script yet, which makes
#: this file unrunnable on its own. It is loaded *by path* instead.
CHECKER_FILENAME = "check_release_consistency.py"


def candidate_checker_paths() -> list[Path]:
    """Every place the checker may live, most specific first.

    ``TEAMWORK_RELEASE_CHECKER`` is an explicit override: when it is set, only
    that path is considered, so a run can be pointed at a mutated copy of the
    checker (the mutation battery) or at nothing at all (the "checker absent"
    proof). Otherwise the current checkout is searched first and the sibling
    developer worktrees second, so the file runs wherever the checker is.
    """
    override = os.environ.get("TEAMWORK_RELEASE_CHECKER")
    if override:
        return [Path(override)]
    candidates = [REPO_ROOT / "scripts" / CHECKER_FILENAME]
    worktrees = REPO_ROOT.parent
    if worktrees.name == "Worktrees":
        candidates.extend(sorted(worktrees.glob(f"*/scripts/{CHECKER_FILENAME}")))
    return candidates


def load_checker(path: Path):
    """Import the checker from ``path`` and return the module.

    The module is registered in ``sys.modules`` before it is executed: it
    declares dataclasses, and a dataclass whose module is not in
    ``sys.modules`` fails with ``AttributeError: 'NoneType' object has no
    attribute '__dict__'``.
    """
    spec = importlib.util.spec_from_file_location("check_release_consistency_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{path}: not an importable Python file")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


CHECKER_PATH: Path | None = next(
    (path for path in candidate_checker_paths() if path.is_file()), None
)
CHECKER_MISSING_REASON = f"{CHECKER_FILENAME} has not landed yet; looked in " + ", ".join(
    str(path) for path in candidate_checker_paths()
)

#: ``None`` when the checker is nowhere to be found. The tests that need it
#: are then *skipped with that reason* - never the whole file, and never
#: silently: ``test_the_checker_surface_is_available`` still runs and asserts
#: that the loader either found a checker with the documented surface or
#: reported precisely which paths it looked at.
_CHECKER_MODULE = load_checker(CHECKER_PATH) if CHECKER_PATH is not None else None


class _MissingChecker:
    """Stand-in for the checker when it has not landed yet.

    Every attribute access to a *checker's* name skips the individual test with
    the full reason ("scripts/check_release_consistency.py has not landed yet;
    looked in ..."). The module is never skipped as a whole, and no test can
    quietly become "no tests ran": ``test_the_checker_surface_is_available``
    always runs.

    Dunder names and ``pytestmark`` raise ``AttributeError`` instead: pytest
    reads those while it collects the module, and a skip raised there would
    skip the whole file - the silent hole this stand-in exists to avoid.
    """

    def __getattr__(self, name: str):
        if name.startswith("__") or name == "pytestmark":
            raise AttributeError(name)
        raise pytest.skip(CHECKER_MISSING_REASON)


crc = _CHECKER_MODULE if _CHECKER_MODULE is not None else _MissingChecker()


#: The two exact marker literals of Architecture 11.2.4; nothing else is a marker.
ILLUSTRATIVE = "<!-- release-consistency: illustrative -->"
CHANNEL_UNAVAILABLE = "<!-- release-consistency: channel-unavailable -->"

#: Rules whose published half needs the network, so ``fetch=None`` is a SKIP.
NETWORK_RULES = frozenset({"R3", "R4", "R5", "R8"})

VERSION_FILE = '__version__ = "{version}"\nDIST_NAME = "teamwork-agents"\n'

PYPROJECT = (
    '[project]\nname = "teamwork-agents"\n\n[project.scripts]\nteamwork = "teamwork.cli:main"\n'
)

#: Identity and signing are pinned per call: the fixture must not depend on the
#: operator's git config, and a global gpgsign setting must not fail the commit.
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


# --------------------------------------------------------------------------- #
# Fixture repository
# --------------------------------------------------------------------------- #


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
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def commit(root: Path, files: Mapping[str, str] | None = None, message: str = "edit") -> None:
    write(root, files or {})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def make_repo(
    root: Path,
    version: str = "1.1.0",
    files: Mapping[str, str] | None = None,
    exceptions: str = "[]\n",
) -> Path:
    """A committed, clean-by-construction fixture: one version, one changelog section."""
    baseline = {
        "src/teamwork/version.py": VERSION_FILE.format(version=version),
        "pyproject.toml": PYPROJECT,
        "CHANGELOG.md": f"# Changelog\n\n## [{version}]\n\n- initial\n",
        "README.md": "# Teamwork\n",
        "release-exceptions.json": exceptions,
    }
    baseline.update(files or {})
    write(root, baseline)
    git(root, "init", "-q")
    commit(root, message="fixture")
    return root


def bump(root: Path, version: str, files: Mapping[str, str] | None = None) -> None:
    """Raise HEAD's version above the tag, which R2 requires of every release."""
    payload = {"src/teamwork/version.py": VERSION_FILE.format(version=version)}
    payload["CHANGELOG.md"] = (
        f"# Changelog\n\n## [{version}]\n\n- next\n\n"
        + (root / "CHANGELOG.md").read_text(encoding="utf-8").split("\n", 2)[2]
    )
    payload.update(files or {})
    commit(root, payload, message=f"bump to {version}")


def run_main(argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = crc.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def fake_http(responses: Mapping[str, object]):
    """A ``fetch`` callable that answers from memory and records the URLs asked."""

    asked: list[str] = []

    def fetch(url: str) -> object:
        asked.append(url)
        if url not in responses:
            raise AssertionError(f"unexpected network request: {url}")
        return responses[url]

    fetch.asked = asked  # type: ignore[attr-defined]
    return fetch


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


def npm_registry(versions: Mapping[str, str]) -> dict[str, object]:
    return {
        "versions": {
            version: {"dist": {"tarball": f"https://registry.npmjs.org/-/{version}.tgz"}}
            for version in versions
        }
    }


#: The payload subtree of the fixture used by the R3 digest test.
PAYLOAD = {
    "SKILL.md": "# Skill\n",
    "AGENTS.md": "# Agents\n",
    "roles/developer.md": "# Developer\n",
    "src/teamwork/version.py": VERSION_FILE.format(version="1.1.0"),
}


# --------------------------------------------------------------------------- #
# R1 - a tag must carry its own version
# --------------------------------------------------------------------------- #


def test_r1_reports_a_tag_whose_version_py_disagrees(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.0.0")

    result = crc.rule_r1_tagged_version(root)

    assert result.status == "DRIFT"
    assert "v1.0.0" in result.detail
    assert "1.1.0" in result.detail


def test_r1_reports_a_tag_without_version_py(tmp_path):
    root = tmp_path / "repo"
    write(root, {"README.md": "# Teamwork\n"})
    git(root, "init", "-q")
    commit(root, message="fixture without a version file")
    git(root, "tag", "v1.0.0")

    result = crc.rule_r1_tagged_version(root)

    assert result.status == "DRIFT"
    assert "v1.0.0" in result.detail
    assert "version.py" in result.detail


def test_r1_reports_a_non_semver_version_at_a_tag(tmp_path):
    root = make_repo(tmp_path / "repo", version="rolling")
    git(root, "tag", "v1.0.0")

    result = crc.rule_r1_tagged_version(root)

    assert result.status == "DRIFT"
    assert "rolling" in result.detail
    assert "not X.Y.Z" in result.detail


def test_r1_accepts_agreeing_tags_and_ignores_names_that_are_not_versions(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    git(root, "tag", "nightly")

    result = crc.rule_r1_tagged_version(root)

    assert result.status == "ok"
    assert "1 tag(s) agree" in result.detail


# --------------------------------------------------------------------------- #
# R2 - HEAD must be strictly newer than every tag
# --------------------------------------------------------------------------- #


def test_r2_ignores_the_tag_that_points_at_head(tmp_path):
    """11.2.2: the tag at HEAD is in O and is excluded from the comparison.

    Comparing a release with itself could only ever ask whether a version is
    greater than itself, so a checkout that is exactly a tag is ok.
    """
    root = make_repo(tmp_path / "repo", version="1.2.0")
    git(root, "tag", "v1.2.0")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert "newer than 0 tag(s)" in result.detail


def test_r2_accepts_head_newer_than_every_tag(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert "1.1.0" not in result.detail.split("newer than")[0]
    assert "newer than 1 tag(s)" in result.detail


# --------------------------------------------------------------------------- #
# R3 - npm versions must resolve to a tagged payload or a recorded exception
# --------------------------------------------------------------------------- #


def test_r3_offline_skips_and_never_claims_ok(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")

    result = crc.rule_r3_npm_payloads(root)

    assert result.status == "SKIP"
    assert result.fatal is False
    assert "offline" in result.detail
    assert "not queried" in result.detail


def test_r3_admitted_version_is_ok_and_the_exception_is_visible(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    exceptions = [
        {
            "version": "9.9.9",
            "reason": "published from a workspace whose commit was never pushed",
            "evidence": "digest 0123456789abcdef matches no commit in git rev-list --all",
            "recorded": "2026-10-20",
        }
    ]

    result = crc.rule_r3_npm_payloads(
        root, exceptions, fake_http({crc.NPM_REGISTRY: npm_registry({"9.9.9": "x"})})
    )

    assert result.status == "ok"
    assert "9.9.9 admitted by exception" in result.detail
    assert "never pushed" in result.detail


def test_r3_exception_for_a_traceable_version_is_drift(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    exceptions = [
        {
            "version": "1.1.0",
            "reason": "an admission that is no longer needed",
            "evidence": "tag v1.1.0 exists in git tag -l",
            "recorded": "2026-10-20",
        }
    ]

    result = crc.rule_r3_npm_payloads(
        root, exceptions, fake_http({crc.NPM_REGISTRY: npm_registry({})})
    )

    assert result.status == "DRIFT"
    assert "traceable version" in result.detail
    assert "v1.1.0" in result.detail


def test_r3_exception_with_an_empty_reason_is_an_input_error(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    write(
        root,
        {
            "release-exceptions.json": json.dumps(
                [
                    {
                        "version": "1.0.0",
                        "reason": "  ",
                        "evidence": "e",
                        "recorded": "2026-10-20",
                    }
                ]
            )
        },
    )

    with pytest.raises(crc.InputError, match="reason is empty"):
        crc.load_exceptions(root / "release-exceptions.json")

    code, stdout, _ = run_main(["--offline", "--repo-root", str(root)])
    assert code == 2
    assert "reason is empty" in stdout
    assert "R3 SKIP" in stdout


def test_r3_compares_the_tarball_payload_with_the_tagged_payload(tmp_path):
    root = make_repo(tmp_path / "repo", files=PAYLOAD)
    git(root, "tag", "v1.1.0")
    digest = crc.payload_digest(root, "v1.1.0")
    assert len(digest) == 16
    assert digest == crc.payload_digest(root, None)
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"1.1.0": "x"})})

    matching = crc.rule_r3_npm_payloads(root, [], fetch, lambda url: tarball(PAYLOAD))
    drifted = crc.rule_r3_npm_payloads(
        root, [], fetch, lambda url: tarball({**PAYLOAD, "SKILL.md": "# different\n"})
    )

    assert matching.status == "ok"
    assert "1 npm version(s) match" in matching.detail
    assert drifted.status == "DRIFT"
    assert "payload digest" in drifted.detail
    assert fetch.asked == [crc.NPM_REGISTRY, crc.NPM_REGISTRY]


def test_r3_an_unadmitted_non_semver_published_version_is_drift(tmp_path):
    """A published version must not escape R3 by its version shape.

    11.2.3 says R3 takes *every* version key from the registry and that an npm
    version is satisfied by a tag or by a 11.4 entry - there is no third path.
    Treating a key that is not ``X.Y.Z`` as "ignored" therefore lets a version
    that is neither tagged nor admitted in writing pass as clean, which is
    exactly what AC-REL-1 forbids: the npm staged-publish placeholder
    ``0.0.0-stage`` is published, carries no ``gitHead``, has no tag and no
    payload to digest, and the gate used to print ``ok`` for it.
    """
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"1.1.0": "x", "0.0.0-stage": "x"})})

    result = crc.rule_r3_npm_payloads(root, [], fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "DRIFT"
    assert any("0.0.0-stage" in finding for finding in result.findings)
    assert "ignored non-X.Y.Z" not in result.detail


def test_r3_an_admitted_non_semver_published_version_is_ok_end_to_end(tmp_path):
    """The escape must be *recorded*: 11.4 admits the version, the gate is green.

    AC-REL-1's second path is a written admission with a measured reason. The
    exception record is the only place that admission can live, so
    ``load_exceptions`` has to accept the published version string it admits
    (the placeholder is ``0.0.0-stage``, which no ``vX.Y.Z`` tag can carry) and
    R3 has to keep it visible in its ``detail`` on every run.
    """
    exception = {
        "version": "0.0.0-stage",
        "reason": "npm's staged-publish placeholder, published before 1.1.0",
        "evidence": "gitHead is null and no commit in git rev-list --all carries 0.0.0-stage",
        "recorded": "2026-10-21",
    }
    root = make_repo(
        tmp_path / "repo", version="1.1.0", files=PAYLOAD, exceptions=json.dumps([exception])
    )
    git(root, "tag", "v1.1.0")
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"1.1.0": "x", "0.0.0-stage": "x"})})

    result = crc.rule_r3_npm_payloads(
        root,
        crc.load_exceptions(root / "release-exceptions.json"),
        fetch,
        lambda url: tarball(PAYLOAD),
    )

    assert result.status == "ok"
    assert "1 npm version(s) match" in result.detail
    assert "0.0.0-stage admitted by exception" in result.detail


# --------------------------------------------------------------------------- #
# R4 / R5 - the GitHub Release list and the tag list must agree
# --------------------------------------------------------------------------- #


def test_r4_release_without_a_tag_is_drift(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    fetch = fake_http({crc.GITHUB_RELEASES: [{"tag_name": "v1.9.9"}]})

    result = crc.rule_r4_releases_have_tags(root, fetch)

    assert result.status == "DRIFT"
    assert "v1.9.9" in result.detail
    assert fetch.asked == [crc.GITHUB_RELEASES]


def test_r5_tag_without_a_release_is_drift(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    git(root, "tag", "v1.2.0")
    fetch = fake_http({crc.GITHUB_RELEASES: [{"tag_name": "v1.1.0"}]})

    result = crc.rule_r5_tags_have_releases(root, fetch)

    assert result.status == "DRIFT"
    assert "v1.2.0" in result.detail
    assert "v1.1.0 has no" not in result.detail


def test_r4_and_r5_are_ok_when_the_two_lists_agree(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    fetch = fake_http({crc.GITHUB_RELEASES: [{"tag_name": "v1.1.0"}]})

    assert crc.rule_r4_releases_have_tags(root, fetch).status == "ok"
    assert crc.rule_r5_tags_have_releases(root, fetch).status == "ok"


# --------------------------------------------------------------------------- #
# R6 - committed prose must not print a stale project version
# --------------------------------------------------------------------------- #


def test_r6_reports_an_older_project_version(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0", {"README.md": "# Teamwork\n\nTeamwork 1.1.0 shipped.\n"})

    result = crc.rule_r6_markdown_versions(root)

    assert result.status == "DRIFT"
    assert "README.md:3" in result.detail
    assert "1.1.0" in result.detail


def test_r6_illustrative_marker_exempts_the_line_and_is_counted(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0", {"README.md": f"# Teamwork\n\nTeamwork 1.1.0 shipped. {ILLUSTRATIVE}\n"})

    result = crc.rule_r6_markdown_versions(root)

    assert result.status == "ok"
    assert "1 illustrative" in result.detail


def test_r6_marker_above_a_fence_exempts_the_whole_block(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(
        root,
        "1.2.0",
        {"README.md": f"# Teamwork\n\n{ILLUSTRATIVE}\n```\nTeamwork 1.1.0\n```\n"},
    )

    result = crc.rule_r6_markdown_versions(root)

    assert result.status == "ok"
    assert "1 illustrative" in result.detail


def test_r6_version_inside_a_url_is_not_a_claim(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(
        root,
        "1.2.0",
        {
            "README.md": "# Teamwork\n\nTeamwork diff: https://github.com/o/r/compare/v1.1.0...HEAD\n"
        },
    )

    result = crc.rule_r6_markdown_versions(root)

    assert result.status == "ok"
    assert "0 illustrative" in result.detail


def test_r6_skips_a_foreign_tool_version(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "4.0.0", {"README.md": "# Teamwork\n\nTeamwork runs on python: 3.12.13\n"})
    control = "# Teamwork\n\nTeamwork runs on python 3.12.13\n"

    skipped = crc.rule_r6_markdown_versions(root)
    write(root, {"README.md": control})
    unmarked = crc.rule_r6_markdown_versions(root)

    assert skipped.status == "ok"
    assert unmarked.status == "DRIFT"
    assert "3.12.13" in unmarked.detail


# --------------------------------------------------------------------------- #
# R7 - every tagged version needs exactly one CHANGELOG section
# --------------------------------------------------------------------------- #


def test_r7_missing_section_is_drift(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    commit(
        root,
        {
            "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n- nothing\n",
            "src/teamwork/version.py": VERSION_FILE.format(version="1.2.0"),
        },
        message="drop the section",
    )

    result = crc.rule_r7_changelog(root)

    assert result.status == "DRIFT"
    assert "v1.1.0 has no" in result.detail


def test_r7_duplicate_section_is_drift(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "CHANGELOG.md": (
                "# Changelog\n\n## [1.1.0]\n\n- one\n\n## [1.1.0]\n\n- the same version twice\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r7_changelog(root)

    assert result.status == "DRIFT"
    assert "2 '## [1.1.0]' sections" in result.detail


def test_r7_unreleased_and_untagged_headings_are_fine(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.2.0")
    git(root, "tag", "v1.2.0")
    commit(
        root,
        {
            "CHANGELOG.md": (
                "# Changelog\n\n## [Unreleased]\n\n- pending\n\n"
                "## [1.2.0]\n\n- released\n\n## [1.3.0]\n\n- leads the tag\n"
            )
        },
        message="unreleased and a leading section",
    )

    result = crc.rule_r7_changelog(root)

    assert result.status == "ok"
    assert "1 tagged version(s)" in result.detail


# --------------------------------------------------------------------------- #
# R8 - advertised install channels must name what the repository ships
# --------------------------------------------------------------------------- #


def test_r8_unshipped_name_is_drift_offline(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={"README.md": "# Teamwork\n\n```\npip install teamwork\n```\n"},
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "README.md:4" in result.detail
    assert "teamwork-agents" in result.detail


def test_r8_channel_unavailable_marker_exempts_the_block(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "README.md": (
                f"# Teamwork\n\n{CHANNEL_UNAVAILABLE}\n```\npip install teamwork-agents\n```\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    offline = crc.rule_r8_install_channels(root)
    published = crc.rule_r8_install_channels(
        root, fake_http({crc.PYPI_JSON: {"info": {"version": "1.1.0"}}})
    )

    assert offline.status == "SKIP"
    assert "1 marked channel-unavailable" in offline.detail
    assert published.status == "ok"


def test_r8_unmarked_channel_is_drift_when_pypi_answers_404(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={"README.md": "# Teamwork\n\n```\npip install teamwork-agents\n```\n"},
    )
    git(root, "tag", "v1.1.0")

    def not_found(url: str) -> object:
        raise crc.HttpError(url, 404)

    result = crc.rule_r8_install_channels(root, not_found)

    assert result.status == "DRIFT"
    assert "HTTP 404" in result.detail
    assert "unmarked" in result.detail


def test_r8_negated_install_line_is_not_a_channel(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={"README.md": "# Teamwork\n\nThere is no pip install step and no venv.\n"},
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "SKIP"
    assert "0 channel line(s)" in result.detail


# --------------------------------------------------------------------------- #
# R9 - a vX.Y.Z token must name a real tag
# --------------------------------------------------------------------------- #


def test_r9_token_naming_no_tag_is_drift(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={"README.md": "# Teamwork\n\nPin the checkout to v9.9.9 (a tag)\n"},
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "DRIFT"
    assert "README.md:3" in result.detail
    assert "v9.9.9" in result.detail


def test_r9_illustrative_marker_exempts_the_token(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={"README.md": f"# Teamwork\n\nPin the checkout to v9.9.9 (a tag) {ILLUSTRATIVE}\n"},
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "ok"
    assert "1 illustrative" in result.detail


def test_r9_marker_exempts_a_line_that_denies_a_tag(tmp_path):
    """A historical *denial* of a tag is exempt only through the marker.

    The prose says the tag does not exist; the rule cannot tell a denial from a
    claim, so the documented escape - the illustrative marker - is what makes the
    line pass. Without the marker the very same line is drift (see the next
    test).
    """
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "CHANGELOG.md": (
                "# Changelog\n\n## [1.1.0]\n\n"
                "- Its rollback pointed at a `v0.9.0` tag that was never cut. "
                f"{ILLUSTRATIVE}\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "ok"
    assert "1 illustrative" in result.detail


def test_r9_a_denial_without_the_marker_is_still_drift(tmp_path):
    """The rule does not understand negations - the limitation, pinned.

    ``v0.9.0`` is named on a line that says the tag does not exist. R9 reports
    it anyway: it matches the frozen tag-claim pattern and does not parse
    English. The marker is therefore the only escape, which is why a
    denying line must carry it.
    """
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "CHANGELOG.md": (
                "# Changelog\n\n## [1.1.0]\n\n"
                "- Its rollback pointed at a `v0.9.0` tag that was never cut.\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "DRIFT"
    assert "CHANGELOG.md:5" in result.detail
    assert "v0.9.0" in result.detail


def test_r9_marker_on_one_line_does_not_exempt_a_genuine_claim(tmp_path):
    """The marker exempts its own line only; a real claim beside it is drift."""
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "README.md": (
                "# Teamwork\n\n"
                f"The v0.9.0 tag was never cut. {ILLUSTRATIVE}\n\n"
                "Install with `--branch v9.9.9`\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r9_markdown_tags(root)

    assert result.status == "DRIFT"
    assert "README.md:5" in result.detail
    assert "v9.9.9" in result.detail


def test_r9_archive_is_out_of_scope_for_every_scanner(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    write(
        root,
        {
            "docs/Team/Archive.md": (
                "# Archive\n\n"
                "Passed at v9.9.9, and the release printed teamwork 0.0.1.\n\n"
                "```\npip install teamwork-old\n```\n"
            )
        },
    )
    commit(root, message="historical evidence")

    assert crc.markdown_paths(root) == [
        rel for rel in crc.markdown_paths(root) if rel != crc.SCAN_EXCLUDED
    ]
    assert crc.rule_r9_markdown_tags(root).status == "ok"
    assert crc.rule_r8_install_channels(root).status == "SKIP"
    assert crc.rule_r6_markdown_versions(root).status == "ok"


# --------------------------------------------------------------------------- #
# Exit codes and the JSON contract
# --------------------------------------------------------------------------- #


def clean_root(tmp_path: Path) -> Path:
    """R1/R2/R7 clean, exceptions empty; the network rules can only SKIP."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")
    return root


def test_main_exits_zero_on_a_clean_fixture(tmp_path):
    root = clean_root(tmp_path)

    code, stdout, stderr = run_main(["--offline", "--repo-root", str(root)])

    assert (code, stderr) == (0, "")
    assert stdout.splitlines()[-1] == "# release consistency: 0 problem(s)"
    assert [line.split()[0] for line in stdout.splitlines()[:-1]] == [
        f"R{index}" for index in range(1, 10)
    ]


def test_main_exits_one_on_a_drifted_fixture(tmp_path):
    """A reachable tag ahead of HEAD is the R2 drift the gate must report."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.0.0")

    code, stdout, _ = run_main(["--offline", "--repo-root", str(root)])

    assert code == 1
    assert "R2 DRIFT" in stdout
    assert "# release consistency: 1 problem(s)" in stdout


def test_main_exits_two_when_the_repo_root_is_not_a_work_tree(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    code, stdout, _ = run_main(["--offline", "--repo-root", str(plain)])

    assert code == 2
    assert "not a git work tree" in stdout
    assert all(" SKIP " in line for line in stdout.splitlines()[:-1])


def test_main_exits_two_for_a_missing_repo_root(tmp_path):
    code, _, _ = run_main(["--offline", "--repo-root", str(tmp_path / "absent")])

    assert code == 2


def test_json_output_carries_problems_rules_and_exit_code(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.0.0")

    code, stdout, _ = run_main(["--offline", "--json", "--repo-root", str(root)])
    payload = json.loads(stdout)

    assert code == 1
    assert list(payload) == ["problems", "rules", "exit_code"]
    assert payload["exit_code"] == code
    assert [rule["id"] for rule in payload["rules"]] == [f"R{index}" for index in range(1, 10)]
    assert payload["problems"] == [
        {"rule": "R2", "detail": "HEAD version 1.0.0 is not greater than tag v1.1.0"}
    ]
    assert all(rule["detail"] for rule in payload["rules"])


def test_json_exit_code_is_two_when_an_input_is_unreadable(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    code, stdout, _ = run_main(["--offline", "--json", "--repo-root", str(plain)])

    assert code == 2
    assert json.loads(stdout)["exit_code"] == 2


# --------------------------------------------------------------------------- #
# The whole gate on one fixture, rule by rule
# --------------------------------------------------------------------------- #


def test_offline_run_never_reports_ok_for_a_network_rule(tmp_path):
    """A silent ``ok`` on a rule that never queried the registry would be a lie."""
    root = clean_root(tmp_path)

    code, stdout, _ = run_main(["--offline", "--repo-root", str(root)])
    statuses = {line.split()[0]: line.split()[1] for line in stdout.splitlines() if line[:1] == "R"}

    assert code == 0
    assert set(statuses) == {f"R{index}" for index in range(1, 10)}
    for rule in NETWORK_RULES:
        assert statuses[rule] == "SKIP", f"{rule} must not pass offline: {statuses[rule]}"
    for line in stdout.splitlines()[:-1]:
        if line.split()[1] == "SKIP":
            assert "offline" in line, line


def test_every_scanner_is_evaluated_on_a_fixture_with_a_tag(tmp_path):
    """Guard against a fixture that makes a rule vacuously pass by having no input."""
    root = make_repo(tmp_path / "repo", files=PAYLOAD)
    git(root, "tag", "v1.1.0")

    results = {
        "R1": crc.rule_r1_tagged_version(root),
        "R6": crc.rule_r6_markdown_versions(root),
        "R7": crc.rule_r7_changelog(root),
        "R9": crc.rule_r9_markdown_tags(root),
    }

    assert {rule: result.status for rule, result in results.items()} == {
        "R1": "ok",
        "R6": "ok",
        "R7": "ok",
        "R9": "ok",
    }
    assert "1 tag(s) agree" in results["R1"].detail
    assert "1 tagged version(s)" in results["R7"].detail


@pytest.fixture(autouse=True)
def _no_socket(monkeypatch: Iterator[None]) -> Iterator[None]:
    """No test may reach the network: the seam raises instead of opening a socket."""
    if _CHECKER_MODULE is None:
        # The checker is absent; nothing can open a socket through it.
        yield
        return

    def refuse(url: str) -> object:
        raise AssertionError(f"a test opened a socket: {url}")

    monkeypatch.setattr(crc, "_http_get", refuse)
    monkeypatch.setattr(crc, "_http_get_json", refuse)
    monkeypatch.setattr(crc, "_http_get_bytes", refuse)
    yield


# --------------------------------------------------------------------------- #
# The loader: the file must be collectible and runnable wherever the checker is
# --------------------------------------------------------------------------- #


def test_the_checker_surface_is_available():
    """The loader must either find the checker or say exactly where it looked.

    This test always runs, with or without the checker: it is what stops the
    "the whole file was skipped" hole. A skip that hid every assertion would
    leave a green suite that proves nothing.
    """
    if _CHECKER_MODULE is None:
        assert CHECKER_PATH is None
        assert CHECKER_FILENAME in CHECKER_MISSING_REASON
        for candidate in candidate_checker_paths():
            assert str(candidate) in CHECKER_MISSING_REASON
        assert not candidate_checker_paths()[0].exists()
        return
    # The checker is present: it must expose the documented surface.
    for name in (
        "main",
        "payload_digest",
        "rule_r1_tagged_version",
        "rule_r2_head_is_newer",
        "rule_r3_npm_payloads",
        "rule_r4_releases_have_tags",
        "rule_r5_tags_have_releases",
        "rule_r6_markdown_versions",
        "rule_r7_changelog",
        "rule_r8_install_channels",
        "rule_r9_markdown_tags",
        "load_exceptions",
        "InputError",
        "RuleResult",
    ):
        assert hasattr(crc, name), f"the checker has no {name}"


def test_the_checker_is_loaded_by_path_not_by_sys_path():
    """A plain import would shadow the real ``teamwork`` package.

    ``scripts/teamwork.py`` is the CLI; putting ``scripts/`` on ``sys.path``
    makes every later import of ``teamwork`` in the session resolve to the
    script instead of the package under ``src/``.
    """
    if _CHECKER_MODULE is None:
        return
    import teamwork

    assert str(REPO_ROOT / "scripts") not in sys.path
    assert crc.__name__ == "check_release_consistency_under_test"
    assert crc.__file__ == str(CHECKER_PATH)
    assert not getattr(teamwork, "__file__", "").endswith("scripts/teamwork.py")


def test_an_explicit_override_points_the_loader_at_one_file(monkeypatch):
    """``TEAMWORK_RELEASE_CHECKER`` names the checker, so a mutated copy can be run."""
    candidates = candidate_checker_paths()
    assert candidates

    monkeypatch.setenv("TEAMWORK_RELEASE_CHECKER", "/nonexistent/checker.py")
    assert candidate_checker_paths() == [Path("/nonexistent/checker.py")]


# --------------------------------------------------------------------------- #
# 11.3 - the payload digest and the symlink policy
# --------------------------------------------------------------------------- #

#: A link cannot be created without privileges on Windows, so the link policy
#: is only exercised where the platform supports it.
needs_symlinks = pytest.mark.skipif(
    os.name == "nt", reason="creating a symlink needs Developer Mode on Windows"
)


def payload_repo(root: Path, version: str = "1.1.0") -> Path:
    """A fixture whose tree carries the whole 11.3 payload."""
    files = {
        "SKILL.md": "# Skill\n",
        "AGENTS.md": "# Agents\n",
        "roles/developer.md": "# Developer\n",
        "src/teamwork/version.py": VERSION_FILE.format(version=version),
    }
    root.mkdir(parents=True, exist_ok=True)
    write(root, files)
    git(root, "init", "-q")
    commit(root, message="payload")
    return root


@needs_symlinks
def test_11_3_a_link_in_the_commit_resolves_to_its_target_bytes(tmp_path):
    """11.3: "Symlinks are resolved." A link contributes its target's bytes."""
    root = payload_repo(tmp_path / "repo")
    os.symlink("../SKILL.md", root / "roles" / "link.md")
    commit(root, message="add a link")

    digest = crc.payload_digest(root, None)

    # The link resolves to SKILL.md's bytes, so the digest is the digest of the
    # tree with that file *in place of* the link - not the digest of a tree
    # where the link is simply absent.
    plain = payload_repo(tmp_path / "plain")
    commit(plain, {"roles/link.md": "# Skill\n"}, message="the same bytes as a file")
    assert digest == crc.payload_digest(plain, None)
    assert len(digest) == 16


@needs_symlinks
def test_11_3_the_two_digest_paths_agree_on_the_same_tree(tmp_path):
    """``rev=None`` and ``rev="HEAD"`` must never disagree about one commit.

    The two paths are separate code (the working tree against ``git archive``),
    so they can drift apart; the contract wants one number for one tree.
    """
    root = payload_repo(tmp_path / "repo")
    os.symlink("../SKILL.md", root / "roles" / "link.md")
    commit(root, message="add a link")

    assert crc.payload_digest(root, None) == crc.payload_digest(root, "HEAD")


@needs_symlinks
def test_11_3_a_link_to_a_gitignored_file_is_refused(tmp_path):
    """A link to a file that is not in the commit cannot be resolved.

    The file is gitignored, so it is not in the commit and therefore not in
    ``git archive``'s output: the link has no target in the tree that the
    digest is built from. 11.3 makes an unreadable file drift, not a skip.
    """
    root = payload_repo(tmp_path / "repo")
    write(root, {".gitignore": "secret.txt\n", "secret.txt": "SECRET\n"})
    commit(root, message="ignore a file that is never committed")
    os.symlink("../secret.txt", root / "roles" / "link.md")
    commit(root, message="a link to the ignored file")

    with pytest.raises(crc.InputError):
        crc.payload_digest(root, None)


@needs_symlinks
def test_11_3_the_working_tree_contributes_no_byte_to_the_digest(tmp_path):
    """Editing a file on disk must not move the digest of a commit.

    The two digest paths must agree, and the only way they can is if both read
    the *commit* rather than the working tree: a working tree can hold a link
    into ``.git``, and those bytes would then reach the digest and the printed
    output. Measured against the implementation at c66c387, which reads
    ``rev=None`` as the commit ``HEAD`` names.
    """
    root = payload_repo(tmp_path / "repo")
    write(root, {".gitignore": "secret.txt\n", "secret.txt": "SECRET\n"})
    git(root, "add", "-f", "secret.txt")
    commit(root, message="a tracked, gitignored file")
    os.symlink("../secret.txt", root / "roles" / "link.md")
    commit(root, message="a link to it")

    before = crc.payload_digest(root, None)
    (root / "secret.txt").write_text("CHANGED ON DISK\n", encoding="utf-8")

    assert crc.payload_digest(root, None) == before
    assert crc.payload_digest(root, "HEAD") == before


@needs_symlinks
def test_11_3_a_link_into_the_git_directory_is_refused_and_named_nowhere(tmp_path):
    """A link to ``../.git/config`` must be refused *and* must not be echoed.

    The refusal names the *member* (the link), never the target: the target
    can be a file that carries a remote URL with a token.
    """
    root = payload_repo(tmp_path / "repo")
    os.symlink("../../.git/config", root / "roles" / "link.md")
    commit(root, message="a link into .git")

    with pytest.raises(crc.InputError) as caught:
        crc.payload_digest(root, None)

    message = str(caught.value)
    assert "config" not in message
    assert "link.md" in message


@needs_symlinks
def test_11_3_an_absolute_link_is_refused(tmp_path):
    """An absolute link points outside the tree by construction."""
    root = payload_repo(tmp_path / "repo")
    os.symlink("/etc/hostname", root / "roles" / "abs.md")
    commit(root, message="an absolute link")

    with pytest.raises(crc.InputError) as caught:
        crc.payload_digest(root, None)

    assert "abs.md" in str(caught.value)
    assert "hostname" not in str(caught.value)


@needs_symlinks
def test_11_3_a_broken_link_is_refused(tmp_path):
    """A link whose target does not exist cannot be resolved, so it is drift."""
    root = payload_repo(tmp_path / "repo")
    os.symlink("../nope.md", root / "roles" / "broken.md")
    commit(root, message="a broken link")

    with pytest.raises(crc.InputError):
        crc.payload_digest(root, None)


@needs_symlinks
def test_11_3_a_cyclic_pair_of_links_is_refused(tmp_path):
    """Two links pointing at each other resolve to nothing."""
    root = payload_repo(tmp_path / "repo")
    os.symlink("../roles/b.md", root / "roles" / "a.md")
    os.symlink("../roles/a.md", root / "roles" / "b.md")
    commit(root, message="a cyclic pair")

    with pytest.raises(crc.InputError):
        crc.payload_digest(root, None)


@needs_symlinks
def test_11_3_a_self_referential_link_is_refused(tmp_path):
    """A link pointing at itself is the degenerate cyclic case."""
    root = payload_repo(tmp_path / "repo")
    os.symlink("self.md", root / "roles" / "self.md")
    commit(root, message="a self link")

    with pytest.raises(crc.InputError):
        crc.payload_digest(root, None)


# --------------------------------------------------------------------------- #
# 11.2.4 R8 - an install line in inline code names a script too
# --------------------------------------------------------------------------- #


def test_r8_an_inline_code_install_line_names_the_script_it_runs(tmp_path):
    """The inline-code form of an install line is a channel like any other.

    The tokenizer once captured the closing backtick with the argument, so
    ``uvx --from teamwork-agents wrongscript`` yielded no script at all and the
    rule reported 0 findings end to end - the drift was invisible.
    """
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "README.md": "# Teamwork\n\nRun `uvx --from teamwork-agents wrongscript` to try it.\n"
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "wrongscript" in result.detail
    assert "[project.scripts]" in result.detail


def test_r8_an_inline_code_channel_without_a_script_invents_none(tmp_path):
    """``uvx --from teamwork-agents`` names a distribution, not an executable.

    The trailing word of a prose sentence is not a script name, and the
    distribution alone must not be read as a missing console script.
    """
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "README.md": "# Teamwork\n\n`uvx --from teamwork-agents` is the fastest way to try it.\n"
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "SKIP"
    assert "not a [project.scripts] entry" not in result.detail


def test_r8_a_flag_before_the_script_is_not_the_script(tmp_path):
    """``--python 3.12`` is a flag and its value, not the executable name."""
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        files={
            "README.md": (
                "# Teamwork\n\n`uvx --from teamwork-agents --python 3.12 wrongscript --version`\n"
            )
        },
    )
    git(root, "tag", "v1.1.0")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "wrongscript" in result.detail
    assert "--python" not in result.detail
    assert "3.12" not in result.detail


# --------------------------------------------------------------------------- #
# 11.2.3 R3 - an exception admits one version, never every version
# --------------------------------------------------------------------------- #


def test_r3_an_exception_admits_one_version_and_not_another(tmp_path):
    """One exception must not admit the whole registry.

    The admission test is ``version in admitted``. Read as ``if admitted``,
    a single recorded exception would swallow every published version and R3
    would pass for versions that cannot be traced to any commit.
    """
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    exceptions = [
        {
            "version": "9.9.9",
            "reason": "published from a workspace whose commit was never pushed",
            "evidence": "digest 0123456789abcdef matches no commit in git rev-list --all",
            "recorded": "2026-10-20",
        }
    ]
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"9.9.9": "x", "8.8.8": "x"})})

    result = crc.rule_r3_npm_payloads(root, exceptions, fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "DRIFT"
    assert any("8.8.8" in finding for finding in result.findings)
    assert not any("9.9.9" in finding for finding in result.findings)
    # The admitted version is still *visible* in the detail - it is a note, not
    # a finding, so the reader sees what was excused.
    assert "9.9.9 admitted by exception" in result.detail


def test_r3_an_unadmitted_version_is_reported_even_next_to_an_admitted_one(tmp_path):
    """The unadmitted version must be *named*, not merely counted."""
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    exceptions = [
        {
            "version": "1.1.1",
            "reason": "a workspace commit that was never pushed",
            "evidence": "digest 0123456789abcdef matches no commit",
            "recorded": "2026-10-20",
        }
    ]
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"1.1.1": "x", "1.1.2": "x"})})

    result = crc.rule_r3_npm_payloads(root, exceptions, fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "DRIFT"
    assert any("1.1.2" in finding for finding in result.findings)
    assert any("no tag v1.1.2" in finding for finding in result.findings)
    assert not any("1.1.1" in finding for finding in result.findings)


def test_r3_an_exception_admits_only_the_version_it_names_end_to_end(tmp_path):
    """The same admission rule, driven through the whole gate.

    ``main`` reads the exception file from the repository, so the recorded
    exception must admit its own version and nothing else there either.
    """
    root = make_repo(
        tmp_path / "repo",
        version="1.1.0",
        exceptions=json.dumps(
            [
                {
                    "version": "9.9.9",
                    "reason": "published from a workspace whose commit was never pushed",
                    "evidence": "digest 0123456789abcdef matches no commit",
                    "recorded": "2026-10-20",
                }
            ]
        ),
    )
    git(root, "tag", "v1.1.0")
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"9.9.9": "x", "8.8.8": "x"})})

    result = crc.rule_r3_npm_payloads(
        root,
        crc.load_exceptions(root / "release-exceptions.json"),
        fetch,
        lambda url: tarball(PAYLOAD),
    )

    assert result.status == "DRIFT"
    assert any("8.8.8" in finding for finding in result.findings)
    assert not any("9.9.9" in finding for finding in result.findings)


def test_r3_an_exception_admits_exactly_its_own_version_and_no_other(tmp_path):
    """The admission is per version: the exception's own version and nothing else.

    Two npm versions are published; one of them has a recorded exception, the
    other has no tag and therefore cannot be traced to any commit. The gate
    must report the untraceable one (11.2.3: an exception "cannot silence a
    DRIFT that R3 found for a *different* version").

    The admission test is ``version in admitted``. Read as ``if admitted`` -
    the truthiness of the admitted set - a single recorded exception would
    swallow the second version too and R3 would report ``ok`` for a publish
    that cannot be traced to any commit. That is the defect this test pins.
    """
    root = make_repo(tmp_path / "repo", version="1.1.0")
    git(root, "tag", "v1.1.0")
    exceptions = [
        {
            "version": "1.1.1",
            "reason": "published from a workspace whose commit was never pushed",
            "evidence": "digest 0123456789abcdef matches no commit in git rev-list --all",
            "recorded": "2026-10-20",
        }
    ]
    fetch = fake_http({crc.NPM_REGISTRY: npm_registry({"1.1.1": "x", "1.1.2": "x"})})

    result = crc.rule_r3_npm_payloads(root, exceptions, fetch, lambda url: tarball(PAYLOAD))

    assert result.status == "DRIFT"
    # The untraceable version is named, and named as untraceable.
    assert any("1.1.2" in finding for finding in result.findings)
    assert any("no tag v1.1.2" in finding for finding in result.findings)
    # The admitted version produces no finding at all - it is excused, not drifted.
    assert not any("1.1.1" in finding for finding in result.findings)
    # The admission stays visible on every run.
    assert "1.1.1 admitted by exception" in result.detail


def test_load_exceptions_returns_every_recorded_entry(tmp_path):
    """The loader hands the recorded entries to the admission test.

    A loader that returns an empty list would leave the gate with no
    exception at all, so every published version would be compared - and the
    recorded admission would be silently forgotten. The loaded entry must
    therefore carry the four contract keys of 11.4.
    """
    root = make_repo(
        tmp_path / "repo",
        exceptions=json.dumps(
            [
                {
                    "version": "1.1.1",
                    "reason": "published from a workspace whose commit was never pushed",
                    "evidence": "digest 0123456789abcdef matches no commit",
                    "recorded": "2026-10-20",
                }
            ]
        ),
    )

    entries = crc.load_exceptions(root / "release-exceptions.json")

    assert len(entries) == 1
    assert entries[0]["version"] == "1.1.1"
    assert set(entries[0]) == {"version", "reason", "evidence", "recorded"}


def test_load_exceptions_rejects_an_entry_with_a_missing_key(tmp_path):
    """An entry without all four contract keys is an input error (11.4).

    A loader that tolerates a missing ``evidence`` (or ``reason``, or
    ``recorded``) would admit a version on a record no reviewer can judge -
    the "silent pass" 11.4 forbids.
    """
    root = make_repo(tmp_path / "repo")
    write(
        root,
        {
            "release-exceptions.json": json.dumps(
                [
                    {
                        "version": "1.1.1",
                        "reason": "published from a workspace whose commit was never pushed",
                        "recorded": "2026-10-20",
                    }
                ]
            )
        },
    )

    with pytest.raises(crc.InputError, match="missing key"):
        crc.load_exceptions(root / "release-exceptions.json")


def test_r3_a_missing_exception_file_is_an_input_error(tmp_path):
    """A missing exception file is exit 2, never "there are no exceptions".

    11.4: "Missing file ... is an input error: exit 2". Reading a missing file
    as an empty exception list would make the gate pass a publish that has no
    recorded admission at all - the failure this whole rule exists to remove.
    """
    root = make_repo(tmp_path / "repo", version="1.1.0")
    (root / "release-exceptions.json").unlink()

    with pytest.raises(crc.InputError, match="missing"):
        crc.load_exceptions(root / "release-exceptions.json")

    code, stdout, _ = run_main(["--offline", "--repo-root", str(root)])
    assert code == 2
    assert "R3 SKIP" in stdout
    assert "missing" in stdout


#: The bundled payload of the fixture below, exactly as 11.3 defines it: the two
#: files plus the two trees, with nothing else. The root files of the fixture
#: (pyproject.toml, CHANGELOG.md, README.md, release-exceptions.json) are not
#: payload and are therefore not in the digest.
FIXTURE_PAYLOAD = (
    "AGENTS.md",
    "SKILL.md",
    "roles/developer.md",
    "src/teamwork/version.py",
)


def contract_payload_digest(root: Path, names: Sequence[str]) -> str:
    """The 11.3 digest, computed from the contract's own recipe.

    The recipe is written out here rather than reused from the checker, so the
    test pins the *contract* and not the implementation: sorted
    ``"{sha256}  {relpath}"`` lines, two spaces, joined with "\\n", one trailing
    newline, hashed once, truncated to 16 hex characters.
    """
    lines = []
    for rel in sorted(names):
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  {rel}")
    joined = "\n".join(sorted(lines)) + "\n"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def test_11_3_the_digest_is_the_contract_recipe_computed_over_the_payload(tmp_path):
    """The digest is a *number*, not just "something that changes".

    A digest that is merely self-consistent would still be wrong: the published
    form is a number other tools compute from the contract. Sorting the lines,
    the two-space separator and the single trailing newline are all part of the
    frozen recipe, so the test recomputes the recipe and compares.
    """
    root = payload_repo(tmp_path / "repo")

    digest = crc.payload_digest(root, "HEAD")

    assert digest == contract_payload_digest(root, FIXTURE_PAYLOAD)
    assert len(digest) == 16
    assert all(char in "0123456789abcdef" for char in digest)


@needs_symlinks
def test_11_3_a_link_outside_the_tree_is_refused_even_when_its_target_exists(tmp_path):
    """A relative link that escapes the tree must not contribute foreign bytes.

    The target is a real file outside the tree, so without the refusal the
    digest would silently hash bytes that are not this repository's payload.
    """
    root = payload_repo(tmp_path / "repo")
    os.symlink("../../../../../../etc/hostname", root / "roles" / "escape.md")
    commit(root, message="a link that escapes the tree")

    with pytest.raises(crc.InputError):
        crc.payload_digest(root, None)


@needs_symlinks
def test_11_3_a_link_into_a_git_directory_inside_the_tree_is_refused(tmp_path):
    """A ``.git`` directory is never payload, wherever it sits in the tree.

    The link resolves *inside* the tree (to ``<root>/.git/config``), so the
    refusal cannot come from the "outside the tree" rule: it is the ``.git``
    rule that refuses it, because those bytes are not payload and a remote URL
    carrying a token would otherwise reach the digest and the printed output.
    """
    root = payload_repo(tmp_path / "repo")
    os.symlink("../.git/config", root / "roles" / "link.md")
    commit(root, message="a link into the git directory")

    with pytest.raises(crc.InputError) as caught:
        crc.payload_digest(root, None)

    message = str(caught.value)
    assert "config" not in message
    assert "link.md" in message


# --------------------------------------------------------------------------- #
# 11.2.2 - R2's tag set is the *reachable* tags, minus the tags at HEAD
# --------------------------------------------------------------------------- #


def branched_repo(root: Path) -> Path:
    """A fixture with a main line and a side line that carries its own tag.

    The side line's ``v2.0.0`` is not an ancestor of the main line's HEAD, so
    it is outside ``A`` in 11.2.2's terms.
    """
    make_repo(root, version="1.0.0")
    git(root, "tag", "v1.0.0")
    git(root, "checkout", "-q", "-b", "side")
    bump(root, "2.0.0")
    git(root, "tag", "v2.0.0")
    git(root, "checkout", "-q", "-b", "trunk", "HEAD~1")
    bump(root, "1.1.0")
    git(root, "tag", "v1.1.0")
    return root


def test_r2_contract_a_non_ancestor_tag_is_still_checked_by_r1(tmp_path):
    """A tag outside HEAD's history is invisible to R2 but not to R1.

    R1 evaluates every tag against its own commit, so it sees ``v2.0.0`` even
    though ``v2.0.0`` is not an ancestor of HEAD.
    """
    root = branched_repo(tmp_path / "repo")

    result = crc.rule_r1_tagged_version(root)

    assert result.status == "ok"
    assert "3 tag(s) agree" in result.detail


def test_r2_contract_the_tag_count_is_never_negative(tmp_path):
    """The old defect printed ``is newer than -2 tag(s)``.

    The count is subtracted from the *reachable* version tags only, so it can
    never be negative whatever the repository holds.
    """
    root = make_repo(tmp_path / "repo", version="1.2.0")
    git(root, "tag", "v1.2.0")
    git(root, "tag", "nightly")
    git(root, "tag", "docs-v1")

    result = crc.rule_r2_head_is_newer(root)

    match = re.search(r"newer than (-?\d+) tag", result.detail)
    if match is not None:
        assert int(match.group(1)) >= 0, result.detail


def test_r2_contract_a_maintenance_branch_off_an_old_tag_is_ok(tmp_path):
    """11.2.2: "A maintenance branch is not permanently red."

    The maintenance line branched off ``v1.0.0`` and carries ``v1.0.1`` on its
    own HEAD; the main line's later tags are not its ancestors, so they are
    outside ``A`` and R2 is ok with ``|S| = 1``.
    """
    root = make_repo(tmp_path / "repo", version="1.0.0")
    git(root, "tag", "v1.0.0")
    git(root, "checkout", "-q", "-b", "maint")
    bump(root, "1.0.1")
    git(root, "tag", "v1.0.1")
    git(root, "checkout", "-q", "-b", "trunk", "HEAD~1")
    bump(root, "1.1.0")
    git(root, "tag", "v1.1.0")
    git(root, "checkout", "-q", "maint")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert "newer than 1 tag(s)" in result.detail


def test_r2_contract_a_tag_at_head_is_excluded_from_the_count(tmp_path):
    """The commit that carries ``vX.Y.Z`` has ``version.py == X.Y.Z``.

    Comparing HEAD against that tag could only ever ask whether a release is
    greater than itself, so the tag at HEAD is excluded and the count is the
    number of *other* reachable version tags.
    """
    root = make_repo(tmp_path / "repo", version="1.2.0")
    git(root, "tag", "v1.1.0")
    bump(root, "1.2.0")
    git(root, "tag", "v1.2.0")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert "newer than 1 tag(s)" in result.detail


def test_r2_contract_a_non_ancestor_tag_is_invisible_to_r2(tmp_path):
    """R2 alone ignores a tag that says nothing about this checkout."""
    root = branched_repo(tmp_path / "repo")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "ok"
    assert "v2.0.0" not in result.detail


# --------------------------------------------------------------------------- #
# 11.2.2 - a shallow clone is an input error, never a clean run
# --------------------------------------------------------------------------- #


def test_a_shallow_clone_is_an_input_error(tmp_path):
    """A blind checkout must not turn the gate green.

    ``actions/checkout`` without ``fetch-depth: 0`` gives a clone that cannot
    see the tags; the contract makes that an input error, so every tag rule
    exits 2 with the reason in its detail.
    """
    source = make_repo(tmp_path / "source", version="1.0.0")
    git(source, "tag", "v1.0.0")
    clone = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", f"file://{source}", str(clone)],
        check=True,
        capture_output=True,
    )
    assert git(clone, "rev-parse", "--is-shallow-repository").strip() == "true"

    code, stdout, _ = run_main(["--offline", "--repo-root", str(clone)])

    assert code == 2
    assert "shallow" in stdout


def test_an_empty_tag_set_while_the_remote_carries_tags_is_an_input_error(tmp_path):
    """The other half of the same guard: the tags are simply not there."""
    source = make_repo(tmp_path / "source", version="1.0.0")
    git(source, "tag", "v1.0.0")
    clone = tmp_path / "untagged"
    subprocess.run(
        ["git", "clone", "-q", str(source), str(clone)],
        check=True,
        capture_output=True,
    )
    git(clone, "tag", "-d", "v1.0.0")
    assert git(source, "tag", "-l").strip() == "v1.0.0"

    code, stdout, _ = run_main(["--offline", "--repo-root", str(clone)])

    assert code == 2
    assert "0 tag(s) agree" not in stdout


def link_refusal_reason(root: Path) -> str:
    """The reason of the refusal ``payload_digest`` raises for this tree.

    The reason is the message without the member names, so two different
    causes that are merely reported with different file names still count as
    the same reason.
    """
    with pytest.raises(crc.InputError) as caught:
        crc.payload_digest(root, None)
    return str(caught.value).split(":")[0].strip()


@needs_symlinks
def test_11_3_each_kind_of_link_refusal_says_a_different_reason(tmp_path):
    """The refusal must say *why*, not only that it refused.

    An operator reading the output has to be able to tell an absolute link
    from a link that escapes the tree, from a link into the git directory and
    from a link that is simply broken. Four causes with one reason would hide
    which one it is - and the test is what keeps the four rules apart: a
    single rule that swallows all four causes passes this test only if it can
    still tell them apart.
    """
    absolute = payload_repo(tmp_path / "absolute")
    os.symlink("/etc/hostname", absolute / "roles" / "abs.md")
    commit(absolute, message="an absolute link")

    escaping = payload_repo(tmp_path / "escaping")
    os.symlink("../../../../../../etc/hostname", escaping / "roles" / "escape.md")
    commit(escaping, message="a link that escapes the tree")

    into_git = payload_repo(tmp_path / "into_git")
    os.symlink("../.git/config", into_git / "roles" / "link.md")
    commit(into_git, message="a link into the git directory")

    broken = payload_repo(tmp_path / "broken")
    os.symlink("../nope.md", broken / "roles" / "broken.md")
    commit(broken, message="a broken link")

    reasons = {
        "absolute": link_refusal_reason(absolute),
        "escaping": link_refusal_reason(escaping),
        "into_git": link_refusal_reason(into_git),
        "broken": link_refusal_reason(broken),
    }

    assert len(set(reasons.values())) == 4, reasons
