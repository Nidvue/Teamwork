"""Integration: ``teamwork links`` as a real subprocess against real trees.

The unit layer (``tests/unit/test_integrity_fixes.py``) calls
``engine.link_report`` and the CLI in-process. This module instead drives the
*command* the docs gate runs - ``scripts/teamwork.py links``, exactly as
``.github/workflows/docs.yml`` invokes it - against throwaway project trees
under ``tmp_path``, and reads the verdict from its exit code and its sections.

Covered, one test each: a clean tree, a broken internal link, a bare URL, a
stale release-asset path, a missing back-link and its ``--no-reciprocity``
suppression, the quoted-evidence exemption in ``Archive.md``, and the
per-instance worktree regression this area exists for (a tree that lives under
``.pi/`` must be measured, not skipped).

``tests/acceptance/cli_harness.py`` offers the same subprocess runner, but a
module of this layer must not depend on the acceptance layer; the local helper
below is the pattern the sibling ``test_docs_pipeline_flow.py`` already uses.
The worktree test is mutation-proved by reverting 781b1b4 in a scratch copy.

Owner: tester. Task: T-0005.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SHIM = REPO_ROOT / "scripts" / "teamwork.py"
SRC_DIR = REPO_ROOT / "src"

#: Installed sha at the time this module was written; the fix below lives here.
BASELINE = "781b1b4"

RELEASE_ASSET = (
    "https://github.com/Nidvue/Teamwork/releases/download/v9.9.9/"
    "teamwork_agents-9.9.9-py3-none-any.whl"
)


# --------------------------------------------------------------------------- #
# Driving the command
# --------------------------------------------------------------------------- #


def run_links(cwd: Path, *args: str, timeout: int = 180) -> tuple[int, str]:
    """Run ``scripts/teamwork.py links`` from ``cwd`` and return its output."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env["TEAMWORK_SKILL_DIR"] = str(REPO_ROOT)
    env["PYTHONPATH"] = str(SRC_DIR)
    result = subprocess.run(
        [sys.executable, str(CLI_SHIM), "links", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def section(text: str, title: str) -> str:
    """The body of one ``## `` section of the report (empty when absent)."""
    marker = f"## {title}\n"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1]
    return body.split("\n## ", 1)[0]


def issues(text: str) -> int:
    for line in reversed(text.splitlines()):
        if line.startswith("# issues:"):
            return int(line.split(":", 1)[1])
    raise AssertionError(f"links printed no issue count:\n{text}")


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def home(root: Path, body: str) -> Path:
    """A one-document project; ``body`` is the rest of ``README.md``."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(f"# Home\n\n{body}\n", encoding="utf-8")
    return root


# --------------------------------------------------------------------------- #
# 1 - a clean tree
# --------------------------------------------------------------------------- #


def test_a_clean_tree_exits_zero_and_prints_the_count_it_measured(tmp_path: Path) -> None:
    root = tmp_path / "Clean"
    write(
        root,
        {
            "README.md": "# Home\n\n[the page](docs/page.md)\n",
            "docs/page.md": "# Page\n\nBack to [home](../README.md)\n",
        },
    )

    code, text = run_links(root)

    assert code == 0, text
    assert issues(text) == 0, text
    # Two documents that link to each other: a measured count, not a blank run.
    assert "# 2 markdown file(s), 2 internal link(s)" in text, text
    assert f"# Link check ({root.resolve()})" in text, text
    assert "- none" in section(text, "broken internal links")


# --------------------------------------------------------------------------- #
# 2 - a broken internal link
# --------------------------------------------------------------------------- #


def test_a_broken_internal_link_exits_one_and_names_file_and_target(tmp_path: Path) -> None:
    root = home(tmp_path / "Broken", "See [the page](docs/missing.md).")

    code, text = run_links(root)

    assert code == 1, text
    assert "README.md: [the page](docs/missing.md) - target does not exist" in text, text
    assert issues(text) == 1, text


# --------------------------------------------------------------------------- #
# 3 - a bare URL
# --------------------------------------------------------------------------- #


def test_a_bare_url_is_reported_under_bare_urls_and_fails(tmp_path: Path) -> None:
    root = home(tmp_path / "Bare", "Source: https://example.org/report")

    code, text = run_links(root)

    assert code == 1, text
    assert "README.md: https://example.org/report" in section(
        text, "bare URLs (wrap them as [title](url))"
    )
    assert issues(text) == 1, text


# --------------------------------------------------------------------------- #
# 4 - a stale release asset
# --------------------------------------------------------------------------- #


def test_a_release_asset_path_that_does_not_exist_is_reported_broken(tmp_path: Path) -> None:
    """An install command pointing at a missing ``releases/download/<tag>/`` asset."""
    root = home(
        tmp_path / "StaleAsset",
        "```console\npip install releases/download/v9.9.9/teamwork_agents-9.9.9-py3-none-any.whl\n```\n\n"
        "Download [the wheel](releases/download/v9.9.9/teamwork_agents-9.9.9-py3-none-any.whl).",
    )

    code, text = run_links(root)

    assert code == 1, text
    assert (
        "README.md: [the wheel]"
        "(releases/download/v9.9.9/teamwork_agents-9.9.9-py3-none-any.whl) - target does not exist"
    ) in text, text
    # The fenced command is illustrative text, not a maintained link: one issue only.
    assert issues(text) == 1, text

    # Bite check: the same link with the asset present is clean.
    write(
        root,
        {"releases/download/v9.9.9/teamwork_agents-9.9.9-py3-none-any.whl": "wheel\n"},
    )
    code, text = run_links(root)
    assert code == 0, text


def test_a_remote_release_asset_url_is_not_checked_offline(tmp_path: Path) -> None:
    """No network: an absolute release URL stays a valid direct URL."""
    root = home(tmp_path / "RemoteAsset", f"[the wheel]({RELEASE_ASSET})")

    code, text = run_links(root)

    assert code == 0, text
    assert "- none" in section(text, "external links that are not valid direct URLs"), text


# --------------------------------------------------------------------------- #
# 5 - reciprocity
# --------------------------------------------------------------------------- #


def test_a_doc_nothing_links_back_to_is_a_missing_back_link(tmp_path: Path) -> None:
    root = tmp_path / "Reciprocity"
    write(
        root,
        {
            "README.md": "# Home\n\n[broken](missing.md)\n",
            "docs/index.md": "# Index\n\nSee [the page](page.md).\n",
            "docs/page.md": "# Page\n\nNot linking back.\n",
        },
    )

    code, text = run_links(root)

    assert code == 1, text
    assert "docs/index.md links to docs/page.md but docs/page.md does not link back" in text, text
    assert issues(text) == 2, text  # the missing back-link plus README's broken link

    # --no-reciprocity suppresses exactly that section, and still fails on the link.
    code, text = run_links(root, "--no-reciprocity")

    assert code == 1, text
    assert "missing back-links" not in text, text
    assert "README.md: [broken](missing.md) - target does not exist" in text, text
    assert issues(text) == 1, text


# --------------------------------------------------------------------------- #
# 6 - quoted evidence in Archive.md
# --------------------------------------------------------------------------- #


def test_a_link_quoted_inside_archive_evidence_is_not_reported(tmp_path: Path) -> None:
    """A quotation is not a maintained link: the author's text is checked in full."""
    root = tmp_path / "Archived"
    write(
        root,
        {
            "docs/Team/Archive.md": (
                "# Archive\n\n## P-1 - an entry\n\n"
                "- self-check: [pass] checked [gone](missing.md) and https://example.org/q\n"
                "- author evidence: see [also gone](nope.md)\n"
                "\nAuthored prose: [kept](kept.md).\n"
            ),
            "docs/Team/kept.md": "# Kept\n\nBack to [archive](Archive.md).\n",
        },
    )

    code, text = run_links(root)

    assert code == 0, text
    assert "missing.md" not in text and "nope.md" not in text, text
    assert "example.org/q" not in text, text

    # Bite check: the same broken link outside the quoted field is reported.
    write(
        root,
        {"docs/Team/Archive.md": "# Archive\n\n## P-1\n\nAuthored: [gone](missing.md).\n"},
    )
    code, text = run_links(root)
    assert code == 1, text
    assert "target does not exist" in text, text


# --------------------------------------------------------------------------- #
# 7 - the worktree regression (781b1b4)
# --------------------------------------------------------------------------- #


def worktree(tmp_path: Path, files: dict[str, str]) -> Path:
    """One of our per-instance worktrees: under ``.pi``, with a ``.git`` entry."""
    team = tmp_path / "Project" / ".pi" / "Teamwork" / "Teams" / "X"
    (team / "Roles").mkdir(parents=True)
    path = team / "Runtime" / "Worktrees" / "Dev"
    (path / ".git").mkdir(parents=True)
    write(path, files)
    return path


def test_a_broken_link_inside_a_worktree_is_reported_and_fails(tmp_path: Path) -> None:
    """The tree sits under ``.pi``, so a skip test on the absolute path skipped all
    of it and ``links`` reported zero files while exiting 0. Measured at 781b1b4."""
    path = worktree(tmp_path, {"README.md": "# Dev\n\n[gone](missing.md)\n"})

    code, text = run_links(path)

    assert code == 1, text
    assert f"# Link check ({path.resolve()})" in text, text
    assert "# 1 markdown file(s)" in text, text
    assert "README.md: [gone](missing.md) - target does not exist" in text, text


def test_a_clean_worktree_exits_zero_so_the_regression_test_cannot_pass_vacuously(
    tmp_path: Path,
) -> None:
    path = worktree(
        tmp_path,
        {
            "README.md": "# Dev\n\n[the page](docs/page.md)\n",
            "docs/page.md": "# Page\n\nBack to [home](../README.md)\n",
            ".pi/Scratch/Notes.md": "# Note\n\n[local state](gone.md)\n",
        },
    )

    code, text = run_links(path)

    assert code == 0, text
    assert f"# Link check ({path.resolve()})" in text, text
    assert "# 2 markdown file(s), 2 internal link(s)" in text, text
    assert "gone.md" not in text, "the worktree's own .pi/ state stays skipped"
