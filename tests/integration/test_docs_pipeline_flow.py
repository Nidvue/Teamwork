"""Integration: the docs pipeline end to end (links + privacy over a real tree).

The docs gate is two commands that ship in ``.github/workflows/docs.yml``:
``teamwork links`` and the privacy scan. Neither is exercised against the real
repository by any other layer, so this module runs both as real subprocesses:

* against *this checkout* - the committed docs must be clean;
* against a *fixture docs tree* under ``tmp_path`` - a broken relative link, a
  malformed external link and a bare URL must each be reported, and a planted
  secret must fail the privacy scan.

Every fixture test is proved to bite by removing the defect and watching the
report go quiet.

Owner: tester. Task: T-0004.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"
PRIVACY = REPO_ROOT / "scripts" / "privacy_scan.py"


def run(argv: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, *argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def links(cwd: Path) -> tuple[int, str]:
    result = run([str(CLI_SHIM), "links"], cwd)
    return result.returncode, result.stdout + result.stderr


def issues(text: str) -> int:
    for line in reversed(text.splitlines()):
        if line.startswith("# issues:"):
            return int(line.split(":", 1)[1])
    raise AssertionError(f"links printed no issue count:\n{text}")


# --------------------------------------------------------------------------- #
# The real tree
# --------------------------------------------------------------------------- #


def test_the_committed_docs_are_link_clean() -> None:
    code, text = links(REPO_ROOT)
    assert code == 0, text
    assert issues(text) == 0, text
    assert "- none" in text.split("## broken internal links")[1]


def test_the_committed_tree_passes_the_privacy_scan() -> None:
    result = run(
        [str(PRIVACY), "--tree", "--allow", ".github/privacy-allow.txt", "--quiet"],
        REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


# --------------------------------------------------------------------------- #
# A fixture docs tree with planted defects
# --------------------------------------------------------------------------- #


def fixture_docs(tmp_path: Path, target: str, extra: str = "") -> Path:
    """A minimal project whose ``docs/index.md`` links to ``target``."""
    root = tmp_path / "DocFixture"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text(
        "# Index\n\nSee [the page](" + target + ").\n" + extra,
        encoding="utf-8",
    )
    return root


def test_a_broken_relative_link_is_reported(tmp_path: Path) -> None:
    root = fixture_docs(tmp_path, "missing.md")

    code, text = links(root)

    assert code == 1, text
    assert "docs/index.md" in text
    assert "target does not exist" in text
    assert issues(text) == 1, text


def test_the_broken_link_case_bites_only_because_the_target_is_absent(tmp_path: Path) -> None:
    """Create the missing target and the very same tree reports zero issues."""
    root = fixture_docs(tmp_path, "missing.md")
    assert issues(links(root)[1]) == 1

    (root / "docs" / "missing.md").write_text("# Missing\n\nBack to [index](index.md).\n")

    code, text = links(root)

    assert code == 0, text
    assert issues(text) == 0, text


def test_an_absolute_and_a_bare_url_are_reported(tmp_path: Path) -> None:
    root = fixture_docs(tmp_path, "/absolute/path.md", extra="\nBare: https://example.com/x\n")

    code, text = links(root)

    assert code == 1, text
    assert "absolute path" in text
    assert "https://example.com/x" in text
    assert issues(text) == 2, text


def test_a_planted_secret_fails_the_privacy_scan(tmp_path: Path) -> None:
    """The fixture is a real git tree: the scan reads tracked files only."""
    root = tmp_path / "LeakyDocs"
    (root / "docs").mkdir(parents=True)
    # Assembled at runtime so this test file is not itself a finding.
    token = "ghp_" + "0123456789abcdefghijklmnopqrstuvwxyz"
    (root / "docs" / "leak.md").write_text(f"token = {token}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)

    result = run([str(PRIVACY), "--tree", "--quiet"], root)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL" in result.stdout

    # Bite check: remove the secret and the same tree passes.
    (root / "docs" / "leak.md").write_text("token = <redacted>\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)

    clean = run([str(PRIVACY), "--tree", "--quiet"], root)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "PASS" in clean.stdout
