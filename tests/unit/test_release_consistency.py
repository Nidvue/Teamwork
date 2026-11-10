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
import io
import json
import subprocess
import sys
import tarfile
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

# ``tests/unit/test_release_consistency.py`` -> parents[2] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

# The checker is a script, not a package module, so it is imported by path. The
# directory is removed again because ``scripts/teamwork.py`` would otherwise
# shadow the real ``teamwork`` package for every later test in the session.
_SCRIPTS_ADDED = str(SCRIPTS) not in sys.path
if _SCRIPTS_ADDED:
    sys.path.insert(0, str(SCRIPTS))

import check_release_consistency as crc  # noqa: E402  (import after sys.path setup)

if _SCRIPTS_ADDED:
    sys.path.remove(str(SCRIPTS))


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


def test_r2_reports_head_equal_to_a_tag(tmp_path):
    root = make_repo(tmp_path / "repo", version="1.2.0")
    git(root, "tag", "v1.2.0")

    result = crc.rule_r2_head_is_newer(root)

    assert result.status == "DRIFT"
    assert "not greater than tag v1.2.0" in result.detail


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
    root = clean_root(tmp_path)
    git(root, "tag", "v1.2.0")

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
    root = clean_root(tmp_path)
    git(root, "tag", "v1.2.0")

    code, stdout, _ = run_main(["--offline", "--json", "--repo-root", str(root)])
    payload = json.loads(stdout)

    assert code == 1
    assert list(payload) == ["problems", "rules", "exit_code"]
    assert payload["exit_code"] == code
    assert [rule["id"] for rule in payload["rules"]] == [f"R{index}" for index in range(1, 10)]
    assert payload["problems"] == [
        {"rule": "R2", "detail": "HEAD version 1.2.0 is not greater than tag v1.2.0"}
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

    def refuse(url: str) -> object:
        raise AssertionError(f"a test opened a socket: {url}")

    monkeypatch.setattr(crc, "_http_get", refuse)
    monkeypatch.setattr(crc, "_http_get_json", refuse)
    monkeypatch.setattr(crc, "_http_get_bytes", refuse)
    yield
