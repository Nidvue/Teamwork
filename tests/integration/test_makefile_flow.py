"""Integration: the real Makefile targets, executed end to end.

The Makefile is the documented developer surface (``make lint``, ``make help``,
``make release-check``), and nothing else executes it. This module runs the
*committed* Makefile through ``make`` with an explicit ``PYTHON`` so the result
does not depend on which interpreter happens to be first on ``PATH``:

* ``make help`` lists every documented target;
* ``make help`` with a target-less comment stays out of the list (a self-check
  that the ``## `` convention is what drives the list);
* ``make lint`` is green on this checkout;
* a target whose command fails returns non-zero - proved twice: with a
  non-existent interpreter, and with a real style error planted in a scratch
  tree that ``make lint`` then reports;
* every gate ``make lint`` runs is executed on that scratch tree: one planted
  violation per gate (ruff check, ruff format, the no-comment rule, the commit
  identity audit) is reported, so dropping a gate from the target - or replacing
  ``identity --audit`` with another ``teamwork.py`` subcommand, which the static
  parity test cannot tell apart - leaves a violation silently green and fails
  here instead.

``make lint`` ends with ``teamwork.py identity --audit``, which audits the
repository of the *current* directory. The scratch tree is therefore a git
repository carrying one canonical ``Developer`` commit (with its ``Acting
role:`` trailer): a bare directory made the audit fail with "not a git
repository", a gate unrelated to the file under test (T-0018, CI run
41949313654 at ``088e185``).

``make test`` and ``make ci`` are deliberately not run: they are slow and are
covered by their own layers.

Every test here needs GNU make, so one guard - routed through
``tests.tooling.require_tool`` - skips the file where it is absent and names the
tool. It is a plain function so a test can call it and prove what it does.

Owner: tester. Tasks: T-0004, T-0018.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.tooling import require_tool

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"


def make_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("TEAMWORK_")}
    env["PYTHON"] = sys.executable
    env.pop("PYTHONPATH", None)
    return env


def run_make(args: list[str], cwd: Path, *, env: dict[str, str] | None = None):
    assert MAKEFILE.is_file(), f"{MAKEFILE} is missing"
    return subprocess.run(
        ["make", "-f", str(MAKEFILE), *args],
        cwd=str(cwd),
        env=env or make_env(),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


ROLE_NAME = "Developer"
ROLE_EMAIL = "developer@agents.nidvue.com"
GIT_IDENTITY = [
    "-c",
    f"user.name={ROLE_NAME}",
    "-c",
    f"user.email={ROLE_EMAIL}",
    "-c",
    "commit.gpgsign=false",
]


def git_env() -> dict[str, str]:
    """The host environment without a git override that could rewrite a commit."""
    return {
        key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "TEAMWORK_"))
    }


def run_git(tree: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=str(tree),
        env=git_env(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def git_or_die(tree: Path, args: list[str]) -> None:
    done = run_git(tree, args)
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stdout}{done.stderr}"


def lint_tree(tmp_path: Path) -> Path:
    """A scratch tree ``make lint`` must accept, in a repository it must audit."""
    scratch = tmp_path / "LintTree"
    scratch.mkdir(parents=True)
    (scratch / "planted.py").write_text(
        '"""A deliberately plain fixture the whole lint target accepts."""\n\nVALUE = 1\n',
        encoding="utf-8",
    )
    git_or_die(scratch, ["init", "-q"])
    git_or_die(scratch, ["add", "-A"])
    git_or_die(
        scratch,
        ["commit", "-q", "-m", f"chore(scratch): lint fixture\n\nActing role: {ROLE_NAME}\n"],
    )
    return scratch


@pytest.fixture(autouse=True)
def require_make():
    make_required()


def make_required() -> None:
    """Skip when GNU make is absent: the targets below *are* ``make``."""
    require_tool("make")


DOCUMENTED_TARGETS = (
    "help",
    "lint",
    "format",
    "test",
    "test-unit",
    "test-integration",
    "test-acceptance",
    "verify",
    "privacy",
    "links",
    "release-consistency",
    "release-check",
    "ci",
    "clean",
)


def test_help_lists_every_documented_target() -> None:
    result = run_make(["help"], REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Teamwork - available targets:" in result.stdout
    for target in DOCUMENTED_TARGETS:
        assert target in result.stdout, f"{target} missing from `make help`"
    assert f"PYTHON={sys.executable}" in result.stdout


def test_help_bites_when_the_doc_comment_marker_is_removed(tmp_path: Path) -> None:
    """A target is listed only because of its ``## `` comment: drop it, it vanishes."""
    text = MAKEFILE.read_text(encoding="utf-8")
    marker = "links: ## Check markdown links, URLs and back-links."
    assert marker in text, "the links target doc comment changed; update this test"
    mutated = tmp_path / "Makefile"
    mutated.write_text(text.replace(marker, "links: # Check markdown links."), encoding="utf-8")

    result = subprocess.run(
        ["make", "-f", str(mutated), "help"],
        cwd=str(REPO_ROOT),
        env=make_env(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All checks passed" not in result.stdout
    assert "links" not in result.stdout.split("PYTHON=")[0]


def test_lint_is_green_on_this_checkout() -> None:
    result = run_make(["lint"], REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All checks passed!" in result.stdout
    assert "already formatted" in result.stdout


def test_lint_fails_when_the_interpreter_cannot_run_ruff() -> None:
    """A failing command must fail the target, not be swallowed."""
    env = make_env()
    env["PYTHON"] = "/nonexistent/python-that-cannot-exist"

    result = run_make(["lint"], REPO_ROOT, env=env)

    assert result.returncode != 0
    assert "Error" in result.stdout + result.stderr


def test_lint_reports_a_real_style_error_and_goes_green_when_it_is_removed(
    tmp_path: Path,
) -> None:
    """The subject of ``make lint`` is the tree: plant a defect, then remove it."""
    scratch = lint_tree(tmp_path)
    subject = scratch / "planted.py"

    clean = run_make(["lint"], scratch)
    assert clean.returncode == 0, clean.stdout + clean.stderr

    subject.write_text("import os\nx=1\n", encoding="utf-8")

    broken = run_make(["lint"], scratch)
    assert broken.returncode != 0, broken.stdout + broken.stderr
    assert "F401" in broken.stdout + broken.stderr

    subject.write_text('"""Fixed."""\n\nx = 1\n', encoding="utf-8")

    fixed = run_make(["lint"], scratch)
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr


def plant_style_error(tree: Path) -> None:
    (tree / "planted.py").write_text("import os\nx=1\n", encoding="utf-8")


def plant_unformatted(tree: Path) -> None:
    (tree / "planted.py").write_text("def add( a, b ):\n    return a+b\n", encoding="utf-8")


def plant_explanatory_comment(tree: Path) -> None:
    source = tree / "src"
    source.mkdir()
    (source / "planted.py").write_text(
        '"""Module."""\n\nVALUE = 1  # explain the value\n', encoding="utf-8"
    )


def plant_unattributed_commit(tree: Path) -> None:
    git_or_die(tree, ["commit", "-q", "--allow-empty", "-m", "chore(scratch): second change"])


GATE_VIOLATIONS = (
    pytest.param(plant_style_error, "F401", id="ruff-check"),
    pytest.param(plant_unformatted, "would be reformatted", id="ruff-format"),
    pytest.param(plant_explanatory_comment, "explanatory comment", id="check-comments"),
    pytest.param(plant_unattributed_commit, "Acting role", id="identity"),
)


@pytest.mark.parametrize(("plant", "marker"), GATE_VIOLATIONS)
def test_lint_reports_a_violation_of_every_gate_it_runs(tmp_path: Path, plant, marker: str) -> None:
    """Each gate in the target is really executed, not just listed.

    The fixture is green before the plant, so a gate removed from the recipe - or
    an ``identity --audit`` line swapped for another ``teamwork.py`` subcommand,
    which the parity test's signature comparison cannot see - leaves that gate's
    violation unreported and this case red.
    """
    scratch = lint_tree(tmp_path)

    baseline = run_make(["lint"], scratch)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr

    plant(scratch)

    broken = run_make(["lint"], scratch)
    assert broken.returncode != 0, broken.stdout + broken.stderr
    assert marker in broken.stdout + broken.stderr
