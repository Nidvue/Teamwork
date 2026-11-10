"""R8's per-claim warning exemption (T-0010).

11.2.4 scopes R8 to an **advertised** install channel. A line that names a
distribution in order to warn against it - risk R-8 in ``docs/Team/Risks.md``
names the taken ``teamwork`` PyPI name - is a hazard statement, not an
advertisement, and must not be a drift.

The exemption is per claim, not per line: a line that both warns and
advertises keeps the shipped name under the normal check.

The checker is loaded by path, so this file stays collectible on a revision
where the checker has not landed. Every fixture is a synthetic repository built
in ``tmp_path``; no test opens a socket and no test reads this repository's own
tree.

Owner: developer. Task: T-0010.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "scripts" / "check_release_consistency.py"

SKIP_REASON = "scripts/check_release_consistency.py is not present on this revision"

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


def _load_checker():
    """Load the checker by path, or skip when it is not on this revision."""
    if not CHECKER_PATH.is_file():
        pytest.skip(SKIP_REASON)
    spec = importlib.util.spec_from_file_location("check_release_consistency_r8", CHECKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The dataclasses in the checker resolve their own module, so it must be
    # importable by name before the body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crc = _load_checker()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *GIT_OPTIONS, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(root: Path, readme: str) -> Path:
    """A committed fixture that ships ``teamwork-agents`` and one script."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    write(
        root,
        "pyproject.toml",
        '[project]\nname = "teamwork-agents"\n\n[project.scripts]\nteamwork = "teamwork.cli:main"\n',
    )
    write(root, "src/teamwork/version.py", '__version__ = "1.1.0"\nDIST_NAME = "teamwork-agents"\n')
    write(root, "README.md", readme)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture")
    return root


RISK_ROW = (
    "| R-8 | The `teamwork` PyPI name is taken, so `pip install teamwork` gets "
    "the wrong project | delivery | high | low | Distribution name `teamwork-agents` "
    "| ReleaseEngineer | resolved |"
)


# --------------------------------------------------------------------------- #
# the loader
# --------------------------------------------------------------------------- #


def test_the_loader_works():
    """The module loaded by path exposes the rule the fix changed."""
    assert hasattr(crc, "rule_r8_install_channels")
    assert hasattr(crc, "WARNING_CONTEXT")


# --------------------------------------------------------------------------- #
# a hazard statement is not an advertisement
# --------------------------------------------------------------------------- #


def test_the_risk_row_is_not_drift(tmp_path):
    root = make_repo(tmp_path / "repo", f"# Teamwork\n\n{RISK_ROW}\n")

    result = crc.rule_r8_install_channels(root)

    assert result.status != "DRIFT"
    assert "Risks" not in result.detail


@pytest.mark.parametrize(
    "line",
    [
        "The `teamwork` PyPI name is taken, so `pip install teamwork` gets the wrong project",
        "`pip install teamwork` resolves to a different package",
        "`pip install teamwork` installs another project entirely",
        "the `teamwork` name belongs to another project",
        "`pip install teamwork` gets you an unrelated package by that name",
    ],
)
def test_a_hazard_statement_is_not_drift(tmp_path, line):
    root = make_repo(tmp_path / "repo", f"# Teamwork\n\n{line}\n")

    result = crc.rule_r8_install_channels(root)

    assert result.status != "DRIFT"


def test_a_plain_advice_line_is_drift(tmp_path):
    """No hazard context: the claim is an advertisement and is checked."""
    root = make_repo(tmp_path / "repo", "# Teamwork\n\nJust run `pip install teamwork` to start.\n")

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "teamwork" in result.detail


def test_a_bare_wrong_is_not_a_hazard(tmp_path):
    """A bare "wrong" is advice, not a warning about a name."""
    root = make_repo(
        tmp_path / "repo",
        "# Teamwork\n\nThe wrong way to install is `pip install teamwork` - use `pip install teamwork-agents`\n",
    )

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "teamwork" in result.detail


# --------------------------------------------------------------------------- #
# the exemption is per claim
# --------------------------------------------------------------------------- #


def test_a_line_that_both_warns_and_advertises_keeps_the_good_name_checked(tmp_path):
    """The bad name is exempt, the good name is still an advertisement."""
    root = make_repo(
        tmp_path / "repo",
        "# Teamwork\n\n`pip install teamwork` gets the wrong project; "
        "use `pip install teamwork-agents` instead.\n",
    )

    result = crc.rule_r8_install_channels(root)

    assert result.status != "DRIFT"
    assert "teamwork" not in result.findings


def test_a_line_that_warns_and_advertises_a_bad_script_is_drift(tmp_path):
    """The shipped name on a hazard line is still checked, script and all."""
    root = make_repo(
        tmp_path / "repo",
        "# Teamwork\n\n`pip install teamwork` gets the wrong project; "
        "use `uvx --from teamwork-agents wrongscript` instead.\n",
    )

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "wrongscript" in result.detail


def test_the_shipped_name_on_a_hazard_line_is_still_checked(tmp_path):
    """A hazard context never excuses a claim of the shipped distribution."""
    root = make_repo(
        tmp_path / "repo",
        "# Teamwork\n\n`uvx --from teamwork-agents wrongscript` belongs to a different project\n",
    )

    result = crc.rule_r8_install_channels(root)

    assert result.status == "DRIFT"
    assert "wrongscript" in result.detail


# --------------------------------------------------------------------------- #
# the existing escapes are untouched
# --------------------------------------------------------------------------- #


def test_the_channel_unavailable_marker_still_works(tmp_path):
    root = make_repo(
        tmp_path / "repo",
        "# Teamwork\n\n`pip install teamwork-agents` "
        "<!-- release-consistency: channel-unavailable -->\n",
    )

    result = crc.rule_r8_install_channels(root)

    assert result.status != "DRIFT"
    assert "marked" in result.detail


@pytest.mark.parametrize(
    "line",
    [
        "there is no pip install and no venv",
        "no uvx --from teamwork-agents here",
        "never pipx run --spec teamwork-agents",
    ],
)
def test_the_negated_forms_still_work(tmp_path, line):
    root = make_repo(tmp_path / "repo", f"# Teamwork\n\n{line}\n")

    result = crc.rule_r8_install_channels(root)

    assert result.status != "DRIFT"


def test_an_unreadable_input_is_still_an_error(tmp_path):
    """Exit 2 is unchanged: a tree without git is an input error, not a pass."""
    root = tmp_path / "tarball"
    root.mkdir()
    write(root, "src/teamwork/version.py", '__version__ = "1.1.0"\n')

    assert crc.main(["--offline", "--repo-root", str(root)]) == 2


def test_the_module_imports_on_python_39_plus():
    """The checker is stdlib-only and must stay importable without extras."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import ast,sys;ast.parse(open(sys.argv[1]).read())",
            str(CHECKER_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
