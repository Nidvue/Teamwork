"""Acceptance: the documentation tells the truth to a reader.

The subject is a **fresh checkout** of the committed tree, not this team's
worktree: ``teamwork.py links`` skips any directory named ``.pi`` (the engine's
``SKIP_DIRS``), and every worktree lives under ``.pi/Teamwork/...``, so a link
check run inside one would scan zero files and pass vacuously. A user meets the
docs in a clone, so the tests copy the committed tree with ``git archive`` into
``tmp_path`` and drive that.

Accepted from the outside - the reader's tools, not the author's:

1. `teamwork.py links` reports ``0`` issues on a fresh checkout (a broken
   internal link, a bare URL, a malformed external URL or a missing back-link is
   a defect a reader hits);
2. every committed ``docs/Team/*.md`` opens with an ``# `` H1 and states a
   non-empty ``Owner:`` (the writing standard the team publishes as its
   contract), and the manifest's known shape is not silently exempted;
3. the install commands the README prints name a distribution that exists in
   ``pyproject.toml`` - parsed from both files, not hard-coded.

Owner: reviewer. Task: T-0003. Requirement: acceptance layer, area ``docs``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from cli_harness import run_shim
from gate_fixtures import checkout

AREA = "docs"
DOCS_TEAM = Path("docs") / "Team"
README = Path("README.md")
PYPROJECT = Path("pyproject.toml")

#: ``docs/Team/AuditManifest.md`` is *generated* by `ledger export`
#: (`src/teamwork/engine.py`, ``_emit_manifest``) and opens with ``# Audit report``
#: rather than an agent-owned H1 + ``Owner:`` line. It is excluded by name, and by
#: name only: an exclusion list of one generated file cannot hide a hand-written
#: document that lost its owner.
GENERATED_DOCS = {"AuditManifest.md"}


def _commit_docs(root: Path) -> list[Path]:
    """Every committed ``docs/Team/*.md`` a reader can open in the checkout."""
    docs = sorted((root / DOCS_TEAM).glob("*.md"))
    assert docs, f"no documentation found under {root / DOCS_TEAM}"
    return docs


def test_link_check_reports_zero_issues(tmp_path):
    """ACCEPT: `python3 scripts/teamwork.py links` -> exit 0, `# issues: 0`."""
    tree = checkout(tmp_path / "clone")

    result = run_shim(["links", "--project", str(tree), "--team", "Acceptance"])

    assert result.returncode == 0, (
        "the link checker CI blocks on fails for a reader of this tree:\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert "# issues: 0" in result.stdout, result.stdout
    # A check that skips files is not an acceptance: the checkout is nothing but
    # committed text, so the checker must have read *every* markdown file a
    # reader can open, not a convenient subset.
    files = int(re.search(r"# (\d+) markdown file\(s\)", result.stdout).group(1))
    readable = len(list(tree.rglob("*.md")))
    assert files == readable, (
        f"the link check read {files} of the {readable} markdown file(s) in the checkout"
    )
    for section in ("## broken internal links", "## bare URLs (wrap them as [title](url))"):
        assert section in result.stdout, f"missing section {section!r}:\n{result.stdout}"


def test_every_team_doc_has_an_h1_and_an_owner(tmp_path):
    """ACCEPT: each hand-written doc opens with `# ` and names a non-empty owner."""
    tree = checkout(tmp_path / "clone")

    offenders = []
    for path in _commit_docs(tree):
        if path.name in GENERATED_DOCS:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        h1 = next((line for line in lines if line.startswith("# ")), None)
        if h1 is None or not h1[2:].strip():
            offenders.append(f"{path.name}: no H1")
            continue
        # Only the document preamble counts. A section-level `Owner:` further
        # down attributes a section, not the document, so accepting it would let
        # a doc lose its real owner and still pass.
        first_section = next(
            (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
        )
        preamble = lines[:first_section]
        owner = next((line for line in preamble if line.startswith("Owner:")), None)
        if owner is None:
            offenders.append(f"{path.name}: no preamble Owner: line")
        elif not owner[len("Owner:") :].strip():
            offenders.append(f"{path.name}: empty Owner: line")
    assert not offenders, "documentation a reader cannot attribute:\n" + "\n".join(offenders)


def _manifest(tree: Path) -> dict:
    """``pyproject.toml`` parsed by the stdlib parser, or skip on Python < 3.11."""
    tomllib = pytest.importorskip("tomllib", reason="tomllib is standard from Python 3.11")
    return tomllib.loads((tree / PYPROJECT).read_text(encoding="utf-8"))


def _is_distribution_name(name: str) -> bool:
    """Whether a token after ``install`` names a package rather than a source."""
    return not name.startswith((".", "/", "~", "http")) and name != "https"


def test_readme_install_commands_name_a_real_distribution(tmp_path):
    """ACCEPT: the README's install commands name a package `pyproject.toml` declares."""
    tree = checkout(tmp_path / "clone")
    declared = _manifest(tree)["project"]["name"]
    readme = (tree / README).read_text(encoding="utf-8")

    # `pip install <name>`, `pipx install <name>`, `uvx --from <name>` - the
    # commands a reader copies. Flags and URLs are not distribution names.
    commands = re.findall(
        r"(?:pip|pipx)\s+install\s+(?:--[\w-]+\s+)*([A-Za-z0-9._/-]+)"
        r"|uvx\s+--from\s+([A-Za-z0-9._-]+)",
        readme,
    )
    names = {match[0] or match[1] for match in commands}
    assert names, "the README documents no install command to accept:\n" + readme[:400]
    assert declared in names, (
        f"the README never installs the declared distribution {declared!r}; it names {sorted(names)}"
    )
    # And no phantom names: every distribution the README tells a reader to
    # install is one this project actually builds. A local path or a URL is an
    # install *source*, not a distribution name, so those are not checked.
    phantom = sorted(name for name in names - {declared} if _is_distribution_name(name))
    assert not phantom, (
        f"the README tells a reader to install {phantom}, which `pyproject.toml` does "
        f"not declare (it builds {declared!r})"
    )


def test_the_distribution_name_is_read_from_the_manifest_not_hard_coded(tmp_path):
    """The acceptance above is only meaningful if it parses the real manifest."""
    project = _manifest(checkout(tmp_path / "clone"))["project"]
    assert project["name"] == "teamwork-agents", project["name"]
    assert project["scripts"]["teamwork"] == "teamwork.cli:main", project["scripts"]
