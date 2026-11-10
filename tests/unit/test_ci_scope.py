"""Unit: the CI scope classifier's prose set, gate answers and CLI surface.

`scripts/ci_scope.py` decides whether the five-lane test matrix runs, so every
branch of that decision is pinned here: prose-only, shipping, mixed, empty, an
undetermined change set, a tag push and a non-push event. The `docs.yml` trigger
list is pinned to the classifier's own :func:`prose_paths`, and the workflow is
pinned to running the module instead of carrying a second copy of the logic.

Owner: team-leader. Task: T-0001.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci_scope.py"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DOCS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"

EXPECTED_PROSE_PATHS = (
    "docs/**",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CITATION.cff",
    "LICENSE",
    "AGENTS.md",
    "assets/**",
    "mkdocs.yml",
)


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CI_SCOPE = _load(SCRIPT, "ci_scope_under_test")


def docs_trigger_paths() -> tuple[str, ...]:
    """The literal `paths:` entries under `push:` in docs.yml."""
    lines = DOCS_WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "paths:"), None)
    assert start is not None, "docs.yml has no `paths:` trigger list"
    key_indent = len(lines[start]) - len(lines[start].lstrip())
    markers: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if len(line) - len(line.lstrip()) <= key_indent:
            break
        if not stripped.startswith("- "):
            break
        markers.append(stripped[2:].strip().strip('"').strip("'"))
    assert markers, "docs.yml has an empty `paths:` trigger list"
    return tuple(markers)


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_prose_paths_are_the_documented_set() -> None:
    assert CI_SCOPE.prose_paths() == EXPECTED_PROSE_PATHS


@pytest.mark.parametrize(
    "path",
    (
        "docs/guide/ci.md",
        "docs/index.md",
        "assets/logo.svg",
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CITATION.cff",
        "LICENSE",
        "AGENTS.md",
        "mkdocs.yml",
    ),
)
def test_is_prose_accepts_the_prose_set(path: str) -> None:
    assert CI_SCOPE.is_prose(path) is True


@pytest.mark.parametrize(
    "path",
    (
        "docs",
        "docs-notes/page.md",
        "assets2/logo.svg",
        "README.md.bak",
        "LICENSE.md",
        "NOTICE",
        "SKILL.md",
        "AGENTS.template.md",
        "src/teamwork/cli.py",
        "scripts/teamwork.py",
        ".github/workflows/ci.yml",
        "tests/unit/test_ci_scope.py",
        "Makefile",
        "pyproject.toml",
    ),
)
def test_is_prose_rejects_near_misses_and_shipping_paths(path: str) -> None:
    assert CI_SCOPE.is_prose(path) is False


def test_a_prose_only_change_set_is_not_code() -> None:
    scope = CI_SCOPE.classify_files(("docs/guide/ci.md", "README.md", "assets/logo.svg"))

    assert (scope.code, scope.prose) == (False, True)


def test_a_shipping_change_set_is_code() -> None:
    scope = CI_SCOPE.classify_files(("src/teamwork/cli.py", "docs/guide/ci.md"))

    assert (scope.code, scope.prose) == (True, False)


def test_a_mixed_change_set_is_code_even_when_prose_is_the_majority() -> None:
    scope = CI_SCOPE.classify_files(("docs/a.md", "README.md", "scripts/ci_scope.py"))

    assert (scope.code, scope.prose) == (True, False)


def test_an_empty_change_set_is_neither_code_nor_prose() -> None:
    scope = CI_SCOPE.classify_files(())

    assert (scope.code, scope.prose) == (False, False)


def test_an_undetermined_change_set_is_code() -> None:
    scope = CI_SCOPE.classify(repo=Path("/nonexistent/ci-scope-probe"))

    assert (scope.code, scope.prose) == (True, False)
    assert scope.undetermined is True


def test_a_non_push_event_runs_every_job() -> None:
    scope = CI_SCOPE.classify(event="pull_request", files=["docs/guide/ci.md"])

    assert (scope.code, scope.prose) == (True, False)


def test_a_tag_push_runs_only_the_tag_sensitive_jobs() -> None:
    scope = CI_SCOPE.classify(
        event="push",
        ref="refs/tags/v1.2.3",
        files=["docs/guide/ci.md"],
    )

    assert (scope.code, scope.prose) == (False, False)


def test_an_explicit_file_list_does_not_touch_git() -> None:
    scope = CI_SCOPE.classify(files=["src/teamwork/cli.py"], repo=Path("/nonexistent"))

    assert (scope.code, scope.prose) == (True, False)
    assert scope.files == ("src/teamwork/cli.py",)


def test_docs_trigger_list_is_the_classifier_prose_set() -> None:
    assert docs_trigger_paths() == CI_SCOPE.prose_paths(), (
        "docs.yml's `paths:` list and scripts/ci_scope.py::PROSE_PATHS disagree; "
        "a path in one list and not the other is a hole in one of the two gates"
    )


def test_ci_runs_the_module_instead_of_carrying_a_second_copy() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python scripts/ci_scope.py" in text, "the scope step does not run the module"
    assert "PROSE=" not in text, "ci.yml still carries an inline prose regex"
    assert "UNDETERMINED=" not in text, "ci.yml still carries the inline classifier"


def test_the_cli_prints_code_and_prose_for_a_prose_path() -> None:
    result = cli("--file", "docs/guide/ci.md")

    assert result.returncode == 0, result.stderr
    assert "code=false" in result.stdout.splitlines()
    assert "prose=true" in result.stdout.splitlines()


def test_the_cli_prints_code_and_prose_for_a_shipping_path() -> None:
    result = cli("--file", "scripts/ci_scope.py")

    assert result.returncode == 0, result.stderr
    assert "code=true" in result.stdout.splitlines()
    assert "prose=false" in result.stdout.splitlines()


def test_the_cli_appends_the_two_answers_to_the_step_output(tmp_path: Path) -> None:
    sink = tmp_path / "github-output.txt"
    sink.write_text("", encoding="utf-8")

    result = cli("--file", "README.md", "--output", str(sink))

    assert result.returncode == 0, result.stderr
    assert sink.read_text(encoding="utf-8").splitlines() == ["code=false", "prose=true"]


def scope_step_flags() -> list[str]:
    """Every long flag the `scope` job's run line passes to the classifier."""
    lines = CI_WORKFLOW.read_text(encoding="utf-8").splitlines()
    command = [
        line for line in lines if line.strip().startswith("run:") and "scripts/ci_scope.py" in line
    ]
    assert command, "ci.yml no longer runs scripts/ci_scope.py in a run: line"
    return sorted({flag for line in command for flag in re.findall(r"--[a-z][a-z0-9-]+", line)})


def test_the_workflow_publishes_the_answers_to_the_step_output() -> None:
    assert "--output" in scope_step_flags(), (
        'the scope step must pass --output "${GITHUB_OUTPUT}", or the job publishes no outputs'
    )


def test_every_flag_the_workflow_passes_is_documented() -> None:
    flags = scope_step_flags()
    assert flags, "the scope step passes no flags - the scan is blind"
    help_text = cli("--help").stdout

    undocumented = [flag for flag in flags if flag not in help_text]
    assert undocumented == [], (
        f"ci.yml passes flags the classifier does not document: {undocumented}"
    )
