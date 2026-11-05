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
3. the install commands a reader is pointed to - the README's own, or those on
   the install page the README links - name a distribution that exists in
   ``pyproject.toml``; parsed from both files, not hard-coded.

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


INSTALL_COMMAND = re.compile(
    r"(?:pip|pipx)\s+install\s+(?:--[\w-]+\s+)*([A-Za-z0-9._/][A-Za-z0-9._/-]*)"
    r"|uvx\s+--from\s+([A-Za-z0-9._-]+)"
)

MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def _install_commands(text: str) -> set[str]:
    return {match[0] or match[1] for match in INSTALL_COMMAND.findall(text)}


def _install_pages(tree: Path, readme: str) -> list[Path]:
    """The install page(s) the README sends a reader to, in the checkout."""
    pages = set()
    for label, target in MARKDOWN_LINK.findall(readme):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        if "install" not in label.lower() and "install" not in target.lower():
            continue
        path = (tree / target.split("#", 1)[0]).resolve()
        try:
            path.relative_to(tree.resolve())
        except ValueError:
            continue
        if path.suffix == ".md" and path.is_file():
            pages.add(path)
    return sorted(pages)


def install_problems(tree: Path) -> list[str]:
    """Every way the README's install route fails to name a declared package."""
    readme = (tree / README).read_text(encoding="utf-8")
    declared = _manifest(tree)["project"]["name"]
    pages = _install_pages(tree, readme)
    names = _install_commands(readme)
    for page in pages:
        names |= _install_commands(page.read_text(encoding="utf-8"))

    problems = []
    if not pages and not names:
        problems.append("the README documents no install command and links no page that does")
    if not names:
        problems.append("the README's install route documents no install command to accept")
    if names and declared not in names:
        problems.append(
            f"the README's install route never installs the declared distribution "
            f"{declared!r}; it names {sorted(names)}"
        )
    phantom = sorted(name for name in names - {declared} if _is_distribution_name(name))
    if phantom:
        problems.append(
            f"a reader is told to install {phantom}, which `pyproject.toml` does not "
            f"declare (it builds {declared!r})"
        )
    return problems


def test_readme_install_commands_name_a_real_distribution(tmp_path):
    """ACCEPT: the README, or the install page it links, names a declared package."""
    tree = checkout(tmp_path / "clone")
    problems = install_problems(tree)
    assert problems == [], "\n".join(problems)


def test_mutant_a_phantom_distribution_on_the_linked_page_is_reported(tmp_path):
    """The link is followed: a page that names another package must fail."""
    tree = checkout(tmp_path / "clone")
    page = tree / "docs" / "guide" / "install.md"
    text = page.read_text(encoding="utf-8")
    assert "pipx install teamwork-agents" in text, "mutant anchor is gone"
    page.write_text(
        text.replace("pipx install teamwork-agents", "pipx install phantom-agents", 1),
        encoding="utf-8",
    )

    problems = install_problems(tree)
    assert any("phantom-agents" in problem for problem in problems), problems


def test_mutant_removing_the_install_link_is_reported(tmp_path):
    """A README with no command must point at a page that has one."""
    tree = checkout(tmp_path / "clone")
    readme = tree / README
    text = readme.read_text(encoding="utf-8")
    mutant = text.replace("[Installation](docs/guide/install.md)", "Installation")
    assert mutant != text, "mutant anchor is gone"
    readme.write_text(mutant, encoding="utf-8")

    problems = install_problems(tree)
    assert any("links no page that does" in problem for problem in problems), problems


def test_mutant_a_phantom_command_in_the_readme_is_still_reported(tmp_path):
    """The README's own commands are checked too, not only the linked page."""
    tree = checkout(tmp_path / "clone")
    readme = tree / README
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n```bash\npip install phantom-readme\n```\n",
        encoding="utf-8",
    )

    problems = install_problems(tree)
    assert any("phantom-readme" in problem for problem in problems), problems


def test_the_distribution_name_is_read_from_the_manifest_not_hard_coded(tmp_path):
    """The acceptance above is only meaningful if it parses the real manifest."""
    project = _manifest(checkout(tmp_path / "clone"))["project"]
    assert project["name"] == "teamwork-agents", project["name"]
    assert project["scripts"]["teamwork"] == "teamwork.cli:main", project["scripts"]
