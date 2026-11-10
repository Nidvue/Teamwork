"""Workspace hygiene: no unnecessary comments, no temp or stale debris.

Every agent must keep the tree clean and organised (see the COMMENTS and CLEAN
WORKING TREE rules in ``templates/AGENTS.md`` and the Working clean section of
every role charter). These checks make the rule enforceable instead of aspirational.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

#: Temp, editor and OS noise that must never be committed.
TEMP_PATTERNS = (
    "*.orig",
    "*.rej",
    "*.bak",
    "*.tmp",
    "*.temp",
    "*~",
    "*.log",
    "*.swp",
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
)

#: Names that suggest a draft or scratch file left behind.
STRAY_NAMES = re.compile(
    r"^(?:untitled|draft|tmp|temp|scratch|wip|copy|old|new|backup)\b.*\.\w+$", re.IGNORECASE
)

#: Directives that are tooling instructions, not commented-out code.
DIRECTIVE = re.compile(
    r"^(?:type:\s*ignore|noqa|pragma:|nosec|pyright:|ruff:|mypy:|"
    r"isort:|fmt:\s*(?:on|off)|fmt:|noqa\b)"
)

ROOT_ALLOWLIST = {
    ".editorconfig",
    ".git",
    ".github",
    ".gitattributes",
    ".gitignore",
    ".mypy_cache",
    ".pi",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "SKILL.md",
    "assets",
    "build",
    "dist",
    "docs",
    "mkdocs.yml",
    "pyproject.toml",
    "references",
    "roles",
    "scripts",
    "site",
    "src",
    "templates",
    "tests",
    "reports",
    "coverage",
}


@pytest.fixture(scope="module")
def root() -> Path:
    return Path(__file__).resolve().parents[2]


def tracked(root: Path) -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


# --------------------------------------------------------------------------- #
# no debris
# --------------------------------------------------------------------------- #


def test_no_temp_or_stale_files_are_tracked(root):
    offenders = []
    for rel in tracked(root):
        name = Path(rel).name
        if any(Path(rel).match(pattern) for pattern in TEMP_PATTERNS):
            offenders.append(rel)
        elif STRAY_NAMES.match(name):
            offenders.append(rel)
    assert offenders == [], f"temp/stale files are tracked: {offenders}"


def test_repository_root_contains_only_expected_entries(root):
    """Committed debris is the defect; gitignored build/CI output is expected.

    The CI test job writes ``reports/`` for the junit and coverage artefacts, so
    an entry that ``git check-ignore`` matches is not a hygiene failure.
    """
    unexpected = []
    for entry in sorted(root.iterdir()):
        name = entry.name
        if name in ROOT_ALLOWLIST or name.endswith(".egg-info"):
            continue
        ignored = (
            subprocess.run(
                ["git", "check-ignore", "-q", name], cwd=root, capture_output=True
            ).returncode
            == 0
        )
        if not ignored:
            unexpected.append(name)
    assert unexpected == [], f"unexpected entries in the repository root: {unexpected}"


def test_no_editor_or_os_noise_on_disk(root):
    """Not just tracked: nothing obvious may be lying around untracked either."""
    skip = {
        ".git",
        ".pi",
        ".venv",
        "site",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
    offenders = []
    for path in root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.is_file() and (
            path.name.endswith(".orig")
            or path.name.endswith(".rej")
            or path.name.endswith("~")
            or path.name == ".DS_Store"
        ):
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], f"editor/OS noise present: {offenders}"


# --------------------------------------------------------------------------- #
# no unnecessary comments
# --------------------------------------------------------------------------- #


def _commented_out_code(path: Path) -> list[tuple[int, str]]:
    """Comment lines whose body is a real Python statement (not a directive)."""
    found: list[tuple[int, str]] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline)
    except (tokenize.TokenError, IndentationError):
        return found
    code_nodes = (
        ast.Assign,
        ast.AugAssign,
        ast.AnnAssign,
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.With,
        ast.Return,
        ast.Import,
        ast.ImportFrom,
        ast.FunctionDef,
        ast.ClassDef,
        ast.Delete,
        ast.Raise,
    )
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        body = token.string.lstrip("#").strip()
        if len(body) < 8 or DIRECTIVE.match(body):
            continue
        try:
            tree = ast.parse(body)
        except SyntaxError:
            continue
        if not tree.body:
            continue
        node = tree.body[0]
        if isinstance(node, code_nodes):
            found.append((token.start[0], body[:80]))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            found.append((token.start[0], body[:80]))
    return found


def test_no_commented_out_code_in_shipped_python(root):
    offenders = {}
    for base in (root / "src" / "teamwork", root / "scripts"):
        for path in sorted(base.rglob("*.py")):
            hits = _commented_out_code(path)
            if hits:
                offenders[str(path.relative_to(root))] = hits
    assert offenders == {}, f"commented-out code: {offenders}"


def test_no_unowned_todo_markers(root):
    """An actionable marker must name a tracked task, or it does not exist.

    Only *comments that begin with* the marker count: a marker inside a string is
    data, and a comment that merely mentions markers is describing a rule, not
    filing work.
    """
    marker = re.compile(r"^\s*(TODO|FIXME|XXX|HACK)\b")
    owned = re.compile(r"^\s*(TODO|FIXME|XXX|HACK)\(T-\d+\)")
    offenders = []
    for base in (root / "src", root / "scripts", root / "tests"):
        for path in sorted(base.rglob("*.py")):
            try:
                tokens = tokenize.generate_tokens(
                    io.StringIO(path.read_text(encoding="utf-8")).readline
                )
            except (tokenize.TokenError, IndentationError):
                continue
            for token in tokens:
                if token.type != tokenize.COMMENT:
                    continue
                body = token.string.lstrip("#")
                if marker.match(body) and not owned.match(body):
                    offenders.append(f"{path.relative_to(root)}:{token.start[0]}")
    assert offenders == [], f"unowned TODO/FIXME markers: {offenders}"


# --------------------------------------------------------------------------- #
# the rule itself is documented for every agent
# --------------------------------------------------------------------------- #


def test_every_role_charter_documents_working_clean(root):
    for path in sorted((root / "roles").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "### Working clean (all roles)" in text, path.name
        assert "Comments:" in text, path.name
        assert "Working tree:" in text, path.name


def test_agents_template_documents_comments_and_clean_tree(root):
    text = (root / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    assert "**COMMENTS**" in text
    assert "**CLEAN WORKING TREE**" in text


def test_engineering_reference_documents_the_comments_policy(root):
    text = (root / "references" / "Engineering.md").read_text(encoding="utf-8")
    assert "### Comments - write none that the code already says" in text
    assert "### Working tree - clean, structured, current" in text


def test_skill_documents_the_housekeeping_rule(root):
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    assert "Everyone keeps the tree clean" in text
